# Session 2 — Rate Limiter Java, Alien Dictionary, Cheapest Flights, Distributed Cache, Bias-Variance

**Date:** May 3, 2026
**Domains:** LLD · DSA × 2 · HLD · ML · Bonus
**Theme:** Heaviest session so far. Built the full rate limiter family in Java, hit graph problems hard, deep-dove distributed cache, and worked Coinbase-style MCQs.

---

## 🧠 New Algorithms

- **Fixed Window Counter** — `{windowId, count}` per user. O(1). Vulnerable to boundary spike.
- **Sliding Window Log** — `ArrayDeque<timestamp>`. Evict old, count remaining. Exact but O(N) memory.
- **Sliding Window Counter** — 2 windows + interpolation. `estimate = currCount + (1−elapsed) × prevCount`. Cloudflare uses this.
- **Token Bucket** — `{tokens, lastRefill}`. Refill at rate R, consume on request. Allows bursts. AWS / Stripe.
- **Leaky Bucket** — `{waterLevel, lastDrain}`. Drains at fixed rate, fill on request. Smooth output, no bursts.
- **Kahn's BFS (topological sort)** — Track in-degrees, queue zero-in-degree nodes, decrement neighbors. Cycle detected if `result.size() < N`.
- **DFS-based topological sort** — Post-order DFS + reverse. 3-state cycle detection (white/gray/black).
- **Constrained Dijkstra (state augmentation)** — State = `(node, budget)` not just `node`. No `visited` set. First pop of `dst` = answer.

## 🎯 New Patterns

- **Strategy pattern (LLD)** — Abstract `RateLimiter` interface, concrete strategy classes. Java template for swappable algorithms.
- **ConcurrentHashMap + per-user synchronized lock** — Outer concurrent map, inner object-level lock. `putIfAbsent` before `synchronized` block.
- **Constraint Graph from comparisons** — Extract directed edges from adjacent pairs → topo sort. Alien Dictionary, prerequisite chains, build systems.
- **State augmentation for constrained shortest path** — Adding the constraint dimension to the node state to preserve Dijkstra's pop-once invariant.
- **Consistent hashing (ring)** — Virtual nodes (~150 per server). Node loss → only 1/N keys remap, not (N−1)/N.
- **Thundering Herd Toolkit** — TTL jitter, probabilistic early expiry, request coalescing, background refresh, stale-while-revalidate.
- **CDC pipeline** — DB WAL → Debezium → Kafka → cache invalidator. Required when multiple writers.

## 🛠️ Systems / Tools / Libraries (named things)

- **Debezium** — CDC tool that tails DB WAL and publishes changes to Kafka.
- **Redis (rate limiter store)** — Atomic INCR, Lua scripts for compound atomicity.
- **PostgreSQL / MySQL / MongoDB / Cassandra** — DB R/W rate reference table.
- **WAL (Write-Ahead Log)** — DB's source of truth for replication, CDC.
- **Cloudflare's rate limiter** — Sliding Window Counter in production.

## 📚 Terms / Concepts

- **TOCTOU (Time-of-Check-to-Time-of-Use)** — Race condition class; fix with atomic ops.
- **Fail open vs fail closed** — Behavior when rate limiter store dies. Production trade-off.
- **Retry-After header** — Tell clients when to retry on 429.
- **In-process vs sidecar/gateway** — Rate limiter deployment model.
- **N+1 query problem** — DB anti-pattern: loop fires one query per parent.
- **SQL injection** — String concatenation in queries. Fix: parameterized queries / PreparedStatement.
- **Bias** — Error from oversimplification. High bias = underfit. Bad on train AND test.
- **Variance** — Error from oversensitivity. High variance = overfit. Big gap between train and test.
- **L1 (Lasso)** — Penalty `λ·Σ|w|`. Diamond constraint geometry. Sparse weights, feature selection.
- **L2 (Ridge)** — Penalty `λ·Σw²`. Circle constraint geometry. Shrinks all weights smoothly.
- **ElasticNet** — L1 + L2 combo.
- **Dropout** — NN-specific. Randomly disable neurons during training.
- **Early stopping** — Halt training when val loss starts climbing.
- **Vanishing gradients** — Sigmoid/tanh derivative < 1; chained multiplication → 0. Fix: ReLU, BatchNorm, residual connections.
- **Activation cheat sheet** — Regression→linear, Binary→sigmoid, Multiclass→softmax, Hidden→ReLU.
- **Dartboard mental model (bias/variance)** — Centered+tight = ideal; centered+scattered = overfit; off-center+tight = underfit.
- **SLA / SLO / SLI** — Contract / target / measurement.
- **Shard / Partition** — Effectively same. Replica = copy, not split.
- **Hash mod N catastrophe** — (N−1)/N of keys remap on single node death.

## 🅿️ Backlog Surfaced

- L1 / L2 geometry deep dive (diamond vs circle, why L1 → sparsity, optimizer behavior at corners) — **PARKED**
- Race condition on concurrent cache writes — **PARKED**
- Java RateLimiter line-by-line code review (parts of session) — covered next session

## 🔗 References

- [Redis Atomic Operations](https://redis.io/docs/latest/develop/use/patterns/distributed-locks/)
- Cloudflare's sliding window counter blog (search "Cloudflare rate limiting")
