#!/usr/bin/env python3
"""CBP Advance Ruling Crawler — CLI Entry Point.

Collects Binding Advance Rulings from the CBP CROSS database
(https://rulings.cbp.gov) via the official JSON API and stores them as
5-field structured records.

Usage:
    python main.py --phase api             # Crawl via CROSS JSON API
    python main.py --phase export          # Export stored rulings to text
    python main.py --stats                 # Show database statistics
"""

import argparse
import sys
import time
from typing import Dict, Any, List, Optional, Set

from config import (
    DB_FILENAME,
    YEAR_RANGE,
    API_SEARCH_TERMS,
    API_MAX_PAGES_PER_TERM,
    API_SORT_BY_DATE_DESC,
)
from utils import (
    setup_logger,
    random_delay,
)
from storage import DatabaseManager
from fetcher import (
    fetch_json,
    build_api_search_url,
    build_api_ruling_url,
)
from extractor import (
    JsonSearchExtractor,
    JsonDetailExtractor,
)
from validator import RulingValidator, validate_ruling_batch
from exporter import RulingExporter

logger = setup_logger("cbp-crawler")


class CrawlerPipeline:
    """Orchestrates the CBP Advance Ruling crawling pipeline.

    The pipeline consumes the official CROSS JSON API to collect binding
    advance rulings, stores them in SQLite, and can export the results.
    """

    def __init__(self, db_path: str = DB_FILENAME) -> None:
        """Initialize the pipeline with database connection.

        Args:
            db_path: Path to SQLite database.
        """
        self.db = DatabaseManager(db_path)
        self.exporter = RulingExporter()
        self.validator = RulingValidator()
        self._ruling_no_cache: Set[str] = set()

    # ── JSON API Crawl ────────────────────────────────────────────────────

    def phase_api_crawl(self, terms: Optional[List[str]] = None,
                        collection: Optional[str] = None,
                        years: Optional[List[int]] = None,
                        max_pages_per_term: int = -1,
                        max_rulings: int = -1,
                        min_date: Optional[str] = None,
                        series: Optional[List[str]] = None,
                        sort_by: str = API_SORT_BY_DATE_DESC) -> Dict[str, Any]:
        """Crawl rulings via the CROSS JSON API.

        For each enumeration term (HTS chapter code), pages through
        /api/search collecting new ruling numbers, then fetches each ruling's
        full record from /api/ruling/{no} and upserts it into the database.

        Because the data comes straight from the official API, records with
        the essential fields are stored as parse_failed=0. Validation is still
        run and any warnings are recorded in parse_error_msg for transparency,
        but do not by themselves flip the record to failed.

        Args:
            terms: Search terms to enumerate. Defaults to API_SEARCH_TERMS
                   (HTS chapters 01-97).
            collection: Optional collection filter ('ny' or 'hq'). When omitted
                        both collections are enumerated and `series` (below)
                        filters them client-side.
            years: Optional whitelist of years to keep (others are skipped).
            max_pages_per_term: Max search pages per term (-1 = until empty).
            max_rulings: Stop after collecting this many NEW rulings
                         (-1 = no limit). Useful for smoke tests.
            min_date: Optional inclusive lower bound on ruling_date
                      (ISO 'YYYY-MM-DD'). Anything older is skipped. Requires
                      sort_by='DATE_DESC' (default) so pagination can stop early
                      once the date threshold is crossed.
            series: Allowed collection series to keep, e.g. ['hq', 'ny'] for
                    HQ/NY/N tariff-classification rulings. Others are skipped.
                    Defaults to ['hq', 'ny'] (the only two CROSS collections).
            sort_by: API sort mode. Defaults to 'DATE_DESC' (newest first) so a
                     date-bounded crawl stops paging as soon as it passes
                     min_date; use 'RELEVANCE' for the original behaviour.

        Returns:
            Dict with crawl statistics.
        """
        logger.info("=" * 60)
        logger.info("PHASE (API): JSON API Crawl")
        logger.info("=" * 60)

        terms = terms or list(API_SEARCH_TERMS)
        year_filter = set(years) if years else None
        page_cap = (max_pages_per_term if max_pages_per_term > 0
                    else API_MAX_PAGES_PER_TERM)
        allowed_series = set(s.lower() for s in (series or ["hq", "ny"]))
        min_date = (min_date or "").strip()

        stats: Dict[str, Any] = {
            "terms_processed": 0,
            "search_pages": 0,
            "search_hits": 0,
            "new_rulings": 0,
            "details_fetched": 0,
            "detail_failed": 0,
            "upserted": 0,
            "skipped_year": 0,
            "skipped_series": 0,
            "skipped_no_date": 0,
            "validation_warnings": 0,
            "errors": [],
        }

        # ── Stage 1: enumerate search terms and collect NEW ruling summaries ──
        # rn -> summary dict (storage-aligned, without description)
        pending: Dict[str, Dict[str, Any]] = {}

        for term in terms:
            stats["terms_processed"] += 1
            logger.info("Enumerating term %r", term)

            past_cutoff = False  # True once we see a ruling older than min_date
            for page in range(1, page_cap + 1):
                if max_rulings > 0 and len(pending) >= max_rulings:
                    break
                if past_cutoff:
                    break

                url = build_api_search_url(
                    term, page=page, collection=collection, sort_by=sort_by)
                result = fetch_json(url)
                stats["search_pages"] += 1

                if not result.success():
                    logger.warning("Search failed for term=%r page=%d: %s",
                                   term, page, result.error_message)
                    break

                extractor = JsonSearchExtractor(result.data)
                items = extractor.extract_items()
                if not items:
                    logger.debug("Term %r page %d empty — end of results",
                                 term, page)
                    break

                stats["search_hits"] += len(items)

                for item in items:
                    rn = item["ruling_no"]
                    if not rn or rn in pending:
                        continue

                    # Series filter (HQ/NY/N only by default)
                    item_collection = str(item.get("collection") or "").lower()
                    if item_collection and item_collection not in allowed_series:
                        stats["skipped_series"] += 1
                        continue

                    # Date lower-bound filter (inclusive, ISO string compare)
                    rd = str(item.get("ruling_date") or "")
                    if min_date:
                        if not rd:
                            stats["skipped_no_date"] += 1
                            continue
                        if rd < min_date:
                            # DATE_DESC => everything after is also older
                            past_cutoff = True
                            continue

                    if year_filter is not None and item.get("year") not in year_filter:
                        stats["skipped_year"] += 1
                        continue
                    if rn in self._ruling_no_cache or self.db.ruling_exists(rn):
                        self._ruling_no_cache.add(rn)
                        continue
                    pending[rn] = item
                    if max_rulings > 0 and len(pending) >= max_rulings:
                        break

                # With DATE_DESC, once a page contains anything older than
                # min_date we have collected all the recent rulings for this
                # term; stop paging it.
                if past_cutoff:
                    logger.debug("Term %r passed min_date on page %d — stop",
                                 term, page)
                    break

            if max_rulings > 0 and len(pending) >= max_rulings:
                logger.info("Reached max_rulings=%d, stopping enumeration",
                            max_rulings)
                break

        stats["new_rulings"] = len(pending)
        logger.info("Collected %d new ruling(s) to fetch", len(pending))

        # ── Stage 2: fetch full detail for each new ruling and upsert ──
        for rn, summary in pending.items():
            try:
                detail = fetch_json(build_api_ruling_url(rn))
                if not detail.success():
                    logger.warning("Detail failed for %s: %s",
                                   rn, detail.error_message)
                    stats["detail_failed"] += 1
                    stats["errors"].append(f"{rn}: {detail.error_message}")
                    continue

                record = JsonDetailExtractor(detail.data).extract_all()
                stats["details_fetched"] += 1

                # Merge: prefer detail fields, fall back to search summary.
                if not record.get("ruling_no"):
                    record["ruling_no"] = rn
                for key in ("subject", "hs_code", "hs_codes", "year",
                            "ruling_date", "status", "detail_url"):
                    if not record.get(key) and summary.get(key):
                        record[key] = summary[key]

                # Validation is advisory for API-sourced data.
                is_valid, errors = self.validator.validate(
                    record, check_uniqueness=False)
                has_essentials = bool(record.get("ruling_no")) and bool(
                    (record.get("description") or "").strip())

                if errors:
                    stats["validation_warnings"] += 1
                    record["parse_error_msg"] = "; ".join(
                        e.message for e in errors)[:1000]

                # Only mark failed if the essentials (id + body text) are missing.
                record["parse_failed"] = 0 if has_essentials else 1

                if self.db.upsert_ruling(record):
                    self._ruling_no_cache.add(record["ruling_no"])
                    stats["upserted"] += 1

                random_delay()

            except Exception as e:  # noqa: BLE001 - keep the crawl resilient
                logger.error("API crawl error for %s: %s", rn, str(e))
                stats["detail_failed"] += 1
                stats["errors"].append(f"{rn}: {str(e)}")

        logger.info("API crawl complete: %d new, %d fetched, %d upserted, "
                    "%d detail-failed",
                    stats["new_rulings"], stats["details_fetched"],
                    stats["upserted"], stats["detail_failed"])
        return stats

    def run_api(self, terms: Optional[List[str]] = None,
                collection: Optional[str] = None,
                years: Optional[List[int]] = None,
                max_pages_per_term: int = -1,
                max_rulings: int = -1,
                min_date: Optional[str] = None,
                series: Optional[List[str]] = None,
                sort_by: str = API_SORT_BY_DATE_DESC,
                include_failed: bool = False,
                format: str = "text") -> Dict[str, Any]:
        """Run the JSON-API crawl end to end, then export.

        Returns:
            Dict with the api crawl and export results.
        """
        results: Dict[str, Any] = {}
        start_time = time.time()

        results["api_crawl"] = self.phase_api_crawl(
            terms=terms,
            collection=collection,
            years=years,
            max_pages_per_term=max_pages_per_term,
            max_rulings=max_rulings,
            min_date=min_date,
            series=series,
            sort_by=sort_by,
        )
        results["export"] = self.phase_export(
            include_failed=include_failed, format=format)

        results["elapsed_seconds"] = time.time() - start_time
        logger.info("=" * 60)
        logger.info("API PIPELINE COMPLETE in %.1f seconds",
                    results["elapsed_seconds"])
        logger.info("=" * 60)
        return results

    # ── Export ────────────────────────────────────────────────────────────

    def phase_export(self, include_failed: bool = False,
                     format: str = "text") -> Dict[str, Any]:
        """Validate and export parsed rulings.

        Args:
            include_failed: Whether to also export parse-failed rulings.
            format: Export format ('text' or 'csv').

        Returns:
            Dict with stats (exported, failed, file_path).
        """
        logger.info("=" * 60)
        logger.info("PHASE: Export")
        logger.info("=" * 60)

        stats: Dict[str, Any] = {
            "exported": 0,
            "file_path": "",
            "failed_exports": [],
        }

        # Get unexported rulings
        rulings = self.db.get_unexported_rulings(limit=10000)

        if not rulings:
            logger.info("No unexported rulings to export")
            stats["file_path"] = "No data to export"
            return stats

        # Filter out parse_failed if not requested
        if not include_failed:
            rulings = [r for r in rulings if r.get("parse_failed") != 1]

        if not rulings:
            logger.info("No successfully parsed rulings to export")
            return stats

        # Validate batch
        validation = validate_ruling_batch(rulings)
        if validation["invalid"] > 0:
            logger.warning("%d rulings failed validation", validation["invalid"])
            for rn, errs in validation["errors"].items():
                for err in errs:
                    logger.warning("  %s: %s", rn, err["message"])

        # Export
        try:
            if format == "csv":
                file_path = self.exporter.export_to_csv(rulings)
            else:
                file_path = self.exporter.export_to_text(rulings)

            # Mark as exported
            exported_count = 0
            for ruling in rulings:
                self.db.mark_exported(ruling["ruling_no"])
                exported_count += 1

            stats["exported"] = exported_count
            stats["file_path"] = file_path

            # Also export failed parses separately
            failed_rulings = self.db.get_unexported_rulings(limit=10000)
            failed_rulings = [r for r in failed_rulings if r.get("parse_failed") == 1]
            if failed_rulings:
                failed_path = self.exporter.export_failed_parses(failed_rulings)
                stats["failed_export_path"] = failed_path
                logger.info("Exported %d failed parses to %s",
                             len(failed_rulings), failed_path)

            logger.info("Export complete: %d rulings to %s",
                         exported_count, file_path)

        except Exception as e:
            logger.error("Export failed: %s", str(e))
            stats["failed_exports"].append(str(e))

        return stats

    # ── Utility ───────────────────────────────────────────────────────────

    def show_stats(self) -> Dict[str, Any]:
        """Display and return database statistics.

        Returns:
            Dict of statistics.
        """
        stats = self.db.get_statistics()
        logger.info("=" * 60)
        logger.info("DATABASE STATISTICS")
        logger.info("=" * 60)
        logger.info("Total rulings:     %d", stats.get("total_rulings", 0))
        logger.info("Parsed OK:         %d", stats.get("parsed_ok", 0))
        logger.info("Parse failed:      %d", stats.get("parse_failed", 0))
        logger.info("Exported:          %d", stats.get("exported", 0))
        logger.info("=" * 60)
        return stats

    def cleanup(self) -> None:
        """Release all resources."""
        self.db.close()
        logger.info("Pipeline resources released")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed argparse.Namespace.
    """
    parser = argparse.ArgumentParser(
        description="CBP Advance Ruling Crawler — collect and parse "
                    "Binding Advance Rulings from the CBP CROSS database "
                    "via the official JSON API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --phase api                          # Full JSON-API crawl
  python main.py --phase api --terms 8517 --max-rulings 20   # Smoke test
  python main.py --phase api --terms 85 --api-collection ny  # One chapter, NY
  python main.py --phase api --year 2024 2025         # Keep only these years
  python main.py --phase api --min-date 2025-01-01 --series hq ny --reset
                                                # Fresh re-crawl: HQ/NY/N only,
                                                # ruling_date >= 2025-01-01
  python main.py --phase export                       # Export only
  python main.py --stats                              # Show statistics
        """,
    )

    parser.add_argument(
        "--phase",
        choices=["api", "export"],
        default=None,
        help="Pipeline phase to execute ('api' = JSON-API crawl)",
    )

    parser.add_argument(
        "--year",
        type=int,
        nargs="+",
        default=None,
        help="Year(s) to process (default: %d-%d)" % YEAR_RANGE,
    )

    parser.add_argument(
        "--terms",
        type=str,
        nargs="+",
        default=None,
        help="(api phase) Search terms to enumerate, e.g. HTS codes like "
             "85 8517. Default: HTS chapters 01-97.",
    )

    parser.add_argument(
        "--api-collection",
        type=str,
        default=None,
        choices=["ny", "hq"],
        help="(api phase) Restrict to a single collection (ny or hq)",
    )

    parser.add_argument(
        "--max-rulings",
        type=int,
        default=-1,
        help="(api phase) Stop after collecting this many NEW rulings "
             "(-1 = no limit; handy for smoke tests)",
    )

    parser.add_argument(
        "--max-pages",
        type=int,
        default=-1,
        help="(api phase) Max search pages per term (-1 = until empty)",
    )

    parser.add_argument(
        "--min-date",
        type=str,
        default=None,
        help="(api phase) Inclusive lower bound on ruling_date (ISO "
             "YYYY-MM-DD). Anything older is skipped. Use with the default "
             "DATE_DESC sort so paging stops early past the threshold.",
    )

    parser.add_argument(
        "--series",
        type=str,
        nargs="+",
        choices=["hq", "ny"],
        default=["hq", "ny"],
        help="(api phase) Collection series to keep. Default: hq ny "
             "(HQ/NY/N tariff-classification rulings). Others are skipped.",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        default=False,
        help="(api phase) DELETE all existing rulings before crawling "
             "(fresh re-crawl). Schema and indexes are preserved.",
    )

    parser.add_argument(
        "--include-failed",
        action="store_true",
        default=False,
        help="Include parse-failed rulings in export",
    )

    parser.add_argument(
        "--format",
        choices=["text", "csv"],
        default="text",
        help="Export format (default: text/pipe-delimited)",
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        default=False,
        help="Show database statistics and exit",
    )

    parser.add_argument(
        "--db",
        type=str,
        default=DB_FILENAME,
        help="Path to SQLite database file",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    # Show stats mode
    if args.stats:
        db = DatabaseManager(args.db)
        stats = db.get_statistics()
        db.close()
        print("\n" + "=" * 60)
        print("  CBP Advance Ruling Crawler — Database Statistics")
        print("=" * 60)
        for key, value in stats.items():
            key_display = key.replace("_", " ").title()
            print(f"  {key_display:20s}: {value}")
        print("=" * 60 + "\n")
        return

    pipeline = CrawlerPipeline(db_path=args.db)

    try:
        if args.phase == "api":
            if args.reset:
                deleted = pipeline.db.clear_rulings()
                logger.info("Reset requested: cleared %d existing ruling(s)", deleted)
            pipeline.run_api(
                terms=args.terms,
                collection=args.api_collection,
                years=args.year,
                max_pages_per_term=args.max_pages,
                max_rulings=args.max_rulings,
                min_date=args.min_date,
                series=args.series,
                include_failed=args.include_failed,
                format=args.format,
            )

        elif args.phase == "export":
            pipeline.phase_export(
                include_failed=args.include_failed,
                format=args.format,
            )

        else:
            print("No phase specified. Use --phase or --stats.")
            print("Run 'python main.py --help' for usage information.")
            return

        # Show final stats
        pipeline.show_stats()

    except KeyboardInterrupt:
        logger.info("Interrupted by user. Progress is saved in the database.")
        print("\nInterrupted. Database state is preserved — run the same command "
              "again to resume from where you left off.")

    except Exception as e:
        logger.critical("Fatal error: %s", str(e), exc_info=True)
        print(f"\nFatal error: {e}")
        sys.exit(1)

    finally:
        pipeline.cleanup()


if __name__ == "__main__":
    main()
