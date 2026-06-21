# AGENTS.md

Libre Asist is a LibreOffice Basic/UNO Python extension that exposes a
floating ChatGPT-like side panel inside LibreOffice Writer and Calc. The
user writes natural-language requests in the panel; the assistant reads
context from the active document, asks an LLM via a multi-provider HTTP
client, validates the model's proposed JSON, shows a preview, and only
applies the change after the user confirms in chat.

## How to run

There is no build step. The extension lives inside the LibreOffice user
profile and is loaded by the LibreOffice Basic/Python bridge.

```bash
# Modules import cleanly from the system Python 3 (3.14 in this env).
cd /home/nicolas/.config/libreoffice/4/user/Scripts/python/libre_asist
python3 -c "import sys; sys.path.insert(0,'.'); import panel, config, skills, ai_client, actions; print('OK')"
```

To actually open the panel inside LibreOffice, configure a macro that
calls `libre_asist.show_panel` (or run `python3 __init__.py show_panel`
in a context where LibreOffice's `uno` module is importable — usually
not possible from system Python, only from the LO Python bridge).

## Entry points

- `__init__.py` — module entry; defines `show_panel()` and
  `show_config_dialog()`. Has a `__main__` block that routes the first
  CLI arg to a function (only useful for syntax check / smoke test).
- `panel.py:show_panel` and `panel.py:show_config_dialog` — the actual
  LibreOffice entry points. Both are no-arg callables intended to be
  invoked from a LibreOffice macro.

## Module map

| File | Responsibility |
| --- | --- |
| `__init__.py` | LO entry points; sys.path bootstrap. |
| `config.py` | JSON config at `~/.config/libreoffice/4/user/libre_asist/config.json`. Provider presets, system-prompt presets, `load()` / `save()` / `apply_preset()`. |
| `ai_client.py` | Multi-provider HTTP client (`AIClient`). Auto-detects OpenAI, Ollama native, Anthropic, and MiniMax-native from the API URL. Optional `web_search` tool with tool-calling loop. |
| `web_search.py` | DuckDuckGo HTML backend, stdlib only. Returns `[{title,url,snippet}]`. |
| `prompts.py` | Thin compat wrapper around `skills_common.chat`. |
| `skills.py` | Router facade (`route(skill_name, user_prompt, ctx)`). Dispatches to `skills_calc` or `skills_writer` based on `ctx["kind"]`. |
| `skills_common.py` | Shared JSON prompt scaffolding (`_block`, `*_SCHEMA` constants, `chat` skill, `COMMON_RULES`). |
| `skills_calc.py` | All Calc prompt skills (`calc_formula`, `calc_audit_sheet`, `calc_summary_table_builder`, etc.). The `calc_preview` function is the keyword-based router for the main `preview` skill. |
| `skills_writer.py` | All Writer prompt skills (`writer_rewrite`, `writer_format`, `writer_export`, etc.). `writer_preview` is the keyword-based router. |
| `actions.py` | `extract_json` (parses ```json``` blocks), `validate_calc_preview` and `validate_writer_preview` (schema validation + safety checks), `preview_to_text` (human-readable summary). |
| `calc_ops.py` | UNO operations for Calc: cell/range access, selection context builder, profile/audit heuristics, `apply_preview`, `make_undo_snapshot`, `restore_snapshot`. |
| `writer_ops.py` | UNO operations for Writer: selection/document text, replace/insert/format, lists, tables, hyperlinks, headers/footers, footnotes, comments, track-changes, markdown insert, export, `apply_preview`, `make_undo_snapshot`, `restore_snapshot`. |
| `panel.py` | The UI: builds the dialog, wires listeners, runs the conversation loop, routes user input to skills, manages `pending_action` / `undo_stack` / `action_history`. |

## End-to-end flow

1. User opens panel → `PanelController.show()` (`panel.py:183`).
2. User selects content (or has a cursor) and types a request, hits Enter.
3. `do_send` (`panel.py:489`) does heuristic routing:
   - Confirmation / cancellation / undo / history text shortcuts.
   - `_looks_like_*` classifiers decide between read-only analysis,
     review, and an actionable change.
