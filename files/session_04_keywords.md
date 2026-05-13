# Session 4 — Quadtree Nearest Neighbor + LeetCode #3528

**Date:** May 7, 2026
**Domains:** DSA · HLD-adjacent
**Theme:** Deep dive into Best-First Search for spatial nearest-neighbor queries. Started a LeetCode Hard graph problem (parked mid-deconstruction).

---

## 🧠 New Algorithms

- **Best-First Search on Quadtree (Nearest Neighbor)** — Min-heap ordered by min-distance from query to node bbox. Pop point → done (1-NN) or add to top-K max-heap (KNN). Prune quadrant if `min_dist(query, bbox) > current_best`.
  - **Bbox distance formula:**
    ```
    dx = max(xmin − qx, 0, qx − xmax)
    dy = max(ymin − qy, 0, qy − ymax)
    min_dist = sqrt(dx² + dy²)
    ```
  - **1-NN guarantee:** First *point* popped is provably the nearest — everything remaining in heap has greater or equal min-distance.
  - **K-NN:** Maintain max-heap of size K; pruning threshold = distance to current K-th nearest.
  - **Complexity:** Avg O(log N), worst O(N).

## 🎯 New Patterns

- **Best-First Search (general)** — Priority-queue exploration ordered by best lower-bound estimate. Generalizes to A*, branch-and-bound.
- **Spatial pruning via bbox** — Always prune via *minimum possible* distance from query to region, not center.
- **Min-heap (best-first) vs DFS** — DFS over-explores irrelevant regions; best-first never visits a region unless it *could* improve the answer.

## 🛠️ Systems / Tools / Libraries (named things)

- **R-tree** — Generalization of quadtree for arbitrary rectangles. PostGIS, geospatial DBs.
- **KD-tree (revisited)** — Static NN works elegantly with best-first; bad for moving fleets.
- **M-tree** — Metric tree generalizing best-first to arbitrary distance functions (not just Euclidean).

## 📚 Terms / Concepts

- **Why H3 over quadtree** — Quadtrees have bbox-distance asymmetry at quadrant boundaries (corners). H3 hex cells have 6 equidistant neighbors, no corner ambiguity, equal-area cells at all latitudes.
- **Pruning threshold** — In K-NN, the distance to the K-th nearest found so far. Updated whenever a closer point is added.
- **Heap entry types** — Heap can contain *nodes* (regions, with min-dist) or *points* (with exact dist). Different processing for each.

## 🅿️ Backlog Surfaced

- **LeetCode #3528 "Maximum Reachable Value"** — Jump forward if smaller, backward if larger. Key unlock: edges are bidirectional → undirected graph → DSU components. Open question: minimum edge set per index to build components in O(N log N) via monotonic stack or sort+sweep. **PARKED for retry from this point.**

## 🔗 References

- [Uber H3 Blog](https://www.uber.com/blog/h3/) — saved
- [H3 GitHub](https://github.com/uber/h3) — saved
