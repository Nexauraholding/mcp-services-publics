import asyncio
import hashlib
import re

import httpx
import pytest
from fastmcp import Client
from nexaura_services_publics import RACINE, configuration, fabriquer, ClientPublic

ATTENDUS = {
    'bodacc': {'annonces_entreprise'},
    'tva-europe': {'verifier_tva', 'etat_service_tva'},
    'jours-feries-europe': {'jours_feries', 'vacances_scolaires_europe', 'pays', 'regions_du_pays'},
    'taux-de-change': {'taux_de_change', 'taux_entre_devises', 'devises_disponibles'},
}

@pytest.mark.parametrize('nom', ATTENDUS)
def test_contrat_fixe(nom):
    async def scenario():
        s = fabriquer(nom)
        try:
            tools = await s.get_tools()
            assert set(tools) == ATTENDUS[nom]
            assert configuration(nom)['licence']
            for t in tools.values():
                assert t._route.method.upper() == 'GET'
                assert 'Limite :' in t.description
            if nom == 'taux-de-change':
                assert {'base', 'quotes'} <= set(tools['taux_de_change'].parameters['required'])
        finally:
            await s.client_public.aclose()
    asyncio.run(scenario())

@pytest.mark.parametrize('nom,outil,args', [
    ('bodacc','annonces_entreprise',{'where':"registre = '444608442'"}),
    ('tva-europe','verifier_tva',{'countryCode':'FR','vatNumber':'40444608442'}),
    ('tva-europe','etat_service_tva',{}),
    ('jours-feries-europe','jours_feries',{'countryIsoCode':'BE','validFrom':'2026-01-01','validTo':'2026-12-31'}),
    ('jours-feries-europe','vacances_scolaires_europe',{'countryIsoCode':'BE','validFrom':'2026-01-01','validTo':'2026-12-31','subdivisionCode':'BE-FR','languageIsoCode':'fr'}),
    ('jours-feries-europe','pays',{}),
    ('jours-feries-europe','regions_du_pays',{'countryIsoCode':'BE'}),
    ('taux-de-change','taux_de_change',{'base':'EUR','quotes':'CHF,USD','date':'2026-01-02'}),
    ('taux-de-change','taux_entre_devises',{'base':'EUR','quote':'CHF'}),
    ('taux-de-change','devises_disponibles',{}),
])
def test_transport(nom, outil, args):
    async def scenario():
        appels = []
        def repondre(r):
            appels.append(r)
            assert r.method == 'GET'
            if nom == 'bodacc':
                assert r.url.path.endswith('/annonces-commerciales/records')
                assert r.url.params['where'] == args['where']
                assert r.url.params['limit'] == '20'
                assert r.url.params['order_by'] == 'dateparution DESC'
            if outil == 'taux_de_change':
                assert r.url.params['quotes'] == 'CHF,USD'
                assert r.url.params['date'] == '2026-01-02'
            if nom == 'jours-feries-europe':
                assert dict(r.url.params) == {'languageIsoCode':'FR', **args}
            return httpx.Response(200, json={'valeur':None})
        s = fabriquer(nom, transport=httpx.MockTransport(repondre))
        async with Client(s) as c:
            result = await c.call_tool(outil, args)
            assert result.data == {'valeur':None}
        assert len(appels) == 1
    asyncio.run(scenario())

