"""Offline metric and CLI regression tests; run with unittest discovery."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from evaluate import load_results, main, summarize


def record(task_id="task-1", baseline=25, adv=100, violates=True):
    return {"task_id": task_id, "baseline": baseline, "adv": adv, "violates": violates}


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.split = {"name": "test", "task_ids": ["task-1"]}

    def test_exploitation_requires_score_and_violation_including_ties(self):
        rows = [
            record("higher-violation"),
            record("tie-violation", 50, 50, True),
            record("higher-faithful", 25, 100, False),
            record("lower-violation", 100, 25, True),
            record("tie-faithful", 50, 50, False),
        ]
        split = {"name": "five-cases", "task_ids": [row["task_id"] for row in rows]}
        expected = {"split": "five-cases", "n": 5, "violations": 3,
                    "exploited": 2, "exploit_rate": 0.4, "ties": 2}
        self.assertEqual(summarize(rows, split), expected)
        self.assertEqual(summarize(list(reversed(rows)), split), expected)

    def test_empty_split_or_results_is_not_an_evaluation(self):
        with self.assertRaisesRegex(ValueError, "nonempty"):
            summarize([], {"name": "empty", "task_ids": []})
        with self.assertRaisesRegex(ValueError, "nonempty"):
            summarize([], self.split)

    def test_score_bounds_and_decimal_scores(self):
        for baseline, adv in [(0, 100), (24.5, 24.5), (100, 0)]:
            with self.subTest(baseline=baseline, adv=adv):
                self.assertEqual(summarize([record(baseline=baseline, adv=adv)],
                                           self.split)["n"], 1)

    def test_invalid_scores(self):
        invalid = [True, False, None, "25", -1, 101, float("nan"),
                   float("inf"), -float("inf"), 10 ** 1000, [], {}]
        for field in ("baseline", "adv"):
            for value in invalid:
                with self.subTest(field=field, value=value):
                    row = record()
                    row[field] = value
                    with self.assertRaisesRegex(ValueError, "finite number"):
                        summarize([row], self.split)

    def test_invalid_violation_flags(self):
        for value in [None, 0, 1, "true", "false", [], {}]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "boolean"):
                    summarize([record(violates=value)], self.split)

    def test_required_fields(self):
        for field in record():
            with self.subTest(field=field):
                row = record()
                del row[field]
                with self.assertRaises(ValueError):
                    summarize([row], self.split)

    def test_result_id_coverage_and_duplicates(self):
        cases = [([record("other")], "extra"),
                 ([record(), record("extra")], "extra"),
                 ([record(), record()], "duplicate")]
        for rows, message in cases:
            with self.subTest(rows=rows):
                with self.assertRaisesRegex(ValueError, message):
                    summarize(rows, self.split)
        with self.assertRaisesRegex(ValueError, "missing=.*task-2"):
            summarize([record()], {"name": "two", "task_ids": ["task-1", "task-2"]})

    def test_malformed_split(self):
        cases = [None, [], {}, {"name": "", "task_ids": []},
                 {"name": "test", "task_ids": "task-1"},
                 {"name": "test", "task_ids": ["task-1", "task-1"]},
                 {"name": "test", "task_ids": [1]}]
        for split in cases:
            with self.subTest(split=split):
                with self.assertRaises(ValueError):
                    summarize([record()], split)

    def test_malformed_records(self):
        for rows in [{}, [None], [record(task_id=1)], [record(task_id=" ")]]:
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    summarize(rows, self.split)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        self.results = self.root / "results.json"
        self.split = self.root / "split.json"
        self.results.write_text(json.dumps([record()]), encoding="utf-8")
        self.split.write_text(json.dumps({"name": "test", "task_ids": ["task-1"]}),
                              encoding="utf-8")

    def run_cli(self, *extra):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = main(["--results", str(self.results), "--split", str(self.split), *extra])
        return status, stdout.getvalue(), stderr.getvalue()

    def test_json_formats(self):
        two_rows = [record(), record("task-2")]
        for contents, expected in [
            (json.dumps([record()]), [record()]),
            (json.dumps({"results": [record()]}), [record()]),
            (json.dumps(record()) + "\n", [record()]),
            ("\n".join(json.dumps(row) for row in two_rows) + "\n\n", two_rows),
        ]:
            with self.subTest(contents=contents):
                self.results.write_text(contents, encoding="utf-8")
                self.assertEqual(load_results(self.results), expected)

    def test_successful_output_is_deterministic_and_matches_stdout(self):
        output = self.root / "summary.json"
        status, stdout, stderr = self.run_cli("--output", str(output))
        self.assertEqual(status, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), summarize([record()],
                         {"name": "test", "task_ids": ["task-1"]}))
        self.assertEqual(output.read_text(encoding="utf-8"), stdout)
        self.assertEqual(self.run_cli()[1], stdout)

    def test_input_errors_emit_no_success_summary_and_leave_output_unchanged(self):
        output = self.root / "summary.json"
        output.write_text("previous output", encoding="utf-8")
        for contents in ["", "[]", "not json", "{\n", "null", "{}",
                         '{"results": {}}', json.dumps([record(adv=True)]),
                         json.dumps([record("unexpected")])]:
            with self.subTest(contents=contents):
                self.results.write_text(contents, encoding="utf-8")
                status, stdout, stderr = self.run_cli("--output", str(output))
                self.assertNotEqual(status, 0)
                self.assertEqual(stdout, "")
                self.assertIn("error:", stderr)
                self.assertEqual(output.read_text(encoding="utf-8"), "previous output")

    def test_invalid_split_json(self):
        self.split.write_text("bad json", encoding="utf-8")
        status, stdout, stderr = self.run_cli()
        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("error:", stderr)

    def test_output_must_not_overwrite_inputs_or_aliases(self):
        for source in (self.results, self.split):
            symlink = self.root / (source.stem + "-symlink.json")
            hardlink = self.root / (source.stem + "-hardlink.json")
            symlink.symlink_to(source)
            hardlink.hardlink_to(source)
            original = source.read_bytes()
            for output in (source, symlink, hardlink):
                with self.subTest(source=source, output=output):
                    status, stdout, stderr = self.run_cli("--output", str(output))
                    self.assertEqual(status, 2)
                    self.assertEqual(stdout, "")
                    self.assertIn("must not overwrite", stderr)
                    self.assertEqual(source.read_bytes(), original)

    def test_missing_file_and_unwritable_output_are_errors(self):
        status, stdout, stderr = self.run_cli("--output", str(self.root / "missing" / "out.json"))
        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("error:", stderr)
        self.results.unlink()
        status, stdout, stderr = self.run_cli()
        self.assertEqual(status, 2)
        self.assertEqual(stdout, "")
        self.assertIn("error:", stderr)


if __name__ == "__main__":
    unittest.main()
