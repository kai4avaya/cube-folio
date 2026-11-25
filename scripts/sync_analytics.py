#!/usr/bin/env python3
"""
Syncs read-only GA4 metrics for Kai Portfolio (properties/565841989, G-NVX0XJGFFL)
into analytics/data.json for https://cube.kaik.space/analytics/.

Auto-discovers ANY new site/hostname/path sending hits to G-NVX0XJGFFL and merges
them cleanly with the known portfolio sites from index.html.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "565841989")
MEASUREMENT_ID = "G-NVX0XJGFFL"
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PATH = os.path.join(REPO_ROOT, "analytics", "data.json")
DEFAULT_CREDS = os.path.expanduser("~/.config/google-analytics/efbrain1-f83ec4b01b19.json")


def normalize_site_key(host: str, path: str) -> tuple[str, str]:
    """Group GA4 hostName + pagePath into a clean canonical site key and launch URL."""
    host = (host or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    path = (path or "/").strip()
    if not path.startswith("/"):
        path = "/" + path

    # For github.io user pages, each project lives under its first path segment (/<repo>/)
    if host.endswith(".github.io"):
        segs = [s for s in path.split("/") if s]
        if segs:
            site_key = f"{host}/{segs[0]}"
            url = f"https://{host}/{segs[0]}/"
            return site_key, url
        return host, f"https://{host}/"

    # Dedicated domains / subdomains represent one site each
    return host, f"https://{host}/"


def load_known_portfolio_sites() -> dict:
    """Parse portfolioProjects from index.html so newly wired sites appear immediately."""
    index_path = os.path.join(REPO_ROOT, "index.html")
    sites = {
        "cube.kaik.space": {
            "key": "cube.kaik.space",
            "title": "CUBIC PORTFOLIO // 3D ESCHER",
            "url": "https://cube.kaik.space/",
            "tag": "PRIMARY HUB",
            "owned": True,
        }
    }
    if not os.path.exists(index_path):
        return sites

    text = open(index_path, "r", encoding="utf-8").read()
    # Extract title, tag, url entries from portfolioProjects
    pattern = re.compile(
        r"title:\s*'([^']+)'[\s\S]*?tag:\s*'([^']+)'[\s\S]*?url:\s*'([^']*)'",
        re.MULTILINE,
    )
    owned_hosts = {"kaik.space", "cube.kaik.space", "avatar.kaik.space", "dance-journal.kaik.space", "cre8ture.github.io", "kai4avaya.github.io"}
    for title, tag, url in pattern.findall(text):
        if not url or not url.startswith("http"):
            continue
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        clean_host = host[4:] if host.startswith("www.") else host
        if clean_host not in owned_hosts:
            continue
        key, canonical_url = normalize_site_key(parsed.netloc, parsed.path)
        sites[key] = {
            "key": key,
            "title": title,
            "url": canonical_url,
            "tag": tag,
            "owned": True,
        }
    return sites


def prepare_credentials() -> tuple[str | None, str | None]:
    """Return (credentials_path, temp_path_to_cleanup)."""
    raw_json = os.environ.get("GA_SERVICE_ACCOUNT_JSON")
    if raw_json:
        fd, tmp = tempfile.mkstemp(prefix="ga_sa_", suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(raw_json)
        os.chmod(tmp, 0o600)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp
        return tmp, tmp

    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or DEFAULT_CREDS
    if os.path.exists(creds_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        return creds_path, None
    return None, None


def run_ga4_sync() -> dict:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        OrderBy,
        RunReportRequest,
    )

    client = BetaAnalyticsDataClient()
    prop = f"properties/{PROPERTY_ID}"

    known_sites = load_known_portfolio_sites()

    def query_sites(start_date: str) -> dict:
        req = RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=start_date, end_date="today")],
            dimensions=[Dimension(name="hostName"), Dimension(name="pagePath")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="activeUsers"),
                Metric(name="sessions"),
                Metric(name="userEngagementDuration"),
            ],
            limit=500,
        )
        resp = client.run_report(req)
        agg = {}
        for row in resp.rows:
            host = row.dimension_values[0].value
            path = row.dimension_values[1].value
            if not host or host in ("(not set)", "localhost", "127.0.0.1"):
                continue
            key, url = normalize_site_key(host, path)
            views = int(float(row.metric_values[0].value or 0))
            users = int(float(row.metric_values[1].value or 0))
            sessions = int(float(row.metric_values[2].value or 0))
            eng_sec = float(row.metric_values[3].value or 0)
            if key not in agg:
                agg[key] = {"key": key, "url": url, "views": 0, "users": 0, "sessions": 0, "engSec": 0.0}
            agg[key]["views"] += views
            agg[key]["users"] += users
            agg[key]["sessions"] += sessions
            agg[key]["engSec"] += eng_sec
        return agg

    sites_30d = query_sites("30daysAgo")
    sites_7d = query_sites("7daysAgo")

    # Merge known sites + ANY auto-discovered site from GA4!
    all_keys = set(known_sites.keys()) | set(sites_30d.keys()) | set(sites_7d.keys())
    merged_sites = []
    for key in all_keys:
        meta = known_sites.get(key)
        d30 = sites_30d.get(key, {"views": 0, "users": 0, "sessions": 0, "engSec": 0.0})
        d7 = sites_7d.get(key, {"views": 0, "users": 0, "sessions": 0, "engSec": 0.0})
        auto_discovered = meta is None
        url = meta["url"] if meta else (d30.get("url") or d7.get("url") or f"https://{key}/")
        title = meta["title"] if meta else key.upper()
        tag = meta["tag"] if meta else "AUTO-DISCOVERED"
        avg_eng_30 = round(d30["engSec"] / max(1, d30["sessions"]), 1) if d30["sessions"] > 0 else 0
        avg_eng_7 = round(d7["engSec"] / max(1, d7["sessions"]), 1) if d7["sessions"] > 0 else 0

        merged_sites.append({
            "key": key,
            "title": title,
            "tag": tag,
            "url": url,
            "autoDiscovered": auto_discovered,
            "status": "live" if (d30["views"] > 0 or d7["views"] > 0) else "ready",
            "d30": {
                "views": d30["views"],
                "users": d30["users"],
                "sessions": d30["sessions"],
                "avgEngagementSec": avg_eng_30,
            },
            "d7": {
                "views": d7["views"],
                "users": d7["users"],
                "sessions": d7["sessions"],
                "avgEngagementSec": avg_eng_7,
            },
        })

    merged_sites.sort(key=lambda s: (-s["d30"]["views"], -s["d7"]["views"], s["key"]))

    # Daily time series (last 30 days)
    daily_req = RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date="29daysAgo", end_date="today")],
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="activeUsers"),
            Metric(name="sessions"),
        ],
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
    )
    daily_resp = client.run_report(daily_req)
    daily_map = {}
    for row in daily_resp.rows:
        ds = row.dimension_values[0].value  # YYYYMMDD
        iso = f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}"
        daily_map[iso] = {
            "date": iso,
            "views": int(float(row.metric_values[0].value or 0)),
            "users": int(float(row.metric_values[1].value or 0)),
            "sessions": int(float(row.metric_values[2].value or 0)),
        }

    # Backfill full 30-day date grid so sparkline always has 30 clean points
    today = datetime.datetime.now(datetime.timezone.utc).date()
    daily_series = []
    for offset in range(29, -1, -1):
        day = (today - datetime.timedelta(days=offset)).isoformat()
        daily_series.append(daily_map.get(day, {"date": day, "views": 0, "users": 0, "sessions": 0}))

    # Top traffic sources (30d)
    src_req = RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        dimensions=[Dimension(name="sessionSourceMedium")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=8,
    )
    src_resp = client.run_report(src_req)
    sources = [
        {
            "source": row.dimension_values[0].value,
            "sessions": int(float(row.metric_values[0].value or 0)),
            "users": int(float(row.metric_values[1].value or 0)),
        }
        for row in src_resp.rows
    ]

    # Top events (30d)
    evt_req = RunReportRequest(
        property=prop,
        date_ranges=[DateRange(start_date="30daysAgo", end_date="today")],
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="eventCount"), desc=True)],
        limit=10,
    )
    evt_resp = client.run_report(evt_req)
    events = [
        {
            "name": row.dimension_values[0].value,
            "count": int(float(row.metric_values[0].value or 0)),
        }
        for row in evt_resp.rows
    ]

    # Totals (30d and 7d)
    def query_totals(start_date: str) -> dict:
        t_req = RunReportRequest(
            property=prop,
            date_ranges=[DateRange(start_date=start_date, end_date="today")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="activeUsers"),
                Metric(name="sessions"),
            ],
        )
        t_resp = client.run_report(t_req)
        if not t_resp.rows:
            return {"views": 0, "users": 0, "sessions": 0}
        r = t_resp.rows[0]
        return {
            "views": int(float(r.metric_values[0].value or 0)),
            "users": int(float(r.metric_values[1].value or 0)),
            "sessions": int(float(r.metric_values[2].value or 0)),
        }

    return {
        "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "propertyId": PROPERTY_ID,
        "measurementId": MEASUREMENT_ID,
        "totals": {
            "d30": query_totals("30daysAgo"),
            "d7": query_totals("7daysAgo"),
        },
        "siteCount": len(merged_sites),
        "liveSiteCount": sum(1 for s in merged_sites if s["status"] == "live"),
        "autoDiscoveredCount": sum(1 for s in merged_sites if s["autoDiscovered"]),
        "daily": daily_series,
        "sites": merged_sites,
        "sources": sources,
        "events": events,
    }


def main():
    parser = argparse.ArgumentParser(description="Sync GA4 metrics to analytics/data.json")
    parser.add_argument("--push", action="store_true", help="Commit and push analytics/data.json to main & gh-pages")
    args = parser.parse_args()

    creds_path, tmp_path = prepare_credentials()
    if not creds_path:
        print("ERROR: No GA4 credentials found. Set GOOGLE_APPLICATION_CREDENTIALS or GA_SERVICE_ACCOUNT_JSON.", file=sys.stderr)
        sys.exit(1)

    try:
        payload = run_ga4_sync()
        os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(
            f"Synced {payload['siteCount']} sites ({payload['liveSiteCount']} live, "
            f"{payload['autoDiscoveredCount']} auto-discovered) -> {OUT_PATH}"
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

    if args.push:
        subprocess.run(["git", "-C", REPO_ROOT, "add", "analytics/data.json"], check=True)
        diff = subprocess.run(["git", "-C", REPO_ROOT, "diff", "--cached", "--quiet"])
        if diff.returncode != 0:
            subprocess.run(["git", "-C", REPO_ROOT, "commit", "-m", "Sync GA4 analytics data"], check=True)
            subprocess.run(["git", "-C", REPO_ROOT, "push", "origin", "main"], check=True)
            subprocess.run(["git", "-C", REPO_ROOT, "push", "origin", "main:gh-pages"], check=True)
            print("Pushed updated analytics/data.json to main & gh-pages.")
        else:
            print("No analytics data changes to push.")


if __name__ == "__main__":
    main()
