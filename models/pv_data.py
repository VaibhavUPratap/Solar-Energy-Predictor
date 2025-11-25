import csv
import requests
import datetime
import pvlib
from typing import Dict, Any

def get_data(loc: str, now: datetime.datetime = None) -> Dict[str, Any]:
    """Retrieve solar and weather data for a location.
    Returns a dictionary containing poa_direct, poa_sky_diffuse, solar_elevation,
    temp_air, wind_speed, latitude, longitude.
    """
    import os
    # Load location coordinates from results.csv
    csv_path = os.path.join(os.path.dirname(__file__), 'results.csv')
    result = csv.DictReader(open(csv_path))
    # Find the row for the location
    try:
        row = next(r for r in result if r["Location"] == loc)
        lat = float(row["Latitude"])
        lon = float(row["Longitude"])
    except StopIteration:
        # Fallback to geopy if not found in CSV
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="geoapi")
        location = geolocator.geocode(loc)
        if location is None:
            raise ValueError(f"Location '{loc}' not found")
        lat, lon = location.latitude, location.longitude

    # Current UTC hour
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    now = now.replace(minute=0, second=0, microsecond=0)
    time_str = now.strftime("%Y-%m-%dT%H:00")

    # Fetch weather from Open-Meteo
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,windspeed_10m,direct_radiation,diffuse_radiation,cloudcover,relative_humidity_2m,weathercode"
        "&daily=sunrise,sunset&timezone=auto"
    )
    data = requests.get(url, timeout=10).json()
    if "hourly" not in data:
        raise RuntimeError("Missing hourly data from Open-Meteo")
    
    hourly = data["hourly"]
    daily = data.get("daily", {})
    utc_offset_seconds = data.get("utc_offset_seconds", 0)
    timezone_str = data.get("timezone", "UTC")

    # Adjust now to location's local time
    local_now = now + datetime.timedelta(seconds=utc_offset_seconds)
    time_str = local_now.strftime("%Y-%m-%dT%H:00")

    if time_str not in hourly["time"]:
        # Fallback: try UTC if local time fails (unlikely if API works as expected)
        # Or maybe the API returned time in a different format?
        raise RuntimeError(f"Time {time_str} not found in API data (Timezone: {timezone_str})")
    i = hourly["time"].index(time_str)
    
    dni = float(hourly["direct_radiation"][i])
    dhi = float(hourly["diffuse_radiation"][i])
    ghi = dni + dhi
    temp_air = float(hourly["temperature_2m"][i])
    wind_speed = float(hourly["windspeed_10m"][i])
    cloud_cover = float(hourly["cloudcover"][i])
    humidity = float(hourly["relative_humidity_2m"][i])
    weather_code = int(hourly["weathercode"][i])

    # Get sunrise/sunset for today (approximate based on 0th index of daily)
    # Note: Open-Meteo returns daily arrays. We assume the first one is relevant for "now" if "now" is today.
    sunrise = daily["sunrise"][0] if "sunrise" in daily and daily["sunrise"] else None
    sunset = daily["sunset"][0] if "sunset" in daily and daily["sunset"] else None

    # Solar position
    solpos = pvlib.solarposition.get_solarposition(now, lat, lon)
    solar_elev = float(solpos["elevation"].iloc[0])

    # Plane-of-array irradiance
    tilt, azim = 30, 180
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=tilt,
        surface_azimuth=azim,
        solar_zenith=90 - solar_elev,
        solar_azimuth=solpos["azimuth"].iloc[0],
        dni=dni,
        ghi=ghi,
        dhi=dhi,
    )
    poa_direct = float(poa["poa_direct"])
    poa_sky_diffuse = float(poa["poa_sky_diffuse"])
    poa_ground_diffuse = float(poa["poa_ground_diffuse"])

    return {
        "poa_direct": poa_direct,
        "poa_sky_diffuse": poa_sky_diffuse,
        "poa_ground_diffuse": poa_ground_diffuse,
        "solar_elevation": solar_elev,
        "temp_air": temp_air,
        "wind_speed": wind_speed,
        "latitude": lat,
        "longitude": lon,
        "clouds": cloud_cover,
        "humidity": humidity,
        "weather_code": weather_code,
        "sunrise": sunrise,
        "sunset": sunset,
        "timezone": timezone_str,
        "utc_offset_seconds": utc_offset_seconds
    }

__all__ = ["get_data"]
