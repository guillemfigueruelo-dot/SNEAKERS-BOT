import os

VINTED_BASE_URL = "https://www.vinted.es"

# Mujer > Calzado > Zapatillas de deporte (confirmado navegando el sitio real)
WOMEN_SPORT_SHOES_CATALOG_ID = 2630
WOMEN_SPORT_SHOES_SLUG = "women_sport_shoes"

BRANDS = ["nike", "adidas"]

SIZE_RANGE_EU = (38.0, 41.0)  # inclusive

# Solo interesan anuncios nuevos con etiquetas (más comparables a precio de
# mercado que un usado, y más fáciles de revender). Se filtra en cliente
# sobre el campo "estado" ya extraído del anuncio.
CONDITION_FILTER = "nuevo con etiquetas"

# Vinted no expone el "modelo" como campo estructurado, así que lo inferimos
# buscando estas familias conocidas dentro del título del anuncio. Ampliar
# esta lista es la forma de "enseñarle" al bot nuevos modelos a vigilar.
MODEL_KEYWORDS = {
    "nike": [
        "air force 1", "air force", "af1",
        "air max 1", "air max 90", "air max 95", "air max 97", "air max plus", "air max",
        "dunk low", "dunk high", "dunk",
        "pegasus", "vomero", "invincible",
        "cortez", "blazer", "waffle", "p-6000", "v2k",
    ],
    "adidas": [
        "samba", "gazelle", "campus 00", "campus", "spezial", "handball spezial",
        "superstar", "stan smith", "sl 72", "forum", "ozweego", "nmd",
    ],
}

MAX_LISTINGS_PAGES_PER_BRAND = 1  # MVP: 1 página (~100 anuncios) por marca, ver notas en vinted_scraper.py

# "oferta baja": pocos anuncios activos del modelo detectado en el rango de tallas
LOW_SUPPLY_MAX_LISTINGS = 3
# "demanda alta": crecimiento de interés en Google Trends por encima de este % (3 meses)
HIGH_DEMAND_TREND_GROWTH_PCT = 20
# ...o alternativamente, favoritos promedio por anuncio por encima de este umbral
HIGH_DEMAND_MIN_AVG_FAVORITES = 5

ALERT_COOLDOWN_HOURS = 24  # no repetir alerta del mismo modelo antes de este tiempo

DB_PATH = os.getenv("DB_PATH", "data/sneakers.db")
