"""Calc document operations.

Get/set cell values, formulas and selected ranges.
"""

import re


def _col_name(index):
    name = ""
    n = index + 1
    while n:
        n, rem = divmod(n - 1, 26)
        name = chr(65 + rem) + name
    return name


def _cell_name(col, row):
    return _col_name(col) + str(row + 1)


def _generated_cells_from(start_col, start_row, max_rows=30, max_cols=12):
    cells = []
    for r in range(max_rows):
        for c in range(max_cols):
            cells.append(_cell_name(start_col + c, start_row + r))
    return cells


def _value_kind(value, formula=""):
    if formula:
        return "formula"
    if value == "" or value is None:
        return "blank"
    if isinstance(value, (int, float)):
        return "number"
    text = str(value).strip()
    if not text:
        return "blank"
    try:
        float(text.replace(",", "."))
        return "number_text"
    except Exception:
        pass
    if "/" in text or "-" in text:
        pieces = text.replace("-", "/").split("/")
        if len(pieces) in (2, 3) and all(p.strip().isdigit() for p in pieces):
            return "date_text"
    return "text"


def _to_number(value):
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except Exception:
        return None


def _dominant_type(kinds):
    counts = {}
    for kind in kinds:
        counts[kind] = counts.get(kind, 0) + 1
    if not counts:
        return "blank"
    return sorted(counts.items(), key=lambda item: item[1], reverse=True)[0][0]


def _header_intent(header, dominant_type=""):
    text = str(header or "").strip().lower()
    if any(word in text for word in ("fecha", "date", "emision", "emisión", "vencimiento", "pago", "acredit")) or dominant_type == "date_text":
        return "date"
    if any(word in text for word in ("descripcion", "descripción", "detalle", "concepto", "movimiento", "referencia", "glosa")):
        return "description"
    if any(word in text for word in ("importe", "monto", "total", "saldo", "debe", "haber", "debito", "débito", "credito", "crédito", "amount")) or dominant_type in ("number", "number_text"):
        return "amount"
    if any(word in text for word in ("estado", "status", "conciliado", "observacion", "observación", "marca")):
        return "status"
    if any(word in text for word in ("cliente", "proveedor", "categoria", "categoría", "cuenta", "rubro", "tipo")):
        return "dimension"
    if any(word in text for word in ("factura", "comprobante", "recibo", "numero", "número", "id", "codigo", "código", "cuit", "dni")):
        return "key"
    return ""


def _get_active_sheet(doc):
    controller = doc.getCurrentController()
    return controller.getActiveSheet()


def _get_or_create_sheet(doc, name):
    sheets = doc.getSheets()
    safe_name = str(name or "").strip()[:31] or "Resumen IA"
    try:
        return sheets.getByName(safe_name)
    except Exception:
        pass
    base_name = safe_name
    idx = 1
    while True:
        try:
            sheets.insertNewByName(safe_name, sheets.getCount())
            return sheets.getByName(safe_name)
        except Exception:
            idx += 1
            suffix = " " + str(idx)
            safe_name = (base_name[:31 - len(suffix)] + suffix)[:31]


def _get_selection_address(doc):
    controller = doc.getCurrentController()
    sel = controller.getSelection()
    if sel is None:
        return None
    try:
        if sel.supportsService("com.sun.star.sheet.SheetCell"):
            return sel.getCellAddress()
    except Exception:
        pass
    try:
        return sel.getRangeAddress()
    except Exception:
        pass
    try:
        if sel.getCount() == 0:
            return None
        return sel.getByIndex(0).getRangeAddress()
    except Exception:
        try:
            return sel.getByIndex(0).getCellAddress()
        except Exception:
            return None


def _normalize_range_address(addr):
    if addr is None:
        return None
    if hasattr(addr, "StartColumn"):
        return addr
    class RangeAddress:
        pass
    out = RangeAddress()
    out.Sheet = addr.Sheet
    out.StartColumn = addr.Column
    out.EndColumn = addr.Column
    out.StartRow = addr.Row
    out.EndRow = addr.Row
    return out


