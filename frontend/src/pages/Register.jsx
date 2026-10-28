import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import Alert from "../components/Alert.jsx";
import Field from "../components/Field.jsx";
import { useAuth } from "../services/auth.jsx";

export default function Register() {
  const { user, register } = useAuth();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/dashboard" replace />;

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await register({ ...form, email: form.email.trim(), full_name: form.full_name.trim() });
    } catch (err) {
      setError(err.status === 409 ? "That email is already registered. Try logging in." : err.message);
      setBusy(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="card auth-card p-4">
        <h1 className="h4 mb-1">Create your account</h1>
        <p className="text-muted small mb-3">Your predictions and reports are private to you.</p>
        <Alert>{error}</Alert>
        <form onSubmit={onSubmit}>
          <Field label="Full name" id="name">
            <input id="name" className="form-control" required maxLength={100}
              value={form.full_name} onChange={set("full_name")} />
          </Field>
          <Field label="Email" id="email">
            <input id="email" type="email" className="form-control" required
              value={form.email} onChange={set("email")} />
          </Field>
          <Field label="Password" id="password" hint="At least 8 characters.">
            <input id="password" type="password" className="form-control" required minLength={8} maxLength={72}
              autoComplete="new-password" value={form.password} onChange={set("password")} />
          </Field>
          <button type="submit" className="btn btn-success w-100" disabled={busy}>
            {busy ? "Creating account..." : "Create account"}
          </button>
        </form>
        <p className="small text-center mt-3 mb-0">
          Already registered? <Link to="/login">Log in</Link>
        </p>
      </div>
    </div>
  );
}
