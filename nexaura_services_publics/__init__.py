"""Outils issus exclusivement d'opérations OpenAPI GET locales."""
import os
os.environ["FASTMCP_CHECK_FOR_UPDATES"] = "off"

import asyncio
import copy
from contextlib import asynccontextmanager
from datetime import date
import json
from pathlib import Path
import re
import sysconfig
import time

import httpx
import yaml
from fastmcp import FastMCP
from fastmcp.server.openapi import MCPType, RouteMap
from mcp.types import ToolAnnotations

NOMS = ("adresse", "geo", "jours-feries", "calendrier-scolaire",
        "bodacc", "tva-europe", "jours-feries-europe", "taux-de-change")
TITRES = {
    "chercher_adresse": "Chercher une adresse",
    "adresse_depuis_position": "Chercher une adresse depuis une position",
    "chercher_communes": "Chercher des communes",
    "commune_par_code": "Consulter une commune par son code",
    "departements": "Consulter les départements",
    "regions": "Consulter les régions",
    "jours_feries": "Consulter les jours fériés",
    "vacances_scolaires": "Consulter les vacances scolaires",
    "annonces_entreprise": "Consulter les annonces d'une entreprise",
    "verifier_tva": "Vérifier un numéro de TVA",
    "etat_service_tva": "Consulter la disponibilité du service TVA",
    "vacances_scolaires_europe": "Consulter les vacances scolaires en Europe",
    "pays": "Consulter les pays disponibles",
    "regions_du_pays": "Consulter les régions d'un pays",
    "taux_de_change": "Consulter les taux de change",
    "taux_entre_devises": "Consulter le taux entre deux devises",
    "devises_disponibles": "Consulter les devises disponibles",
}
MAX_OCTETS = 200_000  # 200 Ko décimaux, contenu décompressé
USER_AGENT = "NexAura-services-publics/0.1.1 (lecture seule)"
RACINE = Path(__file__).resolve().parent.parent
if not (RACINE / "connecteurs").is_dir():
    RACINE = Path(sysconfig.get_path("data")) / "share/nexaura_services_publics"


def configuration(nom):
    if nom not in NOMS:
        raise ValueError("Connecteur inconnu")
    return yaml.safe_load((RACINE / "connecteurs" / f"{nom}.yaml").read_text())


def charger(chemin):
    spec = yaml.safe_load(Path(chemin).read_text())
    if not str(spec.get("openapi", "")).startswith("3."):
        raise ValueError("OpenAPI 3 requis")

    def verifier(obj):
        if isinstance(obj, dict):
            if "$ref" in obj and not obj["$ref"].startswith("#/"):
                raise ValueError("Référence externe interdite")
            for value in obj.values():
                verifier(value)
        elif isinstance(obj, list):
            for value in obj:
                verifier(value)
    verifier(spec)
    return spec


class Limiteur:
    """Intervalle minimal, sans rafale, commun aux outils d'un connecteur."""
    def __init__(self, appels_seconde, horloge=time.monotonic, dormir=asyncio.sleep):
        self.intervalle = 1 / appels_seconde
        self.horloge, self.dormir = horloge, dormir
        self.prochain = 0.0
        self.verrou = asyncio.Lock()

    async def attendre(self):
        async with self.verrou:
            retard = self.prochain - self.horloge()
            if retard > 0:
                await self.dormir(retard)
            self.prochain = self.horloge() + self.intervalle


def tronquer(contenu):
    """Conserve un préfixe UTF-8 et un avertissement dans une enveloppe JSON valide."""
    extrait = contenu.decode("utf-8", errors="replace")
    def encoder(texte):
        return json.dumps({"avertissement": "réponse tronquée", "extrait": texte},
                          ensure_ascii=False).encode("utf-8")
    bas, haut = 0, len(extrait)
    while bas < haut:
        milieu = (bas + haut + 1) // 2
        if len(encoder(extrait[:milieu])) <= MAX_OCTETS:
            bas = milieu
        else:
            haut = milieu - 1
    return encoder(extrait[:bas])


