# Sources figées le 2026-10-27

| Fichier | Source | Date | SHA256 |
|---|---|---|---|
| adresse.openapi.yaml | https://data.geopf.fr/geocodage/openapi.yaml | 2026-10-27 | `90d83f1353b6c4e6e0813a747bf0d338a315f5727f37ccf773e8b2e3a9ed093a` |
| geo.openapi.yml | https://geo.api.gouv.fr/definition.yml | 2026-10-27 | `287cad99fe8a57ce4b562bf0e77adc6706fbefc8fb8c856115785d9c48fd76c4` |
| geo.converti.openapi.json | Conversion locale de geo.openapi.yml | 2026-10-27 | `f474aac0d059332b2f998b0cb6c161285ee494a49b0bdac5dcea4969628e7071` |
| jours-feries.openapi.yml | Copie du banc ../openapi-banc/specs/jours-feries.openapi.yml ; origine https://github.com/etalab/calendrier.api.gouv.fr/blob/master/openapi.yml | 2026-10-27 | `64694331d79465280d61fe1413b58cb3ca09515188353e7faaf4a0fb588681e7` |
| calendrier-scolaire.original.json | https://data.education.gouv.fr/api/v2/swagger.json | 2026-10-27 | `10add39cb2f6e4d41aac4ab1457f2b3cf55ed6a638e8597481452d19fad0a3ca` |
| bodacc.original.json | https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/swagger.json | 2026-10-27 | `7034cc4930907da7f5893514b1c80550959645965d61e8bf33e2e7c4e04fb002` |
| tva-europe.openapi.yaml | description écrite par NexAura d’après la doc officielle : https://ec.europa.eu/taxation_customs/vies/#/technical-information | 2026-10-27 | `9ff3e4d50c25db26a4b56f2a8caafac2a6c9d65fbb38ef5aa153674edeead277` |
| tva-europe.documentation.json | Contenu officiel de la page technique : https://ec.europa.eu/taxation_customs/vies/rest-api/technicalInformation/CONTENT | 2026-10-27 | `40ec55c6115516d6b3627662d9dcd3d5f4753a193b40e1c2432e7a5dd73c08d5` |
| tva-europe.reference-officielle.yaml | Référence officielle POST + état GET : https://ec.europa.eu/assets/taxud/vow-information/swagger_publicVAT.yaml | 2026-10-27 | `f8e15e184c009da31bcceb01be494aaf79cbb6b8f770c1ec680695eadd8848d5` |
| jours-feries-europe.openapi.json | https://openholidaysapi.org/swagger/v1/swagger.json | 2026-10-27 | `5af1c4e33e6b9cd77eec094aa85ab68c067584006d945adda03c2d28caa17ac6` |
| taux-de-change.openapi.json | https://api.frankfurter.dev/v2/openapi.json | 2026-10-27 | `2f3e6a4012b8461401e462237ef4f5122fd6cf71b766db948fe86fd696745fe4` |

Les descriptions distantes ont été téléchargées une seule fois. Les jours fériés sont copiés du banc autorisé, sans retéléchargement.

## Formats et conversion

