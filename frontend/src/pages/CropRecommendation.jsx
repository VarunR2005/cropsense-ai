import { useState } from "react";
import Alert from "../components/Alert.jsx";
import Field from "../components/Field.jsx";
import { api } from "../services/api.js";
import { num } from "../services/format.js";
import { useAction } from "../services/useAction.js";

const FIELDS = [
  ["nitrogen", "Nitrogen (N), kg/ha", 90],
  ["phosphorus", "Phosphorus (P), kg/ha", 42],
  ["potassium", "Potassium (K), kg/ha", 43],
  ["temperature", "Temperature, °C", 21],
  ["humidity", "Humidity, %", 82],
  ["ph", "Soil pH", 6.5],
  ["rainfall", "Rainfall, mm", 200],
];
const LABELS = { N: "Nitrogen", P: "Phosphorus", K: "Potassium", temperature: "Temperature °C",
  humidity: "Humidity %", ph: "pH", rainfall: "Rainfall mm" };

export default function CropRecommendation() {
  const [form, setForm] = useState(Object.fromEntries(FIELDS.map(([k, , v]) => [k, v])));
  const recommend = useAction(api.recommendCrops);
  const res = recommend.data;

  const onSubmit = (e) => {
    e.preventDefault();
    const body = Object.fromEntries(Object.entries(form).map(([k, v]) => [k, Number(v)]));
    recommend.run(body);
  };

  return (
    <div>
      <h1 className="h3 mb-1">Crop recommendation</h1>
      <p className="text-muted small mb-4">
        Enter your soil test results and local weather. The top three crops are ranked by a model
        trained on a public crop dataset.
      </p>
      <div className="row g-4">
        <div className="col-lg-4">
          <div className="card"><div className="card-body">
            <form onSubmit={onSubmit}>
              {FIELDS.map(([k, label]) => (
                <Field key={k} label={label} id={k}>
                  <input id={k} type="number" step="any" className="form-control" required
                    value={form[k]} onChange={(e) => setForm((f) => ({ ...f, [k]: e.target.value }))} />
                </Field>
              ))}
              <button type="submit" className="btn btn-success w-100" disabled={recommend.loading}>
                {recommend.loading ? "Analysing..." : "Recommend crops"}
              </button>
            </form>
            <Alert>{recommend.error}</Alert>
          </div></div>
        </div>

        <div className="col-lg-8">
          {!res && !recommend.loading && (
            <div className="card"><div className="card-body text-muted">Your top three crops will appear here.</div></div>
          )}
          {res && (
            <>
              {res.warnings.map((w) => <div key={w} className="alert alert-warning py-2">{w}</div>)}
              <div className="row g-3">
                {res.recommendations.map((c, i) => (
                  <div className="col-12" key={c.crop}>
                    <div className="card"><div className="card-body">
                      <div className="d-flex justify-content-between align-items-center">
                        <h2 className="h5 mb-0 text-capitalize">{i + 1}. {c.crop}</h2>
                        <span className="badge bg-success fs-6">{(c.suitability_score * 100).toFixed(1)}% score</span>
                      </div>
                      <details className="mt-2">
                        <summary className="small">Typical growing range for {c.crop} (training data, 5th-95th percentile)</summary>
                        <div className="table-responsive mt-2">
                          <table className="table table-sm mb-0">
                            <thead><tr><th>Factor</th><th>Low</th><th>High</th></tr></thead>
                            <tbody>
                              {Object.entries(c.growing_requirements).map(([k, v]) => (
                                <tr key={k}><td>{LABELS[k] ?? k}</td><td>{num(v.low, 1)}</td><td>{num(v.high, 1)}</td></tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </details>
                    </div></div>
                  </div>
                ))}
              </div>
              <ul className="small text-muted mt-3">
                {res.notes.map((n) => <li key={n}>{n}</li>)}
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
