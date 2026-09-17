from __future__ import annotations

import csv
import gzip
import io
import json
import tarfile
from datetime import date
from pathlib import Path

from scripts.stream_edgar_feed_day import stream_day, submission_documents


def _fixture(tmp_path: Path, *, extra_master: bool = False):
    day = date(2026, 6, 10)
    accession = "0000001234-26-000001"
    raw = (
        b"0" * 266
        + b"<SUBMISSION>\n<ACCESSION-NUMBER>0000001234-26-000001\n"
        + b"<DOCUMENT>\n<TYPE>8-K\n<FILENAME>main.htm\n<TEXT>\n"
        + b"<html>main filing</html>\n</TEXT>\n</DOCUMENT>\n"
        + b"<DOCUMENT>\n<TYPE>EX-10.1\n<FILENAME>agreement.htm\n<TEXT>\n"
        + b"<html>credit agreement</html>\n</TEXT>\n</DOCUMENT>\n</SUBMISSION>"
    )
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
        member = tarfile.TarInfo(f"./{accession}.nc")
        member.size = len(raw)
        archive.addfile(member, io.BytesIO(raw))
    compressed = gzip.compress(tar_buffer.getvalue())
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "cik", "company_name", "form", "accession_number", "filing_date",
            "primary_document", "filing_url", "relevance_score", "relevance_reasons",
            "document_type", "size_bytes",
        ])
        writer.writeheader()
        writer.writerow({
            "cik": "0000001234", "company_name": "Example Corp", "form": "8-K",
            "accession_number": accession, "filing_date": day.isoformat(),
            "primary_document": "main.htm",
            "filing_url": "https://www.sec.gov/Archives/edgar/data/1234/000000123426000001/main.htm",
            "relevance_score": "80", "relevance_reasons": "test", "document_type": "primary",
        })
    master = tmp_path / "master.idx"
    rows = [
        "Description: test", "CIK|Company Name|Form Type|Date Filed|Filename",
        f"1234|Example Corp|8-K|{day.isoformat()}|edgar/data/1234/{accession}.txt",
    ]
    if extra_master:
        rows.append(f"5678|Another Corp|8-K|{day.isoformat()}|edgar/data/5678/0000005678-26-000002.txt")
    master.write_text("\n".join(rows) + "\n")
    return day, compressed, manifest, master


