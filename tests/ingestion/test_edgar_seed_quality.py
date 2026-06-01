from bubble.ingestion.edgar.seeds import PRIVATE_SEEDS, PUBLIC_SEEDS, WATCHLIST_CIKS


def test_public_edgar_seed_ciks_are_curated_away_from_known_bad_mappings() -> None:
    bad_ciks = {
        "0001065353",  # not Oracle
        "0001703399",  # not Snowflake
        "0001773383",  # not Datadog
        "0001705696",  # VICI, not Vantage
        "0001783879",  # Robinhood, not CoreWeave
        "0001660280",  # Tenable, not Stack Infrastructure
        "0001766526",  # not Aligned Data Centers
        "0001839412",  # not Crusoe Energy
        "0001842952",  # not Groq
        "0001212545",  # Western Alliance, not KKR
        "0001690820",  # Carvana, not Vistra
        "0001713683",  # Zscaler, not Constellation Energy
        "0000072971",  # Wells Fargo, not Siemens
    }

    assert bad_ciks.isdisjoint(PUBLIC_SEEDS)


def test_public_edgar_seed_ciks_include_verified_core_watchlist_entries() -> None:
    expected = {
        "0001341439": "Oracle",
        "0001640147": "Snowflake",
        "0001561550": "Datadog",
        "0001769628": "CoreWeave",
        "0001858681": "Apollo Global Management",
        "0001393818": "Blackstone",
        "0001404912": "KKR",
        "0001692819": "Vistra",
        "0001868275": "Constellation Energy",
        "0001622536": "Talen Energy",
        "0001996810": "General Electric (GE Vernova)",
        "0001830056": "Siemens Energy",
        "0001551182": "Eaton",
        "0001674101": "Vertiv",
    }

    assert {cik: PUBLIC_SEEDS[cik]["name"] for cik in expected} == expected


def test_private_entities_without_reliable_public_company_ciks_stay_out_of_public_watchlist() -> (
    None
):
    private_names = {seed["name"] for seed in PRIVATE_SEEDS}
    public_names = {seed["name"] for seed in PUBLIC_SEEDS.values()}

    assert {"Vantage Data Centers", "CyrusOne", "QTS Realty", "Lambda Labs", "Groq"} <= (
        private_names
    )
    assert private_names.isdisjoint(public_names)
    assert list(PUBLIC_SEEDS) == WATCHLIST_CIKS
