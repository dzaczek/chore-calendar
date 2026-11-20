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
# Only trust X-Forwarded-* headers from the internal Docker network
# (chore-calendar_internal), where cloudflared is the only proxy.

forwarded_allow_ips = "172.19.0.0/16"
# secure_scheme_headers = {"X-Forwarded-Proto": "https"}  # Detect HTTPS from CF header
proxy_protocol = False             # CF tunnel uses HTTP, not PROXY protocol
