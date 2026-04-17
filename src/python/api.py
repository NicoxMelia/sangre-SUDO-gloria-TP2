import requests
import ctypes

lib = ctypes.CDLL("./libgini.so")

lib.get_value_processed.argtypes = [ctypes.c_double]
lib.get_value_processed.restype  = ctypes.c_int

URL = "https://api.worldbank.org/v2/en/country/all/indicator/SI.POV.GINI?format=json&date=2011:2020&per_page=32500&page=1&country=%22Argentina%22"

def get_data_from_api(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        response = response.json()
        return response[1]
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None
    
def filter_data_by_country(data, country):
    items_filtered = []
    for item in data:
        if item["country"]["value"] == country:
            items_filtered.append(item)
    return items_filtered

def get_gini_data(data):
    gini_data = []
    for item in data:
        value = item["value"]
        if value is not None:
            print("-----------------------------------")
            print(f"Processing value: {value}")
            gini_index = lib.get_value_processed(item["value"])
            print(f"Processed Gini index: {gini_index}")
            print("-----------------------------------")
        gini_data.append(gini_index)
    return gini_data

if __name__ == "__main__":
    result = get_data_from_api(URL)
    filtered_data = filter_data_by_country(result, "Argentina")
    print(get_gini_data(filtered_data))