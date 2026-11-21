"""
Skincare Ingredient Interaction Checker: FastAPI backend (retrieval + LLM).

Run:   pip install fastapi uvicorn chromadb openai pandas
       export OPENAI_API_KEY=...          (Windows: set OPENAI_API_KEY=...)
       uvicorn app:create_app --factory --port 8000
Files needed in the same folder: ingredient_corpus.jsonl, interaction_dataset_draft.csv
Test:  POST http://127.0.0.1:8000/query   {"question": "Can I use retinol and vitamin C together?"}
Docs:  http://127.0.0.1:8000/docs
"""
import os
import json, re, unicodedata, html
import pandas as pd
import chromadb

def norm(s):
    s = unicodedata.normalize("NFKD", html.unescape(str(s))).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# Ingredients that are in the interaction table but NOT in the expanded corpus (too rare in OBF, or drugs not in CosIng).
# Facts below come only from the CosIng file we downloaded (benzoyl peroxide: OXIDISING, Annex III/94; adapalene and
# tretinoin: not in the CosIng cosmetic inventory).
PINNED = [
    {"id": "ing_benzoyl_peroxide", "inci": "BENZOYL PEROXIDE", "function": "OXIDISING", "restriction": "III/94",
     "text": "Ingredient: Benzoyl Peroxide (INCI: BENZOYL PEROXIDE)\nCosmetic function(s) per EU CosIng: oxidising\n"
             "EU regulatory reference: III/94 (Annex III: restricted substance list (limits/conditions apply)). This is a regulatory listing, not a safety rating.\n"
             "Added because it appears in our interaction table (found in only 2 products in our Open Beauty Facts sample)."},
    {"id": "ing_adapalene", "inci": "ADAPALENE", "function": "", "restriction": "",
     "text": "Ingredient: Adapalene\nNot listed in the EU CosIng cosmetic ingredient inventory.\n"
             "Added because it appears in our interaction table (a topical retinoid medication, brand name Differin)."},
    {"id": "ing_tretinoin", "inci": "TRETINOIN", "function": "", "restriction": "",
     "text": "Ingredient: Tretinoin (retinoic acid)\nNot listed in the EU CosIng cosmetic ingredient inventory.\n"
             "Added because it appears in our interaction table (a topical retinoid medication)."},
]

def load_all(corpus_path="ingredient_corpus.jsonl", inter_path="interaction_dataset_draft.csv"):
    corpus = [json.loads(l) for l in open(corpus_path, encoding="utf-8")]
    have = {c["id"] for c in corpus}
    for p in PINNED:
        if p["id"] not in have:
            corpus.append({"id": p["id"], "text": p["text"], "metadata": {
                "inci": p["inci"], "function": p["function"], "restriction": p["restriction"], "n_products": 0,
                "source": "interaction table / CosIng", "type": "ingredient"}})
    inter = pd.read_csv(inter_path, dtype=str).fillna("")
    return corpus, inter

def interaction_text(r):
    return (f"Interaction {r.pair_id}: {r.ingredient_a} + {r.ingredient_b}. Type: {r.interaction_type}. "
            f"Severity: {r.severity}. Evidence: {r.evidence_strength}. {r.explanation} Caveat: {r.caveat}")

def build_index(corpus, inter, embedding_function=None, client=None):
    client = client or chromadb.Client()
    kw = {"embedding_function": embedding_function} if embedding_function else {}
    ing = client.get_or_create_collection("ingredients_v2", **kw)
    for i in range(0, len(corpus), 200):
        b = corpus[i:i+200]
        ing.add(ids=[d["id"] for d in b], documents=[d["text"] for d in b],
                metadatas=[{k: str(v) for k, v in d["metadata"].items()} for d in b])
    its = client.get_or_create_collection("interactions_v2", **kw)
    its.add(ids=inter.pair_id.tolist(), documents=[interaction_text(r) for r in inter.itertuples()],
            metadatas=[{"pair_id": r.pair_id, "a": r.ingredient_a, "b": r.ingredient_b, "severity": r.severity,
                        "evidence": r.evidence_strength} for r in inter.itertuples()])
    return ing, its

