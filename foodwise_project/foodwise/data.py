"""Loading, validation, and analysis helpers for WFP Kenya food-price data."""

from __future__ import annotations

import re
from pathlib import Path
from typing import IO

import pandas as pd

PRICE_COLUMNS = {
    "date",
    "admin1",
    "admin2",
    "market",
    "latitude",
    "longitude",
    "commodity",
    "unit",
    "priceflag",
    "pricetype",
    "currency",
    "price",
}
MARKET_COLUMNS = {"market_id", "market", "countryiso3", "latitude", "longitude"}
DEFAULT_PRICE_FILE = Path(__file__).resolve().parents[1] / "data" / "wfp_food_prices_ken.csv"
DEFAULT_MARKET_FILE = Path(__file__).resolve().parents[1] / "data" / "wfp_markets_ken.csv"
CANONICAL_FOODS = (
    "Maize flour",
    "Beans (dry)",
    "Kale",
    "Milk (cow, fresh)",
    "Oil (vegetable)",
    "Potatoes (Irish)",
    "Rice",
)


def _check_columns(columns: set[str], required: set[str], label: str) -> None:
    missing = sorted(required - columns)
    if missing:
        raise ValueError(f"{label} is missing required column(s): {', '.join(missing)}")


def normalize_unit(unit: object) -> tuple[float | None, str]:
    """Return source-unit quantity per KG/L, plus the analysis price denominator.

    For example, price per 50 KG becomes price per KG; unsupported units retain
    their own denominator and are never silently converted.
    """
    if pd.isna(unit):
        return None, "per unknown source unit"
    raw = str(unit).strip()
    normalized = raw.upper().replace(",", "").strip()
    match = re.fullmatch(r"(?:(\d+(?:\.\d+)?)\s*)?(KG|KGS|G|L|ML)", normalized)
    if not match:
        return 1.0, f"per {raw}"

    size = float(match.group(1) or 1)
    token = match.group(2)
    if token in {"KG", "KGS"}:
        return size, "KES/kg"
    if token == "G":
        return size / 1000, "KES/kg"
    if token == "L":
        return size, "KES/L"
    return size / 1000, "KES/L"


