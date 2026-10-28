"""
Irrigation planner: FAO-56 style daily soil-water balance driven by the weather forecast.

  ET0  : Hargreaves (FAO-56 Eq. 52) from forecast Tmin/Tmax and extraterrestrial radiation (Eq. 21)
  ETc  : Kc x ET0 (FAO-56 Eq. 58), Kc from Table 12 by growth stage
  TAW  : 1000 (thetaFC - thetaWP) Zr, RAW = p TAW (Eq. 82, 83)
  Rule : irrigate when root-zone depletion reaches RAW; net depth = depletion
This is an ESTIMATE. Assumptions are returned with every result.
"""
import json
import math
from datetime import date
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).resolve().parents[1] / "ml" / "data" / "irrigation_rules.json"
STAGES = ("initial", "development", "mid", "late")
RAIN_EFFICIENCY = 0.8  # ASSUMPTION (not from FAO): 20% of rain lost to runoff


@lru_cache(maxsize=1)
def load_rules() -> dict:
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def supported_crops() -> list[str]:
    return sorted(load_rules()["crops"].keys())


def extraterrestrial_radiation_mm(lat_deg: float, doy: int) -> float:
    """FAO-56 Eq. 21, returned as equivalent evaporation in mm/day."""
    phi = math.radians(lat_deg)
    dr = 1 + 0.033 * math.cos(2 * math.pi * doy / 365)
    delta = 0.409 * math.sin(2 * math.pi * doy / 365 - 1.39)
    x = max(-1.0, min(1.0, -math.tan(phi) * math.tan(delta)))
    ws = math.acos(x)
    gsc = 0.0820  # MJ m-2 min-1
    ra = (24 * 60 / math.pi) * gsc * dr * (
        ws * math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta) * math.sin(ws))
    return ra * 0.408


def hargreaves_et0(tmin: float, tmax: float, ra_mm: float) -> float:
    """FAO-56 Eq. 52 (mm/day)."""
    tmean = (tmax + tmin) / 2
    return max(0.0023 * (tmean + 17.8) * math.sqrt(max(tmax - tmin, 0.0)) * ra_mm, 0.0)


def stage_kc(crop: dict, stage: str) -> float:
    """Initial/mid use table values; development and late use the stage midpoint of FAO's linear ramps."""
    if stage == "initial":
        return crop["kc_ini"]
    if stage == "mid":
        return crop["kc_mid"]
    if stage == "development":
        return (crop["kc_ini"] + crop["kc_mid"]) / 2
    return (crop["kc_mid"] + crop["kc_end"]) / 2


def stage_root_depth(crop: dict, stage: str, early_m: float) -> float:
    """Simplification: 0.3 m early (as in FAO Example 38), FAO's smaller Zr value from mid-season on."""
    zr_full = crop["root_min_m"]
    if stage == "initial":
        return min(early_m, zr_full)
    if stage == "development":
        return (min(early_m, zr_full) + zr_full) / 2
    return zr_full


def taw_raw(awc_mm_per_m: float, zr_m: float, p: float) -> tuple[float, float]:
    taw = awc_mm_per_m * zr_m  # Eq. 82
    return taw, p * taw        # Eq. 83


