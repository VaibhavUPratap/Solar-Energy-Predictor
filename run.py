"""
Application entry point
Runs the Flask development server
"""
from app import app
from config import Config

if __name__ == '__main__':
    print("\n🌞 Starting SolarEnergyPredictor Server...")
    print(f"🌐 Access the application at: http://127.0.0.1:5000")
    print(f"🔧 Debug mode: {Config.DEBUG}")
    print(f"📊 Database: {Config.DB_PATH}")
    print("\n⏳ Press CTRL+C to stop the server\n")
    
    # Run the Flask development server
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=Config.DEBUG
    )