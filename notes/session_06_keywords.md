# Session 6 — Constructive Greedy + Concurrent LRU + URL Shortener Full Tour

**Date:** May 13, 2026
**Domains:** DSA · LLD (Python) · HLD · Revision (partial)
**Theme:** First session under the new 4-part format. Cracked an Amazon OA constructive problem, built a thread-safe LRU from scratch in Python (12 bugs → 0 in 3 iterations), and went deep on URL shortener from QPS estimation through pigeonhole impossibility and viral-key mitigations.

---

## 🧠 New Algorithms

- **Constructive greedy for subset-sum permutation** — Given a permutation of `{1..n}` with some signs flipped, achieve a target sum. Key trick: reformulate as "which subset N gets negated?" with `sum(N) = (S − target) / 2` where `S = n(n+1)/2`. Greedy from largest down: include `i` if `i ≤ remaining`. O(n).
- **Snowflake ID generation** — `[timestamp_ms (41 bits) | machine_id (10 bits) | sequence (12 bits)]`. Each server generates IDs locally with zero coordination, guaranteed globally unique by construction. Twitter's design, used everywhere.
- **Single-flight / request coalescing** — When N concurrent requests want the same uncached key, first caller starts a Future/Promise, all others await the same one. 1 DB query serves N callers. Go's `singleflight`, trivial in JS Promises, easy in Python `asyncio.create_task` + `dict`, Java `ConcurrentHashMap.computeIfAbsent` + `CompletableFuture`.

## 🎯 New Patterns

- **Double-Checked Locking (DCL)** — Unsynchronized fast-path read; if it suggests work is needed, acquire lock and re-verify. Pattern: `if (key in cache) { lock { if (key in cache) { do_work() } } }`. Real performance win in Java/C++ where it lets multiple threads read in parallel. **Largely useless in Python** due to GIL serializing all bytecode anyway.
- **Key replication with random suffix** — Mitigate hot-key bottlenecks: store the same value at `K_0`, `K_1`, ..., `K_{N-1}`. Reader picks a random suffix. Writes amplify N×, but read load on a viral key spreads across ~N shards. Only applied to known hot keys (not all keys — would 10× storage).
- **Write-Around with read-population** — Writes go straight to DB; cache populates only on read miss. For long-tail read patterns, this naturally fills cache with hot items only. Strictly better than write-through when most writes are never read.
- **Optimistic concurrency via conditional INSERT/SET (SETNX)** — First writer wins; second writer detects existing key and reports collision. Used for custom URL aliases ("first to claim wins"), idempotent dedup, and as a CAS primitive.
- **In-process LRU on top of distributed cache** — App servers each cache top-K hottest keys in their own heap before hitting Redis. Sub-millisecond reads for viral content; cuts Redis load 90%+.
- **Persistent cache for cold-start protection** — Redis AOF / RDB snapshots → cache survives reboot, avoids DB stampede on failover.

## 🛠️ Systems / Tools / Libraries

- **CDN edge caching** — Cloudflare, Fastly, Akamai. PoPs (Points of Presence) globally; anycast DNS routes user to nearest PoP. Foundation of global low-latency reads.
- **base62 encoding** — `[A-Z][a-z][0-9]`, 62 symbols. URL-safe. 7 chars = 62⁷ ≈ 3.5 trillion codes. What bit.ly / tinyurl actually use.
- **base64url** — base64 variant with `+` → `-`, `/` → `_`. URL-safe RFC 4648 alphabet.
- **`functools.lru_cache`** — Python stdlib memoization. Function-level only, no manual eviction, no TTL, args must be hashable. Thread-safe in CPython.
- **Caffeine** — JVM cache library. Uses W-TinyLFU eviction (near-optimal hit rates) with lock-free reads and amortized writes.
- **W-TinyLFU, CLOCK** — Approximate-LRU eviction policies. Don't mutate eviction structure on every read; defer or use a "referenced" bit.
- **`ConcurrentHashMap.computeIfAbsent`** — Java's atomic check-and-insert. Magic primitive for single-flight in Java.
- **`asyncio.Lock` vs `threading.Lock`** — `asyncio.Lock` is **task-safe within one event loop**, not thread-safe across threads. Pure asyncio often needs no lock at all (no `await` in critical section = atomic by construction).
- **`RLock` (reentrant lock)** — Same thread can acquire multiple times. Use over plain `Lock` when methods may call each other while holding the lock.
- **gunicorn / uvicorn / WSGI workers** — Multi-process Python deployment. `gunicorn -w 4 --threads 8` = 4 worker processes × 8 threads = 32 concurrent request slots.
- **libuv thread pool (Node.js)** — Default 4 threads for operations OS can't do async natively (file I/O, DNS, crypto). NOT used for network I/O, which uses `epoll`/`kqueue` directly.

## 📚 Terms / Concepts

