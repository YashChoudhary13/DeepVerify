// pages/support.tsx
import Head from "next/head";
import dynamic from "next/dynamic";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import { useState } from "react";
import { Button } from "@/components/ui/button";
const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });
const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

export default function Support() {
  const { t } = useTranslation("common");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<null | "idle" | "sending" | "success" | "error">(null);

  const submitTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !message) {
      setStatus("error");
      return;
    }
    setStatus("sending");

    try {
      // Replace this URL with your backend support endpoint if you have one
      const res = await fetch(`${API}/support`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, message }),
      });

      if (res.ok) {
        setStatus("success");
        setName("");
        setEmail("");
        setMessage("");
      } else {
        setStatus("error");
      }
    } catch (err) {
      setStatus("error");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Head>
        <title>DeepVerify — Support</title>
        <meta name="description" content="Contact support for DeepVerify — help with billing, technical issues and research inquiries." />
      </Head>

      <Navbar />

      <main className="pt-16">
        <section className="py-16">
          <div className="container mx-auto px-4 max-w-4xl text-center">
            <h1 className="text-3xl md:text-4xl font-bold">{t("support.title")}</h1>
            <p className="text-base text-muted-foreground max-w-3xl mx-auto mt-3">
              {t("support.subtitle")}
            </p>
          </div>
        </section>

        <section className="py-8">
          <div className="container mx-auto px-4 max-w-6xl grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 rounded-xl border border-border bg-card p-6 shadow-sm">
              <h2 className="text-xl font-semibold mb-4">{t("support.contactSupport")}</h2>

              <form onSubmit={submitTicket} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-1">{t("support.name")}</label>
                  <input
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full border border-input bg-background rounded px-3 py-2"
                    placeholder={t("support.namePlaceholder")}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">{t("support.email")}</label>
                  <input
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full border border-input bg-background rounded px-3 py-2"
                    placeholder={t("support.emailPlaceholder")}
                    required
                    type="email"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium mb-1">{t("support.message")}</label>
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    className="w-full border border-input bg-background rounded px-3 py-2 h-32"
                    placeholder={t("support.messagePlaceholder")}
                    required
                  />
                </div>

                <div>
                  <Button type="submit" size="lg" disabled={status === "sending"}>
                    {status === "sending" ? t("support.sending") : t("support.sendMessage")}
                  </Button>

                  {status === "success" && (
                    <div className="text-green-600 text-sm mt-3">{t("support.success")}</div>
                  )}
                  {status === "error" && (
                    <div className="text-red-600 text-sm mt-3">{t("support.error")}</div>
                  )}
                </div>
              </form>
            </div>

            <aside className="rounded-xl border border-border bg-card p-6 shadow-sm">
              <h3 className="text-lg font-semibold mb-3">{t("support.quickResources")}</h3>

              <ul className="space-y-3 text-sm text-muted-foreground">
                <li>
                  <a href="/docs" className="text-primary hover:underline">{t("support.documentation")}</a>
                </li>
                <li>
                  <a href="/faq" className="text-primary hover:underline">{t("support.faq")}</a>
                </li>
                <li>
                  <a href="/membership" className="text-primary hover:underline">{t("support.billingPlans")}</a>
                </li>
              </ul>

              <div className="mt-6">
                <h4 className="text-sm font-medium mb-2">{t("support.officeHours")}</h4>
                <div className="text-sm text-muted-foreground">{t("support.officeHoursTime")}</div>
              </div>
            </aside>
          </div>
        </section>
      </main>
    </div>
  );
}
