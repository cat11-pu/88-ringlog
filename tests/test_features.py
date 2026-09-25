import os
import tempfile
import time
import unittest

from ringlog import Journal


class FeatureTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "state.json")

    def tearDown(self):
        self.tmp.cleanup()

    def journal(self):
        return Journal(state_path=self.path)

    def test_replay_is_idempotent(self):
        journal = self.journal()
        journal.append("o1", "put")
        journal.append("o2", "put")
        self.assertEqual(journal.replay()["replayed"], 2)
        self.assertEqual(journal.replay()["replayed"], 0)
        self.assertEqual(journal.replay()["applied"], ["o1", "o2"])

    def test_duplicate_op_id_applied_once(self):
        journal = self.journal()
        journal.append("o1", "put")
        journal.append("o1", "put")
        self.assertEqual(journal.replay()["replayed"], 1)
        self.assertEqual(journal.replay()["replayed"], 0)

    def test_replay_only_after_checkpoint(self):
        journal = self.journal()
        for i in range(1, 4):
            journal.append("o%d" % i, "put")
        self.assertEqual(journal.checkpoint()["checkpoint"], 3)
        journal.append("o4", "put")
        journal.append("o5", "put")
        self.assertEqual(journal.replay()["replayed"], 2)
        self.assertEqual(journal.replay()["replayed"], 0)
        self.assertEqual(journal.stats()["applied"], 2)

    def test_truncate_keeps_post_checkpoint_records(self):
        journal = self.journal()
        for i in range(1, 4):
            journal.append("o%d" % i, "put")
        journal.checkpoint()
        journal.append("o4", "put")
        journal.append("o5", "put")
        result = journal.truncate()
        self.assertEqual(result, {"removed": 3, "checkpoint": 3})
        self.assertEqual(len(journal.records), 2)
        self.assertEqual(journal.replay()["replayed"], 2)
        self.assertEqual(journal.truncate()["removed"], 0)

    def test_persist_restore_roundtrip(self):
        journal = self.journal()
        journal.append("o1", "put")
        journal.append("o2", "put")
        journal.checkpoint()
        journal.append("o3", "del")
        journal.replay()
        journal.truncate()
        blob = journal.persist()["blob"]

        restarted = self.journal()
        restarted.restore(blob)
        self.assertEqual(restored_checkpoint(restarted), 2)
        self.assertEqual(restarted.records, journal.records)
        self.assertEqual(restarted.applied, {"o3"})
        self.assertEqual(restarted.offset, journal.offset)
        self.assertEqual(restarted.truncated, 2)
        self.assertEqual(restarted.replay()["replayed"], 0)

    def test_recover_empty_without_snapshot(self):
        journal = self.journal()
        journal.append("o1", "put")
        journal.checkpoint()
        result = journal.recover()
        self.assertEqual(result["checkpoint"], 0)
        self.assertFalse(result["restored"])

    def test_recover_after_persist(self):
        journal = self.journal()
        journal.append("o1", "put")
        journal.checkpoint()
        journal.persist()
        restarted = self.journal()
        result = restarted.recover()
        self.assertTrue(result["restored"])
        self.assertEqual(result["checkpoint"], 1)

    def test_replay_complexity_is_suffix_only(self):
        journal = self.journal()
        for i in range(100000):
            journal.append("o%d" % i, "put")
        journal.checkpoint()
        for i in range(100000, 100050):
            journal.append("o%d" % i, "put")
        started = time.perf_counter()
        self.assertEqual(journal.replay()["replayed"], 50)
        self.assertLess(time.perf_counter() - started, 1.0)


def restored_checkpoint(journal):
    return journal.checkpoint_pos


if __name__ == "__main__":
    unittest.main()
