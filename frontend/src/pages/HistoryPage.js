import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Eye, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function HistoryPage() {
  const [sessions, setSessions] = useState([]);

  const load = async () => {
    try {
      const response = await api.listSessions();
      setSessions(response.data);
    } catch (error) {
      toast.error("Could not load history");
    }
  };

  useEffect(() => { load(); }, []);

  const remove = async (id) => {
    await api.deleteSession(id);
    toast.success("Session deleted");
    load();
  };

  return (
    <section className="page-band" data-testid="history-page">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end" data-testid="history-header">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-[#D4A373]" data-testid="history-kicker">Saved sessions</p>
            <h1 className="mt-3 font-heading text-4xl font-bold tracking-normal" data-testid="history-title">Consultation history</h1>
          </div>
          <Link to="/record" className="earth-button inline-flex" data-testid="history-new-session-link">New session</Link>
        </div>
        <div className="solid-panel overflow-hidden" data-testid="history-table-panel">
          <div className="history-row header" data-testid="history-table-header">
            <span>Created</span><span>Status</span><span>Languages</span><span>File</span><span>Actions</span>
          </div>
          {sessions.length === 0 ? (
            <div className="p-8 text-center text-[#636965]" data-testid="history-empty-state">No sessions yet.</div>
          ) : sessions.map((item) => (
            <div className="history-row" key={item.id} data-testid={`history-row-${item.id}`}>
              <span data-testid={`history-created-${item.id}`}>{new Date(item.created_at).toLocaleString()}</span>
              <span className={`status-badge ${item.status}`} data-testid={`history-status-${item.id}`}>{item.status}</span>
              <span data-testid={`history-languages-${item.id}`}>{item.source_language} → {item.target_language}</span>
              <span data-testid={`history-file-${item.id}`}>{item.original_filename || "Recorded audio"}</span>
              <span className="flex gap-2">
                {item.has_result && <Link to={`/result/${item.id}`} className="icon-action" data-testid={`history-view-${item.id}`}><Eye className="h-4 w-4" /> View</Link>}
                <Button onClick={() => remove(item.id)} className="icon-action danger" data-testid={`history-delete-${item.id}`}><Trash2 className="h-4 w-4" /> Delete</Button>
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
