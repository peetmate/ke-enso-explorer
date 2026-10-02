---
title: "Méthodes et sources"
---

## Jeux de données

### Participation féminine dans le travail agricole et la production de cultures

Les données sur la participation féminine à la production de différentes cultures dans plusieurs pays proviennent de l'étude de [Palacios-Lopez, A., Christiaensen, L. et Kilic, T. (2017)](https://doi.org/10.1016/j.foodpol.2016.09.017). Ces données sont basées sur une enquête auprès d'environ 2000 ménages dans 6 pays vers 2015. Les données pour le nord et le sud du Nigeria ont été combinées en prenant la valeur moyenne pour chaque culture ou activité agricole.

### Emploi dans les systèmes agroalimentaires

Les parts d'emploi par sexe proviennent du domaine [Genre dans les systèmes agroalimentaires](https://www.fao.org/faostat/en/#data/SXS) de FAOSTAT (estimations modélisées de l'OIT, 2000-2023; le graphique montre la dernière année disponible pour chaque pays). L'emploi à la ferme correspond à l'agriculture; l'emploi agroalimentaire hors exploitation comprend la transformation alimentaire, le commerce, le transport et les services de restauration.

### Indicateurs de capacité d'adaptation

Les indicateurs de capacité d'adaptation désagrégés par sexe proviennent également du domaine [Genre dans les systèmes agroalimentaires](https://www.fao.org/faostat/en/#data/SXS) de FAOSTAT : achèvement de l'enseignement primaire en milieu rural (UNESCO), droits fonciers agricoles sûrs (ODD 5.a.1), possession d'un compte bancaire et paiements reçus pour des ventes agricoles (Global Findex de la Banque mondiale), emploi formel dans les systèmes agroalimentaires (OIT), utilisation d'Internet et sécurité alimentaire. Tous sont des parts de personnes de chaque sexe, présentés pour la dernière année disponible de chaque pays, et orientés de sorte que des valeurs plus élevées indiquent une plus grande capacité d'adaptation — la sécurité alimentaire est exprimée comme la part des personnes qui ne sont *pas* en insécurité alimentaire modérée ou grave (inverse de la prévalence ODD 2.1.2).

### Stress thermique humain (WBGT)

