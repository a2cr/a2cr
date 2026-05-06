import { ArrowRight, CheckCircle2, LayoutDashboard, LogIn, PlugZap, TimerReset } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { LanguageToggle } from "../components/LanguageToggle";
import { useAuth } from "../providers/AuthProvider";

const points = [
  { icon: TimerReset, key: "checkpoints" },
  { icon: PlugZap, key: "mcp" },
  { icon: CheckCircle2, key: "inspection" }
];

const surfaces = [
  { label: "Dashboard", bodyKey: "dashboard" },
  { label: "API", bodyKey: "api" },
  { label: "MCP", bodyKey: "mcp" }
];

export function TopPage() {
  const { t } = useTranslation();
  const { session } = useAuth();
  const primaryTo = session ? "/dashboard" : "/login";
  const primaryLabel = session ? t("top.ctaDashboard") : t("auth.google");
  const PrimaryIcon = session ? LayoutDashboard : LogIn;

  return (
    <div className="min-h-screen bg-neutral-950 text-white">
      <header className="relative z-10 mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link to="/" className="flex items-center gap-3">
          <img src="/brand/a2cr-logo.png" alt="A2CR" className="h-8 w-auto object-contain" />
          <span className="sr-only">A2CR</span>
        </Link>
        <div className="flex flex-wrap items-center justify-end gap-2">
          <Link
            to="/guide"
            className="rounded-md px-3 py-2 text-sm font-medium text-neutral-200 hover:bg-white/10"
          >
            {t("nav.guide")}
          </Link>
          <Link
            to="/pricing"
            className="rounded-md px-3 py-2 text-sm font-medium text-neutral-200 hover:bg-white/10"
          >
            {t("nav.pricing")}
          </Link>
          <LanguageToggle />
        </div>
      </header>

      <main>
        <section className="mx-auto grid min-h-[calc(100vh-124px)] max-w-7xl content-center gap-8 px-4 pb-14 pt-8 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
          <div className="max-w-3xl">
            <img src="/brand/a2cr-logo.png" alt="A2CR" className="mb-7 w-full max-w-xl object-contain" />
            <h1 className="max-w-4xl text-4xl font-semibold tracking-normal text-white sm:text-5xl lg:text-6xl">
              {t("appSubtitle")}
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-300 sm:text-lg">
              {t("top.heroBody")}
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to={primaryTo}
                className="inline-flex h-11 items-center gap-2 rounded-md bg-emerald-500 px-4 text-sm font-semibold text-neutral-950 hover:bg-emerald-400"
              >
                <PrimaryIcon className="size-4" aria-hidden="true" />
                {primaryLabel}
              </Link>
              <Link
                to="/pricing"
                className="inline-flex h-11 items-center gap-2 rounded-md border border-white/20 px-4 text-sm font-semibold text-white hover:bg-white/10"
              >
                {t("top.ctaPricing")}
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
            </div>
          </div>

          <div className="grid gap-3">
            {points.map(({ icon: Icon, key }) => (
              <article key={key} className="rounded-md border border-white/15 bg-white/[0.06] p-4">
                <div className="flex items-start gap-3">
                  <div className="grid size-9 shrink-0 place-items-center rounded-md bg-emerald-400 text-neutral-950">
                    <Icon className="size-4" aria-hidden="true" />
                  </div>
                  <div>
                    <h2 className="text-base font-semibold text-white">{t(`top.points.${key}.title`)}</h2>
                    <p className="mt-1 text-sm leading-6 text-neutral-300">{t(`top.points.${key}.body`)}</p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="bg-neutral-100 px-4 py-12 text-neutral-950 sm:px-6">
          <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
            <div>
              <h2 className="text-2xl font-semibold tracking-normal">{t("top.originTitle")}</h2>
              <p className="mt-3 max-w-xl text-sm leading-6 text-neutral-600">
                {t("top.originBody")}
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              {surfaces.map(({ label, bodyKey }) => (
                <div key={label} className="rounded-md border border-neutral-200 bg-white p-4">
                  <div className="text-sm font-semibold text-emerald-700">{label}</div>
                  <div className="mt-2 text-sm text-neutral-600">{t(`top.surfaces.${bodyKey}`)}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
