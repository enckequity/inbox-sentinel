"""Registration with no configuration: tools and hooks only, no network,
no bundled skills, and the watcher stays off."""
from __future__ import annotations

import asyncio
import socket
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_register_with_no_config_is_offline_and_off(plugin, ctx, monkeypatch):
    monkeypatch.delenv("INBOX_SENTINEL_CLIENT_ID", raising=False)
    monkeypatch.delenv("INBOX_SENTINEL_CLIENT_SECRET", raising=False)

    def no_network(*_a, **_kw):
        raise AssertionError("registration must not open network connections")
    monkeypatch.setattr(socket, "create_connection", no_network)
    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(plugin, "credentialed_provider_request", no_network)

    plugin.register(ctx)

    assert sorted(ctx.tools) == ["inbox_sentinel_feedback", "inbox_sentinel_status",
                                 "inbox_sentinel_test"]
    assert {t["toolset"] for t in ctx.tools.values()} == {"inbox_sentinel"}
    assert sorted(ctx.hooks) == ["on_session_start", "pre_llm_call"]
    assert ctx.skills == {}

    async def fire():
        for cbs in ctx.hooks.values():
            for cb in cbs:
                await cb()
    asyncio.run(fire())  # enabled defaults to false: no watcher starts
    assert ctx.spawned == []
    assert plugin._WATCHERS == {}
    status = plugin._status(ctx)
    assert status["enabled"] is False and status["running"] is False
    assert status["delivery_target"] == "relay"


def test_setup_skill_is_not_shipped():
    assert not (REPO_ROOT / "skills").exists()


def test_manifest_is_neutral_and_off_by_default():
    import hermes_yaml as yaml
    text = (REPO_ROOT / "plugin.yaml").read_text()
    manifest = yaml.safe_load(text)
    schema = manifest["config_schema"]
    assert schema["enabled"]["default"] is False
    assert schema["delivery_target"]["default"] == "relay"
    for name in ("Hermes", "Nous"):
        assert name not in manifest["description"]
        assert name not in schema["delivery_target"]["description"]
    assert "push" not in manifest["tags"]
