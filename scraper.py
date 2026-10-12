#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Motor Asíncrono de Extracción, Clasificación Regional y Consolidación de Noticias de Venezuela
Genera el archivo data.json estático para consumo frontend serverless.
"""

import asyncio
import re
import os
import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
import dateutil.parser

import aiohttp
import feedparser
from bs4 import BeautifulSoup

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("NewsScraper")

# Mapeo de Expresiones Regulares para Clasificación Regional (24 Estados + Esequibo)
REGIONAL_PATTERNS = {
    "Zulia": re.compile(r'\b(zulia|zuliano|zuliana|maracaibo|marabino|san francisco|cabimas|ciudad ojeda|machiques|santa b[aá]rbara del zulia|costa oriental del lago|lagunillas)\b', re.IGNORECASE),
    "Miranda": re.compile(r'\b(miranda|mirandino|mirandina|los teques|chacao|baruta|el hatillo|sucre|guarenas|guatire|valles del tuy|barlovento|petare|charallave|cua|higuerote)\b', re.IGNORECASE),
    "Carabobo": re.compile(r'\b(carabobo|carabobe[nñ]o|carabobe[nñ]a|valencia|puerto cabello|naguanagua|guacara|san diego|los guayos|mariara|el palito)\b', re.IGNORECASE),
    "Distrito Capital": re.compile(r'\b(caracas|caraque[nñ]o|caraque[nñ]a|distrito capital|libertador|catia|el valle|la candelaria|chacao|palacio de miraflores|ant[ií]mano|el para[ií]so)\b', re.IGNORECASE),
    "Lara": re.compile(r'\b(lara|larense|barquisimeto|cabudare|carora|el tocuyo|qu[ií]bor|duaca|crepuscular|guaro|guara)\b', re.IGNORECASE),
    "Anzoátegui": re.compile(r'\b(anzo[aá]tegui|anzoatiguense|barcelona|puerto la cruz|lecher[ií]a|guanta|el tigre|anaco|cantaura|jose|faja del orinoco)\b', re.IGNORECASE),
    "Aragua": re.compile(r'\b(aragua|arag[uü]e[nñ]o|arag[uü]e[nñ]a|maracay|cagua|turmero|la victoria|ocumare de la costa|choron[ií]|el lim[oó]n|saman de guere)\b', re.IGNORECASE),
    "Bolívar": re.compile(r'\b(bol[ií]var|bolivarense|ciudad bol[ií]var|puerto ordaz|san f[eé]lix|ciudad guayana|la gran sabana|santa elena de uair[eé]n|sidor|guri|caron[ií]|upata|el callao)\b', re.IGNORECASE),
    "Táchira": re.compile(r'\b(t[aá]chira|tachirense|san crist[oó]bal|san antonio del t[aá]chira|ure[nñ]a|rubio|t[aá]riba|la grita|puente atanasio girardot|frontera colombo-venezolana)\b', re.IGNORECASE),
    "Falcón": re.compile(r'\b(falc[oó]n|falconiano|falconiana|coro|punto fijo|paraguan[aá]|tucacas|chichiriviche|morrocoy|amuay|card[oó]n|la vela de coro)\b', re.IGNORECASE),
    "Sucre": re.compile(r'\b(sucre|sucrense|cuman[aá]|car[uú]pano|g[uü][ií]ria|araya|golfo de paria|cariaco|marig[uü]itar)\b', re.IGNORECASE),
    "Monagas": re.compile(r'\b(monagas|monaguense|matur[ií]n|el furrial|punta de mata|jusep[ií]n|caripe|uverito)\b', re.IGNORECASE),
    "Nueva Esparta": re.compile(r'\b(nueva esparta|margarita|margarite[nñ]o|margarite[nñ]a|porlamar|pampatar|juan griego|la asunci[oó]n|isla de coche|isla de cubagua)\b', re.IGNORECASE),
    "Portuguesa": re.compile(r'\b(portuguesa|portuguese[nñ]o|portuguese[nñ]a|guanare|acarigua|araure|tur[eé]n|p[ií]ritu|ospino)\b', re.IGNORECASE),
    "Barinas": re.compile(r'\b(barinas|barin[eé]s|barinesa|barinitas|pedraza|santa b[aá]rbara de barinas|socop[oó]|sabaneta)\b', re.IGNORECASE),
    "Mérida": re.compile(r'\b(m[eé]rida|meride[nñ]o|meride[nñ]a|el vig[ií]a|tovar|mucuch[ií]es|sierra nevada|mukumbar[ií]|lagunillas de m[eé]rida)\b', re.IGNORECASE),
    "Trujillo": re.compile(r'\b(trujillo|trujillano|trujillana|valera|bocon[oó]|betijoque|sabana de mendoza|la puerta|monumento a la paz)\b', re.IGNORECASE),
    "Yaracuy": re.compile(r'\b(yaracuy|yaracuyano|yaracuyana|san felipe|yaritagua|chivacoa|nirgua|urachiche)\b', re.IGNORECASE),
    "Guárico": re.compile(r'\b(gu[aá]rico|guarique[nñ]o|guarique[nñ]a|san juan de los morros|calabozo|valle de la pascua|zaraza|altagracia de orituco)\b', re.IGNORECASE),
    "Cojedes": re.compile(r'\b(cojedes|cojede[nñ]o|cojede[nñ]a|san carlos|tinaquillo|tinaco|el ba[uú]l)\b', re.IGNORECASE),
    "Apure": re.compile(r'\b(apure|apure[nñ]o|apure[nñ]a|san fernando de apure|biruaca|guasdualito|achaguas|mantecal|elorza)\b', re.IGNORECASE),
    "Delta Amacuro": re.compile(r'\b(delta amacuro|deltano|deltana|tucupita|pedernales|curiapo|ca[nñ]o manamo)\b', re.IGNORECASE),
    "Amazonas": re.compile(r'\b(amazonas|amazonense|puerto ayacucho|atures|san fernando de atabapo|maroa|r[ií]o negro|orinoco medio)\b', re.IGNORECASE),
    "La Guaira": re.compile(r'\b(la guaira|vargas|guaire[nñ]o|guaire[nñ]a|maiquet[ií]a|catia la mar|macuto|caraballeda|naiguat[aá]|puerto de la guaira)\b', re.IGNORECASE),
    "Guayana Esequiba": re.compile(r'\b(esequibo|esequiba|guayana esequiba|ankoko|tumeremo|r[ií]o cuyun[ií])\b', re.IGNORECASE),
}

# Rutas estándar para auto-descubrimiento de feeds RSS
FEED_PATHS = [
    '/feed',
    '/feed/',
    '/rss',
    '/rss/',
    '/rss.xml',
    '/feed.xml',
    '/index.xml',
    '/atom.xml',
    '/?feed=rss2'
]

def classify_region(title: str, text: str) -> str:
    """Clasifica una noticia por estado según menciones en el título o extracto."""
    combined = f"{title} {text}"
    # Prioridad 1: Detección en el título (mayor peso)
    for state, pattern in REGIONAL_PATTERNS.items():
        if pattern.search(title):
            return state
    # Prioridad 2: Detección en el extracto
    for state, pattern in REGIONAL_PATTERNS.items():
        if pattern.search(combined):
            return state
    return "Nacional"

def clean_html(raw_html: str) -> str:
    """Limpia etiquetas HTML y normaliza espacios en blanco."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ")
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:320]

