import { ArrowLeft, Check, Database, Gauge, ScrollText, WalletCards } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { LanguageToggle } from "../components/LanguageToggle";

function PlanColumn({
  name,
  price,
  rows,
  badge,
  note,
  comingSoon
}: {
  name: string;
  price: string;
  rows: Array<[string, string]>;
  badge?: string;
  note?: string;
  comingSoon?: boolean;
}) {
  return (
    <section className={`rounded-md border p-5 ${comingSoon ? "border-neutral-200 bg-neutral-50" : "border-neutral-200 bg-white"}`}>
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h2 className={`text-xl font-semibold ${comingSoon ? "text-neutral-400" : ""}`}>{name}</h2>
            {badge && (
              <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${comingSoon ? "bg-emerald-100 text-emerald-700" : "bg-neutral-100 text-neutral-500"}`}>{badge}</span>
            )}
          </div>
          <div className={`mt-1 text-2xl font-semibold ${comingSoon ? "text-neutral-400" : "text-neutral-900"}`}>{price}</div>
          {note && <p className={`mt-1 text-sm ${comingSoon ? "text-neutral-400" : "text-neutral-600"}`}>{note}</p>}
        </div>
        <WalletCards className={`size-5 ${comingSoon ? "text-neutral-300" : "text-neutral-400"}`} aria-hidden="true" />
      </div>
      <dl className="grid gap-3 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="grid gap-1 border-t border-neutral-100 pt-3 sm:grid-cols-[minmax(0,1fr)_minmax(8rem,1.2fr)] sm:gap-3">
            <dt className={comingSoon ? "text-neutral-400" : "text-neutral-500"}>{label}</dt>
            <dd className={`flex items-start gap-2 font-medium ${comingSoon ? "text-neutral-400" : "text-neutral-900"}`}>
              <Check className={`mt-0.5 size-4 shrink-0 ${comingSoon ? "text-neutral-300" : "text-emerald-700"}`} aria-hidden="true" />
              <span>{value}</span>
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function PricingPage() {
  const { t } = useTranslation();
  const freeRows: Array<[string, string]> = [
    [t("pricing.slots"), "5"],
    [t("pricing.retention"), "15m / 30m / 1h / 3h / 6h / 12h / 24h"],
    [t("pricing.body"), "24 KB"],
    [t("pricing.workStash"), "256 KB"],
    [t("pricing.handoff"), t("pricing.focusedHandoff")],
    [t("pricing.workBatonSaves"), "100 / hour"],
    [t("pricing.workBatonLoads"), "200 / hour"],
    [t("pricing.workStashWrites"), "200 / hour"],
    [t("pricing.workStashReads"), "300 / hour"],
    [t("pricing.logs"), "24h"],
    [t("pricing.workthreads"), t("pricing.notIncluded")]
  ];
  const proRows: Array<[string, string]> = [
    [t("pricing.slots"), "50"],
    [t("pricing.retention"), "15m / 30m / 1h / 3h / 6h / 12h / 24h / 3d / 7d / 10d / 14d / 30d"],
    [t("pricing.body"), "64 KB"],
    [t("pricing.workStash"), "1,024 KB"],
    [t("pricing.handoff"), t("pricing.richerHandoff")],
    [t("pricing.workBatonSaves"), "300 / hour"],
    [t("pricing.workBatonLoads"), "600 / hour"],
    [t("pricing.workStashWrites"), "400 / hour"],
    [t("pricing.workStashReads"), "800 / hour"],
    [t("pricing.logs"), "30d"],
    [t("pricing.workthreads"), t("pricing.planned")]
  ];
  const explainers = [
    {
      icon: ScrollText,
      title: t("pricing.explainWorkBatonTitle"),
      body: t("pricing.explainWorkBatonBody")
    },
    {
      icon: Database,
      title: t("pricing.explainWorkStashTitle"),
      body: t("pricing.explainWorkStashBody")
    },
    {
      icon: Gauge,
      title: t("pricing.explainRateTitle"),
      body: t("pricing.explainRateBody")
    }
  ];
  const notes = [t("pricing.notePublicPreview"), t("pricing.noteProPlanned"), t("pricing.noteNoSecrets")];

  return (
    <div className="min-h-screen bg-neutral-100 px-4 py-6 text-neutral-950">
      <header className="mx-auto flex max-w-6xl items-center justify-between">
        <Link
          to="/dashboard"
          className="inline-flex items-center gap-2 rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-100"
        >
          <ArrowLeft className="size-4" aria-hidden="true" />
          {t("nav.dashboard")}
        </Link>
        <LanguageToggle />
      </header>
      <main className="mx-auto mt-8 max-w-6xl">
        <h1 className="text-2xl font-semibold tracking-normal">{t("pricing.title")}</h1>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">{t("pricing.subtitle")}</p>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <PlanColumn name={t("pricing.freeName")} price={t("pricing.freePrice")} rows={freeRows} note={t("pricing.freeNote")} />
          <PlanColumn
            name={t("pricing.proName")}
            price={t("pricing.proPrice")}
            rows={proRows}
            badge={t("pricing.comingSoon")}
            note={t("pricing.proNote")}
            comingSoon
          />
        </div>
        <section className="mt-8 border-t border-neutral-200 pt-6">
          <h2 className="text-lg font-semibold tracking-normal">{t("pricing.explainerTitle")}</h2>
          <div className="mt-4 grid gap-5 md:grid-cols-3">
            {explainers.map(({ icon: Icon, title, body }) => (
              <article key={title} className="border-l border-neutral-300 pl-4">
                <Icon className="mb-3 size-5 text-emerald-700" aria-hidden="true" />
                <h3 className="text-sm font-semibold text-neutral-950">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-neutral-600">{body}</p>
              </article>
            ))}
          </div>
        </section>
        <section className="mt-8 border-t border-neutral-200 pt-6">
          <h2 className="text-lg font-semibold tracking-normal">{t("pricing.notesTitle")}</h2>
          <ul className="mt-3 grid gap-2 text-sm leading-6 text-neutral-600">
            {notes.map((note) => (
              <li key={note} className="flex gap-2">
                <Check className="mt-1 size-4 shrink-0 text-emerald-700" aria-hidden="true" />
                <span>{note}</span>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}
