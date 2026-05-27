# Session 9 — Regex DP, Python Singleton, Java Fundamentals, Word Ladder, Distributed-Txn Cluster (CQRS/Saga/2PC/CDC), Concurrent Aggregation

**Date:** May 26, 2026
**Domains:** DSA × 2 · LLD (Python + Java) · Distributed Systems (HLD concepts) · Java fundamentals
**Theme:** Wide-ranging session. Two graph/DP problems, Python design patterns, a Java fundamentals sweep, and a deep distributed-transactions concept chain (CQRS → Saga → 2PC → CDC) that fed straight into an Amazon concurrent-aggregation LLD. Big finish on lock-free high-contention counters.

---

## 🧠 New Algorithms

- **Regex Matching DP (LC 10)** — 2D DP, `dp[i][j]` = does `s[0:i]` match `p[0:j]`.
  - Literal/`.` branch: `p[j-1]==s[i-1] or p[j-1]=='.'` → `dp[i][j] = dp[i-1][j-1]`.
  - Star branch (`p[j-1]=='*'`): `dp[i][j] = dp[i][j-2]` (**zero** occurrences) **OR** `dp[i-1][j]` if `p[j-2]==s[i-1] or p[j-2]=='.'` (**one-or-more**).
  - **Kleene star is ZERO-or-more, not one-or-more.** The unbounded count is carried by `dp[i-1][j]` (consume one char from `s`, keep the pattern index), which recurses through 0,1,2,… occurrences and bottoms out at the zero-case.
  - Empty-string row: `dp[0][j] = dp[0][j-2]` only at even positions where `p[j-1]=='*'` (chain breaks otherwise).
  - O(n1·n2) time/space; rolling row → O(n2) space.

- **Word Ladder BFS (LC 127)** — unweighted shortest path on an *implicit* word graph. Plain **BFS** (uniform edge weight = 1); first dequeue of `endWord` = shortest. Answer = number of words in path (both ends counted); `0` if `endWord ∉ wordList`.
  - **Wildcard pattern buckets** for neighbor generation: build `pattern → [words]`, where each word emits L masked patterns (`hot → *ot, h*t, ho*`). Two words are neighbors iff they share a bucket. Collapses **O(N²·L)** all-pairs → **O(N·L²)**.
  - Alt neighbor gen: probe L positions × 26 letters against a `HashSet` → same O(N·L²) (26 folded as constant).

## 🎯 New Patterns

- **Unbounded-quantifier DP transition** — for `*`/Kleene-style repetition, the recurrence must reference the **same pattern index on a smaller string** (`dp[i-1][j]`), NOT a smaller pattern index. Shrinking `j` counts only a *bounded* number of repetitions; holding `j` while shrinking `i` is what creates the loop. (Root cause of the bug: `dp[i][j-1]` only captures "exactly one" — sound but incomplete.)
- **Edge-weight reflex (reinforced — two misfires this session)** — pick the traversal from the *actual edge weights*, not "most powerful algorithm I know." Look for the 0-weight edge BEFORE reaching for 0-1 BFS; if there's none, it's plain BFS. Reached for Dijkstra, then 0-1 BFS, on a uniform-weight graph — both over-engineered.
- **Lock-free high-contention accumulation** — for millions of writes/sec + occasional read, use **cell-striped adders** (`LongAdder`/`DoubleAdder`), not a single lock and not a single atomic. Each thread updates its own cell (contention-free); reads aggregate cells.
- **Optimize the dominant operation** — when writes vastly outnumber reads, don't tax the write path to protect a rare read. `synchronized`-on-write is backwards under write-heavy load.
- **Per-object locking for contention isolation** — sync on the specific entity (per-`Show` lock in seat locking), not a global lock: same-entity ops serialize, different-entity ops run in parallel.
- **Lock-with-auto-expiry + ownership stamp** — hold a resource (seat) with a timeout via `ScheduledExecutorService`; ownership-stamped unlock (`lockedBy == userId`) prevents another actor releasing your lock.

## 🛠️ Systems / Tools / Libraries

