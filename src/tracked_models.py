import csv

from config import TRACKED_MODELS_CSV


def load_tracked_models(path=TRACKED_MODELS_CSV):
    """
    Lee el CSV de modelos a trackear (columnas: brand,model). Cada fila
    define una búsqueda exacta en Vinted -- no hay adivinación de modelo a
    partir del título del anuncio, así que el nombre que verás en la alerta
    es siempre este texto, tal cual lo escribiste.
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            {"brand": row["brand"].strip(), "model": row["model"].strip()}
            for row in reader
            if row.get("brand", "").strip() and row.get("model", "").strip()
        ]
