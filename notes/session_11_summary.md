# Session 11 — Python Heap Fundamentals + DSA Gauntlet + Google Docs Full HLD

**Date:** May 30, 2026
**Domains:** Python fundamentals (organic) · DSA × 4 · HLD (Hard — Google Docs) · HLD deep-dive follow-up
**Theme:** Heavy organic Python session (heapq, stack, deque, f-strings) + four monotonic-stack/two-pointer DSA problems + the most comprehensive HLD of the prep so far (Google Docs, OT vs CRDT, event sourcing, WAL, gRPC vs WebSocket, pessimistic distributed locking, broadcast fan-out).

---

## 🧠 New Algorithms

### K-way heap merge (LC 23 — Merge K Sorted Lists)
Store `(val, list_index, node)` triples in the heap. Key invariant: **each list contributes at most ONE node to the heap at any moment** — pop list `i`'s node, advance, push back with same `i`. This guarantees `i` is unique among heap entries, so `(val, i)` never ties → node comparison never reached. Complexity: O(N log K).

### Longest Valid Parentheses — stack-of-indices (LC 32, Hard)
Store **indices**, not characters. `stack[-1]` is always the index of the last character that is NOT part of the current valid run (the "wall"). `length = current_index − stack[-1]`. Two types of entries:
- Unmatched `(` index: the potential left wall if it never closes.
- Unmatched `)` index: a hard wall pushed when the stack is empty on a `)`.
Init with `[-1]` (virtual wall before the string). On `)`: pop; if stack empty → push current index as new wall; else `ml = max(ml, i − stack[-1])`.

Alternative — **counts in stack**: push `0` instead of `'('`. On match: `matched = pop() + 2`, add to new top (`stack[-1] += matched`). Unmatched `)`→ reset to `[0]`. Each nesting level accumulates its own length; an unmatched `(` walls off regions by keeping its count isolated.

Alternative — **two-pass counter** (O(1) space): count `open`/`close` L→R (reset when `close > open`, record when equal), repeat R→L (reset when `open > close`). Needed because one pass is blind to trailing unmatched `(`.

### Largest Rectangle in Histogram — single-pass monotonic stack (LC 84, Hard)
Stack of **indices**, monotonically increasing in height. On a shorter bar: pop `top`, compute area = `heights[top] × (i − stack[-1] − 1)`. Left boundary = new top of stack after pop (revealed neighbor); right boundary = current `i`. Sentinel `heights.append(0)` flushes everything cleanly. No post-loop cleanup needed.

Divide-and-conquer alternative (O(n log n)): find min-bar index → area = `h[min] × width`; recurse left and right halves. Use sparse table/segment tree for range-min query.

### Trapping Rain Water — two-pointer (LC 42, Hard) ⚠️ REVISIT FRESH
Anchor at ends, process only the committed side's own max, never `min`:
```python
l, r = 0, len(h) - 1
l_max = r_max = 0
while l < r:
    if h[l] < h[r]:
        l_max = max(l_max, h[l])
        res += l_max - h[l]
        l += 1
    else:
        r_max = max(r_max, h[r])
        res += r_max - h[r]
        r -= 1
```
**The one insight that unlocks it:** `h[l] < h[r]` doesn't tell you the water level — it tells you the **safe-to-commit side**. When h[l] < h[r], you know a right bar ≥ h[r] > h[l] exists, so l_max is the binding constraint. Process left with l_max alone. Symmetric for right.

**The trap that cost 2 hours:** Inward init `l=1, r=n-2` + preloading `h[0]/h[-1]` into maxes **breaks the invariant** and cannot be patched:
- `min(l_max, r_max)` undercounts when a tall bar hides in the unscanned middle (`[8,3,9,10,6,5,10]` → 12, not 14).
- Side's-own-max overcounts at boundaries (`[3,0,0,5]` → 10, not 6).
The standard init (l=0, r=n-1, maxes=0) works because the branch guarantees the committed side has a **complete** max (the pointer has scanned everything from its end inward).