4. `_selection_context` builds the `ctx` dict:
   - Calc: `calc_ops.get_selection_context` returns sheet/range,
     column profiles, duplicates, bank-reconciliation hints,
     `allowed_cells` (the selection) and `generated_allowed_cells`
     (a 30×12 grid starting at the active cell).
   - Writer: `writer_ops.get_context` returns selection or whole
     document text (truncated to ~4000 chars plus a `text_tail` of the
     last 1200 chars), plus detected placeholders.
5. The skill router returns a prompt string (the LLM message). For
   action paths, `skills_calc.calc_preview` / `skills_writer.writer_preview`
   does a Spanish+English keyword match to pick the right specialized skill.
6. `AIClient.ask` POSTs to the configured endpoint. With
   `enable_web_search=True` it runs a tool-calling loop (max 3 iterations)
   using `web_search.search`.
7. The reply comes back. `_prepare_pending_action` extracts the
   ```json``` block, validates it via `actions.validate_preview`, and
   presents a `preview_to_text` summary. If validation fails and the
   user asked to "create" something, the code retries with stricter
   prompts and falls back to `_local_*_creation_proposal` baked-in
   templates.
8. User says `si` / `confirmar` / `ok` / `dale` → `_confirm_pending_action`
   calls `*_ops.apply_preview`, snapshots state into `undo_stack`
   (max 10), and records the action in `action_history` (max 20).
9. `deshacer` / `undo` / `revertir` → `_undo_last_change` calls
   `restore_snapshot`. Writer restores the full document text;
   Calc restores only the affected cells.

## Key conventions

- **The `ctx` dict is the contract between context builders, skills,
  and validators.** `kind` is `"calc"` or `"writer"`. Calc adds
  `sheet`, `range`, `allowed_cells`, `generated_allowed_cells`,
  `summary_allowed_cells`, `audit_report_allowed_cells`,
  `column_profiles`, `profile_summary`, `formula_audit`,
  `bank_reconciliation`. Writer adds `text`, `text_tail`,
  `has_selection`, `placeholders`, `placeholder_count`.
- **`allowed_cells` is the safety boundary** for Calc. Every validated
  change cell must be in this set or in `generated_allowed_cells` (used
  when creating new structure) / `summary_allowed_cells` /
  `audit_report_allowed_cells` for the corresponding target sheets.
- **Spanish-first copy.** All user-facing strings, system prompts,
  validators, and suggestion messages are in Spanish. Model replies
  are Spanish unless the user writes in English. Prompts instruct
  the model to match the user's language.
- **JSON proposals must be wrapped in a single ```json fenced code
  block.** `actions.extract_json` is forgiving (regex search then
  bracket-fallback) but the skills tell the model to return exactly one
  block with no commentary outside it.
- **`promptable` is a synonym for `applicable`**: the model never
  applies anything itself. The panel always shows a proposal, then the
  user confirms. The skill text in `skills_common.COMMON_RULES`
  reinforces this: "Nunca digas que ya modificaste el documento".
- **Snapshots are session-scoped.** `undo_stack` and `action_history`
  live on `PanelController` and vanish when the panel closes.

## Calc action contract (`CALC_ACTION_SCHEMA` in `skills_common.py`)

```json
{
  "summary": "...",
  "target_sheet": "Auditoria IA",
  "changes": [
    {
      "cell": "A1",
      "value": "texto o =formula",
      "formula": false,
      "bold": true,
      "italic": false,
      "background": "#D9EAF7",
      "font_color": "#000000",
      "border": true,
      "width": 2500
    }
  ]
}
```

- `formula=true` requires `value` to start with `=`. LibreOffice
  function names are in Spanish (`SUMA`, `SI`, `BUSCARV`, `SI.ERROR`,
  `ELEGIR`, `ALEATORIO.ENTRE`, `CONCATENAR`, `REDONDEAR`, `FECHA`,
  `TEXTO`).
- Colors are always `#RRGGBB` hex. `width` is in 1/100 mm (2500 = 2.5 cm).
- `target_sheet` lets a proposal write to a different sheet (e.g.
  `Auditoria IA`, `Resumen IA`). The validator enforces
  ≤31 chars and forbids `: \ / ? * [ ]` in the sheet name.
- The validator rejects changes where `cell` is outside the right
  `allowed_cells` set for the request type.

## Writer action contract (`WRITER_ACTION_SCHEMA` and friends)

Allowed actions (see `actions.py:210`):

