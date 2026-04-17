import requests

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

def remove_null_values(data):
    return [item for item in data if item["value"] is not None]

if __name__ == "__main__":
    result = get_data_from_api(URL)
    filtered_data = filter_data_by_country(result, "Argentina")
    filtered_data = remove_null_values(filtered_data)
    print(list(enumerate(filtered_data)))