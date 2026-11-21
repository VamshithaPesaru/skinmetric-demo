"""
Risk scoring for the app (connects the data-science model to the chatbot).

Input : the ingredients of one product, as a list of dicts
        {"label": text on the label, "inci": CosIng name or "", "function": CosIng function or "", "restriction": annex ref or ""}
Output: an estimated irritation-risk level (low / medium / high), a 0-100 score, the class probabilities, and the
        ingredients that triggered the rule-based labelling (known fragrance allergens and common irritants).

The level comes from the random-forest model tuned in Sprint 3. The model deliberately does NOT see the allergen/irritant
counts (they define the label), it uses indirect features such as the number of perfuming ingredients.
The labels are rule-based PROXIES, not clinical data: this is an estimate of a proxy, not a skin-reaction prediction.
"""
import joblib
import numpy as np
import pandas as pd
from risk_model import norm, ALLERGENS, IRRITANTS, GENTLE, OTHER_FEATS, risk_label

SCORE = {"low": 0, "medium": 50, "high": 100}
MIN_ITEMS = 3            # the model was trained on lists of at least 3 ingredients
MIN_MATCH = 0.6          # ... and on products where at least 60% of ingredients matched CosIng


def featurize(rows):
    """Same 12 indirect features as in training, computed from one product's ingredient rows."""
    funcs = [str(r.get("function", "")).lower() for r in rows]
    restr = [str(r.get("restriction", "")) for r in rows]
    names = set()
    for r in rows:
        for x in (r.get("label", ""), r.get("inci", "")):
            n = norm(x)
            if n:
                names.add(n)
    f = lambda w: sum(w in x for x in funcs)
    n = max(len(rows), 1)
    return {
        "n_ingredients": len(rows), "n_gentle": len(names & GENTLE), "n_restricted": sum(bool(x) for x in restr),
        "n_preservative": f("preservative"), "n_surfactant": f("surfactant"), "n_perfuming": f("perfuming"),
        "n_colorant": f("colorant"), "n_emollient": f("emollient"), "n_humectant": f("humectant"),
        "n_antioxidant": f("antioxidant"), "n_emulsifying": f("emulsifying"),
        "match_fraction": sum(bool(r.get("recognized")) for r in rows) / n,
    }, names


class RiskScorer:
    def __init__(self, model):
        self.model = model
        self.classes = list(model.classes_)

    @classmethod
    def load(cls, path):
        return cls(joblib.load(path))

    def assess(self, rows):
        feats, names = featurize(rows)
        X = pd.DataFrame([feats])[OTHER_FEATS]
        proba = self.model.predict_proba(X)[0]
        probs = {c: round(float(p), 3) for c, p in zip(self.classes, proba)}
        level = max(probs, key=probs.get)
        score = int(round(sum(probs[c] * SCORE[c] for c in probs)))
        allergens = sorted(names & ALLERGENS)
        irritants = sorted(names & IRRITANTS)
        notes = []
        if len(rows) < MIN_ITEMS:
            notes.append("The list has fewer than 3 ingredients, so the estimate is unreliable.")
        if feats["match_fraction"] < MIN_MATCH:
            notes.append("Many ingredients were not recognised, so the estimate is less reliable.")
        return {
            "level": level, "score": score, "probabilities": probs,
            "rule_level": risk_label(len(allergens), len(irritants)),     # the proxy label itself, from the flagged ingredients
            "flagged_allergens": allergens, "flagged_irritants": irritants,
            "features": {k: (round(v, 3) if isinstance(v, float) else v) for k, v in feats.items()},
            "notes": notes,
            "basis": ("Estimated by a model trained on Open Beauty Facts products. The labels it learns are rule-based proxies "
                      "(known fragrance allergens and common irritants), not clinical data."),
        }
