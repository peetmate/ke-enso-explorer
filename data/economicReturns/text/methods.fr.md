---
title: "Méthodes & Sources"
---

L'outil utilise les meilleurs ensembles de données disponibles sur la valeur de
la production couvrant l'ensemble de l'Afrique subsaharienne, ce qui permet des
comparaisons entre les pays, les cultures et le bétail. S'il convient à
l'analyse macroéconomique pour déterminer la viabilité économique et les
différences régionales, l'applicabilité des données diminue à plus petite
échelle. Pour les projets dont les objectifs et les contextes sont définis, nous
recommandons de s'engager avec les communautés locales et la gouvernance par le
biais d'approches participatives afin d'affiner le ciblage et la conception des
investissements.

Ce _Spotlight_ met en œuvre un modèle développé pour le programme AICCRA
(Accelerating the Impact of CGIAR Climate Research in Africa).

## Ensembles de Données

- **[Les données spatiales sur la production végétale](https://radiantearth.github.io/stac-browser/#/external/digital-atlas.s3.amazonaws.com/stac/public_stac/exposure_catalog/mapspam2017/collection.json)**
  pour 2017 proviennent de MapSPAM 2017 V2r3 (Modèle d’Allocation de Production
  Spatiale).
- **Les données spatiales sur la répartition des animaux** proviennent de
  [Gridded Livestock of the World - 2015](https://dataverse.harvard.edu/dataverse/glw_4).
- **Les données nationales sur les prix à la production** proviennent de
  [FAOstat](https://fenixservices.fao.org/faostat/static/bulkdownloads/Prices_E_Africa.zip)
- **Les données sur les productions et les rendements nationaux** proviennent de
  [FAOstat](https://fenixservices.fao.org/faostat/static/bulkdownloads/Production_Crops_Livestock_E_Africa.zip)
- **[Les frontières administratives](https://radiantearth.github.io/stac-browser/#/external/digital-atlas.s3.amazonaws.com/stac/public_stac/boundary_catalog/geoBoundaries_SSA/collection.json)**
  sont fournies par geoBoundaries 6.0.0. Les frontières gbHumanitarian sont
  utilisées et, si elles ne sont pas disponibles, les frontières gbOpen sont
  substituées.`

  ## Méthodes

  Cet outil met en œuvre la méthodologie développée par
  [Philip Thorton](https://scholar.google.com/citations?user=Wx_me7EAAAAJ&hl=en)
  et utilisée pour informer
  [l'Analyse Économique et Financière (AEF)](https://github.com/CIAT/AICCRA_EFA/blob/main/Documents/AICCRA%20EFA%2027-07-20.docx)
  pour le
  [projet AICCRA (Accelerating Impacts of CGIAR Climate Research for Africa)](https://aiccra.cgiar.org/)
  project.

  ### Préparation des données

#### Prix des Producteurs

1. La production de la FAOstat en USD est calculée en moyenne par produit et par
   pays pour la période 2015-2019.
2. Les données manquantes pour les combinaisons de pays et de produits sont
   comblées en utilisant, par ordre de préférence : a) la moyenne des pays
   voisins ; b) la moyenne régionale pour la région de la Banque mondiale à
   laquelle le pays appartient ; c) la moyenne continentale pour l'Afrique
   subsaharienne.
3. Les prix à la production sont ensuite fusionnés avec les limites
   administratives du pays (admin0) et tramés.
4. Disponibilité du code:
   [fao_producer_prices.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/fao_producer_prices.R)

#### Valeur de la Production Animale

1. Étant donné que la production animale spatiale date de 2000, nous avons remis
   à l'échelle les valeurs pour 2017 en utilisant la variation nationale
   proportionnelle de la production faostat entre 2000 et 2017. La méthode de
   mise à l'échelle ajoute de préférence les augmentations de production au
   milieu de la distribution de la production pour un pays et non aux queues.
   Par exemple, les régions sans production en 2000 ne deviennent pas
   soudainement productrices et les régions à forte production n'augmentent pas
   autant que les régions à production intermédiaire.
2. La production animale ramenée à 2017 est ensuite multipliée par les données
   de prix à la production correspondantes pour générer la valeur de la
   production animale en USD en 2017.
3. La viande et le lait sont additionnés pour les ovins, les caprins et les
   bovins.
4. Les valeurs sont extraites pour les zones administratives, additionnées et
   converties sous forme de tableau.
5. Disponibilité du code:
   [fao_producer_prices_livestock.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/fao_producer_prices_livestock.R)

#### Valeur des Cultures

1. La production végétale de MapSPAM est multipliée par les données de prix à la
   production correspondantes pour obtenir la valeur de la production végétale
   en USD en 2017.
2. Disponibilité du code:
   [fao_producer_prices.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/fao_producer_prices.R)

### Calculs

#### Variabilité du Rendement et de la Production

- Les données de rendement et de production de la FAOstat pour la période
  2000-2022 sont utilisées pour calculer le
  [coefficient de variation (CV)](https://en.wikipedia.org/wiki/Coefficient_of_variation)
  des cultures (rendement) et du bétail (production). Nous utilisons les données
  de production plutôt que les rendements pour le bétail parce que les données
  de rendement du bétail semblent être très bien calculées dans la FAOstat et
  montrent très peu de variabilité dans le temps, alors que les données de
  production sont variables.
- Les rendements des produits et les quantités produites dans de nombreux pays
  montrent une forte augmentation au fil du temps. Lorsque les tendances
  temporelles sont significatives, nous procédons à une désintégration des
  données (linéaire) avant de calculer le CV.
- Les données manquantes dans les CV pour les combinaisons de pays et de
  produits sont comblées en utilisant, par ordre de préférence: a) la moyenne
  des pays voisins; b) la moyenne régionale pour la région de la Banque mondiale
  à laquelle le pays appartient; c) la moyenne continentale pour l'Afrique
  subsaharienne.
- Disponibilité du code:
  [fao_production_cv.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/fao_production_cv.R)

#### Bénéfices économiques

Nous estimons les bénéfices économiques d’un projet en modélisant de manière
heuristique comment les innovations influencent la valeur de la production (VoP)
et les pertes liées au climat dans le temps, l’espace, et selon les taux
d’adoption définis par l’utilisateur. Les principales étapes sont :

1. **VoP sous adoption de l’innovation** :  
   Nous appliquons des taux d’adoption progressifs définis par l’utilisateur,
   réduisant chaque année la part de non-adoptants. Par exemple, pour une VoP
   initiale de 1000 et un taux d’adoption de 10 %, la première année voit 100
   sous innovation, la deuxième ajoute 90 (des 900 restants), totalisant 190, et
   ainsi de suite.

2. **Gains liés à l’impact sur la production** :  
   Nous multiplions la VoP totale sous adoption par l’impact de production
   sélectionné (par exemple, +20 % de rendement). Le gain marginal est la
   différence entre la VoP avec et sans innovation.

3. **Pertes climatiques évitées** :  
   Pour estimer les pertes évitées grâce à des innovations réduisant les impacts
   climatiques, nous supposons :
   - Une distribution normale des rendements/productions
   - Une réduction proportionnelle de la variabilité des rendements (CV) liée à
     l’adoption  
     Pour chaque culture et zone, nous générons deux distributions normales
     (moyenne = 1) : une pour les non-adoptants (CV de référence), une pour les
     adoptants (CV réduite). La proportion de perte évitée correspond à la
     différence entre les queues gauches (en dessous de 0) de ces distributions.

4. **Bénéfice marginal total** :  
   La VoP totale sous adoption est ajustée à la hausse via la proportion de
   perte évitée. Le bénéfice marginal lié à la réduction des impacts climatiques
   est ajouté au gain de production pour obtenir le bénéfice marginal total.

5. **Bénéfice total du projet** :  
   Le bénéfice total est calculé comme :  
   `Bénéfice total = Bénéfice marginal – (Bénéfice marginal / BCR)` où BCR =
   1.62 (valeur tirée de Harris & Orr, 2014). Les bénéfices et coûts sont
   ensuite actualisés à l’aide du taux d’actualisation sélectionné afin
   d’obtenir des valeurs ajustées dans le temps pour le calcul des indicateurs.

6. **Disponibilité du code** :  
   Voir
   [4_roi.R](https://github.com/AdaptationAtlas/hazards_prototype/blob/main/R/4_roi.R)

---

#### Indicateurs économiques

Quatre indicateurs — TRI (IRR), TRI modifié (MIRR), VAN (NPV) et RCA actualisé
(BCR) — capturent différents aspects de la performance financière et peuvent
diverger selon plusieurs facteurs :

1. **Calendrier des flux de trésorerie** :  
   Le TRI et le MIRR reflètent les taux de rendement dans le temps et peuvent
   être élevés si les bénéfices arrivent tardivement. La VAN et le RCA
   appliquent l’actualisation, ce qui diminue la valeur des bénéfices différés,
   même si le projet reste rentable à long terme.

2. **Échelle de l’investissement** :  
   Des projets de petite taille avec des bénéfices modestes peuvent afficher un
   TRI ou MIRR élevé, mais des gains nets totaux (VAN) ou une efficacité (BCR)
   faibles.

3. **Effets du taux d’actualisation** :  
   La VAN et le BCR sont sensibles au taux d’actualisation (par défaut 8 %). Un
   taux élevé réduit la valeur des bénéfices futurs. Le TRI et le MIRR n’y sont
   pas sensibles dans leur formule de base, mais le MIRR incorpore les
   hypothèses de réinvestissement (également à 8 % ici).

4. **Structure cumulative** :  
   Chaque année reflète les retours cumulés actualisés jusqu’à ce point, ce qui
   permet de suivre l’évolution de la viabilité financière dans le temps.

Ces indicateurs doivent être utilisés ensemble pour une lecture équilibrée de la
performance financière.

---

#### Notes méthodologiques sur le calcul des indicateurs

1. **Construction des flux de trésorerie**
   - Les flux sont construits en soustrayant les coûts du projet (uniformément
     répartis) des bénéfices économiques estimés.
   - Les bénéfices incluent l’augmentation de la VoP et les pertes climatiques
     évitées, calculés annuellement.
   - Le taux d’adoption est appliqué progressivement, réduisant la base des
     non-adoptants chaque année.

2. **Actualisation**
   - Tous les flux futurs sont actualisés selon `PV = FV / (1 + r)^t`
     (actualisation discrète annuelle).
   - Les coûts et bénéfices actualisés sont enregistrés cumulativement par
     année.

3. **Valeur actuelle nette (VAN)**
   - La VAN est la somme des flux nets actualisés jusqu’à l’année sélectionnée.
   - Une VAN positive indique que les bénéfices surpassent les coûts en valeur
     actuelle.

4. **Ratio coût-bénéfice actualisé (RCA)**
   - Le BCR est le ratio des bénéfices actualisés cumulés sur les coûts
     actualisés cumulés.
   - Un BCR > 1,0 suggère un projet efficient financièrement.
   - Cette approche utilise les séries temporelles complètes actualisées.

5. **Taux de rendement interne (TRI)**
   - Estimé par méthode des sécantes, il est le taux qui annule la VAN du flux
     cumulatif.
   - Le TRI exprime le rendement annuel implicite du projet.

6. **Taux de rendement interne modifié (TRIM)**
   - Corrige les limites du TRI en supposant que :
     - Les investissements sont financés au taux d’actualisation
     - Les retours sont réinvestis à ce même taux
   - Calcul :  
     `MIRR = (VF des flux positifs / |VA des flux négatifs|)^(1/n) - 1` où `n`
     est la durée du projet (en années).
   - Les taux de financement et de réinvestissement sont fixés au taux
     d’actualisation (par défaut 8 %).

7. **Horizon temporel cumulatif**
   - Tous les indicateurs sont calculés de manière cumulative : par ex. le TRI à
     l’année 3 utilise les flux des années 0 à 3.
   - Cela permet d’analyser la performance au fil du projet.

8. **Traitement des cas limites**
   - Si le TRI ou le MIRR ne peuvent être calculés (tous les flux étant positifs
     ou négatifs), la valeur retournée est null.
   - Les résultats sont arrondis pour clarté : VAN à 1 décimale, BCR à 2,
     TRI/MIRR à 1 décimale (%).

Tous les calculs sont réalisés localement dans le notebook Observable (aucune
API externe), assurant interactivité et transparence.

Une version antérieure et plus technique de cette méthodologie a été implémentée
dans l’outil R Shiny [AICCRA_EFA](https://github.com/CIAT/AICCRA_EFA).
