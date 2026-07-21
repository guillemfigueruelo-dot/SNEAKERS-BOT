import os

VINTED_BASE_URL = "https://www.vinted.es"

# Mujer > Calzado > Zapatillas de deporte (confirmado navegando el sitio real)
WOMEN_SPORT_SHOES_CATALOG_ID = 2630
WOMEN_SPORT_SHOES_SLUG = "women_sport_shoes"

SIZE_RANGE_EU = (38.0, 41.0)  # inclusive

# Solo interesan anuncios nuevos con etiquetas (más comparables a precio de
# mercado que un usado, y más fáciles de revender). Se filtra en cliente
# sobre el campo "estado" ya extraído del anuncio.
CONDITION_FILTER = "nuevo con etiquetas"

# Vinted no expone una fecha de publicación en el listado de búsqueda. Como
# proxy se usa el timestamp que trae la URL de la imagen de cada anuncio
# (verificado en vivo: con order=newest_first los timestamps salen en orden
# decreciente y el más reciente coincide con la hora actual real). Es una
# heurística, no un dato exacto -- si Vinted cambia el formato de sus URLs
# de imagen, este filtro deja de aplicarse (ver vinted_scraper.py).
MAX_LISTING_AGE_DAYS = 7

# Ruta al CSV con los modelos exactos a trackear (columnas: brand,model).
# Cada fila = una búsqueda literal "{brand} {model}" en Vinted. Sustituye a
# la antigua detección automática de modelo por palabras clave.
TRACKED_MODELS_CSV = os.getenv("TRACKED_MODELS_CSV", "tracked_models.csv")

MAX_LISTINGS_PAGES_PER_MODEL = 1  # MVP: 1 página por modelo, ver notas en vinted_scraper.py

# "oferta baja": pocos anuncios activos del modelo en el rango de tallas
LOW_SUPPLY_MAX_LISTINGS = 3
# "demanda alta": crecimiento de interés en Google Trends por encima de este % (3 meses)
HIGH_DEMAND_TREND_GROWTH_PCT = 20
# ...o alternativamente, favoritos promedio por anuncio por encima de este umbral
HIGH_DEMAND_MIN_AVG_FAVORITES = 5

ALERT_COOLDOWN_HOURS = 24  # no repetir alerta del mismo modelo antes de este tiempo

DB_PATH = os.getenv("DB_PATH", "data/sneakers.db")
