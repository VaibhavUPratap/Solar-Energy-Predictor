"""
Unit tests for the new pv_data module.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import patch, MagicMock
from models.pv_data import get_data

def test_get_data_structure():
    """
    Test that get_data returns a dictionary with the expected keys and types.
    We'll mock the internal requests to avoid hitting the real API during testing.
    """
    # Mock response data for Open-Meteo
    mock_response = {
        "hourly": {
            "time": ["2025-01-01T17:00"],
            "temperature_2m": [25.0],
            "windspeed_10m": [5.0],
            "direct_radiation": [800.0],
            "diffuse_radiation": [100.0],
            "cloudcover": [20.0],
            "relative_humidity_2m": [45.0],
            "weathercode": [1]
        },
        "utc_offset_seconds": 19800,
        "timezone": "Asia/Kolkata"
    }

    # Mock location lookup (geopy)
    mock_location = MagicMock()
    mock_location.latitude = 12.9716
    mock_location.longitude = 77.5946

    with patch('geopy.geocoders.Nominatim') as MockNominatim:
        # Setup mock geolocator
        mock_geolocator = MockNominatim.return_value
        mock_geolocator.geocode.return_value = mock_location

        with patch('requests.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            
            # Create a real datetime object
            import datetime
            fixed_now = datetime.datetime(2025, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)

            # Call the function with fixed time
            result = get_data("Bangalore", now=fixed_now)

            # Verify result is a dict
            assert isinstance(result, dict)
            
            # Check for expected keys
            expected_keys = [
                "poa_direct", "poa_sky_diffuse", "poa_ground_diffuse",
                "solar_elevation", "temp_air", "wind_speed"
            ]
            for key in expected_keys:
                assert key in result
                assert isinstance(result[key], (int, float))

            print("get_data returned:", result)

if __name__ == "__main__":
    test_get_data_structure()
    print("Test passed!")
