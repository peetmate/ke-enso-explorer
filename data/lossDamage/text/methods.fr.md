---
title: "Méthodes"
---

## Projections de la taille des exploitations

Nous combinons des jeux de données spatiaux, démographiques et agricoles afin de produire des projections harmonisées de la distribution de la taille des exploitations africaines de 2000 à 2060. Les données spatiales sur la structure des exploitations, issues de la carte des petits exploitants CIAT/LUGE, ont été associées aux projections démographiques de Mehrabi et al. (2023) et validées à l'aide du Recensement mondial de l'agriculture de la FAO, ainsi que de sources complémentaires telles que Ricciardi et al. (2018) et Aliber & Hart (2009). Pour chaque pays et chaque unité administrative, des tailles d'exploitation représentatives ont été échantillonnées à partir de distributions uniformes ou log-normales par classe de taille, pondérées par le nombre d'exploitations, puis corrigées au moyen d'un algorithme de décalage de la moyenne afin de s'aligner sur les surfaces agricoles totales projetées. Les échantillons corrigés ont été redistribués dans des catégories de taille standardisées et ajustés selon l'un des trois cas de disponibilité des données — données complètes (spatiales + démographiques), démographiques seules ou spatiales seules — par mise à l'échelle proportionnelle. Les valeurs manquantes ont été comblées à l'aide de moyennes nationales ou continentales, et toutes les sorties ont été validées afin d'assurer leur cohérence avec les totaux d'exploitations, les surfaces agricoles et des formes de distribution réalistes. Le jeu de données harmonisé qui en résulte fournit des distributions sous-nationales de la taille des exploitations pour tous les pays africains, par décennie, sur la période 2000-2060.

## Probabilités de perte et de proportion de revenus perdus

Nous examinons comment les pertes de production agricole dues aux chocs climatiques (sécheresses et inondations) varient en fonction de la taille des exploitations, à partir de données d'enquêtes auprès des ménages harmonisées, couvrant 17 pays d'Afrique, d'Asie et d'Amérique latine. L'étude s'appuie sur un jeu de données élaboré par Mehrabi, Fortin et Ramankutty, qui intègre la taille des exploitations au niveau des ménages, les pertes de production déclarées et les indicateurs climatiques correspondants. Deux grands types de modèles ont été mis en œuvre : (1) des modèles de perte binaires estimant la probabilité de subir une perte de production d'origine climatique, et (2) des modèles de perte continus quantifiant le pourcentage de revenus perdus. Les deux types de modèles intègrent des interactions entre la taille de l'exploitation (transformée en logarithme) et le type d'événement (sécheresse ou inondation), et recourent à des structures multiniveaux à effets aléatoires pour tenir compte des hiérarchies spatiales emboîtées (pays et unités administratives). Les modèles ont en outre été filtrés selon des seuils élevés de SPEI (< –0,99 pour la sécheresse, > 0,99 pour l'inondation) afin d'isoler les effets des événements climatiques sévères. Des contrôles diagnostiques, dont la simulation des résidus et le bootstrap, ont servi à vérifier les hypothèses des modèles, et des modèles robustes alternatifs ont été estimés pour éprouver la solidité de l'inférence sur la relation entre taille de l'exploitation et vulnérabilité aux chocs climatiques.

## Estimations historiques et CMIP6 des pertes par type d'exploitation

Nous estimons le nombre d'événements climatiques extrêmes et leurs impacts sur les exploitations africaines en combinant des jeux de données climatiques, catastrophiques et agricoles. Les extrêmes annuels de l'indice standardisé de précipitations et d'évapotranspiration (SPEI) sur la saison de culture ont été calculés au niveau sous-national pour l'ensemble de l'Afrique, sur la période historique (1995-2015) et pour les projections futures (2040-2060) sous les scénarios SSP245 et SSP585, à partir de moyennes d'ensemble dérivées de cinq modèles climatiques globaux CMIP6 (GFDL-ESM4, EC-Earth3, MPI-ESM1-HR, MRI-ESM2-0, NorESM2-LM). Les événements extrêmes sont définis comme les années où les valeurs du SPEI dépassent ±1, correspondant à des conditions très humides ou très sèches. Ces événements modélisés ont été validés à l'aide de la base de données de catastrophes EM-DAT, afin de confirmer que l'approche fondée sur le SPEI restitue la chronologie et la distribution spatiale des principales sécheresses et inondations historiques. Après validation, la fréquence des événements extrêmes a été combinée aux fonctions de perte empiriques décrites ci-dessus et aux projections d'exploitations 2020-2050 reliant la taille des exploitations aux pertes de production et de revenus. Pour chaque unité administrative et chaque classe de taille, la probabilité qu'une exploitation subisse une perte a été estimée pour chaque année et chaque scénario climatique, et les pertes de revenus correspondantes ont été calculées comme des réductions proportionnelles du revenu agricole. Les sorties comprennent à la fois des moyennes annuelles et des totaux cumulés d'exploitations et de pourcentages de revenus affectés, ce qui permet de comparer l'exposition historique et future aux événements climatiques extrêmes à travers l'Afrique.

## Disponibilité des données

Un volume important de données a été produit pour ce notebook. Les données relatives aux projections d'exploitations sont disponibles [ici](https://doi.org/10.5281/zenodo.17583015).

Les données initiales et le code de l'application Shiny de ce notebook sont disponibles [ici](https://doi.org/10.5281/zenodo.17584804).

## Méthodes complémentaires

De plus amples informations sur les méthodes d'estimation des projections d'exploitations sont disponibles dans ce [dépôt](https://github.com/Better-Planet-Laboratory/africafarmprojections).

De plus amples informations sur les méthodes relatives aux fonctions de perte sont disponibles dans ce [dépôt](https://github.com/Better-Planet-Laboratory/farm-loss-farmsize).

De plus amples informations sur les méthodes, notamment les événements humides et secs dérivés du SPEI et les estimations du nombre d'exploitations subissant des pertes et de la proportion de revenus perdus par taille d'exploitation, sont disponibles dans ce [dépôt](https://github.com/Better-Planet-Laboratory/climatepayouts).

L'ensemble des détails méthodologiques figurera également dans l'article à paraître :

Mehrabi, Z., Braich, G., Fortin, J., Ramankutty, N., 2025. Climate payouts to smallholder farmers. LUGE lab/Better Planet Laboratory.

## Remerciements

Ce notebook a été développé en partenariat avec le [Better Planet Laboratory](https://betterplanetlab.com/). Nous remercions également Brayden Youngberg pour la transposition en JavaScript du notebook R Shiny original.
