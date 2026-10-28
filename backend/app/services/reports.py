"""
Report builders and exporters (JSON structure -> CSV / PDF).

Regional report : aggregates the historical district-level dataset (crop_production.csv).
Farm report     : the logged-in user's own saved yield predictions.
Every report carries its data source and the dates it relates to.
"""
import csv
import io
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd

DATASET_NAME = "Crop Production in India (Kaggle: crop_production.csv)"
CLEANING = ("Rows with missing or zero area, or missing production, were removed; coconut excluded "
            "(recorded in nuts, not tonnes); yields above 150 t/ha dropped as data errors; names trimmed.")


class ReportDataError(Exception):
    """The data needed for a report is not available (dataset missing, etc.)."""


class NoRecordsError(Exception):
    """The filters matched nothing."""


# ---------------------------------------------------------------- data loading
@lru_cache(maxsize=2)
def _load_cached(path_str: str, mtime: float) -> pd.DataFrame:
    from app.ml.train_yield import load_and_clean  # imported lazily: it pulls in scikit-learn
    return load_and_clean(Path(path_str))


def load_dataset() -> tuple[pd.DataFrame, dict]:
    from app.ml.train_yield import DATASET_PATH
    if not DATASET_PATH.exists():
        raise ReportDataError(
            "Dataset not found. Save the Kaggle file as backend/datasets/crop_production.csv "
            "(see the notes in app/ml/train_yield.py)."
        )
    try:
        df = _load_cached(str(DATASET_PATH), DATASET_PATH.stat().st_mtime)
    except SystemExit as e:  # load_and_clean exits on a bad file
        raise ReportDataError(str(e))
    info = {
        "name": DATASET_NAME,
        "data_as_of": datetime.fromtimestamp(DATASET_PATH.stat().st_mtime, tz=timezone.utc).date().isoformat(),
        "covers_years": [int(df["Crop_Year"].min()), int(df["Crop_Year"].max())],
        "cleaning": CLEANING,
        "licence_note": "Original publisher and licence: see the dataset's Kaggle page.",
    }
    return df, info


# ---------------------------------------------------------------- helpers
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _filter(df: pd.DataFrame, state, district, crop, season) -> pd.DataFrame:
    out = df
    for col, val in (("State_Name", state), ("District_Name", district), ("Crop", crop), ("Season", season)):
        if val:
            out = out[out[col].str.lower() == val.strip().lower()]
    return out


def _summarise(frame: pd.DataFrame, by: str) -> pd.DataFrame:
    t = frame.groupby(by).agg(area_ha=("Area", "sum"), production_t=("Production", "sum"),
                              records=("Production", "size")).reset_index()
    t["yield_t_per_ha"] = t["production_t"] / t["area_ha"]
    return t


def _table(name: str, columns: list[str], frame: pd.DataFrame) -> dict:
    rows = []
    for rec in frame[columns].itertuples(index=False):
        rows.append([None if pd.isna(v) else (round(float(v), 3) if isinstance(v, float) else
                     (int(v) if hasattr(v, "item") and isinstance(v.item(), int) else v)) for v in rec])
    return {"name": name, "columns": columns, "rows": rows}


