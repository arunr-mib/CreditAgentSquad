import json

import pytest
from app.agents.llm import (
    LLMRequest,
    LLMResponse,
    RecordedClient,
    RecordingClient,
    RecordingStale,
    ScriptedClient,
)


def _request(spec):
    return LLMRequest(model="m", system="s", messages=[{"role": "user", "content": "x"}],
                      record_key="spreading/b/2026-09-30/abc/01", spec=spec)


def _response():
    return LLMResponse(content=[{"type": "text", "text": "{}"}], stop_reason="end_turn", model="m", usage={})


def test_a_recording_is_stamped_with_the_spec_and_replays_under_the_same_spec(tmp_path):
    RecordingClient(ScriptedClient([_response()]), tmp_path).create(_request("spreading@5:aaaaaaaaaaaa"))
    stored = json.loads((tmp_path / "spreading/b/2026-09-30/abc/01.json").read_text())
    assert stored["_spec"] == "spreading@5:aaaaaaaaaaaa"
    assert RecordedClient(tmp_path).create(_request("spreading@5:aaaaaaaaaaaa")).stop_reason == "end_turn"


def test_a_recording_from_another_version_or_prompt_refuses_to_replay(tmp_path):
    RecordingClient(ScriptedClient([_response()]), tmp_path).create(_request("spreading@3:aaaaaaaaaaaa"))
    with pytest.raises(RecordingStale, match="spreading@3"):
        RecordedClient(tmp_path).create(_request("spreading@5:aaaaaaaaaaaa"))
    with pytest.raises(RecordingStale):
        RecordedClient(tmp_path).create(_request("spreading@3:bbbbbbbbbbbb"))  # same version, edited prompt


def test_an_unstamped_old_recording_is_stale_unless_the_run_accepts_it_by_agent(tmp_path):
    path = tmp_path / "spreading/b/2026-09-30/abc/01.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({**_response().to_json()}))
    with pytest.raises(RecordingStale, match="no stamp"):
        RecordedClient(tmp_path).create(_request("spreading@5:aaaaaaaaaaaa"))
    assert RecordedClient(tmp_path, accept_stale=frozenset({"spreading"})).create(
        _request("spreading@5:aaaaaaaaaaaa")).stop_reason == "end_turn"


def test_a_stale_stamped_recording_is_accepted_by_the_directory_name_too(tmp_path):
    # the agent's spec name and its recordings directory can differ (certificate_reader / certificate)
    RecordingClient(ScriptedClient([_response()]), tmp_path).create(
        LLMRequest(model="m", system="s", messages=[], record_key="certificate/b/2026-09-30/01",
                   spec="certificate_reader@1:aaaaaaaaaaaa"))
    stale = LLMRequest(model="m", system="s", messages=[], record_key="certificate/b/2026-09-30/01",
                       spec="certificate_reader@2:aaaaaaaaaaaa")
    with pytest.raises(RecordingStale):
        RecordedClient(tmp_path).create(stale)
    assert RecordedClient(tmp_path, accept_stale=frozenset({"certificate"})).create(stale).stop_reason == "end_turn"
    assert RecordedClient(tmp_path, accept_stale=frozenset({"certificate_reader"})).create(stale).stop_reason == "end_turn"


def test_a_request_with_no_spec_skips_the_check(tmp_path):
    RecordingClient(ScriptedClient([_response()]), tmp_path).create(_request(""))
    assert RecordedClient(tmp_path).create(_request("")).stop_reason == "end_turn"
