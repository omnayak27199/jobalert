#!/usr/bin/env python3
"""IndiaJob operations — info, db, users, verify."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _fmt_dt(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M UTC")


def _fmt_bytes(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _section(title: str) -> None:
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


def _row(label: str, value: Any) -> None:
    print(f"  {label:<22} {value}")


def cmd_config() -> dict[str, Any]:
    from app.config import settings

    return {
        "public_site_url": settings.public_site_url,
        "cors_origins": settings.cors_origins,
        "fetch_interval_minutes": settings.fetch_interval_minutes,
        "smtp_configured": bool(settings.smtp_host and settings.smtp_user),
        "twilio_configured": bool(settings.twilio_account_sid and settings.twilio_auth_token),
        "admin_configured": bool(settings.admin_secret),
        "openai_configured": bool(settings.openai_api_key),
        "database_url": settings.database_url,
    }


def cmd_db_stats() -> dict[str, Any]:
    from sqlalchemy import desc, func

    from app.database import SessionLocal
    from app.models.job import Job, JobCategory, NewsItem
    from app.models.user import FavoriteJob, User
    from app.services.application_dates import closed_visibility_cutoff
    from app.services.job_quality import is_publishable_job

    db_path = Path("data/jobalert.db")
    db_size = db_path.stat().st_size if db_path.exists() else 0

    db = SessionLocal()
    try:
        total_jobs = db.query(Job).count()
        active_jobs = db.query(Job).filter(Job.is_active == True).count()  # noqa: E712
        verified = db.query(Job).filter(Job.is_verified == True).count()  # noqa: E712
        users = db.query(User).count()
        favorites = db.query(FavoriteJob).count()
        news = db.query(NewsItem).count()

        cutoff = closed_visibility_cutoff()
        notif_jobs = (
            db.query(Job)
            .filter(
                Job.is_active == True,  # noqa: E712
                Job.category == JobCategory.NOTIFICATION,
            )
            .all()
        )
        publishable = [j for j in notif_jobs if is_publishable_job(j)]
        listable = [
            j
            for j in publishable
            if j.last_date is None or j.last_date >= cutoff
        ]

        week_later = datetime.utcnow() + timedelta(days=7)
        now = datetime.utcnow()
        closing_soon = sum(
            1
            for j in listable
            if j.last_date is not None and now <= j.last_date <= week_later
        )

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_updates = sum(1 for j in listable if j.created_at and j.created_at >= today)
        states = len({j.state for j in listable if j.state})

        latest_job = db.query(Job).order_by(desc(Job.created_at)).first()
        latest_user = db.query(User).order_by(desc(User.created_at)).first()

        by_category = (
            db.query(Job.category, func.count(Job.id))
            .filter(Job.is_active == True)  # noqa: E712
            .group_by(Job.category)
            .all()
        )

        return {
            "path": str(db_path.resolve()),
            "size_bytes": db_size,
            "total_jobs": total_jobs,
            "active_jobs": active_jobs,
            "publishable_notifications": len(publishable),
            "visible_on_site": len(listable),
            "closing_soon": closing_soon,
            "today_updates": today_updates,
            "states_covered": states,
            "verified_jobs": verified,
            "users": users,
            "favorites": favorites,
            "news_items": news,
            "by_category": {cat.value: count for cat, count in by_category},
            "latest_job": {
                "id": latest_job.id,
                "title": latest_job.title[:80] if latest_job else None,
                "created_at": latest_job.created_at if latest_job else None,
            }
            if latest_job
            else None,
            "latest_user": {
                "id": latest_user.id,
                "email": latest_user.email,
                "created_at": latest_user.created_at,
            }
            if latest_user
            else None,
        }
    finally:
        db.close()


def cmd_users_list(limit: int = 50) -> list[dict[str, Any]]:
    from sqlalchemy import desc

    from app.database import SessionLocal
    from app.models.user import User

    db = SessionLocal()
    try:
        users = db.query(User).order_by(desc(User.created_at)).limit(limit).all()
        rows: list[dict[str, Any]] = []
        for user in users:
            prefs = user.preferences
            rows.append(
                {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "phone": user.phone or "—",
                    "active": user.is_active,
                    "created_at": user.created_at,
                    "email_alerts": prefs.email_alerts if prefs else False,
                    "whatsapp_alerts": prefs.whatsapp_alerts if prefs else False,
                }
            )
        return rows
    finally:
        db.close()


def print_info() -> None:
    cfg = cmd_config()
    db = cmd_db_stats()

    _section("IndiaJob — System Info")
    _row("Site URL", cfg["public_site_url"])
    _row("Fetch interval", f"{cfg['fetch_interval_minutes']} min")
    _row("Database", cfg["database_url"])
    _row("Admin key set", "yes" if cfg["admin_configured"] else "no")
    _row("OpenAI", "yes" if cfg["openai_configured"] else "no")
    _row("SMTP email", "yes" if cfg["smtp_configured"] else "no")
    _row("Twilio WhatsApp", "yes" if cfg["twilio_configured"] else "no")
    _row("CORS", ", ".join(cfg["cors_origins"]))

    _section("Database")
    _row("File", db["path"])
    _row("Size", _fmt_bytes(db["size_bytes"]))
    _row("Total jobs", db["total_jobs"])
    _row("Active jobs", db["active_jobs"])
    _row("Visible on site", db["visible_on_site"])
    _row("Closing soon (7d)", db["closing_soon"])
    _row("Today's updates", db["today_updates"])
    _row("States covered", db["states_covered"])
    _row("Verified jobs", db["verified_jobs"])
    _row("Users", db["users"])
    _row("Saved favorites", db["favorites"])
    _row("News items", db["news_items"])
    if db["latest_job"]:
        _row(
            "Latest job",
            f"#{db['latest_job']['id']} — {db['latest_job']['title']} ({_fmt_dt(db['latest_job']['created_at'])})",
        )
    if db["latest_user"]:
        _row(
            "Latest user",
            f"{db['latest_user']['email']} ({_fmt_dt(db['latest_user']['created_at'])})",
        )

    if db["by_category"]:
        _section("Jobs by category")
        for cat, count in sorted(db["by_category"].items()):
            _row(cat, count)

    print()


def print_db() -> None:
    db = cmd_db_stats()
    _section("Database")
    for key, value in db.items():
        if key in {"by_category", "latest_job", "latest_user"}:
            continue
        if key == "size_bytes":
            _row("size", _fmt_bytes(value))
        else:
            _row(key.replace("_", " "), value)

    if db["by_category"]:
        print("\n  By category:")
        for cat, count in sorted(db["by_category"].items()):
            print(f"    {cat:<16} {count}")
    print()


def print_users(limit: int) -> None:
    users = cmd_users_list(limit=limit)
    _section(f"Users ({len(users)} shown)")
    if not users:
        print("  No users registered.")
        print()
        return
    print(f"  {'ID':<5} {'Email':<32} {'Name':<18} {'Phone':<12} {'Alerts':<12} Created")
    print(f"  {'-' * 5} {'-' * 32} {'-' * 18} {'-' * 12} {'-' * 12} {'-' * 16}")
    for user in users:
        alerts = []
        if user["email_alerts"]:
            alerts.append("email")
        if user["whatsapp_alerts"]:
            alerts.append("wa")
        alert_str = ",".join(alerts) or "—"
        print(
            f"  {user['id']:<5} {user['email'][:32]:<32} {user['name'][:18]:<18} "
            f"{str(user['phone'])[:12]:<12} {alert_str:<12} {_fmt_dt(user['created_at'])}"
        )
    print()


def cmd_doctor() -> int:
    """Validate backend/.env and config before Docker start."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    issues: list[str] = []
    fixes: list[str] = []

    _section("Environment doctor")
    if not env_path.is_file():
        issues.append(f"Missing {env_path}")
        fixes.append("cp backend/.env.example backend/.env && nano backend/.env")
    else:
        _row("env file", env_path)
        keys: dict[str, str] = {}
        for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            keys[key.strip()] = value.strip()

        if "UBLIC_SITE_URL" in keys:
            issues.append("Typo: UBLIC_SITE_URL (missing P)")
            fixes.append(f"sed -i 's/^UBLIC_SITE_URL=/PUBLIC_SITE_URL=/' {env_path}")
        if "PUBLIC_SITE_URL" not in keys and "UBLIC_SITE_URL" not in keys:
            issues.append("PUBLIC_SITE_URL not set (will default to localhost)")
            fixes.append(f"echo 'PUBLIC_SITE_URL=https://indiagovjob.online' >> {env_path}")

        for label, key in (
            ("site url", "PUBLIC_SITE_URL"),
            ("cors", "CORS_ORIGINS"),
            ("admin", "ADMIN_SECRET"),
        ):
            if key in keys:
                _row(label, keys[key][:80])

    try:
        from app.config import settings

        _row("config load", "OK")
        _row("public_site_url", settings.public_site_url)
        _row("skip_initial_fetch", settings.skip_initial_fetch)
        if settings.public_site_url.startswith("http://localhost"):
            issues.append("PUBLIC_SITE_URL still localhost — set https://indiagovjob.online in .env")
    except Exception as exc:
        issues.append(f"Config failed to load: {exc}")
        fixes.append("docker compose logs backend --tail=80")

    if issues:
        print()
        for item in issues:
            print(f"  [FAIL] {item}")
        if fixes:
            print("\n  Suggested fixes:")
            for fix in fixes:
                print(f"    {fix}")
        print("\n  Then run:")
        print("    docker compose up -d backend")
        print("    docker compose logs backend --tail=50")
        print()
        return 1

    print("\n  [PASS] Environment looks OK. Start backend with:")
    print("    docker compose up -d backend && docker compose logs backend --tail=30")
    print()
    return 0


