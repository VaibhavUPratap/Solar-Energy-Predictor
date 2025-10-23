"""
Minimal pvlib stub for local tests.
Provides the small subset of functionality used by the project tests.
This is a fallback for test environments without the real pvlib installed.
"""
from types import SimpleNamespace
import pandas as pd


class solarposition:
    @staticmethod
    def get_solarposition(time, lat, lon):
        # Return a DataFrame-like object with azimuth and elevation
        df = pd.DataFrame({'azimuth': [180.0], 'elevation': [45.0]})
        return df


class irradiance:
    @staticmethod
    def get_total_irradiance(surface_tilt, surface_azimuth, solar_zenith,
                             solar_azimuth, dni, ghi, dhi):
        # Provide a simple decomposition of POA components
        poa_direct = max(0.0, dni * 0.9)
        poa_sky_diffuse = max(0.0, dhi * 1.0)
        poa_ground_diffuse = max(0.0, ghi * 0.05)
        return {
            'poa_direct': poa_direct,
            'poa_sky_diffuse': poa_sky_diffuse,
            'poa_ground_diffuse': poa_ground_diffuse
        }
