// pages/components/UploadCard.tsx  (replace your existing file)
import { useState, useEffect, useRef, useCallback } from "react";
import { uploadImage, getAuthToken } from "@/lib/api";
import { useRouter } from "next/router";
import Link from "next/link";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, Image as ImageIcon, X } from "lucide-react";

export default function UploadCard() {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const token = getAuthToken();
    setIsAuthenticated(!!token);
  }, []);

  const validate = (f: File) => {
    const allowed = ["image/jpeg", "image/png", "image/jpg"];
    if (!allowed.includes(f.type)) return "Only JPEG and PNG allowed";
    if (f.size > 10_000_000) return "Max file size is 10MB";
    return null;
  };

  const onFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const err = validate(f);
    if (err) {
      setError(err);
      return;
    }
    setError(null);
    setFile(f);
  }, []);

  const onDrop = useCallback(
    (ev: React.DragEvent<HTMLDivElement>) => {
      ev.preventDefault();
      setIsDragging(false);
      const f = ev.dataTransfer.files?.[0];
      if (!f) return;
      const err = validate(f);
      if (err) {
        setError(err);
        return;
      }
      setError(null);
      setFile(f);
    },
    []
  );

  const onDragOver = useCallback((ev: React.DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((ev: React.DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setIsDragging(false);
  }, []);

  const onUpload = async () => {
    if (!file) {
      setError("Select a file first");
      return;
    }

    // NOTE: removed hard client-side block here so anonymous uploads are allowed.
    // If you want to require login, re-enable this check:
    // if (!isAuthenticated) { setError("Please log in to upload images"); return; }

    setError(null);
    setLoading(true);
    try {
      const res = await uploadImage(file);
      // tolerate several possible shapes from backend: jobId, job_id, id
      function extractJobIdFromResponse(res: any): number | string | null {
        if (!res) return null;
        const candidates = [res.jobId, res.job_id, res.id, res?.job?.id];
        for (const c of candidates) {
          if (c !== undefined && c !== null) return c;
        }
        console.warn("Upload returned unexpected shape:", res);
        return null;
      }

      const jobId = extractJobIdFromResponse(res);

      if (!jobId) {
        console.error("Unexpected upload response:", res);
        setError("Upload succeeded but server response was unexpected.");
        return;
      }
      // Navigate to the results dynamic route — correct path: /results/[id]
      router.push(`/${jobId}`);
    } catch (e: any) {
      const errorMsg = e?.message || "Upload failed";
      setError(errorMsg);
      console.error("Upload error:", e);

      // If authentication error, redirect to login (backend may return this)
      if (/auth|login|authenticated/i.test(String(errorMsg))) {
        setTimeout(() => {
          router.push("/login");
        }, 800);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = () => {
    setFile(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  return (
    <Card className="p-8">
      {!file ? (
        <div
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${isDragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"
            }`}
          data-testid="upload-dropzone"
        >
          <div className="flex flex-col items-center gap-4">
            <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Upload className="h-8 w-8 text-primary" />
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold">Upload an image to analyze</h3>
              <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                Drag and drop your image here, or click to browse
              </p>
              <p className="text-xs text-muted-foreground">Supports JPG, PNG • Max 10MB</p>
            </div>

            <Button onClick={() => fileInputRef.current?.click()} size="lg" data-testid="button-browse-files">
              <ImageIcon className="h-4 w-4 mr-2" />
              Choose file
            </Button>

            <input
              ref={fileInputRef}
              onChange={onFileChange}
              type="file"
              accept="image/jpeg,image/png,image/jpg"
              className="hidden"
              data-testid="input-file"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="relative">
            <div className="w-full max-h-96 object-contain rounded-lg bg-slate-50 p-6 flex items-center justify-center">
              <div className="flex flex-col items-center">
                <ImageIcon className="h-12 w-12 text-slate-400 mb-3" />
                <div className="text-sm text-slate-700" data-testid="text-filename">
                  {file.name}
                </div>
                <div className="text-xs text-slate-500">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </div>
              </div>
            </div>

            <Button
              variant="destructive"
              size="icon"
              className="absolute top-2 right-2"
              onClick={handleRemove}
              disabled={loading}
              data-testid="button-clear-image"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <p className="text-sm font-medium" data-testid="text-filename-2">
                {file.name}
              </p>
              <p className="text-xs text-muted-foreground">
                {file && (file.size / 1024 / 1024).toFixed(2)} MB
              </p>
            </div>

            <Button onClick={onUpload} disabled={loading || !file} size="lg" data-testid="button-analyze">
              {loading ? "Analyzing…" : "Upload & Analyze"}
            </Button>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
          <p className="text-sm text-red-600">{error}</p>
          {error.includes("log in") && (
            <Link href="/login" className="text-sm text-indigo-600 underline mt-2 inline-block">
              Go to Login →
            </Link>
          )}
        </div>
      )}

      {/* Show a friendly notice but do NOT block uploads */}
      {!isAuthenticated && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
          <p className="text-sm text-yellow-800">
            You are not signed in. You can still upload, but some features may require an account.{" "}
            <Link href="/login" className="text-indigo-600 underline">Log in</Link>
          </p>
        </div>
      )}

      <div className="mt-6 text-xs text-slate-400">
        Supported: JPG, PNG — max 10MB. By uploading you agree to our terms.
      </div>
    </Card>
  );
}
