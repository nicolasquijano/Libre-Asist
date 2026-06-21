"""Validation and proposal helpers for AI-generated document changes."""

import json
import re
from i18n import _


CELL_RE = re.compile(r"^\$?[A-Za-z]{1,3}\$?[0-9]{1,7}$")
WRITER_STYLE_KEYS = {
    "bold", "italic", "font_size", "font_name", "font_color", "background",
    "align", "line_spacing", "space_before", "space_after", "left_margin",
    "right_margin", "first_line_indent", "paragraph_style",
}
WRITER_PAGE_KEYS = {"left_margin", "right_margin", "top_margin", "bottom_margin"}


def _clean_writer_text(text):
    text = str(text)
    cut_markers = (
        "Sugerencias de formato para LibreOffice Writer",
        "Sugerencias de formato",
        "Formato sugerido",
        "Indicaciones de formato",
        "Notas de formato",
    )
    lower = text.lower()
    cut_at = -1
    for marker in cut_markers:
        idx = lower.find(marker.lower())
        if idx >= 0 and (cut_at < 0 or idx < cut_at):
            cut_at = idx
    if cut_at >= 0:
        text = text[:cut_at]
    while text.rstrip().endswith(("—", "-", "_", "=", "─")):
        text = text.rstrip()[:-1]
    return text.strip()


def _parse_color(value):
    text = str(value).strip()
    if text.startswith("#") and len(text) == 7:
        return text
    if re.match(r"^[0-9]+$", text):
        return text
    raise ValueError(_("actions.error.writer_invalid_color", text))


def _validate_writer_style(style):
    if not isinstance(style, dict):
        return {}
    out = {}
    for key in ("bold", "italic"):
        if key in style:
            out[key] = bool(style.get(key))
    if "font_size" in style:
        size = float(style.get("font_size"))
        if size < 6 or size > 96:
            raise ValueError(_("actions.error.writer_font_size"))
        out["font_size"] = size
    if "font_name" in style:
        value = str(style.get("font_name")).strip()
        if value:
            out["font_name"] = value[:80]
    for key in ("font_color", "background"):
        if key in style:
            out[key] = _parse_color(style.get(key))
    if "align" in style:
        value = str(style.get("align")).strip().lower()
        allowed = {"left", "center", "right", "justify"}
        if value not in allowed:
            raise ValueError(_("actions.error.writer_align", value))
        out["align"] = value
    if "line_spacing" in style:
        spacing = float(style.get("line_spacing"))
        if spacing < 0.8 or spacing > 3.0:
            raise ValueError(_("actions.error.writer_line_spacing"))
        out["line_spacing"] = spacing
    for key in ("space_before", "space_after", "left_margin", "right_margin", "first_line_indent"):
        if key in style:
            value = int(float(style.get(key)))
            if value < -5000 or value > 10000:
                raise ValueError(_("actions.error.writer_measure", key))
            out[key] = value
    if "paragraph_style" in style:
        value = str(style.get("paragraph_style")).strip()
        if value:
            out["paragraph_style"] = value[:80]
    return out


def _validate_writer_page_style(style):
    if not isinstance(style, dict):
        return {}
    out = {}
    for key in WRITER_PAGE_KEYS:
        if key in style:
            value = int(float(style.get(key)))
            if value < 0 or value > 10000:
                raise ValueError(_("actions.error.writer_margin", key))
            out[key] = value
    return out


def _validate_writer_blocks(blocks):
    if not isinstance(blocks, list):
        return []
    out = []
    for item in blocks[:80]:
        if not isinstance(item, dict):
            raise ValueError(_("actions.error.writer_invalid_block"))
        text = _clean_writer_text(item.get("text", ""))
        if not text:
            continue
        block = {"text": text}
        style = _validate_writer_style(item.get("style", {}))
        if style:
            block["style"] = style
        out.append(block)
    return out


def _validate_writer_replacements(replacements):
    if not isinstance(replacements, list) or not replacements:
        raise ValueError(_("actions.error.writer_no_replacements"))
    out = []
    for item in replacements[:30]:
        if not isinstance(item, dict):
            raise ValueError(_("actions.error.writer_invalid_replacement"))
        find = str(item.get("find", ""))
        replace = str(item.get("replace", item.get("new_string", "")))
        if not find.strip():
            raise ValueError(_("actions.error.writer_no_find"))
        if len(find) > 500 or len(replace) > 2000:
            raise ValueError(_("actions.error.writer_replacement_long"))
        if find == replace:
            continue
        out.append({
            "find": find,
            "replace": replace,
            "match_case": bool(item.get("match_case", True)),
            "replace_all": bool(item.get("replace_all", item.get("replace_globally", True))),
        })
    if not out:
        raise ValueError(_("actions.error.writer_no_useful_replacements"))
    return out


