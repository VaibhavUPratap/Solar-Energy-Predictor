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
