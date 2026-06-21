"""Writer document operations.

get/set text in Writer documents via UNO. Selection-based operations
work in both Writer and Impress (and any TextDocument service).
"""

try:
    import uno
except Exception:
    uno = None

import re


ALIGN_VALUES = {
    "left": 0,
    "right": 1,
    "justify": 2,
    "center": 3,
}


def _parse_color(value):
    text = str(value).strip()
    if text.startswith("#") and len(text) == 7:
        return int(text[1:], 16)
    try:
        return int(text)
    except Exception:
        return -1


def get_selection_text(doc):
    if doc is None:
        return ""
    sel = doc.getCurrentSelection()
    if sel is None or sel.getCount() == 0:
        return ""
    text_parts = []
    for i in range(sel.getCount()):
        try:
            text_parts.append(sel.getByIndex(i).getString())
        except Exception:
            pass
    return "\n".join(text_parts)


def replace_selection(doc, new_text):
    if doc is None:
        return False
    sel = doc.getCurrentSelection()
    if sel is None or sel.getCount() == 0:
        insert_at_cursor(doc, new_text)
        return True
    for i in range(sel.getCount()):
        try:
            sel.getByIndex(i).setString(new_text)
        except Exception:
            pass
    return True


def insert_at_cursor(doc, text):
    if doc is None:
        return False
    try:
        controller = doc.getCurrentController()
        cursor = controller.getViewCursor()
        cursor.getText().insertString(cursor, text, False)
        return True
    except Exception:
        return False


def _apply_text_style(obj, preview):
    if "bold" in preview:
        obj.CharWeight = 150 if preview.get("bold") else 100
    if "italic" in preview:
        obj.CharPosture = 2 if preview.get("italic") else 0
    if "font_size" in preview:
        obj.CharHeight = float(preview.get("font_size"))
    if "font_name" in preview:
        obj.CharFontName = str(preview.get("font_name"))
    if "font_color" in preview:
        obj.CharColor = _parse_color(preview.get("font_color"))
    if "background" in preview:
        try:
            obj.CharBackColor = _parse_color(preview.get("background"))
            obj.CharBackTransparent = False
        except Exception:
            pass
        try:
            obj.ParaBackColor = _parse_color(preview.get("background"))
            obj.ParaBackTransparent = False
        except Exception:
            pass
    if "align" in preview:
        obj.ParaAdjust = ALIGN_VALUES.get(str(preview.get("align")).lower(), 0)
    if "line_spacing" in preview and uno is not None:
        try:
            spacing = uno.createUnoStruct("com.sun.star.style.LineSpacing")
            spacing.Mode = 0
            spacing.Height = int(float(preview.get("line_spacing")) * 100)
            obj.ParaLineSpacing = spacing
        except Exception:
            pass
    for key, prop in (
        ("space_before", "ParaTopMargin"),
        ("space_after", "ParaBottomMargin"),
        ("left_margin", "ParaLeftMargin"),
        ("right_margin", "ParaRightMargin"),
        ("first_line_indent", "ParaFirstLineIndent"),
    ):
        if key in preview:
            try:
                setattr(obj, prop, int(preview.get(key)))
            except Exception:
                pass
    if "paragraph_style" in preview:
        try:
            obj.ParaStyleName = str(preview.get("paragraph_style"))
        except Exception:
            pass


def _merged_style(base, override):
    out = {}
    for key in (
        "bold", "italic", "font_size", "font_name", "font_color", "background",
        "align", "line_spacing", "space_before", "space_after", "left_margin",
        "right_margin", "first_line_indent", "paragraph_style",
    ):
        if key in base:
            out[key] = base[key]
    if isinstance(override, dict):
        out.update(override)
    return out


def _apply_page_style(doc, preview):
    page_style = preview.get("page_style")
    if not isinstance(page_style, dict) or not page_style:
        return
    try:
        controller = doc.getCurrentController()
        cursor = controller.getViewCursor()
        style_name = cursor.PageStyleName
        families = doc.getStyleFamilies()
        page_styles = families.getByName("PageStyles")
        style = page_styles.getByName(style_name)
    except Exception:
        return
    for key, prop in (
        ("left_margin", "LeftMargin"),
        ("right_margin", "RightMargin"),
        ("top_margin", "TopMargin"),
        ("bottom_margin", "BottomMargin"),
    ):
        if key in page_style:
            try:
                setattr(style, prop, int(page_style.get(key)))
            except Exception:
                pass


