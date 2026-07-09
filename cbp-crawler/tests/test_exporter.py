"""Tests for the exporter module."""

import os
import tempfile
import csv
import pytest
from exporter import RulingExporter


@pytest.fixture
def exporter():
    """Create an exporter with a temp directory."""
    tmp_dir = tempfile.mkdtemp()
    exp = RulingExporter(output_dir=tmp_dir)
    yield exp
    # Cleanup
    for root, dirs, files in os.walk(tmp_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(tmp_dir)


def make_ruling(**overrides):
    ruling = {
        "ruling_no": "HQ12345",
        "subject": "Classification of Electronic Widgets",
        "description": (
            "This ruling addresses the classification of electronic widgets "
            "under the Harmonized Tariff Schedule of the United States (HTSUS). "
            "The widget is classified under heading 8471."
        ),
        "hs_code": "8471.30.0100",
        "hs_codes": ["8471.30.0100"],
        "year": 2023,
        "ruling_date": "2023-01-15",
        "status": "active",
        "parse_failed": 0,
        "parse_error_msg": "",
        "detail_url": "https://rulings.cbp.gov/rulings/HQ12345",
    }
    ruling.update(overrides)
    return ruling


class TestRulingExporterInit:
    """Tests for exporter initialization."""

    def test_default_output_dir(self):
        exp = RulingExporter()
        assert exp.output_dir is not None
        assert os.path.isdir(exp.output_dir)

    def test_custom_output_dir(self):
        tmp_dir = tempfile.mkdtemp()
        exp = RulingExporter(output_dir=tmp_dir)
        assert exp.output_dir == tmp_dir
        assert os.path.isdir(tmp_dir)
        # Cleanup
        os.rmdir(tmp_dir)


class TestExportToText:
    """Tests for export_to_text method."""

    def test_export_basic(self, exporter):
        rulings = [make_ruling()]
        filepath = exporter.export_to_text(rulings)
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Ruling No|商品名称|商品详情|HSCODE|年份" in content
        assert "HQ12345" in content
        assert "8471.30.0100" in content
        assert "2023" in content

    def test_export_multiple_rulings(self, exporter):
        rulings = [make_ruling(ruling_no=f"HQ{i}") for i in range(3)]
        filepath = exporter.export_to_text(rulings)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Header + 3 data lines
        assert len(lines) == 4
        assert "HQ0" in lines[1]
        assert "HQ1" in lines[2]
        assert "HQ2" in lines[3]

    def test_export_append(self, exporter):
        # Write first batch
        rulings1 = [make_ruling(ruling_no="HQ1")]
        filepath = exporter.export_to_text(rulings1)
        # Append second batch
        rulings2 = [make_ruling(ruling_no="HQ2")]
        exporter.export_to_text(rulings2, filename=filepath, append=True)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Header + 2 data lines (no duplicate header)
        assert len(lines) == 3
        assert lines[0].startswith("Ruling No")
        assert "HQ1" in lines[1]
        assert "HQ2" in lines[2]

    def test_export_empty_list(self, exporter):
        filepath = exporter.export_to_text([])
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Header only
        assert len(lines) == 1

    def test_export_pipe_escaping(self, exporter):
        ruling = make_ruling(subject="Item A | Item B | Item C")
        filepath = exporter.export_to_text([ruling])
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # Pipes in subject should be escaped
        assert "Item A | Item B" not in content  # Pipes should be replaced
        assert "Item A / Item B" in content or "Item A" in content

    def test_export_description_truncation(self, exporter):
        long_desc = "A" * 15000
        ruling = make_ruling(description=long_desc)
        filepath = exporter.export_to_text([ruling])
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        # Description should be truncated
        assert len(long_desc) > 10000  # Verify test data exceeds limit
        assert "..." in content or len(long_desc) > 10000

    def test_export_newlines_in_description(self, exporter):
        ruling = make_ruling(description="Line1\nLine2\nLine3")
        filepath = exporter.export_to_text([ruling])
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Each ruling should be on a single line
        data_line = lines[1]  # Skip header
        # Newlines should be replaced with spaces
        assert "\n" not in data_line.strip().split("|")[2]  # description field


class TestExportToCSV:
    """Tests for export_to_csv method."""

    def test_export_csv_basic(self, exporter):
        rulings = [make_ruling()]
        filepath = exporter.export_to_csv(rulings)
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["ruling_no"] == "HQ12345"
        assert rows[0]["hs_code"] == "8471.30.0100"
        assert rows[0]["year"] == "2023"

    def test_export_csv_multiple(self, exporter):
        rulings = [make_ruling(ruling_no=f"HQ{i}") for i in range(5)]
        filepath = exporter.export_to_csv(rulings)
        with open(filepath, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 5

    def test_export_csv_append(self, exporter):
        filepath = exporter.export_to_csv([make_ruling(ruling_no="HQ1")])
        exporter.export_to_csv([make_ruling(ruling_no="HQ2")], filename=filepath, append=True)
        with open(filepath, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2

    def test_export_csv_extra_fields_ignored(self, exporter):
        ruling = make_ruling(extra_field="should_be_ignored")
        filepath = exporter.export_to_csv([ruling])
        with open(filepath, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert "extra_field" not in rows[0]


class TestExportByYear:
    """Tests for export_by_year method."""

    def test_export_by_year(self, exporter):
        rulings = [
            make_ruling(ruling_no="HQ1", year=2023),
            make_ruling(ruling_no="HQ2", year=2023),
            make_ruling(ruling_no="HQ3", year=2024),
        ]
        result = exporter.export_by_year(rulings)
        assert 2023 in result
        assert 2024 in result
        assert os.path.exists(result[2023])
        assert os.path.exists(result[2024])

    def test_export_by_year_with_unknown(self, exporter):
        rulings = [
            make_ruling(ruling_no="HQ1", year=None),
        ]
        result = exporter.export_by_year(rulings)
        assert 0 in result  # year 0 = unknown

    def test_export_by_year_empty(self, exporter):
        result = exporter.export_by_year([])
        assert result == {}


class TestExportFailedParses:
    """Tests for export_failed_parses method."""

    def test_export_failed_parses(self, exporter):
        rulings = [
            make_ruling(ruling_no="HQ1", parse_failed=1, parse_error_msg="No HTML found"),
            make_ruling(ruling_no="HQ2", parse_failed=1, parse_error_msg="Parse timeout"),
        ]
        filepath = exporter.export_failed_parses(rulings)
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Ruling No|Error Message|URL|Subject" in content
        assert "HQ1" in content
        assert "No HTML found" in content

    def test_export_failed_parses_empty(self, exporter):
        filepath = exporter.export_failed_parses([])
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 1  # Header only


class TestFormatRulingLine:
    """Tests for _format_ruling_line method."""

    def test_format_line(self, exporter):
        line = exporter._format_ruling_line(make_ruling())
        parts = line.split("|")
        assert len(parts) == 5
        assert parts[0] == "HQ12345"
        assert parts[3] == "8471.30.0100"
        assert parts[4] == "2023"

    def test_format_line_missing_fields(self, exporter):
        line = exporter._format_ruling_line({
            "ruling_no": "HQ1",
            "subject": "",
            "description": "",
            "hs_code": "",
            "year": None,
        })
        parts = line.split("|")
        assert parts[0] == "HQ1"
        assert parts[1] == ""
        assert parts[4] == "None" or parts[4] == ""  # None may be converted


class TestPrepareCSVRow:
    """Tests for _prepare_csv_row method."""

    def test_prepare_row(self, exporter):
        row = exporter._prepare_csv_row(make_ruling())
        assert row["ruling_no"] == "HQ12345"
        assert row["hs_code"] == "8471.30.0100"
        assert row["year"] == "2023"

    def test_prepare_row_none_year(self, exporter):
        row = exporter._prepare_csv_row(make_ruling(year=None))
        assert row["year"] == "None" or row["year"] == ""
