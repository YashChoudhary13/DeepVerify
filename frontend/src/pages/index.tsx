import Head from "next/head";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import UploadCard from "@/components/UploadCard";
import FeatureCard from "@/components/FeatureCard";
import { Button } from "@/components/ui/button";
import {
  Layers,
  Flame,
  Zap,
  Shield,
  Lock,
  FileDown,
} from "lucide-react";
import dynamic from "next/dynamic";
const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

export default function Home() {
  const { t } = useTranslation("common");
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
      description: t("home.features.secure.description"),
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
        <title>DeepVerify — Deepfake Detection</title>
        <meta
          name="description"
          content="Multi-model deepfake detection with explainable metrics and heatmap visualizations."
        />
      </Head>

      <Navbar />

      <main className="pt-16">
        {/* HERO */}
          <section className="relative min-h-screen flex items-center py-20 md:py-32 overflow-hidden">
           <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-background to-background" />
            <div className="container mx-auto px-4 relative">
             <div className="max-w-4xl mx-auto text-center space-y-8">
              <div className="space-y-4">
                <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
                  {t("home.title")}
                </h1>
                <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto">
                  {t("home.subtitle")}
                </p>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-4">
                <a href="/login">
                  <Button size="lg">{t("home.getStarted")}</Button>
                </a>

                <a href="#features">
                  <Button variant="outline" size="lg">
                    {t("home.learnMore")}
                  </Button>
                </a>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-8 pt-8 text-sm text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-primary" />
                  <span>{t("home.trustedBy")}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-primary" />
                  <span>{t("home.accuracy")}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Lock className="h-4 w-4 text-primary" />
                  <span>{t("home.secure")}</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* UPLOAD */}
        <section className="py-16 md:py-24">
          <div className="container mx-auto px-4">
            <div className="max-w-2xl mx-auto text-center space-y-2 mb-8">
              <h2 className="text-3xl font-bold">{t("home.tryItNow")}</h2>
              <p className="text-muted-foreground">
                {t("home.tryItDescription")}
              </p>
            </div>

            <UploadCard />

            <p className="text-center text-sm text-muted-foreground mt-4">
              {t("home.signInToSave")}
            </p>
          </div>
        </section>

        {/* FEATURES */}
        <section id="features" className="py-16 md:py-24 bg-muted/30">
          <div className="container mx-auto px-4">
            <div className="max-w-6xl mx-auto">
              <div className="text-center mb-12 space-y-2">
                <h2 className="text-3xl font-bold">{t("home.powerfulFeatures")}</h2>
                <p className="text-muted-foreground max-w-2xl mx-auto">
                  {t("home.featuresSubtitle")}
                </p>
              </div>

              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
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

        {/* CTA */}
        <section className="py-16 md:py-24">
          <div className="container mx-auto px-4">
            <div className="max-w-4xl mx-auto text-center space-y-8">
              <h2 className="text-3xl md:text-4xl font-bold">
                {t("home.readyToVerify")}
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                {t("home.readyDescription")}
              </p>

              <a href="/login" className="mt-6 block">
                <Button size="lg">{t("home.signInToGetStarted")}</Button>
              </a>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t py-8">
        <div className="container mx-auto px-4">
          <p className="text-center text-sm text-muted-foreground">
            {t("home.footer")}
          </p>
        </div>
      </footer>
    </div>
  );
}
