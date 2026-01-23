// pages/tools/metadata.tsx
import Head from "next/head";
import dynamic from "next/dynamic";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import { useState, useRef, useCallback, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, FileSearch, X, ArrowLeft, Loader2, Download } from "lucide-react";
import { useRouter } from "next/router";
import { getAuthToken, buildApiUrl } from "@/lib/api";

const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

interface MetadataResult {
  success: boolean;
  filename: string;
  file_size: number;
  metadata: {
    has_metadata: boolean;
    message?: string;
    categories?: Record<string, any>;
    error?: string;
  };
}

export default function MetadataAnalyzer() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<MetadataResult | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

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
    setResult(null);
  }, []);

  const onDrop = useCallback((ev: React.DragEvent<HTMLDivElement>) => {
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
    setResult(null);
  }, []);

  const onDragOver = useCallback((ev: React.DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((ev: React.DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setIsDragging(false);
  }, []);

  const analyzeMetadata = async () => {
    if (!file) {
      setError("Please select a file first");
      return;
    }

    const token = getAuthToken();
    if (!token) {
      setError("Please log in to use this tool");
      return;
    }

    setError(null);
    setLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(buildApiUrl('/api/analyze/metadata'), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to analyze metadata");
      }

      const data: MetadataResult = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to analyze metadata");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const downloadReport = () => {
    if (!result) {
      setError("Please analyze an image first");
      return;
    }

    // Get the report container
    const reportElement = document.getElementById("metadata-report");
    if (!reportElement) {
      setError("Report element not found");
      return;
    }

    // Load html2pdf from CDN if not already loaded
    const pdf = (window as any).html2pdf;
    if (pdf) {
      performPdfDownload(reportElement);
    } else {
      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
      script.onload = () => {
        performPdfDownload(reportElement);
      };
      script.onerror = () => {
        setError("Failed to load PDF library. Please try again.");
      };
      document.head.appendChild(script);
    }
  };

  const performPdfDownload = (element: HTMLElement) => {
    // Load html2pdf from CDN if not available
    const pdf = (window as any).html2pdf;
    if (!pdf) {
      setError("PDF library failed to load. Please try again.");
      return;
    }

    const opt = {
      margin: 10,
      filename: `metadata-report-${Date.now()}.pdf`,
      image: { type: "jpeg", quality: 0.98 },
      html2canvas: { scale: 2 },
      jsPDF: { orientation: "portrait", unit: "mm", format: "a4" },
    };

    pdf()
      .set(opt)
      .from(element)
      .save()
      .catch((err: any) => {
        console.error("PDF download error:", err);
        setError("Failed to generate PDF. Please try again.");
      });
  };

  const renderMetadataValue = (value: any): string => {
    if (typeof value === "object" && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  return (
    <div className="min-h-screen bg-background">
      <Head>
        <title>Metadata Analyzer — DeepVerify</title>
        <meta name="description" content="Extract EXIF metadata from images" />
      </Head>

      <Navbar />

      <main className="pt-24 pb-16">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="mb-8">
              <Button
                variant="ghost"
                onClick={() => router.push("/tools")}
                className="mb-4"
              >
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Tools
              </Button>
              <h1 className="text-3xl font-bold mb-2">Metadata Analyzer</h1>
              <p className="text-muted-foreground">
                Extract EXIF metadata including camera info, timestamps, and location data
              </p>
            </div>

            {/* Upload Card */}
            {!result && (
              <Card className="p-8 border-2 border-dashed">
                <div
                  className={`transition-colors ${
                    isDragging ? "bg-primary/5" : ""
                  }`}
                  onDrop={onDrop}
                  onDragOver={onDragOver}
                  onDragLeave={onDragLeave}
                >
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={onFileChange}
                    accept="image/jpeg,image/png,image/jpg"
                    className="hidden"
                  />

                  <div className="flex flex-col items-center justify-center gap-4 py-8">
                    <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                      <FileSearch className="h-8 w-8 text-primary" />
                    </div>

                    {!file ? (
                      <>
                        <div className="text-center">
                          <p className="text-lg font-medium mb-1">
                            Drop an image here or click to browse
                          </p>
                          <p className="text-sm text-muted-foreground">
                            Supports JPEG and PNG (max 10MB)
                          </p>
                        </div>

                        <Button
                          onClick={() => fileInputRef.current?.click()}
                          className="gap-2"
                        >
                          <Upload className="h-4 w-4" />
                          Select Image
                        </Button>
                      </>
                    ) : (
                      <>
                        {/* File Preview */}
                        <div className="w-full max-w-md">
                          {file.type.startsWith("image/") && (
                            <div className="relative mb-4">
                              <img
                                src={URL.createObjectURL(file)}
                                alt="Preview"
                                className="w-full h-48 object-contain rounded-lg bg-muted"
                              />
                            </div>
                          )}

                          <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{file.name}</p>
                              <p className="text-sm text-muted-foreground">
                                {formatFileSize(file.size)}
                              </p>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={reset}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>

                        <Button
                          onClick={analyzeMetadata}
                          disabled={loading}
                          className="gap-2"
                          size="lg"
                        >
                          {loading ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Analyzing...
                            </>
                          ) : (
                            <>
                              <FileSearch className="h-4 w-4" />
                              Extract Metadata
                            </>
                          )}
                        </Button>
                      </>
                    )}

                    {error && (
                      <div className="w-full max-w-md p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg">
                        <p className="text-sm text-red-600 dark:text-red-400">
                          {error}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </Card>
            )}

            {/* Results */}
            {result && (
              <div className="space-y-6">
                <Card className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold">Analysis Results</h2>
                    <div className="flex gap-2">
                      <Button onClick={downloadReport} disabled={loading} className="gap-2" variant="outline">
                        {loading ? (
                          <>
                            <Loader2 className="h-4 w-4 animate-spin" />
                            Generating...
                          </>
                        ) : (
                          <>
                            <Download className="h-4 w-4" />
                            Download Report
                          </>
                        )}
                      </Button>
                      <Button variant="outline" onClick={reset}>
                        Analyze Another Image
                      </Button>
                    </div>
                  </div>

                  {/* Report Container for PDF Export */}
                  <div id="metadata-report">
                    {/* Authenticity Risk Badge */}
                    <div className="mb-6 pb-4 border-b">
                      <div className="inline-block px-3 py-1 rounded bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 text-xs font-semibold">
                        Authenticity Risk: MEDIUM
                      </div>
                    </div>

                    <div className="space-y-4">
                      {/* File Info */}
                      <div className="p-4 bg-muted rounded-lg">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-muted-foreground mb-1">Filename</p>
                            <p className="font-medium">{result.filename}</p>
                          </div>
                          <div>
                            <p className="text-muted-foreground mb-1">File Size</p>
                            <p className="font-medium">{formatFileSize(result.file_size)}</p>
                          </div>
                        </div>
                      </div>

                      {/* Metadata */}
                      {!result.metadata.has_metadata ? (
                        <div className="p-6 bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-800 rounded-lg text-center">
                          <FileSearch className="h-12 w-12 text-yellow-600 dark:text-yellow-400 mx-auto mb-4" />
                          <p className="text-lg font-medium text-yellow-900 dark:text-yellow-100 mb-2">
                            {result.metadata.message || result.metadata.error || "No metadata found"}
                          </p>
                          <p className="text-sm text-yellow-700 dark:text-yellow-300">
                            This image does not contain EXIF metadata. This could mean the image was 
                            processed by software that strips metadata, or it was created without metadata.
                          </p>
                        </div>
                    ) : (
                      <div className="space-y-4">
                        {result.metadata.categories &&
                          Object.entries(result.metadata.categories).map(([category, data]) => (
                            <Card key={category} className="p-4">
                              <h3 className="font-semibold mb-3 text-lg">{category}</h3>
                              {category === 'EXIF Metadata' && (
                                <div className="mb-4 p-3 bg-muted rounded text-xs text-muted-foreground border-l-2 border-muted-foreground/50">
                                  <p><strong>Note:</strong> Most social media platforms remove EXIF metadata for privacy. Absence of metadata alone does not confirm image manipulation.</p>
                                </div>
                              )}
                              <div className="space-y-2">
                                {typeof data === "object" && data !== null ? (
                                  <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                      <tbody>
                                        {Object.entries(data).map(([key, value]) => (
                                          <tr key={key} className="border-b last:border-0">
                                            <td className="py-2 pr-4 text-muted-foreground font-medium whitespace-nowrap">
                                              {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                                            </td>
                                            <td className="py-2 font-mono text-xs break-all">
                                              {renderMetadataValue(value)}
                                            </td>
                                          </tr>
                                        ))}
                                      </tbody>
                                    </table>
                                  </div>
                                ) : (
                                  <p className="text-muted-foreground">{renderMetadataValue(data)}</p>
                                )}
                              </div>
                            </Card>
                          ))}
                      </div>
                    )}
                  </div>
                  {/* End of Report Container */}
                </div>
                </Card>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
