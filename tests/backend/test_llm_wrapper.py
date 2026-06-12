# tests/backend/test_llm_wrapper.py
"""The multi-provider wrapper routes by model-name prefix and returns None on failure.
No network: provider clients are faked. Spec US-1 (real-mode path exists and is tested)."""
from types import SimpleNamespace

from src.backend.app.core import llm_wrapper

MESSAGES = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hola"}]


class FakeOpenAI:
    def __init__(self):
        captured = {}
        self.captured = captured

        class Completions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return SimpleNamespace(choices=[SimpleNamespace(
                    message=SimpleNamespace(content='{"ok": true}'))])
        self.chat = SimpleNamespace(completions=Completions())


def test_gpt_prefix_routes_to_openai(monkeypatch):
    fake = FakeOpenAI()
    monkeypatch.setattr(llm_wrapper, "_initialize_openai", lambda: fake)
    out = llm_wrapper.get_llm_completion("gpt-4o", MESSAGES, temperature=0.1,
                                         response_format={"type": "json_object"})
    assert out == '{"ok": true}'
    assert fake.captured["model"] == "gpt-4o"
    assert fake.captured["response_format"] == {"type": "json_object"}


def test_unknown_prefix_returns_none():
    assert llm_wrapper.get_llm_completion("mistral-large", MESSAGES) is None


def test_provider_exception_returns_none(monkeypatch):
    def boom():
        raise RuntimeError("init failed")
    monkeypatch.setattr(llm_wrapper, "_initialize_openai", boom)
    assert llm_wrapper.get_llm_completion("gpt-4o", MESSAGES) is None


def test_gemini_prefix_splits_system(monkeypatch):
    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text='{"ordered_ids": []}')

    fake = SimpleNamespace(models=FakeModels())
    monkeypatch.setattr(llm_wrapper, "_initialize_google", lambda: fake)
    out = llm_wrapper.get_llm_completion("gemini-2.5-flash", MESSAGES,
                                         response_format={"type": "json_object"})
    assert out == '{"ordered_ids": []}'
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["config"].system_instruction == "sys"
    assert captured["config"].response_mime_type == "application/json"
    assert "hola" in captured["contents"]
