import json, re, html, unicodedata
import numpy as np, pandas as pd
from sklearn.model_selection import GroupShuffleSplit, GroupKFold, GridSearchCV
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix, classification_report

def norm(s):
    s = unicodedata.normalize("NFKD", html.unescape(str(s))).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\([^)]*\)", " ", s); s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# ---- reference lists (reviewable; general cosmetic-science knowledge, NOT clinical ground truth) ----
# EU "26 declared fragrance allergens" + parfum (CosIng Annex III) -- these drive the risk label
ALLERGENS = {norm(x) for x in ["parfum", "fragrance", "amyl cinnamal", "benzyl alcohol", "cinnamyl alcohol", "citral", "eugenol",
 "hydroxycitronellal", "isoeugenol", "amylcinnamyl alcohol", "benzyl salicylate", "cinnamal", "coumarin", "geraniol",
 "hydroxyisohexyl 3-cyclohexene carboxaldehyde", "anise alcohol", "benzyl cinnamate", "farnesol", "butylphenyl methylpropional",
 "linalool", "benzyl benzoate", "citronellol", "hexyl cinnamal", "limonene", "methyl 2-octynoate", "alpha-isomethyl ionone",
 "evernia prunastri extract", "evernia furfuracea extract"]}
IRRITANTS = {norm(x) for x in ["retinol","glycolic acid","salicylic acid","lactic acid","mandelic acid","alcohol denat","benzoyl peroxide",
 "sodium lauryl sulfate","methylisothiazolinone","methylchloroisothiazolinone","menthol"]}
GENTLE = {norm(x) for x in ["glycerin","hyaluronic acid","sodium hyaluronate","niacinamide","panthenol","ceramide np","ceramide ap",
 "ceramide eop","aloe barbadensis leaf juice","allantoin","squalane","bisabolol"]}

def risk_label(n_all, n_irr):
    s = n_all + 1.5 * n_irr
    return "high" if s >= 3 else ("medium" if s >= 1 else "low")

def load(filtered="obf_cosing_filtered.jsonl", matched="ingredients_cosing_matched.csv"):
    m = pd.read_csv(matched, dtype=str).fillna("")
    m = m[m.match_type.isin(["exact", "synonym", "split"])]
    fn = {r.ingredient: (r.function.lower(), r.restriction) for r in m.itertuples()}
    rows, seen = [], set()
    for l in open(filtered, encoding="utf-8"):
        p = json.loads(l)
        ings = p["ingredient_list"]
        key = tuple(sorted(norm(i) for i in ings))
        if key in seen or len(ings) < 3: continue          # drop duplicate formulas (leakage) and tiny lists
        seen.add(key)
        ns = {norm(i) for i in ings}
        funcs = [fn.get(i, ("", ""))[0] for i in ings]
        restr = [fn.get(i, ("", ""))[1] for i in ings]
        f = lambda w: sum(w in x for x in funcs)
        rows.append({
            "code": p["code"], "brand": (p.get("brands") or "").strip().lower() or f"nobrand_{p['code']}",
            "n_allergens": len(ns & ALLERGENS), "n_irritants": len(ns & IRRITANTS),
            "n_ingredients": len(ings), "n_gentle": len(ns & GENTLE), "n_restricted": sum(bool(x) for x in restr),
            "n_preservative": f("preservative"), "n_surfactant": f("surfactant"), "n_perfuming": f("perfuming"),
            "n_colorant": f("colorant"), "n_emollient": f("emollient"), "n_humectant": f("humectant"),
            "n_antioxidant": f("antioxidant"), "n_emulsifying": f("emulsifying"), "match_fraction": p["match_fraction"]})
    df = pd.DataFrame(rows)
    df["risk"] = [risk_label(a, b) for a, b in zip(df.n_allergens, df.n_irritants)]
    return df

LABEL_FEATS = ["n_allergens", "n_irritants"]
OTHER_FEATS = ["n_ingredients", "n_gentle", "n_restricted", "n_preservative", "n_surfactant", "n_perfuming", "n_colorant",
               "n_emollient", "n_humectant", "n_antioxidant", "n_emulsifying", "match_fraction"]

def split(df, seed=42):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)   # same brand never in both train and test
    tr, te = next(gss.split(df, df.risk, groups=df.brand))
    return df.iloc[tr].reset_index(drop=True), df.iloc[te].reset_index(drop=True)

def fit_eval(train, test, feats, name):
    grid = {"max_depth": [2, 3, 4, 6, 8, 12], "min_samples_leaf": [1, 10, 50]}
    gs = GridSearchCV(DecisionTreeClassifier(random_state=42, class_weight="balanced"), grid, scoring="f1_macro",
                      cv=GroupKFold(n_splits=5), n_jobs=-1)
    gs.fit(train[feats], train.risk, groups=train.brand)
    pred = gs.predict(test[feats])
    base = DummyClassifier(strategy="most_frequent").fit(train[feats], train.risk).predict(test[feats])
    print(f"\n=== {name} ===  best params {gs.best_params_}  (CV macro-F1 on train {gs.best_score_:.3f})")
    print(f"TEST accuracy {accuracy_score(test.risk, pred):.3f} | macro-F1 {f1_score(test.risk, pred, average='macro'):.3f}"
          f"  vs majority-class baseline accuracy {accuracy_score(test.risk, base):.3f}")
    labels = ["low", "medium", "high"]
    print("confusion matrix (rows = true, cols = predicted; order low, medium, high)")
    print(pd.DataFrame(confusion_matrix(test.risk, pred, labels=labels), index=labels, columns=labels))
    return gs.best_estimator_, pred
