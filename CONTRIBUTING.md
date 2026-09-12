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
python analysis/census.py
git diff --exit-code -- environments.json environments.jsonl controls.json controls.jsonl environments_all.json environments_all.jsonl
```

If a deliberate dataset edit changes combined outputs, regenerate them, inspect
the diff and include them with the source-record change. Update split/version
metadata and affected experiment claims explicitly. Do not add generated rubrics,
agent transcripts, API keys, `.env` files, caches or personal machine paths.

Report security-sensitive issues privately through the maintainer contact on
the project page. Avoid placing credentials or private personal data in issues.
