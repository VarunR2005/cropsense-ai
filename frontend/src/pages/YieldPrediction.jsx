import { useEffect, useState } from "react";
import Alert from "../components/Alert.jsx";
import Field from "../components/Field.jsx";
import Spinner from "../components/Spinner.jsx";
import { api } from "../services/api.js";
import { num, pct } from "../services/format.js";
import { useAction } from "../services/useAction.js";

const EMPTY = { state: "", district: "", crop: "", season: "", year: 2015, area: "", area_unit: "hectares" };

export default function YieldPrediction() {
  const [opts, setOpts] = useState(null);
  const [optsError, setOptsError] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const predict = useAction(api.predictYield);

  useEffect(() => {
    api.yieldOptions().then(setOpts).catch((e) => setOptsError(e.message));
  }, []);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));
  const districts = opts?.districts_by_state?.[form.state] ?? [];

  function onSubmit(e) {
    e.preventDefault();
    predict.run({
      state: form.state,
      district: form.district,
      crop: form.crop,
      season: form.season,
      year: Number(form.year),
      area: Number(form.area),
      area_unit: form.area_unit,
    });
  }

  const r = predict.data;
  const hc = r?.historical_comparison;
  const m = r?.model_info?.metrics;

  return (
    <div>
      <h1 className="h3 mb-1">Crop yield prediction</h1>
      <p className="text-muted small mb-4">
        Estimates yield from location, crop, season and area, based on district-level history (1997-2015).
      </p>

      <Alert>{optsError}</Alert>
      {!opts && !optsError && <Spinner label="Loading options..." />}

      {opts && (
        <div className="row g-4">
          <div className="col-lg-5">
            <div className="card">
              <div className="card-body">
                <form onSubmit={onSubmit}>
                  <Field label="State" id="state">
                    <select id="state" className="form-select" required value={form.state}
                      onChange={(e) => setForm((f) => ({ ...f, state: e.target.value, district: "" }))}>
                      <option value="">Choose a state</option>
                      {Object.keys(opts.districts_by_state).map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </Field>
                  <Field label="District" id="district">
                    <select id="district" className="form-select" required disabled={!form.state}
                      value={form.district} onChange={set("district")}>
                      <option value="">Choose a district</option>
                      {districts.map((d) => <option key={d}>{d}</option>)}
                    </select>
                  </Field>
                  <Field label="Crop" id="crop">
                    <select id="crop" className="form-select" required value={form.crop} onChange={set("crop")}>
                      <option value="">Choose a crop</option>
                      {opts.crops.map((c) => <option key={c}>{c}</option>)}
                    </select>
                  </Field>
                  <Field label="Season" id="season">
                    <select id="season" className="form-select" required value={form.season} onChange={set("season")}>
                      <option value="">Choose a season</option>
                      {opts.seasons.map((s) => <option key={s}>{s}</option>)}
                    </select>
                  </Field>
                  <Field label="Year" id="year" hint="Up to 2100. The model learned from 1997-2015, so later years are extrapolations.">
                    <input id="year" type="number" className="form-control" required min={1990} max={2100}
                      value={form.year} onChange={set("year")} />
                  </Field>
                  <div className="row g-2">
                    <div className="col-7">
                      <Field label="Land area" id="area">
                        <input id="area" type="number" step="any" min="0.01" className="form-control" required
                          value={form.area} onChange={set("area")} />
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
                  <button type="submit" className="btn btn-success w-100" disabled={predict.loading}>
                    {predict.loading ? "Predicting..." : "Predict yield"}
                  </button>
                </form>
                <Alert>{predict.error}</Alert>
              </div>
            </div>
          </div>

          <div className="col-lg-7">
            {!r && !predict.loading && (
              <div className="card"><div className="card-body text-muted">Your prediction will appear here.</div></div>
            )}
            {r && (
              <div className="card">
                <div className="card-body">
                  <h2 className="h5">{r.crop} in {r.district}, {r.state}</h2>
                  <div className="row g-3 my-2">
                    <div className="col-sm-6">
                      <div className="big-number">{num(r.predicted_yield_t_per_ha, 2)} <small>t/ha</small></div>
                      <div className="text-muted">Predicted yield per hectare</div>
                    </div>
                    <div className="col-sm-6">
                      <div className="big-number">{num(r.estimated_total_production_tonnes, 2)} <small>t</small></div>
                      <div className="text-muted">Estimated total for {num(r.area_ha, 2)} ha</div>
                    </div>
                  </div>

                  <h3 className="h6 mt-3">Compared with history</h3>
                  {hc.crop_state_mean_t_per_ha !== null ? (
                    <p className="mb-1">
                      Average for {r.crop} in {r.state} ({hc.crop_state_records} records):
                      {" "}<strong>{num(hc.crop_state_mean_t_per_ha, 2)} t/ha</strong>,
                      {" "}this prediction is <strong>{pct(hc.difference_vs_state_mean_pct)}</strong>.
                    </p>
                  ) : (
                    <p className="mb-1 text-muted">No history for {r.crop} in {r.state}.</p>
                  )}
                  {hc.crop_national_mean_t_per_ha !== null && (
                    <p className="small text-muted">National average for {r.crop}: {num(hc.crop_national_mean_t_per_ha, 2)} t/ha.</p>
                  )}

                  <h3 className="h6 mt-3">How reliable is the model?</h3>
                  <p className="small mb-1">
                    Tested on {r.model_info.test_years.join(", ")} (years it did not learn from):
                    average error <strong>{num(m.mae_t_per_ha, 2)} t/ha</strong> versus{" "}
                    <strong>{num(m.baseline_crop_mean_mae_t_per_ha, 2)} t/ha</strong> for a simple per-crop average.
                  </p>
                  <p className="small text-muted">
                    Soil and weather inputs are not used by this model; they are only stored with your record.
                  </p>

                  <ul className="small text-muted mb-0">
                    {r.notes.map((n) => <li key={n}>{n}</li>)}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
