import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
import urllib.parse
import aiohttp
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
SOURCES_FILE = "sources.txt"
OUTPUT_FILE = "data.json"
JS_OUTPUT_FILE = "data.js"
MAX_CONCURRENT_REQUESTS = 35
REQUEST_TIMEOUT_SECONDS = 14
MAX_HISTORICAL_ITEMS = 1500  # Límite amplio para preservar noticias históricas y recientes
MIN_PER_STATE = 15           # Garantizar mínimo de 15 noticias por estado

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

# Rutas estándar de feeds RSS/Atom
FEED_PATHS = [
    "/feed",
    "/feed/",
    "/rss",
    "/rss.xml",
    "/feed.xml",
    "/index.xml",
]

# Mapa exhaustivo de los 24 estados de Venezuela (con capitales, ciudades y gentilicios)
VENEZUELA_STATES = {
    "Amazonas": [r"\bamazonas\b", r"\bpuerto ayacucho\b", r"\batabapo\b", r"\bmaroa\b"],
    "Anzoátegui": [r"\banzo[aá]tegui\b", r"\bbarcelona\b", r"\bpuerto la cruz\b", r"\blecher[ií]a\b", r"\bel tigre\b", r"\banaco\b", r"\bguanta\b"],
    "Apure": [r"\bapure\b", r"\bsan fernando de apure\b", r"\bachaguas\b", r"\bguasdualito\b"],
    "Aragua": [r"\baragua\b", r"\bmaracay\b", r"\bcagua\b", r"\bturmero\b", r"\bla victoria\b", r"\bel lim[oó]n\b", r"\bvilla de cura\b"],
    "Barinas": [r"\bbarinas\b", r"\bbarinitas\b", r"\bsocop[oó]\b", r"\bpedraza\b"],
    "Bolívar": [r"\bbol[ií]var\b", r"\bciudad guayana\b", r"\bpuerto ordaz\b", r"\bciudad bol[ií]var\b", r"\bsan f[eé]lix\b", r"\bupata\b", r"\bgran sabana\b", r"\bsanta elena de uair[eé]n\b"],
    "Carabobo": [r"\bcarabobo\b", r"\bvalencia\b", r"\bpuerto cabello\b", r"\bguacara\b", r"\bnaguanagua\b", r"\bsan diego\b", r"\blos guayos\b"],
    "Cojedes": [r"\bcojedes\b", r"\bsan carlos\b", r"\btinaquillo\b"],
    "Delta Amacuro": [r"\bdelta amacuro\b", r"\btucupita\b", r"\bpedernales\b"],
    "Falcón": [r"\bfalc[oó]n\b", r"\bcoro\b", r"\bpunto fijo\b", r"\bparaguan[aá]\b", r"\bchichiriviche\b", r"\btucacas\b"],
    "Guárico": [r"\bgu[aá]rico\b", r"\bsan juan de los morros\b", r"\bcalabozo\b", r"\bvalle de la pascua\b", r"\bzaraza\b", r"\baltagracia de orituco\b"],
    "Lara": [r"\blara\b", r"\bbarquisimeto\b", r"\bcabudare\b", r"\bcarora\b", r"\bel tocuyo\b", r"\bqu[ií]bor\b"],
    "Mérida": [r"\bm[eé]rida\b", r"\bel vig[ií]a\b", r"\btovar\b", r"\bmucuch[ií]es\b"],
    "Miranda": [r"\bmiranda\b", r"\blos teques\b", r"\bguarenas\b", r"\bguatire\b", r"\bvalles del tuy\b", r"\bcharallave\b", r"\bcúa\b", r"\bchacao\b", r"\bbaruta\b", r"\bel hatillo\b", r"\bpetare\b", r"\bhiguerote\b", r"\br[ií]o chico\b"],
    "Monagas": [r"\bmonagas\b", r"\bmatur[ií]n\b", r"\bcaripe\b", r"\bpunceres\b"],
    "Nueva Esparta": [r"\bnueva esparta\b", r"\bmargarita\b", r"\bporlamar\b", r"\bpampatar\b", r"\bjuan griego\b", r"\bla asunci[oó]n\b", r"\bcoche\b"],
    "Portuguesa": [r"\bportuguesa\b", r"\bguanare\b", r"\bacarigua\b", r"\baraure\b", r"\btur[eé]n\b"],
    "Sucre": [r"\bsucre\b", r"\bcuman[aá]\b", r"\bcar[uú]pano\b", r"\bg[uü]iria\b"],
    "Táchira": [r"\bt[aá]chira\b", r"\bsan crist[oó]bal\b", r"\bsan antonio del t[aá]chira\b", r"\brubio\b", r"\bt[aá]riba\b", r"\bucire\b", r"\bla fr[ií]a\b"],
    "Trujillo": [r"\btrujillo\b", r"\bvalera\b", r"\bbocon[oó]\b"],
    "La Guaira": [r"\bla guaira\b", r"\bvargas\b", r"\bmaiquet[ií]a\b", r"\bcaraballeda\b", r"\bcatia la mar\b", r"\bmacuto\b"],
    "Yaracuy": [r"\byaracuy\b", r"\bsan felipe\b", r"\byaritagua\b", r"\bchivacoa\b", r"\bnirgua\b"],
    "Zulia": [r"\bzulia\b", r"\bmaracaibo\b", r"\bsan francisco\b", r"\bcabimas\b", r"\bciudad ojeda\b", r"\bmachiques\b", r"\bla villa del rosario\b", r"\bsanta b[aá]rbara del zulia\b"],
    "Distrito Capital": [r"\bdistrito capital\b", r"\bcaracas\b", r"\blibertador\b", r"\bcatia\b", r"\bel para[ií]so\b", r"\bla candelaria\b", r"\bel valle\b"],
}

