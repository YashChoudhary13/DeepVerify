import Head from "next/head";
import dynamic from "next/dynamic";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import ConsensusCard from "../../src/components/ConsensusCard";
import ModelResultCard from "../../src/components/ModelResultCard";
import useSWR from "swr";
import { fetcher, getAuthHeaders } from "../../src/lib/api";
import { useRouter } from "next/router";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw, Download, Loader2 } from "lucide-react";
import { useState } from "react";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";
const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

export default function ResultPage() {
  const { t } = useTranslation("common");
  const router = useRouter();
  const { id } = router.query;
  const [isRerunning, setIsRerunning] = useState(false);

  const { data: job, error, mutate } = useSWR(
    () => (id ? `/api/jobs/${id}` : null),
    fetcher,
    {
      refreshInterval: (data) => {
        // Keep refreshing if job is processing, stop when completed
        if (data?.status === "pending" || data?.status === "processing") {
          return 1000; // Refresh every 1 second when processing
        }
        return 0; // Stop auto-refresh when completed
      },
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
    }
  );

  const isLoading = !job && !error;
  const isProcessing =
    job?.status === "pending" || job?.status === "processing";

  const handleRerun = async () => {
    if (!id || isRerunning) return;

    setIsRerunning(true);
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${API_BASE}/api/jobs/${id}/rerun`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(),
        },
        credentials: "include",
      });

      if (!response.ok) {
        const error = await response.json();
        alert(`${t("result.rerunFailed")}: ${error.detail || t("result.rerunError")}`);
        return;
      }

      // Immediately refresh the job data to show pending status
      await mutate();
      // Show success message
      alert(t("result.rerunStarted"));
    } catch (err) {
      console.error("Error re-running analysis:", err);
      alert(t("result.rerunError"));
    } finally {
      setIsRerunning(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!job) return;

    const doc = new jsPDF();

    // Title
    doc.setFontSize(18);
    doc.text("DeepVerify Analysis Report", 14, 22);

    // Metadata
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(`Job ID: ${String(job.job_id)}`, 14, 32);
    doc.text(`Date: ${new Date(job.created_at).toLocaleString()}`, 14, 38);

    // Image
    if (job.image?.thumbnail_url) {
      try {
        const imgData = await new Promise<string>((resolve, reject) => {
          const img = new Image();
          img.crossOrigin = "Anonymous";
          img.onload = () => {
            const canvas = document.createElement("canvas");
            canvas.width = img.width;
            canvas.height = img.height;
            const ctx = canvas.getContext("2d");
            if (ctx) {
              ctx.drawImage(img, 0, 0);
              resolve(canvas.toDataURL("image/jpeg"));
            } else {
              reject(new Error("Canvas context failed"));
            }
          };
          img.onerror = reject;
          img.src = job.image.thumbnail_url;
        });

        // Add image (x, y, w, h) - adjust aspect ratio if needed, here fixed size for simplicity
        doc.addImage(imgData, "JPEG", 14, 45, 50, 50);
      } catch (err) {
        console.error("Failed to load image for PDF", err);
        doc.text("(Image failed to load)", 14, 60);
      }
    }

    // Consensus
    const consensusY = 110;
    doc.setFontSize(14);
    doc.setTextColor(0);
    doc.text("Consensus Result", 14, consensusY);

    const score = job.consensus?.score ?? 0;
    const decision = job.consensus?.decision || "PENDING";

    let verdictLabel = decision;
    if (decision === "REAL") verdictLabel = "Likely Authentic";
    if (decision === "FAKE") verdictLabel = "Likely Manipulated";
    if (decision === "UNCERTAIN") verdictLabel = "Uncertain";

    doc.setFontSize(11);
    doc.text(`Verdict: ${verdictLabel}`, 14, consensusY + 10);
    doc.text(`Confidence: ${(score * 100).toFixed(1)}%`, 14, consensusY + 16);

    // Models
    doc.setFontSize(14);
    doc.text("Model Breakdown", 14, consensusY + 30);

    const tableData = job.models?.map((m: any) => {
      const mScore = m.score ?? 0;
      const mScorePct = Math.round(mScore * 100);
      const prediction = m.labels?.label ?? (mScorePct >= 50 ? "REAL" : "FAKE");

      return [
        m.model_name,
        prediction,
        `${mScorePct.toFixed(1)}%`
      ];
    }) || [];

    autoTable(doc, {
      startY: consensusY + 35,
      head: [["Model", "Prediction", "Confidence"]],
      body: tableData,
      theme: 'striped',
      headStyles: { fillColor: [63, 81, 181] }
    });

    doc.save(`DeepVerify_Report_${String(job.job_id).slice(0, 8)}.pdf`);
  };

  // ---------- LOADING UI ----------
  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />

        <main className="pt-16 max-w-6xl mx-auto px-4 py-12">
          <div className="space-y-6">
            <Skeleton className="h-8 w-1/3" />
            <Skeleton className="h-64 w-full" />
            <Skeleton className="h-64 w-full" />
          </div>
        </main>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen bg-background">
        <Navbar />
        <main className="pt-16 max-w-4xl mx-auto px-4 py-12 text-center">
          <p className="text-muted-foreground">{t("result.jobNotFound")}</p>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <Head>
        <title>Analysis Result — {job.job_id}</title>
      </Head>

      <Navbar />

      <main className="pt-16 max-w-7xl mx-auto px-4 py-12">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">{t("result.title")}</h1>
          <p className="text-muted-foreground">{job.job_id}</p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* LEFT COLUMN — CONSENSUS + MODELS */}
          <div className="lg:col-span-2 space-y-10">
            {/* Consensus Card */}
            <ConsensusCard
              consensus={job.consensus}
              imageUrl={job.image?.thumbnail_url}
            />

            {/* Per-model breakdown */}
            <section>
              <h3 className="text-2xl font-semibold mb-5">
                {t("result.perModelBreakdown")}
              </h3>

              <div className="grid md:grid-cols-2 gap-6">
                {job.models?.map((model: any, index: number) => (
                  <ModelResultCard key={index} model={model} />
                ))}
              </div>
            </section>
          </div>

          {/* RIGHT SIDEBAR */}
          <aside className="space-y-6 sticky top-24 h-fit">
            {/* Image */}
            <Card className="p-3">
              <img
                src={job.image?.thumbnail_url}
                alt={t("result.analyzedImage")}
                className="rounded-md w-full"
              />
            </Card>

            {/* Buttons */}
            <div className="space-y-3">
              <Button
                variant="outline"
                className="w-full"
                onClick={handleRerun}
                disabled={isRerunning || isProcessing}
              >
                {isRerunning ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {t("result.rerunning")}
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2" />
                    {t("result.rerunAnalysis")}
                  </>
                )}
              </Button>

              <Button variant="outline" className="w-full" onClick={handleDownloadPdf}>
                <Download className="h-4 w-4 mr-2" />
                {t("result.downloadPdf")}
              </Button>
            </div>

            {/* Details */}
            <Card className="p-5">
              <h4 className="font-semibold mb-1">{t("result.details")}</h4>
              <p className="text-sm text-muted-foreground">
                {t("result.uploaded")}: {new Date(job.created_at).toLocaleString()}
              </p>
            </Card>
          </aside>
        </div>
      </main>
    </div>
  );
}
