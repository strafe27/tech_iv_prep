from pathlib import Path

ROOT = Path(__file__).parent
ARTIFACTS = ROOT / "artifacts"

PRODUCT_BRIEF = ROOT / "product_brief.json"
PIPELINE_STATE = ARTIFACTS / "pipeline_state.json"
LLM_CALLS_LOG = ARTIFACTS / "llm_calls.jsonl"

RUBRIC_DRAFT = ARTIFACTS / "stage_1" / "rubric_draft.json"
APPROVED_RUBRIC = ARTIFACTS / "stage_2" / "approved_rubric.json"
COPY_VARIANTS = ARTIFACTS / "stage_3" / "copy_variants.json"
VARIANT_SCORES = ARTIFACTS / "stage_4" / "variant_scores.json"
COMPLIANCE_AUDIT = ARTIFACTS / "stage_5" / "compliance_audit.json"
RECOMMENDATION_JSON = ARTIFACTS / "stage_6" / "recommendation.json"
RECOMMENDATION_MD = ARTIFACTS / "stage_6" / "recommendation.md"
SIMULATED_CTR = ARTIFACTS / "stage_7" / "simulated_ctr.json"
VARIANT_IMPROVEMENT = ARTIFACTS / "stage_8" / "variant_improvement.json"
LOCALISATION_FLAGS = ARTIFACTS / "stage_9" / "localisation_flags.json"
AB_TEST_BRIEF = ARTIFACTS / "stage_10" / "ab_test_brief.md"