def print_verify_json(results: list[dict[str, Any]]) -> None:
    print(json.dumps(results, indent=2))


def run_verify(site_url: str | None = None) -> list[dict[str, Any]]:
    import urllib.error
    import urllib.request

    results: list[dict[str, Any]] = []
    cfg = cmd_config()
    db = cmd_db_stats()
    base = (site_url or cfg["public_site_url"] or "http://localhost:3000").rstrip("/")
    api_base = os.environ.get("JBCLI_API_URL", "http://127.0.0.1:8000")

    def add(name: str, ok: bool, detail: str) -> None:
        results.append({"check": name, "ok": ok, "detail": detail})

    add("database_file", db["size_bytes"] > 0, db["path"])
    add("jobs_in_db", db["total_jobs"] > 0, f"{db['total_jobs']} total, {db['visible_on_site']} visible")
    add("users_in_db", True, f"{db['users']} registered")
    add("admin_secret", cfg["admin_configured"], "configured" if cfg["admin_configured"] else "missing")
    add("public_site_url", bool(cfg["public_site_url"]), cfg["public_site_url"])
    add("smtp", cfg["smtp_configured"], "configured" if cfg["smtp_configured"] else "not configured")
    add("twilio", cfg["twilio_configured"], "configured" if cfg["twilio_configured"] else "not configured")

    domain = cfg["public_site_url"].rstrip("/")
    cors_ok = domain in cfg["cors_origins"] or f"{domain}" in str(cfg["cors_origins"])
    add("cors_includes_site", cors_ok, ", ".join(cfg["cors_origins"]))

    endpoints = [
        ("backend_health", f"{api_base}/health"),
        ("backend_stats", f"{api_base}/api/stats"),
        ("site_stats", f"{base}/api/stats"),
    ]
    for name, url in endpoints:
        try:
            with urllib.request.urlopen(url, timeout=15) as resp:
                body = resp.read(500).decode("utf-8", errors="replace")
                add(name, 200 <= resp.status < 300, f"HTTP {resp.status} — {body[:80]}")
        except urllib.error.HTTPError as exc:
            add(name, False, f"HTTP {exc.code}")
        except Exception as exc:
            add(name, False, str(exc))

    return results


