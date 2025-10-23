"""
Prediction Routes Module
Defines Flask routes for solar power prediction and history retrieval
"""
from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
import joblib
import numpy as np
from services import WeatherService
from services.predictor import prid as predictor_prid
from database.init_db import insert_prediction, get_recent_predictions
from config import Config

# Create Blueprint for prediction routes
prediction_bp = Blueprint('prediction', __name__)

# Load ML model at module level (loaded once when app starts)
try:
    model = joblib.load(Config.MODEL_PATH)
    print(f"✓ ML Model loaded successfully from {Config.MODEL_PATH}")
except Exception as e:
    print(f"✗ Error loading ML model: {e}")
    model = None

# Initialize weather service
weather_service = WeatherService()


@prediction_bp.route('/predict', methods=['POST'])
def predict_solar_power():
    """
    Endpoint to predict solar power output for a given city
    
    Expected JSON input:
        {
            "city": "London"
        }
    
    Returns:
        JSON response with prediction results or error message
    """
    try:
        # Check if model is loaded
        if model is None:
            return jsonify({
                'error': 'Model not loaded',
                'message': 'ML model could not be loaded at startup'
            }), 500
        
        # Get request data
        data = request.get_json()
        
        if not data or 'city' not in data:
            return jsonify({
                'error': 'Invalid request',
                'message': 'City name is required'
            }), 400
        
        city_name = data['city'].strip()
        
        if not city_name:
            return jsonify({
                'error': 'Invalid city name',
                'message': 'City name cannot be empty'
            }), 400
        
        # Fetch weather data from OpenWeatherMap API
        weather_data = weather_service.get_weather_by_city(city_name)
        
        # Check if weather data retrieval was successful
        if 'error' in weather_data:
            return jsonify(weather_data), 400
        
        # Use default solar parameters (can be enhanced with real solar API later)
        solar_params = Config.DEFAULT_SOLAR_PARAMS.copy()
        
        # Adjust solar parameters based on cloud coverage
        # Less clouds = more direct irradiance
        cloud_factor = (100 - weather_data['clouds']) / 100.0
        solar_params['poa_direct'] *= cloud_factor
        solar_params['poa_sky_diffuse'] *= (0.5 + 0.5 * cloud_factor)
        
        # Prepare features for ML model prediction
        # Expected features: [poa_direct, poa_sky_diffuse, poa_ground_diffuse, 
        #                     solar_elevation, wind_speed, temp_air]
        features = np.array([[
            solar_params['poa_direct'],
            solar_params['poa_sky_diffuse'],
            solar_params['poa_ground_diffuse'],
            solar_params['solar_elevation'],
            weather_data['wind_speed'],
            weather_data['temp_air']
        ]])
        
        # Make prediction
        # Use the project's `prid` helper which constructs the full feature
        # vector expected by the trained model. We pass the city name as the
        # location identifier and use a simple numeric time stamp (hour).
        try:
            # For the time_stamp we use the hour of day to keep compatibility
            time_stamp = datetime.now().hour
            predicted_arr = predictor_prid(
                model,
                city_name,
                time_stamp,
                solar_params['poa_direct'],
                solar_params['poa_sky_diffuse'],
                solar_params['solar_elevation'],
                weather_data['wind_speed'],
                weather_data['temp_air']
            )

            # predictor_prid returns an array-like; take first element
            predicted_power = float(predicted_arr[0])
        except Exception:
            # As a safe fallback, use the model.predict on the reduced feature set
            predicted_power = model.predict(features)[0]
        
        # Ensure prediction is non-negative
        predicted_power = max(0, predicted_power)
        
        # Prepare data for database storage
        db_data = {
            'timestamp': datetime.now().isoformat(),
            'city': weather_data['city'],
            'latitude': weather_data['latitude'],
            'longitude': weather_data['longitude'],
            'poa_direct': solar_params['poa_direct'],
            'poa_sky_diffuse': solar_params['poa_sky_diffuse'],
            'poa_ground_diffuse': solar_params['poa_ground_diffuse'],
            'solar_elevation': solar_params['solar_elevation'],
            'wind_speed': weather_data['wind_speed'],
            'temp_air': weather_data['temp_air'],
            'predicted_P': round(predicted_power, 2)
        }
        
        # Save prediction to database
        record_id = insert_prediction(Config.DB_PATH, db_data)
        
        if record_id:
            print(f"✓ Prediction saved with ID: {record_id}")
        else:
            print("⚠ Warning: Could not save prediction to database")
        
        # Prepare response
        response = {
            'success': True,
            'prediction': {
                'city': weather_data['city'],
                'country': weather_data['country'],
                'latitude': weather_data['latitude'],
                'longitude': weather_data['longitude'],
                'predicted_power': round(predicted_power, 2),
                'unit': 'W',
                'timestamp': db_data['timestamp']
            },
            'weather': {
                'temperature': weather_data['temp_air'],
                'wind_speed': weather_data['wind_speed'],
                'clouds': weather_data['clouds'],
                'humidity': weather_data['humidity'],
                'description': weather_data['weather_description']
            },
            'solar_parameters': {
                'poa_direct': round(solar_params['poa_direct'], 2),
                'poa_sky_diffuse': round(solar_params['poa_sky_diffuse'], 2),
                'poa_ground_diffuse': round(solar_params['poa_ground_diffuse'], 2),
                'solar_elevation': solar_params['solar_elevation']
            }
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        print(f"✗ Prediction error: {str(e)}")
        return jsonify({
            'error': 'Prediction failed',
            'message': str(e)
        }), 500


@prediction_bp.route('/history', methods=['GET'])
def get_prediction_history():
    """
    Endpoint to retrieve recent prediction history
    
    Returns:
        JSON response with list of recent predictions
    """
    try:
        # Get recent predictions from database
        predictions = get_recent_predictions(Config.DB_PATH, Config.HISTORY_LIMIT)
        
        # Format predictions for response
        formatted_predictions = []
        for pred in predictions:
            formatted_predictions.append({
                'id': pred['id'],
                'timestamp': pred['timestamp'],
                'city': pred['city'],
                'latitude': pred['latitude'],
                'longitude': pred['longitude'],
                'temperature': pred['temp_air'],
                'wind_speed': pred['wind_speed'],
                'predicted_power': pred['predicted_P'],
                'solar_elevation': pred['solar_elevation']
            })
        
        return jsonify({
            'success': True,
            'count': len(formatted_predictions),
            'predictions': formatted_predictions
        }), 200
    
    except Exception as e:
        print(f"✗ History retrieval error: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve history',
            'message': str(e)
        }), 500


@prediction_bp.route('/history-page')
def history_page():
    """
    Render the history page with recent predictions
    
    Returns:
        Rendered HTML template
    """
    try:
        predictions = get_recent_predictions(Config.DB_PATH, Config.HISTORY_LIMIT)
        return render_template('history.html', predictions=predictions)
    
    except Exception as e:
        print(f"✗ Error rendering history page: {str(e)}")
        return render_template('history.html', predictions=[], error=str(e))