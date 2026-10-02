---
title: "Methods & Sources"
---

The tool utilizes the best available production value datasets covering all of
sub-Saharan Africa, enabling cross-country, crop, and livestock comparisons.
While suitable for macro-scale analysis to determine economic viability and
regional differences, the data's applicability diminishes at smaller scales. For
projects with defined targets and contexts, we recommend engaging with local
communities and governance through participatory approaches to refine investment
targeting and design.

This Spotlight implements a model developed for the Accelerating the Impact of
CGIAR Climate Research in Africa (AICCRA) program.

## Datasets

- **[Spatial crop production](https://radiantearth.github.io/stac-browser/#/external/digital-atlas.s3.amazonaws.com/stac/public_stac/exposure_catalog/mapspam2017/collection.json)**
  data for 2017 comes from MapSPAM 2017 V2r3 (Spatial Production Allocation
  Model)
- **Spatial livestock distribution** data comes from the
  [Gridded Livestock of the World - 2015](https://dataverse.harvard.edu/dataverse/glw_4)
  dataset.
- **National producer price** data comes from
  [FAOstat](https://fenixservices.fao.org/faostat/static/bulkdownloads/Prices_E_Africa.zip)
- **National production and yield** data comes from
  [FAOstat](https://fenixservices.fao.org/faostat/static/bulkdownloads/Production_Crops_Livestock_E_Africa.zip)
- **[Administrative boundaries](https://radiantearth.github.io/stac-browser/#/external/digital-atlas.s3.amazonaws.com/stac/public_stac/boundary_catalog/geoBoundaries_SSA/collection.json)**
  are provided by geoBoundaries 6.0.0. The gbHumanitarian boundaries are used
  and if not available then the gbOpen boundaries are substituted.

## Methodology

This tool implements the methodology developed by
[Philip Thorton](https://scholar.google.com/citations?user=Wx_me7EAAAAJ&hl=en)
used to inform the
[Economic and Financial Analysis (EFA)](https://github.com/CIAT/AICCRA_EFA/blob/main/Documents/AICCRA%20EFA%2027-07-20.docx)
for the
[Accelerating Impacts of CGIAR Climate Research for Africa (AICCRA)](https://aiccra.cgiar.org/)
project.

### Data preparation

#### Producer Prices

1. FAOstat production in USD is averaged by commodity and country for the period
   2015-2019.
2. Data gaps for combinations of country and commodity are filled by using, in
   order of preference: a) the average of neighbouring countries; b) the
   regional average for the worldbank region the country belongs to; c) the
   continental average for sub-Saharan Africa.
3. The producer prices are then merged with country level (admin0)
   administrative boundaries and rasterized.
4. Code availability:
   [fao_producer_prices.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/fao_producer_prices.R)

#### Livestock Value of Production

1. As spatial livestock production comes from 2000, we rescaled values to 2017
   using the proportional national change in faostat production between 2000
   and 2017. The scaling method preferentially adds production increases to the
   middle of the production distribution for a country and not the tails. For
   example, areas without production in 2000 do not suddenly become producers
   and heavy producing areas do not increase as much as intermediate producing
   areas.
2. Livestock production scaled to 2017 is then multiplied by the corresponding
   producer price data to generate livestock value of production in USD in 2017.
3. Meat and milk are added together for sheep, goats and cattle.
4. Values are extracted for administrative areas, summed and converted into
   tabular form.
5. Code availability:
   [fao_producer_prices_livestock.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/fao_producer_prices_livestock.R)

#### Crop Value

1. MapSPAM crop production is multiplied by the corresponding producer price
   data to live crop value of production in USD in 2017.
2. Code availability:
   [fao_producer_prices.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/fao_producer_prices.R)

### Calculations

#### Yield and Production Variability

- FAOstat yield and production data from 2000-2022 are used to calculate the
  [coefficient of variation(CV)](https://en.wikipedia.org/wiki/Coefficient_of_variation)
  for crops (yield) and livestock (production). We use production data rather
  than yields for livestock because livestock yield data appears to be highly
  calculated in FAOstat and shows very little variability over time, whereas
  production data is variable.
- Commodity yields and production amounts in many countries show a strong
  increase over time. Where temporal trends are significant, we detrend to the
  data (linear) before calculating the CV.
- Data gaps in CV for combinations of country and commodity are filled by using,
  in order of preference: a) the average of neighbouring countries; b) the
  regional average for the World Bank region the country belongs to; c) the
  continental average for sub-Saharan Africa.
- Code availability:
  [fao_production_cv.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/fao_production_cv.R)

#### Economic Benefits

We estimate project-level economic benefits by heuristically modeling how
innovations affect value of production (VoP) and climate-related losses across
time, space, and user-defined adoption rates. The main steps are:

1. **VoP under Innovation Adoption**:  
   We apply user-defined adoption rates over time, shrinking the pool of
   non-adopters each year. For instance, with an initial VoP of 1000 and 10%
   adoption: year 1 sees 100 under innovation, year 2 adds 90 (from the
   remaining 900), totaling 190, and so on.

2. **Production Impact Gains**:  
   We multiply the total VoP under adoption by the selected production impact
   (e.g. 20% yield increase). The marginal gain is the difference between VoP
   with and without innovation.

3. **Avoided Climate Losses**:  
   To estimate avoided losses due to innovations that reduce climate impacts, we
   assume:
   - Yield/production follows a normal distribution
   - Adoption reduces yield variability (CV) proportionally  
     For each crop and area, we generate two normal distributions (mean = 1):
     one for non-adopters (baseline CV) and one for adopters (reduced CV). The
     avoided loss proportion is the difference in expected loss in the lower
     tail (below 0) of each distribution.

4. **Total Marginal Benefit**:  
   The total VoP under adoption is adjusted upward using the avoided loss
   proportion. The marginal benefit from climate impact reduction is added to
   the production gain, giving total marginal benefit.

5. **Total Project Benefit**:  
   The total benefit is calculated as:  
   `Total Benefit = Marginal Benefit – (Marginal Benefit / BCR)` where BCR =
   1.62 (assumed from Harris & Orr, 2014). We then discount both benefits and
   costs over time using the selected discount rate to obtain time-adjusted
   values for indicator computation.

6. **Code Availability**:  
   See
   [4_roi.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/4_roi.R)

#### Economic Indicators

The four indicators presented — IRR, MIRR, NPV, and BCR — capture different
aspects of financial performance and can diverge for several reasons:

1. **Timing of cash flows**: IRR and MIRR reflect return rates over time and can
   appear high when large benefits arrive late in a project. However, NPV and
   BCR account for discounting, so delayed benefits reduce their values even if
   the project is profitable in the long run.

2. **Scale of investment**: Small investments with modest benefits can generate
   high IRR or MIRR due to efficiency, but the total net gain (NPV) or
   cost-effectiveness (BCR) may still be low.

3. **Discount rate effects**: Since NPV and BCR rely on discounting, a high
   discount rate (default 8%) can make delayed gains appear smaller. IRR and
   MIRR are unaffected by this rate in their core calculation, but MIRR
   incorporates reinvestment assumptions (also 8% here).

4. **Cumulative structure**: Each year’s values represent cumulative discounted
   returns to date, which helps track how financial indicators evolve across the
   life of the project.

These indicators should be used together for a balanced view of financial
viability.

**Methodological Notes on Indicator Calculations**

This notebook computes four financial indicators — Internal Rate of Return
(IRR), Modified Internal Rate of Return (MIRR), Net Present Value (NPV), and
Discounted Benefit-Cost Ratio (BCR) — using the following methodology:

1. **Cash Flow Construction**:
   - A project cash flow is created by subtracting user-defined project costs
     from estimated economic benefits.
   - Benefits are derived from the value of increased agricultural production
     (VoP) and the reduction of climate-related yield losses, both calculated
     annually based on user inputs.
   - Adoption rate is applied progressively over time, reducing the pool of
     non-adopters and reflecting diminishing marginal expansion.

2. **Discounting**:
   - All future cash flows are discounted to present value using a
     user-specified discount rate (default: 8%).
   - Cumulative discounted benefits and cumulative discounted costs are stored
     for each project year.

3. **Net Present Value (NPV)**:
   - NPV is calculated as the sum of discounted net returns (benefit minus cost)
     up to the selected year.
   - A positive NPV implies the project’s benefits exceed its costs in
     present-value terms.
   - **Note**: We use discrete annual discounting `PV = FV / (1 + r)^t`, not
     continuous compounding.

4. **Discounted Benefit-Cost Ratio (BCR)**:
   - BCR is calculated as the ratio of cumulative discounted benefits to
     cumulative discounted costs.
   - A BCR > 1 indicates a financially efficient project.
   - Unlike some simplified BCR approaches, this version uses full discounted
     benefit and cost streams.

5. **Internal Rate of Return (IRR)**:
   - IRR is estimated via a secant method to find the discount rate that sets
     the net present value of the project’s cumulative cash flow to zero.
   - IRR reflects the annualized rate of return implied by the cash flows.

6. **Modified Internal Rate of Return (MIRR)**:
   - MIRR addresses limitations of IRR by assuming:
     - Negative cash flows (investments) are financed at the discount (finance)
       rate
     - Positive cash flows (returns) are reinvested at the same (reinvestment)
       rate
   - MIRR is calculated from the future value of positive flows and the present
     value of negative flows using the formula:  
     `MIRR = (FV of inflows / |PV of outflows|)^(1/n) - 1  `, where `n` is the
     project duration.
   - We assume the finance and reinvestment rates are equal to the discount rate
     used in NPV and BCR (default: 8%).

7. **Cumulative Time Horizon**:
   - Each metric is calculated cumulatively: i.e., IRR and MIRR at year 3
     reflect performance based on the first 4 years of project cash flows (year
     0 to year 3).
   - This provides a dynamic view of how financial indicators evolve as the
     project progresses.

8. **Edge Case Handling**:
   - If IRR or MIRR cannot be calculated (e.g., due to all-positive or
     all-negative flows), the result is returned as null.
   - Indicators are rounded (NPV to 1 decimal, BCR to 2 decimals, IRR and MIRR
     to 1 decimal %) for clarity.

All indicator calculations are implemented natively within the Observable
notebook (no external APIs), enabling real-time interactivity and transparency.

An earlier and more technical version of this methodology was developed into a
tool using Shiny R and can be found on the github
[AICCRA_EFA](https://github.com/CIAT/AICCRA_EFA).
