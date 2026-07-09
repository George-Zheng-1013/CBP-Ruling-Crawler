"""Export module for the CBP Advance Ruling Crawler.

Exports parsed ruling data to:
1. UTF-8 text files (pipe-delimited |)
2. Optional CSV format
"""

import csv
import os
from typing import List, Dict, Any, Optional, TextIO

from config import (
    EXPORT_FIELD_SEPARATOR,
    EXPORT_ENCODING,
    EXPORT_FILENAME,
    DATA_DIR,
)
from utils import setup_logger, clean_text

logger = setup_logger("exporter")


class RulingExporter:
    """Exports parsed ruling data to text and CSV formats.

    The primary export format is pipe-delimited (|) UTF-8 text with 5 fields:
        Ruling No | 商品名称 | 商品详情 | HSCODE | 年份
    """

    # Canonical field names for export
    FIELD_NAMES = ["ruling_no", "subject", "description", "hs_code", "year"]
    # Chinese header for the export file (human-readable)
    HEADER_CHINESE = "Ruling No|商品名称|商品详情|HSCODE|年份"

    def __init__(self, output_dir: Optional[str] = None) -> None:
        """Initialize the exporter.

        Args:
            output_dir: Directory for output files. Defaults to DATA_DIR.
        """
        self.output_dir = output_dir or DATA_DIR
        os.makedirs(self.output_dir, exist_ok=True)

    def export_to_text(self, rulings: List[Dict[str, Any]],
                       filename: Optional[str] = None,
                       append: bool = False) -> str:
        """Export rulings to a pipe-delimited UTF-8 text file.

        Each line contains 5 fields separated by '|':
            Ruling No|商品名称(Subject)|商品详情(Description)|HSCODE|年份

        Args:
            rulings: List of parsed ruling dicts.
            filename: Output filename. Defaults to EXPORT_FILENAME.
            append: If True, append to existing file (no header).

        Returns:
            Path to the exported file.
        """
        filepath = filename or EXPORT_FILENAME
        mode = "a" if append else "w"
        encoding = EXPORT_ENCODING

        with open(filepath, mode, encoding=encoding) as f:
            if not append:
                f.write(self.HEADER_CHINESE + "\n")

            for ruling in rulings:
                line = self._format_ruling_line(ruling)
                f.write(line + "\n")

        count = len(rulings)
        logger.info("Exported %d rulings to %s (append=%s)", count, filepath, append)
        return filepath

    def export_to_csv(self, rulings: List[Dict[str, Any]],
                      filename: Optional[str] = None,
                      append: bool = False) -> str:
        """Export rulings to a CSV file.

        Args:
            rulings: List of parsed ruling dicts.
            filename: Output filename. Defaults to cbp_rulings_export.csv.
            append: If True, append to existing file.

        Returns:
            Path to the exported CSV file.
        """
        filepath = filename or os.path.join(self.output_dir, "cbp_rulings_export.csv")
        mode = "a" if append else "w"

        with open(filepath, mode, encoding=EXPORT_ENCODING, newline="") as f:
            writer = csv.DictWriter(f, fieldnames=self.FIELD_NAMES,
                                    extrasaction="ignore")
            if not append:
                writer.writeheader()
            for ruling in rulings:
                row = self._prepare_csv_row(ruling)
                writer.writerow(row)

        logger.info("Exported %d rulings to CSV %s (append=%s)",
                     len(rulings), filepath, append)
        return filepath

    def export_by_year(self, rulings: List[Dict[str, Any]],
                       base_dir: Optional[str] = None) -> Dict[int, str]:
        """Export rulings organized by year into separate files.

        Creates one file per year in a 'by_year' subdirectory.

        Args:
            rulings: List of parsed ruling dicts.
            base_dir: Base export directory. Defaults to DATA_DIR.

        Returns:
            Dict mapping year -> exported file path.
        """
        base_dir = base_dir or self.output_dir
        year_dir = os.path.join(base_dir, "by_year")
        os.makedirs(year_dir, exist_ok=True)

        year_groups: Dict[int, List[Dict[str, Any]]] = {}
        for ruling in rulings:
            year = ruling.get("year")
            if year is None:
                year = 0  # Unknown year
            year_int = int(year)
            if year_int not in year_groups:
                year_groups[year_int] = []
            year_groups[year_int].append(ruling)

        result: Dict[int, str] = {}
        for year, year_rulings in sorted(year_groups.items()):
            year_label = str(year) if year > 0 else "unknown"
            filename = os.path.join(year_dir, f"rulings_{year_label}.txt")
            self.export_to_text(year_rulings, filename=filename)
            result[year] = filename

        logger.info("Exported rulings to %d year-based files", len(result))
        return result

    def export_failed_parses(self, rulings: List[Dict[str, Any]],
                             filename: Optional[str] = None) -> str:
        """Export rulings that failed parsing for manual review.

        Args:
            rulings: List of ruling dicts (with parse_failed=1).
            filename: Output filename.

        Returns:
            Path to the exported file.
        """
        filepath = filename or os.path.join(self.output_dir,
                                            "failed_parses.txt")

        with open(filepath, "w", encoding=EXPORT_ENCODING) as f:
            f.write("Ruling No|Error Message|URL|Subject\n")
            for ruling in rulings:
                ruling_no = ruling.get("ruling_no", "UNKNOWN")
                error_msg = ruling.get("parse_error_msg", "Unknown error")
                url = ruling.get("detail_url", "")
                subject = ruling.get("subject", "")
                # Escape internal pipes
                error_msg = error_msg.replace("|", "/")
                subject = subject.replace("|", "/")
                f.write(f"{ruling_no}|{error_msg}|{url}|{subject}\n")

        logger.info("Exported %d failed parses to %s", len(rulings), filepath)
        return filepath

    def _format_ruling_line(self, ruling: Dict[str, Any]) -> str:
        """Format a single ruling as a pipe-delimited line.

        Args:
            ruling: Parsed ruling dict.

        Returns:
            Formatted line string (5 fields, pipe-separated).
        """
        ruling_no = ruling.get("ruling_no", "").strip()
        subject = clean_text(ruling.get("subject", "")).replace("\n", " ").replace("|", "/")
        description = clean_text(ruling.get("description", "")).replace("|", "/")
        hs_code = ruling.get("hs_code", "").strip()
        year = ruling.get("year", "")

        # Replace newlines in description with spaces for single-line format
        description = description.replace("\n", " ").replace("\r", " ")
        # Truncate very long descriptions (max 10000 chars per line)
        if len(description) > 10000:
            description = description[:9997] + "..."

        return (f"{ruling_no}{EXPORT_FIELD_SEPARATOR}"
                f"{subject}{EXPORT_FIELD_SEPARATOR}"
                f"{description}{EXPORT_FIELD_SEPARATOR}"
                f"{hs_code}{EXPORT_FIELD_SEPARATOR}"
                f"{year}")

    def _prepare_csv_row(self, ruling: Dict[str, Any]) -> Dict[str, str]:
        """Prepare a ruling dict for CSV export.

        Args:
            ruling: Parsed ruling dict.

        Returns:
            Dict with CSV-safe values.
        """
        return {
            "ruling_no": ruling.get("ruling_no", "").strip(),
            "subject": clean_text(ruling.get("subject", "")),
            "description": clean_text(ruling.get("description", "")),
            "hs_code": ruling.get("hs_code", "").strip(),
            "year": str(ruling.get("year", "")),
        }
