import { useEffect, useState } from "react";
import Alert from "../components/Alert.jsx";
import DataTable from "../components/DataTable.jsx";
import Field from "../components/Field.jsx";
import Spinner from "../components/Spinner.jsx";
import { api } from "../services/api.js";
import { num } from "../services/format.js";
import { useAction } from "../services/useAction.js";

const EMPTY = { crop: "", nitrogen: 200, phosphorus: 8, potassium: 150, area: "", area_unit: "hectares" };
const RATING_BADGE = { low: "bg-warning text-dark", medium: "bg-success", high: "bg-info text-dark" };

export default function FertilizerRecommendation() {
  const [crops, setCrops] = useState(null);
  const [cropsError, setCropsError] = useState(null);
  const [form, setForm] = useState(EMPTY);
  const rec = useAction(api.recommendFertilizer);
  const r = rec.data;

  useEffect(() => {
    api.fertilizerCrops().then((d) => setCrops(d.crops)).catch((e) => setCropsError(e.message));
  }, []);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  function onSubmit(e) {
    e.preventDefault();
    rec.run({
      crop: form.crop,
      nitrogen: Number(form.nitrogen),
      phosphorus: Number(form.phosphorus),
      potassium: Number(form.potassium),
      area: form.area === "" ? undefined : Number(form.area),
      area_unit: form.area_unit,
    });
  }

  return (
    <div>
      <h1 className="h3 mb-1">Fertilizer recommendation</h1>
      <p className="text-muted small mb-4">
        Estimates fertilizer quantities from your soil test values (kg/ha). These are rule-based estimates,
        not a substitute for a soil test and local advice.
      </p>
      <Alert>{cropsError}</Alert>
      {!crops && !cropsError && <Spinner label="Loading crops..." />}

      {crops && (
        <div className="row g-4">
          <div className="col-lg-4">
            <div className="card"><div className="card-body">
              <form onSubmit={onSubmit}>
                <Field label="Crop" id="crop">
                  <select id="crop" className="form-select" required value={form.crop} onChange={set("crop")}>
                    <option value="">Choose a crop</option>
                    {crops.map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </Field>
                <Field label="Available nitrogen (N), kg/ha" id="n" hint="From your soil test (Soil Health Card values).">
                  <input id="n" type="number" step="any" min="0" className="form-control" required value={form.nitrogen} onChange={set("nitrogen")} />
                </Field>
                <Field label="Available phosphorus (P), kg/ha" id="p">
                  <input id="p" type="number" step="any" min="0" className="form-control" required value={form.phosphorus} onChange={set("phosphorus")} />
                </Field>
                <Field label="Available potassium (K), kg/ha" id="k">
                  <input id="k" type="number" step="any" min="0" className="form-control" required value={form.potassium} onChange={set("potassium")} />
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
                <button type="submit" className="btn btn-success w-100" disabled={rec.loading}>
                  {rec.loading ? "Calculating..." : "Calculate fertilizer"}
                </button>
              </form>
              <Alert>{rec.error}</Alert>
            </div></div>
          </div>

          <div className="col-lg-8">
            {!r && !rec.loading && (
              <div className="card"><div className="card-body text-muted">Fertilizer quantities will appear here.</div></div>
            )}
            {r && (
              <>
                <Alert type="warning">{r.disclaimer}</Alert>
                <div className="card mb-3"><div className="card-body">
                  <h2 className="h5 text-capitalize">{r.crop}</h2>
                  <p className="mb-2">
                    Soil test ratings:{" "}
                    {Object.entries(r.soil_test_ratings).map(([k, v]) => (
                      <span key={k} className={`badge ${RATING_BADGE[v]} me-1`}>{k}: {v}</span>
                    ))}
                  </p>
                  <p className="small mb-0">
                    Target nutrients per hectare: N {num(r.nutrient_target_kg_per_ha.N, 1)} kg,
                    P<sub>2</sub>O<sub>5</sub> {num(r.nutrient_target_kg_per_ha.P2O5, 1)} kg,
                    K<sub>2</sub>O {num(r.nutrient_target_kg_per_ha.K2O, 1)} kg
                  </p>
                </div></div>

                <div className="card mb-3"><div className="card-body">
                  <h3 className="h6">Fertilizer quantities</h3>
                  <DataTable
                    rows={r.fertilizers}
                    columns={[
                      { label: "Fertilizer", get: (f) => f.fertilizer },
                      { label: "kg/ha", get: (f) => num(f.kg_per_ha, 1) },
                      { label: "For your area (kg)", get: (f) => (f.kg_for_your_area !== undefined ? num(f.kg_for_your_area, 1) : "-") },
                    ]}
                  />
                  <div className="mt-3">
                    {r.fertilizers.map((f) => (
                      <p key={f.fertilizer} className="small mb-2">
                        <strong>{f.fertilizer.split(" ")[0]}:</strong> {f.reason}
                      </p>
                    ))}
                  </div>
                </div></div>

                {r.alternatives.map((a) => (
                  <div key={a.option} className="card mb-3"><div className="card-body small">
                    <strong>Alternative: {a.option}</strong> - SSP {num(a.ssp_kg_per_ha, 1)} kg/ha, urea {num(a.urea_kg_per_ha, 1)} kg/ha, MOP {num(a.mop_kg_per_ha, 1)} kg/ha. {a.note}
                  </div></div>
                ))}
                {r.notes.map((n) => <Alert key={n} type="warning">{n}</Alert>)}
                <p className="small text-muted">Rules source: {r.rules_source}</p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
