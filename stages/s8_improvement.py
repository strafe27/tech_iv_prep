import json
import paths
import constants
import llm_client


def run():
    scores_data = json.loads(paths.VARIANT_SCORES.read_text())
    audit_data = json.loads(paths.COMPLIANCE_AUDIT.read_text())
    rubric = json.loads(paths.APPROVED_RUBRIC.read_text())
    variants_data = json.loads(paths.COPY_VARIANTS.read_text())
    brief = json.loads(paths.PRODUCT_BRIEF.read_text())["product_brief"]

    audit = {a["variant_id"]: a for a in audit_data["audit"]}
    variants = {v["variant_id"]: v for v in variants_data["variants"]}
    scores = scores_data["scores"]
    dims = rubric["dimensions"]
    rubric_weights = {d["dimension_id"]: d["weight"] for d in dims}
    dim_lookup = {d["dimension_id"]: d["name"] for d in dims}

    eligible_headline_ids = [
        v["variant_id"] for v in variants_data["variants"]
        if v["variant_type"] == "headline" and audit.get(v["variant_id"], {}).get("severity") != "blocker"
    ]
    if not eligible_headline_ids:
        print("  No eligible headlines to improve.")
        return

    def avg_score(vid: str) -> float:
        relevant = [s["total_weighted_score"] for s in scores if s["variant_id"] == vid]
        return sum(relevant) / len(relevant) if relevant else 0.0

    target_id = min(eligible_headline_ids, key=avg_score)
    target_variant = variants[target_id]
    target_scores = [s for s in scores if s["variant_id"] == target_id]
    original_avg = avg_score(target_id)

    # Find weak dimensions (avg score below 6)
    dim_avgs: dict[str, list] = {}
    for s in target_scores:
        for ds in s["dimension_scores"]:
            dim_avgs.setdefault(ds["dimension_id"], []).append(ds["score"])
    dim_avgs_final = {did: sum(v) / len(v) for did, v in dim_avgs.items()}
    weak_dims = {did: avg for did, avg in dim_avgs_final.items() if avg < 6}

    weak_desc = "\n".join(
        f"- {dim_lookup.get(did, did)} (avg score: {avg:.1f})" for did, avg in weak_dims.items()
    )
    rationale_desc = "\n".join(
        f"  [{s['persona']}] " + "; ".join(
            f"{dim_lookup.get(ds['dimension_id'], ds['dimension_id'])}: {ds['score']} — {ds['rationale']}"
            for ds in s["dimension_scores"] if ds["dimension_id"] in weak_dims
        )
        for s in target_scores
    )
    constraints = "\n".join(f"- {c}" for c in brief["compliance_constraints"])

    # LLM call 1: generate improved headline
    prompt1 = f"""You are a senior marketing copywriter improving a low-scoring headline.

Original headline: "{target_variant["text"]}"
Angle: {target_variant["angle"]}

Weak dimensions needing improvement:
{weak_desc}

Scoring rationale for weak dimensions:
{rationale_desc}

Compliance constraints (must not violate):
{constraints}

Produce an improved headline that addresses the weak dimensions while keeping the same creative angle and staying compliant.

Return JSON:
{{
  "improved_text": "the improved headline",
  "changes_made": "brief explanation of what was changed and why",
  "targeted_dimensions": ["dimension_id_1"]
}}"""

    improvement = llm_client.call(
        stage="variant_improvement",
        prompt=prompt1,
        input_artifacts=[
            "artifacts/stage_4/variant_scores.json",
            "artifacts/stage_5/compliance_audit.json",
            "artifacts/stage_2/approved_rubric.json",
        ],
        output_artifact="artifacts/stage_8/variant_improvement.json",
    )

    improved_text = improvement.get("improved_text", "")
    personas = [brief["primary_audience"]["persona"], brief["secondary_audience"]["persona"]]
    dims_desc = "\n".join(
        f"- {d['dimension_id']} ({d['name']}, weight {d['weight']}): score 10 means {d['description_of_10']}"
        for d in dims
    )
    persona_desc = "\n".join(f"- {p}" for p in personas)

    # LLM call 2: re-score
    prompt2 = f"""Score this improved headline against the rubric for both personas.

Improved headline: "{improved_text}"
Angle: {target_variant["angle"]}

RUBRIC:
{dims_desc}

PERSONAS:
{persona_desc}

Return JSON:
{{
  "scores": [
    {{
      "variant_id": "{target_id}_improved",
      "persona": "persona name",
      "dimension_scores": [
        {{"dimension_id": "...", "score": 8, "rationale": "..."}}
      ]
    }}
  ]
}}"""

    rescore = llm_client.call(
        stage="variant_improvement_scoring",
        prompt=prompt2,
        input_artifacts=["artifacts/stage_2/approved_rubric.json"],
        output_artifact="artifacts/stage_8/variant_improvement.json",
    )

    improved_scores = rescore.get("scores", [])
    for s in improved_scores:
        s["total_weighted_score"] = round(
            sum(ds["score"] * rubric_weights.get(ds["dimension_id"], 0) for ds in s["dimension_scores"]), 4
        )
    improved_avg = sum(s["total_weighted_score"] for s in improved_scores) / len(improved_scores) if improved_scores else 0.0

    # LLM call 3: re-audit
    constraints_quoted = "\n".join(f'{i+1}. "{c}"' for i, c in enumerate(brief["compliance_constraints"]))
    improved_variant_id = f"{target_id}_improved"
    allowed_severities = ", ".join(f'"{s}"' for s in constants.COMPLIANCE_SEVERITIES)
    prompt3 = f"""Audit this headline for financial marketing compliance.

Headline: "{improved_text}"

COMPLIANCE RULES:
{constraints_quoted}

Severity must be one of these exact values only: {allowed_severities}
- "blocker": directly violates a rule — must not be used
- "warning": borderline or could be misread as violating a rule
- "clear": no compliance issues detected

Return JSON with variant_id set to exactly "{improved_variant_id}":
{{
  "audit": [
    {{
      "variant_id": "{improved_variant_id}",
      "variant_text": "{improved_text}",
      "status": "clear",
      "severity": "clear",
      "rule_violated": null,
      "suggested_fix": null
    }}
  ]
}}"""

    reaudit_result = llm_client.call(
        stage="variant_improvement_compliance",
        prompt=prompt3,
        input_artifacts=["product_brief.json"],
        output_artifact="artifacts/stage_8/variant_improvement.json",
    )

    reaudit = reaudit_result.get("audit", [{}])[0]
    reaudit["variant_id"] = improved_variant_id
    if reaudit.get("severity") not in constants.COMPLIANCE_SEVERITIES:
        reaudit["severity"] = "warning"

    is_improvement = improved_avg > original_avg and reaudit.get("severity") != "blocker"

    output = {
        "original_variant_id": target_id,
        "original_text": target_variant["text"],
        "original_avg_score": round(original_avg, 4),
        "weak_dimensions": [{"dimension_id": did, "avg_score": round(avg, 4)} for did, avg in weak_dims.items()],
        "changes_made": improvement.get("changes_made", ""),
        "improved_text": improved_text,
        "improved_avg_score": round(improved_avg, 4),
        "improved_scores": improved_scores,
        "improved_compliance": reaudit,
        "is_improvement": is_improvement,
    }

    paths.VARIANT_IMPROVEMENT.parent.mkdir(parents=True, exist_ok=True)
    paths.VARIANT_IMPROVEMENT.write_text(json.dumps(output, indent=2))
    delta = improved_avg - original_avg
    print(f"  Improved '{target_id}': {original_avg:.2f} -> {improved_avg:.2f} (delta: {delta:+.2f}, is_improvement: {is_improvement})")
