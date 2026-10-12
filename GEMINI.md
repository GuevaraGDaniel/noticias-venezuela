# Observatorio Económico y Regional de Venezuela — Memoria y Reglas de Proyecto

Este archivo define las reglas inviolables de arquitectura, diseño y datos para el **Observatorio Económico y Regional de Venezuela**. Cualquier agente de IA o desarrollador que trabaje en este proyecto debe cumplir con estos principios.

---

## 1. Alcance General y Misión
El proyecto es una plataforma integral de inteligencia económica y monitoreo de noticias para las 24 entidades federales de Venezuela (+ Guayana Esequiba y Distrito Capital), compuesta por:
1. **Frontend:** Dashboard interactivo corporativo en un único archivo HTML (`index.html`) con visualización geográfica vectorial, animaciones con GSAP y renderizado en tiempo real.
2. **Backend Serverless:** Pipeline ETL automatizado (`scraper.py`) en GitHub Actions que extrae, clasifica y consolida noticias de más de 30 medios dos veces al día en `data.json`.

---

## 2. Reglas Estrictas de Frontend (UI/UX)
- **Tema y Estética:** Estrictamente **Modo Light Corporativo** (`bg-slate-50`, blancos puros, bordes `slate-200`, acentos institucionales en azul `sky-700` y dorado presidencial). Prohibido el modo oscuro.
- **Tipografía Exclusiva:** **Montserrat** (`font-family: 'Montserrat' !important`) aplicada a todos los elementos del DOM. Prohibidas fuentes monoespaciadas para titulares o párrafos.
- **Motor de Mapas:** **Leaflet 1.9** sobre **OpenStreetMap público** (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`).
  - **PROHIBIDO Carto.com** o cualquier servicio que solicite API keys o inserte marcas de agua.
  - El mapa se dibuja con polígonos vectoriales GeoJSON de alta definición y velocidad de renderizado.
- **Comportamiento No Invasivo del Mapa:**
  - **EL MAPA NUNCA SE OCULTA NI SE TAPA.** Al hacer clic sobre cualquier estado, el mapa ejecuta un alejamiento y desplazamiento suave hacia la izquierda con GSAP (`flyToBounds` con compensación en `paddingBottomRight`), haciendo espacio para el panel lateral derecho.
- **Modos del Mapa:** Alternancia fluida con GSAP entre "Mapa Territorial" y "Mapa de Calor" según el volumen de noticias.

---

## 3. Figuras Públicas y Retratos de Gran Formato
- **Presidenta Encargada:** **Delcy Eloína Rodríguez Gómez** destacada en la cabecera superior del panel nacional como Presidenta Encargada de la República, Vicepresidenta Ejecutiva y Ministra de Economía, Finanzas y Comercio Exterior.
  - **Retrato Grande:** Imagen oficial destacada (`w-36 h-48 sm:w-40 sm:h-52`) con marco dorado institucional.
- **Gobernadores de los 24 Estados:** Nómina oficial actualizada en la metadata del proyecto:
  - Amazonas: Miguel Leonardo Rodríguez
  - Anzoátegui: Luis José Marcano
  - Apure: Wilmer Rodríguez
  - Aragua: Joana Sánchez
  - Barinas: Adán Chávez
  - Bolívar: Yulisbeth García
  - Carabobo: Rafael Lacava
  - Cojedes: Alberto Galíndez
  - Delta Amacuro: Loa Tamaronis
  - Falcón: Víctor Clark
  - Guárico: Donald Donaire
  - Guayana Esequiba: Neil Villamizar
  - La Guaira: José Alejandro Terán
  - Lara: Luis Reyes Reyes
  - Mérida: Arnaldo Sánchez
  - Miranda: Elio Serrano
  - Monagas: Ernesto Luna
  - Nueva Esparta: Marisel Velásquez
  - Portuguesa: Antonio Cedeño (Primitivo)
  - Sucre: Jhoanna Carrillo
  - Táchira: Freddy Bernal
  - Trujillo: Gerardo Márquez
  - Yaracuy: Leonardo Intoci
  - Zulia: Luis Caldera
  - Distrito Capital: Nahum Fernández
- **Retratos Grandes de Gobernadores:** En la ficha de cada estado, la foto del mandatario debe ser de gran formato (`w-36 h-48 sm:w-40 sm:h-52`), con su fecha oficial de inicio de funciones, partido y botón directo a su cuenta de Instagram (`@usuario`).
- **Tolerancia a Fallos de Imágenes:** Uso de generador vectorial SVG en línea (`createInstitutionalSvgAvatar`) para garantizar que nunca se vean iconos rotos en caso de bloqueos por CORS o servidores externos.

---

## 4. Fuentes de Noticias y Tratamiento Equitativo
- **Tratamiento Equitativo:** Los 30+ medios nacionales y regionales (Banca y Negocios, Finanzas Digital, Descifrado, Versión Final, El Carabobeño, El Impulso, Correo del Caroní, El Tiempo, La Mañana, etc.) reciben igual peso e importancia según la región que cubren.
- **Enlaces Directos Reales:** Todas las tarjetas de noticias deben incluir enlaces permanentes directos (`item.url` abriendo con `target="_blank"`), nunca enlaces genéricos a la página principal del medio.
- **Logos Dinámicos:** Extracción automática de favicons vía Google Favicons API (`https://s2.googleusercontent.com/s2/favicons?domain=...&sz=64`).
- **Extracto Truncado:** Máximo 3 líneas de texto con clase `line-clamp-3`.

---

## 5. Backend Serverless y Contrato de Datos (data.json)
- **Repositorio:** `GuevaraGDaniel/noticias-venezuela` en GitHub.
- **Automatización:** GitHub Actions (`.github/workflows/update_news.yml`) programado a las `0 10,22 * * * UTC` con permisos `contents: write`.
- **Motor ETL (`scraper.py`):**
  - Concurrencia asíncrona con `aiohttp` y `asyncio`.
  - Descubrimiento dinámico de feeds (`/feed`, `/rss`, `/atom.xml`, etc.).
  - Parser dual con `feedparser` y fallback en `BeautifulSoup4`.
  - Clasificación geográfica con Regex de 24 estados, capitales y gentilicios populares (*marabino, guaro, caraqueño, gocho, etc.*).
  - Acumulación histórica deduplicada y balanceo regional.
- **Contrato de Datos Estricto (`data.json`):**
  ```json
  [
    {
      "estado_relacionado": "Zulia",
      "titular": "Título limpio de la noticia",
      "medio": "Nombre del Medio",
      "url": "https://...",
      "fecha": "2026-10-12T14:30:00+00:00",
      "extracto": "Resumen limpio de hasta 300 caracteres"
    }
  ]
  ```
- **Consumo en Frontend:**
  1. `./data.json` local (desarrollo/servidor local).
  2. `https://cdn.jsdelivr.net/gh/GuevaraGDaniel/noticias-venezuela@main/data.json` (CDN de alta velocidad y libre de CORS).
  3. `https://raw.githubusercontent.com/GuevaraGDaniel/noticias-venezuela/main/data.json` (Fallback directo).
  4. Base de respaldo integrada si la conexión no está disponible.
