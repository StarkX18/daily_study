# Session 3 — Spaced Revision + 0-1 BFS + Terminology Lock

**Date:** May 4-5, 2026 (approximate)
**Domains:** Revision-heavy · DSA · Terminology rules
**Theme:** Reinforcement of Session 2 cards via concept-level revision (not problem-clones). First introduction of 0-1 BFS. Locked in Coinbase ML focus and Write-Around terminology.

---

## 🧠 New Algorithms

- **0-1 BFS** — Shortest path on graphs where edge weights are *only 0 or 1*. Use `Deque`: push-front for 0-weight edges, push-back for 1-weight. O(V+E). Beats Dijkstra's O((V+E) log V) when weights are binary.

## 🎯 New Patterns

- **Concept-level revision (not problem-clone)** — When revising a pattern, test the abstraction, not a recycled scenario. Q-style: "What invariant breaks?", "What does state look like?", "What edge weights tell you which algorithm?"
- **Dijkstra's invariant** — "Once popped from PQ, the node has its globally optimal distance." Constraint problems can break this invariant.

## 🛠️ Systems / Tools / Libraries (named things)

- (Mostly reinforcement of Session 2's tooling — no new named systems this session)

## 📚 Terms / Concepts

- **Coinbase OA style (locked-in rule)** — ML questions = theoretical MCQs + small ML logic implementations. No fluffy open-ended.
- **Write-Around (terminology rule)** — Never use "cache-aside." Always "Write-Around." This is now a permanent terminology rule.
- **Algorithm choice by edge-weight shape** —
  - Unweighted graph (or uniform weight) → BFS
  - Binary edge weights (only 0/1) → 0-1 BFS with deque
  - Arbitrary positive weights → Dijkstra
  - Negative weights possible → Bellman-Ford
- **DFS topo sort 3-state machinery** — white (unvisited) / gray (in-progress) / black (done). Gray hit during DFS = cycle.

## 🅿️ Backlog Surfaced

- (No new backlog items introduced — primarily clearing previous backlog through revision)

## 🔗 References

- (Reinforcement session — no new references)

---

## ⚠️ Note on coverage

This file is reconstructed from partial memory + spaced-revision questions visible in past chats. If specific topics or problems were covered that aren't reflected here, flag them for retrofit in Session 6's revision.
