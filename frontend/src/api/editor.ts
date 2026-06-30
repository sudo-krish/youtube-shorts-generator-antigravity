import { fetchClient } from './client';

export interface SpliceRequest {
  video_path: string;
  json_path: string;
}

export const editorApi = {
  getProjects: () => 
    fetchClient<{ status: string; projects: any[] }>('/editor/projects'),
    
  generateShort: () => 
    fetchClient<{ status: string; message: string; video_id: string }>('/editor/generate-short', {
      method: 'POST',
    }),
    
  spliceVideo: (data: SpliceRequest) => 
    fetchClient<{ status: string; message: string }>('/editor/splice', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
