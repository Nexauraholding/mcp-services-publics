import asyncio
import copy
import json
import os
import re

import httpx
import pytest
from fastmcp import Client
from nexaura_services_publics import (
    NOMS, RACINE, MAX_OCTETS, TITRES, USER_AGENT, ClientPublic, Limiteur,
    charger, configuration, fabriquer,
)


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize('nom', NOMS)
def test_outils_exacts_et_origine_get(nom):
    async def scenario():
        config = configuration(nom)
        source = charger(RACINE / config['description'])
        s = fabriquer(nom)
        try:
            tools = await s.get_tools()
            assert set(tools) == {op['nom'] for op in config['operations']}
            for op in config['operations']:
                t = tools[op['nom']]
                assert re.fullmatch('[a-z_]+', t.name)
                assert 'get' in source['paths'][op['chemin']]
                assert op['methode'] == t._route.method.upper() == 'GET'
                assert t._route.path == op.get('chemin_fixe', op['chemin'])
                assert 'Limite :' in t.description
                assert t.output_schema is None
        finally:
            await s.client_public.aclose()
    run(scenario())


@pytest.mark.parametrize('nom', NOMS)
def test_annotations_lecture_seule(nom):
    async def scenario():
        server = fabriquer(nom)
        async with Client(server) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools} == {
                op['nom'] for op in configuration(nom)['operations']
            }
            for tool in tools:
                assert tool.annotations is not None
                assert tool.annotations.title == TITRES[tool.name]
                assert tool.annotations.readOnlyHint is True
                assert tool.annotations.destructiveHint is False
                assert tool.annotations.idempotentHint is True
                assert tool.annotations.openWorldHint is True
    run(scenario())


def test_mixte():
    c = copy.deepcopy(configuration('geo'))
    c['operations'] = [dict(methode='GET', chemin='/communes', nom='chercher_communes', description='Cherche ta commune.')]
    s = {'openapi':'3.0.3','info':{'title':'mixte','version':'1'},'paths':{
        '/communes': {method:{'operationId':method,'responses':{'200':{'description':'OK'}}} for method in ('get','post','delete')},
        '/interdit': {'get':{'operationId':'interdit','responses':{'200':{'description':'OK'}}}}}}
    async def scenario():
        server = fabriquer('geo', spec=s, config=c)
        try:
            assert list(await server.get_tools()) == ['chercher_communes']
        finally:
            await server.client_public.aclose()
    run(scenario())


def test_limiteur_horloge_simulee():
    async def scenario():
        maintenant = [0.0]
        async def dormir(duree):
            maintenant[0] += duree
        limiteur = Limiteur(4, lambda: maintenant[0], dormir)
        await asyncio.gather(*(limiteur.attendre() for _ in range(9)))
        assert maintenant[0] >= (9 - 1) / 4
    run(scenario())


@pytest.mark.parametrize('taille', [MAX_OCTETS, MAX_OCTETS + 1, MAX_OCTETS * 3])
def test_troncature(taille):
    async def scenario():
        contenu = ('é"\\\n' * taille).encode()[:taille]
        def repondre(request):
            return httpx.Response(200, content=contenu)
        async with ClientPublic(configuration('geo'), transport=httpx.MockTransport(repondre)) as client:
            r = await client.get('/communes')
            assert len(r.content) <= MAX_OCTETS
            if taille > MAX_OCTETS:
                assert r.json()['avertissement'] == 'réponse tronquée'
            else:
                assert r.content == contenu
    run(scenario())


@pytest.mark.parametrize('url,methode', [
    ('https://example.org/communes','GET'),
    ('https://geo.api.gouv.fr/communes','POST'),
    ('https://geo.api.gouv.fr/epcis','GET'),
    ('http://geo.api.gouv.fr/communes','GET'),
])
def test_destination_verrouillee(url, methode):
    async def scenario():
        def interdit(_):
            pytest.fail('Le transport ne doit pas être appelé')
        async with ClientPublic(configuration('geo'), transport=httpx.MockTransport(interdit)) as client:
            with pytest.raises(ValueError):
                await client.request(methode, url)
    run(scenario())


def test_redirection_non_suivie():
    async def scenario():
        appels = []
        def repondre(request):
            appels.append(request)
            assert request.headers['user-agent'] == USER_AGENT
            assert request.extensions['timeout']['read'] == 15
            return httpx.Response(302, headers={'location':'https://example.org/'})
        async with ClientPublic(configuration('geo'), transport=httpx.MockTransport(repondre)) as c:
            assert (await c.get('/communes')).status_code == 302
        assert len(appels) == 1
    run(scenario())


