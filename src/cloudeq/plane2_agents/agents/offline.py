"""Offline stage text. These strings are simulations, not model output."""

from cloudeq.plane2_agents.models import StageName


class OfflineStageWorker:
    live_crewai = False
    live_gemini = False

    def summarize(self, stage: StageName, prompt: str) -> str:
        clipped = " ".join(prompt.split())[:180]
        return (
            f"Simulated {stage.value} decision for: {clipped}. "
            "This is an offline simulation, not a live CrewAI or Gemini result."
        )

    def diff_summary(self, task_id: str, iteration: int) -> str:
        return f"simulated diff task={task_id} iteration={iteration}"
