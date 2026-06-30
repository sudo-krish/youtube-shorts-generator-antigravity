import { fetchClient } from './client';

export const jobsApi = {
  listJobs: () => 
    fetchClient<{ status: string; jobs: any[] }>('/jobs'),

  getStatus: (jobId: string) => 
    fetchClient<{ status: string; stages: any[] }>(`/jobs/${jobId}/status`),

  getStages: (jobId: string) => 
    fetchClient<{ status: string; stages: any[] }>(`/jobs/${jobId}/stages`),

  getLogs: (jobId: string) => 
    fetchClient<{ status: string; logs: string }>(`/jobs/${jobId}/logs`),

  getNodeResult: (jobId: string, nodeId: string) => 
    fetchClient<{ status: string; data: any }>(`/jobs/${jobId}/nodes/${nodeId}`),

  cancelJob: (jobId: string) => 
    fetchClient<{ status: string; message: string }>(`/jobs/${jobId}/cancel`, { method: 'POST' }),

  renderBatch: (jobId: string, variants: number[]) => 
    fetchClient<{ status: string; message: string }>(`/jobs/${jobId}/render/batch`, {
      method: 'POST',
      body: JSON.stringify({ variants })
    }),
};