# On skincare labels/blogs 'BHA' means beta hydroxy acid (salicylic acid), but in CosIng 'BHA' is butylated hydroxyanisole.
# We follow the skincare meaning for these two shorthand terms.
SKINCARE_SHORTHAND = {"bha", "aha"}

class Retriever:
    def __init__(self, corpus, inter, ing_col, int_col):
        self.ing, self.its, self.inter = ing_col, int_col, inter
        self.docs = {c["id"]: c for c in corpus}
        self.canon_to_id = {norm(c["metadata"]["inci"]): c["id"] for c in corpus}
        entries = {}                                       # alias -> {"ing": id, "canon": name}
        for c in corpus:                                   # names printed on labels + INCI name
            m = c["metadata"]
            names = [m["inci"]]
            mm = re.search(r"Also written on labels as: (.*)", c["text"])
            if mm: names += [x.strip() for x in mm.group(1).split(",")]
            for n in names:
                n = norm(n)
                if len(n) >= 3 and n not in SKINCARE_SHORTHAND:
                    entries.setdefault(n, {}).setdefault("ing", c["id"])
        for r in inter.itertuples():                       # interaction aliases -> canonical ingredient name
            for canon, al in ((r.ingredient_a, r.aliases_a), (r.ingredient_b, r.aliases_b)):
                for n in [canon] + al.split(";"):
                    n = norm(n)
                    if len(n) >= 3: entries.setdefault(n, {}).setdefault("canon", norm(canon))
        self.alias = sorted(entries.items(), key=lambda kv: -len(kv[0]))
        self.alias_map = dict(entries)                     # exact lookup, used by the label (ingredient list) endpoint

    def extract(self, query):
        q = " " + norm(query) + " "
        ids, canons = [], []
        for a, t in self.alias:
            pat = f" {a} "
            if pat in q:
                q = q.replace(pat, " ~ ", 1)               # consume the text so shorter aliases don't re-match
                if "ing" in t:
                    ids.append(t["ing"])
                    canons.append(norm(self.docs[t["ing"]]["metadata"]["inci"]))
                if "canon" in t:
                    canons.append(t["canon"])
                    if t["canon"] in self.canon_to_id: ids.append(self.canon_to_id[t["canon"]])
        return list(dict.fromkeys(ids)), list(dict.fromkeys(canons))

    def pairs_for(self, canons):
        s = set(canons)
        both, one = [], []
        for r in self.inter.itertuples():
            ina, inb = norm(r.ingredient_a) in s, norm(r.ingredient_b) in s
            if ina and inb: both.append(r.pair_id)
            elif ina or inb: one.append(r.pair_id)
        return both, one

    def match_item(self, item):
        """Match ONE label item (e.g. 'Retinol 0.5%', 'Aqua/Water/Eau') to an alias. Returns (ingredient_id or None, canonical names)."""
        item = re.sub(r"\d+(\.\d+)?\s*%", " ", str(item))          # drop strengths like '0.5%'
        item = re.sub(r"^\s*(ingredients?|inci)\s*:\s*", "", item, flags=re.I)
        for cand in [item] + [p for p in re.split(r"\s*/\s*", item) if "/" in item]:
            t = self.alias_map.get(norm(cand))
            if t:
                ing_id = t.get("ing") or self.canon_to_id.get(t.get("canon", ""))
                canons = []
                if ing_id: canons.append(norm(self.docs[ing_id]["metadata"]["inci"]))
                if "canon" in t: canons.append(t["canon"])
                return ing_id, list(dict.fromkeys(canons))
        return None, []

    def vector(self, query, k=3):
        return self.ing.query(query_texts=[query], n_results=k)["ids"][0]

    def retrieve(self, query, k=3):
        ids, canons = self.extract(query)
        both, one = self.pairs_for(canons)
        ing_ids = list(dict.fromkeys(ids + self.vector(query, k + len(ids))))[:max(k, len(ids))]
        if len(one) > 3:                                   # many rows mention only one named ingredient: keep the 3 closest to the question
            ranked = self.its.query(query_texts=[query], n_results=len(self.inter))["ids"][0]
            one = [p for p in ranked if p in set(one)]
        pair_ids = both + one[:3]
        if not canons:                                     # no ingredient recognised -> fall back to vector search
            pair_ids = self.its.query(query_texts=[query], n_results=3)["ids"][0]
        return {"ingredient_ids": ing_ids, "pair_ids": pair_ids, "found_names": canons}


