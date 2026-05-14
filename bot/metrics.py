from prometheus_client import Counter, Histogram, start_http_server

# Metrics
REGISTRATIONS = Counter("bot_registrations_total", "Total number of user registrations")
LIKES = Counter("bot_likes_total", "Total number of likes given")
MATCHES = Counter("bot_matches_total", "Total number of matches created")
MESSAGE_PROCESSING_TIME = Histogram("bot_message_processing_seconds", "Time spent processing messages")


def start_metrics_server(port: int = 8000):
    start_http_server(port)