---

## 🎯 New Patterns

### Monotonic stack with indices — the universal rule
For any next-greater / boundary-distance / slab problem: **store indices, not values**. The index is the position; the value is looked up via `heights[idx]`. Pop gives you a triple: (the popped element, the element beneath it as left boundary, the current element as right boundary). Length/width flows from `i − stack[-1] − 1`.

Relevant problems: LC 42, 84, 32, 739, 503, 1019 — all the same family.

### Two-tier fan-out for broadcast at scale
Publisher emits **once** to a pub/sub backbone (Kafka, Redis Pub/Sub). Every gateway server subscribed to that channel receives it and pushes locally to its own connected sockets. The publisher never tracks where clients live. For one channel with millions of subscribers: hierarchical fan-out tree (origin → N relays → M clients each). Fan-out-on-write vs fan-out-on-read tradeoff.

### Event sourcing
Don't store current state and mutate it. Store the **full append-only sequence of events** and derive current state by replay. Benefits: full audit trail, time travel, multiple read projections, high write throughput (sequential append). Cost: replay is O(n) → mitigate with **periodic snapshots** (replay only the tail). Pairs with CQRS. The Google Docs op log IS event sourcing.

### WAL pattern (Write-Ahead Log)
Append sequentially → **ensure durable** (fsync or replicate) → ack the client → async apply/materialize to the primary store. On crash, replay the WAL. The speedup comes from converting a slow random/replicated write into a fast sequential append on the ack path, decoupling durability from materialization. A local WAL has lower latency than a distributed Kafka round-trip because there's no cross-broker replication before ack.

### Optimistic vs pessimistic — when to pick
- **Optimistic** = proceed freely, detect conflict on commit, retry. `UPDATE ... WHERE version = expected`, `CAS`, `SETNX`, git, OT/CRDT, ETag+If-Match, optimistic UI. Best when **conflicts are rare**.
- **Pessimistic** = lock before touching, block others. `SELECT FOR UPDATE`, `synchronized`/`ReentrantLock`, `ZooKeeper ephemeral znode`, section-locks. Best when **conflicts are frequent** or rollback is expensive.
- Examples: DB OCC vs row locks; Java `AtomicInteger.compareAndSet` vs `synchronized`; git (optimistic) vs Perforce lock checkout (pessimistic); inventory booking; collaborative text (OT) vs section-lock.

