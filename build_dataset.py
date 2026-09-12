#!/usr/bin/env python3
"""
build_dataset.py - validate, combine, and report on ImpossibleRubrics environments.

Reads every data/*.json (impossible environments) and data_control/*.json
(answerable control environments), validates them (structurally + referential
integrity, and against the JSON Schemas when `jsonschema` is available), and emits:
  - environments.json / .jsonl        (the impossible environments)
  - controls.json / .jsonl            (the answerable control environments)
  - environments_all.json / .jsonl    (impossible + controls, each tagged `env_type`)
  - reports/coverage_report.json
  - reports/validation_report.md

Usage:
    python3 build_dataset.py
    python3 build_dataset.py --strict   # exit non-zero on any error (and REQUIRE jsonschema)

`--strict` requires the `jsonschema` package (pip install -r requirements.txt) so the
validation verdict is identical on every machine / in CI. Without --strict, jsonschema
validation is run if available and skipped (with a note) otherwise.
Strict validation errors leave combined exports unchanged; diagnostic reports are
still written to reports/.
"""

import json
import os
import sys
import glob
from collections import Counter

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT, "data")
CONTROL_DIR = os.path.join(ROOT, "data_control")
ENV_SCHEMA_PATH = os.path.join(ROOT, "schema", "environment.schema.json")
CTRL_SCHEMA_PATH = os.path.join(ROOT, "schema", "control_environment.schema.json")
REPORTS_DIR = os.path.join(ROOT, "reports")

IMPOSSIBILITY_TYPES = [
    "evidence_insufficient", "missing_support_citation", "counterevidence_trap",
    "false_premise", "exhaustiveness_impossible", "objective_conflict",
]
PROVENANCE_TYPES = ["real_web_grounded", "synthetic_control", "hybrid"]
VERIFIABILITY = ["verifiable", "partially_verifiable", "non_verifiable_synthetic"]
SCOPES = ["closed_packet", "open_retrieval_allowed"]
EXPECTED_PER_TYPE = 25

REQUIRED_TOP = [
    "task_id", "version", "domain", "impossibility_type", "question",
    "evidence_scope", "provenance_type", "source_verifiability", "evidence",
    "oracle_certificate", "known_failure_modes", "fixed_stress_answers",
    "expected_honest_answer_summary",
]
REQUIRED_CERT = [
    "impossibility_claim", "supported_claims", "unsupported_claims",
    "contradicted_or_weakening_evidence", "required_honest_behavior",
    "reward_hacking_behaviors",
]
EVIDENCE_FIELDS = ["doc_id", "title", "source_type", "url_or_reference",
                   "publication_date", "text", "relevance_note"]

# Controlled per-source verification vocabulary; the two "full" statuses mean the
# source was actually fetched/confirmed and so make its evidence doc verifiable.
FULLY_VERIFIED = {"primary_fetched", "mirror_fetched"}


def _refs_by_doc(env):
    by = {}
    for r in env.get("source_references", []) or []:
        by.setdefault(r.get("doc_id"), []).append(r)
    return by


def _doc_synthetic(doc, by):
    """A single evidence doc is synthetic if it self-declares SYNTHETIC, or all of
    its source_references are `synthetic`."""
    if (doc.get("url_or_reference") or "") == "SYNTHETIC":
        return True
    if (doc.get("provenance") or "").lower() in ("synthetic", "synthetic_control"):
        return True
    rs = [r.get("verification_status") for r in by.get(doc.get("doc_id"), [])]
    return bool(rs) and all(x == "synthetic" for x in rs)


def _doc_verified(doc, by):
    """A real evidence doc is verified iff at least one of its source_references is
    primary_fetched or mirror_fetched. Extra corroborating refs (e.g.
    secondary_corroborated) neither verify nor downgrade a doc that already has a
    full ref; a doc whose only refs are non-full is not verified."""
    return any(r.get("verification_status") in FULLY_VERIFIED
               for r in by.get(doc.get("doc_id"), []))


def derive_provenance(env):
    """Canonically derive (provenance_type, source_verifiability) from the per-source
    controlled vocabulary, the single source of truth. Iterates over EVIDENCE docs;
    source_references that don't correspond to an evidence doc do not participate.

    provenance_type:    all docs synthetic -> synthetic_control; some -> hybrid; none -> real_web_grounded
    source_verifiability: all synthetic -> non_verifiable_synthetic; any synthetic -> partially_verifiable;
                          else (all real) verifiable iff every real doc has a full ref, else partially_verifiable
    """
    evidence = env.get("evidence") or []
    by = _refs_by_doc(env)
    syn = [_doc_synthetic(d, by) for d in evidence]
    if evidence and all(syn):
        return "synthetic_control", "non_verifiable_synthetic"
    if any(syn):
        return "hybrid", "partially_verifiable"
    all_verified = bool(evidence) and all(_doc_verified(d, by) for d in evidence)
    return "real_web_grounded", ("verifiable" if all_verified else "partially_verifiable")


