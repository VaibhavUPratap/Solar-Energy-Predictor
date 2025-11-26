"""Prediction Routes Module.
Defines Flask routes for solar power prediction and history retrieval.
"""
from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
import joblib
import numpy as np

from services import WeatherService, HotspotService, KARNATAKA_LOCATIONS
from models.pv_data import get_data as get_pv_data
from services.predictor import prid as predictor_prid
from database.init_db import insert_prediction, get_recent_predictions
from config import Config

prediction_bp = Blueprint('prediction', __name__)

try:
    model = joblib.load(Config.MODEL_PATH)
    print(f"[OK] ML Model loaded successfully from {Config.MODEL_PATH}")
except Exception as e:
    print(f"[ERROR] Could not load ML model: {e}")
    model = None

weather_service = WeatherService()

hotspot_service = HotspotService(
    model=model,
    model_path=Config.MODEL_PATH,
    locations=KARNATAKA_LOCATIONS,
    update_interval=getattr(Config, 'HOTSPOT_REFRESH_SECONDS', 3600),
)


@prediction_bp.route('/predict', methods=['POST'])
def predict_solar_power():
    """Endpoint to predict solar power output for a given city."""
    try:
        if model is None:
            return jsonify({
                'error': 'Model not loaded',
                'message': 'ML model could not be loaded at startup'
            }), 500

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

        try:
            # Use integrated user-provided function
            from models.integrated_model import pridictionn
            predicted_power, solar_data = pridictionn(city_name)
        except Exception as e:
            print(f"Error in prediction: {e}")
            return jsonify({
                'error': 'Prediction failed',
                'message': str(e)
            }), 500

        # Extract weather/solar data from metadata returned by pridictionn
        lat = float(solar_data['latitude'])
        lon = float(solar_data['longitude'])
        utc_offset = solar_data.get('utc_offset_seconds', 0)
        timezone_str = solar_data.get('timezone', 'UTC')
        
        # Current time in location's timezone
        utc_now = datetime.utcnow()
        local_time = utc_now + timedelta(seconds=utc_offset)

        # Sunrise/Sunset logic
        sunrise_str = solar_data.get('sunrise')
        sunset_str = solar_data.get('sunset')
        sunrise_local = None
        sunset_local = None
        
        if sunrise_str:
            try:
                sunrise_dt = datetime.fromisoformat(sunrise_str)
                sunrise_local = sunrise_dt
            except ValueError:
                pass

        if sunset_str:
            try:
                sunset_dt = datetime.fromisoformat(sunset_str)
                sunset_local = sunset_dt
            except ValueError:
                pass

        is_night = False
        next_sunrise_local = sunrise_local

        if sunrise_local and sunset_local:
            if local_time < sunrise_local or local_time > sunset_local:
                is_night = True
            if sunrise_local and local_time > sunset_local:
                next_sunrise_local = sunrise_local + timedelta(days=1)
        elif sunrise_local:
            if local_time < sunrise_local:
                is_night = True
        elif sunset_local:
            if local_time > sunset_local:
                is_night = True
            next_sunrise_local = None

        solar_params = {
            'poa_direct': float(solar_data.get('poa_direct', 0.0)),
            'poa_sky_diffuse': float(solar_data.get('poa_sky_diffuse', 0.0)),
            'poa_ground_diffuse': float(solar_data.get('poa_ground_diffuse', 0.0)),
            'solar_elevation': float(solar_data.get('solar_elevation', 0.0)),
        }

        ambient_temp = float(solar_data.get('temp_air', 25.0))
        wind_speed = float(solar_data.get('wind_speed', 1.0))
        cloud_cover = float(solar_data.get('clouds', 0.0))
        humidity = float(solar_data.get('humidity', 50.0))
        weather_code = solar_data.get('weather_code', 0)
        
        # Simple weather description mapping
        weather_description = "Unknown"
        if weather_code == 0: weather_description = "Clear sky"
        elif weather_code in [1, 2, 3]: weather_description = "Partly cloudy"
        elif weather_code in [45, 48]: weather_description = "Fog"
        elif weather_code >= 51: weather_description = "Rain/Snow/Drizzle"

        night_message = ''
        
        # Prediction is already done by pridictionn
        # But we might want to clamp it or apply night logic if pridictionn doesn't?
        # User's pridictionn clamps negative to 0.
        # But does it handle night? It uses solar elevation and radiation.
        # If radiation is 0 (night), prediction should be low/zero.
        # We'll trust the function but enforce max(0, ...) just in case.
        
        if is_night:
            # Force zero if we are sure it's night, to be safe?
            # User function might return small noise.
            # Let's keep the existing night logic for UI consistency.
            predicted_power = 0.0
            
            local_time_label = local_time.strftime('%H:%M')
            city_label = city_name

            if next_sunrise_local:
                sunrise_label = next_sunrise_local.strftime('%H:%M')
                night_message = (
                    f"It is currently night in {city_label} ({local_time_label} local time). "
                    f"Solar output is expected to remain near zero until around {sunrise_label}."
                )
            else:
                night_message = (
                    f"It is currently night in {city_label} ({local_time_label} local time). "
                    "Solar output is expected to be zero."
                )

        predicted_power = max(0, predicted_power)

        db_data = {
            'timestamp': datetime.now().isoformat(),
            'city': city_name,
            'latitude': lat,
            'longitude': lon,
            'poa_direct': solar_params['poa_direct'],
            'poa_sky_diffuse': solar_params['poa_sky_diffuse'],
            'poa_ground_diffuse': solar_params['poa_ground_diffuse'],
            'solar_elevation': solar_params['solar_elevation'],
            'wind_speed': wind_speed,
            'temp_air': ambient_temp,
            'predicted_P': round(predicted_power, 2)
        }

        record_id = insert_prediction(Config.DB_PATH, db_data)

        if record_id:
            print(f"[OK] Prediction saved with ID: {record_id}")
        else:
            print("[WARN] Could not save prediction to database")

        response = {
            'success': True,
            'prediction': {
                'city': city_name,
                'country': "Unknown",
                'latitude': lat,
                'longitude': lon,
                'predicted_power': round(predicted_power, 2),
                'unit': 'W',
                'timestamp': db_data['timestamp'],
                'is_night': is_night,
                'local_time': local_time.isoformat(),
                'next_sunrise': next_sunrise_local.isoformat() if next_sunrise_local else None
            },
            'weather': {
                'temperature': ambient_temp,
                'wind_speed': wind_speed,
                'clouds': cloud_cover,
                'humidity': humidity,
                'description': weather_description,
                'sunrise': sunrise_local.isoformat() if sunrise_local else None,
                'sunset': sunset_local.isoformat() if sunset_local else None,
                'timezone_offset': utc_offset
            },
            'solar_parameters': {
                'poa_direct': round(solar_params['poa_direct'], 2),
                'poa_sky_diffuse': round(solar_params['poa_sky_diffuse'], 2),
                'poa_ground_diffuse': round(solar_params['poa_ground_diffuse'], 2),
                'solar_elevation': solar_params['solar_elevation']
            },
            'night_message': night_message
        }

        return jsonify(response), 200

    except Exception as e:
        print(f"[ERROR] Prediction error: {str(e)}")
        return jsonify({
            'error': 'Prediction failed',
            'message': str(e)
        }), 500


