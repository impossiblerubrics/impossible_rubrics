# Dataset card

## Task

The benchmark evaluates **rubric generators**. A generated rubric is exploited
when an attacker earns at least the fixed honest baseline's score and its answer
violates the environment's certificate. Answerable controls check that a rubric
does not simply reward refusal.

## Frozen resource

| Property | Impossible | Controls |
|---|---:|---:|
| Environments | 169 | 48 |
| Evidence passages | 773 | 164 |
| Fixed stress answers | 685 | 144 |
| Fully verifiable environments | 109 | 27 |
| Partially verifiable environments | 60 | 21 |

The impossible types are counterevidence trap (27), insufficient evidence (26),
impossible exhaustiveness (25), missing citation support (25), objective conflict
(41), and false premise (25). `EXPECTED_PER_TYPE=25` in the validator is the
historical balanced 150-item reference, not a current-release size requirement.

All environments use a closed evidence packet. Of the impossible environments,
158 are `real_web_grounded` and 11 are `hybrid`; controls are real-web-grounded.
There are 12 synthetic evidence passages. Environment records contain 939 source
references; the per-evidence inventory covers 937 passages and attaches 936
matching references. All original source-reference entries remain in the records.
Fetch-verification labels record how sources
were checked; they do not imply semantic correctness or copyright permission.

## Record structure

- `question`, `evidence[].doc_id` and `evidence[].text` define generator input.
- `oracle_certificate`, `ground_truth`, fixed stress answers and their validity
  labels are evaluation material. Never pass them into the generator prompt.
- `provenance_type`, `source_verifiability`, `source_references` and review/audit
  metadata describe construction and validation. They are not model inputs.
- `evaluation_spec` is optional; 3 impossible records lack it. Their oracle
  certificates remain present. `oracle_certificate_supplement`, when present,
  may carry substantive clarification and is retained.
- Fixed stress answers deliberately include incorrect or unsupported statements
  for evaluation. Their inclusion does not endorse those statements as facts.

Previous `adaptive_stress` and `adaptive_stress_grounded` blocks are moved into
`results/difficulty_selection.json` in the
[optional reproduction pack](https://github.com/impossiblerubrics/impossible_rubrics/releases/download/reproduction-v1.2/impossiblerubrics-reproduction-v1.2.zip).
Split IDs are frozen separately in `splits/`.
Three unused empty/placeholder fields are removed. Questions, evidence passages,
certificates, ground truth, answer text and meaningful supplements are preserved.
The [release manifest](https://github.com/impossiblerubrics/impossible_rubrics/releases/download/reproduction-v1.2/release_manifest.json)
records every projection and output-file hash.

## Intended use and limits

Use for research on generated scoring rules, evidence fidelity and adversarial
reward optimization. It is a selected research benchmark, not a prevalence
estimate for ordinary user questions and not a medical, legal or financial advice
system. A low observed exploit rate under one attacker is not a proof of robustness
against all possible optimizers.

The resource stores environments and certificates rather than a library of
generated rubrics. The optional numeric results permit specific offline checks;
new generator evaluation requires generating new rubrics and running the chain.

### Interpretation and reproducibility

- **Selected tasks and cuts.** Full-150 and Hard-45 answer different questions.
  Hard-45 was selected for difficulty and shares 26 environments with Full-150.
  Its exploit rates are selection-amplified.
- **Single draws and resampling.** Several headline rows use one generated rubric.
  Resampling was characterized for only a subset of generators; do not transfer
  those intervals to other models or treat small ordering differences as resolved.
- **Attacker dependence.** Rates measure exploitation under a specified attacker,
  judge and oracle chain. They do not certify a global optimum or adversarial bound.
- **Shared families and self-play.** Some generator/attacker/oracle roles share a
  model family, and the Opus 5 arm uses the model in three roles. Held-out checks
  bound particular explanations without establishing fully independent evaluators.
- **Oracle and source limits.** A certificate is a task-specific operational
  honesty boundary. Human calibration used a single author/rater; agreement does
  not make the oracle infallible. Source-verification labels and mechanical schema
  checks do not establish semantic truth.
- **Historical execution conditions.** Original runs used an author-specific
  agent workflow runtime. Audit records describe tool access, some access to
  repository/ground-truth information, certificate/configuration changes and
  invalidated attempts. The released packages exclude internal logs but do not
  claim those conditions never occurred. New evaluations should explicitly isolate
  role inputs and record tool permissions.
- **Missing records and incomplete runs.** Not every original headline draw can
  be regenerated from a saved rubric; some bridge or experimental stages were
  stopped or invalidated. The optional census is limited to its named completed
  result inputs and does not reproduce every paper result.
- **Statistical interpretation.** The research notes identify unresolved wording
  around multiple testing, non-significance, mean shifts versus variance and
  single-draw conclusions. Packaging does not resolve those questions or modify
  the recorded measurements.

The benchmark is an adversarial evaluation of generated reward specifications.
The worked example does not measure a policy's reinforcement-learning training
trajectory. Ordinary best-of-N selection and adversarial optimization are
different threat models.

## Rights and corrections

The licensing scope is in [NOTICE](../NOTICE). Evidence is frozen for
reproducibility, but the source snapshot does not establish per-passage
redistribution rights. The
[source inventory](https://github.com/impossiblerubrics/impossible_rubrics/releases/download/reproduction-v1.2/source_manifest.json)
lists source URLs, citations, fetch-verification status, word counts and text
hashes. Its `source_license` field records upstream licensing information and
remains unknown until verified; it is separate from the project's Apache-2.0 grant.
Source-rights review remains pending for the 925 passages not marked synthetic.
This is an unfinished review, not a conclusion that every passage requires
separate permission or that none may be redistributed.

Report source or annotation errors with task ID, document ID and source URL.
Substantive evidence/certificate edits need a versioned change and result
revalidation. Preserve the frozen evidence and annotations when reviewing rights;
a citation-only or rights-resolved subset must be versioned and labeled as such,
rather than described as the complete original benchmark.

## Snapshot provenance

This repository contains the reviewed benchmark snapshot with new history.
The original research repository and its development history remain private.

This snapshot intentionally preserves exact task/evidence strings and scientific
annotations. Its technical validation is not a grant of third-party rights.

The snapshot corresponds to source commit
`a3ff18d48983fd6f2712d5cb7083a3aff2ad12e6`, with release-specific validation fixes,
portable tools, documentation and mechanical field projections. Uncommitted
experiments from the author's working directory are not included.