import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

SYSTEM_PROMPT = """You are a cosmetic-ingredient information assistant for a student project.
Answer ONLY using the CONTEXT below. Rules:
1. If the context does not contain the answer, say: "I don't have documented information about that in my sources." Do not guess. Use that sentence ONLY when nothing in the context answers the question; if you give a documented answer, never also say you have no documented information.
2. Never invent an interaction. If no interaction row covers the pair, say no documented interaction was found in the sources, and that this does not prove it is safe.
3. Cite what you use with tags like [I1] for ingredient entries and [P13] for interaction rows. Every answer that uses the context MUST include at least one tag.
4. If an interaction row says its source is not yet verified, say so.
5. EU CosIng listings are regulatory references, not safety ratings. Do not present them as proof that something is safe or unsafe.
6. Never describe a combination as 'safe'. Use the words 'documented as compatible' ONLY when the row's Type is compatible_combination, compatible_myth_debunked, beneficial_combination, complementary, synergistic or compatible_with_scheduling. For additive_irritation, photosensitivity or chemical_degradation rows, describe the documented risk instead, and always state the evidence strength.
7. Keep the answer short (under 150 words) and plain. End with: "General information only, not medical or dermatological advice."
"""

DISCLAIMER = "General information only, not medical or dermatological advice."

def build_context(rt, result):
    parts, sources = [], []
    for n, cid in enumerate(result["ingredient_ids"], 1):
        d = rt.docs[cid]
        parts.append(f"[I{n}] {d['text']}")
        sources.append({"tag": f"I{n}", "type": "ingredient", "id": cid, "name": d["metadata"]["inci"],
                        "origin": d["metadata"].get("source", "")})
    rows = rt.inter.set_index("pair_id")
    for pid in result["pair_ids"]:
        r = rows.loc[pid]
        verified = "yes" if str(r.get("verified_by_team", "")).lower() == "yes" else "NOT YET VERIFIED"
        url = r["source_url"] + (f" ; {r['source_url_2']}" if r.get("source_url_2") else "")
        parts.append(f"[{pid}] {r.ingredient_a} + {r.ingredient_b}. Type: {r.interaction_type}. Severity: {r.severity}. "
                     f"Evidence strength: {r.evidence_strength}. {r.explanation} Caveat: {r.caveat} "
                     f"Source: {url}. Source verification: {verified}.")
        sources.append({"tag": pid, "type": "interaction", "id": pid, "name": f"{r.ingredient_a} + {r.ingredient_b}",
                        "evidence_strength": r.evidence_strength, "source_url": url, "verified": verified == "yes"})
    return "\n\n".join(parts), sources

def split_label(text):
    """Split a pasted ingredient list on commas, semicolons and newlines, but not inside (parentheses)."""
    items, buf, depth = [], [], 0
    for ch in str(text):
        if ch in "([": depth += 1
        elif ch in ")]": depth = max(0, depth - 1)
        if ch in ",;\n" and depth == 0:
            items.append("".join(buf)); buf = []
        else:
            buf.append(ch)
    items.append("".join(buf))
    items = [re.sub(r"^(ingredients?|inci)\s*:\s*", "", re.sub(r"\s+", " ", i).strip(" .\t"), flags=re.I) for i in items]
    return [i for i in items if i and i.lower() not in {"ingredients", "ingredients:"}]

