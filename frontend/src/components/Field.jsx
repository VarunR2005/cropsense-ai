export default function Field({ label, id, hint, children }) {
  return (
    <div className="mb-3">
      <label htmlFor={id} className="form-label fw-semibold">
        {label}
      </label>
      {children}
      {hint && <div className="form-text">{hint}</div>}
    </div>
  );
}
