// src/pages/contribute.tsx
import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/router";
import { useTranslation } from "next-i18next";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { GetServerSideProps } from "next";
import Head from "next/head";
import Link from "next/link";
import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Upload, CheckCircle2, AlertCircle, Sparkles, Camera, Download, Bot, HelpCircle } from "lucide-react";
import { getAuthToken, getCurrentUser, buildApiUrl } from "@/lib/api";

const AI_TOOLS = [
    "DALL-E / ChatGPT",
    "Midjourney",
    "Stable Diffusion",
    "Adobe Firefly",
    "Leonardo.AI",
    "NanoBanana",
    "Bing Image Creator",
    "Other",
];

export default function ContributePage() {
    const router = useRouter();
    const { t } = useTranslation("common");

    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    // Form state
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string | null>(null);
    const [label, setLabel] = useState<string>("");
    const [source, setSource] = useState<string>("");
    const [aiToolName, setAiToolName] = useState<string>("");
    const [description, setDescription] = useState<string>("");

    // Submission state
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [submitSuccess, setSubmitSuccess] = useState(false);
    const [submitError, setSubmitError] = useState<string | null>(null);

    // Stats
    const [stats, setStats] = useState<any>(null);

    // Check auth on mount
    useEffect(() => {
        const token = getAuthToken();
        if (!token) {
            router.push("/login?redirect=/contribute");
            return;
        }
        setIsLoggedIn(true);
        setIsLoading(false);

        // Fetch stats
        fetchStats();
    }, [router]);

    const fetchStats = async () => {
        try {
            const token = getAuthToken();
            const res = await fetch(buildApiUrl('/api/contributions/stats'), {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (res.ok) {
                setStats(await res.json());
            }
        } catch (e) {
            console.error("Failed to fetch stats", e);
        }
    };

    const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (selectedFile) {
            setFile(selectedFile);
            setPreview(URL.createObjectURL(selectedFile));
            setSubmitSuccess(false);
            setSubmitError(null);
        }
    }, []);

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault();
        const droppedFile = e.dataTransfer.files[0];
        if (droppedFile && droppedFile.type.startsWith("image/")) {
            setFile(droppedFile);
            setPreview(URL.createObjectURL(droppedFile));
            setSubmitSuccess(false);
            setSubmitError(null);
        }
    }, []);

    const handleSubmit = async () => {
        if (!file || !label || !source) {
            setSubmitError("Please fill in all required fields");
            return;
        }

        if (label === "fake" && source === "ai_tool" && !aiToolName) {
            setSubmitError("Please select which AI tool generated this image");
            return;
        }

        setIsSubmitting(true);
        setSubmitError(null);

        try {
            const token = getAuthToken();
            const formData = new FormData();
            formData.append("file", file);
            formData.append("label", label);
            formData.append("source", source);
            if (aiToolName) formData.append("ai_tool_name", aiToolName);
            if (description) formData.append("description", description);

            const res = await fetch(buildApiUrl('/api/contribute'), {
                method: "POST",
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Submission failed");
            }

            setSubmitSuccess(true);
            setFile(null);
            setPreview(null);
            setLabel("");
            setSource("");
            setAiToolName("");
            setDescription("");
            fetchStats();
        } catch (e: any) {
            setSubmitError(e.message || "Failed to submit contribution");
        } finally {
            setIsSubmitting(false);
        }
    };

    const resetForm = () => {
        setFile(null);
        setPreview(null);
        setLabel("");
        setSource("");
        setAiToolName("");
        setDescription("");
        setSubmitSuccess(false);
        setSubmitError(null);
    };

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <>
            <Head>
                <title>Help Improve Detection | DeepVerify</title>
            </Head>
            <Navbar />

            <main className="min-h-screen pt-24 pb-16 px-4">
                <div className="container mx-auto max-w-4xl">
                    {/* Header */}
                    <div className="text-center mb-12">
                        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary mb-4">
                            <Sparkles className="h-4 w-4" />
                            <span className="text-sm font-medium">Community Contribution</span>
                        </div>
                        <h1 className="text-4xl font-bold mb-4">Help Us Improve Detection</h1>
                        <p className="text-muted-foreground max-w-2xl mx-auto">
                            Your contributions help train our AI to better detect deepfakes.
                            Upload images and label them as real or AI-generated.
                        </p>
                    </div>

                    {/* Stats */}
                    {stats && (
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                            <Card>
                                <CardContent className="pt-6 text-center">
                                    <p className="text-3xl font-bold text-primary">{stats.user?.total || 0}</p>
                                    <p className="text-sm text-muted-foreground">Your Contributions</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="pt-6 text-center">
                                    <p className="text-3xl font-bold">{stats.global?.total || 0}</p>
                                    <p className="text-sm text-muted-foreground">Total Dataset</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="pt-6 text-center">
                                    <p className="text-3xl font-bold text-green-500">{stats.global?.real || 0}</p>
                                    <p className="text-sm text-muted-foreground">Real Images</p>
                                </CardContent>
                            </Card>
                            <Card>
                                <CardContent className="pt-6 text-center">
                                    <p className="text-3xl font-bold text-red-500">{stats.global?.fake || 0}</p>
                                    <p className="text-sm text-muted-foreground">AI Generated</p>
                                </CardContent>
                            </Card>
                        </div>
                    )}

                    {/* Success Message */}
                    {submitSuccess && (
                        <Card className="mb-8 border-green-500 bg-green-50 dark:bg-green-950/20">
                            <CardContent className="pt-6 flex items-center gap-4">
                                <CheckCircle2 className="h-8 w-8 text-green-500" />
                                <div>
                                    <p className="font-semibold text-green-700 dark:text-green-400">Thank you for your contribution!</p>
                                    <p className="text-sm text-green-600 dark:text-green-500">Your image has been added to our training dataset.</p>
                                </div>
                                <Button variant="outline" className="ml-auto" onClick={resetForm}>
                                    Contribute Another
                                </Button>
                            </CardContent>
                        </Card>
                    )}

                    {/* Upload Form */}
                    {!submitSuccess && (
                        <Card>
                            <CardHeader>
                                <CardTitle>Upload an Image</CardTitle>
                                <CardDescription>
                                    Help us by providing labeled images for training
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-6">
                                {/* File Upload */}
                                <div
                                    className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
                    ${preview ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50"}`}
                                    onDrop={handleDrop}
                                    onDragOver={(e) => e.preventDefault()}
                                    onClick={() => document.getElementById("file-input")?.click()}
                                >
                                    <input
                                        id="file-input"
                                        type="file"
                                        accept="image/*"
                                        className="hidden"
                                        onChange={handleFileChange}
                                    />

                                    {preview ? (
                                        <div className="space-y-4">
                                            <img src={preview} alt="Preview" className="max-h-64 mx-auto rounded-lg" />
                                            <p className="text-sm text-muted-foreground">{file?.name}</p>
                                        </div>
                                    ) : (
                                        <div className="space-y-4">
                                            <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                                            <div>
                                                <p className="font-medium">Drag & drop an image here</p>
                                                <p className="text-sm text-muted-foreground">or click to browse</p>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Label Selection */}
                                <div className="space-y-3">
                                    <Label className="text-base">Is this image real or AI-generated? *</Label>
                                    <RadioGroup value={label} onValueChange={setLabel} className="flex gap-4">
                                        <div className="flex items-center space-x-2">
                                            <RadioGroupItem value="real" id="real" />
                                            <Label htmlFor="real" className="flex items-center gap-2 cursor-pointer">
                                                <CheckCircle2 className="h-4 w-4 text-green-500" />
                                                Real Image
                                            </Label>
                                        </div>
                                        <div className="flex items-center space-x-2">
                                            <RadioGroupItem value="fake" id="fake" />
                                            <Label htmlFor="fake" className="flex items-center gap-2 cursor-pointer">
                                                <Bot className="h-4 w-4 text-red-500" />
                                                AI Generated
                                            </Label>
                                        </div>
                                    </RadioGroup>
                                </div>

                                {/* Source Selection */}
                                <div className="space-y-3">
                                    <Label className="text-base">Where did this image come from? *</Label>
                                    <RadioGroup value={source} onValueChange={setSource} className="grid grid-cols-2 gap-3">
                                        <div className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-accent cursor-pointer">
                                            <RadioGroupItem value="camera" id="camera" />
                                            <Label htmlFor="camera" className="flex items-center gap-2 cursor-pointer">
                                                <Camera className="h-4 w-4" />
                                                Camera / Phone
                                            </Label>
                                        </div>
                                        <div className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-accent cursor-pointer">
                                            <RadioGroupItem value="download" id="download" />
                                            <Label htmlFor="download" className="flex items-center gap-2 cursor-pointer">
                                                <Download className="h-4 w-4" />
                                                Downloaded
                                            </Label>
                                        </div>
                                        <div className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-accent cursor-pointer">
                                            <RadioGroupItem value="ai_tool" id="ai_tool" />
                                            <Label htmlFor="ai_tool" className="flex items-center gap-2 cursor-pointer">
                                                <Bot className="h-4 w-4" />
                                                AI Tool
                                            </Label>
                                        </div>
                                        <div className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-accent cursor-pointer">
                                            <RadioGroupItem value="other" id="other" />
                                            <Label htmlFor="other" className="flex items-center gap-2 cursor-pointer">
                                                <HelpCircle className="h-4 w-4" />
                                                Other
                                            </Label>
                                        </div>
                                    </RadioGroup>
                                </div>

                                {/* AI Tool Selection (conditional) */}
                                {source === "ai_tool" && (
                                    <div className="space-y-3">
                                        <Label className="text-base">Which AI tool generated this? *</Label>
                                        <Select value={aiToolName} onValueChange={setAiToolName}>
                                            <SelectTrigger>
                                                <SelectValue placeholder="Select AI tool..." />
                                            </SelectTrigger>
                                            <SelectContent>
                                                {AI_TOOLS.map((tool) => (
                                                    <SelectItem key={tool} value={tool}>{tool}</SelectItem>
                                                ))}
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}

                                {/* Description (optional) */}
                                <div className="space-y-3">
                                    <Label className="text-base">Additional notes (optional)</Label>
                                    <Textarea
                                        placeholder="Any additional context about this image..."
                                        value={description}
                                        onChange={(e) => setDescription(e.target.value)}
                                        rows={3}
                                    />
                                </div>

                                {/* Error Message */}
                                {submitError && (
                                    <div className="flex items-center gap-2 text-red-500 text-sm">
                                        <AlertCircle className="h-4 w-4" />
                                        {submitError}
                                    </div>
                                )}

                                {/* Submit Button */}
                                <Button
                                    className="w-full"
                                    size="lg"
                                    onClick={handleSubmit}
                                    disabled={!file || !label || !source || isSubmitting}
                                >
                                    {isSubmitting ? (
                                        <>
                                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                            Uploading...
                                        </>
                                    ) : (
                                        <>
                                            <Upload className="h-4 w-4 mr-2" />
                                            Submit Contribution
                                        </>
                                    )}
                                </Button>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </main>
        </>
    );
}

export const getServerSideProps: GetServerSideProps = async ({ locale }) => ({
    props: {
        ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
});