LABEL_NOTE = ("Only pairs in our small interaction table are shown. A pair that is not listed does NOT mean it is safe; "
              "it means we have no documented information about it.")

EXPLAIN_PROMPT = """You are a cosmetic-ingredient information assistant for a student project.
You explain a product's estimated irritation risk in plain language, using ONLY the CONTEXT below. Rules:
1. Use only facts in the context. If something is not in the context, do not say it.
2. [R1] is a model estimate based on proxy labels (known fragrance allergens and common irritants). It is NOT a clinical prediction
   and NOT a measure of how any person's skin will react. Say it is an estimate, give the level and score, and name the flagged
   ingredients listed in [R1] as the reasons. If [R1] lists notes about reliability, mention them.
   If the estimated level differs from the rule-based proxy level in [R1], state BOTH and say that the model does not see the
   flagged ingredients directly, so the rule-based level from the flagged ingredients should be read alongside the estimate.
3. Cite what you use with tags: [R1] for the risk estimate, [I1], [I2]... for ingredient entries, [P13] for interaction rows.
   Every answer MUST include at least [R1].
4. Mention documented interactions only if interaction rows are in the context. If an interaction row says its source is not yet
   verified, say so. If there are no interaction rows, say no documented interaction was found in the sources, and that this does
   not prove the combination is safe.
5. EU CosIng listings are regulatory references, not safety ratings.
6. Never call the product or a combination 'safe' or 'dangerous'.
7. Keep it under 170 words, plain language. End with: "General information only, not medical or dermatological advice."
"""

def build_explain_context(rt, res):
    risk = res["risk"]
    lines = [f"[R1] Estimated irritation-risk level: {risk['level']} (score {risk['score']} out of 100; class probabilities "
             f"{risk['probabilities']}). Ingredients flagged by the rule as known fragrance allergens: "
             f"{', '.join(risk['flagged_allergens']) or 'none'}. Flagged as common irritants: "
             f"{', '.join(risk['flagged_irritants']) or 'none'}. Rule-based proxy level from these flags: {risk['rule_level']}. "
             f"Reliability notes: {' '.join(risk['notes']) or 'none'}. Basis: {risk['basis']}"]
    sources = [{"tag": "R1", "type": "risk estimate", "name": f"risk level {risk['level']}", "origin": "risk model (Sprint 3)"}]
    flagged = {a for a in risk["flagged_allergens"] + risk["flagged_irritants"]}
    n = 0
    for r in res["recognized"]:                      # ingredient entries for the flagged ones (explains what they are)
        if r["ingredient_id"] and (norm(r["cosing_inci"]) in flagged or norm(r["label_name"]) in flagged):
            n += 1
            if n > 5:
                break
            d = rt.docs[r["ingredient_id"]]
            lines.append(f"[I{n}] {d['text']}")
            sources.append({"tag": f"I{n}", "type": "ingredient", "id": r["ingredient_id"], "name": d["metadata"]["inci"],
                            "origin": d["metadata"].get("source", "")})
    rows = rt.inter.set_index("pair_id")
    for p in res["pairs"][:5]:
        r = rows.loc[p["pair_id"]]
        verified = "yes" if str(r.get("verified_by_team", "")).lower() == "yes" else "NOT YET VERIFIED"
        lines.append(f"[{p['pair_id']}] {r.ingredient_a} + {r.ingredient_b}. Type: {r.interaction_type}. Severity: {r.severity}. "
                     f"Evidence strength: {r.evidence_strength}. {r.explanation} Caveat: {r.caveat} Source verification: {verified}.")
        sources.append({"tag": p["pair_id"], "type": "interaction", "id": p["pair_id"], "name": p["ingredients"],
                        "evidence_strength": p["evidence_strength"], "source_url": p["source_url"], "verified": p["verified"]})
    return "\n\n".join(lines), sources

