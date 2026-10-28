export default function Alert({ type = "danger", children }) {
  if (!children) return null;
  return (
    <div className={`alert alert-${type} py-2`} role={type === "danger" ? "alert" : "status"}>
      {children}
    </div>
  );
}
