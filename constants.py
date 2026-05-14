ANGLES = [
    "fear_of_missing_out",
    "social_proof",
    "benefit_led",
    "curiosity",
    "empowerment",
    "loss_aversion",
]

COMPLIANCE_SEVERITIES = ["blocker", "warning", "clear"]

RECOMMENDATION_STATUSES = ["eligible", "excluded_compliance_blocker", "needs_review"]

PIPELINE_STAGES = [
    "INIT",
    "PRODUCT_BRIEF_LOADED",
    "RUBRIC_DRAFTED",
    "RUBRIC_APPROVED",
    "VARIANTS_GENERATED",
    "VARIANTS_SCORED",
    "COMPLIANCE_AUDITED",
    "BLOCKERS_EXCLUDED",
    "RECOMMENDATIONS_SELECTED",
    "COPY_DECK_GENERATED",
    "OPTIONAL_ANALYSES_GENERATED",
    "VALIDATION_COMPLETE",
    "RESULTS_FINALISED",
]

REQUIRED_LLM_STAGES = [
    "rubric_design",
    "variant_generation",
    "persona_scoring",
    "compliance_audit",
    "recommendation_generation",
]