def insert_at_cursor_with_style(doc, text, preview):
    if doc is None:
        return False
    try:
        _apply_page_style(doc, preview)
        controller = doc.getCurrentController()
        cursor = controller.getViewCursor()
        _apply_text_style(cursor, preview)
        cursor.getText().insertString(cursor, text, False)
        return True
    except Exception:
        return insert_at_cursor(doc, text)


def replace_selection_with_style(doc, text, preview):
    if doc is None:
        return False
    _apply_page_style(doc, preview)
    sel = doc.getCurrentSelection()
    if sel is None or sel.getCount() == 0:
        return insert_at_cursor_with_style(doc, text, preview)
    changed = False
    for i in range(sel.getCount()):
        try:
            part = sel.getByIndex(i)
            part.setString(text)
            _apply_text_style(part, preview)
            changed = True
        except Exception:
            pass
    return changed


def _insert_blocks_at_cursor(doc, blocks, preview, append=False):
    if doc is None or not blocks:
        return False
    try:
        _apply_page_style(doc, preview)
        text_obj = doc.getText()
        if append:
            cursor = text_obj.createTextCursor()
            cursor.gotoEnd(False)
        else:
            cursor = doc.getCurrentController().getViewCursor()
        for idx, block in enumerate(blocks):
            if idx > 0:
                text_obj.insertControlCharacter(cursor, 0, False)
            style = _merged_style(preview, block.get("style", {}))
            _apply_text_style(cursor, style)
            text_obj.insertString(cursor, block.get("text", ""), False)
        return True
    except Exception:
        return False


def _clear_document(doc):
    try:
        text_obj = doc.getText()
        cursor = text_obj.createTextCursor()
        cursor.gotoStart(False)
        cursor.gotoEnd(True)
        cursor.setString("")
        return True
    except Exception:
        return False


def replace_document_with_style(doc, text, preview):
    if doc is None:
        return False
    try:
        _apply_page_style(doc, preview)
        text_obj = doc.getText()
        cursor = text_obj.createTextCursor()
        cursor.gotoStart(False)
        cursor.gotoEnd(True)
        cursor.setString(text)
        _apply_text_style(cursor, preview)
        return True
    except Exception:
        return False


def replace_document_with_blocks(doc, blocks, preview):
    if doc is None or not blocks:
        return False
    if not _clear_document(doc):
        return False
    return _insert_blocks_at_cursor(doc, blocks, preview)


def replace_text(doc, replacements):
    if doc is None or not replacements:
        return 0
    changed = 0
    fallback_needed = []
    for item in replacements:
        find = item.get("find", "")
        replace = item.get("replace", "")
        if not find:
            continue
        try:
            desc = doc.createReplaceDescriptor()
            desc.SearchString = find
            desc.ReplaceString = replace
            desc.SearchCaseSensitive = bool(item.get("match_case", True))
            desc.SearchRegularExpression = False
            if item.get("replace_all", True):
                count = doc.replaceAll(desc)
                changed += int(count or 0)
            else:
                found = doc.findFirst(desc)
                if found:
                    found.setString(replace)
                    changed += 1
        except Exception:
            fallback_needed.append(item)
    if fallback_needed:
        changed += _replace_text_fallback(doc, fallback_needed)
    return changed


def _replace_text_fallback(doc, replacements):
    text = get_document_text(doc)
    if not text:
        return 0
    changed = 0
    new_text = text
    for item in replacements:
        find = item.get("find", "")
        replace = item.get("replace", "")
        if not find:
            continue
        replace_all = bool(item.get("replace_all", True))
        if item.get("match_case", True):
            occurrences = new_text.count(find)
            if occurrences:
                max_replace = -1 if replace_all else 1
                new_text = new_text.replace(find, replace, max_replace)
                changed += occurrences if replace_all else 1
        else:
            pattern = re.compile(re.escape(find), re.I)
            new_text, occurrences = pattern.subn(replace, new_text, 0 if replace_all else 1)
            changed += occurrences
    if changed and new_text != text:
        return changed if replace_document_with_style(doc, new_text, {}) else 0
    return 0