@pytest.mark.parametrize('nom,outils,args', [
    ('adresse','chercher_adresse',{'q':'20 avenue de Ségur Paris'}),
    ('geo','commune_par_code',{'code':'75056'}),
    ('jours-feries','jours_feries',{'zone':'metropole','annee':2026}),
    ('calendrier-scolaire','vacances_scolaires',{'where':"zones = 'Zone A' AND annee_scolaire = '2026-2027'",'limit':100}),
    ('bodacc','annonces_entreprise',{'where':"registre = '444608442'"}),
    pytest.param('tva-europe','verifier_tva',{'countryCode':'FR','vatNumber':'40444608442'}, id='vies'),
    ('jours-feries-europe','jours_feries',{'countryIsoCode':'BE','validFrom':'2026-01-01','validTo':'2026-12-31'}),
    ('taux-de-change','taux_de_change',{'base':'EUR','quotes':'CHF'}),
])
@pytest.mark.reseau
@pytest.mark.skipif(os.environ.get('BANC_RESEAU') != '1', reason='BANC_RESEAU != 1')
def test_reel_unique(nom, outils, args):
    async def scenario():
        s = fabriquer(nom)
        # Un appel métier ; seule VIES peut relancer une fois selon sa politique.
        async with Client(s) as client:
            result = await client.call_tool(outils, args)
            assert not result.is_error
            data = result.data
            assert data
            if nom == 'geo':
                assert data['code'] == '75056'
            elif nom == 'adresse':
                assert data['features']
            elif nom == 'jours-feries':
                assert data['2026-01-01']
            elif nom == 'calendrier-scolaire':
                assert data['total_count'] > 0
                assert data['records']
            elif nom == 'bodacc':
                assert data['total_count'] > 0
                rows = data['results']
                assert 0 < len(rows) <= 20
                assert all('444608442' in row['registre'] for row in rows)
                dates = [r['dateparution'] for r in rows]
                assert dates == sorted(dates, reverse=True)
            elif nom == 'tva-europe':
                assert isinstance(data, dict)
                assert type(data['isValid']) is bool
            elif nom == 'jours-feries-europe':
                data = data['result']  # Enveloppe MCP des réponses HTTP de type tableau.
                assert isinstance(data, list) and data
                assert all('2026-01-01' <= r['startDate'] <= r['endDate'] <= '2026-12-31' for r in data)
                assert any(r['startDate'] == '2026-01-01' for r in data)
            elif nom == 'taux-de-change':
                data = data['result']
                assert isinstance(data, list) and len(data) == 1
                assert data[0]['base'] == 'EUR' and data[0]['quote'] == 'CHF'
                assert data[0]['rate'] > 0
    run(scenario())


@pytest.mark.parametrize('nom,url', [
    ('adresse','https://data.geopf.fr/geocodage/search?index=parcel'),
    ('calendrier-scolaire','https://data.education.gouv.fr/api/explore/v2.0/catalog/datasets/autre/records'),
    ('calendrier-scolaire','https://data.education.gouv.fr/api/explore/v2.0/catalog/datasets/fr-en-calendrier-scolaire/records'),
    ('calendrier-scolaire','https://data.education.gouv.fr/api/explore/v2.0/catalog/datasets/fr-en-calendrier-scolaire/records?where=1%3D1'),
])
def test_specialisation_verrouillee(nom, url):
    async def scenario():
        def interdit(_):
            pytest.fail('Accès réseau interdit')
        async with ClientPublic(configuration(nom), transport=httpx.MockTransport(interdit)) as c:
            with pytest.raises(ValueError):
                await c.get(url)
    run(scenario())


@pytest.mark.parametrize('nom,outil,args', [
    ('adresse','chercher_adresse',{'q':'Paris'}),
    ('geo','commune_par_code',{'code':'75056'}),
    ('jours-feries','jours_feries',{'zone':'metropole','annee':2026}),
    ('calendrier-scolaire','vacances_scolaires',{'where':"zones = 'Zone A' AND annee_scolaire = '2026-2027'"}),
])
def test_transport_mcp_simule(nom, outil, args):
    async def scenario():
        appels = []
        def repondre(request):
            appels.append(request)
            assert request.method == 'GET'
            if nom == 'adresse':
                assert request.url.params['index'] == 'address'
            if nom == 'geo':
                assert request.url.params['format'] == 'json'
                assert request.url.params['geometry'] == 'centre'
            if nom == 'calendrier-scolaire':
                assert '/fr-en-calendrier-scolaire/' in request.url.path
                assert request.url.params['where'] == args['where']
            return httpx.Response(200, json={'valeur':None})
        s = fabriquer(nom, transport=httpx.MockTransport(repondre))
        async with Client(s) as client:
            tools = await client.list_tools()
            assert all(t.outputSchema is None for t in tools)
            resultat = await client.call_tool(outil, args)
            assert resultat.data == {'valeur':None}
        assert len(appels) == 1
    run(scenario())


def test_troncature_via_mcp():
    async def scenario():
        def repondre(_):
            return httpx.Response(200, json={'volumineux':'é' * MAX_OCTETS})
        s = fabriquer('geo', transport=httpx.MockTransport(repondre))
        async with Client(s) as client:
            result = await client.call_tool('commune_par_code', {'code':'75056'})
            assert result.data['avertissement'] == 'réponse tronquée'
    run(scenario())