- `insert_text`, `append_text`, `replace_selection`, `replace_document`
- `format_selection`, `format_document`
- `replace_text` (with `replacements: [{find, replace, match_case, replace_all}]`)
- `apply_list` (`bullet` | `number` | `outline`, `level` 0-9, `start_at`)
- `insert_hyperlink`, `insert_table`, `set_header_footer`,
  `insert_footnote`, `insert_comment`, `export_document`,
  `insert_markdown`, `track_changes`, `accept_all_redlines`,
  `reject_all_redlines`

Style keys: `bold`, `italic`, `font_size` (6-96), `font_name`,
`font_color`/`background` (`#RRGGBB` or decimal), `align`
(`left|center|right|justify`), `line_spacing` (0.8-3.0),
`space_before`/`space_after`/`left_margin`/`right_margin`/
`first_line_indent` (centésimas de milímetro, -5000..10000),
`paragraph_style` (e.g. `Heading 1`, `Text Body`).

`page_style` allows `left_margin`/`right_margin`/`top_margin`/
`bottom_margin` (centésimas de milímetro, 0..10000).

`actions._clean_writer_text` strips trailing dashes/underscores and
cuts at phrases like "Sugerencias de formato" so the model can't
smuggle formatting instructions into the output `text` field.

## AI client quirks

- Provider auto-detection (`ai_client.py:77`) keys off the URL:
  `/v1/messages` → Anthropic; `/api/generate` → Ollama generate;
  `/api/chat` → Ollama chat; `/v1/text/chatcompletion_v2` → MiniMax
  native; `/chat/completions` or `/v1/chat` → OpenAI-compatible.
- Only OpenAI-family + Anthropic + MiniMax-native + Ollama-chat support
  the `web_search` tool. `Ollama generate` and other formats silently
  fall back to plain completion.
- All HTTP goes through `urllib.request` — no `requests` dependency.
- `AIError` is the only user-visible exception. Network errors get
  prefixed with `HTTP <code>:`, `No se pudo conectar:`, or
  `Error de red:`.

## Validators: safety rails

- `actions.validate_calc_preview` enforces cell name format
  (`CELL_RE = ^[A-Z]{1,3}[0-9]{1,7}$` after stripping `$`), allowed-cell
  membership, formula prefix `=`, and rejects change entries that
  carry neither value nor format.
- `actions.validate_writer_preview` allows the actions listed above,
  strips trailing punctuation in `text`/`blocks[].text`, clamps
  `font_size`/`line_spacing`/margins, and limits each list to
  ≤80 blocks / ≤30 replacements / ≤20 comments.
- A failed validation always cancels the proposal — never silently
  applies a partial.

## Routing heuristics (panel.py)

The panel uses long Spanish+English keyword lists to classify user
input without an LLM call:

- `_is_confirmation` / `_is_cancellation` / `_is_undo_request` /
  `_is_history_request` (lines 539-583) — exact-match short answers.
- `_looks_like_review`, `_looks_like_placeholder_review`,
  `_looks_like_action`, `_looks_like_writer_edit`,
  `_looks_like_writer_create`, `_looks_like_writer_format_only`,
  `_looks_like_calc_readonly_analysis` — keyword-based classifiers.
- The "is it an action?" rule for Writer defaults to `True` unless
  the prompt contains a question word, so most free-form Writer
  prompts go through `skills.writer_preview` (which then picks the
  right specialized Writer skill by keyword match).

When adding a new intent, add the keyword(s) in both Spanish and
English to the relevant `_looks_like_*` list in `panel.py` AND the
matching branch in `skills_calc.calc_preview` /
`skills_writer.writer_preview`.

## Adding a new skill

1. Pick the right module: `skills_calc.py` for Calc, `skills_writer.py`
   for Writer. Reuse `_block(role, task, ctx, rules, output_contract,
   examples)` from `skills_common.py`.
2. Add a schema constant in `skills_common.py` if you need a new shape.
3. Register a new `Writer/Calc action` name in `actions.py:210` and
   add a validation branch in `validate_writer_preview` /
   `validate_calc_preview`.
4. Add the apply branch in `writer_ops.apply_preview` /
   `calc_ops.apply_preview`, and a human-readable summary line in
   `actions.preview_to_text`.
5. Add a keyword branch in `skills_writer.writer_preview` /
   `skills_calc.calc_preview` so `route("preview", ...)` reaches it.
