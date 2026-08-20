#!/usr/bin/env python3
"""IndiaJob CLI — manual fetch and PDF upload commands.

Usage:
  python -m app.cli fetch              # Fetch from all govt portals
  python -m app.cli upload path/to.pdf # Upload & parse a PDF notification
  python -m app.cli upload path/to.pdf --state "Uttar Pradesh" --org UPPSC
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

# Ensure backend root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def cmd_fetch():
    from app.database import SessionLocal
    from app.scrapers.sources_registry import registry_stats
    from app.services.ingestion import fetch_and_store_all

    db = SessionLocal()
    try:
        print(
            f"Fetching from {registry_stats()['total_sources']} official sources "
            f"(central + {registry_stats()['state_groups']} states + PSU)..."
        )
        result = await fetch_and_store_all(db)
        pipeline = result.get("fetch_pipeline", {})
        print(
            f"Done: {result['jobs']} jobs total, {result['new_jobs']} new, {result['news']} news"
        )
        if pipeline:
            print(
                f"  Central: {pipeline.get('central_found', 0)} from "
                f"{pipeline.get('central_sites', 0)} sites"
            )
            print(
                f"  States:  {pipeline.get('state_found', 0)} from "
                f"{pipeline.get('state_sites', 0)} sites across "
                f"{pipeline.get('state_groups', 0)} states"
            )
            print(
                f"  PSUs:    {pipeline.get('psu_found', 0)} from "
                f"{pipeline.get('psu_sites', 0)} sites"
            )
        if result.get("alerts"):
            print(f"Alerts sent: {result['alerts']}")
    finally:
        db.close()

    print("Running post-fetch cleanup...")
    await cmd_cleanup()


async def cmd_upload(pdf_path: str, state: Optional[str], org: Optional[str], apply_url: Optional[str]):
    from app.database import SessionLocal
    from app.services.pdf_ingestion import save_parsed_pdf
    from app.services.pdf_parser import parse_pdf

    path = Path(pdf_path)
    if not path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    print(f"Parsing PDF: {path.name}")
    content = path.read_bytes()
    parsed = await parse_pdf(content, path.name)

    if state:
        parsed.state = state
    if org:
        parsed.organization = org

    db = SessionLocal()
    try:
        job = save_parsed_pdf(db, parsed, path.name, apply_url=apply_url)
        print(f"Published! Job ID: {job.id}")
        print(f"  Title:   {job.title}")
        print(f"  Org:     {job.organization}")
        print(f"  State:   {job.state or 'All India'}")
        print(f"  Category:{job.category.value}")
        print(f"  Last date:{job.last_date or 'Not detected'}")
    finally:
        db.close()


async def cmd_cleanup():
    import logging

    from app.database import SessionLocal
    from app.services.cleanup_service import run_cleanup

    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = run_cleanup(db)
        print(f"Reactivated {result['reactivated']} qualifying listings")
        print(f"Deactivated {result['deactivated']} junk listings")
        print(f"Deactivated {result['expired']} expired listings (closed >7 days ago)")
        print(f"Post expansion: {result['expand']}")
        print(
            f"Built detail sections for {result['sections_built']} jobs "
            f"({result['deep_built']} deep-enriched from PDF/portal)"
        )
    finally:
        db.close()


async def cmd_repair():
    from app.database import SessionLocal
    from app.services.job_repair import repair_all_jobs

    db = SessionLocal()
    try:
        print("Repairing jobs with aggregator links — fetching official details...")
        result = await repair_all_jobs(db)
        print(f"Done: updated {result['updated']} / {result['total']} jobs")
    finally:
        db.close()


async def cmd_enrich(force: bool = False, limit: int | None = None):
    import logging

    from app.database import SessionLocal
    from app.services.job_repair import deep_enrich_all_jobs

    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        print(
            f"Deep enriching {'all' if not limit else limit} active jobs "
            f"({'force' if force else 'incomplete only'})..."
        )
        result = deep_enrich_all_jobs(db, limit=limit, force=force)
        print(
            f"Done: enriched {result['enriched']}, skipped {result['skipped']}, "
            f"errors {result['errors']} / {result['total']} jobs"
        )
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="IndiaJob.in CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("fetch", help="Fetch jobs from all government portals")
    sub.add_parser("cleanup", help="Remove junk listings and split multi-post recruitments")

    sub.add_parser("repair", help="Fix jobs with aggregator URLs and rebuild official details")

    enrich = sub.add_parser("enrich", help="Deep-parse PDFs/portals and rebuild sections for all jobs")
    enrich.add_argument("--force", action="store_true", help="Re-enrich even if sections look complete")
    enrich.add_argument("--limit", type=int, default=0, help="Max jobs to process (0 = all)")

    up = sub.add_parser("upload", help="Upload and parse a recruitment PDF")
    up.add_argument("pdf", help="Path to PDF file")
    up.add_argument("--state", help="Override state (e.g. 'Uttar Pradesh')")
    up.add_argument("--org", help="Override organization (e.g. UPPSC)")
    up.add_argument("--apply-url", help="Official apply link")

    args = parser.parse_args()

    if args.command == "fetch":
        asyncio.run(cmd_fetch())
    elif args.command == "cleanup":
        asyncio.run(cmd_cleanup())
    elif args.command == "repair":
        asyncio.run(cmd_repair())
    elif args.command == "enrich":
        asyncio.run(cmd_enrich(force=args.force, limit=args.limit or None))
    elif args.command == "upload":
        asyncio.run(cmd_upload(args.pdf, args.state, args.org, args.apply_url))


if __name__ == "__main__":
    main()
