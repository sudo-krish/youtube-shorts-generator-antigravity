import { useState, useEffect, useMemo } from 'react';
import { Database, Trash2, RefreshCw, CheckCircle2, XCircle, Loader2, Search, Table2 } from 'lucide-react';
import { api } from '../api';

interface DatabaseViewerProps {
  onClear: () => void;
}

export const DatabaseViewer = ({ onClear }: DatabaseViewerProps) => {
  const [dbData, setDbData] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchDbDump = async () => {
    setLoading(true);
    try {
      const data = await api.getDatabaseDump();
      setDbData(data);
      if (data && Object.keys(data).length > 0) {
        setSelectedTable(prev => prev && Object.keys(data).includes(prev) ? prev : Object.keys(data)[0]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDbDump();
  }, []);

  const handleClear = async () => {
    if (confirm("Are you sure you want to clear the ENTIRE database and wipe all generated files? This cannot be undone.")) {
      try {
        await api.clearDatabase();
        onClear(); // Tell parent to reset state
      } catch (err) {
        alert("Failed to clear database.");
      }
    }
  };

  const tables = Object.keys(dbData || {}).sort();
  const currentData = selectedTable && dbData ? dbData[selectedTable] || [] : [];
  
  const filteredData = useMemo(() => {
    if (!searchQuery) return currentData;
    const lowerQuery = searchQuery.toLowerCase();
    return currentData.filter(row => {
      return Object.values(row).some(val => 
        String(val).toLowerCase().includes(lowerQuery)
      );
    });
  }, [currentData, searchQuery]);

  const columns = currentData.length > 0 ? Object.keys(currentData[0]) : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-8 h-8 animate-spin text-aurora-cyan" />
      </div>
    );
  }

  const renderStatusBadge = (status: string) => {
    if (status === 'completed') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <CheckCircle2 className="w-3.5 h-3.5" />
          Completed
        </span>
      );
    }
    if (status === 'failed') {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <XCircle className="w-3.5 h-3.5" />
          Failed
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        {status}
      </span>
    );
  };

  const formatDate = (timestamp: number) => {
    if (!timestamp) return '-';
    return new Date(timestamp * 1000).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
  };

  return (
    <div className="flex flex-col gap-6 h-full w-full max-w-[1600px] mx-auto pb-8 animate-fade-in relative z-10">
      <header className="flex justify-between items-center bg-black/40 backdrop-blur-xl border border-white/10 p-6 rounded-2xl shadow-lg">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-3">
            <Database className="w-6 h-6 text-aurora-violet" />
            System Database
          </h2>
          <p className="text-sm text-white/50 mt-1">Live inspection of all SQLite tables and states.</p>
        </div>
        
        <div className="flex gap-4">
          <button onClick={fetchDbDump} className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl transition-all font-semibold text-white hover:text-aurora-cyan">
            <RefreshCw className="w-4 h-4" /> Refresh
          </button>
          <button onClick={handleClear} className="flex items-center gap-2 px-5 py-2.5 bg-rose-500/20 hover:bg-rose-500/30 border border-rose-500/30 rounded-xl transition-all font-semibold text-rose-400">
            <Trash2 className="w-4 h-4" /> Reset DB
          </button>
        </div>
      </header>

      <div className="flex gap-4 bg-black/30 border border-white/10 p-4 rounded-2xl items-center shadow-md">
        <div className="flex items-center gap-3 px-4 border-r border-white/10 shrink-0">
          <Table2 className="w-5 h-5 text-white/50" />
          <select 
            value={selectedTable} 
            onChange={(e) => setSelectedTable(e.target.value)}
            className="bg-transparent text-white font-bold text-sm outline-none cursor-pointer hover:text-aurora-cyan transition-colors"
          >
            {tables.map(t => (
              <option key={t} value={t} className="bg-black text-white">{t}</option>
            ))}
          </select>
        </div>
        <div className="flex items-center gap-3 flex-1 px-4">
          <Search className="w-4 h-4 text-white/40" />
          <input 
            type="text" 
            placeholder={`Filter ${currentData.length} records...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-transparent text-white text-sm outline-none placeholder:text-white/30"
          />
        </div>
      </div>

      <div className="flex flex-col gap-8 flex-1 overflow-hidden">
        <section className="bg-black/30 border border-white/10 rounded-2xl shadow-2xl h-full flex flex-col">
          <div className="overflow-auto flex-1 custom-scrollbar">
            <table className="w-full text-sm text-left relative">
              <thead className="text-xs uppercase bg-[#1a1a1a] text-white/50 border-b border-white/10 sticky top-0 z-10 shadow-md">
                <tr>
                  {columns.map(col => (
                    <th key={col} className="px-6 py-4 font-semibold tracking-wider whitespace-nowrap">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredData.length === 0 ? (
                  <tr>
                    <td colSpan={columns.length || 1} className="px-6 py-8 text-center text-white/30 italic">
                      No records found.
                    </td>
                  </tr>
                ) : (
                  filteredData.map((row, idx) => (
                    <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                      {columns.map(col => {
                        const val = row[col];
                        let renderVal = val;
                        
                        // Smart formatting
                        if (val === null) renderVal = <span className="text-white/20 italic">null</span>;
                        else if (typeof val === 'number' && col.includes('time')) renderVal = <span className="text-white/50">{formatDate(val)}</span>;
                        else if (col === 'status') renderVal = renderStatusBadge(val);
                        else if (typeof val === 'object') renderVal = JSON.stringify(val);
                        
                        return (
                          <td key={col} className="px-6 py-4 text-white/70 truncate max-w-sm" title={String(val)}>
                            {renderVal}
                          </td>
                        );
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );

};
