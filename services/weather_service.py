import requests
import os

API_KEY = os.getenv("OPENWEATHER_KEY", "your_key_here")

def get_weather_data(city):
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    r = requests.get(url).json()

    if "coord" not in r:
        return {"error": "City not found"}

    return {
        "city": city,
        "lat": r["coord"]["lat"],
        "lon": r["coord"]["lon"],
        "temp_air": r["main"]["temp"],
        "wind_speed": r["wind"]["speed"]
    }
