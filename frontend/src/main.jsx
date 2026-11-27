import { createRoot } from "react-dom/client";
import Caregiver from "./Caregiver.jsx";
import ElderScreen from "./ElderScreen.jsx";
import "./styles.css";

// "#/screen/<token>" is the elder's screen; anything else is the caregiver app.
const match = location.hash.match(/^#\/screen\/(.+)$/);
const screenToken = match ? match[1] : null;

createRoot(document.getElementById("root")).render(
  screenToken ? <ElderScreen screenToken={screenToken} /> : <Caregiver />,
);

// Offline support for the installed app (not in dev, where caching gets in the way).
if (import.meta.env.PROD && "serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js");
}
