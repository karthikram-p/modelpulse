import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Database,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  XCircle,
} from "lucide-react";

import {
  getModels,
  getModelHealth,
  getPerformance,
  getDrift,
  getPredictions,
} from "../services/api";

import StatusBadge from "../components/StatusBadge";

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(digits) : "—";
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

function getErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.message ||
    "An unexpected error occurred."
  );
}

function MetricCard({ title, value, description, icon: Icon }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">{title}</p>
        <Icon size={20} className="text-sky-400" />
      </div>

      <p className="mt-3 text-2xl font-semibold text-white">
        {value ?? "—"}
      </p>

      {description && (
        <p className="mt-2 text-xs text-slate-500">{description}</p>
      )}
    </div>
  );
}

function Section({ title, icon: Icon, children }) {
  return (
    <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="mb-5 flex items-center gap-2">
        <Icon size={19} className="text-sky-400" />
        <h2 className="text-lg font-semibold text-white">{title}</h2>
      </div>

      {children}
    </section>
  );
}

function EmptyState({ message }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
      {message}
    </div>
  );
}

export default function Monitoring() {
  const [models, setModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState("");

  const [health, setHealth] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [drift, setDrift] = useState(null);
  const [predictions, setPredictions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  const productionModel = models.find(
    (model) => model.model_id === selectedModelId
  );

  const loadMonitoringData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const modelsResponse = await getModels();

      const modelList = Array.isArray(modelsResponse)
        ? modelsResponse
        : modelsResponse?.models ?? [];

      setModels(modelList);

      const productionModels = modelList.filter(
        (model) => model.status === "PRODUCTION"
      );

      const activeModelId =
        selectedModelId &&
        productionModels.some(
          (model) => model.model_id === selectedModelId
        )
          ? selectedModelId
          : productionModels[0]?.model_id ?? "";

      setSelectedModelId(activeModelId);

      const results = await Promise.allSettled([
        getDrift(100),
        getPredictions(100),
        activeModelId ? getModelHealth(activeModelId) : Promise.resolve(null),
        activeModelId
          ? getPerformance(activeModelId)
          : Promise.resolve(null),
      ]);

      const [
        driftResult,
        predictionsResult,
        healthResult,
        performanceResult,
      ] = results;

      if (driftResult.status === "fulfilled") {
        setDrift(driftResult.value);
      } else {
        setDrift(null);
      }

      if (predictionsResult.status === "fulfilled") {
        const response = predictionsResult.value;

        setPredictions(
          Array.isArray(response)
            ? response
            : response?.predictions ?? []
        );
      } else {
        setPredictions([]);
      }

      if (healthResult.status === "fulfilled") {
        setHealth(healthResult.value);
      } else {
        setHealth(null);
      }

      if (performanceResult.status === "fulfilled") {
        setPerformance(performanceResult.value);
      } else {
        setPerformance(null);
      }

      const failures = results.filter(
        (result) => result.status === "rejected"
      );

      if (failures.length > 0) {
        setError(
          "Some monitoring data could not be loaded. Check the API and refresh the page."
        );
      }

      setLastUpdated(new Date());
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [selectedModelId]);

  useEffect(() => {
    loadMonitoringData();
  }, [loadMonitoringData]);

  const healthStatus = health?.status ?? "UNKNOWN";

  const driftedFeatures = Array.isArray(drift?.drifted_features)
    ? drift.drifted_features
    : [];

  const driftDetected =
    drift?.status === "DRIFT_DETECTED" || driftedFeatures.length > 0;

  const performanceMae =
    performance?.mae ??
    performance?.mean_absolute_error ??
    performance?.summary?.mae;

  const evaluatedCount =
    health?.evaluation_count ??
    health?.evaluated_predictions ??
    health?.evaluations ??
    performance?.evaluation_count ??
    performance?.total_evaluations;

  const driftPredictionCount =
    drift?.prediction_count ?? drift?.predictions_checked;

  return (
    <div className="space-y-6 p-6 text-slate-200">
      {/* Page Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="text-sky-400" size={25} />
            <h1 className="text-2xl font-bold text-white">
              Model Monitoring
            </h1>
          </div>

          <p className="mt-2 text-sm text-slate-400">
            Monitor production model health, performance, and input drift.
          </p>
        </div>

        <button
          onClick={loadMonitoringData}
          disabled={loading}
          className="flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={loading ? "animate-spin" : ""}
          />
          {loading ? "Refreshing..." : "Refresh Data"}
        </button>
      </div>

      {/* Model Selector */}
      <div className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-900 p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium text-white">
            Production Model
          </p>

          <p className="mt-1 text-xs text-slate-400">
            Select a registered production model to inspect.
          </p>
        </div>

        <select
          value={selectedModelId}
          onChange={(event) => setSelectedModelId(event.target.value)}
          className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-white outline-none focus:border-sky-500 sm:max-w-md"
        >
          {models.filter((model) => model.status === "PRODUCTION").length ===
          0 ? (
            <option value="">No production model available</option>
          ) : (
            models
              .filter((model) => model.status === "PRODUCTION")
              .map((model) => (
                <option key={model.model_id} value={model.model_id}>
                  {model.model_name} — v{model.version}
                </option>
              ))
          )}
        </select>
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-3 rounded-lg border border-amber-700/50 bg-amber-950/30 p-4 text-sm text-amber-300"
        >
          <AlertTriangle size={19} className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {loading && !lastUpdated ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-12 text-center text-slate-400">
          Loading monitoring data...
        </div>
      ) : (
        <>
          {/* Health and Drift Summary */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard
              title="Model Health"
              value={healthStatus.replaceAll("_", " ")}
              description="Current health assessment"
              icon={ShieldCheck}
            />

            <MetricCard
              title="Evaluated Predictions"
              value={evaluatedCount ?? "—"}
              description="Predictions with recorded actual values"
              icon={Database}
            />

            <MetricCard
              title="Evaluation MAE"
              value={formatNumber(performanceMae)}
              description="Lower is generally better"
              icon={TrendingUp}
            />

            <MetricCard
              title="Drifted Features"
              value={
                drift
                  ? driftedFeatures.length
                  : "—"
              }
              description={
                drift
                  ? `${driftPredictionCount ?? "—"} predictions checked`
                  : "Drift information unavailable"
              }
              icon={AlertTriangle}
            />
          </div>

          {/* Health Details */}
          <Section title="Model Health Details" icon={ShieldCheck}>
            {!selectedModelId ? (
              <EmptyState message="Register and promote a model before viewing its health." />
            ) : !health ? (
              <EmptyState message="Health information is unavailable. Check the health endpoint." />
            ) : (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-sm text-slate-400">
                    Current status
                  </span>
                  <StatusBadge status={healthStatus} />
                </div>

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <MetricCard
                    title="Health MAE"
                    value={formatNumber(health.mae)}
                    description="Observed evaluation error"
                    icon={TrendingUp}
                  />

                  <MetricCard
                    title="MAE Threshold"
                    value={formatNumber(
                    health.threshold ?? health.mae_threshold ?? 75
                    )}
                    description="Configured degradation threshold"
                    icon={Activity}
                  />

                  <MetricCard
                    title="Evaluations"
                    value={evaluatedCount ?? "—"}
                    description="Available evaluation records"
                    icon={Database}
                  />
                </div>

                {health.message && (
                  <p className="text-sm text-slate-400">
                    {health.message}
                  </p>
                )}
              </div>
            )}
          </Section>

          {/* Drift Detection */}
          <Section title="Feature Drift Detection" icon={AlertTriangle}>
            {!drift ? (
              <EmptyState message="Drift results are unavailable. Check the monitoring/drift endpoint." />
            ) : driftDetected ? (
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-amber-400">
                  <AlertTriangle size={20} />
                  <span className="font-semibold">
                    Potential drift detected
                  </span>
                </div>

                <p className="text-sm text-slate-400">
                  The monitoring service flagged the following input
                  features for review.
                </p>

                {driftedFeatures.length > 0 ? (
                  <div className="flex flex-wrap gap-2">
                    {driftedFeatures.map((feature) => (
                      <span
                        key={feature}
                        className="rounded-full border border-amber-700/50 bg-amber-950/40 px-3 py-1.5 text-sm text-amber-300"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">
                    Drift was flagged, but no feature names were returned.
                  </p>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-3 text-emerald-400">
                <CheckCircle2 size={22} />
                <div>
                  <p className="font-medium">No drift detected</p>
                  <p className="mt-1 text-sm text-slate-400">
                    No features were flagged by the current drift check.
                  </p>
                </div>
              </div>
            )}

            {drift?.message && (
              <p className="mt-4 text-sm text-slate-400">
                {drift.message}
              </p>
            )}

            <p className="mt-4 text-xs text-slate-500">
              Drift detection is a statistical warning, not proof that
              model accuracy has declined.
            </p>
          </Section>

          {/* Performance Details */}
          <Section title="Performance Summary" icon={TrendingUp}>
            {!performance ? (
              <EmptyState message="Performance data is unavailable. Check the performance endpoint." />
            ) : (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <MetricCard
                  title="Mean Absolute Error"
                  value={formatNumber(
                    performance.mae ??
                      performance.mean_absolute_error ??
                      performance.summary?.mae
                  )}
                  description="Average absolute prediction error"
                  icon={TrendingUp}
                />

                <MetricCard
                  title="Evaluations Recorded"
                  value={
                    performance.evaluation_count ??
                    performance.total_evaluations ??
                    evaluatedCount ??
                    "—"
                  }
                  description="Records included in performance tracking"
                  icon={Database}
                />
              </div>
            )}
          </Section>

          {/* Recent Predictions */}
          <Section title="Recent Predictions" icon={Clock}>
            {predictions.length === 0 ? (
              <EmptyState message="No prediction records are available." />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[700px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs uppercase text-slate-500">
                      <th className="px-4 py-3">Prediction ID</th>
                      <th className="px-4 py-3">Model Version</th>
                      <th className="px-4 py-3">Predicted Value</th>
                      <th className="px-4 py-3">Timestamp</th>
                    </tr>
                  </thead>

                  <tbody>
                    {predictions.map((prediction, index) => (
                      <tr
                        key={
                          prediction.prediction_id ??
                          `${prediction.model_id}-${index}`
                        }
                        className="border-b border-slate-800/70 hover:bg-slate-800/40"
                      >
                        <td className="px-4 py-3 font-mono text-xs text-slate-400">
                          {prediction.prediction_id
                            ? `${String(
                                prediction.prediction_id
                              ).slice(0, 12)}...`
                            : "—"}
                        </td>

                        <td className="px-4 py-3 text-slate-300">
                          {prediction.model_version != null
                            ? `v${prediction.model_version}`
                            : "—"}
                        </td>

                        <td className="px-4 py-3 font-medium text-white">
                          {formatNumber(prediction.predicted_value, 2)}
                        </td>

                        <td className="px-4 py-3 text-slate-400">
                          {formatDate(prediction.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Section>

          {/* Footer */}
          <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
            <p>
              Model: {productionModel?.model_name ?? "Unavailable"}
              {productionModel?.version != null
                ? ` · Version ${productionModel.version}`
                : ""}
            </p>

            <p>
              Last updated:{" "}
              {lastUpdated ? lastUpdated.toLocaleTimeString() : "—"}
            </p>
          </div>
        </>
      )}
    </div>
  );
}