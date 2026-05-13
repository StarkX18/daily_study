# Session 1 — Foundations: Merge K Lists, Rate Limiter, Queue vs Log, Confusion Matrix

**Date:** May 2, 2026
**Domains:** DSA × 2 · LLD · HLD · ML
**Theme:** Establishing the five core domains and the QnA prep format. First round of foundational patterns.

---

## 🧠 New Algorithms

- **K-way merge with min-heap** — Merging N sorted streams: heap holds one entry per stream's head. O(E log N).
- **Top-K via bounded max-heap** — Maintain a max-heap of size K; replace top if new item is smaller. O(N log K), O(K) space.
- **Two-pointer merge with carried state** — Merging 2 sorted streams where values persist between events; track `lastA`, `lastB`.
- **Delta aggregation trick** — Maintain running sum across streams via `sum += new − old`. Avoids O(N) recomputation per pop.

## 🎯 New Patterns

- **Stream Merge with Carried State + Incremental Aggregate** — Heap of stream heads + per-stream `last[]` cache + running aggregate updated via delta.
- **Top-K + Spatial Indexing combo** — First narrow N via spatial grid lookup, then run Top-K on the reduced set.
- **Confusion Matrix decomposition** — Every classification metric derives from {TP, FP, FN, TN}.

## 🛠️ Systems / Tools / Libraries (named things)

- **Geohash** — String-prefix grid encoding (Redis GEO, Elasticsearch).
- **H3 (Uber)** — Hexagonal hierarchical spatial index. Equal-area cells, 6 equidistant neighbors.
- **S2 (Google)** — Spherical Hilbert curve projection of cube faces. Google Maps.
- **Quadtree** — Density-adaptive recursive 4-way subdivision. Games, GIS.
- **k-d tree** — k-dimensional BST alternating split dimensions. Sklearn KNN. Bad under updates.
- **Kafka** — Append-only partitioned log. Replay, multiple consumer groups.
- **RabbitMQ** — Smart broker / dumb consumer queue. Ack-and-delete.
- **APNs / FCM** — Apple/Firebase push notification services.

## 📚 Terms / Concepts

- **Precision** — TP / (TP + FP). Column metric. "When I say yes, am I right?"
- **Recall (Sensitivity, TPR)** — TP / (TP + FN). Row metric. "Of all real positives, how many caught?"
- **F1** — Harmonic mean of P and R: `2·P·R / (P+R)`. Punishes the weaker.
- **F2** — Recall-heavy variant: `5·P·R / (4P+R)`. For fraud, cancer.
- **ROC-AUC** — TPR vs FPR area. Threshold-agnostic ranking quality.
- **PR-AUC** — Precision vs Recall area. Better than ROC under imbalance.
- **MCC (Matthews Correlation)** — Uses all 4 cells. Imbalance-robust.
- **Type I error** — False Positive.
- **Type II error** — False Negative.
- **Class imbalance** — Skewed label distribution; accuracy metric becomes misleading.
- **Queue vs Log dichotomy** — Queue = competing consumers, ack-delete. Log = independent groups, replay.
- **Delivery guarantees** — At-most-once / At-least-once / Exactly-once.
- **Consumer groups** — Kafka coordinated consumption unit. Parallelism ≤ partition count.
- **Carry-forward semantics (LWW)** — Last-Write-Wins persistence between events in stream merges.
- **Last-Write-Wins (LWW)** — Distributed systems conflict resolution.

## 🅿️ Backlog Surfaced

- Full confusion matrix tour (Specificity, NPV, FPR, FNR, MCC, balanced accuracy)
- ROC-AUC vs PR-AUC construction & geometry
- Probability calibration (Platt scaling, isotonic regression, reliability diagrams)
- Imbalance techniques (SMOTE, undersampling, class weights, focal loss)

## 🔗 References

- [Uber H3 Blog](https://www.uber.com/blog/h3/)
- [H3 GitHub](https://github.com/uber/h3)
- [Google S2 docs](https://s2geometry.io/)
- [S2 Hilbert curve deep dive (Perone)](https://blog.christianperone.com/2015/08/googles-s2-geometry-on-the-sphere-cells-and-hilbert-curve)