def extract_json(text):
    if not text:
        raise ValueError(_("actions.error.empty_response"))
    match = re.search(r"```json\s*(.*?)\s*```", text, re.S | re.I)
    raw = match.group(1) if match else text
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError(_("actions.error.no_json_block"))
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(_("actions.error.invalid_json", str(e)))


def validate_calc_preview(data, allowed_cells=None):
    if not isinstance(data, dict):
        raise ValueError(_("actions.error.not_json"))
    changes = data.get("changes")
    if not isinstance(changes, list) or not changes:
        raise ValueError(_("actions.error.no_changes"))

    allowed = set(allowed_cells or [])
    out = {"summary": str(data.get("summary", "Cambios propuestos")), "changes": []}
    target_sheet = str(data.get("target_sheet", "")).strip()
    if target_sheet:
        if len(target_sheet) > 31 or any(ch in target_sheet for ch in (":", "\\", "/", "?", "*", "[", "]")):
            raise ValueError(_("actions.error.invalid_sheet_name", target_sheet))
        out["target_sheet"] = target_sheet
    for item in changes:
        if not isinstance(item, dict):
            raise ValueError(_("actions.error.invalid_change"))
        cell = str(item.get("cell", "")).replace("$", "").upper()
        if not CELL_RE.match(cell):
            raise ValueError(_("actions.error.invalid_cell", cell))
        if allowed and cell not in allowed:
            raise ValueError(_("actions.error.cell_outside", cell))
        value = item.get("value", "")
        formula = bool(item.get("formula", False))
        if formula and not str(value).strip().startswith("="):
            raise ValueError(_("actions.error.invalid_formula", cell))
        change = {"cell": cell}
        if "value" in item:
            change["value"] = str(value)
            change["formula"] = formula
        for key in ("bold", "italic", "background", "font_color", "width", "border"):
            if key in item:
                change[key] = item[key]
        if len(change) == 1:
            raise ValueError(_("actions.error.change_no_value", cell))
        out["changes"].append(change)
    return out


