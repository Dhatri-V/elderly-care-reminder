// Words shown and spoken on the elder screen, in Kannada, Hindi and English.

export const WORDS = {
  en: {
    took: "I TOOK IT",
    later: "Remind me later",
    sos: "SOS – Call family",
    sosSent: "Family has been told",
    nothing: "No medicine now",
    next: "Next medicine",
    at: "at",
    food: { before: "Before food", after: "After food", with: "With food", any: "" },
    appointment: "Doctor visit",
  },
  hi: {
    took: "मैंने ले ली",
    later: "बाद में याद दिलाएं",
    sos: "SOS – परिवार को बुलाएं",
    sosSent: "परिवार को बता दिया गया है",
    nothing: "अभी कोई दवा नहीं",
    next: "अगली दवा",
    at: "समय",
    food: { before: "खाने से पहले", after: "खाने के बाद", with: "खाने के साथ", any: "" },
    appointment: "डॉक्टर से मिलना",
  },
  kn: {
    took: "ತೆಗೆದುಕೊಂಡೆ",
    later: "ನಂತರ ನೆನಪಿಸಿ",
    sos: "SOS – ಮನೆಯವರನ್ನು ಕರೆಯಿರಿ",
    sosSent: "ಮನೆಯವರಿಗೆ ತಿಳಿಸಲಾಗಿದೆ",
    nothing: "ಈಗ ಯಾವುದೇ ಔಷಧಿ ಇಲ್ಲ",
    next: "ಮುಂದಿನ ಔಷಧಿ",
    at: "ಸಮಯ",
    food: { before: "ಊಟದ ಮೊದಲು", after: "ಊಟದ ನಂತರ", with: "ಊಟದ ಜೊತೆ", any: "" },
    appointment: "ವೈದ್ಯರ ಭೇಟಿ",
  },
};

export const VOICE_LANG = { en: "en-IN", hi: "hi-IN", kn: "kn-IN" };

// Spoken amounts. Words sound more natural than digits.
const SPOKEN = {
  en: { 0.5: "half a", 1: "one", 1.5: "one and a half", 2: "two", 3: "three" },
  hi: { 0.5: "आधी", 1: "एक", 1.5: "डेढ़", 2: "दो", 3: "तीन" },
  kn: { 0.5: "ಅರ್ಧ", 1: "ಒಂದು", 1.5: "ಒಂದೂವರೆ", 2: "ಎರಡು", 3: "ಮೂರು" },
};

// How food timing is said out loud (everyday speech, not written form).
const SPOKEN_FOOD = {
  en: { before: "before food", after: "after food", with: "with food", any: "" },
  hi: { before: "खाने से पहले", after: "खाने के बाद", with: "खाने के साथ", any: "" },
  kn: { before: "ಊಟಕ್ಕೆ ಮುಂಚೆ", after: "ಊಟ ಆದ್ಮೇಲೆ", with: "ಊಟದ ಜೊತೆ", any: "" },
};

export function amount(quantity, lang) {
  return SPOKEN[lang][quantity] ?? String(quantity);
}

// 0.5 -> "½", 1.5 -> "1½" for display.
export function fraction(quantity) {
  const whole = Math.floor(quantity);
  return quantity === whole ? String(whole) : `${whole || ""}½`;
}

// Remove the gaps left when there is no food timing.
const tidy = (text) => text.replace(/\s+/g, " ").replace(" .", ".");

// The sentence spoken when a dose is due.
export function reminderText(name, dose, lang) {
  return tidy(sentence(name, dose, lang));
}

function sentence(name, dose, lang) {
  const qty = amount(dose.quantity, lang);
  const food = SPOKEN_FOOD[lang][dose.food_timing];
  const medicine = dose.medicine_name;
  if (lang === "kn") {
    return `${name}, ಮಾತ್ರೆ ತಗೊಳ್ಳೋ ಸಮಯ ಆಯ್ತು. ${food} ${medicine}, ${qty} ಮಾತ್ರೆ ತಗೊಳ್ಳಿ.`;
  }
  if (lang === "hi") {
    return `${name} जी, दवा का समय हो गया है। ${food} ${medicine} की ${qty} गोली ले लीजिए।`;
  }
  const tablets = dose.quantity > 1 ? "tablets" : "tablet";
  return `${name}, it is time for your medicine. Please take ${qty} ${tablets} of ${medicine} ${food}.`;
}
