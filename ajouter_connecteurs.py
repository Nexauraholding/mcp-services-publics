"""Reproduit les quatre manifestes supplémentaires, sans téléchargement."""
from pathlib import Path
import yaml
def op(path, name, desc, **kwargs):
    return dict(methode='GET', chemin=path, nom=name, description=desc, **kwargs)
P = Path(__file__).parent

def quota(texte=None):
    return dict(officiel=None, client_appels_seconde=1,
                affichage=texte or 'quota officiel non communiqué ; cadence locale de 1 appel/seconde.')

def param(type='string', **schema):
    return {'schema': dict(type=type, **schema)}

configs = {
'bodacc': dict(description='specs/bodacc.original.json',
 base='https://bodacc-datadila.opendatasoft.com/api/explore/v2.1',
 quota=quota('quota officiel non communiqué ; 1 appel/seconde, 20 annonces au maximum par appel, tri récent imposé.'),
 requete_stricte=True, licence='Licence Ouverte / Open Licence (fr-lo)',
 licence_source='https://www.data.gouv.fr/datasets/bodacc',
 operations=[op('/catalog/datasets/{dataset_id}/records', 'annonces_entreprise',
 "Consulte les annonces de ton entreprise, de la plus récente à la plus ancienne. Donne un SIREN dans where, par exemple : registre = '444608442'. Tu reçois au plus 20 annonces ; utilise offset pour la suite.",
 chemin_fixe='/catalog/datasets/annonces-commerciales/records',
 retirer_parametres=['dataset_id','select','group_by','refine','exclude','lang','timezone','include_links','include_app_metas'],
 parametres={'where':dict(required=True, **param(pattern="^registre = '[0-9]{9}'$")),
 'order_by':param(enum=['dateparution DESC'], default='dateparution DESC'),
 'limit':param('integer',minimum=1,maximum=20,default=20),
 'offset':param('integer',minimum=0,maximum=9980,default=0)})]),
 'tva-europe':dict(description='specs/tva-europe.openapi.yaml',
 base='https://ec.europa.eu/taxation_customs/vies/rest-api',
 quota=quota('quota officiel chiffré non communiqué ; 1 appel/seconde et une requête à la fois ; sur MS_UNAVAILABLE ou MS_MAX_CONCURRENT_REQ, une seule nouvelle tentative après 3 s.'),
 requete_stricte=True, une_a_la_fois=True,
 reprise=dict(codes=['MS_UNAVAILABLE','MS_MAX_CONCURRENT_REQ'],delai_secondes=3),
 licence='Conditions VIES et droits des administrations nationales ; aucune licence ouverte uniforme annoncée pour les données',
 licence_source='https://ec.europa.eu/taxation_customs/vies/#/disclaimer',
 operations=[op('/ms/{countryCode}/vat/{vatNumber}','verifier_tva',
 "Vérifie ton numéro de TVA avec countryCode et vatNumber sans le préfixe pays. Pour la France, le nom et l’adresse reviennent souvent vides : tu obtiens surtout « valide » ou « non valide ». Une indisponibilité ne signifie pas « non valide ».",
 parametres={'countryCode':param(pattern='^[A-Z]{2}$'),'vatNumber':param(pattern='^[A-Z0-9]{2,14}$')}),
 op('/check-status','etat_service_tva','Consulte la disponibilité de VIES et des services des pays.',parametres={})]),
 'jours-feries-europe':dict(description='specs/jours-feries-europe.openapi.json',
 base='https://openholidaysapi.org', quota=quota(), requete_stricte=True,
 licence='ODbL-1.0 — Données OpenHolidays API (ODbL)',
 licence_source='https://github.com/openpotato/openholidaysapi.data',
 operations=[
 op(path, name, desc + ' Données OpenHolidays API (ODbL).',
    **(dict(periode_dates=dict(debut='validFrom', fin='validTo', maximum_annees=3),
            retirer_parametres=['groupCode']) if calendrier else {}),
    parametres={
        **({'countryIsoCode':dict(required=True, **param(pattern='^[A-Z]{2}$'))}
           if path != '/Countries' else {}),
        'languageIsoCode':param(pattern='^[A-Za-z]{2}$', default='FR'),
        **({'validFrom':dict(required=True, **param(format='date', pattern='^[0-9]{4}-[0-9]{2}-[0-9]{2}$')),
            'validTo':dict(required=True, **param(format='date', pattern='^[0-9]{4}-[0-9]{2}-[0-9]{2}$')),
            'subdivisionCode':param(minLength=1)} if calendrier else {})})
 for path, name, desc, calendrier in [
 ('/PublicHolidays','jours_feries','Choisis countryIsoCode, validFrom et validTo (AAAA-MM-JJ), sur trois ans au maximum ; subdivisionCode est facultatif, languageIsoCode vaut FR par défaut (traduction selon disponibilité).',True),
 ('/SchoolHolidays','vacances_scolaires_europe','Choisis countryIsoCode, validFrom et validTo (AAAA-MM-JJ), sur trois ans au maximum ; subdivisionCode est facultatif, languageIsoCode vaut FR par défaut (traduction selon disponibilité).',True),
 ('/Countries','pays','Consulte les pays disponibles ; languageIsoCode vaut FR par défaut (traduction selon disponibilité).',False),
 ('/Subdivisions','regions_du_pays','Donne countryIsoCode pour consulter les régions pertinentes ; languageIsoCode vaut FR par défaut (traduction selon disponibilité).',False)]]),
 'taux-de-change':dict(description='specs/taux-de-change.openapi.json',base='https://api.frankfurter.dev/v2',
 quota=quota('pas de quota journalier ou mensuel annoncé, protection contre les abus ; cadence locale de 1 appel/seconde.'),
 requete_stricte=True,
 licence='Taux agrégés Frankfurter librement utilisables, y compris commercialement ; pas de licence de données distincte nommée (MIT concerne le code)',
 licence_source='https://frankfurter.dev/',
 operations=[op('/rates','taux_de_change',
 'Choisis ta devise de base et obligatoirement les devises cibles dans quotes (séparées par des virgules). Tu reçois les derniers taux disponibles, ou ceux de date : taux de référence indicatif, pas un cours de banque.',
 retirer_parametres=['from','to','providers','group','expand'],
 parametres={'base':dict(required=True,**param(pattern='^[A-Za-z]{3}$')),
 'quotes':dict(required=True,**param(pattern='^[A-Za-z]{3}(,[A-Za-z]{3})*$')),
 'date':param(pattern='^[0-9]{4}-[0-9]{2}-[0-9]{2}$')}),
 op('/rate/{base}/{quote}','taux_entre_devises',
 'Choisis tes deux devises et éventuellement date : tu reçois un taux de référence indicatif, pas un cours de banque.',
 retirer_parametres=['providers'],parametres={'base':param(pattern='^[A-Za-z]{3}$'),'quote':param(pattern='^[A-Za-z]{3}$'), 'date':param(pattern='^[0-9]{4}-[0-9]{2}-[0-9]{2}$')}),
 op('/currencies','devises_disponibles','Consulte les devises que tu peux utiliser ; scope=all inclut les anciennes devises.',
 retirer_parametres=['providers'],parametres={'scope':param(enum=['all'])})])}
