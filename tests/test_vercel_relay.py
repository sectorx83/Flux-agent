from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vercel_dashboard_uses_same_origin_relay():
    dashboard = (ROOT / "index.html").read_text(encoding="utf-8")
    assert 'fetch("/api"+path' in dashboard


def test_vercel_relay_forwards_parsed_json_body():
    relay = (ROOT / "api" / "[...path].js").read_text(encoding="utf-8")
    assert "req.body !== undefined" in relay
    assert "JSON.stringify(req.body)" in relay
    assert 'process.env.FLUX_API_URL' in relay
