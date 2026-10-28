import { useEffect } from "react";
import Alert from "../components/Alert.jsx";
import DataTable from "../components/DataTable.jsx";
import ReportChart from "../components/ReportChart.jsx";
import Spinner from "../components/Spinner.jsx";
import StatCard from "../components/StatCard.jsx";
import { api } from "../services/api.js";
import { dateOnly, num, pct } from "../services/format.js";
import { useAction } from "../services/useAction.js";

export default function Dashboard() {
  const dash = useAction(api.dashboard);

  useEffect(() => {
    dash.run();
  }, [dash.run]); // eslint-disable-line react-hooks/exhaustive-deps

  if (dash.loading && !dash.data) return <Spinner label="Loading your dashboard..." />;
  if (dash.error) return <Alert>{dash.error}</Alert>;
  const d = dash.data;
  if (!d) return null;

  const t = d.totals;
  const yc = d.yield_comparison_chart;
  const w = d.weather_summary;

  return (
    <div>
      <h1 className="h3 mb-1">Dashboard</h1>
      <p className="text-muted small mb-4">Everything here is calculated from your own saved records.</p>

      <div className="row g-3 mb-4">
        <div className="col-6 col-lg-3"><StatCard icon="🌾" label="Yield predictions" value={t.yield_predictions} /></div>
        <div className="col-6 col-lg-3"><StatCard icon="🌱" label="Crop recommendations" value={t.crop_recommendations} /></div>
        <div className="col-6 col-lg-3"><StatCard icon="🧪" label="Fertilizer plans" value={t.fertilizer_recommendations} /></div>
        <div className="col-6 col-lg-3"><StatCard icon="💧" label="Irrigation plans" value={t.irrigation_plans} /></div>
      </div>

      <div className="row g-4">
        <div className="col-lg-7">
          <div className="card h-100">
            <div className="card-header">Recent yield predictions</div>
            <div className="card-body">
              <DataTable
                empty="No yield predictions yet. Try the Crop Yield Prediction page."
                rows={d.recent_predictions}
                columns={[
                  { label: "Date", get: (r) => dateOnly(r.created_at) },
                  { label: "Crop", get: (r) => r.crop },
                  { label: "Location", get: (r) => `${r.district}, ${r.state}` },
                  { label: "t/ha", get: (r) => num(r.predicted_yield_t_per_ha, 2) },
                  { label: "History", get: (r) => num(r.historical_mean_t_per_ha, 2) },
                  { label: "vs history", get: (r) => pct(r.difference_vs_history_pct) },
                ]}
              />
            </div>
          </div>
        </div>
        <div className="col-lg-5">
          <div className="card h-100">
            <div className="card-header">Weather</div>
            <div className="card-body">
              {w ? (
                <>
                  <div className="big-number">{num(w.temperature_c, 1)}<small> °C</small></div>
                  <div className="text-muted mb-2">{w.city} · {w.condition}, {num(w.humidity_pct, 0)}% humidity</div>
                  <div>Forecast rain today: <strong>{num(w.forecast_today_rain_mm, 1)} mm</strong></div>
                  <div>Active alerts: <strong>{w.alerts}</strong></div>
                  {w.first_alert && <div className="alert alert-warning py-2 mt-2 mb-0">{w.first_alert}</div>}
                  <div className="small text-muted mt-2">Saved {dateOnly(w.fetched_at)}</div>
                </>
              ) : (
                <p className="text-muted mb-0">{d.weather_note}</p>
              )}
            </div>
          </div>
        </div>
      </div>

      {yc.labels.length > 0 && (
        <div className="card mt-4">
          <div className="card-body">
            <ReportChart
              chart={{
                title: "Predicted vs historical mean yield (t/ha), latest predictions",
                type: "bar",
                x: yc.labels,
                series: [
                  { name: "predicted", values: yc.predicted_t_per_ha },
                  { name: "historical mean", values: yc.historical_mean_t_per_ha },
                ],
              }}
            />
          </div>
        </div>
      )}

      <div className="row g-4 mt-1">
        <div className="col-lg-6">
          <div className="card h-100">
            <div className="card-header">Seasonal production</div>
            <div className="card-body">
              <DataTable
                empty="No data yet."
                rows={d.seasonal_trend}
                columns={[
                  { label: "Season", get: (r) => r.season },
                  { label: "Predictions", get: (r) => r.predictions },
                  { label: "Total production (t)", get: (r) => num(r.total_production_t, 1) },
                  { label: "Avg t/ha", get: (r) => num(r.avg_predicted_yield_t_per_ha, 2) },
                ]}
              />
            </div>
          </div>
        </div>
        <div className="col-lg-6">
          <div className="card h-100">
            <div className="card-header">Recent crop recommendations</div>
            <div className="card-body">
              <DataTable
                empty="No crop recommendations yet."
                rows={d.recent_crop_recommendations}
                columns={[
                  { label: "Date", get: (r) => dateOnly(r.created_at) },
                  { label: "Top crop", get: (r) => r.top_crop },
                  { label: "Top 3", get: (r) => r.top_3.join(", ") },
                ]}
              />
            </div>
          </div>
        </div>
      </div>

      {d.monthly_trend.length > 0 && (
        <div className="card mt-4">
          <div className="card-body">
            <ReportChart
              chart={{
                title: "Monthly predicted production (t)",
                type: "bar",
                x: d.monthly_trend.map((m) => m.month),
                series: [{ name: "production", values: d.monthly_trend.map((m) => m.total_production_t) }],
              }}
            />
          </div>
        </div>
      )}

      <div className="row g-4 mt-1">
        <div className="col-lg-6">
          <div className="card h-100">
            <div className="card-header">Disease detection</div>
            <div className="card-body text-muted">{d.disease_history.note}</div>
          </div>
        </div>
        <div className="col-lg-6">
          <div className="card h-100">
            <div className="card-header">Saved farms</div>
            <div className="card-body text-muted">{d.farms.note}</div>
          </div>
        </div>
      </div>

      <p className="small text-muted mt-4">{d.notes[0]}</p>
    </div>
  );
}
