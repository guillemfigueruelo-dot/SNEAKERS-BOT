from dotenv import load_dotenv

load_dotenv()

from config import ALERT_COOLDOWN_HOURS
from scoring import evaluate_opportunity
from storage import mark_alerted, was_recently_alerted
from telegram_bot import send_alert
from tracked_models import load_tracked_models
from trends import get_trend_growth_pct
from vinted_scraper import fetch_listings_for_model


def format_alert(model_name, search_url, evaluation):
    cheapest = evaluation["cheapest_listing"]
    lines = [
        f"\U0001F525 <b>{model_name}</b> — alta demanda / baja oferta",
        f"Anuncios activos (talla 38-41, últimos 7 días): {evaluation['n_listings']}",
        f"Favoritos promedio: {evaluation['avg_favorites']}",
    ]
    if evaluation["avg_price_eur"] is not None:
        lines.append(f"Precio medio: {evaluation['avg_price_eur']} €")
    if evaluation["trend_growth_pct"] is not None:
        lines.append(f"Crecimiento interés (Google Trends, 3 meses): {evaluation['trend_growth_pct']}%")
    if cheapest:
        lines.append(f"Más barato: {cheapest['price_eur']} € (talla {cheapest['size_eu']})")
    lines.append(f"Ver búsqueda en Vinted: {search_url}")
    return "\n".join(lines)


def run():
    tracked_models = load_tracked_models()
    print(f"Modelos a trackear: {len(tracked_models)}")

    for entry in tracked_models:
        brand, model = entry["brand"], entry["model"]
        model_name = f"{brand.title()} {model}"
        print(f"Buscando '{model_name}' en Vinted.es...")

        listings, search_url = fetch_listings_for_model(brand, model)
        print(f"  {len(listings)} anuncios (talla 38-41, <7 días) tras filtrar")

        trend_growth = get_trend_growth_pct(model_name)
        evaluation = evaluate_opportunity(model_name, listings, trend_growth)

        print(
            f"- {model_name}: {evaluation['n_listings']} anuncios, "
            f"{evaluation['avg_favorites']} favs/anuncio, "
            f"trend {evaluation['trend_growth_pct']}%"
        )

        if evaluation["is_opportunity"] and not was_recently_alerted(model_name, ALERT_COOLDOWN_HOURS):
            send_alert(format_alert(model_name, search_url, evaluation))
            mark_alerted(model_name)
            print(f"  -> alerta enviada para {model_name}")


if __name__ == "__main__":
    run()
