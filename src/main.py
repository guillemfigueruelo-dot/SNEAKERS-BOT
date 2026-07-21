from dotenv import load_dotenv

load_dotenv()

from config import ALERT_COOLDOWN_HOURS, BRANDS
from discovery import group_by_model
from scoring import evaluate_opportunity
from storage import mark_alerted, was_recently_alerted
from telegram_bot import send_alert
from trends import get_trend_growth_pct
from vinted_scraper import fetch_listings_for_brand


def format_alert(evaluation):
    cheapest = evaluation["cheapest_listing"]
    lines = [
        f"\U0001F525 <b>{evaluation['model']}</b> — alta demanda / baja oferta",
        f"Anuncios activos (mujer, talla 38-41): {evaluation['n_listings']}",
        f"Favoritos promedio: {evaluation['avg_favorites']}",
    ]
    if evaluation["avg_price_eur"] is not None:
        lines.append(f"Precio medio: {evaluation['avg_price_eur']} €")
    if evaluation["trend_growth_pct"] is not None:
        lines.append(f"Crecimiento interés (Google Trends, 3 meses): {evaluation['trend_growth_pct']}%")
    if cheapest:
        lines.append(f"Más barato: {cheapest['price_eur']} € (talla {cheapest['size_eu']}) → {cheapest['url']}")
    return "\n".join(lines)


def run():
    all_listings = []
    for brand in BRANDS:
        print(f"Buscando {brand} en Vinted.es...")
        listings = fetch_listings_for_brand(brand)
        print(f"  {len(listings)} anuncios (mujer, talla 38-41) tras filtrar")
        all_listings.extend(listings)

    groups = group_by_model(all_listings)
    grouped_count = sum(len(g["listings"]) for g in groups.values())
    print(f"Modelos detectados: {len(groups)} ({grouped_count}/{len(all_listings)} anuncios agrupados)")
    if grouped_count < len(all_listings):
        print(f"  {len(all_listings) - grouped_count} anuncio(s) descartado(s): marca/modelo no reconocido en MODEL_KEYWORDS")

    for model_name, group in groups.items():
        trend_growth = get_trend_growth_pct(group["trend_query"])
        evaluation = evaluate_opportunity(model_name, group["listings"], trend_growth)

        print(
            f"- {model_name}: {evaluation['n_listings']} anuncios, "
            f"{evaluation['avg_favorites']} favs/anuncio, "
            f"trend {evaluation['trend_growth_pct']}%"
        )

        if evaluation["is_opportunity"] and not was_recently_alerted(model_name, ALERT_COOLDOWN_HOURS):
            send_alert(format_alert(evaluation))
            mark_alerted(model_name)
            print(f"  -> alerta enviada para {model_name}")


if __name__ == "__main__":
    run()
