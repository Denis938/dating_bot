import time
import json
import threading
import statistics
import pika
import redis

QUEUE = "bench"

MSG_SIZES = [128, 1024, 10240, 102400]
TARGET_RATES = [1000, 5000, 10000]
TEST_DURATION = 20


class ConsumerStats:
    def __init__(self):
        self.received = 0
        self.latencies = []
        self.done = False


def consume_redis(stats: ConsumerStats):
    r = redis.Redis(host="localhost", port=6379)
    while not stats.done or r.llen(QUEUE) > 0:
        result = r.blpop(QUEUE, timeout=1)
        if result:
            _, body = result
            msg = json.loads(body)
            latency_ms = (time.time() - msg["ts"]) * 1000
            stats.latencies.append(latency_ms)
            stats.received += 1


def consume_rabbitmq(stats: ConsumerStats):
    conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
    ch = conn.channel()
    ch.queue_declare(queue=QUEUE)
    ch.basic_qos(prefetch_count=200)

    def on_message(ch, method, _props, body):
        msg = json.loads(body)
        latency_ms = (time.time() - msg["ts"]) * 1000
        stats.latencies.append(latency_ms)
        stats.received += 1
        ch.basic_ack(delivery_tag=method.delivery_tag)

    ch.basic_consume(queue=QUEUE, on_message_callback=on_message)

    while not stats.done:
        conn.process_data_events(time_limit=0.1)

    for _ in range(50):
        conn.process_data_events(time_limit=0.2)
        q = ch.queue_declare(queue=QUEUE, passive=True)
        if q.method.message_count == 0:
            break

    conn.close()


def run_test(broker: str, msg_size: int, target_rate: int) -> dict:
    payload = "x" * msg_size
    interval = 1.0 / target_rate
    stats = ConsumerStats()

    consumer_fn = consume_redis if broker == "redis" else consume_rabbitmq
    consumer_thread = threading.Thread(target=consumer_fn, args=(stats,), daemon=True)
    consumer_thread.start()

    if broker == "redis":
        conn = redis.Redis(host="localhost", port=6379)
    else:
        pika_conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        ch = pika_conn.channel()
        ch.queue_declare(queue=QUEUE)

    sent = 0
    errors = 0
    deadline = time.time() + TEST_DURATION

    while time.time() < deadline:
        loop_start = time.time()
        msg = json.dumps({"ts": time.time(), "data": payload})

        try:
            if broker == "redis":
                conn.rpush(QUEUE, msg)
            else:
                ch.basic_publish(exchange="", routing_key=QUEUE, body=msg)
            sent += 1
        except Exception:
            errors += 1

        spent = time.time() - loop_start
        wait = interval - spent
        if wait > 0:
            time.sleep(wait)

    if broker != "redis":
        pika_conn.close()

    stats.done = True
    consumer_thread.join(timeout=15)

    lats = sorted(stats.latencies)
    avg_lat = statistics.mean(lats) if lats else 0
    p95_lat = lats[int(len(lats) * 0.95)] if lats else 0
    max_lat = lats[-1] if lats else 0
    lost = sent - stats.received
    loss_pct = round(lost / sent * 100, 1) if sent > 0 else 0

    return {
        "broker": broker,
        "size": msg_size,
        "rate": target_rate,
        "sent": sent,
        "received": stats.received,
        "errors": errors,
        "loss_pct": loss_pct,
        "avg_ms": round(avg_lat, 2),
        "p95_ms": round(p95_lat, 2),
        "max_ms": round(max_lat, 2),
        "real_rate": round(sent / TEST_DURATION),
    }


def clear_queues():
    try:
        r = redis.Redis(host="localhost", port=6379)
        r.delete(QUEUE)
    except Exception:
        pass
    try:
        conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
        ch = conn.channel()
        ch.queue_purge(QUEUE)
        conn.close()
    except Exception:
        pass


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes}B"
    return f"{size_bytes // 1024}KB"


def print_table(results: list):
    header = (
        f"{'BROKER':<10} {'SIZE':>7} {'TARGET':>7} {'REAL':>7} "
        f"{'SENT':>7} {'RECV':>7} {'LOSS%':>6} "
        f"{'AVG ms':>8} {'P95 ms':>8} {'MAX ms':>8}"
    )
    sep = "-" * len(header)

    print(f"\n{sep}")
    print(header)
    print(sep)

    prev_broker = None
    for r in results:
        if prev_broker and r["broker"] != prev_broker:
            print(sep)
        prev_broker = r["broker"]

        flag = ""
        if r["loss_pct"] > 5 or r["p95_ms"] > 100:
            flag = " << degradation"

        print(
            f"{r['broker']:<10} {format_size(r['size']):>7} {r['rate']:>7} {r['real_rate']:>7} "
            f"{r['sent']:>7} {r['received']:>7} {r['loss_pct']:>6} "
            f"{r['avg_ms']:>8} {r['p95_ms']:>8} {r['max_ms']:>8}{flag}"
        )

    print(sep)


if __name__ == "__main__":
    all_results = []
    total = len(["redis", "rabbitmq"]) * len(MSG_SIZES) * len(TARGET_RATES)
    current = 0

    for broker in ["redis", "rabbitmq"]:
        for size in MSG_SIZES:
            for rate in TARGET_RATES:
                current += 1
                print(
                    f"\n[{current}/{total}] {broker} | {format_size(size)} | {rate} msg/s ..."
                )

                clear_queues()
                time.sleep(1)

                result = run_test(broker, size, rate)
                all_results.append(result)

                print(
                    f"  sent={result['sent']} recv={result['received']} "
                    f"loss={result['loss_pct']}% "
                    f"avg={result['avg_ms']}ms p95={result['p95_ms']}ms"
                )

    print_table(all_results)
