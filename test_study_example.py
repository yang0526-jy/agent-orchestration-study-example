"""Small regression tests for the deterministic study demo."""

import asyncio
import unittest

import agent_orchestration_study_example as demo


class OrchestrationStudyExampleTests(unittest.TestCase):
    def test_reflex_agent_executes_matching_rule(self) -> None:
        self.assertEqual(demo.reflex_agent("calculate: 2 * 5"), "2 * 5 = 10")

    def test_semantic_selection_returns_customer_tools(self) -> None:
        names = [tool.name for tool in demo.semantic_tool_selection("customer renewal order risk")]
        self.assertIn("customer_profile", names)
        self.assertIn("order_history", names)

    def test_hierarchical_selection_routes_to_knowledge(self) -> None:
        selected = demo.hierarchical_tool_selection("enterprise refund policy")
        self.assertEqual(demo.select_tool_group("enterprise refund policy"), "knowledge")
        self.assertEqual([tool.name for tool in selected], ["policy_lookup"])

    def test_parallel_execution_collects_every_independent_result(self) -> None:
        result = asyncio.run(demo.parallel_tool_execution("C-1024", "T-1237"))
        self.assertEqual(set(result), {"profile", "orders", "ticket", "policy"})
        self.assertEqual(result["profile"]["tier"], "enterprise")

    def test_graph_adds_human_review_for_enterprise_billing(self) -> None:
        result = demo.graph_workflow("Enterprise customer requests refund approval")
        self.assertEqual(result["issue_type"], "billing")
        self.assertIn("Human review requested", result["step_result"])

    def test_context_keeps_its_structure_under_a_limit(self) -> None:
        context, included = demo.build_context_with_trace(
            "Need a reply",
            {"issue_type": "billing"},
            ["First fact", "Second fact"],
            max_chars=240,
        )
        self.assertIn("SYSTEM:", context)
        self.assertIn("USER:", context)
        self.assertLessEqual(len(context), 240)
        self.assertIsInstance(included, list)


if __name__ == "__main__":
    unittest.main()
