import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import Alert from "../components/Alert.jsx";
import Field from "../components/Field.jsx";
import { useAuth } from "../services/auth.jsx";

export default function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(email.trim(), password);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="card auth-card p-4">
        <h1 className="h4 mb-1">Log in</h1>
        <p className="text-muted small mb-3">Welcome back to CropSense AI.</p>
        <Alert>{error}</Alert>
        <form onSubmit={onSubmit}>
          <Field label="Email" id="email">
            <input id="email" type="email" className="form-control" required autoComplete="email"
              value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <Field label="Password" id="password">
            <input id="password" type="password" className="form-control" required autoComplete="current-password"
              value={password} onChange={(e) => setPassword(e.target.value)} />
          </Field>
          <button type="submit" className="btn btn-success w-100" disabled={busy}>
            {busy ? "Logging in..." : "Log in"}
          </button>
        </form>
        <p className="small text-center mt-3 mb-0">
          New here? <Link to="/register">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