def prepare_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate source columns and derive comparable prices without imputing rows."""
    _check_columns(set(frame.columns), PRICE_COLUMNS, "WFP price CSV")
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result["price"] = pd.to_numeric(result["price"], errors="coerce")
    result["latitude"] = pd.to_numeric(result["latitude"], errors="coerce")
    result["longitude"] = pd.to_numeric(result["longitude"], errors="coerce")
    result = result.dropna(
        subset=["date", "price", "market", "commodity", "unit", "currency"]
    )
    result = result[result["price"] > 0].copy()
    result["currency"] = result["currency"].astype(str).str.strip().str.upper()
    result = result[result["currency"] == "KES"].copy()
    result["unit"] = result["unit"].astype(str).str.strip()
    unit_factors = result["unit"].map(normalize_unit)
    result["source_unit_quantity"] = unit_factors.map(lambda value: value[0])
    result["analysis_unit"] = unit_factors.map(lambda value: value[1])
    result["price_per_analysis_unit"] = result["price"] / result["source_unit_quantity"]
    result["month"] = result["date"].dt.to_period("M").dt.to_timestamp()
    return result.reset_index(drop=True)


def load_price_data(source: str | Path | IO[str] = DEFAULT_PRICE_FILE) -> pd.DataFrame:
    """Load and validate a WFP-style CSV file."""
    try:
        frame = pd.read_csv(source, low_memory=False)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ValueError(f"Could not read the WFP price CSV: {exc}") from exc
    return prepare_price_frame(frame)


def load_market_data(source: str | Path | IO[str] = DEFAULT_MARKET_FILE) -> pd.DataFrame:
    """Load WFP market coordinates for map views."""
    try:
        frame = pd.read_csv(source, low_memory=False)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ValueError(f"Could not read the WFP markets CSV: {exc}") from exc
    _check_columns(set(frame.columns), MARKET_COLUMNS, "WFP markets CSV")
    result = frame.copy()
    result["latitude"] = pd.to_numeric(result["latitude"], errors="coerce")
    result["longitude"] = pd.to_numeric(result["longitude"], errors="coerce")
    result = result.dropna(subset=["latitude", "longitude"])
    result = result[result["countryiso3"].astype(str).str.upper() == "KEN"]
    return result.reset_index(drop=True)


def filter_prices(
    prices: pd.DataFrame,
    *,
    start: object,
    end: object,
    markets: list[str] | None = None,
    commodities: list[str] | None = None,
    price_type: str | None = "Retail",
) -> pd.DataFrame:
    """Apply date and optional dimensions while preserving each source record."""
    start_ts = pd.Timestamp(start)
    end_exclusive = pd.Timestamp(end) + pd.DateOffset(days=1)
    filtered = prices[
        (prices["date"] >= start_ts) & (prices["date"] < end_exclusive)
    ].copy()
    if markets:
        filtered = filtered[filtered["market"].isin(markets)]
    if commodities:
        filtered = filtered[filtered["commodity"].isin(commodities)]
    if price_type and "pricetype" in filtered.columns:
        filtered = filtered[
            filtered["pricetype"].astype(str).str.casefold() == price_type.casefold()
        ]
    return filtered.reset_index(drop=True)


def market_coverage(
    prices: pd.DataFrame,
    *,
    start: object,
    end: object,
    price_type: str | None = "Retail",
) -> pd.DataFrame:
    """Summarize recent source-record coverage; this is not representativeness."""
    recent = filter_prices(prices, start=start, end=end, price_type=price_type)
    if recent.empty:
        return pd.DataFrame(
            columns=[
                "market",
                "admin1",
                "admin2",
                "commodities",
                "observations",
                "latest_observation",
            ]
        )
    return (
        recent.groupby(["market", "admin1", "admin2"], as_index=False)
        .agg(
            commodities=("commodity", "nunique"),
            observations=("price", "size"),
            latest_observation=("date", "max"),
        )
        .sort_values(
            ["commodities", "latest_observation", "observations"],
            ascending=[False, False, False],
        )
        .reset_index(drop=True)
    )


def monthly_price_trend(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate monthly medians grouped by market and comparable unit."""
    if prices.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "market",
                "commodity",
                "analysis_unit",
                "median_price",
                "observations",
            ]
        )
    return (
        prices.groupby(
            ["month", "market", "commodity", "analysis_unit"], as_index=False
        )
        .agg(
            median_price=("price_per_analysis_unit", "median"),
            observations=("price", "size"),
        )
        .sort_values(["month", "market", "commodity", "analysis_unit"])
        .reset_index(drop=True)
    )


def latest_market_prices(
    prices: pd.DataFrame,
    market: str,
    commodities: list[str] | None = None,
    price_type: str | None = "Retail",
) -> pd.DataFrame:
    """Get the most recent item/unit observation and same-day median for a market."""
    selected = prices[prices["market"] == market].copy()
    if commodities:
        selected = selected[selected["commodity"].isin(commodities)]
    if price_type and "pricetype" in selected.columns:
        selected = selected[
            selected["pricetype"].astype(str).str.casefold() == price_type.casefold()
        ]
    if selected.empty:
        return pd.DataFrame(
            columns=[
                "market",
                "commodity",
                "analysis_unit",
                "date",
                "price_per_analysis_unit",
                "observations",
                "priceflag",
            ]
        )

    most_recent = (
        selected.groupby(["commodity", "analysis_unit"], as_index=False)["date"].max()
    )
    current = selected.merge(
        most_recent, on=["commodity", "analysis_unit", "date"], how="inner"
    )
    result = (
        current.groupby(
            ["market", "commodity", "analysis_unit", "date"], as_index=False
        )
        .agg(
            price_per_analysis_unit=("price_per_analysis_unit", "median"),
            observations=("price", "size"),
            priceflag=("priceflag", "first"),
        )
        .sort_values(["commodity", "date"], ascending=[True, False])
    )
    return result.reset_index(drop=True)
