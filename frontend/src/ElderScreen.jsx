import { useEffect, useRef, useState } from "react";
import { api, fromUtc } from "./api.js";
import { fraction, reminderText, VOICE_LANG, WORDS } from "./words.js";

function findVoice(lang) {
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.lang.replace("_", "-") === VOICE_LANG[lang]) ??
    voices.find((v) => v.lang.startsWith(lang));
}

// Speak the reminder in the elder's language. If the phone has no voice for it,
// speak English rather than letting another voice mangle Kannada or Hindi.
function speak(name, dose, lang) {
  if (!window.speechSynthesis) return;
  let voice = findVoice(lang);
  if (!voice) {
    lang = "en";
    voice = findVoice("en");
  }
  const utterance = new SpeechSynthesisUtterance(reminderText(name, dose, lang));
  utterance.lang = VOICE_LANG[lang];
  if (voice) utterance.voice = voice;
  utterance.rate = 0.85;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

const timeText = (date) => date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

// The ONE screen the elder sees.
export default function ElderScreen({ screenToken }) {
  const [screen, setScreen] = useState(null);
  const [error, setError] = useState("");
  const [sosSent, setSosSent] = useState(false);
  const spokenFor = useRef(null);

  async function load() {
    try {
      setScreen(await api("/screen", { screenToken }));
      setError("");
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    load();
    const timer = setInterval(load, 30_000);
    return () => clearInterval(timer);
  }, [screenToken]);

  const dose = screen?.next_dose;
  const lang = screen?.language ?? "en";
  const words = WORDS[lang];
  const dueAt = dose && fromUtc(dose.scheduled_at);
  const due = dose && dueAt <= new Date();
  // Buttons appear 30 minutes early, so a dose many hours away can't be tapped by mistake.
  const canTake = dose && dueAt - 30 * 60_000 <= Date.now();

  // Speak once when a dose becomes due.
  useEffect(() => {
    if (due && spokenFor.current !== dose.dose_id) {
      spokenFor.current = dose.dose_id;
      speak(screen.elder_name, dose, lang);
    }
  }, [due, dose?.dose_id]);

  async function act(action) {
    await api(`/screen/doses/${dose.dose_id}/${action}`, { method: "POST", screenToken });
    load();
  }

  async function sos() {
    await api("/screen/sos", { method: "POST", screenToken });
    setSosSent(true);
    setTimeout(() => setSosSent(false), 10_000);
  }

  if (error) return <main className="elder"><p className="big">{error}</p></main>;
  if (!screen) return <main className="elder" />;

  return (
    <main className="elder">
      <h1>{screen.elder_name}</h1>

      {dose ? (
        <section className="dose">
          {!canTake && <p className="next">{words.next}</p>}
          {dose.photo_url ? (
            <img src={dose.photo_url} alt={dose.medicine_name} />
          ) : (
            <div className="pill">💊</div>
          )}
          <p className="medicine">
            {dose.medicine_name} {dose.strength}
          </p>
          <p className="quantity">× {fraction(dose.quantity)}</p>
          {words.food[dose.food_timing] && <p className="food">{words.food[dose.food_timing]}</p>}
          <p className="when">
            {words.at} {timeText(fromUtc(dose.scheduled_at))}
            <button
              className="speak"
              aria-label="Say it again"
              onClick={() => speak(screen.elder_name, dose, lang)}
            >
              🔊
            </button>
          </p>
          {canTake && (
            <>
              <button className="took" onClick={() => act("take")}>
                ✔ {words.took}
              </button>
              <button className="later" onClick={() => act("snooze")}>
                {words.later}
              </button>
            </>
          )}
        </section>
      ) : (
        <p className="big">✔ {words.nothing}</p>
      )}

      {screen.next_appointment && (
        <p className="appointment">
          🩺 {words.appointment}: {screen.next_appointment.title},{" "}
          {new Date(screen.next_appointment.starts_at).toLocaleString([], {
            dateStyle: "medium",
            timeStyle: "short",
          })}
        </p>
      )}

      <button className="sos" onClick={sos}>
        {sosSent ? words.sosSent : words.sos}
      </button>
    </main>
  );
}
