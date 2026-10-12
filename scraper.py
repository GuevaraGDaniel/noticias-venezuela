import asyncio
import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Set
import aiohttp
from bs4 import BeautifulSoup
from dateutil import parser as date_parser
import feedparser

# Configuración general
SOURCES_FILE = "sources.txt"
OUTPUT_FILE = "data.json"
MAX_CONCURRENT_REQUESTS = 30
REQUEST_TIMEOUT_SECONDS = 12
MAX_HISTORICAL_ITEMS = 1200  # Límite amplio para preservar más de 500 noticias históricas
MIN_PER_STATE = 15           # Garantizar mínimo de 15 noticias por estado

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

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def clean_html(text: str) -> str:
    """Limpia etiquetas HTML y espacios redundantes."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True)).strip()


def parse_sources(filepath: str) -> List[Dict[str, str]]:
    """Lee y filtra sources.txt: sólo estatus active y categorías NEWS o ECON."""
    sources = []
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


def parse_date(entry: dict) -> Tuple[str, datetime]:
    """Extrae la fecha en formato ISO 8601 normalizado en UTC."""
    raw_date = None
    for field in ("published", "pubDate", "updated", "created"):
        if field in entry and entry[field]:
            raw_date = entry[field]
            break

    dt = None
    if raw_date:
        try:
            dt = date_parser.parse(raw_date)
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


def get_state(text: str) -> str:
    """Identifica el estado de Venezuela o devuelve 'Nacional' si no hay mención."""
    for state_name, patterns in VENEZUELA_STATES.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return state_name
    return "Nacional"


async def fetch_working_feed(session: aiohttp.ClientSession, domain: str) -> Optional[str]:
    """Prueba diferentes variantes de endpoints RSS hasta obtener contenido válido."""
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


async def process_domain(
    session: aiohttp.ClientSession,
    source: Dict[str, str],
    semaphore: asyncio.Semaphore,
) -> List[Dict]:
    """Descarga y procesa un feed de forma aislada."""
    domain = source["domain"]
    name = source["name"]
    category = source["category"]
    results = []

    async with semaphore:
        content = await fetch_working_feed(session, domain)

    if not content:
        return []

    # 1. Parseo con feedparser
    try:
        parsed = feedparser.parse(content)
        entries = parsed.entries
    except Exception:
        entries = []

    # 2. Fallback con BeautifulSoup si feedparser no extrajo entradas
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
    """Carga los datos previos de data.json para acumularlos."""
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

    # Procesar noticias recién extraídas
    for entry in new_items:
        url = entry["item"]["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            combined.append((entry["item"], entry["_sort_date"]))

    # Procesar histórico existente
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

    # Primera pasada: asegurar cupo para cada estado regional
    for item, dt in combined:
        state = item.get("estado_relacionado", "Nacional")
        if state in state_counts and state_counts[state] < min_per_state:
            reserved.append((item, dt))
            reserved_urls.add(item["url"])
            state_counts[state] += 1

    # Segunda pasada: agregar las más recientes hasta alcanzar max_total
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
    sources = parse_sources(SOURCES_FILE)
    if not sources:
        print("[!] No hay fuentes activas para procesar.")
        return

    print(f"Consultando {len(sources)} medios concurrentemente...")
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    connector = aiohttp.TCPConnector(ssl=False, limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [process_domain(session, s, semaphore) for s in sources]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

    new_scraped: List[Dict] = []
    for res in all_results:
        if isinstance(res, list):
            new_scraped.extend(res)

    print(f"Nuevas noticias capturadas en esta ronda: {len(new_scraped)}")

    existing_data = load_existing_data(OUTPUT_FILE)
    print(f"Noticias previas en historial: {len(existing_data)}")

    final_output = merge_and_balance(existing_data, new_scraped)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

    # Conteo rápido de cobertura regional
    states_found = set(item.get("estado_relacionado") for item in final_output)
    print(f"Total consolidado: {len(final_output)} noticias ({len(states_found)} estados cubiertos).")


if __name__ == "__main__":
    asyncio.run(main())
