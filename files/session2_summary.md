# FAANG+ Prep — Session 2 Summary (3rd May)

---

## 📖 Index / Preface

> Quick-reference map of everything covered this session. Use this to navigate.

| # | Topic | Type | Key Takeaway |
|---|---|---|---|
| 1 | Revision — 5 prior cards | Spaced repetition | Rate limiter algos, spatial indexing, stream merge, queue vs log, class imbalance |
| 2 | Alien Dictionary | DSA — Graph + Topo Sort | Extract constraints from adjacent word pairs → Kahn's BFS |
| 3 | Cheapest Flights Within K Stops | DSA — Constrained Dijkstra | State = (node, stops), no visited set, first pop = cheapest |
| 4 | Distributed Cache | HLD | Consistent hashing, Write-Around, CDC, TTL, Thundering Herd |
| 5 | All 5 Rate Limiters in Java | LLD | Fixed Window, Sliding Log, Sliding Counter, Token Bucket, Leaky Bucket |
| 6 | Bias-Variance + Regularization | ML | High variance = overfit, L1/L2 penalties, activations, vanishing gradients |
| 7 | DB Fundamentals | Bonus | R/W rates, N+1 query problem, SQL injection + fix |

---

## ✅ Parts Completed

| Part | Topic | Status |
|---|---|---|
| 0 | Revision — 5 pattern cards | ✅ |
| 1 | LLD — All 5 Rate Limiters (Java) | ✅ |
| 2 | DSA — Alien Dictionary | ✅ |
| 3 | DSA — Cheapest Flights Within K Stops | ✅ |
| 4 | HLD — Distributed Cache | ✅ |
| 5 | ML — Bias/Variance + Regularization MCQ | ✅ |
| 6 | Bonus — DB Fundamentals | ✅ |

---

## 🃏 Pattern Cards Added

### Card #6 — Constraint Graph + Topological Sort
| | |
|---|---|
| **What** | Extract ordering constraints from comparisons → directed edges → topo sort |
| **Recognize when** | "Given sorted list, infer ordering rule" / "schedule with dependencies" / "prerequisite chains" |
| **Core mechanic** | Kahn's BFS: track in-degrees, process zero-in-degree nodes first, detect cycles by checking output size |
| **Edge cases** | Prefix violation + cycle detection |
| **Complexity** | O(N·L) where N = words, L = max word length |
| **Connections** | Course Schedule (LC 207), Task Scheduler, Build Systems, Package dependency resolution |

---

### Card #7 — Distributed Cache Architecture
**Core decisions in order:**
```
1. Sharding       → Consistent hashing (NOT hash mod N — node death = 75% remap)
                  → Virtual nodes (~150/server) for even distribution
                  → Blast radius on node loss = 1/N

2. Read flow      → Write-Around
                  → App: check cache → miss → fetch DB → populate cache → return

3. Write flow     → Write-Around (write to DB, skip cache)
                  → Or Write-Through (cache + DB sync) if freshness matters
                  → Or Write-Back (cache → DB async) if write throughput matters; risk = data loss

4. DB↔Cache sync  → CDC (Debezium tails WAL → Kafka → cache invalidator)
                  → Required when multiple writers or non-app writes exist

5. Invalidation   → TTL (simplest, stale-OK systems)
                  → Event-driven via CDC (proactive)
                  → Hybrid (TTL safety net + CDC for known writes)
```

**Thundering Herd Toolkit:**

| Solution | Mechanism |
|---|---|
| TTL Jitter | Randomize expiry ± delta |
| Probabilistic Early Expiry | Request voluntarily refreshes near expiry; probability ramps as TTL approaches |
| Request Coalescing | Mutex on key — only 1 request goes to DB on miss, others wait |
| Background Refresh | Async job refreshes hot keys before expiry |
| Stale-While-Revalidate | Serve stale immediately + async refresh |

**Numbers to memorize:**

| Stat | Value |
|---|---|
| Single Redis node throughput | ~100K ops/sec |
| Single Redis node memory | ~25-50GB practical |
| Hash mod N rebalance cost | (N-1)/N keys remapped |
| Consistent hashing rebalance cost | 1/N keys remapped |

**Vocab unlocked:**
```
SLA / SLO / SLI    →  contract / target / measurement
Shard / Partition  →  effectively the same
Replica            →  copy, not split
WAL                →  write-ahead log, DB's source of truth
Debezium           →  CDC tool that tails WAL → publishes to Kafka
Thundering Herd    →  simultaneous expiry → DB stampede
CDC                →  Change Data Capture — streams every DB change as an event
```

