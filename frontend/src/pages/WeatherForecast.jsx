import { useState } from "react";
import Alert from "../components/Alert.jsx";
import Spinner from "../components/Spinner.jsx";
import StatCard from "../components/StatCard.jsx";
import { api } from "../services/api.js";
import { dateOnly, num } from "../services/format.js";
import { useAction } from "../services/useAction.js";

const SEVERITY_CLASS = { high: "danger", medium: "warning", low: "info" };

export default function WeatherForecast() {
  const [city, setCity] = useState("");
  const wx = useAction(api.weather);
  const w = wx.data;

  const onSubmit = (e) => {
    e.preventDefault();
    wx.run(city.trim());
  };

  return (
    <div>
      <h1 className="h3 mb-1">Weather forecast</h1>
      <p className="text-muted small mb-4">Current weather and a 5-day outlook for your area, with farming alerts.</p>

      <form className="row g-2 align-items-end mb-4" onSubmit={onSubmit}>
        <div className="col-sm-8 col-md-6">
          <label htmlFor="city" className="form-label fw-semibold">City or district</label>
          <input id="city" className="form-control" required minLength={2} maxLength={100}
            placeholder="e.g. Mysuru,IN" value={city} onChange={(e) => setCity(e.target.value)} />
          <div className="form-text">Add the country code after a comma for better matches, such as Mysuru,IN.</div>
        </div>
        <div className="col-auto">
          <button type="submit" className="btn btn-success" disabled={wx.loading}>
            {wx.loading ? "Fetching..." : "Get forecast"}
          </button>
        </div>
      </form>

      <Alert>{wx.error}</Alert>
      {wx.loading && <Spinner label="Fetching weather..." />}

      {w && (
        <>
          <h2 className="h5">
            {w.location.name}{w.location.country ? `, ${w.location.country}` : ""}
            {" "}
            <span className="badge bg-light text-dark border small ms-2">
              {w.source.cached ? "saved result" : "live"} · {dateOnly(w.source.fetched_at)}
            </span>
          </h2>
          {w.source.stale && (
            <Alert type="warning">The weather service is unavailable, so this is the last saved result.</Alert>
          )}

          <div className="row g-3 mb-4">
            <div className="col-6 col-lg-3"><StatCard icon="🌡️" label="Temperature" value={`${num(w.current.temperature_c, 1)} °C`} hint={`Feels like ${num(w.current.feels_like_c, 1)} °C`} /></div>
            <div className="col-6 col-lg-3"><StatCard icon="💦" label="Humidity" value={`${num(w.current.humidity_pct, 0)}%`} /></div>
            <div className="col-6 col-lg-3"><StatCard icon="🌤️" label="Conditions" value={w.current.condition ?? "-"} hint={w.current.description} /></div>
            <div className="col-6 col-lg-3"><StatCard icon="🌬️" label="Wind" value={`${num(w.current.wind_speed_ms, 1)} m/s`}
              hint={w.current.rain_last_1h_mm === null ? "Rain last hour: not reported" : `Rain last hour: ${num(w.current.rain_last_1h_mm, 1)} mm`} /></div>
          </div>

          {w.alerts.length > 0 && (
            <div className="mb-4">
              <h3 className="h6">Farming alerts</h3>
              {w.alerts.map((a, i) => (
                <div key={i} className={`alert alert-${SEVERITY_CLASS[a.severity] ?? "info"} py-2`}>
                  <strong>{a.date}:</strong> {a.message}
                </div>
              ))}
            </div>
          )}

          {w.irrigation_hints.length > 0 && (
            <div className="alert alert-success">
              <strong>Irrigation hint:</strong> {w.irrigation_hints.join(" ")}
            </div>
          )}

          <div className="card"><div className="card-body">
            <h3 className="h6">5-day outlook</h3>
            <div className="table-responsive">
              <table className="table table-sm align-middle mb-0">
                <thead className="table-success">
                  <tr><th>Date</th><th>Min °C</th><th>Max °C</th><th>Humidity</th><th>Rain mm</th><th>Rain chance</th><th>Wind m/s</th><th>Conditions</th></tr>
                </thead>
                <tbody>
                  {w.daily_forecast.map((d) => (
                    <tr key={d.date}>
                      <td>{d.date}{d.partial_day && <span className="text-muted small"> (partial)</span>}</td>
                      <td>{num(d.temp_min_c, 1)}</td>
                      <td>{num(d.temp_max_c, 1)}</td>
                      <td>{num(d.humidity_avg_pct, 0)}%</td>
                      <td>{num(d.rain_mm, 1)}</td>
                      <td>{d.rain_probability_pct}%</td>
                      <td>{num(d.wind_max_ms, 1)}</td>
                      <td>{d.condition ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div></div>

          <ul className="small text-muted mt-3">
            {w.notes.map((n) => <li key={n}>{n}</li>)}
          </ul>
        </>
      )}
    </div>
  );
}
