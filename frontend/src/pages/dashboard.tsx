import Head from "next/head";
import dynamic from "next/dynamic";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import DashboardItem from "@/components/DashboardItem";
import { fetcher } from "@/lib/api";
import useSWR from "swr";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Upload, FileSearch } from "lucide-react";
import Link from "next/link";
const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

export default function Dashboard() {
  const { t } = useTranslation("common");
  const { data, error } = useSWR("/api/dashboard", fetcher, {
    fallbackData: [],
  });

  const items = data || [];
  const isLoading = !data && !error;

  return (
    <div className="min-h-screen bg-background">
      <Head>
        <title>Dashboard — DeepVerify</title>
        <meta name="description" content="Your recent image analyses." />
      </Head>

      <Navbar />

      <main className="pt-24">
        <div className="container mx-auto px-4 py-8 md:py-12">
          <div className="max-w-5xl mx-auto">
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-3xl font-bold mb-2">{t("dashboard.title")}</h1>
                <p className="text-muted-foreground">
                  {t("dashboard.subtitle")}
                </p>
              </div>

              <Button asChild>
                <Link href="/indexloggedin">
                  <Upload className="h-4 w-4 mr-2" />
                  {t("dashboard.newAnalysis")}
                </Link>
              </Button>
            </div>

            {/* Loading skeleton */}
            {isLoading && (
              <div className="space-y-4">
                {Array.from({ length: 5 }).map((_, i) => (
                  <Skeleton key={i} className="h-32 w-full" />
                ))}
              </div>
            )}

            {/* Empty state */}
            {!isLoading && items.length === 0 && (
              <div className="text-center py-16 space-y-6">
                <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center mx-auto">
                  <FileSearch className="h-8 w-8 text-muted-foreground" />
                </div>

                <div className="space-y-2">
                  <h3 className="text-lg font-semibold">{t("dashboard.noAnalyses")}</h3>
                  <p className="text-sm text-muted-foreground max-w-sm mx-auto">
                    {t("dashboard.noAnalysesDescription")}
                  </p>
                </div>

                <Button asChild>
                  <Link href="/indexloggedin">
                    <Upload className="h-4 w-4 mr-2" />
                    {t("dashboard.uploadImage")}
                  </Link>
                </Button>
              </div>
            )}

            {/* Items list */}
            {!isLoading && items.length > 0 && (
              <div className="space-y-4">
                {items.map((it: any) => (
                  <DashboardItem key={it.job_id} item={it} />
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
