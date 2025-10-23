"""Unit tests for services.predictor.prid

This test will try to load the project's model file and call prid with
representative inputs. If the model file is missing the test will skip itself.
"""
import os
import numpy as np
from services.predictor import prid

MODEL_PATH = os.path.join('models', 'Linear_Regression.pkl')


def test_prid_returns_non_negative():
    if not os.path.exists(MODEL_PATH):
        print('SKIP: model file not found, skipping prid test')
        return

    # Use a typical city name and reasonable inputs
    city = 'Bangalore'
    time_stamp = 12
    poa_direct = 500.0
    poa_sky_diffuse = 150.0
    solar_elevation = 45.0
    wind_speed = 3.0
    temp_air = 25.0

    pred = prid(MODEL_PATH, city, time_stamp, poa_direct, poa_sky_diffuse,
               solar_elevation, wind_speed, temp_air)

    # Predictor returns array-like
    assert hasattr(pred, '__len__') or np.isscalar(pred)
    val = float(pred[0]) if hasattr(pred, '__len__') else float(pred)
    assert val >= 0
    print('OK: prid returned', val)