# ---------------------------------------------------------------- regional report
def build_regional_report(df: pd.DataFrame, source: dict, *, state=None, district=None, crop=None, season=None) -> dict:
    f = _filter(df, state, district, crop, season)
    if f.empty:
        raise NoRecordsError("No records match these filters. Check the spelling of state, district, crop and season.")

    area, prod = float(f["Area"].sum()), float(f["Production"].sum())
    by_year = _summarise(f, "Crop_Year").sort_values("Crop_Year").rename(columns={"Crop_Year": "year"})
    by_year["area_ha"] = by_year["area_ha"].round(1)
    by_year["production_t"] = by_year["production_t"].round(1)
    tables = [_table("Yield by year", ["year", "area_ha", "production_t", "yield_t_per_ha", "records"], by_year)]
    charts = [{"title": "Yield by year (t/ha)", "type": "line", "x": [int(y) for y in by_year["year"]],
               "series": [{"name": "yield t/ha", "values": [round(float(v), 3) for v in by_year["yield_t_per_ha"]]}]}]

    if not district:
        group_col = "District_Name" if state else "State_Name"
        label = "district" if state else "state"
        grp = (_summarise(f, group_col).sort_values("production_t", ascending=False).head(15)
               .rename(columns={group_col: label}))
        grp["area_ha"], grp["production_t"] = grp["area_ha"].round(1), grp["production_t"].round(1)
        tables.append(_table(f"Top {label}s by production", [label, "area_ha", "production_t", "yield_t_per_ha", "records"], grp))
        use_yield = bool(crop)
        charts.append({"title": f"{label.title()}s: " + ("yield (t/ha)" if use_yield else "production (t)"),
                       "type": "bar", "x": [str(x) for x in grp[label]],
                       "series": [{"name": "yield t/ha" if use_yield else "production t",
                                   "values": [round(float(v), 2) for v in grp["yield_t_per_ha" if use_yield else "production_t"]]}]})
    if not season:
        s = _summarise(f, "Season").sort_values("production_t", ascending=False).rename(columns={"Season": "season"})
        s["area_ha"], s["production_t"] = s["area_ha"].round(1), s["production_t"].round(1)
        tables.append(_table("By season", ["season", "area_ha", "production_t", "yield_t_per_ha", "records"], s))
    if not crop:
        c = (_summarise(f, "Crop").sort_values("production_t", ascending=False).head(10).rename(columns={"Crop": "crop"}))
        c["area_ha"], c["production_t"] = c["area_ha"].round(1), c["production_t"].round(1)
        tables.append(_table("Top crops by production", ["crop", "area_ha", "production_t", "yield_t_per_ha", "records"], c))

    notes = ["Yield = total production / total area (t/ha), so large areas weigh more."]
    if not crop:
        notes.append("No crop filter: averaging yields across different crops is not meaningful. Filter by a crop to compare yields.")
    return {
        "title": "Regional crop yield report", "report_type": "regional", "generated_at": _now(),
        "filters": {"state": state, "district": district, "crop": crop, "season": season},
        "source": source,
        "summary": {"records": int(len(f)), "years": [int(f["Crop_Year"].min()), int(f["Crop_Year"].max())],
                    "total_area_ha": round(area, 1), "total_production_t": round(prod, 1),
                    "weighted_yield_t_per_ha": round(prod / area, 3) if area else None},
        "tables": tables, "charts": charts, "notes": notes,
    }


# ---------------------------------------------------------------- farm report
def build_farm_report(predictions: list[dict], model_info: dict | None, *, state=None, district=None,
                      crop=None, season=None) -> dict:
    def keep(p):
        return all(not v or str(p[k]).lower() == v.strip().lower()
                   for k, v in (("state", state), ("district", district), ("crop", crop), ("season", season)))

    rows = [p for p in predictions if keep(p)]
    if not rows:
        raise NoRecordsError("You have no saved predictions matching these filters.")

    table_rows = []
    for p in rows:
        hm = p.get("historical_mean_t_per_ha")
        diff = round((p["predicted_yield_t_per_ha"] - hm) / hm * 100, 1) if hm else None
        table_rows.append([p["created_at"][:10], p["state"], p["district"], p["crop"], p["season"], p["year"],
                           round(p["area_ha"], 2), round(p["predicted_yield_t_per_ha"], 3),
                           round(p["predicted_production_tonnes"], 2),
                           round(hm, 3) if hm else None, diff])
    columns = ["date", "state", "district", "crop", "season", "year", "area_ha", "predicted_yield_t_per_ha",
               "predicted_production_t", "historical_mean_t_per_ha", "difference_vs_history_pct"]

    recent = table_rows[:12][::-1]  # chronological
    charts = [{"title": "Predicted vs historical mean yield (t/ha), latest predictions", "type": "bar",
               "x": [f"{r[3]} {r[1]}" for r in recent],
               "series": [{"name": "predicted", "values": [r[7] for r in recent]},
                          {"name": "historical mean", "values": [r[9] for r in recent]}]}]
    total_area = sum(r[6] for r in table_rows)
    return {
        "title": "Farm-level yield report (your saved predictions)", "report_type": "farm", "generated_at": _now(),
        "filters": {"state": state, "district": district, "crop": crop, "season": season},
        "source": {"name": "Your saved CropSense yield predictions",
                   "data_as_of": max(r[0] for r in table_rows),
                   "model": model_info or "model information unavailable (model not trained on this server)",
                   "historical_mean": "Mean yield for the same crop and state in the model's training years"},
        "summary": {"predictions": len(table_rows), "total_area_ha": round(total_area, 2),
                    "total_predicted_production_t": round(sum(r[8] for r in table_rows), 2)},
        "tables": [{"name": "Saved predictions", "columns": columns, "rows": table_rows}],
        "charts": charts,
        "notes": ["Predictions are statistical estimates, not guarantees. Historical mean is blank where the "
                  "model has no history for that crop and state."],
    }


