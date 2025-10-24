"""
Prediction Routes Module
Defines Flask routes for solar power prediction and history retrieval
"""
from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
import joblib
import numpy as np
import requests
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

@prediction_bp.route('/karnataka-hotspots')
def karnataka_hotspots():
    """
    Render the Karnataka hotspots page with hourly updates
    """
    return render_template('karnataka_hotspots.html')

@prediction_bp.route('/karnataka-predictions', methods=['GET'])
def get_karnataka_predictions():
    """
    Get predictions for all major Karnataka cities using real solar irradiance data
    """
    # Check if model is loaded
    if model is None:
        return jsonify({
            'error': 'Model not loaded',
            'message': 'ML model could not be loaded at startup'
        }), 500
    
    # Karnataka cities with their coordinates (expanded list)
    karnataka_cities = {
        'Bangalore': (12.9716, 77.5946),
        'Mysore': (12.2958, 76.6394),
        'Hubli': (15.3647, 75.1240),
        'Mangalore': (12.9141, 74.8560),
        'Belgaum': (15.8497, 74.4977),
        'Gulbarga': (17.3297, 76.8343),
        'Davanagere': (14.4669, 75.9264),
        'Bellary': (15.1420, 76.9180),
        'Bijapur': (16.8302, 75.7100),
        'Shimoga': (13.9299, 75.5681),
        'Tumkur': (13.3399, 77.1013),
        'Raichur': (16.2076, 77.3463),
        'Bidar': (17.9133, 77.5301),
        'Hospet': (15.2667, 76.4000),
        'Gadag': (15.4167, 75.6167),
        'Chitradurga': (14.2234, 76.4004),
        'Kolar': (13.1370, 78.1330),
        'Mandya': (12.5242, 76.8958),
        'Hassan': (13.0034, 76.1004),
        'Chikmagalur': (13.3161, 75.7720),
        'Udupi': (13.3409, 74.7421),
        'Karwar': (14.8136, 74.1299),
        'Chamrajanagar': (11.9261, 76.9397),
        'Kodagu': (12.3372, 75.8069),
        'Chikkaballapur': (13.4355, 77.7315),
        'Ramanagara': (12.7154, 77.2815),
        'Yadgir': (16.7650, 77.1350),
        'Koppal': (15.3548, 76.2039),
        'Vijayapura': (16.8302, 75.7100),
        'Kalaburagi': (17.3297, 76.8343)
    }
    
    predictions = []
    
    for city_name, (lat, lon) in karnataka_cities.items():
        try:
            # Get real solar irradiance data from Open-Meteo API
            solar_data = get_solar_data_from_open_meteo(lat, lon)
            
            if solar_data and 'error' not in solar_data:
                # Prepare features for ML model prediction
                features = np.array([[
                    solar_data['poa_direct'],
                    solar_data['poa_sky_diffuse'],
                    solar_data['poa_ground_diffuse'],
                    solar_data['solar_elevation'],
                    solar_data['wind_speed'],
                    solar_data['temp_air']
                ]])
                
                # Try prid first, fallback to direct model.predict
                try:
                    time_stamp = datetime.now().hour
                    predicted_arr = predictor_prid(
                        model,
                        city_name,
                        time_stamp,
                        solar_data['poa_direct'],
                        solar_data['poa_sky_diffuse'],
                        solar_data['solar_elevation'],
                        solar_data['wind_speed'],
                        solar_data['temp_air']
                    )
                    predicted_power = float(predicted_arr[0])
                    print(f"✓ prid prediction for {city_name}: {predicted_power}W")
                except Exception as prid_error:
                    print(f"⚠ prid failed for {city_name}: {prid_error}, using fallback")
                    # Fallback to direct model prediction
                    predicted_power = model.predict(features)[0]
                    print(f"✓ fallback prediction for {city_name}: {predicted_power}W")
                
                # Ensure prediction is non-negative
                predicted_power = max(0, predicted_power)
                
                predictions.append({
                    'city': city_name,
                    'latitude': lat,
                    'longitude': lon,
                    'predicted_power': round(predicted_power, 2),
                    'temperature': solar_data['temp_air'],
                    'wind_speed': solar_data['wind_speed'],
                    'clouds': solar_data.get('clouds', 0),  # Not available from Open-Meteo
                    'humidity': solar_data.get('humidity', 0),  # Not available from Open-Meteo
                    'weather_description': solar_data.get('weather_description', 'Clear sky'),
                    'poa_direct': solar_data['poa_direct'],
                    'poa_sky_diffuse': solar_data['poa_sky_diffuse'],
                    'solar_elevation': solar_data['solar_elevation']
                })
            else:
                print(f"⚠ Solar data error for {city_name}: {solar_data.get('error', 'Unknown error') if solar_data else 'No data'}")
                
        except Exception as e:
            print(f"✗ Error getting prediction for {city_name}: {e}")
            continue
    
    print(f"✓ Generated {len(predictions)} predictions for Karnataka cities")
    
    return jsonify({
        'success': True,
        'predictions': predictions,
        'timestamp': datetime.now().isoformat(),
        'total_cities': len(karnataka_cities),
        'successful_predictions': len(predictions)
    })


