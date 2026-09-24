import json
import threading
import unittest
import urllib.error
import urllib.request

from ringlog import Journal
from server import serve

class TestJournal(unittest.TestCase):
    def test_append_counts(self):
        journal = Journal()
        self.assertEqual(journal.append("o1", "put")["records"], 1)

    def test_replay_empty(self):
        self.assertEqual(Journal().replay()["replayed"], 0)

    def test_replay_counts_records(self):
        journal = Journal()
        journal.append("o1", "put")
        journal.append("o2", "put")
        self.assertEqual(journal.replay()["replayed"], 2)

    def test_stats_shape(self):
        self.assertIn("capacity", Journal().stats())

    def test_http_append_replay(self):
        server = serve(0)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % server.server_port
        urllib.request.urlopen(base + "/append", data=b'{"id": "o1", "op": "put"}', timeout=5).read()
        with urllib.request.urlopen(base + "/replay", data=b"{}", timeout=5) as response:
            self.assertEqual(json.loads(response.read())["replayed"], 1)
        server.shutdown()
