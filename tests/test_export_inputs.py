import copy
import unittest

from export_inputs import project_inputs


class InputBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "task_id": "task-a", "question": "What does the packet support?",
            "evidence": [{"doc_id": "D1", "text": "Evidence text.",
                          "relevance_note": "PRIVATE_EVALUATION_ANNOTATION"}],
            "oracle_certificate": {"claim": "PRIVATE_EVALUATION_ANNOTATION"},
            "ground_truth": "PRIVATE_EVALUATION_ANNOTATION",
            "adaptive_stress": {"tier": "high"},
            "fixed_stress_answers": ["PRIVATE_EVALUATION_ANNOTATION"],
        }
        self.split = {"name": "example", "task_ids": ["task-a"]}

    def test_only_question_and_evidence_fields_cross_boundary(self):
        before = copy.deepcopy(self.record)
        rows = project_inputs([self.record], self.split)
        self.assertEqual(rows, [{"task_id": "task-a", "question": self.record["question"],
                                 "evidence": [{"doc_id": "D1", "text": "Evidence text."}]}])
        self.assertEqual(self.record, before)

    def test_uses_explicit_split_order(self):
        second = dict(self.record, task_id="task-b")
        rows = project_inputs([self.record, second], {"task_ids": ["task-b", "task-a"]})
        self.assertEqual([r["task_id"] for r in rows], ["task-b", "task-a"])

    def test_rejects_missing_or_duplicate_ids(self):
        for records, split in [([self.record], {"task_ids": ["missing"]}),
                               ([self.record, self.record], self.split),
                               ([self.record], {"task_ids": ["task-a", "task-a"]}),
                               ([self.record], {"task_ids": []})]:
            with self.subTest(split=split), self.assertRaises(ValueError):
                project_inputs(records, split)

    def test_rejects_ambiguous_evidence_ids(self):
        self.record["evidence"] *= 2
        with self.assertRaises(ValueError):
            project_inputs([self.record], self.split)


if __name__ == "__main__":
    unittest.main()
