from __future__ import annotations

from typing import TYPE_CHECKING

from scripts.complete_refresh_exhibits import SharedClient

if TYPE_CHECKING:
    from pathlib import Path


def test_same_submission_reuses_verified_bytes_across_cofiler_company_ids(tmp_path: Path) -> None:
    accession = "000000012326000001"
    first = f"https://www.sec.gov/Archives/edgar/data/123/{accession}/index.json"
    second = f"https://www.sec.gov/Archives/edgar/data/456/{accession}/index.json"
    raw = f"""<table summary="Document Format Files"><tr><td>1</td><td>Results</td>
    <td><a href="/Archives/edgar/data/789/{accession}/results.htm">results.htm</a></td>
    <td>EX-99.1</td><td>100</td></tr></table>""".encode()
    client = SharedClient(tmp_path, 1, "test")
    calls = []
    client.get = lambda url: (calls.append(url), raw)[1]
    try:
        one, two = client.json(first), client.json(second)
        assert len(calls) == 1
        assert one == two
        assert one["directory"]["item"][0]["document_url"].endswith(f"/789/{accession}/results.htm")
        assert client.index_cache_hits == 1
    finally:
        client.client.close()
    resumed = SharedClient(tmp_path, 1, "test")
    resumed.get = lambda _url: (_ for _ in ()).throw(
        AssertionError("Cached submission must not refetch")
    )
    try:
        assert resumed.json(second) == one
        assert resumed.index_cache_hits == 1
    finally:
        resumed.client.close()
