from __future__ import annotations

import unittest

from scripts.probe_mof_announced_RON_primary_reference_auction_full_2025_source_vintage import (
    act_identity_checks,
    load_contract,
    romanian_date_anchor,
)


class MOFAnnouncedRONPrimaryReferenceAuctionFull2025SourceVintageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()

    def test_frozen_document_set_has_nine_base_orders_and_three_amendments(self) -> None:
        docs = self.contract["documents"]
        self.assertEqual(len(docs), 12)
        self.assertEqual(sum(x["version_role"] == "BASE" for x in docs), 9)
        self.assertEqual(sum(x["version_role"] == "AMENDMENT" for x in docs), 3)
        self.assertEqual(
            {x["month"] for x in docs if x["version_role"] == "BASE"},
            {f"2025-{month:02d}" for month in range(4, 13)},
        )

    def test_amendment_graph_is_frozen(self) -> None:
        self.assertEqual(
            self.contract["amendment_graph"]["2025-05"],
            ["728/2025", "752/2025"],
        )
        self.assertEqual(
            self.contract["amendment_graph"]["2025-11"],
            ["1795/2025", "1831/2025"],
        )
        self.assertEqual(
            self.contract["amendment_graph"]["2025-12"],
            ["1928/2025", "1998/2025"],
        )
        self.assertTrue(
            self.contract["amendment_graph"][
                "base_orders_may_not_be_silently_overwritten"
            ]
        )

    def test_no_document_id_guessing_is_authorized(self) -> None:
        discovery = self.contract["discovery"]
        self.assertTrue(discovery["fail_if_zero_matches"])
        self.assertTrue(discovery["fail_if_multiple_matches"])
        self.assertTrue(discovery["no_guessed_document_ids"])
        self.assertTrue(discovery["no_search_engine_snapshot_as_repository_source"])

    def test_partial_retention_cannot_impute_or_promote(self) -> None:
        retention = self.contract["retention"]
        self.assertTrue(retention["partial_official_retention_allowed"])
        self.assertTrue(retention["unavailable_sources_must_remain_unavailable"])
        self.assertTrue(
            retention["event_materialisation_allowed_only_for_retained_raw_sources"]
        )
        self.assertTrue(
            retention["canonical_promotion_requires_complete_required_source_coverage"]
        )


    def test_hard_rules_keep_model_inactive(self) -> None:
        rules = self.contract["hard_rules"]
        for key in (
            "no_event_materialisation_in_discovery_probe",
            "no_SSON_in_full_year_canonical_candidate",
            "no_accepted_or_borrowed_values",
            "no_retail_or_external_issuance",
            "no_manual_approximation",
            "no_OCR",
            "no_canonical_reference_mode_promotion",
            "no_yield_effect_estimation",
            "no_feedback_activation",
            "no_behavioural_closure_change",
            "no_public_version_change",
        ):
            self.assertTrue(rules[key], key)

    def test_identity_check_accepts_thousands_separator_order_number(self) -> None:
        document = next(
            x for x in self.contract["documents"]
            if x["source_id"] == "mof_order_1626_october_2025"
        )
        text = """
        ORDIN nr. 1.626 din 1 octombrie 2025
        privind prospectele de emisiune a certificatelor de trezorerie
        si a obligatiunilor de stat de tip benchmark aferente lunii octombrie 2025
        EMITENT MINISTERUL FINANTELOR
        """
        checks = act_identity_checks(text, document)
        self.assertTrue(all(checks.values()))

    def test_romanian_date_anchor_is_deterministic(self) -> None:
        self.assertEqual(romanian_date_anchor("2025-11-10"), "10 noiembrie 2025")
        self.assertEqual(romanian_date_anchor("2025-03-31"), "31 martie 2025")


if __name__ == "__main__":
    unittest.main()