def test_stream_day_extracts_primary_and_exhibit_and_reconciles(tmp_path):
    day, compressed, manifest, master = _fixture(tmp_path)
    output_dir = tmp_path / "output"
    summary = stream_day(
        io.BytesIO(compressed),
        archive_url="https://www.sec.gov/Archives/edgar/Feed/2026/QTR2/20260610.nc.tar.gz",
        manifest_csv=manifest,
        master_index=master,
        day=day,
        output_dir=output_dir,
        expected_compressed_bytes=len(compressed),
    )
    assert summary["reconciled"] is True
    assert summary["feed_accessions"] == 1
    assert summary["selected_documents_extracted"] == 2
    assert summary["exhibit_documents_extracted"] == 1
    with (output_dir / "feed_document_manifest.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert {row["primary_document"] for row in rows} == {"main.htm", "agreement.htm"}
    exhibit = next(row for row in rows if row["document_type"] == "exhibit")
    assert exhibit["filing_url"].endswith("/agreement.htm")
    local = output_dir / "documents" / "0000001234" / "000000123426000001" / "agreement.htm.gz"
    assert b"credit agreement" in gzip.decompress(local.read_bytes())
    assert json.loads((output_dir / "feed_stream_summary.json").read_text())["reconciled"]


def test_submission_parser_accepts_sec_feed_carriage_return_lines():
    raw = (
        b"<SUBMISSION>\r<DOCUMENT>\r<TYPE>8-K\r<SEQUENCE>1\r<FILENAME>main.htm\r"
        b"<TEXT>\r<html>main</html>\r</TEXT>\r</DOCUMENT>\r"
        b"<DOCUMENT>\r<TYPE>EX-10.1\r<FILENAME>agreement.htm\r"
        b"<TEXT>\r<html>agreement</html>\r</TEXT>\r</DOCUMENT></SUBMISSION>"
    )
    assert [(kind, name) for kind, name, _ in submission_documents(raw)] == [
        ("8-K", "main.htm"), ("EX-10.1", "agreement.htm"),
    ]


def test_stream_day_reports_master_accession_missing_from_feed(tmp_path):
    day, compressed, manifest, master = _fixture(tmp_path, extra_master=True)
    summary = stream_day(
        io.BytesIO(compressed),
        archive_url="https://www.sec.gov/Archives/edgar/Feed/2026/QTR2/20260610.nc.tar.gz",
        manifest_csv=manifest,
        master_index=master,
        day=day,
        output_dir=tmp_path / "output",
    )
    assert summary["reconciled"] is False
    assert summary["missing_from_feed"] == ["0000005678-26-000002"]


def test_stream_day_preserves_all_index_metadata_and_hashes_unselected_members(tmp_path):
    day, compressed, manifest, master = _fixture(tmp_path)
    additions = [
        ("0000005678-26-000002", "8-K", "second.htm", b"<html>second filing</html>"),
        ("0000009012-26-000003", "4", "form4.xml", b"<form4>holdings</form4>"),
        ("0000003456-26-000004", "DEF 14A", "proxy.htm", b"<html>data center proxy</html>"),
    ]
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=io.BytesIO(gzip.decompress(compressed)), mode="r") as original:
        with tarfile.open(fileobj=tar_buffer, mode="w") as archive:
            for member in original:
                archive.addfile(member, original.extractfile(member))
            for accession, form, filename, content in additions:
                payload = (
                    f"<SUBMISSION><ACCESSION-NUMBER>{accession}\n<DOCUMENT>\n<TYPE>{form}\n"
                    f"<FILENAME>{filename}\n<TEXT>\n"
                ).encode() + content + b"\n</TEXT>\n</DOCUMENT></SUBMISSION>"
                member = tarfile.TarInfo(f"./{accession}.nc")
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
    with master.open("a") as stream:
        for accession, form, _, _ in additions:
            cik = str(int(accession[:10]))
            stream.write(f"{cik}|Extra {cik}|{form}|{day.isoformat()}|edgar/data/{cik}/{accession}.txt\n")
    exact_ciks = tmp_path / "exact.csv"
    exact_ciks.write_text("cik\n0000009012\n")
    output_dir = tmp_path / "output"
    summary = stream_day(
        io.BytesIO(gzip.compress(tar_buffer.getvalue())),
        archive_url="https://www.sec.gov/Archives/edgar/Feed/2026/QTR2/20260610.nc.tar.gz",
        manifest_csv=manifest,
        master_index=master,
        day=day,
        output_dir=output_dir,
        extra_cik_csv=exact_ciks,
    )
    assert summary["reconciled"]
    assert summary["master_accessions"] == 4
    assert summary["feed_accessions"] == 4
    assert summary["member_hashes_recorded"] == 4
    assert summary["index_only_candidate_accessions"] == 2
    assert summary["other_form_content_pending_accessions"] == 1
    with (output_dir / "master_day_rows.csv").open(newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 4
    with (output_dir / "feed_member_inventory.csv").open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 4
    assert all(len(row["member_sha256"]) == 64 for row in rows)
    proxy = next(row for row in rows if row["form"] == "DEF 14A")
    assert proxy["content_selected"] == "False"
    assert proxy["signature_screened"] == "True"
    assert proxy["signature_hits"] == "data_center"
    with (output_dir / "feed_document_metadata.csv").open(newline="") as stream:
        metadata = list(csv.DictReader(stream))
    assert len(metadata) == 5
    with (output_dir / "feed_content_candidate_queue.csv").open(newline="") as stream:
        queue = list(csv.DictReader(stream))
    assert len(queue) == 1
    assert queue[0]["accession_number"] == "0000003456-26-000004"
    with (output_dir / "feed_document_manifest.csv").open(newline="") as stream:
        documents = list(csv.DictReader(stream))
    assert {row["primary_document"] for row in documents} == {
        "main.htm", "agreement.htm", "second.htm", "form4.xml",
    }


def test_master_index_preserves_multiple_cik_rows_for_one_accession(tmp_path):
    day, compressed, manifest, master = _fixture(tmp_path)
    with master.open("a") as stream:
        stream.write(
            f"5678|Second Indexed Entity|8-K|{day.isoformat()}|"
            "edgar/data/5678/0000001234-26-000001.txt\n"
        )
    output_dir = tmp_path / "output"
    summary = stream_day(
        io.BytesIO(compressed),
        archive_url="https://www.sec.gov/Archives/edgar/Feed/2026/QTR2/20260610.nc.tar.gz",
        manifest_csv=manifest,
        master_index=master,
        day=day,
        output_dir=output_dir,
    )
    assert summary["master_accessions"] == 1
    assert summary["master_filing_rows"] == 2
    with (output_dir / "master_day_rows.csv").open(newline="") as stream:
        assert len(list(csv.DictReader(stream))) == 2
