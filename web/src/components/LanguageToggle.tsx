import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";

import { setAppLanguage } from "../i18n";

export function LanguageToggle() {
  const { i18n } = useTranslation();
  const current = i18n.language.startsWith("ja") ? "ja" : "en";

  return (
    <div className="inline-flex items-center gap-1 rounded-md border border-neutral-300 bg-white p-1 text-sm">
      <Languages className="ml-1 size-4 text-neutral-500" aria-hidden="true" />
      {(["en", "ja"] as const).map((language) => (
        <button
          key={language}
          type="button"
          onClick={() => void setAppLanguage(language)}
          className={`rounded px-2.5 py-1 font-medium ${
            current === language
              ? "bg-neutral-900 text-white"
              : "text-neutral-600 hover:bg-neutral-100"
          }`}
        >
          {language.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
