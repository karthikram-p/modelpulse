import { useEffect, useState } from "react";
import { RefreshCw, GitCompare, Boxes } from "lucide-react";
import { getModels, compareModels } from "../services/api";
import StatusBadge from "../components/StatusBadge";

function Metric({ label, value }) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-800/60 p-4">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-xl font-semibold text-white">
        {value === null || value === undefined || value === ""
          ? "—"
          : value}
      </p>
    </div>
  );
}

export default function ModelRegistry() {
  const [models, setModels] = useState([]);
  const [filter, setFilter] = useState("ALL");
  const [selectedCandidate, setSelectedCandidate] = useState("");
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState("");

  async function loadModels() {
    setLoading(true);
    setError("");

    try {
      const response = await getModels();
      const list = Array.isArray(response)
        ? response
        : response.models ?? [];

      setModels(list);

      const candidate = list.find(
        (model) =>
          String(model.status).toUpperCase() === "CANDIDATE"
      );

      setSelectedCandidate(candidate?.model_id ?? "");
      setComparison(null);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Failed to load model registry."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadModels();
  }, []);

  const filteredModels =
    filter === "ALL"
      ? models
      : models.filter(
          (model) =>
            String(model.status).toUpperCase() === filter
        );

  const candidates = models.filter(
    (model) =>
      String(model.status).toUpperCase() === "CANDIDATE"
  );

  async function handleCompare() {
    if (!selectedCandidate) {
      setError("Select a candidate model first.");
      return;
    }

    setComparing(true);
    setError("");
    setComparison(null);

    try {
      const result = await compareModels(selectedCandidate);
      setComparison(result);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Model comparison failed."
      );
    } finally {
      setComparing(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Model Registry
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            Manage model versions and compare candidate performance.
          </p>
        </div>

        <button
          onClick={loadModels}
          disabled={loading}
          className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm hover:bg-slate-800 disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={loading ? "animate-spin" : ""}
          />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          {
            label: "All Versions",
            value: models.length,
          },
          {
            label: "Production",
            value: models.filter(
              (m) => String(m.status).toUpperCase() === "PRODUCTION"
            ).length,
          },
          {
            label: "Candidates",
            value: candidates.length,
          },
        ].map((item) => (
          <div
            key={item.label}
            className="rounded-xl border border-slate-800 bg-slate-900 p-5"
          >
            <p className="text-sm text-slate-400">{item.label}</p>
            <p className="mt-3 text-3xl font-bold text-white">
              {item.value}
            </p>
          </div>
        ))}
      </div>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="font-semibold text-white">
              Registered Models
            </h3>
            <p className="mt-1 text-sm text-slate-400">
              Metrics recorded during model evaluation.
            </p>
          </div>

          <select
            value={filter}
            onChange={(event) => setFilter(event.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white"
          >
            <option value="ALL">All models</option>
            <option value="PRODUCTION">Production</option>
            <option value="CANDIDATE">Candidates</option>
          </select>
        </div>

        {loading ? (
          <p className="py-10 text-center text-slate-400">
            Loading registered models...
          </p>
        ) : filteredModels.length === 0 ? (
          <div className="py-12 text-center">
            <Boxes className="mx-auto text-slate-600" size={36} />
            <p className="mt-3 text-slate-400">
              No models found for this filter.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[700px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="px-4 py-3 font-medium">Model</th>
                  <th className="px-4 py-3 font-medium">Version</th>
                  <th className="px-4 py-3 font-medium">MAE</th>
                  <th className="px-4 py-3 font-medium">RMSE</th>
                  <th className="px-4 py-3 font-medium">R²</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                </tr>
              </thead>

              <tbody>
                {filteredModels.map((model) => (
                  <tr
                    key={model.model_id}
                    className="border-b border-slate-800/70 last:border-0 hover:bg-slate-800/30"
                  >
                    <td className="px-4 py-4">
                      <p className="font-medium text-white">
                        {model.model_name || "Model"}
                      </p>
                      <p className="mt-1 font-mono text-xs text-slate-500">
                        {model.model_id}
                      </p>
                    </td>

                    <td className="px-4 py-4 text-slate-300">
                      {String(model.version ?? "—").replace(/^v/i, "v")}
                    </td>

                    <td className="px-4 py-4 text-slate-300">
                      <Metric label="" value={model.mae} />
                    </td>

                    <td className="px-4 py-4 text-slate-300">
                      <Metric label="" value={model.rmse} />
                    </td>

                    <td className="px-4 py-4 text-slate-300">
                      <Metric label="" value={model.r2} digits={4} />
                    </td>

                    <td className="px-4 py-4">
                      <StatusBadge status={model.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <div className="mb-5">
          <h3 className="flex items-center gap-2 font-semibold text-white">
            <GitCompare size={19} className="text-cyan-400" />
            Compare Candidate with Production
          </h3>
          <p className="mt-2 text-sm text-slate-400">
            Evaluate a candidate using the backend's existing acceptance
            criteria.
          </p>
        </div>

        {candidates.length === 0 ? (
          <p className="text-sm text-slate-400">
            No candidate models are currently registered.
          </p>
        ) : (
          <div className="flex flex-col gap-3 sm:flex-row">
            <select
              value={selectedCandidate}
              onChange={(event) => {
                setSelectedCandidate(event.target.value);
                setComparison(null);
              }}
              className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white"
            >
              {candidates.map((candidate) => (
                <option
                  key={candidate.model_id}
                  value={candidate.model_id}
                >
                  {candidate.model_name || "Model"} —{" "}
                  {candidate.version} (
                  {candidate.model_id.slice(0, 8)})
                </option>
              ))}
            </select>

            <button
              onClick={handleCompare}
              disabled={comparing || !selectedCandidate}
              className="flex items-center justify-center gap-2 rounded-lg bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-cyan-400 disabled:opacity-50"
            >
              {comparing && (
                <RefreshCw size={16} className="animate-spin" />
              )}
              {comparing ? "Comparing..." : "Compare Models"}
            </button>
          </div>
        )}

        {/* Comparison Result */}
        {comparison && (
        <div className="mt-6 rounded-xl border border-slate-700 bg-slate-900 p-6">
            <div className="mb-5 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-white">
                Comparison Result
            </h2>

            <span className="rounded-full bg-amber-500/10 px-3 py-1 text-sm font-medium text-amber-400">
                {comparison.recommendation?.replaceAll("_", " ") || "UNKNOWN"}
            </span>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Metric
                label="Production MAE"
                value={Number(
                comparison.production_model?.metrics?.mae
                ).toFixed(2)}
            />

            <Metric
                label="Candidate MAE"
                value={Number(
                comparison.candidate_model?.metrics?.mae
                ).toFixed(2)}
            />

            <Metric
                label="MAE Improvement (%)"
                value={`${Number(
                    comparison?.comparison?.mae_improvement_percent ?? 0
                ).toFixed(2)}%`}
                />
            </div>

            <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
            <Metric
                label="Production RMSE"
                value={Number(
                comparison.production_model?.metrics?.rmse
                ).toFixed(2)}
            />

            <Metric
                label="Candidate RMSE"
                value={Number(
                comparison.candidate_model?.metrics?.rmse
                ).toFixed(2)}
            />

            <Metric
                label="Test Rows"
                value={comparison.comparison?.test_rows ?? "—"}
            />

            <Metric
                label="Production R²"
                value={Number(
                comparison.production_model?.metrics?.r2
                ).toFixed(4)}
            />

            <Metric
                label="Candidate R²"
                value={Number(
                comparison.candidate_model?.metrics?.r2
                ).toFixed(4)}
            />

            <Metric
                label="Production Changed"
                value={comparison?.production_changed === true ? "Yes" : "No"}
                />
            </div>

            <div className="mt-6 rounded-lg border border-slate-700 bg-slate-800/60 p-4">
            <h3 className="mb-3 font-medium text-white">
                Acceptance Checks
            </h3>

            <div className="space-y-2 text-sm">
                <p className="text-slate-300">
                MAE improved by at least 1%:{" "}
                <span className={
                    comparison.acceptance_checks?.mae_improved_by_at_least_1_percent
                    ? "text-emerald-400"
                    : "text-amber-400"
                }>
                    {comparison.acceptance_checks?.mae_improved_by_at_least_1_percent
                    ? "PASS"
                    : "NOT MET"}
                </span>
                </p>

                <p className="text-slate-300">
                RMSE degradation within 2%:{" "}
                <span className={
                    comparison.acceptance_checks?.rmse_degradation_within_2_percent
                    ? "text-emerald-400"
                    : "text-red-400"
                }>
                    {comparison.acceptance_checks?.rmse_degradation_within_2_percent
                    ? "PASS"
                    : "FAIL"}
                </span>
                </p>

                <p className="text-slate-300">
                R² drop within 0.01:{" "}
                <span className={
                    comparison.acceptance_checks?.r2_drop_within_0_01
                    ? "text-emerald-400"
                    : "text-red-400"
                }>
                    {comparison.acceptance_checks?.r2_drop_within_0_01
                    ? "PASS"
                    : "FAIL"}
                </span>
                </p>
            </div>
            </div>

            <p className="mt-4 text-sm text-slate-400">
            {comparison.note ||
                "Review the comparison before making a deployment decision."}
            </p>

            <details className="mt-4">
            <summary className="cursor-pointer text-sm text-sky-400">
                View complete comparison response
            </summary>

            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-300">
                {JSON.stringify(comparison, null, 2)}
            </pre>
            </details>
        </div>
        )}
      </section>
    </div>
  );
}