def format_document_structure(doc, preview):
    if doc is None:
        return 0
    _apply_page_style(doc, preview)
    mode = preview.get("structure_mode", "professional")
    base = {
        "font_name": preview.get("font_name", "Liberation Sans"),
        "font_size": preview.get("font_size", 12),
        "font_color": preview.get("font_color", "#222222"),
        "line_spacing": preview.get("line_spacing", 1.15),
        "space_after": preview.get("space_after", 180),
        "align": preview.get("align", "justify"),
        "paragraph_style": "Text Body",
    }
    title = {
        "font_name": base["font_name"],
        "font_size": 18 if mode != "minimal" else 16,
        "bold": True,
        "font_color": "#1F4E79",
        "align": "center" if mode in ("letter", "professional") else "left",
        "space_after": 260,
        "paragraph_style": "Heading 1",
    }
    subtitle = {
        "font_name": base["font_name"],
        "font_size": 13,
        "bold": True,
        "font_color": "#3B3B3B",
        "align": "left",
        "space_before": 160,
        "space_after": 120,
        "paragraph_style": "Heading 2",
    }
    signature = {
        "font_name": base["font_name"],
        "font_size": base["font_size"],
        "italic": True,
        "align": "left",
        "space_before": 240,
        "space_after": 120,
        "paragraph_style": "Text Body",
    }
    count = 0
    try:
        enum = doc.getText().createEnumeration()
        paragraph_index = 0
        while enum.hasMoreElements():
            part = enum.nextElement()
            try:
                if not part.supportsService("com.sun.star.text.Paragraph"):
                    continue
                text = part.getString().strip()
                if not text:
                    continue
                lower = text.lower()
                if paragraph_index == 0 and len(text) <= 120:
                    style = title
                elif lower.startswith(("asunto:", "tema:", "referencia:", "ref:")) or (len(text) <= 70 and text.endswith(":")):
                    style = subtitle
                elif lower.startswith(("atentamente", "saludos", "un saludo", "cordialmente", "firma", "con cariño", "con amor")):
                    style = signature
                else:
                    style = base
                _apply_text_style(part, style)
                count += 1
                paragraph_index += 1
            except Exception:
                pass
    except Exception:
        return 0
    return count


def _replace_selection_with_blocks(doc, blocks, preview):
    if not blocks:
        return False
    text = "\n\n".join(block.get("text", "") for block in blocks)
    return replace_selection_with_style(doc, text, preview)


def get_document_text(doc):
    if doc is None:
        return ""
    try:
        enum = doc.getText().createEnumeration()
        parts = []
        while enum.hasMoreElements():
            el = enum.nextElement()
            if el.supportsService("com.sun.star.text.Paragraph"):
                parts.append(el.getString())
        return "\n".join(parts)
    except Exception:
        return ""


def detect_placeholders(text, max_items=80):
    if not text:
        return []
    patterns = [
        r"\[[^\[\]\n]{1,80}\]",
        r"\{[^\{\}\n]{1,80}\}",
        r"<[^<>\n]{1,80}>",
        r"\b(NOMBRE|APELLIDO|FECHA|DIRECCION|DIRECCIÓN|EMPRESA|CUIT|DNI|EMAIL|CORREO|TELEFONO|TELÉFONO|DESTINATARIO|FIRMA|ASUNTO)\b",
        r"\b(Tu nombre|Nombre completo|Ciudad, País|dia/mes/año|dd/mm/aaaa)\b",
    ]
    found = []
    seen = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            value = match.group(0).strip()
            key = value.lower()
            wrapped_key = "[" + key + "]"
            brace_key = "{" + key + "}"
            angle_key = "<" + key + ">"
            if wrapped_key in seen or brace_key in seen or angle_key in seen:
                continue
            if key in seen:
                continue
            seen.add(key)
            before = text[max(0, match.start() - 45):match.start()].replace("\n", " ")
            after = text[match.end():match.end() + 45].replace("\n", " ")
            found.append({
                "text": value,
                "context": (before + value + after).strip(),
            })
            if len(found) >= max_items:
                return found
    return found


def make_undo_snapshot(doc, preview=None):
    if doc is None:
        return None
    text = get_document_text(doc)
    return {"kind": "writer", "text": text}


def restore_snapshot(doc, snapshot):
    if doc is None or not snapshot or snapshot.get("kind") != "writer":
        return 0
    return 1 if replace_document_with_style(doc, snapshot.get("text", ""), {}) else 0


