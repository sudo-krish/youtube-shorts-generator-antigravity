export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const api = {
  // Videos
  getVideos: async () => {
    const res = await fetch(`${API_BASE_URL}/api/videos`);
    return res.json();
  },
  
  uploadVideo: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE_URL}/api/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Analysis & Jobs
  analyzeVideo: async (videoId: string, metadata: any) => {
    const res = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ video_id: videoId, metadata })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getJobs: async () => {
    const res = await fetch(`${API_BASE_URL}/api/jobs`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getJobStatus: async (jobId: string) => {
    const res = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/status`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  getJobLogs: async (jobId: string) => {
    const res = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/logs`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  redriveJob: async (jobId: string) => {
    const res = await fetch(`${API_BASE_URL}/api/redrive/${jobId}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  cancelJob: async (jobId: string) => {
    const res = await fetch(`${API_BASE_URL}/api/jobs/${jobId}/cancel`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Admin / Database
  getDatabaseDump: async () => {
    const res = await fetch(`${API_BASE_URL}/api/db/dump`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  clearDatabase: async () => {
    const res = await fetch(`${API_BASE_URL}/api/db/clear`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // Engine Toggles / Config
  installSfx: async () => {
    const res = await fetch(`${API_BASE_URL}/api/sfx/install`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  // WebSocket URL Helper
  getWebSocketUrl: (jobId: string) => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (API_BASE_URL.startsWith('http')) {
      return API_BASE_URL.replace('http', 'ws') + `/api/jobs/${jobId}/logs/stream`;
    }
    return `${wsProtocol}//${window.location.host}${API_BASE_URL}/api/jobs/${jobId}/logs/stream`;
  }
};
