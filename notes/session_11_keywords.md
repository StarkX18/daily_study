# Session 11 — Python Heap Fundamentals + DSA Gauntlet + Google Docs Full HLD

**Date:** May 30, 2026
**Domains:** Python fundamentals (organic) · DSA × 4 · HLD (Hard — Google Docs)
**Theme:** Heavy organic Python tangents (heapq, stack, deque, f-strings) + four monotonic-stack/two-pointer problems + deepest HLD of the prep so far (Google Docs, OT vs CRDT, event sourcing, WAL, gRPC, distributed locking, broadcast fan-out).

---

## 🧠 New Algorithms

- **K-way heap merge (mergeKLists)** — push `(val, list_idx, node)` triples. Key invariant: each list has at most ONE node in the heap at any time → `idx` is unique → `(val, idx)` never ties → node comparison never reached.
- **Longest Valid Parentheses (LC 32)** — stack of indices (not chars). `stack[-1]` = last unmatched position (the "wall"). Length = `i − stack[-1]`. Init `[-1]`. Unmatched `)` → push its own index as new wall.
- **Largest Rectangle in Histogram — single-pass mono stack (LC 84)** — indices on stack, pop on shorter bar. Area = `heights[top] × (i − stack[-1] − 1)`. Sentinel `0` appended to flush everything. Divide-and-conquer alternative: find min-bar, recurse left + right, O(n log n).
- **Trapping Rain Water — two-pointer (LC 42) ⚠️ RETRY FRESH** — anchor at ends `l=0, r=n-1`, maxes start at 0. `h[l] < h[r]` picks the SAFE-TO-COMMIT side (not the water level). Process that side with only its OWN max — never `min(l_max, r_max)`. Inward init (`l=1, r=n-2`, preloaded maxes) is fatally broken — unpatchable.

---

## 🎯 New Patterns

- **Monotonic stack with indices — universal rule** — store indices, not values. Pop gives (popped, revealed-left-neighbor, current-right). Width/distance flows from `i − stack[-1] − 1`. Covers LC 42, 84, 32, 739, 503, 1019.
- **Event sourcing** — append-only event log as source of truth; derive current state by replay. Snapshot every N events, replay tail. Audit trail + time travel for free. Google Docs op log IS event sourcing.
- **WAL pattern** — append → ensure durable (fsync/replicate) → ack → async apply to primary store. On crash: replay WAL. Faster than synchronous primary-store writes because sequential append beats random/replicated write on the ack path. Kafka is also a log, but a co-located WAL has lower ack latency (no cross-broker replication round-trip).
- **Two-path architecture** — fast path (WebSocket → OT server → broadcast) never waits on disk. Reliable path (Kafka → op log → snapshots) guarantees durability. Decoupled so a slow disk write never stalls a keystroke.
- **Sticky routing via consistent hash + lease** — `hash(doc_id)` → owning instance. Lease store (ZooKeeper / etcd / Redis SETNX + TTL) makes the claim atomic. Auto-expires on death so a new owner can claim. Claim via CAS — same OCC family. This = Ringpop.
- **Two-tier broadcast fan-out** — publish once to pub/sub backbone (Kafka / Redis Pub/Sub) → gateways subscribed to that channel push locally to their own sockets. Publisher never tracks where clients are. Hot-topic at millions: hierarchical fan-out tree.

---

## 🛠️ Systems / Tools / Libraries (named things)

- **heapq** — Python stdlib, C-accelerated via `_heapq`. Min-heap in-place on a `list`. No comparator param. `heapify` is O(n).
- **itertools.count()** — monotonic counter. `next(counter)` = globally unique integer; perfect heap tie-breaker.
- **Jupiter algorithm** — OT variant used by Google Docs. Central server serializes ops per doc, transforms against concurrent ops, assigns revision numbers.
- **QUIC** — UDP-based transport (Google). TLS 1.3 built in. Per-stream loss isolation (no TCP head-of-line blocking). HTTP/3 rides it.
- **WebTransport** — browser API over HTTP/3/QUIC for bidi streams + datagrams. Emerging WebSocket alternative.
- **gRPC-Web** — browser-compatible gRPC via a proxy. Supports server-streaming; cannot do browser-initiated bidi streaming. Hence browsers use WebSocket for bidi, not gRPC.
- **ZooKeeper ephemeral znodes / etcd leases** — distributed lock primitives. Node auto-deleted on session death → lock auto-released. Classic pessimistic distributed lock.
- **Fencing tokens** — monotonically increasing number per lock acquisition. Storage layer rejects writes from stale holders even after TTL confusion (Redlock fix).
- **RAMEN** — Uber's WebSocket push platform. 1M+ concurrent connections per box. The broadcast layer for large-scale fan-out. (Backlog: standalone deep-dive.)

---

## 📚 Terms / Concepts

