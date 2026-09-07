"""Chapter 5 orchestration study demo.

This is a deliberately small, deterministic model of an agent system. It does
not call an LLM, a database, or an external API. Local functions play the role
of tools so that the orchestration decisions are visible during a presentation.

Run the complete demo:
    python3 agent_orchestration_study_example.py

Run one section during a live demo:
    python3 agent_orchestration_study_example.py --section graph
"""

from __future__ import annotations

import argparse
import asyncio
import ast
import json
import operator
from dataclasses import dataclass
from typing import Any, Callable


ToolFn = Callable[..., Any]
ALL_SECTIONS = (
    "reflex",
    "semantic",
    "hierarchical",
    "parallel",
    "chain",
    "graph",
    "context",
)


@dataclass(frozen=True)
class Tool:
    """A tool contract the orchestrator can search and execute."""

    name: str
    description: str
    func: ToolFn
    group: str


def safe_calculate(expression: str) -> str:
    """Evaluate a small arithmetic expression without using ``eval``."""
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


# These local functions stand in for CRM, billing, support, and policy services.
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
    """5.1.1: a condition-action agent with no planning loop."""
    lowered = query.lower()
    if "calculate:" in lowered:
        expression = query.split(":", 1)[1].strip()
        return safe_calculate(expression)
    if "refund" in lowered:
        return lookup_policy("refund")
    return "No reflex rule matched."


def score_tool(query: str, tool: Tool) -> int:
    """Return a transparent word-overlap score for this educational model."""
    terms = set(query.lower().replace("-", " ").split())
    haystack = f"{tool.name} {tool.description} {tool.group}".lower()
    return sum(1 for term in terms if term in haystack)


def explain_semantic_selection(query: str) -> list[dict[str, Any]]:
    """Show why each tool was ranked, so the selection is easy to present."""
    scores = [
        {"tool": tool.name, "group": tool.group, "score": score_tool(query, tool)}
        for tool in TOOLS
    ]
    return sorted(scores, key=lambda item: item["score"], reverse=True)


def semantic_tool_selection(query: str, top_k: int = 3) -> list[Tool]:
    """5.2.2: retrieve a small candidate set before choosing a tool.

    Production systems normally compare embeddings of the query and tool
    descriptions. This demo uses word overlap so its ranking stays inspectable.
    """
    ranked = sorted(TOOLS, key=lambda tool: score_tool(query, tool), reverse=True)
    return [tool for tool in ranked[:top_k] if score_tool(query, tool) > 0]


def select_tool_group(query: str) -> str:
    """Choose the first routing level for the hierarchical-selection example."""
    lowered = query.lower()
    if any(word in lowered for word in ["invoice", "refund", "billing"]):
        return "knowledge"
    if any(word in lowered for word in ["customer", "renewal", "order"]):
        return "customer"
    if any(word in lowered for word in ["ticket", "login", "sso"]):
        return "support"
    return "computation"


def hierarchical_tool_selection(query: str) -> list[Tool]:
    """5.2.3: route to a group first, then rank tools only inside that group."""
    group = select_tool_group(query)
    candidates = [tool for tool in TOOLS if tool.group == group]
    return sorted(candidates, key=lambda tool: score_tool(query, tool), reverse=True)


async def parallel_tool_execution(customer_id: str, ticket_id: str) -> dict[str, Any]:
    """5.4.2: gather independent facts at the same time.

    ``asyncio.gather`` waits for every task; no task needs another task's result.
    ``to_thread`` represents calling blocking SDK or database code safely from an
    async orchestration function.
    """
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
    """5.4.3: a linear pipeline where later steps consume earlier results."""
    normalized = user_message.strip().lower()
    category = "billing" if "invoice" in normalized or "refund" in normalized else "technical"
    action = "look up policy" if category == "billing" else "check login runbook"
    response = f"Category: {category}. Next action: {action}."
    return {
        "step_1_normalize": normalized,
        "step_2_classify": category,
        "step_3_choose_action": action,
        "response": response,
    }


def graph_workflow(user_message: str) -> dict[str, str]:
    """5.4.4: a state graph with a conditional branch and a common summary."""
    state = {"user_message": user_message, "issue_type": "", "step_result": "", "response": ""}
    text = user_message.lower()

    # Route node: its output determines which edge is taken next.
    state["issue_type"] = "billing" if "refund" in text or "invoice" in text else "technical"

    if state["issue_type"] == "billing":
        state["step_result"] = lookup_policy("refund" if "refund" in text else "billing")
        if "enterprise" in text:
            state["step_result"] += " " + send_human_review_notice("enterprise billing request")
    else:
        state["step_result"] = lookup_policy("login" if "login" in text or "sso" in text else "technical")

    # Merge node: every branch produces a single response-shaped state.
    state["response"] = f"Handled as {state['issue_type']}: {state['step_result']}"
    return state


