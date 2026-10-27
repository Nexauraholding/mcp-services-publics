"""Reproduit les seuls manifestes locaux ; aucun téléchargement."""
from pathlib import Path
import yaml
P = Path(__file__).parent

def op(path, name, desc, **kwargs):
    return dict(methode='GET', chemin=path, nom=name, description=desc, **kwargs)

configs = {
'adresse': dict(description='specs/adresse.openapi.yaml', base='https://data.geopf.fr/geocodage',
 quota=dict(officiel='50 appels / seconde / IP', client_appels_seconde=40,
 affichage='50 appels/seconde/IP ; ce connecteur se limite à 40 appels/seconde.',
 source='https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/geocodage/'),
 licence='Licence Ouverte 2.0 (BAN, index address uniquement)',
 licence_source='https://adresse.data.gouv.fr/outils/api-doc/adresse',
 operations=[op('/search','chercher_adresse','Cherche une adresse avec q et renvoie ses coordonnées et les adresses proposées.'),
 op('/reverse','adresse_depuis_position','Donne lon et lat : tu reçois les adresses proches de cette position.')]),
'geo': dict(description='specs/geo.converti.openapi.json', base='https://geo.api.gouv.fr',
 quota=dict(officiel='50 appels / seconde / IP', client_appels_seconde=40,
 affichage='50 appels/seconde/IP ; ce connecteur se limite à 40 appels/seconde.',
 source='https://www.data.gouv.fr/dataservices/api-decoupage-administratif-api-geo'),
 licence='Licence Ouverte 2.0 (données administratives INSEE) ; sources géographiques sous licences Open Data',
 licence_source='https://geo.api.gouv.fr/decoupage-administratif',
 operations=[op('/communes','chercher_communes','Cherche avec nom ou codePostal : tu reçois les communes correspondantes.'),
 op('/communes/{code}','commune_par_code','Donne un code INSEE : tu reçois les informations de cette commune.'),
 op('/departements','departements','Consulte les départements : tu reçois leurs noms et codes.'),
 op('/regions','regions','Consulte les régions : tu reçois leurs noms et codes.')]),
'jours-feries': dict(description='specs/jours-feries.openapi.yml', base='https://calendrier.api.gouv.fr/jours-feries/',
 quota=dict(officiel=None,client_appels_seconde=1,
 affichage='quota officiel non communiqué ; cadence locale de 1 appel/seconde.',
 source='https://www.data.gouv.fr/api/1/dataservices/?q=jours%20f%C3%A9ri%C3%A9s'),
 licence='Licence Ouverte 2.0', licence_source='https://www.data.gouv.fr/datasets/jours-feries-en-france',
 operations=[op('/{zone}/{annee}.json','jours_feries','Choisis une zone et une année : tu reçois les dates et les noms des jours fériés.')]),
'calendrier-scolaire': dict(description='specs/calendrier-scolaire.original.json',base='https://data.education.gouv.fr/api/explore/v2.0',
 quota=dict(officiel=None,client_appels_seconde=1,
 affichage='quota officiel non communiqué ; cadence locale de 1 appel/seconde.',
 source='https://www.data.gouv.fr/api/1/dataservices/?q=calendrier%20scolaire'),
 licence='Licence Ouverte 2.0',licence_source='https://www.data.gouv.fr/datasets/le-calendrier-scolaire',
 operations=[op('/catalog/datasets/{dataset_id}/records','vacances_scolaires',
 'Consulte les vacances du calendrier scolaire officiel pour ta zone et ton année scolaire. Dans where, écris par exemple : zones = \'Zone A\' AND annee_scolaire = \'2026-2027\' ; tu reçois les périodes et académies, parfois répétées.',
 chemin_fixe='/catalog/datasets/fr-en-calendrier-scolaire/records',
 retirer_parametres=['dataset_id','select','group_by','order_by','refine','exclude','lang','timezone'],
 parametres={'where':{'required':True,'schema':{'pattern':"^zones = '[^']+' AND annee_scolaire = '[0-9]{4}-[0-9]{4}'$"}},
 'limit':{'schema':{'minimum':1,'maximum':100,'default':100}}})])}
for c in configs.values():
 if c['base'].startswith('https://data.geopf'):
  for o in c['operations']:
   o['parametres']={'index':{'schema':{'type':'string','enum':['address'],'default':'address'}}}
 if c['base']=='https://geo.api.gouv.fr':
  for o in c['operations']:
   o['parametres']={'format':{'schema':{'default':'json'}},'geometry':{'schema':{'default':'centre'}}}
for nom,c in configs.items():
 (P/'connecteurs'/f'{nom}.yaml').write_text(yaml.safe_dump(c,allow_unicode=True,sort_keys=False))
