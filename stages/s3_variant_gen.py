import json
import paths
import constants
import llm_client


def run():
    brief = json.loads(paths.PRODUCT_BRIEF.read_text())["product_brief"]

    angle_list = "\n".join(f"- {a}" for a in constants.ANGLES)
    constraints = "\n".join(f"- {c}" for c in brief["compliance_constraints"])
    headline_ids = ", ".join(f"headline_{a}" for a in constants.ANGLES)
    cta_ids = ", ".join(f"cta_{a}" for a in constants.ANGLES)
    sub_ids = ", ".join(f"subheadline_{a}_1 / subheadline_{a}_2" for a in constants.ANGLES)

    prompt = f"""You are a marketing copywriter. Generate copy variants for this product.

Product: {brief["product"]}
Description: {brief["description"]}
Markets: {", ".join(brief["markets"])}
Tone: {brief["tone"]}

Primary audience: {brief["primary_audience"]["persona"]}
Traits: {", ".join(brief["primary_audience"]["traits"])}

Secondary audience: {brief["secondary_audience"]["persona"]}
Traits: {", ".join(brief["secondary_audience"]["traits"])}

Compliance constraints (all variants must comply):
{constraints}

Generate copy using these exact creative angles (one variant per angle per type):
{angle_list}

Produce:
1. 6 headline variants (one per angle)
2. 6 CTA variants (one per angle)
3. 12 subheadline variants (2 per angle, each linked to its headline)

Use these exact variant_id values:
Headlines: {headline_ids}
CTAs: {cta_ids}
Subheadlines: {sub_ids}

Rules:
- Stay strictly grounded in the product brief — no invented features or unsupported claims
- Do not imply guaranteed returns or risk-free trading
- Do not claim superiority over competitors without substantiation
- Do not use urgency language that could be construed as pressure selling
- If making performance claims, imply that trading involves risk
- Subheadlines must expand on or complement their linked headline

Return JSON:
{{
  "variants": [
    {{
      "variant_id": "headline_empowerment",
      "variant_type": "headline",
      "angle": "empowerment",
      "text": "...",
      "linked_headline_id": null
    }},
    {{
      "variant_id": "subheadline_empowerment_1",
      "variant_type": "subheadline",
      "angle": "empowerment",
      "text": "...",
      "linked_headline_id": "headline_empowerment"
    }}
  ]
}}

For subheadlines, set linked_headline_id to the corresponding headline variant_id.
For headlines and CTAs, set linked_headline_id to null."""

    result = llm_client.call(
        stage="variant_generation",
        prompt=prompt,
        input_artifacts=["product_brief.json", "artifacts/stage_2/approved_rubric.json"],
        output_artifact="artifacts/stage_3/copy_variants.json",
    )

    variants = result.get("variants", [])
    headlines = [v for v in variants if v["variant_type"] == "headline"]
    ctas = [v for v in variants if v["variant_type"] == "cta"]
    subheadlines = [v for v in variants if v["variant_type"] == "subheadline"]

    if len(headlines) != 6:
        raise RuntimeError(f"Expected 6 headlines, got {len(headlines)}")
    if len(ctas) != 6:
        raise RuntimeError(f"Expected 6 CTAs, got {len(ctas)}")
    if len(subheadlines) != 12:
        raise RuntimeError(f"Expected 12 subheadlines, got {len(subheadlines)}")

    headline_angles = {v["angle"] for v in headlines}
    cta_angles = {v["angle"] for v in ctas}
    for angle in constants.ANGLES:
        if angle not in headline_angles:
            raise RuntimeError(f"Missing headline for angle: {angle}")
        if angle not in cta_angles:
            raise RuntimeError(f"Missing CTA for angle: {angle}")

    required = {"variant_id", "variant_type", "angle", "text", "linked_headline_id"}
    for v in variants:
        missing = required - v.keys()
        if missing:
            raise RuntimeError(f"Variant '{v.get('variant_id')}' missing fields: {missing}")

    paths.COPY_VARIANTS.parent.mkdir(parents=True, exist_ok=True)
    paths.COPY_VARIANTS.write_text(json.dumps(result, indent=2))
    print(f"  Generated {len(variants)} variants ({len(headlines)} headlines, {len(ctas)} CTAs, {len(subheadlines)} subheadlines)")
