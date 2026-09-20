from __future__ import annotations

import unittest

from scripts.probe_mof_announced_RON_primary_reference_auction_missing_official_pdfs import (
    MISSING_SOURCE_IDS,
    candidate_urls,
    identity_checks,
    load_contract,
)


class MOFMissingOfficialPDFProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        contract = load_contract()
        self.docs = {item["source_id"]: item for item in contract["documents"]}

    def test_scope_is_exactly_eight_currently_missing_sources(self) -> None:
        self.assertEqual(len(MISSING_SOURCE_IDS), 8)
        self.assertEqual(
            MISSING_SOURCE_IDS,
            {
                "mof_order_752_may_2025_amendment",
                "mof_order_1088_july_2025",
                "mof_order_1221_august_2025",
                "mof_order_1452_september_2025",
                "mof_order_1795_november_2025",
                "mof_order_1831_november_2025_amendment",
                "mof_order_1928_december_2025",
                "mof_order_1998_december_2025_amendment",
            },
        )

    def test_december_base_has_exact_web_verified_anaf_candidate(self) -> None:
        urls = candidate_urls("mof_order_1928_december_2025")
        self.assertIn(
            {
                "url": "https://static.anaf.ro/static/10/Anaf/legislatie/OMF_1928_2025.pdf",
                "discovery_basis": "EXACT_WEB_VERIFIED_OFFICIAL_PDF",
            },
            urls,
        )

    def test_pattern_candidates_are_never_labelled_web_verified(self) -> None:
        for source_id in MISSING_SOURCE_IDS - {"mof_order_1928_december_2025"}:
            for candidate in candidate_urls(source_id):
                self.assertNotEqual(
                    candidate["discovery_basis"],
                    "EXACT_WEB_VERIFIED_OFFICIAL_PDF",
                )

    def test_base_identity_requires_order_date_ministry_title_month_and_publication(self) -> None:
        doc = self.docs["mof_order_1088_july_2025"]
        text = """
        MINISTERUL FINANȚELOR
        ORDIN Nr. 1.088 din 30 iunie 2025
        privind prospectele de emisiune a certificatelor de trezorerie și
        a obligațiunilor de stat de tip benchmark aferente lunii iulie 2025
        Publicat în: Monitorul Oficial Nr. 622 din 2 iulie 2025
        """
        checks = identity_checks(text, doc)
        self.assertTrue(all(checks.values()))

    def test_amendment_identity_requires_superseded_order(self) -> None:
        doc = self.docs["mof_order_1831_november_2025_amendment"]
        text = """
        MINISTERUL FINANȚELOR
        ORDIN Nr. 1.831 din 10 noiembrie 2025
        pentru modificarea Ordinului ministrului finanțelor nr. 1.795/2025
        privind prospectele de emisiune aferente lunii noiembrie 2025
        Publicat în: Monitorul Oficial Nr. 1041 din 11 noiembrie 2025
        """
        checks = identity_checks(text, doc)
        self.assertTrue(all(checks.values()))

    def test_dotted_monitorul_oficial_number_is_accepted(self) -> None:
        doc = self.docs["mof_order_1928_december_2025"]
        text = """
        Ministerul Finanţelor
        ORDIN Nr. 1.928 din 2 decembrie 2025
        privind prospectele de emisiune a obligaţiunilor de stat de tip benchmark
        aferente lunii decembrie 2025
        Publicat în: Monitorul Oficial Nr. 1.114 din 3 decembrie 2025
        """
        checks = identity_checks(text, doc)
        self.assertTrue(all(checks.values()))

    def test_wrong_month_fails_identity(self) -> None:
        doc = self.docs["mof_order_1452_september_2025"]
        text = """
        MINISTERUL FINANȚELOR
        ORDIN Nr. 1.452 din 29 august 2025
        privind prospectele de emisiune aferente lunii august 2025
        Publicat în: Monitorul Oficial Nr. 806 din 29 august 2025
        """
        checks = identity_checks(text, doc)
        self.assertFalse(checks["month_anchor"])


if __name__ == "__main__":
    unittest.main()