class ClientPublic(httpx.AsyncClient):
    def __init__(self, config, **kwargs):
        self.config = config
        self.fixe = httpx.URL(config["base"])
        self.verrou_requete = asyncio.Lock()
        self.limiteur = Limiteur(config["quota"]["client_appels_seconde"])
        super().__init__(base_url=config["base"], timeout=15, follow_redirects=False,
                         trust_env=False, headers={"User-Agent": USER_AGENT}, **kwargs)

    async def send(self, request, **kwargs):
        # Contrôle aussi la requête construite par FastMCP, avant tout accès réseau.
        if (request.method != "GET" or request.url.scheme != "https"
                or request.url.host != self.fixe.host or request.url.port != self.fixe.port
                or request.url.userinfo):
            raise ValueError("Seul GET sur la base fixe est autorisé")
        prefixe = self.fixe.path.rstrip("/")
        chemin = request.url.path[len(prefixe):] if request.url.path.startswith(prefixe + "/") else ""
        permis = [op for op in self.config["operations"] if re.fullmatch(re.sub(r"\\\{[^}]+\\\}", "[^/]+", re.escape(
            op.get("chemin_fixe", op["chemin"]))), chemin)]
        if not permis or any(part in (".", "..") for part in request.url.path.split("/")):
            raise ValueError("Opération hors liste")
        operation = permis[0]
        modele = operation.get("chemin_fixe", operation["chemin"])
        noms = re.findall(r"\{([^}]+)\}", modele)
        motif = re.sub(r"\\\{[^}]+\\\}", "([^/]+)", re.escape(modele))
        valeurs_chemin = dict(zip(noms, re.fullmatch(motif, chemin).groups()))
        params = request.url.params
        if self.config.get("requete_stricte"):
            autorises = set(operation.get("parametres", {})) - set(noms)
            if set(params) - autorises:
                raise ValueError("Paramètre hors liste")
        for name, patch in permis[0].get("parametres", {}).items():
            schema = patch.get("schema", {})
            if name not in noms and name not in params and "default" in schema:
                params = params.set(name, str(schema["default"]))
            values = [valeurs_chemin[name]] if name in noms else params.get_list(name)
            if len(values) > 1:
                raise ValueError(f"Paramètre répété : {name}")
            if patch.get("required") and not values:
                raise ValueError(f"Paramètre requis : {name}")
            for value in values:
                if schema.get("type") == "integer":
                    if not re.fullmatch(r"-?[0-9]+", value):
                        raise ValueError(f"Entier requis : {name}")
                    nombre = int(value)
                    if nombre < schema.get("minimum", nombre) or nombre > schema.get("maximum", nombre):
                        raise ValueError(f"Limite dépassée : {name}")
                if "enum" in schema and value not in schema["enum"]:
                    raise ValueError(f"Valeur interdite : {name}")
                if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
                    raise ValueError(f"Filtre invalide : {name}")
        periode = operation.get("periode_dates")
        if periode:
            debut = date.fromisoformat(params[periode["debut"]])
            fin = date.fromisoformat(params[periode["fin"]])
            # Comparaison calendaire, y compris un départ le 29 février.
            maximum = (debut.year + periode["maximum_annees"], debut.month, debut.day)
            if fin < debut or (fin.year, fin.month, fin.day) > maximum:
                raise ValueError("Période invalide : trois ans au maximum")
        request.url = request.url.copy_with(params=params)
        request.headers["User-Agent"] = USER_AGENT
        request.extensions["timeout"] = httpx.Timeout(15).as_dict()
        if self.config.get("une_a_la_fois"):
            async with self.verrou_requete:
                return await self._avec_reprise(request, **kwargs)
        return await self._avec_reprise(request, **kwargs)

    async def _avec_reprise(self, request, **kwargs):
        response = await self._envoyer(request, **kwargs)
        reprise = self.config.get("reprise")
        if reprise:
            try:
                donnees = response.json()
            except (ValueError, UnicodeDecodeError):
                donnees = None
            # Codes exacts uniquement, dans les valeurs JSON (y compris errorWrappers).
            def contient_code(obj):
                if isinstance(obj, dict):
                    return any(contient_code(v) for v in obj.values())
                if isinstance(obj, list):
                    return any(contient_code(v) for v in obj)
                return isinstance(obj, str) and obj in reprise["codes"]
            if contient_code(donnees):
                await response.aclose()
                await asyncio.sleep(reprise["delai_secondes"])
                response = await self._envoyer(request, **kwargs)
        return response

    async def _envoyer(self, request, **kwargs):
        await self.limiteur.attendre()
        kwargs.update(stream=True, follow_redirects=False)
        response = await super().send(request, **kwargs)
        contenu = bytearray()
        try:
            async for morceau in response.aiter_bytes(chunk_size=8192):
                contenu.extend(morceau)
                if len(contenu) > MAX_OCTETS:
                    break
        finally:
            await response.aclose()
        coupe = len(contenu) > MAX_OCTETS
        headers = {k: v for k, v in response.headers.items()
                   if k.lower() not in ("content-length", "content-encoding", "transfer-encoding")}
        if coupe:
            headers["content-type"] = "application/json; charset=utf-8"
        return httpx.Response(response.status_code, headers=headers, request=request,
                              content=tronquer(contenu) if coupe else bytes(contenu))


