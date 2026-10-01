import threading
import unittest

from burnharness.ignition_layer.legs.sentinel_dot.ignition_stub import (
    SentinelDotIgnitionStub,
)
from companion import Companion
from couplers.orrery_sentinel_dot.coupler import OrrerySentinelDotCoupler
from coordinator import SentinelDotCoordinator


class SentinelDotCoordinatorTests(unittest.TestCase):
    def test_instances_wait_then_fire_with_the_same_block_id(self):
        coordinator = SentinelDotCoordinator()
        sentinels = {
            instance_id: SentinelDotIgnitionStub()
            for instance_id in coordinator.instance_ids
        }
        releases = {}
        first_ready = threading.Event()

        def activate(instance_id):
            if instance_id == coordinator.instance_ids[0]:
                first_ready.set()
            release = coordinator.report_alignment(
                instance_id,
                p_i="position",
                p_j="position",
                a_i="alignment",
                a_j="alignment",
                timeout=2,
            )
            releases[instance_id] = release
            sentinels[instance_id].fire(coordinator, release, instance_id)

        first = threading.Thread(
            target=activate, args=(coordinator.instance_ids[0],)
        )
        first.start()
        self.assertTrue(first_ready.wait(1))
        self.assertIsNone(sentinels[coordinator.instance_ids[0]].fire_record)
        self.assertTrue(coordinator.state["barrier_blocking"])
        self.assertFalse(coordinator.state["superposition_integrity"])

        second = threading.Thread(
            target=activate, args=(coordinator.instance_ids[1],)
        )
        second.start()
        first.join(2)
        second.join(2)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())

        records = [sentinel.fire_record for sentinel in sentinels.values()]
        self.assertTrue(all(record["fired"] for record in records))
        self.assertEqual(records[0]["block_id"], records[1]["block_id"])
        self.assertEqual(len(records[0]["block_id"]), 128)
        self.assertIs(
            releases[coordinator.instance_ids[0]],
            releases[coordinator.instance_ids[1]],
        )
        self.assertTrue(coordinator.state["barrier_blocking"])
        self.assertTrue(coordinator.state["barrier_released"])
        self.assertTrue(coordinator.state["superposition_integrity"])

    def test_misalignment_does_not_report_ready(self):
        coordinator = SentinelDotCoordinator()
        release = coordinator.report_alignment(
            coordinator.instance_ids[0],
            p_i=1,
            p_j=2,
            a_i="same",
            a_j="same",
            timeout=0.01,
        )
        self.assertIsNone(release)
        self.assertEqual(coordinator.state["ready_instances"], ())

    def test_aligned_couplers_report_both_instances_to_the_barrier(self):
        class Leg:
            def ignite(self):
                return {"p": "position", "a": "alignment"}

        coordinator = SentinelDotCoordinator()
        results = {}

        def couple(instance_id):
            coupler = OrrerySentinelDotCoupler(
                Leg(), Leg(), coordinator=coordinator,
                sentinel_instance_id=instance_id, timeout=2,
            )
            results[instance_id] = coupler.couple()

        threads = [
            threading.Thread(target=couple, args=(instance_id,))
            for instance_id in coordinator.instance_ids
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(2)
            self.assertFalse(thread.is_alive())

        releases = [
            results[instance_id]["sentinel_release"]
            for instance_id in coordinator.instance_ids
        ]
        self.assertTrue(
            all(results[instance_id]["sentinel_ready"]
                for instance_id in coordinator.instance_ids)
        )
        self.assertIs(releases[0], releases[1])

    def test_sentinel_rejects_unreleased_barrier_data(self):
        sentinel = SentinelDotIgnitionStub()
        coordinator = SentinelDotCoordinator()
        with self.assertRaises(RuntimeError):
            sentinel.fire(coordinator, object(), coordinator.instance_ids[0])

    def test_companion_integrity_requires_both_instances_to_pass_barrier(self):
        companion = Companion()
        valid_system_state = {
            "paths_valid": True,
            "imports_valid": True,
            "load_order_locked": True,
        }
        self.assertFalse(companion.superposition_integrity(valid_system_state))
        coordinator = SentinelDotCoordinator()
        self.assertFalse(
            companion.superposition_integrity(valid_system_state, coordinator.state)
        )


if __name__ == "__main__":
    unittest.main()
