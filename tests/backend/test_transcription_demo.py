# tests/backend/test_transcription_demo.py
"""Demo transcription replay: by recording_id and deterministically by upload hash."""
from src.backend.app.services import transcription_service as ts
from src.backend.app.services.replay_store import ReplayStore

PAIRS = [
    {"transcription": "Pedido [customer] [order-ref], 2 tacos", "expected_items": []},
    {"transcription": "Pedido [customer] [order-ref], 1 codo inox", "expected_items": []},
]


async def test_replay_by_recording_id(monkeypatch):
    monkeypatch.setattr(ts.settings, "APP_MODE", "demo")
    clients = {"replay": ReplayStore(PAIRS)}
    out = await ts.transcribe_audio_service(clients, b"whatever", "a.wav", recording_id=1)
    assert out == (PAIRS[1]["transcription"], 1)


async def test_replay_by_hash_is_deterministic(monkeypatch):
    monkeypatch.setattr(ts.settings, "APP_MODE", "demo")
    clients = {"replay": ReplayStore(PAIRS)}
    a = await ts.transcribe_audio_service(clients, b"same bytes", "a.wav")
    b = await ts.transcribe_audio_service(clients, b"same bytes", "b.ogg")
    assert a == b
    assert a[0] in {p["transcription"] for p in PAIRS}


async def test_unknown_recording_id_fails(monkeypatch):
    monkeypatch.setattr(ts.settings, "APP_MODE", "demo")
    clients = {"replay": ReplayStore(PAIRS)}
    out = await ts.transcribe_audio_service(clients, b"x", "a.wav", recording_id=99)
    assert out is None
