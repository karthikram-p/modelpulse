import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

export const getModels = async () => {
  const response = await api.get("/models");
  return response.data;
};

export const getRecoveryJobs = async () => {
  const response = await api.get("/recovery/jobs");
  return response.data;
};

export const getModelHealth = async (modelId) => {
  const response = await api.get(`/monitoring/health/${modelId}`);
  return response.data;
};

export const getDrift = async (limit = 100) => {
  const response = await api.get("/monitoring/drift", {
    params: { limit },
  });
  return response.data;
};

export const getPerformance = async (modelId) => {
  const response = await api.get(
    `/monitoring/performance/${modelId}`
  );
  return response.data;
};

export const runRecovery = async (modelId) => {
  const response = await api.post(`/recovery/run/${modelId}`);
  return response.data;
};

export const runRecoveryDryRun = async (modelId) => {
  const response = await api.post(`/recovery/dry-run/${modelId}`);
  return response.data;
};

export const approveRecovery = async (jobId) => {
  const response = await api.post(
    `/recovery/jobs/${jobId}/approve`
  );
  return response.data;
};

export const rejectRecovery = async (jobId, reason) => {
  const response = await api.post(
    `/recovery/jobs/${jobId}/reject`,
    null,
    { params: { reason } }
  );
  return response.data;
};

export const compareModels = async (candidateModelId) => {
  const response = await api.get(
    `/models/${candidateModelId}/compare`
  );
  return response.data;
};

export const getPredictions = async (limit = 100) => {
  const response = await api.get("/predictions", {
    params: { limit },
  });

  return response.data;
};

export default api;