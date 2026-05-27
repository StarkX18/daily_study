# FAANG+ Interview Prep Tracker

## Session Format
- **Part 0:** Revision pings on ALL prior pattern cards
- **Parts 1-5:** One question each — LLD, DSA, DSA, ML, HLD (rotate order)
- **Style:** GMAT QnA — Claude poses, user attempts, deep deconstruction, extract pattern card
- **Threading:** Separate thread per session, same project
- **Model:** Sonnet for daily grind, Opus for weekly deep-review/mock interviews

---

## Company-Specific Patterns

### Google
- Heavy on **graph problems** (BFS/DFS, shortest path, topological sort)
- System design loves **scale** — "design for 1 billion users"
- Behavioral: Googleyness, leadership

### Meta (Facebook)
- Heavy on **string/array problems**, sliding window, two pointers
- System design: social graph, news feed, real-time messaging
- Move fast energy — they want clean code quickly

### Uber
- **Graphs, heaps, design-y data structures, real-world simulation**
- Matching, routing, surge pricing, ETA estimation
- HLD: geo-indexing (H3), real-time dispatch (DISCO), Kafka-heavy architecture
- Uses NodeJS for dispatch, Go for DISCO, Java for backend

### Amazon
- **Leadership Principles** dominate behavioral rounds
- DSA: trees, graphs, greedy, DP
- System design: distributed systems, availability > consistency

### Jane Street
- **Probability, combinatorics, expected value, conditional probability, Markov chains**
- Mental math & estimation (Fermi problems)
- Game theory & puzzles
- Trading games / market making simulations
- OCaml-flavored functional thinking
- NOT standard leetcode — more mathematical reasoning

### Tower Research / HRT / Citadel / Optiver / Jump
- **Probability heavy** — same as Jane Street
- Trading games (especially Optiver, IMC)
- Mental math speed tests
- DSA less leetcode-grindy, more "reason about complexity"
- Brainteasers with mathematical substance

### Netflix / Airbnb / Stripe
- Strong system design focus
- Stripe: payment systems, idempotency, exactly-once semantics
- Netflix: streaming, CDN, recommendation systems, chaos engineering
- Airbnb: search ranking, availability systems, pricing

---

## Pattern Cards Completed

### #1 — Class Imbalance & Metric Selection (ML)
- **What:** When positive class is rare (<10%), accuracy is misleading
- **Recognize when:** Fraud, anomaly detection, disease screening, churn, ad CTR, defect detection
- **Metric toolbox:** Confusion matrix → Precision (TP/TP+FP) → Recall (TP/TP+FN) → F1 → PR-AUC (better than ROC-AUC under imbalance) → Cost-weighted error
- **Threshold selection:** Not 0.5 by default. Driven by business cost matrix. Often tiered thresholds in production.
- **Connections:** Imbalance handling (SMOTE, focal loss), calibration, A/B testing thresholds

### #2 — Top-K with Max-Heap + Spatial Indexing (DSA)
- **Pattern A — Top-K via bounded max-heap:** Maintain max-heap of size K. Compare new item to heap top; replace if better. O(N log K) time, O(K) space.
- **Pattern B — Spatial indexing:** Reduce N first via grid/cell lookup, then run algorithm on reduced set. Options: geohash (string-prefix), H3 (hex, Uber), S2 (spherical, Google), quadtree (density-adaptive), k-d tree (bad for updates).
- **Recognize when:** "K closest/largest/most frequent", anything geographic
- **Key insight:** Compare squared distances — skip sqrt (monotonic, preserves order)
- **Connections:** Streaming algorithms, HLD for geo-systems (Uber/Yelp/Tinder)

### #3 — Stream Merge with Carried State + Incremental Aggregate (DSA)
- **Pattern A — Two-pointer merge with carried state:** Merging 2 sorted streams where values persist between events. Track lastA, lastB. Don't forget drain loop at end.
- **Pattern B — K-way merge with min-heap + delta aggregation:** N sorted streams → heap holds one entry per stream head. Maintain last[N] + running_sum. Update via delta (sum += new - old). O(E log N) time, O(N) space.
- **Recognize when:** "Merge K sorted lists", log/metric aggregation, sensor fusion, financial tick aggregation
- **Key gotcha:** Carry-forward semantics break naive merge. Tied timestamps need batched processing.
- **Connections:** LWW in distributed systems, K-way merge in external sort, streaming sketches

