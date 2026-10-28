import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../services/auth.jsx";

const NAV = [
  ["/dashboard", "📊", "Dashboard"],
  ["/yield", "🌾", "Crop Yield Prediction"],
  ["/crops", "🌱", "Crop Recommendation"],
  ["/fertilizer", "🧪", "Fertilizer Recommendation"],
  ["/disease", "🍃", "Disease Detection"],
  ["/weather", "⛅", "Weather Forecast"],
  ["/irrigation", "💧", "Irrigation Planner"],
  ["/reports", "📄", "Reports"],
  ["/profile", "👤", "Profile"],
];

export default function Layout() {
  const [open, setOpen] = useState(false);
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Main navigation">
        <div className="sidebar-brand">🌾 CropSense AI</div>
        <nav className="nav flex-column">
          {NAV.map(([to, icon, label]) => (
            <NavLink key={to} to={to} className="sidebar-link" onClick={() => setOpen(false)}>
              <span aria-hidden="true">{icon}</span> {label}
            </NavLink>
          ))}
          <button type="button" className="sidebar-link sidebar-logout" onClick={handleLogout}>
            <span aria-hidden="true">🚪</span> Logout
          </button>
        </nav>
      </aside>
      {open && <div className="backdrop" onClick={() => setOpen(false)} />}
      <div className="main">
        <header className="topbar">
          <button type="button" className="btn btn-outline-success btn-sm d-md-none" aria-label="Open menu" onClick={() => setOpen(true)}>
            ☰
          </button>
          <span className="ms-auto text-muted small">Signed in as {user?.full_name}</span>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
