import matplotlib.pyplot as plt
import numpy as np

sizes = ["128B", "1KB", "10KB", "100KB"]
rates = [1000, 5000, 10000]

redis_data = {
    "128B":  {"sent": [11446, 21346, 23420], "real_rate": [572, 1067, 1171], "avg_ms": [0.39, 0.58, 0.37], "p95_ms": [1.08, 1.66, 1.43]},
    "1KB":   {"sent": [12284, 21786, 26791], "real_rate": [614, 1089, 1340], "avg_ms": [0.39, 0.67, 0.49], "p95_ms": [1.06, 2.46, 1.12]},
    "10KB":  {"sent": [452, 452, 453],       "real_rate": [23, 23, 23],     "avg_ms": [44.39, 44.35, 44.36], "p95_ms": [48.39, 48.7, 48.39]},
    "100KB": {"sent": [1546, 1417, 1713],    "real_rate": [77, 71, 86],     "avg_ms": [12.64, 14.47, 11.77], "p95_ms": [45.43, 45.55, 45.24]},
}

rabbit_data = {
    "128B":  {"sent": [12331, 27770, 29891], "real_rate": [617, 1388, 1495], "avg_ms": [0.67, 1.15, 0.75], "p95_ms": [2.02, 3.08, 1.82]},
    "1KB":   {"sent": [12099, 29073, 29298], "real_rate": [605, 1454, 1465], "avg_ms": [0.62, 1.12, 0.99], "p95_ms": [1.62, 2.19, 2.74]},
    "10KB":  {"sent": [12219, 27841, 28266], "real_rate": [611, 1392, 1413], "avg_ms": [6.57, 4.26, 3.95], "p95_ms": [11.61, 6.68, 6.03]},
    "100KB": {"sent": [12574, 17338, 16985], "real_rate": [629, 867, 849],   "avg_ms": [2.71, 155.31, 30.34], "p95_ms": [14.81, 662.19, 144.31]},
}

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("RabbitMQ vs Redis: Benchmark Comparison", fontsize=16, fontweight="bold")

# 1 — Real throughput by message size (at target 10000)
ax = axes[0][0]
x = np.arange(len(sizes))
w = 0.35
redis_rates = [redis_data[s]["real_rate"][2] for s in sizes]
rabbit_rates = [rabbit_data[s]["real_rate"][2] for s in sizes]
ax.bar(x - w/2, redis_rates, w, label="Redis", color="#d63031")
ax.bar(x + w/2, rabbit_rates, w, label="RabbitMQ", color="#0984e3")
ax.set_xlabel("Message Size")
ax.set_ylabel("Real msg/s")
ax.set_title("Throughput (target 10000 msg/s)")
ax.set_xticks(x)
ax.set_xticklabels(sizes)
ax.legend()
ax.set_yscale("log")

# 2 — AVG latency by message size (at target 10000)
ax = axes[0][1]
redis_avg = [redis_data[s]["avg_ms"][2] for s in sizes]
rabbit_avg = [rabbit_data[s]["avg_ms"][2] for s in sizes]
ax.bar(x - w/2, redis_avg, w, label="Redis", color="#d63031")
ax.bar(x + w/2, rabbit_avg, w, label="RabbitMQ", color="#0984e3")
ax.set_xlabel("Message Size")
ax.set_ylabel("AVG Latency (ms)")
ax.set_title("AVG Latency (target 10000 msg/s)")
ax.set_xticks(x)
ax.set_xticklabels(sizes)
ax.legend()

# 3 — P95 latency by message size (at target 5000)
ax = axes[1][0]
redis_p95 = [redis_data[s]["p95_ms"][1] for s in sizes]
rabbit_p95 = [rabbit_data[s]["p95_ms"][1] for s in sizes]
ax.bar(x - w/2, redis_p95, w, label="Redis", color="#d63031")
ax.bar(x + w/2, rabbit_p95, w, label="RabbitMQ", color="#0984e3")
ax.set_xlabel("Message Size")
ax.set_ylabel("P95 Latency (ms)")
ax.set_title("P95 Latency (target 5000 msg/s)")
ax.set_xticks(x)
ax.set_xticklabels(sizes)
ax.legend()

# 4 — Total messages sent by rate (100KB)
ax = axes[1][1]
x2 = np.arange(len(rates))
redis_sent = redis_data["100KB"]["sent"]
rabbit_sent = rabbit_data["100KB"]["sent"]
ax.bar(x2 - w/2, redis_sent, w, label="Redis", color="#d63031")
ax.bar(x2 + w/2, rabbit_sent, w, label="RabbitMQ", color="#0984e3")
ax.set_xlabel("Target Rate (msg/s)")
ax.set_ylabel("Total Messages Sent")
ax.set_title("Messages Sent — 100KB payload")
ax.set_xticks(x2)
ax.set_xticklabels([str(r) for r in rates])
ax.legend()

plt.tight_layout()
plt.savefig("d:/dating_bot/tasks/task2/benchmark_results.png", dpi=150)
print("Chart saved to benchmark_results.png")
