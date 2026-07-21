"""
Scraping de Vinted -- página pública de búsqueda, sin login ni credenciales.

IMPORTANTE (decisión explícita del usuario, no asumida por defecto):
Vinted está detrás de un reto de bot-management de Cloudflare que bloquea
Playwright estándar tanto en headless como con navegador visible (verificado
en vivo). Para poder automatizar esto se usa `patchright`, un fork de
Playwright con parches anti-detección -- es decir, esto **elude
activamente** el sistema anti-bot de Vinted, un escalón de riesgo por
encima del scraping "pasivo" planteado originalmente. El usuario aceptó
este riesgo de forma explícita tras comprobar que la alternativa sin
evasión no funcionaba.

Incluso con patchright el reto no siempre se supera al primer intento
(el scoring de riesgo de Cloudflare es adaptativo) -- por eso hay reintentos
con backoff. Si falla persistentemente, es una señal de que la IP/patrón de
uso se ha marcado como sospechoso y conviene bajar la frecuencia.
"""

import re
import time
from urllib.parse import quote_plus

from patchright.sync_api import sync_playwright

from config import (
    CONDITION_FILTER,
    MAX_LISTING_AGE_DAYS,
    MAX_LISTINGS_PAGES_PER_MODEL,
    SIZE_RANGE_EU,
    VINTED_BASE_URL,
)

# El alt del <img> de cada tarjeta trae toda la info estructurada, p.ej.:
# "Nike Zoom Pegasus 38, marca: Nike, estado: Nuevo con etiquetas, tamaño: 38.5, 40,00 €, 42,70 € Protección al comprador incluida"
ALT_PATTERN = re.compile(
    r"^(?P<title>.+?),\s*marca:\s*(?P<brand>.+?),\s*estado:\s*(?P<condition>.+?),"
    r"\s*tama[nñ]o:\s*(?P<size>[^,]+),\s*(?P<price>[\d.,]+)\s*€",
    re.IGNORECASE,
)
FAVORITES_PATTERN = re.compile(r"favorito de (\d+) usuario", re.IGNORECASE)

# Vinted no da una fecha de publicación en el listado, pero la URL de la
# imagen trae un timestamp que, combinado con order=newest_first, se
# comporta de forma consistente como proxy de antigüedad (verificado en
# vivo). Es una heurística: si cambia el formato de imagen de Vinted, esto
# deja de funcionar silenciosamente (age_days da None y no se filtra).
IMAGE_TIMESTAMP_RE = re.compile(r"/(\d{9,12})\.webp")


def _parse_size(raw):
    raw = raw.strip().replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_price(raw):
    raw = raw.strip().replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_listing_age_days(img_src):
    match = IMAGE_TIMESTAMP_RE.search(img_src or "")
    if not match:
        return None
    photo_epoch = int(match.group(1))
    return (time.time() - photo_epoch) / 86400


def _extract_cards(page):
    cards = page.query_selector_all('[data-testid="grid-item"]')
    listings = []
    for card in cards:
        img = card.query_selector("img[alt]")
        link = card.query_selector('a[href*="/items/"]')
        fav_btn = card.query_selector('button[data-testid$="--favourite"]')
        if not img or not link:
            continue

        alt = img.get_attribute("alt") or ""
        match = ALT_PATTERN.match(alt)
        if not match:
            continue

        size = _parse_size(match.group("size"))
        if size is None or not (SIZE_RANGE_EU[0] <= size <= SIZE_RANGE_EU[1]):
            continue

        condition = match.group("condition").strip()
        if condition.lower() != CONDITION_FILTER:
            continue

        age_days = _parse_listing_age_days(img.get_attribute("src"))
        if age_days is not None and age_days > MAX_LISTING_AGE_DAYS:
            continue

        fav_aria = fav_btn.get_attribute("aria-label") if fav_btn else ""
        fav_match = FAVORITES_PATTERN.search(fav_aria or "")
        favorites = int(fav_match.group(1)) if fav_match else 0

        listings.append(
            {
                "title": match.group("title").strip(),
                "brand": match.group("brand").strip(),
                "condition": condition,
                "size_eu": size,
                "price_eur": _parse_price(match.group("price")),
                "favorites": favorites,
                "url": link.get_attribute("href"),
                "age_days": round(age_days, 1) if age_days is not None else None,
            }
        )
    return listings


CHALLENGE_TITLES = {"just a moment...", "un momento"}
MAX_CHALLENGE_RETRIES = 3


def _goto_with_retries(page, url):
    """
    El reto de Cloudflare no siempre se resuelve al primer intento (scoring
    adaptativo). Reintenta con backoff antes de rendirse.
    """
    for attempt in range(1, MAX_CHALLENGE_RETRIES + 1):
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        title = (page.title() or "").strip().lower()
        if title not in CHALLENGE_TITLES:
            return True
        wait_s = 8 * attempt
        print(f"  Cloudflare challenge detectado (intento {attempt}/{MAX_CHALLENGE_RETRIES}), esperando {wait_s}s...")
        time.sleep(wait_s)
    return False


def build_search_url(brand, model):
    query = quote_plus(f"{brand} {model}")
    return f"{VINTED_BASE_URL}/catalog?search_text={query}&order=newest_first"


def fetch_listings_for_model(brand, model, max_pages=MAX_LISTINGS_PAGES_PER_MODEL):
    """
    Busca "{brand} {model}" literal en Vinted.es, sin restringir a ninguna
    categoría (antes se limitaba a Mujer > Zapatillas de deporte, pero eso
    descartaba anuncios mal categorizados en Vinted). Los únicos filtros
    aplicados son talla 38-41, estado "Nuevo con etiquetas" y antigüedad <=
    MAX_LISTING_AGE_DAYS -- todos en cliente, ya que Vinted no los expone de
    forma fiable en la URL pública.

    Devuelve (listings, search_url) -- search_url es el enlace de búsqueda
    real (no de un anuncio concreto), pensado para que el usuario lo abra y
    verifique la señal él mismo.

    Nota MVP: solo se lee la primera página de resultados por búsqueda.
    """
    search_url = build_search_url(brand, model)
    all_listings = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for page_num in range(1, max_pages + 1):
            url = f"{search_url}&page={page_num}"
            if not _goto_with_retries(page, url):
                print(f"  No se pudo superar el reto de Cloudflare para '{brand} {model}' pág. {page_num}, se omite.")
                break

            try:
                page.wait_for_selector('[data-testid="grid-item"]', timeout=15000)
            except Exception:
                break

            listings = _extract_cards(page)
            # Defensa extra: nos quedamos solo con anuncios cuya marca
            # detectada realmente coincide (search_text no siempre filtra 100%).
            listings = [l for l in listings if brand.lower() in l["brand"].lower()]
            if not listings:
                break

            all_listings.extend(listings)
            time.sleep(2)  # pausa entre páginas, comportamiento no agresivo

        browser.close()

    return all_listings, search_url
