"""
Routes package initialization
Exports prediction blueprint for Flask app registration
"""
from .prediction_routes import prediction_bp

__all__ = ['prediction_bp']