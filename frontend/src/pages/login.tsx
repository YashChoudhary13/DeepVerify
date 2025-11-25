import { useState } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import { login } from "@/lib/api";
import { ModeToggle } from "@/components/mode-toggle";

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

export default function LoginPage() {
  const router = useRouter();
  const { t, ready } = useTranslation("common");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const resp = await login({ username, password });
      console.debug("login: token set ->", localStorage.getItem("auth_token"));
      window.dispatchEvent(new CustomEvent("auth-change", { detail: { source: "login" } }));
      router.push("/indexloggedin");
    } catch (err: any) {
      setError(err.message || getText("login.loginFailed", "Login failed"));
    } finally {
      setLoading(false);
    }
  };

  // Helper to safely get translations
  const getText = (key: string, fallback: string) => {
    if (!ready) return fallback;
    try {
      const translated = t(key);
      return translated === key ? fallback : translated;
    } catch {
      return fallback;
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center relative">
      <div className="absolute top-4 right-4">
        <ModeToggle />
      </div>
      <Head>
        <title>Login — DeepVerify</title>
      </Head>

      <div className="bg-card rounded-xl shadow-lg p-8 w-full max-w-md border border-border">
        <div className="text-center mb-8">
          <div className="h-12 w-12 bg-primary text-primary-foreground font-bold rounded-md flex items-center justify-center mx-auto mb-4">
            D
          </div>
          <h1 className="text-2xl font-bold text-foreground">{getText("login.title", "Welcome Back")}</h1>
          <p className="text-muted-foreground mt-2">{getText("login.subtitle", "Sign in to your account")}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-foreground mb-2">
              {getText("login.username", "Username")}
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-4 py-2 bg-background border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-ring text-foreground placeholder:text-muted-foreground"
              placeholder={getText("login.usernamePlaceholder", "Enter your username")}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-foreground mb-2">
              {getText("login.password", "Password")}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2 bg-background border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-ring text-foreground placeholder:text-muted-foreground"
              placeholder={getText("login.passwordPlaceholder", "Enter your password")}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {loading ? getText("login.signingIn", "Signing in...") : getText("login.signIn", "Sign In")}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-muted-foreground">
            {getText("login.noAccount", "Don't have an account?")}{" "}
            <Link href="/register" className="text-primary hover:text-primary/90 font-medium">
              {getText("login.createOne", "Create one")}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

