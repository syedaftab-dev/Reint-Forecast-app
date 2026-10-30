import { useState } from "react";
import AccuracyPage from "./pages/AccuracyPage";
import ForecastPage from "./pages/ForecastPage";

type Tab = "forecast" | "accuracy";

export default function App() {
  const [tab, setTab] = useState<Tab>("forecast");

  return (
    <div className="app">
      <header>
        <h1>Wind forecast desk</h1>
        <nav>
          <button className={tab === "forecast" ? "active" : ""} onClick={() => setTab("forecast")}>
            Forecast
          </button>
          <button className={tab === "accuracy" ? "active" : ""} onClick={() => setTab("accuracy")}>
            Accuracy
          </button>
        </nav>
      </header>
      <main>{tab === "forecast" ? <ForecastPage /> : <AccuracyPage />}</main>
    </div>
  );
}