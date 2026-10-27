# Services publics NexAura

Tu peux consulter huit API publiques françaises et internationales, sans clé. Les conditions de chaque source restent applicables. Les outils sont fabriqués avec `FastMCP.from_openapi` depuis des descriptions locales : aucun outil métier n'est écrit à la main.

## Installer et lancer

Depuis ce dossier, avec Python 3.11 ou plus récent :

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/python -m nexaura_services_publics adresse
```

Remplace `adresse` par le nom d’un connecteur du tableau ci-dessous. Le serveur échange par l'entrée et la sortie standard ; ses messages techniques restent sur la sortie d'erreur.
Aucune description n'est téléchargée au démarrage. Les fichiers `specs/` et `connecteurs/` sont inclus dans la distribution Python.

## Les huit connecteurs

| Connecteur | Source | Outils |
|---|---|---|
| `adresse` | Géoplateforme / BAN | `chercher_adresse`, `adresse_depuis_position` |
| `geo` | API Geo | `chercher_communes`, `commune_par_code`, `departements`, `regions` |
| `jours-feries` | Etalab | `jours_feries` |
| `calendrier-scolaire` | Éducation nationale | `vacances_scolaires` |
| `bodacc` | DILA / BODACC | `annonces_entreprise` |
| `tva-europe` | Commission européenne / VIES | `verifier_tva`, `etat_service_tva` |
| `jours-feries-europe` | OpenHolidays API | `jours_feries`, `vacances_scolaires_europe`, `pays`, `regions_du_pays` |
| `taux-de-change` | Frankfurter | `taux_de_change`, `taux_entre_devises`, `devises_disponibles` |

## Outils disponibles

Chaque outil se déclare en lecture seule (readOnlyHint).

### adresse

| Outil | Ce qu’il fait | Limite |
|---|---|---|
| `chercher_adresse` | Cherche une adresse avec q et renvoie ses coordonnées et les adresses proposées. | 50 appels/seconde/IP ; ce connecteur se limite à 40 appels/seconde. |
| `adresse_depuis_position` | Donne lon et lat : tu reçois les adresses proches de cette position. | 50 appels/seconde/IP ; ce connecteur se limite à 40 appels/seconde. |

Données : Licence Ouverte 2.0 (BAN, index address uniquement). [Licence et source](https://adresse.data.gouv.fr/outils/api-doc/adresse). [Quota](https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/geocodage/).

### geo

| Outil | Ce qu’il fait | Limite |
|---|---|---|
| `chercher_communes` | Cherche avec nom ou codePostal : tu reçois les communes correspondantes. | 50 appels/seconde/IP ; ce connecteur se limite à 40 appels/seconde. |
| `commune_par_code` | Donne un code INSEE : tu reçois les informations de cette commune. | 50 appels/seconde/IP ; ce connecteur se limite à 40 appels/seconde. |
| `departements` | Consulte les départements : tu reçois leurs noms et codes. | 50 appels/seconde/IP ; ce connecteur se limite à 40 appels/seconde. |
| `regions` | Consulte les régions : tu reçois leurs noms et codes. | 50 appels/seconde/IP ; ce connecteur se limite à 40 appels/seconde. |

Données : Licence Ouverte 2.0 (données administratives INSEE) ; sources géographiques sous licences Open Data. [Licence et source](https://geo.api.gouv.fr/decoupage-administratif). [Quota](https://www.data.gouv.fr/dataservices/api-decoupage-administratif-api-geo).

### jours-feries

| Outil | Ce qu’il fait | Limite |
|---|---|---|
| `jours_feries` | Choisis une zone et une année : tu reçois les dates et les noms des jours fériés. | quota officiel non communiqué ; cadence locale de 1 appel/seconde. |

Données : Licence Ouverte 2.0. [Licence et source](https://www.data.gouv.fr/datasets/jours-feries-en-france). [Quota](https://www.data.gouv.fr/api/1/dataservices/?q=jours%20f%C3%A9ri%C3%A9s).

### calendrier-scolaire

| Outil | Ce qu’il fait | Limite |
|---|---|---|
| `vacances_scolaires` | Consulte les vacances du calendrier scolaire officiel pour ta zone et ton année scolaire. Dans where, écris par exemple : zones = 'Zone A' AND annee_scolaire = '2026-2027' ; tu reçois les périodes et académies, parfois répétées. | quota officiel non communiqué ; cadence locale de 1 appel/seconde. |

Données : Licence Ouverte 2.0. [Licence et source](https://www.data.gouv.fr/datasets/le-calendrier-scolaire). [Quota](https://www.data.gouv.fr/api/1/dataservices/?q=calendrier%20scolaire).

### bodacc

| Outil | Ce qu’il fait | Limite |
|---|---|---|
| `annonces_entreprise` | Donne `where: "registre = '444608442'"` pour consulter les annonces de ton entreprise, de la plus récente à la plus ancienne. | Quota officiel non communiqué ; 1 appel/seconde, 20 annonces au maximum par appel (20 par défaut). |

Données : [Licence Ouverte / Open Licence (`fr-lo`), fiche DILA](https://www.data.gouv.fr/datasets/bodacc). Le jeu `annonces-commerciales` est fixé dans le chemin ; `registre` et `dateparution` sont les vrais champs vérifiés dans les métadonnées officielles. Le filtre natif exige exactement un SIREN de neuf chiffres. `order_by` est fixé à `dateparution DESC` ; `offset` permet la suite, entre 0 et 9980, sans pagination automatique. Aucune recherche générique sur d’autres jeux.

### tva-europe

| Outil | Ce qu’il fait | Limite |
|---|---|---|
| `verifier_tva` | Donne `countryCode: FR` et `vatNumber: "40444608442"`, sans répéter le pays dans le numéro. | 1 appel/seconde, une requête à la fois ; une seule relance après 3 s sur `MS_UNAVAILABLE` ou `MS_MAX_CONCURRENT_REQ`. |
| `etat_service_tva` | Consulte la disponibilité de VIES et des services nationaux. | Même limite partagée avec la vérification. |

Quota officiel chiffré non communiqué. Pour la France, le nom et l’adresse reviennent souvent vides : tu obtiens surtout « valide » ou « non valide » (`isValid` sur le GET). Une erreur ou une indisponibilité n’est jamais un verdict « non valide ». Les erreurs restent des réponses de la source, sans faux résultat. Le verrou couvre la réponse entière, l’attente de 3 s et la seconde tentative, pour tous les outils d’un même serveur. Aucune autre relance, même sur délai d’attente ou erreur HTTP seule.

Données : [conditions VIES et droits des administrations nationales](https://ec.europa.eu/taxation_customs/vies/#/disclaimer), sans licence ouverte uniforme annoncée. Description OpenAPI 3.0 **écrite par NexAura d’après la documentation officielle** ; la description Swagger désormais liée par cette documentation décrit la vérification en POST, pas le GET demandé ici. Aucun POST n’est exposé.

### jours-feries-europe

| Outil | Ce qu’il fait | Limite |
|---|---|---|
| `jours_feries` | Jours fériés du pays : `countryIsoCode: BE`, `validFrom: 2026-01-01`, `validTo: 2026-12-31` obligatoires ; région `subdivisionCode` facultative. | Trois ans au maximum ; quota officiel non communiqué, cadence locale de 1 appel/seconde. |
| `vacances_scolaires_europe` | Vacances scolaires avec les mêmes paramètres. | Même période maximale et cadence partagée. |
| `pays` | Pays disponibles. | Même cadence partagée. |
| `regions_du_pays` | Régions pertinentes du pays `countryIsoCode` obligatoire. | Même cadence partagée. |

Données OpenHolidays API (ODbL). [Licence ODbL-1.0 des données](https://github.com/openpotato/openholidaysapi.data) ; [FAQ : accès gratuit, usage commercial autorisé](https://www.openholidaysapi.org/en/faq/). Aucun quota chiffré annoncé sur la [page d’accueil](https://www.openholidaysapi.org/en/) ni dans la FAQ : **1/s est une cadence locale**, sans garantie de quota journalier. Attribution à conserver ; les obligations ODbL s’appliquent à la réutilisation, notamment au partage des bases dérivées.

Les quatre outils demandent `languageIsoCode: FR` par défaut ; tu peux choisir une autre langue ISO 639-1. Le français n’est pas disponible pour tous les pays ; les traductions dépendent de la source. Les régions renvoyées sont celles pertinentes pour les calendriers, sans promesse d’exhaustivité administrative. La couverture varie par pays et type de calendrier ; ce connecteur comprend aussi les pays hors Europe disponibles dans la source.

Description officielle OpenAPI **3.0.4** conservée intacte. Elle exige les deux dates mais n’exprime pas leur écart maximal : la [documentation des erreurs](https://www.openholidaysapi.org/en/errors/) confirme la limite de trois ans. Le transport vérifie les dates civiles, leur ordre et cette durée avant réseau, y compris les années bissextiles. Aucun filtre de groupe ni outil mondial par date n’est exposé.

### taux-de-change

| Outil | Ce qu’il fait | Limite |
|---|---|---|
| `taux_de_change` | Choisis `base` et obligatoirement `quotes` (par exemple `EUR` et `CHF,USD`), avec `date` facultative. | 1 appel/seconde ; cibles obligatoires, pas de séries de dates. |
| `taux_entre_devises` | Choisis `base` et `quote`, avec `date` facultative. | Même cadence partagée. |
| `devises_disponibles` | Consulte les devises ; `scope: all` inclut les anciennes. | Même cadence partagée. |

**Taux de référence indicatif, pas un cours de banque.** Sans date, tu reçois le dernier taux disponible, qui peut dater d’un jour ouvré précédent. Frankfurter annonce l’absence de quota journalier ou mensuel, avec protection contre les abus ; le connecteur limite sa cadence à 1 appel/seconde. Les champs `providers`, `from`, `to`, `group` et `expand` sont exclus ; aucun outil de fournisseurs n’est exposé. Les devises cibles sont requises aussi dans le transport HTTP, pas seulement dans le schéma MCP.

Données : [taux agrégés Frankfurter librement utilisables, y compris commercialement](https://frankfurter.dev/). Pas de licence de données distincte nommée ; MIT concerne le code. Les requêtes directes aux fournisseurs sont exclues de ce connecteur.

## Brancher dans Hermès

Dans ta configuration Hermès, remplace chaque chemin `/chemin/absolu/services-publics/.venv/bin/python` par celui de ton installation. Tu peux garder les huit entrées ou seulement celles qui t'intéressent.

```yaml
mcp_servers:
  services-publics-adresse:
    command: /chemin/absolu/services-publics/.venv/bin/python
    args: ["-m", "nexaura_services_publics", "adresse"]
    tools:
      include: [chercher_adresse, adresse_depuis_position]
  services-publics-geo:
    command: /chemin/absolu/services-publics/.venv/bin/python
    args: ["-m", "nexaura_services_publics", "geo"]
    tools:
      include: [chercher_communes, commune_par_code, departements, regions]
  services-publics-jours-feries:
    command: /chemin/absolu/services-publics/.venv/bin/python
    args: ["-m", "nexaura_services_publics", "jours-feries"]
    tools:
      include: [jours_feries]
  services-publics-calendrier-scolaire:
    command: /chemin/absolu/services-publics/.venv/bin/python
    args: ["-m", "nexaura_services_publics", "calendrier-scolaire"]
    tools:
      include: [vacances_scolaires]
  services-publics-bodacc:
    command: /chemin/absolu/services-publics/.venv/bin/python
    args: ["-m", "nexaura_services_publics", "bodacc"]
    tools:
      include: [annonces_entreprise]
  services-publics-tva-europe:
    command: /chemin/absolu/services-publics/.venv/bin/python
    args: ["-m", "nexaura_services_publics", "tva-europe"]
    tools:
      include: [verifier_tva, etat_service_tva]
  services-publics-jours-feries-europe:
    command: /chemin/absolu/services-publics/.venv/bin/python
    args: ["-m", "nexaura_services_publics", "jours-feries-europe"]
    tools:
      include: [jours_feries, vacances_scolaires_europe, pays, regions_du_pays]
  services-publics-taux-de-change:
    command: /chemin/absolu/services-publics/.venv/bin/python
    args: ["-m", "nexaura_services_publics", "taux-de-change"]
    tools:
      include: [taux_de_change, taux_entre_devises, devises_disponibles]
