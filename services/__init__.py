"""
Services package initialization
Exports weather service for easy importing
"""
from .weather_service import WeatherService

__all__ = ['WeatherService']