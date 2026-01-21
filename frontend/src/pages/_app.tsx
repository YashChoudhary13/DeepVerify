// pages/_app.tsx
import "../../styles/globals.css";
import { ThemeProvider } from "next-themes";
import type { AppProps } from "next/app";
import React from "react";
import { appWithTranslation } from "next-i18next";

// Query caching + UI providers
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/queryClient";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import PageTransition from "@/components/PageTransition";

function App({ Component, pageProps }: AppProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
        <TooltipProvider>
          <Toaster />
          <PageTransition>
            <Component {...pageProps} />
          </PageTransition>
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default appWithTranslation(App);
