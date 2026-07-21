"""
"Descubrimiento" de modelos en tendencia: en vez de NLP abierto (frágil y
más caro de mantener), usamos una lista curada de familias de modelos
conocidas (config.MODEL_KEYWORDS) y la buscamos dentro de cada título de
anuncio. Es la aproximación pragmática para un MVP gratuito: ampliar la
cobertura es tan simple como añadir palabras clave a config.py.
"""

from config import MODEL_KEYWORDS


def detect_model(brand, title):
    brand_key = brand.lower().strip()
    keywords = MODEL_KEYWORDS.get(brand_key, [])
    title_lower = title.lower()

    # Las keywords más largas/específicas se comprueban primero para no
    # confundir p.ej. "air max" con "air max 90" cuando ambas encajan.
    for kw in sorted(keywords, key=len, reverse=True):
        if kw in title_lower:
            return kw.title()
    return None


def group_by_model(listings):
    groups = {}
    for listing in listings:
        model = detect_model(listing["brand"], listing["title"])
        if model is None:
            continue
        key = f"{listing['brand'].title()} {model}"
        groups.setdefault(key, []).append(listing)
    return groups
