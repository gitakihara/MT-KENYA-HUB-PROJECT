from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import xlsxwriter
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CHARTS = ROOT / "charts"
SOURCE_CSV = DATA / "wfp_food_prices_ken.csv"
SELECTED = [
    "Maize flour",
    "Beans (dry)",
    "Kale",
    "Milk (cow, fresh)",
    "Oil (vegetable)",
    "Potatoes (Irish)",
    "Rice",
    "Sugar",
]
MARKETS = ["IFO (Daadab)", "Kakuma 2"]
START_DATE = date(2024, 10, 1)
SOURCE_URL = (
    "https://data.humdata.org/dataset/wfp-food-prices-for-kenya"
)
KNBS_URL = (
    "https://www.knbs.or.ke/reports/"
    "consumer-price-indices-and-inflation-rates-september-2026/"
)
NAVY = "#15324B"
TEAL = "#1A8A83"
MINT = "#E7F4F0"
GOLD = "#E7B84B"
PALE = "#F4F7F9"
INK = "#213547"


def read_prices() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    all_rows: list[dict[str, object]] = []
    with SOURCE_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for source in csv.DictReader(handle):
            row_date = datetime.strptime(source["date"], "%Y-%m-%d").date()
            try:
                price = float(source["price"])
            except (TypeError, ValueError):
                continue
            all_rows.append(
                {
                    **source,
                    "parsed_date": row_date,
                    "numeric_price": price,
                }
            )

    recent = [
        row
        for row in all_rows
        if row["commodity"] in SELECTED
        and START_DATE <= row["parsed_date"]
    ]
    return all_rows, recent


def latest_by_market_item(
    recent: list[dict[str, object]],
) -> dict[tuple[str, str], dict[str, object]]:
    latest: dict[tuple[str, str], dict[str, object]] = {}
    for row in recent:
        key = (str(row["market"]), str(row["commodity"]))
        current = latest.get(key)
        if current is None or row["parsed_date"] > current["parsed_date"]:
            latest[key] = row
    return latest


def build_trend_images(
    recent: list[dict[str, object]],
) -> tuple[list[dict[str, object]], dict[str, list[tuple[str, float]]]]:
    CHARTS.mkdir(exist_ok=True)
    chart_items = ["Maize flour", "Beans (dry)", "Potatoes (Irish)", "Rice"]
    by_item_unit: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in recent:
        if row["commodity"] in chart_items:
            by_item_unit[(str(row["commodity"]), str(row["unit"]))].append(row)

    unit_for_item: dict[str, str] = {}
    for item in chart_items:
        candidates = [
            (len(rows), unit)
            for (candidate, unit), rows in by_item_unit.items()
            if candidate == item
        ]
        if candidates:
            unit_for_item[item] = max(candidates)[1]

    trend_rows: list[dict[str, object]] = []
    chart_values: dict[str, list[tuple[str, float]]] = {}
    for item in chart_items:
        unit = unit_for_item.get(item)
        if unit is None:
            continue
        monthly: dict[str, list[float]] = defaultdict(list)
        for row in by_item_unit[(item, unit)]:
            key = row["parsed_date"].strftime("%Y-%m")
            monthly[key].append(float(row["numeric_price"]))
        values = [
            (month, statistics.median(prices))
            for month, prices in sorted(monthly.items())
        ]
        chart_values[item] = values
        trend_rows.extend(
            {
                "month": month,
                "commodity": item,
                "unit": unit,
                "median": median,
                "market_observations": len(monthly[month]),
            }
            for month, median in values
        )

        fig, ax = plt.subplots(figsize=(7.3, 3.8), dpi=160)
        ax.plot(
            [month for month, _ in values],
            [median for _, median in values],
            color="#1A8A83",
            linewidth=2.6,
            marker="o",
            markersize=4,
        )
        ax.set_title(f"{item} — monthly median ({unit})", loc="left", color=NAVY)
        ax.set_ylabel("Median reported price (KES)")
        ax.set_xlabel("Month")
        ax.grid(axis="y", alpha=0.2)
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", labelrotation=45, labelsize=8)
        fig.tight_layout()
        fig.savefig(CHARTS / f"trend_{item.lower().replace(' ', '_')}.png")
        plt.close(fig)

    return trend_rows, chart_values