for nom,c in configs.items():
 (P/'connecteurs'/f'{nom}.yaml').write_text(yaml.safe_dump(c,allow_unicode=True,sort_keys=False))

# Description volontairement écrite ici : aucun outil Python métier.
spec={'openapi':'3.0.3','info':{'title':'VIES — description NexAura des GET','version':'2026-10-27',
 'description':'Description écrite par NexAura d’après la documentation officielle VIES. Nom et adresse souvent vides en France ; le verdict est surtout valide ou non valide.'},
 'servers':[{'url':configs['tva-europe']['base']}], 'paths':{}}
for o in configs['tva-europe']['operations']:
 parameters=[{'name':n,'in':'path','required':True,**v} for n,v in o['parametres'].items()]
 spec['paths'][o['chemin']]={'get':{'operationId':o['nom'],'description':o['description'], 'parameters':parameters,
 'responses':{'200':{'description':('Réponse VIES JSON ; isValid est un booléen (GET) pour une vérification réussie. Les erreurs ne sont pas un verdict.' if o['nom']=='verifier_tva' else 'Disponibilité de VIES dans vow.available et des services nationaux dans countries.'),
 'content':{'application/json':{'schema':{'type':'object','additionalProperties':True}}}},
 '400':{'description':'Requête invalide'},'403':{'description':'Service indisponible ou limite atteinte ; erreur JSON'},'500':{'description':'Erreur VIES'}}}}
(P/'specs/tva-europe.openapi.yaml').write_text(yaml.safe_dump(spec,allow_unicode=True,sort_keys=False))
