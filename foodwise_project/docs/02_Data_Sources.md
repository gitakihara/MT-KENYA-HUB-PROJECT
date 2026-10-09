# FOODWISE — Data sources and definitions

## WFP Kenya food-price observations

- Dataset page: [WFP Food Prices for Kenya](https://data.humdata.org/dataset/wfp-food-prices-for-kenya)
- Files included: [`wfp_food_prices_ken.csv`](../data/wfp_food_prices_ken.csv) and [`wfp_markets_ken.csv`](../data/wfp_markets_ken.csv)
- Retrieved for this project on **8 October 2026**.
- The source price file has **27,897 rows**, date coverage from **15 January 2006 through 15 September 2026**, market and administrative names, commodity, source unit, price, currency, price type, price flag and coordinates.
- Project dashboard retains positive numeric KES records with valid date, market, commodity and unit. Retail and wholesale records remain separate.
- Source units are normalized only where explicit: kg, g, l and ml, including package sizes such as `50 KG` and `500 ML`. Recognized package prices are divided by package content and reported per kg or per litre. Unknown source units remain separate; no guessed conversion is performed.
- Price charts use monthly medians of observed prices, separately by commodity, market and comparable unit. They are descriptive WFP observations, not a CPI, county-weighted panel, or household expenditure survey.
- Last observation in the downloaded file is **15 September 2026**. Counts and latest dates change by food and market.
- The source includes markets in North Eastern/Garissa and Rift Valley/Turkana with relatively current target-food coverage, including refugee-camp markets. Do not generalize these observations to Nairobi, Nyeri or county-wide household retail conditions.

## KNBS CPI

- Release page: [Consumer Price Indices and Inflation Rates — September 2026](https://www.knbs.or.ke/reports/consumer-price-indices-and-inflation-rates-september-2026/)
- Report included locally: [`knbs_cpi_september_2026.pdf`](../data/knbs_cpi_september_2026.pdf)
- The release page reports **9.5%** annual inflation for Food and Non-Alcoholic Beverages and **6.8%** overall annual CPI inflation. FOODWISE shows the 9.5% as context only, without blending it into market-level prices.
- Milk, wheat flour, cabbage and potatoes are priorities provided by the brief. Verify exact item-level changes in the underlying CPI tables before saying these were the greatest risers.

## FAO Cost and Affordability of a Healthy Diet

- Reference series: [FAOSTAT CoAHD](https://www.fao.org/faostat/en/#data/CAHD)
- The briefing figures (**43.5–43.9 million / 76–77%**; **KSh 189–582 per person per day**) are not recomputed from WFP. Exact series, year, population definition and method still need to be recorded before public use.
- This first running application has no FAO CoAHD download. It does not label its editable household basket as a healthy diet.

## Refresh and provenance

1. Retrieve the latest Kenya price and market files from HDX; keep the retrieval date and a copy of the old files for comparison.
2. Replace the CSVs in `data/`; refresh the downloaded KNBS report and source descriptions if the reference period changes.
3. Run the tests with `python -m unittest discover -s tests -v`.
4. Check latest dates, market coverage, exact source units and flags before making any claim from the app.
