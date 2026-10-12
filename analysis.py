"""Taxonomy-guided best-first type-state search vs. breadth-first type-state search
on a synthetic, seeded typed-tool domain (pizza-like scale). CPU only, deterministic."""
import heapq, json, os, sys, time
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SEED = 42
N_TYPES, N_TOOLS, N_INST, MAX_LEN = 30, 60, 60, 15   # pizza-like size; L = max workflow length
BUDGET = 2.0            # per-instance wall-clock budget (s), identical for both methods
TEST_FRAC = 0.3
INF = 10**9
rng = np.random.default_rng(SEED)

# 1. Taxonomy: random tree over types 0..N-1 (type 0 = root "Any"); parent[i] < i
PARENT = [-1] + [int(rng.integers(0, i)) for i in range(1, N_TYPES)]
def _anc(t):  # type t plus all of its ancestors
    out = set()
    while t != -1:
        out.add(t); t = PARENT[t]
    return frozenset(out)
ANC = [_anc(t) for t in range(N_TYPES)]

# 2. Tools as (input type, output type); outputs are never the root
TOOLS = [(int(rng.integers(0, N_TYPES)), int(rng.integers(1, N_TYPES))) for _ in range(N_TOOLS)]
# A state = set of held types, closed under ancestors (holding a leaf implies its supertypes).
# A tool is applicable iff its input type is in the state; applying it adds its output's ancestors.

def bfs_search(start, goal, deadline):
    """Baseline: breadth-first search over type-states, no pruning. True/False, None on timeout."""
    s0 = ANC[start]
    if goal in s0:
        return True
    seen, frontier = {s0}, [s0]
    for _ in range(MAX_LEN):
        nxt = []
        for s in frontier:
            if time.perf_counter() > deadline:
                return None
            for i, o in TOOLS:
                if i not in s:
                    continue
                ns = s | ANC[o]
                if ns in seen:
                    continue
                if goal in ns:
                    return True
                seen.add(ns); nxt.append(ns)
        frontier = nxt
        if not frontier:
            break
    return False

def taxonomy_prune(start, goal):
    """Taxonomy-based relaxed reachability. Forward: types obtainable from start.
    Backward: types needed to reach goal. Keep only tools that are applicable in the
    forward relaxation and whose outputs can provide a needed type (sound pruning)."""
    F = set(ANC[start]); changed = True
    while changed:
        changed = False
        for i, o in TOOLS:
            if i in F and not ANC[o] <= F:
                F |= ANC[o]; changed = True
    N = {goal}; changed = True
    while changed:
        changed = False
        for i, o in TOOLS:
            if ANC[o] & N and i not in N:
                N.add(i); changed = True
    return [(i, o) for i, o in TOOLS if i in F and ANC[o] & N]

def distance_estimate(tools, goal):
    """d[x] = relaxed number of tool applications needed to reach goal from a held type x."""
    d = [INF] * N_TYPES
    for x in range(N_TYPES):
        if goal in ANC[x]:
            d[x] = 0
    changed = True
    while changed:  # Bellman-Ford style relaxation over the pruned tool set
        changed = False
        for i, o in tools:
            best = min(d[y] for y in ANC[o]) + 1
            for x in range(N_TYPES):
                if i in ANC[x] and best < d[x]:
                    d[x] = best; changed = True
    return d

def taxonomy_search(start, goal, deadline):
    """Improved: prune with taxonomy reachability, then best-first search ordered by g + h.
    Complete within MAX_LEN, so the yes/no answer matches the baseline."""
    s0 = ANC[start]
    if goal in s0:
        return True
    tools = taxonomy_prune(start, goal)
    d = distance_estimate(tools, goal)
    h = lambda s: min(d[x] for x in s)
    best = {s0: 0}
    heap, cnt = [(h(s0), 0, 0, s0)], 1  # (priority, depth, unique tiebreak, state)
    while heap:
        _, g, _, s = heapq.heappop(heap)
        if best.get(s, INF) < g or g >= MAX_LEN:
            continue
        if time.perf_counter() > deadline:
            return None
        for i, o in tools:
            if i not in s:
                continue
            ns = s | ANC[o]
            if ns == s:
                continue
            if goal in ns:
                return True
            if g + 1 < best.get(ns, INF):
                best[ns] = g + 1
                heapq.heappush(heap, (g + 1 + h(ns), g + 1, cnt, ns)); cnt += 1
    return False

