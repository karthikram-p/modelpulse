export default function StatCard({
  title,
  value,
  description,
  icon: Icon,
  accent = "cyan",
}) {
  const accents = {
    cyan: "bg-cyan-500/10 text-cyan-400",
    green: "bg-emerald-500/10 text-emerald-400",
    purple: "bg-violet-500/10 text-violet-400",
    orange: "bg-orange-500/10 text-orange-400",
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-start justify-between">
        <p className="text-sm text-slate-400">{title}</p>

        {Icon && (
          <div className={`rounded-lg p-2 ${accents[accent] ?? accents.cyan}`}>
            <Icon size={20} />
          </div>
        )}
      </div>

      <h3 className="mt-4 text-3xl font-semibold text-white">{value}</h3>
      <p className="mt-2 text-xs text-slate-500">{description}</p>
    </div>
  );
}