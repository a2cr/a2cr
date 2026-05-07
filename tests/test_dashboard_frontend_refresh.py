from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_dashboard_refresh_does_not_replace_required_data_with_empty_fallbacks():
    source = read("web/src/lib/api.ts")

    assert 'dashboardFetch<DashboardContext[]>("/api/dashboard/contexts", token).catch(() => [])' not in source
    assert 'dashboardFetch<DashboardStats>("/api/dashboard/stats", token).catch' not in source
    assert "DASHBOARD_GET_RETRY_DELAYS_MS" in source
    assert "isRetryableDashboardError" in source


def test_dashboard_refresh_keeps_last_successful_data_on_failure():
    source = read("web/src/pages/DashboardPage.tsx")
    i18n = read("web/src/i18n.ts")

    assert "dataRef.current = nextData" in source
    assert "errors.refreshFailedCached" in source
    assert "前回取得できた表示を維持しています" in i18n
