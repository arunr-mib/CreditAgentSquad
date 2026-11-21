"""Model access for the product's agents: one interface, three ways to serve it.

- LiveClient calls the Claude Messages API (billable).
- RecordingClient wraps a live client and saves every response to disk.
- RecordedClient replays saved responses, so tests and CI never call a model.
- ScriptedClient returns responses given in code (unit tests).
"""
import hashlib
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from app.core.config import Settings, get_settings

FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass
class LLMRequest:
    model: str
    system: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] = field(default_factory=list)
    output_schema: dict[str, Any] | None = None
    effort: str = "high"
    max_tokens: int = 32000
    record_key: str = ""  # where a recording of this exchange lives: "<agent>/<task key>/<step>"
    spec: str = ""  # "<agent>@<version>:<sha-256 of everything the model sees, 12 hex>": see spec_stamp
    spec_prompt: str = ""  # the system prompt's own sha-256, 12 hex (for recordings stamped on the prompt only)


@dataclass
class LLMResponse:
    content: list[dict[str, Any]]  # content blocks as plain dicts
    stop_reason: str
    model: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    request_id: str | None = None
    stop_details: dict[str, Any] | None = None

    def text(self) -> str:
        return "".join(b.get("text", "") for b in self.content if b.get("type") == "text")

    def tool_uses(self) -> list[dict[str, Any]]:
        return [b for b in self.content if b.get("type") == "tool_use"]

    def to_json(self) -> dict[str, Any]:
        return {"content": self.content, "stop_reason": self.stop_reason, "model": self.model,
                "usage": self.usage, "request_id": self.request_id, "stop_details": self.stop_details}

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "LLMResponse":
        return cls(content=data["content"], stop_reason=data["stop_reason"], model=data.get("model", ""),
                   usage=data.get("usage", {}), request_id=data.get("request_id"),
                   stop_details=data.get("stop_details"))


class LLMClient(Protocol):
    mode: str

    def create(self, request: LLMRequest) -> LLMResponse: ...


class RecordingMissing(Exception):
    """Raised in recorded mode when no saved response exists for a request."""


def spec_stamp(name: str, version: str, *, system: str, tools: list, schema: Any, effort: str, max_tokens: int,
               model: str) -> tuple[str, str]:
    """What a recording was made under: the agent and version, and a hash of every request value that is the
    agent's own (system prompt, tool definitions as sent, output schema, effort, max tokens, model).
    Returns (stamp, prompt hash)."""
    body = {"system": system, "tools": tools, "schema": schema, "effort": effort, "max_tokens": max_tokens,
            "model": model}
    digest = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:12]
    return f"{name}@{version}:{digest}", hashlib.sha256(system.encode()).hexdigest()[:12]


class RecordingStale(Exception):
    """A saved model response was made under another version or prompt of the agent than the one asking."""


# ---- stable ids for replay ---------------------------------------------------------------------------
# Fact, document and calculation ids are random per run, so a recorded answer that cites one cites an id
# that does not exist in the replay. The harness (never the product) fixes that by value: at record time
# it saves, beside each response, a descriptor of every id the request showed the model; at replay it
# describes the ids in the replay's request and rewrites the recorded ids to the replay's where the
# descriptor matches exactly once. A resolver is `uuid string -> descriptor dict | None`; the product
# never supplies one, ids stay random and the ledger is untouched.

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
IdResolver = Callable[[str], "dict[str, Any] | None"]


def uuids_in(value: Any) -> list[str]:
    """Every uuid in a request or response, lower case, first appearance first."""
    seen: list[str] = []
    for m in _UUID.finditer(json.dumps(value, default=str)):
        u = m.group(0).lower()
        if u not in seen:
            seen.append(u)
    return seen


def describe_ids(value: Any, resolver: IdResolver) -> dict[str, dict[str, Any]]:
    out = {}
    for u in uuids_in(value):
        descriptor = resolver(u)
        if descriptor is not None:
            out[u] = descriptor
    return out


def _descriptor_key(descriptor: dict[str, Any]) -> str:
    return json.dumps(descriptor, sort_keys=True, default=str)


