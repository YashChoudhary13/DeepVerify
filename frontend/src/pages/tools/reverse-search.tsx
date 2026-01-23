// pages/tools/reverse-search.tsx
import Head from "next/head";
import dynamic from "next/dynamic";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import { useState, useRef, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Upload, Search, X, ArrowLeft, Loader2, ExternalLink } from "lucide-react";
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

export default function ReverseImageSearch() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [searchInProgress, setSearchInProgress] = useState(false);
  const [isPublicUrl, setIsPublicUrl] = useState(false);
  const [verifyingImage, setVerifyingImage] = useState(false);
  const [imageAccessible, setImageAccessible] = useState(false);

  const validate = (f: File) => {
    const allowed = ["image/jpeg", "image/png", "image/jpg"];
    if (!allowed.includes(f.type)) return "Only JPEG and PNG allowed";
    if (f.size > 10_000_000) return "Max file size is 10MB";
    return null;
  };

  const verifyImageAccessibility = async (url: string) => {
    // Try to verify the image is accessible by checking if it loads
    return new Promise((resolve, reject) => {
      const img = new Image();
      const timeout = setTimeout(() => {
        img.src = '';
        setImageAccessible(false);
        setError("Image uploaded but verification timed out. The image may still be processing on the server.");
        reject(new Error('Timeout'));
      }, 15000); // 15 second timeout

      img.onload = () => {
        clearTimeout(timeout);
        setImageAccessible(true);
        setError(null);
        console.log('✅ Image is accessible and ready for reverse search');
        resolve(true);
      };

      img.onerror = () => {
        clearTimeout(timeout);
        setImageAccessible(false);
        setError("Image uploaded but not accessible yet. Please wait a moment and try refreshing, or check your backend URL configuration.");
        console.error('❌ Image failed to load from URL');
        reject(new Error('Image not accessible'));
      };

      // Add timestamp to bypass cache
      img.src = url + (url.includes('?') ? '&' : '?') + '_t=' + Date.now();
    });
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
    setImageUrl(null); // Reset URL when new file selected
    uploadImage(f);
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
    setImageUrl(null); // Reset URL when new file selected
    uploadImage(f);
  }, []);

  const onDragOver = useCallback((ev: React.DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setIsDragging(true);
  }, []);

  const onDragLeave = useCallback((ev: React.DragEvent<HTMLDivElement>) => {
    ev.preventDefault();
    setIsDragging(false);
  }, []);

  const uploadImage = async (fileToUpload: File) => {
    setLoading(true);
    setError(null);

    const token = getAuthToken();
    if (!token) {
      setError("Please log in to use this tool");
      setLoading(false);
      return;
    }

    try {
      const formData = new FormData();
      formData.append("file", fileToUpload);

      const response = await fetch(buildApiUrl('/api/tools/reverse-image'), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || "Failed to upload image");
      }

      const data = await response.json();
      const url = data.imageUrl;
      setImageUrl(url);
      
      // Check if URL is publicly accessible (not localhost or local IP)
      const isPublic = !url.includes('localhost') && 
                       !url.includes('127.0.0.1') && 
                       !url.startsWith('http://192.168.') &&
                       !url.startsWith('http://10.') &&
                       !url.startsWith('http://172.') &&
                       (url.startsWith('https://') || url.startsWith('http://'));
      setIsPublicUrl(isPublic);
      
      console.log('Image URL:', url);
      console.log('Is Public URL:', isPublic);
      
      // Verify the image is actually accessible
      if (isPublic) {
        setVerifyingImage(true);
        try {
          await verifyImageAccessibility(url);
        } catch (verifyErr) {
          console.error('Image verification failed:', verifyErr);
        } finally {
          setVerifyingImage(false);
        }
      }
    } catch (err: any) {
      setError(err.message || "Failed to upload image");
      setFile(null);
    } finally {
      setLoading(false);
    }
  };

  const searchOnGoogle = async () => {
    if (!file) return;
    
    // Google Lens doesn't accept direct URLs, so we open their upload page
    // User will need to manually upload the image there
    window.open("https://lens.google.com/", "_blank");
  };

  const searchOnBing = () => {
    if (!imageUrl) {
      setError("Image not ready. Please wait.");
      return;
    }
    const bingUrl = `https://www.bing.com/images/search?q=imgurl:${encodeURIComponent(imageUrl)}&view=detailv2&iss=sbi`;
    window.open(bingUrl, "_blank");
  };

  const searchOnYandex = () => {
    if (!imageUrl) {
      setError("Image not ready. Please wait.");
      return;
    }
    const yandexUrl = `https://yandex.com/images/search?rpt=imageview&url=${encodeURIComponent(imageUrl)}`;
    window.open(yandexUrl, "_blank");
  };

  const searchOnTinEye = () => {
    if (!imageUrl) {
      setError("Image not ready. Please wait.");
      return;
    }
    const tineyeUrl = `https://tineye.com/search?url=${encodeURIComponent(imageUrl)}`;
    window.open(tineyeUrl, "_blank");
  };

  const reset = () => {
    setIsPublicUrl(false);
    setFile(null);
    setImageUrl(null);
    setError(null);
    setSearchInProgress(false);
    setVerifyingImage(false);
    setImageAccessible(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="min-h-screen bg-background">
      <Head>
        <title>Reverse Image Search — DeepVerify</title>
        <meta name="description" content="Find where an image has appeared online" />
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
              <h1 className="text-3xl font-bold mb-2">Reverse Image Search</h1>
              <p className="text-muted-foreground">
                Find where this image has appeared online
              </p>
            </div>

            {/* Upload Card */}
            {!file && (
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
                      <Search className="h-8 w-8 text-primary" />
                    </div>

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
            {file && (
              <div className="space-y-6">
                <Card className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold">Search Results</h2>
                    <Button variant="outline" onClick={reset}>
                      Search Another Image
                    </Button>
                  </div>

                  <div className="space-y-4">
                    {/* Image Preview */}
                    <div className="p-4 bg-muted rounded-lg">
                      <div className="flex items-center justify-between mb-4">
                        <div>
                          <p className="text-muted-foreground mb-1 text-sm">
                            Selected Image
                          </p>
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

                      {imageUrl && (
                        <div className="relative mt-4">
                          <img
                            src={imageUrl}
                            alt="Preview"
                            className="w-full max-h-96 object-contain rounded-lg bg-background"
                          />
                        </div>
                      )}

                      {loading && (
                        <div className="flex items-center justify-center py-6">
                          <Loader2 className="h-6 w-6 animate-spin text-primary mr-2" />
                          <p className="text-sm text-muted-foreground">Uploading image...</p>
                        </div>
                      )}

                      {verifyingImage && (
                        <div className="flex items-center justify-center py-6 bg-blue-50 dark:bg-blue-950/30 rounded-lg mt-4">
                          <Loader2 className="h-6 w-6 animate-spin text-blue-600 mr-2" />
                          <p className="text-sm text-blue-700 dark:text-blue-300">Verifying image accessibility...</p>
                        </div>
                      )}
                    </div>

                    {/* Search Buttons */}
                    {imageUrl && !loading && (
                      <div className="space-y-3">
                        <h3 className="font-semibold text-lg">Reverse Search:</h3>
                        
                        {!isPublicUrl && (
                          <div className="p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-lg">
                            <p className="text-sm text-amber-900 dark:text-amber-300">
                              <strong>⚠️ Local URL Detected:</strong> These search engines cannot access localhost URLs. 
                              To use reverse image search, your backend must be publicly accessible (deployed with a public domain) 
                              or use a service like ngrok to expose your local server temporarily.
                            </p>
                          </div>
                        )}

                        {isPublicUrl && !imageAccessible && !verifyingImage && (
                          <div className="p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900 rounded-lg">
                            <p className="text-sm text-amber-900 dark:text-amber-300">
                              <strong>⚠️ Image Not Verified:</strong> The image URL could not be verified. 
                              The buttons below may not work if the image isn't publicly accessible. 
                              Check your BACKEND_URL configuration and ensure the image is properly uploaded to your storage.
                            </p>
                          </div>
                        )}

                        <Button
                          onClick={searchOnGoogle}
                          className="w-full gap-2 h-11"
                          variant="outline"
                        >
                          <ExternalLink className="h-4 w-4" />
                          Search on Google Lens (Manual Upload)
                          <ExternalLink className="h-4 w-4 ml-auto" />
                        </Button>

                        <Button
                          onClick={searchOnBing}
                          disabled={!imageUrl || searchInProgress || !isPublicUrl || verifyingImage}
                          className="w-full gap-2 h-11"
                          variant="outline"
                        >
                          {verifyingImage ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Verifying...
                            </>
                          ) : (
                            <>
                              <ExternalLink className="h-4 w-4" />
                              Search on Bing
                              <ExternalLink className="h-4 w-4 ml-auto" />
                            </>
                          )}
                        </Button>

                        <Button
                          onClick={searchOnYandex}
                          disabled={!imageUrl || searchInProgress || !isPublicUrl || verifyingImage}
                          className="w-full gap-2 h-11"
                          variant="outline"
                        >
                          {verifyingImage ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Verifying...
                            </>
                          ) : (
                            <>
                              <ExternalLink className="h-4 w-4" />
                              Search on Yandex
                              <ExternalLink className="h-4 w-4 ml-auto" />
                            </>
                          )}
                        </Button>

                        <Button
                          onClick={searchOnTinEye}
                          disabled={!imageUrl || searchInProgress || !isPublicUrl || verifyingImage}
                          className="w-full gap-2 h-11"
                          variant="outline"
                        >
                          {verifyingImage ? (
                            <>
                              <Loader2 className="h-4 w-4 animate-spin" />
                              Verifying...
                            </>
                          ) : (
                            <>
                              <ExternalLink className="h-4 w-4" />
                              Search on TinEye
                              <ExternalLink className="h-4 w-4 ml-auto" />
                            </>
                          )}
                        </Button>
                      </div>
                    )}

                    {/* Helper Text */}
                    <div className="p-4 bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900 rounded-lg">
                      <div className="text-sm text-blue-900 dark:text-blue-300 space-y-2">
                        <p><strong>Note:</strong> Your image is temporarily hosted to enable reverse image search.</p>
                        {verifyingImage ? (
                          <p className="flex items-center gap-2">
                            <Loader2 className="h-3 w-3 animate-spin" />
                            Verifying image accessibility...
                          </p>
                        ) : imageAccessible && isPublicUrl ? (
                          <p>✅ Image URL is publicly accessible and verified - ready for reverse search!</p>
                        ) : isPublicUrl && !imageAccessible ? (
                          <p>⚠️ Image URL is public but couldn't be verified. The reverse search may not work properly.</p>
                        ) : (
                          <p>⚠️ Image URL is local-only. For full functionality, deploy your backend with a public URL.</p>
                        )}
                      </div>
                    </div>

                    {error && (
                      <div className="w-full p-4 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg">
                        <p className="text-sm text-red-600 dark:text-red-400">
                          {error}
                        </p>
                      </div>
                    )}
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
