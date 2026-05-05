import { LogIn } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useLocation } from "react-router-dom";

import { LanguageToggle } from "../components/LanguageToggle";
import { Notice } from "../components/Notice";
import { useAuth } from "../providers/AuthProvider";

export function LoginPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const { configured, session, signInWithGoogle } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || "/dashboard";

  if (session) {
    return <Navigate to={from} replace />;
  }

  const handleSignIn = async () => {
    setBusy(true);
    setError(null);
    try {
      await signInWithGoogle();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("errors.generic"));
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-neutral-100 px-4 py-6 text-neutral-950">
      <div className="mx-auto flex max-w-6xl justify-end">
        <LanguageToggle />
      </div>
      <main className="mx-auto mt-16 grid max-w-md gap-5 rounded-md border border-neutral-200 bg-white p-6 shadow-sm">
        <div>
          <div className="mb-4 grid size-11 place-items-center rounded-md bg-emerald-700 font-semibold text-white">
            A2
          </div>
          <h1 className="text-2xl font-semibold tracking-normal">{t("auth.title")}</h1>
          <p className="mt-2 text-sm text-neutral-600">{t("appSubtitle")}</p>
        </div>

        {!configured && (
          <Notice>
            <strong className="block text-neutral-900">{t("auth.missingConfig")}</strong>
            {t("auth.missingConfigBody")}
          </Notice>
        )}

        {error && <Notice tone="danger">{error}</Notice>}

        <button
          type="button"
          disabled={!configured || busy}
          onClick={() => void handleSignIn()}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-md bg-neutral-900 px-4 text-sm font-semibold text-white hover:bg-neutral-700 disabled:cursor-not-allowed disabled:bg-neutral-300"
        >
          <LogIn className="size-4" aria-hidden="true" />
          {busy ? t("auth.signingIn") : t("auth.google")}
        </button>
      </main>
    </div>
  );
}
