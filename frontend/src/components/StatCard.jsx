export default function StatCard({ icon, label, value, hint }) {
  return (
    <div className="card stat-card h-100">
      <div className="card-body">
        <div className="stat-icon" aria-hidden="true">{icon}</div>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
        {hint && <div className="small text-muted mt-1">{hint}</div>}
      </div>
    </div>
  );
}