def remap_ids(record_key: str, recorded: dict[str, Any], replay_request: LLMRequest, resolver: IdResolver,
              ) -> dict[str, str]:
    """Recorded id -> replay id, for each id the recorded response cites that has a descriptor. A cited id
    with no descriptor (one the model invented) is not mapped. An id whose descriptor matches no replay id
    (the value or the source changed) or more than one (ambiguous) raises RecordingStale."""
    described: dict[str, dict[str, Any]] = recorded.get("_ids") or {}
    cited = [u for u in uuids_in({k: v for k, v in recorded.items() if not k.startswith("_")}) if u in described]
    if not cited:
        return {}
    index: dict[str, list[str]] = {}
    for u, d in describe_ids({"m": replay_request.messages}, resolver).items():
        index.setdefault(_descriptor_key(d), []).append(u)
    mapping: dict[str, str] = {}
    for u in cited:
        matches = index.get(_descriptor_key(described[u]), [])
        if len(matches) != 1:
            why = "matches no id in this run (the value or the source changed)" if not matches else \
                f"matches {len(matches)} ids in this run (ambiguous)"
            raise RecordingStale(f"{record_key}: the recorded answer cites {u}, described as "
                                 f"{_descriptor_key(described[u])}, which {why}")
        mapping[u] = matches[0]
    return mapping


def _rewrite(content: Any, mapping: dict[str, str]) -> Any:
    if not mapping:
        return content
    text = json.dumps(content)
    text = _UUID.sub(lambda m: mapping.get(m.group(0).lower(), m.group(0)), text)
    return json.loads(text)


class LiveClient:
    """Calls the Claude Messages API. Streaming is used so long outputs do not time out."""

    mode = "live"

    def __init__(self, settings: Settings | None = None):
        import anthropic  # imported here so tests never need network or a key

        s = settings or get_settings()
        if not s.anthropic_api_key:
            raise RuntimeError("No model key is set (SQUAD_ANTHROPIC_API_KEY or ANTHROPIC_API_KEY); live model runs are not available.")
        self._anthropic = anthropic
        self._client = anthropic.Anthropic(api_key=s.anthropic_api_key, base_url=s.squad_anthropic_base_url)

    def create(self, request: LLMRequest) -> LLMResponse:
        output_config: dict[str, Any] = {"effort": request.effort}
        if request.output_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": request.output_schema}
        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "system": request.system,
            "messages": request.messages,
            "thinking": {"type": "adaptive"},
            "output_config": output_config,
            "cache_control": {"type": "ephemeral"},
            # if the model declines for safety reasons, the API re-runs the request on its default
            # fallback model inside the same call
            "betas": [FALLBACK_BETA],
            "fallbacks": "default",
        }
        if request.tools:
            kwargs["tools"] = request.tools
        with self._client.beta.messages.stream(**kwargs) as stream:
            message = stream.get_final_message()
        usage = message.usage
        details = getattr(message, "stop_details", None)
        return LLMResponse(
            content=[block.model_dump(mode="json", exclude_none=True) for block in message.content],
            stop_reason=message.stop_reason or "",
            model=message.model,
            usage={
                "input_tokens": getattr(usage, "input_tokens", 0) or 0,
                "output_tokens": getattr(usage, "output_tokens", 0) or 0,
                "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_input_tokens": getattr(usage, "cache_creation_input_tokens", 0) or 0,
            },
            request_id=getattr(message, "_request_id", None),
            stop_details=details.model_dump(mode="json") if details is not None else None,
        )


def _recording_path(root: Path, record_key: str) -> Path:
    if not record_key or ".." in record_key:
        raise ValueError(f"bad record_key {record_key!r}")
    return root / f"{record_key}.json"


