# 🌞 Solar Energy Predictor

A production-ready Flask web application that predicts real-time solar power output using machine learning and live weather data.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Features

- 🤖 **AI-Powered Predictions**: Uses trained ML model for solar power forecasting
- 🌍 **Real-Time Weather Data**: Pulls live irradiance + meteorology from Open-Meteo (no API key required)
- 🗺️ **Interactive Map**: Leaflet.js integration for location visualization
- 💾 **MongoDB Database**: Stores prediction history with high scalability
- 📊 **History Tracking**: View past predictions with detailed metrics
- 🎨 **Modern UI**: Responsive design with dark theme
- 🔧 **Modular Architecture**: Clean separation of concerns

## 🏗️ Project Structure

```
SolarEnergyPredictor/
├── database/
│   └── init_db.py          # Database initialization script (MongoDB)
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
- MongoDB (running locally or on Atlas)
- pip (Python package manager)
- Internet access for Open-Meteo and Nominatim APIs (no keys required)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/VaibhavUPratap/Solar-Energy-Predictor.git
     cd Solar-Energy-Predictor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv

### API response format (JSON schemas)

POST `/api/predict` (success)

```json
{
   "success": true,
   "prediction": {
      "city": "London",
      "country": "GB",
      "latitude": 51.5074,
      "longitude": -0.1278,
      "predicted_power": 756.42,    /* number (W) */
      "unit": "W",
      "timestamp": "2025-10-16T10:30:00"
   },
   "weather": {
      "temperature": 18.5,          /* °C */
      "wind_speed": 3.2,            /* m/s */
      "clouds": 40,                 /* % */
      "humidity": 65,               /* % */
      "description": "scattered clouds"
   },
   "solar_parameters": {
      "poa_direct": 480.0,          /* W/m^2 */
      "poa_sky_diffuse": 112.5,     /* W/m^2 */
      "poa_ground_diffuse": 50.0,   /* W/m^2 */
      "solar_elevation": 45.0       /* degrees */
   }
}
```

POST `/api/predict` (error)

```json
{
   "error": "Prediction failed",
   "message": "Detailed error message"
}
```

GET `/api/history` (success)

```json
{
   "success": true,
   "count": 10,
   "predictions": [
      {
         "id": 1,
         "timestamp": "2025-10-16T10:30:00",
         "city": "London",
         "latitude": 51.5074,
         "longitude": -0.1278,
         "temperature": 18.5,
         "wind_speed": 3.2,
         "predicted_power": 756.42
      }
   ]
}
```

   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables (optional)**
   ```bash
   # Copy .env template if you want to override defaults like DB_PATH or DEBUG
   cp .env.example .env
   ```
   The current build does not require any external API keys; weather and irradiance data come from Open-Meteo.

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
   print('[OK] Model created successfully')
   "
   ```

5. **Model training & feature contract**

The application expects a model trained on a specific feature layout:

- The feature vector length is 246.
   - First 240 features are one-hot encodings for locations (location dummy columns).
   - Last 6 features (indices 240..245) are numeric features in this order:
      240: time_stamp (for example, hour of day or a numeric time feature)
      241: poa_direct (W/m^2)
      242: poa_sky_diffuse (W/m^2)
      243: solar_elevation (degrees)
      244: wind_speed (m/s)
      245: temp_air (°C)

It's strongly recommended to train the model with a pandas.DataFrame containing the same column names used at inference time. Save the column names to `column_names.json` so the server's `services.predictor.prid` can construct the correct one-hot vector.

Example training script (recommended approach using DataFrame and column names):

```python
import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

# Example: create dummy column names and training data
location_cols = [f"loc_{i}" for i in range(240)]
numeric_cols = ["time_stamp","poa_direct","poa_sky_diffuse","solar_elevation","wind_speed","temp_air"]
columns = location_cols + numeric_cols  # length 246

# Create dummy data (N x 246)
N = 500
X = np.zeros((N, len(columns)))
# populate some random location dummies and numeric features
for i in range(N):
      loc_idx = np.random.randint(0, 240)
      X[i, loc_idx] = 1
X[:, 240:] = np.random.rand(N, 6) * 1000

df = pd.DataFrame(X, columns=columns)
y = df['poa_direct'] * 0.8 + df['poa_sky_diffuse'] * 0.3 + np.random.rand(N) * 50

# Train model and save with joblib
os.makedirs('models', exist_ok=True)
model = LinearRegression()
model.fit(df, y)
joblib.dump(model, 'models/Linear_Regression.pkl')

# Save column names so the server can reconstruct the 246-length vector
with open('column_names.json', 'w') as f:
      json.dump(columns, f)

print('[OK] Model and column_names.json saved')
```

Notes:

- Saving `column_names.json` is important to allow `services.predictor.prid` to set the correct location dummy column by name.
- Training with a DataFrame that preserves column names avoids sklearn warnings about feature names at inference time.
- Version your model files (include model metadata like training date and scikit-learn version) to avoid unpickling issues across sklearn versions.
6. **Run the application**
   ```bash
   python run.py
   ```

7. **Access the application**
   ```
   Open your browser and navigate to:
   http://127.0.0.1:5000
   ```

## ☁️ Weather & Irradiance Data Sources