Adresse : OpenAPI 3.1.0. Éducation : **OpenAPI 3.0.3**, aucune conversion nécessaire.
Geo : Swagger 2.0, converti avec **swagger2openapi 7.0.8**, outil libre BSD-3-Clause (https://github.com/Mermade/oas-kit).
Commande depuis ce dossier :

```sh
npm install --prefix .conversion --cache .conversion/cache --no-audit --no-fund swagger2openapi@7.0.8
.conversion/node_modules/.bin/swagger2openapi specs/geo.openapi.yml -o specs/geo.converti.openapi.json
```

## Quotas et licences consultés le 2026-10-27

- Adresse : https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/geocodage/ : 50 appels/s/IP. BAN : Licence Ouverte 2.0, https://adresse.data.gouv.fr/outils/api-doc/adresse . L'index est limité à `address`.
- Geo : https://www.data.gouv.fr/dataservices/api-decoupage-administratif-api-geo : 50 appels/s/IP ; sources sous licences Open Data. Données administratives INSEE sous Licence Ouverte 2.0 ; voir https://geo.api.gouv.fr/decoupage-administratif . Pas de contours demandés par défaut.
- Jours fériés : https://www.data.gouv.fr/api/1/dataservices/?q=jours%20f%C3%A9ri%C3%A9s : `rate_limiting: null`. Quota non communiqué. Licence Ouverte 2.0 : https://www.data.gouv.fr/datasets/jours-feries-en-france .
- Calendrier scolaire : https://www.data.gouv.fr/api/1/dataservices/?q=calendrier%20scolaire : `rate_limiting: null`. Quota non communiqué. Licence Ouverte 2.0 : https://www.data.gouv.fr/datasets/le-calendrier-scolaire .

Aucune limite officielle n'est inventée lorsque la fiche n'en donne pas. Cadence conservatrice de 1 appel/s dans ces deux cas, sans garantie face à un éventuel quota journalier inconnu.

## Projection déclarative du calendrier

L'opération officielle `GET /catalog/datasets/{dataset_id}/records` fournit les paramètres natifs `where`, `limit`, `offset`.
Le YAML fixe `dataset_id` dans le chemin, retire les options inutiles et exige un filtre `where` égalité zone ET année scolaire (syntaxe native OD SQL).
Aucune fonction d'outil manuelle et aucun faux paramètre zone/année n'est ajouté. Le chemin d'origine reste enregistré dans le YAML.
L'outil n'est donc pas une interface à deux champs simples : si cette interface est indispensable, il faut autoriser une petite adaptation manuelle ou demander une description spécialisée à l'éditeur.


## Quatre connecteurs supplémentaires

- **BODACC** : description reçue en OpenAPI **3.0.3**, donc aucune conversion Swagger. Les champs `registre` (texte multivalué) et `dateparution` (date, triable) ont été vérifiés dans https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales le 2026-10-27. Même projection déclarative que le calendrier scolaire : chemin fixé au jeu `annonces-commerciales`, filtre natif `where` restreint à `registre = 'SIREN'`, tri `dateparution DESC`, limite entre 1 et 20, défaut 20, offset entre 0 et 9980. Licence **fr-lo / Licence Ouverte** (ne pas lui attribuer arbitrairement la version 2.0) : https://www.data.gouv.fr/datasets/bodacc ; accès API gratuit : https://www.bodacc.fr/pages/donnees-ouvertes-et-api/ . Quota chiffré non trouvé : cadence locale de 1/s.
- **VIES** : **description écrite par NexAura d'après la doc officielle**, OpenAPI **3.0.3**, deux GET seulement. La page demandée propose désormais un Swagger 2.0 officiel (`tva-europe.reference-officielle.yaml`), mais il décrit le contrôle de TVA en POST. Le GET `/ms/{countryCode}/vat/{vatNumber}` est celui utilisé par le client web officiel (code `CHECK_VAT="ms/{msCode}/vat/{vatNumber}"` dans https://ec.europa.eu/taxation_customs/vies/app/main.357206a88a995527.js, inspecté le 2026-10-27). Le fichier de référence est archivé comme preuve documentaire et n’est pas chargé par le connecteur. La vérification GET renvoie `isValid`, alors que la description POST emploie `valid`. Aucune licence ouverte uniforme des réponses nationales n’est annoncée : https://ec.europa.eu/taxation_customs/vies/#/disclaimer . Quota chiffré non annoncé : 1/s local et un verrou couvrant tous les outils, y compris lecture et éventuelle relance après 3 s ; exactement une seconde tentative sur les valeurs JSON exactes `MS_UNAVAILABLE` et `MS_MAX_CONCURRENT_REQ`, aucune autre.
- **OpenHolidays API** : description officielle **OpenAPI 3.0.4**, conservée sans conversion ; base fixe https://openholidaysapi.org . Données **ODbL-1.0**, https://github.com/openpotato/openholidaysapi.data . La FAQ https://www.openholidaysapi.org/en/faq/ autorise explicitement l’accès gratuit et les projets commerciaux. Aucun quota chiffré trouvé dans la FAQ ou https://www.openholidaysapi.org/en/ : cadence locale de 1/s, aucun quota journalier garanti. Attribution dans chaque outil : « Données OpenHolidays API (ODbL) » ; conserver l’attribution et respecter les obligations ODbL de réutilisation et de partage des bases dérivées. Seuls GET /PublicHolidays, /SchoolHolidays, /Countries et /Subdivisions sont exposés. Paramètres natifs conservés ; countryIsoCode obligatoire sauf pour /Countries, dates validFrom et validTo obligatoires pour les calendriers, subdivisionCode facultatif, languageIsoCode par défaut FR (traductions selon disponibilité). groupCode retiré. La description ne contient aucune contrainte de durée entre les dates ; https://www.openholidaysapi.org/en/errors/ confirme le refus des périodes de plus de trois ans. La projection YAML déclare cette contrainte et le transport la vérifie avant réseau (dates civiles, ordre et comparaison calendaire, années bissextiles comprises). Un seul appel réel : Belgique du 2026-01-01 au 2026-12-31 ; autres outils et limites testés hors réseau.
- **Frankfurter** : OpenAPI **3.1.2**, conservé sans conversion. Conditions https://frankfurter.dev/ (consultées le 2026-10-27) : taux agrégés librement utilisables, y compris commercialement ; pas de licence de données distincte nommée (MIT concerne le code). Pas de plafond journalier/mensuel annoncé, protection contre les abus, cadence locale 1/s. Seuls `/rates`, `/rate/{base}/{quote}` et `/currencies` sont autorisés. `base` et `quotes` obligatoires pour `/rates` ; aucun intervalle de dates ni filtre fournisseur. Taux de référence indicatif, pas un cours de banque.

Les descriptions locales ne sont pas des copies spécialisées inventant des paramètres : les trois descriptions téléchargées restent intactes. Les changements d’interface sont uniquement les projections YAML. `ajouter_connecteurs.py` reproduit les quatre nouveaux manifestes et la description VIES écrite localement, sans téléchargement. Les limites des paramètres sont également vérifiées dans le transport HTTP, avant accès réseau.
