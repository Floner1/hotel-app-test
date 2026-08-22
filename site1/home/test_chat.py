"""Chat widget: the deterministic pieces.

Scope note: the model's *wording* is not testable here — it changes run to run.
What is testable, and what these cover, is the machinery around it: that raw
reasoning can never survive the trip to the client, that the seam is a real
seam, that the endpoint only answers POST, and that the system prompt is built
from the room_price table rather than from anything the model made up.

The live-model checks (a grounded price, a refusal to invent) are a separate
end-to-end run — see docs/superpowers/plans/2026-08-22-local-llm-chat-widget.md
Task 6. They need Ollama up, so they do not belong in the unit suite.
"""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from backend.services.ai_providers import ChatProvider, OllamaProvider, strip_thinking


# ---------------------------------------------------------------- strip_thinking

def test_strip_thinking_removes_reasoning_before_close_tag():
    raw = "<think>I should reason about this</think>The rate is 650,000 VND."
    assert strip_thinking(raw) == "The rate is 650,000 VND."


def test_strip_thinking_handles_bare_close_tag():
    """The observed think=False failure mode: reasoning text and a closing tag
    with no opening tag at all. Splitting on the closer is what saves us."""
    raw = "Hmm, the user is asking about price.</think>Rooms start at 650,000 VND."
    assert strip_thinking(raw) == "Rooms start at 650,000 VND."


def test_strip_thinking_passes_clean_text_through_trimmed():
    assert strip_thinking("  Just an answer.  ") == "Just an answer."


def test_strip_thinking_never_leaks_a_close_tag():
    for raw in ["<think>a</think>b", "a</think>b", "clean", "</think>", "x</think>y</think>z"]:
        assert "</think>" not in strip_thinking(raw)


def test_strip_thinking_keeps_only_the_final_answer_on_repeat_tags():
    assert strip_thinking("one</think>two</think>three") == "three"


# ---------------------------------------------------------------- the seam

def test_chatprovider_cannot_be_instantiated():
    with pytest.raises(TypeError):
        ChatProvider()


def test_ollama_provider_implements_the_seam():
    assert issubclass(OllamaProvider, ChatProvider)


def test_provider_strips_thinking_from_whatever_the_model_returns(monkeypatch):
    """The safety net runs inside the provider, so no caller can forget it."""
    provider = OllamaProvider(model="qwen3:4b")

    def fake_chat(*, model, messages, options=None):
        return {"message": {"content": "internal monologue</think>The real answer."}}

    monkeypatch.setattr(provider._client, "chat", fake_chat)
    assert provider.complete("sys", "hi") == "The real answer."


def test_provider_sends_no_think_instruction(monkeypatch):
    """/no_think is model-level, so it has to ride in the system message."""
    provider = OllamaProvider(model="qwen3:4b")
    captured = {}

    def fake_chat(*, model, messages, options=None):
        captured["messages"] = messages
        return {"message": {"content": "ok"}}

    monkeypatch.setattr(provider._client, "chat", fake_chat)
    provider.complete("You are a concierge.", "hi")

    system_msg = captured["messages"][0]
    assert system_msg["role"] == "system"
    assert "/no_think" in system_msg["content"]


# ---------------------------------------------------------------- prompt grounding

@pytest.fixture
def priced_rooms(db):
    from data.models import Hotel, RoomPrice
    hotel = Hotel.objects.create(hotel_name='Thien Tai Hotel', address='452 Nguyen Thi Minh Khai')
    RoomPrice.objects.create(
        hotel=hotel, room_type='1 Bed No Window', price_per_night=650000,
        room_description='A comfortable and affordable option.',
    )
    return hotel


def test_system_prompt_carries_real_room_prices(priced_rooms):
    from backend.services.services import ChatService
    prompt = ChatService.build_system_prompt()
    assert '1 Bed No Window' in prompt
    assert '650' in prompt


def test_system_prompt_forbids_inventing_details(priced_rooms):
    from backend.services.services import ChatService
    prompt = ChatService.build_system_prompt().lower()
    assert "don't know" in prompt or "do not know" in prompt


def test_blank_message_is_rejected_before_reaching_the_model():
    from backend.services.services import ChatService
    with pytest.raises(ValidationError):
        ChatService.reply('   ')


def test_overlong_message_is_rejected_before_reaching_the_model():
    from backend.services.services import ChatService
    with pytest.raises(ValidationError):
        ChatService.reply('x' * 2001)


# ---------------------------------------------------------------- routing / view