def get_selected_values(doc, as_formula=False):
    addr = _normalize_range_address(_get_selection_address(doc))
    if addr is None:
        return None
    sheet = doc.getSheets().getByIndex(addr.Sheet)
    cell_range = sheet.getCellRangeByPosition(addr.StartColumn, addr.StartRow, addr.EndColumn, addr.EndRow)
    data = cell_range.getDataArray()
    formulas = cell_range.getFormulaArray()
    result = []
    for r, row in enumerate(data):
        out_row = []
        for c, val in enumerate(row):
            if as_formula:
                out_row.append(formulas[r][c] if formulas[r][c] else val)
            else:
                out_row.append(val)
        result.append(out_row)
    return result


def get_active_cell_value(doc, as_formula=False):
    controller = doc.getCurrentController()
    sheet = controller.getActiveSheet()
    sel = controller.getSelection()
    try:
        if sel.supportsService("com.sun.star.sheet.SheetCell"):
            cell = sel
        else:
            addr = sel.getRangeAddress()
            cell = sheet.getCellByPosition(addr.StartColumn, addr.StartRow)
    except Exception:
        try:
            addr = sel.getByIndex(0).getRangeAddress()
            cell = sheet.getCellByPosition(addr.StartColumn, addr.StartRow)
        except Exception:
            return None, None, None
    if as_formula:
        return cell.getFormula(), cell, sheet
    return cell.getValue(), cell, sheet


def set_cell(cell, value, as_formula=False):
    if as_formula:
        cell.setFormula(str(value))
    else:
        try:
            f = float(value)
            cell.setValue(f)
            return
        except (TypeError, ValueError):
            pass
        cell.setString(str(value))


def set_selected_values(doc, values):
    addr = _normalize_range_address(_get_selection_address(doc))
    if addr is None or values is None:
        return False
    sheet = doc.getSheets().getByIndex(addr.Sheet)
    n_rows = len(values)
    n_cols = max((len(r) for r in values), default=0)
    if n_rows == 0 or n_cols == 0:
        return False
    flat = []
    for row in values:
        for v in row:
            flat.append(v)
    cell_range = sheet.getCellRangeByPosition(
        addr.StartColumn, addr.StartRow,
        addr.StartColumn + n_cols - 1, addr.StartRow + n_rows - 1,
    )
    cell_range.setDataArray([flat[r * n_cols:(r + 1) * n_cols] for r in range(n_rows)])
    return True


def set_active_cell(doc, value, as_formula=False):
    val, cell, sheet = get_active_cell_value(doc, as_formula=False)
    if cell is None:
        return False
    set_cell(cell, value, as_formula=as_formula)
    return True


