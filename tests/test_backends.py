import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from jevroute.backends import BackendError, HttpBackend, MockBackend, get_backend, validate_answers
from jevroute.questions import build_request, build_state


def good_answers():
    return MockBackend().ask(build_request(build_state({"prompt": "find the config"})))[0]


class FakeJev(BaseHTTPRequestHandler):
    script = []      # list of (status, body, delay_s) consumed per request
    received = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeJev.received.append((dict(self.headers), body))
        status, payload, delay = FakeJev.script.pop(0)
        if delay:
            import time
            time.sleep(delay)
        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except BrokenPipeError:
            pass

    def log_message(self, *a):
        pass


class HttpBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeJev)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/v1/systemone"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        FakeJev.script, FakeJev.received = [], []

    def backend(self, deadline=2.0):
        return HttpBackend("test-key", url=self.url, deadline_s=deadline)

    def ok(self):
        return {"model": "jev-1.13.0", "answers": good_answers(), "usage": {"input_tokens": 500, "output_tokens": 0}}

    def test_success_and_request_shape(self):
        FakeJev.script = [(200, self.ok(), 0)]
        answers, raw = self.backend().ask(build_request(build_state({"prompt": "x", "description": "d"})))
        self.assertEqual(raw["model"], "jev-1.13.0")
        headers, body = FakeJev.received[0]
        self.assertEqual(headers["Authorization"], "Bearer test-key")
        self.assertEqual(set(body), {"state", "model", "questions"})
        self.assertEqual(body["model"], "jev-latest")
        self.assertEqual(body["questions"]["kind"]["type"], "choice")

    def test_retries_429_then_succeeds(self):
        FakeJev.script = [(429, {"error": "rate"}, 0), (529, {"error": "busy"}, 0), (200, self.ok(), 0)]
        self.backend().ask(build_request(build_state({"prompt": "x"})))
        self.assertEqual(len(FakeJev.received), 3)

    def test_timeout_raises(self):
        FakeJev.script = [(200, self.ok(), 1.0)]
        with self.assertRaises(BackendError):
            self.backend(deadline=0.3).ask(build_request(build_state({"prompt": "x"})))

    def test_server_error_raises_without_retry(self):
        FakeJev.script = [(500, {"error": "boom"}, 0)]
        with self.assertRaises(BackendError):
            self.backend().ask(build_request(build_state({"prompt": "x"})))
        self.assertEqual(len(FakeJev.received), 1)

    def test_malformed_body_raises(self):
        FakeJev.script = [(200, b"not json", 0)]
        with self.assertRaises(BackendError):
            self.backend().ask(build_request(build_state({"prompt": "x"})))

    def test_missing_answer_raises(self):
        bad = self.ok()
        del bad["answers"]["novelty"]
        FakeJev.script = [(200, bad, 0)]
        with self.assertRaises(BackendError):
            self.backend().ask(build_request(build_state({"prompt": "x"})))


class MiscTest(unittest.TestCase):
    def test_validate_rejects_unknown_choice(self):
        a = good_answers()
        a["kind"]["choice"] = "dance"
        with self.assertRaises(BackendError):
            validate_answers(a)

    def test_get_backend_selection(self):
        self.assertEqual(get_backend({}).name, "mock")
        self.assertEqual(get_backend({"TYPESAFE_API_KEY": "k"}).name, "http")
        self.assertEqual(get_backend({"TYPESAFE_API_KEY": "k", "JEV_BACKEND": "mock"}).name, "mock")
        with self.assertRaises(BackendError):
            get_backend({"JEV_BACKEND": "http"})

    def test_state_truncates_long_prompt(self):
        s = build_state({"prompt": "x" * 10000})
        self.assertLess(len(s["task"]), 6100)

    def test_mock_handles_japanese(self):
        a = MockBackend().ask(build_request(build_state({"prompt": "compute_total の定義ファイルを探して"})))[0]
        self.assertEqual(a["kind"]["choice"], "search")


if __name__ == "__main__":
    unittest.main()