# Slugs de secciones regionales de Últimas Noticias mapeados a entidades federales
UN_STATE_SECTIONS = {
    "Amazonas": "amazonas",
    "Anzoátegui": "anzoateggui",  # Últimas Noticias utiliza doble 'g' en su slug oficial
    "Apure": "apure",
    "Aragua": "aragua",
    "Barinas": "barinas",
    "Bolívar": "bolivar",
    "Carabobo": "carabobo",
    "Cojedes": "cojedes",
    "Delta Amacuro": "delta-amacuro",
    "Falcón": "falcon",
    "Guárico": "guarico",
    "Lara": "lara",
    "Mérida": "merida",
    "Miranda": "miranda",
    "Monagas": "monagas",
    "Nueva Esparta": "nueva-esparta",
    "Portuguesa": "portuguesa",
    "Sucre": "sucre",
    "Táchira": "tachira",
    "Trujillo": "trujillo",
    "La Guaira": "la-guaira",
    "Yaracuy": "yaracuy",
    "Zulia": "zulia",
    "Distrito Capital": "superbarrio",
}


def clean_html(text: str) -> str:
    """Limpia etiquetas HTML, entidades HTML y espacios redundantes."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    cleaned = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True)).strip()
    return cleaned


def parse_date(entry: dict) -> Tuple[str, datetime]:
    """Extrae y normaliza la fecha en formato ISO 8601 en UTC."""
    raw_date = None
    for field in ("published", "pubDate", "updated", "created", "date"):
        if field in entry and entry[field]:
            raw_date = entry[field]
            break

    dt = None
    if raw_date:
        try:
            dt = date_parser.parse(str(raw_date))
        except Exception:
            pass

    if not dt and "published_parsed" in entry and entry.published_parsed:
        try:
            dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass

    if not dt:
        dt = datetime.now(timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)

    return dt.isoformat(), dt


def get_state(text: str, default: str = "Nacional") -> str:
    """Identifica el estado de Venezuela analizando el texto según patrones de ciudades y gentilicios."""
    for state_name, patterns in VENEZUELA_STATES.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return state_name
    return default


def parse_sources(filepath: str) -> List[Dict[str, str]]:
    """Lee y filtra sources.txt: estatus active y categorías NEWS o ECON."""
    sources = []
    if not os.path.exists(filepath):
        return sources
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.strip()
                if not clean_line or clean_line.startswith("#"):
                    continue

                parts = clean_line.split()
                if len(parts) < 4:
                    continue

                category = parts[-1].upper()
                status = parts[-2].lower()
                domain = parts[-3]
                name = " ".join(parts[:-3])

                if status == "active" and category in {"NEWS", "ECON"}:
                    clean_domain = domain.replace("https://", "").replace("http://", "").strip("/")
                    sources.append({
                        "name": name,
                        "domain": clean_domain,
                        "status": status,
                        "category": category,
                    })
    except Exception as e:
        print(f"[!] Error al leer {filepath}: {e}")
    return sources


async def fetch_working_feed(session: aiohttp.ClientSession, domain: str) -> Optional[str]:
    """Prueba variantes de endpoints RSS hasta obtener contenido válido."""
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    for path in FEED_PATHS:
        url = f"https://{domain}{path}"
        try:
            async with session.get(url, headers=HEADERS, timeout=timeout) as response:
                if response.status == 200:
                    text = await response.text()
                    lower_text = text.lower()
                    if any(tag in lower_text for tag in ("<rss", "<feed", "<channel", "<item", "<entry")):
                        return text
        except Exception:
            continue
    return None


def fetch_un_url_sync(url: str, timeout: int = 10) -> Optional[str]:
    """Descarga síncrona con urllib para evitar bloqueos 403 de Cloudflare en Últimas Noticias."""
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            }
        )
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    return None


# ==========================================
# 1. SCRAPER ESPECIALIZADO: ÚLTIMAS NOTICIAS (ESTRUCTURA DE SECCIONES REGIONALES)
# ==========================================
async def scrape_ultimas_noticias(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Dict]:
    """
    Scraper enfocado en la estructura de Últimas Noticias:
    - https://ultimasnoticias.com.ve/seccion/{estado}/ (Estructura para los 24 estados)
    - Secciones adicionales de economía, política, pulso regional y actualidad.
    - Utiliza syndication RSS de Google News con filtrado estricto para Últimas Noticias
      debido al challenge antibot (sgcaptcha) del host principal.
    """
    results = []
    print("[*] Iniciando scraping especializado de Últimas Noticias por entidades federales...")

    # Lista de consultas: (Nombre del estado / sección, término de búsqueda)
    sections_to_scrape = list(UN_STATE_SECTIONS.items()) + [
        ("Nacional", "economia"),
        ("Nacional", "politica"),
        ("Nacional", "pulso regional"),
        ("Nacional", "actualidad"),
    ]

    import urllib.request, ssl, urllib.parse
    ctx = ssl._create_unverified_context()

    def fetch_un_section_sync(state_name: str, query_term: str) -> List[Dict]:
        items = []
        # Búsqueda dirigida a ultimasnoticias.com.ve por estado o sección
        query = f"site:ultimasnoticias.com.ve {query_term}"
        url = f"https://news.google.com/rss/search?q={urllib.parse.quote(query)}&hl=es-419&gl=VE&ceid=VE:es-419"
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
                }
            )
            with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                content = resp.read()
            parsed = feedparser.parse(content)
            for entry in parsed.entries[:12]:
                title_raw = getattr(entry, "title", "")
                title = re.sub(r"\s*-\s*(Últimas Noticias|ultimasnoticias\.com\.ve).*$", "", title_raw, flags=re.IGNORECASE).strip()
                title = clean_html(title)
                link = getattr(entry, "link", "")
                summary_raw = clean_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
                summary = re.sub(r"\s*-\s*(Últimas Noticias|ultimasnoticias\.com\.ve).*$", "", summary_raw, flags=re.IGNORECASE).strip()
                if not summary or len(summary) < 20:
                    summary = title

                if not title or not link or len(title) < 10:
                    continue

                assigned_state = state_name if state_name != "Nacional" else get_state(f"{title} {summary}")
                iso_date, sort_dt = parse_date(entry)

                items.append({
                    "item": {
                        "estado_relacionado": assigned_state,
                        "titular": title,
                        "medio": "Últimas Noticias",
                        "url": link,
                        "fecha": iso_date,
                        "extracto": (summary[:320] + "...") if len(summary) > 320 else summary,
                    },
                    "_sort_date": sort_dt,
                })
        except Exception:
            pass
        return items

    async def run_section(state_name: str, query_term: str):
        async with semaphore:
            return await asyncio.to_thread(fetch_un_section_sync, state_name, query_term)

    tasks = [run_section(st, term) for st, term in sections_to_scrape]
    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
    for res in batch_results:
        if isinstance(res, list):
            results.extend(res)

    print(f"[OK] Últimas Noticias: {len(results)} artículos recolectados en total.")
    return results


# ==========================================
# 2. SCRAPER ESPECIALIZADO: VTV (VENEZOLANA DE TELEVISIÓN)
# ==========================================
async def scrape_vtv(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Dict]:
    """
    Scraper para Venezolana de Televisión:
    - https://vtv.com.ve/category/noticias/economia/
    - https://vtv.com.ve/category/noticias/
    - https://vtv.com.ve/category/noticias/regionales/
    """
    results = []
    print("[*] Scrapeando Venezolana de Televisión (VTV)...")

    vtv_urls = [
        ("https://vtv.com.ve/category/noticias/economia/feed/", "Economía"),
        ("https://vtv.com.ve/category/noticias/feed/", "Noticias"),
        ("https://vtv.com.ve/category/noticias/regionales/feed/", "Regionales"),
        ("https://vtv.com.ve/feed/", "General"),
    ]

    async def fetch_vtv_feed(url: str, default_cat: str):
        sub_results = []
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
        async with semaphore:
            try:
                async with session.get(url, headers=HEADERS, timeout=timeout) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        parsed = feedparser.parse(content)
                        for entry in parsed.entries:
                            title = clean_html(getattr(entry, "title", ""))
                            link = getattr(entry, "link", "")
                            summary = clean_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
                            if not title or not link:
                                continue

                            full_text = f"{title} {summary}"
                            state = get_state(full_text)
                            iso_date, sort_dt = parse_date(entry)

                            sub_results.append({
                                "item": {
                                    "estado_relacionado": state,
                                    "titular": title,
                                    "medio": "VTV",
                                    "url": link,
                                    "fecha": iso_date,
                                    "extracto": (summary[:320] + "...") if len(summary) > 320 else summary,
                                },
                                "_sort_date": sort_dt,
                            })
            except Exception:
                pass
        return sub_results

    tasks = [fetch_vtv_feed(u, c) for u, c in vtv_urls]
    batch = await asyncio.gather(*tasks, return_exceptions=True)
    for b in batch:
        if isinstance(b, list):
            results.extend(b)

    print(f"[OK] VTV: {len(results)} noticias recolectadas.")
    return results


# ==========================================
# 3. SCRAPER ESPECIALIZADO: GLOBOVISIÓN
# ==========================================
async def scrape_globovision(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Dict]:
    """
    Scraper HTML para Globovisión:
    - https://www.globovision.com
    - /nacionales, /regiones, /economia, /politica
    """
    results = []
    print("[*] Scrapeando Globovisión...")

    gv_sections = [
        "https://www.globovision.com",
        "https://www.globovision.com/nacionales",
        "https://www.globovision.com/regiones",
        "https://www.globovision.com/economia",
        "https://www.globovision.com/politica",
    ]

    seen_links = set()
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)

    for section_url in gv_sections:
        async with semaphore:
            try:
                async with session.get(section_url, headers=HEADERS, timeout=timeout) as resp:
                    if resp.status != 200:
                        continue
                    html = await resp.text()
            except Exception:
                continue

        try:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                title = clean_html(a.get_text())

                if len(title) < 22:
                    continue

                full_url = href if href.startswith("http") else f"https://www.globovision.com{href}"
                if "globovision.com" not in full_url or full_url in seen_links:
                    continue

                if not any(c in full_url for c in ["/politica/", "/nacionales/", "/economia/", "/regiones/", "/sociedad/"]):
                    continue

                seen_links.add(full_url)
                state = get_state(title)
                now_iso = datetime.now(timezone.utc).isoformat()
                now_dt = datetime.now(timezone.utc)

                results.append({
                    "item": {
                        "estado_relacionado": state,
                        "titular": title,
                        "medio": "Globovisión",
                        "url": full_url,
                        "fecha": now_iso,
                        "extracto": title,
                    },
                    "_sort_date": now_dt,
                })
        except Exception:
            continue

    print(f"[OK] Globovisión: {len(results)} noticias recolectadas.")
    return results


# ==========================================
# 4. SCRAPER ESPECIALIZADO: EL NACIONAL
# ==========================================
async def scrape_el_nacional(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Dict]:
    """
    Scraper para El Nacional:
    - https://www.elnacional.com/venezuela/feed/
    - https://www.elnacional.com/feed/
    """
    results = []
    print("[*] Scrapeando El Nacional (Sección Venezuela)...")

    urls = [
        "https://www.elnacional.com/venezuela/feed/",
        "https://www.elnacional.com/feed/",
    ]

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    for u in urls:
        async with semaphore:
            try:
                async with session.get(u, headers=HEADERS, timeout=timeout) as resp:
                    if resp.status != 200:
                        continue
                    content = await resp.text()
            except Exception:
                continue

        try:
            parsed = feedparser.parse(content)
            for entry in parsed.entries:
                title = clean_html(getattr(entry, "title", ""))
                link = getattr(entry, "link", "")
                summary = clean_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
                if not title or not link:
                    continue

                full_text = f"{title} {summary}"
                state = get_state(full_text)
                iso_date, sort_dt = parse_date(entry)

                results.append({
                    "item": {
                        "estado_relacionado": state,
                        "titular": title,
                        "medio": "El Nacional",
                        "url": link,
                        "fecha": iso_date,
                        "extracto": (summary[:320] + "...") if len(summary) > 320 else summary,
                    },
                    "_sort_date": sort_dt,
                })
        except Exception:
            continue

    print(f"[OK] El Nacional: {len(results)} noticias recolectadas.")
    return results


# ==========================================
# 5. SCRAPER ESPECIALIZADO: CARAOTA DIGITAL
# ==========================================
async def scrape_caraota_digital(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Dict]:
    """
    Scraper para Caraota Digital:
    - https://caraotadigital.net/category/venezuela/feed/
    - https://caraotadigital.net/feed/
    """
    results = []
    print("[*] Scrapeando Caraota Digital (Sección Venezuela)...")

    urls = [
        "https://caraotadigital.net/category/venezuela/feed/",
        "https://caraotadigital.net/feed/",
    ]

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    for u in urls:
        async with semaphore:
            try:
                async with session.get(u, headers=HEADERS, timeout=timeout) as resp:
                    if resp.status != 200:
                        continue
                    content = await resp.text()
            except Exception:
                continue

        try:
            parsed = feedparser.parse(content)
            for entry in parsed.entries:
                title = clean_html(getattr(entry, "title", ""))
                link = getattr(entry, "link", "")
                summary = clean_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
                if not title or not link:
                    continue

                full_text = f"{title} {summary}"
                state = get_state(full_text)
                iso_date, sort_dt = parse_date(entry)

                results.append({
                    "item": {
                        "estado_relacionado": state,
                        "titular": title,
                        "medio": "Caraota Digital",
                        "url": link,
                        "fecha": iso_date,
                        "extracto": (summary[:320] + "...") if len(summary) > 320 else summary,
                    },
                    "_sort_date": sort_dt,
                })
        except Exception:
            continue

    print(f"[OK] Caraota Digital: {len(results)} noticias recolectadas.")
    return results


# ==========================================
# 6. SCRAPER ESPECIALIZADO: BANCA Y NEGOCIOS
# ==========================================
async def scrape_banca_y_negocios(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Dict]:
    """
    Scraper para Banca y Negocios:
    - https://www.bancaynegocios.com
    - /categoria/economia/ y /categoria/finanzas/
    """
    results = []
    print("[*] Scrapeando Banca y Negocios...")

    urls = [
        "https://www.bancaynegocios.com",
        "https://www.bancaynegocios.com/categoria/economia/",
        "https://www.bancaynegocios.com/categoria/finanzas/",
    ]

    seen = set()
    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)

    for u in urls:
        async with semaphore:
            try:
                async with session.get(u, headers=HEADERS, timeout=timeout) as resp:
                    if resp.status != 200:
                        continue
                    html = await resp.text()
            except Exception:
                continue

        try:
            soup = BeautifulSoup(html, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                title = clean_html(a.get_text())

                if "bancaynegocios.com/" not in href or len(title) < 22:
                    continue

                if href.count("/") < 4 or href.endswith("/categoria/"):
                    continue

                if href in seen:
                    continue
                seen.add(href)

                state = get_state(title)
                now_iso = datetime.now(timezone.utc).isoformat()
                now_dt = datetime.now(timezone.utc)

                results.append({
                    "item": {
                        "estado_relacionado": state,
                        "titular": title,
                        "medio": "Banca y Negocios",
                        "url": href,
                        "fecha": now_iso,
                        "extracto": title,
                    },
                    "_sort_date": now_dt,
                })
        except Exception:
            continue

    print(f"[OK] Banca y Negocios: {len(results)} noticias recolectadas.")
    return results


# ==========================================
# 7. SCRAPER ESPECIALIZADO: EL IMPULSO
# ==========================================
async def scrape_el_impulso(session: aiohttp.ClientSession, semaphore: asyncio.Semaphore) -> List[Dict]:
    """
    Scraper para El Impulso:
    - https://www.elimpulso.com/feed/
    - /category/regionales/feed/, /category/economia/feed/
    """
    results = []
    print("[*] Scrapeando El Impulso...")

    urls = [
        "https://www.elimpulso.com/feed/",
        "https://www.elimpulso.com/category/regionales/feed/",
        "https://www.elimpulso.com/category/economia/feed/",
        "https://www.elimpulso.com/category/nacionales/feed/",
    ]

    timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT_SECONDS)
    for u in urls:
        async with semaphore:
            try:
                async with session.get(u, headers=HEADERS, timeout=timeout) as resp:
                    if resp.status != 200:
                        continue
                    content = await resp.text()
            except Exception:
                continue

        try:
            parsed = feedparser.parse(content)
            for entry in parsed.entries:
                title = clean_html(getattr(entry, "title", ""))
                link = getattr(entry, "link", "")
                summary = clean_html(getattr(entry, "summary", "") or getattr(entry, "description", ""))
                if not title or not link:
                    continue

                full_text = f"{title} {summary}"
                # Por defecto en El Impulso si es regional suele ser Lara si no especifica otro
                state = get_state(full_text, default="Lara" if "regionales" in u else "Nacional")
                iso_date, sort_dt = parse_date(entry)

                results.append({
                    "item": {
                        "estado_relacionado": state,
                        "titular": title,
                        "medio": "El Impulso",
                        "url": link,
                        "fecha": iso_date,
                        "extracto": (summary[:320] + "...") if len(summary) > 320 else summary,
                    },
                    "_sort_date": sort_dt,
                })
        except Exception:
            continue

    print(f"[OK] El Impulso: {len(results)} noticias recolectadas.")
    return results


# ==========================================
# 8. SCRAPER GENÉRICO PARA FUENTES RESTANTES EN SOURCES.TXT
# ==========================================
async def process_domain(
    session: aiohttp.ClientSession,
    source: Dict[str, str],
    semaphore: asyncio.Semaphore,
) -> List[Dict]:
    """Descarga y procesa un feed genérico de forma aislada."""
    domain = source["domain"]
    name = source["name"]
    results = []

    # Omitir fuentes que ya cuentan con scraping especializado
    specialized_domains = {
        "ultimasnoticias.com.ve",
        "vtv.com.ve",
        "globovision.com",
        "elnacional.com",
        "caraotadigital.net",
        "bancaynegocios.com",
        "elimpulso.com",
    }
    if any(sd in domain for sd in specialized_domains):
        return []

    async with semaphore:
        content = await fetch_working_feed(session, domain)

    if not content:
        return []

    # Parseo con feedparser
    try:
        parsed = feedparser.parse(content)
        entries = parsed.entries
    except Exception:
        entries = []

    if not entries:
        try:
            soup = BeautifulSoup(content, "html.parser")
            xml_items = soup.find_all("item") or soup.find_all("entry")
            for item in xml_items:
                t = item.find("title")
                l = item.find("link")
                d = item.find("description") or item.find("summary")
                p = item.find("pubdate") or item.find("published")

                entries.append({
                    "title": t.get_text() if t else "",
                    "link": (l.get_text() if l and l.get_text() else (l.get("href", "") if l else "")),
                    "summary": d.get_text() if d else "",
                    "published": p.get_text() if p else "",
                })
        except Exception:
            return []

    for entry in entries:
        try:
            title = clean_html(getattr(entry, "title", "") or entry.get("title", ""))
            link = getattr(entry, "link", "") or entry.get("link", "")
            summary = clean_html(getattr(entry, "summary", "") or entry.get("summary", ""))

            if not title or not link:
                continue

            full_text = f"{title} {summary}"
            iso_date, sort_dt = parse_date(entry)
            state = get_state(full_text)

            results.append({
                "item": {
                    "estado_relacionado": state,
                    "titular": title,
                    "medio": name,
                    "url": link,
                    "fecha": iso_date,
                    "extracto": summary[:320] + ("..." if len(summary) > 320 else ""),
                },
                "_sort_date": sort_dt,
            })
        except Exception:
            continue

    if results:
        print(f"[OK] {name}: {len(results)} noticias.")
    return results


def load_existing_data(filepath: str) -> List[Dict]:
    """Carga los datos previos de data.json para preservar el histórico."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
    except Exception as e:
        print(f"[!] No se pudo leer histórico: {e}")
    return []