### #4 — Queue vs Log (HLD)
- **Queue (RabbitMQ/SQS):** One message → one consumer → acked → deleted. Workers compete. No replay. Good for task distribution.
- **Log (Kafka):** Append-only, partitioned, persistent. Multiple consumer groups read independently at own offsets. Replay is a feature. Ordering within partition only.
- **Kafka ordering rule:** key → hash → partition. Same key = same partition = ordered. No key = round-robin = no order guarantee.
- **Delivery guarantees:** At-most-once (fire & forget), At-least-once (retry, possible dupes), Exactly-once (= at-least-once + idempotent processing in practice)
- **Broker model:** RabbitMQ = smart broker/dumb consumer. Kafka = dumb broker/smart consumer.
- **Consumer groups:** Label for coordinated consumption. Parallelism ceiling = partition count. Heartbeat → session.timeout.ms → rebalance on failure.
- **Connections:** Event sourcing, CDC, idempotency patterns, distributed transactions

### #5 — Rate Limiter (LLD)
- **Algorithms:** Sliding window counter (O(1), approximate, Cloudflare), Token bucket (O(1), burst-friendly, AWS/Stripe), Fixed window counter (boundary attack risk), Sliding window log (exact but O(N)), Leaky bucket (smooths traffic, rarely used for APIs)
- **Token bucket ≠ Leaky bucket:** Token = tokens refill, requests drain them, allows bursts. Leaky = queue drains at fixed rate, smooths output.
- **Single server:** Strategy pattern interface + ConcurrentHashMap + per-user synchronized lock
- **Distributed:** Redis. Atomic INCR for counters. Lua scripts for multi-step atomicity.
- **Race condition:** TOCTOU (Time of Check to Time of Use). Fix: atomic Redis ops.
- **Production concerns:** Fail open vs fail closed when Redis down. Retry-After header. Per-user vs per-IP vs per-endpoint.
- **Connections:** Distributed locks (Redlock), backpressure, circuit breaker

---

## Spatial Indexing Reference

| Structure | Type | Cells | Density-adaptive | Update-friendly | Famous user |
|-----------|------|-------|-------------------|-----------------|-------------|
| Geohash | Encoding scheme | Uniform | No | Great (O(1)) | Redis GEO, Elasticsearch |
| Quadtree | Tree (4-way) | Variable | Yes | OK | Games, GIS |
| k-d tree | BST (alternating dims) | Implicit | No | Painful | Sklearn KNN |
| H3 (Uber) | Hex hierarchy | Hexagonal | Hierarchical | Great | Uber dispatch |
| S2 (Google) | Spherical Hilbert | Spherical | Hierarchical | Great | Google Maps |

