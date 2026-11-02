import { useEffect, useMemo, useState } from "react";
import {
  Boxes,
  Activity,
  CheckCircle2,
  GitBranch,
  RefreshCw,
  AlertTriangle,
  TrendingUp,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

import StatCard from "../components/StatCard";
import StatusBadge from "../components/StatusBadge";
import {
  getModels,
  getRecoveryJobs,
  getModelHealth,
} from "../services/api";

function extractList(response, key) {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.[key])) return response[key];
  return [];
}

function formatMetric(value, digits = 2) {
  const number = Number(value);
  return value !== null &&
    value !== undefined &&
    value !== "" &&
    Number.isFinite(number)
    ? number.toFixed(digits)
    : "—";
}

function SectionHeading({ title, description }) {
  return (
    <div className="mb-5">
      <h3 className="text-lg font-semibold text-white">{title}</h3>
      <p className="mt-1 text-sm text-slate-400">{description}</p>
    </div>
  );
}

export default function Dashboard() {
  const [models, setModels] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [health, setHealth] = useState(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const loadDashboard = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError("");

    try {
      const [modelsResult, jobsResult] = await Promise.all([
        getModels(),
        getRecoveryJobs(),
      ]);

      const modelList = extractList(modelsResult, "models");
      const jobList = extractList(jobsResult, "jobs");

      setModels(modelList);
      setJobs(jobList);

      const productionModel = modelList.find(
        (model) =>
          String(model.status ?? "").toUpperCase() === "PRODUCTION"
      );

      if (productionModel?.model_id) {
        try {
          const healthResult = await getModelHealth(
            productionModel.model_id
          );
          setHealth(healthResult);
        } catch {
          setHealth(null);
        }
      } else {
        setHealth(null);
      }
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Unable to load dashboard data."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const productionModel = useMemo(
    () =>
      models.find(
        (model) =>
          String(model.status ?? "").toUpperCase() === "PRODUCTION"
      ),
    [models]
  );

  const candidateCount = models.filter(
    (model) =>
      String(model.status ?? "").toUpperCase() === "CANDIDATE"
  ).length;

  const healthy =
    String(health?.status ?? "").toUpperCase() === "HEALTHY";

  const chartData = models
    .filter((model) => Number.isFinite(Number(model.mae)))
    .map((model) => ({
      name: `${model.model_name || "Model"} ${
        model.version ? `v${String(model.version).replace(/^v/i, "")}` : ""
      }`.trim(),
      mae: Number(model.mae),
      status: model.status,
    }));

  if (loading) {
    return (
      <div className="flex min-h-64 items-center justify-center gap-3 text-slate-400">
        <RefreshCw className="animate-spin" size={20} />
        Loading ModelPulse dashboard...
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page heading */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">
            Model Overview
          </h2>
          <p className="mt-2 text-sm text-slate-400">
            Monitor model health, registered versions, and recovery activity.
          </p>
        </div>

        <button
          onClick={() => loadDashboard(true)}
          disabled={refreshing}
          className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-sm text-slate-200 transition hover:bg-slate-800 disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={refreshing ? "animate-spin" : ""}
          />
          Refresh
        </button>
      </div>

      {/* API errors */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-red-500/30 bg-red-500/10 p-4">
          <AlertTriangle
            size={20}
            className="mt-0.5 shrink-0 text-red-400"
          />
          <div>
            <p className="font-medium text-red-300">
              Unable to load dashboard data
            </p>
            <p className="mt-1 text-sm text-red-200/80">{error}</p>
            <p className="mt-2 text-xs text-slate-400">
              Check that FastAPI is running and that CORS is configured.
            </p>
          </div>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Registered Models"
          value={models.length}
          description="All registered model versions"
          icon={Boxes}
          accent="cyan"
        />

        <StatCard
          title="Production Models"
          value={productionModel ? 1 : 0}
          description="Currently active registry entries"
          icon={CheckCircle2}
          accent="green"
        />

        <StatCard
          title="Candidate Models"
          value={candidateCount}
          description="Models awaiting evaluation or approval"
          icon={GitBranch}
          accent="purple"
        />

        <StatCard
          title="Recovery Jobs"
          value={jobs.length}
          description="Recorded recovery workflow jobs"
          icon={Activity}
          accent="orange"
        />
      </div>

      {/* Production model and health */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-6 xl:col-span-2">
          <SectionHeading
            title="Production Model"
            description="Current model serving predictions"
          />

          {productionModel ? (
            <>
              <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-5">
                <div>
                  <h4 className="text-xl font-semibold text-white">
                    {productionModel.model_name || "Registered Model"}
                  </h4>
                  <p className="mt-1 text-sm text-slate-400">
                    Version{" "}
                    {String(productionModel.version ?? "—").replace(
                      /^v/i,
                      ""
                    )}
                  </p>
                </div>

                <StatusBadge status={productionModel.status} />
              </div>

              <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="rounded-lg bg-slate-950 p-4">
                  <p className="text-sm text-slate-400">
                    Mean Absolute Error
                  </p>
                  <p className="mt-2 text-2xl font-bold text-white">
                    {formatMetric(productionModel.mae)}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Lower is better
                  </p>
                </div>

                <div className="rounded-lg bg-slate-950 p-4">
                  <p className="text-sm text-slate-400">
                    Root Mean Squared Error
                  </p>
                  <p className="mt-2 text-2xl font-bold text-white">
                    {formatMetric(productionModel.rmse)}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Lower is better
                  </p>
                </div>

                <div className="rounded-lg bg-slate-950 p-4">
                  <p className="text-sm text-slate-400">
                    R² Score
                  </p>
                  <p className="mt-2 text-2xl font-bold text-white">
                    {formatMetric(productionModel.r2, 4)}
                  </p>
                  <p className="mt-1 text-xs text-slate-500">
                    Higher is better
                  </p>
                </div>
              </div>
            </>
          ) : (
            <p className="rounded-lg bg-slate-950 p-5 text-sm text-slate-400">
              No production model was found in the registry.
            </p>
          )}
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
          <SectionHeading
            title="Model Health"
            description="Latest health evaluation for production"
          />

          {health ? (
            <>
              <div className="flex items-center gap-3">
                <div
                  className={`rounded-xl p-3 ${
                    healthy
                      ? "bg-emerald-500/10 text-emerald-400"
                      : "bg-amber-500/10 text-amber-400"
                  }`}
                >
                  {healthy ? (
                    <CheckCircle2 size={28} />
                  ) : (
                    <AlertTriangle size={28} />
                  )}
                </div>

                <div>
                  <p className="text-lg font-semibold text-white">
                    {String(health.status ?? "UNKNOWN").replaceAll(
                      "_",
                      " "
                    )}
                  </p>
                  <p className="text-sm text-slate-400">
                    Current evaluation status
                  </p>
                </div>
              </div>

              <div className="mt-6 space-y-4">
                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <span className="text-sm text-slate-400">
                    Evaluations
                  </span>
                  <span className="font-medium text-white">
                    {health.evaluation_count ?? "—"}
                  </span>
                </div>

                <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                  <span className="text-sm text-slate-400">
                    Current MAE
                  </span>
                  <span className="font-medium text-white">
                    {formatMetric(health.mae)}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-400">
                    MAE Threshold
                  </span>
                  <span className="font-medium text-white">
                    {formatMetric(health.mae_threshold)}
                  </span>
                </div>
              </div>

              <p className="mt-5 text-xs leading-5 text-slate-500">
                {health.message ||
                  "Health status returned by the monitoring service."}
              </p>
            </>
          ) : (
            <div className="rounded-lg bg-slate-950 p-4 text-sm text-slate-400">
              Health information is unavailable. Check the production model
              and monitoring endpoint.
            </div>
          )}
        </section>
      </div>

      {/* Model comparison chart */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <SectionHeading
          title="Model Error Comparison"
          description="Compare registered models using their recorded MAE metrics"
        />

        {chartData.length > 0 ? (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                margin={{ top: 10, right: 20, left: 0, bottom: 10 }}
              >
                <CartesianGrid
                  stroke="#334155"
                  strokeDasharray="3 3"
                  vertical={false}
                />
                <XAxis
                  dataKey="name"
                  stroke="#94a3b8"
                  tick={{ fill: "#cbd5e1", fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  stroke="#94a3b8"
                  tick={{ fill: "#94a3b8", fontSize: 12 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#020617",
                    border: "1px solid #334155",
                    borderRadius: "8px",
                    color: "#f8fafc",
                  }}
                  formatter={(value) => [
                    Number(value).toFixed(2),
                    "MAE",
                  ]}
                />
                <Bar
                  dataKey="mae"
                  fill="#22d3ee"
                  radius={[5, 5, 0, 0]}
                  maxBarSize={70}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <div className="flex h-48 items-center justify-center text-sm text-slate-500">
            No valid model MAE metrics are available for the chart.
          </div>
        )}

        <p className="mt-3 flex items-center gap-2 text-xs text-slate-500">
          <TrendingUp size={14} />
          A lower MAE indicates smaller average prediction errors. Compare
          models on the same evaluation dataset.
        </p>
      </section>

      {/* Recent recovery activity */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-6">
        <SectionHeading
          title="Recent Recovery Activity"
          description="Latest tracked recovery and evaluation workflows"
        />

        {jobs.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="px-4 py-3 font-medium">Job ID</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Reason</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                </tr>
              </thead>

              <tbody>
                {jobs.slice(0, 5).map((job) => (
                  <tr
                    key={job.job_id}
                    className="border-b border-slate-800/70 last:border-0 hover:bg-slate-800/30"
                  >
                    <td className="px-4 py-4 font-mono text-xs text-slate-300">
                      {job.job_id
                        ? `${job.job_id.slice(0, 8)}...`
                        : "—"}
                    </td>

                    <td className="px-4 py-4">
                      <StatusBadge status={job.status} />
                    </td>

                    <td className="max-w-xs px-4 py-4 text-slate-400">
                      {job.reason || "—"}
                    </td>

                    <td className="whitespace-nowrap px-4 py-4 text-slate-400">
                      {job.created_at
                        ? new Date(job.created_at).toLocaleString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="rounded-lg bg-slate-950 p-5 text-sm text-slate-400">
            No recovery jobs have been recorded yet.
          </p>
        )}
      </section>

      <p className="text-xs text-slate-500">
        ModelPulse dashboard · Data retrieved from your FastAPI backend.
      </p>
    </div>
  );
}