import { LayoutDashboard, LogOut, Settings, WalletCards } from "lucide-react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { LanguageToggle } from "./LanguageToggle";
import { useAuth } from "../providers/AuthProvider";

const navItems = [
  { to: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
  { to: "/settings", labelKey: "nav.settings", icon: Settings },
  { to: "/pricing", labelKey: "nav.pricing", icon: WalletCards }
];

export function AppShell({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { signOut, user } = useAuth();

  const handleSignOut = async () => {
    await signOut();
    navigate("/login", { replace: true });
  };

  return (
    <div className="min-h-screen bg-neutral-100 text-neutral-950">
      <header className="border-b border-neutral-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6">
          <Link to="/">
            <img src="/brand/a2cr-logo-v2.png" alt="A2CR" className="h-[168px] w-auto object-contain" />
          </Link>
          <div className="flex items-center gap-2">
            <LanguageToggle />
            <button
              type="button"
              onClick={() => void handleSignOut()}
              title={t("nav.signOut")}
              className="inline-flex size-9 items-center justify-center rounded-md border border-neutral-300 bg-white text-neutral-600 hover:bg-neutral-100"
            >
              <LogOut className="size-4" aria-hidden="true" />
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-4 py-5 sm:px-6 lg:grid-cols-[220px_1fr]">
        <aside className="lg:sticky lg:top-5 lg:self-start">
          <nav className="grid gap-1 rounded-md border border-neutral-200 bg-white p-2">
            {navItems.map(({ to, labelKey, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium ${
                    isActive
                      ? "bg-emerald-700 text-white"
                      : "text-neutral-700 hover:bg-neutral-100"
                  }`
                }
              >
                <Icon className="size-4" aria-hidden="true" />
                <span>{t(labelKey)}</span>
              </NavLink>
            ))}
          </nav>
          <div className="mt-3 truncate rounded-md border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-500">
            {user?.email || user?.id}
          </div>
        </aside>

        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}
