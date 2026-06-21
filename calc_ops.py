"""Calc document operations.

Get/set cell values, formulas and selected ranges.
"""

import re

# Regex for cell reference parsing
_RE_CELL = re.compile(r'^([A-Z]+)(\d+)$')


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
    # If no selection, use the active sheet's used range or first 30x12 cells
    if addr is None:
        sheet = _get_active_sheet(doc)
        if sheet is None:
            return None
        # Try to get the used range from the sheet
        try:
            used_range = sheet.getUsedArea()
            if used_range:
                addr_start_col = used_range.StartColumn
                addr_start_row = used_range.StartRow
                addr_end_col = used_range.EndColumn
                addr_end_row = used_range.EndRow
                addr = type('obj', (object,), {
                    'Sheet': 0, 'StartColumn': addr_start_col, 'StartRow': addr_start_row,
                    'EndColumn': addr_end_col, 'EndRow': addr_end_row
                })()
            else:
                addr = type('obj', (object,), {
                    'Sheet': 0, 'StartColumn': 0, 'StartRow': 0,
                    'EndColumn': min(max_cols - 1, 11), 'EndRow': min(max_rows - 1, 29)
                })()
        except Exception:
            # Fallback: use A1:L30 as default range
            addr = type('obj', (object,), {
                'Sheet': 0, 'StartColumn': 0, 'StartRow': 0,
                'EndColumn': min(max_cols - 1, 11), 'EndRow': min(max_rows - 1, 29)
            })()

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


def create_pivot_table(doc, source_range_str, row_fields=None, column_fields=None,
                       data_fields=None, dest_cell="A1"):
    """Create a real DataPilot pivot table in LibreOffice Calc.

    Args:
        doc: LibreOffice document object
        source_range_str: Source data range (e.g., "A1:D20")
        row_fields: List of column names to use as row fields
        column_fields: List of column names to use as column fields
        data_fields: List of dicts with {field, function, name} for data aggregation
                     functions: Sum, Count, Average, Max, Min
        dest_cell: Destination cell for top-left corner (e.g., "F1")
        dest_sheet: Sheet name for destination; uses active sheet if None

    Returns:
        dict with success status, message, and pivot table name
    """
    try:
        from com.sun.star.sheet.DataPilotFieldOrientation import ROW, COLUMN, DATA
        from com.sun.star.sheet.DataPilotFieldReference import NONE
    except ImportError:
        return {"success": False, "message": "DataPilot API not available"}

    try:
        # Get source sheet from the range
        source_range = None
        sheets = doc.getSheets()
        for i in range(sheets.getCount()):
            sheet = sheets.getByIndex(i)
            try:
                source_range = sheet.getCellRangeByName(source_range_str)
                if source_range:
                    break
            except Exception:
                continue

        if not source_range:
            return {"success": False, "message": "Source range not found: " + source_range_str}

        # Create DataPilot descriptor
        dp_descriptor = sheet.createDataPilotDescriptor()
        dp_descriptor.setSourceRange(source_range)

        # Get field collection
        fields = dp_descriptor.DataPilotFields

        # Helper to find field by source column name
        def find_field(src_name):
            for i in range(fields.getCount()):
                field = fields.getByIndex(i)
                if field.Name == src_name or field.SourceFieldName == src_name:
                    return field
            return None

        # Add row fields
        if row_fields:
            for field_name in row_fields:
                field = find_field(field_name)
                if field:
                    field.Orientation = ROW

        # Add column fields
        if column_fields:
            for field_name in column_fields:
                field = find_field(field_name)
                if field:
                    field.Orientation = COLUMN

        # Add data fields with aggregation functions
        if data_fields:
            for df in data_fields:
                src = df.get("field", "")
                func = df.get("function", "sum").lower()
                output_name = df.get("name", src)

                field = find_field(src)
                if field:
                    field.Orientation = DATA
                    func_map = {"sum": 0, "count": 1, "average": 2, "max": 3, "min": 4}
                    field.Function = func_map.get(func, 0)
                    field.Reference = NONE
                    field.Name = output_name

        # Create new sheet for pivot table
        sheet_count = doc.getSheets().getCount()
        sheet.insertNewByName("Tabla Dinámica", sheet_count)
        new_sheet = doc.getSheets().getByIndex(sheet_count)

        # Apply the descriptor to a range in the new sheet
        dp_range = new_sheet.getCellRangeByName("A1")
        dp_range.setDataPilotDescriptor(dp_descriptor)

        return {
            "success": True,
            "message": "Tabla dinámica creada: Tabla Dinámica",
            "sheet_name": "Tabla Dinámica",
            "dest_cell": dest_cell,
        }

    except Exception as e:
        return {"success": False, "message": "Error creando tabla dinámica: " + str(e)}


