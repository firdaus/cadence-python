from unittest import TestCase

from cadence.decision_loop import DecisionId, DecisionTarget


class TestDecisionId(TestCase):
    def setUp(self) -> None:
        pass

    def test_str(self):
        decision_id = DecisionId(DecisionTarget.ACTIVITY, 123)
        s = str(decision_id)
        self.assertIn(str(DecisionTarget.ACTIVITY), s)
        self.assertIn("123", s)

    def test_hash(self):
        d1 = DecisionId(DecisionTarget.ACTIVITY, 123)
        d2 = DecisionId(DecisionTarget.ACTIVITY, 123)
        d3 = DecisionId(DecisionTarget.CHILD_WORKFLOW, 456)
        self.assertEqual(hash(d1), hash(d2))
        self.assertNotEqual(hash(d1), hash(d3))

    def test_equal(self):
        d1 = DecisionId(DecisionTarget.ACTIVITY, 123)
        d2 = DecisionId(DecisionTarget.ACTIVITY, 123)
        d3 = DecisionId(DecisionTarget.CHILD_WORKFLOW, 456)
        self.assertTrue(d1 == d2)
        self.assertFalse(d1 == d3)

    def test_dictionary_key(self):
        e = {}
        d1 = DecisionId(DecisionTarget.ACTIVITY, 123)
        d2 = DecisionId(DecisionTarget.CHILD_WORKFLOW, 456)
        e[d1] = "abc"
        e[d2] = "def"
        self.assertEqual(e[d1], "abc")
        self.assertEqual(e[d2], "def")
