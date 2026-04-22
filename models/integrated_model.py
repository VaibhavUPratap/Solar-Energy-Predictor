import requests
import datetime
import pvlib
import pandas as pd
import numpy as np
import os
import json
from joblib import load

def pridictionn(loc, model=None):
    try:
        base_dir = os.path.dirname(__file__)
        results_path = os.path.join(base_dir, "results.csv")
        result = pd.read_csv(results_path)
        
        # Logic to handle duplicates and fallback to geopy (User's pridictionn2 logic adapted)
        matches = result[result["Location"] == loc]
        if not matches.empty:
            lat = float(matches.Latitude.iloc[0])
            lon = float(matches.Longitude.iloc[0])
        else:
            # Fallback to geopy
            try:
                from geopy.geocoders import Nominatim
                geolocator = Nominatim(user_agent="geoapi")
                location = geolocator.geocode(loc)
                if location:
                    lat, lon = location.latitude, location.longitude
                else:
                    print("loc not found via geopy")
                    raise ValueError(f"Location '{loc}' not found")
            except Exception as e:
                print(f"Geopy error: {e}")
                raise ValueError(f"Location '{loc}' not found and geocoding failed")

        # --------------------------
        # 2) Current time (UTC, rounded to nearest hour)
        # --------------------------
        now = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
        time_str = now.strftime("%Y-%m-%dT%H:00")

        # --------------------------
        # 3) Get weather forecast from API
        # --------------------------
        # Note: User's code uses default timezone (UTC) for hourly data.
        # I am adding extra fields for the UI but keeping the core logic same.
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}" \
              "&hourly=temperature_2m,windspeed_10m,direct_radiation,diffuse_radiation,cloudcover,relative_humidity_2m,weathercode" \
              "&daily=sunrise,sunset&timezone=auto"
        
        data = requests.get(url).json()

        if "hourly" not in data:
            raise RuntimeError(f"No hourly data! Reason: {data.get('reason', 'Unknown')}")

        hourly = data["hourly"]
        daily = data.get("daily", {})
        utc_offset_seconds = data.get("utc_offset_seconds", 0)
        timezone_str = data.get("timezone", "UTC")

        # --------------------------
        # 4) Extract values for current hour
        # --------------------------
        # Adjust for timezone lookup as API returns local time when timezone=auto is used
        local_now = now + datetime.timedelta(seconds=utc_offset_seconds)
        time_str_local = local_now.strftime("%Y-%m-%dT%H:00")
        
        if time_str_local in hourly["time"]:
            i = hourly["time"].index(time_str_local)
        elif time_str in hourly["time"]:
             i = hourly["time"].index(time_str)
        else:
            raise RuntimeError(f"Time {time_str_local} (Local) or {time_str} (UTC) not found in API data!")

        dni = float(hourly["direct_radiation"][i])
        dhi = float(hourly["diffuse_radiation"][i])
        ghi = dni + dhi
        temp_air = float(hourly["temperature_2m"][i])
        wind_speed = float(hourly["windspeed_10m"][i])
        
        # Extras for UI
        cloud_cover = float(hourly["cloudcover"][i]) if "cloudcover" in hourly else 0.0
        humidity = float(hourly["relative_humidity_2m"][i]) if "relative_humidity_2m" in hourly else 0.0
        weather_code = int(hourly["weathercode"][i]) if "weathercode" in hourly else 0
        sunrise = daily["sunrise"][0] if "sunrise" in daily and daily["sunrise"] else None
        sunset = daily["sunset"][0] if "sunset" in daily and daily["sunset"] else None

        # --------------------------
        # 5) Solar position
        # --------------------------
        solpos = pvlib.solarposition.get_solarposition(now, lat, lon)
        solar_elev = float(solpos["elevation"].iloc[0])

        # --------------------------
        # 6) Plane-of-array irradiance
        # --------------------------
        tilt, azim = 30, 180
        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=tilt,
            surface_azimuth=azim,
            solar_zenith=90 - solar_elev,
            solar_azimuth=solpos["azimuth"].iloc[0],
            dni=dni, ghi=ghi, dhi=dhi
        )

        poa_direct = float(poa["poa_direct"])
        poa_sky_diffuse = float(poa["poa_sky_diffuse"])
        poa_ground_diffuse = float(poa["poa_ground_diffuse"])

        # --------------------------
        # 7) Collect results
        # --------------------------
        print("Current compatible data entry:")
        print(f"poa_direct: {poa_direct}")
        print(f"poa_sky_diffuse: {poa_sky_diffuse}")
        print(f"solar_elevation: {solar_elev}")
        print(f"temp_air: {temp_air}")
        print(f"wind_speed: {wind_speed}")

        def prid(loaded_model, loc, time_stamp, poa_direct, poa_sky_diffuse, solar_elev, wind_speed, temp_air):
            # Load column names
            with open(os.path.join(base_dir, "column_names.json"), "r") as f:
                column_names = json.load(f)
        
            location_names = [name.lower() for name in column_names[:240]]
            loc_lower = loc.lower()
        
            xi = np.zeros(246)
            
            # Set numeric features
            xi[240] = time_stamp
            xi[241] = poa_direct
            xi[242] = poa_sky_diffuse
            xi[243] = solar_elev
            xi[244] = wind_speed
            xi[245] = temp_air
        
            if loc_lower != "afzalpur":
                try:
                    loc_index = location_names.index(loc_lower)
                    xi[loc_index] = 1
                except ValueError:
                    print("globel model aactivate")
                    # No dummy variable set, effectively using the base case (or global model behavior)
        
            xi = xi.reshape(1, -1)
            
            prediction = loaded_model.predict(xi)
            if prediction < 0:
                prediction = 0
            return prediction
    
        time_stamp = datetime.datetime.now().month
        
        if model is None:
            model_path = os.path.join(base_dir, "Linear_Regression.pkl")
            model = load(model_path)
            
        ans = prid(model, loc, time_stamp, poa_direct, poa_sky_diffuse, solar_elev, wind_speed, temp_air)

        
        # Metadata for API response
        metadata = {
            "poa_direct": poa_direct,
            "poa_sky_diffuse": poa_sky_diffuse,
            "poa_ground_diffuse": poa_ground_diffuse,
            "solar_elevation": solar_elev,
            "temp_air": temp_air,
            "wind_speed": wind_speed,
            "latitude": lat,
            "longitude": lon,
            "clouds": cloud_cover,
            "humidity": humidity,
            "weather_code": weather_code,
            "sunrise": sunrise,
            "sunset": sunset,
            "timezone": timezone_str,
            "utc_offset_seconds": utc_offset_seconds
        }
        
        # Handle return types safely
        if isinstance(ans, (np.ndarray, np.generic)):
            prediction_value = ans.item()
        else:
            prediction_value = ans
            
        return prediction_value, metadata
        
    except Exception as e:
            print(f"Error in pridictionn: {e}")
            raise e
