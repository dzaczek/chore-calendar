import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 2
timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
graceful_timeout = 10
limit_request_line = 8190
limit_request_fields = 50
limit_request_field_size = 8190
accesslog = "/var/log/gunicorn/access.log"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
loglevel = "warning"
preload_app = True

# --- Cloudflare Tunnel / Reverse Proxy ---
# Uncomment these when running behind Cloudflare Tunnel or any reverse proxy.
# They allow gunicorn to trust X-Forwarded-* headers for correct client IP
# and HTTPS detection.

# forwarded_allow_ips = "*"          # Trust proxy headers from any source (safe behind CF tunnel in internal network)
# secure_scheme_headers = {"X-Forwarded-Proto": "https"}  # Detect HTTPS from CF header
# proxy_protocol = False             # CF tunnel uses HTTP, not PROXY protocol
# proxy_allow_from = "*"             # Allow proxy connections from any internal IP
