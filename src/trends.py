"""
Señal de demanda externa vía Google Trends (pytrends). Gratuito, sin
credenciales, y sin problemas de ToS -- es la fuente de menor riesgo de
las tres que se evaluaron (frente a scraping de StockX/GOAT).
"""

from pytrends.request import TrendReq


def get_trend_growth_pct(query, timeframe="today 3-m", geo="ES"):
    """
    % de crecimiento del interés de búsqueda: promedio del último cuarto del
    periodo frente al promedio del primer cuarto. None si no hay datos.
    """
    pytrends = TrendReq(hl="es-ES", tz=60)
    pytrends.build_payload([query], timeframe=timeframe, geo=geo)
    df = pytrends.interest_over_time()

    if df.empty or query not in df.columns or len(df) < 4:
        return None

    series = df[query]
    quarter = max(len(series) // 4, 1)
    first_avg = series.iloc[:quarter].mean()
    last_avg = series.iloc[-quarter:].mean()

    if first_avg == 0:
        return None
    return ((last_avg - first_avg) / first_avg) * 100
