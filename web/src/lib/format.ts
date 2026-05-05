export const FREE_RETENTION_SECONDS = [900, 1800, 3600, 10800, 21600, 43200, 86400];
export const PRO_RETENTION_SECONDS = [
  900,
  1800,
  3600,
  10800,
  21600,
  43200,
  86400,
  259200,
  604800,
  864000,
  1209600,
  2592000
];

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat().format(value);
}

export function formatDateTime(value: string | null | undefined, timezone: string): string {
  if (!value) {
    return "-";
  }
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: timezone || "UTC"
    }).format(new Date(value));
  } catch {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "UTC"
    }).format(new Date(value));
  }
}

export function retentionLabel(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d`;
}

export function serviceUrl(): string {
  const configured = import.meta.env.VITE_A2CR_SERVICE_URL?.trim();
  if (configured) {
    return configured;
  }
  return `${window.location.origin}/mcp`;
}