def create_workbook(
    recent: list[dict[str, object]],
    latest: dict[tuple[str, str], dict[str, object]],
    trend_rows: list[dict[str, object]],
    chart_values: dict[str, list[tuple[str, float]]],
) -> None:
    path = ROOT / "FOODWISE_Prototype.xlsx"
    workbook = xlsxwriter.Workbook(path)
    workbook.set_properties(
        {
            "title": "FOODWISE Tonight — price and household pressure prototype",
            "subject": "Kenya WFP food prices and editable basket scenario",
            "author": "FOODWISE",
            "comments": "Prototype; see Read Me & Notes for scope and limitations.",
        }
    )
    workbook.set_calc_mode("auto")

    title = workbook.add_format(
        {"bold": True, "font_size": 19, "font_color": "white", "bg_color": NAVY}
    )
    subtitle = workbook.add_format(
        {"font_size": 10, "font_color": "#52687A", "text_wrap": True}
    )
    header = workbook.add_format(
        {
            "bold": True,
            "font_color": "white",
            "bg_color": TEAL,
            "border": 0,
            "text_wrap": True,
            "valign": "vcenter",
        }
    )
    section = workbook.add_format(
        {"bold": True, "font_size": 12, "font_color": NAVY, "bottom": 1}
    )
    input_format = workbook.add_format(
        {"bg_color": "#FFF4CF", "border": 1, "border_color": GOLD, "num_format": "0.00"}
    )
    int_input = workbook.add_format(
        {"bg_color": "#FFF4CF", "border": 1, "border_color": GOLD, "num_format": "0"}
    )
    money = workbook.add_format({"num_format": '"KSh " #,##0.00;[Red]-"KSh " #,##0.00'})
    money_input = workbook.add_format(
        {
            "bg_color": "#FFF4CF",
            "border": 1,
            "border_color": GOLD,
            "num_format": '"KSh " #,##0.00',
        }
    )
    percent = workbook.add_format({"num_format": "0.0%"})
    score_format = workbook.add_format({"num_format": "0.0"})
    text_wrap = workbook.add_format({"text_wrap": True, "valign": "top"})
    date_format = workbook.add_format({"num_format": "yyyy-mm-dd"})
    small = workbook.add_format({"font_size": 9, "font_color": "#52687A", "text_wrap": True})
    banner = workbook.add_format(
        {"bold": True, "font_color": NAVY, "bg_color": MINT, "text_wrap": True, "valign": "vcenter"}
    )
    raw_date = workbook.add_format({"num_format": "yyyy-mm-dd"})

    # Tab 1: filtered recent observations, preserving the original units and flags.
    raw = workbook.add_worksheet("WFP Raw Prices")
    raw.freeze_panes(1, 0)
    raw.set_tab_color(TEAL)
    raw_headers = [
        "Date",
        "Admin 1",
        "Admin 2",
        "Market",
        "Commodity",
        "Unit",
        "Price (KES)",
        "Price Type",
        "Price Flag",
        "Currency",
        "Source",
    ]
    raw.write_row(0, 0, raw_headers, header)
    for idx, row in enumerate(recent, start=1):
        raw.write_datetime(idx, 0, datetime.combine(row["parsed_date"], datetime.min.time()), raw_date)
        raw.write_row(
            idx,
            1,
            [
                row["admin1"],
                row["admin2"],
                row["market"],
                row["commodity"],
                row["unit"],
            ],
        )
        raw.write_number(idx, 6, float(row["numeric_price"]), money)
        raw.write_row(
            idx,
            7,
            [row["pricetype"], row["priceflag"], row["currency"], "WFP / HDX"],
        )
    raw.add_table(
        0,
        0,
        len(recent),
        len(raw_headers) - 1,
        {
            "name": "WFPRecentPrices",
            "style": "Table Style Medium 2",
            "columns": [{"header": value} for value in raw_headers],
        },
    )
    raw.set_column("A:A", 13)
    raw.set_column("B:D", 22)
    raw.set_column("E:F", 21)
    raw.set_column("G:G", 17)
    raw.set_column("H:K", 16)

    # Internal lookup table contains only the two markets used by the simulator.
    snapshot = workbook.add_worksheet("Market Price Snapshot")
    snapshot.hide()
    snapshot_headers = [
        "Lookup Key",
        "Market",
        "Commodity",
        "Unit",
        "Latest Price",
        "Currency",
        "Observation Date",
    ]
    snapshot.write_row(0, 0, snapshot_headers, header)
    snapshot_rows: list[dict[str, object]] = []
    for market in MARKETS:
        for item in SELECTED:
            row = latest.get((market, item))
            if row is None:
                continue
            snapshot_rows.append(row)
    for idx, row in enumerate(snapshot_rows, start=1):
        key = f"{row['market']}|{row['commodity']}"
        snapshot.write_row(idx, 0, [key, row["market"], row["commodity"], row["unit"]])
        snapshot.write_number(idx, 4, float(row["numeric_price"]))
        snapshot.write_row(idx, 5, [row["currency"]])
        snapshot.write_datetime(
            idx, 6, datetime.combine(row["parsed_date"], datetime.min.time()), raw_date
        )
    snapshot_last = len(snapshot_rows) + 1

    # Tab 2: editable per-person weekly basket.
    basket = workbook.add_worksheet("Healthy Basket")
    basket.set_tab_color(GOLD)
    basket.freeze_panes(7, 0)
    basket.merge_range("A1:F1", "FOODWISE | Healthy Basket Calculator", title)
    basket.merge_range(
        "A2:F2",
        "Editable scenario only — quantities are illustrative, not an FAO or clinical diet prescription.",
        subtitle,
    )
    basket.write("A4", "Selected market", section)
    basket.write("B4", MARKETS[0], input_format)
    basket.data_validation("B4", {"validate": "list", "source": MARKETS})
    basket.merge_range(
        "D4:F4",
        "Yellow cells are editable. Prices/units/dates come from the latest matching WFP record in the selected market.",
        banner,
    )
    basket_headers = [
        "Food item",
        "Quantity / person / week",
        "Recorded unit",
        "Unit price (KES)",
        "Weekly cost (KES)",
        "Latest observation",
    ]
    basket.write_row(6, 0, basket_headers, header)
    quantities = {
        "Maize flour": 1.5,
        "Beans (dry)": 0.35,
        "Kale": 0.75,
        "Milk (cow, fresh)": 1.75,
        "Oil (vegetable)": 0.25,
        "Potatoes (Irish)": 0.75,
        "Rice": 0.35,
    }
    market_values = {
        (str(row["market"]), str(row["commodity"])): row for row in snapshot_rows
    }
    basket_items = list(quantities)
    for idx, item in enumerate(basket_items, start=7):
        excel_row = idx + 1
        default_row = market_values.get((MARKETS[0], item))
        basket.write(idx, 0, item)
        basket.write_number(idx, 1, quantities[item], input_format)
        key_formula = f'$B$4&"|"&A{excel_row}'
        lookup_range = f"'Market Price Snapshot'!$A$2:$G${snapshot_last}"
        unit_formula = f'=IFERROR(VLOOKUP({key_formula},{lookup_range},4,FALSE),"")'
        price_formula = f'=IFERROR(VLOOKUP({key_formula},{lookup_range},5,FALSE),"")'
        date_formula = f'=IFERROR(VLOOKUP({key_formula},{lookup_range},7,FALSE),"")'
        basket.write_formula(
            idx, 2, unit_formula, None, str(default_row["unit"]) if default_row else ""
        )
        basket.write_formula(
            idx,
            3,
            price_formula,
            money,
            float(default_row["numeric_price"]) if default_row else "",
        )
        default_cost = (
            quantities[item] * float(default_row["numeric_price"])
            if default_row
            else ""
        )
        basket.write_formula(
            idx,
            4,
            f'=IF(OR(C{excel_row}="",D{excel_row}=""),"",B{excel_row}*D{excel_row})',
            money,
            default_cost,
        )
        basket.write_formula(
            idx,
            5,
            date_formula,
            date_format,
            datetime.combine(default_row["parsed_date"], datetime.min.time())
            if default_row
            else "",
        )
    first_item_row = 8
    last_item_row = first_item_row + len(basket_items) - 1
    total_row = last_item_row + 2
    default_total = sum(
        quantities[item] * float(market_values[(MARKETS[0], item)]["numeric_price"])
        for item in basket_items
        if (MARKETS[0], item) in market_values
    )
    basket.write(total_row, 0, "Weekly total for priced foods", section)
    basket.write_formula(
        total_row,
        4,
        f"=SUM(E{first_item_row}:E{last_item_row})",
        money,
        default_total,
    )
    default_coverage = sum(
        (MARKETS[0], item) in market_values for item in basket_items
    )
    basket.write(
        total_row + 1,
        0,
        "Price coverage",
        section,
    )
    basket.write_formula(
        total_row + 1,
        4,
        f'=COUNT(D{first_item_row}:D{last_item_row})&" / {len(basket_items)} items"',
        None,
        f"{default_coverage} / {len(basket_items)} items",
    )
    basket.merge_range(
        total_row + 3,
        0,
        total_row + 4,
        5,
        "Interpretation: the total is the sum of only the listed foods with available prices. "
        "The chosen weekly quantities are demonstration assumptions. Confirm comparable units, "
        "quality, prices and a nutritionist-approved basket before presenting this as a diet cost.",
        text_wrap,
    )
    basket.set_column("A:A", 25)
    basket.set_column("B:B", 23)
    basket.set_column("C:C", 17)
    basket.set_column("D:E", 19)
    basket.set_column("F:F", 18)
    basket.set_row(1, 30)

    # Tab 3: household calculator with visible partial-data warning.
    sim = workbook.add_worksheet("Household Simulator")
    sim.set_tab_color(GOLD)
    sim.merge_range("A1:D1", "FOODWISE | Household Pressure Simulator", title)
    sim.merge_range(
        "A2:D2",
        "Uses the currently selected market and only the foods with recorded prices.",
        subtitle,
    )
    sim.write("A4", "Household size (people)", header)
    sim.write_number("B4", 4, int_input)
    sim.write("A5", "Monthly household income (KES)", header)
    sim.write_number("B5", 25000, money_input)
    sim.write("A7", "Selected market", header)
    sim.write_formula("B7", "='Healthy Basket'!B4", None, MARKETS[0])
    sim.write("A8", "Priced foods available", header)
    sim.write_formula(
        "B8",
        f'=COUNT(\'Healthy Basket\'!D{first_item_row}:D{last_item_row})',
        None,
        default_coverage,
    )
    sim.write("A9", "Weekly cost per person (priced foods)", header)
    sim.write_formula(
        "B9",
        f"='Healthy Basket'!E{total_row + 1}",
        money,
        default_total,
    )
    monthly_person = default_total * 4.345
    monthly_household = monthly_person * 4
    pressure_value = monthly_household / 25000 if 25000 else 0
    sim.write("A10", "Monthly cost per person (KES)", header)
    sim.write_formula("B10", "=B9*4.345", money, monthly_person)
    sim.write("A11", "Monthly household cost (KES)", header)
    sim.write_formula("B11", "=B10*B4", money, monthly_household)
    sim.write("A12", "Income share for priced foods", header)
    sim.write_formula("B12", '=IF(B5>0,B11/B5,"")', percent, pressure_value)
    sim.write("A13", "Affordability score (0-100)", header)
    sim.write_formula(
        "B13",
        '=IF(B5>0,MAX(0,MIN(100,100-B12*100)),"")',
        score_format,
        max(0.0, min(100.0, 100 - pressure_value * 100)),
    )
    sim.write("A14", "Pressure signal", header)
    pressure_label = (
        "Critical: above 60%"
        if pressure_value > 0.6
        else "Watch: 50–60%"
        if pressure_value >= 0.5
        else "Below prototype thresholds"
    )
    sim.write_formula(
        "B14",
        '=IF(B12>60%,"Critical: above 60%",IF(B12>=50%,"Watch: 50–60%","Below prototype thresholds"))',
        banner,
        pressure_label,
    )
    sim.write("A15", "Data coverage warning", header)
    sim.write_formula(
        "B15",
        f'=IF(B8<{len(basket_items)},"PARTIAL: missing prices; cost is understated","All listed food prices available")',
        banner,
        "All listed food prices available"
        if default_coverage == len(basket_items)
        else "PARTIAL: missing prices; cost is understated",
    )
    sim.merge_range(
        "A18:D20",
        "Score definition: max(0, 100 − income share in percentage points). "
        "The 50%/60% warning thresholds and score are prototype signals, not validated "
        "poverty, nutrition or clinical thresholds. A partial basket can only understate pressure.",
        text_wrap,
    )
    sim.set_column("A:A", 40)
    sim.set_column("B:B", 35)
    sim.set_column("C:D", 17)
    sim.conditional_format(
        "B12",
        {"type": "cell", "criteria": ">=", "value": 0.6, "format": workbook.add_format({"bg_color": "#FCE4D6", "font_color": "#9C0006"})},
    )
    sim.conditional_format(
        "B12",
        {"type": "cell", "criteria": "between", "minimum": 0.5, "maximum": 0.6, "format": workbook.add_format({"bg_color": "#FFF2CC", "font_color": "#7F6000"})},
    )

    # Tab 4: four auditable, item-specific trends and their source data.
    dash = workbook.add_worksheet("Dashboard & Charts")
    dash.set_tab_color(TEAL)
    dash.merge_range("A1:N1", "FOODWISE | Kenya Food Price Intelligence", title)
    dash.merge_range(
        "A2:N2",
        "Monthly median of reported WFP market observations; exact commodity and most common unit shown. "
        "Not county-weighted and not a KNBS CPI series.",
        subtitle,
    )
    dash.merge_range(
        "A3:N3",
        f"Selected records: {len(recent):,} from {START_DATE.isoformat()} to {max(row['parsed_date'] for row in recent).isoformat()}; "
        f"{len(set(str(row['market']) for row in recent))} distinct markets.",
        banner,
    )
    table_start = 37
    dash.write_row(table_start, 0, ["Month", "Commodity", "Unit", "Median KES", "Market observations"], header)
    for idx, row in enumerate(trend_rows, start=table_start + 1):
        month_date = datetime.strptime(str(row["month"]) + "-01", "%Y-%m-%d")
        dash.write_datetime(idx, 0, month_date, workbook.add_format({"num_format": "mmm yyyy"}))
        dash.write_row(idx, 1, [row["commodity"], row["unit"]])
        dash.write_number(idx, 3, float(row["median"]), money)
        dash.write_number(idx, 4, int(row["market_observations"]))
    chart_locations = ["A5", "H5", "A21", "H21"]
    chart_items = list(chart_values)
    for chart_index, item in enumerate(chart_items):
        chart = workbook.add_chart({"type": "line"})
        start = table_start + 1
        rows_for_item = [row for row in trend_rows if row["commodity"] == item]
        end = start + len(rows_for_item) - 1
        chart.add_series(
            {
                "name": f"{item} ({rows_for_item[0]['unit']})",
                "categories": ["Dashboard & Charts", start, 0, end, 0],
                "values": ["Dashboard & Charts", start, 3, end, 3],
                "line": {"color": TEAL, "width": 2.25},
                "marker": {"type": "circle", "size": 4, "border": {"color": TEAL}, "fill": {"color": "white"}},
            }
        )
        chart.set_title({"name": f"{item} — {rows_for_item[0]['unit']}"})
        chart.set_y_axis({"name": "Median price (KES)", "major_gridlines": {"visible": True, "line": {"color": "#E2E8ED"}}})
        chart.set_x_axis({"date_axis": True, "num_format": "mmm yy", "label_position": "low"})
        chart.set_legend({"none": True})
        chart.set_size({"width": 500, "height": 280})
        chart.set_chartarea({"border": {"none": True}})
        dash.insert_chart(chart_locations[chart_index], chart)
    dash.set_column("A:A", 15)
    dash.set_column("B:B", 25)
    dash.set_column("C:C", 13)
    dash.set_column("D:E", 22)
    dash.set_column("F:N", 13)
    dash.set_row(2, 32)

    # Tab 5: methodology and safe-to-say context.
    notes = workbook.add_worksheet("Read Me & Notes")
    notes.merge_range("A1:F1", "FOODWISE | Read Me & Data Notes", title)
    notes.set_column("A:A", 30)
    notes.set_column("B:F", 24)
    notes.write("A3", "Data and freshness", section)
    notes.merge_range(
        "A4:F5",
        f"Official WFP Kenya food-price file downloaded from HDX on 8 October 2026. "
        f"The full source file contains {len(read_prices()[0]):,} rows through "
        f"{max(row['parsed_date'] for row in read_prices()[0]).isoformat()}; the workbook's raw tab "
        f"contains {len(recent):,} selected food observations from October 2024 onward. "
        f"Latest file metadata update reported by HDX: 4 October 2026.",
        text_wrap,
    )
    notes.write_url("A7", SOURCE_URL, string="WFP Kenya Food Prices (HDX)", cell_format=small)
    notes.write_url("A8", KNBS_URL, string="KNBS September 2026 CPI release", cell_format=small)
    notes.write("A10", "Use these supplied benchmarks carefully", section)
    notes.merge_range(
        "A11:F13",
        "Brief-supplied figures: 43.5–43.9 million people (about 76–77%) unable to afford a healthy diet; "
        "estimated daily healthy-diet cost KSh 189–582 depending on method; September 2026 food and "
        "non-alcoholic beverages inflation 9.5% (verified on the KNBS release page). "
        "The million/percentage and cost range need their precise FAO edition, year, geographic definition "
        "and method attached before external publication.",
        text_wrap,
    )
    notes.write("A15", "Important limits", section)
    notes.merge_range(
        "A16:F21",
        "WFP observations are not a nationally representative retail panel; markets and dates vary. "
        "The most recent multi-item records in this extract include IFO (Daadab) and Kakuma 2; these are "
        "camp markets, not a proxy for Nairobi or Nyeri households. The market dropdown intentionally shows "
        "only markets with multiple recent target-item records. Units are kept as published, prices may be "
        "missing/stale, and the simulator flags incomplete coverage. Food quantities are editable demo inputs, "
        "not a recommended healthy diet. The score and 50%/60% flags are concept-stage indicators, not "
        "validated policy thresholds. Diet-gap module requires an agreed healthy-diet basket and nutrient data.",
        text_wrap,
    )
    notes.write("A23", "Formula conventions", section)
    notes.merge_range(
        "A24:F26",
        "Monthly cost = weekly basket cost × 4.345 weeks/month × household size. "
        "Income share = monthly household cost ÷ monthly household income. "
        "Affordability score = max(0, 100 − income share in percentage points). "
        "If one or more prices are missing, totals include only priced foods and the household cost is an "
        "underestimate.",
        text_wrap,
    )

    workbook.close()


