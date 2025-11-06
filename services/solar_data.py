"""Solar irradiance data helpers.

Provides functions to retrieve plane-of-array irradiance inputs from Open-Meteo
and to synthesize reasonable fallback values when the API is unavailable.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Dict, Any

import requests
import pvlib


def get_solar_data_from_open_meteo(lat: float, lon: float) -> Dict[str, Any]:
    """Fetch irradiance values for the current hour via Open-Meteo."""
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    time_str = now.strftime("%Y-%m-%dT%H:00")

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=temperature_2m,windspeed_10m,direct_radiation,diffuse_radiation,cloudcover"
    )

    response = requests.get(url, timeout=15)
    if response.status_code != 200:
        raise RuntimeError(f"Open-Meteo status {response.status_code}")

    payload = response.json()
    if "hourly" not in payload:
        raise RuntimeError(payload.get("reason", "Missing hourly block"))

    hourly = payload["hourly"]
    if time_str not in hourly["time"]:
        # Use first available index if exact hour is missing
        idx = 0
    else:
        idx = hourly["time"].index(time_str)

    def _safe_value(key: str, default: float = 0.0) -> float:
        value = hourly.get(key, [default])[idx]
        return float(value) if value is not None else float(default)

    dni = _safe_value("direct_radiation")
    dhi = _safe_value("diffuse_radiation")
    ghi = dni + dhi
    temp_air = _safe_value("temperature_2m", 25.0)
    wind_speed = _safe_value("windspeed_10m", 2.0)
    cloud_cover = _safe_value("cloudcover", 0.0)

    solpos = pvlib.solarposition.get_solarposition(now, lat, lon)
    solar_elev = float(solpos["elevation"].iloc[0])

    if solar_elev > 0:
        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=30,
            surface_azimuth=180,
            solar_zenith=90 - solar_elev,
            solar_azimuth=solpos["azimuth"].iloc[0],
            dni=dni,
            ghi=ghi,
            dhi=dhi,
        )
        poa_direct = float(poa["poa_direct"])
        poa_sky_diffuse = float(poa["poa_sky_diffuse"])
        poa_ground_diffuse = float(poa["poa_ground_diffuse"])
    else:
        poa_direct = 0.0
        poa_sky_diffuse = 0.0
        poa_ground_diffuse = 0.0

    description = "Clear sky"
    if cloud_cover >= 60:
        description = "Cloudy"
    elif cloud_cover >= 20:
        description = "Partly cloudy"

    return {
        "poa_direct": max(0.0, poa_direct),
        "poa_sky_diffuse": max(0.0, poa_sky_diffuse),
        "poa_ground_diffuse": max(0.0, poa_ground_diffuse),
        "solar_elevation": solar_elev,
        "temp_air": temp_air,
        "wind_speed": wind_speed,
        "ghi": ghi,
        "clouds": cloud_cover,
        "humidity": 60.0,
        "weather_description": description,
    }


def get_fallback_solar_data(lat: float, lon: float) -> Dict[str, Any]:
    """Create a deterministic fallback irradiance profile."""
    now = datetime.now(timezone.utc)
    hour = now.hour

    if 6 <= hour <= 18:
        solar_elev = max(0.0, 45 * math.sin(math.pi * (hour - 6) / 12))
        base_irradiance = 800 * (solar_elev / 45) if solar_elev else 0.0
        poa_direct = base_irradiance * 0.7
        poa_sky_diffuse = base_irradiance * 0.2
        poa_ground_diffuse = base_irradiance * 0.1
    else:
        solar_elev = 0.0
        poa_direct = 0.0
        poa_sky_diffuse = 0.0
        poa_ground_diffuse = 0.0

    temp_air = 25 + (lat - 15) * 0.5
    wind_speed = 2.0 + (hour % 6) * 0.5
    cloud_cover = 30 + (hour % 8) * 5

    description = "Clear sky"
    if cloud_cover >= 60:
        description = "Cloudy"
    elif cloud_cover >= 20:
        description = "Partly cloudy"

    return {
        "poa_direct": max(0.0, poa_direct),
        "poa_sky_diffuse": max(0.0, poa_sky_diffuse),
        "poa_ground_diffuse": max(0.0, poa_ground_diffuse),
        "solar_elevation": solar_elev,
        "temp_air": temp_air,
        "wind_speed": wind_speed,
        "ghi": poa_direct + poa_sky_diffuse,
        "clouds": cloud_cover,
        "humidity": 60.0,
        "weather_description": description,
    }


__all__ = ["get_solar_data_from_open_meteo", "get_fallback_solar_data"]
