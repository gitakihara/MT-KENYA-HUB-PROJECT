# FOODWISE — Data sources

## WFP Kenya Food Prices (downloaded)

- Dataset: [WFP Food Prices for Kenya — HDX](https://data.humdata.org/dataset/wfp-food-prices-for-kenya)
- Main source file: [`data/wfp_food_prices_ken.csv`](./data/wfp_food_prices_ken.csv)
- Market lookup file: [`data/wfp_markets_ken.csv`](./data/wfp_markets_ken.csv)
- Resource: Kenya - Food Prices; CSV served by HDX
- Downloaded: **8 October 2026**
- Source file size: approximately **3.6 MB**
- Fields include date, administrative areas, market, commodity, unit, currency, price type, price flag, price and USD price.
- Observed source dates: **15 January 2006–15 September 2026**. The workbook keeps selected food observations from **1 October 2024 onward**.
- The prototype filters exact available WFP commodity labels: maize flour, dry beans, kale, fresh cow milk, vegetable oil, Irish potatoes, rice and sugar.
- The two example markets available in the household calculator are **IFO (Daadab)** and **Kakuma 2**. These are camp markets; they should not be described as representative Nairobi, Nyeri or county-wide prices.
- Prices remain in the source's recorded units. Observations can be missing or have different dates; the workbook shows the observation date and warns when the basket is incomplete.
- HDX dataset page: <https://data.humdata.org/dataset/wfp-food-prices-for-kenya>

## KNBS Consumer Price Index (downloaded)

- Release page: [Consumer Price Indices and Inflation Rates — September 2026](https://www.knbs.or.ke/reports/consumer-price-indices-and-inflation-rates-september-2026/)
- Report: [`data/knbs_cpi_september_2026.pdf`](./data/knbs_cpi_september_2026.pdf)
- The release page reports **9.5% year-on-year inflation** in Food and Non-Alcoholic Beverages and **6.8% overall annual CPI inflation**.
- The selected item-level priorities (milk, wheat flour, cabbage and potatoes) are retained from the project brief; verify their exact item-level movements and comparison period in the report before making a claim about which rose most.

## FAO healthy-diet affordability

- Reference: [FAOSTAT Cost and affordability of a healthy diet (CoAHD)](https://www.fao.org/faostat/en/#data/CAHD)
- The figures of **43.5–43.9 million (about 76–77%)** unable to afford a healthy diet and **KSh 189–582 per person per day** are supplied in the brief. Record the matching FAOSTAT series, reporting year, method and geography in a future data refresh before using the numbers as a fully sourced time series.
- No CoAHD data file is included in this first prototype; the downloadable WFP and KNBS files are included.

## Refresh steps

1. Download the current Kenya - Food Prices CSV and Markets CSV from the HDX dataset page.
2. Replace the matching files in `data/` only after keeping a dated copy of the old source file.
3. Install the listed build packages with `python -m pip install -r requirements.txt`.
4. Run `python build_foodwise.py`.
5. Check new date coverage, units, markets, missing prices and source flags before presenting updated outputs.