# ---------------------------------------------------------------- exporters
def report_to_csv(report: dict) -> str:
    """First table, with the data source and dates repeated on every row so they survive in Excel."""
    t = report["tables"][0]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(t["columns"] + ["source", "data_as_of", "report_generated_utc"])
    for r in t["rows"]:
        w.writerow(r + [report["source"]["name"], report["source"]["data_as_of"], report["generated_at"]])
    return buf.getvalue()


def _fmt(v) -> str:
    if v is None:
        return "-"
    return f"{v:,.2f}" if isinstance(v, float) else str(v)


def _chart_drawing(chart: dict, width=480, height=210):
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors

    palette = [colors.HexColor("#2e7d32"), colors.HexColor("#a1887f")]
    series = [[(v if v is not None else 0) for v in s["values"]] for s in chart["series"]]
    d = Drawing(width, height)
    c = HorizontalLineChart() if chart["type"] == "line" else VerticalBarChart()
    c.x, c.y, c.width, c.height = 45, 55, width - 65, height - 85
    c.data = series
    c.categoryAxis.categoryNames = [str(x) for x in chart["x"]]
    c.categoryAxis.labels.angle = 30
    c.categoryAxis.labels.boxAnchor = "ne"
    c.categoryAxis.labels.fontSize = 6
    c.valueAxis.labels.fontSize = 7
    c.valueAxis.valueMin = 0
    for i in range(len(series)):
        if chart["type"] == "line":
            c.lines[i].strokeColor, c.lines[i].strokeWidth = palette[i % 2], 2
        else:
            c.bars[i].fillColor = palette[i % 2]
    d.add(c)
    d.add(String(width / 2, height - 12, chart["title"], textAnchor="middle", fontSize=9))
    if len(series) > 1:
        names = "   ".join(f"{['green', 'brown'][i % 2]}: {s['name']}" for i, s in enumerate(chart["series"]))
        d.add(String(10, 8, names, fontSize=7))
    return d


def report_to_pdf(report: dict, max_rows: int = 25) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    ss = getSampleStyleSheet()
    small = ss["BodyText"].clone("small", fontSize=8, leading=10)
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm, title=report["title"])
    story = [Paragraph(escape(report["title"]), ss["Title"])]

    active = {k: v for k, v in report["filters"].items() if v}
    story.append(Paragraph("Filters: " + (escape(", ".join(f"{k}={v}" for k, v in active.items())) or "none (all records)"), small))
    story.append(Paragraph("Generated (UTC): " + escape(report["generated_at"]), small))
    src = report["source"]
    story.append(Paragraph("<b>Data source:</b> " + escape(str(src["name"])) + " &nbsp; <b>Data as of:</b> " + escape(str(src["data_as_of"])), small))
    for k, v in src.items():
        if k not in ("name", "data_as_of"):
            story.append(Paragraph(f"{escape(k.replace('_', ' ').title())}: {escape(str(v))}", small))
    story.append(Spacer(1, 6 * mm))

    green = colors.HexColor("#2e7d32")
    summary = [[k.replace("_", " "), _fmt(v) if not isinstance(v, list) else " - ".join(map(str, v))]
               for k, v in report["summary"].items()]
    st = Table(summary, colWidths=[60 * mm, 60 * mm])
    st.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f5e9"))]))
    story += [st, Spacer(1, 6 * mm)]

    for chart in report["charts"]:
        story += [_chart_drawing(chart), Spacer(1, 4 * mm)]

    for t in report["tables"]:
        story.append(Paragraph(escape(t["name"]), ss["Heading3"]))
        data = [t["columns"]] + [[_fmt(v) for v in r] for r in t["rows"][:max_rows]]
        tb = Table(data, repeatRows=1)
        tb.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 7), ("BACKGROUND", (0, 0), (-1, 0), green),
                                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f8e9")])]))
        story.append(tb)
        if len(t["rows"]) > max_rows:
            story.append(Paragraph(f"Showing {max_rows} of {len(t['rows'])} rows. Use the CSV export for all rows.", small))
        story.append(Spacer(1, 4 * mm))

    for n in report["notes"]:
        story.append(Paragraph("Note: " + escape(n), small))
    doc.build(story)
    return buf.getvalue()
