"""Regression checks for browser detail presentation."""

from z0.api.web_dashboard import PAGE


def test_browser_uses_local_dates_and_handles_missing_timestamps():
    assert "function formattedTime(value)" in PAGE
    assert "new Intl.DateTimeFormat(undefined" in PAGE
    assert "timeZoneName:'short'" in PAGE
    assert "Number.isNaN(date.getTime())" in PAGE
    assert "if(!value)return 'Not recorded'" in PAGE


def test_details_distinguish_discovery_from_manual_monitoring():
    assert "Device identity &amp; discovery" in PAGE
    assert "Inventory observations are not live availability tests." in PAGE
    assert "Verified availability checks" in PAGE
    assert "Saved results from manually initiated ICMP probes." in PAGE
    assert "Recorded real transitions" in PAGE


def test_detail_fields_and_event_rows_are_display_only():
    assert "function fieldValue(value)" in PAGE
    assert "'Not reported'" in PAGE
    assert "'First seen':formattedTime(d.first_seen)" in PAGE
    assert "'Last observed':formattedTime(d.last_observed)" in PAGE
    assert "e=>formattedTime(e.timestamp)" in PAGE
    assert "textContent" in PAGE
    assert "innerHTML" not in PAGE
    assert "fetch('/api/network/device?mac='" in PAGE
