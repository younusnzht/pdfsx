import { useState } from "react";
import { useNavigate } from "react-router-dom";
import AppLayout from "../components/AppLayout";
import { uploadStatement } from "../api/statements";

export default function UploadPage() {
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);
    try {
      const result = await uploadStatement(file);
      navigate(`/statements/${result.statement_id}`);
    } catch {
      setError("Upload failed. Please try again.");
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <AppLayout title="Bank Statements">
      <div className="mb-5">
        <div className="text-2xl font-extrabold text-slate-900">Bank Statements</div>
        <div className="text-slate-500 text-sm mt-0.5">
          Upload, extract, and reconcile Canadian bank and card statements
        </div>
      </div>

      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <label className="block cursor-pointer">
          <input
            type="file"
            accept="application/pdf"
            className="hidden"
            onChange={handleFileChange}
            disabled={isUploading}
          />
          <div className="border-2 border-dashed border-slate-300 rounded-lg py-8 text-center bg-slate-50 hover:border-slate-400 transition-colors">
            <div className="text-2xl mb-1.5">📤</div>
            <div className="text-sm text-slate-600 font-semibold">
              {isUploading ? "Uploading..." : "Click to upload a PDF statement"}
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              Scanned statements are automatically routed through OCR
            </div>
          </div>
        </label>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </div>
    </AppLayout>
  );
}