**Java concurrency + language**
- **`LongAdder` / `DoubleAdder`** (`java.util.concurrent.atomic`) — striped counters for high-contention sums. `add()`/`increment()` are lock-free per-cell; `sum()` aggregates on read. Beats both `synchronized` (no serialization) and `AtomicLong` (no CAS spin). The canonical "count millions of events/sec" tool.
- **`AtomicLong`** — CAS-based lock-free counter. Fine for moderate contention; under *extreme* contention the CAS retry-loop spins (all threads fight one memory location).
- **`AtomicReference<Snapshot>`** — CAS-swap an immutable `(sum, count)` object for a *consistent* lock-free snapshot. But CAS-spins + allocates per write → slower under heavy writes. Use only if strict pair-consistency is non-negotiable.
- **`ScheduledExecutorService` / `Executors.newScheduledThreadPool`** — delayed tasks (auto-unlock seat after timeout). Graceful shutdown: `shutdown()` → `awaitTermination()` → `shutdownNow()`.
- **`ConcurrentHashMap.computeIfAbsent`** — atomic lazy init of a nested map.
- **Streams `mapToDouble`/`mapToInt`/`mapToLong`** — return *primitive* streams (`DoubleStream`…) carrying numeric terminal ops (`.sum()`, `.average()`, `.max()`). `.map()` returns boxed `Stream<T>`, which has **no** `.sum()`.

**Python design patterns**
- **Singleton — four flavors:**
  - `__new__` override — interview classic; re-init footgun (`__init__` runs on *every* call even though the cached object is returned → needs an `_initialized` guard).
  - Thread-safe DCL — `_lock` + double-check. Lock = **correctness** (GIL does NOT make check-then-set atomic); outer check = post-init optimization.
  - **Metaclass** (`SingletonMeta.__call__`) — cleanest; gates construction before `__init__` runs, reusable across classes.
  - **Module-level object** — the Pythonic singleton (cached in `sys.modules`, import-lock-safe, zero boilerplate).
  - `@lru_cache(maxsize=None)` on a factory function — quick service-singleton.

**Distributed systems**
- **Debezium** — open-source CDC connector (on Kafka Connect) that tails the DB WAL → Kafka.

## 📚 Terms / Concepts

