
import sys
import os
# Add the project root to sys.path
sys.path.append(os.getcwd())

from models.integrated_model import pridictionn

def test_app_prediction(loc):
    try:
        print(f"Testing prediction logic for location: {loc}")
        prediction, metadata = pridictionn(loc)
        print(f"[SUCCESS] Prediction for {loc}: {prediction}")
        print(f"Coordinates: {metadata['latitude']}, {metadata['longitude']}")
    except Exception as e:
        print(f"[FAILURE] Prediction failed for {loc}: {e}")

if __name__ == "__main__":
    loc = sys.argv[1] if len(sys.argv) > 1 else "tokyo"
    test_app_prediction(loc)
