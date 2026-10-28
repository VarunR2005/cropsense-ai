import { useState } from "react";
import Alert from "../components/Alert.jsx";
import Field from "../components/Field.jsx";
import { api } from "../services/api.js";
import { dateOnly } from "../services/format.js";
import { useAuth } from "../services/auth.jsx";
import { useAction } from "../services/useAction.js";

export default function Profile() {
  const { user, setUser } = useAuth();
  const [name, setName] = useState(user?.full_name ?? "");
  const [nameSaved, setNameSaved] = useState(null);
  const [pw, setPw] = useState({ current: "", next: "", confirm: "" });
  const [pwDone, setPwDone] = useState(null);
  const [pwError, setPwError] = useState(null);
  const saveName = useAction(api.updateMe);
  const changePw = useAction(api.changePassword);

  async function onSaveName(e) {
    e.preventDefault();
    setNameSaved(null);
    const updated = await saveName.run({ full_name: name.trim() });
    if (updated) {
      setUser(updated);
      setNameSaved("Name updated.");
    }
  }

  async function onChangePassword(e) {
    e.preventDefault();
    setPwDone(null);
    setPwError(null);
    if (pw.next !== pw.confirm) {
      setPwError("The new passwords do not match.");
      return;
    }
    // changePassword returns null on success (204) and undefined on failure
    const ok = await changePw.run({ current_password: pw.current, new_password: pw.next });
    if (ok !== undefined) {
      setPw({ current: "", next: "", confirm: "" });
      setPwDone("Password changed. Use the new password next time you log in.");
    }
  }

  return (
    <div>
      <h1 className="h3 mb-4">Profile</h1>
      <div className="row g-4">
        <div className="col-lg-6">
          <div className="card"><div className="card-body">
            <h2 className="h5">Your details</h2>
            <p className="small text-muted mb-3">Email: {user?.email} · Member since {dateOnly(user?.created_at)}</p>
            <form onSubmit={onSaveName}>
              <Field label="Full name" id="fullname">
                <input id="fullname" className="form-control" required maxLength={100}
                  value={name} onChange={(e) => setName(e.target.value)} />
              </Field>
              <button type="submit" className="btn btn-success" disabled={saveName.loading}>Save name</button>
            </form>
            <Alert>{saveName.error}</Alert>
            {nameSaved && <Alert type="success">{nameSaved}</Alert>}
          </div></div>
        </div>

        <div className="col-lg-6">
          <div className="card"><div className="card-body">
            <h2 className="h5">Change password</h2>
            <form onSubmit={onChangePassword}>
              <Field label="Current password" id="cur">
                <input id="cur" type="password" className="form-control" required autoComplete="current-password"
                  value={pw.current} onChange={(e) => setPw({ ...pw, current: e.target.value })} />
              </Field>
              <Field label="New password" id="new" hint="At least 8 characters.">
                <input id="new" type="password" className="form-control" required minLength={8} maxLength={72}
                  autoComplete="new-password" value={pw.next} onChange={(e) => setPw({ ...pw, next: e.target.value })} />
              </Field>
              <Field label="Confirm new password" id="confirm">
                <input id="confirm" type="password" className="form-control" required minLength={8} maxLength={72}
                  autoComplete="new-password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} />
              </Field>
              <button type="submit" className="btn btn-success" disabled={changePw.loading}>Change password</button>
            </form>
            <Alert>{pwError}</Alert>
            <Alert>{changePw.error}</Alert>
            {pwDone && <Alert type="success">{pwDone}</Alert>}
          </div></div>
        </div>
      </div>
    </div>
  );
}
