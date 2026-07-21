"""
"Descubrimiento" de modelos en tendencia: en vez de NLP abierto (frágil y
más caro de mantener), usamos una lista curada de familias de modelos
(config.MODEL_KEYWORDS) y la buscamos dentro de cada título de anuncio. Es
la aproximación pragmática para un MVP gratuito: ampliar la cobertura es
tan simple como añadir palabras clave a config.py.

El "colorway" (p.ej. "OG Night Indigo Blue") NO se clasifica contra una
lista cerrada de colores genéricos -- eso daría nombres como "Adidas Samba
Azul", que no es el nombre real de ningún colorway y no se puede pegar tal
cual en el buscador de Vinted para verificar la señal a mano. En su lugar,
se extrae el texto que sobra en el título del anuncio tras quitar la marca
y el modelo detectados, que es justo lo que un vendedor real escribió y por
tanto lo que hay que buscar en Vinted para reproducir el resultado.

Importante: ese colorway solo se usa para agrupar oferta/favoritos (eso sí
es específico de un colorway concreto). La demanda externa (Google Trends)
se consulta sobre el modelo genérico -- "Nike Dunk Low OG Night Indigo
Blue" apenas tiene volumen de búsqueda propio en Trends, mientras que "Nike
Dunk Low" sí, así que mezclar el colorway en la query de Trends solo
producía falsos negativos.
"""

import re

from config import BRANDS, MODEL_KEYWORDS

# Palabras sin valor como "colorway" que sobran tras quitar marca+modelo
# (tallas, género, tipo de calzado, nexos...). Multi-idioma porque Vinted.es
# mezcla anuncios en español, inglés, italiano y francés.
FILLER_WORDS = {
    "mujer", "hombre", "woman", "women", "unisex", "femme", "donna",
    "nuevo", "nueva", "nuevos", "nuevas", "new",
    "con", "sin", "etiqueta", "etiquetas", "tags", "tag",
    "zapatillas", "zapatos", "sneakers", "trainers", "chaussures",
    "scarpe", "calzado", "shoes", "chaussure", "scarpa",
    "talla", "talle", "size", "eu", "eur",
    "y", "and", "e", "et", "de", "del", "la", "el", "las", "los", "en", "in",
}
SIZE_TOKEN_RE = re.compile(r"^\d{1,2}([.,]\d+)?$")


def match_brand_key(brand):
    """
    El campo "marca" que da Vinted a veces incluye el propio modelo (p.ej.
    "adidas Stan Smith" en vez de solo "adidas"), así que se busca qué marca
    conocida aparece dentro del texto en vez de exigir una coincidencia
    exacta -- si no, esos anuncios se descartaban en silencio.
    """
    brand_lower = brand.lower().strip()
    for known_brand in BRANDS:
        if known_brand in brand_lower:
            return known_brand
    return None


def detect_model(brand, title):
    brand_key = match_brand_key(brand)
    if brand_key is None:
        return None

    keywords = MODEL_KEYWORDS.get(brand_key, [])
    title_lower = title.lower()

    # Las keywords más largas/específicas se comprueban primero para no
    # confundir p.ej. "air max" con "air max 90" cuando ambas encajan.
    for kw in sorted(keywords, key=len, reverse=True):
        if kw in title_lower:
            return kw
    return None


def extract_colorway(brand, model_keyword, title):
    """
    Quita marca y modelo (ambos case-insensitive) del título real del
    anuncio y limpia lo que queda de relleno. Lo que sobra es, por
    construcción, texto que un vendedor escribió describiendo ese anuncio
    concreto -- normalmente el nombre del colorway.
    """
    remainder = re.sub(re.escape(brand), " ", title, flags=re.IGNORECASE)
    remainder = re.sub(re.escape(model_keyword), " ", remainder, flags=re.IGNORECASE)

    tokens = re.split(r"[\s,/;]+", remainder)
    kept = []
    for token in tokens:
        cleaned = token.strip(".-()")
        if not cleaned:
            continue
        if SIZE_TOKEN_RE.match(cleaned):
            continue
        if cleaned.lower() in FILLER_WORDS:
            continue
        kept.append(cleaned)

    phrase = " ".join(kept).strip()
    return phrase or None


def group_by_model(listings):
    """
    Devuelve un dict: nombre_para_mostrar -> {
        "listings": [...],
        "trend_query": "Marca Modelo" (sin colorway, para Google Trends),
    }
    """
    groups = {}
    for listing in listings:
        model_keyword = detect_model(listing["brand"], listing["title"])
        if model_keyword is None:
            continue

        # Se usa la marca "canónica" (nike/adidas), no el campo bruto de
        # Vinted, que a veces ya trae el modelo pegado (ver match_brand_key)
        # y duplicaría texto en el nombre mostrado.
        brand_key = match_brand_key(listing["brand"])
        base_name = f"{brand_key.title()} {model_keyword.title()}"

        colorway = extract_colorway(brand_key, model_keyword, listing["title"])
        display_name = f"{base_name} {colorway}" if colorway else base_name

        group = groups.setdefault(display_name, {"listings": [], "trend_query": base_name})
        group["listings"].append(listing)

    return groups
