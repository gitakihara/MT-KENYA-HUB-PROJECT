from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from foodwise.calculations import household_result, nutrient_gap
from foodwise.data import (
    DEFAULT_PRICE_FILE,
    filter_prices,
    latest_market_prices,
    load_price_data,
    monthly_price_trend,
    normalize_unit,
    prepare_price_frame,
)


class UnitNormalizationTests(unittest.TestCase):
    def test_package_units_convert_to_common_base_units(self) -> None:
        self.assertEqual(normalize_unit("50 KG"), (50.0, "KES/kg"))
        self.assertEqual(normalize_unit("500 ML"), (0.5, "KES/L"))
        self.assertEqual(normalize_unit("400 G"), (0.4, "KES/kg"))

    def test_unrecognized_units_remain_separate(self) -> None:
        self.assertEqual(normalize_unit("Bunch"), (1.0, "per Bunch"))


class PriceDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.prices = load_price_data(DEFAULT_PRICE_FILE)

    def test_bundled_file_loads_expected_recent_kenya_records(self) -> None:
        self.assertGreater(len(self.prices), 1000)
        self.assertEqual(set(self.prices["currency"]), {"KES"})
        self.assertEqual(str(self.prices["date"].max().date()), "2026-09-15")

    def test_filter_separates_price_type_and_respects_date(self) -> None:
        retail = filter_prices(
            self.prices,
            start="2026-09-01",
            end="2026-09-30",
            markets=["IFO (Daadab)"],
            commodities=["Maize flour"],
            price_type="Retail",
        )
        wholesale = filter_prices(
            self.prices,
            start="2026-09-01",
            end="2026-09-30",
            markets=["IFO (Daadab)"],
            commodities=["Maize flour"],
            price_type="Wholesale",
        )
        self.assertFalse(retail.empty)
        self.assertTrue((retail["date"].dt.month == 9).all())
        self.assertTrue((retail["pricetype"] == "Retail").all())
        self.assertTrue(wholesale.empty)

    def test_latest_price_uses_comparable_unit_and_date(self) -> None:
        latest = latest_market_prices(
            self.prices,
            market="IFO (Daadab)",
            commodities=["Maize flour"],
        )
        per_kg = latest[latest["analysis_unit"] == "KES/kg"]
        self.assertEqual(len(per_kg), 1)
        self.assertEqual(str(per_kg.iloc[0]["date"].date()), "2026-09-15")
        self.assertAlmostEqual(float(per_kg.iloc[0]["price_per_analysis_unit"]), 100.0)

    def test_monthly_trend_keeps_markets_and_units_distinct(self) -> None:
        selected = filter_prices(
            self.prices,
            start="2026-08-01",
            end="2026-09-30",
            markets=["IFO (Daadab)", "Kakuma 2"],
            commodities=["Maize flour"],
        )
        trend = monthly_price_trend(selected)
        self.assertEqual(set(trend["market"]), {"IFO (Daadab)", "Kakuma 2"})
        self.assertEqual(set(trend["commodity"]), {"Maize flour"})
        self.assertEqual(set(trend["analysis_unit"]), {"KES/kg"})
        self.assertEqual(int(trend["observations"].sum()), len(selected))

    def test_required_columns_are_reported(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing required column"):
            prepare_price_frame(pd.DataFrame({"date": ["2026-01-01"]}))


class HouseholdCalculationTests(unittest.TestCase):
    def test_household_cost_income_share_and_score(self) -> None:
        result = household_result(
            weekly_basket_per_person=1000,
            household_size=4,
            monthly_income=25000,
            priced_items=7,
            requested_items=7,
        )
        self.assertAlmostEqual(result.monthly_household, 17392.8571429, places=3)
        self.assertAlmostEqual(result.income_share or 0, 0.69571429, places=5)
        self.assertEqual(result.pressure_band, "Critical prototype signal")
        self.assertAlmostEqual(result.affordability_score or 0, 30.428571, places=5)
        self.assertTrue(result.full_coverage)

    def test_no_income_is_not_misrepresented_as_zero_pressure(self) -> None:
        result = household_result(
            weekly_basket_per_person=100,
            household_size=2,
            monthly_income=0,
            priced_items=1,
            requested_items=7,
        )
        self.assertIsNone(result.income_share)
        self.assertEqual(result.pressure_band, "Income required")
        self.assertFalse(result.full_coverage)

    def test_invalid_thresholds_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Thresholds"):
            household_result(
                weekly_basket_per_person=1,
                household_size=1,
                monthly_income=1,
                warning_share=0.6,
                critical_share=0.5,
                priced_items=1,
                requested_items=1,
            )


class NutrientGapTests(unittest.TestCase):
    def test_user_supplied_nutrient_values_are_calculated_and_cited(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "commodity": "Beans (dry)",
                    "analysis_unit": "KES/kg",
                    "nutrient": "iron",
                    "population_group": "Adult reference profile",
                    "nutrient_per_analysis_unit": 30.0,
                    "nutrient_unit": "mg",
                    "daily_reference": 18.0,
                    "reference_source": "Expert-approved test reference",
                    "reference_year": 2025,
                }
            ]
        )
        result = nutrient_gap(
            weekly_quantities={"Beans (dry)": 0.35},
            nutrient_data=source,
            expected_units={"Beans (dry)": "KES/kg"},
        )
        self.assertAlmostEqual(float(result.iloc[0]["estimated_per_day"]), 1.5)
        self.assertAlmostEqual(float(result.iloc[0]["reference_share"]), 1.5 / 18)

    def test_mixed_references_for_one_nutrient_are_rejected(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "commodity": food,
                    "analysis_unit": "KES/kg",
                    "nutrient": "iron",
                    "population_group": "Adult reference profile",
                    "nutrient_per_analysis_unit": 1.0,
                    "nutrient_unit": "mg",
                    "daily_reference": ref,
                    "reference_source": "Expert",
                    "reference_year": 2025,
                }
                for food, ref in [("Rice", 8), ("Beans", 18)]
            ]
        )
        with self.assertRaisesRegex(ValueError, "consistent unit, reference"):
            nutrient_gap(
                weekly_quantities={},
                nutrient_data=source,
                expected_units={},
            )

    def test_scenario_composition_unit_must_match_food_quantity_unit(self) -> None:
        source = pd.DataFrame(
            [
                {
                    "commodity": "Beans (dry)",
                    "analysis_unit": "per 50 KG",
                    "nutrient": "iron",
                    "population_group": "Adults",
                    "nutrient_per_analysis_unit": 3.0,
                    "nutrient_unit": "mg",
                    "daily_reference": 18.0,
                    "reference_source": "Expert reference",
                    "reference_year": 2025,
                }
            ]
        )
        with self.assertRaisesRegex(ValueError, "must match the scenario unit"):
            nutrient_gap(
                weekly_quantities={"Beans (dry)": 0.35},
                nutrient_data=source,
                expected_units={"Beans (dry)": "KES/kg"},
            )


if __name__ == "__main__":
    unittest.main()
