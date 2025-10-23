"""
Prediction helper
Provides a `prid` function compatible with the project's reference implementation.
The function accepts either a model object or a path to a joblib model file.
"""
from typing import Union
import numpy as np
import json
from joblib import load


def prid(model_or_path: Union[str, object], loc: str, time_stamp: float,
         poa_direct: float, poa_sky_diffuse: float, solar_elevation: float,
         wind_speed: float, temp_air: float):
    """
    Build the 246-length feature vector expected by the reference model and
    return the model prediction.

    Args:
        model_or_path: joblib model path or already-loaded model object
        loc: location name (string)
        time_stamp: numeric time feature (e.g. hour or timestamp)
        poa_direct: direct plane-of-array irradiance
        poa_sky_diffuse: sky diffuse component
        solar_elevation: sun elevation in degrees
        wind_speed: m/s
        temp_air: deg C

    Returns:
        numpy array: prediction array from model.predict
    """
    # Load model if a path was provided
    if isinstance(model_or_path, str):
        model = load(model_or_path)
    else:
        model = model_or_path

    # Try to load column names to know which index corresponds to locations.
    # If the file is missing, fall back to putting all-zero dummies (e.g. 'afzalpur').
    try:
        with open('column_names.json', 'r') as f:
            column_names = json.load(f)
    except Exception:
        column_names = None

    xi = np.zeros(246)

    # Handle location dummies if column names are available
    if column_names and len(column_names) >= 240:
        location_names = [name.lower() for name in column_names[:240]]
        loc_lower = (loc or '').lower()
        if loc_lower != 'afzalpur':
            if loc_lower not in location_names:
                raise ValueError(f"Location '{loc}' not found in location list.")
            loc_index = location_names.index(loc_lower)
            xi[loc_index] = 1
    # else: leave first 240 as zeros 

    # Set numeric features at tail indices
    xi[240] = float(time_stamp)
    xi[241] = float(poa_direct)
    xi[242] = float(poa_sky_diffuse)
    xi[243] = float(solar_elevation)
    xi[244] = float(wind_speed)
    xi[245] = float(temp_air)

    xi = xi.reshape(1, -1)

    prediction = model.predict(xi)
    # If model returns negative values, clamp to zero
    try:
        if isinstance(prediction, (list, tuple, np.ndarray)):
            pred = np.array(prediction)
            pred[pred < 0] = 0
            return pred
        else:
            return np.array([max(0, float(prediction))])
    except Exception:
        # Best effort: return raw prediction
        return prediction