**Distributed-transactions chain (the session's spine)**
- **CQRS (Command Query Responsibility Segregation)** — *architecture / HLD*. Separate **write** model+store from **read** model+store; sync asynchronously (events / CDC) → **eventual consistency**. Write side normalized + invariant-enforcing; read side denormalized + per-view. Stores can be heterogeneous (Postgres-write → Elasticsearch/Redis/Mongo-read). **NOT a caching strategy, NOT a Thundering-Herd mitigation.**
- **CQS (Command Query Separation)** — the *code-level / LLD* cousin (Bertrand Meyer): a method is **either** a command (mutates, returns void) **or** a query (returns data, no side effects). Anti-pattern = a method that mutates AND returns.
- **Saga** — manage a long-lived multi-service transaction as a sequence of **local commits + compensating transactions** that semantically undo prior steps on failure (refund, not "un-charge"). **Compensation is the defining mechanism — NOT reconciliation.** Flavors: **choreography** (event-driven, no coordinator; implicit flow) vs **orchestration** (central coordinator; explicit, debuggable). Trades atomicity for eventual consistency; replaces 2PC in microservices. Hard part: compensations are *business logic*; some steps don't cleanly undo (email sent) → design idempotent steps + "pivot" points.
- **2PC (Two-Phase Commit)** — distributed atomic-commit protocol.
  - **Phase 1 — Prepare:** coordinator asks all participants; each does the work, **holds locks**, **durably logs a "prepared" record (WAL) + fsync**, then votes YES/NO.
  - **Phase 2 — Commit/Abort:** all-YES → COMMIT, any-NO → ABORT.
  - **The promise** = durable prepared record + held locks ⇒ commit becomes *inevitable* and survives a crash (recovery re-enters the in-doubt state, re-acquires locks, asks coordinator for the verdict).
  - **Costs:** locks held across the network round-trip (throughput collapse under contention); **blocking problem** — coordinator dies post-vote → participants stuck in-doubt holding locks, can't resolve alone. This is *why microservices reject 2PC* → Saga. **3PC** is non-blocking in theory but fails under partitions → real systems use **consensus (Raft/Paxos)** for a fault-tolerant replicated coordinator.
- **CDC (Change Data Capture)** — stream every committed row change out of a DB by **tailing its WAL** (Postgres logical replication / MySQL binlog). Zero app involvement, nothing missed, low overhead (sequential log read). Feeds: cache invalidation, CQRS read-model sync, search indexing, analytics. **It's the plumbing; CQRS/Saga are what you build on top.** Captures low-level row deltas, not rich domain events.
- **Write-through cache vs 2PC** — write-through writes two stores (cache + DB) but **not atomically**; the cache is disposable/derived, best-effort, TTL heals. 2PC is all-or-nothing across N *peer authoritative* stores. Don't conflate "writing to 2 places" with atomic commit.
- **WAL (recap)** — DB's durable change log; source of truth for crash recovery, replication, 2PC prepared records, and CDC.

**Concurrency / aggregation**
- **"Correct average at any instant" isn't strictly definable under continuous concurrent writes** — no single moment the system is at rest; any returned value is stale the nanosecond the lock releases. The real engineering question = *which op to optimize* + *what staleness is tolerable*.
- **Consistency tradeoff of separate adders** — `sum.sum()` then `count.sum()` are read separately, so a write can slip between → off by ~1 reading out of millions = negligible for averaging.
- **CAS contention** — many threads CAS-ing the *same* variable spin and retry; contention just moves from lock to CAS. Striping (`LongAdder`) avoids it.
- **Running average via (sum, count)** — never store all readings (unbounded memory); keep two aggregates, O(1) update, compute on read. Watch unbounded-sum overflow (periodic reset / `BigDecimal` in prod).

**Java language**
- **`ordinal()`** — zero-based declaration-order position of an enum constant. Backs `EnumSet`/`EnumMap` (bit position). **Anti-pattern:** persisting it or branching on it — reordering constants silently corrupts stored data (no compile error). Enum natural ordering (`compareTo`, `TreeSet`) IS ordinal order. Safe across boundaries: `valueOf(name)` or an explicit code field.
- **Java imports** — compile-time aliases (simple name → fully-qualified); NOT C `#include`; zero runtime cost (bytecode always fully-qualified). `java.lang` auto-imported. Wildcard `*` is **non-recursive** (no subpackages) and free. Static imports pull in static members. **Single-type import beats wildcard** on a name conflict (`java.util.Date` vs `java.sql.Date`).
- **Primitive vs boxed streams** — `mapToDouble` → `DoubleStream` (has `.sum()`); `map` → `Stream<Double>` (no `.sum()`; must unbox/reduce).

**Python (recap)**
- **GIL & atomicity** — single C-level ops are atomic; a multi-step check-then-act (Singleton `if None: create`) is **not** — the GIL can switch threads between bytecodes → lock required for correctness.

## 🅿️ Backlog Surfaced

- **Word Ladder II (LC 126)** — return ALL shortest sequences. BFS to build layers + DFS to reconstruct. Harder; do after 127 is solid.
- **Regex Matching (LC 10)** — code parked mid-correction. Re-implement clean with the corrected star recurrence, then verify on `s="aa", p="a*"` (→ True) and `s="ab", p=".*"` (→ True).
- **Consensus (Raft/Paxos)** — surfaced via the 2PC blocking problem → fault-tolerant replicated coordinator. Standing HLD backlog item, now strongly motivated.
- **Idempotency / Stripe-style keys** — still pending; natural companion to Saga + exactly-once.
- **3PC** — non-blocking 2PC variant, partition assumptions. Light touch only.

## 🔗 References

- LC 10 — Regular Expression Matching: https://leetcode.com/problems/regular-expression-matching/
- LC 127 — Word Ladder: https://leetcode.com/problems/word-ladder/
- LC 126 — Word Ladder II: https://leetcode.com/problems/word-ladder-ii/
- LC 2008 — Maximum Earnings From Taxi (the genuine `bisect_left` problem): https://leetcode.com/problems/maximum-earnings-from-taxi/
- LC 2812 — Find the Safest Path in a Grid (binary-search-on-answer, not `bisect`): https://leetcode.com/problems/find-the-safest-path-in-a-grid/

---

*No StatQuest / 3Blue1Brown this session — no ML or math-intuition topics covered.*