def get_context(doc, max_chars=4000):
    selection = get_selection_text(doc)
    whole = "" if selection else get_document_text(doc)
    source_text = selection or whole
    source_chars = len(source_text)
    placeholders = detect_placeholders(source_text)
    if source_chars > max_chars:
        text = source_text[:max_chars]
        tail_chars = min(1200, max_chars // 3)
        text_tail = source_text[-tail_chars:] if not selection else ""
        truncated = True
    else:
        text = source_text
        text_tail = ""
        truncated = False
    return {
        "kind": "writer",
        "selection": selection,
        "text": text,
        "text_tail": text_tail,
        "has_selection": bool(selection.strip()),
        "selection_chars": len(selection),
        "document_chars": len(whole) if not selection else len(selection),
        "context_chars": len(text),
        "context_scope": "selection" if selection else "document",
        "truncated": truncated,
        "placeholders": placeholders,
        "placeholder_count": len(placeholders),
    }


def apply_list(doc, style):
    if doc is None:
        return 0
    list_style = str(style.get("list_style", "bullet")).lower()
    level = max(0, min(9, int(style.get("level", 0))))
    start_at = max(1, int(style.get("start_at", 1)))
    sel = doc.getCurrentSelection()
    if list_style == "number":
        style_name = "List Number"
    elif list_style == "outline":
        style_name = "Numbering"
    else:
        style_name = "List Bullet"
    count = 0
    if sel and sel.getCount() > 0:
        for i in range(sel.getCount()):
            try:
                part = sel.getByIndex(i)
                text = part.getString().strip()
                if not text:
                    continue
                part.ParaStyleName = style_name
                try:
                    part.NumberingLevel = level
                except Exception:
                    pass
                if list_style == "number" and start_at > 1:
                    try:
                        rules = part.ParaNumberingRules
                        if rules:
                            rules.StartAfter = start_at - 1
                            part.ParaNumberingRules = rules
                    except Exception:
                        pass
                count += 1
            except Exception:
                pass
    else:
        enum = doc.getText().createEnumeration()
        while enum.hasMoreElements():
            try:
                el = enum.nextElement()
                if not el.supportsService("com.sun.star.text.Paragraph"):
                    continue
                text = el.getString().strip()
                if not text:
                    continue
                el.ParaStyleName = style_name
                try:
                    el.NumberingLevel = level
                except Exception:
                    pass
                count += 1
            except Exception:
                pass
    return count


def transform_text(doc, mode):
    if doc is None:
        return 0
    mode = str(mode).lower()
    transforms = {
        "upper": lambda t: t.upper(),
        "lower": lambda t: t.lower(),
        "title": lambda t: t.title(),
        "sentence": lambda t: t.capitalize(),
        "capitalize": lambda t: " ".join(w.capitalize() for w in t.split()),
    }
    if mode not in transforms:
        return 0
    fn = transforms[mode]
    sel = doc.getCurrentSelection()
    if sel and sel.getCount() > 0:
        count = 0
        for i in range(sel.getCount()):
            try:
                part = sel.getByIndex(i)
                part.setString(fn(part.getString()))
                count += 1
            except Exception:
                pass
        return count
    enum = doc.getText().createEnumeration()
    count = 0
    while enum.hasMoreElements():
        try:
            el = enum.nextElement()
            if el.supportsService("com.sun.star.text.Paragraph"):
                el.setString(fn(el.getString()))
                count += 1
        except Exception:
            pass
    return count


def get_text_stats(doc, selection_text=""):
    if doc is None:
        return None
    if selection_text:
        text = selection_text
    else:
        text = get_document_text(doc)
    chars = len(text)
    chars_no_spaces = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))
    words = len(text.split())
    paragraphs = len([p for p in text.split("\n") if p.strip()])
    sentences = len([s for s in re.split(r"[.!?]+", text) if s.strip()])
    reading_time = max(1, round(words / 200))
    return {
        "chars": chars,
        "chars_no_spaces": chars_no_spaces,
        "words": words,
        "paragraphs": paragraphs,
        "sentences": sentences,
        "reading_time": reading_time,
    }


def insert_hyperlink(doc, text, url, apply_to_selection=False):
    if doc is None or not url:
        return 0
    url = str(url).strip()
    if not url:
        return 0
    if not url.startswith(("http://", "https://", "mailto:", "ftp://")):
        url = "https://" + url
    try:
        controller = doc.getCurrentController()
        cursor = controller.getViewCursor()
        if apply_to_selection:
            sel = doc.getCurrentSelection()
            if sel and sel.getCount() > 0:
                for i in range(sel.getCount()):
                    try:
                        part = sel.getByIndex(i)
                        text_content = part.getString().strip()
                        if not text_content:
                            continue
                        tf = doc.createInstance("com.sun.star.text.TextField.URL")
                        tf.URL = url
                        tf.display = text_content
                        part.setString("")
                        part.getText().insertTextCursorAtEnd(tf)
                    except Exception:
                        pass
                return 1
        if text:
            cursor.getText().insertString(cursor, text, False)
            cursor.setString("")
        tf = doc.createInstance("com.sun.star.text.TextField.URL")
        tf.URL = url
        tf.display = text or url
        cursor.getText().insertTextCursorAtEnd(tf)
        return 1
    except Exception:
        return 0


