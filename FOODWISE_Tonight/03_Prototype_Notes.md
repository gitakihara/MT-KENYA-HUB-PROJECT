# FOODWISE — Prototype and demo notes

## The three modules

**1. Price Intelligence**

Tracks market prices of staple and nutritious foods across counties using WFP + KNBS data.

**2. Household Pressure Score**

Estimates how much of a household’s income is needed for a healthy diet and flags when the share becomes dangerous (>50–60%).

**3. Diet Gap Analysis**

Compares the cost of the cheapest calorie diet vs a healthy diet and highlights the most expensive nutrients (usually iron, calcium, vitamin B12, zinc).

## What is included

- `FOODWISE_Prototype.xlsx`: recent WFP price observations, item-level monthly trend charts, editable weekly basket, market price lookups and household simulator.
- `FOODWISE_8_Slide_Showcase.pptx`: an 8-slide pitch deck.
- `FOODWISE_One_Page_Handout.pdf`: one-page print handout.
- `charts/`: four PNG price trend charts suitable for slides or a handout.
- `data/`: the downloaded WFP prices, WFP market lookup and KNBS September 2026 CPI report.

## Calculator assumptions

- The calculator demonstrates seven editable food quantities for one person per week. The quantities are **illustrative prototype inputs**, not an official healthy-diet basket, nutrition advice or an FAO CoAHD estimate.
- A listed food is priced from the latest matching WFP observation for the chosen market. The spreadsheet displays its date and unit.
- Weekly cost is summed for foods with prices; monthly cost is weekly cost × **4.345** × household size.
- Income share is monthly household cost divided by monthly household income. The demonstration affordability score is `max(0, 100 − income share in percentage points)`.
- The 50% and 60% warnings are concept-stage signals, not validated food-security or health thresholds.
- Missing prices reduce the calculated basket cost. The simulator flags partial price coverage; never present an incomplete total as the full cost of a healthy diet.
- Price trends show the monthly median of reported observations by commodity and the most common recorded unit. Market participation can change by month, so these lines are not county-weighted or the same as the KNBS CPI.
- Latest multi-item coverage includes camp markets (IFO/Daadab and Kakuma 2), not a Nairobi/Nyeri price panel. The next data task should find and validate a more representative county-market series.

## 60-second live demo flow

1. “Here is the current cost of a basic healthy basket for one person…”
2. “If a family of 4 earns KSh 25,000, this is the % of income needed…”
3. “When that percentage goes above 60%, diet diversity collapses — this is the pressure signal.”
4. “FOODWISE turns these three signals into one simple dashboard for households and counties.”

**Demo accuracy note:** The first sentence and the 60% statement should be framed as a prototype scenario / proposed pressure signal. The spreadsheet does not yet prove a complete healthy-diet cost or establish that diet diversity collapses at 60%. If any selected food has no recent market price, say the basket is partial and its total understates cost.

## Five-to-seven-minute presentation order

1. **Title — 20 seconds:** introduce yourself and FOODWISE.
2. **Problem — 60–70 seconds:** use the two FAO briefing figures and the verified KNBS food inflation number; identify the FAO figures as briefing values pending exact table citation.
3. **Why it happens — 50 seconds:** price, household budget and information gaps.
4. **Solution — 60 seconds:** walk through Price Intelligence, Household Pressure Score and Diet Gap Analysis.
5. **How it works — 40 seconds:** ingest → analyse → visualise → recommend.
6. **Who benefits — 40 seconds:** households, counties, NGOs and partners.
7. **Where we are — 40 seconds:** concept and data-backed prototype ready; explain its current market-coverage limitation; county pilot next.
8. **Close — 30 seconds:** ask for partners, mentors or a pilot opportunity; add your contact details to the deck and handout.

## Close

“Healthy food should not be a luxury. FOODWISE makes the barriers visible so we can act on them.”

## Before presenting

- Add your name, email and phone to the PowerPoint and PDF handout.
- Open the workbook in Excel, change the yellow basket quantities / income / family-size inputs and confirm the formulas update.
- Confirm market selection and price coverage; use a partial-data caveat if needed.
- Cite the exact FAO series and KNBS item-level table if you state those details as verified facts.
- Ask a nutrition expert to approve a healthy-diet basket and a county partner to validate market coverage before a pilot.

