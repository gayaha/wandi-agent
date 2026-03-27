import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { supabase } from "@/lib/supabase";

interface DeletionRequest {
  confirmation_code: string;
  status: string;
  created_at: string;
  completed_at: string | null;
}

const DeletionStatus = () => {
  const [searchParams] = useSearchParams();
  const code = searchParams.get("code");
  const [request, setRequest] = useState<DeletionRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!code) {
      setError("Missing confirmation code");
      setLoading(false);
      return;
    }

    const fetchStatus = async () => {
      const { data, error: fetchError } = await supabase
        .from("data_deletion_requests")
        .select("confirmation_code, status, created_at, completed_at")
        .eq("confirmation_code", code)
        .single();

      if (fetchError || !data) {
        setError("Deletion request not found");
      } else {
        setRequest(data);
      }
      setLoading(false);
    };

    fetchStatus();
  }, [code]);

  const statusLabel = (status: string) => {
    switch (status) {
      case "completed":
        return "Completed";
      case "pending":
        return "In Progress";
      case "failed":
        return "Failed";
      default:
        return status;
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-green-400";
      case "pending":
        return "text-yellow-400";
      case "failed":
        return "text-red-400";
      default:
        return "text-gray-400";
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4" dir="rtl">
      <div className="max-w-md w-full bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-8">
        <h1 className="text-2xl font-bold text-white mb-2 text-center">
          סטטוס מחיקת נתונים
        </h1>
        <p className="text-slate-400 text-sm text-center mb-6">
          Data Deletion Request Status
        </p>

        {loading && (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500" />
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-center">
            <p className="text-red-400">{error}</p>
          </div>
        )}

        {request && (
          <div className="space-y-4">
            <div className="flex justify-between items-center py-2 border-b border-slate-700">
              <span className="text-slate-400">קוד אישור</span>
              <span className="text-white font-mono text-sm">{request.confirmation_code}</span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-700">
              <span className="text-slate-400">סטטוס</span>
              <span className={`font-semibold ${statusColor(request.status)}`}>
                {statusLabel(request.status)}
              </span>
            </div>
            <div className="flex justify-between items-center py-2 border-b border-slate-700">
              <span className="text-slate-400">תאריך בקשה</span>
              <span className="text-white text-sm">
                {new Date(request.created_at).toLocaleDateString("he-IL")}
              </span>
            </div>
            {request.completed_at && (
              <div className="flex justify-between items-center py-2 border-b border-slate-700">
                <span className="text-slate-400">תאריך השלמה</span>
                <span className="text-white text-sm">
                  {new Date(request.completed_at).toLocaleDateString("he-IL")}
                </span>
              </div>
            )}
          </div>
        )}

        <p className="text-slate-500 text-xs text-center mt-6">
          Wandi AI &mdash; Instagram Scheduling Platform
        </p>
      </div>
    </div>
  );
};

export default DeletionStatus;