def preparer(spec, config):
    """Projection déclarative : noms, descriptions, paramètres natifs et chemins fixes."""
    spec = copy.deepcopy(spec)
    def normaliser(obj):
        if isinstance(obj, dict):
            # `any` n'est pas un type OpenAPI : schéma libre équivalent = {}.
            if obj.get("type") == "any":
                del obj["type"]
            for valeur in obj.values():
                normaliser(valeur)
        elif isinstance(obj, list):
            for valeur in obj:
                normaliser(valeur)
    normaliser(spec)
    # Certains codes HTTP officiels YAML sont des clés numériques non citées.
    for item in spec["paths"].values():
        for operation in item.values():
            if isinstance(operation, dict) and "responses" in operation:
                operation["responses"] = {str(k): v for k, v in operation["responses"].items()}
    for op in config["operations"]:
        original = op["chemin"]
        operation = spec["paths"][original]["get"]
        operation["operationId"] = op["nom"]
        operation["description"] = op["description"] + " Limite : " + config["quota"]["affichage"]
        operation["summary"] = operation["description"]
        params = operation.get("parameters", [])
        params = [copy.deepcopy(spec["components"]["parameters"][p["$ref"].split("/")[-1]])
                  if "$ref" in p else p for p in params]
        params = [p for p in params if p["name"] not in op.get("retirer_parametres", [])]
        for p in params:
            if p["name"] in op.get("parametres", {}):
                patch = op["parametres"][p["name"]]
                p.update({k: v for k, v in patch.items() if k != "schema"})
                p["schema"] = {**p.get("schema", {}), **patch.get("schema", {})}
        operation["parameters"] = params
        if "chemin_fixe" in op:
            spec["paths"][op["chemin_fixe"]] = {"get": operation}
            del spec["paths"][original]
    return spec


def fabriquer(nom, *, spec=None, config=None, transport=None):
    config = config or configuration(nom)
    spec = preparer(spec or charger(RACINE / config["description"]), config)
    # Première règle gagnante : toutes les écritures exclues AVANT les autorisations.
    maps = [RouteMap(methods=["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"],
                     mcp_type=MCPType.EXCLUDE)]
    maps.extend(RouteMap(methods=["GET"], pattern="^" + re.escape(op.get("chemin_fixe", op["chemin"])) + "$",
                         mcp_type=MCPType.TOOL) for op in config["operations"])
    maps.append(RouteMap(mcp_type=MCPType.EXCLUDE))
    client = ClientPublic(config, **({"transport": transport} if transport else {}))

    @asynccontextmanager
    async def duree_de_vie(_server):
        async with client:
            yield

    def adapter(_route, composant):
        composant.output_schema = None
        composant.annotations = ToolAnnotations(
            title=TITRES[composant.name],
            readOnlyHint=True, destructiveHint=False,
            idempotentHint=True, openWorldHint=True,
        )

    server = FastMCP.from_openapi(openapi_spec=spec, client=client, name=nom,
        route_maps=maps, mcp_component_fn=adapter, lifespan=duree_de_vie)
    # Accessible aux tests pour fermer aussi les clients hors cycle MCP.
    server.client_public = client
    return server
