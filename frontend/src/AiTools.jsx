import { useEffect, useState } from "react";
import { api } from "./api.js";

const readAsDataUrl = (file) =>
  new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.readAsDataURL(file);
  });

// Prescription photo -> drafts the caregiver checks and fixes -> saved only on Confirm.
function PrescriptionScan({ base, token, onSaved }) {
  const [drafts, setDrafts] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function scan(event) {
    const file = event.target.files[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const image = await readAsDataUrl(file);
      setDrafts(await api(`${base}/prescriptions/scan`, { method: "POST", body: { image }, token }));
    } catch (e) {
      setError(e.message);
    }
    setBusy(false);
  }

  const update = (i, key, value) =>
    setDrafts(drafts.map((d, j) => (j === i ? { ...d, [key]: value } : d)));

  async function confirm() {
    const medicines = drafts
      .filter((d) => d.keep !== false)
      .map(({ name, strength, pattern, food_timing }) => ({ name, strength, pattern, food_timing }));
    try {
      await api(`${base}/prescriptions/confirm`, {
        method: "POST",
        body: { start_date: new Date().toLocaleDateString("en-CA"), medicines },
        token,
      });
      setDrafts(null);
      onSaved();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="card">
      <h3>Scan a prescription</h3>
      <p className="muted">AI reads the photo. Check every line before saving — nothing is saved until you confirm.</p>
      <input type="file" accept="image/*" capture="environment" onChange={scan} />
      {busy && <p className="muted">Reading…</p>}
      {drafts && (
        <>
          {drafts.map((d, i) => (
            <div key={i} className="row">
              <input type="checkbox" checked={d.keep !== false} onChange={(e) => update(i, "keep", e.target.checked)} />
              <input value={d.name ?? ""} placeholder="Name" onChange={(e) => update(i, "name", e.target.value)} />
              <input value={d.strength ?? ""} placeholder="Strength" onChange={(e) => update(i, "strength", e.target.value)} />
              <input value={d.pattern ?? ""} placeholder="1-0-1" onChange={(e) => update(i, "pattern", e.target.value)} />
              <select value={d.food_timing} onChange={(e) => update(i, "food_timing", e.target.value)}>
                <option value="before">Before food</option>
                <option value="after">After food</option>
                <option value="with">With food</option>
                <option value="any">Any time</option>
              </select>
              {d.problem && <span className="error">{d.problem}</span>}
            </div>
          ))}
          <button onClick={confirm}>Confirm and save checked medicines</button>
        </>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

function Documents({ base, token }) {
  const [documents, setDocuments] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const load = () => api(`${base}/documents`, { token }).then(setDocuments);
  useEffect(() => {
    load();
  }, [base]);

  async function add(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.target));
    await api(`${base}/documents`, { method: "POST", body, token });
    event.target.reset();
    load();
  }

  async function ask(event) {
    event.preventDefault();
    const body = Object.fromEntries(new FormData(event.target));
    setError("");
    try {
      setResult(await api(`${base}/ask`, { method: "POST", body, token }));
    } catch (e) {
      setError(e.message);
    }
  }

  async function remove(id) {
    await api(`${base}/documents/${id}`, { method: "DELETE", token });
    load();
  }

  return (
    <div className="card">
      <h3>Health documents and questions</h3>
      <ul>
        {documents.map((d) => (
          <li key={d.id}>
            {d.title}{" "}
            <button className="link" onClick={() => remove(d.id)}>
              Delete
            </button>
          </li>
        ))}
      </ul>
      <form className="card" onSubmit={add}>
        <input name="title" placeholder="Title, e.g. Discharge summary" required />
        <textarea name="text" rows="4" placeholder="Paste the document text" required />
        <button>Add document</button>
      </form>
      <form className="row" onSubmit={ask}>
        <input name="question" placeholder="Ask about these documents" required />
        <button>Ask</button>
      </form>
      <p className="muted">Answers come only from the documents above. It won't give dosage advice.</p>
      {error && <p className="error">{error}</p>}
      {result && (
        <div>
          <p>{result.answer}</p>
          <ol className="muted">
            {result.sources.map((s) => (
              <li key={s.n}>
                <strong>{s.title}:</strong> {s.text}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function WeeklySummary({ base, token }) {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      setSummary(await api(`${base}/summary/weekly`, { token }));
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="card">
      <div className="row spread">
        <h3>Last 7 days</h3>
        <button onClick={load}>Write summary</button>
      </div>
      {summary && (
        <>
          <p>{summary.summary}</p>
          <ul className="muted">
            {summary.stats.map((s) => (
              <li key={s.medicine}>
                {s.medicine}: taken {s.taken} of {s.total}, missed {s.missed}
              </li>
            ))}
          </ul>
        </>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}

export default function AiTools({ elderId, token, onChange }) {
  const base = `/elders/${elderId}`;
  return (
    <>
      <h3>AI helpers</h3>
      <PrescriptionScan base={base} token={token} onSaved={onChange} />
      <Documents base={base} token={token} />
      <WeeklySummary base={base} token={token} />
    </>
  );
}
