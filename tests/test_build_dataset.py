"""Offline regression checks for dataset integrity and safe strict builds."""

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
ARTIFACTS = tuple(
    f"{name}.{extension}"
    for name in ("environments", "controls", "environments_all")
    for extension in ("json", "jsonl")
)


class DatasetBuildTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="impossiblerubrics-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        shutil.copy2(REPO / "build_dataset.py", self.root / "build_dataset.py")
        shutil.copytree(REPO / "schema", self.root / "schema")
        for directory, filename in (
            ("data", "objective_conflict_m002.json"),
            ("data_control", "ctrl_001.json"),
        ):
            (self.root / directory).mkdir()
            shutil.copy2(REPO / directory / filename, self.root / directory / filename)
        self.impossible_path = self.root / "data" / "objective_conflict_m002.json"
        self.control_path = self.root / "data_control" / "ctrl_001.json"

    def run_build(self, strict=True):
        command = [sys.executable, str(self.root / "build_dataset.py")]
        if strict:
            command.append("--strict")
        return subprocess.run(command, cwd=self.root, text=True, capture_output=True)

    def read_record(self, path):
        return json.loads(path.read_text())

    def write_record(self, path, record):
        path.write_text(json.dumps(record), encoding="utf-8")

    def load_validator(self):
        spec = importlib.util.spec_from_file_location(
            "temporary_build_dataset", self.root / "build_dataset.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_valid_subset_builds_despite_historical_coverage_gaps(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(all((self.root / name).exists() for name in ARTIFACTS))
        combined = self.read_record(self.root / "environments_all.json")
        self.assertEqual([row["env_type"] for row in combined],
                         ["impossible", "answerable_control"])
        report = self.read_record(self.root / "reports" / "coverage_report.json")
        self.assertEqual(report["expected_per_type"], 25)
        self.assertTrue(report["type_coverage_gaps"])

    def test_duplicate_task_ids_within_impossible_records_fail_strict(self):
        record = self.read_record(self.impossible_path)
        self.write_record(self.root / "data" / "duplicate.json", record)
        result = self.run_build()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = self.read_record(self.root / "reports" / "coverage_report.json")
        self.assertEqual(report["duplicate_task_ids"], {record["task_id"]: 2})

    def test_duplicate_task_ids_across_impossible_and_control_fail_strict(self):
        impossible = self.read_record(self.impossible_path)
        control = self.read_record(self.control_path)
        control["task_id"] = impossible["task_id"]
        self.write_record(self.control_path, control)
        result = self.run_build()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_control_duplicate_evidence_id_fails_strict(self):
        record = self.read_record(self.control_path)
        record["evidence"].append(copy.deepcopy(record["evidence"][0]))
        self.write_record(self.control_path, record)
        result = self.run_build()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = (self.root / "reports" / "validation_report.md").read_text()
        self.assertIn("duplicate evidence doc_id", report)

    def test_strict_errors_do_not_create_or_overwrite_combined_artifacts(self):
        original = self.read_record(self.impossible_path)
        for error_kind in ("structural", "schema", "parse", "duplicate_id"):
            for preexisting in (False, True):
                with self.subTest(error=error_kind, preexisting=preexisting):
                    self.write_record(self.impossible_path, original)
                    extra_path = self.root / "data" / "extra.json"
                    extra_path.unlink(missing_ok=True)
                    sentinels = {}
                    for name in ARTIFACTS:
                        path = self.root / name
                        path.unlink(missing_ok=True)
                        if preexisting:
                            sentinels[name] = f"previous-good-export:{name}\n".encode()
                            path.write_bytes(sentinels[name])
                    broken = copy.deepcopy(original)
                    if error_kind == "structural":
                        del broken["question"]
                        self.write_record(self.impossible_path, broken)
                    elif error_kind == "schema":
                        broken["version"] = 123
                        self.write_record(self.impossible_path, broken)
                    elif error_kind == "parse":
                        extra_path.write_text("{not valid json", encoding="utf-8")
                    else:
                        self.write_record(extra_path, original)
                    result = self.run_build()
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertTrue((self.root / "reports" / "coverage_report.json").exists())
                    for name in ARTIFACTS:
                        if preexisting:
                            self.assertEqual((self.root / name).read_bytes(), sentinels[name])
                        else:
                            self.assertFalse((self.root / name).exists(), name)

    def test_nonstrict_invalid_inputs_still_write_exports(self):
        record = self.read_record(self.impossible_path)
        del record["question"]
        self.write_record(self.impossible_path, record)
        result = self.run_build(strict=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        exported = self.read_record(self.root / "environments.json")
        self.assertEqual(exported, [record])
        self.assertTrue(all((self.root / name).exists() for name in ARTIFACTS))

    def test_approved_inconsistent_certificate_is_rejected(self):
        record = self.read_record(self.impossible_path)
        record.setdefault("review_status", {})["status"] = "approved"
        record.setdefault("evaluation_spec", {}).setdefault("audit", {})[
            "certificate_consistent"
        ] = False
        errors, _ = self.load_validator().structural_errors(record)
        self.assertTrue(any("certificate_consistent=false" in error for error in errors))

    def test_extra_references_do_not_downgrade_verified_evidence(self):
        record = {
            "evidence": [{"doc_id": "DOC1", "url_or_reference": "https://example.org"}],
            "source_references": [
                {"doc_id": "DOC1", "verification_status": "primary_fetched"},
                {"doc_id": "DOC1", "verification_status": "snippet_only"},
                {"doc_id": "UNRELATED", "verification_status": "unverifiable"},
            ],
        }
        validator = self.load_validator()
        self.assertEqual(validator.derive_provenance(record),
                         ("real_web_grounded", "verifiable"))
        record["evidence"].append({"doc_id": "DOC2", "url_or_reference": "SYNTHETIC"})
        self.assertEqual(validator.derive_provenance(record),
                         ("hybrid", "partially_verifiable"))

    def test_valid_full_dataset_preserves_export_bytes(self):
        for directory in ("data", "data_control"):
            shutil.rmtree(self.root / directory)
            shutil.copytree(REPO / directory, self.root / directory)
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for name in ARTIFACTS:
            with self.subTest(artifact=name):
                self.assertEqual((self.root / name).read_bytes(), (REPO / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