def insert_table(doc, rows, cols, headers, rows_data, style):
    if doc is None:
        return 0
    rows = max(1, min(50, int(rows)))
    cols = max(1, min(20, int(cols)))
    try:
        table = doc.createInstance("com.sun.star.text.TextTable")
        table.initialize(rows, cols)
        cursor = doc.getCurrentController().getViewCursor()
        cursor.getText().insertTextCursorAtEnd(table)
        if headers:
            for ci, header in enumerate(headers[:cols]):
                try:
                    cell = table.getCellByPosition(ci, 0)
                    cell.setString(str(header))
                except Exception:
                    pass
        if rows_data:
            for ri, row_data in enumerate(rows_data[:rows - 1]):
                for ci, val in enumerate(row_data[:cols]):
                    try:
                        cell = table.getCellByPosition(ci, ri + 1)
                        cell.setString(str(val))
                    except Exception:
                        pass
        header_bg = style.get("header_background") if isinstance(style, dict) else None
        header_bold = style.get("header_bold") if isinstance(style, dict) else False
        if header_bg or header_bold:
            for ci in range(cols):
                try:
                    cell = table.getCellByPosition(ci, 0)
                    cursor2 = cell.getText().createTextCursor()
                    if header_bold:
                        cursor2.CharWeight = 150
                    if header_bg:
                        cursor2.CharBackColor = _parse_color(header_bg)
                        cursor2.CharBackTransparent = False
                except Exception:
                    pass
        return 1
    except Exception:
        return 0


def set_header_footer(doc, header, footer, first_page_different=False):
    if doc is None:
        return 0
    try:
        controller = doc.getCurrentController()
        cursor = controller.getViewCursor()
        style_name = cursor.PageStyleName
        families = doc.getStyleFamilies()
        page_styles = families.getByName("PageStyles")
        style = page_styles.getByName(style_name)
    except Exception:
        return 0
    count = 0
    if isinstance(header, dict) and header.get("text"):
        try:
            header_text = doc.getText()
            header_cursor = header_text.createTextCursor()
            style.HeaderText = header_cursor
            if header.get("page_numbers"):
                pf = doc.createInstance("com.sun.star.text.TextField.PageNumber")
                pf.NumberingType = 4
                header_cursor.getText().insertTextCursorAtEnd(pf)
            else:
                header_cursor.getText().insertString(header_cursor, str(header["text"]), False)
            align = header.get("alignment", "").lower()
            if align == "center":
                header_cursor.ParaAdjust = 3
            elif align == "right":
                header_cursor.ParaAdjust = 1
            else:
                header_cursor.ParaAdjust = 0
            count += 1
        except Exception:
            pass
    if isinstance(footer, dict) and footer.get("text"):
        try:
            footer_text = doc.getText()
            footer_cursor = footer_text.createTextCursor()
            style.FooterText = footer_cursor
            text_content = str(footer["text"]).replace("{{date}}", "")
            if footer.get("page_numbers"):
                pf = doc.createInstance("com.sun.star.text.TextField.PageNumber")
                pf.NumberingType = 4
                footer_cursor.getText().insertTextCursorAtEnd(pf)
                if text_content:
                    footer_cursor.getText().insertString(footer_cursor, " " + text_content, False)
            else:
                footer_cursor.getText().insertString(footer_cursor, text_content, False)
            align = footer.get("alignment", "").lower()
            if align == "center":
                footer_cursor.ParaAdjust = 3
            elif align == "right":
                footer_cursor.ParaAdjust = 1
            else:
                footer_cursor.ParaAdjust = 0
            count += 1
        except Exception:
            pass
    try:
        style.FirstPageIsShared = bool(first_page_different)
    except Exception:
        pass
    return count


def insert_footnote(doc, marker_text, note_text):
    if doc is None:
        return 0
    try:
        footnote = doc.createInstance("com.sun.star.text.Footnote")
        tf = footnote.getAnchor()
        tf.setString(str(marker_text))
        cf = footnote.getText()
        cf.insertString(cf.createTextCursor(), str(note_text), False)
        cursor = doc.getCurrentController().getViewCursor()
        cursor.getText().insertTextCursorAtEnd(footnote)
        return 1
    except Exception:
        return 0


def _find_text_range(doc, marker_text):
    marker = str(marker_text or "").strip()
    if not marker:
        return None
    try:
        desc = doc.createSearchDescriptor()
        desc.SearchString = marker
        desc.SearchCaseSensitive = False
        desc.SearchRegularExpression = False
        return doc.findFirst(desc)
    except Exception:
        return None