### Sticky routing / per-doc ownership
Map `doc_id → owning_instance` via consistent hashing + a lease store (ZooKeeper ephemeral node / etcd lease / Redis SETNX with TTL). Claim is atomic (CAS). Lease auto-expires on server death so a new owner can claim. The gateway terminates the WebSocket, resolves the owner from the coordinator, and proxies the op stream. This = **Ringpop** (Uber's gossip-based consistent-hash sharding library).

---

## 🛠️ Systems / Tools / Libraries (named things)

- **heapq** — Python stdlib module, C-accelerated via `_heapq`. Min-heap in-place on a plain `list`. No comparator param; use tuple trick or `__lt__` wrapper. `heapify` is O(n), not O(n log n).
- **collections.deque** — O(1) at both ends. The queue/0-1BFS primitive. `deque[-1]` and `deque[0]` O(1); middle index O(n).
- **queue.Queue** — thread-safe FIFO for threading; **never** for DSA algos (slow).
- **itertools.count()** — global monotonic counter; `next(counter)` guarantees a unique tie-breaker in a heap.
- **Jupiter algorithm** — OT variant used by Google Docs (and Google Wave). Central server serializes ops per document, transforms against concurrent ops, assigns revision numbers.
- **Ringpop** — Uber's gossip-based consistent-hash sharding library. Per-doc ownership in a collaborative editor is a textbook Ringpop use case.
- **RAMEN** — Uber's WebSocket push platform, 1M+ concurrent connections per box. The broadcast layer for large-scale fan-out.
- **ZooKeeper / etcd** — coordination services for distributed leases and ephemeral nodes; the basis for distributed pessimistic locks and leader election.
- **Redlock** — Redis distributed lock algorithm; controversial because clock skew + GC pauses can make holders believe they still hold an expired lock. Mitigation: **fencing tokens** (monotonically increasing, checked by storage layer to reject stale writers).
- **QUIC** — UDP-based transport (Google-origin). TLS 1.3 baked in; multiplexed streams where a lost packet only stalls its own stream (no TCP head-of-line blocking). Faster handshake (0–1 RTT).
- **WebTransport** — browser API over HTTP/3/QUIC for bidirectional streams + datagrams. Emerging WebSocket alternative.
- **gRPC-Web** — browser-compatible gRPC variant via a proxy (Envoy). Supports server-streaming; historically **cannot** do client-initiated bidirectional streaming from a browser.
- **Figma multiplayer** — CRDT-inspired (tree of LWW-registers per object property). Not a text CRDT; doesn't need OT because Figma isn't a text editor.
- **Yjs** — production CRDT library (YATA algorithm) used for text collaboration. State-vector diffing for offline sync.

---

## 📚 Terms / Concepts

### Python fundamentals

**heapq — no built-in comparator:**
- Tuple trick: `(priority, idx, value)` — compare element-by-element; `idx` as unique tie-breaker.
- Monotonic counter: `counter = itertools.count(); heapq.heappush(heap, (val, next(counter), obj))`. Every push gets a unique second field.
- Wrapper: `class Item: def __lt__(self, other): return self.priority < other.priority`.
- Min-heap only. Max-heap: negate values (`-val`).

**Python stack:** plain `list`. `append(x)` = push (O(1) amortized). `pop()` = pop from right (O(1)). `pop(0)` = O(n) — **never do this.**

**deque key operations and complexities:**
```
append(x)      O(1)  — right
appendleft(x)  O(1)  — left
pop()          O(1)  — right
popleft()      O(1)  — left
d[0], d[-1]   O(1)  — end access
d[i]           O(n)  — middle (not random-access)
rotate(n)      O(k)
```
Usage map: BFS → `append + popleft`; 0-1 BFS → `appendleft` for 0-weight, `append` for 1-weight; sliding window → pop/push both ends.

**Python f-strings — format spec `{value:[fill][align][width][,][.precision][type]}`:**
```python
f"{42:05d}"      # "00042"     zero-pad
f"{3.14:.2f}"    # "3.14"      2 decimals
f"{1234567:,}"   # "1,234,567" thousands sep
f"{0.85:.1%}"    # "85.0%"     percent
f"{255:#010b}"   # "0b11111111" binary with prefix, width 10
f"{'hi':-^10}"  # "----hi----" fill + center
f"{x=}, {y=}"   # "x=10, y=20" debug syntax (Python 3.8+)
```

---

### Google Docs HLD — the core design

**The reframe:** Google Docs is a **concurrency problem**, not a storage problem. The hard part is reconciling simultaneous edits so everyone converges.

**The core problem (Alice/Bob):** both edit local copies; edits cross in flight. Naive apply-in-order → position drift → divergence. Three solution families: locking (pessimistic, bad UX), OT (Google's choice), CRDT (Figma's choice).

---

### Operational Transformation (OT)

Represent edits as operations: `insert(pos, char)`, `delete(pos)`, `retain(n)`. The primitive: a **transform function T(opA, opB)** that rewrites one op to account for the other's concurrent effect. Example: Alice inserts at position 3, Bob deletes at position 1 → Bob's delete shifts Alice's position by -1 → transform adjusts to position 2.

**Jupiter algorithm** (Google Docs): central server serializes all ops per document. Client sends op + last-seen revision. Server transforms the incoming op against everything committed since that revision, assigns the next revision number, applies, broadcasts. Result: a **single canonical sequence** per doc.

**Why central server is a correctness requirement (not a weakness):** OT's transform functions are only proven correct with a single serializer. Two instances both transforming the same doc's ops independently → two different canonical sequences → divergence. The single serializer IS the concurrency control mechanism.

**Serialization analogy:** like Python's GIL — one thread (the OT instance) processes one doc's ops sequentially. Different docs run on different instances in parallel (like different processes each with their own GIL). Per-doc serial, cross-doc massively parallel.

**OT's cost for offline:** user edits for an hour offline (N ops based on old version V). Others made M ops online (version now V+M). On reconnect: transform each of N against each of M → **O(N × M)**. Large offline gaps = quadratic reconciliation cost.

---

### CRDT (Conflict-free Replicated Data Type)

Design the data so operations **commute** — apply in any order, same result. No central server needed.

**For text:** give every character a **unique, stable, totally-ordered ID** (fractional index or tree position). Inserts use positions between existing IDs. Deletes leave **tombstones** (hidden but still anchor ordering). Any subset of operations, applied in any order, sorts characters identically → convergence.

**Cost:** 16–32 bytes of metadata per character; tombstone accumulation; slow document load and high memory for large docs. Mitigate with garbage collection (Figma removes tombstones >24h, accepting brief inconsistency for late-joiners).

**Offline advantage:** CRDT ops carry stable IDs and commute → merging a divergent offline branch is "union ops, sort by ID" — no N×M cascade. Natural fit for offline-first.

---

### LWW-Register (Last-Write-Wins Register)

The simplest CRDT. A single-value cell where each write carries a timestamp. Merge = take the **max-timestamp value**. Commutative (max is order-independent) + associative + idempotent → valid CRDT.

**Limitation:** loses the losing concurrent write (one is discarded). Fine for a property like `color` or `width`. Useless for text (you'd lose characters).

**Figma's model:** every Figma document is a tree of objects (like the DOM). Each property of each object is an LWW-register. Two people set the same rectangle's `width` simultaneously → later write wins → convergence. No OT needed because Figma isn't editing a linear text sequence. That's why their "CRDT" is simple — it's mostly a tree of LWW-registers, not a sequence CRDT.

---

### OT vs CRDT — the definitive comparison

| Dimension | OT (Google Docs) | CRDT (Figma / Yjs) |
|---|---|---|
| Per-char metadata | None (tiny ops) | 16–32 bytes + tombstones |
| Central server | Required (correctness) | Not needed |
| Offline / P2P | Expensive (O(n²) divergent merge) | Natural (commutative merge) |
| Intent preservation | Better for rich text | LWW can lose concurrent edits |
| Correctness proof | Hard (transform matrix) | Mathematical guarantee |
| Best for | Online-first, rich text, memory-sensitive | Offline-first, P2P, structured data |

**The nuance that impresses interviewers:** "I'd use OT for the online real-time path (proven at scale, low memory), and seriously consider a CRDT layer (Yjs-style state vector) for the offline sync path where OT's divergent-merge cost is quadratic."

---

### ACL (Access Control List)

A list attached to a resource specifying **who** (principal) can do **what** (permission). For Google Docs: `{ alice: owner, bob: editor, carol: commenter, "link": viewer }`. Checked before every edit. Must stay fast → cached aggressively at the collab tier with short TTL + invalidation on share changes.

Permission levels: owner > editor > commenter > viewer. Siblings: RBAC (permissions on roles, users get roles) and ABAC (policy/attribute-based). ACL = per-resource explicit list.

---

### Event sourcing

Don't store current state; store the **full sequence of state-changing events** append-only. Current state = replay of events. The Google Docs op log IS event sourcing.

Benefits: full history for free, time travel, multiple read projections, high write throughput. Cost: replay is O(n) → snapshot every N events and replay only the tail. The Google Docs pattern: snapshot every ~100 ops (some systems every 500 ops or every 5 min). Load time = load latest snapshot + replay tail. Pairs with CQRS.

---

### WAL (Write-Ahead Log) pattern

Append to sequential log (durable) → flush to disk/replicate → ack the client → **asynchronously** apply to the primary/queryable store. On crash: replay WAL to recover unmatched ops.

Why it's faster than synchronous primary-store writes: sequential append to nearby storage is microseconds–milliseconds; a synchronous write to a distributed primary store (network + replication) is tens–hundreds of milliseconds.

"Isn't Kafka a WAL?" — **yes, Kafka is architecturally a distributed commit log / WAL**. Both embody the same principle. The distinction is latency and locality: a co-located WAL append before ack is faster than a Kafka round-trip (cross-broker replication on the hot path). Kafka excels as the **async durable backbone + fan-out layer**; a local WAL is for **fast ack latency**.

---

### Two-path architecture (Google Docs)

**Fast path (perceived latency):** keystroke → optimistic local apply → WebSocket → OT server (transform + assign revision) → fan-out to collaborators. Never waits on disk.

**Reliable path (durability):** OT server → Kafka buffer → append to operation log (before ack) → async snapshot. The Kafka buffer decouples the real-time path from slow persistent writes.

---

### Sticky routing per doc + discovery

Clients connect to any stateless gateway. Gateway resolves `doc_id → owning_instance`:
- **Consistent hashing on doc_id** → deterministic owner computation, no central lookup needed (mostly).
- **Lease store** (ZooKeeper ephemeral node / etcd lease / Redis SETNX + TTL) → atomic claim, auto-expires on death, prevents split-brain.
- On reconnect after owner death: new instance claimed via atomic CAS, rehydrates from `snapshot + op log tail`.
- This architecture = **Ringpop** (Uber's gossip-based sharding library).

---

### Presence & cursors

Ephemeral, separate from the edit pipeline. Redis hash keyed `presence:{doc_id}:{client_id}` → `{ cursor_pos, selection_range, user_name, color, last_seen }`. TTL = heartbeat (refresh on each cursor move; expiry = user gone). Broadcast via pub/sub channel per doc. Throttled/coalesced so 100 cursor moves/sec don't become 100 presence broadcasts.

---

### RPC vs REST vs GraphQL

| Style | Paradigm | Format | Transport | Best for |
|---|---|---|---|---|
| REST | Resources/nouns, HTTP verbs | JSON | HTTP/1.1+ | Public APIs, browser-facing |
| gRPC (RPC) | Procedures/verbs | Protobuf (binary) | HTTP/2 | Internal service-to-service |
| GraphQL | Client queries exactly what it needs | JSON | HTTP | Flexible data fetching, BFF layer |

**gRPC and WebSocket are different transports.** gRPC runs over HTTP/2 (not WebSocket). Browsers can't speak raw gRPC → use gRPC-Web, which has limited streaming (no browser-initiated bidi streams). For browser bidi → WebSocket (or emerging WebTransport over HTTP/3/QUIC).

---

### HTTP protocol evolution (transport axis — orthogonal to Web2/Web3)

- **HTTP/1.1:** text-based, one request per connection at a time, head-of-line blocking.
- **HTTP/2:** binary framing, multiplexed streams over one TCP connection, header compression (HPACK). gRPC rides this. Still has TCP head-of-line blocking (one lost packet stalls all streams).
- **QUIC:** UDP-based transport (Google). TLS 1.3 built in. Per-stream loss isolation (lost packet only stalls its own stream). 0–1 RTT handshake. Removes TCP head-of-line blocking.
- **HTTP/3:** HTTP semantics over QUIC. Big win on lossy/mobile networks.
- **WebTransport:** browser API over HTTP/3/QUIC for bidi streams + datagrams. The emerging WebSocket replacement.

---

### Web2 vs Web3 — era axis (orthogonal to HTTP versions)

- **Web 1.0:** static read-only pages. Consume, don't contribute.
- **Web 2.0:** interactive, user-generated content, SaaS, social. Read-write. (Facebook, YouTube, Google Docs are Web 2.0.)
- **Web3:** proposed decentralized web on blockchains — crypto tokens, smart contracts, ownership without central platforms. A philosophy/ownership model, not a protocol.

**Key:** "Web3" (blockchain) and "HTTP/3" (transport protocol) are completely orthogonal. You can run a Web 2.0 app over HTTP/3. The naming collision is confusing; they have nothing to do with each other.

---

### Distributed pessimistic locking

**Mechanism:** distributed lock keyed per region — `lock:{doc_id}:{region_id}`. Acquire before editing, release after. Implementations:
- **ZooKeeper ephemeral znodes:** create a node to acquire; if it exists, someone holds it; auto-released when the holder's session dies. Classic distributed lock.
- **etcd leases:** similar, with TTL.
- **Redis SETNX + TTL:** simpler, but Redlock controversy (clock skew / GC pauses can cause false expiry → stale holder writes after TTL).
- **Fencing tokens:** monotonically increasing number on each lock acquisition; storage layer rejects writes from holders with a stale token. Fixes the Redlock problem.

**Real examples:** Microsoft Word co-authoring (paragraph-level locks), older wikis (page-level), some CAD/design tools (object locks).

**Why text avoids it:** terrible UX (blocked while others type), coordination overhead, text is too fine-grained. Works for coarse/discrete objects (cells, shapes, sections), not for fluid text.

---

### Broadcast fan-out at scale

**Two-tier pattern:**
1. Publisher emits once to a pub/sub backbone (Kafka / Redis Pub/Sub).
2. Each gateway server subscribed to that channel receives it and pushes to its own locally-connected sockets.

Publisher never tracks where clients live. No central registry of `client → socket` needed (gateways subscribe to channels by `doc_id`).

For a single doc (~3–100 editors): cheap. For millions on one channel (live event / hot topic): hierarchical fan-out tree (origin → N relay boxes → M clients each). This is the **fan-out-on-write vs fan-out-on-read** decision — push eagerly to all subscribers (write fan-out) vs let subscribers pull on demand (read fan-out).

Scale reference: **RAMEN** (Uber) = 1M+ concurrent WebSocket connections per box.

---

### Idempotency (extended)

Client generates an **idempotency key** (UUID or `(clientId, sequenceNumber)`) per logical operation. Server records processed keys + their results; on a duplicate key, returns the cached result.

**The atomic part matters:** "check if key exists, then skip" is a TOCTOU race. The check-and-record must be atomic: unique constraint + `INSERT ON CONFLICT DO NOTHING` (check rows affected), `SETNX`, or conditional UPDATE. Same family as OCC / CAS.

**For Google Docs ops:** key = `(clientId, seqNumber)`. The op log dedupes on it. Applying op #5 from client X twice is a no-op. On reconnect, client sends its last-known revision; server streams missed ops; duplicate-key ops are idempotent.

---

## 🅿️ Backlog Surfaced

- **REVISIT (DSA):** LC 42 Trapping Rain Water — flagged for fresh solo retry. Core trap: inward init. Core insight: the branch picks the safe-to-commit side, not the water level. Revision angle: pose as monotonic-stack slab form or as a next-greater-node variant.
- **REVISIT (HLD):** Fan-out at scale deep-dive — two-tier pub/sub, hot-topic hierarchical fan-out, fan-out-on-write vs read, RAMEN internals.
- **NEW (HLD):** Amazon WAF + CloudFront — parked at session start, never reached. CloudFront = edge CDN for static assets + media (the Google Docs media layer). WAF = application-layer firewall protecting API/WebSocket endpoints (rate-limit the op stream, block malicious payloads before gateway). Next HLD part.
- **CARRY-FORWARD (HLD):** Ringpop deep-dive — appeared organically today (sticky routing = Ringpop). Now has concrete context; ready for standalone session.
- **CARRY-FORWARD (HLD):** Distributed locks (Redlock, fencing tokens) — appeared in pessimistic-locking discussion. Fencing tokens + clock skew problem = the core controversy. Worth its own deep-dive.

---

## 🔑 New Keywords Quick-Reference

| Term | One-line definition |
|---|---|
| Operational Transformation | Transform concurrent ops to preserve intent + convergence; central server serializes |
| Jupiter algorithm | Google's OT variant; client sends op + last-seen revision; server transforms + sequences |
| CRDT | Data structured so ops commute; merge in any order = same result; no central authority |
| LWW-register | Single-value CRDT; last-write-wins via max-timestamp merge |
| Tombstone | Deleted-but-retained character in a sequence CRDT; anchors ordering without shifting |
| Event sourcing | Store full event log; derive state by replay; snapshot + tail = efficient load |
| WAL (Write-Ahead Log) | Append + flush durably → ack → async apply to primary; sequential write beats random |
| Sticky routing | Route all connections for a given doc_id to one owner instance |
| Fencing token | Monotonically increasing lock sequence number; storage layer rejects stale holders |
| ACL | Access Control List; per-resource list of (principal, permission) pairs |
| QUIC | UDP-based transport; TLS built-in; per-stream loss isolation; HTTP/3 rides it |
| Fan-out | Distributing one message to N subscribers; two-tier: publish once → gateways push locally |
| Serialization (OT) | Processing ops one-at-a-time in a single total order; the GIL analog for a doc |
| Two-path architecture | Fast path (WebSocket → transform → broadcast) + reliable path (Kafka → op log) |
| heapq | Python stdlib min-heap on a list; no comparator; use tuple trick or __lt__ |
| Monotonic counter | `itertools.count()` gives globally unique tie-breaker integers for heap tuples |

---

## 🔗 References

- [Figma — "How Figma's Multiplayer Technology Works"](https://www.figma.com/blog/how-figmas-multiplayer-technology-works/) — Evan Wallace, co-founder. The canonical CRDT-vs-OT "we chose differently" post. Read it for the object-tree/LWW model.
- [Figma — "Making Multiplayer More Reliable"](https://www.figma.com/blog/making-multiplayer-more-reliable/) — WAL pattern + the 95% edits saved within 600ms target.
- [Hello Interview — Design a Collaborative Document Editor](https://www.hellointerview.com/learn/system-design/problem-breakdowns/google-docs) — cleanest interview-framed walkthrough; mirrors real delivery.
- [AlgoMaster — Google Docs System Design](https://blog.algomaster.io/p/google-docs-system-design-interview) — strong on component breakdown and API design.
- [arXiv 2409.14252 — "Collaborative Text Editing with Eg-walker"](https://arxiv.org/abs/2409.14252) — 2024 paper benchmarking OT vs CRDT; source of the O(n²) divergent-merge claim.
- Uber H3 Blog, Ringpop GitHub — carry-forward from prior sessions (sticky routing context).

---

## ⚠️ Session Notes

- **WAF + CloudFront** parked at session start — never reached. Pull as first HLD next session (or standalone).
- **Fan-out at scale** he wants a dedicated revisit — RAMEN internals, hot-topic fan-out tree, fan-out-on-write vs read.
- **LC 42 Trapping Rain Water** — flagged for fresh retry. Do NOT walk through the solution; pose it cold and let him solve from scratch. Trap to watch: inward init.
- **LLD language tracking:** no LLD problem this session (pure HLD + DSA organic). Python was the language of the organic tangents. Java still owed for the weekly 3/3/1 cadence.
- This session was entirely organic — no structured 5-part format. All content emerged from a Google Docs HLD deep-dive that grew into 18 concept sub-questions. Arguably one of the highest-density sessions in the prep.
