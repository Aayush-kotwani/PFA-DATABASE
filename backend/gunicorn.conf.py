"""Gunicorn configuration tuned for Render 512 MB RAM and memory:// rate limiting."""

import os

# Single worker keeps in-memory Flask-Limiter counters consistent and fits 512 MB RAM
workers = 1
worker_class = "gthread"
threads = 4
timeout = 60

bind = f"0.0.0.0:{os.getenv('PORT', '5000')}"

# Log to stdout/stderr; %(m)s %(U)s %(H)s omits query strings, headers, and tokens
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s "%(m)s %(U)s %(H)s" %(s)s %(b)s %(L)ss'