def provenance_derivation_errors(env):
    """HARD errors: stored provenance_type / source_verifiability must equal the
    canonical derivation, so the controlled per-source vocabulary stays the single
    source of truth and the two can never silently diverge."""
    errs = []
    d_pt, d_sv = derive_provenance(env)
    if env.get("provenance_type") != d_pt:
        errs.append(f"provenance_type {env.get('provenance_type')!r} != derived {d_pt!r} "
                    f"(from per-source verification_status)")
    if env.get("source_verifiability") != d_sv:
        errs.append(f"source_verifiability {env.get('source_verifiability')!r} != derived {d_sv!r} "
                    f"(from per-source verification_status)")
    return errs


_CVE_RE = __import__("re").compile(r"CVE-\d{4}-\d+")


def _packet_text(env):
    return " ".join((d.get("text") or "") + " " + (d.get("title") or "")
                    for d in (env.get("evidence") or []))


def gold_answer_grounding_errors(env, gold_blobs):
    """HARD: a `valid` gold answer (and the expected-answer summary) must not assert a
    specific CVE identifier that is absent from the packet — an out-of-packet identifier
    in a gold answer teaches downstream that the hallucination is an honest answer.
    (Mechanical guard for the CVE class; broader semantic faithfulness of gold answers is
    verified out-of-band by the gold-answer audit, workflows/exp_gold_audit.js.)"""
    errs = []
    packet_cves = set(_CVE_RE.findall(_packet_text(env)))
    for label, text in gold_blobs:
        oop = sorted(set(_CVE_RE.findall(text or "")) - packet_cves)
        if oop:
            errs.append(f"valid gold answer/summary [{label}] names out-of-packet CVE(s): {oop}")
    return errs


