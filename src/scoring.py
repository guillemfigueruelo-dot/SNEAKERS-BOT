from config import (
    HIGH_DEMAND_MIN_AVG_FAVORITES,
    HIGH_DEMAND_TREND_GROWTH_PCT,
    LOW_SUPPLY_MAX_LISTINGS,
)


def evaluate_opportunity(model_name, listings, trend_growth_pct):
    n_listings = len(listings)
    avg_favorites = sum(l["favorites"] for l in listings) / n_listings if n_listings else 0
    priced = [l["price_eur"] for l in listings if l["price_eur"] is not None]
    avg_price = sum(priced) / len(priced) if priced else None

    low_supply = 0 < n_listings <= LOW_SUPPLY_MAX_LISTINGS
    high_demand = (
        (trend_growth_pct is not None and trend_growth_pct >= HIGH_DEMAND_TREND_GROWTH_PCT)
        or avg_favorites >= HIGH_DEMAND_MIN_AVG_FAVORITES
    )

    cheapest = min(priced) if priced else None
    cheapest_listing = None
    if cheapest is not None:
        cheapest_listing = next(l for l in listings if l["price_eur"] == cheapest)

    return {
        "model": model_name,
        "n_listings": n_listings,
        "avg_favorites": round(avg_favorites, 1),
        "avg_price_eur": round(avg_price, 2) if avg_price is not None else None,
        "trend_growth_pct": round(trend_growth_pct, 1) if trend_growth_pct is not None else None,
        "low_supply": low_supply,
        "high_demand": high_demand,
        "is_opportunity": low_supply and high_demand,
        "cheapest_listing": cheapest_listing,
    }
