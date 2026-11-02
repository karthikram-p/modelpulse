import { useState } from "react";
import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import ModelRegistry from "./pages/ModelRegistry";
import Monitoring from "./pages/Monitoring";
import RecoveryJobs from "./pages/RecoveryJobs";

export default function App() {
  const [activePage, setActivePage] = useState("Dashboard");

  const pages = {
    Dashboard: Dashboard,
    "Model Registry": ModelRegistry,
    Monitoring: Monitoring,
    "Recovery Jobs": RecoveryJobs,
  };

  const CurrentPage = pages[activePage];

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="flex">
        <Sidebar
          activePage={activePage}
          onNavigate={setActivePage}
        />

        <main className="min-w-0 flex-1 p-8">
          <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-sm text-slate-400">
                Model Reliability and Recovery Platform
              </p>
              <h2 className="mt-2 text-3xl font-bold">{activePage}</h2>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-2">
              <span className="mr-2 inline-block h-2 w-2 rounded-full bg-emerald-400" />
              <span className="text-sm text-slate-300">
                Backend connected
              </span>
            </div>
          </header>

          <CurrentPage />
        </main>
      </div>
    </div>
  );
}