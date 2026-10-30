"""
EchoAgent — Conversation Generator Agent with RAG Question Selection
Selects optimal questions to guide vocal diversity across the 120-second session.
"""

import random
import structlog

from src.agent.prompts import CURATED_QUESTIONS, SYSTEM_PROMPT

logger = structlog.get_logger(__name__)


class ConversationAgent:
    """Manages conversational dialogue turns and question progression."""

    def __init__(self, system_prompt: str = SYSTEM_PROMPT):
        self.system_prompt = system_prompt
        self.used_question_ids: set[str] = set()
        self.turn_count = 0

    def get_initial_greeting(self) -> str:
        """Greeting that starts Session 1."""
        return (
            "Hey! I am EchoAgent. Let us chat for a couple of minutes so I can get to know you. "
            "To kick things off, what has been on your mind today?"
        )

    def get_cloned_session_greeting(self, display_name: str | None = None) -> str:
        """Greeting that starts Session 2 ('Speak to Yourself')."""
        name_str = f", {display_name}" if display_name else ""
        return (
            f"Hey{name_str}! Look at this... you are now talking directly to your own cloned voice! "
            "How does it feel to hear your own voice speaking back to you?"
        )

    def select_next_question(self, user_text: str | None = None) -> dict[str, str]:
        """Selects the next question from the RAG bank ensuring category diversity."""
        available = [q for q in CURATED_QUESTIONS if q["id"] not in self.used_question_ids]

        if not available:
            # Reset pool if all questions were used
            self.used_question_ids.clear()
            available = CURATED_QUESTIONS

        selected = random.choice(available)
        self.used_question_ids.add(selected["id"])
        self.turn_count += 1

        logger.info("question_selected", turn=self.turn_count, q_id=selected["id"], cat=selected["category"])
        return selected

    def generate_response(self, user_transcript: str | None = None) -> str:
        """Generate conversational reply incorporating the next question."""
        question_data = self.select_next_question(user_transcript)
        question = question_data["question"]

        if not user_transcript or self.turn_count == 1:
            return question

        # Contextual transition phrase + question
        transitions = [
            "That is fascinating! Speaking of which, ",
            "I love that perspective! Here is something I am curious about: ",
            "That tells me a lot about you! Tell me, ",
            "That is really cool. ",
        ]
        prefix = random.choice(transitions)
        return f"{prefix}{question}"