def validate_writer_preview(data):
    if not isinstance(data, dict):
        raise ValueError(_("actions.error.not_json"))
    action = str(data.get("action", "")).strip()
    if action in ("find_replace", "replace_all", "search_replace"):
        action = "replace_text"
        if "replacements" not in data and "operations" in data:
            data = dict(data)
            data["replacements"] = data.get("operations", [])
    allowed = {"insert_text", "replace_selection", "replace_document", "append_text", "format_selection", "format_document", "replace_text", "apply_list", "insert_hyperlink", "insert_table", "set_header_footer", "insert_footnote", "insert_comment", "export_document", "insert_markdown", "track_changes", "accept_all_redlines", "reject_all_redlines"}
    if action not in allowed:
        raise ValueError(_("actions.error.writer_action_not_allowed", action))
    out = {"summary": str(data.get("summary", "Cambios propuestos")), "action": action}
    if action in {"insert_text", "replace_selection", "replace_document", "append_text"}:
        blocks = _validate_writer_blocks(data.get("blocks", []))
        text = _clean_writer_text(data.get("text", ""))
        if blocks:
            out["blocks"] = blocks
            out["text"] = "\n\n".join(block["text"] for block in blocks)
        elif isinstance(text, str) and text.strip():
            out["text"] = text
        else:
            raise ValueError(_("actions.error.writer_no_text"))
        merged_style = {}
        if isinstance(data.get("style", {}), dict):
            merged_style.update(data.get("style", {}))
        merged_style.update({key: data.get(key) for key in WRITER_STYLE_KEYS if key in data})
        out.update(_validate_writer_style(merged_style))
        page_style = _validate_writer_page_style(data.get("page_style", {}))
        if page_style:
            out["page_style"] = page_style
    if action == "format_selection":
        style = {key: data.get(key) for key in WRITER_STYLE_KEYS if key in data}
        out.update(_validate_writer_style(style))
        page_style = _validate_writer_page_style(data.get("page_style", {}))
        if page_style:
            out["page_style"] = page_style
        if len(out) <= 2:
            raise ValueError(_("actions.error.format_no_changes"))
    if action == "format_document":
        style = {key: data.get(key) for key in WRITER_STYLE_KEYS if key in data}
        if isinstance(data.get("style", {}), dict):
            style.update(data.get("style", {}))
        out.update(_validate_writer_style(style))
        page_style = _validate_writer_page_style(data.get("page_style", {}))
        if page_style:
            out["page_style"] = page_style
        mode = str(data.get("structure_mode", "professional")).strip().lower()
        if mode not in ("professional", "letter", "report", "minimal"):
            mode = "professional"
        out["structure_mode"] = mode
    if action == "replace_text":
        out["replacements"] = _validate_writer_replacements(data.get("replacements", []))
    if action == "apply_list":
        ls = str(data.get("list_style", "bullet")).lower()
        if ls not in ("bullet", "number", "outline"):
            raise ValueError(_("actions.error.list_style", ls))
        out["list_style"] = ls
        out["level"] = max(0, min(9, int(data.get("level", 0))))
        out["start_at"] = max(1, int(data.get("start_at", 1)))
    if action == "insert_hyperlink":
        url = str(data.get("url", "")).strip()
        if not url:
            raise ValueError(_("actions.error.no_url"))
        out["url"] = url
        out["text"] = str(data.get("text", ""))
        out["apply_to_selection"] = bool(data.get("apply_to_selection", False))
    if action == "insert_table":
        rows = int(data.get("rows", 3))
        cols = int(data.get("cols", 3))
        if rows < 1 or rows > 50:
            raise ValueError(_("actions.error.table_rows"))
        if cols < 1 or cols > 20:
            raise ValueError(_("actions.error.table_cols"))
        out["rows"] = rows
        out["cols"] = cols
        headers = data.get("headers", [])
        if isinstance(headers, list):
            out["headers"] = [str(h)[:500] for h in headers[:20]]
        rows_data = data.get("rows_data", [])
        if isinstance(rows_data, list):
            out["rows_data"] = [[str(c)[:500] for c in row[:20]] for row in rows_data[:50]]
        if isinstance(data.get("style"), dict):
            out["style"] = data.get("style")
    if action == "set_header_footer":
        if isinstance(data.get("header"), dict):
            out["header"] = {"text": str(data.get("header", {}).get("text", "")), "alignment": str(data.get("header", {}).get("alignment", "left")), "page_numbers": bool(data.get("header", {}).get("page_numbers", False))}
        if isinstance(data.get("footer"), dict):
            out["footer"] = {"text": str(data.get("footer", {}).get("text", "")), "alignment": str(data.get("footer", {}).get("alignment", "left")), "page_numbers": bool(data.get("footer", {}).get("page_numbers", False))}
        out["first_page_different"] = bool(data.get("first_page_different", False))
    if action == "insert_footnote":
        marker = str(data.get("marker_text", "")).strip()
        note = str(data.get("note_text", "")).strip()
        if not marker:
            raise ValueError(_("actions.error.footnote_no_marker"))
        if not note:
            raise ValueError(_("actions.error.footnote_no_text"))
        out["marker_text"] = marker[:200]
        out["note_text"] = note[:2000]
    if action == "insert_comment":
        comments = data.get("comments", [])
        if not isinstance(comments, list) or not comments:
            single = str(data.get("comment", "")).strip()
            if single:
                comments = [{"marker_text": data.get("marker_text", ""), "comment": single, "author": data.get("author", "Libre Asist")}]
        if not isinstance(comments, list) or not comments:
            raise ValueError(_("actions.error.comment_no_content"))
        out_comments = []
        for item in comments[:20]:
            if not isinstance(item, dict):
                raise ValueError(_("actions.error.comment_invalid"))
            comment = str(item.get("comment", "")).strip()
            if not comment:
                continue
            marker = str(item.get("marker_text", "")).strip()
            author = str(item.get("author", "Libre Asist")).strip() or "Libre Asist"
            out_comments.append({
                "marker_text": marker[:200],
                "comment": comment[:2000],
                "author": author[:80],
            })
        if not out_comments:
            raise ValueError(_("actions.error.comment_no_useful"))
        out["comments"] = out_comments
    if action == "export_document":
        fmt = str(data.get("format", "pdf")).lower()
        if fmt not in ("pdf", "docx", "odt", "txt"):
            raise ValueError(_("actions.error.export_format", fmt))
        out["format"] = fmt
        out["path"] = str(data.get("path", ""))
    if action == "insert_markdown":
        md = str(data.get("markdown_text", "")).strip()
        if not md:
            raise ValueError(_("actions.error.markdown_empty"))
        if len(md) > 50000:
            raise ValueError(_("actions.error.markdown_long"))
        out["markdown_text"] = md
        mode = str(data.get("mode", "insert_text")).strip()
        if mode not in ("insert_text", "replace_document", "append_text"):
            mode = "insert_text"
        out["mode"] = mode
    if action == "track_changes":
        out["enabled"] = bool(data.get("enabled", True))
    if action in ("accept_all_redlines", "reject_all_redlines"):
        pass
    return out


def validate_preview(data, doc_kind="calc", allowed_cells=None):
    if doc_kind == "writer":
        return validate_writer_preview(data)
    return validate_calc_preview(data, allowed_cells=allowed_cells)


