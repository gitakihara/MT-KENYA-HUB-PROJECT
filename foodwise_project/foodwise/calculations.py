"""Transparent household scenario and optional nutrient-gap calculations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import pandas as pd

WEEKS_PER_MONTH = 365.25 / 7 / 12
NUTRIENT_COLUMNS = {
    "commodity",
    "analysis_unit",
    "nutrient",
    "population_group",
    "nutrient_per_analysis_unit",
    "nutrient_unit",
    "daily_reference",
    "reference_source",
    "reference_year",
}


@dataclass(frozen=True)
class HouseholdResult:
    weekly_per_person: float
    monthly_per_person: float
    monthly_household: float
    income_share: float | None
    affordability_score: float | None
    pressure_band: str
    priced_items: int
    requested_items: int
    full_coverage: bool


def household_result(
    *,
    weekly_basket_per_person: float,
    household_size: int,
    monthly_income: float,
    warning_share: float = 0.50,
    critical_share: float = 0.60,
    priced_items: int,
    requested_items: int,
) -> HouseholdResult:
    """Calculate scenario outputs; unavailable item prices must not be zero-filled."""
    if not isfinite(weekly_basket_per_person) or weekly_basket_per_person < 0:
        raise ValueError("Weekly basket cost cannot be negative.")
    if household_size < 1:
        raise ValueError("Household size must be at least one person.")
    if not isfinite(monthly_income) or monthly_income < 0:
        raise ValueError("Monthly income cannot be negative.")
    if not 0 <= warning_share < critical_share <= 1:
        raise ValueError("Thresholds must satisfy 0 <= warning < critical <= 1.")
    if requested_items < 1 or not 0 <= priced_items <= requested_items:
        raise ValueError("Price coverage counts are inconsistent.")

    monthly_per_person = weekly_basket_per_person * WEEKS_PER_MONTH
    monthly_household = monthly_per_person * household_size
    income_share = monthly_household / monthly_income if monthly_income > 0 else None
    score = (
        max(0.0, 100.0 * (1.0 - income_share))
        if income_share is not None
        else None
    )
    if income_share is None:
        band = "Income required"
    elif income_share >= critical_share:
        band = "Critical prototype signal"
    elif income_share >= warning_share:
        band = "Watch prototype signal"
    else:
        band = "Below prototype signals"

    return HouseholdResult(
        weekly_per_person=weekly_basket_per_person,
        monthly_per_person=monthly_per_person,
        monthly_household=monthly_household,
        income_share=income_share,
        affordability_score=score,
        pressure_band=band,
        priced_items=priced_items,
        requested_items=requested_items,
        full_coverage=priced_items == requested_items,
    )


def nutrient_gap(
    *,
    weekly_quantities: dict[str, float],
    nutrient_data: pd.DataFrame,
    expected_units: dict[str, str],
) -> pd.DataFrame:
    """Estimate daily nutrient contribution from user-supplied sourced composition data.

    Nutrient references are provided by the uploaded dataset and are not inferred
    or hard-coded by FOODWISE.
    """
    missing = sorted(NUTRIENT_COLUMNS - set(nutrient_data.columns))
    if missing:
        raise ValueError(f"Nutrient CSV is missing columns: {', '.join(missing)}")
    data = nutrient_data.copy()
    for column in ("nutrient_per_analysis_unit", "daily_reference", "reference_year"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    for column in (
        "commodity",
        "analysis_unit",
        "nutrient",
        "population_group",
        "nutrient_unit",
        "reference_source",
    ):
        data[column] = data[column].astype("string").str.strip()
    data = data.dropna(
        subset=[
            "commodity",
            "analysis_unit",
            "nutrient",
            "population_group",
            "nutrient_per_analysis_unit",
            "nutrient_unit",
            "daily_reference",
            "reference_source",
            "reference_year",
        ]
    )
    data = data[
        data[
            [
                "commodity",
                "analysis_unit",
                "nutrient",
                "population_group",
                "nutrient_unit",
                "reference_source",
            ]
        ]
        .ne("")
        .all(axis=1)
    ]
    if data.empty:
        return pd.DataFrame(
            columns=[
                "nutrient",
                "nutrient_unit",
                "estimated_per_day",
                "daily_reference",
                "reference_source",
                "reference_year",
                "reference_share",
                "remaining_to_reference",
            ]
        )
    if (
        (data["nutrient_per_analysis_unit"] < 0).any()
        or (data["daily_reference"] <= 0).any()
    ):
        raise ValueError("Nutrient amounts must be non-negative and references positive.")
    if (data["reference_year"] % 1 != 0).any():
        raise ValueError("Reference year must be a whole year.")
    if any(not isfinite(float(quantity)) or float(quantity) < 0 for quantity in weekly_quantities.values()):
        raise ValueError("Weekly food quantities must be finite and non-negative.")
    for food, quantity in weekly_quantities.items():
        if float(quantity) <= 0:
            continue
        units = set(data.loc[data["commodity"] == food, "analysis_unit"])
        if units and units != {expected_units.get(food)}:
            raise ValueError(
                f"Composition unit for {food} must match the scenario unit "
                f"{expected_units.get(food)!r}."
            )
    duplicate_key = data.duplicated(
        ["commodity", "analysis_unit", "nutrient"], keep=False
    )
    if duplicate_key.any():
        raise ValueError("Each food/unit/nutrient combination must occur only once.")
    active_foods = {
        food
        for food, quantity in weekly_quantities.items()
        if float(quantity) > 0
    }
    if active_foods:
        coverage = data.groupby("nutrient")["commodity"].agg(set)
        incomplete = [
            nutrient
            for nutrient, foods in coverage.items()
            if not active_foods.issubset(foods)
        ]
        if incomplete:
            raise ValueError(
                "Composition data must include every requested food for each nutrient; "
                "incomplete nutrient(s): " + ", ".join(incomplete)
            )
    data["weekly_quantity"] = data.apply(
        lambda row: float(weekly_quantities.get(str(row["commodity"]), 0)),
        axis=1,
    )
    data["estimated_per_day"] = (
        data["nutrient_per_analysis_unit"] * data["weekly_quantity"] / 7
    )
    reference_counts = data.groupby("nutrient")["daily_reference"].nunique()
    reference_profile_columns = [
        "nutrient_unit",
        "daily_reference",
        "reference_source",
        "reference_year",
        "population_group",
    ]
    profile_counts = data.groupby("nutrient")[reference_profile_columns].nunique()
    inconsistent_profile = profile_counts.gt(1).any(axis=1)
    if inconsistent_profile.any():
        inconsistent = ", ".join(inconsistent_profile[inconsistent_profile].index)
        raise ValueError(
            "Each nutrient must have one consistent unit, reference, source, year "
            f"and population group: {inconsistent}"
        )

    grouped = (
        data.groupby("nutrient", as_index=False)
        .agg(
            nutrient_unit=("nutrient_unit", "first"),
            estimated_per_day=("estimated_per_day", "sum"),
            daily_reference=("daily_reference", "first"),
            reference_source=("reference_source", "first"),
            reference_year=("reference_year", "first"),
            population_group=("population_group", "first"),
        )
        .sort_values("nutrient")
    )
    grouped["reference_share"] = (
        grouped["estimated_per_day"] / grouped["daily_reference"]
    )
    grouped["remaining_to_reference"] = (
        grouped["daily_reference"] - grouped["estimated_per_day"]
    ).clip(lower=0)
    return grouped.reset_index(drop=True)