def parse_iso_date(date_raw) -> str:
    """Convierte cualquier formato de fecha a ISO 8601 UTC estricto."""
    if not date_raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = dateutil.parser.parse(str(date_raw))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()

async def fetch_feed_content(session: aiohttp.ClientSession, base_url: str):
    """Descubre y descarga el feed RSS de un medio con tolerancia a fallos."""
    domain = base_url.strip()
    if not domain.startswith("http"):
        domain = "https://" + domain

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }

    # Probar primero URL directa por si ya incluye ruta de feed
    candidate_urls = [domain] + [urljoin(domain, p) for p in FEED_PATHS]

    for target_url in candidate_urls:
        try:
            async with session.get(target_url, headers=headers, timeout=aiohttp.ClientTimeout(total=8), ssl=False) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get("Content-Type", "").lower()
                    text = await resp.text()
                    if ("xml" in content_type or "<rss" in text or "<feed" in text or "<channel" in text):
                        return text, target_url
        except Exception:
            continue

    return None, None

def parse_feed_items(xml_content: str, media_name: str, base_domain: str):
    """Parsea entradas RSS/Atom con feedparser y fallback a BeautifulSoup."""
    items = []
    feed = feedparser.parse(xml_content)

    if feed.entries:
        for entry in feed.entries[:25]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            clean_summary = clean_html(summary)
            published = getattr(entry, "published", None) or getattr(entry, "updated", None)

            if not title or not link:
                continue

            # Corregir URLs relativas
            if not link.startswith("http"):
                link = urljoin("https://" + base_domain, link)

            items.append({
                "estado_relacionado": classify_region(title, clean_summary),
                "titular": title,
                "medio": media_name,
                "url": link,
                "fecha": parse_iso_date(published),
                "extracto": clean_summary or title
            })
    else:
        # Fallback a BeautifulSoup para XMLs no estándar
        try:
            soup = BeautifulSoup(xml_content, "xml")
            raw_items = soup.find_all("item") or soup.find_all("entry")
            for entry in raw_items[:25]:
                title_tag = entry.find("title")
                link_tag = entry.find("link")
                desc_tag = entry.find("description") or entry.find("summary")
                pub_tag = entry.find("pubDate") or entry.find("updated")

                title = title_tag.get_text(strip=True) if title_tag else ""
                link = ""
                if link_tag:
                    link = link_tag.get("href") or link_tag.get_text(strip=True)
                summary = desc_tag.get_text(strip=True) if desc_tag else ""
                clean_summary = clean_html(summary)

                if title and link:
                    if not link.startswith("http"):
                        link = urljoin("https://" + base_domain, link)
                    items.append({
                        "estado_relacionado": classify_region(title, clean_summary),
                        "titular": title,
                        "medio": media_name,
                        "url": link,
                        "fecha": parse_iso_date(pub_tag.get_text(strip=True) if pub_tag else None),
                        "extracto": clean_summary or title
                    })
        except Exception as e:
            logger.warning(f"Error en fallback BeautifulSoup para {media_name}: {e}")

    return items