**Links:**
- [Uber H3 Blog](https://uber.com/en-NL/blog/h3)
- [H3 GitHub](https://github.com/uber/h3)
- [Google S2](https://s2geometry.io)
- [S2 Deep Dive (Hilbert curve)](https://blog.christianperone.com/2015/08/googles-s2-geometry-on-the-sphere-cells-and-hilbert-curve)

---

## Backlog — Topics to Cover

### ML (fundamentals → modern)
- [ ] Logistic regression from scratch (sigmoid, log loss, gradient)
- [ ] Full confusion matrix tour (specificity, NPV, FPR, FNR, MCC, balanced accuracy)
- [ ] ROC-AUC vs PR-AUC curves (construction, geometry, when each lies)
- [ ] Probability calibration (Platt scaling, isotonic regression, reliability diagrams)
- [ ] Class imbalance techniques (SMOTE, undersampling, class weights, focal loss)
- [ ] Cost-sensitive learning (baking cost matrix into loss)
- [ ] Threshold selection in production (tiered, segment-specific, drift)
- [ ] Decision boundaries (linear vs non-linear, geometric intuition)
- [ ] Bias-variance tradeoff (overfitting/underfitting)
- [ ] Cross-validation (k-fold, stratified, time-series CV, leakage)
- [ ] Regularization L1/L2 (intuition, when each helps)
- [ ] Feature engineering & selection
- [ ] Loss functions zoo (MSE, MAE, Huber, log loss, hinge, cross-entropy)
- [ ] Gradient descent variants (SGD, momentum, Adam, learning rate schedules)
- [ ] Regression metrics (RMSE, MAE, R², MAPE)
- [ ] Embeddings, transformers, attention, RAG, RLHF

### HLD
- [ ] RabbitMQ exchange types (topic, fanout, direct, headers)
- [ ] Kafka rebalance strategies (cooperative sticky, stop-the-world problem)
- [ ] Consumer lag monitoring
- [ ] Distributed locks (Redlock, why controversial)
- [ ] Redis Lua scripting patterns
- [ ] Spatial indexing deep dive (geohash internals, H3, S2, quadtrees)
- [ ] CDC / event sourcing
- [ ] Backpressure & flow control
- [ ] Idempotency patterns (Stripe-style)
- [ ] WebSockets & C10M problem (Uber RAMEN)
- [ ] Pub/sub fan-out (push vs pull, write vs read)
- [ ] Consistent hashing deep dive
- [ ] Consensus (Raft/Paxos intuition level)
- [ ] Circuit breakers, retries, timeouts, exponential backoff with jitter
- [ ] Multi-region & failover (active-active vs active-passive)

### LLD
- [ ] Rate limiter rebuild in Java (next session Part 1)
- [ ] Distributed locks (optimistic vs pessimistic locking)
- [ ] TOCTOU patterns
- [ ] Redis distributed rate limiter with Lua
- [ ] Observer pattern
- [ ] Factory pattern
- [ ] Builder pattern
- [ ] Command pattern

### DSA
- [ ] k-d tree deep dive
- [ ] Streaming algorithms
- [ ] Graph problems (Google-style)
- [ ] String/array problems (Meta-style)
- [ ] DP on trees
- [ ] Minimax / game theory DP
- [ ] Dijkstra with constraints (Cheapest Flights Within K Stops)

---

## Session History

### Session 1 (Day 1)

**Index / What We Covered:**
| # | Topic | Problem | Key Concept |
|---|-------|---------|-------------|
| ML #1 | Class Imbalance | Fraud detection classifier | Accuracy paradox, precision/recall, PR-AUC, threshold selection |
| DSA #1 | K Closest Drivers | Top-K nearest drivers (Uber dispatch) | Max-heap of size K, geohash, H3, quadtrees vs k-d trees |
| DSA #2 | Time Series Merge | Merge N price series with carry-forward | K-way heap + delta aggregation, carry-forward state |
| HLD #1 | Queue vs Log | When to use Kafka vs RabbitMQ vs SQS | Queue = to-do list, Log = diary, delivery guarantees, consumer groups |
| LLD #1 | Rate Limiter | Design isAllowed(userId) at scale | Sliding window counter, token bucket, Redis INCR, TOCTOU, Strategy pattern |

**Concepts introduced outside questions:**
- TP/TN/FP/FN confusion matrix mechanics
- Geohash vs quadtree vs k-d tree — three different beasts
- Kafka broker = dumb broker / smart consumer
- Kafka heartbeat → session.timeout.ms → rebalance on consumer death
- `final` in Java = immutable reference, not immutable object
- Per-user synchronized locking vs global method lock

**Pattern Cards extracted:** #1 (ML), #2 (DSA), #3 (DSA), #4 (HLD), #5 (LLD)

**Next session:**
- Part 0: Revision pings on all 5 pattern cards
- Part 1 (LLD): User rebuilds rate limiter in Java from scratch — no peeking
- Parts 2-3 (DSA): MH + H problems from real Uber/FAANG interview reports
- Part 4 (ML): Fresh fundamentals question
- Part 5 (HLD): Fresh concept deep dive
