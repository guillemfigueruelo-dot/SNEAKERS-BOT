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

from patchright.sync_api import sync_playwright

from config import (
    CONDITION_FILTER,
    MAX_LISTINGS_PAGES_PER_BRAND,
    SIZE_RANGE_EU,
    VINTED_BASE_URL,
    WOMEN_SPORT_SHOES_CATALOG_ID,
    WOMEN_SPORT_SHOES_SLUG,
)

# El alt del <img> de cada tarjeta trae toda la info estructurada, p.ej.:
# "Nike Zoom Pegasus 38, marca: Nike, estado: Nuevo con etiquetas, tamaño: 38.5, 40,00 €, 42,70 € Protección al comprador incluida"
ALT_PATTERN = re.compile(
    r"^(?P<title>.+?),\s*marca:\s*(?P<brand>.+?),\s*estado:\s*(?P<condition>.+?),"
    r"\s*tama[nñ]o:\s*(?P<size>[^,]+),\s*(?P<price>[\d.,]+)\s*€",
    re.IGNORECASE,
)
FAVORITES_PATTERN = re.compile(r"favorito de (\d+) usuario", re.IGNORECASE)


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

        fav_aria = fav_btn.get_attribute("aria-label") if fav_btn else ""
        fav_match = FAVORITES_PATTERN.search(fav_aria or "")
        favorites = int(fav_match.group(1)) if fav_match else 0

        listings.append(
            {
                "title": match.group("title").strip(),
                "brand": match.group("brand").strip(),
                "condition": match.group("condition").strip(),
                "size_eu": size,
                "price_eur": _parse_price(match.group("price")),
                "favorites": favorites,
                "url": link.get_attribute("href"),
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


def fetch_listings_for_brand(brand, max_pages=MAX_LISTINGS_PAGES_PER_BRAND):
    """
    Devuelve anuncios de Vinted.es en Mujer > Zapatillas de deporte, filtrados
    por marca (vía search_text, verificado contra el sitio real), talla 38-41
    y estado "Nuevo con etiquetas" (ambos filtrados en cliente, ya que Vinted
    no expone estos filtros de forma fiable en la URL pública).

    Nota MVP: solo se lee la primera página de resultados (~100 anuncios) por
    marca. Vinted pagina por scroll infinito dentro de una SPA; automatizar el
    scroll es una mejora de Fase 2, no bloqueante para validar la idea.
    """
    all_listings = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for page_num in range(1, max_pages + 1):
            url = (
                f"{VINTED_BASE_URL}/catalog/{WOMEN_SPORT_SHOES_CATALOG_ID}-{WOMEN_SPORT_SHOES_SLUG}"
                f"?search_text={brand}&page={page_num}"
            )
            if not _goto_with_retries(page, url):
                print(f"  No se pudo superar el reto de Cloudflare para '{brand}' pág. {page_num}, se omite.")
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

    return all_listings