def build_context_with_trace(
    user_message: str,
    state: dict[str, Any],
    snippets: list[str],
    max_chars: int = 900,
) -> tuple[str, list[str]]:
    """5.5: select, order, and trim information before a model call."""
    blocks = [
        "SYSTEM: You are a customer-support agent. Use policy-backed answers.",
        f"USER: {user_message}",
        f"WORKFLOW_STATE: {state}",
        "RETRIEVED_KNOWLEDGE:",
    ]
    included: list[str] = []
    for snippet in snippets:
        candidate = f"- {snippet}"
        if len("\n".join([*blocks, candidate])) <= max_chars:
            blocks.append(candidate)
            included.append(snippet)
    return "\n".join(blocks), included


def build_context(user_message: str, state: dict[str, Any], snippets: list[str], max_chars: int = 900) -> str:
    """Return only the assembled context when a caller does not need its trace."""
    context, _ = build_context_with_trace(user_message, state, snippets, max_chars)
    return context


def print_section(number: int, title: str, book_section: str) -> None:
    print(f"\n{'=' * 74}\n{number}. {title}  |  Book: {book_section}\n{'=' * 74}")


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


async def run_demo(sections: tuple[str, ...]) -> None:
    """Run selected sections in the same order as the presentation."""
    graph_result: dict[str, str] | None = None

    if "reflex" in sections:
        print_section(1, "Reflex agent", "5.1.1")
        print("입력: calculate: 3.15 * 12.25")
        print("판단: 'calculate:' 규칙이 일치하므로 계산 도구를 즉시 실행")
        print(f"결과: {reflex_agent('calculate: 3.15 * 12.25')}")

    if "semantic" in sections:
        query = "customer renewal order risk"
        print_section(2, "Semantic tool selection", "5.2.2")
        print(f"질문: {query}")
        print("후보 점수 (이 예제는 임베딩 대신 단어 겹침을 사용):")
        print_json(explain_semantic_selection(query))
        print("선택된 후보:")
        for tool in semantic_tool_selection(query):
            print(f"- {tool.name}: {tool.description}")

    if "hierarchical" in sections:
        query = "enterprise refund policy"
        print_section(3, "Hierarchical tool selection", "5.2.3")
        print(f"질문: {query}")
        print(f"1단계 그룹 선택: {select_tool_group(query)}")
        print("2단계 그룹 안의 도구 후보:")
        for tool in hierarchical_tool_selection(query):
            print(f"- {tool.name}: {tool.description}")

    if "parallel" in sections:
        print_section(4, "Parallel tool execution", "5.4.2")
        print("독립 조회 4개를 asyncio.gather로 동시에 시작합니다.")
        gathered = await parallel_tool_execution(customer_id="C-1024", ticket_id="T-1237")
        print_json(gathered)

    if "chain" in sections:
        print_section(5, "Chain workflow", "5.4.3")
        print_json(chain_workflow("Customer asks for a refund on the latest invoice"))

    if "graph" in sections:
        print_section(6, "Graph workflow", "5.4.4")
        graph_result = graph_workflow("Enterprise customer requests refund approval")
        print("분기: billing -> refund policy -> enterprise human review -> summary")
        print_json(graph_result)

    if "context" in sections:
        print_section(7, "Context engineering", "5.5")
        state = graph_result or graph_workflow("Enterprise customer requests refund approval")
        snippets = [
            "Enterprise accounts need human approval for refunds.",
            "SSO incidents affecting more than 5 users should be escalated.",
            "Victor Hart has a renewal in 14 days.",
        ]
        context, included = build_context_with_trace(
            "What should I tell Victor about ticket T-1237?", state, snippets
        )
        print(f"길이 제한 안에 포함된 검색 지식: {len(included)}개")
        print(context)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chapter 5 orchestration study demo")
    parser.add_argument(
        "--section",
        choices=ALL_SECTIONS,
        help="Run one demo section. Omit this option to run every section.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sections = (args.section,) if args.section else ALL_SECTIONS
    asyncio.run(run_demo(sections))


if __name__ == "__main__":
    main()
