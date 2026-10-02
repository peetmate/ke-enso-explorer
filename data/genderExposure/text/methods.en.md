---
title: "Methods & Sources"
---

## Datasets

### Female participation in agricultural labor and crop production

The data for female labor participation in the production of different crops across multiple countries is taken from [Palacios-Lopez, A., Christiaensen, L. and  Kilic, T. (2017)](https://doi.org/10.1016/j.foodpol.2016.09.017). The data is based on a survey of ~2000 households in 6 countries circa 2015. Data for North and South Nigeria was combined by taking the mean value for each crop or agricultural activity.

### Agrifood Systems Employment

Employment shares by sex come from the FAOSTAT [Gender in Agrifood Systems domain](https://www.fao.org/faostat/en/#data/SXS) (ILO modelled estimates, 2000–2023; the chart shows each country's latest available year). On-farm employment corresponds to agriculture; off-farm agrifood-systems employment includes food processing, trade, transport, and food services.

### Adaptive Capacity Indicators

The sex-disaggregated adaptive-capacity indicators also come from the FAOSTAT [Gender in Agrifood Systems domain](https://www.fao.org/faostat/en/#data/SXS): rural primary-school completion (UNESCO), secure rights over agricultural land (SDG 5.a.1), bank account ownership and payments received for agricultural sales (World Bank Global Findex), formal employment in agrifood systems (ILO), internet use, and food security. All are shares of people of each sex, shown for each country's latest available year, and oriented so that higher values indicate greater ability to adapt — food security is expressed as the share of people who are *not* moderately or severely food insecure (inverse of SDG 2.1.2 prevalence).

### Human Heat Stress (WBGT)

Human heat stress is measured as the number of days per year on which the wet-bulb globe temperature (WBGT), a heat index that combines temperature and humidity, exceeds 28°C or 30°C, two standard occupational heat-risk thresholds. The data are global 0.05° rasters covering a historic baseline (2000s) and the 2030s and 2050s under the SSP2-4.5 (medium emissions) and SSP5-8.5 (high emissions) scenarios. Source: [Ormaza Zulueta, N. and Mehrabi, Z. (2025). Reductions in the future agricultural workday due to climate change. Research Square preprint](https://doi.org/10.21203/rs.3.rs-5983106/v1); dataset on [Zenodo](https://doi.org/10.5281/zenodo.14853836).

### Number of Women Involved In Agriculture

- Female population data is based on the WorldPop age/sex structure dataset, and includes all females aged 65 or younger [(WorldPop, 2016)](https://hub.worldpop.org/geodata/summary?id=1276). This data has a spatial resolution of 1 km and is based on the WorldPop 2015 estimates. 
- Percentage of women working in agriculture per admin level 1 boundary is taken from the LivWell dataset [(Belmin et al., 2022)](https://doi.org/10.1038/s41597-022-01824-2). In regions not covered by the Livwell data, country scale data from the ILO stat modeled estimate of employment in agriculture is used [(International Labour Organization, 2022)](https://ilostat.ilo.org/resources/concepts-and-definitions/ilo-modelled-estimates/).

### Women's Livestock Sale Income

Household data on livestock sale income come from the Rural Household Multi-Indicator Survey ([RHoMIS](https://doi.org/10.7910/DVN/WS38SA); Gorman et al., 2024), which covers 53,144 farm households surveyed between 2015 and 2023, most of them in Africa. For each household that sold a given type of livestock we take the portion of that income attributed to adult and youth women, then average this share across households in the country. RHoMIS surveys are run within development projects, so the results describe the surveyed sites rather than national populations.

### Adaptation Solutions and Gender Outcomes

The solution data is based on a systematic review of adaptation solutions and evidence on their gender outcomes by [Roy, J., Prakash, A., Some, S. et al. (2022)](https://doi.org/10.1057/s41599-022-01266-6). This review is comprised of >17,000 studies on gender and climate adaptation globally.

### Climate-Agriculture-Gender Hotspot Index

The hotspot index comes from an IFPRI analysis covering 87 countries, built on the IPCC risk framework. It combines the share of rural population likely to face specific climate hazard types (CGIAR Research Program on Climate Change, Agriculture and Food Security), women's exposure measured from labor participation and hours worked in agriculture (Labor Force Survey data), and women's vulnerability proxied by five discriminatory social institutions from the Social Institutions and Gender Index (SIGI) 2014. Principal component analysis is used to construct an ordinal hotspot index from these indicators. Ranks shown in this notebook are recomputed across the African countries included; the original global rank (out of 87 countries) is included in the data download. Source: [Lecoutere, E., Mishra, A., Singaraju, N., Koo, J., Azzarri, C., Chanana, N., Nico, G. and Puskur, R. (2023). Where women in agri-food systems are at highest climate risk: a methodology for mapping climate–agriculture–gender inequality hotspots. *Frontiers in Sustainable Food Systems*, 7, 1197809](https://doi.org/10.3389/fsufs.2023.1197809).

### Boundaries

Administrative areas used in this notebook come from the Adaptation Atlas boundary dataset, derived from the FAO Global Administrative Unit Layers (GAUL) 2024 with Atlas-specific modifications so that countries are shown as they represent themselves.

## Methods

### Number of Women in Agriculture

The share of women working in agriculture per admin 1 region is the female-population-weighted mean of the combined LivWell/ILO layer. Multiplying the female population raster by this share and summing per region gives the total number of women working in agriculture in each country and admin 1 region.

### Heat Stress and Gender Hot Spots

The WBGT heat-stress rasters and the women-in-agriculture layer were summarized to admin 1 boundaries: heat stress as the area mean, and the share of women working in agriculture as the female-population-weighted mean. Each was then classified into three levels using fixed breaks: heat stress at **30 and 90 days per year** above the selected WBGT threshold (roughly, more than a month and more than a quarter of the year), and women's participation at **20% and 50%**. The same breaks apply to every time period, scenario, and WBGT threshold, so map colors are directly comparable across selections. Overlaying the two classifications gives the nine bivariate map classes, highlighting regions where high heat stress coincides with high female participation in agriculture.

### Adaptation Solutions

The solutions data was subset by studies that were focused on agriculture and located in Africa. The resulting adaptive solutions were grouped in four key categories:

- Financial mechanisms and knowledge management (including studies on insurance, credit, and microfinance)
- Migration
- Natural resource management
- Biodiversity conservation
- Livelihood diversification

The adaptation category, intervention, gender outcome score (SDG 5 score), geography, risk, and degree of agreement from each of these studies was extracted for inclusion in the table.

### A Note on the Data

Most employment figures in this notebook come from labour force surveys and ILO models. These are known to undercount informal and unpaid farm work, which falls mostly to women, so women's actual agricultural labour is likely higher than the numbers shown here. The source data are disaggregated by sex (female and male); we use them to describe gender roles in agriculture, which the underlying surveys can only partly capture. National averages also hide differences between regions, age groups, and income levels.