---

### Card #8 — Bias-Variance & Regularization

| Term | Meaning |
|---|---|
| **Bias** | Error from oversimplification. High bias = underfit. Symptom: bad on train AND test |
| **Variance** | Error from oversensitivity. High variance = overfit. Symptom: great on train, bad on test |
| **Sweet spot** | Low bias + low variance. Balance via model complexity, regularization, more data |
| **L1 (Lasso)** | Penalty `λ·Σ\|w\|`. Sparse weights. Feature selection. Diamond constraint geometry |
| **L2 (Ridge)** | Penalty `λ·Σw²`. Shrinks all weights smoothly. Circle constraint geometry |
| **Dropout** | NN-specific. Randomly disables neurons during training. Different from L1/L2 |
| **Early stopping** | Stop training when val loss starts rising |

**Dartboard mental model:**
```
Low bias, low variance   → darts clustered ON bullseye        ✅ ideal
Low bias, high variance  → darts scattered AROUND bullseye    → overfit
High bias, low variance  → darts clustered AWAY from bullseye → underfit
High bias, high variance → darts scattered AND off center     → worst case
```

**Activation cheat sheet:**
```
Regression        → linear (z)
Binary classif.   → sigmoid: 1 / (1 + e^(-z))
Multiclass        → softmax: e^z / Σe^z
Hidden layers     → ReLU: max(0, z)
```

**Vanishing gradient fixes:**
```
ReLU              → gradient doesn't shrink for positive activations
Xavier/He init    → weights initialized at right scale
Batch norm        → keeps activations well-scaled between layers
Residual conns    → gradient highway that bypasses layers entirely
```

**Metrics cheat sheet:**
```
Accuracy    = (TP+TN) / all          → naive, useless under imbalance
Precision   = TP / (TP+FP)          → cautious, "when I fire, am I right?"
Recall      = TP / (TP+FN)          → vigilant, "did I catch all positives?"
F1          = 2·P·R / (P+R)         → balanced diplomat
F2          = 5·P·R / (4P+R)        → recall-heavy (fraud, cancer)
ROC-AUC     = TPR vs FPR            → ranking quality, threshold-agnostic
PR-AUC      = Precision vs Recall   → imbalance-honest, preferred for fraud
MCC         = correlation using all 4 cells → holistic, incorruptible
```

---

### Card #9 — Rate Limiter Algorithms

| Algorithm | Burst | Memory | Accuracy |
|---|---|---|---|
| Fixed Window Counter | ✅ | O(1) | ❌ boundary spike |
| Sliding Window Log | ❌ | O(n requests) | ✅ perfect |
| Sliding Window Counter | ❌ | O(1) | ✅ approximate |
| Token Bucket | ✅ up to capacity | O(1) | ✅ |
| Leaky Bucket | ❌ smooth output | O(1) | ✅ |

**State per user:**
```
Fixed Window        → {windowId, count}
Sliding Window Log  → ArrayDeque<timestamp>
Sliding Window Ctr  → {windowId, count} × 2 windows
Token Bucket        → {tokens, lastRefillTime}
Leaky Bucket        → {waterLevel, lastDrainTime}
```

**Sliding Window Counter formula:**
```
elapsed  = (currentTimeSec - windowStart) / windowSize   // 0.0 → 1.0
estimate = currCount + (1 - elapsed) × prevCount
```

**Token Bucket formula:**
```
tokens = Math.min(tokens + elapsed × refillRate, maxTokens)
```

**Leaky Bucket formula:**
```
waterLevel = Math.max(0, waterLevel - elapsed × drainRate)
if waterLevel < capacity → waterLevel++ → allow
else → deny
```

**Thread safety pattern across all 5:**
```java
ConcurrentHashMap (outer) + synchronized(userObject) (inner)
putIfAbsent BEFORE synchronized block
```

---

### Card #10 — Constrained Shortest Path (Dijkstra + Budget)

| | |
|---|---|
| **What** | Shortest path with a secondary constraint (stops, hops, time) limiting exploration |
| **Recognize when** | "Cheapest/shortest within K steps/hops/stops" |
| **Key insight** | State = `(node, budget)` not just `node`. Same node at different budgets = different states |
| **Pruning** | Only prune on budget (`stops > k`), NOT on cost |
| **Terminating** | First time you POP dst from min-heap = cheapest valid path |
| **Complexity** | O(K·E·log(K·E)) |

