"""Stage 2 books its own work items the way Stages 1 and 3 register theirs."""

from __future__ import annotations

import unittest
from unittest import mock

from tests.pr_lifecycle_helpers import (
    import_lifecycle_run,
    make_ledger,
    make_work_item,
)

import_lifecycle_run()

import pr_lifecycle_stage_plan as plan  # noqa: E402

SHA = "a" * 40
HEAD = "b" * 40


def _owned(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "key": f"abhimehro/demo#8@{HEAD}",
        "repository": "abhimehro/demo",
        "pr": 8,
        "base_sha": SHA,
        "head_sha": HEAD,
        "changed_paths": ["src/demo.py"],
        "current_owner": "stage2",
        "lifecycle_state": "STAGE2_QUEUED",
        "author_type": "BOT",
        "guardrail_outcome": "HOLD_CONTRACT",
    }
    item.update(overrides)
    return item


class Stage2BookingTests(unittest.TestCase):
    def test_stage2_books_an_owned_item_that_is_not_yet_a_work_item(self) -> None:
        item = _owned()
        ledger = make_ledger([item], [])
        actions = plan.plan_stage2_bookings(ledger)
        self.assertEqual(len(actions), 1)
        action = actions[0]
        self.assertEqual(action["action"], "BOOK_STAGE2_WI")
        self.assertEqual(action["reason"], "STAGE2_BOOK_OWNED")
        self.assertEqual(action["source_key"], item["key"])
        self.assertEqual(action["repository"], "abhimehro/demo")
        self.assertEqual(action["pr"], 8)
        self.assertEqual(action["base_sha"], SHA)
        self.assertEqual(action["head_sha"], HEAD)
        self.assertEqual(action["allowed_paths"], ["src/demo.py"])
        self.assertEqual(ledger["items"], [item])
        self.assertEqual(ledger["stage2_work_items"], [])

    def test_stage1_and_stage3_items_are_not_booked_by_stage2(self) -> None:
        stage1 = _owned(current_owner="stage1", lifecycle_state="STAGE1_INTAKE")
        stage3 = _owned(
            key=f"abhimehro/demo#9@{HEAD}",
            pr=9,
            current_owner="stage3",
            lifecycle_state="STAGE3_RECONCILIATION",
        )
        self.assertEqual(
            plan.plan_stage2_bookings(make_ledger([stage1, stage3], [])), []
        )

    def test_already_registered_and_never_touch_and_incomplete_are_skipped(
        self,
    ) -> None:
        owned = _owned()
        registered = make_work_item(
            source_item_key=owned["key"],
            repository="abhimehro/demo",
            pr=8,
            base_sha=SHA,
            head_sha=HEAD,
            expiry_utc="2999-01-01T00:00:00Z",
        )
        never = _owned(
            key="abhimehro/Seatek_Analysis#692@" + HEAD,
            repository="abhimehro/Seatek_Analysis",
            pr=692,
        )
        incomplete = _owned(
            key=f"abhimehro/demo#10@{HEAD}",
            pr=10,
            changed_paths=[],
        )
        self.assertEqual(
            plan.plan_stage2_bookings(make_ledger([owned], [registered])), []
        )
        self.assertEqual(plan.plan_stage2_bookings(make_ledger([never], [])), [])
        self.assertEqual(plan.plan_stage2_bookings(make_ledger([incomplete], [])), [])

    def test_stage2_plan_emits_booking_when_the_feed_is_empty(self) -> None:
        ledger = make_ledger([_owned()], [])
        allowed, actions, stop, reason, extras = plan._stage2_plan(
            ledger, {"lifecycle": {}}
        )
        self.assertIn(
            "BOOK_STAGE2_WI for Stage 2-owned items that are not yet registered",
            allowed,
        )
        self.assertIsNone(stop)
        self.assertEqual(reason, "OK")
        self.assertEqual(extras["stage2_booking_count"], 1)
        self.assertEqual([action["action"] for action in actions], ["BOOK_STAGE2_WI"])
        self.assertEqual(ledger["stage2_work_items"], [])

    def test_owned_state_books_without_a_stage2_owner(self) -> None:
        item = _owned(current_owner="stage1", lifecycle_state="STAGE2_ACTIVE")
        actions = plan.plan_stage2_bookings(make_ledger([item], []))
        self.assertEqual([action["action"] for action in actions], ["BOOK_STAGE2_WI"])

    def test_human_security_and_closed_items_are_not_booked(self) -> None:
        human = _owned(author_type="HUMAN")
        security = _owned(
            key=f"abhimehro/demo#11@{HEAD}",
            pr=11,
            guardrail_outcome="REVIEW_SECURITY",
            sensitive_paths=["shell_execution"],
        )
        closed = _owned(key=f"abhimehro/demo#12@{HEAD}", pr=12)
        signals = plan.health.ReselectSignals(closed_keys=frozenset({closed["key"]}))
        actions = plan.plan_stage2_bookings(
            make_ledger([human, security, closed], []), signals=signals
        )
        self.assertEqual(actions, [])

    def test_closed_prefix_and_unqueried_keys_are_not_booked(self) -> None:
        item = _owned()
        prefix = str(item["key"]).split("@", 1)[0]
        closed = plan.health.ReselectSignals(closed_keys=frozenset({prefix}))
        unseen = plan.health.ReselectSignals(unqueried_keys=frozenset({item["key"]}))
        self.assertEqual(
            plan.plan_stage2_bookings(make_ledger([item], []), signals=closed), []
        )
        self.assertEqual(
            plan.plan_stage2_bookings(make_ledger([item], []), signals=unseen), []
        )

    def test_eligible_stock_stops_even_when_a_booking_exists(self) -> None:
        ledger = make_ledger([_owned()], [])

        def fake_feed(*_args: object, **_kwargs: object) -> dict[str, object]:
            return {
                "reason": "EMPTY",
                "work_item_count": 0,
                "eligible_stock_count": 1,
                "non_never_touch_stock_count": 1,
                "work_items": [],
            }

        with mock.patch.object(plan.feed_mod, "build_feed", fake_feed):
            _allowed, actions, stop, reason, extras = plan._stage2_plan(
                ledger, {"lifecycle": {}}
            )
        self.assertEqual(stop, "LOGIC_STOP")
        self.assertEqual(reason, "EMPTY_FEED_WITH_ELIGIBLE_STOCK")
        self.assertEqual(actions[0]["action"], "FEED_SUMMARY")
        self.assertEqual(extras["stage2_booking_count"], 1)

    def test_booking_cap_matches_the_stage2_candidate_cap(self) -> None:
        items = [_owned(key=f"abhimehro/demo#{n}@{HEAD}", pr=n) for n in range(1, 5)]
        actions = plan.plan_stage2_bookings(make_ledger(items, []), limit=2)
        self.assertEqual([action["pr"] for action in actions], [1, 2])


if __name__ == "__main__":
    unittest.main()