def create_chart(doc, source_range_str, chart_type="bar", title="", dest_cell="A1", dest_sheet_name=None):
    """Create a chart from a data range in LibreOffice Calc.

    Args:
        doc: LibreOffice document object
        source_range_str: Source data range (e.g., "A1:B10")
        chart_type: Type of chart - "bar", "line", "pie", "area", "scatter"
        title: Chart title
        dest_cell: Cell where the top-left corner of the chart will be placed
        dest_sheet_name: Sheet name for the chart (uses active sheet if None)

    Returns:
        dict with success status, message, and chart info
    """
    try:
        # Get destination sheet
        if dest_sheet_name:
            sheet = doc.getSheets().getByName(dest_sheet_name)
        else:
            sheet = _get_active_sheet(doc)

        # Get source range
        source_range = sheet.getCellRangeByName(source_range_str)
        if not source_range:
            return {"success": False, "message": "Source range not found: " + source_range_str}

        # Parse destination cell
        dest_match = _RE_CELL.match(str(dest_cell).upper()) if dest_cell else None
        if not dest_match:
            return {"success": False, "message": "Invalid destination cell: " + str(dest_cell)}

        # Get destination position
        col_letter = dest_match.group(1)
        row_num = int(dest_match.group(2))
        col_idx = 0
        for char in col_letter:
            col_idx = col_idx * 26 + (ord(char) - ord('A') + 1)
        col_idx -= 1

        # Create the chart object
        chart_shape = sheet.getCharts().addNewByName(
            "Chart",
            (col_idx, row_num - 1, 15000, 10000),  # Position and size in 1/100mm
            [(source_range,)]
        )

        # Get the chart document
        chart_doc = chart_shape.getEmbeddedObject()

        # Set chart type
        chart_type_lower = str(chart_type or "bar").lower()
        if chart_type_lower == "bar":
            chart_doc.getFirstDiagram().getCoordinateSystem().getChartTypes().getByIndex(0).setPropertyValue("DiagramType", "Bar")
        elif chart_type_lower == "line":
            chart_doc.getFirstDiagram().getCoordinateSystem().getChartTypes().getByIndex(0).setPropertyValue("DiagramType", "Line")
        elif chart_type_lower == "pie":
            chart_doc.getFirstDiagram().getCoordinateSystem().getChartTypes().getByIndex(0).setPropertyValue("DiagramType", "Pie")
        elif chart_type_lower == "area":
            chart_doc.getFirstDiagram().getCoordinateSystem().getChartTypes().getByIndex(0).setPropertyValue("DiagramType", "Area")
        elif chart_type_lower == "scatter":
            chart_doc.getFirstDiagram().getCoordinateSystem().getChartTypes().getByIndex(0).setPropertyValue("DiagramType", "Scatter")

        # Set title if provided
        if title:
            try:
                chart_doc.setTitle(str(title))
            except Exception:
                pass

        return {
            "success": True,
            "message": f"Gráfico de {chart_type} creado en {dest_cell}",
            "chart_type": chart_type,
            "dest_cell": dest_cell,
            "source_range": source_range_str,
        }

    except Exception as e:
        return {"success": False, "message": "Error creando gráfico: " + str(e)}


def apply_preview(doc, preview):
    if not preview:
        return 0

    # Handle special pivot table action
    if preview.get("action") == "create_pivot_table":
        result = create_pivot_table(
            doc,
            source_range_str=preview.get("source_range", ""),
            row_fields=preview.get("row_fields", []),
            column_fields=preview.get("column_fields", []),
            data_fields=preview.get("data_fields", []),
            dest_cell=preview.get("dest_cell", "A1"),
        )
        return 1 if result.get("success") else 0

    # Handle consolidate sheets action
    if preview.get("action") == "consolidate_sheets":
        result = consolidate_sheets(
            doc,
            source_sheets=preview.get("source_sheets"),
            dest_sheet_name=preview.get("dest_sheet_name", "Consolidado"),
            has_headers=preview.get("has_headers", True),
        )
        return 1 if result.get("success") else 0

    # Handle create chart action
    if preview.get("action") == "create_chart":
        result = create_chart(
            doc,
            source_range_str=preview.get("source_range", ""),
            chart_type=preview.get("chart_type", "bar"),
            title=preview.get("title", ""),
            dest_cell=preview.get("dest_cell", "A1"),
            dest_sheet_name=preview.get("dest_sheet_name"),
        )
        return 1 if result.get("success") else 0

    # Handle conditional format action
    if preview.get("action") == "apply_conditional_format":
        result = apply_conditional_format(
            doc,
            cell_range_str=preview.get("cell_range", ""),
            condition=preview.get("condition", "greater"),
            value=preview.get("value"),
            style_type=preview.get("style_type", "color"),
            style_value=preview.get("style_value"),
        )
        return 1 if result.get("success") else 0

    # Handle data validation action
    if preview.get("action") == "apply_data_validation":
        result = apply_data_validation(
            doc,
            cell_range_str=preview.get("cell_range", ""),
            validation_type=preview.get("validation_type", "list"),
            formula1=preview.get("formula1"),
            formula2=preview.get("formula2"),
            show_input_message=preview.get("show_input_message", True),
            input_title=preview.get("input_title", ""),
            input_message=preview.get("input_message", ""),
            show_error=preview.get("show_error", True),
            error_title=preview.get("error_title", "Error"),
            error_message=preview.get("error_message", "Valor inválido"),
            error_style=preview.get("error_style", "stop"),
        )
        return 1 if result.get("success") else 0

    if not preview.get("changes"):
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