def get_selection_context(doc, max_rows=30, max_cols=12):
    addr = _normalize_range_address(_get_selection_address(doc))
    if addr is None:
        return None
    sheet = doc.getSheets().getByIndex(addr.Sheet)
    rows_total = addr.EndRow - addr.StartRow + 1
    cols_total = addr.EndColumn - addr.StartColumn + 1
    rows = min(rows_total, max_rows)
    cols = min(cols_total, max_cols)
    rng = sheet.getCellRangeByPosition(
        addr.StartColumn, addr.StartRow,
        addr.StartColumn + cols - 1, addr.StartRow + rows - 1,
    )
    data = rng.getDataArray()
    formulas = rng.getFormulaArray()
    cells = []
    allowed = []
    type_counts = {"number": 0, "text": 0, "formula": 0, "blank": 0}
    column_kinds = [[] for _ in range(cols)]
    blank_cells = []
    formula_cells = []
    for r in range(rows):
        row = []
        for c in range(cols):
            cell = _cell_name(addr.StartColumn + c, addr.StartRow + r)
            allowed.append(cell)
            value = data[r][c]
            formula = formulas[r][c]
            kind = _value_kind(value, formula)
            column_kinds[c].append(kind)
            if kind == "formula":
                type_counts["formula"] += 1
                formula_cells.append({"cell": cell, "formula": formula})
            elif kind == "blank":
                type_counts["blank"] += 1
                blank_cells.append(cell)
            elif kind in ("number", "number_text"):
                type_counts["number"] += 1
            else:
                type_counts["text"] += 1
            row.append({
                "cell": cell,
                "value": value,
                "formula": formula,
                "kind": kind,
            })
        cells.append(row)
    start = _cell_name(addr.StartColumn, addr.StartRow)
    end = _cell_name(addr.EndColumn, addr.EndRow)
    headers = []
    header_confidence = "none"
    if rows > 1:
        headers = [str(c.get("value", "") or c.get("formula", "")) for c in cells[0]]
        first_row_nonblank = sum(1 for h in headers if h.strip())
        below_types = []
        for c in range(cols):
            below_types.extend(column_kinds[c][1:])
        if first_row_nonblank >= max(1, int(cols * 0.6)) and any(t in ("number", "formula", "number_text", "date_text") for t in below_types):
            header_confidence = "high"
        elif first_row_nonblank:
            header_confidence = "medium"
    data_start = 1 if header_confidence in ("high", "medium") and rows > 1 else 0
    column_profiles = []
    for c in range(cols):
        header = headers[c] if c < len(headers) else ""
        kinds = column_kinds[c][1:] if header_confidence in ("high", "medium") and rows > 1 else column_kinds[c]
        values = []
        numbers = []
        formulas_in_col = []
        nonblank_count = 0
        formula_pattern_counts = {}
        for r in range(data_start, rows):
            item = cells[r][c]
            raw_value = item.get("formula") or item.get("value")
            text_value = str(raw_value or "").strip()
            if text_value:
                nonblank_count += 1
                values.append(text_value)
            number = _to_number(item.get("value"))
            if number is not None:
                numbers.append(number)
            if item.get("formula"):
                formula_text = str(item.get("formula"))
                formulas_in_col.append({"cell": item["cell"], "formula": formula_text})
                normalized = re.sub(r"\d+", "#", formula_text.upper())
                formula_pattern_counts[normalized] = formula_pattern_counts.get(normalized, 0) + 1
        unique_count = len(set(v.lower() for v in values))
        duplicate_count = max(0, len(values) - unique_count)
        dominant = _dominant_type(kinds)
        numeric_summary = {}
        if numbers:
            total = sum(numbers)
            numeric_summary = {
                "min": min(numbers),
                "max": max(numbers),
                "sum": total,
                "average": total / len(numbers),
                "negative_count": sum(1 for n in numbers if n < 0),
                "zero_count": sum(1 for n in numbers if abs(n) < 0.00001),
            }
        formula_patterns = []
        for pattern, count in sorted(formula_pattern_counts.items(), key=lambda item: item[1], reverse=True)[:5]:
            formula_patterns.append({"pattern": pattern, "count": count})
        column_profiles.append({
            "column": _col_name(addr.StartColumn + c),
            "header": header,
            "intent": _header_intent(header, dominant),
            "dominant_type": dominant,
            "nonblank_count": nonblank_count,
            "blank_count": sum(1 for k in kinds if k == "blank"),
            "formula_count": sum(1 for k in kinds if k == "formula"),
            "unique_count": unique_count,
            "duplicate_count": duplicate_count,
            "numeric_summary": numeric_summary,
            "formula_patterns": formula_patterns,
            "sample_values": values[:5],
        })
    duplicate_rows = []
    row_seen = {}
    for r in range(data_start, rows):
        values = []
        for c in range(cols):
            item = cells[r][c]
            values.append(str(item.get("formula") or item.get("value") or "").strip().lower())
        key = tuple(values)
        if any(key) and key in row_seen:
            duplicate_rows.append({
                "first_row": addr.StartRow + row_seen[key] + 1,
                "duplicate_row": addr.StartRow + r + 1,
            })
        elif any(key):
            row_seen[key] = r
    duplicate_values = []
    for c in range(cols):
        seen = {}
        header = headers[c] if c < len(headers) else _col_name(addr.StartColumn + c)
        for r in range(data_start, rows):
            item = cells[r][c]
            value = str(item.get("formula") or item.get("value") or "").strip()
            key = value.lower()
            if not key:
                continue
            if key in seen:
                duplicate_values.append({
                    "column": _col_name(addr.StartColumn + c),
                    "header": header,
                    "value": value,
                    "first_cell": _cell_name(addr.StartColumn + c, addr.StartRow + seen[key]),
                    "duplicate_cell": _cell_name(addr.StartColumn + c, addr.StartRow + r),
                })
            else:
                seen[key] = r
    bank_columns = {"date": [], "description": [], "amount": [], "status": []}
    for profile in column_profiles:
        header_text = str(profile.get("header", "")).lower()
        col_name = profile.get("column", "")
        intent = profile.get("intent", "")
        if intent == "date":
            bank_columns["date"].append(col_name)
        if intent == "description" or any(word in header_text for word in ("comprobante", "referencia")):
            bank_columns["description"].append(col_name)
        if intent == "amount":
            bank_columns["amount"].append(col_name)
        if intent == "status":
            bank_columns["status"].append(col_name)
    amount_matches = []
    amounts = {}
    amount_records = {}
    for r in range(data_start, rows):
        for c in range(cols):
            number = _to_number(cells[r][c].get("value"))
            if number is None or abs(number) < 0.00001:
                continue
            key = round(abs(number), 2)
            cell_name = cells[r][c]["cell"]
            row_number = addr.StartRow + r + 1
            record = {
                "cell": cell_name,
                "row": row_number,
                "amount": number,
                "absolute_amount": key,
            }
            if key in amounts:
                amount_matches.append({
                    "amount": key,
                    "first_cell": amounts[key],
                    "match_cell": cell_name,
                })
                amount_records.setdefault(key, []).append(record)
            else:
                amounts[key] = cell_name
                amount_records.setdefault(key, []).append(record)
    suggested_pairs = []
    for key, records in amount_records.items():
        if len(records) < 2:
            continue
        positives = [item for item in records if item["amount"] > 0]
        negatives = [item for item in records if item["amount"] < 0]
        if positives and negatives:
            for pos in positives[:3]:
                for neg in negatives[:3]:
                    suggested_pairs.append({
                        "amount": key,
                        "debit_or_credit_cell": pos["cell"],
                        "counterpart_cell": neg["cell"],
                        "confidence": "high",
                        "reason": "mismo importe absoluto con signo opuesto",
                    })
                    if len(suggested_pairs) >= 50:
                        break
                if len(suggested_pairs) >= 50:
                    break
        else:
            suggested_pairs.append({
                "amount": key,
                "cells": [item["cell"] for item in records[:6]],
                "confidence": "medium",
                "reason": "importe repetido",
            })
        if len(suggested_pairs) >= 50:
            break
    formula_suspects = []
    for c, profile in enumerate(column_profiles):
        patterns = profile.get("formula_patterns", [])
        if len(patterns) <= 1:
            continue
        dominant_pattern = patterns[0].get("pattern", "")
        for r in range(data_start, rows):
            item = cells[r][c]
            formula = str(item.get("formula") or "")
            if not formula:
                continue
            normalized = re.sub(r"\d+", "#", formula.upper())
            if normalized != dominant_pattern:
                formula_suspects.append({
                    "cell": item["cell"],
                    "formula": formula,
                    "expected_pattern": dominant_pattern,
                    "actual_pattern": normalized,
                    "reason": "formula distinta al patron dominante de la columna",
                })
                if len(formula_suspects) >= 80:
                    break
        if len(formula_suspects) >= 80:
            break
    visible_formula_errors = []
    for r in range(data_start, rows):
        for c in range(cols):
            item = cells[r][c]
            text = str(item.get("value") or item.get("formula") or "").upper()
            if any(err in text for err in ("#VALOR", "#VALUE", "#REF", "#DIV/0", "#N/A", "#NAME", "#¿NOMBRE?")):
                visible_formula_errors.append({
                    "cell": item["cell"],
                    "value": item.get("value"),
                    "formula": item.get("formula"),
                })
                if len(visible_formula_errors) >= 50:
                    break
        if len(visible_formula_errors) >= 50:
            break
    audit_findings = []
    for profile in column_profiles:
        col = profile.get("column", "")
        header = profile.get("header") or col
        if profile.get("blank_count", 0) and profile.get("nonblank_count", 0):
            audit_findings.append({"severity": "medium", "type": "blank_cells", "column": col, "header": header, "count": profile.get("blank_count")})
        if profile.get("dominant_type") == "number_text":
            audit_findings.append({"severity": "medium", "type": "numbers_as_text", "column": col, "header": header})
        if profile.get("dominant_type") == "date_text":
            audit_findings.append({"severity": "low", "type": "dates_as_text", "column": col, "header": header})
        if profile.get("duplicate_count", 0):
            audit_findings.append({"severity": "medium", "type": "duplicate_values", "column": col, "header": header, "count": profile.get("duplicate_count")})
        if len(profile.get("formula_patterns", [])) > 1:
            audit_findings.append({"severity": "high", "type": "mixed_formula_patterns", "column": col, "header": header, "patterns": profile.get("formula_patterns")})
        numeric = profile.get("numeric_summary") or {}
        if numeric.get("negative_count") and profile.get("intent") == "amount":
            audit_findings.append({"severity": "low", "type": "negative_amounts", "column": col, "header": header, "count": numeric.get("negative_count")})
    if duplicate_rows:
        audit_findings.append({"severity": "high", "type": "duplicate_rows", "count": len(duplicate_rows)})

    dimension_columns = [p["column"] for p in column_profiles if p.get("intent") in ("dimension", "date", "status", "key") or p.get("dominant_type") in ("text", "date_text")]
    metric_columns = [p["column"] for p in column_profiles if p.get("intent") == "amount" or p.get("dominant_type") in ("number", "number_text", "formula")]

    return {
        "sheet": sheet.getName(),
        "range": start if start == end else start + ":" + end,
        "truncated": rows < rows_total or cols < cols_total,
        "rows_total": rows_total,
        "cols_total": cols_total,
        "rows_included": rows,
        "cols_included": cols,
        "headers": headers,
        "header_confidence": header_confidence,
        "first_data_cell": _cell_name(addr.StartColumn, addr.StartRow + (1 if header_confidence in ("high", "medium") and rows > 1 else 0)),
        "type_counts": type_counts,
        "column_profiles": column_profiles,
        "profile_summary": {
            "likely_dimension_columns": dimension_columns[:10],
            "likely_metric_columns": metric_columns[:10],
            "quality_findings": audit_findings[:80],
        },
        "blank_cells": blank_cells[:50],
        "formula_cells": formula_cells[:50],
        "formula_audit": {
            "suspect_cells": formula_suspects[:80],
            "visible_errors": visible_formula_errors[:50],
        },
        "cells": cells,
        "allowed_cells": allowed,
        "generated_allowed_cells": _generated_cells_from(addr.StartColumn, addr.StartRow, max_rows=max_rows, max_cols=max_cols),
        "summary_allowed_cells": _generated_cells_from(0, 0, max_rows=40, max_cols=12),
        "audit_report_allowed_cells": _generated_cells_from(0, 0, max_rows=80, max_cols=8),
        "duplicate_rows": duplicate_rows[:50],
        "duplicate_values": duplicate_values[:80],
        "bank_reconciliation": {
            "candidate_columns": bank_columns,
            "amount_matches": amount_matches[:80],
            "suggested_pairs": suggested_pairs[:50],
        },
    }


