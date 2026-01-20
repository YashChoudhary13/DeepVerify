// pages/indexloggedin.tsx
import Head from "next/head";
import dynamic from "next/dynamic";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import UploadCard from "@/components/UploadCard";
import FeatureCard from "@/components/FeatureCard";
import { Button } from "@/components/ui/button";
import { Layers, Flame, Zap, Shield, Lock, FileDown, Sparkles } from "lucide-react";
import useSWR from "swr";
import { fetcher, getAuthHeaders } from "@/lib/api";
import type { DashboardJob } from "@/types";
import { useRouter } from "next/router";

const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

export default function LoggedInHome() {
  const router = useRouter();

  const handleSampleReport = async () => {
    try {
      const API_BASE =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      const res = await fetch(`${API_BASE}/api/jobs/demo`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...getAuthHeaders(), // ← THIS WAS MISSING
        },
        credentials: "include",
      });

      if (!res.ok) {
        throw new Error("Failed to create demo job");
      }

      const data = await res.json();

      if (!data.job_id) {
        throw new Error("No job_id returned from demo job");
      }

      router.push(`/${data.job_id}`);
    } catch (err) {
      console.error(err);
      alert("Failed to load sample report");
    }
  };

  const { t } = useTranslation("common");
  const { data: jobs } = useSWR<DashboardJob[]>(
    "/api/dashboard",
    fetcher
  );
  const features = [
    {
      icon: Layers,
      title: t("home.features.modelPipeline.title"),
      description: t("home.features.modelPipeline.description"),
    },
    {
      icon: Flame,
      title: t("home.features.heatmap.title"),
      description: t("home.features.heatmap.description"),
    },
    {
      icon: Zap,
      title: t("home.features.accuracy.title"),
      description: t("home.features.accuracy.description"),
    },
    {
      icon: Zap,
      title: t("home.features.fast.title"),
      description: t("home.features.fast.description"),
    },
    {
      icon: Lock,
      title: t("home.features.secure.title"),
      description: t("loggedIn.securePrivate"),
    },
    {
      icon: FileDown,
      title: t("home.features.downloadable.title"),
      description: t("home.features.downloadable.description"),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Head>
        <title>DeepVerify — Upload</title>
        <meta
          name="description"
          content="Upload and analyze images with DeepVerify's multi-model detection pipeline."
        />
      </Head>

      <Navbar />

      <main className="pt-16">
        {/* Top / Hero condensed for logged-in */}
        <section className="py-8 md:py-12">
          <div className="container mx-auto px-4">
            <div className="max-w-5xl mx-auto text-center">
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight">
                {t("loggedIn.quickVerify")}
              </h1>
              <p className="text-base md:text-lg text-muted-foreground max-w-3xl mx-auto mt-3">
                {t("loggedIn.quickVerifyDescription")}
              </p>
            </div>
          </div>
        </section>

        {/* Main two-column area: center UploadCard (wide) + right extras */}
        <section className="py-8 md:py-12">
          <div className="container mx-auto px-4">
            <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
              {/* Center column: wide Upload area (spans 2 cols on large screens) */}
              <div className="lg:col-span-2">
                <div className="rounded-xl shadow-sm border border-border bg-card p-6">
                  <h2 className="text-2xl font-semibold mb-4">{t("loggedIn.uploadAnalyze")}</h2>
                  <p className="text-sm text-muted-foreground mb-6">
                    {t("loggedIn.uploadDescription")}
                  </p>

                  {/* UploadCard should implement the drag/drop UI + progress. Keep it wide and centered. */}
                  <div className="max-w-3xl mx-auto">
                    <UploadCard />
                  </div>

                  <div className="mt-6 flex items-center gap-3 justify-center">
                    <Button size="lg" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
                      {t("loggedIn.uploadImage")}
                    </Button>
                    <Button variant="outline" size="lg" onClick={() => window.location.href = "/dashboard"}>
                      {t("loggedIn.viewHistory")}
                    </Button>
                  </div>
                </div>
              </div>

              {/* Right column: extras / quick actions / recent analyses */}
              <aside className="lg:col-span-1">
                <div className="rounded-xl border border-border bg-card p-6 shadow-sm sticky top-24">
                  <h3 className="text-lg font-semibold mb-3">{t("loggedIn.quickActions")}</h3>

                  <div className="flex flex-col gap-3">
                    <button
                      onClick={() => document.querySelector<HTMLInputElement>("input[type=file]")?.click()}
                      className="w-full text-left px-4 py-3 bg-muted hover:bg-muted/80 rounded-lg transition"
                      aria-label="Upload image"
                    >
                      {t("loggedIn.uploadImage")}
                    </button>

                    <button
                      onClick={() => (window.location.href = "/dashboard")}
                      className="w-full text-left px-4 py-3 border rounded-lg hover:shadow-sm transition"
                      aria-label="View dashboard"
                    >
                      {t("loggedIn.viewDashboard")}
                    </button>

                    <button
                      onClick={handleSampleReport}
                      className="w-full text-left px-4 py-3 border rounded-lg hover:shadow-sm transition"
                      aria-label="Sample report"
                    >
                      {t("loggedIn.openSampleReport")}
                    </button>
                  </div>

                  <div className="mt-6 border-t pt-4">
                    <h4 className="text-sm font-medium uppercase tracking-wide mb-3">{t("loggedIn.recentAnalyses")}</h4>

                    {/* Placeholder list — replace with real data */}
                    <ul className="space-y-3">
                      {jobs?.slice(0, 3).map((job: any) => (
                        <li
                          key={job.id}
                          className="flex items-center gap-3 cursor-pointer"
                          onClick={() => (window.location.href = `/${job.id}`)}
                        >
                          <div className="w-12 h-12 rounded overflow-hidden flex-shrink-0 bg-muted">
                            {job.image?.thumbnail_url && (
                              <img
                                src={`${process.env.NEXT_PUBLIC_API_URL}${job.image.thumbnail_url}`}
                                className="w-full h-full object-cover"
                                alt="analysis thumbnail"
                              />
                            )}
                          </div>

                          <div className="flex-1">
                            <div className="text-sm font-medium">
                              Analysis #{job.analysis_number ?? job.id}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              {job.consensus?.decision ?? "PENDING"} •{" "}
                              {Math.round((job.consensus?.score ?? 0) * 100)}%
                            </div>
                          </div>
                        </li>
                      ))}

                      {!jobs?.length && (
                        <li className="text-sm text-muted-foreground">
                          No analyses yet
                        </li>
                      )}
                    </ul>

                    <div className="mt-4">
                      <a href="/dashboard" className="text-sm text-primary hover:underline">
                        {t("loggedIn.viewAllAnalyses")}
                      </a>
                    </div>
                  </div>
                </div>

                {/* Small trust panel */}
                <div className="mt-4 rounded-xl border border-border bg-card p-4 shadow-sm">
                  <div className="flex items-center gap-3">
                    <Shield className="h-5 w-5 text-primary" />
                    <div>
                      <div className="text-sm font-medium">{t("loggedIn.securePrivate")}</div>
                      <div className="text-xs text-muted-foreground">{t("loggedIn.analysisEncrypted")}</div>
                    </div>
                  </div>
                </div>
              </aside>
            </div>

            {/* Features — SAME WIDTH */}
            <div className="mt-10">
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                {features.map((f, i) => (
                  <FeatureCard
                    key={i}
                    icon={f.icon}
                    title={f.title}
                    desc={f.description}
                  />
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Community Contribution CTA */}
        <section className="py-12 bg-gradient-to-r from-primary/5 to-primary/10">
          <div className="container mx-auto px-4 max-w-7xl">
            <div className="rounded-xl border border-primary/20 bg-card p-8 text-center">
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary mb-4">
                <Sparkles className="h-4 w-4" />
                <span className="text-sm font-medium">Community Program</span>
              </div>
              <h3 className="text-2xl font-bold mb-3">Help Us Improve Detection</h3>
              <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
                Your contributions train our AI to better detect deepfakes.
                Upload and label images to help build a more accurate model.
              </p>
              <Button size="lg" onClick={() => (window.location.href = "/contribute")}>
                <Sparkles className="h-4 w-4 mr-2" />
                Contribute Now
              </Button>
            </div>
          </div>
        </section>

        {/* small footer CTA */}
        <section className="py-12">
          <div className="container mx-auto px-4 max-w-7xl">
            <div className="rounded-xl border border-border bg-card p-6 text-center">
              <h3 className="text-xl font-semibold mb-2">{t("loggedIn.needHelp")}</h3>
              <p className="text-sm text-muted-foreground mb-4">{t("loggedIn.contactSupport")}</p>
              <div className="flex items-center justify-center gap-3">
                <Button onClick={() => (window.location.href = "/support")}>{t("loggedIn.contactSupportButton")}</Button>
                <Button variant="outline" onClick={() => (window.location.href = "/dashboard")}>{t("loggedIn.viewHistory")}</Button>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
