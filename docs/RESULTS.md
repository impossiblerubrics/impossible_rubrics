# Frozen results and reproducibility

## Download and run

[Download the reproduction pack](https://github.com/impossiblerubrics/impossible_rubrics/releases/download/reproduction-v1.1/impossiblerubrics-reproduction-v1.1.zip)
from the repository's release assets. It is separate from the core benchmark
checkout and includes its own split manifests, scorer and census script.
Python 3.10+ is sufficient; no dependency installation or model API is needed.

```sh
unzip impossiblerubrics-reproduction-v1.1.zip
cd impossiblerubrics-reproduction
python analysis/census.py
```

The archive also retains prior difficulty-selection metadata in
`results/difficulty_selection.json`. Its file hashes and archive SHA-256 are
recorded in the core repository's
[release manifest](https://github.com/impossiblerubrics/impossible_rubrics/blob/main/docs/release_manifest.json).

## Frozen measurements

The optional pack contains 18 numeric result files under `results/census/`, used by the explicit roster in
`analysis/census.py`. Only `task_id`, model/generator labels, `baseline`, `adv` and
`violates` are retained. Free-form strategies, generated rubric text and raw agent
responses are not needed for this computation and are not included.

```sh
python analysis/census.py
```

Expected totals:

| Quantity | Value |
|---|---:|
| Arms | 21 |
| Environment–arm cells | 2,100 |
| Certificate violations | 522 |
| Exploited cells | 514 |
| Violations scoring below baseline | 8 |
| Violating score ties | 5 |

The two exploitation conditions differ on 8 cells. The 5 violating ties are
included among the 514 exploits because the rule is `adv >= baseline`.

This census combines multiple model arms and scoring periods. Full-150 and
Hard-45 overlap, and a model can appear in both. The total is not 2,100 independent
environments, and it is not a single leaderboard rate. The original three Claude
Hard-45 headline draws are not silently reconstructed by substituting resampled
or held-out-attacker rates.

To check one exact included arm with strict split coverage:

```sh
python evaluate.py --results results/census/opus5_hardset_runs.json --split splits/hard45.json
```

Expected: 16 exploits out of 45, no ties. This is an **offline recomputation of
stored measurements**, not independent regeneration of the rubric or answers.

Requested model aliases are retained as recorded. Some historical artifacts do
not preserve fully resolved version identifiers. A display-name correction in a
paper does not retroactively add missing runtime metadata to these records.

The complete paper includes analyses beyond this compact census package.
Excluded partial/invalid runs, bridge failures and internal execution logs are
not silently counted as completed replications. Relevant constraints are
summarized in [LIMITATIONS.md](LIMITATIONS.md).
