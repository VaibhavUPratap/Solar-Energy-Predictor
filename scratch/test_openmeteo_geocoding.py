
import requests

def test_openmeteo_geocode(loc):
    try:
        print(f"Testing Open-Meteo geocoding for '{loc}'...")
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={loc}&count=1&language=en&format=json"
        response = requests.get(url)
        data = response.json()
        
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            print(f"[SUCCESS] Location found: {result.get('name')}, {result.get('country')}")
            print(f"Latitude: {result.get('latitude')}, Longitude: {result.get('longitude')}")
            return result.get('latitude'), result.get('longitude')
        else:
            print(f"[FAILURE] Location '{loc}' not found via Open-Meteo")
            return None, None
    except Exception as e:
        print(f"[ERROR] Open-Meteo geocoding failed: {e}")
        return None, None

if __name__ == "__main__":
    test_openmeteo_geocode("tokyo")
    test_openmeteo_geocode("london")
