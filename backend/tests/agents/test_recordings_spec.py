import json

import pytest
from app.agents.llm import (
    LLMRequest,
    LLMResponse,
    RecordedClient,
    RecordingClient,
    RecordingStale,
    ScriptedClient,
    spec_stamp,
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


def test_a_recorded_request_with_no_spec_is_an_error_not_a_silent_skip(tmp_path):
    RecordingClient(ScriptedClient([_response()]), tmp_path).create(_request(""))
    with pytest.raises(ValueError, match="no spec"):
        RecordedClient(tmp_path).create(_request(""))


def test_a_prompt_only_stamp_is_compared_on_the_prompt_alone_and_counted(tmp_path):
    path = tmp_path / "spreading/b/2026-09-30/abc/01.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({**_response().to_json(), "_spec": "spreading@3:pppppppppppp", "_basis": "prompt-only"}))
    client = RecordedClient(tmp_path)
    same_prompt = _request("spreading@3:zzzzzzzzzzzz")  # other tools/schema: not checkable, not stale
    same_prompt.spec_prompt = "pppppppppppp"
    assert client.create(same_prompt).stop_reason == "end_turn" and client.prompt_only_verified == 1
    other = _request("spreading@3:zzzzzzzzzzzz")
    other.spec_prompt = "qqqqqqqqqqqq"
    with pytest.raises(RecordingStale):
        client.create(other)
    bumped = _request("spreading@4:zzzzzzzzzzzz")
    bumped.spec_prompt = "pppppppppppp"
    with pytest.raises(RecordingStale):
        client.create(bumped)


def _stamp(**changes):
    args = {"system": "p", "tools": [{"name": "t", "input_schema": {"type": "object"}}],
            "schema": {"type": "object", "properties": {"a": {"type": "string"}}}, "effort": "high",
            "max_tokens": 100, "model": "m"}
    return spec_stamp("spreading", "4", **{**args, **changes})[0]


def test_a_tool_schema_or_output_schema_edit_without_a_version_bump_makes_a_recording_stale(tmp_path):
    RecordingClient(ScriptedClient([_response()]), tmp_path).create(_request(_stamp()))
    assert RecordedClient(tmp_path).create(_request(_stamp())).stop_reason == "end_turn"
    edited_tool = _stamp(tools=[{"name": "t", "input_schema": {"type": "object", "required": ["x"]}}])
    edited_schema = _stamp(schema={"type": "object", "properties": {"a": {"type": "number"}}})
    assert len({_stamp(), edited_tool, edited_schema}) == 3
    for stamp in (edited_tool, edited_schema, _stamp(effort="low"), _stamp(max_tokens=5), _stamp(model="n")):
        with pytest.raises(RecordingStale):
            RecordedClient(tmp_path).create(_request(stamp))