def test_chat_url_resolves():
    assert reverse('chat') == '/chat/'


def test_get_is_rejected(client):
    assert client.get('/chat/').status_code == 405


def test_blank_message_returns_400(client):
    resp = client.post('/chat/', {'message': '   '},
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.status_code == 400
    assert resp.json()['status'] == 'error'


def test_post_without_csrf_token_is_forbidden():
    """CSRF is enforced, same as every other POST endpoint on the site."""
    from django.test import Client
    resp = Client(enforce_csrf_checks=True).post(
        '/chat/', {'message': 'hello'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    assert resp.status_code == 403


# ---------------------------------------------------------------- empty replies

def test_provider_raises_when_the_model_returns_nothing(monkeypatch):
    """Regression: a blank chat bubble.

    qwen3:4b reasons even when told not to, and that reasoning spends the
    num_predict budget. With the cap set too low the generation was cut off
    (done_reason='length') before any answer was emitted, so content came back
    empty and the widget rendered an empty message. An empty answer is a
    failed call, so it is raised as one — the view already turns that into a
    'try again shortly' message.
    """
    provider = OllamaProvider(model="qwen3:4b")
    monkeypatch.setattr(provider._client, "chat",
                        lambda **kw: {"message": {"content": "   "}})
    with pytest.raises(RuntimeError):
        provider.complete("sys", "hi")


def test_provider_raises_when_only_reasoning_comes_back(monkeypatch):
    """Reasoning with no answer after it strips down to nothing."""
    provider = OllamaProvider(model="qwen3:4b")
    monkeypatch.setattr(provider._client, "chat",
                        lambda **kw: {"message": {"content": "thinking out loud</think>"}})
    with pytest.raises(RuntimeError):
        provider.complete("sys", "hi")


def test_no_think_rides_on_both_messages(monkeypatch):
    """Measured: /no_think in the system prompt alone left ~2500 characters of
    reasoning; on both messages it dropped to ~840, roughly a third of the
    tokens per reply. It is a nudge, not a switch, so it goes in both places."""
    provider = OllamaProvider(model="qwen3:4b")
    captured = {}

    def fake_chat(**kw):
        captured.update(kw)
        return {"message": {"content": "ok"}}

    monkeypatch.setattr(provider._client, "chat", fake_chat)
    provider.complete("You are a concierge.", "hi")

    system_msg, user_msg = captured["messages"]
    assert "/no_think" in system_msg["content"]
    assert "/no_think" in user_msg["content"]
    assert "hi" in user_msg["content"]


def test_generation_budget_leaves_room_for_an_answer(monkeypatch):
    """num_predict caps thinking + answer together. 400 was not enough: the
    model hit the cap mid-reasoning and emitted no answer at all."""
    provider = OllamaProvider(model="qwen3:4b")
    captured = {}

    def fake_chat(**kw):
        captured.update(kw)
        return {"message": {"content": "ok"}}

    monkeypatch.setattr(provider._client, "chat", fake_chat)
    provider.complete("sys", "hi")
    assert captured["options"]["num_predict"] >= 1000


def test_provider_retries_once_when_the_first_answer_is_empty(monkeypatch):
    """qwen3:4b occasionally runs away deliberating and emits no answer.

    Measured on 'Do you rent motorbikes and how much?': 1 empty in 4 at
    num_predict 1200, and still 1 in 4 at 2000 — the reasoning simply expands
    to fill whatever budget it is given (7522 characters of it at 2000), so a
    bigger cap is not the fix. It is stochastic, so a single retry is: it takes
    a 1-in-4 failure to about 1 in 16.
    """
    provider = OllamaProvider(model="qwen3:4b")
    calls = []

    def fake_chat(**kw):
        calls.append(1)
        content = "" if len(calls) == 1 else "Yes, 150,000 VND."
        return {"message": {"content": content}}

    monkeypatch.setattr(provider._client, "chat", fake_chat)
    assert provider.complete("sys", "hi") == "Yes, 150,000 VND."
    assert len(calls) == 2


def test_provider_gives_up_after_the_retry(monkeypatch):
    """Two empties in a row is a real failure, not bad luck. Raise it."""
    provider = OllamaProvider(model="qwen3:4b")
    calls = []

    def fake_chat(**kw):
        calls.append(1)
        return {"message": {"content": ""}}

    monkeypatch.setattr(provider._client, "chat", fake_chat)
    with pytest.raises(RuntimeError):
        provider.complete("sys", "hi")
    assert len(calls) == 2