def add_text(slide, x, y, w, h, text, size=20, color=INK, bold=False, align=None):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = Inches(0.06)
    frame.margin_right = Inches(0.06)
    frame.margin_top = Inches(0.03)
    frame.margin_bottom = Inches(0.03)
    para = frame.paragraphs[0]
    para.text = text
    para.font.name = "Aptos"
    para.font.size = Pt(size)
    para.font.bold = bold
    para.font.color.rgb = RGBColor.from_string(color.replace("#", ""))
    if align is not None:
        para.alignment = align
    return box


def slide_base(prs: Presentation, number: int, title_text: str):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    background = slide.background.fill
    background.solid()
    background.fore_color.rgb = RGBColor(247, 249, 250)
    bar = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.18)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = RGBColor(26, 138, 131)
    bar.line.fill.background()
    add_text(slide, 0.65, 0.38, 12.0, 0.65, title_text, 28, NAVY, True)
    add_text(slide, 0.68, 7.14, 10.5, 0.22, "FOODWISE | Healthy food should not be a luxury.", 9, "#607586")
    add_text(slide, 12.0, 7.08, 0.55, 0.28, f"{number:02d}", 10, TEAL, True, PP_ALIGN.RIGHT)
    return slide


def create_deck() -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    slide.background.fill.solid()
    slide.background.fill.fore_color.rgb = RGBColor(21, 50, 75)
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(1.0), Inches(0.14), Inches(4.8))
    accent.fill.solid()
    accent.fill.fore_color.rgb = RGBColor(231, 184, 75)
    accent.line.fill.background()
    add_text(slide, 1.2, 1.35, 10.9, 1.2, "FOODWISE", 42, "#FFFFFF", True)
    add_text(slide, 1.23, 2.48, 10.5, 0.95, "Making healthy food affordability visible", 27, "#BCE5DA")
    add_text(slide, 1.23, 3.68, 9.8, 0.65, "A public-data concept and mini-prototype for Kenya", 18, "#FFFFFF")
    add_text(slide, 1.23, 6.0, 10.2, 0.45, "[Your name]  |  [Email / phone]", 14, "#D5E2E9")
    add_text(slide, 12.0, 7.08, 0.55, 0.28, "01", 10, "#BCE5DA", True, PP_ALIGN.RIGHT)

    slide = slide_base(prs, 2, "The problem | Healthy diets remain out of reach")
    cards = [
        ("43.5–43.9M", "people, about 76–77%, cannot afford a healthy diet*"),
        ("KSh 189–582", "estimated daily cost of a healthy diet, depending on method*"),
        ("9.5%", "annual food and non-alcoholic beverages inflation, Sep 2026"),
    ]
    for index, (metric, caption) in enumerate(cards):
        x = 0.75 + index * 4.15
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(1.65), Inches(3.75), Inches(2.35))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(231, 244, 240)
        shape.line.color.rgb = RGBColor(207, 227, 220)
        add_text(slide, x + 0.2, 2.03, 3.35, 0.65, metric, 27, TEAL, True, PP_ALIGN.CENTER)
        add_text(slide, x + 0.28, 2.86, 3.2, 0.85, caption, 15, INK, False, PP_ALIGN.CENTER)
    add_text(slide, 0.9, 4.55, 11.5, 0.7, "*FAO figures supplied for this concept; confirm edition, year and method before publication.", 12, "#607586")
    add_text(slide, 0.9, 5.3, 11.5, 0.8, "KNBS reports 9.5% year-on-year inflation for Food and Non-Alcoholic Beverages in September 2026.", 17, NAVY, True)

    slide = slide_base(prs, 3, "Why affordability breaks down")
    drivers = [
        ("PRICE", "Staple and nutritious food prices vary by place and month."),
        ("BUDGET", "Households face trade-offs between food, housing, transport and other essentials."),
        ("INFORMATION", "A price alone does not show the cost of a nutritious basket or the household's pressure."),
    ]
    for index, (label, body) in enumerate(drivers):
        y = 1.65 + index * 1.45
        add_text(slide, 1.0, y, 2.0, 0.5, label, 19, TEAL, True)
        add_text(slide, 3.0, y - 0.02, 8.9, 0.78, body, 19, INK)
        if index < 2:
            slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1), Inches(y + 0.88), Inches(10.9), Inches(0.02)).fill.solid()

    slide = slide_base(prs, 4, "The solution | Three connected modules")
    modules = [
        ("1. Price Intelligence", "Tracks market prices of staple and nutritious foods across counties using WFP + KNBS data."),
        ("2. Household Pressure Score", "Estimates how much of a household’s income is needed for a healthy diet and flags when the share becomes dangerous (>50–60%)."),
        ("3. Diet Gap Analysis", "Compares the cost of the cheapest calorie diet vs a healthy diet and highlights the most expensive nutrients (usually iron, calcium, vitamin B12, zinc)."),
    ]
    for index, (heading, body) in enumerate(modules):
        y = 1.45 + index * 1.62
        add_text(slide, 0.95, y, 11.0, 0.4, heading, 20, TEAL, True)
        add_text(slide, 1.0, y + 0.48, 11.0, 0.82, body, 16, INK)

    slide = slide_base(prs, 5, "How it works | Ingest → Analyse → Visualise → Recommend")
    steps = [
        ("INGEST", "WFP market prices\nKNBS CPI"),
        ("ANALYSE", "Clean units\nCompare trends"),
        ("VISUALISE", "Price signals\nHousehold pressure"),
        ("RECOMMEND", "Pilot priorities\nCounty action"),
    ]
    for index, (heading, body) in enumerate(steps):
        x = 0.6 + index * 3.2
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(2.0), Inches(2.65), Inches(2.15))
        shape.fill.solid()
        shape.fill.fore_color.rgb = RGBColor(231, 244, 240)
        shape.line.color.rgb = RGBColor(207, 227, 220)
        add_text(slide, x + 0.15, 2.35, 2.35, 0.45, heading, 17, TEAL, True, PP_ALIGN.CENTER)
        add_text(slide, x + 0.18, 3.05, 2.3, 0.75, body, 16, INK, False, PP_ALIGN.CENTER)
        if index < 3:
            add_text(slide, x + 2.66, 2.74, 0.43, 0.4, "→", 22, GOLD, True, PP_ALIGN.CENTER)
    add_text(slide, 0.95, 5.15, 11.4, 0.75, "The first prototype uses public WFP observations; KNBS CPI provides national inflation context.", 17, NAVY, True)

    slide = slide_base(prs, 6, "Who benefits")
    beneficiaries = [
        ("Households", "Understand how food costs compare with income and where prices are moving."),
        ("Counties", "See market-level signals that can inform monitoring and pilot targeting."),
        ("NGOs & partners", "Use a shared evidence base to focus nutrition and livelihood support."),
    ]
    for index, (heading, body) in enumerate(beneficiaries):
        x = 0.85 + index * 4.15
        add_text(slide, x, 2.0, 3.55, 0.55, heading, 21, TEAL, True, PP_ALIGN.CENTER)
        add_text(slide, x + 0.15, 2.85, 3.25, 1.4, body, 16, INK, False, PP_ALIGN.CENTER)
    add_text(slide, 1.1, 5.25, 11.0, 0.65, "Next step: co-design a county-level pilot with local price and nutrition partners.", 19, NAVY, True, PP_ALIGN.CENTER)

    slide = slide_base(prs, 7, "Where we are | Concept + prototype")
    add_text(slide, 0.9, 1.24, 11.4, 0.55, "WFP price trends (monthly median by item; reported markets)", 17, NAVY, True)
    chart_path = CHARTS / "trend_maize_flour.png"
    if chart_path.exists():
        slide.shapes.add_picture(str(chart_path), Inches(0.85), Inches(1.85), width=Inches(7.0))
    add_text(
        slide,
        8.15,
        2.0,
        4.25,
        2.1,
        "Live spreadsheet prototype\n• Price trends from WFP Kenya data\n• Editable household basket\n• Income-share pressure signal",
        17,
        INK,
    )
    add_text(
        slide,
        8.15,
        4.45,
        4.15,
        1.2,
        "Coverage is uneven; recent multi-item examples include camp markets, not Nairobi or Nyeri.",
        13,
        "#607586",
    )
    add_text(slide, 0.9, 6.2, 11.5, 0.45, "Prototype ready; next: validate the basket, add county coverage and run a pilot.", 17, TEAL, True)

    slide = slide_base(prs, 8, "Healthy food should not be a luxury.")
    add_text(slide, 1.2, 1.8, 10.8, 1.2, "FOODWISE makes the barriers visible so we can act on them.", 29, TEAL, True, PP_ALIGN.CENTER)
    add_text(slide, 1.55, 3.7, 10.2, 0.8, "Seeking county partners, nutrition mentors and a pilot opportunity.", 20, NAVY, False, PP_ALIGN.CENTER)
    add_text(slide, 2.2, 5.2, 8.9, 0.55, "[Your name]  |  [Email]  |  [Phone]", 16, "#607586", False, PP_ALIGN.CENTER)

    prs.save(ROOT / "FOODWISE_8_Slide_Showcase.pptx")


