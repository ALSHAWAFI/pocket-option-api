# Code Generator

`PocketOptionClient`'s `on.*` / `emit.*` namespaces are **generated** from a JSON spec. The generator lives in `pocket_trader/generator/`.

## Purpose

`generated_client.py` is produced by assembling:

- `events.json` — the spec (methods per event/emit, Pydantic models, args).
- `templates/layout.jinja2` — main layout (imports + both namespaces + client class).
- `templates/on_method.jinja2`, `templates/emit.jinja2` — per-method fragments.
- `generate.py` — Jinja2 + Pydantic + Rich orchestration.

## Files

| Path | Role |
|------|------|
| `generate.py` | Entry point + build pipeline |
| `events.json` | Method definitions (`on`, `emit`, `imports`) |
| `templates/layout.jinja2` | Full client layout |
| `templates/on_method.jinja2` | Handlers |
| `templates/emit.jinja2` | Emit methods |
| `../generated_client.py` | Output (committed to repo) |

## Running

```bash
# From the repo root (uses jinja2, pydantic, rich)
python -m pocket_trader.generator.generate

# or directly
python pocket_trader/generator/generate.py
```

The pipeline (`CodeGenerator.generate()`):

1. **Load** `events.json` → `EventsData` (Pydantic `Method` models; `imports` defaults; missing `doc`/`return_type`/`pydantic_model` filled in).
2. **Generate** via `TemplateRenderer` (Jinja2 `trim_blocks`/`lstrip_blocks`, custom `indent` filter). If the layout template fails, falls back to `_generate_client_manual()`.
3. **Save** to `generated_client.py` — the previous file is first renamed to `generated_client.py.bak`.
4. **Validate** with `ast.parse`.
5. **Format** with `black` (fallback `ruff format`).

Failure to load events raises; it prints a Rich summary table on success.

## `events.json` schema

Validated against `EventsData` (Pydantic):

```jsonc
{
  "imports": ["from pocket_trader.types import TypedEventListener"],
  "on": [
    {
      "name": "update_balance",          // handler method name
      "event": "successupdateBalance",   // socket event string
      "doc": "Handle balance update events",
      "return_type": "models.SuccessUpdateBalanceEvent", // callback annotation
      "pydantic_model": "models.SuccessUpdateBalanceEvent" // or "null"
    }
  ],
  "emit": [
    {
      "name": "subscribe_to_asset",
      "event": "subscribeSymbol",
      "doc": "Subscribe to asset for real-time updates",
      "args": { "name": "asset", "type": "models.Asset" } // optional
    }
  ]
}
```

Generated emit methods call `self.client.send("event", arg)`; handler methods call `self.client.add_on("event", handler=..., model=...)`.

## Customizing

- **Add/rename an event:** edit `events.json`, then regenerate. `generated_client.py` is `DO NOT EDIT` — always edit the spec and regenerate.
- **Note:** `_ensure_templates()` re-creates the three `.jinja2` files from embedded defaults if they are missing.

> See the generated surface documented in [Client — Events & Emits](client.md). The generator itself is not required at runtime; `generated_client.py` is committed.

---

Next: [Examples](examples.md) · [Client](client.md) · [README](../README.md)