def merge_and_balance(
    existing_items: List[Dict],
    new_items: List[Dict],
    min_per_state: int = MIN_PER_STATE,
    max_total: int = MAX_HISTORICAL_ITEMS,
) -> List[Dict]:
    """
    1. Une el histórico con las nuevas noticias sin duplicados.
    2. Garantiza al menos min_per_state noticias por cada estado (si existen).
    3. Completa el resto con las noticias más recientes hasta max_total.
    4. Devuelve todo ordenado cronológicamente de más reciente a más antigua.
    """
    seen_urls: Set[str] = set()
    combined: List[Tuple[Dict, datetime]] = []

    # 1. Procesar noticias recién extraídas
    for entry in new_items:
        url = entry["item"]["url"]
        if url and url not in seen_urls:
            seen_urls.add(url)
            combined.append((entry["item"], entry["_sort_date"]))

    # 2. Procesar histórico existente
    for item in existing_items:
        url = item.get("url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            try:
                dt = date_parser.parse(item.get("fecha", ""))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
            except Exception:
                dt = datetime.fromtimestamp(0, tz=timezone.utc)
            combined.append((item, dt))

    # Ordenar todo de más reciente a más antigua
    combined.sort(key=lambda x: x[1], reverse=True)

    # Balanceo por estado
    reserved: List[Tuple[Dict, datetime]] = []
    reserved_urls: Set[str] = set()
    state_counts: Dict[str, int] = {st: 0 for st in VENEZUELA_STATES.keys()}

    # Pasada 1: Asegurar cupo mínimo por entidad federal
    for item, dt in combined:
        state = item.get("estado_relacionado", "Nacional")
        if state in state_counts and state_counts[state] < min_per_state:
            reserved.append((item, dt))
            reserved_urls.add(item["url"])
            state_counts[state] += 1

    # Pasada 2: Agregar las más recientes restantes hasta max_total
    final_combined = list(reserved)
    for item, dt in combined:
        if len(final_combined) >= max_total:
            break
        if item["url"] not in reserved_urls:
            final_combined.append((item, dt))

    # Orden final estrictamente por fecha descendente
    final_combined.sort(key=lambda x: x[1], reverse=True)
    return [item for item, _ in final_combined]


async def main():
    print("====================================================")
    print("  SCRAPER MULTI-FUENTE DE NOTICIAS DE VENEZUELA    ")
    print("====================================================")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    connector = aiohttp.TCPConnector(ssl=False, limit=0)

    async with aiohttp.ClientSession(connector=connector) as session:
        # 1. Ejecutar scrapers especializados prioritarios concurrentemente
        specialized_tasks = [
            scrape_ultimas_noticias(session, semaphore),
            scrape_vtv(session, semaphore),
            scrape_globovision(session, semaphore),
            scrape_el_nacional(session, semaphore),
            scrape_caraota_digital(session, semaphore),
            scrape_el_impulso(session, semaphore),
            scrape_banca_y_negocios(session, semaphore),
        ]

        # 2. Fuentes genéricas adicionales de sources.txt
        sources = parse_sources(SOURCES_FILE)
        generic_tasks = [process_domain(session, s, semaphore) for s in sources]

        all_tasks = specialized_tasks + generic_tasks
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

    new_scraped: List[Dict] = []
    for res in all_results:
        if isinstance(res, list):
            new_scraped.extend(res)

    print(f"\n[+] Total de nuevas noticias capturadas: {len(new_scraped)}")

    # 3. Fusión y balanceo con el archivo histórico
    existing_data = load_existing_data(OUTPUT_FILE)
    print(f"[+] Total previo en histórico: {len(existing_data)}")

    final_output = merge_and_balance(existing_data, new_scraped)

    # 4. Guardar data.json
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    # 5. Guardar data.js (para ejecución local inmediata sin problemas de CORS)
    js_content = "window.NEWS_DATA = " + json.dumps(final_output, ensure_ascii=False, indent=2) + ";\n"
    with open(JS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(js_content)

    # 6. Estadísticas de cobertura regional
    states_count = {}
    media_count = {}
    for item in final_output:
        st = item.get("estado_relacionado", "Nacional")
        med = item.get("medio", "Desconocido")
        states_count[st] = states_count.get(st, 0) + 1
        media_count[med] = media_count.get(med, 0) + 1

    print("\n----------------------------------------------------")
    print(f"EXITO: {len(final_output)} noticias consolidadas.")
    print(f"Cobertura regional: {len(states_count)} entidades registradas.")
    print("Principales medios representados:")
    for m, c in sorted(media_count.items(), key=lambda x: x[1], reverse=True)[:8]:
        print(f"  - {m}: {c} noticias")
    print("----------------------------------------------------")


if __name__ == "__main__":
    asyncio.run(main())
