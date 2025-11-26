"""
Configuration file for SolarEnergyPredictor
Loads environment variables and sets application constants
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration class"""
    
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Database settings
    DB_PATH = os.getenv('DB_PATH', 'database/database.db')
    
    # API Keys
    OPENWEATHER_KEY = os.getenv('OPENWEATHER_KEY', '')
    
    # OpenWeather API settings
    OPENWEATHER_BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'
    
    # Model settings
    MODEL_PATH = 'models/Linear_Regression.pkl'
    
    # Default solar parameters (used when real solar data unavailable)
    DEFAULT_SOLAR_PARAMS = {
        'poa_direct': 800.0,          # W/m^2 - Direct irradiance on panel
        'poa_sky_diffuse': 150.0,     # W/m^2 - Diffuse sky irradiance
        'poa_ground_diffuse': 50.0,   # W/m^2 - Ground reflected irradiance
        'solar_elevation': 45.0       # Degrees - Sun angle above horizon
    }
    
    # Application settings
    HISTORY_LIMIT = 10  # Number of predictions to show in history
    HOTSPOT_REFRESH_SECONDS = int(os.getenv('HOTSPOT_REFRESH_SECONDS', '3600'))