def insert_comments(doc, comments):
    if doc is None or not comments:
        return 0
    count = 0
    try:
        sel = doc.getCurrentSelection()
    except Exception:
        sel = None
    for item in comments:
        try:
            annotation = doc.createInstance("com.sun.star.text.textfield.Annotation")
            try:
                annotation.Content = str(item.get("comment", ""))
            except Exception:
                pass
            try:
                annotation.Author = str(item.get("author", "Libre Asist"))
            except Exception:
                pass
            try:
                annotation.Initials = "AI"
            except Exception:
                pass
            target = _find_text_range(doc, item.get("marker_text", ""))
            if target is None and sel is not None and sel.getCount() > 0:
                try:
                    selected = sel.getByIndex(0)
                    if selected.getString().strip():
                        target = selected
                except Exception:
                    pass
            if target is None:
                target = doc.getCurrentController().getViewCursor()
            target.getText().insertTextContent(target, annotation, False)
            count += 1
        except Exception:
            pass
    return count


def apply_format_shortcut(doc, shortcut):
    if doc is None:
        return 0
    shortcuts = {
        "center": {"align": "center"},
        "centrar": {"align": "center"},
        "justify": {"align": "justify"},
        "justificar": {"align": "justify"},
        "left": {"align": "left"},
        "izquierda": {"align": "left"},
        "right": {"align": "right"},
        "derecha": {"align": "right"},
        "bold": {"bold": True},
        "negrita": {"bold": True},
        "negritas": {"bold": True},
        "italic": {"italic": True},
        "cursiva": {"italic": True},
        "cursivas": {"italic": True},
        "underline": {"underline": True},
        "subrayado": {"underline": True},
        "double_space": {"line_spacing": 2.0},
        "espacio_doble": {"line_spacing": 2.0},
        "space_15": {"line_spacing": 1.5},
        "espacio_1.5": {"line_spacing": 1.5},
        "single_space": {"line_spacing": 1.0},
        "espacio_simple": {"line_spacing": 1.0},
        "clear_format": {"paragraph_style": "Default Paragraph Style"},
        "quitar_formato": {"paragraph_style": "Default Paragraph Style"},
        "default_style": {"paragraph_style": "Default Paragraph Style"},
    }
    if shortcut not in shortcuts:
        return 0
    props = shortcuts[shortcut]
    sel = doc.getCurrentSelection()
    if sel and sel.getCount() > 0:
        count = 0
        for i in range(sel.getCount()):
            try:
                part = sel.getByIndex(i)
                if not part.getString().strip():
                    continue
                _apply_text_style(part, props)
                count += 1
            except Exception:
                pass
        return count
    enum = doc.getText().createEnumeration()
    count = 0
    while enum.hasMoreElements():
        try:
            el = enum.nextElement()
            if el.supportsService("com.sun.star.text.Paragraph"):
                text = el.getString().strip()
                if not text:
                    continue
                _apply_text_style(el, props)
                count += 1
        except Exception:
            pass
    return count


def export_document(doc, format, path):
    if doc is None:
        return False
    formats = {
        "pdf": ("application/pdf", "pdf"),
        "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
        "odt": ("application/vnd.oasis.opendocument.text", "odt"),
        "txt": ("text/plain", "txt"),
    }
    if format not in formats:
        return False
    media_type, ext = formats[format]
    if not path:
        return False
    try:
        from urllib.parse import urlsplit
    except Exception:
        from urlparse import urlsplit
    try:
        import sys
        if sys.version_info[0] >= 3:
            from urllib.parse import urlsplit
        else:
            from urlparse import urlsplit
    except Exception:
        pass
    try:
        o_url = urlsplit(path).geturl()
    except Exception:
        o_url = path
    try:
        filter_data = doc.createInstance("com.sun.star.document.MediaDescriptor")
        filter_data["FilterName"] = media_type
        doc.storeToURL(o_url, (filter_data,))
        return True
    except Exception:
        return False


def set_track_changes(doc, enabled):
    if doc is None:
        return False
    try:
        doc.RecordChanges = bool(enabled)
        return True
    except Exception:
        return False


def get_track_changes_status(doc):
    if doc is None:
        return None
    try:
        return bool(doc.RecordChanges)
    except Exception:
        return None


def get_redlines_summary(doc):
    if doc is None:
        return []
    redlines = []
    try:
        count = doc.getRedlineCount()
        for i in range(min(count, 50)):
            try:
                redline = doc.getRedlineByIndex(i)
                author = ""
                try:
                    author = redline.Author
                except Exception:
                    pass
                text = ""
                try:
                    text = redline.getText()
                except Exception:
                    pass
                text_short = text[:100].replace("\n", " ") if text else ""
                redlines.append({
                    "author": author,
                    "text": text_short,
                    "index": i,
                })
            except Exception:
                pass
    except Exception:
        pass
    return redlines


