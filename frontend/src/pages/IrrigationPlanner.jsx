import { useEffect, useState } from "react";
import Alert from "../components/Alert.jsx";
import DataTable from "../components/DataTable.jsx";
import Field from "../components/Field.jsx";
import Spinner from "../components/Spinner.jsx";
import { api } from "../services/api.js";
import { num } from "../services/format.js";
import { useAction } from "../services/useAction.js";

const STAGES = [
  ["initial", "Initial (sowing to establishment)"],
  ["development", "Development (canopy growing)"],
  ["mid", "Mid-season (flowering / grain fill)"],
  ["late", "Late (maturity)"],
];
const SOILS = [
  ["loamy_sand", "Loamy sand (light, sandy)"],
  ["silt", "Silt"],
  ["silty_clay", "Silty clay (heavy, clayey)"],
];
const MOISTURE = [
  ["dry", "Dry (irrigation due now)"],
  ["moderate", "Moderate (half of available water used)"],
  ["wet", "Wet (near field capacity)"],
];
const EMPTY = { city: "", crop: "", growth_stage: "mid", soil_type: "silt", soil_moisture: "moderate", area: "", area_unit: "hectares" };

export default function IrrigationPlanner() {
  const [crops, setCrops] = useState(null);
  const [cropsError, setCropsError] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const plan = useAction(api.planIrrigation);
  const r = plan.data;

  useEffect(() => {
    api.irrigationCrops().then((d) => setCrops(d.crops)).catch((e) => setCropsError(e.message));
  }, []);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  function onSubmit(e) {
    e.preventDefault();
    plan.run({
      city: form.city.trim(),
      crop: form.crop,
      growth_stage: form.growth_stage,
      soil_type: form.soil_type,
      soil_moisture: form.soil_moisture,
      area: form.area === "" ? undefined : Number(form.area),
      area_unit: form.area_unit,
    });
  }

  return (
    <div>
      <h1 className="h3 mb-1">Irrigation planner</h1>
      <p className="text-muted small mb-4">
        A daily soil-water estimate using the 5-day forecast (FAO-56 method). It is an estimate, not a schedule
        to follow blindly: check soil moisture in your field.
      </p>
      <Alert>{cropsError}</Alert>
      {!crops && !cropsError && <Spinner label="Loading crops..." />}

      {crops && (
        <div className="row g-4">
          <div className="col-lg-4">
            <div className="card"><div className="card-body">
              <form onSubmit={onSubmit}>
                <Field label="City or district" id="city" hint="Used for the forecast, e.g. Mysuru,IN">
                  <input id="city" className="form-control" required minLength={2} value={form.city} onChange={set("city")} />
                </Field>
                <Field label="Crop" id="crop">
                  <select id="crop" className="form-select" required value={form.crop} onChange={set("crop")}>
                    <option value="">Choose a crop</option>
                    {crops.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </Field>
                <Field label="Growth stage" id="stage">
                  <select id="stage" className="form-select" value={form.growth_stage} onChange={set("growth_stage")}>
                    {STAGES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </Field>
                <Field label="Soil type" id="soil">
                  <select id="soil" className="form-select" value={form.soil_type} onChange={set("soil_type")}>
                    {SOILS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </Field>
                <Field label="Soil moisture now" id="moist">
                  <select id="moist" className="form-select" value={form.soil_moisture} onChange={set("soil_moisture")}>
                    {MOISTURE.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </select>
                </Field>
                <div className="row g-2">
                  <div className="col-7">
                    <Field label="Area (optional)" id="area">
                      <input id="area" type="number" step="any" min="0.01" className="form-control" value={form.area} onChange={set("area")} />
                    </Field>
                  </div>
                  <div className="col-5">
                    <Field label="Unit" id="unit">
                      <select id="unit" className="form-select" value={form.area_unit} onChange={set("area_unit")}>
                        <option value="hectares">hectares</option>
                        <option value="acres">acres</option>
                      </select>
                    </Field>
                  </div>
                </div>
                <button type="submit" className="btn btn-success w-100" disabled={plan.loading}>
                  {plan.loading ? "Planning..." : "Plan irrigation"}
                </button>
              </form>
              <Alert>{plan.error}</Alert>
            </div></div>
          </div>

          <div className="col-lg-8">
            {!r && !plan.loading && (
              <div className="card"><div className="card-body text-muted">Your irrigation plan will appear here.</div></div>
            )}
            {r && (
              <>
                <Alert type="info">{r.summary}</Alert>
                <Alert type="warning">{r.disclaimer}</Alert>

                {r.irrigation_events.length > 0 && (
                  <div className="card mb-3"><div className="card-body">
                    <h3 className="h6">Suggested irrigations</h3>
                    <DataTable
                      rows={r.irrigation_events}
                      columns={[
                        { label: "Date", get: (e) => e.date },
                        { label: "Net depth (mm)", get: (e) => num(e.net_mm, 1) },
                        { label: "Water per hectare (m³)", get: (e) => num(e.m3_per_ha, 1) },
                        { label: "For your area (m³)", get: (e) => (e.m3_for_your_area !== undefined ? num(e.m3_for_your_area, 1) : "-") },
                      ]}
                    />
                  </div></div>
                )}

                <div className="card mb-3"><div className="card-body">
                  <h3 className="h6">Daily water balance</h3>
                  <DataTable
                    rows={r.daily}
                    columns={[
                      { label: "Date", get: (d) => d.date },
                      { label: "ET₀ (mm)", get: (d) => num(d.et0_mm, 2) },
                      { label: "Crop use (mm)", get: (d) => num(d.etc_mm, 2) },
                      { label: "Rain (mm)", get: (d) => num(d.rain_mm, 1) },
                      { label: "Effective rain (mm)", get: (d) => num(d.effective_rain_mm, 1) },
                      { label: "Depletion (mm)", get: (d) => num(d.depletion_end_mm, 1) },
                      { label: "Irrigation (mm)", get: (d) => num(d.irrigation_net_mm, 1) },
                    ]}
                  />
                </div></div>

                <div className="card mb-3"><div className="card-body">
                  <h3 className="h6">Totals</h3>
                  <p className="mb-0">
                    Crop use {num(r.totals.etc_mm, 1)} mm, effective rain {num(r.totals.effective_rain_mm, 1)} mm,
                    irrigation {num(r.totals.irrigation_net_mm, 1)} mm net ({num(r.totals.irrigation_m3_per_ha, 1)} m³/ha).
                  </p>
                </div></div>

                <div className="card mb-3"><div className="card-body">
                  <h3 className="h6">Assumptions</h3>
                  <table className="table table-sm mb-0">
                    <tbody>
                      {Object.entries(r.assumptions).map(([k, v]) => (
                        <tr key={k}>
                          <th className="fw-normal text-muted" style={{ width: "35%" }}>{k.replace(/_/g, " ")}</th>
                          <td className="small">{String(v)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div></div>

                <ul className="small text-muted">
                  {r.notes.map((n) => <li key={n}>{n}</li>)}
                </ul>
                <p className="small text-muted">
                  Weather: {r.weather_source.location}, fetched {r.weather_source.fetched_at?.slice(0, 16).replace("T", " ")}
                  {r.weather_source.cached ? " (saved)" : ""}.
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
