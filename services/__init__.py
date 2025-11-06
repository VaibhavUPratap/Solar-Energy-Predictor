"""Services package initialization."""
from .weather_service import WeatherService
from .hotspot_service import HotspotService, KARNATAKA_LOCATIONS

__all__ = ['WeatherService', 'HotspotService', 'KARNATAKA_LOCATIONS']