def create_handout() -> None:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="BrandTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=27,
            leading=32,
            textColor=colors.HexColor(NAVY),
            alignment=TA_CENTER,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Subheading",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor(TEAL),
            spaceBefore=6,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontSize=10.2,
            leading=14,
            textColor=colors.HexColor(INK),
            alignment=TA_LEFT,
            spaceAfter=5,
        )
    )
    doc = SimpleDocTemplate(
        str(ROOT / "FOODWISE_One_Page_Handout.pdf"),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title="FOODWISE — Healthy food affordability",
        author="FOODWISE",
    )
    story = [
        Paragraph("FOODWISE", styles["BrandTitle"]),
        Paragraph(
            "Healthy food should not be a luxury.<br/>Making the barriers visible so we can act on them.",
            ParagraphStyle(
                "Tagline",
                parent=styles["BodyText"],
                alignment=TA_CENTER,
                fontSize=14,
                leading=19,
                textColor=colors.HexColor(TEAL),
                spaceAfter=12,
            ),
        ),
        HRFlowable(width="100%", thickness=1.2, color=colors.HexColor(TEAL), spaceAfter=9),
        Paragraph("THE PROBLEM", styles["Subheading"]),
        Paragraph(
            "<b>43.5–43.9 million people</b> (about 76–77%) cannot afford a healthy diet; "
            "the estimated daily cost is <b>KSh 189–582</b> depending on method.* "
            "In September 2026, KNBS reported <b>9.5% annual food and non-alcoholic beverages inflation</b>.",
            styles["BodySmall"],
        ),
        Paragraph("THE SOLUTION", styles["Subheading"]),
        Paragraph(
            "<b>Price Intelligence</b> tracks staple and nutritious food prices. "
            "<b>Household Pressure Score</b> estimates the income share needed for a healthy diet. "
            "<b>Diet Gap Analysis</b> compares the cost of a healthy diet with a cheapest-calorie diet "
            "and highlights nutrient cost barriers.",
            styles["BodySmall"],
        ),
        Paragraph("WHAT IS READY", styles["Subheading"]),
        Paragraph(
            "A concept-stage spreadsheet prototype uses public WFP Kenya market-price observations, "
            "with a household basket calculator and price-trend charts. Data coverage varies by market; "
            "the prototype's editable quantities and pressure thresholds need validation before policy use.",
            styles["BodySmall"],
        ),
        Paragraph("NEXT STEP", styles["Subheading"]),
        Paragraph(
            "Partner with a county, nutrition expert and local data users to validate the basket, "
            "expand market coverage and run a county-level pilot.",
            styles["BodySmall"],
        ),
        Spacer(1, 5),
        HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#D9E3E8"), spaceAfter=8),
        Paragraph(
            "<b>CONTACT</b> &nbsp;&nbsp; [Your name] &nbsp;|&nbsp; [Email] &nbsp;|&nbsp; [Phone]",
            ParagraphStyle(
                "Contact",
                parent=styles["BodyText"],
                alignment=TA_CENTER,
                fontSize=10,
                leading=14,
                textColor=colors.HexColor(NAVY),
            ),
        ),
        Spacer(1, 8),
        Paragraph(
            "*FAO figures supplied for this concept; confirm exact edition, year and method before external publication. "
            "KNBS September 2026 CPI release: knbs.or.ke. WFP Kenya Food Prices: data.humdata.org.",
            ParagraphStyle(
                "Footnote",
                parent=styles["BodyText"],
                fontSize=7.7,
                leading=10,
                textColor=colors.HexColor("#607586"),
            ),
        ),
    ]
    doc.build(story)


def main() -> None:
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(f"Missing WFP source file: {SOURCE_CSV}")
    _, recent = read_prices()
    if not recent:
        raise ValueError("No recent observations matched the selected foods.")
    latest = latest_by_market_item(recent)
    trend_rows, chart_values = build_trend_images(recent)
    create_workbook(recent, latest, trend_rows, chart_values)
    create_deck()
    create_handout()
    print(f"Selected WFP rows: {len(recent)}")
    print(
        "Latest observation: "
        + max(row["parsed_date"] for row in recent).isoformat()
    )
    print(f"Basket snapshot rows: {len(latest)}")
    print(f"Workbook: {ROOT / 'FOODWISE_Prototype.xlsx'}")
    print(f"PowerPoint: {ROOT / 'FOODWISE_8_Slide_Showcase.pptx'}")
    print(f"Handout: {ROOT / 'FOODWISE_One_Page_Handout.pdf'}")


if __name__ == "__main__":
    main()
