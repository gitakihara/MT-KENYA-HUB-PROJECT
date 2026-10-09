from __future__ import annotations

from datetime import timedelta
from io import StringIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from foodwise.calculations import household_result, nutrient_gap
from foodwise.data import (
    CANONICAL_FOODS,
    DEFAULT_MARKET_FILE,
    DEFAULT_PRICE_FILE,
    filter_prices,
    latest_market_prices,
    load_market_data,
    load_price_data,
    market_coverage,
    monthly_price_trend,
)


ROOT = Path(__file__).resolve().parent
KNBS_RELEASE = (
    "https://www.knbs.or.ke/reports/"
    "consumer-price-indices-and-inflation-rates-september-2026/"
)
WFP_DATASET = "https://data.humdata.org/dataset/wfp-food-prices-for-kenya"
FAOSTAT_CAHD = "https://www.fao.org/faostat/en/#data/CAHD"

st.set_page_config(
    page_title="FOODWISE | Food affordability intelligence",
    page_icon="🥬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
      .stApp { background: #f6f8f7; }
      .block-container { padding-top: 1.3rem; padding-bottom: 3rem; max-width: 1440px; }
      h1, h2, h3 { font-family: 'Manrope', sans-serif; color: #173a35; }
      .hero { background: linear-gradient(120deg,#123c38 0%,#17665a 72%,#1a8a72 100%);
              padding: 1.65rem 1.9rem; border-radius: 18px; color: white; margin-bottom: 1.1rem; }
      .hero h1 { color: white; margin: 0 0 .35rem 0; letter-spacing: -.04em; }
      .hero p { color: #d8eee6; margin: 0; font-size: 1.03rem; }
      .eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: .72rem;
                 font-weight: 700; color: #b3ded1; margin-bottom: .45rem; }
      .metric-note { color: #687a74; font-size: .79rem; margin-top: -.55rem; }
      .notice { border-left: 4px solid #dfa63b; background: #fff6df; color: #5f4d25;
                padding: .8rem 1rem; border-radius: 6px; margin: .7rem 0 1rem; }
      .info-card { background: white; border: 1px solid #e4ebe7; padding: 1rem 1.1rem;
                   border-radius: 12px; min-height: 120px; }
      .muted { color: #63736e; font-size: .9rem; }
      [data-testid="stMetric"] { background: #fff; border: 1px solid #e4ebe7;
                                 padding: .85rem 1rem; border-radius: 12px; }
      [data-testid="stMetricLabel"] { color: #60746e; }
      section[data-testid="stSidebar"] { background: #edf3f0; }
      .stTabs [data-baseweb="tab-list"] { gap: .5rem; }
      .stTabs [data-baseweb="tab"] { background: white; border-radius: 8px 8px 0 0; padding: .5rem .95rem; }
      footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Loading verified WFP observations...")
def load_cached_prices(source_bytes: bytes | None = None) -> pd.DataFrame:
    if source_bytes is None:
        return load_price_data(DEFAULT_PRICE_FILE)
    return load_price_data(StringIO(source_bytes.decode("utf-8-sig")))


@st.cache_data(show_spinner=False)
def load_cached_markets() -> pd.DataFrame:
    return load_market_data(DEFAULT_MARKET_FILE)


@st.cache_data(show_spinner=False)
def get_cached_coverage(
    start: date,
    end: date,
    price_type: str,
    source_bytes: bytes | None,
) -> pd.DataFrame:
    data = load_cached_prices(source_bytes)
    return market_coverage(data, start=start, end=end, price_type=price_type)


@st.cache_data(show_spinner=False)
def get_cached_filter(
    start: date,
    end: date,
    markets: tuple[str, ...],
    commodities: tuple[str, ...],
    price_type: str,
    source_bytes: bytes | None,
) -> pd.DataFrame:
    data = load_cached_prices(source_bytes)
    return filter_prices(
        data,
        start=start,
        end=end,
        markets=list(markets) or None,
        commodities=list(commodities) or None,
        price_type=price_type,
    )


@st.cache_data(show_spinner=False)
def get_cached_latest_market_prices(
    market: str,
    end: date,
    price_type: str,
    source_bytes: bytes | None,
) -> pd.DataFrame:
    data = load_cached_prices(source_bytes)
    filtered = filter_prices(
        data,
        start=data["date"].min().date(),
        end=end,
        price_type=price_type,
    )
    return latest_market_prices(
        filtered,
        market=market,
        commodities=list(CANONICAL_FOODS),
        price_type=None,
    )


def money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"KSh {value:,.0f}"


def create_diet_template() -> bytes:
    headers = [
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
    template = pd.DataFrame(columns=headers)
    return template.to_csv(index=False).encode("utf-8")


prices: pd.DataFrame | None = None
load_error: str | None = None

with st.sidebar:
    st.markdown("## FOODWISE")
    st.caption("Public price signals · household scenarios · pilot readiness")
    uploaded_source = st.file_uploader(
        "Optional: use an updated WFP-style price CSV",
        type=["csv"],
        help="The uploaded file is checked for required columns and KES price records.",
    )
    try:
        prices = load_cached_prices(uploaded_source.getvalue() if uploaded_source else None)
    except ValueError as exc:
        load_error = str(exc)
    if prices is not None and not prices.empty:
        latest_source_date = prices["date"].max().date()
        earliest_source_date = prices["date"].min().date()
        default_start = max(
            earliest_source_date,
            (pd.Timestamp(latest_source_date) - pd.DateOffset(months=24)).date(),
        )
        st.markdown("---")
        st.markdown("### Price explorer filters")
        start_date, end_date = st.date_input(
            "Observation window",
            value=(default_start, latest_source_date),
            min_value=earliest_source_date,
            max_value=latest_source_date,
        )
        price_type = st.selectbox(
            "Price series",
            ["Retail", "Wholesale"],
            index=0,
            help="Retail and wholesale observations are kept separate.",
        )
        all_commodities = sorted(prices["commodity"].dropna().unique().tolist())
        defaults = [item for item in CANONICAL_FOODS + ("Sugar",) if item in all_commodities]
        selected_commodities = st.multiselect(
            "Foods",
            options=all_commodities,
            default=defaults,
        )
        source_bytes = uploaded_source.getvalue() if uploaded_source else None
        coverage = get_cached_coverage(
            start_date,
            end_date,
            price_type,
            source_bytes,
        )
        default_markets = coverage.head(5)["market"].tolist()
        selected_markets = st.multiselect(
            "Markets to compare",
            options=sorted(prices["market"].dropna().unique().tolist()),
            default=default_markets,
        )
        st.markdown("---")
        st.caption(
            f"Source dates: {earliest_source_date:%d %b %Y}–"
            f"{latest_source_date:%d %b %Y} · {len(prices):,} valid KES records"
        )

if prices is None:
    st.error(f"The price data could not be loaded: {load_error or 'No valid observations found.'}")
    st.info("Check the bundled CSV or upload a WFP-style CSV with the required columns.")
    st.stop()
if prices.empty:
    st.error("The selected price file has no valid KES price observations.")
    st.stop()
if "start_date" not in locals() or "end_date" not in locals():
    st.error("Choose a valid observation window in the sidebar.")
    st.stop()
if start_date > end_date:
    st.error("The observation-window start must be on or before its end.")
    st.stop()

try:
    source_bytes = uploaded_source.getvalue() if uploaded_source else None
    selected_prices = get_cached_filter(
        start_date,
        end_date,
        tuple(selected_markets),
        tuple(selected_commodities),
        price_type,
        source_bytes,
    )
    markets = load_cached_markets()
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">FOOD SYSTEMS · KENYA</div>
      <h1>Healthy food should not be a luxury.</h1>
      <p>Make food-price signals and household budget pressure visible—without disguising data gaps.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

if len(selected_prices) == 0:
    st.warning(
        "No observations match these filters. Expand the dates, choose a different market or food, "
        "or switch Retail / Wholesale."
    )

dashboard_tab, explorer_tab, household_tab, diet_tab, data_tab = st.tabs(
    [
        "Overview",
        "Price intelligence",
        "Household simulator",
        "Diet gap readiness",
        "Data & methods",
    ]
)

with dashboard_tab:
    national_col, source_col = st.columns([1.05, 2.1])
    with national_col:
        st.metric("KNBS food inflation", "9.5%", "year-on-year · Sep 2026")
        st.markdown(
            '<p class="metric-note">Food & Non-Alcoholic Beverages division; not the overall CPI.</p>',
            unsafe_allow_html=True,
        )
    with source_col:
        st.markdown(
            """
            <div class="info-card">
              <b>National context, local market observations</b>
              <p class="muted">KNBS CPI describes national price movement. WFP observations show
              individual market prices. This prototype does not blend the two measures.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    observed_markets = selected_prices["market"].nunique() if not selected_prices.empty else 0
    selected_food_count = selected_prices["commodity"].nunique() if not selected_prices.empty else 0
    selected_dates = (
        f"{selected_prices['date'].min():%b %Y} – {selected_prices['date'].max():%b %Y}"
        if not selected_prices.empty
        else "No matching observations"
    )
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Price observations", f"{len(selected_prices):,}")
    kpi2.metric("Foods covered", f"{selected_food_count}")
    kpi3.metric("Markets covered", f"{observed_markets}")
    kpi4.metric("Matching date span", selected_dates)

    st.subheader("The signal is local—and coverage is uneven")
    recent_window_start = max(start_date, end_date - timedelta(days=365))
    coverage_view = get_cached_coverage(
        recent_window_start,
        end_date,
        price_type,
        source_bytes,
    )
    overview_left, overview_right = st.columns([1.45, 1])
    with overview_left:
        overview_foods = sorted(selected_prices["commodity"].dropna().unique().tolist())
        overview_food = (
            st.selectbox(
                "Trend food",
                overview_foods,
                index=overview_foods.index("Maize flour")
                if "Maize flour" in overview_foods
                else 0,
                key="overview_food",
            )
            if overview_foods
            else None
        )
        trend_prices = (
            selected_prices[selected_prices["commodity"] == overview_food]
            if overview_food
            else selected_prices.iloc[0:0]
        )
        trend = monthly_price_trend(trend_prices)
        if trend.empty:
            st.info("No price series to chart with this filter combination.")
        else:
            chart = px.line(
                trend,
                x="month",
                y="median_price",
                color="market",
                line_dash="analysis_unit",
                markers=True,
                hover_data={
                    "analysis_unit": True,
                    "observations": True,
                    "month": "|%b %Y",
                },
                labels={
                    "month": "Month",
                    "median_price": "Monthly median (KES per normalized unit)",
                    "market": "Market",
                    "analysis_unit": "Price unit",
                },
                title="Monthly median of source observations",
                template="plotly_white",
            )
            chart.update_layout(
                height=390,
                margin=dict(l=0, r=10, t=55, b=0),
                legend_title_text="Market · unit",
            )
            chart.update_yaxes(rangemode="tozero", gridcolor="#e8eeeb")
            st.plotly_chart(chart, width="stretch")
            st.caption(
                "Each line is a median of reported records, not a county-weighted index. "
                "Markets, items and observation counts can vary across months."
            )
    with overview_right:
        if coverage_view.empty:
            st.info("No market coverage rows found for the selected period.")
        else:
            display_coverage = coverage_view.head(12).copy()
            display_coverage["Latest observed"] = display_coverage[
                "latest_observation"
            ].dt.strftime("%d %b %Y")
            display_coverage = display_coverage.rename(
                columns={
                    "market": "Market",
                    "admin1": "Region",
                    "admin2": "County / area",
                    "commodities": "Foods",
                    "observations": "Records",
                }
            )
            st.dataframe(
                display_coverage[
                    ["Market", "County / area", "Foods", "Records", "Latest observed"]
                ],
                width="stretch",
                hide_index=True,
            )
            st.caption(
                "Coverage count = unique recorded commodities in the selected recent window. "
                "It is not a data-quality or representativeness score."
            )

    st.markdown(
        '<div class="notice"><b>Interpretation guardrail:</b> WFP market-price coverage is uneven. '
        'A price gap means “no matching source record,” not “free food” or a zero price.</div>',
        unsafe_allow_html=True,
    )

with explorer_tab:
    st.subheader("Explore reported food prices")
    st.caption(
        f"{price_type} observations · {start_date:%d %b %Y} through {end_date:%d %b %Y}"
    )
    if not selected_prices.empty:
        food_options = sorted(selected_prices["commodity"].unique().tolist())
        chart_food = st.selectbox(
            "Choose one food for an apples-to-apples series",
            options=food_options,
            key="explorer_food",
        )
        food_frame = selected_prices[selected_prices["commodity"] == chart_food].copy()
        unit_options = sorted(food_frame["analysis_unit"].dropna().unique().tolist())
        selected_units = st.multiselect(
            "Comparable source units",
            unit_options,
            default=unit_options,
            key="explorer_units",
            help="50 KG bags and per-KG observations are converted to KES/kg; unsupported units remain separate.",
        )
        comparable = food_frame[food_frame["analysis_unit"].isin(selected_units)]
        plot_frame = monthly_price_trend(comparable)
        if not plot_frame.empty:
            chart = px.line(
                plot_frame,
                x="month",
                y="median_price",
                color="market",
                line_dash="analysis_unit",
                markers=True,
                hover_data=["observations", "analysis_unit"],
                labels={
                    "month": "Month",
                    "median_price": "Median price (KES per comparable unit)",
                    "market": "Market",
                    "analysis_unit": "Unit",
                },
                template="plotly_white",
            )
            chart.update_layout(height=440, margin=dict(l=0, r=0, t=25, b=0))
            chart.update_yaxes(rangemode="tozero", gridcolor="#e8eeeb")
            st.plotly_chart(chart, width="stretch")
        else:
            st.info("Choose at least one unit to display a trend.")

        st.markdown("#### Latest price observations in the selected period")
        latest_rows = (
            comparable.sort_values("date")
            .groupby(["market", "commodity", "analysis_unit"], as_index=False)
            .tail(1)
            .sort_values(["commodity", "market"])
            .copy()
        )
        latest_rows["Price (KES / unit)"] = latest_rows["price_per_analysis_unit"].map(
            lambda value: f"{value:,.2f}"
        )
        latest_rows["Date"] = latest_rows["date"].dt.strftime("%d %b %Y")
        latest_rows = latest_rows.rename(
            columns={
                "market": "Market",
                "admin2": "County / area",
                "commodity": "Food",
                "analysis_unit": "Comparable unit",
                "pricetype": "Type",
                "priceflag": "WFP price flag",
            }
        )
        show_columns = [
            name
            for name in [
                "Market",
                "County / area",
                "Food",
                "Date",
                "Price (KES / unit)",
                "Comparable unit",
                "Type",
                "WFP price flag",
            ]
            if name in latest_rows.columns
        ]
        st.dataframe(latest_rows[show_columns], width="stretch", hide_index=True)
        st.download_button(
            "Download filtered source records",
            data=comparable.to_csv(index=False).encode("utf-8"),
            file_name="foodwise_filtered_wfp_prices.csv",
            mime="text/csv",
        )
    else:
        st.info("Adjust the sidebar filters to find source observations.")

with household_tab:
    st.subheader("Household basket scenario")
    st.markdown(
        '<div class="notice"><b>Not a healthy-diet estimate:</b> quantities below are illustrative '
        'scenario inputs. This tool prices only selected items that have matching WFP records; it is not '
        'a nutrition recommendation, official CoAHD cost or validated poverty measure.</div>',
        unsafe_allow_html=True,
    )
    coverage_start = max(
        start_date, (pd.Timestamp(end_date) - pd.DateOffset(months=24)).date()
    )
    scenario_coverage = get_cached_coverage(
        coverage_start,
        end_date,
        price_type,
        source_bytes,
    )
    default_market = (
        scenario_coverage.iloc[0]["market"]
        if not scenario_coverage.empty
        else str(prices["market"].mode().iloc[0])
    )
    all_market_names = sorted(prices["market"].dropna().unique().tolist())
    scenario_market = st.selectbox(
        "Market for this scenario",
        all_market_names,
        index=all_market_names.index(default_market),
        key="scenario_market",
        help="Prices use the latest matching Retail/Wholesale source records up to the end date.",
    )
    latest_for_market = get_cached_latest_market_prices(
        scenario_market,
        end_date,
        price_type,
        source_bytes,
    )

    mass_items = {
        "Maize flour": 1.5,
        "Beans (dry)": 0.35,
        "Kale": 0.75,
        "Potatoes (Irish)": 0.75,
        "Rice": 0.35,
    }
    liquid_items = {"Milk (cow, fresh)": 1.75, "Oil (vegetable)": 0.25}
    basket_inputs: dict[str, float] = {}
    basket_records: list[dict[str, object]] = []
    left, right = st.columns([1.15, 0.85])
    with left:
        st.markdown("##### Illustrative weekly quantity per person")
        for item in CANONICAL_FOODS:
            quantity_default = mass_items.get(item, liquid_items.get(item, 0.0))
            basket_inputs[item] = st.number_input(
                f"{item} · {('L' if item in liquid_items else 'kg')}/week",
                min_value=0.0,
                max_value=25.0,
                value=float(quantity_default),
                step=0.05,
                key=f"quantity_{item}",
            )

    with right:
        st.markdown("##### Household inputs")
        household_size = st.number_input(
            "People in household", min_value=1, max_value=25, value=4, step=1
        )
        monthly_income = st.number_input(
            "Monthly household income (KSh)",
            min_value=0,
            max_value=5_000_000,
            value=25_000,
            step=1_000,
        )
        warning_percent = st.slider(
            "Watch threshold · scenario share of income",
            min_value=10,
            max_value=80,
            value=50,
            step=5,
        )
        critical_percent = st.slider(
            "Critical threshold · scenario share of income",
            min_value=15,
            max_value=95,
            value=60,
            step=5,
        )
        if warning_percent >= critical_percent:
            st.error("The critical threshold must be above the watch threshold.")

    latest_lookup = {
        (row["commodity"], row["analysis_unit"]): row
        for _, row in latest_for_market.iterrows()
    }
    weekly_cost = 0.0
    for item, quantity in basket_inputs.items():
        target_unit = "KES/L" if item in liquid_items else "KES/kg"
        price_row = latest_lookup.get((item, target_unit))
        if price_row is None:
            unit_label = target_unit.replace("KES/", "")
            price_value = None
            price_date = None
            age_days = None
            cost = None
        else:
            unit_label = str(price_row["analysis_unit"]).replace("KES/", "")
            price_value = float(price_row["price_per_analysis_unit"])
            price_date = price_row["date"]
            age_days = (pd.Timestamp(end_date) - price_date).days
            cost = price_value * quantity
            weekly_cost += cost
        basket_records.append(
            {
                "Food": item,
                "Quantity / week": quantity,
                "Source unit": unit_label,
                "Latest price": price_value,
                "Observation date": price_date,
                "Days before cutoff": age_days,
                "Freshness": (
                    "Missing"
                    if age_days is None
                    else "Older than 90 days"
                    if age_days > 90
                    else "Within 90 days"
                ),
                "Weekly cost": cost,
                "Priced": price_row is not None,
            }
        )

    basket_frame = pd.DataFrame(basket_records)
    basket_display = basket_frame.copy()
    basket_display["Latest price"] = basket_display["Latest price"].map(
        lambda value: f"KSh {value:,.2f}" if pd.notna(value) else "Missing"
    )
    basket_display["Weekly cost"] = basket_display["Weekly cost"].map(
        lambda value: f"KSh {value:,.2f}" if pd.notna(value) else "Missing"
    )
    basket_display["Observation date"] = basket_display["Observation date"].map(
        lambda value: value.strftime("%d %b %Y") if pd.notna(value) else "—"
    )
    basket_display = basket_display.drop(columns=["Priced"])
    st.dataframe(
        basket_display.drop(columns=["Days before cutoff"]),
        width="stretch",
        hide_index=True,
    )

    requested_item_count = sum(quantity > 0 for quantity in basket_inputs.values())
    if requested_item_count == 0:
        st.info("Enter a positive weekly quantity for at least one food to calculate a scenario.")
    elif warning_percent >= critical_percent:
        st.warning("Fix the thresholds above to calculate this scenario.")
    else:
        priced_item_count = sum(
            bool(record["Priced"]) and float(record["Quantity / week"]) > 0
            for record in basket_records
        )
        result = household_result(
            weekly_basket_per_person=weekly_cost,
            household_size=int(household_size),
            monthly_income=float(monthly_income),
            warning_share=warning_percent / 100,
            critical_share=critical_percent / 100,
            priced_items=priced_item_count,
            requested_items=requested_item_count,
        )
        metric1, metric2, metric3, metric4 = st.columns(4)
        metric1.metric("Weekly cost / person · priced items", money(result.weekly_per_person))
        metric2.metric("Monthly scenario cost · household", money(result.monthly_household))
        metric3.metric(
            "Income share · priced items",
            f"{result.income_share:.1%}" if result.income_share is not None else "Income required",
        )
        metric4.metric(
            "Illustrative affordability score",
            f"{result.affordability_score:.0f} / 100"
            if result.affordability_score is not None
            else "—",
        )
        coverage_copy = (
            "All selected foods have a matching price observation."
            if result.full_coverage
            else f"Partial basket: {priced_item_count} of {requested_item_count} requested foods priced. "
            "The displayed cost and income share understate the full selected basket."
        )
        st.info(coverage_copy)
        stale_foods = [
            str(record["Food"])
            for record in basket_records
            if record["Days before cutoff"] is not None
            and int(record["Days before cutoff"]) > 90
            and float(record["Quantity / week"]) > 0
        ]
        if stale_foods:
            st.warning(
                "Some prices are older than 90 days at the selected cutoff: "
                + ", ".join(stale_foods)
                + ". Their dates remain visible above; review freshness before using the scenario."
            )
        st.caption(
            f"Prototype pressure signal: {result.pressure_band}. Monthly conversion uses "
            f"{365.25 / 7 / 12:.3f} weeks/month. The score is max(0, 100 − income share in "
            "percentage points); thresholds and score are unvalidated and descriptive only."
        )

with diet_tab:
    st.subheader("Diet gap analysis | built to avoid invented nutrition")
    st.markdown(
        """
        A price file alone cannot tell us iron, calcium, vitamin B12 or zinc availability. This module
        accepts an expert-reviewed nutrient-composition CSV and compares the resulting scenario intake
        with references explicitly supplied in that same file. No nutrient values are hard-coded.
        """
    )
    template_bytes = create_diet_template()
    st.download_button(
        "Download nutrient-data template",
        data=template_bytes,
        file_name="foodwise_nutrient_data_template.csv",
        mime="text/csv",
    )
    st.caption(
        "Template units: `analysis_unit` must match the app's price unit (KES/kg, KES/L or `per ...`). "
        "`nutrient_per_analysis_unit` must use the nutrient unit shown and refer to that whole kg/L/source unit."
    )
    nutrient_upload = st.file_uploader(
        "Upload expert-reviewed nutrient composition CSV",
        type=["csv"],
        key="nutrient_csv",
    )
    if nutrient_upload is None:
        st.info(
            "Nutrition comparison is not yet populated. Ask a nutrition expert to source composition "
            "values and population-appropriate reference amounts before using this module."
        )
    else:
        try:
            nutrient_frame = pd.read_csv(nutrient_upload)
            quantities = st.session_state
            weekly_inputs = {
                item: float(quantities.get(f"quantity_{item}", 0))
                for item in CANONICAL_FOODS
            }
            scenario_units = {
                item: "KES/L" if item in {"Milk (cow, fresh)", "Oil (vegetable)"} else "KES/kg"
                for item in CANONICAL_FOODS
            }
            gaps = nutrient_gap(
                weekly_quantities=weekly_inputs,
                nutrient_data=nutrient_frame,
                expected_units=scenario_units,
            )
            if gaps.empty:
                st.warning("The uploaded file has no complete nutrient records.")
            else:
                gaps["Estimated/day"] = gaps.apply(
                    lambda row: f"{row['estimated_per_day']:,.2f} {row['nutrient_unit']}",
                    axis=1,
                )
                gaps["Reference/day"] = gaps.apply(
                    lambda row: f"{row['daily_reference']:,.2f} {row['nutrient_unit']}",
                    axis=1,
                )
                gaps["Reference share"] = gaps["reference_share"].map(
                    lambda value: f"{value:.0%}"
                )
                gaps["Remaining to reference"] = gaps.apply(
                    lambda row: f"{row['remaining_to_reference']:,.2f} {row['nutrient_unit']}",
                    axis=1,
                )
                st.dataframe(
                    gaps[
                        [
                            "nutrient",
                            "Estimated/day",
                            "Reference/day",
                            "Reference share",
                            "Remaining to reference",
                            "reference_source",
                            "reference_year",
                        ]
                    ].rename(
                        columns={
                            "nutrient": "Nutrient",
                            "reference_source": "Reference source",
                            "population_group": "Population group",
                            "reference_year": "Reference year",
                        }
                    ),
                    width="stretch",
                    hide_index=True,
                )
                st.warning(
                    "This is an arithmetic scenario estimate, not a diagnosis or dietary recommendation. "
                    "Results depend on food matching, composition source, population group, and serving assumptions."
                )
        except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            st.error(f"Nutrient data could not be analysed: {exc}")

with data_tab:
    st.subheader("Data sources, definitions and limits")
    st.markdown(
        f"""
        **WFP Kenya Food Prices (HDX):** [dataset page]({WFP_DATASET}). The bundled source file contains
        {len(prices):,} valid KES source observations from {prices['date'].min():%d %b %Y} to
        {prices['date'].max():%d %b %Y}. The app retains each reported row and its WFP price flag.

        **KNBS:** [September 2026 CPI release]({KNBS_RELEASE}). The 9.5% headline is the annual
        Food and Non-Alcoholic Beverages division inflation rate; the KNBS release page reports
        6.8% overall annual CPI inflation. National CPI is not directly combined with WFP market prices.

        **FAO CoAHD:** [FAOSTAT Cost and Affordability of a Healthy Diet]({FAOSTAT_CAHD}). The
        brief-supplied 43.5–43.9 million / 76–77% and KSh 189–582 figures are reference context only;
        exact edition, year and methodology should be verified before publishing.
        """
    )
    st.markdown("#### How this prototype handles the data")
    st.markdown(
        """
        - Only positive numeric KES observations with a valid date/item/market are analysed.
        - `90 KG`, `50 KG`, grams and millilitres are converted to a per-kg or per-litre price
          where the source unit is explicit. Other source units stay separate and are not converted.
        - Monthly charts report the median of matching source observations. They are not official CPI
          values and do not compensate for changing market coverage.
        - The household calculator prices an editable, illustrative basket only. Missing prices are
          shown as missing; the total is explicitly marked partial.
        - Income-share thresholds, affordability score and nutrient comparison are prototype calculations,
          not validated policy or clinical measures.
        - County and market coverage in this WFP source is uneven; observed markets are not necessarily
          representative of local prices or household diets.
        """
    )
    if not markets.empty:
        st.markdown("#### WFP market locations")
        selected_locations = markets[markets["market"].isin(selected_markets)]
        if not selected_locations.empty:
            map_fig = px.scatter_geo(
                selected_locations,
                lat="latitude",
                lon="longitude",
                hover_name="market",
                hover_data={"admin1": True, "latitude": False, "longitude": False},
                scope="africa",
                projection="natural earth",
                title="Market locations in the selected comparison set",
                template="plotly_white",
            )
            map_fig.update_geos(
                showcountries=True,
                countrycolor="#d7e1dc",
                showland=True,
                landcolor="#eef3ef",
                showocean=True,
                oceancolor="#f8fbf9",
                lonaxis_range=(33, 43),
                lataxis_range=(-6, 6),
            )
            map_fig.update_traces(marker={"size": 10, "color": "#1a8a72"})
            map_fig.update_layout(height=420, margin=dict(l=0, r=0, t=50, b=0))
            st.plotly_chart(map_fig, width="stretch")
        else:
            st.caption("No selected market coordinates were found in the WFP market file.")
    st.markdown("#### Source files included")
    st.markdown(
        "- `data/wfp_food_prices_ken.csv` — main WFP food-price observations.\n"
        "- `data/wfp_markets_ken.csv` — WFP market names and location coordinates.\n"
        "- `data/knbs_cpi_september_2026.pdf` — KNBS reference release."
    )

st.markdown("---")
st.caption(
    "FOODWISE is a concept-stage decision-support prototype. It is not a nutrition, medical, "
    "benefits-eligibility or official inflation tool."
)
