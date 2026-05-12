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


def test_dashboard_tokens_saved_has_explanatory_tooltip():
    source = read("web/src/pages/DashboardPage.tsx")
    i18n = read("web/src/i18n.ts")

    assert "CircleHelp" in source
    assert 'helpText={t("dashboard.tokensSavedHelp")}' in source
    assert "group-hover:block" in source
    assert "元の会話量の推定値" in i18n
    assert "Saves without original_length are not calculated" in i18n


def test_slot_card_shows_saved_tokens_against_original_estimate():
    source = read("web/src/pages/DashboardPage.tsx")

    assert "tokenReductionLabel(item)" in source
    assert "item.compressed_tokens + item.saved_tokens" in source
    assert "←" in source


def test_slot_card_shows_size_against_plan_limit():
    source = read("web/src/pages/DashboardPage.tsx")
    pricing = read("web/src/pages/PricingPage.tsx")

    assert "sizeLimitLabel(item.size_bytes, maxBodyBytes)" in source
    assert "plan === \"pro\" ? 64 * 1024 : 24 * 1024" in source
    assert '"24 KB"' in pricing
    assert '"64 KB"' in pricing
    assert '"256 KB"' in pricing
    assert '"1,024 KB"' in pricing


def test_pricing_copy_uses_planned_eight_dollar_pro_price():
    i18n = read("web/src/i18n.ts")

    assert 'proPrice: "$8 / month"' in i18n
    assert 'proPrice: "$8 / 月"' in i18n
    assert "$5 / month" not in i18n
    assert "$5 / 月" not in i18n


def test_access_log_table_uses_slot_numbers_and_badges():
    source = read("web/src/pages/DashboardPage.tsx")
    i18n = read("web/src/i18n.ts")

    assert "accessLogSlotLabel(item, data?.contexts || [])" in source
    assert 't("common.slotNumber")' in source
    assert "slotNumber: \"スロット番号\"" in i18n
    assert "candidate.slot_name === item.slot_name" in source
    assert "`Slot ${context.slot_number}`" in source
    assert "clientBadgeClass(item.client_type)" in source
    assert "resultBadgeClass(item.result)" in source
    assert "bg-emerald-100 text-emerald-800" in source
    assert "bg-rose-100 text-rose-800" in source
    assert "Claude Code" in source
    assert "Codex" in source


def test_dashboard_active_slots_show_used_over_limit():
    source = read("web/src/pages/DashboardPage.tsx")
    types = read("web/src/lib/types.ts")

    assert "active_slot_limit: number" in types
    assert "slotUsageLabel(data?.stats)" in source
    assert "stats?.active_slot_limit" in source
    assert "`${formatNumber(used)}/${formatNumber(limit)}`" in source
