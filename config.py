import os

class Config:
    WEATHER_API_KEY = os.getenv("OPENWEATHER_KEY")
    DB_PATH = "database/database.db"
