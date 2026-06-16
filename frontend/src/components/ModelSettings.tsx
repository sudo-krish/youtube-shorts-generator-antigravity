import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Settings, Loader2 } from 'lucide-react';
import { api } from '../api';

export const ModelSettings = () => {
  const [models, setModels] = useState<string[]>([]);
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (isOpen && !config) {
      loadData();
    }
  }, [isOpen]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [modelsRes, configRes] = await Promise.all([
        api.getModels(),
        api.getConfig()
      ]);
      setModels(modelsRes.models || []);
      setConfig(configRes);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleModelChange = (agent: string, model: string) => {
    setConfig((prev: any) => ({
      ...prev,
      models: {
        ...prev.models,
        [agent]: model
      }
    }));
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      await api.updateConfig(config);
      setIsOpen(false);
    } catch (err) {
      console.error(err);
      alert('Failed to save config');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-4 py-2 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 transition-colors text-sm font-medium text-white/80"
      >
        <Settings className="w-4 h-4" /> AI Models
      </button>
    );
  }

  const modalContent = (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl bg-[#0a0a0a] border border-white/10 rounded-2xl p-6 shadow-2xl relative">
        <h3 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
          <Settings className="w-5 h-5 text-aurora-cyan" /> Configure AI Pipeline
        </h3>

        {loading ? (
          <div className="flex justify-center p-12">
            <Loader2 className="w-8 h-8 text-aurora-cyan animate-spin" />
          </div>
        ) : (
          <div className="space-y-4">
            {['observer', 'scriptwriter', 'director', 'editor', 'specialist', 'builder'].map((agent) => {
              // Restriction: Observer MUST be gemini
              const availableModels = agent === 'observer' 
                ? models.filter(m => m.includes('gemini'))
                : models;

              return (
                <div key={agent} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 hover:border-white/10 transition-colors">
                  <div className="flex flex-col">
                    <span className="text-sm font-bold text-white/90 capitalize">{agent}</span>
                    <span className="text-xs text-white/40">
                      {agent === 'observer' ? 'Requires Multimodal Vision' : 'Text generation & Logic'}
                    </span>
                  </div>
                  <select
                    value={config?.models?.[agent] || ''}
                    onChange={(e) => handleModelChange(agent, e.target.value)}
                    className="bg-black border border-white/20 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-aurora-cyan w-64 appearance-none"
                  >
                    {availableModels.map(m => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-8 flex justify-end gap-3 pt-6 border-t border-white/10">
          <button
            onClick={() => setIsOpen(false)}
            className="px-5 py-2 rounded-lg text-sm font-medium text-white/60 hover:text-white transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={saveConfig}
            disabled={saving || loading}
            className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold bg-white text-black hover:bg-white/90 transition-colors disabled:opacity-50"
          >
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            Save Settings
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};
