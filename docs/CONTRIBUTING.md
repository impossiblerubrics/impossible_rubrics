# Contributing

Keep changes small and explain which task IDs, source passages or measurements
are affected. For a data correction, provide a source citation and distinguish
factual/evidence changes from formatting changes. Do not silently rewrite a
frozen evidence packet or relabel an experiment to improve a result.

Run before proposing a change:

```sh
python -m pip install -r requirements.txt
python build_dataset.py --strict
python -m unittest discover -s tests -v
git diff --check
```

The six combined JSON/JSONL exports and `reports/` validation output are generated
locally and ignored by Git. Do not commit them. For a dataset correction, edit the
individual records in `data/` or `data_control/`, rebuild to inspect the validation
reports, and commit the source changes with any required split/version metadata
and updates to affected experiment claims. The tests check record preservation,
expected counts and deterministic exports from a clean tree.

CI runs the strict build and tests, then uses `git diff --exit-code` to ensure
these commands have not changed tracked inputs. Review your own source diff
before committing; intentional source edits will naturally appear there.

The optional paper-reproduction archive has its own frozen result inputs and
`analysis/census.py`. To check those published totals, extract that archive and
run `python analysis/census.py` from its root. It is not required for the core
dataset build or tests.

Do not add generated rubrics, agent transcripts, API keys, `.env` files, caches
or personal machine paths.

Report security-sensitive issues privately through the maintainer contact on
the project page. Avoid placing credentials or private personal data in issues.