def plan_irrigation(*, weather: dict, crop: str, growth_stage: str, soil_type: str,
                    soil_moisture: str = "moderate", area_ha: float | None = None) -> dict:
    rules = load_rules()
    crop_key = crop.strip().lower()
    if crop_key not in rules["crops"]:
        raise ValueError(f"Crop '{crop}' is not supported. Supported crops: {', '.join(supported_crops())}")
    if growth_stage not in STAGES:
        raise ValueError(f"growth_stage must be one of {', '.join(STAGES)}")
    if soil_type not in rules["soils"]:
        raise ValueError(f"soil_type must be one of {', '.join(rules['soils'])}")
    if soil_moisture not in ("dry", "moderate", "wet"):
        raise ValueError("soil_moisture must be dry, moderate or wet")

    c = rules["crops"][crop_key]
    paddy = bool(c.get("paddy"))
    soil = rules["soils"][soil_type]
    lat = (weather.get("location") or {}).get("latitude")
    if lat is None:
        raise ValueError("The weather data has no latitude, so evapotranspiration cannot be estimated.")

    kc = stage_kc(c, growth_stage)
    zr = stage_root_depth(c, growth_stage, rules["stage_root_depth_m_early"])
    taw, raw0 = taw_raw(soil["awc_mm_per_m"], zr, c["p"])
    dr_prev = {"wet": 0.0, "moderate": 0.5 * raw0, "dry": raw0}[soil_moisture]

    rows, events = [], []
    for d in weather.get("daily_forecast", []):
        tmin, tmax = d.get("temp_min_c"), d.get("temp_max_c")
        if tmin is None or tmax is None:
            rows.append({"date": d["date"], "note": "skipped: temperature missing"})
            continue
        frac = min(d.get("slots", 8), 8) / 8  # partial first/last forecast days
        doy = date.fromisoformat(d["date"]).timetuple().tm_yday
        et0_full = hargreaves_et0(tmin, tmax, extraterrestrial_radiation_mm(lat, doy))
        et0 = et0_full * frac
        etc = kc * et0
        rain = d.get("rain_mm") or 0.0
        pe = 0.0 if rain < 0.2 * et0 else RAIN_EFFICIENCY * rain  # FAO: rain < 0.2 ET0 is ignored

        row = {"date": d["date"], "partial_day": frac < 1, "et0_mm": round(et0, 2), "etc_mm": round(etc, 2),
               "rain_mm": round(rain, 1), "effective_rain_mm": round(pe, 1)}
        if paddy:
            row["net_requirement_mm"] = round(max(etc - pe, 0.0), 1)
            rows.append(row)
            continue

        p_day = min(max(c["p"] + 0.04 * (5 - kc * et0_full), 0.1), 0.8)  # FAO-56 footnote to Table 22
        raw = p_day * taw
        dr_start = max(dr_prev - pe, 0.0)
        irrigation = 0.0
        if dr_start >= raw:
            irrigation, dr_start = dr_start, 0.0
        dr_end = min(dr_start + etc, taw)
        row.update({"raw_mm": round(raw, 1), "depletion_end_mm": round(dr_end, 1),
                    "irrigation_net_mm": round(irrigation, 1)})
        if irrigation > 0:
            ev = {"date": d["date"], "net_mm": round(irrigation, 1), "m3_per_ha": round(irrigation * 10, 1)}
            if area_ha:
                ev["m3_for_your_area"] = round(irrigation * 10 * area_ha, 1)
            events.append(ev)
        rows.append(row)
        dr_prev = dr_end

    used = [r for r in rows if "etc_mm" in r]
    totals = {
        "etc_mm": round(sum(r["etc_mm"] for r in used), 1),
        "effective_rain_mm": round(sum(r["effective_rain_mm"] for r in used), 1),
        "irrigation_net_mm": round(sum(e["net_mm"] for e in events), 1),
    }
    totals["irrigation_m3_per_ha"] = round(totals["irrigation_net_mm"] * 10, 1)
    if area_ha:
        totals["irrigation_m3_for_your_area"] = round(totals["irrigation_net_mm"] * 10 * area_ha, 1)

    if paddy:
        summary = (f"Paddy rice: crop water use over the forecast window is about {totals['etc_mm']} mm, "
                   f"with about {totals['effective_rain_mm']} mm of effective rain. A day-by-day net requirement is "
                   "listed. Seepage/percolation and puddling water are NOT included; keep standing water as "
                   "your local recommendation advises.")
    elif events:
        e = events[0]
        summary = (f"First irrigation suggested on {e['date']}: about {e['net_mm']} mm net "
                   f"({e['m3_per_ha']} m3 per hectare). {len(events)} irrigation(s) in the forecast window, "
                   f"{totals['irrigation_net_mm']} mm net in total.")
    else:
        summary = ("No irrigation is suggested in the forecast window: stored soil water plus forecast rain "
                   "should cover crop use. Check your soil moisture in the field.")

    notes = [
        "ESTIMATE only, not guaranteed agricultural advice. Verify with field soil-moisture checks and local experts.",
        "Water amounts are NET depths reaching the root zone. The volume you must pump or release is larger and depends on your irrigation method and losses.",
        "Only the 5-day forecast window is covered; run it again as new forecasts arrive.",
    ]
    if c.get("note"):
        notes.append(f"Crop data note: {c['note']}")

    return {
        "crop": crop_key, "growth_stage": growth_stage, "soil_type": soil_type,
        "soil_moisture_start": soil_moisture,
        "summary": summary,
        "irrigation_events": events,
        "daily": rows,
        "totals": totals,
        "assumptions": {
            "kc": round(kc, 3),
            "kc_source": "FAO-56 Table 12 (sub-humid climate); development/late use the stage midpoint of the linear ramp",
            "root_depth_m": round(zr, 2),
            "root_depth_rule": "FAO's smaller Zr value for scheduling, scaled by stage (0.3 m early) - a simplification",
            "soil_water_holding_mm_per_m": soil["awc_mm_per_m"],
            "taw_mm": round(taw, 1), "raw_mm_at_start": round(raw0, 1), "depletion_fraction_p": c["p"],
            "et0_method": "Hargreaves (FAO-56 Eq. 52) from forecast Tmin/Tmax; rough, can be off by a wide margin",
            "effective_rain": f"{int(RAIN_EFFICIENCY * 100)}% of rain counted (my assumption for runoff); rain below 0.2 x ET0 ignored (FAO-56)",
            "initial_moisture": {"wet": "field capacity", "moderate": "half of readily available water used",
                                 "dry": "readily available water used up (irrigation due)"}[soil_moisture],
            "not_included": "capillary rise, salinity, runoff modelling, crop stress effects, local Kc adjustments for humidity and wind",
        },
        "notes": notes,
    }