def apply_preview(doc, preview):
    if not preview or not preview.get("changes"):
        return 0
    sheet = _get_or_create_sheet(doc, preview.get("target_sheet")) if preview.get("target_sheet") else _get_active_sheet(doc)
    count = 0
    for change in preview["changes"]:
        cell = sheet.getCellRangeByName(change["cell"])
        if "value" in change:
            set_cell(cell, change.get("value", ""), as_formula=change.get("formula", False))
        if "bold" in change:
            cell.CharWeight = 150 if change.get("bold") else 100
        if "italic" in change:
            cell.CharPosture = 2 if change.get("italic") else 0
        if "background" in change:
            cell.CellBackColor = _parse_color(change.get("background"))
        if "font_color" in change:
            cell.CharColor = _parse_color(change.get("font_color"))
        if "width" in change:
            try:
                col = cell.getCellAddress().Column
                sheet.getColumns().getByIndex(col).Width = int(change.get("width"))
            except Exception:
                pass
        if change.get("border"):
            _apply_simple_border(cell)
        count += 1
    return count


def make_undo_snapshot(doc, preview):
    if not preview or not preview.get("changes"):
        return None
    sheet = _get_or_create_sheet(doc, preview.get("target_sheet")) if preview.get("target_sheet") else _get_active_sheet(doc)
    cells = []
    seen = set()
    for change in preview.get("changes", []):
        name = str(change.get("cell", "")).replace("$", "").upper()
        if not name or name in seen:
            continue
        seen.add(name)
        try:
            cell = sheet.getCellRangeByName(name)
            snap = {
                "cell": name,
                "formula": cell.getFormula(),
                "string": cell.getString(),
                "value": cell.getValue(),
                "type": str(cell.getType()),
                "bold": cell.CharWeight,
                "italic": cell.CharPosture,
                "background": cell.CellBackColor,
                "font_color": cell.CharColor,
            }
            try:
                col = cell.getCellAddress().Column
                snap["width"] = sheet.getColumns().getByIndex(col).Width
            except Exception:
                pass
            cells.append(snap)
        except Exception:
            pass
    if not cells:
        return None
    return {"kind": "calc", "sheet": sheet.getName(), "cells": cells}


