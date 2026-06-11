# Session 12 — Online Stock Exchange: Full LLD + HLD + HFT Overview

**Date:** June 1, 2026
**Domains:** LLD (Hard, Java) · HLD (Hard) · HFT (overview, SE perspective)
**Theme:** First Hard-tier session across both LLD and HLD. Full end-to-end design of an Online Stock Exchange — matching engine, order book, concurrency model, the full HLD pipeline, and an SE-perspective overview of how HFT firms build on top.

---

## 🔄 Rule Changes This Session

- **LLD difficulty upgraded to Hard** — fluency rebuild complete for Java/Python. JS/Node.js remains E/M fluency-rebuild only (pending).
- **HLD difficulty upgraded to Hard** — same rationale.

---

## Part 1 — LLD: Online Stock Exchange (Java)

### The Core Concept

A stock exchange does one job: match buyers and sellers. The **order book** holds all waiting orders for one symbol. When a new order arrives whose price "crosses" an existing one (buyer's max ≥ seller's min), a **trade** happens. The matching rule is **price-time priority**: best price wins; ties broken by earliest arrival.

The key framing: the matching core is *inherently sequential* — order A must fully process before order B or priority becomes nondeterministic. Every architecture decision flows from this constraint.

---

### Scope Decisions

- **One OrderBook per symbol** — AAPL and TSLA never interact. One book correct → `Map<symbol, OrderBook>` scales it N times. Sharding axis: across symbols, never within one.
- **Order types:** LIMIT + MARKET + CANCEL + MODIFY.
- **Matching:** price-time priority, match-on-submit, synchronous.
- **Prices as integers (ticks/cents as `long`)** — `double` has no exact binary representation; `0.1 + 0.2 != 0.3`. In a money path that's a correctness bug, not a style choice. `BigDecimal` is exact but allocates objects per op — too slow. Integer ticks: exact AND fast.
- **Out of scope (named explicitly):** settlement/clearing, risk/margin, market-data dissemination infra, auth, persistence.

---

### Why Not a Heap?

The natural first instinct — max-heap of bids + min-heap of asks — breaks on the operation that dominates in real markets:

**Cancel is the hot path.** In modern US equities, ~97% of orders are cancelled before they fill. A heap can only cheaply remove its *top*; removing an arbitrary middle element is O(n). Lazy deletion sounds like a fix but:
1. **Garbage accumulation** — dead orders near-the-touch get cleaned; deep orders never do. Memory grows unbounded.
2. **Bursty tail latency** — when matching finally hits a garbage-filled region, it pops hundreds of dead orders in sequence. P99 spikes.
3. **No sorted iteration** — you can't walk the book to publish Level 2 depth without destroying the heap.

The third point alone disqualifies it: the exchange *must* publish depth feeds.

**Solution:** `TreeMap<price, PriceLevel>` + FIFO doubly-linked list per level + `HashMap<id, Order>` index.

---

### Data Structures

**`PriceLevel`** — one price level on the book:
```java
final class PriceLevel {
    final long price;
    Order head, tail;      // FIFO: head = oldest = first to fill
    long totalVolume;      // cached Σ remainingQty, for depth feeds

    void append(Order o)   // O(1) — new order joins the back (time priority)
    void unlink(Order o)   // O(1) — intrusive doubly-linked list
    boolean isEmpty()
}
```

**`OrderBook`** — storage only, no matching logic:
```java
final class OrderBook {
    // bids: reverseOrder() so firstEntry() = highest bid
    // asks: natural order so firstEntry() = lowest ask
    NavigableMap<Long, PriceLevel> bids = new TreeMap<>(Comparator.reverseOrder());
    NavigableMap<Long, PriceLevel> asks = new TreeMap<>();
    Map<Long, Order> index = new HashMap<>();   // id→Order for O(1) cancel

    PriceLevel bestBid()           // O(log P)
    PriceLevel bestAsk()           // O(log P)
    void addResting(Order o)       // O(log P): find/create level, O(1) append
    boolean cancel(long orderId)   // O(1) amortized: hash lookup + unlink
    void remove(Order o)           // shared unlink used by cancel + fill
}
```

**Complexity scorecard (P = distinct price levels, not order count):**

| Operation | Cost | Why |
|---|---|---|
| Best bid/ask | O(log P) | TreeMap.firstEntry() |
| Add resting order | O(log P) | find/create level, then O(1) append |
| Cancel by id | O(1) amortized | hash lookup + intrusive unlink |
| Match one fill | O(1) | always touches head of best level |

P is small and bounded in practice — price levels, not order count. This is nearly O(1) on the hot path.

---

### The `Order` Entity

`final` fields = set once at construction (safely published, cancel+replace to change); mutable fields = change during the order's life:

