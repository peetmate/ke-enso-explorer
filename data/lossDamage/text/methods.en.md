---
title: "Methods"
---

## Farm size projections

We integrate spatial, demographic, and agricultural datasets to generate harmonized projections of African farm size distributions from 2000 to 2060. Spatial farm structure data from the CIAT/LUGE Smallholder Map were combined with demographic projections from Mehrabi et al. 2023 and validated against the FAO World Census of Agriculture, alongside auxiliary sources such as Ricciardi et al. (2018) and Aliber & Hart (2009). For each country and administrative unit, representative farm sizes were sampled from uniform or log-normal distributions by size class, weighted by farm counts, and corrected via a mean-shift algorithm to align with projected agricultural area totals. Corrected samples were rebinned into standardized size categories and adjusted according to one of three data availability cases—full data (spatial + demographic), demographic-only, or spatial-only—using proportional scaling, dependent on data availability. Missing values were filled using country or continental means, and all outputs were validated to ensure consistency with farm totals, agricultural area, and realistic distributional shapes. The resulting harmonized dataset provides subnational farm size distributions for all African countries at decadal intervals through 2000-2060.

## Loss and proportion of lost revenue probabilities

We examine how agricultural production losses from climate shocks (droughts and floods) vary as a function of farm size using harmonized household survey data from 17 countries across Africa, Asia, and Latin America. The study employs a dataset developed by Mehrabi, Fortin, and Ramankutty, which integrates household-level farm size, reported production losses, and corresponding climatic indicators. Two main model types were implemented: (1) binary loss models estimating the probability of experiencing a climate-induced production loss, and (2) continuous loss models quantifying the percentage of revenue lost. Both models incorporated interactions between log-transformed farm size and event type (drought or flood) and used multilevel random effects structures to account for nested spatial hierarchies (country and administrative units). Models were further filtered for high SPEI thresholds (< –0.99 for drought, > 0.99 for flood) to isolate the effects of severe climatic events. Diagnostic checks, including residual simulation and bootstrapping, were used to check model assumptions, with alternative robust models being run to check robustness of inference on the relationship between farm size and vulnerability to climate shocks.

## Historical and CMIP6 estimates of loss by farm type

We estimate the number of extreme climate events and their impacts on African farms by integrating climate, disaster, and agricultural datasets. Annual growing-season extremes of the Standardized Precipitation Evapotranspiration Index (SPEI) were computed at the subnational level across Africa for the historical period (1995–2015) and for future projections (2040–2060) under SSP245 and SSP585 scenarios, using ensemble means derived from five CMIP6 global climate models (GFDL-ESM4, EC-Earth3, MPI-ESM1-HR, MRI-ESM2-0, NorESM2-LM). Extreme events were defined as years when SPEI values exceeded ±1, corresponding to very wet or very dry conditions. These modeled events were validated against the EM-DAT disaster database to confirm that the SPEI-based approach captured the timing and spatial distribution of major historical droughts and floods. Once validated, the frequency of extreme events was used in combination with the above empirically derived loss functions and 2020-2050 farm projections linking farm size to production and revenue losses. For each administrative unit and farm size class, the probability of farms experiencing loss was estimated for each year and climate scenario, and corresponding revenue losses were calculated as proportional reductions in farm income. The outputs include both yearly averages and cumulative totals of farms and % of revenue affected, allowing comparison of historical and future exposure to extreme climate events across Africa.

## Data availability

A significant amount of data was developed for this notebook. The data for farm projections can be found [here](https://doi.org/10.5281/zenodo.17583015).

The initial data and shiny app code for this notebook can be found [here](https://doi.org/10.5281/zenodo.17584804).

## Additional methods

More information on methods for farm projections estimates are available at this [repository](https://github.com/Better-Planet-Laboratory/africafarmprojections).

More information on methods for loss functions are available at this [repository](https://github.com/Better-Planet-Laboratory/farm-loss-farmsize).

More information on methods including SPEI-derived wet and dry events and estimates of farms experiencing losses and the proportion of lost revenue by farm size are available at this [repository](https://github.com/Better-Planet-Laboratory/climatepayouts).

Full methodological details will also be contained in the forthcoming paper:

Mehrabi, Z., Braich, G., Fortin, J., Ramankutty, N., 2025. Climate payouts to smallholder farmers. LUGE lab/Better Planet Laboratory.

## Acknowledgements

This notebook was developed in partnership with the [Better Planet Laboratory](https://betterplanetlab.com/). We also acknowledge Brayden Youngberg for translating the original R Shiny notebook to JavaScript.
