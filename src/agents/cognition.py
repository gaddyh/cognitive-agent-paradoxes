# src/agents/cognition.py
import dspy
from typing import Literal


class DetectGoal(dspy.Signature):
    """Identify the user's high-level goal, not the next tool.

    The goal may require multiple prerequisite tool calls before the final action.
    Do not jump directly to the terminal write tool.
    """
    conversation: str = dspy.InputField(desc="recent turns, newest last")
    last_user: str = dspy.InputField(desc="latest user message")
    goal: str = dspy.OutputField(desc="high-level user goal")
    needs_tool_workflow: bool = dspy.OutputField(desc="true if the goal requires tools")
    rationale: str = dspy.OutputField(desc="short reason")


class PlanWorkflow(dspy.Signature):
    """Plan the next workflow phase, not the final tool.

    Choose the next phase required for safe progress:
    - authenticate_user
    - inspect_order
    - inspect_product
    - collect_missing_info
    - confirm_write_action
    - perform_write_action
    - answer_user
    """
    goal: str = dspy.InputField()
    conversation: str = dspy.InputField(desc="recent turns and tool results")
    phase: Literal[
        "authenticate_user",
        "inspect_order",
        "inspect_product",
        "collect_missing_info",
        "confirm_write_action",
        "perform_write_action",
        "answer_user",
    ] = dspy.OutputField()
    rationale: str = dspy.OutputField(desc="why this phase is next")


class SelectNextTool(dspy.Signature):
    """Select the next executable tool for the current workflow phase.

    Important:
    Choose the NEXT prerequisite tool, not the terminal goal tool.
    Example:
    If the user wants an exchange but the order was not inspected yet,
    choose get_order_details before exchange_delivered_order_items.
    """
    phase: str = dspy.InputField()
    goal: str = dspy.InputField()
    conversation: str = dspy.InputField()
    available_tools: str = dspy.InputField(desc="name: description, one per line")
    tool: str = dspy.OutputField(desc="exact next tool name, or '' if no tool should run")
    confidence: float = dspy.OutputField(desc="0.0 to 1.0")
    rationale: str = dspy.OutputField(desc="short reason")


class DecideNextMove(dspy.Signature):
    """Decide the next move after goal + workflow + tool selection."""
    goal: str = dspy.InputField()
    phase: str = dspy.InputField()
    selected_tool: str = dspy.InputField()
    confidence: float = dspy.InputField()
    move: Literal["tool_call", "clarify", "answer"] = dspy.OutputField()
    question: str = dspy.OutputField(desc="clarifying question if move=clarify, else ''")
    rationale: str = dspy.OutputField(desc="short reason")


def _as_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1"}


def _as_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clean_tool(value) -> str:
    return str(value or "").strip().strip('"').strip("'")


class ReasonProgram(dspy.Module):
    """Goal → Workflow → Next Tool.

    This is intentionally not a final-action selector.
    It separates:
    - goal cognition
    - workflow dependency cognition
    - next executable step cognition
    """

    def __init__(self):
        super().__init__()
        self.detect_goal = dspy.Predict(DetectGoal)
        self.plan_workflow = dspy.Predict(PlanWorkflow)
        self.select_tool = dspy.Predict(SelectNextTool)
        self.decide = dspy.Predict(DecideNextMove)

    def forward(
        self,
        conversation: str,
        last_user: str,
        available_tools: str,
        tool_schemas: dict,
    ) -> dspy.Prediction:
        g = self.detect_goal(
            conversation=conversation,
            last_user=last_user,
        )

        goal = str(getattr(g, "goal", "") or "")
        needs_tool_workflow = _as_bool(getattr(g, "needs_tool_workflow", False))

        if not needs_tool_workflow:
            return dspy.Prediction(
                move="answer",
                goal=goal,
                phase="answer_user",
                tool=None,
                args={},
                missing=[],
                question="",
                rationale=getattr(g, "rationale", ""),
            )

        p = self.plan_workflow(
            goal=goal,
            conversation=conversation,
        )

        phase = str(getattr(p, "phase", "") or "").strip()

        if phase in {"collect_missing_info", "confirm_write_action"}:
            return dspy.Prediction(
                move="clarify",
                goal=goal,
                phase=phase,
                tool=None,
                args={},
                missing=[],
                question="Ask for the missing information or explicit confirmation needed to proceed.",
                rationale=getattr(p, "rationale", ""),
            )

        if phase == "answer_user":
            return dspy.Prediction(
                move="answer",
                goal=goal,
                phase=phase,
                tool=None,
                args={},
                missing=[],
                question="",
                rationale=getattr(p, "rationale", ""),
            )

        s = self.select_tool(
            phase=phase,
            goal=goal,
            conversation=conversation,
            available_tools=available_tools,
        )

        tool = _clean_tool(getattr(s, "tool", ""))
        confidence = _as_float(getattr(s, "confidence", 0.0))

        d = self.decide(
            goal=goal,
            phase=phase,
            selected_tool=tool,
            confidence=confidence,
        )

        move = str(getattr(d, "move", "") or "").strip().lower()

        if move == "clarify" or not tool:
            return dspy.Prediction(
                move="clarify",
                goal=goal,
                phase=phase,
                tool=tool or None,
                args={},
                missing=[],
                question=getattr(d, "question", "") or "What information should I use to continue?",
                rationale=getattr(d, "rationale", ""),
            )

        if move == "answer":
            return dspy.Prediction(
                move="answer",
                goal=goal,
                phase=phase,
                tool=None,
                args={},
                missing=[],
                question="",
                rationale=getattr(d, "rationale", ""),
            )

        return dspy.Prediction(
            move="tool_call",
            goal=goal,
            phase=phase,
            tool=tool,
            args={},
            missing=[],
            question="",
            rationale=getattr(s, "rationale", ""),
        )