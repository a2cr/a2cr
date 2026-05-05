import { Check, Copy } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export function CopyButton({
  value,
  label,
  compact = false
}: {
  value: string;
  label?: string;
  compact?: boolean;
}) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  const Icon = copied ? Check : Copy;
  return (
    <button
      type="button"
      title={label || t("common.copy")}
      onClick={() => void copy()}
      className={`inline-flex items-center justify-center gap-2 rounded-md border border-neutral-300 bg-white font-medium text-neutral-700 hover:bg-neutral-100 ${
        compact ? "size-9 p-0" : "px-3 py-2 text-sm"
      }`}
    >
      <Icon className="size-4" aria-hidden="true" />
      {!compact && <span>{copied ? t("common.copied") : label || t("common.copy")}</span>}
    </button>
  );
}
