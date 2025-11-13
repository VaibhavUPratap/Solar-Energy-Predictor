"""Prediction Routes Module.
Defines Flask routes for solar power prediction and history retrieval.
"""
from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
import joblib
import numpy as np

from services import WeatherService, HotspotService, KARNATAKA_LOCATIONS
from services.solar_data import get_solar_data_from_open_meteo, get_fallback_solar_data
from services.predictor import prid as predictor_prid
from database.init_db import insert_prediction, get_recent_predictions
from config import Config

prediction_bp = Blueprint('prediction', __name__)

try:
    model = joblib.load(Config.MODEL_PATH)
    print(f"✓ ML Model loaded successfully from {Config.MODEL_PATH}")
except Exception as e:
    print(f"✗ Error loading ML model: {e}")
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

        weather_data = weather_service.get_weather_by_city(city_name)

        if 'error' in weather_data:
            return jsonify(weather_data), 400

        timezone_offset = int(weather_data.get('timezone') or 0)
        utc_now = datetime.utcnow()
        local_time = utc_now + timedelta(seconds=timezone_offset)

        sunrise_local = None
        sunset_local = None
        sunrise_ts = weather_data.get('sunrise')
        sunset_ts = weather_data.get('sunset')
        if sunrise_ts is not None:
            sunrise_local = datetime.utcfromtimestamp(int(sunrise_ts) + timezone_offset)
        if sunset_ts is not None:
            sunset_local = datetime.utcfromtimestamp(int(sunset_ts) + timezone_offset)

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

        lat = float(weather_data['latitude'])
        lon = float(weather_data['longitude'])

        try:
            solar_data = get_solar_data_from_open_meteo(lat, lon)
        except Exception as exc:
            print(f"⚠ Warning: Open-Meteo fetch failed ({exc}). Using fallback irradiance values.")
            solar_data = get_fallback_solar_data(lat, lon)

        solar_params = {
            'poa_direct': float(solar_data.get('poa_direct', Config.DEFAULT_SOLAR_PARAMS['poa_direct'])),
            'poa_sky_diffuse': float(solar_data.get('poa_sky_diffuse', Config.DEFAULT_SOLAR_PARAMS['poa_sky_diffuse'])),
            'poa_ground_diffuse': float(solar_data.get('poa_ground_diffuse', Config.DEFAULT_SOLAR_PARAMS['poa_ground_diffuse'])),
            'solar_elevation': float(solar_data.get('solar_elevation', Config.DEFAULT_SOLAR_PARAMS['solar_elevation'])),
        }

        ambient_temp = float(solar_data.get('temp_air', weather_data['temp_air']))
        wind_speed = float(solar_data.get('wind_speed', weather_data['wind_speed']))
        night_message = ''
        predicted_power = 0.0

        if is_night:
            solar_params['poa_direct'] = 0.0
            solar_params['poa_sky_diffuse'] = 0.0
            solar_params['poa_ground_diffuse'] = 0.0
            solar_params['solar_elevation'] = 0.0

            local_time_label = local_time.strftime('%H:%M')
            city_label = weather_data.get('city', 'this location')

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
        else:
            cloud_factor = (100 - weather_data['clouds']) / 100.0
            cloud_factor = max(0.0, min(1.0, cloud_factor))
            solar_params['poa_direct'] *= cloud_factor
            solar_params['poa_sky_diffuse'] *= max(0.0, (0.5 + 0.5 * cloud_factor))

            features = np.array([
                [
                    solar_params['poa_direct'],
                    solar_params['poa_sky_diffuse'],
                    solar_params['poa_ground_diffuse'],
                    solar_params['solar_elevation'],
                    wind_speed,
                    ambient_temp
                ]
            ])

            try:
                time_stamp = local_time.hour
                predicted_arr = predictor_prid(
                    model,
                    city_name,
                    time_stamp,
                    solar_params['poa_direct'],
                    solar_params['poa_sky_diffuse'],
                    solar_params['solar_elevation'],
                    wind_speed,
                    ambient_temp
                )
                predicted_power = float(predicted_arr[0])
            except Exception:
                predicted_power = float(model.predict(features)[0])

            next_sunrise_local = None

        predicted_power = max(0, predicted_power)

        db_data = {
            'timestamp': datetime.now().isoformat(),
            'city': weather_data['city'],
            'latitude': weather_data['latitude'],
            'longitude': weather_data['longitude'],
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
            print(f"✓ Prediction saved with ID: {record_id}")
        else:
            print("⚠ Warning: Could not save prediction to database")

        response = {
            'success': True,
            'prediction': {
                'city': weather_data['city'],
                'country': weather_data['country'],
                'latitude': weather_data['latitude'],
                'longitude': weather_data['longitude'],
                'predicted_power': round(predicted_power, 2),
                'unit': 'W',
                'timestamp': db_data['timestamp'],
                'is_night': is_night,
                'local_time': local_time.isoformat(),
                'night_message': night_message,
                'sunrise': sunrise_local.isoformat() if sunrise_local else None,
                'sunset': sunset_local.isoformat() if sunset_local else None,
                'next_sunrise': next_sunrise_local.isoformat() if next_sunrise_local else None
            },
            'weather': {
                'temperature': ambient_temp,
                'wind_speed': wind_speed,
                'clouds': weather_data['clouds'],
                'humidity': weather_data['humidity'],
                'description': weather_data['weather_description'],
                'sunrise': sunrise_local.isoformat() if sunrise_local else None,
                'sunset': sunset_local.isoformat() if sunset_local else None,
                'timezone_offset': timezone_offset
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
        print(f"✗ History retrieval error: {str(e)}")
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
        print(f"✗ Error rendering history page: {str(e)}")
        return render_template('history.html', predictions=[], error=str(e))


@prediction_bp.route('/karnataka-hotspots')
def karnataka_hotspots():
    """Render the Karnataka hotspots page with hourly updates."""
    return render_template('karnataka_hotspots.html')


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
        print(f"✗ Error fetching Karnataka predictions: {exc}")
        return jsonify({
            'error': 'Failed to generate Karnataka predictions',
            'message': str(exc)
        }), 500