class RecordedClient:
    mode = "recorded"

    def __init__(self, root: str | Path | None = None, accept_stale: frozenset[str] = frozenset(),
                 resolver: IdResolver | None = None):
        self.root = Path(root or get_settings().squad_recordings_dir)
        self.accept_stale = frozenset(accept_stale)
        self.resolver = resolver
        self.prompt_only_verified = 0  # recordings replayed on a prompt-only stamp

    def create(self, request: LLMRequest) -> LLMResponse:
        path = _recording_path(self.root, request.record_key)
        if not path.exists():
            raise RecordingMissing(f"no recorded model response at {path}")
        data = json.loads(path.read_text())
        if not request.spec:
            raise ValueError(f"a recorded-mode request for {request.record_key} carries no spec: it cannot be checked")
        stamp = data.get("_spec")
        if data.get("_basis") == "prompt-only":
            # stamped from git history (best effort): only the prompt could be recovered, so only it is compared
            wanted = f"{request.spec.split(':', 1)[0]}:{request.spec_prompt}"
            ok = stamp == wanted
            if ok:
                self.prompt_only_verified += 1
        else:
            ok = stamp == request.spec
        if not ok:
            # an agent is named by its spec name or by its recordings directory (they can differ)
            names = {request.spec.split("@", 1)[0], request.record_key.split("/", 1)[0]}
            if not names & self.accept_stale:
                raise RecordingStale(f"{path} was recorded under {stamp or 'no stamp'}, this request is {request.spec}"
                                     + ("" if stamp else " (no stamp: an old recording)"))
        response = LLMResponse.from_json({k: v for k, v in data.items() if not k.startswith("_")})
        if self.resolver is not None and data.get("_ids"):
            mapping = remap_ids(request.record_key, data, request, self.resolver)
            response.content = _rewrite(response.content, mapping)
        return response


class RecordingClient:
    mode = "record"

    def __init__(self, inner: LLMClient, root: str | Path | None = None, resolver: IdResolver | None = None):
        self.inner = inner
        self.root = Path(root or get_settings().squad_recordings_dir)
        self.resolver = resolver

    def create(self, request: LLMRequest) -> LLMResponse:
        # described before the call, while the ids the model is shown are the ones in the database
        ids = describe_ids({"m": request.messages}, self.resolver) if self.resolver is not None else None
        response = self.inner.create(request)
        path = _recording_path(self.root, request.record_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        extra = {"_ids": ids} if ids is not None else {}
        path.write_text(json.dumps({**response.to_json(), "_spec": request.spec, "_basis": "full", **extra},
                                   indent=1, sort_keys=True))
        return response


class ScriptedClient:
    """Returns the given responses in order and keeps the requests it saw."""

    mode = "scripted"

    def __init__(self, responses: list[LLMResponse]):
        self._responses = list(responses)
        self.requests: list[LLMRequest] = []

    def create(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if not self._responses:
            raise RecordingMissing("the scripted client has no more responses")
        return self._responses.pop(0)


class KeyedScriptedClient:
    """Scripted responses chosen by the start of the request's record key (one list per agent)."""

    mode = "scripted"

    def __init__(self, responses: dict[str, list[LLMResponse]]):
        self._responses = {prefix: list(items) for prefix, items in responses.items()}
        self.requests: list[LLMRequest] = []

    def create(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        for prefix, items in self._responses.items():
            if request.record_key.startswith(prefix) and items:
                return items.pop(0)
        raise RecordingMissing(f"no scripted response for {request.record_key}")


def model_status(settings: Settings | None = None) -> dict[str, Any]:
    """Whether an agent could get an answer here. Live and record modes need a key; recorded mode
    needs stored responses to replay."""
    s = settings or get_settings()
    mode = s.squad_llm_mode
    if mode in ("live", "record"):
        connected = bool(s.anthropic_api_key.strip())
        reason = "" if connected else "No model key is set for this deployment."
    else:
        root = Path(s.squad_recordings_dir)
        connected = root.is_dir() and any(root.rglob("*.json"))
        reason = "" if connected else "This deployment replays recorded model responses and has none stored."
    return {"mode": mode, "model": s.squad_model, "connected": connected, "reason": reason}


def client_for(settings: Settings | None = None) -> LLMClient:
    s = settings or get_settings()
    if s.squad_llm_mode == "live":
        return LiveClient(s)
    if s.squad_llm_mode == "record":
        return RecordingClient(LiveClient(s), s.squad_recordings_dir)
    return RecordedClient(s.squad_recordings_dir)
