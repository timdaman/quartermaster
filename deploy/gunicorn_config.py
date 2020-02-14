import multiprocessing
import os

DEFAULT_WORKERS = multiprocessing.cpu_count() * 2
bind = "0.0.0.0:8000"
workers = os.environ.get("GUNICORN_WORKERS", DEFAULT_WORKERS)

loglevel = 'info'
errorlog = '-'
accesslog = '-'
capture_output = True