```java
final class Order {
    // Immutable — changing any of these resets queue priority (cancel + replace)
    final long      id;
    final String    symbol;
    final Side      side;          // BUY or SELL
    final OrderType type;          // LIMIT or MARKET
    final long      price;         // integer ticks; ignored for MARKET
    final long      originalQty;
    final long      seq;           // monotonic arrival number = time priority

    // Mutable — changes during the order's life
    long        remainingQty;
    OrderStatus status;            // NEW → PARTIALLY_FILLED → FILLED / CANCELLED

    // Intrusive linked list pointers (the O(1) cancel price)
    Order prev, next;
}
```

**The modify rules (derived from fairness):**
- Price change → back of queue (either direction). Cancel + replace.
- Quantity decrease → keep your spot (claiming less, nobody's hurt). In-place.
- Quantity increase → back of queue (claiming more, re-earn priority). Cancel + replace.

Some venues let only the *added* portion lose priority; the simple interview answer is "any increase = lose priority."

**Why `price` is `final`:** changing it must reset priority anyway, so it's semantically a cancel+replace, never a mutation. The keyword enforces the rule.

**`volatile` vs `final` (Java memory model):**
- `final` — JMM inserts a "freeze" barrier at constructor end. Once any thread sees the reference, all `final` fields are guaranteed fully constructed. One-shot safe publication.
- `volatile` — ongoing visibility. A volatile *write* is a store-release (publishes everything written before it); a volatile *read* is a load-acquire (sees all of it). Also: volatile reads/writes are not compound-atomic — `volatile int count; count++` is still a race.

LMAX Disruptor is essentially `volatile` sequence counters + single-writer-per-slot discipline, no lock needed because you don't need exclusion, just visibility.

---

### Intrusive Linked List

"Intrusive" = the list pointers (`prev`/`next`) live *inside* the object, not in separate wrapper nodes. Tradeoff:

- **+** No wrapper allocation per resting order (zero GC churn).
- **+** O(1) unlink when you already hold the object — the `HashMap` index hands you the exact `Order`, and since it carries its own pointers, unlinking is `o.prev.next = o.next; o.next.prev = o.prev`. No search.
- **−** The `Order` class "knows" it lives in a list — couples domain object to storage concern.
- **−** Can only be in one such list at a time (one set of pointers).

The coupling is worth it because O(1) cancel on a 97%-cancel-rate hot path is the most important property.

---

### Matching Engine

```java
final class MatchingEngine {
    List<Trade> submit(OrderBook book, Order taker) {
        List<Trade> trades = new ArrayList<>();
        boolean buy = taker.side == Side.BUY;

        while (taker.remainingQty > 0) {
            PriceLevel best = buy ? book.bestAsk() : book.bestBid();
            if (best == null) break;
            if (!crosses(taker, best.price, buy)) break;   // spread opened

            Order maker = best.head;                       // oldest = time priority
            long fill = Math.min(taker.remainingQty, maker.remainingQty);
            long px   = maker.price;                       // MAKER sets the price

            trades.add(new Trade(++tradeSeq, taker.id, maker.id, px, fill, tradeSeq));
            taker.remainingQty -= fill;
            maker.remainingQty -= fill;
            best.totalVolume   -= fill;

            if (maker.remainingQty == 0) {
                maker.status = OrderStatus.FILLED;
                book.remove(maker);                        // level may empty → removed from TreeMap
            } else {
                maker.status = OrderStatus.PARTIALLY_FILLED;
            }
        }

        // Settle the taker's remainder
        if (taker.remainingQty == 0) {
            taker.status = OrderStatus.FILLED;
        } else if (taker.type == OrderType.LIMIT) {
            taker.status = (taker.remainingQty == taker.originalQty)
                         ? OrderStatus.NEW : OrderStatus.PARTIALLY_FILLED;
            book.addResting(taker);                        // taker becomes a maker
        } else {                                           // MARKET: nowhere to rest
            taker.status = trades.isEmpty() ? OrderStatus.REJECTED : OrderStatus.PARTIALLY_FILLED;
        }
        return trades;
    }

    private boolean crosses(Order taker, long bookPrice, boolean buy) {
        if (taker.type == OrderType.MARKET) return true;
        return buy ? bookPrice <= taker.price : bookPrice >= taker.price;
    }
}
```

**Five interlocking parts of the algorithm:**
1. Walk the *opposite* side (BUY hits asks; SELL hits bids).
2. Keep going `while prices cross AND taker has appetite` — the moment the spread opens, stop.
3. `maker = best.head` — oldest at best price = price-time priority in one line.
4. **Execution price is the maker's** — resting order posted its price first. Any improvement (buyer willing to pay $152, ask is $151 → trades at $151) accrues to the taker as *price improvement*. Nobody "pockets" the difference — it's savings to the aggressor.
5. `fillQty = min(taker.remaining, maker.remaining)` — whoever runs out first determines the outcome (maker exhausted/stays; taker exhausted/stays; etc.).

**The loop re-fetches `best` each pass** — when a level empties, `book.remove` deletes it from the TreeMap, so the next `bestAsk()` returns the next-best level. The taker naturally walks the book sweeping multiple price levels.

---

### Concurrency Model — The LMAX Move

The order book uses plain `HashMap`/`TreeMap` with no locks — which is safe only if one thread ever touches it. This is intentional.

**Why not lock the book?** A lock serializes threads into a single-file line — but matching is inherently sequential anyway, so you were always going to serialize. A lock just adds: thread park/wake overhead, OS scheduler involvement, and the book's data cache-bouncing between cores as lock ownership changes hands. You serialize either way; the queue serializes cheaply.

**The design:** producers (1000s of request threads) publish commands to a `BlockingQueue`; one consumer thread drains it and applies commands to the book. The book only ever sees a serial stream — no contention, no locks, no dirty reads.

```java
final class Exchange {
    private final Map<String, OrderBook>    books  = new HashMap<>();  // single-thread owned
    private final BlockingQueue<Command>    queue  = new LinkedBlockingQueue<>();
    private final MatchingEngine            engine = new MatchingEngine();
    private volatile boolean                running = true;

    CompletableFuture<List<Trade>> submitOrder(Order order) {
        Command cmd = Command.submit(order);
        queue.offer(cmd);       // O(1), thread-safe, returns instantly
        return cmd.result;      // caller awaits or chains
    }

    private void matchLoop() {
        while (running) {
            try {
                Command cmd = queue.take();           // parks when empty — no busy CPU
                OrderBook book = books.computeIfAbsent(cmd.symbol, OrderBook::new);
                List<Trade> trades = switch (cmd.type) {
                    case SUBMIT -> engine.submit(book, cmd.order);
                    case CANCEL -> { book.cancel(cmd.cancelId); yield List.of(); }
                };
                cmd.result.complete(trades);
            } catch (Exception e) {
                cmd.result.completeExceptionally(e);  // one bad order must NOT kill the loop
            }
        }
    }
}
```

**`BlockingQueue` over `ConcurrentLinkedQueue`:** `take()` parks when idle (zero CPU). `ConcurrentLinkedQueue.poll()` returns null and requires busy-spinning — burns a whole core doing nothing, no backpressure, unbounded growth under overload. The Disruptor is the upgrade path when microseconds justify the CPU cost of spinning.

**`CompletableFuture` as the bridge:** the command carries an IOU (`CompletableFuture<List<Trade>>`); the producer returns it immediately; the matcher completes it after matching. `complete(value)` pays it successfully; `completeExceptionally(e)` pays it as a failure.

**Parallelism axis:** across symbols, never within one. AAPL engine on thread 1, TSLA on thread 2 — zero shared state, true parallelism.

**The exception guard is non-optional** — one matching thread is a single point of failure. A thrown exception must fail only that command, not kill the loop.

---

### Market Data Dissemination (LLD angle)

Why not textbook Observer (hold a `List<Observer>`, iterate, call `update()`)?

Three landmines:
1. **Slow-consumer stall** — synchronous `update()` means the slowest subscriber stalls the matching thread. The sacred single thread can't be held hostage.
2. **Concurrent modification** — subscribe/unsubscribe while iterating → `ConcurrentModificationException`. Fix with `CopyOnWriteArrayList` if in-process, but the real design keeps subscriber management in the gateway tier entirely.
3. **Network-scale fan-out** — millions of subscribers can't be in a `List` you iterate. One UDP multicast packet; the network fabric replicates it.

**The real design:** engine publishes to an output queue and moves on. A separate dissemination tier fans out: UDP multicast for pro feeds (L1/L2/L3), WebSocket gateway fleet for retail. Consumers rebuild from snapshot + sequenced deltas; gaps detected by sequence number → re-request snapshot. **Conflation** for slow consumers (drop intermediate stale ticks; only the latest price is useful).

---

### Key Nuances (interview-level details)

- **Cancel-replace vs in-place modify:** price change or quantity increase = cancel + fresh insert at back of new level (fairness rule — no gaming queue priority). Quantity decrease = in-place (claiming less, nobody hurt). Some venues let only the *added* size lose priority.
- **TOCTOU race on cancel-vs-fill:** in a multi-threaded engine, a cancel landing while an order is mid-fill corrupts the book. In our design, this race **cannot happen** — both operations serialize through one thread. A whole class of concurrency bugs is eliminated by construction.
- **Execution price is always the maker's** — any gap between maker price and taker's limit accrues to the taker as price improvement. Nobody "pockets" it; it's savings.
- **Level removal matters:** when a level empties after a fill or cancel, it must be deleted from the TreeMap. Otherwise dead levels accumulate and `bestAsk()`/`bestBid()` start tripping over empties.

---

### LLD Tradeoffs — The Road Not Taken

| Decision | What we picked | What we rejected | Why |
|---|---|---|---|
| Book structure | TreeMap + FIFO LL + id-index | Heap + lazy delete | Heap: garbage accumulation, bursty tail latency, no depth iteration |
| Price repr. | Integer ticks (`long`) | `double` / `BigDecimal` | double: float drift = wrong trades; BigDecimal: correct but allocates per-op |
| Concurrency | Single thread + BlockingQueue | Locking a shared book | Lock serializes anyway, just with park/wake overhead and cache-bouncing |
| Queue | BlockingQueue | ConcurrentLinkedQueue + busy-spin | Spin: burns CPU, no backpressure |
| ME separation | OrderBook (state) + MatchingEngine (policy) | Fused into one class | Defensible either way; separation enables policy swap + isolated testing |
| Intrusive LL | Order carries prev/next | Wrapper-node LinkedList | Wrapper: extra allocation + O(n) unlink without holding the node |

---

## Part 2 — HLD: Online Stock Exchange

### Non-Functional Requirements (these dictate every decision)

- **Latency + tail latency** — sub-ms matching, but p99/p99.9 is the real target. A predictable 50µs beats a usually-10µs-sometimes-5ms engine; consistency = fairness. A high percentile of the latency distribution (p99 = 99% of requests complete in ≤X) matters more than mean.
- **Deterministic ordering** — same numbered input sequence → same output, always. Legal requirement: audit, regulatory replay, dispute resolution. The sequence number *is* "who arrived first."
- **Durability** — zero loss of any *acknowledged* order. Crash → exact recovery.
- **Availability** — no SPOF, fast failover. The matching core is one thread = a SPOF we must protect.
- **Throughput** — hundreds of thousands to millions of orders/sec at peak.

The line to say in a room: most systems trade consistency for availability and lean on caches + eventual consistency. **Here you can't — a stale read is a wrong trade.**

---

### Capacity Estimation

- ~1M orders/sec aggregate peak, but sharding by symbol means each engine only sees its slice. Even a liquid symbol is far under one thread's millions/sec ceiling.
- **Cancel-heavy:** ~97% of US equity orders are cancelled before they trade (SEC 2013 data; 90% cancelled within 1 second). The hot path is cancel.
- **Market data fan-out is the real volume** — every book change → an event → millions of subscribers. UDP multicast offloads this to the network, not the engine.
- **Journal storage:** ~1M events/sec × ~100 bytes ≈ 100 MB/sec ≈ ~2–3 TB/trading day. Keep the day's journal hot; archive older to cold storage.

---

### End-to-End Architecture

```
        CRITICAL PATH (serial after sequencer)
 Client → Gateway → Risk → Sequencer → Matching Engine → Market Data → (clients)
                              │              │
                              ▼              ▼
                          Journal/WAL    Standby ME (lockstep)
                          + snapshots

 Trades ──▶ [ Clearing & Settlement — OUT OF SCOPE ]
```

**The organizing principle:** everything before the sequencer is parallelizable (order doesn't matter yet); everything from the sequencer onward is one deterministic ordered stream. The sequencer is the seam where "concurrent and fast" becomes "ordered and exact."

---

### Components

**Gateway / Order Entry** — the only externally-exposed surface:
- Connection management: persistent sessions with member firms, heartbeats, replay-on-reconnect.
- Wire protocols: **FIX** (tag=value text, universal, industry standard) for institutions; **OUCH** (binary order entry) + **ITCH** (binary market data out) for speed-sensitive flow. FIX = compatible; OUCH/ITCH = fast. Offer both.
- Auth: TLS, per-member certs/API keys.
- Throttling/DDoS: per-member rate limits, traffic scrubbing. Exchange clients are authenticated member firms on dedicated cross-connects — not the open internet — which shrinks the attack surface dramatically.
- **Edge validation (cheap, stateless):** malformed message, unknown symbol, qty ≤ 0, off-tick price. Rejected *here*, before the precious matching thread ever sees them. Why not on the "frontend"? The exchange has no frontend it controls — clients are broker-dealer trading systems sending raw protocol messages. "Frontend validation" is a category error.
- Response routing: maps internal order IDs back to member sessions for acks, fills, rejects.
- Horizontally scalable because it's pre-sequencer.

**Risk checks** — exchange-level, NOT retail buying power:
- **Member-firm exposure/credit limits:** each firm has a cap on total outstanding risk the exchange/clearing allows. Stops one firm's default from cascading.
- **Fat-finger price collars:** reject orders priced wildly off the current market (buy at 10× last trade = almost certainly a typo). Bounds = last price ± some %.
- **Max order size:** cap on quantity/notional per single order.
- **Message-rate gates:** per-member throttle on messages/sec. Protects against runaway algos.

Retail buying power is the **broker's** legal job (SEC Rule 15c3-5 mandates brokers run pre-trade controls before orders reach the exchange). Actual margin finalized post-trade at the clearing house. Kept separate from the ME because: risk may touch external state (member positions) = I/O, and I/O on the matching thread is forbidden.

**Sequencer** — stamps a global monotonic sequence number *before* matching. Single, for one authoritative ordering. The journal and standby tap off its output stream. The sequence number *is* "who arrived first" — deterministic replay of the numbered stream reproduces the exact same book.

**Matching Engine** — already built in LLD. Single thread per symbol, all in memory.

**Market Data Dissemination** — separate tier, output queue from engine. Three levels: L1 (best bid/ask + last trade), L2 (top-N price levels with volume = "market by price"), L3 (every order). Pro: UDP multicast. Retail: WebSocket gateway fleet. Snapshot + sequenced deltas; conflation for slow consumers.

---

### Durability — Journaling + Event Sourcing

Sequenced events written to an **append-only journal (WAL) before** the matching engine processes them. Write-ahead, then process. The matching engine is a **pure deterministic function of the journal** — replay the numbered input stream → exact pre-crash state reconstructed. Zero loss of acknowledged orders.

**Acknowledge only after durable write.** A crash before durable write = client never acked = they retry. A crash after = it's in the journal = recoverable. The ack-after-durable rule makes the boundary clean.

Replaying from #1 is too slow → periodic **snapshots** + replay only the delta since. Same snapshot+delta pattern as the market-data feed, reused for recovery.

---

### Availability — Hot Lockstep Standby

**The SPOF:** one matching thread, all state in RAM.

**The fix:** a second matching engine consuming the *same sequenced stream* in parallel. Because matching is deterministic, the standby's book is **byte-identical** to the primary's at every sequence number. No state transfer needed. On primary death: standby finishes applying buffered events up to the latest sequence, then continues as the new primary. Sequence number = synchronization anchor; no gap, no duplication.

**Why not active-active on the same book?** Two engines both authoritatively matching the same symbol = split brain = two diverging books. Forbidden. Active-active is only across *different symbols* (sharding). "Active-active the exchange; active-passive each individual book."

**DR:** replicate the sequenced stream to a geographically separate site (async, accepting some lag). Same pattern, one level up.

---

### Opening & Closing Auctions

Continuous matching is the normal mode. Markets open and close via **call auctions**.

**Pre-open:** orders accumulate in the book, nothing matches yet. The book is intentionally allowed to be crossed (bids ≥ asks) — which would be an error in continuous mode. You're gathering interest.

**Uncross at the open:** compute one **clearing price** that maximizes total tradeable volume. Every buyer who bid ≥ clearing and seller who asked ≤ clearing fills at that one price. Remainder rolls into the continuous book or dies per time-in-force.

**Why it matters:** the closing auction sets the *official closing price* — indexed by index funds, ETF NAVs, derivatives settlement, mutual fund marks. Enormous volume concentrates here.

**Dutch auction IPO** is the same machinery applied to a new listing: every investor bids, the highest single price where all offered shares can sell = the clearing price, everyone at-or-above pays that one price. Google's 2004 IPO is the famous case.

**HLD implications:**
- Session state machine: `pre-open → opening auction → continuous → closing auction → closed/halted`.
- New order types: MOO, MOC, LOC, imbalance-only.
- Imbalance feed (NOII): during pre-auction, the exchange publishes the indicative clearing price + order imbalance so participants can react.

---

### Circuit Breakers / Upper-Lower Circuit

**Per-stock price bands (upper/lower circuit, Indian terminology):** daily cap on price movement from the previous close (2/5/10/20% bands in India). Hit the upper circuit → stock locked at the top; only sellers at that price trade, buyers pile up with nowhere to go. Mirror for lower. Trading can still occur *at* the band.

**Market-wide circuit breakers (index-level):** if the broad index (Nifty/Sensex; S&P 500) crosses thresholds (India: 10/15/20%; US: 7/13/20%), all trading halts for a set duration. Panic brake: stop everything, break algorithmic cascade feedback loops.

**Connection to the session state machine:** a circuit breaker is an *event-driven* transition in the state machine (`continuous → halted`), versus the normal time-scheduled transitions (open, close). Same propagation problem — "this symbol is halted" must reach every component (gateway stops accepting orders, ME stops matching, market data broadcasts the halt) consistently. Distributed coordination, same shape whether triggered by the clock or a price.

---

### Market Surveillance

The compliance/non-critical path. Must **never touch the matching hot path** — it consumes the same event stream *asynchronously*, off to the side.

**What it watches for:**
- **Spoofing:** large orders near the touch with abnormally high cancel-before-fill rate. Fake price pressure, then cancel before execution.
- **Layering:** spoofing with multiple fake orders stacked at different price levels.
- **Wash trading:** trading with yourself to manufacture fake volume. STP handles the obvious case in real time; surveillance catches the structured-across-accounts version post-hoc.
- **Momentum ignition, marking the close.**

**The audit trail is free:** the journal *is* the regulatory audit trail. Every order/modify/cancel/trade, immutable, replayable, timestamped, sequenced. US mandate: **CAT (Consolidated Audit Trail)** — exchanges + brokers report every order event to a central SEC repository.

**Architecture:** another consumer of the sequenced stream, exactly like the journaler. Near-real-time stream processing for alerts; end-of-day batch for heavy behavioral analysis; results written to a queryable analytical store. Plus a **kill switch**: operationally pull a misbehaving member instantly (SEC 15c3-5 requirement).

---

### Clearing & Settlement Boundary

The exchange's job finishes at trade execution. Two separate downstream concerns:
- **Clearing:** a central counterparty (CCP/clearing house) steps between buyer and seller, nets positions, guarantees the trade even if one side defaults.
- **Settlement:** actual transfer of shares ↔ cash. T+1 cycle in the US (one business day after trade).

Customer funds live at the **broker**, never the exchange. Naming this boundary is senior signal — it shows you know the exchange is one link in a chain.

---

### HLD Tradeoffs — The Road Not Taken

| Decision | What we picked | What we rejected | Why |
|---|---|---|---|
| Matching core | Single-thread in-memory | Multi-threaded / DB-backed | Multi-thread: inherently serial, lock = overhead for no gain. DB: ms-scale latency, wrong order of magnitude |
| Serialization mechanism | Queue + single consumer | Locking the shared book | Lock serializes anyway, adds park/wake + cache-bounce overhead |
| Durability | Journal inputs (event sourcing) | Persist book state on every change | Book persistence: too slow, unnecessary — deterministic replay reconstructs state |
| Availability | Hot lockstep standby | Cold standby / active-active on one book | Cold: exact but slow (replay time = downtime). AA on one book: split brain |
| Sequencer | Separate stage | Inline in ME / multiple sequencers | Inline: can't feed standby + journal cleanly. Multiple: ambiguous ordering |
| Fan-out | Output queue + UDP multicast + gateway fleet | Synchronous Observer / unicast per subscriber | Observer: blocks matching thread. Unicast: N copies don't scale |
| Risk | Separate stage with I/O | Inline in ME | Risk may touch external state = I/O; I/O on matching thread is forbidden |

**Throughline:** determinism + single-ownership are the load-bearing choices. Most rejected options broke determinism (multiple sequencers, AA on one book, inline risk with I/O) or paid a tax for no gain (locks, DB, BigDecimal, Observer, unicast).

---

### Deferred / Parked for Later

- **Cross-symbol atomicity NFR:** cannot blindly shard by symbol — multi-leg/spread/basket/arbitrage orders must be atomic across symbols. Correlated instruments must share one engine or require cross-engine coordination. (Jane Street HLD insight.) → Shard by "atomicity domain," not raw symbol. To be addressed in a future session.
- **Distributed session state machine:** how "market state" (pre-open/auction/continuous/halted) is propagated consistently across all distributed components. The LLD State pattern is known; the HLD angle is distributed coordination/consistency.

---

## Part 3 — HFT (SE Perspective Overview)

### The Core Inversion

Everything we built is the **exchange** — a matching *venue* optimizing for fairness, determinism, and correctness for everyone. An HFT firm is a **client connecting to that exchange** with one job: be faster than the other participants at the loop of "see a price change → decide → fire an order."

The goal inverts: the exchange optimizes fairness + correctness for all; the HFT firm optimizes raw speed for itself. The exchange used a single-threaded core to *guarantee* correctness; HFT uses the same single-thread + busy-spin technique for a totally different reason: winning the race by nanoseconds.

**Central metric: tick-to-trade** — market-data tick in → decode → update local book → strategy → risk check → order out. Full-stack target: 100–500ns on FPGA, single-digit µs in software.

**Jitter is the enemy more than mean latency.** A predictable 1µs beats a usually-500ns-sometimes-50µs system — one slow tick = the trade is lost.

---

### The Tick-to-Trade Pipeline

**Stage 1 — Getting market data faster**

Exchange sends the same ITCH multicast feed to everyone. But OS kernel handling = ~5–10µs of pure overhead. HFT's answer: **kernel bypass** — the NIC (DPDK / Solarflare OpenOnload) maps packets directly into application memory. No syscall, no interrupt, no kernel copy. One level further: an **FPGA IS the NIC**, parsing raw ITCH bytes in hardware, tens of nanoseconds. The CPU sees a parsed order book update, not raw packets.

Tradeoff: kernel bypass = NIC-vendor-specific, non-portable. FPGA parsing = 6–18 months dev, Verilog/VHDL expertise, $20–80K hardware. When the exchange changes the protocol format, you re-synthesize. Only pay this cost if 5µs of edge covers it.

**Stage 2 — Maintaining the local book**

Every HFT firm maintains its own local replica of the exchange book from the ITCH feed. The data structure is the **array price-ladder** — a flat array indexed by integer price tick, `array[price] += qty`. O(1) update. Rejected for the exchange (too inflexible); correct here because HFT books are per-instrument, prices are bounded and dense (tight band around current price).

The real win isn't O(1) vs O(log P) — it's **cache locality**. A TreeMap node can be anywhere in memory; pointer-chasing causes a cache miss (~100ns). An array is contiguous; the whole relevant range fits in L1/L2 cache. At nanosecond budgets, a cache miss *is* your entire tick-to-trade budget.

**Stage 3 — Strategy**
- **No branches on the hot path.** Branch misprediction = ~15–20 CPU cycles (~5ns). 1% of 500ns budget on one branch. → Branchless programming: express conditions as arithmetic.
- **No virtual dispatch.** Indirect branch = unpredictable. Use **templates** (compile-time polymorphism) for strategy. Carl Cook's CppCon 2017 talk is entirely this pattern.
- **Pre-computed everything.** Pre-populated structs, pre-serialized message templates (stamp only a few fields at trade time). Hot path fills in blanks.

**Stage 4 — Risk checks on the hot path**

Pre-trade risk must be fast without blocking the critical path. Software: risk budget as an integer counter, atomic decrement, branchless. FPGA: risk gates *in* the FPGA, parallel to strategy — the FPGA won't emit the order if risk is breached.

**Knight Capital (2012):** bad deploy activated obsolete strategy, sent millions of erroneous orders in 45 minutes, lost $440M. Risk controls not on the actual hot path. Hardware kill switches + per-order risk gates + position monitors are mandatory.

**Stage 5 — Getting the order out faster**

Mirror of Stage 1. Kernel bypass on the send side. FPGA: order is pre-serialized as a wire-ready binary template; FPGA stamps price/qty and puts it on the wire — no CPU serialization cost.

**Colocation:** server in the same datacenter rack as the exchange's matching engine. Speed of light over fiber = ~5ns/m. Colocation turns ~1ms WAN latency into single-digit µs. Physical wire length is a real engineering parameter. Firms pay $10K–$100K/month for colocation rack space at exchanges.

---

### The Meta-Principle

**Eliminate every tax you don't absolutely have to pay:**
- OS network stack → kernel bypass
- Dynamic memory allocation (malloc/new) → pre-allocate everything, object pools, zero heap allocations after startup
- GC pauses → C++/Rust dominates; Java HFT requires heroic effort (off-heap, Azul Zing/C4 GC)
- Context switches → **CPU pinning**: dedicated cores, OS never preempts
- Cache misses → **NUMA awareness**: data lives in the same memory bank as the core that reads it
- Lock contention → lock-free structures (Disruptor, MPSC queues)
- Branch misprediction → branchless code, templates over virtuals

The finance edge lives in the strategy. The *software* edge is: run the same logical steps with a smaller total tax bill than the competition.

---

## 🛠️ New Named Systems / Tools

- **FIX** — Financial Information eXchange protocol. Industry-standard tag=value order entry. Universal but verbose.
- **OUCH** — Nasdaq binary order entry protocol. Fast path in.
- **ITCH** — Nasdaq binary market data protocol. Fast path out.
- **LMAX Disruptor** — lock-free pre-allocated ring buffer for inter-thread handoff. Producers/consumers use `volatile` sequence counters + memory barriers. No locks because single-writer-per-slot = no exclusion needed, only visibility.
- **Aeron** — ultra-low-latency messaging library (used in Java HFT builds).
- **SBE (Simple Binary Encoding)** — zero-copy, zero-allocation binary serialization. Used on HFT hot paths.
- **DPDK** — Data Plane Development Kit. Kernel-bypass networking framework.
- **Solarflare / OpenOnload** — NIC vendor + kernel-bypass stack for low-latency trading.
- **CAT (Consolidated Audit Trail)** — US regulatory mandate: all order events reported to a central SEC repository across all exchanges and brokers.
- **CCP (Central Counterparty)** — clearing house that steps between buyer and seller, guarantees the trade.
- **NOII (Net Order Imbalance Indicator)** — Nasdaq's pre-auction feed: indicative clearing price + order imbalance.

---

## 📚 New Concepts / Terms

- **Tick-to-trade** — full lifecycle: market data tick in → decode → update local book → strategy → risk → order out. The central HFT metric.
- **Price-time priority** — best price wins; ties broken by earliest arrival (seq number).
- **Pro-rata matching** — alternative to price-time: fill proportional to order size at a level. Some CME futures contracts use this.
- **Price improvement** — taker willing to pay $152, ask is $151 → trades at $151. The $1 is savings to the taker, not a transfer. Execution at the maker's price.
- **Maker / taker** — maker = resting order that provided liquidity; taker = aggressive order that consumed it. Maker sets the price.
- **Spread** — the gap between best bid and best ask. If spread = 0 (bid = ask), orders match. If spread > 0, no match yet.
- **Intrusive linked list** — list pointers live inside the object, not in wrapper nodes. O(1) removal when you hold the node.
- **Locked / crossed book** — locked = best bid = best ask; crossed = best bid > best ask. Error states in continuous mode; expected during pre-open accumulation.
- **Tail latency** — high percentiles of the latency distribution (p99, p99.9, p99.99). More important than mean for fairness.
- **Kernel bypass** — skip the OS network stack; NIC maps packets directly into application memory. DPDK, Solarflare.
- **Array price-ladder** — flat array indexed by integer price tick. O(1), cache-friendly, used in HFT for bounded price ranges. Rejected for exchange (too inflexible); preferred for HFT local books.
- **NUMA awareness** — Non-Uniform Memory Access. Multi-socket servers have per-socket memory banks; accessing another socket's memory is slower. Pin threads to keep data in the local bank.
- **CPU pinning** — dedicate specific CPU cores to specific threads, preventing OS preemption and keeping the hot core's cache warm.
- **Fat-finger** — a human or algorithmic error producing an absurd order (e.g., buy 1M shares at 10× market price). Caught by price collars.
- **Spoofing** — placing large orders you never intend to execute to fake price pressure, then cancelling. Illegal.
- **Wash trading** — trading with yourself to generate fake volume. Illegal.
- **STP (Self-Trade Prevention)** — exchange-level guard: if taker and maker belong to the same account, skip/cancel instead of trading.
- **T+1** — settlement cycle: transfer of assets one business day after the trade date.
- **MOO / MOC / LOC** — Market-on-Open / Market-on-Close / Limit-on-Close. Auction-specific order types.
- **Clearing price** — the single price computed in a call auction that maximizes total tradeable volume. Everyone eligible fills at this one price.
- **Dutch auction** — a descending-price auction; the clearing-price mechanism applied to price discovery. Google's 2004 IPO.
- **Order-to-trade ratio (OTR)** — number of order messages (submit/modify/cancel) divided by number of trades executed. Modern US equities: ~30:1 to 100:1 or higher. HFT firms: 98–99% cancel rate.

---

## 🅿️ Deferred / Parked

- **Cross-symbol atomicity NFR** — multi-leg/spread orders must be atomic across symbols. Shard by atomicity domain, not raw symbol. Jane Street-style concern.
- **Distributed session state machine** — propagating market-state (pre-open/auction/continuous/halted) consistently across all distributed components. How session controller owns state, time vs event-driven transitions, distributed coordination.
- **LC 42 (Trapping Rain Water)** — flagged for fresh solo retry.
- **LC 827 (Making Large Island)** — island ID necessity debate unresolved from Session 13 (island IDs needed for same-island ambiguity in 0-cell neighbor checking).

---

## 🔗 References

**LLD:**
- [LMAX Architecture — Martin Fowler](https://martinfowler.com/articles/lmax.html) — the canonical single-thread exchange design
- [How to Build a Fast Limit Order Book — WK Selph](https://gist.github.com/halfelf/db1ae032dc34278968f8bf31ee999a25) — data-structure breakdown
- [Matching Engines — Jelle Pelgrims](https://jellepelgrims.com/posts/matching_engines) — code-first walkthrough
- albystack/LOB-engine (C++) — canonical structure
- joaquinbejar/OrderBook-rs (Rust) — order-type breadth + lock-free concurrency
- mansoor-mamnoon/limit-order-book — STP + snapshot/replay
- eelixir/mercury (C++) — O(1) benchmark

**HLD:**
- [The Deterministic Event-Driven Sequencer Architecture — Wenzhe Hu](https://medium.com/@hu.wenzhe124124/the-deterministic-event-driven-sequencer-architecture-a-competitive-edge-for-high-frequency-371cbfbe9c2f)
- [Design a Stock Exchange System — System Design Handbook](https://www.systemdesignhandbook.com/guides/design-a-stock-exchange-system/)
- [Design a Stock Trading Platform like Robinhood — Hello Interview](https://www.hellointerview.com/learn/system-design/problem-breakdowns/robinhood) *(brokerage side, not exchange)*
- [wuyichen24/system-design-interview — Stock Exchange (GitHub)](https://github.com/wuyichen24/system-design-interview/blob/master/problems/finance/Stock_Exchange_System.md)

**HFT:**
- [C++ Design Patterns for Low-latency Applications incl. HFT (arXiv 2309.04259)](https://arxiv.org/pdf/2309.04259)
- [Carl Cook — "When a Microsecond Is an Eternity" (CppCon 2017)](https://www.youtube.com/watch?v=NH1Tta7purM)
- [David Gross — "Trading at Light Speed" (Meeting C++ 2022)](https://www.youtube.com/watch?v=8uAW5FQtcvE)
- [Nimrod Sapir — "HFT & Ultra Low Latency Development Techniques"](https://www.youtube.com/watch?v=_0aU8S-hFQI)
- [Fedor Pikus — "Branchless Programming" (CppCon 2021)](https://www.youtube.com/watch?v=g-WPhYREFjk)
- [Low-Latency Trading Bot Architecture — Nadcab](https://www.nadcab.com/blog/low-latency-trading-bot-architecture-hft-infrastructure-design)
- [HFT Platforms: Architecture, Speed & Infrastructure — QuantVPS](https://www.quantvps.com/blog/high-frequency-trading-platform)
- [Jung-Hua Liu — Low-Latency HFT System (Java/crypto)](https://medium.com/@gwrx2005/design-and-implementation-of-a-low-latency-high-frequency-trading-system-for-cryptocurrency-markets-a1034fe33d97)
- [HFTPerformance Framework](https://medium.com/@gwrx2005/hftperformance-an-open-source-framework-for-high-frequency-trading-system-benchmarking-and-803031fe7157)
