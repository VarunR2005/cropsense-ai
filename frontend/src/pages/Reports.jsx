import { useEffect, useState } from "react";
import Alert from "../components/Alert.jsx";
import DataTable from "../components/DataTable.jsx";
import Field from "../components/Field.jsx";
import ReportChart from "../components/ReportChart.jsx";
import Spinner from "../components/Spinner.jsx";
import { api, downloadReport } from "../services/api.js";
import { num } from "../services/format.js";
import { useAction } from "../services/useAction.js";

const KINDS = [
  ["yield", "Regional yield report (historical district data)"],
  ["farm", "Your farm report (your saved predictions)"],
];
const EMPTY = { state: "", district: "", crop: "", season: "" };

const cell = (v) =>
  v === null || v === undefined ? "-" : typeof v === "number" && !Number.isInteger(v) ? num(v, 3) : String(v);

export default function Reports() {
  const [opts, setOpts] = useState(null);
  const [optsError, setOptsError] = useState(null);
  const [kind, setKind] = useState("yield");
  const [filters, setFilters] = useState(EMPTY);
  const load = useAction(api.report);
  const dl = useAction(downloadReport);
  const report = load.data;

  useEffect(() => {
    api.yieldOptions().then(setOpts).catch((e) => setOptsError(e.message));
  }, []);

  const districts = opts?.districts_by_state?.[filters.state] ?? [];
  const params = () => ({ ...filters });

  // Dropdowns only offer names the data actually contains, so filters cannot misspell them.
  const pick = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value }));
  const pickState = (e) => setFilters((f) => ({ ...f, state: e.target.value, district: "" }));

  return (
    <div>
      <h1 className="h3 mb-1">Reports</h1>
      <p className="text-muted small mb-4">
        View a report on screen, or download it as CSV (for Excel) or PDF. Every report shows its data source
        and date. Leave a filter blank to include everything.
      </p>

      <Alert>{optsError}</Alert>

      <div className="card mb-4"><div className="card-body">
        <form className="row g-3" onSubmit={(e) => { e.preventDefault(); load.run(kind, params()); }}>
          <div className="col-12">
            <Field label="Report" id="kind">
              <select id="kind" className="form-select" value={kind} onChange={(e) => setKind(e.target.value)}>
                {KINDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </Field>
          </div>

          {!opts && !optsError && (
            <div className="col-12"><Spinner label="Loading filter options..." /></div>
          )}

          {opts && (
            <>
              <div className="col-md-6">
                <Field label="State" id="state">
                  <select id="state" className="form-select" value={filters.state} onChange={pickState}>
                    <option value="">All states</option>
                    {Object.keys(opts.districts_by_state).map((s) => <option key={s}>{s}</option>)}
                  </select>
                </Field>
              </div>
              <div className="col-md-6">
                <Field label="District" id="district" hint={filters.state ? null : "Choose a state first."}>
                  <select id="district" className="form-select" value={filters.district} disabled={!filters.state}
                    onChange={pick("district")}>
                    <option value="">All districts</option>
                    {districts.map((d) => <option key={d}>{d}</option>)}
                  </select>
                </Field>
              </div>
              <div className="col-md-6">
                <Field label="Crop" id="crop">
                  <select id="crop" className="form-select" value={filters.crop} onChange={pick("crop")}>
                    <option value="">All crops</option>
                    {opts.crops.map((c) => <option key={c}>{c}</option>)}
                  </select>
                </Field>
              </div>
              <div className="col-md-6">
                <Field label="Season" id="season">
                  <select id="season" className="form-select" value={filters.season} onChange={pick("season")}>
                    <option value="">All seasons</option>
                    {opts.seasons.map((s) => <option key={s}>{s}</option>)}
                  </select>
                </Field>
              </div>
            </>
          )}

          <div className="col-12 d-flex flex-wrap gap-2">
            <button type="submit" className="btn btn-success" disabled={load.loading || !opts}>
              {load.loading ? "Building report..." : "View report"}
            </button>
            <button type="button" className="btn btn-outline-success" disabled={dl.loading || !opts}
              onClick={() => dl.run(kind, params(), "csv")}>Download CSV</button>
            <button type="button" className="btn btn-outline-success" disabled={dl.loading || !opts}
              onClick={() => dl.run(kind, params(), "pdf")}>Download PDF</button>
          </div>
        </form>
        <Alert>{load.error}</Alert>
        <Alert>{dl.error}</Alert>
        {kind === "farm" && (
          <p className="small text-muted mt-3 mb-0">
            The farm report only includes predictions you have saved, so filters that match none of them show no records.
          </p>
        )}
      </div></div>

      {load.loading && <Spinner label="Building report..." />}

      {report && (
        <>
          <div className="card mb-4"><div className="card-body">
            <h2 className="h5">{report.title}</h2>
            <p className="small text-muted mb-2">
              Data source: {report.source.name}
              {report.source.data_as_of && <> · data as of {report.source.data_as_of}</>}
              {" · "}generated {report.generated_at.slice(0, 16).replace("T", " ")} UTC
            </p>
            <table className="table table-sm w-auto mb-0">
              <tbody>
                {Object.entries(report.summary).map(([k, v]) => (
                  <tr key={k}>
                    <th className="fw-normal text-muted pe-4">{k.replace(/_/g, " ")}</th>
                    <td>{Array.isArray(v) ? v.join(" - ") : cell(v)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div></div>

          {report.charts.map((c) => (
            <div key={c.title} className="card mb-4"><div className="card-body">
              <ReportChart chart={c} />
            </div></div>
          ))}

          {report.tables.map((t) => (
            <div key={t.name} className="card mb-4"><div className="card-body">
              <h3 className="h6">{t.name}</h3>
              <DataTable
                rows={t.rows}
                columns={t.columns.map((name, i) => ({ label: name.replace(/_/g, " "), get: (r) => cell(r[i]) }))}
              />
            </div></div>
          ))}

          <ul className="small text-muted">
            {report.notes.map((n) => <li key={n}>{n}</li>)}
          </ul>
        </>
      )}
    </div>
  );
}
