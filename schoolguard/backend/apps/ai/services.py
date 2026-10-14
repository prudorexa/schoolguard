"""
ai/services.py

ask_assistant() is the whole AI Financial Assistant feature (blueprint
section 21) in one function, and it follows the blueprint's AI data flow
exactly (section 20):

  1. Claude sees the question and the TOOL whitelist (tools.py) -- not the
     database, not raw SQL, not free-form code execution. It can only
     request one of a handful of named, parameterized functions.
  2. WE execute that tool, in Python, against the caller's own school --
     Claude never gets a live connection or credentials of any kind.
  3. Claude sees ONLY the JSON that tool returned, with an explicit
     instruction to answer using only those numbers and never invent a
     figure that isn't present.
  4. Every step is logged to AIAnalysisRecord -- question, which tool was
     called with what parameters, exactly what data came back, and the
     final answer -- so any answer can be audited and replayed later.

`client` is injectable specifically so this can be tested without a
network call: tests pass a fake object with the same `.messages.create()`
shape the real `anthropic.Anthropic()` client has.
"""

from typing import Any, Protocol

from .claude_client import AIConfigurationError, get_client
from .models import AIAnalysisRecord
from .tools import build_claude_tools, execute_tool

SYSTEM_PROMPT_TOOL_SELECTION = (
    "You are SchoolGuard's financial assistant. The user is a school finance "
    "staff member asking about their own school's real financial data. You "
    "must call exactly one of the available tools to retrieve the data "
    "needed to answer their question -- you have no other way to see any "
    "data, and you must never guess or invent figures."
)

SYSTEM_PROMPT_ANSWER = (
    "Answer the user's question using ONLY the JSON data provided below. "
    "Do not invent, estimate, or round in a way that changes the meaning of "
    "any figure. If the data doesn't fully answer the question, say what's "
    "missing rather than guessing. Keep the answer concise -- a few "
    "sentences, in plain language, suitable for a school finance officer."
)


class ClaudeClientProtocol(Protocol):
    """Structural type -- anything with this shape can stand in for the
    real anthropic.Anthropic() client in tests."""

    messages: Any


class AIAssistantError(Exception):
    pass


def ask_assistant(*, school, user, question: str, client=None) -> dict:
    record = AIAnalysisRecord(school=school, asked_by=user, question=question)

    try:
        active_client = client or get_client()
        model = _get_model()

        tool_response = active_client.messages.create(
            model=model,
            max_tokens=512,
            system=SYSTEM_PROMPT_TOOL_SELECTION,
            tools=build_claude_tools(),
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": question}],
        )

        tool_use_block = next((b for b in tool_response.content if getattr(b, "type", None) == "tool_use"), None)
        if tool_use_block is None:
            raise AIAssistantError("The assistant did not select a data source to answer this question.")

        tool_name = tool_use_block.name
        tool_params = tool_use_block.input or {}
        record.tool_called = tool_name
        record.tool_params = tool_params

        data = execute_tool(tool_name, school, tool_params)
        record.data_retrieved = data

        answer_response = active_client.messages.create(
            model=model,
            max_tokens=512,
            system=SYSTEM_PROMPT_ANSWER,
            messages=[
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nData:\n{data}",
                }
            ],
        )
        text_block = next((b for b in answer_response.content if getattr(b, "type", None) == "text"), None)
        answer = text_block.text if text_block else ""
        record.answer = answer

        return {"answer": answer, "tool_called": tool_name, "data": data}

    except AIConfigurationError as exc:
        record.error = str(exc)
        raise
    except Exception as exc:  # noqa: BLE001 -- log whatever went wrong, then re-raise
        record.error = str(exc)
        raise
    finally:
        record.save()


def _get_model() -> str:
    from django.conf import settings

    return settings.ANTHROPIC_MODEL
