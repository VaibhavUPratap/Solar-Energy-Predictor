# 🌞 Solar Energy Predictor

A production-ready Flask web application that predicts real-time solar power output using machine learning and live weather data.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Features

- 🤖 **AI-Powered Predictions**: Uses trained ML model for solar power forecasting
- 🌍 **Real-Time Weather Data**: Fetches live weather from OpenWeatherMap API
- 🗺️ **Interactive Map**: Leaflet.js integration for location visualization
- 💾 **SQLite Database**: Stores prediction history with timestamps
- 📊 **History Tracking**: View past predictions with detailed metrics
- 🎨 **Modern UI**: Responsive design with dark theme
- 🔧 **Modular Architecture**: Clean separation of concerns

## 🏗️ Project Structure

```
SolarEnergyPredictor/
├── database/
│   ├── database.db          # SQLite database (auto-created)
│   └── init_db.py          # Database initialization script
├── models/
│   └── Linear_Regression.pkl  # Trained ML model
├── routes/
│   ├── __init__.py
│   └── prediction_routes.py   # API endpoints
├── services/
│   ├── __init__.py
│   └── weather_service.py     # Weather API integration
├── static/
│   ├── css/
│   │   └── style.css         # Application styles
│   ├── js/
│   │   └── script.js         # Frontend logic
│   └── images/
│       └── logo.png          # Application logo
├── templates/
│   ├── index.html            # Main page
│   └── history.html          # History page
├── tests/
│   └── test_prediction.py    # Unit tests
├── .env                      # Environment variables
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
├── README.md                # This file
├── app.py                   # Flask application factory
├── config.py                # Configuration management
├── requirements.txt         # Python dependencies
└── run.py                   # Application entry point
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- OpenWeatherMap API key ([Get free key](https://openweathermap.org/api))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/SolarEnergyPredictor.git
   cd SolarEnergyPredictor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   # Copy .env template and edit with your API key
   cp .env .env.local
   # Edit .env and add your OPENWEATHER_KEY
   ```

5. **Create ML model file**
   ```python
   # Create a simple trained model (or use your own)
   python -c "
   from sklearn.linear_model import LinearRegression
   import joblib
   import numpy as np
   
   # Create dummy training data
   X = np.random.rand(100, 6) * 1000
   y = X[:, 0] * 0.8 + X[:, 1] * 0.5 + np.random.rand(100) * 50
   
   # Train model
   model = LinearRegression()
   model.fit(X, y)
   
   # Save model
   import os
   os.makedirs('models', exist_ok=True)
   joblib.dump(model, 'models/Linear_Regression.pkl')
   print('✓ Model created successfully')
   "
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

7. **Access the application**
   ```
   Open your browser and navigate to:
   http://127.0.0.1:5000
   ```

## 🔧 Configuration

Edit `.env` file with your settings:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
DB_PATH=database/database.db

# OpenWeatherMap API
OPENWEATHER_KEY=your_api_key_here
```

## 📡 API Endpoints

### POST `/api/predict`
Predict solar power for a city

**Request:**
```json
{
  "city": "London"
}
```

**Response:**
```json
{
  "success": true,
  "prediction": {
    "city": "London",
    "country": "GB",
    "latitude": 51.5074,
    "longitude": -0.1278,
    "predicted_power": 756.42,
    "unit": "W",
    "timestamp": "2025-10-16T10:30:00"
  },
  "weather": {
    "temperature": 18.5,
    "wind_speed": 3.2,
    "clouds": 40,
    "humidity": 65,
    "description": "scattered clouds"
  },
  "solar_parameters": {
    "poa_direct": 480.0,
    "poa_sky_diffuse": 112.5,
    "poa_ground_diffuse": 50.0,
    "solar_elevation": 45.0
  }
}
```

### GET `/api/history`
Retrieve recent predictions

**Response:**
```json
{
  "success": true,
  "count": 10,
  "predictions": [...]
}
```

### GET `/api/history-page`
Renders HTML history page with table of predictions

## 🧪 Testing

Run unit tests:

```bash
python -m pytest tests/
```

Run specific test:

```bash
python -m pytest tests/test_prediction.py -v
```

### Notes about the prid prediction method

- The app supports a custom prediction helper `prid` that builds the full 246-feature
   input vector expected by the trained model. The helper is implemented at
   `services/predictor.py` and used by the `/api/predict` route.
- If `column_names.json` exists in the project root the helper will set the
   one-hot location columns correctly; otherwise it leaves that region of the
   feature vector zeroed (default behavior used by the original reference).
- For environments without `pvlib` installed (test/dev), the repository contains
   a minimal `pvlib.py` stub to allow running tests without installing that dependency.


## 📊 Database Schema

**Table: predictions**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| timestamp | TEXT | Prediction timestamp |
| city | TEXT | City name |
| latitude | REAL | Location latitude |
| longitude | REAL | Location longitude |
| poa_direct | REAL | Direct irradiance (W/m²) |
| poa_sky_diffuse | REAL | Sky diffuse irradiance (W/m²) |
| poa_ground_diffuse | REAL | Ground reflected irradiance (W/m²) |
| solar_elevation | REAL | Sun elevation angle (degrees) |
| wind_speed | REAL | Wind speed (m/s) |
| temp_air | REAL | Air temperature (°C) |
| predicted_P | REAL | Predicted power (W) |

## 🎨 Technologies Used

- **Backend:** Flask 3.0, SQLite
- **Frontend:** HTML5, CSS3, JavaScript, Leaflet.js
- **ML:** Scikit-learn, NumPy, Pandas
- **APIs:** OpenWeatherMap
- **Others:** Python-dotenv, Requests, Flask-CORS

## 🔒 Security Notes

- Never commit `.env` file to version control
- Change `SECRET_KEY` in production
- Use environment variables for sensitive data
- Set `DEBUG=False` in production
- Consider rate limiting for API endpoints

## 🚀 Deployment

### Using Gunicorn (Production)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "run.py"]
```

## 🛠️ Development

### Adding New Features

1. Create feature branch
2. Make changes following project structure
3. Add tests in `tests/` directory
4. Update documentation
5. Submit pull request

### Code Style

- Follow PEP 8 guidelines
- Use descriptive variable names
- Add docstrings to functions
- Comment complex logic

## 📝 Future Enhancements

- [ ] Integration with NASA POWER API for real solar data
- [ ] Multiple ML model support (Random Forest, XGBoost)
- [ ] User authentication and personalized dashboards
- [ ] Export predictions to CSV/PDF
- [ ] Real-time updates using WebSockets
- [ ] Mobile app integration
- [ ] Advanced data visualization (charts, graphs)
- [ ] Multi-language support

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Your Name** - *Initial work*

## 🙏 Acknowledgments

- OpenWeatherMap for weather data API
- Leaflet.js for interactive maps
- Flask community for excellent documentation
- Scikit-learn for ML tools

## 📧 Contact

For questions or support, please contact:
- Email: your.email@example.com
- GitHub: [@yourusername](https://github.com/yourusername)

---

⭐ **Star this repository if you find it helpful!**

Made with ❤️ and ☀️ by the Solar Energy Predictor Team