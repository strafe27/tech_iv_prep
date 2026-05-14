import json
import paths
import llm_client


def run():
    scores_data = json.loads(paths.VARIANT_SCORES.read_text())
    audit_data = json.loads(paths.COMPLIANCE_AUDIT.read_text())
    variants_data = json.loads(paths.COPY_VARIANTS.read_text())

    audit = {a["variant_id"]: a for a in audit_data["audit"]}
    variants = {v["variant_id"]: v for v in variants_data["variants"]}
    scores = scores_data["scores"]

    eligible_headline_ids = [
        v["variant_id"] for v in variants_data["variants"]
        if v["variant_type"] == "headline" and audit.get(v["variant_id"], {}).get("severity") != "blocker"
    ]

    def avg_score(vid: str) -> float:
        relevant = [s["total_weighted_score"] for s in scores if s["variant_id"] == vid]
        return sum(relevant) / len(relevant) if relevant else 0.0

    top3_ids = sorted(eligible_headline_ids, key=avg_score, reverse=True)[:3]
    top3 = [variants[vid] for vid in top3_ids]
    headlines_desc = "\n".join(
        f'- {h["variant_id"]} ({h["angle"]}): "{h["text"]}"' for h in top3
    )

    prompt = f"""You are a localisation expert evaluating marketing headlines for adaptation into Arabic and Bahasa Malaysia markets.

TOP 3 HEADLINES:
{headlines_desc}

For each headline, evaluate conceptual localisation into:
1. Arabic (Middle East / Gulf market context)
2. Bahasa Malaysia (Malaysian market context)

Flag any issues in each language using these types:
- "idiom": phrase that doesn't translate conceptually
- "cultural_assumption": assumption that may not hold in that culture
- "unclear_phrasing": phrasing that becomes ambiguous or confusing in translation
- "compliance_risk": translation could introduce financial compliance risk

Return JSON:
{{
  "localisation_flags": [
    {{
      "variant_id": "headline_empowerment",
      "text": "original headline text",
      "languages": {{
        "arabic": {{
          "flags": [
            {{"type": "idiom", "phrase": "the problematic phrase", "description": "why this is an issue"}}
          ]
        }},
        "bahasa_malaysia": {{
          "flags": []
        }}
      }}
    }}
  ]
}}

Return an empty flags array if a headline has no issues in a language."""

    result = llm_client.call(
        stage="localisation_review",
        prompt=prompt,
        input_artifacts=[
            "artifacts/stage_3/copy_variants.json",
            "artifacts/stage_4/variant_scores.json",
            "artifacts/stage_5/compliance_audit.json",
        ],
        output_artifact="artifacts/stage_9/localisation_flags.json",
    )

    paths.LOCALISATION_FLAGS.parent.mkdir(parents=True, exist_ok=True)
    paths.LOCALISATION_FLAGS.write_text(json.dumps(result, indent=2))

    flags = result.get("localisation_flags", [])
    total_flags = sum(
        len(lang.get("flags", []))
        for f in flags
        for lang in f.get("languages", {}).values()
    )
    print(f"  Localisation: {len(flags)} headlines reviewed, {total_flags} total flags")
