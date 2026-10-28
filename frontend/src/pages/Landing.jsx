import { Link } from "react-router-dom";

const FEATURES = [
  ["🌾", "Crop yield prediction", "Estimate yield per hectare from location, crop, season and area, compared with history."],
  ["🌱", "Crop recommendation", "Top three suitable crops from your soil nutrients, pH and weather inputs."],
  ["🧪", "Fertilizer estimates", "Nutrient-based fertilizer quantities in kg per hectare, with the reasoning shown."],
  ["⛅", "Weather and alerts", "Forecast for your district with farming alerts and simple irrigation hints."],
  ["💧", "Irrigation planner", "A daily soil-water estimate telling you when irrigation is likely needed."],
  ["📄", "Reports", "Regional and farm reports with charts, exported as CSV or PDF with their data source."],
];

export default function Landing() {
  return (
    <div>
      <section className="hero">
        <div className="container">
          <div className="row align-items-center">
            <div className="col-lg-7">
              <h1 className="display-5">Smarter farming decisions, powered by data</h1>
              <p className="lead mt-3 opacity-75">
                CropSense AI helps you estimate yields, choose suitable crops, plan fertilizer and irrigation,
                and check the weather. Every result is an estimate, and each one shows how it was calculated.
              </p>
              <div className="d-flex gap-2 mt-4">
                <Link to="/register" className="btn btn-light btn-lg text-success fw-semibold">Get started</Link>
                <Link to="/login" className="btn btn-outline-light btn-lg">Log in</Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="container py-5">
        <h2 className="h3 text-center mb-4">What CropSense AI does</h2>
        <div className="row g-4">
          {FEATURES.map(([icon, title, text]) => (
            <div className="col-md-6 col-lg-4" key={title}>
              <div className="card h-100 p-3">
                <div className="feature-icon" aria-hidden="true">{icon}</div>
                <h3 className="h5 mt-2">{title}</h3>
                <p className="text-muted mb-0">{text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="earth-band py-4">
        <div className="container small text-muted">
          Estimates only. Verify soil test results, fertilizer doses and irrigation with local agricultural
          experts before acting on them. Yield and recommendation models are trained on public datasets and
          are not guarantees of field performance.
        </div>
      </section>
    </div>
  );
}
