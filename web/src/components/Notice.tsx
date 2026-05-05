import type { ReactNode } from "react";

export function Notice({
  tone = "neutral",
  children
}: {
  tone?: "neutral" | "danger" | "success";
  children: ReactNode;
}) {
  const classes = {
    neutral: "border-neutral-300 bg-white text-neutral-700",
    danger: "border-rose-300 bg-rose-50 text-rose-800",
    success: "border-emerald-300 bg-emerald-50 text-emerald-800"
  };

  return <div className={`rounded-md border px-3 py-2 text-sm ${classes[tone]}`}>{children}</div>;
}
