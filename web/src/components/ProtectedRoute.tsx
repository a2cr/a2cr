import { Navigate, useLocation } from "react-router-dom";
import { Loader2 } from "lucide-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../providers/AuthProvider";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const location = useLocation();
  const { loading, session } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-neutral-100 text-neutral-700">
        <Loader2 className="mr-3 size-5 animate-spin" aria-hidden="true" />
        <span>{t("common.loading")}</span>
      </div>
    );
  }

  if (!session) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}