**Two classic mistakes:**
```
1. Using visited set          → kills valid higher-cost lower-stop paths
2. Returning in neighbor loop → might not be cheapest path yet
```

---

## 🗄️ Bonus — DB Fundamentals

### DB R/W Rates (ballpark)

| DB | Reads/sec | Writes/sec | Notes |
|---|---|---|---|
| PostgreSQL | ~10K-50K | ~5K-10K | single node, simple queries |
| MySQL | ~10K-50K | ~5K-10K | similar to Postgres |
| MongoDB | ~20K-80K | ~10K-20K | document model, less joins |
| Cassandra | ~100K+ | ~100K+ | distributed, write-optimized |
| Redis | ~500K-1M | ~500K-1M | in-memory, no disk |

**Interview takeaway:** Single Postgres node saturates ~10-50K reads/sec. That's why you cache — 500K reads/sec with Redis + 5K misses hitting Postgres is fine. Without cache, 500K → Postgres melts. 🔥

---

### N+1 Query Problem

**What it is:** Making 1 query to fetch N records, then N more queries to fetch related data — one per record.

```sql
-- BAD: 1 + N queries
SELECT * FROM users;                               -- 1 query, returns 100 users
SELECT * FROM orders WHERE userId = 1;             -- query 1 of 100
SELECT * FROM orders WHERE userId = 2;             -- query 2 of 100
...                                                -- 99 more queries 😱

-- GOOD: 1 query
SELECT u.*, o.*
FROM users u
LEFT JOIN orders o ON o.userId = u.id;             -- 1 query ✅
```

**Where it comes from:** ORMs (Hibernate, Django ORM, ActiveRecord) with lazy-loading. Hidden in your code — you don't see the extra queries.

**How to detect:** Query logging — if you see 100 identical queries with different IDs → N+1.

**Fixes:**
```
1. Eager loading   → JOIN in one query
2. Batch loading   → WHERE userId IN (1, 2, 3 ... 100)
3. DataLoader      → used in GraphQL, batches requests in one event loop tick
```

---

### SQL Injection

**The attack — injecting SQL via user input:**

```sql
-- Your intended query:
SELECT * FROM users WHERE username = '[INPUT]'

-- Normal:       username = "alice"
SELECT * FROM users WHERE username = 'alice'        -- fine ✅

-- Attack 1:     username = "' OR '1'='1"
SELECT * FROM users WHERE username = '' OR '1'='1'
-- always true → dumps all users 😱

-- Attack 2:     username = "'; DROP TABLE users; --"
SELECT * FROM users WHERE username = ''; DROP TABLE users; --'
-- deletes entire table 💀
```

Works in ANY language — Python, Node, Go, Ruby, PHP — wherever you concatenate strings into SQL.

**The fix — parameterized queries (language-agnostic):**

```python
# Python
cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
```
```javascript
// Node
db.query("SELECT * FROM users WHERE username = $1", [username])
```
```go
// Go
db.Query("SELECT * FROM users WHERE username = ?", username)
```

```
❌ String concatenation / interpolation → vulnerable
✅ Placeholder (?, $1, %s) + separate data → safe
```

The DB driver sends query skeleton and data **separately**. Data is never parsed as SQL. Attack neutralized regardless of input.

**Other layers of defence:**

| Fix | How |
|---|---|
| Parameterized queries | Primary fix — always |
| Input validation | Whitelist expected formats |
| Least privilege | DB user only has SELECT, not DROP/DELETE |
| WAF | Blocks known injection patterns at network level |
| ORM | Auto-parameterizes — but raw queries still dangerous |

---

## 📋 Backlog for Session 3

- [ ] L1/L2 geometry deep dive (diamond vs circle, why L1 produces sparsity)
- [ ] Race condition on concurrent cache writes (HLD follow-up)
- [ ] Vanishing gradients deep dive (ML)
- [ ] Metrics deep dive: Part 2 (Specificity, ROC-AUC, PR-AUC, MCC)

---

## 🔁 All Pattern Cards So Far

| Card | Topic |
|---|---|
| #1 | Class Imbalance |
| #2 | Top-K + Spatial Indexing |
| #3 | Stream Merge + Delta Aggregation |
| #4 | Queue vs Log |
| #5 | Rate Limiter Algorithms (conceptual) |
| #6 | Constraint Graph + Topological Sort |
| #7 | Distributed Cache Architecture |
| #8 | Bias-Variance & Regularization |
| #9 | Rate Limiter Algorithms (implementation) |
| #10 | Constrained Shortest Path |
