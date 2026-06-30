import { fetchClient } from './client';

export interface SequenceStep {
  name: string;
  endpoint: string;
  params: Record<string, any>;
}

export interface RunRequest {
  video_id: string;
  metadata?: Record<string, any>;
  sequence?: SequenceStep[];
}

export const orchestratorApi = {
  startRun: (data: RunRequest) => 
    fetchClient<{ status: string; job_id: string }>('/orchestrator/run', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
    
  redriveJob: (jobId: string) => 
    fetchClient<{ status: string; message: string; job_id: string }>(`/orchestrator/redrive/${jobId}`, {
      method: 'POST',
    }),
};
