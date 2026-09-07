"""
Study example for Chapter 5, "Orchestration".

This file is intentionally dependency-free. It shows the orchestration ideas
from the chapter with small local tools instead of paid APIs.

Run:
    python3 outputs/agent_orchestration_study_example.py
"""

from __future__ import annotations

import asyncio
import ast
import operator
from dataclasses import dataclass
from typing import Any, Callable


ToolFn = Callable[..., Any]


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    func: ToolFn
    group: str


def safe_calculate(expression: str) -> str:
    """Evaluate a tiny arithmetic expression without using eval."""
    allowed = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def visit(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in allowed:
            return allowed[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in allowed:
            return allowed[type(node.op)](visit(node.operand))
        raise ValueError(f"Unsupported expression: {expression}")

    result = visit(ast.parse(expression, mode="eval"))
    return f"{expression} = {result}"


def get_customer_profile(customer_id: str) -> dict[str, str]:
    return {
        "customer_id": customer_id,
        "name": "Victor Hart",
        "tier": "enterprise",
        "risk": "renewal in 14 days",
    }


def get_order_history(customer_id: str) -> list[str]:
    return [
        f"{customer_id}: Pro plan renewed on 2026-08-01",
        f"{customer_id}: Added 20 seats on 2026-08-21",
    ]


def get_ticket_log(ticket_id: str) -> list[str]:
    return [
        f"{ticket_id}: login failures started after SSO policy change",
        f"{ticket_id}: customer reports impact to finance team",
    ]


def lookup_policy(topic: str) -> str:
    policies = {
        "refund": "Refunds require manager approval for enterprise contracts.",
        "login": "SSO incidents should be escalated if more than 5 users are blocked.",
        "billing": "Invoice corrections need the billing owner and customer approval.",
    }
    return policies.get(topic, "No exact policy found. Ask a human reviewer.")


def send_human_review_notice(summary: str) -> str:
    return f"Human review requested: {summary}"


TOOLS = [
    Tool("calculate", "Calculate arithmetic expressions like 3.15 * 12.25.", safe_calculate, "computation"),
    Tool("customer_profile", "Fetch customer tier, renewal status, and account risk.", get_customer_profile, "customer"),
    Tool("order_history", "Fetch recent customer orders and subscription changes.", get_order_history, "customer"),
    Tool("ticket_log", "Fetch support ticket history and recent events.", get_ticket_log, "support"),
    Tool("policy_lookup", "Look up support, billing, refund, and login policies.", lookup_policy, "knowledge"),
    Tool("human_review", "Notify a human reviewer when risk or approval is required.", send_human_review_notice, "workflow"),
]


def reflex_agent(query: str) -> str:
    """A condition-action agent. Fast, predictable, and limited."""
    lowered = query.lower()
    if "calculate:" in lowered:
        expression = query.split(":", 1)[1].strip()
        return safe_calculate(expression)
    if "refund" in lowered:
        return lookup_policy("refund")
    return "No reflex rule matched."


def score_tool(query: str, tool: Tool) -> int:
    terms = set(query.lower().replace("-", " ").split())
    haystack = f"{tool.name} {tool.description} {tool.group}".lower()
    return sum(1 for term in terms if term in haystack)


def semantic_tool_selection(query: str, top_k: int = 3) -> list[Tool]:
    """A tiny stand-in for embedding search over tool descriptions."""
    ranked = sorted(TOOLS, key=lambda tool: score_tool(query, tool), reverse=True)
    return [tool for tool in ranked[:top_k] if score_tool(query, tool) > 0]


def hierarchical_tool_selection(query: str) -> list[Tool]:
    """Select a group first, then select tools only inside that group."""
    lowered = query.lower()
    if any(word in lowered for word in ["invoice", "refund", "billing"]):
        group = "knowledge"
    elif any(word in lowered for word in ["customer", "renewal", "order"]):
        group = "customer"
    elif any(word in lowered for word in ["ticket", "login", "sso"]):
        group = "support"
    else:
        group = "computation"
    return [tool for tool in semantic_tool_selection(query, top_k=6) if tool.group == group]


async def parallel_tool_execution(customer_id: str, ticket_id: str) -> dict[str, Any]:
    """Run independent information-gathering tools together."""
    profile, orders, ticket, login_policy = await asyncio.gather(
        asyncio.to_thread(get_customer_profile, customer_id),
        asyncio.to_thread(get_order_history, customer_id),
        asyncio.to_thread(get_ticket_log, ticket_id),
        asyncio.to_thread(lookup_policy, "login"),
    )
    return {
        "profile": profile,
        "orders": orders,
        "ticket": ticket,
        "policy": login_policy,
    }


def chain_workflow(user_message: str) -> dict[str, str]:
    """A linear chain where each step depends on the previous step."""
    normalized = user_message.strip().lower()
    category = "billing" if "invoice" in normalized or "refund" in normalized else "technical"
    action = "look up policy" if category == "billing" else "check login runbook"
    response = f"Category: {category}. Next action: {action}."
    return {"normalized": normalized, "category": category, "action": action, "response": response}


def graph_workflow(user_message: str) -> dict[str, str]:
    """A small state graph with conditional branches and a shared summary step."""
    state = {"user_message": user_message, "issue_type": "", "step_result": "", "response": ""}
    text = user_message.lower()

    state["issue_type"] = "billing" if "refund" in text or "invoice" in text else "technical"

    if state["issue_type"] == "billing":
        state["step_result"] = lookup_policy("refund" if "refund" in text else "billing")
        if "enterprise" in text:
            state["step_result"] += " " + send_human_review_notice("enterprise billing request")
    else:
        state["step_result"] = lookup_policy("login" if "login" in text or "sso" in text else "technical")

    state["response"] = f"Handled as {state['issue_type']}: {state['step_result']}"
    return state


def build_context(user_message: str, state: dict[str, Any], snippets: list[str], max_chars: int = 900) -> str:
    """Context engineering: choose, structure, and trim what the model sees."""
    blocks = [
        "SYSTEM: You are a customer-support agent. Use policy-backed answers.",
        f"USER: {user_message}",
        f"WORKFLOW_STATE: {state}",
        "RETRIEVED_KNOWLEDGE:",
    ]
    for snippet in snippets:
        if len("\n".join(blocks)) + len(snippet) <= max_chars:
            blocks.append(f"- {snippet}")
    return "\n".join(blocks)


async def main() -> None:
    print("\n1. Reflex agent")
    print(reflex_agent("calculate: 3.15 * 12.25"))

    print("\n2. Semantic tool selection")
    for tool in semantic_tool_selection("customer renewal order risk"):
        print(f"- {tool.name}: {tool.description}")

    print("\n3. Hierarchical tool selection")
    for tool in hierarchical_tool_selection("enterprise refund policy"):
        print(f"- {tool.name}: group={tool.group}")

    print("\n4. Parallel tool execution")
    gathered = await parallel_tool_execution(customer_id="C-1024", ticket_id="T-1237")
    print(gathered)

    print("\n5. Chain workflow")
    print(chain_workflow("Customer asks for a refund on the latest invoice"))

    print("\n6. Graph workflow")
    graph_result = graph_workflow("Enterprise customer requests refund approval")
    print(graph_result)

    print("\n7. Context engineering")
    print(build_context(
        "What should I tell Victor about ticket T-1237?",
        graph_result,
        [
            "Enterprise accounts need human approval for refunds.",
            "SSO incidents affecting more than 5 users should be escalated.",
            "Victor Hart has a renewal in 14 days.",
        ],
    ))


if __name__ == "__main__":
    asyncio.run(main())