- **Open-Meteo Forecast API** supplies hourly temperature, wind, direct and diffuse radiation, cloud cover, humidity, and weather codes. The project requests these fields with `timezone=auto`, so no API key or account is necessary.
- **PVLib** converts the irradiance + solar position into plane-of-array (POA) values that the ML model consumes.
- **Location lookup** comes from the bundled `results.csv` coordinates, and falls back to OpenStreetMap's Nominatim geocoder when needed (again, no API key required).

Because all upstream services are free and keyless, a fresh clone can run predictions immediately as long as the machine has internet access.

## 🔧 Configuration

Edit `.env` file with your settings:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database (MongoDB)
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DB=solar_energy_db

# Weather + irradiance data come from Open-Meteo, so no API key is required.
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

## 🛠️ Developer notes & troubleshooting

If you can't start the app with `python run.py`, try these steps first:

- 1) Check for circular imports
   - A common startup error is an ImportError referencing a "partially initialized module".
   - This repo's app used to export a route from `services.__init__` which caused a circular import.
      Do not import route handlers from `services.__init__`; `services` should only export service classes.

- 2) Run sequence
   ```bash
   # from project root
   python -m venv venv
   venv\Scripts\activate    # Windows
   pip install -r requirements.txt
   python run.py
   ```

- 3) If you see sklearn warnings like:
   "X does not have valid feature names, but LinearRegression was fitted with feature names"
   - This is a warning only; predictions still work. To remove it:
      - Retrain/save the model with consistent feature names (recommended), or
      - Wrap inputs in a pandas.DataFrame with the original column names before calling `model.predict`.

- 4) `pvlib` missing locally
   - For tests and lightweight development we provide a small `pvlib.py` stub. If you prefer the real package,
      install it with `pip install pvlib` and then remove the `pvlib.py` stub file.

- 5) Database file and migrations
   - The app initializes a SQLite DB at `database/database.db` automatically on first run.
   - If DB schema changes or you want a clean slate, stop the server and delete `database/database.db`.

### Windows debugging note

- Reason: Older versions of this repository printed emoji/checkmark characters during startup (for example `✓` and `⚠`). On some Windows developer setups the console encoding defaults to a legacy code page (for example `cp1252`) which cannot encode those glyphs. When Python attempted to print them the process raised a `UnicodeEncodeError` and the Flask server aborted before listening on the API port. This caused clients to receive HTML fallback/error pages and led to the familiar "Unexpected token '<' - not valid JSON" when code tried to parse the response as JSON.
- Fix: Console output was changed to ASCII-only tags such as `[OK]`, `[WARN]`, and `[ERROR]` across the runtime modules (`run.py`, `app.py`, `routes/prediction_routes.py`, `database/init_db.py`, `services/weather_service.py`). With these changes the Flask app starts reliably under Windows debuggers and returns proper JSON to API clients.

If you still see HTML returned where JSON is expected, confirm the debugger is launching the updated code and that your client is targeting the correct host/port (by default `http://127.0.0.1:5000`).

- 6) Tests
   - pytest is optional. If you want to run tests with pytest:
      ```bash
      pip install pytest
      python -m pytest -q
      ```

### Short change-log (recent developer changes)

- Added `services/predictor.py` — helper `prid()` builds the full 246-feature vector and calls the model.
- Updated `/api/predict` route to use the `prid` helper with a safe fallback to `model.predict()`.
- Added `tests/test_predictor.py` to validate the `prid` helper returns non-negative predictions.
- Added small `pvlib.py` stub to support running tests without installing heavy dependencies.
- Fixed a circular import by removing route exports from `services.__init__`.



## 📊 Database Schema

**Table: predictions**

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| timestamp | TEXT | Prediction timestamp |
| city | TEXT | City name |
| latitude | REAL | Location latitude |
| longitude | REAL | Location longitude |
| poa_direct | REAL | Direct irradiance (W/m^2) |
| poa_sky_diffuse | REAL | Sky diffuse irradiance (W/m^2) |
| poa_ground_diffuse | REAL | Ground reflected irradiance (W/m^2) |
| solar_elevation | REAL | Sun elevation angle (degrees) |
| wind_speed | REAL | Wind speed (m/s) |
| temp_air | REAL | Air temperature (°C) |
| predicted_P | REAL | Predicted power (W) |

## 🎨 Technologies Used

- **Backend:** Flask 3.0, MongoDB
- **Frontend:** HTML5, CSS3, JavaScript, Leaflet.js
- **ML:** Scikit-learn, NumPy, Pandas
- **APIs:** Open-Meteo Forecast, OpenStreetMap Nominatim
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

- **Vaibhav U Pratap** - *Web Dev*
- **Zishaanmalik** - *ML Model Training*
- **Tharun V N** - *Front-end*
- **Rohit V** - *Database*

## 🙏 Acknowledgments

- Open-Meteo for weather + irradiance forecasts
- OpenStreetMap Nominatim for geocoding fallback
- Leaflet.js for interactive maps
- Flask community for excellent documentation
- Scikit-learn for ML tools

## 📧 Contact

For questions or support, please contact:
- Email: vaibhavupratap@gmail.com
- GitHub: [@VaibhavUPratap](https://github.com/VaibhavUPratap)

---

⭐ **Star this repository if you find it helpful!**

Made with ❤️ and ☀️ by the Solar Energy Predictor Team