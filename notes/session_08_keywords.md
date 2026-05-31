# FAANG+ Prep — Consolidated Notes: Session 8 + Session 10

**Compiled:** May 26, 2026
**Covers:** Session 8 (May 18 — LC 2812 + Splitwise LLD in Java) and Session 10 / this thread (rapid debugging + dihedral-group DSA brainstorm + Java/Python LLD decision + Amazon LLD research + Java randomness).

---
---

# SESSION 8 — May 18, 2026 — Java (Splitwise) + LC 2812

**Theme:** Max-min path family (binary-search-on-answer + multi-source BFS), then a deep Splitwise LLD in Java — money modeling, Strategy vs Factory, modern Java idioms (records/sealed), and layered architecture for in-memory systems.

## DSA — LC 2812 "Find the Safest Path in a Grid" (Medium-Hard)

**Problem:** `n×n` grid, cells are thieves (`1`) or empty (`0`). Safeness of a path `(0,0)→(n-1,n-1)` = the **minimum Manhattan distance** from any path cell to any thief. Maximize safeness over all paths.

### 🧠 Algorithm / Approach
- **Multi-source BFS** from ALL thief cells at once → `dist[i][j]` = Manhattan distance to nearest thief. Works because on an unobstructed 4-connected grid, **BFS step count == Manhattan (L1) distance**.
- **Binary search on the answer** (the safeness threshold `T`). The predicate *"does a path exist where every cell has `dist ≥ T`?"* is **monotonic** (true for small `T`, false for large) → binary-searchable.
- Predicate check = BFS/DFS over the subgraph of cells with `dist ≥ T`, testing `(0,0)→(n-1,n-1)` reachability.

### 🎯 Patterns
- **Max-min / bottleneck / widest-path family** — "maximize the minimum value along a path." Recognize → binary search on answer + monotonic reachability predicate.
- **Tighter upper bound** for the binary search: cap by the **mandatory endpoint values** (`dist` at start and end) — you can't beat the safeness of cells you're forced to visit.

### ⏱️ Complexity
- Multi-source BFS: `O(n²)` one-shot.
- Each predicate check: BFS over grid = `O(V+E) = O(n²)`.
- **Total: `O(n² log n)`, space `O(n²)`.** The `log` comes from the binary search, NOT from inside the BFS (BFS is plain linear-in-grid).

### 📚 Sister problems
- LC 1102 — Path With Maximum Minimum Value
- LC 778 — Swim in Rising Water

> 🅿️ **Status:** approach locked, code (Python, iterative `collections.deque`) parked.

---

## LLD — Splitwise (Java)

**Scope:** Users in ≥0 groups; expenses with payer + participants + split type (Equal / Exact / Percentage); per-user balances; `addExpense`, `showBalance`; extra-credit `simplifyDebts`.

### 🎯 Requirements clarification (interview craft)
- **Strong questions to ask:** split strategy per-expense (locks the polymorphism axis early); cross-group balance when two users share multiple groups (settle per-group vs as individuals — a senior-level catch); simplify-debts semantics (does it mutate original balances? revertible? auto-trigger on expense update?).
- **Sharpen:** don't *assume* "everything is a group." Real Splitwise has direct / 1-on-1 expenses. Ask *"do we support direct expenses, or collapse 1-on-1 into a 2-person group?"* — make it the interviewer's call, not your silent assumption.

### 🛠️ Java idioms for money + design
- **`BigDecimal` for all amounts — NEVER `double`.** Floating-point rounding will betray you on percentage splits.
- `enum SplitType` with per-instance strategy (the smart-enum pattern from S7).
- Interface/abstract `SplitStrategy` for Equal / Exact / Percentage (Strategy pattern).
- `ConcurrentHashMap` for user/group/balance registries; per-user `synchronized` block or `ReentrantLock` for balance mutations.
- `equals` / `hashCode` on `User` keyed on **UUID, not name**.

### 📚 Design-pattern concepts
- **Strategy vs Factory:** Strategy = *behavior selection* (polymorphic dispatch — NOT overloading); Factory = *object creation*. Enum-with-methods can express either, but trades flexibility/testability for readability.
- **Records** = immutable data, zero boilerplate.
- **Sealed interfaces** = closed-set polymorphism, compiler-enforced exhaustiveness.
- **Records implementing a sealed interface** = algebraic data types — the modern FAANG-senior Java idiom (e.g. `sealed interface Transaction permits Expense, Settlement`).
- **Abstract classes** sit between interfaces (contract only) and concrete classes (everything) — use when you need shared state + subclass flexibility.

### 🏛️ Architecture — in-memory (no REST)
In-memory means MVC doesn't map directly → use **layered architecture** (same separation-of-concerns spirit, different layers):

