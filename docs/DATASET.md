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
`results/difficulty_selection.json`. Split IDs are frozen separately in `splits/`.
Three unused empty/placeholder fields are removed. Questions, evidence passages,
certificates, ground truth, answer text and meaningful supplements are preserved.
`RELEASE_MANIFEST.json` records every projection and output-file hash.

## Intended use and limits

Use for research on generated scoring rules, evidence fidelity and adversarial
reward optimization. It is a selected research benchmark, not a prevalence
estimate for ordinary user questions and not a medical, legal or financial advice
system. A low observed exploit rate under one attacker is not a proof of robustness
against all possible optimizers. See [LIMITATIONS.md](LIMITATIONS.md).

The resource stores environments and certificates rather than a library of
generated rubrics. The bundled numeric results permit specific offline checks;
new generator evaluation requires generating new rubrics and running the chain.

## Rights and corrections

See [DATA_LICENSE.md](../DATA_LICENSE.md). Evidence is frozen for reproducibility,
but the source snapshot does not establish per-passage redistribution rights.
Report source or annotation errors with task ID and document ID. Substantive
evidence/certificate edits need a versioned change and result revalidation.
