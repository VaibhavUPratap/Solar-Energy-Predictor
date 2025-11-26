"""
Weather Service Module
Handles API calls to OpenWeatherMap for fetching real-time weather data
"""
import requests
from config import Config

class WeatherService:
    """Service class for weather data retrieval"""
    
    def __init__(self, api_key=None):
        """
        Initialize weather service with API key
        
        Args:
            api_key (str): OpenWeatherMap API key
        """
        self.api_key = api_key or Config.OPENWEATHER_KEY
        self.base_url = Config.OPENWEATHER_BASE_URL
        
        if not self.api_key:
            print("[WARN] No OpenWeatherMap API key provided!")
    
    def get_weather_by_city(self, city_name):
        """
        Fetch weather data for a given city
        
        Args:
            city_name (str): Name of the city
        
        Returns:
            dict: Weather data including coordinates, temperature, wind speed
                  Returns None if request fails
        """
        if not self.api_key:
            return {
                'error': 'API key not configured',
                'message': 'Please set OPENWEATHER_KEY in .env file'
            }
        
        try:
            # Build API request parameters
            params = {
                'q': city_name,
                'appid': self.api_key,
                'units': 'metric'  # Use metric units (Celsius, m/s)
            }
            
            # Make API request
            response = requests.get(self.base_url, params=params, timeout=10)
            
            # Check if request was successful
            if response.status_code == 200:
                data = response.json()
                
                # Extract relevant weather information
                weather_data = {
                    'city': data['name'],
                    'country': data['sys']['country'],
                    'latitude': data['coord']['lat'],
                    'longitude': data['coord']['lon'],
                    'temp_air': data['main']['temp'],  # Temperature in Celsius
                    'temp_feels_like': data['main']['feels_like'],
                    'humidity': data['main']['humidity'],
                    'pressure': data['main']['pressure'],
                    'wind_speed': data['wind']['speed'],  # Wind speed in m/s
                    'wind_deg': data['wind'].get('deg', 0),
                    'clouds': data['clouds']['all'],  # Cloud coverage %
                    'weather_main': data['weather'][0]['main'],
                    'weather_description': data['weather'][0]['description'],
                    'weather_icon': data['weather'][0]['icon'],
                    'sunrise': data['sys']['sunrise'],
                    'sunset': data['sys']['sunset'],
                    'timezone': data['timezone']
                }
                
                return weather_data
            
            elif response.status_code == 404:
                return {
                    'error': 'City not found',
                    'message': f'Could not find weather data for "{city_name}"'
                }
            
            elif response.status_code == 401:
                return {
                    'error': 'Invalid API key',
                    'message': 'Please check your OpenWeatherMap API key'
                }
            
            else:
                return {
                    'error': 'API request failed',
                    'message': f'Status code: {response.status_code}',
                    'details': response.text
                }
        
        except requests.exceptions.Timeout:
            return {
                'error': 'Request timeout',
                'message': 'Weather service took too long to respond'
            }
        
        except requests.exceptions.ConnectionError:
            return {
                'error': 'Connection error',
                'message': 'Could not connect to weather service'
            }
        
        except Exception as e:
            return {
                'error': 'Unexpected error',
                'message': str(e)
            }
    
    def get_weather_by_coordinates(self, lat, lon):
        """
        Fetch weather data for given coordinates
        
        Args:
            lat (float): Latitude
            lon (float): Longitude
        
        Returns:
            dict: Weather data
        """
        if not self.api_key:
            return {
                'error': 'API key not configured'
            }
        
        try:
            params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_weather_data(data)
            else:
                return {
                    'error': 'API request failed',
                    'status_code': response.status_code
                }
        
        except Exception as e:
            return {
                'error': 'Request failed',
                'message': str(e)
            }
    
    def _parse_weather_data(self, data):
        """
        Internal method to parse OpenWeatherMap API response
        
        Args:
            data (dict): Raw API response
        
        Returns:
            dict: Parsed weather data
        """
        return {
            'city': data['name'],
            'latitude': data['coord']['lat'],
            'longitude': data['coord']['lon'],
            'temp_air': data['main']['temp'],
            'wind_speed': data['wind']['speed'],
            'humidity': data['main']['humidity'],
            'clouds': data['clouds']['all']
        }