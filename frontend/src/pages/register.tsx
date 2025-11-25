import { useState } from "react";
import { useRouter } from "next/router";
import Head from "next/head";
import Link from "next/link";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import { useTranslation } from "next-i18next";
import { register, login } from "@/lib/api";
import { ModeToggle } from "@/components/mode-toggle";

export async function getServerSideProps({ locale }: { locale: string }) {
  return {
    props: {
      ...(await serverSideTranslations(locale ?? "en", ["common"])),
    },
  };
}

export default function RegisterPage() {
  const router = useRouter();
  const { t, ready } = useTranslation("common");

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
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    // Validation
    if (password !== confirmPassword) {
      setError(getText("register.passwordsNoMatch", "Passwords do not match"));
      return;
    }

    if (password.length < 6) {
      setError(getText("register.passwordTooShort", "Password must be at least 6 characters"));
      return;
    }

    setLoading(true);

    try {
      // Register user
      await register({ username, email, password });

      // Auto-login after registration
      await login({ username, password });

      router.push("/indexloggedin");
    } catch (err: any) {
      setError(err.message || getText("register.registrationFailed", "Registration failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center relative">
      <div className="absolute top-4 right-4">
        <ModeToggle />
      </div>
      <Head>
        <title>Register — DeepVerify</title>
      </Head>

      <div className="bg-card rounded-xl shadow-lg p-8 w-full max-w-md border border-border">
        <div className="text-center mb-8">
          <div className="h-12 w-12 bg-primary text-primary-foreground font-bold rounded-md flex items-center justify-center mx-auto mb-4">
            D
          </div>
          <h1 className="text-2xl font-bold text-foreground">{getText("register.title", "Create Account")}</h1>
          <p className="text-muted-foreground mt-2">{getText("register.subtitle", "Sign up to get started")}</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && (
            <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="username" className="block text-sm font-medium text-foreground mb-2">
              {getText("register.username", "Username")}
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-4 py-2 bg-background border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-ring text-foreground placeholder:text-muted-foreground"
              placeholder={getText("register.usernamePlaceholder", "Choose a username")}
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-foreground mb-2">
              {getText("register.email", "Email")}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full px-4 py-2 bg-background border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-ring text-foreground placeholder:text-muted-foreground"
              placeholder={getText("register.emailPlaceholder", "Enter your email")}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-foreground mb-2">
              {getText("register.password", "Password")}
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="w-full px-4 py-2 bg-background border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-ring text-foreground placeholder:text-muted-foreground"
              placeholder={getText("register.passwordPlaceholder", "Create a password (min 6 characters)")}
            />
          </div>

          <div>
            <label htmlFor="confirmPassword" className="block text-sm font-medium text-foreground mb-2">
              {getText("register.confirmPassword", "Confirm Password")}
            </label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              className="w-full px-4 py-2 bg-background border border-input rounded-lg focus:ring-2 focus:ring-ring focus:border-ring text-foreground placeholder:text-muted-foreground"
              placeholder={getText("register.confirmPasswordPlaceholder", "Confirm your password")}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary text-primary-foreground py-2 px-4 rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {loading ? getText("register.creatingAccount", "Creating account...") : getText("register.createAccount", "Create Account")}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-muted-foreground">
            {getText("register.haveAccount", "Already have an account?")}{" "}
            <Link href="/login" className="text-primary hover:text-primary/90 font-medium">
              {getText("register.signIn", "Sign in")}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

