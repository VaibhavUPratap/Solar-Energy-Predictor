
from geopy.geocoders import Nominatim
import sys

def test_geocode(loc):
    try:
        # Use a more unique user agent
        user_agent = f"SolarPredictor_App_v1_{loc}"
        print(f"Testing geocoding for '{loc}' with user_agent: {user_agent}")
        geolocator = Nominatim(user_agent=user_agent)
        location = geolocator.geocode(loc)
        if location:
            print(f"[SUCCESS] Location found: {location.address}")
            print(f"Latitude: {location.latitude}, Longitude: {location.longitude}")
        else:
            print(f"[FAILURE] Location '{loc}' not found")
    except Exception as e:
        print(f"[ERROR] Geocoding failed: {e}")

if __name__ == "__main__":
    loc = sys.argv[1] if len(sys.argv) > 1 else "tokyo"
    test_geocode(loc)