```
com/splitwise/
├── Main.java                  ← entry point / CLI demo
├── service/                   ← public API + per-concern services (Expense, Settlement, Balance)
├── model/                     ← records, entities, sealed Transaction
├── strategy/                  ← SplitStrategy (enum-with-method)
├── repository/                ← interface + InMemory* (Map-backed) impl
├── exception/                 ← InvalidSplit / UserNotFound / GroupNotFound
└── util/                      ← IdGenerator (interface = testability boundary) + UuidGenerator
```
With Maven/Gradle: prefix `src/main/java/`; tests mirror under `src/test/java/`.

### 🧰 Java packaging tricks (single-file practice)
- Multiple top-level classes in ONE `.java` file (only one `public`, rest package-private) — practice design without 10 files.
- `java Splitwise.java` runs directly (single-file source-launch, Java 11+) — no `javac` step.
- For the Razorpay R1 take-home you need a real multi-file project anyway → reserve single-file for *design practice*, use IntelliJ for the actual build.

### 🔗 LLD practice tools
- Sandboxes: OneCompiler / JDoodle / Replit (single-file, zero setup).
- Purpose-built: `lowleveldesignmastery.com`, `algomaster.io/learn/lld` (problem libraries, diagrams, language filters).
- Reference repo: GitHub `ashishps1/awesome-low-level-design` (clean solutions to read).

> 🅿️ **Deferred again from S8:** HLD Idempotency Keys (Stripe-style) · Revision replays (Thundering Herd toolkit, OCC predicate-incompleteness).

---
---

# SESSION 10 — ~May 26, 2026 — This Thread

**Theme:** Rapid-fire debugging + a permutation-sorting DSA brainstorm (dihedral group), the Java-vs-Python LLD-language decision, Tic-Tac-Toe + Fixed-Window-Counter debugging, Amazon SDE2 LLD interview research, and a tour of Java randomness.

## DSA #1 — `limitOccurrences` (Python loop-counter bug)
- **You cannot advance a Python `for i in range(n)` loop from inside the body.** `i = j` is silently discarded — the iterator rebinds `i` on the next pass. Result: the index never jumps, runs get re-processed (e.g. `[1,1,1]`,k=2 → `[1,1,1,1,1]`).
- **Fix:** use a `while` loop with manual index control whenever the body needs to skip/jump the index (run-skipping, two-pointer skips).

## DSA #2 — LC 3942 "Minimum Operations to Sort a Permutation" (MH)  ·  🅿️ BACKLOG: retry fresh
Ops: **Reverse-all (R)** + **Rotate-left-by-1 (L)**. Min ops to sort a permutation of `[0..n-1]`, or `-1`.

### 🧠 Key insight
- `L` (order n) + `R` (involution), with `R·L·R = L⁻¹` → these generate the **dihedral group `D_n`**. So the reachable orbit from `nums` is ≤ **2n** arrays: all rotations of `nums` + all rotations of `reverse(nums)`.
- **Sortable iff** the sorted array is a rotation of `nums` OR a rotation of `reverse(nums)`; else **`-1`**.

### 🎯 Cost model
- rotate-left-by-`k` = `k` ops; reverse = `1` op.
- **rotate-right-by-`k` = `R·L^k·R` = `k+2` ops** — the non-obvious trick (beats `n-k` lefts for small `k`).
- **Direction-flip model:** a word `L^{a0} R L^{a1} R ...` has net rotate-left = `a0 - a1 + a2 - ...`, reflection = parity of R count.
- **Type 1** (sorted = rotation of `nums`, even reverses): cost `= min(p, n - p + 2)`, `p` = index of 0.
- **Type 2** (sorted = rotation of `reverse(nums)`, one reverse): cost `= min(q, n - q) + 1`, `q` = index of 0 in `reverse(nums)`.
- **`+2` vs `+1` asymmetry** (memorize): Type 1's alternate route needs a *double*-reverse (`+2`); Type 2 already spends one reverse, so its rotation only costs `+1`.

### ⚡ Optimal single-pass (C++)
One loop gathers: index-of-0, `asc` flag (`a[(i+1)%n] == (a[i]+1)%n` → rotation of ascending), `desc` flag (predecessor check → rotation of descending). Then O(1) arithmetic: Type1 if `asc`, Type2 if `desc`, `q = n-1-zero`. **O(n) time, O(1) space**, no `reverse()` allocation, no redundant scans.

### 🐛 Attempt bugs
Handling only Type 1; no validation that `nums` is actually a rotation; no `-1`; `idx+2` where it should be `idx` (plain left-rotation costs `idx`); `nums[i+1]` IndexError at `i=n-1`; fragile local-min scan instead of `index(0)`.

