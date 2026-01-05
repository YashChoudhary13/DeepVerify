import Head from "next/head";
import dynamic from "next/dynamic";
import ConsensusCard from "@/components/ConsensusCard";
import ModelResultCard from "@/components/ModelResultCard";
import { Card } from "@/components/ui/card";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common", "navbar"])),
    },
  };
}


const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });

export default function SampleReport() {
  const sampleJob = {
    job_id: "sample",
    created_at: new Date().toISOString(),
    image: {
      thumbnail_url: "/sample-face.jpg", // put image in /public
    },
    consensus: {
      decision: "FAKE",
      score: 0.47,
    },
    models: [
      {
        model_name: "MobileNetV2_Deepfake",
        score: 0.9,
        labels: { label: "fake" },
        heatmap_url: "/sample_heatmap_1.png",
      },
      {
        model_name: "Xception_Deepfake",
        score: 0.67,
        labels: { label: "real" },
        heatmap_url: "/sample_heatmap_2.png",
      },
      {
        model_name: "ResNet50_Deepfake",
        score: 0.55,
        labels: { label: "real" },
        heatmap_url: "//sample_heatmap_3.png",
      },
      {
        model_name: "EfficientNetB0_Deepfake",
        score: 0.54,
        labels: { label: "real" },
        heatmap_url: "/sample_heatmap_4.png",
      },
    ],
  };

  return (
    <div className="min-h-screen bg-background">
      <Head>
        <title>Sample Analysis — DeepVerify</title>
      </Head>

      <Navbar />

      <main className="pt-16 max-w-7xl mx-auto px-4 py-12">
        <ConsensusCard
          consensus={sampleJob.consensus}
          imageUrl={sampleJob.image.thumbnail_url}
        />


        <section className="mt-10 grid md:grid-cols-2 gap-6">
          {sampleJob.models.map((model, i) => (
            <ModelResultCard key={i} model={model} />
          ))}
        </section>
      </main>
    </div>
  );
}