def run(method, instances):
    """Run one method on all instances; runtime capped at budget; None = unsolved in budget."""
    times, res = [], []
    for start, goal in instances:
        t0 = time.perf_counter()
        r = method(start, goal, t0 + BUDGET)
        times.append(min(time.perf_counter() - t0, BUDGET)); res.append(r)
    return np.array(times), res

def main():
    # Instances: seeded start/goal pairs; 30% held out as the test set (nothing is tuned).
    pairs = [(int(rng.integers(1, N_TYPES)), int(rng.integers(1, N_TYPES))) for _ in range(N_INST)]
    perm = rng.permutation(N_INST)
    n_test = int(round(TEST_FRAC * N_INST))
    test = [pairs[k] for k in sorted(perm[:n_test])]
    print(f"types={N_TYPES} tools={N_TOOLS} instances={N_INST} "
          f"train={N_INST - n_test} test={n_test} L={MAX_LEN} budget={BUDGET}s")

    print("Running baseline (breadth-first type-state search)...")
    tb, rb = run(bfs_search, test)
    print("Running improved (taxonomy-pruned best-first search)...")
    ti, ri = run(taxonomy_search, test)

    both = [(a, b) for a, b in zip(rb, ri) if a is not None and b is not None]
    n_agree = sum(a == b for a, b in both)
    if n_agree != len(both):
        print("ERROR: methods disagree on yes/no validity"); sys.exit(1)
    if not both:
        print("ERROR: no instance solved by both methods"); sys.exit(1)

    metrics = {
        "baseline_score": float(tb.mean()),
        "improved_score": float(ti.mean()),
        "improvement": float(tb.mean() - ti.mean()),
        "baseline_runtime_std": float(tb.std()),
        "improved_runtime_std": float(ti.std()),
        "baseline_solved_frac": float(np.mean([r is not None for r in rb])),
        "improved_solved_frac": float(np.mean([r is not None for r in ri])),
        "n_test": n_test,
        "n_compared": len(both),
        "n_agree": n_agree,
        "n_valid_chains_found": int(sum(r is True for r in ri)),
    }
    print(json.dumps(metrics, indent=2))

    os.makedirs("figures", exist_ok=True)
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.bar(["baseline BFS", "taxonomy best-first"], [tb.mean(), ti.mean()],
           yerr=[tb.std(), ti.std()], capsize=6, color=["gray", "steelblue"])
    ax.set_ylabel("mean runtime per instance (s)")
    ax.set_title("Synthetic typed-tool search (test split)")
    fig.tight_layout(); fig.savefig("figures/runtime_bar.png", dpi=120); plt.close(fig)

    results = {
        "question": "Can a taxonomy-guided search with backward type pruning find valid analysis "
                    "workflows faster and with less runtime variance than a standard breadth-first "
                    "type-state search on a synthetic typed-tool domain?",
        "method": "Seeded synthetic taxonomy and tool library; per instance, search for a tool chain "
                  "of length <= 15 from start type to goal type; compare runtime, solved fraction "
                  "and runtime std under a fixed per-instance budget; verify identical yes/no answers.",
        "dataset": {
            "name": "synthetic typed-tool domain (seeded numpy, pizza-like scale)",
            "source_url": "none (generated in analysis.py)",
            "n_rows": N_INST,
            "n_train": N_INST - n_test,
            "n_test": n_test,
            "same_as_paper": False,
            "baseline_is_papers_method": False,
        },
        "metric_name": "mean wall-clock runtime per instance (s)",
        "higher_is_better": False,
        "baseline": "Breadth-first forward search over type-states (sets of held types closed under "
                    "the taxonomy), no pruning, depth limit 15.",
        "improved": "Same search domain, but first propagates taxonomy-based forward and backward type "
                    "reachability to prune tools that cannot contribute to the goal, then runs best-first "
                    "search ordered by an estimated distance-to-goal.",
        "metrics": metrics,
        "notes": "Synthetic domain, not the paper's pizza data; not the paper's ASP/Clingo or APE system. "
                 "Both methods are deterministic, so seeds 42-44 repetition is not needed. "
                 "Nothing is tuned; the train split is reserved and unused, and all metrics are on the test split. "
                 "Runtimes are capped at the per-instance budget and depend on the machine. "
                 "Unsolved-in-budget instances are excluded from the yes/no agreement check. "
                 "The distance heuristic is not admissible; it only orders the search.",
    }
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("Wrote results.json and figures/runtime_bar.png")

if __name__ == "__main__":
    main()