def accept_all_redlines(doc):
    if doc is None:
        return 0
    try:
        count = doc.getRedlineCount()
        doc.acceptAllRedlines()
        return count
    except Exception:
        return 0


def reject_all_redlines(doc):
    if doc is None:
        return 0
    try:
        count = doc.getRedlineCount()
        doc.rejectAllRedlines()
        return count
    except Exception:
        return 0


def markdown_to_blocks(markdown_text, max_blocks=80):
    if not markdown_text:
        return []
    lines = markdown_text.splitlines()
    blocks = []
    in_code_block = False
    code_lines = []
    current_block = {"text": "", "style": {}}
    in_list = False
    list_items = []

    def _flush_block():
        nonlocal current_block
        if current_block["text"].strip():
            blocks.append(current_block)
        current_block = {"text": "", "style": {}}

    def _flush_list():
        nonlocal list_items, in_list
        if list_items:
            for item_text in list_items:
                blocks.append({"text": item_text, "style": {"paragraph_style": "List Bullet"}})
            list_items = []
        in_list = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code_block:
                blocks.append({"text": "\n".join(code_lines), "style": {"paragraph_style": "Quotations"}})
                code_lines = []
                in_code_block = False
            else:
                _flush_block()
                _flush_list()
                in_code_block = True
            continue
        if in_code_block:
            code_lines.append(stripped)
            continue
        if stripped.startswith("# "):
            _flush_block()
            _flush_list()
            blocks.append({"text": stripped[2:], "style": {"paragraph_style": "Heading 1", "font_size": 18, "bold": True}})
            continue
        if stripped.startswith("## "):
            _flush_block()
            _flush_list()
            blocks.append({"text": stripped[3:], "style": {"paragraph_style": "Heading 2", "font_size": 14, "bold": True}})
            continue
        if stripped.startswith("### "):
            _flush_block()
            _flush_list()
            blocks.append({"text": stripped[4:], "style": {"paragraph_style": "Heading 3", "font_size": 12, "bold": True}})
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            list_items.append(stripped[2:])
            in_list = True
            continue
        if re.match(r"^\d+\.\s", stripped):
            list_items.append(re.sub(r"^\d+\.\s", "", stripped))
            in_list = True
            continue
        if in_list:
            _flush_list()
        if not stripped:
            _flush_block()
            continue
        processed = stripped
        processed = re.sub(r"\*\*(.+?)\*\*", r"\1", processed)
        processed = re.sub(r"__(.+?)__", r"\1", processed)
        processed = re.sub(r"\*(.+?)\*", r"\1", processed)
        processed = re.sub(r"_(.+?)_", r"\1", processed)
        processed = re.sub(r"`(.+?)`", r"\1", processed)
        processed = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", processed)
        current_block["text"] += processed
        if len(blocks) >= max_blocks:
            break
    if in_code_block and code_lines:
        blocks.append({"text": "\n".join(code_lines), "style": {"paragraph_style": "Quotations"}})
    _flush_block()
    _flush_list()
    return [b for b in blocks if b["text"].strip()]


def writer_to_markdown(doc):
    if doc is None:
        return ""
    try:
        enum = doc.getText().createEnumeration()
        lines = []
        while enum.hasMoreElements():
            el = enum.nextElement()
            if not el.supportsService("com.sun.star.text.Paragraph"):
                continue
            text = el.getString().strip()
            if not text:
                lines.append("")
                continue
            style = el.ParaStyleName or ""
            if "Heading 1" in style or style == "Title":
                lines.append("# " + text)
            elif "Heading 2" in style:
                lines.append("## " + text)
            elif "Heading 3" in style:
                lines.append("### " + text)
            elif "List" in style or "Numbering" in style:
                lines.append("- " + text)
            elif "Quotations" in style:
                lines.append("> " + text)
            else:
                lines.append(text)
        return "\n".join(lines)
    except Exception:
        return ""


def find_spelling_issues(doc, max_issues=100):
    if doc is None:
        return []
    issues = []
    try:
        ctx = uno.getComponentContext()
        smgr = ctx.getServiceManager()
        spell_svc = smgr.createInstanceWithContext("com.sun.star.linguistic2.SpellChecker", ctx)
    except Exception:
        return []
    if not spell_svc:
        return []
    try:
        enum = doc.getText().createEnumeration()
        para_index = 0
        while enum.hasMoreElements() and len(issues) < max_issues:
            para = enum.nextElement()
            if not para.supportsService("com.sun.star.text.Paragraph"):
                continue
            para_index += 1
            text = para.getString()
            if not text.strip():
                continue
            words = re.findall(r"\b[\w\xdf\xfe\xc0-\xd6\xd8-\xf6\xa0-\xff]{2,}\b", text, re.U)
            prev_end = 0
            for m in re.finditer(r"\b[\w\xdf\xfe\xc0-\xd6\xd8-\xf6\xa0-\xff]{2,}\b", text, re.U):
                word = m.group(0)
                try:
                    result = spell_svc.spell(word, 0, "")
                    if result and result.isValid():
                        continue
                except Exception:
                    pass
                start = max(0, m.start() - 30)
                end = min(len(text), m.end() + 30)
                context = text[start:end].replace("\n", " ")
                issues.append({
                    "word": word,
                    "context": context,
                    "para": para_index,
                })
    except Exception:
        pass
    return issues[:max_issues]