- **heapq comparator patterns** — tuple trick `(priority, idx, value)`; monotonic counter for guaranteed uniqueness; `__lt__` wrapper class for complex objects.
- **Operational Transformation (OT)** — transform concurrent ops so they preserve intent + converge. Central server serializes all ops per doc (correctness requirement, not weakness). O(n²) merge cost for divergent offline branches.
- **CRDT (Conflict-free Replicated Data Type)** — design data so ops commute; apply in any order → same result. Per-char unique stable IDs, tombstones for deletes. No central server. High memory overhead (16–32 bytes/char).
- **LWW-register** — Last-Write-Wins register. Simplest CRDT. Single value + max-timestamp wins on conflict. Commutative (max is order-independent). Figma's per-property CRDT. Loses the losing write — fine for color/width, wrong for text.
- **Tombstone** — deleted-but-retained character in a sequence CRDT. Anchors ordering without shifting positions of surviving chars.
- **OT vs CRDT one-liner** — OT: small data, smart central server. CRDT: dumb merge, fat data, no central authority.
- **Serialization = GIL analog** — the OT server processes one doc's ops one-at-a-time in a total order. Like Python's GIL: per-doc serial, cross-doc parallel (different docs → different instances). Two instances serializing the same doc = split-brain.
- **ACL (Access Control List)** — per-resource list of (principal, permission) pairs. Checked before every edit. Siblings: RBAC (role-based), ABAC (attribute-based).
- **RPC vs REST** — RPC: verb/procedure-oriented, binary (protobuf), HTTP/2 (gRPC), internal service-to-service. REST: resource/noun-oriented, JSON + HTTP verbs, stateless, public APIs.
- **HTTP protocol evolution** — HTTP/1.1 (one request at a time, text) → HTTP/2 (multiplexed streams over TCP, gRPC rides this) → HTTP/3 (same semantics over QUIC/UDP, per-stream loss isolation).
- **Web2 vs Web3 vs HTTP3 — orthogonal axes** — Web 1/2/3 = eras of the web (static → interactive → blockchain/decentralized). HTTP/1.1 → 2 → 3 = transport protocol evolution. Completely independent. "Web3" (blockchain) and "HTTP/3" (transport) have nothing to do with each other.
- **Distributed pessimistic locking** — lock `{doc_id}:{region_id}` via ZooKeeper ephemeral znode or Redis SETNX + TTL. Auto-releases on holder death. Needs fencing tokens to handle Redlock-style stale-holder bugs. Works for coarse objects (cells, shapes, paragraphs); terrible UX for fluid text.
- **Presence storage** — Redis hash `presence:{doc_id}:{client_id}` → `{ cursor_pos, selection, name, color }`. TTL = heartbeat. Throttled + coalesced. Ephemeral — separate pipeline from durable edits.
- **OT offline cost** — user offline N ops, others made M ops online → reconnect transforms each of N against each of M = **O(N × M)**. Can't shortcut to "send final state" without clobbering others' concurrent edits. CRDT avoids via commutative merge.
- **Idempotency (extended)** — key = `(clientId, seqNumber)`. Check-and-record must be atomic (unique constraint + `INSERT ON CONFLICT`, or SETNX) — not check-then-act (TOCTOU). Cache the result too so retries get the same response.
- **f-string format spec** — `{value:[fill][align][width][,][.precision][type]}`. Key combos: `05d` (zero-pad), `.2f` (2 decimals), `,` (thousands sep), `.1%` (percent), `#b` (binary + prefix), `^10` (center), `{x=}` (debug, Python 3.8+).

---

## 🅿️ Backlog Surfaced

- **LC 42 Trapping Rain Water** — retry fresh; trap is inward init; insight is safe-to-commit side. Revision angle: mono-stack slab form.
- **Fan-out at scale deep-dive** — two-tier pub/sub, hot-topic hierarchical fan-out tree, fan-out-on-write vs read, RAMEN internals. He wants to revisit this specifically.
- **Amazon WAF + CloudFront** — parked at session start, never reached. Pull as first HLD next session.
- **Ringpop** — appeared organically today (sticky routing = Ringpop). Now has concrete context; ready for standalone.
- **Distributed locks (Redlock + fencing tokens)** — surfaced in pessimistic-locking discussion; worth dedicated deep-dive.

---

## 🔗 References

- [Figma — "How Figma's Multiplayer Technology Works"](https://www.figma.com/blog/how-figmas-multiplayer-technology-works/) — canonical CRDT-vs-OT write-up; LWW-register + object-tree model.
- [Figma — "Making Multiplayer More Reliable"](https://www.figma.com/blog/making-multiplayer-more-reliable/) — WAL pattern + 95% saves within 600ms.
- [Hello Interview — Design a Collaborative Document Editor](https://www.hellointerview.com/learn/system-design/problem-breakdowns/google-docs) — cleanest interview-framed walkthrough.
- [AlgoMaster — Google Docs System Design](https://blog.algomaster.io/p/google-docs-system-design-interview) — component breakdown + API design.
- [arXiv 2409.14252 — "Collaborative Text Editing with Eg-walker"](https://arxiv.org/abs/2409.14252) — 2024 paper; source of O(n²) divergent-merge claim + OT vs CRDT benchmarks.
