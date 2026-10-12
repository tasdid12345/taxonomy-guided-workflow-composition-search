# Taxonomy-Guided Type-State Search for Synthetic Workflow Composition

**Motivation.** The paper "Comparing SLTLx-based Synthesis and ASP for the Automated Composition of Data Analysis Workflows" compares two ways of automatically composing data-analysis tools into valid workflows, and reports that answer-set programming with taxonomy-based type propagation is much faster than SLTLx-based synthesis as workflow length grows. This repository asks whether a similar idea, pruning with taxonomy-based forward and backward type reachability, also helps a plain search-based composer.

**Question.** Can a taxonomy-guided search with backward type pruning find valid analysis workflows faster and with less runtime variance than a standard breadth-first type-state search on a synthetic typed-tool domain?

**Dataset.** No external data. A typed-tool library (a random type taxonomy and random tools with input and output types) is generated in `analysis.py` with a fixed numpy seed, at roughly the size of the pizza-baking domain from the paper's Listing 1.1. This is not the paper's own dataset.

**Baseline vs. improved.** The baseline is a breadth-first forward search over type-states with no pruning. The improved method first prunes tools with taxonomy-based forward and backward reachability, then runs best-first search ordered by an estimated distance to the goal. Both methods share the same instances, the same test split, the same time budget and the same yes/no check.

**How to run**

```
pip install -r requirements.txt
python analysis.py
```

**Results:** results are written to `results.json` (and a chart to `figures/`).

## Reference

This project is motivated by the following paper:

> AL Lamprecht. *Comparing SLTLx-based Synthesis and ASP for the Automated Composition of Data Analysis Workflows*. taasp.at. https://taasp.at/2025/assets/paper/20_Comparing_SLTL_x_based_Synt.pdf

Paper author: Prof. Anna-Lena Lamprecht, Universität Potsdam (anna-lena.lamprecht@uni-potsdam.de)


---
_The code in this repository was drafted with AI assistance and runs automatically on GitHub Actions; results come from the latest run._