6. Add any new safety-cell set (e.g. `target_allowed_cells`) in
   `calc_ops.get_selection_context` and a `panel.py` rule in
   `_allowed_cells_for_request`.
7. Add a `_looks_like_*` keyword list in `panel.py` if the new action
   needs a different routing decision from a chat prompt.
8. Smoke-test the import path:
   `python3 -c "import sys; sys.path.insert(0,'.'); import panel, skills, actions; print('OK')"`
   Anything that fails to import breaks the entire panel.

## Gotchas

- The system is installed in `~/.config/libreoffice/4/user/Scripts/python/libre_asist/`
  but the user config lives at `~/.config/libreoffice/4/user/libre_asist/config.json`
  (note the different `libre_asist` directory). This is intentional —
  config survives LibreOffice reinstalls.
- `panel.py:1` contains `# CACHE_BUSTER: 1781319001`. If you change
  the panel and the dialog doesn't update inside LibreOffice, bump
  this number. LibreOffice caches Python bytecode aggressively and
  sometimes won't re-import changed files until the file's mtime
  changes meaningfully.
- `__init__.py:11` does `os.path.dirname(os.path.abspath(__file__))`
  inside a `try/except NameError` because `__file__` is undefined
  when the module is loaded through some LO macro paths. Don't simplify
  it.
- `panel.py:382` hardcodes `dock_right` to position the dialog 24px
  from the right edge of a 1280px-wide screen. It does not query the
  actual screen size.
- `panel._run_background` runs user requests on a daemon thread.
  UNO calls must happen on the main LO thread — the existing code
  already invokes the thread only for the AI call and validation
  work, not for direct UNO mutations, so don't add new UNO writes
  inside the threaded runner.
- `calc_ops._apply_simple_border` (around line 588) only applies a
  basic border via `TableBorder2`. Complex borders are not supported
  in the current schema.
- `writer_ops.replace_text` falls back to a full document rewrite via
  `replace_document_with_style` when `createReplaceDescriptor` fails
  for a specific replacement. This can be slow on large documents.
- The two retry paths in `panel.py` (`_retry_writer_creation_json`,
  `_retry_calc_creation_json`) wrap the model call in a try/except
  and silently fall through to hard-coded local templates — this is
  intentional graceful degradation, not a bug.
- `writer_ops.make_undo_snapshot` saves the **entire** document text,
  not the changed range. Restoring is therefore a full rewrite via
  `replace_document_with_style`. For very large documents this is
  expensive; it is what enables reliable undo regardless of action
  type.
- `calc_ops.make_undo_snapshot` saves only cells listed in
  `preview["changes"]`, plus their format attributes. Restoring
  touches only those cells.
- `MAX_TOOL_ITERATIONS = 3` in `ai_client.py` caps the web-search
  tool-calling loop. Bump it if you find the model running out of
  iterations on multi-hop searches.
- The `__pycache__/` directory and the `.crush/` directory are local
  tooling state; they are gitignored.
- `IMPLEMENTATION_PLAN.md` is the Spanish-language product/architecture
  doc that this AGENTS.md summarizes. Read it for additional product
  context (e.g. the original prioritized roadmap).
- LibreOffice's Python (3.14 in this env) and the system Python
  share the same `libre_asist` directory. Editing a file from the
  system Python and then opening LibreOffice will pick up the new
  bytecode immediately (LibreOffice invalidates `.pyc` on mtime
  change), but the dialog itself caches the module reference
  across reopens — see the CACHE_BUSTER note above.

## Things not to change casually

- The `kind` discriminator in `ctx` (`"calc"` vs `"writer"`) is used
  in every skill, every validator, and the apply pipeline. Renaming
  it touches 30+ call sites.
- The validation rules in `actions.py` are the safety contract —
  if you loosen a constraint, document why in `IMPLEMENTATION_PLAN.md`
  and confirm it doesn't enable the model to escape `allowed_cells`.
- The provider URL detection in `ai_client._format` is the source of
  truth for which HTTP body shape gets sent. Adding a new provider
  means adding a new `if` branch and a new `_ask_<provider>` method.
- The schema constants in `skills_common.py` are referenced both from
  the prompt strings (telling the model what shape to return) and
  from `actions.py` (validating the shape). They must stay in sync.
