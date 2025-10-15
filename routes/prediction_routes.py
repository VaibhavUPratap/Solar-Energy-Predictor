from flask import Blueprint, render_template, request, jsonify
from services.weather_service import get_weather_data
import pickle, sqlite3, os
from datetime import datetime

prediction_bp = Blueprint("prediction", __name__)

model = pickle.load(open("models/Linear_Regression.pkl", "rb"))
DB_PATH = "database/database.db"

@prediction_bp.route("/")
def index():
    return render_template("index.html")

@prediction_bp.route("/predict", methods=["POST"])
def predict():
    city = request.form["city"]
    data = get_weather_data(city)
    if data.get("error"):
        return jsonify(data)

    features = [[850, 120, 60, 45, data["wind_speed"], data["temp_air"]]]
    predicted_P = float(model.predict(features)[0])

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO predictions 
                 (timestamp, city, latitude, longitude, temp_air, wind_speed, predicted_P)
                 VALUES (?, ?, ?, ?, ?, ?, ?)""",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), city, data["lat"], data["lon"],
               data["temp_air"], data["wind_speed"], predicted_P))
    conn.commit()
    conn.close()

    return jsonify({**data, "predicted_P": round(predicted_P, 2)})

@prediction_bp.route("/history")
def history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM predictions ORDER BY id DESC LIMIT 10")
    data = c.fetchall()
    conn.close()
    return render_template("history.html", data=data)
