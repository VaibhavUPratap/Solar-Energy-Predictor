"""
Application entry point
Runs the Flask development server
"""
import os

from app import app
from config import Config

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '127.0.0.1')

    print("\n[BOOT] Starting SolarEnergyPredictor Server...")
    print(f"[INFO] Access the application at: http://{host}:{port}")
    print(f"[INFO] Debug mode: {Config.DEBUG}")
    print(f"[INFO] Database: {Config.DB_PATH}")
    print("\n[HINT] Press CTRL+C to stop the server\n")
    
    # Run the Flask development server
    app.run(
        host=host,
        port=port,
        debug=Config.DEBUG
    )