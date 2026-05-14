import json
import paths
import llm_client


def run():
    brief = json.loads(paths.PRODUCT_BRIEF.read_text())["product_brief"]
    constraints = "\n".join(f"- {c}" for c in brief["compliance_constraints"])

    prompt = f"""You are a marketing strategy expert designing a scoring rubric for evaluating marketing copy.

Product: {brief["product"]}
Description: {brief["description"]}
Markets: {", ".join(brief["markets"])}
Tone: {brief["tone"]}

Primary audience: {brief["primary_audience"]["persona"]}
Traits: {", ".join(brief["primary_audience"]["traits"])}

Secondary audience: {brief["secondary_audience"]["persona"]}
Traits: {", ".join(brief["secondary_audience"]["traits"])}

Compliance constraints:
{constraints}

Design a scoring rubric with EXACTLY 5 dimensions for evaluating marketing copy variants.

Requirements:
- Every dimension must be specific to this product, audience, and compliance context
- Do NOT produce a generic marketing rubric
- Weights must sum to exactly 1.0
- Each weight must be a positive value
- scale is always "0-10"
- description_of_10 must describe what a perfect score looks like for THIS product and audience specifically

Return JSON with this exact structure:
{{
  "dimensions": [
    {{
      "dimension_id": "snake_case_id",
      "name": "Dimension Name",
      "weight": 0.2,
      "scale": "0-10",
      "description_of_10": "What a perfect 10 looks like for this specific product and audience"
    }}
  ]
}}"""

    result = llm_client.call(
        stage="rubric_design",
        prompt=prompt,
        input_artifacts=["product_brief.json"],
        output_artifact="artifacts/stage_1/rubric_draft.json",
    )

    dims = result.get("dimensions", [])
    if len(dims) != 5:
        raise RuntimeError(f"Expected 5 rubric dimensions, got {len(dims)}")

    total_weight = sum(d["weight"] for d in dims)
    if abs(total_weight - 1.0) > 0.001:
        raise RuntimeError(f"Rubric weights sum to {total_weight:.4f}, must be 1.0")

    required = {"dimension_id", "name", "weight", "scale", "description_of_10"}
    for d in dims:
        missing = required - d.keys()
        if missing:
            raise RuntimeError(f"Dimension '{d.get('name')}' missing fields: {missing}")

    paths.RUBRIC_DRAFT.parent.mkdir(parents=True, exist_ok=True)
    paths.RUBRIC_DRAFT.write_text(json.dumps(result, indent=2))
    print(f"  Rubric draft saved ({len(dims)} dimensions)")