def restore_snapshot(doc, snapshot):
    if not snapshot or snapshot.get("kind") != "calc":
        return 0
    try:
        sheet = doc.getSheets().getByName(snapshot.get("sheet"))
    except Exception:
        sheet = _get_active_sheet(doc)
    count = 0
    for snap in snapshot.get("cells", []):
        try:
            cell = sheet.getCellRangeByName(snap["cell"])
            formula = snap.get("formula", "")
            if formula:
                cell.setFormula(formula)
            else:
                cell.setString(snap.get("string", ""))
                if str(snap.get("type", "")).endswith("VALUE"):
                    try:
                        cell.setValue(float(snap.get("value", 0)))
                    except Exception:
                        pass
            if "bold" in snap:
                cell.CharWeight = snap["bold"]
            if "italic" in snap:
                cell.CharPosture = snap["italic"]
            if "background" in snap:
                cell.CellBackColor = snap["background"]
            if "font_color" in snap:
                cell.CharColor = snap["font_color"]
            if "width" in snap:
                try:
                    col = cell.getCellAddress().Column
                    sheet.getColumns().getByIndex(col).Width = int(snap["width"])
                except Exception:
                    pass
            count += 1
        except Exception:
            pass
    return count


def _parse_color(value):
    text = str(value).strip()
    if text.startswith("#") and len(text) == 7:
        return int(text[1:], 16)
    try:
        return int(text)
    except Exception:
        return -1


def _apply_simple_border(cell):
    try:
        from com.sun.star.table import BorderLine2
        line = BorderLine2()
        line.LineWidth = 18
        cell.TopBorder = line
        cell.BottomBorder = line
        cell.LeftBorder = line
        cell.RightBorder = line
    except Exception:
        pass
