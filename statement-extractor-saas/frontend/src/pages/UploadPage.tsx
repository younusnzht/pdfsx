import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
    <div className="mx-auto max-w-xl py-16">
      <h1 className="mb-4 text-2xl font-semibold">Upload a statement</h1>
      <p className="mb-6 text-sm text-gray-500">
        PDF bank or card statements. Scanned statements are automatically routed through OCR.
      </p>
      <label className="block cursor-pointer rounded-lg border-2 border-dashed border-gray-300 p-10 text-center hover:border-gray-400">
        <input type="file" accept="application/pdf" className="hidden" onChange={handleFileChange} disabled={isUploading} />
        {isUploading ? "Uploading..." : "Click to select a PDF"}
      </label>
      {error && <p className="mt-4 text-sm text-red-600">{error}</p>}
    </div>
  );
}