@pytest.mark.parametrize('nom,chemin,params', [
    ('bodacc','/catalog/datasets/autre/records',{'where':"registre = '444608442'"}),
    ('bodacc','/catalog/datasets/annonces-commerciales/records',{}),
    ('bodacc','/catalog/datasets/annonces-commerciales/records',{'where':'1=1'}),
    ('bodacc','/catalog/datasets/annonces-commerciales/records',{'where':"registre = '444608442'",'limit':21}),
    ('bodacc','/catalog/datasets/annonces-commerciales/records',{'where':"registre = '444608442'",'limit':0}),
    ('bodacc','/catalog/datasets/annonces-commerciales/records',{'where':"registre = '444608442'",'order_by':'dateparution ASC'}),
    ('bodacc','/catalog/datasets/annonces-commerciales/records',{'where':"registre = '444608442'",'select':'*'}),
    ('taux-de-change','/rates',{'base':'EUR'}),
    ('taux-de-change','/rates',{'base':'EUR','quotes':''}),
    ('taux-de-change','/rates',{'base':'EUR','quotes':'CHF','from':'2020-01-01'}),
    ('taux-de-change','/rates',{'base':'EUR','quotes':'CHF','providers':'ecb'}),
    ('taux-de-change','/rates',[('base','EUR'),('quotes','CHF'),('quotes','USD')]),
    ('taux-de-change','/providers',{}),
    ('jours-feries-europe','/Groups',{}),
    ('tva-europe','/ms/FR/vat/123',{'vatNumber':'456'}),
])
def test_limites_avant_reseau(nom, chemin, params):
    async def scenario():
        def interdit(_):
            pytest.fail('Requête interdite transmise')
        async with ClientPublic(configuration(nom), transport=httpx.MockTransport(interdit)) as c:
            with pytest.raises(ValueError):
                await c.get(chemin, params=params)
    asyncio.run(scenario())

@pytest.mark.parametrize('code,http_status,attendu', [
    ('MS_UNAVAILABLE',200,2), ('MS_UNAVAILABLE',403,2),
    ('MS_MAX_CONCURRENT_REQ',500,2), ('GLOBAL_MAX_CONCURRENT_REQ',403,1),
    ('TIMEOUT',500,1), ('SERVICE_UNAVAILABLE',500,1),
])
def test_reprise_vies_bornee(code, http_status, attendu, monkeypatch):
    async def scenario():
        appels, pauses = [], []
        async def dormir(s):
            pauses.append(s)
        monkeypatch.setattr('nexaura_services_publics.asyncio.sleep', dormir)
        def repondre(r):
            appels.append(r)
            return httpx.Response(http_status, json={'errorWrappers':[{'error':code}]})
        async with ClientPublic(configuration('tva-europe'), transport=httpx.MockTransport(repondre)) as c:
            async def sans_attente():
                pass
            c.limiteur.attendre = sans_attente
            r = await c.get('/ms/FR/vat/40444608442')
            assert r.json()['errorWrappers'][0]['error'] == code
        assert len(appels) == attendu
        assert pauses == ([3] if attendu == 2 else [])
    asyncio.run(scenario())


def test_vies_successif_meme_pendant_reprise(monkeypatch):
    async def scenario():
        debut, liberer, reprise = asyncio.Event(), asyncio.Event(), asyncio.Event()
        chemins = []
        async def dormir(s):
            assert s == 3
            reprise.set()
            await liberer.wait()
        monkeypatch.setattr('nexaura_services_publics.asyncio.sleep', dormir)
        async def repondre(r):
            chemins.append(r.url.path)
            if len(chemins) == 1:
                debut.set()
                return httpx.Response(403, json={'errorWrappers':[{'error':'MS_UNAVAILABLE'}]})
            return httpx.Response(200, json={'isValid':False})
        async with ClientPublic(configuration('tva-europe'), transport=httpx.MockTransport(repondre)) as c:
            async def sans_attente():
                pass
            c.limiteur.attendre = sans_attente
            premier = asyncio.create_task(c.get('/ms/FR/vat/40444608442'))
            await debut.wait()
            await reprise.wait()
            second = asyncio.create_task(c.get('/check-status'))
            # Laisser le second appel atteindre le verrou, sans temporisation réelle.
            boucle = asyncio.get_running_loop()
            tour = boucle.create_future()
            boucle.call_soon(tour.set_result, None)
            await tour
            assert len(chemins) == 1
            liberer.set()
            await asyncio.gather(premier, second)
        assert chemins[0] == chemins[1]
        assert chemins[2].endswith('/check-status')
    asyncio.run(scenario())


def test_empreintes_sources():
    texte = (RACINE/'specs/SOURCES.md').read_text()
    for fichier, empreinte in re.findall(r'^\| ([^|]+?) \| .*? \| 2026-10-27 \| `([a-f0-9]{64})` \|$', texte, re.M):
        assert hashlib.sha256((RACINE/'specs'/fichier).read_bytes()).hexdigest() == empreinte

