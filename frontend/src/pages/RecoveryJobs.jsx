import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Eye,
  Play,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from "lucide-react";

import {
  getModels,
  getRecoveryJobs,
  runRecovery,
  runRecoveryDryRun,
  approveRecovery,
  rejectRecovery,
} from "../services/api";

import StatusBadge from "../components/StatusBadge";

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

function formatNumber(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(2) : "—";
}

function getErrorMessage(error) {
  return (
    error?.response?.data?.detail ||
    error?.message ||
    "An unexpected error occurred."
  );
}

function parseComparison(value) {
  if (!value) return null;

  if (typeof value === "object") return value;

  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function StatCard({ title, value, icon: Icon }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">{title}</p>
        <Icon size={20} className="text-sky-400" />
      </div>

      <p className="mt-3 text-2xl font-semibold text-white">
        {value}
      </p>
    </div>
  );
}

export default function RecoveryJobs() {
  const [models, setModels] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState("");
  const [selectedJob, setSelectedJob] = useState(null);

  const [loading, setLoading] = useState(true);
  const [busyAction, setBusyAction] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  const productionModels = models.filter(
    (model) => model.status === "PRODUCTION"
  );

  const awaitingApproval = jobs.filter(
    (job) => job.status === "AWAITING_APPROVAL"
  ).length;

  const deployedJobs = jobs.filter(
    (job) => job.status === "DEPLOYED"
  ).length;

  const rejectedJobs = jobs.filter(
    (job) => job.status === "REJECTED"
  ).length;

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [modelsResponse, jobsResponse] = await Promise.all([
        getModels(),
        getRecoveryJobs(),
      ]);

      const modelList = Array.isArray(modelsResponse)
        ? modelsResponse
        : modelsResponse?.models ?? [];

      const jobList = Array.isArray(jobsResponse)
        ? jobsResponse
        : jobsResponse?.jobs ?? [];

      setModels(modelList);
      setJobs(jobList);

      setSelectedModelId((currentId) => {
        if (
          currentId &&
          modelList.some(
            (model) =>
              model.model_id === currentId &&
              model.status === "PRODUCTION"
          )
        ) {
          return currentId;
        }

        return (
          modelList.find((model) => model.status === "PRODUCTION")
            ?.model_id ?? ""
        );
      });

      setLastUpdated(new Date());
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleRecovery(dryRun = false) {
    if (!selectedModelId) {
      setError("Select a production model first.");
      return;
    }

    const actionName = dryRun ? "dry-run" : "recovery";

    if (
      !dryRun &&
      !window.confirm(
        "Run the recovery workflow for the selected production model? This may train a candidate model, but deployment still requires approval."
      )
    ) {
      return;
    }

    setBusyAction(actionName);
    setError("");
    setMessage("");
    setSelectedJob(null);

    try {
      const result = dryRun
        ? await runRecoveryDryRun(selectedModelId)
        : await runRecovery(selectedModelId);

      setMessage(
        dryRun
          ? "Dry run completed. No model was deployed."
          : "Recovery workflow completed. Review the resulting job status."
      );

      await loadData();

      if (result?.job_id) {
        setSelectedJob(result);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyAction("");
    }
  }

  async function handleApprove(job) {
    if (job.status !== "AWAITING_APPROVAL") {
      setError("Only jobs awaiting approval can be approved.");
      return;
    }

    const confirmed = window.confirm(
      "Approve this recovery job and promote its candidate model to production? Review the comparison before continuing."
    );

    if (!confirmed) return;

    setBusyAction(`approve-${job.job_id}`);
    setError("");
    setMessage("");

    try {
      await approveRecovery(job.job_id);

      setMessage(
        `Recovery job ${job.job_id} was approved. Refreshing the registry and job status.`
      );

      setSelectedJob(null);
      await loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyAction("");
    }
  }

  async function handleReject(job) {
    if (job.status !== "AWAITING_APPROVAL") {
      setError("Only jobs awaiting approval can be rejected.");
      return;
    }

    const reason = window.prompt(
      "Enter a reason for rejecting this candidate:"
    );

    if (reason === null) return;

    if (!reason.trim()) {
      setError("Enter a rejection reason.");
      return;
    }

    setBusyAction(`reject-${job.job_id}`);
    setError("");
    setMessage("");

    try {
      await rejectRecovery(job.job_id, reason.trim());

      setMessage("Recovery job rejected successfully.");
      setSelectedJob(null);
      await loadData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusyAction("");
    }
  }

  const detailJob =
    selectedJob &&
    jobs.find((job) => job.job_id === selectedJob.job_id);

  const displayedJob = detailJob ?? selectedJob;

  const comparison = parseComparison(
    displayedJob?.comparison_json ??
      displayedJob?.comparison ??
      displayedJob?.result?.comparison
  );

  return (
    <div className="space-y-6 p-6 text-slate-200">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="flex items-center gap-2">
            <Activity size={25} className="text-sky-400" />
            <h1 className="text-2xl font-bold text-white">
              Recovery Jobs
            </h1>
          </div>

          <p className="mt-2 text-sm text-slate-400">
            Manage model recovery, candidate evaluation, and deployment
            approvals.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading || Boolean(busyAction)}
          className="flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm text-white hover:bg-slate-700 disabled:opacity-50"
        >
          <RefreshCw
            size={16}
            className={loading ? "animate-spin" : ""}
          />
          Refresh Jobs
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div
          role="alert"
          className="flex gap-3 rounded-lg border border-red-800/60 bg-red-950/30 p-4 text-sm text-red-300"
        >
          <AlertTriangle size={19} className="shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {message && (
        <div
          role="status"
          className="flex gap-3 rounded-lg border border-emerald-800/60 bg-emerald-950/30 p-4 text-sm text-emerald-300"
        >
          <CheckCircle2 size={19} className="shrink-0" />
          <p>{message}</p>
        </div>
      )}

      {/* Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          title="Total Recovery Jobs"
          value={jobs.length}
          icon={Activity}
        />

        <StatCard
          title="Awaiting Approval"
          value={awaitingApproval}
          icon={Clock}
        />

        <StatCard
          title="Successfully Deployed"
          value={deployedJobs}
          icon={ShieldCheck}
        />

        <StatCard
          title="Rejected Jobs"
          value={rejectedJobs}
          icon={XCircle}
        />
      </div>

      {/* Recovery Controls */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <h2 className="text-lg font-semibold text-white">
          Start Recovery
        </h2>

        <p className="mt-2 text-sm text-slate-400">
          Choose a production model and run the recovery workflow or a
          non-deploying dry run.
        </p>

        <div className="mt-5 flex flex-col gap-4 lg:flex-row lg:items-end">
          <div className="flex-1">
            <label
              htmlFor="production-model"
              className="mb-2 block text-sm text-slate-300"
            >
              Production Model
            </label>

            <select
              id="production-model"
              value={selectedModelId}
              onChange={(event) =>
                setSelectedModelId(event.target.value)
              }
              disabled={Boolean(busyAction)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-white outline-none focus:border-sky-500"
            >
              {productionModels.length === 0 ? (
                <option value="">No production model available</option>
              ) : (
                productionModels.map((model) => (
                  <option key={model.model_id} value={model.model_id}>
                    {model.model_name} — v{model.version}
                  </option>
                ))
              )}
            </select>
          </div>

          <button
            onClick={() => handleRecovery(false)}
            disabled={
              !selectedModelId ||
              loading ||
              Boolean(busyAction)
            }
            className="flex items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Play size={16} />
            {busyAction === "recovery"
              ? "Running Recovery..."
              : "Run Recovery"}
          </button>

          <button
            onClick={() => handleRecovery(true)}
            disabled={
              !selectedModelId ||
              loading ||
              Boolean(busyAction)
            }
            className="flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-800 px-4 py-2.5 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Activity size={16} />
            {busyAction === "dry-run"
              ? "Running Dry Run..."
              : "Run Dry Run"}
          </button>
        </div>

        <p className="mt-4 text-xs text-slate-500">
          Run Recovery executes the recovery decision workflow. Run Dry
          Run evaluates a new candidate without promoting it. Neither
          action bypasses the backend's deployment approval requirements.
        </p>
      </section>

      {/* Jobs Table */}
      <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
        <div className="mb-5 flex items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-white">
            Recovery Job History
          </h2>

          <span className="text-sm text-slate-400">
            {jobs.length} jobs
          </span>
        </div>

        {loading && jobs.length === 0 ? (
          <p className="py-10 text-center text-slate-400">
            Loading recovery jobs...
          </p>
        ) : jobs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-700 p-8 text-center">
            <Activity
              size={28}
              className="mx-auto mb-3 text-slate-500"
            />
            <p className="font-medium text-white">
              No recovery jobs yet
            </p>
            <p className="mt-2 text-sm text-slate-400">
              Run a recovery workflow or a dry run to create a job.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase text-slate-500">
                  <th className="px-4 py-3">Job ID</th>
                  <th className="px-4 py-3">Production Model</th>
                  <th className="px-4 py-3">Candidate Model</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                  <th className="px-4 py-3">Actions</th>
                </tr>
              </thead>

              <tbody>
                {jobs.map((job) => {
                  const canApprove =
                    job.status === "AWAITING_APPROVAL";

                  const production = models.find(
                    (model) =>
                      model.model_id === job.production_model_id
                  );

                  const candidate = models.find(
                    (model) =>
                      model.model_id === job.candidate_model_id
                  );

                  return (
                    <tr
                      key={job.job_id}
                      className="border-b border-slate-800/70 align-top hover:bg-slate-800/30"
                    >
                      <td className="px-4 py-4 font-mono text-xs text-slate-400">
                        {job.job_id
                          ? `${job.job_id.slice(0, 12)}...`
                          : "—"}
                      </td>

                      <td className="px-4 py-4 text-slate-300">
                        {production
                          ? `${production.model_name} v${production.version}`
                          : job.production_model_id
                            ? `${job.production_model_id.slice(0, 8)}...`
                            : "—"}
                      </td>

                      <td className="px-4 py-4 text-slate-300">
                        {candidate
                          ? `${candidate.model_name} v${candidate.version}`
                          : job.candidate_model_id
                            ? `${job.candidate_model_id.slice(0, 8)}...`
                            : "—"}
                      </td>

                      <td className="px-4 py-4">
                        <StatusBadge status={job.status} />
                      </td>

                      <td className="px-4 py-4 text-xs text-slate-400">
                        {formatDate(job.created_at)}
                      </td>

                      <td className="px-4 py-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            onClick={() => {
                              setSelectedJob(job);
                              setError("");
                            }}
                            className="flex items-center gap-1 rounded-md border border-slate-700 px-2.5 py-1.5 text-xs text-slate-200 hover:bg-slate-700"
                          >
                            <Eye size={14} />
                            Details
                          </button>

                          {canApprove && (
                            <>
                              <button
                                onClick={() => handleApprove(job)}
                                disabled={Boolean(busyAction)}
                                className="rounded-md bg-emerald-700 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
                              >
                                {busyAction === `approve-${job.job_id}`
                                  ? "Approving..."
                                  : "Approve"}
                              </button>

                              <button
                                onClick={() => handleReject(job)}
                                disabled={Boolean(busyAction)}
                                className="rounded-md bg-red-900 px-2.5 py-1.5 text-xs font-medium text-white hover:bg-red-800 disabled:opacity-50"
                              >
                                {busyAction === `reject-${job.job_id}`
                                  ? "Rejecting..."
                                  : "Reject"}
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Selected Job Details */}
      {displayedJob && (
        <section className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-white">
              Recovery Job Details
            </h2>

            <button
              onClick={() => setSelectedJob(null)}
              className="rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
            >
              Close
            </button>
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <p className="text-xs text-slate-500">Job ID</p>
              <p className="mt-1 break-all font-mono text-sm text-slate-300">
                {displayedJob.job_id ?? "—"}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">Status</p>
              <div className="mt-2">
                <StatusBadge status={displayedJob.status} />
              </div>
            </div>

            <div>
              <p className="text-xs text-slate-500">Reason</p>
              <p className="mt-1 text-sm text-slate-300">
                {displayedJob.reason || "No reason provided."}
              </p>
            </div>

            <div>
              <p className="text-xs text-slate-500">Last Updated</p>
              <p className="mt-1 text-sm text-slate-300">
                {formatDate(displayedJob.updated_at)}
              </p>
            </div>
          </div>

          {comparison && (
            <div className="mt-6">
              <h3 className="mb-3 font-medium text-white">
                Candidate Comparison
              </h3>

              <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                <StatCard
                  title="Recommendation"
                  value={String(
                    comparison.recommendation ??
                      comparison.comparison?.recommendation ??
                      "—"
                  ).replaceAll("_", " ")}
                  icon={ShieldCheck}
                />

                <StatCard
                  title="Production MAE"
                  value={formatNumber(
                    comparison.production_model?.metrics?.mae ??
                      comparison.production_metrics?.mae ??
                      comparison.production_mae
                  )}
                  icon={Activity}
                />

                <StatCard
                  title="Candidate MAE"
                  value={formatNumber(
                    comparison.candidate_model?.metrics?.mae ??
                      comparison.candidate_metrics?.mae ??
                      comparison.candidate_mae
                  )}
                  icon={Activity}
                />
              </div>
            </div>
          )}

          {displayedJob.comparison_json && !comparison && (
            <p className="mt-4 text-sm text-amber-400">
              Comparison data exists, but it could not be parsed as JSON.
            </p>
          )}

          <details className="mt-5">
            <summary className="cursor-pointer text-sm text-sky-400">
              View complete job response
            </summary>

            <pre className="mt-3 overflow-x-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-300">
              {JSON.stringify(displayedJob, null, 2)}
            </pre>
          </details>

          {displayedJob.status === "AWAITING_APPROVAL" && (
            <div className="mt-5 rounded-lg border border-amber-800/50 bg-amber-950/20 p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle
                  size={19}
                  className="mt-0.5 shrink-0 text-amber-400"
                />

                <div>
                  <p className="font-medium text-amber-300">
                    Approval required
                  </p>
                  <p className="mt-1 text-sm text-slate-400">
                    Review the candidate's evaluation and comparison before
                    approving deployment. Approval is permitted only when
                    the backend confirms the job is awaiting approval.
                  </p>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      <div className="text-xs text-slate-500">
        Last updated: {lastUpdated ? lastUpdated.toLocaleTimeString() : "—"}
      </div>
    </div>
  );
}