Le stress thermique humain est mesuré comme le nombre de jours par an où la température au thermomètre-globe mouillé (WBGT), un indice de chaleur qui combine température et humidité, dépasse 28°C ou 30°C, deux seuils standards de risque thermique au travail. Les données sont des rasters mondiaux à 0,05° couvrant une base historique (années 2000) ainsi que les années 2030 et 2050 selon les scénarios SSP2-4.5 (émissions moyennes) et SSP5-8.5 (émissions élevées). Source : [Ormaza Zulueta, N. et Mehrabi, Z. (2025). Reductions in the future agricultural workday due to climate change. Préimpression Research Square](https://doi.org/10.21203/rs.3.rs-5983106/v1); jeu de données sur [Zenodo](https://doi.org/10.5281/zenodo.14853836).

### Nombre de femmes impliquées dans l'agriculture

- Les données sur la population féminine sont basées sur le jeu de données sur la structure par âge/sexe de WorldPop, et incluent toutes les femmes âgées de 65 ans ou moins [(WorldPop, 2016)](https://hub.worldpop.org/geodata/summary?id=1276). Ces données ont une résolution spatiale de 1 km et sont basées sur les estimations de WorldPop pour 2015.
- Le pourcentage de femmes travaillant dans l'agriculture par limite administrative de niveau 1 est tiré du jeu de données LivWell [(Belmin et al., 2022)](https://doi.org/10.1038/s41597-022-01824-2). Dans les régions non couvertes par les données LivWell, les données à l'échelle nationale de l'estimation modélisée de l'emploi dans l'agriculture de l'ILO stat sont utilisées [(International Labour Organization, 2022)](https://ilostat.ilo.org/fr/methods/concepts-and-definitions/ilo-modelled-estimates/).

### Revenu des ventes de bétail des femmes

Les données sur le revenu des ventes de bétail proviennent de l'enquête Rural Household Multi-Indicator Survey ([RHoMIS](https://doi.org/10.7910/DVN/WS38SA); Gorman et al., 2024), qui couvre 53 144 ménages agricoles enquêtés entre 2015 et 2023, pour la plupart en Afrique. Pour chaque ménage ayant vendu un type de bétail donné, nous prenons la part de ce revenu attribuée aux femmes adultes et jeunes, puis nous faisons la moyenne de cette part entre les ménages du pays. Les enquêtes RHoMIS sont menées dans le cadre de projets de développement; les résultats décrivent donc les sites enquêtés plutôt que les populations nationales.

### Solutions d'adaptation et résultats en matière de genre

Les données sur les solutions sont basées sur une revue systématique des solutions d'adaptation et des preuves de leurs résultats en matière de genre réalisée par [Roy, J., Prakash, A., Some, S. et al. (2022)](https://doi.org/10.1057/s41599-022-01266-6). Cette revue comprend plus de 17 000 études sur le genre et l'adaptation au climat à l'échelle mondiale.

### Indice des points chauds climat-agriculture-genre

L'indice des points chauds provient d'une analyse de l'IFPRI couvrant 87 pays, fondée sur le cadre d'analyse des risques du GIEC. Il combine la part de la population rurale susceptible de faire face à des types spécifiques d'aléas climatiques (programme de recherche du CGIAR sur le changement climatique, l'agriculture et la sécurité alimentaire), l'exposition des femmes mesurée par leur participation au travail et les heures travaillées dans l'agriculture (données des enquêtes sur la main-d'œuvre), et la vulnérabilité des femmes approchée par cinq institutions sociales discriminatoires de l'indice SIGI 2014. Une analyse en composantes principales est utilisée pour construire un indice ordinal des points chauds à partir de ces indicateurs. Les rangs affichés dans ce notebook sont recalculés parmi les pays africains inclus; le rang mondial d'origine (sur 87 pays) figure dans le téléchargement des données. Source : [Lecoutere, E., Mishra, A., Singaraju, N., Koo, J., Azzarri, C., Chanana, N., Nico, G. et Puskur, R. (2023). Where women in agri-food systems are at highest climate risk: a methodology for mapping climate–agriculture–gender inequality hotspots. *Frontiers in Sustainable Food Systems*, 7, 1197809](https://doi.org/10.3389/fsufs.2023.1197809).

### Délimitations

Les zones administratives utilisées dans ce notebook proviennent du jeu de données de délimitations de l'Adaptation Atlas, dérivé des couches administratives mondiales (GAUL) 2024 de la FAO, avec des modifications propres à l'Atlas afin que les pays soient représentés tels qu'ils se représentent eux-mêmes.

## Méthodologie

### Nombre de femmes dans l'agriculture

La part des femmes travaillant dans l'agriculture par région administrative de niveau 1 est la moyenne pondérée par la population féminine de la couche combinée LivWell/OIT. En multipliant le raster de population féminine par cette part puis en sommant par région, on obtient le nombre total de femmes travaillant dans l'agriculture dans chaque pays et région administrative de niveau 1.

### Stress thermique et zones critiques genrées

Les rasters de stress thermique WBGT et la couche des femmes dans l'agriculture ont été résumés aux limites administratives de niveau 1 : le stress thermique comme moyenne de surface, et la part des femmes travaillant dans l'agriculture comme moyenne pondérée par la population féminine. Chacun a ensuite été classé en trois niveaux selon des seuils fixes : le stress thermique à **30 et 90 jours par an** au-dessus du seuil WBGT sélectionné (environ plus d'un mois et plus d'un quart de l'année), et la participation des femmes à **20 % et 50 %**. Les mêmes seuils s'appliquent à toutes les périodes, à tous les scénarios et aux deux seuils WBGT, de sorte que les couleurs de la carte sont directement comparables d'une sélection à l'autre. La superposition des deux classifications donne les neuf classes bivariées de la carte, mettant en évidence les régions où un fort stress thermique coïncide avec une forte participation des femmes à l'agriculture.

### Solutions d'adaptation

Les données sur les solutions ont été extraites d'études centrées sur l'agriculture et situées en Afrique. Les solutions d'adaptation résultantes ont été regroupées en quatre catégories clés:

- Mécanismes financiers et gestion des connaissances (y compris les études sur l'assurance, le crédit et la microfinance)
- Migration
- Gestion des ressources naturelles
- Conservation de la biodiversité
- Diversification des moyens de subsistance

La catégorie d'adaptation, l'intervention, le score de résultat en matière de genre (score ODD 5), la géographie, le risque et le degré d'accord de chacune de ces études ont été extraits pour inclusion dans le tableau.

### Remarque sur les données

La plupart des chiffres d'emploi de ce notebook proviennent d'enquêtes sur la main-d'œuvre et de modèles de l'OIT. Ces sources sous-estiment le travail agricole informel et non rémunéré, qui revient surtout aux femmes; le travail agricole réel des femmes est donc probablement plus élevé que les chiffres présentés ici. Les données sources sont désagrégées par sexe (femmes et hommes); nous les utilisons pour décrire les rôles de genre dans l'agriculture, que les enquêtes sous-jacentes ne peuvent saisir que partiellement. Les moyennes nationales masquent aussi des différences entre régions, groupes d'âge et niveaux de revenu.