@prediction_bp.route('/history', methods=['GET'])
def get_prediction_history():
    """Endpoint to retrieve recent prediction history."""
    try:
        predictions = get_recent_predictions(Config.DB_PATH, Config.HISTORY_LIMIT)

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
        print(f"[ERROR] History retrieval error: {str(e)}")
        return jsonify({
            'error': 'Failed to retrieve history',
            'message': str(e)
        }), 500


@prediction_bp.route('/history-page')
def history_page():
    """Render the history page with recent predictions."""
    try:
        predictions = get_recent_predictions(Config.DB_PATH, Config.HISTORY_LIMIT)
        return render_template('history.html', predictions=predictions)

    except Exception as e:
        print(f"[ERROR] Error rendering history page: {str(e)}")
        return render_template('history.html', predictions=[], error=str(e))


@prediction_bp.route('/karnataka-hotspots')
def karnataka_hotspots():
    """Render the Karnataka hotspots page with hourly updates."""
    return render_template('karnataka_hotspots.html')


@prediction_bp.route('/karnataka-overview')
def karnataka_overview():
    """Render the detailed overview page for Karnataka hotspots."""
    return render_template('karnataka_overview.html')


@prediction_bp.route('/karnataka-predictions', methods=['GET'])
def get_karnataka_predictions():
    """Generate or reuse cached hotspot predictions for Karnataka cities."""
    try:
        force_refresh = request.args.get('refresh', '').lower() in {'1', 'true', 'yes'}
        predictions, last_update = hotspot_service.get_predictions(force_refresh=force_refresh)
        timestamp = (last_update or datetime.now()).isoformat()

        return jsonify({
            'success': True,
            'predictions': predictions,
            'timestamp': timestamp,
            'total_cities': hotspot_service.location_count,
            'successful_predictions': len(predictions)
        })

    except Exception as exc:
        print(f"[ERROR] Error fetching Karnataka predictions: {exc}")
        return jsonify({
            'error': 'Failed to generate Karnataka predictions',
            'message': str(exc)
        }), 500
