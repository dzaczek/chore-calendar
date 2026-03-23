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
accesslog = "-"
errorlog = "-"
loglevel = "warning"
preload_app = True