- **Shannon entropy floor** — Mathematical lower bound on lossless compression. No algorithm can compress below the information content of the source distribution. For typical URLs: ~3–4 bits/char × ~50 chars ≈ 150–200 bits true entropy.
- **Pigeonhole principle (applied to URL shortening)** — Cannot losslessly map an infinite/huge space (arbitrary URLs) onto a finite/small one (7-char codes). The lookup table is **mathematically required**, not an implementation choice.
- **Compression overhead on small inputs** — gzip/Huffman embed dictionary/headers in output. For tiny inputs like a 43-byte URL, gzip produces ~63 bytes — **larger than the input**. Compression only beats raw when overhead amortizes over a long payload.
- **Lossless vs lossy** — Lossless (ZIP, gzip, PNG, FLAC) preserves every bit. Lossy (JPEG, MP3, MP4) discards info humans can't perceive — reconstruction is approximate. URLs require lossless; redirecting to "almost the right URL" is broken.
- **TOCTOU race** — Time-Of-Check to Time-Of-Use. Reading state outside a critical section and acting on it inside is unsafe; state may have changed.
- **GIL atomicity (CPython)** — Single C-level operations on built-in types (dict `in`, list `append`, etc.) are atomic because the GIL is held throughout one C call. Multi-step operations are not.
- **Long tail / power-law / Pareto / Zipf** — ~80% of traffic comes from ~5% of items. Most short URLs get few or zero reads; a handful go viral. Drives Write-Around cache policy.
- **Hot key problem** — One viral key gets disproportionate traffic, overwhelming the single shard / replica holding it. Solved with key replication, in-process LRU, read replicas.
- **Cold cache cascading failure** — On reboot/failover, empty cache means every read misses → DB stampede → DB falls over → recovery stalls → systems hang. Mitigations: persistent Redis, cache warming, single-flight, request coalescing.
- **Per-process vs distributed coordination** — Single-flight deduplicates within ONE worker process. Cross-process / cross-server deduplication requires distributed locks (Redis SETNX, Redlock). Per-process suffices ~99% of the time.
- **Multi-master vs in-sync replicas** — Orthogonal concepts. Multi-master = multiple nodes accept writes. In-sync replicas = write ack'd only after N replicas have it. Can combine in any way.
- **Concurrency models** — Three flavors:
  - **Thread pool** (Java, WSGI threads): N threads share one process; OS schedules.
  - **Process pool** (Python gunicorn, PHP-FPM): N isolated processes, each with own memory/GIL.
  - **Event loop** (Node.js, asyncio, Go): One thread; coroutines yield at `await`; OS-level non-blocking I/O.
- **Async ≠ multi-threaded** — Async = cooperative yielding on a single thread. Multi-threaded = truly parallel execution. JavaScript is async without multi-threading. Java's executor is multi-threaded without async (until Project Loom).
- **Event loop blocking** — Sync CPU-heavy work on the event loop thread blocks ALL concurrent requests. #1 footgun of async runtimes. Offload to worker threads or separate processes.
- **HTTP 302 (Found)** — "Go fetch this other URL instead." Used for redirects. (301 vs 302 parked for next session.)
- **Anycast DNS** — Same IP routed by BGP to nearest geographic data center. Bottom layer of CDN edge caching.

## 🚨 C++ Pitfalls Caught

- **`int * int` overflow before cast** — `long long S = n*(n+1)/2` overflows at n≥46341. Fix: `(long long)n * (n+1) / 2`.
- **`std::min` template type deduction** — `min(long_long, int)` fails to compile. Fix: cast at call site, or `min<long long>(a, b)`.
- **`vector<bool>` is bitpacked** — Special template specialization, not a regular vector. Size mismatch → heap-buffer-overflow. Often use `vector<char>` or `vector<int>` for general bool arrays.
- **`std::set` vs `vector<bool>` for integer-keyed membership** — Set is a red-black tree (O(log n), pointer-chasing). `vector<bool>` is O(1) with cache-friendly layout. Huge perf difference on LeetCode.

## 🅿️ Backlog Surfaced

- **HTTP 301 vs 302** — Permanent vs temporary redirect. Impact on browser caching, analytics, SEO.
- **`Lock` vs `RLock` deep dive** — When does reentrancy matter?
- **`Any`, `Optional`, `TypeVar`, `Hashable`, `typing` module overall** — Python type-hinting tour.
- **Python sentinels (`_MISSING = object()`)** — Why and when.
- **Python enums** — `enum.Enum`, `IntEnum`, `Flag`.
- **`eval`-able repr** — Convention and when it matters.
- **Project Loom (Java)** — Virtual threads, async without callbacks.
- **Distributed locks** — Redis SETNX, Redlock controversy, when worth the complexity.
- **PyPy / no-GIL CPython (3.13t)** — How concurrency model shifts when the GIL is gone.

## 🔁 Carry-over Revision Cards (2)

From the 5-card budget this session, only 3 landed cleanly. Carry these into next session:
- Hungarian Algorithm intuition (Session 5)
- Two-tier H3 use: coarse for Kafka partition routing, fine for actual driver lookup (Session 5)

## 🔗 References

- LeetCode #3752 — Lexicographically Smallest Negated Permutation that Sums to Target
- [Go `singleflight` package](https://pkg.go.dev/golang.org/x/sync/singleflight) — canonical implementation
- [Cloudflare CDN architecture](https://www.cloudflare.com/learning/cdn/what-is-a-cdn/) — for the edge caching deep dive
- Shannon's 1948 paper: *A Mathematical Theory of Communication* — original entropy / source coding theorem
