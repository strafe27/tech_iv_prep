import json
import paths
import constants
import llm_client


def run():
    brief = json.loads(paths.PRODUCT_BRIEF.read_text())["product_brief"]
    variants_data = json.loads(paths.COPY_VARIANTS.read_text())

    variants = variants_data["variants"]
    constraints = brief["compliance_constraints"]
    constraints_quoted = "\n".join(f'{i+1}. "{c}"' for i, c in enumerate(constraints))
    variants_desc = "\n".join(
        f'- {v["variant_id"]} ({v["variant_type"]}): "{v["text"]}"'
        for v in variants
    )

    prompt = f"""You are a compliance officer reviewing marketing copy for a financial trading product.

COMPLIANCE RULES (apply exactly as stated — these come directly from the product brief):
{constraints_quoted}

VARIANTS TO AUDIT:
{variants_desc}

Audit every variant against all compliance rules.

Severity definitions:
- "blocker": directly violates a rule — must not be used
- "warning": borderline or could be misread as violating a rule — needs human review
- "clear": no compliance issues detected

Return JSON with one entry per variant:
{{
  "audit": [
    {{
      "variant_id": "headline_empowerment",
      "variant_text": "the exact variant text",
      "status": "clear",
      "severity": "clear",
      "rule_violated": null,
      "suggested_fix": null
    }}
  ]
}}

For blockers and warnings, populate rule_violated with the exact rule text and suggested_fix with a compliant rewrite."""

    result = llm_client.call(
        stage="compliance_audit",
        prompt=prompt,
        input_artifacts=["product_brief.json", "artifacts/stage_3/copy_variants.json"],
        output_artifact="artifacts/stage_5/compliance_audit.json",
    )

    audit = result.get("audit", [])

    audited_ids = {a["variant_id"] for a in audit}
    all_ids = {v["variant_id"] for v in variants}
    missing = all_ids - audited_ids
    if missing:
        raise RuntimeError(f"Compliance audit missing variants: {missing}")

    for a in audit:
        if a["severity"] not in constants.COMPLIANCE_SEVERITIES:
            raise RuntimeError(f"Invalid severity '{a['severity']}' for variant '{a['variant_id']}'")

    blockers = [a for a in audit if a["severity"] == "blocker"]
    warnings = [a for a in audit if a["severity"] == "warning"]
    clears = [a for a in audit if a["severity"] == "clear"]

    paths.COMPLIANCE_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    paths.COMPLIANCE_AUDIT.write_text(json.dumps(result, indent=2))
    print(f"  Compliance: {len(clears)} clear, {len(warnings)} warning, {len(blockers)} blocker")
