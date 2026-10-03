import unittest

from jevroute.policy import Config, decide


def answers(kind="search", kind_conf=0.9, edits=0.1, multi=0.1, ambiguous=0.1, risky=0.1, novelty=0.0):
    return {
        "kind": {"type": "choice", "choice": kind, "confidence": kind_conf, "probabilities": {}},
        "edits_code": {"type": "noul", "noul": edits},
        "multi_module": {"type": "noul", "noul": multi},
        "ambiguous": {"type": "noul", "noul": ambiguous},
        "risky_domain": {"type": "noul", "noul": risky},
        "novelty": {"type": "score", "score": novelty, "confidence": 0.9,
                    "legend": {"0": "a", "1": "b", "2": "c"}, "probabilities": {}},
    }


class PolicyTest(unittest.TestCase):
    def test_base_models(self):
        self.assertEqual(decide(answers("search")).model, "haiku")
        self.assertEqual(decide(answers("feature", edits=0.9)).model, "sonnet")
        self.assertEqual(decide(answers("design", novelty=1.0)).model, "opus")

    def test_complexity_bumps(self):
        # 0.35 + 0.25 = 0.6 -> +1
        self.assertEqual(decide(answers("feature", edits=0.9, multi=1.0, ambiguous=1.0)).model, "opus")
        # everything high -> +2, clamped at default max (opus)
        d = decide(answers("feature", edits=0.9, multi=1, ambiguous=1, risky=1, novelty=2))
        self.assertEqual(d.model, "opus")
        self.assertTrue(any("clamped" in r for r in d.reasons))

    def test_fable_only_when_allowed(self):
        hard = answers("design", multi=1, ambiguous=1, risky=1, novelty=2)
        self.assertEqual(decide(hard).model, "opus")
        self.assertEqual(decide(hard, Config(max_model="fable")).model, "fable")

    def test_low_kind_confidence_escalates(self):
        self.assertEqual(decide(answers("search", kind_conf=0.3)).model, "sonnet")

    def test_unsure_noul_counts_as_present(self):
        # risky=0.55 is "unsure" -> treated as >= 0.5 -> haiku forbidden
        self.assertEqual(decide(answers("search", risky=0.55)).model, "sonnet")

    def test_no_haiku_for_multi_module_edit(self):
        self.assertEqual(decide(answers("mechanical_edit", edits=0.9, multi=0.9)).model, "sonnet")

    def test_min_model(self):
        self.assertEqual(decide(answers("search"), Config(min_model="sonnet")).model, "sonnet")


if __name__ == "__main__":
    unittest.main()
