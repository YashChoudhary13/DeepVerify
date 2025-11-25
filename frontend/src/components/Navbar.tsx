// src/components/Navbar.tsx
"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/router";
import { useTranslation } from "next-i18next";

import { getAuthToken, getCurrentUser, logout as apiLogout } from "@/lib/api";

import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { Shield, LogOut, LayoutDashboard, Globe, Check, User as UserIcon, Settings } from "lucide-react";
import { ModeToggle } from "./mode-toggle";

const LANGUAGES = [
  { code: "en", name: "English", nativeName: "English" },
  { code: "es", name: "Spanish", nativeName: "Español" },
  { code: "fr", name: "French", nativeName: "Français" },
  { code: "de", name: "German", nativeName: "Deutsch" },
  { code: "hi", name: "Hindi", nativeName: "हिंदी" },
  { code: "zh", name: "Chinese", nativeName: "中文" },
  { code: "ja", name: "Japanese", nativeName: "日本語" },
  { code: "ar", name: "Arabic", nativeName: "العربية" },
];

interface User {
  firstName?: string | null;
  lastName?: string | null;
  email?: string | null;
  profileImageUrl?: string | null;
}

const AUTH_USER_KEY = "auth_user";
const AUTH_TOKEN_KEY = "auth_token"; // keep in sync with lib/api.ts if key name differs

