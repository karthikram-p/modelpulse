export default function StatusBadge({ status }) {
  const normalized = String(status ?? "UNKNOWN").toUpperCase();

  const styles = {
    PRODUCTION: "bg-emerald-500/10 text-emerald-400",
    HEALTHY: "bg-emerald-500/10 text-emerald-400",
    DEPLOYED: "bg-emerald-500/10 text-emerald-400",
    CANDIDATE: "bg-blue-500/10 text-blue-400",
    DEGRADED: "bg-red-500/10 text-red-400",
    REJECTED: "bg-red-500/10 text-red-400",
    AWAITING_APPROVAL: "bg-amber-500/10 text-amber-400",
    WAITING_FOR_DATA: "bg-amber-500/10 text-amber-400",
    NO_RECOVERY_REQUIRED: "bg-emerald-500/10 text-emerald-400",
    DRY_RUN_COMPLETED: "bg-violet-500/10 text-violet-400",
  };

  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${
        styles[normalized] ?? "bg-slate-700 text-slate-300"
      }`}
    >
      {normalized.replaceAll("_", " ")}
    </span>
  );
}