// pages/membership.tsx
import Head from "next/head";
import dynamic from "next/dynamic";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import { Button } from "@/components/ui/button";
import { Shield, Zap, FileDown } from "lucide-react";
import { useCallback, useState } from "react";

const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

export default function Membership() {
  const { t } = useTranslation("common");
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);

  const startCheckout = useCallback(async (plan: "pro_monthly" | "pro_yearly") => {
    try {
      setLoadingPlan(plan);
      const res = await fetch(`${API}/create-checkout-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Failed to create checkout session");
      }

      const data = await res.json();
      // redirect the browser to Stripe Checkout (session URL)
      window.location.href = data.url;
    } catch (err) {
      console.error("Checkout error:", err);
      alert("Could not start checkout. See console for details.");
    } finally {
      setLoadingPlan(null);
    }
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Head>
        <title>DeepVerify — Membership</title>
        <meta
          name="description"
          content="Choose a DeepVerify plan for advanced features, priority processing and team access."
        />
      </Head>

      <Navbar />

      <main className="pt-16">
        <section className="py-16">
          <div className="container mx-auto px-4 max-w-4xl text-center">
            <h1 className="text-3xl md:text-4xl font-bold">{t("membership.title")}</h1>
            <p className="text-base text-muted-foreground max-w-2xl mx-auto mt-3">
              {t("membership.subtitle")}
            </p>
          </div>
        </section>

        <section className="py-8">
          <div className="container mx-auto px-4 max-w-7xl">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
              {/* Left: Benefits */}
              <div className="md:col-span-1 rounded-xl border border-border bg-card p-6 shadow-sm">
                <h2 className="text-xl font-semibold mb-3">{t("membership.whyUpgrade")}</h2>
                <ul className="space-y-4 text-sm text-muted-foreground">
                  <li className="flex gap-3 items-start">
                    <Shield className="h-5 w-5 text-primary mt-1" />
                    <div>
                      <div className="font-medium">{t("membership.priorityProcessing")}</div>
                      <div className="text-xs">{t("membership.priorityProcessingDesc")}</div>
                    </div>
                  </li>

                  <li className="flex gap-3 items-start">
                    <Zap className="h-5 w-5 text-primary mt-1" />
                    <div>
                      <div className="font-medium">{t("membership.batchUploads")}</div>
                      <div className="text-xs">{t("membership.batchUploadsDesc")}</div>
                    </div>
                  </li>

                  <li className="flex gap-3 items-start">
                    <FileDown className="h-5 w-5 text-primary mt-1" />
                    <div>
                      <div className="font-medium">{t("membership.downloadableReports")}</div>
                      <div className="text-xs">{t("membership.downloadableReportsDesc")}</div>
                    </div>
                  </li>
                </ul>

                <div className="mt-6">
                  <a href="/support" className="text-sm text-primary hover:underline">
                    {t("membership.enterpriseContact")}
                  </a>
                </div>
              </div>

              {/* Pricing cards */}
              <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Monthly */}
                <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col">
                  <div className="flex items-baseline justify-between">
                    <div>
                      <h3 className="text-2xl font-semibold">{t("membership.proMonthly")}</h3>
                      <p className="text-sm text-muted-foreground mt-1">10 uploads limit for Free users</p>
                      <p className="text-sm text-muted-foreground mt-1">{t("membership.billedMonthly")}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-extrabold leading-none">$19</div>
                      <div className="text-xs text-muted-foreground">{t("membership.perMonth")}</div>
                    </div>
                  </div>

                  <ul className="mt-6 space-y-3 text-sm">
                    <li>{t("membership.features.priority")}</li>
                    <li>Unlimited uploads</li>
                    <li>{t("membership.features.pdfReports")}</li>
                    <li>{t("membership.features.emailSupport")}</li>
                  </ul>

                  <div className="mt-6">
                    <Button
                      variant="outline"
                      size="lg"
                      onClick={() => startCheckout("pro_monthly")}
                      disabled={loadingPlan === "pro_monthly"}
                    >
                      {loadingPlan === "pro_monthly" ? t("membership.redirecting") : t("membership.startPro")}
                    </Button>
                  </div>
                </div>

                {/* Yearly */}
                <div className="rounded-xl border border-border bg-card p-6 shadow-sm flex flex-col">
                  <div className="flex items-baseline justify-between">
                    <div>
                      <h3 className="text-2xl font-semibold">{t("membership.proYearly")}</h3>
                      <p className="text-sm text-muted-foreground mt-1">{t("membership.bestValue")}</p>
                    </div>
                    <div className="text-right">
                      <div className="text-3xl font-extrabold leading-none">$179</div>
                      <div className="text-xs text-muted-foreground">{t("membership.perYear")}</div>
                    </div>
                  </div>

                  <ul className="mt-6 space-y-3 text-sm">
                    <li>{t("membership.features.priority")}</li>
                    <li>Unlimited uploads</li>
                    <li>{t("membership.features.pdfReports")}</li>
                    <li>{t("membership.features.prioritySupport")}</li>
                  </ul>

                  <div className="mt-6">
                    <Button
                      variant="outline"
                      size="lg"
                      onClick={() => startCheckout("pro_yearly")}
                      disabled={loadingPlan === "pro_yearly"}
                    >
                      {loadingPlan === "pro_yearly" ? t("membership.redirecting") : t("membership.startYearly")}
                    </Button>
                  </div>
                </div>
              </div>
            </div>

            {/* FAQ */}
            <div className="mt-10 rounded-xl border border-border bg-card p-6 shadow-sm">
              <h3 className="text-lg font-semibold mb-4">{t("membership.faq")}</h3>

              <div className="space-y-3 text-sm text-muted-foreground">
                <details className="p-3 rounded-lg border">
                  <summary className="font-medium cursor-pointer">{t("membership.cancelAnytime")}</summary>
                  <div className="mt-2">{t("membership.cancelAnswer")}</div>
                </details>

                <details className="p-3 rounded-lg border">
                  <summary className="font-medium cursor-pointer">{t("membership.teamPlans")}</summary>
                  <div className="mt-2">{t("membership.teamPlansAnswer")}</div>
                </details>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
