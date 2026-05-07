import { ArrowLeft, Check, WalletCards } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { LanguageToggle } from "../components/LanguageToggle";

function PlanColumn({
  name,
  price,
  rows
}: {
  name: string;
  price: string;
  rows: Array<[string, string]>;
}) {
  return (
    <section className="rounded-md border border-neutral-200 bg-white p-5">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">{name}</h2>
          <div className="mt-1 text-2xl font-semibold">{price}</div>
        </div>
        <WalletCards className="size-5 text-emerald-700" aria-hidden="true" />
      </div>
      <dl className="grid gap-3 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="grid grid-cols-[1fr_1.2fr] gap-3 border-t border-neutral-100 pt-3">
            <dt className="text-neutral-500">{label}</dt>
            <dd className="flex items-start gap-2 font-medium text-neutral-900">
              <Check className="mt-0.5 size-4 shrink-0 text-emerald-700" aria-hidden="true" />
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
    [t("pricing.slots"), "3"],
    [t("pricing.retention"), "15m / 30m / 1h / 3h / 6h / 12h / 24h"],
    [t("pricing.body"), "24KB"],
    [t("pricing.detail"), t("common.compact")],
    [t("pricing.saves"), "100 / hour"],
    [t("pricing.loads"), "300 / hour"],
    [t("pricing.logs"), "24h"],
    [t("pricing.workthreads"), t("pricing.notIncluded")]
  ];
  const proRows: Array<[string, string]> = [
    [t("pricing.slots"), "100"],
    [t("pricing.retention"), "15m / 30m / 1h / 3h / 6h / 12h / 24h / 3d / 7d / 10d / 14d / 30d"],
    [t("pricing.body"), "64KB"],
    [t("pricing.detail"), "Compact / Detailed"],
    [t("pricing.saves"), "1,000 / hour"],
    [t("pricing.loads"), "3,000 / hour"],
    [t("pricing.logs"), "30d"],
    [t("pricing.workthreads"), t("pricing.planned")]
  ];

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
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <PlanColumn name={t("pricing.freeName")} price={t("pricing.freePrice")} rows={freeRows} />
          <PlanColumn name={t("pricing.proName")} price={t("pricing.proPrice")} rows={proRows} />
        </div>
      </main>
    </div>
  );
}
