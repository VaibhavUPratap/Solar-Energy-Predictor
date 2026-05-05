import os

# Gunicorn configuration settings
bind = "0.0.0.0:" + os.environ.get("PORT", "10000")
workers = 2
threads = 4
timeout = 120  # Increased timeout for ML model loading
worker_class = "gthread"
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Preload the application before forking worker processes.
# This prevents initialization code (like loading models and connecting to DB) from running twice.
preload_app = True

def on_starting(server):
    port = os.environ.get("PORT", "10000")
    print(f"\n[INFO] Access the application at: http://localhost:{port}\n")