### 🐍→C++ abstraction map (what Python was hiding)
| Python | C++ explicit |
|---|---|
| `.index(0)` | manual scan loop |
| `[::-1]` | reverse-iterator ctor copy |
| `all(gen)` | explicit loop + early `return false` |
| `float('inf')` | `INT_MAX` sentinel + ternary |
| `min(a, b, c)` (variadic) | `std::min({a, b, c})` (watch S6 template-deduction trap if mixing `int`/`long long`) |

---

## LLD — Java vs Python (decision LOCKED: **Java by default**)
- "Python is easier" holds almost everywhere EXCEPT an LLD round. LLD grades **visible design**, not typing speed — the boilerplate Java forces (interfaces, abstract classes, explicit composition) **is** the signal interviewers grade.
- Your pattern knowledge is **Java-shaped**; Pythonic patterns *dissolve* (Strategy→callable, Singleton→module, Factory→dict) → less visible structure, harder to demo, and you'd be re-buying patterns you already own.
- **Target set has zero Python shops:** Amazon expects explicit OOD (Java's turf); Razorpay = JVM/Go; Capital One = huge Java shop; Intercom Dublin = Rails/Ruby (language-agnostic). No company gives Python a fit advantage.
- **Override Java only for:** explicit Python-stack rounds, or ship-fast AI-permitted take-homes. For Razorpay: choose R1's language for the **no-AI R2 live extension**, not for AI-scaffolding speed.
- Fear of fumbling Java live → fix is **drilling 3–4 Java LLD problems for speed**, not switching languages.

---

## LLD debugging — Tic-Tac-Toe `Game` class  (an Amazon Hyderabad LLD prompt)

### `main()`
- `(char) sc.nextByte()` is wrong for reading a symbol — `nextByte()` parses a *numeric* byte and throws `InputMismatchException` on `'X'`. Use **`sc.next().charAt(0)`**.
- Missing `java.util.*` imports (`Scanner`, `List`, `ArrayList`).
- `void main()` is valid only on Java 21+ (preview) / 25+ (final, instance main in compact source files); else need `public static void main(String[] args)`.

### `checkWinner()`
- **Anti-diagonal condition** `row + col == boardDimensions` is wrong → must be **`== boardDimensions - 1`**. As-is it counts the wrong cells and never detects the true anti-diagonal.
- **NPE** on `diagonalMap` / `antiDiagonalMap` via `.get(player) + 1` (null unboxing) → use **`getOrDefault(player, 0)`** (row/col already do).
- ✅ Correct: `.equals(boardDimensions)` not `==` for `Integer` (`==` breaks above the 127 cache).

### `start()`
- Off-by-one: `currentTurn++` runs BEFORE `currentPlayer = currentTurn % size` → **player index 1 moves first, player 0 never opens.** Compute the index before incrementing, or start `currentTurn` at `-1`.

---

## LLD — Fixed Window Counter (rate limiter, Java)
- **Window id** `= System.currentTimeMillis() / (1000L * windowInSeconds)`. **Parenthesize the denominator** — `/1000L * windowInSeconds` parses as `(t/1000) * windowInSeconds` (precedence trap, same family as the S7 Euclidean-quotient parens trap). `1000L` keeps it `long` (overflow guard).
- Floor division gives the **current** window (prev = `current - 1`).
- State per user = `{windowId, count}` — fixed window only needs the CURRENT window. A `Map<windowId, count>` grows unbounded (memory leak) unless you `clear()` on rollover; the single `Window` object is structurally leak-free → preferred.
- **Thread-safe pattern:** `ConcurrentHashMap` outer + `computeIfAbsent` (atomic get-or-create — hands racing threads the *same* ref) + `synchronized(window)` inner (serializes + establishes visibility). This is the S1/S2 locked pattern.

**🐛 Attempt bugs**
- Precedence on window-id (above).
- `count <= maxRequests` lets through `maxRequests + 1` → use **`count < maxRequests`**.
- Naming: `userMap` → `window` (it's not a map); `windowStart` → `windowId` (holds the bucket index, not a start time).

**Boundary-spike weakness:** bursts straddling the window seam can pass up to **2× maxRequests** → the motivation for sliding-window counter. *Name your own algorithm's flaw before the interviewer does.*

---

## Java — Randomness

### 🛠️ Which generator (the decision that matters)
- **`Random`** — LCG, 48-bit seed, seedable/reproducible. Thread-safe but **contended** (shared seed via CAS).
- **`ThreadLocalRandom.current().nextInt(...)`** — per-thread generator, zero contention. **Default for concurrent code.** Never cache/share `current()` — call it inline on the using thread; `setSeed` throws.
- **`SecureRandom`** — crypto-strong, OS-entropy seeded. Use for tokens, session IDs, salts. `Random` is *predictable* — never for unguessable IDs.
- **`SplittableRandom`** — parallel/fork-join, splittable, not thread-safe alone.
- Since Java 17 all of these implement the `RandomGenerator` interface.

### 🎲 Dice 1–6
`ThreadLocalRandom.current().nextInt(1, 7)` — `nextInt(origin, bound)` is origin-**inclusive**, bound-**exclusive** (so `7`, not `6` — the trap). Does rejection sampling → no modulo bias.
- `nextInt()` → any int (can be negative) · `nextInt(6)` → `[0,6)` · `nextInt(1,7)` → `[1,7)`.

### 🧱 LLD `Dice` abstraction
Wrap the roll in `Dice(faces)`: configurable faces (no magic `6`) + a **testable seam** (inject a deterministic roller; otherwise a randomized game is untestable). Multi-dice = sum N rolls.

### ⚠️ Why NOT `(int)(Math.random() * (max - min + 1) + min)`
- Works for *positive* ranges (your die is fine), BUT `(int)` truncates **toward zero**, not floor → for `min ≤ 0` the distribution skews (e.g. `Dice(-3,3)`: `-3` almost never, `0` ~2× as often). The general two-arg class silently lies about being general.
- `Math.random()` is the shared, contended singleton.
- Review clarity: float→int forces the reader to verify floor/boundary every time; `nextInt(1,7)` is obviously correct.
- Negative-safe float form if you insist: `(int) Math.floor(Math.random() * (max - min + 1)) + min` — but that's more code than `nextInt(min, max+1)` does in one call.

### 📚 Gotchas
- Modulo bias: `nextInt() % n` is biased AND can be negative → use `nextInt(n)`.
- `nextInt(bound)` requires `bound > 0`.
- Range `[min, max]` inclusive = `min + nextInt(max - min + 1)` (watch overflow on the subtraction).
- Same seed → same sequence (great for tests, bad for security).
- `Math.random()` = shared `Random.nextDouble()` → `[0.0, 1.0)`.

---

## Interview research — Amazon SDE2 Hyderabad (AGI org)
- AGI SDE2 runs the **standard** Amazon SDE2 India loop — the org barely changes the bar. (AGI-specific signal exists only for *Applied Scientist II*: breadth/depth/application + Bar Raiser — a different pipeline.)
- **LLD-round bank (recurring 2026 India/Hyderabad):**
  - **Tic-Tac-Toe** — entities → win/end conditions → class diagram (← you're on this).
  - **LRU Cache** — working code expected, DLL assumed given (you've built this, S6).
  - **Restaurant token / order-management** — class + DB design, full API list, pseudocode, **Redis atomic ops for contention**.
  - **Coffee / vending machine** — incomplete requirements on purpose → drive the clarifying questions.
  - **API rate limiter** (done, S1–2), **Elevator** (state machine + scheduling), **BookMyShow / ticketing** (seat selection + concurrency + data modeling).
- **The bar:** code it live in the editor — modular, SOLID, scalable, exception handling, clean naming — and an LP/behavioral question mid-round.
- **DSA round (done):** graphs (Word Ladder, currency conversion, Dijkstra), monotonic stack (Asteroid Collision, Max Points from Cards), sliding window, intervals/sweep, connect-sticks greedy, binary-search-on-answer.
- **Gaps to close (priority):** (1) **BookMyShow / ticketing** — concurrency-heavy, your strength, double-counts for Razorpay; (2) **Elevator**; (3) **Coffee machine** (a requirements-elicitation rep). Resource: Shrayansh Jain LLD playlist.
- LP bar is brutal; the **Bar Raiser can veto** a clean coding loop; they push for hard metrics on every "Result."

---
---

## 🅿️ Open backlog after Session 10

**DSA**
- LC 3942 — Minimum Operations to Sort a Permutation (retry FRESH; dihedral-group insight).
- LC 2812 — Find the Safest Path in a Grid (code parked; approach locked).
- LC 3528 — Maximum Reachable Value (resume from DSU + bidirectional edges).

**LLD (to drill, priority order)**
- BookMyShow / ticketing (concurrency — double-counts for Razorpay R1).
- Elevator.
- Coffee/vending machine (requirements elicitation).

**HLD (still deferred)**
- Idempotency Keys / Stripe-style idempotent APIs.
- Kafka deep dive (exactly-once, partitioning, consumer groups, ISR, KRaft, compaction, Streams).
- Ringpop · DocStore · AresDB · RAMEN.

**Revision (different-angle, owed since S7)**
- Thundering Herd toolkit.
- OCC via conditional UPDATE (the `offered_to_driver_id` predicate-incompleteness gotcha).