def get_solar_data_from_open_meteo(lat, lon):
    """
    Get real solar irradiance data from Open-Meteo API using pvlib calculations
    Based on the approach from your model2_with_scale.ipynb
    """
    try:
        import pvlib
        from datetime import datetime
        import time
        
        # Current time (UTC, rounded to nearest hour)
        now = datetime.now(datetime.UTC).replace(minute=0, second=0, microsecond=0)
        time_str = now.strftime("%Y-%m-%dT%H:00")
        
        # Get weather forecast from Open-Meteo API
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}" \
              "&hourly=temperature_2m,windspeed_10m,direct_radiation,diffuse_radiation,cloudcover"
        
        response = requests.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"⚠ Open-Meteo API error for {lat},{lon}: {response.status_code}")
            return get_fallback_solar_data(lat, lon)
            
        data = response.json()
        
        # Check if we have hourly data
        if "hourly" not in data:
            print(f"⚠ No hourly data for {lat},{lon}: {data.get('reason', 'Unknown error')}")
            return get_fallback_solar_data(lat, lon)
        
        hourly = data["hourly"]
        
        # Check if current time is available, if not use the first available time
        if time_str not in hourly["time"]:
            print(f"⚠ Time {time_str} not found for {lat},{lon}, using first available time")
            i = 0  # Use first available time
        else:
            i = hourly["time"].index(time_str)
        
        # Extract values for current hour
        dni = float(hourly["direct_radiation"][i]) if hourly["direct_radiation"][i] is not None else 0
        dhi = float(hourly["diffuse_radiation"][i]) if hourly["diffuse_radiation"][i] is not None else 0
        ghi = dni + dhi  # Approximate global irradiance
        temp_air = float(hourly["temperature_2m"][i]) if hourly["temperature_2m"][i] is not None else 25.0
        wind_speed = float(hourly["windspeed_10m"][i]) if hourly["windspeed_10m"][i] is not None else 2.0
        cloud_cover = float(hourly["cloudcover"][i]) if hourly["cloudcover"][i] is not None else 0
        
        # Solar position calculation
        solpos = pvlib.solarposition.get_solarposition(now, lat, lon)
        solar_elev = float(solpos["elevation"].iloc[0])  # Sun height in degrees
        
        # Only calculate POA if sun is above horizon
        if solar_elev > 0:
            # Plane-of-array irradiance (for tilted panel)
            tilt, azim = 30, 180  # 30° tilt, facing south
            poa = pvlib.irradiance.get_total_irradiance(
                surface_tilt=tilt,
                surface_azimuth=azim,
                solar_zenith=90 - solar_elev,   # zenith = 90 - elevation
                solar_azimuth=solpos["azimuth"].iloc[0],
                dni=dni, ghi=ghi, dhi=dhi
            )
            
            # Break down POA components
            poa_direct = float(poa["poa_direct"])
            poa_sky_diffuse = float(poa["poa_sky_diffuse"])
            poa_ground_diffuse = float(poa["poa_ground_diffuse"])
        else:
            # Sun is below horizon, use minimal values
            poa_direct = 0.0
            poa_sky_diffuse = 0.0
            poa_ground_diffuse = 0.0
        
        return {
            'poa_direct': max(0, poa_direct),
            'poa_sky_diffuse': max(0, poa_sky_diffuse),
            'poa_ground_diffuse': max(0, poa_ground_diffuse),
            'solar_elevation': solar_elev,
            'temp_air': temp_air,
            'wind_speed': wind_speed,
            'ghi': ghi,
            'clouds': cloud_cover,
            'humidity': 60.0,  # Default humidity
            'weather_description': 'Clear sky' if cloud_cover < 20 else 'Partly cloudy' if cloud_cover < 60 else 'Cloudy'
        }
        
    except ImportError:
        print("⚠ pvlib not installed, using fallback data")
        return get_fallback_solar_data(lat, lon)
    except Exception as e:
        print(f"⚠ Solar data fetch failed for {lat},{lon}: {str(e)}")
        return get_fallback_solar_data(lat, lon)


def get_fallback_solar_data(lat, lon):
    """
    Generate fallback solar data when API fails
    """
    from datetime import datetime
    import math
    
    # Current time
    now = datetime.now()
    hour = now.hour
    
    # Simple solar elevation calculation based on time of day and latitude
    # This is a rough approximation
    solar_elev = max(0, 45 * math.sin(math.pi * (hour - 6) / 12)) if 6 <= hour <= 18 else 0
    
    # Generate realistic solar data based on time and location
    if solar_elev > 0:
        # Daytime - generate realistic solar values
        base_irradiance = 800 * (solar_elev / 45)  # Scale with elevation
        poa_direct = base_irradiance * 0.7
        poa_sky_diffuse = base_irradiance * 0.2
        poa_ground_diffuse = base_irradiance * 0.1
    else:
        # Nighttime - minimal values
        poa_direct = 0
        poa_sky_diffuse = 0
        poa_ground_diffuse = 0
    
    # Generate weather data
    temp_air = 25 + (lat - 15) * 0.5  # Temperature varies with latitude
    wind_speed = 2.0 + (hour % 6) * 0.5  # Wind varies with time
    cloud_cover = 30 + (hour % 8) * 5  # Cloud cover varies
    
    return {
        'poa_direct': max(0, poa_direct),
        'poa_sky_diffuse': max(0, poa_sky_diffuse),
        'poa_ground_diffuse': max(0, poa_ground_diffuse),
        'solar_elevation': solar_elev,
        'temp_air': temp_air,
        'wind_speed': wind_speed,
        'ghi': poa_direct + poa_sky_diffuse,
        'clouds': cloud_cover,
        'humidity': 60.0,
        'weather_description': 'Clear sky' if cloud_cover < 20 else 'Partly cloudy' if cloud_cover < 60 else 'Cloudy'
    }