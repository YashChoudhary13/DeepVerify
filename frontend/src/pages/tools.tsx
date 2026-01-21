// pages/tools.tsx
import Head from "next/head";
import dynamic from "next/dynamic";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import { Card } from "@/components/ui/card";
import { useRouter } from "next/router";
import { Shield, FileSearch, ArrowRight, Search } from "lucide-react";

const Navbar = dynamic(() => import("@/components/Navbar"), { ssr: false });

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

export default function ToolsPage() {
  const { t } = useTranslation("common");
  const router = useRouter();

  const tools = [
    {
      id: "deepfake-detection",
      title: "Deepfake Detection",
      description: "Analyze images for AI-generated content using multiple detection models",
      icon: Shield,
      path: "/indexloggedin",
      gradient: "from-blue-500 to-indigo-600",
    },
    {
      id: "metadata-analyzer",
      title: "Metadata Analyzer",
      description: "Extract EXIF metadata including camera info, timestamps, and location data",
      icon: FileSearch,
      path: "/tools/metadata",
      gradient: "from-purple-500 to-pink-600",
    },
    {
      id: "reverse-search",
      title: "Reverse Image Search",
      description: "Find where this image has appeared online",
      icon: Search,
      path: "/tools/reverse-search",
      gradient: "from-amber-500 to-orange-600",
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Head>
        <title>Tools — DeepVerify</title>
        <meta name="description" content="Forensic analysis tools for image verification" />
      </Head>

      <Navbar />

      <main className="pt-24 pb-16">
        <div className="container mx-auto px-4">
          <div className="max-w-5xl mx-auto">
            {/* Header */}
            <div className="mb-12 text-center">
              <h1 className="text-4xl font-bold mb-4">
                Forensic Tools
              </h1>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Professional-grade tools for image analysis and verification
              </p>
            </div>

            {/* Tools Grid */}
            <div className="grid md:grid-cols-2 gap-6">
              {tools.map((tool) => {
                const Icon = tool.icon;
                return (
                  <Card
                    key={tool.id}
                    className="p-6 hover:shadow-lg transition-all cursor-pointer group border-2 hover:border-primary/50"
                    onClick={() => router.push(tool.path)}
                  >
                    <div className="flex flex-col h-full">
                      {/* Icon with gradient background */}
                      <div className={`h-16 w-16 rounded-xl bg-gradient-to-br ${tool.gradient} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                        <Icon className="h-8 w-8 text-white" />
                      </div>

                      {/* Content */}
                      <div className="flex-1">
                        <h3 className="text-xl font-semibold mb-2 group-hover:text-primary transition-colors">
                          {tool.title}
                        </h3>
                        <p className="text-muted-foreground text-sm leading-relaxed">
                          {tool.description}
                        </p>
                      </div>

                      {/* Arrow indicator */}
                      <div className="flex items-center gap-2 mt-6 text-sm font-medium text-primary group-hover:gap-3 transition-all">
                        <span>Open Tool</span>
                        <ArrowRight className="h-4 w-4" />
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>

            {/* Info Section */}
            <div className="mt-12 p-6 bg-muted/50 rounded-lg border">
              <div className="flex items-start gap-4">
                <Shield className="h-6 w-6 text-primary mt-1 flex-shrink-0" />
                <div>
                  <h3 className="font-semibold mb-2">Professional Forensic Analysis</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">
                    Our forensic tools combine advanced AI detection with traditional metadata analysis 
                    to provide comprehensive image verification. All analysis is performed securely and results 
                    are available in your dashboard.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
