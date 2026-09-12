#!/usr/bin/env python3
"""Export question/evidence inputs without evaluation labels or certificates."""

import argparse
import json
from pathlib import Path
import sys

from evaluate import load_results


def project_inputs(records, split):
    ids = split.get("task_ids") if isinstance(split, dict) else None
    if not isinstance(ids, list) or not ids or any(
        not isinstance(value, str) or not value for value in ids
    ) or len(set(ids)) != len(ids):
        raise ValueError("split.task_ids must be nonempty, unique strings")
    by_id = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("task_id"), str):
            raise ValueError("each environment needs a string task_id")
        task_id = record["task_id"]
        if task_id in by_id:
            raise ValueError(f"duplicate environment task_id: {task_id}")
        by_id[task_id] = record
    missing = set(ids) - by_id.keys()
    if missing:
        raise ValueError(f"split IDs missing from environments: {sorted(missing)}")

    output = []
    for task_id in ids:
        record = by_id[task_id]
        question, evidence = record.get("question"), record.get("evidence")
        if not isinstance(question, str) or not question or not isinstance(evidence, list) or not evidence:
            raise ValueError(f"{task_id}: question and evidence are required")
        projected = []
        seen_docs = set()
        for doc in evidence:
            if not isinstance(doc, dict) or any(
                not isinstance(doc.get(key), str) or not doc[key] for key in ("doc_id", "text")
            ):
                raise ValueError(f"{task_id}: evidence needs nonempty doc_id and text")
            if doc["doc_id"] in seen_docs:
                raise ValueError(f"{task_id}: duplicate evidence doc_id")
            seen_docs.add(doc["doc_id"])
            projected.append({"doc_id": doc["doc_id"], "text": doc["text"]})
        output.append({"task_id": task_id, "question": question, "evidence": projected})
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("environments_all.jsonl"))
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--output", type=Path, help="write JSONL here instead of stdout")
    args = parser.parse_args(argv)
    try:
        if args.output:
            for source in (args.data, args.split):
                if args.output.resolve() == source.resolve() or (
                    args.output.exists() and source.exists() and args.output.samefile(source)
                ):
                    raise ValueError("output must not overwrite an input")
        records = project_inputs(load_results(args.data), json.loads(args.split.read_text()))
        serialized = "".join(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n" for row in records)
        if args.output:
            args.output.write_text(serialized, encoding="utf-8")
        else:
            print(serialized, end="")
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
