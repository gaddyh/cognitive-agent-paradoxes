import dspy
from typing import Literal, TypedDict

from langgraph.graph import StateGraph, END


class TurnClassifier(dspy.Signature):
    conversation: str = dspy.InputField()
    last_user: str = dspy.InputField()
    turn_class: Literal["new_request", "followup", "confirmation", "correction", "cheap"] = dspy.OutputField()
    skip_workflow: bool = dspy.OutputField()
    rationale: str = dspy.OutputField()


class WorkflowPlanner(dspy.Signature):
    conversation: str = dspy.InputField()
    last_user: str = dspy.InputField()
    available_tools: str = dspy.InputField(desc="tool names available, one per line")
    goal: str = dspy.OutputField()
    phase: Literal[
        "authenticate_user",
        "inspect_order",
        "inspect_product",
        "collect_missing_info",
        "confirm_write_action",
        "perform_write_action",
        "answer_user",
    ] = dspy.OutputField()
    needs_tool: bool = dspy.OutputField()


class ToolSelector(dspy.Signature):
    goal: str = dspy.InputField()
    phase: str = dspy.InputField()
    conversation: str = dspy.InputField()
    available_tools: str = dspy.InputField()
    tool: str = dspy.OutputField()
    confidence: float = dspy.OutputField()


class TurnClassifierProgram(dspy.Module):
    def __init__(self):
        self.predict = dspy.Predict(TurnClassifier)

    def forward(self, conversation: str, last_user: str):
        return self.predict(conversation=conversation, last_user=last_user)


class WorkflowPlannerProgram(dspy.Module):
    def __init__(self):
        self.predict = dspy.Predict(WorkflowPlanner)

    def forward(self, conversation: str, last_user: str, available_tools: str = ""):
        return self.predict(conversation=conversation, last_user=last_user, available_tools=available_tools)


class ToolSelectorProgram(dspy.Module):
    def __init__(self):
        self.predict = dspy.Predict(ToolSelector)

    def forward(self, goal: str, phase: str, conversation: str, available_tools: str):
        return self.predict(
            goal=goal,
            phase=phase,
            conversation=conversation,
            available_tools=available_tools,
        )


class GraphState(TypedDict, total=False):
    conversation: str
    last_user: str
    available_tools: str
    turn_class: str
    skip_workflow: bool
    goal: str
    phase: str
    needs_tool: bool
    tool: str
    confidence: float
    move: str
    hint: str
    dspy_calls: int


def _as_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "yes", "1"}


def _as_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def build_cognition_graph(
    turn_classifier: TurnClassifierProgram | None = None,
    planner: WorkflowPlannerProgram | None = None,
    selector: ToolSelectorProgram | None = None,
):
    turn_classifier = turn_classifier or TurnClassifierProgram()
    planner = planner or WorkflowPlannerProgram()
    selector = selector or ToolSelectorProgram()

    def classify_turn_node(state: GraphState) -> GraphState:
        pred = turn_classifier(
            conversation=state["conversation"],
            last_user=state["last_user"],
        )
        turn_class = str(getattr(pred, "turn_class", "new_request")).strip()
        skip = _as_bool(getattr(pred, "skip_workflow", False))
        state["turn_class"] = turn_class
        state["skip_workflow"] = skip
        state["dspy_calls"] = state.get("dspy_calls", 0) + 1
        if skip or turn_class in {"followup", "cheap"}:
            state["move"] = "fallback"
            state["hint"] = (
                f"Cognitive decision: {turn_class}. "
                "Continue with the current workflow context. "
                "Resolve the user's short follow-up against the latest assistant question or tool result."
            )
        return state

    def route_after_classify(state: GraphState) -> str:
        turn_class = state.get("turn_class", "new_request")
        if state.get("skip_workflow") or turn_class in {"cheap", "followup"}:
            return END
        return "plan_next_step"

    def plan_next_step_node(state: GraphState) -> GraphState:
        pred = planner(
            conversation=state["conversation"],
            last_user=state["last_user"],
            available_tools=state.get("available_tools", ""),
        )
        goal = str(getattr(pred, "goal", "") or "")
        phase = str(getattr(pred, "phase", "answer_user") or "")
        needs_tool = _as_bool(getattr(pred, "needs_tool", False))
        state["goal"] = goal
        state["phase"] = phase
        state["needs_tool"] = needs_tool
        state["dspy_calls"] = state.get("dspy_calls", 0) + 1
        if phase == "answer_user" or not needs_tool:
            state["move"] = "answer"
            state["hint"] = (
                f"Cognitive decision: answer_user.\n"
                f"Goal: {goal}\n"
                "Answer naturally. Do not call a tool unless the retail policy clearly requires it."
            )
        return state

    def route_after_plan(state: GraphState) -> str:
        if state.get("phase") == "answer_user" or not state.get("needs_tool"):
            return END
        return "select_tool"

    def select_tool_node(state: GraphState) -> GraphState:
        pred = selector(
            goal=state.get("goal", ""),
            phase=state.get("phase", ""),
            conversation=state["conversation"],
            available_tools=state["available_tools"],
        )
        tool = str(getattr(pred, "tool", "") or "").strip().strip('"').strip("'")
        confidence = _as_float(getattr(pred, "confidence", 0.0))
        state["tool"] = tool
        state["confidence"] = confidence
        state["dspy_calls"] = state.get("dspy_calls", 0) + 1
        if not tool:
            state["move"] = "clarify"
            state["hint"] = (
                f"Cognitive decision: clarify.\n"
                f"Goal: {state.get('goal', '')}\n"
                f"Phase: {state.get('phase', '')}\n"
                "Ask one concise question to resolve the missing workflow step."
            )
        else:
            state["move"] = "tool_call"
            state["hint"] = (
                f"Cognitive decision: next tool recommendation.\n"
                f"Goal: {state.get('goal', '')}\n"
                f"Phase: {state.get('phase', '')}\n"
                f"Recommended next tool: {tool}\n"
                f"Confidence: {confidence}\n"
                "Prefer prerequisite tools before terminal write tools. "
                "Only call the tool if required arguments are grounded; otherwise ask one concise clarification."
            )
        return state

    graph = StateGraph(GraphState)
    graph.add_node("classify_turn", classify_turn_node)
    graph.add_node("plan_next_step", plan_next_step_node)
    graph.add_node("select_tool", select_tool_node)
    graph.set_entry_point("classify_turn")
    graph.add_conditional_edges("classify_turn", route_after_classify)
    graph.add_conditional_edges("plan_next_step", route_after_plan)
    graph.add_edge("select_tool", END)
    return graph.compile()
