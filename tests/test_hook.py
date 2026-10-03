import io
import json
import unittest

from jevroute.hook import main


def run(tool_input, env):
    out = io.StringIO()
    main(io.StringIO(json.dumps({"tool_name": "Agent", "tool_input": tool_input})), out, env)
    return json.loads(out.getvalue()) if out.getvalue() else None


class HookTest(unittest.TestCase):
    def test_rewrites_model_and_keeps_other_fields(self):
        ti = {"description": "Find config", "prompt": "Find the config loader", "subagent_type": "Explore",
              "model": "opus", "run_in_background": False}
        out = run(ti, {"JEV_BACKEND": "mock"})
        upd = out["hookSpecificOutput"]["updatedInput"]
        self.assertEqual(upd["model"], "haiku")
        self.assertEqual({k: v for k, v in upd.items() if k != "model"},
                         {k: v for k, v in ti.items() if k != "model"})
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PreToolUse")

    def test_backend_failure_falls_back_explicitly(self):
        out = run({"prompt": "x", "model": "opus"}, {"JEV_BACKEND": "http", "JEV_ROUTE_FALLBACK": "sonnet"})
        self.assertEqual(out["hookSpecificOutput"]["updatedInput"]["model"], "sonnet")

    def test_bad_config_falls_back(self):
        out = run({"prompt": "find x"}, {"JEV_BACKEND": "mock", "JEV_ROUTE_MAX_MODEL": "gpt"})
        self.assertEqual(out["hookSpecificOutput"]["updatedInput"]["model"], "sonnet")

    def test_skip_types_untouched(self):
        self.assertIsNone(run({"prompt": "x", "subagent_type": "fork"}, {"JEV_BACKEND": "mock"}))

    def test_dry_run_outputs_nothing(self):
        self.assertIsNone(run({"prompt": "find x"}, {"JEV_BACKEND": "mock", "JEV_ROUTE_DRY_RUN": "1"}))

    def test_garbage_stdin_is_ignored(self):
        out = io.StringIO()
        self.assertEqual(main(io.StringIO("nope"), out, {}), 0)
        self.assertEqual(out.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
