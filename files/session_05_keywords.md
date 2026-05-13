# Session 5 — Consistent Hashing Patch + Uber Dispatch (DISCO) System Design

**Date:** May 11, 2026
**Domains:** HLD (heavy) · Distributed systems · Revision (partial)
**Theme:** Patched gaps in Card #7 (consistent hashing), parked Kafka deep dive, then full system design of Uber's real-time dispatch. Covered request routing, matching strategies, concurrency safety, and disconnection handling.

---

## 🧠 New Algorithms

- **Hungarian Algorithm (Linear Assignment Problem)** — Optimal bipartite matching minimizing total cost over an N×M matrix. O(n³). Used in batched ride-matching (airports, UberPool).
- **Auction Algorithm** — Distributed alternative to Hungarian; bidders raise prices on items. Better at large scale.
- **Sequential single-offer matching** — Offer to driver #1 → 15s timeout → driver #2 → ... Uber's default for UberX. Zero concurrency on accept.
- **Broadcast matching (anti-pattern)** — Offer to top-K simultaneously, first-tap-wins. Phantom Ride Problem. Don't.

## 🎯 New Patterns

- **Consistent Hashing (ring + virtual nodes)** — Single fix for hash-mod-N catastrophe. Node death → ~1/N keys move instead of (N−1)/N.
- **Optimistic Concurrency Control via conditional UPDATE** — `UPDATE rides SET state='ACCEPTED' WHERE state='OFFERED' AND offered_to_driver_id=$id`. Atomic state-machine transition. Predicate must include all relevant guards (state + which driver).
- **SETNX / CAS pattern** — Redis SETNX or DB conditional UPDATE achieve the same atomic state guard.
- **Atomic state machine transitions** — Every transition is `UPDATE WHERE state = <expected_prior_state>`. Failure (0 rows affected) signals concurrent state change.
- **Event Bus over Webhook Mesh** — Internal service-to-service communication via Kafka topics, not pairwise HTTP webhooks. Decouples fan-out, replay, backpressure.
- **TTL as Heartbeat** — Store ephemeral state with TTL > expected refresh × 2-3. Refresh on each update. Presence = existence of key. No separate health-check service needed.
- **Sequential vs Batched matching switch** — Per-region config. Default sequential; switch to batched (Hungarian) at hotspots (airports, stadium exits, density triggers).
- **Two-tier H3 use** — Coarse H3 for Kafka partition routing (locality). Fine H3 + kRing expansion for actual driver lookup at match time (global Location Service).
- **Async command pattern (CQRS-lite)** — Sync API returns ack immediately, writes intent to DB, publishes event. Async worker processes. Push result back via WebSocket.

## 🛠️ Systems / Tools / Libraries (named things)

- **DISCO** — Uber's internal name for the Dispatch Optimization service.
- **Ringpop** — Uber's gossip-based sharding library. (BACKLOG: standalone deep-dive)
- **DocStore** — Uber's in-house data store (modern). (BACKLOG)
- **AresDB** — Uber's real-time analytics store. (BACKLOG)
- **RAMEN** — Uber's WebSocket-based real-time push platform. 1M+ concurrent connections per box. (BACKLOG)
- **Apache Pulsar** — Newer Kafka alternative. Decouples storage (BookKeeper) from compute. Tiered S3 storage.
- **AWS Kinesis** — Managed Kafka-like, ~1 MB/s per shard.
- **Redpanda** — C++ Kafka-wire-compatible. No JVM. Lower latency.
- **NATS JetStream** — Lightweight queue/log hybrid.
- **Google Pub/Sub** — Managed, infinite scale, no default ordering.
- **AWS SQS** — Managed hosted queue. Standard = no order, FIFO = 3K msg/sec cap.
- **APNs / FCM** — Apple/Firebase push notifications. Wake the app from sleep. (BACKLOG: deep dive)
- **WebSocket** — Persistent bidirectional TCP, client-initiated. Works through mobile NAT.
- **Idempotent Producer (Kafka)** — Producer ID + sequence number per partition. Broker dedupes. (BACKLOG: deep dive)
- **Transactional API (Kafka)** — Atomic writes across partitions + offset commits. Read-process-write pattern. (BACKLOG: deep dive)