def apply_preview(doc, preview):
    if not preview:
        return 0
    action = preview.get("action", "")
    text = preview.get("text", "")
    blocks = preview.get("blocks", [])
    if action == "insert_text":
        if blocks:
            return 1 if _insert_blocks_at_cursor(doc, blocks, preview) else 0
        return 1 if insert_at_cursor_with_style(doc, text, preview) else 0
    if action == "replace_selection":
        if blocks:
            return 1 if _replace_selection_with_blocks(doc, blocks, preview) else 0
        return 1 if replace_selection_with_style(doc, text, preview) else 0
    if action == "replace_document":
        if blocks:
            return 1 if replace_document_with_blocks(doc, blocks, preview) else 0
        return 1 if replace_document_with_style(doc, text, preview) else 0
    if action == "replace_text":
        return replace_text(doc, preview.get("replacements", []))
    if action == "format_document":
        return format_document_structure(doc, preview)
    if action == "append_text":
        if blocks:
            return 1 if _insert_blocks_at_cursor(doc, blocks, preview, append=True) else 0
        try:
            _apply_page_style(doc, preview)
            cursor = doc.getText().createTextCursor()
            cursor.gotoEnd(False)
            _apply_text_style(cursor, preview)
            doc.getText().insertString(cursor, text, False)
            return 1
        except Exception:
            return 0
    if action == "format_selection":
        _apply_page_style(doc, preview)
        only_page_style = preview.get("page_style") and not any(
            key in preview for key in (
                "bold", "italic", "font_size", "font_name", "font_color", "background",
                "align", "line_spacing", "space_before", "space_after", "left_margin",
                "right_margin", "first_line_indent", "paragraph_style",
            )
        )
        if only_page_style:
            return 1
        sel = doc.getCurrentSelection()
        if sel is None or sel.getCount() == 0:
            return 0
        count = 0
        for i in range(sel.getCount()):
            try:
                part = sel.getByIndex(i)
                if not part.getString().strip():
                    continue
                _apply_text_style(part, preview)
                count += 1
            except Exception:
                pass
        return count
    if action == "apply_list":
        return apply_list(doc, preview)
    if action == "insert_hyperlink":
        return insert_hyperlink(
            doc,
            preview.get("text", ""),
            preview.get("url", ""),
            preview.get("apply_to_selection", False),
        )
    if action == "insert_table":
        return insert_table(
            doc,
            preview.get("rows", 3),
            preview.get("cols", 3),
            preview.get("headers", []),
            preview.get("rows_data", []),
            preview.get("style", {}),
        )
    if action == "set_header_footer":
        return set_header_footer(
            doc,
            preview.get("header", {}),
            preview.get("footer", {}),
            preview.get("first_page_different", False),
        )
    if action == "insert_footnote":
        return insert_footnote(
            doc,
            preview.get("marker_text", ""),
            preview.get("note_text", ""),
        )
    if action == "insert_comment":
        return insert_comments(doc, preview.get("comments", []))
    if action == "export_document":
        return 1 if export_document(
            doc,
            preview.get("format", "pdf"),
            preview.get("path", ""),
        ) else 0
    if action == "insert_markdown":
        blocks = markdown_to_blocks(preview.get("markdown_text", ""))
        if not blocks:
            return 0
        mode = preview.get("mode", "insert_text")
        if mode == "replace_document":
            return 1 if replace_document_with_blocks(doc, blocks, preview) else 0
        if mode == "append_text":
            return 1 if _insert_blocks_at_cursor(doc, blocks, preview, append=True) else 0
        return 1 if _insert_blocks_at_cursor(doc, blocks, preview) else 0
    if action == "track_changes":
        enabled = preview.get("enabled", True)
        return 1 if set_track_changes(doc, enabled) else 0
    if action == "accept_all_redlines":
        return accept_all_redlines(doc)
    if action == "reject_all_redlines":
        return reject_all_redlines(doc)
    return 0