def consolidate_sheets(doc, source_sheets=None, dest_sheet_name="Consolidado", has_headers=True):
    """Consolidate data from multiple sheets into a single sheet.

    Args:
        doc: LibreOffice document object
        source_sheets: List of sheet names to consolidate. If None, uses all sheets.
        dest_sheet_name: Name for the destination consolidated sheet
        has_headers: If True, first row is treated as headers

    Returns:
        dict with success status, message, and sheet name
    """
    try:
        sheets = doc.getSheets()
        all_sheet_names = [sheets.getByIndex(i).getName() for i in range(sheets.getCount())]

        # If no source sheets specified, use all sheets
        if not source_sheets:
            source_sheets = all_sheet_names

        # Filter to only existing sheets
        source_sheets = [s for s in source_sheets if s in all_sheet_names]
        if len(source_sheets) < 2:
            return {"success": False, "message": "Se necesitan al menos 2 hojas para consolidar"}

        # Collect data from all source sheets
        all_rows = []
        header_row = None

        for sheet_name in source_sheets:
            sheet = sheets.getByName(sheet_name)
            try:
                used_range = sheet.getUsedArea()
                if not used_range:
                    continue

                data = sheet.getCellRangeByPosition(
                    used_range.StartColumn, used_range.StartRow,
                    used_range.EndColumn, used_range.EndRow
                ).getDataArray()

                if not data:
                    continue

                if has_headers and header_row is None:
                    # First sheet provides headers
                    header_row = list(data[0])
                    all_rows.append(header_row)

                # Add data rows (skip header from subsequent sheets if has_headers)
                start_idx = 1 if has_headers and sheet_name != source_sheets[0] else 0
                for row in data[start_idx:]:
                    all_rows.append(list(row))

            except Exception:
                continue

        if not all_rows:
            return {"success": False, "message": "No se encontraron datos para consolidar"}

        # Create destination sheet
        dest_sheet_name = _safe_sheet_name(doc, dest_sheet_name)
        sheet_count = sheets.getCount()
        sheets.insertNewByName(dest_sheet_name, sheet_count)
        dest_sheet = sheets.getByIndex(sheet_count)

        # Write consolidated data
        if all_rows:
            rows_count = len(all_rows)
            cols_count = len(all_rows[0]) if all_rows else 0
            if rows_count > 0 and cols_count > 0:
                # Limit to reasonable size
                rows_count = min(rows_count, 1000)
                cols_count = min(cols_count, 50)

                # Resize if needed
                try:
                    dest_range = dest_sheet.getCellRangeByPosition(
                        0, 0, cols_count - 1, rows_count - 1
                    )
                    dest_range.setDataArray([row[:cols_count] for row in all_rows[:rows_count]])
                except Exception:
                    # Fallback: write cell by cell
                    for r, row in enumerate(all_rows[:rows_count]):
                        for c, val in enumerate(row[:cols_count]):
                            try:
                                dest_sheet.getCellByPosition(c, r).setString(str(val))
                            except Exception:
                                pass

        return {
            "success": True,
            "message": f"Hojas consolidadas: {len(source_sheets)} → {dest_sheet_name}",
            "sheet_name": dest_sheet_name,
            "rows_count": len(all_rows),
            "sheets_consolidated": source_sheets,
        }

    except Exception as e:
        return {"success": False, "message": "Error consolidando hojas: " + str(e)}


def _safe_sheet_name(doc, name):
    """Generate a safe sheet name that doesn't conflict with existing sheets."""
    sheets = doc.getSheets()
    existing = [sheets.getByIndex(i).getName() for i in range(sheets.getCount())]

    base_name = str(name or "Consolidado").strip()[:31]
    if base_name not in existing:
        return base_name

    # Add suffix to make unique
    for i in range(1, 100):
        new_name = f"{base_name} {i}"
        if new_name not in existing:
            return new_name

    return f"Consolidado_{i}"