def print_verify(site_url: str | None = None) -> int:
    results = run_verify(site_url=site_url)
    _section("Verify All")
    passed = 0
    for item in results:
        mark = "PASS" if item["ok"] else "FAIL"
        if item["ok"]:
            passed += 1
        print(f"  [{mark}] {item['check']:<22} {item['detail']}")
    print(f"\n  {passed}/{len(results)} checks passed\n")
    return 0 if passed == len(results) else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="IndiaJob jbcli operations")
    parser.add_argument("--json", action="store_true", help="JSON output")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="Full system and database overview")
    sub.add_parser("config", help="Show configuration summary")
    sub.add_parser("db", help="Database statistics")

    users_p = sub.add_parser("users", help="List registered users")
    users_p.add_argument("--limit", type=int, default=50)

    sub.add_parser("doctor", help="Validate backend/.env before Docker start")

    verify_p = sub.add_parser("verify", help="Run health and config checks")
    verify_p.add_argument("--site-url", default=None, help="Public site URL to test")

    args = parser.parse_args()

    if args.command == "info":
        if args.json:
            print(json.dumps({"config": cmd_config(), "db": cmd_db_stats()}, indent=2, default=str))
        else:
            print_info()
    elif args.command == "config":
        print(json.dumps(cmd_config(), indent=2))
    elif args.command == "db":
        if args.json:
            print(json.dumps(cmd_db_stats(), indent=2, default=str))
        else:
            print_db()
    elif args.command == "users":
        if args.json:
            print(json.dumps(cmd_users_list(limit=args.limit), indent=2, default=str))
        else:
            print_users(limit=args.limit)
    elif args.command == "doctor":
        sys.exit(cmd_doctor())
    elif args.command == "verify":
        if args.json:
            print_verify_json(run_verify(site_url=args.site_url))
            sys.exit(0)
        sys.exit(print_verify(site_url=args.site_url))


if __name__ == "__main__":
    main()
