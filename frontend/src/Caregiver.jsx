import { useEffect, useState } from "react";
import { api, fromUtc } from "./api.js";

// Read a <form> into a plain object, dropping empty fields.
function formData(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  for (const key of Object.keys(data)) if (data[key] === "") delete data[key];
  return data;
}

const todayIn = (timezone) => new Date().toLocaleDateString("en-CA", { timeZone: timezone });

function Login({ onLogin }) {
  const [error, setError] = useState("");

  async function submit(event, register) {
    const body = formData(event);
    try {
      if (register) await api("/auth/register", { method: "POST", body });
      const { access_token } = await api("/auth/login", { method: "POST", body });
      onLogin(access_token);
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <form className="card" onSubmit={(e) => submit(e, e.nativeEvent.submitter?.value === "register")}>
      <h2>Caregiver login</h2>
      <input name="email" type="email" placeholder="Email" required />
      <input name="password" type="password" placeholder="Password (8+ characters)" required />
      <div className="row">
        <button value="login">Log in</button>
        <button value="register" className="secondary">
          Create account
        </button>
      </div>
      {error && <p className="error">{error}</p>}
    </form>
  );
}

function Medicine({ medicine, token, onChange }) {
  const [schedules, setSchedules] = useState([]);
  const [error, setError] = useState("");
  const load = () => api(`/medicines/${medicine.id}/schedules`, { token }).then(setSchedules);
  useEffect(() => {
    load();
  }, [medicine.id]);

  async function addSchedule(event) {
    const body = formData(event);
    try {
      await api(`/medicines/${medicine.id}/schedules`, { method: "POST", body, token });
      event.target.reset();
      setError("");
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function remove() {
    await api(`/medicines/${medicine.id}`, { method: "DELETE", token });
    onChange();
  }

  return (
    <li className="card">
      <div className="row spread">
        <strong>
          {medicine.name} {medicine.strength}
        </strong>
        <button className="link" onClick={remove}>
          Delete
        </button>
      </div>
      <p className="muted">
        {medicine.food_timing} food · stock {medicine.stock_count} (refill at{" "}
        {medicine.refill_threshold})
      </p>
      <ul>
        {schedules.map((s) => (
          <li key={s.id}>
            {s.pattern} from {s.start_date}
            {s.end_date && ` to ${s.end_date}`} ({s.morning_time.slice(0, 5)} /{" "}
            {s.afternoon_time.slice(0, 5)} / {s.night_time.slice(0, 5)})
          </li>
        ))}
      </ul>
      <form className="row" onSubmit={addSchedule}>
        <input name="pattern" placeholder="1-0-1 or ½-0-1" required />
        <input name="start_date" type="date" defaultValue={todayIn()} required />
        <input name="end_date" type="date" title="End date (optional)" />
        <button>Add schedule</button>
      </form>
      {error && <p className="error">{error}</p>}
    </li>
  );
}

function Elder({ elder, token, onChange }) {
  const [medicines, setMedicines] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [doses, setDoses] = useState([]);
  const [error, setError] = useState("");
  const base = `/elders/${elder.id}`;
  const today = todayIn(elder.timezone);

  const localDay = (d) =>
    fromUtc(d.scheduled_at).toLocaleDateString("en-CA", { timeZone: elder.timezone });

  function load() {
    api(`${base}/medicines`, { token }).then(setMedicines);
    api(`${base}/appointments`, { token }).then(setAppointments);
    api(`${base}/doses`, { token }).then((all) => setDoses(all.filter((d) => localDay(d) === today)));
  }

  useEffect(load, [elder.id]);

  async function post(path, event, method = "POST") {
    const body = event ? formData(event) : undefined;
    try {
      await api(path, { method, body, token });
      event?.target.reset();
      setError("");
      load();
    } catch (e) {
      setError(e.message);
    }
  }

  async function newLink() {
    await api(`${base}/screen-token`, { method: "POST", token });
    onChange();
  }

  const link = `${location.origin}/#/screen/${elder.screen_token}`;

  return (
    <section>
      <h2>{elder.name}</h2>
      {error && <p className="error">{error}</p>}

      <div className="card">
        <h3>Elder screen link</h3>
        <p className="muted">Open this on {elder.name}'s phone or tablet and add it to the home screen.</p>
        <input readOnly value={link} onFocus={(e) => e.target.select()} />
        <div className="row">
          <a href={link} target="_blank" rel="noreferrer">
            Open screen
          </a>
          <button className="link" onClick={newLink}>
            Make a new link (old one stops working)
          </button>
        </div>
      </div>

      <div className="card">
        <div className="row spread">
          <h3>Today ({today})</h3>
          <button onClick={() => post(`${base}/doses/generate?day=${today}`)}>Create today's doses</button>
        </div>
        <ul>
          {doses.map((d) => (
            <li key={d.id}>
              {fromUtc(d.scheduled_at).toLocaleTimeString([], {
                hour: "numeric",
                minute: "2-digit",
                timeZone: elder.timezone,
              })}{" "}
              · {medicines.find((m) => m.id === d.medicine_id)?.name} × {d.quantity} ·{" "}
              <span className={`status ${d.status}`}>{d.status}</span>
            </li>
          ))}
        </ul>
      </div>

      <h3>Medicines</h3>
      <ul className="plain">
        {medicines.map((m) => (
          <Medicine key={m.id} medicine={m} token={token} onChange={load} />
        ))}
      </ul>
      <form className="card" onSubmit={(e) => post(`${base}/medicines`, e)}>
        <h3>Add medicine</h3>
        <input name="name" placeholder="Name" required />
        <input name="strength" placeholder="Strength, e.g. 500 mg" />
        <input name="photo_url" type="url" placeholder="Photo of the tablet (URL)" />
        <label>
          Food
          <select name="food_timing" defaultValue="after">
            <option value="before">Before food</option>
            <option value="after">After food</option>
            <option value="with">With food</option>
            <option value="any">Any time</option>
          </select>
        </label>
        <div className="row">
          <label>
            Tablets in stock <input name="stock_count" type="number" step="0.5" min="0" />
          </label>
          <label>
            Alert when stock is <input name="refill_threshold" type="number" step="0.5" min="0" />
          </label>
        </div>
        <button>Add medicine</button>
      </form>

      <h3>Appointments</h3>
      <ul>
        {appointments.map((a) => (
          <li key={a.id}>
            {a.starts_at.replace("T", " ").slice(0, 16)} · {a.title}
            {a.doctor && ` with ${a.doctor}`}
            {a.location && ` at ${a.location}`}{" "}
            <button className="link" onClick={() => post(`/appointments/${a.id}`, null, "DELETE")}>
              Delete
            </button>
          </li>
        ))}
      </ul>
      <form className="card row" onSubmit={(e) => post(`${base}/appointments`, e)}>
        <input name="title" placeholder="What, e.g. Eye checkup" required />
        <input name="doctor" placeholder="Doctor" />
        <input name="location" placeholder="Where" />
        <input name="starts_at" type="datetime-local" required />
        <button>Add appointment</button>
      </form>
    </section>
  );
}

export default function Caregiver() {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [elders, setElders] = useState([]);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState("");

  function login(newToken) {
    localStorage.setItem("token", newToken);
    setToken(newToken);
  }

  function logout() {
    localStorage.removeItem("token");
    setToken(null);
  }

  const loadElders = () =>
    api("/elders", { token })
      .then(setElders)
      .catch(logout);

  useEffect(() => {
    if (token) loadElders();
  }, [token]);

  if (!token) return <main className="caregiver"><Login onLogin={login} /></main>;

  async function addElder(event) {
    const body = formData(event);
    const elder = await api("/elders", { method: "POST", body, token });
    event.target.reset();
    await loadElders();
    setSelected(elder.id);
  }

  async function saveTelegram(event) {
    await api("/auth/me/telegram", { method: "PUT", body: formData(event), token });
    setMessage("Telegram alerts are on.");
  }

  const elder = elders.find((e) => e.id === selected);

  return (
    <main className="caregiver">
      <header className="row spread">
        <h1>Medicine Reminder</h1>
        <button className="link" onClick={logout}>
          Log out
        </button>
      </header>

      <nav className="row">
        {elders.map((e) => (
          <button key={e.id} className={e.id === selected ? "" : "secondary"} onClick={() => setSelected(e.id)}>
            {e.name}
          </button>
        ))}
      </nav>

      {elder ? (
        <Elder key={elder.id} elder={elder} token={token} onChange={loadElders} />
      ) : (
        <p className="muted">Pick an elder above, or add one below.</p>
      )}

      <form className="card row" onSubmit={addElder}>
        <input name="name" placeholder="Elder's name" required />
        <select name="language" defaultValue="kn">
          <option value="kn">ಕನ್ನಡ Kannada</option>
          <option value="hi">हिन्दी Hindi</option>
          <option value="en">English</option>
        </select>
        <input name="timezone" defaultValue="Asia/Kolkata" />
        <button>Add elder</button>
      </form>

      <form className="card row" onSubmit={saveTelegram}>
        <input name="chat_id" placeholder="Your Telegram chat id (for alerts)" required />
        <button>Save</button>
        {message && <span className="muted">{message}</span>}
      </form>
    </main>
  );
}