export default function Navbar() {
  const router = useRouter();
  const { t, i18n } = useTranslation("common");
  const [currentLocale, setCurrentLocale] = useState<string>(router.locale || "en");

  // Initial state must match server (false/null) to avoid hydration mismatch
  const [signedIn, setSignedIn] = useState<boolean>(false);
  const [user, setUser] = useState<User | null>(null);

  // Effect to sync with localStorage on client mount
  useEffect(() => {
    try {
      const token = getAuthToken();
      setSignedIn(!!token);

      const rawUser = localStorage.getItem(AUTH_USER_KEY);
      if (rawUser) {
        setUser(JSON.parse(rawUser));
      }
    } catch (e) {
      console.error("Auth init error", e);
    }
  }, []);

  const [isFetchingUser, setIsFetchingUser] = useState<boolean>(false);

  // Fetch fresh user in background without blocking the UI
  const fetchUserBackground = useCallback(async (strictOnAuthFail = false) => {
    const token = getAuthToken();
    setSignedIn(!!token);

    if (!token) {
      // no token -> signed out
      setUser(null);
      try {
        localStorage.removeItem(AUTH_USER_KEY);
      } catch { }
      return;
    }

    setIsFetchingUser(true);
    try {
      const u = await getCurrentUser();
      const normalized: User = {
        firstName: (u as any).firstName ?? (u as any).first_name ?? null,
        lastName: (u as any).lastName ?? (u as any).last_name ?? null,
        email: (u as any).email ?? null,
        profileImageUrl:
          (u as any).profileImageUrl ?? (u as any).profile_image_url ?? null,
      };

      setUser(normalized);
      // update cached user for instant future renders
      try {
        localStorage.setItem(AUTH_USER_KEY, JSON.stringify(normalized));
      } catch { }
    } catch (err: any) {
      if (strictOnAuthFail && /401|Unauthorized/i.test(String(err?.message ?? ""))) {
        setSignedIn(false);
        setUser(null);
        try {
          localStorage.removeItem(AUTH_USER_KEY);
          localStorage.removeItem(AUTH_TOKEN_KEY);
        } catch { }
      } else {
        setUser(null);
      }
    } finally {
      setIsFetchingUser(false);
    }
  }, []);

  // Stable handler for events
  useEffect(() => {
    // run once on mount to ensure background fetch runs and keeps things fresh
    fetchUserBackground();

    const onAuthChange = (e: Event) => {
      fetchUserBackground(true);
    };

    const onStorage = (e: StorageEvent) => {
      if (!e.key) {
        fetchUserBackground(true);
        return;
      }
      if (e.key === AUTH_TOKEN_KEY || e.key === AUTH_USER_KEY) {
        fetchUserBackground(true);
      }
    };

    const onRoute = () => {
      fetchUserBackground();
    };

    window.addEventListener("auth-change", onAuthChange);
    window.addEventListener("storage", onStorage);
    (router.events as any)?.on?.("routeChangeComplete", onRoute);

    return () => {
      window.removeEventListener("auth-change", onAuthChange);
      window.removeEventListener("storage", onStorage);
      (router.events as any)?.off?.("routeChangeComplete", onRoute);
    };
  }, [fetchUserBackground, router.events]);

  const handleLogout = async () => {
    try {
      await apiLogout();
    } catch {
      // ignore backend logout errors — still clear client state
    } finally {
      try {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        localStorage.removeItem(AUTH_USER_KEY);
      } catch { }
      window.dispatchEvent(new CustomEvent("auth-change", { detail: { source: "logout" } }));
      setSignedIn(false);
      setUser(null);
      router.push("/");
    }
  };

  // Update locale when router locale changes
  useEffect(() => {
    if (router.locale) {
      setCurrentLocale(router.locale);
    }
  }, [router.locale]);

  const handleLanguageChange = async (locale: string) => {
    setCurrentLocale(locale);
    // Save to localStorage
    if (typeof window !== "undefined") {
      localStorage.setItem("preferred_language", locale);
    }
    // Change language using router - this will trigger getServerSideProps with new locale
    try {
      await router.push(router.asPath, router.asPath, { locale, scroll: false });
      // Wait a bit for router to update, then reload
      setTimeout(() => {
        window.location.reload();
      }, 200);
    } catch (error) {
      console.error("Language change error:", error);
      // Fallback: direct reload with locale in URL
      window.location.href = `/${locale}${router.asPath}`;
    }
  };

  // Small UI helpers
  const displayName = user
    ? user.firstName && user.lastName
      ? `${user.firstName} ${user.lastName}`
      : user.firstName ?? user.email ?? "User"
    : "";

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-sm border-b">
      <nav className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link href={signedIn ? "/indexloggedin" : "/"} className="flex items-center gap-2 cursor-pointer">
          <Shield className="h-6 w-6 text-primary" />
          <span className="text-xl font-bold tracking-tight">DeepVerify</span>
        </Link>

        <div className="flex items-center gap-4">
          {/* Language Selector Dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-2">
                <Globe className="h-4 w-4" />
                <span className="hidden sm:inline">
                  {LANGUAGES.find(l => l.code === currentLocale)?.nativeName || "English"}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              {LANGUAGES.map((lang) => (
                <DropdownMenuItem
                  key={lang.code}
                  onClick={() => handleLanguageChange(lang.code)}
                  className="flex items-center justify-between cursor-pointer"
                >
                  <div className="flex flex-col">
                    <span className="font-medium">{lang.nativeName}</span>
                    <span className="text-xs text-muted-foreground">{lang.name}</span>
                  </div>
                  {currentLocale === lang.code && (
                    <Check className="h-4 w-4 text-primary" />
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <ModeToggle />

          {signedIn ? (
            <>
              <Link href="/dashboard">
                <span className="hover:text-indigo-600 cursor-pointer">{t("navbar.dashboard")}</span>
              </Link>

              <Link href="/membership">
                <span className="hover:text-indigo-600 cursor-pointer">{t("navbar.membership")}</span>
              </Link>

              <Link href="/support">
                <span className="hover:text-indigo-600 cursor-pointer">{t("navbar.support")}</span>
              </Link>

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="relative h-8 w-8 rounded-full">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user?.profileImageUrl || ""} alt={displayName} />
                      <AvatarFallback>{displayName.charAt(0).toUpperCase()}</AvatarFallback>
                    </Avatar>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="w-56" align="end" forceMount>
                  <div className="flex items-center justify-start gap-2 p-2">
                    <div className="flex flex-col space-y-1 leading-none">
                      <p className="font-medium">{displayName}</p>
                      <p className="w-[200px] truncate text-sm text-muted-foreground">
                        {user?.email}
                      </p>
                    </div>
                  </div>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link href="/settings" className="cursor-pointer w-full flex items-center">
                      <Settings className="mr-2 h-4 w-4" />
                      <span>{t("navbar.settings", "Profile Settings")}</span>
                    </Link>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="cursor-pointer text-red-600 focus:text-red-600"
                    onClick={handleLogout}
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>{t("navbar.signOut")}</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </>
          ) : (
            <>
              <Button asChild data-testid="button-signin">
                <Link href="/login">{t("navbar.signIn")}</Link>
              </Button>

              <Link
                href="/register"
                className="px-4 py-2 bg-slate-100 text-slate-700 rounded hover:bg-slate-200"
              >
                {t("navbar.signUp")}
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
