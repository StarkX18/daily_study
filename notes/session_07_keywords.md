# Session 7 — Parking Lot (Java) + Modulo Number Theory + Next Greater Node

**Date:** May 16, 2026
**Domains:** Revision · LLD (Java) · DSA · Java/Python fundamentals (organic)
**Theme:** Built a thread-safe Parking Lot in Java with heavy focus on idiomatic language features (smart enums, EnumSet, ReentrantLock, Optional, composition). The DSA slot detoured into a high-value tour of modulo number theory, negative-base conversion, and the monotonic-stack-with-indices pattern — driven by user questions rather than a single posed problem. Parts 3 (DSA Hard) and 4 (HLD) deferred to Session 8.

---

## 🧠 New Algorithms

- **Monotonic stack with indices (Next Greater Element)** — LC 1019. Stack holds `(index, value)` pairs, **not** bare values. On pop, the index tells you exactly which `ans[idx]` to fill. Forward pass directly over the linked list — no flattening to array needed. O(n) time/space, **provably optimal** (must read every node; strictly-decreasing input forces all elements onto the stack).
- **Negative-base conversion (base −2)** — LC 1017. Repeated Euclidean division by −2. Critical: loop is `while n != 0` (n alternates sign each step, NOT monotonic toward 0). `r = ((n % -2) + 2) % 2`, then `q = (n - r) // -2`.

## 🎯 New Patterns

- **Smart enums (Java)** — enum constants are singleton class instances created once at class-load. Attach per-instance state via constructor + `final` field; expose behavior via methods. Co-locate intrinsic data **with the type** (`VehicleType.fitsIn(slot)`) instead of in an external map. Adding a new constant forces you to supply the data (ctor demands it).
- **Composition over inheritance (GoF maxim)** — plug behaviors via constructor (`PricingStrategy`, `SlotAllocator`) instead of subclassing (`PremiumParkingLot extends ParkingLot`). Inheritance for *types*, composition for *behaviors*. Avoids combinatorial subclass explosion.
- **Floor-level locking (not slot+floor double-lock)** — "find a free slot + mark it filled" must be **one atomic step**. Wrap both under a single floor lock. Double-locking with unordered acquisition across threads = classic deadlock. Lot-wide = too coarse; per-slot only = doesn't solve the race (two threads see the same empty slot before either locks).
- **Pull vs push for cross-component state** — Gate *pulls* from Lot (the single source of truth). Observer pattern only earns its keep when subscribers must **react** to changes (live display boards), not merely **check** state. Don't add Observer to track state the Lot already owns.
- **Monotonic stack holds indices, not values (general principle)** — for any per-element-answer problem. You can always recover the value via `arr[idx]`, but never the index from a value. Index-keyed writes into a pre-allocated `ans[]` → no temp structures, no ordering gymnastics, no final padding.

## 🛠️ Systems / Tools / Libraries (named things)

- **EnumSet / EnumMap (Java)** — bitset-backed (one `long` per ≤64 enum values). O(1) `contains`, tiny memory (~8 bytes for 3 values vs ~100+ for HashSet), declaration-order iteration. **Always** beats HashSet/HashMap for enum keys.
- **ReentrantLock (Java)** — `java.util.concurrent.locks`. Over `synchronized`: `tryLock()`, `tryLock(timeout)`, `lockInterruptibly()`, fair/unfair ordering, multiple `Condition` objects, acquire-in-one-method-release-in-another. **Must** pair `lock()`/`unlock()` in `try/finally` (else lock leaks on exception). "Reentrant" = same thread can re-acquire its own lock (hold count) without self-deadlock. (`synchronized` is also reentrant.)
- **`tryLock()`** — acquire-or-bail-immediately. Deadlock avoidance + "skip if busy, try next" patterns.
- **Optional<T> (Java)** — wraps "might be absent" at the type level. Use for **return types only** (not fields/params; not `Optional<List>` — return empty list). `of()` / `ofNullable()` / `empty()` = strict (throws on null) / lenient (wraps null as empty) / explicit-nothing.
- **`Math.floorDiv` / `Math.floorMod` (Java 8+)** — Euclidean q and r out of the box for positive n. No manual formula needed.
- **`collections.deque` (Python)** — O(1) both ends (`append`/`pop`/`appendleft`/`popleft`). Use for queue (`append`+`popleft`), stack, sliding window, BFS. NOT random-access — middle indexing is O(n). `maxlen` for bounded ring buffers.
- **`queue.Queue` (Python)** — thread-safe, lock-based. For producer-consumer **across threads ONLY**. Slow for single-threaded algorithms — never use in interviews.
- **`list` as stack (Python)** — `append()` = push, `pop()` = pop, `[-1]` = peek, `not stack` = empty check. NEVER `pop(0)` (O(n), shifts everything). Idiomatic + cache-friendly; no dedicated stack class exists.

## 📚 Terms / Concepts

