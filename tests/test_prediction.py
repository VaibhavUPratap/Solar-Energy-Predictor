from database.init_db import insert_prediction, get_recent_predictions
from config import Config
import requests
import datetime
import pvlib

# Create Blueprint for prediction routes
prediction_bp = Blueprint('prediction', __name__)

# Initialize weather service
weather_service = WeatherService()

def prid(model_path, loc, time_stamp, poa_direct, poa_sky_diffuse, solar_elevation, wind_speed, temp_air):
    import numpy as np
    from joblib import load
    import json

    # Load model
    model = load(model_path)

    # Load column names (all 246 column names)
    with open("column_names.json", "r") as f:
        column_names = json.load(f)  # list of strings, length 246

    location_names = [name.lower() for name in column_names[:240]]
    loc_lower = loc.lower()

    xi = np.zeros(246)

    if loc_lower != "afzalpur":
        if loc_lower not in location_names:
            raise ValueError(f"Location '{loc}' not found in location list.")
        loc_index = location_names.index(loc_lower)
        xi[loc_index] = 1
    # if loc is afzalpur, all zeros in dummies by default (xi initialized to zeros)

    # Set numeric features
    xi[240] = time_stamp
    xi[241] = poa_direct
    xi[242] = poa_sky_diffuse
    xi[243] = solar_elevation
    xi[244] = wind_speed
    xi[245] = temp_air

    xi = xi.reshape(1, -1)

    prediction = model.predict(xi)
    if prediction<0:
        prediction=0
    return prediction


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

        # --------------------------
        # 1) Location (Bangalore example)
        # --------------------------
        lat, lon = 12.9716, 77.5946

        # --------------------------
        # 2) Current time (UTC, rounded to nearest hour)
        # --------------------------
        now = datetime.datetime.now(datetime.UTC).replace(minute=0, second=0, microsecond=0)
        time_str = now.strftime("%Y-%m-%dT%H:00")   # format like "2025-09-12T08:00" .

        # --------------------------
        # 3) Get weather forecast from API
        # --------------------------
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}" \
            "&hourly=temperature_2m,windspeed_10m,direct_radiation,diffuse_radiation"
        data = requests.get(url).json()   # request + convert to dictionary

        # If no hourly data, stop
        if "hourly" not in data:
            raise RuntimeError(f"No hourly data! Reason: {data.get('reason','Unknown')}")

        hourly = data["hourly"]

        # --------------------------
        # 4) Extract values for current hour
        # --------------------------
        if time_str not in hourly["time"]:
            raise RuntimeError(f"Time {time_str} not found in API data!")

        i = hourly["time"].index(time_str)   # find index of current hour

        dni = float(hourly["direct_radiation"][i])   # Direct normal irradiance
        dhi = float(hourly["diffuse_radiation"][i])  # Diffuse horizontal irradiance
        ghi = dni + dhi                              # Approximate global irradiance
        temp_air = float(hourly["temperature_2m"][i])  # Air temp (°C)
        wind_speed = float(hourly["windspeed_10m"][i]) # Wind speed (m/s)

        # --------------------------
        # 5) Solar position
        # --------------------------
        solpos = pvlib.solarposition.get_solarposition(now, lat, lon)
        solar_elev = float(solpos["elevation"].iloc[0])  # Sun height in degrees

        # --------------------------
        # 6) Plane-of-array irradiance (for tilted panel)
        # --------------------------
        tilt, azim = 30, 180  # 30° tilt, facing south
        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=tilt,
            surface_azimuth=azim,
            solar_zenith=90 - solar_elev,   # zenith = 90 - elevation
            solar_azimuth=solpos["azimuth"].iloc[0],
            dni=dni, ghi=ghi, dhi=dhi
        )

        # Break down POA (plane-of-array) components
        poa_direct = float(poa["poa_direct"])
        poa_sky_diffuse = float(poa["poa_sky_diffuse"])
        poa_ground_diffuse = float(poa["poa_ground_diffuse"])

        # --------------------------
        # 7) Collect results
        # --------------------------
        data_entry = {
            "poa_direct": poa_direct,
            "poa_sky_diffuse": poa_sky_diffuse,
            "poa_ground_diffuse": poa_ground_diffuse,
            "solar_elevation": solar_elev,
            "temp_air": temp_air,
            "wind_speed": wind_speed,
            "Int": ghi   # Intensity (GHI)
        }

        # --------------------------
        # 8) Print nicely
        # --------------------------
        print("Current compatible data entry:")
        for key, val in data_entry.items():
            print(f"{key}: {val}")

        
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
        predicted_power = model.prid(features)[0]
        
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