import json
import paths
import llm_client


def _weighted_score(dimension_scores: list, weights: dict) -> float:
    return round(sum(ds["score"] * weights.get(ds["dimension_id"], 0) for ds in dimension_scores), 4)


def run():
    rubric = json.loads(paths.APPROVED_RUBRIC.read_text())
    variants_data = json.loads(paths.COPY_VARIANTS.read_text())
    brief = json.loads(paths.PRODUCT_BRIEF.read_text())["product_brief"]

    dims = rubric["dimensions"]
    rubric_weights = {d["dimension_id"]: d["weight"] for d in dims}
    dim_ids = [d["dimension_id"] for d in dims]

    to_score = [v for v in variants_data["variants"] if v["variant_type"] in ("headline", "cta")]
    personas = [brief["primary_audience"]["persona"], brief["secondary_audience"]["persona"]]
    print(f"  Scoring {len(to_score)} variants x {len(personas)} personas = {len(to_score) * len(personas)} entries...")
    print(f"  Rubric: {len(dims)} dimensions | Calling LLM (this may take a moment)...")

    dims_desc = "\n".join(
        f"- {d['dimension_id']} ({d['name']}, weight {d['weight']}): score 10 means {d['description_of_10']}"
        for d in dims
    )
    variants_desc = "\n".join(
        f"- {v['variant_id']} [{v['variant_type']}] ({v['angle']}): \"{v['text']}\""
        for v in to_score
    )
    persona_desc = "\n".join(f"- {p}" for p in personas)

    prompt = f"""You are a marketing analyst. Score each copy variant against the rubric for each audience persona.

RUBRIC DIMENSIONS:
{dims_desc}

PERSONAS:
{persona_desc}

Primary audience traits: {", ".join(brief["primary_audience"]["traits"])}
Secondary audience traits: {", ".join(brief["secondary_audience"]["traits"])}

VARIANTS TO SCORE:
{variants_desc}

Score every variant for BOTH personas independently. Be critical and differentiated — avoid giving identical scores.

Return JSON with one entry per (variant_id x persona) combination — {len(to_score) * len(personas)} entries total:
{{
  "scores": [
    {{
      "variant_id": "headline_empowerment",
      "persona": "persona name here",
      "dimension_scores": [
        {{"dimension_id": "{dim_ids[0]}", "score": 8, "rationale": "brief rationale"}}
      ]
    }}
  ]
}}

Include all {len(dim_ids)} dimensions for every entry."""

    result = llm_client.call(
        stage="persona_scoring",
        prompt=prompt,
        input_artifacts=[
            "artifacts/stage_2/approved_rubric.json",
            "artifacts/stage_3/copy_variants.json",
            "product_brief.json",
        ],
        output_artifact="artifacts/stage_4/variant_scores.json",
    )

    scores = result.get("scores", [])
    print(f"  LLM returned {len(scores)} score entries. Computing weighted totals...")

    for s in scores:
        s["total_weighted_score"] = _weighted_score(s["dimension_scores"], rubric_weights)

    score_index = {(s["variant_id"], s["persona"]) for s in scores}
    for v in to_score:
        for persona in personas:
            if (v["variant_id"], persona) not in score_index:
                raise RuntimeError(f"Missing score for '{v['variant_id']}' / '{persona}'")

    approved_dim_ids = set(dim_ids)
    for s in scores:
        for ds in s["dimension_scores"]:
            if ds["dimension_id"] not in approved_dim_ids:
                raise RuntimeError(
                    f"Score uses unknown dimension_id '{ds['dimension_id']}'. "
                    f"Approved: {approved_dim_ids}"
                )

    paths.VARIANT_SCORES.parent.mkdir(parents=True, exist_ok=True)
    paths.VARIANT_SCORES.write_text(json.dumps({"scores": scores}, indent=2))
    print(f"  Scored {len(to_score)} variants x {len(personas)} personas = {len(scores)} records")
