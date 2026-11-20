import os

bind = "0.0.0.0:8000"
# cpu_count() reports host cores inside containers; use the CPUs this process may run on.
workers = int(os.environ.get("WEB_CONCURRENCY", len(os.sched_getaffinity(0)) * 2 + 1))
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
# Client IP from CF-Connecting-IP: set by Cloudflare's edge, not spoofable through the tunnel.
# Field order matches GoAccess --log-format=COMBINED.
access_log_format = '%({cf-connecting-ip}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
loglevel = "warning"
preload_app = True

# --- Cloudflare Tunnel / Reverse Proxy ---
# Trust no X-Forwarded-* headers: the app never reads the client IP, and the
# access log takes CF-Connecting-IP straight from the header. gunicorn 23 does
# not accept CIDR ranges here, so a subnet value makes it refuse to start.

forwarded_allow_ips = "127.0.0.1,::1"
# secure_scheme_headers = {"X-Forwarded-Proto": "https"}  # Detect HTTPS from CF header
proxy_protocol = False             # CF tunnel uses HTTP, not PROXY protocol
