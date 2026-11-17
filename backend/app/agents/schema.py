"""Turn a pydantic model into the strict JSON schema the model API accepts for structured
output and strict tools: every object closed, every property required, no decorative keywords."""
from typing import Any

from pydantic import BaseModel

_DROP = {"title", "default", "examples", "minLength", "maxLength", "pattern", "minimum", "maximum",
         "exclusiveMinimum", "exclusiveMaximum", "minItems", "maxItems", "format", "multipleOf"}


def _strict(node: Any) -> Any:
    if isinstance(node, list):
        return [_strict(n) for n in node]
    if not isinstance(node, dict):
        return node
    out = {k: _strict(v) for k, v in node.items() if k not in _DROP}
    if out.get("type") == "object" or "properties" in out:
        out["additionalProperties"] = False
        out["required"] = list(out.get("properties", {}).keys())
    return out


def strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    return _strict(model.model_json_schema())
