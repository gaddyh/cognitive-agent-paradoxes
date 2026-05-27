# src/agents/metrics.py
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class TurnMetric:
    turn: int
    incoming: str
    move: str
    tool: str | None
    reason_ms: float
    generate_ms: float
    total_ms: float
    messages: int
    convo_chars: int
    assistant_tool_call: bool
    assistant_chars: int


class AgentMetrics:
    def __init__(self):
        self.rows: list[TurnMetric] = []

    def add(self, row: TurnMetric):
        self.rows.append(row)

    def print_turn_table(self):
        table = Table(title="Cognitive Agent Turn Metrics")

        for col in [
            "turn", "incoming", "move", "tool",
            "reason_ms", "generate_ms", "total_ms",
            "messages", "convo_chars", "tool_call", "chars"
        ]:
            table.add_column(col)

        for r in self.rows:
            table.add_row(
                str(r.turn),
                r.incoming,
                r.move,
                str(r.tool or ""),
                f"{r.reason_ms:.1f}",
                f"{r.generate_ms:.1f}",
                f"{r.total_ms:.1f}",
                str(r.messages),
                str(r.convo_chars),
                "yes" if r.assistant_tool_call else "no",
                str(r.assistant_chars),
            )

        console.print(table)

    def print_summary(self):
        if not self.rows:
            return

        total_reason = sum(r.reason_ms for r in self.rows)
        total_generate = sum(r.generate_ms for r in self.rows)
        total = sum(r.total_ms for r in self.rows)

        skipped = sum(1 for r in self.rows if r.reason_ms == 0)
        tool_calls = sum(1 for r in self.rows if r.assistant_tool_call)

        table = Table(title="Cognitive Agent Summary")

        table.add_column("metric")
        table.add_column("value")

        table.add_row("turns", str(len(self.rows)))
        table.add_row("skipped cognition turns", str(skipped))
        table.add_row("assistant tool-call turns", str(tool_calls))
        table.add_row("total reason ms", f"{total_reason:.1f}")
        table.add_row("total generate ms", f"{total_generate:.1f}")
        table.add_row("total turn ms", f"{total:.1f}")
        table.add_row("reason %", f"{(total_reason / total * 100):.1f}%")
        table.add_row("generate %", f"{(total_generate / total * 100):.1f}%")

        console.print(table)