- **Modulo conventions (3 of them)** — **Euclidean** (r always ≥ 0, r ∈ [0, |n|)) = pure math; **Floored** (sign follows divisor) = Python/Ruby; **Truncated** (sign follows dividend) = Java/C/C++/JS/Go. Floored = Euclidean *only for positive divisors*.
- **Euclidean modulo fix (all languages)** — `((a % n) + n) % n` → non-negative result in [0, n) for n > 0. For possibly-negative n: `((a % n) + |n|) % |n|`.
- **Euclidean quotient** — `q = (a - r) / n` where r is the Euclidean remainder. The division is exact (no truncation issue) because `(a − r)` is an exact multiple of n. **ALWAYS parenthesize `(a - r)`** — `/`, `//`, `%` bind tighter than `-` in every C-precedence language (the operator-precedence trap that caused the baseNeg2 infinite loop).
- **Clock-face intuition** — `a mod n` = where you land on an n-position clock starting at 0. Python respects ℤ/nℤ equivalence classes (`(a + n) mod n == a mod n` always holds); Java doesn't for negatives — hence the manual `((a%n)+n)%n` fix.
- **`final` field (Java)** — assign-once; freezes the **reference**, not the object behind it (`final List` can still `.add()`). JMM guarantees **safe publication**: any thread that sees the constructed object sees the correct final-field value with no synchronization. This is why immutable classes (String, Integer, LocalDate) are trivially thread-safe.
- **`Optional[T]` (Python)** — a **type hint only**, no runtime wrapper. No `.get()`, no `.isPresent()`. The value is `T` or `None` directly. Unwrap with `if x is not None`. Static checkers (mypy/pyright) use the hint to enforce the None-check at lint time.
- **Strategy pattern misuse signal** — before naming `XStrategy`, ask: "could I imagine 3+ impls the caller wouldn't care to distinguish?" If no, it's just a method. `park()`/`exit()` are *operations*, not strategies. `PricingStrategy` IS legit (flat / tiered / surge).
- **null = "billion-dollar mistake" (Tony Hoare)** — `Optional` return types make absence explicit in the signature and force the caller to handle it; a `null` return hides the contract in javadoc/tribal knowledge.
- **Queue vs deque (terminology)** — queue = abstract FIFO ADT; deque = concrete double-ended structure (can act as queue OR stack); `queue.Queue` = Python's thread-safe concurrency primitive. "Use a queue for BFS" → implement with `collections.deque`.

## ⚠️ Revision Scorecard (5 cards)

| Card | Source | Result | Gap |
|---|---|---|---|
| 0-1 BFS | S3 | ✅ Nailed | — |
| Constrained Dijkstra | S2 | ⚠️ Partial | Got state augmentation; skipped "answer = POP of dst from PQ, never the push" |
| Thundering Herd toolkit | S2 | ❌ Missed | Only TTL jitter; conflated CDC/CQRS (neither is a herd mitigation) |
| OCC conditional UPDATE | S5 | ❌ Missed | Predicate incompleteness — needs `offered_to_driver_id`, not just `state='OFFERED'` |
| Event Bus vs Webhook | S5 | ⚠️ Partial (~70%) | Got the why; missed the trust/network-boundary framing for when webhook is correct |

**→ Thundering Herd + OCC flagged for DIFFERENT-ANGLE replay in Session 8** (per revision rule: pose a new case study / new MH-H problem testing the concept, never re-ask "what is X").

## 🅿️ Backlog Surfaced / Deferred

- **DEFERRED (DSA):** LC 2812 "Find the Safest Path in a Grid" — posed but not attempted. **Pull at start of Session 8.** (Approach: multi-source BFS to precompute distance-to-nearest-thief map, then Dijkstra / binary-search for the max-min safeness path.)
- **DEFERRED (HLD):** Idempotent APIs / Idempotency Keys (Stripe-style) — never posed. Session 8, or fold into the Kafka deep dive (idempotent producer overlaps directly).
- **LLD upgrade path (Parking Lot):** O(1) slot lookup via free-slot queue per `(floor, slotType)` instead of linear scan. Add Observer pattern only if live display boards get introduced.
- **Carried from prior sessions:** LC 3528 (DSU + bidirectional edges), Kafka standalone deep dive, Ringpop / DocStore / AresDB / RAMEN.

## 🔗 References

- LC 1019 — Next Greater Node In Linked List (monotonic stack with indices)
- LC 1017 — Convert to Base −2 (negative-base / Euclidean division)
- LC 2812 — Find the Safest Path in a Grid (deferred to S8)
- Sibling monotonic-stack problems (same pattern): LC 739 Daily Temperatures · LC 503 Next Greater Element II · LC 84 Largest Rectangle in Histogram · LC 42 Trapping Rain Water

---

## 🗒️ Session note

Parts 3 & 4 went off-script. The DSA slot became an organic, high-value fundamentals tour (modulo theory → Euclidean division → negative-base conversion → monotonic stack → Python stack/deque/Optional) driven by user questions rather than a single posed Hard problem. Net positive — patched real Java/Python gaps — but LC 2812 (DSA Hard) and the HLD concept both roll into Session 8.

**LLD language alternation:** S7 = Java (Parking Lot) → **S8 = Python**.