def preview_to_text(preview):
    lines = [preview.get("summary", _("actions.summary.default")), ""]
    if preview.get("action"):
        lines.append(_("preview.action", preview["action"]))
        if preview.get("action") == "replace_document":
            lines.append(_("preview.scope_replace_doc"))
        if preview.get("action") == "format_document":
            lines.append(_("preview.scope_format_doc"))
            if preview.get("structure_mode"):
                lines.append(_("preview.mode", preview["structure_mode"]))
        if preview.get("action") == "replace_text":
            lines.append(_("preview.replacements", len(preview.get("replacements", []))))
            for idx, item in enumerate(preview.get("replacements", [])[:10], 1):
                lines.append(str(idx) + ". " + item["find"][:80] + " -> " + item["replace"][:80])
            if len(preview.get("replacements", [])) > 10:
                lines.append(_("preview.more_replacements", len(preview.get("replacements", [])) - 10))
            return "\n".join(lines).strip()
        if preview.get("blocks"):
            lines.append(_("preview.blocks", len(preview["blocks"])))
            for idx, block in enumerate(preview["blocks"][:8], 1):
                first_line = block["text"].splitlines()[0][:90]
                lines.append(str(idx) + ". " + first_line)
            if len(preview["blocks"]) > 8:
                lines.append(_("preview.more_blocks", len(preview["blocks"]) - 8))
        elif preview.get("text"):
            lines.append(preview["text"])
        for key in sorted(WRITER_STYLE_KEYS):
            if key in preview:
                lines.append(key + ": " + str(preview[key]))
        if preview.get("page_style"):
            lines.append("page_style: " + str(preview["page_style"]))
        if preview.get("action") == "apply_list":
            lines.append(_("preview.list_style", preview.get("list_style", "bullet"), preview.get("level", 0)))
        if preview.get("action") == "insert_hyperlink":
            lines.append(_("preview.url", preview.get("url", "")))
            if preview.get("text"):
                lines.append(_("preview.text", preview.get("text", "")))
        if preview.get("action") == "insert_table":
            lines.append(_("preview.table", preview.get("rows", 3), preview.get("cols", 3)))
            if preview.get("headers"):
                lines.append(_("preview.headers", ", ".join(str(h) for h in preview.get("headers", []))))
        if preview.get("action") == "set_header_footer":
            if preview.get("header"):
                lines.append(_("preview.header", preview.get("header", {}).get("text", "")))
            if preview.get("footer"):
                lines.append(_("preview.footer", preview.get("footer", {}).get("text", "")))
        if preview.get("action") == "insert_footnote":
            lines.append(_("preview.marker", preview.get("marker_text", "")[:80]))
            lines.append(_("preview.note", preview.get("note_text", "")[:80]))
        if preview.get("action") == "insert_comment":
            lines.append(_("preview.comments", len(preview.get("comments", []))))
            for idx, item in enumerate(preview.get("comments", [])[:8], 1):
                marker = item.get("marker_text") or _("preview.cursor_selection")
                lines.append(str(idx) + ". " + marker[:60] + " -> " + item.get("comment", "")[:90])
            if len(preview.get("comments", [])) > 8:
                lines.append(_("preview.more_comments", len(preview.get("comments", [])) - 8))
        if preview.get("action") == "export_document":
            lines.append(_("preview.export_format", preview.get("format", "pdf")))
            if preview.get("path"):
                lines.append(_("preview.export_path", preview.get("path", "")))
        if preview.get("action") == "insert_markdown":
            lines.append(_("preview.markdown_mode", preview.get("mode", "insert_text")))
            md = preview.get("markdown_text", "")
            preview_lines = md.splitlines()[:12]
            lines.append("Contenido:")
            lines.extend(preview_lines)
            if len(md.splitlines()) > 12:
                lines.append(_("preview.markdown_lines_more", len(md.splitlines()) - 12))
        if preview.get("action") == "track_changes":
            lines.append(_("preview.track_changes_on") if preview.get("enabled") else _("preview.track_changes_off"))
        if preview.get("action") == "accept_all_redlines":
            lines.append(_("preview.accept_redlines"))
        if preview.get("action") == "reject_all_redlines":
            lines.append(_("preview.reject_redlines"))
        return "\n".join(lines).strip()
    if preview.get("target_sheet"):
        lines.append(_("preview.target_sheet", preview.get("target_sheet")))
    for idx, change in enumerate(preview.get("changes", []), 1):
        parts = []
        if "value" in change:
            kind = _("preview.value_kind_formula") if change.get("formula") else _("preview.value_kind_value")
            parts.append(kind + ": " + change["value"])
        for key in ("bold", "italic", "background", "font_color", "width", "border"):
            if key in change:
                parts.append(key + ": " + str(change[key]))
        lines.append(str(idx) + ". " + change["cell"] + " <- " + ", ".join(parts))
    return "\n".join(lines).strip()