## 📚 Terms / Concepts

- **Phantom Ride Problem** — Race condition + UX disaster of broadcast matching. Drivers tap accept, only one wins, others wasted miles + frustration.
- **Hot Partition Problem (Kafka)** — One key gets disproportionate traffic, that partition bottlenecks while others idle. Whale users, viral content.
- **Per-key ordering trade-off (Kafka)** — Partition by key for ordering, but consumer parallelism capped at partition count. Pre-commit to enough partitions.
- **Phantom on conditional UPDATE** — `WHERE state='OFFERED'` alone is insufficient if state was re-OFFERED to a different driver. Predicate must include `offered_to_driver_id`.
- **Phone disconnection cascade by state** — Idle = no-op (TTL evict). Offered = auto-timeout. En-route = bad (notify rider, re-dispatch). On-trip = worst (PENDING_RECOVERY, manual review).
- **Webhook vs WebSocket distinction** — Webhook = server-to-server HTTP push. Requires stable public URL on receiver side. Impossible for mobile clients. WebSocket = client-initiated persistent connection.
- **Server-webhook vs event bus internally** — Server webhooks fine for *external* callbacks (Stripe → you). For *internal* event flow, event bus (Kafka) >> webhook mesh.
- **Cross-border matching** — Cities are administrative; drivers/riders care about distance. Don't partition by city_id. Partition by H3 cell, query Location Service globally.
- **Ride state machine** — `REQUESTED → OFFERED → ACCEPTED → EN_ROUTE_PICKUP → ON_TRIP → COMPLETED`, with `EXPIRED`, `CANCELLED`, `PENDING_RECOVERY` branches.
- **Replay (Kafka feature)** — Multiple consumer groups, debug, ML training, audit. Killer feature vs queues.
- **Backpressure** — Kafka absorbs bursts; sync webhook calls would fail/timeout.

## 🅿️ Backlog Surfaced

- **Kafka deep dive (standalone thread)** — Exactly-once mechanics (idempotent producer + transactional API), partitioning + consumer groups, rebalancing, hot partitions, ISR/replication, ZooKeeper vs KRaft, retention, compaction, Kafka Streams.
- **Ringpop standalone deep-dive** — Gossip protocol, consistent hashing implementation, membership.
- **DocStore, AresDB** — Uber's data store stack.
- **RAMEN standalone deep-dive** — Custom WebSocket pub-sub, scaling 1M+ connections.
- **APNs / FCM push notification deep-dive** — Mobile wake-up mechanics, payload structure, certificate management.
- **Bagging algorithm + Naive Bayes implementation** — From Coinbase OA stumpers. **Priority ML topic.**
- **Xavier vs He initialization deep dive** — When and why.
- **L1 / L2 geometry deep dive** — Diamond vs circle, sparsity intuition.
- **LeetCode #3528** — Resume from DSU + bidirectional edges insight.

## 🔗 References

- [Uber Engineering — H3 Hexagonal Hierarchical Spatial Index](https://www.uber.com/blog/h3/)
- [Uber Engineering — Real-time Push Platform (RAMEN)](https://www.uber.com/blog/real-time-push-platform/)
- [Uber Engineering — Real-time Marketplace](https://www.uber.com/blog/real-time-marketplace-pricing-system/)
- 📺 StatQuest: [Sensitivity & Specificity](https://www.youtube.com/watch?v=vP06aMoz4v8) · [Precision vs Recall](https://www.youtube.com/watch?v=8d3JbbSj-I8) · [ROC and AUC](https://www.youtube.com/watch?v=4jRBRDbJemM)
- 📺 StatQuest: [ResNet & Residual Connections](https://www.youtube.com/watch?v=Q1JCrG1bJ-A)
