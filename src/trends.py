"""
Señal de demanda externa vía Google Trends (pytrends). Gratuito, sin
credenciales, y sin problemas de ToS -- es la fuente de menor riesgo de
las tres que se evaluaron (frente a scraping de StockX/GOAT).

Con muchas búsquedas seguidas en una misma ejecución (una por fila del
CSV), Google empieza a devolver 429 (rate limit) a las pocas peticiones.
Un fallo aquí no debe tumbar el resto de la ejecución: si Trends no
responde, se sigue igualmente con el scoring basado en favoritos (ver
config.HIGH_DEMAND_MIN_AVG_FAVORITES).
"""

import time

from pytrends.request import TrendReq

MAX_RETRIES = 2
RETRY_WAIT_SECONDS = 5


def get_trend_growth_pct(query, timeframe="today 3-m", geo="ES"):
    """
    % de crecimiento del interés de búsqueda: promedio del último cuarto del
    periodo frente al promedio del primer cuarto. None si no hay datos o si
    Google Trends falla (rate limit u otro error de red).
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            pytrends = TrendReq(hl="es-ES", tz=60)
            pytrends.build_payload([query], timeframe=timeframe, geo=geo)
            df = pytrends.interest_over_time()
            break
        except Exception as exc:
            print(f"  Google Trends fallo para '{query}' (intento {attempt}/{MAX_RETRIES}): {exc}")
            if attempt == MAX_RETRIES:
                return None
            time.sleep(RETRY_WAIT_SECONDS)

    if df.empty or query not in df.columns or len(df) < 4:
        return None

    series = df[query]
    quarter = max(len(series) // 4, 1)
    first_avg = series.iloc[:quarter].mean()
    last_avg = series.iloc[-quarter:].mean()

    if first_avg == 0:
        return None
    return ((last_avg - first_avg) / first_avg) * 100
