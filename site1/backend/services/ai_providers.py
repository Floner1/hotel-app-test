"""Chat model provider wrapper.

Single seam between the application and whatever generates chat replies.
Today that is Ollama running qwen3:4b on the local machine; swapping to a
cloud LLM later only requires adding a sibling ChatProvider subclass here and
pointing settings.AI_PROVIDER at it. Nothing above this module — not
ChatService, not the view — knows which model answered.

Same shape as backend/email_providers.py, which is the existing seam for the
send path.

On reasoning, measured on this machine 2026-08-22
-------------------------------------------------
qwen3:4b is a thinking model and it thinks whatever you tell it. Numbers below
are characters of reasoning for one fixed question, num_predict 1200:

    no marker at all            3438 reasoning chars, content clean
    /no_think in system          2527 reasoning chars, content clean
    /no_think in user            1262 reasoning chars, content clean
    /no_think in both             842 reasoning chars, content clean
    think=False (API param)         0 reasoning chars, RAW REASONING IN CONTENT

Two things follow.

1. `/no_think` is a nudge, not a switch. It cuts reasoning to about a quarter
   but never to zero, so it is sent on BOTH messages — that was the cheapest
   configuration, roughly a third of the tokens of no marker at all.

2. What keeps `content` clean is not `/no_think` at all: it is Ollama parsing
   the reasoning out into a separate `thinking` field. `think=False` tells
   Ollama not to parse, but the model keeps reasoning anyway, so the whole
   monologue lands in `content` with a literal `</think>` in it. That is the
   documented bug, it reproduces here, and it is why this module never passes
   think=False.

Because the model reasons regardless, reasoning and answer share the
num_predict budget. Setting that cap too low (400) meant generation stopped
mid-thought with done_reason='length' and an EMPTY content field — a blank
chat bubble for the guest. The cap is 1200 for headroom; it is a ceiling, not
a target, so a short answer still stops early and costs nothing extra.

strip_thinking() still runs on every reply, inside the provider where no
caller can forget it, because none of the above is a guarantee.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from django.conf import settings

logger = logging.getLogger(__name__)


def strip_thinking(text: str) -> str:
    """Drop any reasoning block, keeping only what follows the final tag.

    Splitting on the closing tag rather than matching a <think>...</think> pair
    is deliberate: the observed failure mode leaks a closing tag with no
    opening one, so a pair-matching regex would sail straight past it.

    rsplit, not split. The spec for this helper used split(..., 1)[1], which
    keeps everything after the FIRST closing tag — so on a reply carrying two
    of them ("a</think>b</think>c") it returns "b</think>c" and ships a literal
    </think> to the client, the exact thing this function exists to prevent.
    rsplit takes the last, so no tag can survive whatever the model does.
    """
    if "</think>" in text:
        return text.rsplit("</think>", 1)[1].strip()
    return text.strip()


class ChatProvider(ABC):
    """The seam. One method: text in, text out."""

    @abstractmethod
    def complete(self, system_prompt: str, user_message: str) -> str:
        """Return the model's reply, already stripped of any reasoning."""


class OllamaProvider(ChatProvider):
    """Local Ollama. Synchronous; exceptions propagate to ChatService."""

    def __init__(self, model: str | None = None, host: str | None = None):
        import ollama

        self.model = model or getattr(settings, "AI_MODEL", "qwen3:4b")
        self._client = ollama.Client(
            host=host or getattr(settings, "OLLAMA_HOST", "http://localhost:11434")
        )

    def complete(self, system_prompt: str, user_message: str) -> str:
        # Two attempts. The model sometimes runs away deliberating and emits no
        # answer at all; it is stochastic, so asking again usually works. See
        # the module docstring for why a bigger budget does not fix it.
        for _ in range(2):
            reply = self._attempt(system_prompt, user_message)
            if reply:
                return reply
        # Nothing twice over. Better a handled failure the view can turn into a
        # real sentence than an empty chat bubble.
        raise RuntimeError("Model returned no answer")

    def _attempt(self, system_prompt: str, user_message: str) -> str:
        response = self._client.chat(
            model=self.model,
            messages=[
                # /no_think on both messages — see the module docstring. On the
                # system message alone it left roughly three times the reasoning.
                {"role": "system", "content": f"{system_prompt}\n\n/no_think"},
                {"role": "user", "content": f"{user_message}\n\n/no_think"},
            ],
            options={
                # Low temperature: this answers factual questions off a price
                # table. Invention is the failure mode we care about.
                "temperature": 0.3,
                # Reasoning and answer share this budget. 400 was far too low —
                # generation stopped mid-thought and returned nothing at all.
                # 2000 was no better than 1200 (same 1-in-4 empty rate on the
                # worst question, just slower), so this stays at 1200.
                "num_predict": 1200,
            },
        )
        return strip_thinking(response["message"]["content"])


def get_provider() -> ChatProvider:
    """Resolve the configured provider. One name today, by design."""
    name = getattr(settings, "AI_PROVIDER", "ollama").lower()
    if name == "ollama":
        return OllamaProvider()
    raise ValueError(f"Unknown AI_PROVIDER: {name!r}")