def make_app(rt, llm, scorer=None):
    """rt = Retriever; llm = function(system_prompt, user_prompt) -> str; scorer = RiskScorer or None."""
    app = FastAPI(title="Skincare Ingredient Interaction Checker", version="0.2")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # lets a web frontend call it

    class QueryRequest(BaseModel):
        question: str = Field(..., min_length=3, max_length=500, examples=["Can I use retinol and vitamin C together?"])

    class QueryResponse(BaseModel):
        answer: str
        sources: list[dict]
        recognized_ingredients: list[str]
        latency_ms: int
        disclaimer: str = DISCLAIMER

    class LabelRequest(BaseModel):
        ingredients: str = Field(..., min_length=3, max_length=4000,
                                 examples=["Aqua, Glycerin, Retinol 0.5%, Niacinamide, Phenoxyethanol, Parfum"])

    def analyze_label(text):
        """Parse a pasted ingredient list: recognised items, documented pairs, risk estimate. No LLM involved."""
        t0 = time.time()
        items = split_label(text)[:200]
        if not items:
            raise HTTPException(status_code=422, detail="No ingredients found in the text.")
        recognized, unrecognized, canons, seen, rows_for_risk = [], [], [], set(), []
        for it in items:
            ing_id, cn = rt.match_item(it)
            md = rt.docs[ing_id]["metadata"] if ing_id else {}
            rows_for_risk.append({"label": it, "inci": md.get("inci", ""), "function": md.get("function", ""),
                                  "restriction": md.get("restriction", ""), "recognized": bool(cn or ing_id)})
            if not cn and not ing_id:
                unrecognized.append(it); continue
            if ing_id in seen and ing_id is not None:
                continue
            seen.add(ing_id)
            recognized.append({"label_name": it, "cosing_inci": md.get("inci", ""), "function": md.get("function", ""),
                               "eu_restriction": md.get("restriction", ""),
                               "matched_as": cn[-1] if cn else "", "ingredient_id": ing_id or ""})
            canons += cn
        both, one = rt.pairs_for(canons)
        def row(pid):
            r = rt.inter[rt.inter.pair_id == pid].iloc[0]
            return {"pair_id": pid, "ingredients": f"{r.ingredient_a} + {r.ingredient_b}", "interaction_type": r.interaction_type,
                    "severity": r.severity, "explanation": r.explanation, "evidence_strength": r.evidence_strength,
                    "caveat": r.caveat, "source_url": r.source_url, "verified": r.verified_by_team.strip().lower() == "yes"}
        pairs = [row(p) for p in both]
        cond = [row(p) for p in one if rt.inter[rt.inter.pair_id == p].iloc[0].pair_type == "ingredient_condition"]
        risk = scorer.assess(rows_for_risk) if scorer is not None else None
        return {"n_items": len(items), "recognized": recognized, "unrecognized": unrecognized,
                "pairs": pairs, "condition_notes": cond, "risk": risk, "note": LABEL_NOTE, "disclaimer": DISCLAIMER,
                "latency_ms": int((time.time() - t0) * 1000)}

    @app.post("/label")
    def label(req: LabelRequest):
        """Ingredient-list lookup. No LLM: recognition, pair lookup and the risk estimate are deterministic."""
        return analyze_label(req.ingredients)

    @app.post("/explain")
    def explain(req: LabelRequest):
        """Plain-language explanation of a product's risk estimate and documented interactions, grounded in the data."""
        t0 = time.time()
        res = analyze_label(req.ingredients)
        if res["risk"] is None:
            raise HTTPException(status_code=503, detail="The risk model is not loaded on this server.")
        context, sources = build_explain_context(rt, res)
        user_prompt = f"CONTEXT:\n{context}\n\nTASK: Explain this product's estimated irritation risk and any documented interactions."
        try:
            answer = llm(EXPLAIN_PROMPT, user_prompt)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"LLM call failed: {type(e).__name__}: {e}")
        any_tag = any(f"[{x['tag']}]" in answer for x in sources)
        if not any_tag and sources:                      # the model forgot its citation tags: add them
            answer += "\n\nSources: " + " ".join("[" + x["tag"] + "]" for x in sources)
            any_tag = True
        for s in sources:
            s["cited"] = (f"[{s['tag']}]" in answer) if any_tag else False
        return {"answer": answer, "sources": sources, "risk": res["risk"], "pairs": res["pairs"],
                "recognized": res["recognized"], "unrecognized": res["unrecognized"],
                "disclaimer": DISCLAIMER, "latency_ms": int((time.time() - t0) * 1000)}

    @app.get("/health")
    def health():
        return {"status": "ok", "ingredient_entries": len(rt.docs), "interaction_rows": len(rt.inter),
                "risk_model_loaded": scorer is not None}

    @app.post("/query", response_model=QueryResponse)
    def query(req: QueryRequest):
        t0 = time.time()
        result = rt.retrieve(req.question)
        named_ids = rt.extract(req.question)[0]
        if named_ids:                         # the user named ingredients: send only those entries, not vector-search filler
            result["ingredient_ids"] = named_ids[:4]
            both, one = rt.pairs_for(result["found_names"])
            result["pair_ids"] = both if both else one[:3]   # exact-pair rows first; single-ingredient rows only if no pair
        else:                                 # nothing named: no interaction rows (avoid unrelated rows), keep vector hits
            result["pair_ids"] = []
        context, sources = build_context(rt, result)
        user_prompt = f"CONTEXT:\n{context}\n\nQUESTION: {req.question}"
        try:
            answer = llm(SYSTEM_PROMPT, user_prompt)
        except Exception as e:                      # e.g. no API credit, network error
            raise HTTPException(status_code=502, detail=f"LLM call failed: {type(e).__name__}: {e}")
        refused = "don't have documented information" in answer.lower()
        any_tag = any(f"[{x['tag']}]" in answer for x in sources)
        if not any_tag and not refused and sources:      # the model forgot its citation tags: add them from the retrieved context
            answer += "\n\nSources: " + " ".join("[" + x["tag"] + "]" for x in sources)
            any_tag = True
        for s in sources:                           # lets the frontend show only the sources the answer actually used
            s["cited"] = (f"[{s['tag']}]" in answer) if any_tag else (not refused)
        return QueryResponse(answer=answer, sources=sources, recognized_ingredients=result["found_names"],
                             latency_ms=int((time.time() - t0) * 1000))
    return app

def make_openai_llm(client, model="gpt-4o-mini"):
    def llm(system, user):
        r = client.chat.completions.create(model=model, temperature=0, max_tokens=400,
                                           messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
        return r.choices[0].message.content.strip()
    return llm


def create_app(llm=None, embedding_function=None):
    corpus, inter = load_all(os.environ.get("CORPUS_PATH", "ingredient_corpus.jsonl"),
                             os.environ.get("INTERACTION_PATH", "interaction_dataset_draft.csv"))
    ing_col, int_col = build_index(corpus, inter, embedding_function)
    rt = Retriever(corpus, inter, ing_col, int_col)
    if llm is None:
        from openai import OpenAI
        llm = make_openai_llm(OpenAI())          # reads OPENAI_API_KEY from the environment
    scorer = None
    rp = os.environ.get("RISK_MODEL_PATH", "risk_model.joblib")
    if os.path.exists(rp):
        try:
            from risk_score import RiskScorer
            scorer = RiskScorer.load(rp)
        except Exception as e:                        # the app still works without the risk model
            print("Risk model not loaded:", type(e).__name__, e)
    return make_app(rt, llm, scorer)
