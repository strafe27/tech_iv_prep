import json
import os
import sys

from dotenv import load_dotenv

import paths
import validate
from stages import (
    s1_rubric_design,
    s2_approval,
    s3_variant_gen,
    s4_scoring,
    s5_compliance,
    s6_recommendations,
    s7_simulated_ctr,
    s8_improvement,
    s9_localisation,
    s10_ab_test,
)


def _load_state() -> dict:
    if paths.PIPELINE_STATE.exists():
        return json.loads(paths.PIPELINE_STATE.read_text())
    return {"current_stage": "INIT", "completed_stages": []}


def _save_state(state: dict):
    paths.PIPELINE_STATE.write_text(json.dumps(state, indent=2))


def _advance(stage: str):
    state = _load_state()
    if stage not in state["completed_stages"]:
        state["completed_stages"].append(stage)
    state["current_stage"] = stage
    _save_state(state)


def _is_complete(stage: str) -> bool:
    return stage in _load_state()["completed_stages"]


def _init():
    load_dotenv()

    if not os.getenv("gemini_api"):
        print("Error: gemini_api not set. Check .env file.")
        sys.exit(1)

    paths.ARTIFACTS.mkdir(exist_ok=True)

    if not paths.PRODUCT_BRIEF.exists():
        print(f"Error: {paths.PRODUCT_BRIEF} not found.")
        sys.exit(1)

    try:
        data = json.loads(paths.PRODUCT_BRIEF.read_text())
        if "product_brief" not in data:
            raise ValueError("Missing 'product_brief' key")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: Invalid product_brief.json — {e}")
        sys.exit(1)

    if not paths.PIPELINE_STATE.exists():
        _save_state({"current_stage": "INIT", "completed_stages": []})

    _advance("PRODUCT_BRIEF_LOADED")


def run():
    print("=== Copy Testing Pipeline ===")
    _init()
    print("Initialized.\n")

    # Stages 1 + 2: rubric design with operator approval loop
    if not _is_complete("RUBRIC_APPROVED"):
        if not _is_complete("RUBRIC_DRAFTED"):
            print("[Stage 1] Designing rubric...")
            s1_rubric_design.run()
            _advance("RUBRIC_DRAFTED")

        while True:
            print("\n[Stage 2] Operator rubric approval")
            result = s2_approval.run()
            if result == "approved":
                _advance("RUBRIC_APPROVED")
                break
            print("\n[Stage 1] Regenerating rubric...")
            s1_rubric_design.run()
            _advance("RUBRIC_DRAFTED")
    else:
        print("[Stage 1+2] Rubric already approved, skipping.")

    # Stage 3: variant generation
    if not _is_complete("VARIANTS_GENERATED"):
        print("\n[Stage 3] Generating copy variants...")
        s3_variant_gen.run()
        _advance("VARIANTS_GENERATED")
    else:
        print("[Stage 3] Variants already generated, skipping.")

    # Stage 4: persona scoring
    if not _is_complete("VARIANTS_SCORED"):
        print("\n[Stage 4] Scoring variants by persona...")
        s4_scoring.run()
        _advance("VARIANTS_SCORED")
    else:
        print("[Stage 4] Scoring already done, skipping.")

    # Stage 5: compliance audit
    if not _is_complete("COMPLIANCE_AUDITED"):
        print("\n[Stage 5] Running compliance audit...")
        s5_compliance.run()
        _advance("COMPLIANCE_AUDITED")
    else:
        print("[Stage 5] Compliance audit already done, skipping.")

    # Stage 6: recommendations
    if not _is_complete("COPY_DECK_GENERATED"):
        print("\n[Stage 6] Building recommendations...")
        s6_recommendations.run()
        _advance("BLOCKERS_EXCLUDED")
        _advance("RECOMMENDATIONS_SELECTED")
        _advance("COPY_DECK_GENERATED")
    else:
        print("[Stage 6] Recommendations already generated, skipping.")

    # Optional stages — a failure warns but does not stop the pipeline
    print("\n--- Optional Analyses ---")
    for label, module, stage_key in [
        ("[Stage 7] Simulated CTR ranking", s7_simulated_ctr, "SIMULATED_CTR_DONE"),
        ("[Stage 8] Variant improvement loop", s8_improvement, "IMPROVEMENT_DONE"),
        ("[Stage 9] Localisation review", s9_localisation, "LOCALISATION_DONE"),
        ("[Stage 10] A/B test brief", s10_ab_test, "AB_TEST_DONE"),
    ]:
        if not _is_complete(stage_key):
            print(f"\n{label}...")
            try:
                module.run()
                _advance(stage_key)
            except Exception as e:
                print(f"  Warning: {label} failed — {e}")
        else:
            print(f"{label} already done, skipping.")

    _advance("OPTIONAL_ANALYSES_GENERATED")

    print("\n--- Validation ---")
    exit_code = validate.main()
    if exit_code != 0:
        print("\nPipeline aborted: validation failed. Fix the issues above and re-run.")
        sys.exit(1)
    _advance("VALIDATION_COMPLETE")
    _advance("RESULTS_FINALISED")

    print("\n=== Pipeline complete ===")
    print(f"Artifacts: {paths.ARTIFACTS}")
    print(f"To rerun delete artifacts/pipeline_state.json")


if __name__ == "__main__":
    run()
