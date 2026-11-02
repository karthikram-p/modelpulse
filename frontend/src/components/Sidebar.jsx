import {
  LayoutDashboard,
  Boxes,
  Activity,
  GitBranch,
  ShieldCheck,
} from "lucide-react";

const navigation = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Model Registry", icon: Boxes },
  { label: "Monitoring", icon: Activity },
  { label: "Recovery Jobs", icon: GitBranch },
];

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="flex min-h-screen w-64 flex-col border-r border-slate-800 bg-slate-950 text-slate-300">
      <div className="flex items-center gap-3 border-b border-slate-800 px-6 py-6">
        <div className="rounded-xl bg-cyan-500 p-2 text-slate-950">
          <ShieldCheck size={24} />
        </div>

        <div>
          <h1 className="text-xl font-bold text-white">ModelPulse</h1>
          <p className="text-xs text-slate-400">Model Reliability Platform</p>
        </div>
      </div>

      <nav className="flex-1 space-y-2 px-4 py-6">
        {navigation.map(({ label, icon: Icon }) => {
          const isActive = activePage === label;

          return (
            <button
              key={label}
              onClick={() => onNavigate(label)}
              className={`flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left transition ${
                isActive
                  ? "bg-cyan-500/15 text-cyan-400"
                  : "text-slate-400 hover:bg-slate-900 hover:text-white"
              }`}
            >
              <Icon size={19} />
              <span className="text-sm font-medium">{label}</span>
            </button>
          );
        })}
      </nav>

      <div className="border-t border-slate-800 px-6 py-4">
        <p className="text-xs text-slate-500">Local Development</p>
        <p className="mt-1 text-sm text-emerald-400">● API integration</p>
      </div>
    </aside>
  );
}