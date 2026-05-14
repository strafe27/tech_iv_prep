import json
import sys

import constants
import paths


def main():
    failures: list[str] = []

    def ok(name: str):
        print(f"  PASS  {name}")

    def fail(name: str, detail: str = ""):
        msg = f"  FAIL  {name}" + (f" — {detail}" if detail else "")
        failures.append(msg)
        print(msg)

    def check_file_exists(path, label: str) -> bool:
        if path.exists():
            ok(f"{label} exists")
            return True
        fail(f"{label} exists", f"{path} not found")
        return False

    def load_json(path, label: str):
        try:
            data = json.loads(path.read_text())
            ok(f"{label} valid JSON")
            return data
        except json.JSONDecodeError as e:
            fail(f"{label} valid JSON", str(e))
            return None

    # ── Required artifacts ───────────────────────────────────────────────────

    print("\n[1] Required artifacts")
    product_brief_ok = check_file_exists(paths.PRODUCT_BRIEF, "product_brief.json")
    rubric_draft_ok = check_file_exists(paths.RUBRIC_DRAFT, "stage_1/rubric_draft.json")
    approved_rubric_ok = check_file_exists(paths.APPROVED_RUBRIC, "stage_2/approved_rubric.json")
    copy_variants_ok = check_file_exists(paths.COPY_VARIANTS, "stage_3/copy_variants.json")
    variant_scores_ok = check_file_exists(paths.VARIANT_SCORES, "stage_4/variant_scores.json")
    compliance_audit_ok = check_file_exists(paths.COMPLIANCE_AUDIT, "stage_5/compliance_audit.json")
    recommendation_json_ok = check_file_exists(paths.RECOMMENDATION_JSON, "stage_6/recommendation.json")
    recommendation_md_ok = check_file_exists(paths.RECOMMENDATION_MD, "stage_6/recommendation.md")
    llm_log_ok = check_file_exists(paths.LLM_CALLS_LOG, "llm_calls.jsonl")

    # ── JSON validity ────────────────────────────────────────────────────────

    print("\n[2] JSON validity")
    brief_data = load_json(paths.PRODUCT_BRIEF, "product_brief.json") if product_brief_ok else None
    rubric_draft = load_json(paths.RUBRIC_DRAFT, "rubric_draft.json") if rubric_draft_ok else None
    approved_rubric = load_json(paths.APPROVED_RUBRIC, "approved_rubric.json") if approved_rubric_ok else None
    copy_variants = load_json(paths.COPY_VARIANTS, "copy_variants.json") if copy_variants_ok else None
    variant_scores = load_json(paths.VARIANT_SCORES, "variant_scores.json") if variant_scores_ok else None
    compliance_audit = load_json(paths.COMPLIANCE_AUDIT, "compliance_audit.json") if compliance_audit_ok else None
    recommendation = load_json(paths.RECOMMENDATION_JSON, "recommendation.json") if recommendation_json_ok else None

    # ── Product brief ────────────────────────────────────────────────────────

    print("\n[3] Product brief")
    if brief_data:
        if "product_brief" in brief_data:
            ok("product_brief key present")
            pb = brief_data["product_brief"]
            for key in ("product", "description", "markets", "primary_audience", "secondary_audience", "compliance_constraints"):
                if key in pb:
                    ok(f"product_brief.{key} present")
                else:
                    fail(f"product_brief.{key} present")
        else:
            fail("product_brief key present")

    # ── Operator approval checkpoint ─────────────────────────────────────────

    print("\n[4] Operator approval checkpoint")
    if paths.PIPELINE_STATE.exists():
        try:
            state = json.loads(paths.PIPELINE_STATE.read_text())
            if "RUBRIC_APPROVED" in state.get("completed_stages", []):
                ok("operator approval checkpoint completed (RUBRIC_APPROVED in pipeline state)")
            else:
                fail("operator approval checkpoint completed", "RUBRIC_APPROVED not found in pipeline_state.json completed_stages")
        except json.JSONDecodeError:
            fail("operator approval checkpoint completed", "pipeline_state.json is not valid JSON")
    else:
        fail("operator approval checkpoint completed", "pipeline_state.json not found")

    # ── Rubric integrity ─────────────────────────────────────────────────────

    print("\n[5] Rubric integrity")
    for label, rubric in [("rubric_draft", rubric_draft), ("approved_rubric", approved_rubric)]:
        if rubric is None:
            continue
        dims = rubric.get("dimensions", [])
        if len(dims) == 5:
            ok(f"{label} has exactly 5 dimensions")
        else:
            fail(f"{label} has exactly 5 dimensions", f"got {len(dims)}")

        total_weight = sum(d.get("weight", 0) for d in dims)
        if abs(total_weight - 1.0) <= 0.001:
            ok(f"{label} weights sum to 1.0")
        else:
            fail(f"{label} weights sum to 1.0", f"got {total_weight:.4f}")

        required = {"dimension_id", "name", "weight", "scale", "description_of_10"}
        all_ok = True
        for d in dims:
            missing = required - d.keys()
            if missing:
                fail(f"{label} dimension fields complete", f"'{d.get('dimension_id')}' missing {missing}")
                all_ok = False
        if all_ok:
            ok(f"{label} dimension fields complete")

    # ── Variant integrity ────────────────────────────────────────────────────

    print("\n[6] Variant integrity")
    if copy_variants:
        variants = copy_variants.get("variants", [])
        headlines = [v for v in variants if v.get("variant_type") == "headline"]
        ctas = [v for v in variants if v.get("variant_type") == "cta"]
        subheadlines = [v for v in variants if v.get("variant_type") == "subheadline"]

        for label, lst, expected in [("headlines", headlines, 6), ("CTAs", ctas, 6), ("subheadlines", subheadlines, 12)]:
            if len(lst) == expected:
                ok(f"copy_variants has {expected} {label}")
            else:
                fail(f"copy_variants has {expected} {label}", f"got {len(lst)}")

        headline_angles = {v.get("angle") for v in headlines}
        cta_angles = {v.get("angle") for v in ctas}
        for angle in constants.ANGLES:
            if angle in headline_angles:
                ok(f"headline angle '{angle}' present")
            else:
                fail(f"headline angle '{angle}' present")
            if angle in cta_angles:
                ok(f"CTA angle '{angle}' present")
            else:
                fail(f"CTA angle '{angle}' present")

        required_fields = {"variant_id", "variant_type", "angle", "text", "linked_headline_id"}
        headline_ids = {v["variant_id"] for v in headlines}
        all_fields_ok = True
        all_links_ok = True
        for v in variants:
            missing = required_fields - v.keys()
            if missing:
                fail("all variants have required fields", f"'{v.get('variant_id')}' missing {missing}")
                all_fields_ok = False
            if v.get("variant_type") == "subheadline":
                if v.get("linked_headline_id") not in headline_ids:
                    fail("subheadline linked_headline_id valid", f"'{v.get('variant_id')}' links to unknown '{v.get('linked_headline_id')}'")
                    all_links_ok = False
        if all_fields_ok:
            ok("all variants have required fields")
        if all_links_ok:
            ok("all subheadline linked_headline_ids valid")

    # ── Scoring integrity ────────────────────────────────────────────────────

    print("\n[7] Scoring integrity")
    if variant_scores and approved_rubric and copy_variants and brief_data:
        scores = variant_scores.get("scores", [])
        dims = approved_rubric.get("dimensions", [])
        approved_dim_ids = {d["dimension_id"] for d in dims}
        rubric_weights = {d["dimension_id"]: d["weight"] for d in dims}

        to_score = [v for v in copy_variants.get("variants", []) if v.get("variant_type") in ("headline", "cta")]
        pb = brief_data["product_brief"]
        personas = [pb["primary_audience"]["persona"], pb["secondary_audience"]["persona"]]

        score_index = {(s["variant_id"], s["persona"]) for s in scores}
        coverage_ok = True
        for v in to_score:
            for persona in personas:
                if (v["variant_id"], persona) not in score_index:
                    fail("all variants scored for both personas", f"missing '{v['variant_id']}' / '{persona}'")
                    coverage_ok = False
        if coverage_ok:
            ok("all variants scored for both personas")

        dim_refs_ok = True
        for s in scores:
            for ds in s.get("dimension_scores", []):
                if ds["dimension_id"] not in approved_dim_ids:
                    fail("scoring uses approved rubric dimensions", f"unknown dimension_id '{ds['dimension_id']}'")
                    dim_refs_ok = False
                    break
        if dim_refs_ok:
            ok("scoring uses approved rubric dimensions")

        weight_ok = True
        for s in scores:
            expected = round(sum(
                ds["score"] * rubric_weights.get(ds["dimension_id"], 0)
                for ds in s.get("dimension_scores", [])
            ), 4)
            actual = s.get("total_weighted_score")
            if actual is None or abs(actual - expected) > 0.01:
                fail("weighted scores computed correctly", f"'{s['variant_id']}' / '{s['persona']}': expected {expected}, got {actual}")
                weight_ok = False
        if weight_ok:
            ok("weighted scores computed correctly")

    # ── Compliance integrity ─────────────────────────────────────────────────

    print("\n[8] Compliance integrity")
    if compliance_audit and copy_variants:
        audit_list = compliance_audit.get("audit", [])
        audited_ids = {a["variant_id"] for a in audit_list}
        all_variant_ids = {v["variant_id"] for v in copy_variants.get("variants", [])}

        missing = all_variant_ids - audited_ids
        if not missing:
            ok("all variants covered in compliance audit")
        else:
            fail("all variants covered in compliance audit", f"missing: {missing}")

        severity_ok = True
        for a in audit_list:
            if a.get("severity") not in constants.COMPLIANCE_SEVERITIES:
                fail("all severity values valid", f"'{a['variant_id']}' has invalid severity '{a.get('severity')}'")
                severity_ok = False
        if severity_ok:
            ok("all severity values valid")

        if brief_data:
            brief_constraints = brief_data["product_brief"].get("compliance_constraints", [])
            llm_log_path = paths.LLM_CALLS_LOG
            constraints_used = False
            if llm_log_path.exists():
                for line in llm_log_path.read_text().strip().splitlines():
                    try:
                        rec = json.loads(line)
                        if rec.get("stage") == "compliance_audit":
                            constraints_used = True
                            break
                    except json.JSONDecodeError:
                        pass
            if constraints_used and len(brief_constraints) > 0:
                ok("compliance audit references product brief constraints")
            elif not constraints_used:
                fail("compliance audit references product brief constraints", "no compliance_audit record found in llm_calls.jsonl")

    # ── Recommendation integrity ─────────────────────────────────────────────

    print("\n[9] Recommendation integrity")
    if recommendation and compliance_audit:
        audit_by_id = {a["variant_id"]: a for a in compliance_audit.get("audit", [])}

        no_blockers = True
        for rec in recommendation:
            for field in ("headline", "cta", "subheadline"):
                vid = rec.get(field, {}).get("variant_id", "")
                if audit_by_id.get(vid, {}).get("severity") == "blocker":
                    fail("no blocker variants in recommendations", f"'{vid}' is a blocker but appears in recommendation")
                    no_blockers = False
        if no_blockers:
            ok("no blocker variants in recommendations")

        required_fields = ("persona", "headline", "subheadline", "cta", "benefit_bullets", "trust_signal", "compliance_notes", "rationale")
        all_fields_ok = True
        for rec in recommendation:
            for field in required_fields:
                if not rec.get(field):
                    fail(f"recommendation has '{field}'", f"missing or empty in persona '{rec.get('persona')}'")
                    all_fields_ok = False
            bullets = rec.get("benefit_bullets", [])
            if len(bullets) < 3:
                fail("recommendation has 3 benefit bullets", f"persona '{rec.get('persona')}' has {len(bullets)}")
                all_fields_ok = False
        if all_fields_ok:
            ok("all recommendation fields present and populated")

        if len(recommendation) >= 2:
            ok("recommendations cover both personas")
        else:
            fail("recommendations cover both personas", f"only {len(recommendation)} recommendation(s)")

    # ── LLM call log integrity ───────────────────────────────────────────────

    print("\n[10] LLM call log integrity")
    if llm_log_ok:
        records = []
        try:
            for line in paths.LLM_CALLS_LOG.read_text().strip().splitlines():
                if line.strip():
                    records.append(json.loads(line))
            ok("llm_calls.jsonl parseable")
        except json.JSONDecodeError as e:
            fail("llm_calls.jsonl parseable", str(e))

        logged_stages = {r.get("stage") for r in records}
        for stage in constants.REQUIRED_LLM_STAGES:
            if stage in logged_stages:
                ok(f"LLM log has record for '{stage}'")
            else:
                fail(f"LLM log has record for '{stage}'")

        required_record_fields = {"stage", "timestamp", "provider", "model", "prompt_hash", "input_artifacts", "output_artifact"}
        fields_ok = True
        for r in records:
            missing = required_record_fields - r.keys()
            if missing:
                fail("all LLM log records have required fields", f"stage '{r.get('stage')}' missing {missing}")
                fields_ok = False
        if fields_ok:
            ok("all LLM log records have required fields")

    # ── Optional artifacts (informational) ───────────────────────────────────

    print("\n[11] Optional artifacts (informational)")
    for path, label in [
        (paths.SIMULATED_CTR, "stage_7/simulated_ctr.json"),
        (paths.VARIANT_IMPROVEMENT, "stage_8/variant_improvement.json"),
        (paths.LOCALISATION_FLAGS, "stage_9/localisation_flags.json"),
        (paths.AB_TEST_BRIEF, "stage_10/ab_test_brief.md"),
    ]:
        status = "present" if path.exists() else "absent"
        print(f"  INFO  {label}: {status}")

    # ── Result ───────────────────────────────────────────────────────────────

    print()
    if failures:
        print(f"Validation FAILED — {len(failures)} check(s) failed:")
        for f in failures:
            print(f)
        return 1
    else:
        print("Validation PASSED — all checks passed.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
