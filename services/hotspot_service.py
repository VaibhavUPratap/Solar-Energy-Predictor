"""Hotspot prediction service using the project's ML model."""
from __future__ import annotations

from datetime import datetime, timezone
import threading
from typing import Dict, Iterable, List, Optional, Tuple

from models.integrated_model import pridictionn

KARNATAKA_LOCATIONS: Dict[str, Tuple[float, float]] = {
    "Bengaluru (Bangalore)": (12.9716, 77.5946),
    "Mysore (Mysuru)": (12.2958, 76.6394),
    "Hubballi (Hubli)": (15.3647, 75.1240),
    "Mangaluru (Mangalore)": (12.9141, 74.8560),
    "Kalaburagi (Gulbarga)": (17.3297, 76.8343),
    "Belagavi (Belgaum)": (15.8497, 74.4977),

    # District Headquarters (including existing ones for completeness)
    "Bagalkot": (16.1200, 75.6800),
    "Ballari (Bellary)": (15.1420, 76.9180),
    "Bidar": (17.9133, 77.5301),
    "Chamarajanagar": (11.9261, 76.9397),
    "Chikkaballapur": (13.4355, 77.7315),
    "Chikmagalur": (13.3161, 75.7720),
    "Chitradurga": (14.2234, 76.4004),
    "Davanagere": (14.4669, 75.9264),
    "Dharwad": (15.4578, 75.0078),
    "Gadag": (15.4167, 75.6167),
    "Hassan": (13.0034, 76.1004),
    "Haveri": (14.7950, 75.4047),
    "Kodagu (Madikeri)": (12.4200, 75.7400),
    "Kolar": (13.1370, 78.1330),
    "Koppal": (15.3548, 76.2039),
    "Mandya": (12.5242, 76.8958),
    "Raichur": (16.2076, 77.3463),
    "Ramanagara": (12.7154, 77.2815),
    "Shivamogga (Shimoga)": (13.9299, 75.5681),
    "Tumakuru (Tumkur)": (13.3399, 77.1013),
    "Udupi": (13.3409, 74.7421),
    "Uttara Kannada (Karwar)": (14.8136, 74.1299),
    "Vijayapura (Bijapur)": (16.8302, 75.7100),
    "Yadgir": (16.7650, 77.1350),

    # Other Significant Cities/Towns
    "Hospet": (15.2667, 76.4000), # Vijayanagara District HQ
    "KGF (Kolar Gold Fields)": (12.9667, 78.2700),
    "Channapatna": (12.6469, 77.1979),
    "Harihar": (14.5160, 75.8030),
    "Ranebennur": (14.6190, 75.6170),
    "Chintamani": (13.3960, 78.0770),
}


class HotspotService:
    """Encapsulates Karnataka hotspot prediction refresh logic."""

    def __init__(
        self,
        model: Optional[object] = None,
        model_path: Optional[str] = None,
        locations: Optional[Dict[str, Tuple[float, float]]] = None,
        update_interval: int = 3600,
    ) -> None:
        self._model = model
        self._model_path = model_path
        self._locations = locations or dict(KARNATAKA_LOCATIONS)
        self._update_interval = max(60, int(update_interval))
        self._lock = threading.Lock()
        self._predictions: List[Dict[str, float]] = []
        self._last_update: Optional[datetime] = None

    @property
    def locations(self) -> Dict[str, Tuple[float, float]]:
        return self._locations

    @property
    def location_count(self) -> int:
        return len(self._locations)

    @property
    def last_update(self) -> Optional[datetime]:
        with self._lock:
            return self._last_update

    def get_predictions(self, force_refresh: bool = False) -> Tuple[List[Dict[str, float]], Optional[datetime]]:
        if force_refresh or self._needs_refresh():
            self.update_predictions()
        with self._lock:
            predictions = [dict(item) for item in self._predictions]
            last_update = self._last_update
        return predictions, last_update

    def update_predictions(self) -> List[Dict[str, float]]:
        predictions: List[Dict[str, float]] = []
        timestamp = datetime.now(timezone.utc)

        for city in self._locations.keys():
            try:
                # Use unified prediction function
                predicted_power, solar_data = pridictionn(city)
                
                # Map metadata to expected structure
                weather_code = solar_data.get("weather_code", 0)
                weather_description = "Unknown"
                if weather_code == 0: weather_description = "Clear sky"
                elif weather_code in [1, 2, 3]: weather_description = "Partly cloudy"
                elif weather_code in [45, 48]: weather_description = "Fog"
                elif weather_code >= 51: weather_description = "Rain/Snow/Drizzle"

                record = {
                    "city": city,
                    "latitude": float(solar_data.get("latitude", 0.0)),
                    "longitude": float(solar_data.get("longitude", 0.0)),
                    "predicted_power": round(predicted_power, 2),
                    "temperature": float(solar_data.get("temp_air", 0.0)),
                    "wind_speed": float(solar_data.get("wind_speed", 0.0)),
                    "clouds": float(solar_data.get("clouds", 0.0)),
                    "humidity": float(solar_data.get("humidity", 0.0)),
                    "weather_description": weather_description,
                    "poa_direct": float(solar_data.get("poa_direct", 0.0)),
                    "poa_sky_diffuse": float(solar_data.get("poa_sky_diffuse", 0.0)),
                    "poa_ground_diffuse": float(solar_data.get("poa_ground_diffuse", 0.0)),
                    "solar_elevation": float(solar_data.get("solar_elevation", 0.0)),
                }
                predictions.append(record)
            except Exception as e:
                print(f"Error updating hotspot for {city}: {e}")
                # Skip this city if it fails
                continue

        with self._lock:
            self._predictions = predictions
            self._last_update = timestamp
        return predictions

    def _needs_refresh(self) -> bool:
        with self._lock:
            if not self._predictions or self._last_update is None:
                return True
            age = (datetime.now(timezone.utc) - self._last_update).total_seconds()
        return age >= self._update_interval


__all__ = ["HotspotService", "KARNATAKA_LOCATIONS"]