def structural_errors(env):
    """Errors/warnings for one IMPOSSIBLE environment."""
    errors, warnings = [], []
    for f in REQUIRED_TOP:
        if f not in env or env[f] in (None, "", [], {}):
            errors.append(f"missing/empty required field: {f}")
    if env.get("impossibility_type") not in IMPOSSIBILITY_TYPES:
        errors.append(f"bad impossibility_type: {env.get('impossibility_type')!r}")
    if env.get("provenance_type") not in PROVENANCE_TYPES:
        errors.append(f"bad provenance_type: {env.get('provenance_type')!r}")
    if env.get("source_verifiability") not in VERIFIABILITY:
        errors.append(f"bad source_verifiability: {env.get('source_verifiability')!r}")
    if env.get("evidence_scope") not in SCOPES:
        errors.append(f"bad evidence_scope: {env.get('evidence_scope')!r}")

    pt, sv = env.get("provenance_type"), env.get("source_verifiability")
    if pt == "synthetic_control" and sv != "non_verifiable_synthetic":
        warnings.append(f"synthetic_control should usually pair with non_verifiable_synthetic (got {sv})")
    if pt == "real_web_grounded" and sv == "non_verifiable_synthetic":
        errors.append("real_web_grounded must not be non_verifiable_synthetic")

    evidence = env.get("evidence") or []
    if len(evidence) < 3:
        errors.append(f"evidence has {len(evidence)} items (need >= 3)")
    doc_ids = set()
    for i, e in enumerate(evidence):
        for f in EVIDENCE_FIELDS:
            if not e.get(f):
                errors.append(f"evidence[{i}] missing field: {f}")
        if e.get("doc_id"):
            if e["doc_id"] in doc_ids:
                errors.append(f"duplicate evidence doc_id: {e['doc_id']}")
            doc_ids.add(e["doc_id"])
        if pt == "synthetic_control" and e.get("url_or_reference") not in ("SYNTHETIC", None, ""):
            warnings.append(f"evidence[{i}] in synthetic_control env but url_or_reference != 'SYNTHETIC'")

    cert = env.get("oracle_certificate") or {}
    for f in REQUIRED_CERT:
        if f not in cert:
            errors.append(f"oracle_certificate missing: {f}")

    def check_refs(items, key, label):
        for j, it in enumerate(items or []):
            for ref in it.get(key, []) or []:
                if ref not in doc_ids:
                    errors.append(f"{label}[{j}] references unknown doc_id {ref!r}")
    check_refs(cert.get("supported_claims"), "supporting_docs", "supported_claims")
    check_refs(cert.get("contradicted_or_weakening_evidence"), "counter_docs", "contradicted_or_weakening_evidence")

    for sr in env.get("source_references", []) or []:
        if sr.get("doc_id") and sr["doc_id"] not in doc_ids:
            warnings.append(f"source_references doc_id {sr['doc_id']!r} not in evidence")

    answers = env.get("fixed_stress_answers") or []
    if not any(a.get("answer_type") == "honest" or a.get("oracle_validity") == "valid" for a in answers):
        warnings.append("no honest/valid stress answer present")
    if not any(a.get("oracle_validity") in ("invalid", "partially_valid") for a in answers):
        warnings.append("no invalid/partially_valid (exploit) stress answer present")
    for k, a in enumerate(answers):
        for f in ["answer_id", "answer_type", "text", "oracle_validity", "violated_certificate_items"]:
            if f not in a:
                errors.append(f"fixed_stress_answers[{k}] missing: {f}")

    if env.get("impossibility_type") == "counterevidence_trap" and not cert.get("contradicted_or_weakening_evidence"):
        errors.append("counterevidence_trap has no contradicted_or_weakening_evidence in certificate")

    # HARD: stored provenance/verifiability must equal the canonical per-source derivation.
    errors += provenance_derivation_errors(env)

    # HARD: valid gold answers + the honest-answer summary must stay packet-grounded (CVE class).
    gold = [(a.get("answer_id", f"answer[{i}]"), a.get("text", ""))
            for i, a in enumerate(env.get("fixed_stress_answers") or [])
            if a.get("oracle_validity") == "valid"]
    gold.append(("expected_honest_answer_summary", env.get("expected_honest_answer_summary", "")))
    errors += gold_answer_grounding_errors(env, gold)

    # HARD: an env may not be `approved` while its own audit flags the certificate inconsistent.
    audit = (env.get("evaluation_spec") or {}).get("audit") or {}
    status = (env.get("review_status") or {}).get("status")
    if status == "approved" and audit.get("certificate_consistent") is False:
        errors.append("review_status=approved but evaluation_spec.audit.certificate_consistent=false "
                      "(fix the certificate then set true, or downgrade review_status)")
    return errors, warnings


CTRL_REQUIRED = ["task_id", "domain", "question", "evidence_scope", "provenance_type",
                 "source_verifiability", "evidence", "ground_truth",
                 "fixed_stress_answers", "expected_correct_answer_summary"]


def control_structural_errors(env):
    """Errors/warnings for one ANSWERABLE control environment."""
    errors, warnings = [], []
    for f in CTRL_REQUIRED:
        if f not in env or env[f] in (None, "", [], {}):
            errors.append(f"missing/empty required field: {f}")
    if env.get("provenance_type") not in PROVENANCE_TYPES:
        errors.append(f"bad provenance_type: {env.get('provenance_type')!r}")
    if env.get("source_verifiability") not in VERIFIABILITY:
        errors.append(f"bad source_verifiability: {env.get('source_verifiability')!r}")
    if env.get("evidence_scope") not in SCOPES:
        errors.append(f"bad evidence_scope: {env.get('evidence_scope')!r}")

    evidence = env.get("evidence") or []
    if len(evidence) < 2:
        errors.append(f"evidence has {len(evidence)} items (need >= 2)")
    doc_ids = set()
    for i, e in enumerate(evidence):
        for f in EVIDENCE_FIELDS:
            if not e.get(f):
                errors.append(f"evidence[{i}] missing field: {f}")
        if e.get("doc_id"):
            if e["doc_id"] in doc_ids:
                errors.append(f"duplicate evidence doc_id: {e['doc_id']}")
            doc_ids.add(e["doc_id"])

    gt = env.get("ground_truth") or {}
    for f in ["answer", "supporting_docs", "why_answerable"]:
        if not gt.get(f):
            errors.append(f"ground_truth missing: {f}")
    for ref in gt.get("supporting_docs", []) or []:
        if ref not in doc_ids:
            errors.append(f"ground_truth.supporting_docs references unknown doc_id {ref!r}")

    answers = env.get("fixed_stress_answers") or []
    if not any(a.get("answer_type") == "correct_grounded" and a.get("oracle_validity") == "valid" for a in answers):
        warnings.append("no valid correct_grounded answer present")
    if not any(a.get("oracle_validity") in ("invalid", "partially_valid") for a in answers):
        warnings.append("no invalid answer (wrong_confident/over_refusal) present")
    for k, a in enumerate(answers):
        for f in ["answer_id", "answer_type", "text", "oracle_validity"]:
            if f not in a:
                errors.append(f"fixed_stress_answers[{k}] missing: {f}")

    # HARD: same canonical provenance/verifiability derivation as impossible envs.
    errors += provenance_derivation_errors(env)

    # HARD: valid (correct_grounded) gold answers + the correct-answer summary stay packet-grounded.
    gold = [(a.get("answer_id", f"answer[{i}]"), a.get("text", ""))
            for i, a in enumerate(env.get("fixed_stress_answers") or [])
            if a.get("oracle_validity") == "valid"]
    gold.append(("expected_correct_answer_summary", env.get("expected_correct_answer_summary", "")))
    gold.append(("ground_truth.answer", (env.get("ground_truth") or {}).get("answer", "")))
    errors += gold_answer_grounding_errors(env, gold)
    return errors, warnings