```

## Calendrier scolaire : filtre natif

L'outil officiel de consultation prend un filtre `where`. Il reste exposé tel quel, avec une forme limitée à une zone et une année scolaire :

```json
{"where": "zones = 'Zone A' AND annee_scolaire = '2026-2027'", "limit": 100, "offset": 0}
```

Utilise `Zone A`, `Zone B`, `Zone C`, ou le libellé exact de la zone publié par le ministère (Corse et outre-mer). L'outil ne traduit pas les noms des territoires. La présence de chaque zone et de chaque année dépend du jeu officiel : une réponse vide ne prouve pas l'absence de vacances.
Le jeu est fixé à `fr-en-calendrier-scolaire` dans le chemin ; tu ne peux pas consulter d'autres jeux. Les périodes peuvent se répéter par académie. La réponse conserve les enregistrements officiels sans les fusionner.

Si tu veux deux champs simples `zone` et `annee_scolaire`, il faut soit une description officielle spécialisée, soit autoriser une petite adaptation manuelle. Ici, aucun faux paramètre ni conversion maison en requête n'est ajouté.

## Limites connues

- Les quotas de l'Adresse et de Geo sont de 50 appels/seconde/IP ; chaque processus espace ses appels à 40/seconde, sans rafale. Les fiches data.gouv des deux calendriers donnent `rate_limiting: null` : quota officiel **non communiqué**, cadence locale prudente de 1/seconde. Aucun quota journalier n'est connu. Plusieurs processus ou logiciels sur la même IP doivent partager ce budget de leur côté.
- Chaque connecteur ne contacte que sa base HTTPS fixe, en GET, sur les chemins autorisés. Pas de redirection ni de proxy hérité de l'environnement ni de vérification de mise à jour FastMCP. Seule exception aux appels sans relance : VIES, pour les deux codes documentés ci-dessus. Délai d'attente HTTP : 15 secondes par phase (comportement httpx), pas une échéance totale de l'opération ; l'attente du limiteur s'y ajoute.
- Adresse reste sur l'index BAN `address`. Geo demande du JSON et une géométrie de centre par défaut ; tu peux demander un contour explicitement si le paramètre officiel le permet.
- Au-delà de **200 000 octets décompressés**, la lecture s'arrête. Tu reçois une enveloppe JSON avec `avertissement: réponse tronquée` et un `extrait` UTF-8. Cet extrait est du texte, pas un objet JSON partiel utilisable comme une réponse complète. L'enveloppe elle-même reste sous 200 Ko ; réduis la recherche ou consulte la page suivante.
- Calendrier scolaire : 100 enregistrements par défaut, pas de pagination automatique. Si `total_count` dépasse le nombre renvoyé, utilise `offset`. Les autres filtres génériques de l'API sont retirés de cet outil.
- Aucun schéma de sortie MCP : les descriptions publiques sont imprécises. Les réponses JSON sont conservées, y compris les valeurs nulles. FastMCP enveloppe les tableaux HTTP dans `result.data["result"]` côté client Python.
- Normalisations de syntaxe avant fabrication : codes HTTP YAML numériques convertis en chaînes ; le type non standard `any` de la description Éducation devient un schéma libre `{}`. Les originaux restent intacts. Geo, fourni en Swagger 2.0, a été converti avec **swagger2openapi 7.0.8** ; Éducation est déjà en **OpenAPI 3.0.3**.
- Tests réels : seule la zone A 2026-2027 a été vérifiée pour le calendrier scolaire ; Corse et outre-mer ne sont pas vérifiés. Les réponses dépendent de la disponibilité et des données de chaque éditeur.
- Deux avertissements de dépréciation Authlib peuvent apparaître avec les dépendances transitives actuelles ; les trois dépendances directes sont épinglées, les transitives ne sont pas verrouillées.

Les URL, dates, empreintes et commandes de conversion sont dans [specs/SOURCES.md](specs/SOURCES.md). Le code est sous [licence MIT](LICENSE), les données gardent leur propre licence.

## Vérifier

```sh
.venv/bin/python -m pytest -q
BANC_RESEAU=1 .venv/bin/python -m pytest -q -m reseau
```

Le premier passage n’accède pas au réseau et saute les huit tests réels. Le second fait un appel d’outil par connecteur : adresse Ségur, Paris 75056, jours fériés métropole 2026, vacances zone A 2026-2027, BODACC SIREN 444608442, VIES FR 40444608442 (forme de réponse et booléen, aucun verdict imposé), jours fériés OpenHolidays BE du 2026-01-01 au 2026-12-31 et EUR vers CHF. Pas de pagination ; seule VIES peut faire une seconde requête dans les deux cas prévus. Les autres outils sont vérifiés avec des réponses simulées, pas par des appels réels. Les cadences et le verrou sont locaux à un serveur : plusieurs processus doivent coordonner leur budget.

Pour vérifier uniquement OpenHolidays (un seul appel GET, sans relance) :

```sh
BANC_RESEAU=1 .venv/bin/python -m pytest -q -m reseau -k europe
```

Le cas réseau TVA porte l’identifiant `vies` pour que ce filtre ne contacte qu’OpenHolidays.
