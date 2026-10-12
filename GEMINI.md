# MONITOR PAÍS — Memoria, Reglas y Arquitectura del Proyecto
**Dirección y Desarrollo:** Daniel Guevara

Este archivo define las reglas inviolables de arquitectura, diseño y datos para **MONITOR PAÍS** (Sistema Nacional de Inteligencia y Cobertura Regional de Venezuela). Cualquier agente de IA o desarrollador que trabaje en este proyecto debe cumplir estrictamente con estos principios.

---

## 1. Alcance General y Misión
**MONITOR PAÍS** es una plataforma integral de monitoreo territorial, político y económico en tiempo real para las 24 entidades federales de Venezuela (+ Guayana Esequiba y Distrito Capital) y el Gobierno Nacional, concebida y dirigida por **Daniel Guevara**:
1. **Frontend:** Dashboard corporativo de inteligencia nacional en un único archivo compilado (`index.html`), con:
   - Header en **Azul Marino Corporativo** (`#0B1727`) con el distintivo visible y prestigioso: **DANIEL GUEVARA**.
   - Conmutador de perspectiva: **Visión General País** y **Visión por Estado**.
   - **KPIs en Tiempo Real:** Total de noticias cargadas, medios monitoreados (33+), cobertura federal (24/24 estados).
   - **Termómetro Regional del Día:** Algoritmo dinámico que identifica y destaca qué estado/región concentra el mayor número de noticias, nombramientos o eventos hoy, con barra de temperatura animada y ranking Top 3.
   - **Motion Graphics con GSAP:** Entrada fluida de elementos, contadores numéricos interactivos, animaciones de transición entre vistas y efectos radar.
2. **Backend Serverless:** Pipeline ETL automatizado (`scraper.py`) en GitHub Actions que extrae, clasifica y consolida noticias de más de 30 medios dos veces al día en `data.json`.

---

## 2. Reglas Estrictas de Frontend (UI/UX)
- **Header Corporativo:** Fondo azul marino institucional (`#0B1727`) con insignia tecnológica de monitoreo, distintivo visible de **DANIEL GUEVARA**, reloj HLV en vivo, buscador inteligente y filtros de medios.
- **Cuerpo en Modo Light Corporativo:** (`bg-slate-50`, paneles en blanco puro, bordes `slate-200`, contrastes nítidos).
- **Tipografía Exclusiva:** **Montserrat** (`font-family: 'Montserrat' !important`) en el 100% de la interfaz.
- **Motor de Mapas:** **Leaflet 1.9** sobre **OpenStreetMap público** (`https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png`).
  - **PROHIBIDO Carto.com** o cualquier servicio con API keys o marcas de agua.
  - El mapa se dibuja con polígonos vectoriales GeoJSON de alta velocidad.
- **Comportamiento No Invasivo del Mapa:**
  - El mapa nunca se oculta; se desplaza y reencuadra con GSAP hacia la izquierda (`flyToBounds`) cuando el usuario activa la Visión por Estado.
- **Modos del Mapa:** Alternancia fluida entre "Mapa Territorial" y "Mapa de Calor" según el termómetro de actividad.

---

## 3. Figuras Públicas y Retratos Oficiales de Gran Formato
- **Presidenta Encargada:** **Delcy Eloína Rodríguez Gómez** destacada en la cabecera del panel nacional como Presidenta Encargada de la República, Vicepresidenta Ejecutiva y Ministra de Economía.
  - **Foto Oficial Presidencial:** `https://www.mindefensa.gob.ve/wp-content/uploads/2026/05/IMG-20260513-WA0031-810x1024.jpg` (`./img/gobernadores/delcy_rodriguez.jpg`).
  - **Retrato Grande:** Imagen oficial destacada (`w-40 h-52 sm:w-44 sm:h-56`) con marco dorado presidencial.
- **Gobernadores de los 24 Estados:** Nómina oficial actualizada en la metadata del proyecto con fotos oficiales de alta resolución descargadas localmente en `img/gobernadores/`:
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
- **Retratos Grandes de Gobernadores:** En la ficha de cada estado, la foto del mandatario es de gran formato (`w-44 h-56 sm:w-48 sm:h-60`), con fecha oficial de inicio de funciones, partido y botón directo a su cuenta de Instagram (`@usuario`).
- **Tolerancia a Fallos de Imágenes:** Uso de generador vectorial SVG en línea (`createInstitutionalSvgAvatar`) para garantizar que nunca se vean iconos rotos.

---

## 4. Fuentes de Noticias y Tratamiento Equitativo
- El sistema monitorea 33 medios venezolanos (económicos, nacionales y regionales).
- Todas las noticias del feed cuentan con titular limpio, fecha relativa, dominio, extracto de 3 líneas y enlace permanente directo a la fuente original.
- El usuario puede filtrar por medio específico (Banca y Negocios, Últimas Noticias, El Universal, El Nacional, etc.) o ver el consolidado global.

---

## 5. Pipeline Serverless y Consumo de Datos
- **GitHub Actions:** Orquesta la ejecución dos veces al día (`0 10,22 * * *`).
- **data.json:** Archivo estático versionado en la rama `main` del repositorio `GuevaraGDaniel/noticias-venezuela`.
- **Consumo CDN:** `https://cdn.jsdelivr.net/gh/GuevaraGDaniel/noticias-venezuela@main/data.json` con fallback directo a GitHub Raw y archivo local.
