"""
Main Flask Application Module
Initializes and configures the Flask app with routes and blueprints
"""
import os

from flask import Flask, render_template
from flask_cors import CORS
from config import Config
from routes import prediction_bp
from database.init_db import init_database

def create_app():
    """
    Application factory function to create and configure Flask app
    
    Returns:
        Flask: Configured Flask application instance
    """
    # Initialize Flask app
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Enable CORS for cross-origin requests
    CORS(app)
    
    # Initialize database
    print("\n" + "="*50)
    print("Initializing SolarEnergyPredictor Application")
    print("="*50)
    init_database(Config.DB_PATH)
    
    # Register blueprints
    app.register_blueprint(prediction_bp, url_prefix='/api')
    
    # Home route
    @app.route('/')
    def index():
        """Render the main application page"""
        return render_template('index.html')
    
    # Health check route
    @app.route('/health')
    def health():
        """API health check endpoint"""
        return {
            'status': 'healthy',
            'service': 'SolarEnergyPredictor',
            'version': '1.0.0'
        }
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors"""
        return {
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors"""
        return {
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }, 500
    
    print("[OK] Flask app configured successfully")
    print("="*50 + "\n")
    
    return app


# Create app instance (used by run.py)
app = create_app()

if __name__ == '__main__':
    # This block runs only if app.py is executed directly
    # For production, use run.py instead
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=Config.DEBUG)