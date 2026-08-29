from datetime import datetime, timezone, timedelta
from quantforge.risk.news_filter import MacroEvent, NewsRiskShield


def test_news_risk_shield_blocks_during_cpi_window():
    shield = NewsRiskShield(pre_event_blackout_minutes=15, post_event_blackout_minutes=15)
    
    # Scheduled CPI release at 12:30 UTC
    cpi_time = datetime(2026, 9, 10, 12, 30, tzinfo=timezone.utc)
    event = MacroEvent(
        title="US Core CPI (YoY)",
        country="US",
        currency="USD",
        impact="HIGH",
        scheduled_at_utc=cpi_time,
    )
    shield.update_calendar_events([event])

    # 1. 10 minutes before CPI -> Should be BLOCKED
    time_before = cpi_time - timedelta(minutes=10)
    blocked, reason = shield.is_news_blackout(time_before, currency="USD")
    assert blocked is True
    assert "High-Impact News Blackout" in reason

    # 2. 5 minutes after CPI -> Should be BLOCKED (settling window)
    time_after = cpi_time + timedelta(minutes=5)
    blocked, reason = shield.is_news_blackout(time_after, currency="USD")
    assert blocked is True

    # 3. 30 minutes before CPI -> Should be ALLOWED
    time_far_before = cpi_time - timedelta(minutes=30)
    blocked, reason = shield.is_news_blackout(time_far_before, currency="USD")
    assert blocked is False
    assert "Clear" in reason

    # 4. 20 minutes after CPI -> Should be ALLOWED
    time_far_after = cpi_time + timedelta(minutes=20)
    blocked, reason = shield.is_news_blackout(time_far_after, currency="USD")
    assert blocked is False


def test_news_risk_shield_spread_protection():
    shield = NewsRiskShield(max_allowed_spread_dollars=0.50)
    
    # Normal spread ($0.20 on Gold)
    safe, msg = shield.is_spread_safe(0.20)
    assert safe is True

    # High news spread spike ($1.80 on Gold during CPI)
    safe, msg = shield.is_spread_safe(1.80)
    assert safe is False
    assert "Spread Spike Protection" in msg
