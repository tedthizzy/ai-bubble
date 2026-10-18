import pytest

from bubble.ingestion.sources.pjm import PAGE, public_export_headers


def test_public_export_header_comes_from_publisher_bundle():
    pages = {
        PAGE: '<script src="/dist/interconnectionqueues.current.js"></script>',
        "https://www.pjm.com/dist/interconnectionqueues.current.js": '{"api-subscription-key":"anonymous-public-identifier"}',
    }
    headers = public_export_headers(pages.__getitem__)
    assert headers["api-subscription-key"] == "anonymous-public-identifier"
    assert headers["Origin"] == "https://www.pjm.com"


def test_public_export_rejects_an_external_script():
    with pytest.raises(ValueError, match="publisher"):
        public_export_headers(
            lambda _: (
                '<script src="https://other.test/dist/interconnectionqueues.current.js"></script>'
            )
        )
