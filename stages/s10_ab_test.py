import json
import paths
import llm_client


def run():
    recommendations = json.loads(paths.RECOMMENDATION_JSON.read_text())
    brief = json.loads(paths.PRODUCT_BRIEF.read_text())["product_brief"]
    top2 = recommendations[:2]

    recs_desc = ""
    for rec in top2:
        recs_desc += f"""
Persona: {rec["persona"]}
  Headline: "{rec["headline"]["text"]}" (angle: {rec["headline"]["angle"]})
  Subheadline: "{rec["subheadline"]["text"]}"
  CTA: "{rec["cta"]["text"]}"
"""

    prompt = f"""You are a growth marketing strategist designing A/B tests for landing page copy.

CONTROL (current copy):
  Headline: "{brief["control_headline"]}"
  Subheadline: "{brief["control_subheadline"]}"
  CTA: "{brief["control_cta"]}"

VARIANTS TO TEST:
{recs_desc}

For each variant, produce a complete A/B test brief.

Return JSON:
{{
  "ab_tests": [
    {{
      "persona": "persona name",
      "hypothesis": "If we show [variant] to [persona], then [primary metric] will improve by [threshold] because [reason]",
      "control": {{"headline": "...", "subheadline": "...", "cta": "..."}},
      "variant": {{"headline": "...", "subheadline": "...", "cta": "..."}},
      "primary_metric": "...",
      "secondary_metrics": ["...", "..."],
      "sample_size_estimate": "...",
      "success_threshold": "...",
      "guardrail_metrics": ["...", "..."],
      "compliance_review_required": true
    }}
  ]
}}"""

    result = llm_client.call(
        stage="ab_test_brief",
        prompt=prompt,
        input_artifacts=["artifacts/stage_6/recommendation.json"],
        output_artifact="artifacts/stage_10/ab_test_brief.md",
    )

    ab_tests = result.get("ab_tests", [])
    lines = ["# A/B Test Briefs\n"]

    for test in ab_tests:
        ctrl = test.get("control", {})
        var = test.get("variant", {})
        lines += [
            f"---\n\n## Persona: {test.get('persona', '')}\n",
            f"**Hypothesis:** {test.get('hypothesis', '')}\n",
            "**Control:**",
            f"- Headline: {ctrl.get('headline', '')}",
            f"- Subheadline: {ctrl.get('subheadline', '')}",
            f"- CTA: {ctrl.get('cta', '')}\n",
            "**Variant:**",
            f"- Headline: {var.get('headline', '')}",
            f"- Subheadline: {var.get('subheadline', '')}",
            f"- CTA: {var.get('cta', '')}\n",
            f"**Primary Metric:** {test.get('primary_metric', '')}",
            f"**Secondary Metrics:** {', '.join(test.get('secondary_metrics', []))}",
            f"**Sample Size Estimate:** {test.get('sample_size_estimate', '')}",
            f"**Success Threshold:** {test.get('success_threshold', '')}",
            f"**Guardrail Metrics:** {', '.join(test.get('guardrail_metrics', []))}",
            f"**Compliance Review Required:** {test.get('compliance_review_required', True)}\n",
        ]

    paths.AB_TEST_BRIEF.parent.mkdir(parents=True, exist_ok=True)
    paths.AB_TEST_BRIEF.write_text("\n".join(lines))
    print(f"  A/B test briefs generated for {len(ab_tests)} personas")
