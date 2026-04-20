import os
import ctypes
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
LIB_PATH = os.path.join(ROOT_DIR, "libgini.so")

lib = ctypes.CDLL(LIB_PATH)
lib.get_value_processed.argtypes = [ctypes.c_double]
lib.get_value_processed.restype = ctypes.c_int

API_URL = (
    "https://api.worldbank.org/v2/en/country/all/indicator/"
    "SI.POV.GINI?format=json&date=2011:2020&per_page=32500&page=1"
)


def get_data_from_api(url=API_URL):
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, list) and len(payload) > 1:
        return payload[1]
    return []


def filter_data_by_country(data, country):
    items_filtered = []
    for item in data:
        if item.get("country", {}).get("value") == country:
            items_filtered.append(item)
    return items_filtered


def get_gini_data(data):
    gini_data = []
    for item in data:
        value = item.get("value")
        if value is not None:
            gini_index = int(lib.get_value_processed(float(value)))
        else:
            gini_index = None
        gini_data.append(gini_index)
    return gini_data


def add_processed_values(data):
    processed_values = get_gini_data(data)
    for item, processed in zip(data, processed_values):
        item["processed_value"] = processed
    return data


def normalize_data(data):
    items = []
    for item in data:
        if not item or not item.get("country") or not item.get("indicator"):
            continue
        items.append(
            {
                "year": item.get("date"),
                "value": item.get("processed_value"),
                "country": item.get("country", {}).get("value"),
                "iso3": item.get("countryiso3code") or "-",
                "indicator": item.get("indicator", {}).get("value"),
            }
        )
    return items


def format_value(value):
    if value is None:
        return "Unknown"
    return value


def build_view_data(selected_country=""):
    data = add_processed_values(get_data_from_api())
    rows = normalize_data(data)
    rows = sorted(rows, key=lambda item: int(item.get("year") or 0), reverse=True)

    countries = sorted({item["country"] for item in rows if item["country"]})

    if selected_country:
        filtered_data = filter_data_by_country(data, selected_country)
        filtered_rows = normalize_data(filtered_data)
        filtered_rows = sorted(
            filtered_rows, key=lambda item: int(item.get("year") or 0), reverse=True
        )
        status_text = f"Showing results for {selected_country}."
    else:
        filtered_rows = rows
        status_text = "Showing results for all countries."

    for item in filtered_rows:
        item["display_value"] = format_value(item.get("value"))

    return {
        "countries": countries,
        "selected_country": selected_country,
        "rows": filtered_rows,
        "total_count": len(rows),
        "filtered_count": len(filtered_rows),
        "status_text": status_text,
    }


if __name__ == "__main__":
    sample = build_view_data("Argentina")
    print(sample["rows"][:3])