async def process_source(session: aiohttp.ClientSession, media_name: str, domain: str):
    """Procesa una fuente individual de manera asíncrona."""
    try:
        content, found_url = await fetch_feed_content(session, domain)
        if content:
            logger.info(f" Feed descubierto para [{media_name}] en: {found_url}")
            return parse_feed_items(content, media_name, domain)
        else:
            logger.warning(f" No se detectó feed público para: {media_name} ({domain})")
            return []
    except Exception as e:
        logger.error(f" Error procesando {media_name}: {e}")
        return []

def load_sources_file(filepath: str):
    """Lee el archivo sources.txt y extrae medios activos."""
    sources = []
    if not os.path.exists(filepath):
        logger.error(f"Archivo no encontrado: {filepath}")
        return sources

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 4:
                category = parts[-1]
                status = parts[-2]
                domain = parts[-3]
                name = " ".join(parts[:-3])
                if status.lower() == "active":
                    sources.append({"name": name, "domain": domain, "category": category})
    return sources

def merge_and_balance_news(new_items: list, existing_items: list, max_total: int = 400) -> list:
    """Combina noticias históricas sin duplicados, balancea por estado y ordena cronológicamente."""
    seen_urls = set()
    combined = []

    # 1. Agregar ítems nuevos primero (más frescos)
    for item in new_items:
        u = item.get("url", "").strip()
        t = item.get("titular", "").lower().strip()
        key = (u, t[:40])
        if key not in seen_urls and u:
            seen_urls.add(key)
            combined.append(item)

    # 2. Agregar histórico previo sin duplicados
    for item in existing_items:
        u = item.get("url", "").strip()
        t = item.get("titular", "").lower().strip()
        key = (u, t[:40])
        if key not in seen_urls and u:
            seen_urls.add(key)
            combined.append(item)

    # 3. Ordenar cronológicamente descendente (más reciente a más antigua)
    combined.sort(key=lambda x: x.get("fecha", ""), reverse=True)

    # 4. Asegurar representación de cada estado (mínimo 2 noticias por estado si existen)
    by_state = {}
    for item in combined:
        st = item.get("estado_relacionado", "Nacional")
        by_state.setdefault(st, []).append(item)

    balanced = []
    # Primero reservar cupo por estado
    for st, items in by_state.items():
        balanced.extend(items[:4])

    # Luego rellenar con las más recientes hasta el tope
    balanced_urls = {x.get("url") for x in balanced}
    for item in combined:
        if len(balanced) >= max_total:
            break
        if item.get("url") not in balanced_urls:
            balanced.append(item)
            balanced_urls.add(item.get("url"))

    # Re-ordenar final
    balanced.sort(key=lambda x: x.get("fecha", ""), reverse=True)
    return balanced[:max_total]

async def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    sources_file = os.path.join(root_dir, "sources.txt")
    data_file = os.path.join(root_dir, "data.json")

    sources = load_sources_file(sources_file)
    logger.info(f"Iniciando pipeline ETL con {len(sources)} fuentes activas...")

    existing_news = []
    if os.path.exists(data_file):
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                existing_news = json.load(f)
                logger.info(f"Cargadas {len(existing_news)} noticias previas desde data.json")
        except Exception as e:
            logger.warning(f"No se pudo cargar data.json previo: {e}")

    # Configuración de sesión con límite de concurrencia
    conn = aiohttp.TCPConnector(limit=15, ssl=False)
    async with aiohttp.ClientSession(connector=conn) as session:
        tasks = [process_source(session, s["name"], s["domain"]) for s in sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    all_scraped = []
    for res in results:
        if isinstance(res, list):
            all_scraped.extend(res)

    logger.info(f"Noticias totales extraídas en este ciclo: {len(all_scraped)}")

    # Combinar, deduplicar y balancear
    final_database = merge_and_balance_news(all_scraped, existing_news, max_total=450)

    # Guardar data.json estricto
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(final_database, f, ensure_ascii=False, indent=2)

    logger.info(f" data.json generado exitosamente con {len(final_database)} noticias.")
    print(f"PIPELINE COMPLETO: data.json listo con {len(final_database)} noticias.")

if __name__ == "__main__":
    asyncio.run(main())
