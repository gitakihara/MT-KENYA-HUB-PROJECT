# FOODWISE

**A data-backed food-price intelligence and household basket-scenario prototype for Kenya.**

FOODWISE makes market price signals easier to inspect, lets a presenter model household costs with explicit assumptions, and surfaces data gaps rather than filling them with invented prices or nutrient claims.

## Run locally (Windows)

Requires Python 3.10 or newer.

```powershell
cd "C:\Users\Gitau Kihara\Desktop\FOOD\foodwise_project"
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Alternatively, double-click `run_foodwise.bat` after Python and project dependencies are installed. Open the local URL printed by Streamlit (normally `http://localhost:8501`).

The app works offline after dependencies are installed; its data is bundled with the project.

## User flow

1. **Overview:** inspect source observations, market coverage and monthly price medians.
2. **Price intelligence:** compare an individual commodity across locations, inspect latest observations, and download the currently filtered CSV.
3. **Household simulator:** pick a market, adjust quantities / household size / income, and review the priced-item scenario, observation dates, missing-food warning and >90-day freshness prompt.
4. **Diet gap readiness:** download a nutrient-data template. An expert can provide composition values and references; FOODWISE computes arithmetic scenario contributions only from the uploaded inputs.
5. **Data & methods:** read the source definitions and caveats and view selected market coordinates.

## Source data bundled

- `data/wfp_food_prices_ken.csv`: WFP/HDX Kenya prices, through 15 September 2026.
- `data/wfp_markets_ken.csv`: WFP market IDs and locations.
- `data/knbs_cpi_september_2026.pdf`: KNBS September 2026 CPI report.
- `docs/02_Data_Sources.md`: retrieval notes and attribution.

## Tests

```powershell
python -m unittest discover -s tests -v
```

Tests cover source-file validation, market/date/price-type filters, WFP unit normalization, latest market prices, trend segmentation, affordability calculations, missing income handling, nutrient-unit matching and nutrient-reference consistency.

## Product modules and present status

1. **Price Intelligence** is implemented on the bundled WFP price observations; coverage remains uneven and is not county-representative.
2. **Household Pressure Score** is a transparent scenario calculation with configurable, unvalidated thresholds; it is not a validated household survey measure.
3. **Diet Gap Analysis** has a sourced-input workflow, but no nutrient composition values are bundled. It is not active until an expert-reviewed nutrient dataset and population-appropriate reference values are provided.

KNBS reports 9.5% annual inflation for Food and Non-Alcoholic Beverages in September 2026; this national CPI context is displayed separately from WFP market prices. The supplied FAO cost / unaffordability figures are cited as briefing context; confirm exact CoAHD release, year and definitions before external publication.

## Project contents

```text
foodwise_project/
├── app.py
├── FOODWISE_Prototype.xlsx   # companion household calculator
├── foodwise/                 # data cleaning and scenario calculation
├── data/                     # original source CSVs and KNBS PDF
├── docs/                     # problem, source and demo notes
├── presentation/             # final editable PowerPoint and handout
├── scripts/                  # presentation source generator
├── tests/
├── assets/                   # generated figures used in the presentation
├── .streamlit/config.toml    # theme; Streamlit usage statistics disabled
├── requirements.txt
└── run_foodwise.bat
```

Presentation: [`presentation/FOODWISE_Project_Presentation.pptx`](presentation/FOODWISE_Project_Presentation.pptx)  
Demo script: [`docs/04_Demo_Script.md`](docs/04_Demo_Script.md)

Additional companion files: [`FOODWISE_Prototype.xlsx`](FOODWISE_Prototype.xlsx) and
[`presentation/FOODWISE_One_Page_Handout.pdf`](presentation/FOODWISE_One_Page_Handout.pdf).