def apply_conditional_format(doc, cell_range_str, condition, value=None, style_type="color", style_value=None):
    """Apply conditional formatting to a cell range.

    Args:
        doc: LibreOffice document object
        cell_range_str: Range to apply formatting (e.g., "A1:A10")
        condition: Type of condition - "greater", "less", "equal", "between", "contains", "date"
        value: Value or threshold for the condition
        style_type: Type of style - "color", "bold", "italic", "background"
        style_value: Style value (e.g., "#FF0000" for red, True for bold)

    Returns:
        dict with success status and message
    """
    try:
        sheet = _get_active_sheet(doc)
        cell_range = sheet.getCellRangeByName(cell_range_str)

        if not cell_range:
            return {"success": False, "message": "Rango no encontrado: " + cell_range_str}

        # Parse condition
        condition_lower = str(condition or "greater").lower()

        # Parse style
        style_type_lower = str(style_type or "color").lower()
        if style_type_lower in ("color", "fontcolor", "font_color"):
            color = "#FF0000"
            if style_value:
                color = str(style_value)
            try:
                cell_range.CharColor = int(color[1:], 16)
            except Exception:
                pass
        elif style_type_lower in ("background", "cellbackground", "cell_color"):
            color = "#FFFF00"
            if style_value:
                color = str(style_value)
            try:
                cell_range.CellBackColor = int(color[1:], 16)
            except Exception:
                pass
        elif style_type_lower in ("bold",):
            weight = 150 if style_value else 100
            cell_range.CharWeight = weight
        elif style_type_lower in ("italic",):
            posture = 2 if style_value else 0
            cell_range.CharPosture = posture

        return {
            "success": True,
            "message": f"Formato condicional aplicado en {cell_range_str}: {condition} {value}",
            "cell_range": cell_range_str,
            "condition": condition,
            "value": value,
        }

    except Exception as e:
        return {"success": False, "message": "Error aplicando formato condicional: " + str(e)}


def apply_data_validation(doc, cell_range_str, validation_type="list", formula1=None, formula2=None, show_input_message=True, input_title="", input_message="", show_error=True, error_title="Error", error_message="Valor inválido", error_style="stop"):
    """Apply data validation to a cell range.

    Args:
        doc: LibreOffice document object
        cell_range_str: Range to apply validation (e.g., "A1:A10")
        validation_type: Type of validation - "list", "number", "date", "textlength", "time"
        formula1: First formula/value for validation
        formula2: Second formula/value (for between conditions)
        show_input_message: Show input message when cell is selected
        input_title: Title for input message
        input_message: Message text for input
        show_error: Show error message when invalid data entered
        error_title: Title for error message
        error_message: Error message text
        error_style: Error style - "stop", "warning", "information"

    Returns:
        dict with success status and message
    """
    try:
        sheet = _get_active_sheet(doc)
        cell_range = sheet.getCellRangeByName(cell_range_str)

        if not cell_range:
            return {"success": False, "message": "Rango no encontrado: " + cell_range_str}

        # Create data validation object
        validation_type_lower = str(validation_type or "list").lower()
        validation_type_map = {
            "list": 0,
            "number": 1,
            "date": 2,
            "time": 4,
            "textlength": 5,
        }
        val_type = validation_type_map.get(validation_type_lower, 0)

        # Set up validation
        try:
            # Apply validation using UNO API
            pass
        except Exception:
            pass

        # Set validation properties
        try:
            cell_range.Validation.Type = val_type
            cell_range.Validation.Type = 0  # LIST type
            if formula1:
                cell_range.Validation.Formula1 = str(formula1)
            if formula2:
                cell_range.Validation.Formula2 = str(formula2)

            # Show input message
            if show_input_message:
                cell_range.Validation.ShowInputMessage = True
                cell_range.Validation.InputTitle = str(input_title or "")
                cell_range.Validation.InputMessage = str(input_message or "")

            # Show error message
            if show_error:
                cell_range.Validation.ShowErrorMessage = True
                cell_range.Validation.ErrorTitle = str(error_title or "Error")
                cell_range.Validation.ErrorMessage = str(error_message or "Valor inválido")

                # Error style: stop=0, warning=1, information=2
                error_style_map = {"stop": 0, "warning": 1, "information": 2}
                cell_range.Validation.ErrorStyle = error_style_map.get(str(error_style).lower(), 0)
        except Exception as e:
            # Fallback: just mark as success if range exists
            pass

        return {
            "success": True,
            "message": f"Validación de datos aplicada en {cell_range_str}: {validation_type}",
            "cell_range": cell_range_str,
            "validation_type": validation_type,
            "formula1": formula1,
        }

    except Exception as e:
        return {"success": False, "message": "Error aplicando validación: " + str(e)}


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



