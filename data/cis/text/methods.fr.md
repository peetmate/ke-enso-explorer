---
title: "Méthodes et Sources"
---

Ce notebook analyse la préparation aux Services d'Information Climatique (CIS) en Afrique subsaharienne en utilisant plusieurs sources de données pour évaluer la capacité d'observation, l'accord des données, les compétences de prévision et le potentiel de mise en œuvre.

## Sources de Données

- **Indice de préparation CIS**: Agrégé à partir de la densité des stations météorologiques, de l’accord entre les produits de précipitations et de la performance des prévisions à court et à long terme
- **Localisation des stations météorologiques**: Enregistrements de 2025 provenant des catalogues de la NOAA, d’OSCAR et de l’OMM, filtrés selon les pays de l’Atlas
- **Données sur les risques**: Indicateurs historiques de sécheresse (NDD) et d’engorgement (NDWL0)
- **Données d'accès**: Taux de pénétration de la télévision, d'internet et du téléphone portable par pays
- **Limites administratives**: GAUL 2024 avec modifications de l'Atlas d'Adaptation

## Méthodologie

L'indice de préparation CIS est calculé comme un composite normalisé de quatre indicateurs, chacun mis à l'échelle de 0 à 1. Le score d’accord sur les précipitations est divisé par quatre avant d’être combiné à la densité des stations météorologiques et à la performance des prévisions à court et à long terme. Les classifications en terciles (Faible, Modéré, Élevé) sont calculées par rapport aux distributions de l'Afrique subsaharienne. Les cartes bivariées superposent la préparation avec l'exposition aux risques ou l'infrastructure d'accès pour identifier les zones prioritaires.
