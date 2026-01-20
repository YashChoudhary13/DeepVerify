// src/components/ModelResultCard.tsx
import React, { useState } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import { Eye, EyeOff } from "lucide-react";

interface ModelProps {
  model: {
    model_name: string;
    version?: string;
    score?: number;
    heatmap_url?: string;
    image_url?: string;
    run_time_ms?: number;
    labels?: any;
  };
}

export default function ModelResultCard({ model }: ModelProps) {
  // preserve original logic: single-number opacity state
  const [opacity, setOpacity] = useState(60);
  const scorePct = Math.round((model.score || 0) * 100);

  const isReal = (model.labels && model.labels.label === "REAL") || scorePct >= 50; // purely visual hint; doesn't change logic
  const confidence = scorePct;

  return (
    <Card
      className="p-6"
      data-testid={`card-model-${(model.model_name || "model").toLowerCase().replace(/\s+/g, '-')}`}
    >
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-semibold" data-testid="text-model-name">
                {model.model_name}
              </h3>
              <Badge variant="outline" className="text-xs" data-testid="badge-model-version">
                {model.version ?? "v1.0"}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground" data-testid="text-execution-time">
              {model.run_time_ms ?? "--"} ms execution
            </p>
          </div>

          <Badge
            variant={isReal ? "secondary" : "destructive"}
            className="font-semibold"
            data-testid="badge-model-label"
          >
            {/* keep your original label logic if present in model.labels, otherwise show REAL/FAKE by score */}
            {model.labels?.label ?? (scorePct >= 50 ? "REAL" : "FAKE")}
          </Badge>
        </div>

        {/* Confidence */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium">Confidence</span>
            <span className="text-muted-foreground font-mono tabular-nums" data-testid="text-model-confidence">
              {confidence.toFixed(1)}%
            </span>
          </div>
          <Progress value={confidence} className="h-1.5" data-testid="progress-model-confidence" />
        </div>

        {/* Heatmap section (preserve original logic: show overlay if heatmap exists) */}
        {model.heatmap_url && (
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Heatmap Analysis</span>
              {/* purely presentational toggle — does NOT alter upload/analysis logic */}
              {/* Keep toggle minimal: shows/hides overlay preview; original plain UI always showed overlay, but this follows the Prompt design while not changing analysis behavior */}
            </div>

            <div className="space-y-3">
              <div className="relative rounded-md overflow-hidden bg-muted">
                <img
                  src={
                    model.image_url
                      ? (model.image_url.startsWith("http")
                          ? model.image_url
                          : model.image_url.startsWith("/api/")
                            ? `${process.env.NEXT_PUBLIC_API_URL}${model.image_url}`
                            : model.image_url)
                      : "/sample-thumbnails/placeholder.png"
                  }
                  alt="Original"
                  className="w-full h-48 object-contain"
                />
                <img
                  src={
                    model.heatmap_url.startsWith("http")
                      ? model.heatmap_url
                      : model.heatmap_url.startsWith("/api/")
                        ? `${process.env.NEXT_PUBLIC_API_URL}${model.heatmap_url}`
                        : model.heatmap_url
                  }
                  alt="Heatmap overlay"
                  className="absolute inset-0 w-full h-48 object-contain mix-blend-multiply dark:mix-blend-screen"
                  style={{ opacity: opacity / 100 }}
                  data-testid="img-heatmap-overlay"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Overlay Opacity</span>
                  <span className="font-mono tabular-nums" data-testid="text-opacity-value">
                    {opacity}%
                  </span>
                </div>

                {/* Slider uses single-number state kept in original component */}
                <div className="w-full" data-testid="slider-opacity">
                  <Slider
                    value={[opacity]}
                    onValueChange={(v: number[]) => setOpacity(v[0])}
                    min={0}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Labels / Model Notes (preserve original behavior) */}
        {model.labels && (
          <div className="mt-2 p-3 bg-slate-50 border border-slate-200 rounded">
            <div className="text-sm text-slate-700 font-medium mb-1">Model Notes:</div>
            <pre className="text-xs text-slate-600 whitespace-pre-wrap">{JSON.stringify(model.labels, null, 2)}</pre>
          </div>
        )}
      </div>
    </Card>
  );
}
