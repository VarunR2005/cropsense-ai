"""
Rule-based fertilizer estimator (no machine learning).

Steps:
 1. Rate each soil-test value as low / medium / high using thresholds in fertilizer_rules.json.
 2. Scale the crop's standard dose (N, P2O5, K2O kg/ha) by the rating.
 3. Convert nutrient targets to fertilizer kg using each product's nutrient content:
      DAP for phosphorus (it also supplies some N), urea for the remaining N, MOP for K.
The numbers in fertilizer_rules.json are approximate and must be verified (see its _meta).
"""
import json
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parent / "data" / "fertilizer_rules.json"
NUTRIENT_KEY = {"N": "N", "P": "P2O5", "K": "K2O"}


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def supported_crops() -> list[str]:
    return sorted(load_rules()["crops"].keys())


def _rating(nutrient: str, value: float, rules: dict) -> str:
    t = rules["soil_test_ratings_kg_per_ha"][nutrient]
    if value < t["low_below"]:
        return "low"
    if value > t["high_above"]:
        return "high"
    return "medium"


def recommend_fertilizer(*, crop: str, nitrogen: float, phosphorus: float, potassium: float,
                         area_ha: float | None = None) -> dict:
    rules = load_rules()
    crop_key = crop.strip().lower()
    if crop_key not in rules["crops"]:
        raise ValueError(f"Crop '{crop}' is not supported. Supported crops: {', '.join(supported_crops())}")

    base = rules["crops"][crop_key]
    mult = rules["rating_adjustment"]
    fert = rules["fertilizers"]
    soil = {"N": nitrogen, "P": phosphorus, "K": potassium}
    ratings = {n: _rating(n, v, rules) for n, v in soil.items()}
    need = {NUTRIENT_KEY[n]: round(base[NUTRIENT_KEY[n]] * mult[ratings[n]], 1) for n in soil}

    def pct(n):
        return int(mult[ratings[n]] * 100)

    # Phosphorus via DAP (also gives N), remaining N via urea, K via MOP
    dap_kg = need["P2O5"] / (fert["dap"]["P2O5"] / 100)
    n_from_dap = dap_kg * fert["dap"]["N"] / 100
    n_left = max(need["N"] - n_from_dap, 0.0)
    urea_kg = n_left / (fert["urea"]["N"] / 100)
    mop_kg = need["K2O"] / (fert["mop"]["K2O"] / 100)

    notes = []
    if n_from_dap > need["N"]:
        notes.append(
            f"DAP alone supplies {n_from_dap:.1f} kg N/ha, more than the {need['N']} kg N/ha target. "
            "Consider single super phosphate (see alternatives) to avoid excess nitrogen."
        )

    def line(name, kg, nutrient_text, reason):
        item = {"fertilizer": name, "kg_per_ha": round(kg, 1), "supplies": nutrient_text, "reason": reason}
        if area_ha:
            item["kg_for_your_area"] = round(kg * area_ha, 1)
        return item

    items = []
    if dap_kg > 0:
        items.append(line(
            "DAP (18-46-0)", dap_kg,
            f"{need['P2O5']} kg P2O5/ha and {n_from_dap:.1f} kg N/ha",
            f"Phosphorus: soil P is rated {ratings['P']}, so the standard {base['P2O5']} kg P2O5/ha is "
            f"adjusted to {pct('P')}% = {need['P2O5']} kg/ha. DAP is the P source and also supplies some N."))
    if urea_kg > 0:
        items.append(line(
            "Urea (46% N)", urea_kg, f"{n_left:.1f} kg N/ha",
            f"Nitrogen: soil N is rated {ratings['N']}, so the standard {base['N']} kg N/ha is adjusted to "
            f"{pct('N')}% = {need['N']} kg/ha. Urea covers what DAP does not ({n_left:.1f} kg N/ha)."))
    if mop_kg > 0:
        items.append(line(
            "MOP / Muriate of Potash (60% K2O)", mop_kg, f"{need['K2O']} kg K2O/ha",
            f"Potassium: soil K is rated {ratings['K']}, so the standard {base['K2O']} kg K2O/ha is "
            f"adjusted to {pct('K')}% = {need['K2O']} kg/ha."))

    ssp_kg = need["P2O5"] / (fert["ssp"]["P2O5"] / 100)
    urea_full = need["N"] / (fert["urea"]["N"] / 100)
    alternatives = [{
        "option": "Single super phosphate instead of DAP",
        "ssp_kg_per_ha": round(ssp_kg, 1),
        "urea_kg_per_ha": round(urea_full, 1),
        "mop_kg_per_ha": round(mop_kg, 1),
        "note": "SSP supplies phosphorus (and sulphur) but no nitrogen, so urea covers the full N target.",
    }]

    return {
        "crop": crop_key,
        "soil_test_ratings": ratings,
        "standard_dose_kg_per_ha": {k: base[k] for k in ("N", "P2O5", "K2O")},
        "nutrient_target_kg_per_ha": need,
        "fertilizers": items,
        "alternatives": alternatives,
        "notes": notes,
        "rules_status": rules["_meta"]["status"],
        "rules_source": rules["_meta"]["source"],
    }
