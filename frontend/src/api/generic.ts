import { fetchClient } from './client';

export const genericApi = {
  executeNode: (endpoint: string, payload: any) => 
    fetchClient<any>(endpoint, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