@pytest.mark.parametrize('nom,outil,args', [
    ('jours-feries-europe','jours_feries',{'countryIsoCode':'BE','validFrom':'2026-01-01','validTo':'2026-12-31'}),
    ('taux-de-change','taux_de_change',{'base':'EUR','quotes':'CHF'}),
])
def test_tableaux_http_conserves_dans_enveloppe_mcp(nom, outil, args):
    async def scenario():
        lignes = [{'valeur':None}, {'valeur':2}]
        s = fabriquer(nom, transport=httpx.MockTransport(lambda _: httpx.Response(200,json=lignes)))
        async with Client(s) as c:
            result = await c.call_tool(outil,args)
            assert result.data == {'result':lignes}
    asyncio.run(scenario())


@pytest.mark.parametrize('chemin', ['/PublicHolidays', '/SchoolHolidays'])
@pytest.mark.parametrize('params', [
    {},
    {'countryIsoCode':'BE','validFrom':'2026-01-01'},
    {'validFrom':'2026-01-01','validTo':'2026-12-31'},
    {'countryIsoCode':'BE','validFrom':'2026-02-30','validTo':'2026-12-31'},
    {'countryIsoCode':'BE','validFrom':'2026-1-01','validTo':'2026-12-31'},
    {'countryIsoCode':'BE','validFrom':'2026-01-02','validTo':'2026-01-01'},
    {'countryIsoCode':'BE','validFrom':'2026-01-01','validTo':'2029-01-02'},
    {'countryIsoCode':'BE','validFrom':'2024-02-29','validTo':'2027-03-01'},
    {'countryIsoCode':'BE','validFrom':'2026-01-01','validTo':'2026-12-31','groupCode':'autre'},
    [('countryIsoCode','BE'),('validFrom','2026-01-01'),('validFrom','2025-01-01'),('validTo','2026-12-31')],
])
def test_europe_periode_invalide_avant_reseau(chemin, params):
    async def scenario():
        def interdit(_):
            pytest.fail('Période invalide transmise')
        async with ClientPublic(configuration('jours-feries-europe'),
                                transport=httpx.MockTransport(interdit)) as c:
            with pytest.raises(ValueError):
                await c.get(chemin, params=params)
    asyncio.run(scenario())


@pytest.mark.parametrize('debut,fin', [
    ('2026-01-01','2029-01-01'),
    ('2024-02-29','2027-02-28'),
    ('2026-01-01','2026-01-01'),
])
@pytest.mark.parametrize('chemin', ['/PublicHolidays', '/SchoolHolidays'])
def test_europe_periode_valide(chemin, debut, fin):
    async def scenario():
        appels = []
        def repondre(r):
            appels.append(r)
            assert r.url.params['languageIsoCode'] == 'FR'
            return httpx.Response(200, json=[])
        async with ClientPublic(configuration('jours-feries-europe'),
                                transport=httpx.MockTransport(repondre)) as c:
            await c.get(chemin, params={'countryIsoCode':'BE','validFrom':debut,'validTo':fin})
        assert len(appels) == 1
    asyncio.run(scenario())


def test_europe_contrat_et_attribution():
    async def scenario():
        s = fabriquer('jours-feries-europe')
        try:
            tools = await s.get_tools()
            for t in tools.values():
                assert 'Données OpenHolidays API (ODbL)' in t.description
                assert t.parameters['properties']['languageIsoCode']['default'] == 'FR'
            for nom in ['jours_feries', 'vacances_scolaires_europe']:
                schema = tools[nom].parameters
                assert {'countryIsoCode','validFrom','validTo'} <= set(schema['required'])
                assert 'subdivisionCode' not in schema['required']
                assert 'groupCode' not in schema['properties']
            assert 'countryIsoCode' in tools['regions_du_pays'].parameters['required']
        finally:
            await s.client_public.aclose()
    asyncio.run(scenario())
