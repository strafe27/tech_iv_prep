import json
import paths
import llm_client


def run():
    scores_data = json.loads(paths.VARIANT_SCORES.read_text())
    audit_data = json.loads(paths.COMPLIANCE_AUDIT.read_text())
    variants_data = json.loads(paths.COPY_VARIANTS.read_text())
    brief = json.loads(paths.PRODUCT_BRIEF.read_text())["product_brief"]

    scores = scores_data["scores"]
    audit = {a["variant_id"]: a for a in audit_data["audit"]}
    variants = {v["variant_id"]: v for v in variants_data["variants"]}
    personas = [brief["primary_audience"]["persona"], brief["secondary_audience"]["persona"]]

    def is_eligible(vid: str) -> bool:
        return audit.get(vid, {}).get("severity") != "blocker"

    def score_for(vid: str, persona: str) -> float:
        for s in scores:
            if s["variant_id"] == vid and s["persona"] == persona:
                return s["total_weighted_score"]
        return 0.0

    # Part A: deterministic winner selection
    selections = []
    for persona in personas:
        eligible_headlines = [
            v for v in variants.values()
            if v["variant_type"] == "headline" and is_eligible(v["variant_id"])
        ]
        if not eligible_headlines:
            raise RuntimeError(
                f"All headlines are compliance blockers for persona '{persona}'. Cannot produce recommendation."
            )

        winner_headline = max(eligible_headlines, key=lambda v: score_for(v["variant_id"], persona))
        angle = winner_headline["angle"]

        candidate_subs = [
            v for k, v in variants.items()
            if k in (f"subheadline_{angle}_1", f"subheadline_{angle}_2")
            and is_eligible(v["variant_id"])
        ]
        if not candidate_subs:
            # All angle-matched subheadlines are blockers; fall back to any eligible subheadline
            candidate_subs = [
                v for v in variants.values()
                if v["variant_type"] == "subheadline" and is_eligible(v["variant_id"])
            ]
        if not candidate_subs:
            raise RuntimeError(f"No eligible subheadlines available for persona '{persona}'")

        eligible_ctas = [
            v for v in variants.values()
            if v["variant_type"] == "cta" and is_eligible(v["variant_id"])
        ]
        winner_cta = max(eligible_ctas, key=lambda v: score_for(v["variant_id"], persona))

        compliance_notes = []
        for vid in [winner_headline["variant_id"], winner_cta["variant_id"]]:
            a = audit.get(vid, {})
            note = f"{vid}: {a.get('severity', 'clear')}"
            if a.get("rule_violated"):
                note += f" — {a['rule_violated']}"
            compliance_notes.append(note)

        selections.append({
            "persona": persona,
            "headline": winner_headline,
            "candidate_subheadlines": candidate_subs,
            "cta": winner_cta,
            "compliance_notes": compliance_notes,
        })

    # Part B: LLM generates bullets, trust signal, rationale, picks subheadline
    selections_desc = ""
    for sel in selections:
        subs_text = "\n".join(
            f"    - {s['variant_id']}: \"{s['text']}\"" for s in sel["candidate_subheadlines"]
        )
        selections_desc += f"""
Persona: {sel["persona"]}
  Headline ({sel["headline"]["angle"]}): "{sel["headline"]["text"]}"
  CTA ({sel["cta"]["angle"]}): "{sel["cta"]["text"]}"
  Candidate subheadlines (pick the better one):
{subs_text}
"""

    prompt = f"""You are a senior copywriter finalising above-the-fold copy decks for two audience personas.

Product: {brief["product"]}
Description: {brief["description"]}
Tone: {brief["tone"]}

SELECTED WINNERS PER PERSONA:
{selections_desc}

For each persona produce:
1. Select the better subheadline (return its exact variant_id)
2. 3 benefit bullets grounded strictly in the product description — no invented features
3. 1-sentence social proof or trust signal
4. 3-5 sentence recommendation rationale explaining why this copy combination was chosen for this persona

Return JSON:
{{
  "recommendations": [
    {{
      "persona": "exact persona name",
      "selected_subheadline_id": "subheadline_empowerment_1",
      "benefit_bullets": ["bullet 1", "bullet 2", "bullet 3"],
      "trust_signal": "one sentence trust signal",
      "rationale": "3-5 sentence rationale"
    }}
  ]
}}"""

    llm_result = llm_client.call(
        stage="recommendation_generation",
        prompt=prompt,
        input_artifacts=[
            "artifacts/stage_4/variant_scores.json",
            "artifacts/stage_5/compliance_audit.json",
            "product_brief.json",
        ],
        output_artifact="artifacts/stage_6/recommendation.json",
    )

    llm_recs = {r["persona"]: r for r in llm_result.get("recommendations", [])}

    recommendations = []
    for sel in selections:
        persona = sel["persona"]
        llm = llm_recs.get(persona, {})

        selected_sub_id = llm.get("selected_subheadline_id", "")
        eligible_sub_ids = {s["variant_id"] for s in sel["candidate_subheadlines"]}
        selected_sub = (
            variants.get(selected_sub_id) if selected_sub_id in eligible_sub_ids else None
        ) or (sel["candidate_subheadlines"][0] if sel["candidate_subheadlines"] else {})

        recommendations.append({
            "persona": persona,
            "recommendation_status": "eligible",
            "headline": {
                "variant_id": sel["headline"]["variant_id"],
                "text": sel["headline"]["text"],
                "angle": sel["headline"]["angle"],
            },
            "subheadline": {
                "variant_id": selected_sub.get("variant_id", ""),
                "text": selected_sub.get("text", ""),
            },
            "cta": {
                "variant_id": sel["cta"]["variant_id"],
                "text": sel["cta"]["text"],
                "angle": sel["cta"]["angle"],
            },
            "benefit_bullets": llm.get("benefit_bullets", []),
            "trust_signal": llm.get("trust_signal", ""),
            "compliance_notes": sel["compliance_notes"],
            "rationale": llm.get("rationale", ""),
        })

    paths.RECOMMENDATION_JSON.parent.mkdir(parents=True, exist_ok=True)
    paths.RECOMMENDATION_JSON.write_text(json.dumps(recommendations, indent=2))
    _render_md(recommendations)
    print(f"  Recommendations saved for {len(recommendations)} personas")


def _render_md(recommendations: list):
    lines = ["# Copy Deck Recommendations\n"]
    for rec in recommendations:
        lines += [
            f"---\n\n## Persona: {rec['persona']}\n",
            f"**Headline:** {rec['headline']['text']}",
            f"*Angle: {rec['headline']['angle']}*\n",
            f"**Subheadline:** {rec['subheadline']['text']}\n",
            f"**CTA:** {rec['cta']['text']}",
            f"*Angle: {rec['cta']['angle']}*\n",
            "**Benefit Bullets:**",
        ]
        for b in rec["benefit_bullets"]:
            lines.append(f"- {b}")
        lines += [
            f"\n**Trust Signal:** {rec['trust_signal']}\n",
            "**Compliance Notes:**",
        ]
        for n in rec["compliance_notes"]:
            lines.append(f"- {n}")
        lines.append(f"\n**Rationale:** {rec['rationale']}\n")

    paths.RECOMMENDATION_MD.write_text("\n".join(lines))