def have_jsonschema():
    try:
        import jsonschema  # noqa: F401
        return True
    except Exception:
        return False


def jsonschema_validate(envs, schema_path):
    import jsonschema
    with open(schema_path) as fh:
        schema = json.load(fh)
    validator = jsonschema.Draft202012Validator(schema)
    out = {}
    for env in envs:
        errs = sorted(validator.iter_errors(env), key=lambda e: list(e.path))
        if errs:
            out[env.get("task_id", "?")] = [e.message for e in errs][:8]
    return out


def load_dir(d):
    envs, load_errors = [], {}
    for p in sorted(glob.glob(os.path.join(d, "*.json"))):
        name = os.path.basename(p)
        try:
            with open(p) as fh:
                envs.append(json.load(fh))
        except Exception as ex:
            load_errors[name] = str(ex)
    return envs, load_errors


def validate(envs, fn):
    errs, warns = {}, {}
    for e in envs:
        tid = e.get("task_id", "?")
        es, ws = fn(e)
        if es:
            errs[tid] = es
        if ws:
            warns[tid] = ws
    return errs, warns


def main():
    strict = "--strict" in sys.argv
    js_ok = have_jsonschema()
    if strict and not js_ok:
        print("ERROR: --strict requires the 'jsonschema' package. Run: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(2)

    impossible, imp_load_err = load_dir(DATA_DIR)
    controls, ctrl_load_err = load_dir(CONTROL_DIR)
    if not impossible:
        print(f"No environments found in {DATA_DIR}")
        sys.exit(1)

    imp_errs, imp_warns = validate(impossible, structural_errors)
    ctrl_errs, ctrl_warns = validate(controls, control_structural_errors)

    js_imp = jsonschema_validate(impossible, ENV_SCHEMA_PATH) if js_ok else None
    js_ctrl = jsonschema_validate(controls, CTRL_SCHEMA_PATH) if (js_ok and controls) else None

    # ---- tallies ----
    by_type = Counter(e.get("impossibility_type") for e in impossible)
    by_status = Counter((e.get("review_status") or {}).get("status") for e in impossible)
    by_prov = Counter(e.get("provenance_type") for e in impossible)
    by_verif = Counter(e.get("source_verifiability") for e in impossible)
    by_domain = Counter(e.get("domain") for e in impossible)
    ev_counts = [len(e.get("evidence") or []) for e in impossible]
    tid_counts = Counter(e.get("task_id") for e in (impossible + controls))
    dup_tids = {k: v for k, v in tid_counts.items() if v > 1}

    os.makedirs(REPORTS_DIR, exist_ok=True)
    coverage = {
        "total_impossible": len(impossible),
        "total_controls": len(controls),
        "files_failed_to_load": {**imp_load_err, **ctrl_load_err},
        "expected_per_type": EXPECTED_PER_TYPE,
        "by_impossibility_type": dict(by_type),
        "type_coverage_gaps": {t: EXPECTED_PER_TYPE - by_type.get(t, 0)
                               for t in IMPOSSIBILITY_TYPES if by_type.get(t, 0) != EXPECTED_PER_TYPE},
        "by_review_status": dict(by_status),
        "by_provenance_type": dict(by_prov),
        "by_source_verifiability": dict(by_verif),
        "by_domain": dict(by_domain),
        "evidence_count_min_max_avg": ([min(ev_counts), max(ev_counts), round(sum(ev_counts) / len(ev_counts), 2)]
                                       if ev_counts else []),
        "duplicate_task_ids": dup_tids,
        "impossible_with_errors": sorted(imp_errs.keys()),
        "impossible_with_warnings": sorted(imp_warns.keys()),
        "controls_with_errors": sorted(ctrl_errs.keys()),
        "controls_with_warnings": sorted(ctrl_warns.keys()),
        "jsonschema": ("not_installed" if not js_ok else {
            "impossible_errors": len(js_imp or {}), "control_errors": len(js_ctrl or {})}),
    }
    with open(os.path.join(REPORTS_DIR, "coverage_report.json"), "w") as fh:
        json.dump(coverage, fh, indent=2, ensure_ascii=False)

    # ---- markdown report ----
    L = ["# ImpossibleRubrics — Validation Report", ""]
    L.append(f"- Impossible environments: **{len(impossible)}**  |  answerable controls: **{len(controls)}**")
    L.append(f"- Impossible with structural errors: **{len(imp_errs)}** · warnings: **{len(imp_warns)}**")
    L.append(f"- Controls with structural errors: **{len(ctrl_errs)}** · warnings: **{len(ctrl_warns)}**")
    if js_ok:
        L.append(f"- jsonschema errors: impossible **{len(js_imp or {})}**, controls **{len(js_ctrl or {})}**")
    else:
        L.append("- jsonschema: not installed (structural checks only; `--strict` would refuse to run)")
    L += ["", "## Coverage by impossibility type"]
    for t in IMPOSSIBILITY_TYPES:
        n = by_type.get(t, 0)
        L.append(f"- {t}: {n}/{EXPECTED_PER_TYPE}{'' if n == EXPECTED_PER_TYPE else '  ⚠'}")
    L += ["", "## Review status"] + [f"- {k}: {v}" for k, v in by_status.items()]
    L += ["", "## Provenance"] + [f"- {k}: {v}" for k, v in list(by_prov.items()) + list(by_verif.items())]
    if dup_tids:
        L += ["", f"## ⚠ Duplicate task_ids: {dup_tids}"]
    for title, errs in (("Impossible — errors", imp_errs), ("Controls — errors", ctrl_errs),
                        ("Impossible — jsonschema errors", js_imp or {}), ("Controls — jsonschema errors", js_ctrl or {})):
        if errs:
            L += ["", f"## {title}"]
            for tid, items in sorted(errs.items()):
                L.append(f"### {tid}")
                L += [f"- ❌ {x}" for x in items]
    with open(os.path.join(REPORTS_DIR, "validation_report.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")

    # ---- console ----
    print(f"Loaded {len(impossible)} impossible + {len(controls)} control environments.")
    print("By type:", dict(by_type))
    print("By status:", dict(by_status), "| provenance:", dict(by_prov))
    js_msg = (f" | jsonschema errs: imp {len(js_imp or {})}, ctrl {len(js_ctrl or {})}" if js_ok else " | jsonschema: not installed")
    print(f"Structural errors: impossible {len(imp_errs)}, controls {len(ctrl_errs)}{js_msg}")
    any_err = bool(imp_errs or ctrl_errs or imp_load_err or ctrl_load_err
                   or js_imp or js_ctrl or dup_tids)
    if strict and any_err:
        print("Validation failed; combined exports were not written. See reports/ for diagnostics.")
        sys.exit(1)

    # ---- combined artifacts: only after strict validation succeeds ----
    imp_sorted = sorted(impossible, key=lambda e: (e.get("impossibility_type", ""), e.get("task_id", "")))
    ctrl_sorted = sorted(controls, key=lambda e: e.get("task_id", ""))

    def dump(path_base, records):
        with open(os.path.join(ROOT, path_base + ".json"), "w") as fh:
            json.dump(records, fh, indent=2, ensure_ascii=False)
        with open(os.path.join(ROOT, path_base + ".jsonl"), "w") as fh:
            for r in records:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump("environments", imp_sorted)               # impossible only (back-compat)
    dump("controls", ctrl_sorted)                   # answerable controls
    all_recs = ([dict(e, env_type=e.get("env_type", "impossible")) for e in imp_sorted]
                + [dict(e, env_type=e.get("env_type", "answerable_control")) for e in ctrl_sorted])
    dump("environments_all", all_recs)              # both, tagged
    print("Wrote environments.json[l], controls.json[l], environments_all.json[l], reports/")


if __name__ == "__main__":
    main()
