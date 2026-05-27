import os
import time

import dspy

from tau2.agent.base import ValidAgentInputMessage
from tau2.agent.llm_agent import LLMAgent, LLMAgentState
from tau2.data_model.message import AssistantMessage, MultiToolMessage, SystemMessage
from tau2.registry import registry
from tau2.utils.llm_utils import generate

from src.agents.cognition_graph import build_cognition_graph
from src.agents.metrics import AgentMetrics, TurnMetric


COG_MODEL = os.getenv("COG_MODEL", "openai/gpt-4o-mini")
COG_ENABLED = os.getenv("COG_ENABLED", "true").lower() == "true"

dspy.configure(lm=dspy.LM(COG_MODEL, temperature=0.0))


class LangGraphCognitionAgent(LLMAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph = build_cognition_graph()
        self.metrics = AgentMetrics()
        self.tools_block = "\n".join(
            f"{t.name}: {getattr(t, 'description', '')}"
            for t in self.tools
        )

    def _build_recent_conversation(self, state: LLMAgentState, window: int = 4) -> str:
        return "\n".join(
            f"{m.role}: {getattr(m, 'content', '')}"
            for m in state.messages[-window:]
        )

    def _is_tool_result(self, message) -> bool:
        return isinstance(message, MultiToolMessage) or type(message).__name__ == "ToolMessage"

    def _is_cheap_user_message(self, message) -> bool:
        text = (getattr(message, "content", "") or "").strip().lower()
        return text in {
            "",
            "hi",
            "hello",
            "hey",
            "thanks",
            "thank you",
            "ok",
            "okay",
            "yes",
            "no",
            "sure",
            "sounds good",
        }

    def _skip_hint(self, reason: str) -> dict:
        return {
            "move": reason,
            "tool": None,
            "hint": (
                f"Cognitive decision: {reason}. "
                "Continue using the current workflow context. "
                "Do not repeat tools whose result is already available."
            ),
            "dspy_calls": 0,
            "convo_chars": 0,
        }

    def _run_graph(self, state: LLMAgentState, message) -> dict:
        convo = self._build_recent_conversation(state, window=4)
        last_user = getattr(message, "content", "") or ""
        result = self.graph.invoke(
            {
                "conversation": convo,
                "last_user": last_user,
                "available_tools": self.tools_block,
                "dspy_calls": 0,
            }
        )
        result["convo_chars"] = len(convo)
        return result

    def generate_next_message(
        self,
        message: ValidAgentInputMessage,
        state: LLMAgentState,
    ) -> tuple[AssistantMessage, LLMAgentState]:
        total_t0 = time.perf_counter()

        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)

        reason_t0 = time.perf_counter()
        if not COG_ENABLED:
            result = self._skip_hint("cognition_disabled")
        elif self._is_tool_result(message):
            result = self._skip_hint("tool_result")
        elif self._is_cheap_user_message(message):
            result = self._skip_hint("cheap_user_message")
        else:
            result = self._run_graph(state, message)
        reason_ms = round((time.perf_counter() - reason_t0) * 1000, 1)

        sys = list(state.system_messages)
        sys.append(SystemMessage(role="system", content=result.get("hint", "")))
        messages = sys + state.messages

        gen_t0 = time.perf_counter()
        assistant_message = generate(
            model=self.llm,
            tools=self.tools,
            messages=messages,
            **self.llm_args,
        )
        gen_ms = round((time.perf_counter() - gen_t0) * 1000, 1)

        state.messages.append(assistant_message)

        self.metrics.add(
            TurnMetric(
                turn=len(self.metrics.rows),
                incoming=type(message).__name__,
                move=result.get("move", "unknown"),
                tool=result.get("tool"),
                reason_ms=reason_ms,
                generate_ms=gen_ms,
                total_ms=round((time.perf_counter() - total_t0) * 1000, 1),
                messages=len(state.messages),
                convo_chars=result.get("convo_chars", 0),
                assistant_tool_call=bool(getattr(assistant_message, "tool_calls", None)),
                assistant_chars=len(getattr(assistant_message, "content", "") or ""),
            )
        )
        self.metrics.print_turn_table()

        return assistant_message, state


registry.register_agent(LangGraphCognitionAgent, "langgraph_cognition")
