"""
"Descubrimiento" de modelos en tendencia: en vez de NLP abierto (frágil y
más caro de mantener), usamos listas curadas de familias de modelos
(config.MODEL_KEYWORDS) y colores (config.COLOR_KEYWORDS) y las buscamos
dentro de cada título de anuncio. Es la aproximación pragmática para un MVP
gratuito: ampliar la cobertura es tan simple como añadir palabras clave a
config.py.

El color es lo que convierte "Adidas Samba" (familia genérica, poco útil
como alerta) en "Adidas Samba Verde" (colorway concreto, buscable
literalmente en Vinted para verificar la señal a mano).
"""

from config import COLOR_KEYWORDS, MODEL_KEYWORDS


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


def detect_color(title):
    title_lower = title.lower()
    synonym_pairs = [
        (synonym, canonical)
        for canonical, synonyms in COLOR_KEYWORDS.items()
        for synonym in synonyms
    ]
    # Igual que con los modelos: sinónimos más largos primero para evitar
    # falsos positivos parciales.
    for synonym, canonical in sorted(synonym_pairs, key=lambda pair: len(pair[0]), reverse=True):
        if synonym in title_lower:
            return canonical.title()
    return None


def group_by_model(listings):
    groups = {}
    for listing in listings:
        model = detect_model(listing["brand"], listing["title"])
        if model is None:
            continue

        color = detect_color(listing["title"])
        key = f"{listing['brand'].title()} {model}"
        if color:
            key = f"{key} {color}"

        groups.setdefault(key, []).append(listing)
    return groups
