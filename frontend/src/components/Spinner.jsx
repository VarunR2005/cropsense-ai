export default function Spinner({ label = "Loading..." }) {
  return (
    <div className="d-flex align-items-center gap-2 text-success py-3" role="status">
      <div className="spinner-border spinner-border-sm" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
