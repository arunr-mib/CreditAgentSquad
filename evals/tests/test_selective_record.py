import pytest
from app.agents.llm import (
    LLMRequest,
    LLMResponse,
    RecordedClient,
    RecordingClient,
    RecordingMissing,
    ScriptedClient,
)

from evals.run import RunRefused, SelectiveRecordingClient, main, make_client, parse_record_agents


def _request(key):
    return LLMRequest(system="s", messages=[{"role": "user", "content": "hi"}], tools=[], model="m",
                      effort="low", max_tokens=10, record_key=key, spec=f"{key.split('/')[0]}@1:abc")


def _answer(text):
    return LLMResponse(content=[{"type": "text", "text": text}], model="m", stop_reason="end_turn")


def test_only_the_chosen_agents_call_the_model_and_are_saved(tmp_path):
    RecordingClient(ScriptedClient([_answer("old spread")]), tmp_path).create(_request("spreading/b/p/01"))
    live = ScriptedClient([_answer("new review")])
    client = SelectiveRecordingClient(RecordingClient(live, tmp_path), RecordedClient(tmp_path), frozenset({"review"}))
    assert client.create(_request("spreading/b/p/01")).text() == "old spread"  # replayed, the model is not asked
    assert client.create(_request("review/b/p/01")).text() == "new review"     # recorded
    assert (tmp_path / "review/b/p/01.json").exists()
    assert [r.record_key for r in live.requests] == ["review/b/p/01"]
    assert RecordedClient(tmp_path).create(_request("review/b/p/01")).text() == "new review"


def test_a_missing_replay_is_an_error_not_a_call(tmp_path):
    live = ScriptedClient([_answer("x")])
    client = SelectiveRecordingClient(RecordingClient(live, tmp_path), RecordedClient(tmp_path), frozenset({"review"}))
    with pytest.raises(RecordingMissing):
        client.create(_request("intake/b/01"))
    assert not list(tmp_path.rglob("*.json"))


def test_parse_and_guards():
    assert parse_record_agents("covenant, review,early_warning") == {"covenant", "review", "early_warning"}
    assert parse_record_agents(None) == frozenset()
    with pytest.raises(RunRefused):
        parse_record_agents("spreading")
    with pytest.raises(RunRefused):
        make_client("recorded", None, record_agents=frozenset({"review"}))
    assert main(["--mode", "recorded", "--record-agents", "review"]) == 2
    assert main(["--mode", "record", "--record-agents", "intake"]) == 2
