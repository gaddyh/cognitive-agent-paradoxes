# src/agents/my_llm_agent.py
import json
import os
import time
import uuid
from dataclasses import asdict
from typing import IO, Optional

import dspy

from tau2.agent.base import ValidAgentInputMessage
from tau2.agent.llm_agent import LLMAgent, LLMAgentState
from tau2.data_model.message import AssistantMessage, MultiToolMessage, SystemMessage
from tau2.registry import registry
from tau2.utils.llm_utils import generate

from src.agents.cognition import ReasonProgram
from src.agents.metrics import AgentMetrics, TurnMetric


COG_MODEL = os.getenv("COG_MODEL", "openai/gpt-4o-mini")
COG_ENABLED = os.getenv("COG_ENABLED", "true").lower() == "true"

dspy.configure(lm=dspy.LM(COG_MODEL, temperature=0.0))


class MyLLMAgent(LLMAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.reasoner = ReasonProgram()
        self.metrics = AgentMetrics()
        self._session_id: str = str(uuid.uuid4())

        self._turn_log: Optional[IO[str]] = None
        _turn_log_path = os.environ.get("TAU2_TURN_LOG")
        if _turn_log_path:
            self._turn_log = open(_turn_log_path, "a", buffering=1)

        self.tools_block = "\n".join(
            f"{t.name}: {getattr(t, 'description', '')}"
            for t in self.tools
        )

        self.schemas = {
            t.name: getattr(t, "params", getattr(t, "parameters", {}))
            for t in self.tools
        }

    def _build_recent_conversation(self, state: LLMAgentState, window: int = 4) -> str:
        recent = state.messages[-window:]
        return "\n".join(
            f"{m.role}: {getattr(m, 'content', '')}"
            for m in recent
        )

    def _skip_reasoning_for_tool_result(self, message) -> bool:
        return isinstance(message, MultiToolMessage) or type(message).__name__ == "ToolMessage"

    def _cheap_skip_for_user_message(self, message) -> bool:
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

    def _default_row(self, reason: str) -> dict:
        return {
            "turn": len(self.metrics.rows),
            "move": reason,
            "tool": None,
            "args": {},
            "missing": [],
            "clarified": False,
            "reason_ms": 0.0,
            "convo_chars": 0,
        }

    def _reason(self, state: LLMAgentState, incoming) -> dict:
        last_user = getattr(incoming, "content", "") or ""
        convo = self._build_recent_conversation(state, window=4)

        t0 = time.perf_counter()
        try:
            pred = self.reasoner(
                conversation=convo,
                last_user=last_user,
                available_tools=self.tools_block,
                tool_schemas=self.schemas,
            )
            reason_ms = round((time.perf_counter() - t0) * 1000, 1)
            return {
              "turn": len(self.metrics.rows),
              "move": getattr(pred, "move", "unknown"),
              "goal": getattr(pred, "goal", ""),
              "phase": getattr(pred, "phase", ""),
              "tool": getattr(pred, "tool", None),
              "args": getattr(pred, "args", {}) or {},
              "missing": getattr(pred, "missing", []) or [],
              "question": getattr(pred, "question", "") or "",
              "clarified": getattr(pred, "move", None) == "clarify",
              "reason_ms": reason_ms,
              "convo_chars": len(convo),
          }
        except Exception:
            reason_ms = round((time.perf_counter() - t0) * 1000, 1)
            row = self._default_row("cognition_error")
            row["reason_ms"] = reason_ms
            row["convo_chars"] = len(convo)
            return row

    def _hint_for_row(self, row: dict) -> str:
      move = row["move"]
      tool = row.get("tool")
      goal = row.get("goal", "")
      phase = row.get("phase", "")

      if move == "tool_call":
          return (
              f"Cognitive decision:\n"
              f"- User goal: {goal}\n"
              f"- Current workflow phase: {phase}\n"
              f"- Recommended next tool: {tool}\n\n"
              "Follow the workflow phase. Prefer prerequisite tools before terminal write tools. "
              "Only call the recommended tool if its required arguments are grounded. "
              "If required arguments are missing, ask exactly one concise clarification question."
          )

      if move == "clarify":
          question = row.get("question") or "Ask one concise clarification question."
          return (
              f"Cognitive decision:\n"
              f"- User goal: {goal}\n"
              f"- Current workflow phase: {phase}\n"
              f"- Next move: clarify\n\n"
              f"Ask this clarification if needed: {question}"
          )

      if move == "tool_result":
          return (
              "Cognitive decision:\n"
              "- Current workflow phase: tool result synthesis\n\n"
              "Use the latest tool result to continue the workflow. "
              "Do not repeat a tool call whose result is already available."
          )

      return (
          f"Cognitive decision:\n"
          f"- User goal: {goal}\n"
          f"- Current workflow phase: {phase}\n"
          f"- Next move: answer\n\n"
          "Answer naturally. Do not call a tool unless the retail policy or workflow clearly requires it."
      )
      
    def _can_emit_deterministic_tool_call(self, row: dict) -> bool:
        return (
            row.get("move") == "tool_call"
            and bool(row.get("tool"))
            and bool(row.get("args"))
            and not row.get("missing")
        )

    def _build_deterministic_tool_call(self, row: dict) -> AssistantMessage:
        """
        Placeholder: exact tau2 AssistantMessage/tool_call shape may need adjustment
        based on tau2's message model.

        Keep this isolated so we can adapt it after inspecting the expected schema.
        """
        raise NotImplementedError(
            "Deterministic tool-call emission requires matching tau2's AssistantMessage tool_call schema."
        )

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

        if not COG_ENABLED:
            row = self._default_row("cognition_disabled")
        elif self._skip_reasoning_for_tool_result(message):
            row = self._default_row("tool_result")
        elif self._cheap_skip_for_user_message(message):
            row = self._default_row("cheap_user_message")
        else:
            row = self._reason(state, message)

        hint = self._hint_for_row(row)

        gen_t0 = time.perf_counter()

        if self._can_emit_deterministic_tool_call(row):
            assistant_message = self._build_deterministic_tool_call(row)
            gen_ms = 0.0
        else:
            sys = list(state.system_messages)
            sys.append(SystemMessage(role="system", content=hint))
            messages = sys + state.messages

            assistant_message = generate(
                model=self.llm,
                tools=self.tools,
                messages=messages,
                **self.llm_args,
            )

            gen_ms = round((time.perf_counter() - gen_t0) * 1000, 1)

        state.messages.append(assistant_message)

        actual_tool_call = bool(getattr(assistant_message, "tool_calls", None))
        expected_tool_call = row["move"] == "tool_call"

        turn_metric = TurnMetric(
            turn=row["turn"],
            incoming=type(message).__name__,
            move=row["move"],
            tool=row.get("tool"),
            reason_ms=row["reason_ms"],
            generate_ms=gen_ms,
            total_ms=round((time.perf_counter() - total_t0) * 1000, 1),
            messages=len(state.messages),
            convo_chars=row.get("convo_chars", 0),
            assistant_tool_call=actual_tool_call,
            assistant_chars=len(getattr(assistant_message, "content", "") or ""),
        )
        self.metrics.add(turn_metric)

        if self._turn_log is not None:
            self._turn_log.write(
                json.dumps({**asdict(turn_metric), "session_id": self._session_id}) + "\n"
            )

        self.metrics.print_turn_table()

        return assistant_message, state


registry.register_agent(MyLLMAgent, "my_llm_agent")