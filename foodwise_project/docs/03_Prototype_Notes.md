# FOODWISE — Prototype and showcase notes

## The three modules

**1. Price Intelligence**

Tracks market prices of staple and nutritious foods across counties using WFP + KNBS data.

**2. Household Pressure Score**

Estimates how much of a household’s income is needed for a healthy diet and flags when the share becomes dangerous (>50–60%).

**3. Diet Gap Analysis**

Compares the cost of the cheapest calorie diet vs a healthy diet and highlights the most expensive nutrients (usually iron, calcium, vitamin B12, zinc).

## What this software actually does

- **Price Intelligence:** filters WFP retail or wholesale observations by food, market and date; normalizes explicit package units; visualizes monthly median records; offers a downloadable filtered source table.
- **Household simulator:** prices an editable quantity scenario against the latest matching market price, shows monthly cost and income share, and labels missing prices. It is a scenario tool, not a validated household-pressure model.
- **Diet gap readiness:** accepts an expert-reviewed CSV with food composition and population-specific daily reference values. No nutrient values or reference amounts are bundled or invented.
- **KNBS context:** displays the September 2026 9.5% annual food-division inflation rate separately from WFP price records.

## Calculator assumptions and limitations

- Food quantities are user-editable demonstration assumptions—not an official healthy basket, nutrition advice or CoAHD estimate.
- Prices match the selected WFP market and Retail/Wholesale price type; each price row shows its date and normalized per-kg, per-litre or unconverted source-unit basis.
- Prices more than 90 days older than the chosen cutoff receive a freshness warning. This is a review prompt, not a statistical data-quality standard.
- Monthly cost = weekly scenario cost × 365.25 / 7 / 12 × household size.
- Income share = monthly scenario cost / monthly household income. Zero or missing income is never portrayed as 0% pressure.
- The score is `max(0, 100 − income share in percentage points)`. The 50% watch / 60% critical thresholds are configurable prototype markers; neither they nor the score are validated.
- Missing observations stay missing. A partial basket cannot be presented as the full cost of a healthy diet.
- Monthly medians are not adjusted for changes in contributing markets or foods.
- The nutrient module is inactive until sourced nutrient-composition and reference data are provided and checked by a qualified nutrition expert.

## Live-demo sequence (about 60 seconds)

1. “This is the FOODWISE price-intelligence view. These are observed monthly WFP medians, not a national CPI.”
2. “Here is an editable household basket priced from the selected market. The quantities are scenario assumptions, and every price shows its date.”
3. “For this household size and income, this is the share of income represented by the priced items. Missing foods are flagged, and the threshold is a proposed indicator, not a validated rule.”
4. “The diet-gap view is deliberately awaiting expert-reviewed nutrient data; we do not infer micronutrients from price records.”
5. “FOODWISE makes the price and affordability evidence visible so county partners can validate a pilot.”

## Pitch close

“Healthy food should not be a luxury. FOODWISE makes the barriers visible so we can act on them.”

## Before presenting

- Add presenter name and contact information to the deck cover / closing slide.
- Open the app, review its data-freshness caption, choose a market with adequate recent coverage, and confirm every scenario observation date.
- Do not say a price spike “caused diet diversity to collapse”: the public price dataset does not measure household diets.
- Confirm the FAO series / year and KNBS item-level table before attributing specific item price rises.
- Ask a nutrition expert to define and validate a healthy-diet basket and nutrient reference inputs.
- Seek a county or local partner to validate whether selected WFP markets represent the pilot population.
