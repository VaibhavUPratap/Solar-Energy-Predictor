"""
Unit tests for Solar Energy Predictor
Tests prediction routes, weather service, and database operations
"""
import unittest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from config import Config
from services import WeatherService
from database.init_db import init_database, insert_prediction, get_recent_predictions

class TestConfig(Config):
    """Test configuration with test database"""
    TESTING = True
    DB_PATH = 'test_database.db'
    OPENWEATHER_KEY = 'test_api_key'

class TestPredictionRoutes(unittest.TestCase):
    """Test cases for prediction routes"""
    
    def setUp(self):
        """Set up test client and test database"""
        self.app = create_app()
        self.app.config.from_object(TestConfig)
        self.client = self.app.test_client()
        self.db_path = TestConfig.DB_PATH
        
        # Initialize test database
        init_database(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_home_route(self):
        """Test home page loads successfully"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Solar Energy Predictor', response.data)
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/health')
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')
    
    @patch('routes.prediction_routes.weather_service.get_weather_by_city')
    @patch('routes.prediction_routes.model')
    def test_predict_success(self, mock_model, mock_weather):
        """Test successful prediction"""
        # Mock weather service response
        mock_weather.return_value = {
            'city': 'London',
            'country': 'GB',
            'latitude': 51.5074,
            'longitude': -0.1278,
            'temp_air': 18.5,
            'wind_speed': 3.2,
            'clouds': 40,
            'humidity': 65,
            'weather_description': 'scattered clouds'
        }
        
        # Mock model prediction
        mock_model.predict.return_value = [750.0]
        
        # Make request
        response = self.client.post(
            '/api/predict',
            data=json.dumps({'city': 'London'}),
            content_type='application/json'
        )
        
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertEqual(data['prediction']['city'], 'London')
        self.assertIn('predicted_power', data['prediction'])
    
    def test_predict_missing_city(self):
        """Test prediction with missing city parameter"""
        response = self.client.post(
            '/api/predict',
            data=json.dumps({}),
            content_type='application/json'
        )
        
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
    
    def test_predict_empty_city(self):
        """Test prediction with empty city name"""
        response = self.client.post(
            '/api/predict',
            data=json.dumps({'city': ''}),
            content_type='application/json'
        )
        
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
    
    def test_history_endpoint(self):
        """Test history retrieval endpoint"""
        response = self.client.get('/api/history')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data['success'])
        self.assertIn('predictions', data)
        self.assertIn('count', data)


class TestWeatherService(unittest.TestCase):
    """Test cases for weather service"""
    
    def setUp(self):
        """Set up weather service instance"""
        self.service = WeatherService(api_key='test_api_key')
    
    def test_initialization(self):
        """Test weather service initialization"""
        self.assertEqual(self.service.api_key, 'test_api_key')
        self.assertIsNotNone(self.service.base_url)
    
    def test_no_api_key(self):
        """Test weather service without API key"""
        service = WeatherService(api_key=None)
        result = service.get_weather_by_city('London')
        self.assertIn('error', result)
    
    @patch('services.weather_service.requests.get')
    def test_get_weather_success(self, mock_get):
        """Test successful weather data retrieval"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'name': 'London',
            'sys': {'country': 'GB'},
            'coord': {'lat': 51.5074, 'lon': -0.1278},
            'main': {'temp': 18.5, 'feels_like': 17.0, 'humidity': 65, 'pressure': 1013},
            'wind': {'speed': 3.2, 'deg': 180},
            'clouds': {'all': 40},
            'weather': [{'main': 'Clouds', 'description': 'scattered clouds', 'icon': '03d'}],
            'sys': {'sunrise': 1634000000, 'sunset': 1634040000, 'country': 'GB'},
            'timezone': 0
        }
        mock_get.return_value = mock_response
        
        result = self.service.get_weather_by_city('London')
        
        self.assertEqual(result['city'], 'London')
        self.assertEqual(result['temp_air'], 18.5)
        self.assertIn('wind_speed', result)
        self.assertIn('latitude', result)
    
    @patch('services.weather_service.requests.get')
    def test_get_weather_city_not_found(self, mock_get):
        """Test weather retrieval for non-existent city"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        result = self.service.get_weather_by_city('InvalidCity123')
        
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'City not found')
    
    @patch('services.weather_service.requests.get')
    def test_get_weather_timeout(self, mock_get):
        """Test weather retrieval timeout"""
        mock_get.side_effect = Exception('Timeout')
        
        result = self.service.get_weather_by_city('London')
        
        self.assertIn('error', result)


class TestDatabase(unittest.TestCase):
    """Test cases for database operations"""
    
    def setUp(self):
        """Set up test database"""
        self.db_path = 'test_db.db'
        init_database(self.db_path)
    
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
    
    def test_database_initialization(self):
        """Test database is created successfully"""
        self.assertTrue(os.path.exists(self.db_path))
    
    def test_insert_prediction(self):
        """Test inserting prediction into database"""
        test_data = {
            'timestamp': '2025-10-16T10:00:00',
            'city': 'London',
            'latitude': 51.5074,
            'longitude': -0.1278,
            'poa_direct': 800.0,
            'poa_sky_diffuse': 150.0,
            'poa_ground_diffuse': 50.0,
            'solar_elevation': 45.0,
            'wind_speed': 3.2,
            'temp_air': 18.5,
            'predicted_P': 750.0
        }
        
        record_id = insert_prediction(self.db_path, test_data)
        
        self.assertIsNotNone(record_id)
        self.assertIsInstance(record_id, int)
    
    def test_get_recent_predictions(self):
        """Test retrieving recent predictions"""
        # Insert test data
        test_data = {
            'timestamp': '2025-10-16T10:00:00',
            'city': 'London',
            'latitude': 51.5074,
            'longitude': -0.1278,
            'poa_direct': 800.0,
            'poa_sky_diffuse': 150.0,
            'poa_ground_diffuse': 50.0,
            'solar_elevation': 45.0,
            'wind_speed': 3.2,
            'temp_air': 18.5,
            'predicted_P': 750.0
        }
        
        insert_prediction(self.db_path, test_data)
        
        # Retrieve predictions
        predictions = get_recent_predictions(self.db_path, limit=5)
        
        self.assertIsInstance(predictions, list)
        self.assertGreater(len(predictions), 0)
        self.assertEqual(predictions[0]['city'], 'London')


if __name__ == '__main__':
    unittest.main()