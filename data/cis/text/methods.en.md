---
title: "Methods & Sources"
---

This notebook analyzes Climate Information Services (CIS) readiness across Sub-Saharan Africa using multiple data sources to assess observation capacity, data agreement, forecast skill, and implementation potential.

## Data Sources

- **CIS Readiness Index**: Aggregated from weather station density, precipitation agreement, and short- and long-term forecast skill metrics
- **Weather Station Locations**: 2025 catalogue records from NOAA, OSCAR, and WMO, filtered to the Atlas countries
- **Hazard Data**: Historical drought (NDD) and waterlogging (NDWL0) indicators
- **Access Data**: TV, internet, and cellphone penetration rates by country
- **Administrative Boundaries**: GAUL 2024 with Adaptation Atlas modifications

## Methodology

The CIS Readiness Index is calculated as a normalized composite of four indicators, each scaled to 0-1. The precipitation agreement score is divided by four before it is combined with weather station density and short- and long-term forecast skill. Tercile classifications (Low, Moderate, High) are computed relative to Sub-Saharan African distributions. Bivariate maps overlay readiness with hazard exposure or access infrastructure to identify priority zones.
