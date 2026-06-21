"""Calc prompt skills for Libre Asist."""

from skills_common import *


def calc_formula(user_prompt, ctx):
    return _block(
        "You are a LibreOffice Calc formula expert.",
        "Create a LibreOffice Calc-compatible formula to solve the request.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Formula must start with =.\n- Use references from the context.\n- If there is an active cell or selection, propose writing there unless the request specifies another cell.",
        "Briefly explain the formula. Then return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
        'Request: "sum column B"\n```json\n{"changes":[{"cell":"C2","value":"=SUMA(B2:B20)","formula":true}],"summary":"Insert sum of B2:B20 in C2"}\n```',
    )


def calc_analyze(ctx):
    return _block(
        "You are a data analyst for LibreOffice Calc.",
        "Analyze the selection and produce useful insights.",
        ctx,
        COMMON_RULES + "\n- Do not propose JSON or actionable changes.\n- Mention patterns, gaps, outliers, important columns, and next steps.",
        "Return natural text with brief sections: Summary, Findings, Risks, Next Steps.",
    )


def calc_table_detect(ctx):
    return _block(
        "You are a table structure auditor for LibreOffice Calc.",
        "Detect table structure, likely headers, column types, empty cells, formulas, and quality issues.",
        ctx,
        COMMON_RULES + "\n- Do not return JSON.\n- Do not propose actionable changes.\n- Use header_confidence, column_profiles, blank_cells, and formula_cells if they exist.",
        "Return natural text with sections: Structure, Headers, Types, Problems, Recommendations.",
    )


def calc_formula_debug(user_prompt, ctx):
    return _block(
        "You are an expert LibreOffice Calc formula debugger.",
        "Explain formula errors and propose a safe applicable fix if available.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Look for formulas in formula_cells and cells.\n- If there are errors like #VALUE, #REF, #DIV/0, #N/A, explain the likely cause.\n- Only propose changes in cells within allowed_cells.",
        "First explain the problem. Then, if a safe fix exists, return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
        'Broken formula in A2\n```json\n{"changes":[{"cell":"A2","value":"=SI.ERROR(B2/C2;0)","formula":true}],"summary":"Fixes division by zero error in A2"}\n```',
    )


def calc_formula_fill(user_prompt, ctx):
    return _block(
        "You are an expert in bulk formulas for LibreOffice Calc.",
        "Create a formula and fill it down or across the selected range.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Generate an explicit list of changes per cell.\n- Do not use ranges outside allowed_cells.\n- Adjust relative references by row as needed.",
        "Briefly explain and return a single JSON in ```json with many changes if needed:\n" + CALC_ACTION_SCHEMA,
        'Request: "calculate total in C for each row"\n```json\n{"changes":[{"cell":"C2","value":"=A2*B2","formula":true},{"cell":"C3","value":"=A3*B3","formula":true}],"summary":"Fill total formulas down"}\n```',
    )


def calc_random_fill(user_prompt, ctx):
    return _block(
        "You are an expert in realistic random data generation for LibreOffice Calc.",
        "Fill cells (empty or all) within the allowed range with realistic random data compatible with Calc.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + (
            "\n- Detect the likely type of each column by reading headers and column_profiles. "
            "Common categories: name, email, city, country, date, amount, quantity, percentage, id, status, boolean."
            "\n- For numeric columns use formulas like =ALEATORIO.ENTRE(min;max) or "
            "=REDONDEAR(ALEATORIO()*(max-min)+min;decimals) or =ALEATORIO() for 0-1."
            "\n- For text columns (names, cities, states, categories) use formulas like "
            "=ELEGIR(ALEATORIO.ENTRE(1;N);\"opt1\";\"opt2\";\"opt3\";...) with a pool of at least 4-8 varied realistic values. For emails use =CONCATENAR(\"user\";ALEATORIO.ENTRE(100;999);\"@example.com\")."
            "\n- For dates use =FECHA(year;ALEATORIO.ENTRE(month_min;month_max);ALEATORIO.ENTRE(1;28)) "
            "or =FECHA(2024;ALEATORIO.ENTRE(1;12);ALEATORIO.ENTRE(1;28))."
            "\n- For ids or codes use =TEXTO(ALEATORIO.ENTRE(1000;9999);\"0000\") or =CONCATENAR(\"P-\";TEXTO(ALEATORIO.ENTRE(1;9999);\"0000\"))."
            "\n- For short states or categories use =ELEGIR(ALEATORIO.ENTRE(1;3);\"Active\";\"Pending\";\"Closed\")."
            "\n- ALWAYS use formulas that start with = (formula:true) so values change on recalculation."
            "\n- If allowed_cells is empty or the selection is minimal, you may propose a mini-table with suggested headers "
            "(Name, Email, Amount, Date) in generated_allowed_cells."
            "\n- Do not invent real sensitive data (real IDs, real personal emails, real bank account numbers). Use domains like @example.com."
            "\n- If the request does not specify how many records, generate at least 10 rows or fill the allowed cells, whichever is less."
            "\n- If the request does not make sense (no cells, no columns detected), return a JSON with a summary explaining the limitation and empty changes []."
            "\n- Do not change cells outside allowed_cells or generated_allowed_cells."
        ),
        "Briefly explain what type of data you generated and return a single JSON in ```json with many changes (one per cell to fill):\n" + CALC_ACTION_SCHEMA,
        'Request: "fill with random data"\n'
        '```json\n'
        '{"changes":['
        '{"cell":"A2","value":"=ELEGIR(ALEATORIO.ENTRE(1;6);\\"Anna\\";\\"John\\";\\"Maria\\";\\"Peter\\";\\"Lucia\\";\\"Sofia\\")","formula":true},'
        '{"cell":"B2","value":"=CONCATENAR(\\"user\\";TEXTO(ALEATORIO.ENTRE(100;999);\\"000\\");\\"@example.com\\")","formula":true},'
        '{"cell":"C2","value":"=ELEGIR(ALEATORIO.ENTRE(1;3);\\"Active\\";\\"Pending\\";\\"Closed\\")","formula":true},'
        '{"cell":"D2","value":"=FECHA(2024;ALEATORIO.ENTRE(1;12);ALEATORIO.ENTRE(1;28))","formula":true},'
        '{"cell":"E2","value":"=REDONDEAR(ALEATORIO()*9900+100;2)","formula":true}'
        '],"summary":"Filled with random data: names, emails, statuses, dates, amounts"}\n```',
    )


def calc_clean(ctx):
    return _block(
        "You are a data-cleaning specialist for LibreOffice Calc.",
        "Propose safe corrections for the selected data.",
        ctx,
        COMMON_RULES + "\n- Do not delete data.\n- Only fix obvious errors or simple text formatting.\n- Do not change cells outside allowed_cells.",
        "Briefly explain and return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
    )


def calc_clean_advanced(ctx):
    return _block(
        "You are a senior data-cleaning specialist for LibreOffice Calc.",
        "Detect and propose advanced cleaning: whitespace, case normalization, numbers stored as text, dates as text, visible duplicates, and inconsistencies.",
        ctx,
        COMMON_RULES + "\n- Do not delete rows or columns.\n- Do not remove duplicates; only mark or normalize safe values.\n- Convert numbers-as-text only if obvious.\n- Do not change cells outside allowed_cells.",
        "Briefly explain and return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
        '```json\n{"changes":[{"cell":"A2","value":"Juan Perez","formula":false},{"cell":"B2","value":"1234","formula":false}],"summary":"Normalize whitespace and number-as-text"}\n```',
    )


def calc_duplicate_finder(user_prompt, ctx):
    return _block(
        "You are a data quality auditor for LibreOffice Calc.",
        "Detect duplicates, missing data, and visible inconsistencies, and propose safe markings without deleting data.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Use duplicate_rows, duplicate_values, blank_cells, and column_profiles if they exist.\n- Do not delete rows, columns, or content.\n- For duplicates, mark cells/rows with a soft color or add a visible note in an allowed cell if appropriate.\n- Do not change cells outside allowed_cells.",
        "Briefly explain and return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
        '```json\n{"changes":[{"cell":"A3","background":"#FFF2CC"},{"cell":"A7","background":"#FFF2CC"}],"summary":"Mark found duplicate values"}\n```',
    )


def calc_sheet_builder(user_prompt, ctx):
    return _block(
        "You are a professional spreadsheet designer for LibreOffice Calc.",
        "Create or edit a complete sheet from the selected starting cell: headers, base rows, formulas, totals, and formatting.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- If the selection is a single cell, use it as the top-left corner.\n- You may use generated_allowed_cells to create a structure within the allowed area.\n- Do not use cells outside generated_allowed_cells or allowed_cells.\n- Create clear headers, LibreOffice Calc-compatible formulas, and professional formatting.\n- Do not invent real data; use editable examples, placeholders, or empty rows where appropriate.\n- Allowed formats: bold, italic, background, font_color, border, width.",
        "Briefly explain and return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
        'Request: "create monthly budget"\n```json\n{"changes":[{"cell":"A1","value":"Category","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"B1","value":"Budget","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"C1","value":"Actual","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"D1","value":"Difference","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"D2","value":"=B2-C2","formula":true}],"summary":"Creates monthly budget structure"}\n```',
    )


def calc_bank_reconciliation(user_prompt, ctx):
    return _block(
        "You are a banking reconciliation and accounting control specialist for LibreOffice Calc.",
        "Compare bank transactions/accounting ledger within the selection and propose safe markings for reconciliation, pending items, or differences.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Use bank_reconciliation.candidate_columns, amount_matches, and suggested_pairs if they exist.\n- Look for likely date, description/concept, and amount columns.\n- Do not delete rows, columns, or data.\n- Do not move transactions.\n- Mark exact or likely matches with soft colors and/or write statuses in allowed empty cells.\n- Suggested statuses: Reconciled, Review, Pending, Difference.\n- If there is no status column within allowed_cells, use background formatting to mark relevant rows/cells.\n- Do not change cells outside allowed_cells.",
        "Briefly explain the criteria used and return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
        '```json\n{"changes":[{"cell":"E2","value":"Reconciled","formula":false,"background":"#D9EAD3"},{"cell":"E3","value":"Review","formula":false,"background":"#FFF2CC"},{"cell":"C3","background":"#FFF2CC"}],"summary":"Mark reconciled transactions and pending review"}\n```',
    )


def calc_reconciliation_advanced(user_prompt, ctx):
    return _block(
        "You are a specialized accounting auditor for bank reconciliation in LibreOffice Calc.",
        "Reconcile bank transactions, accounting ledger, or statements within the selected range.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Use bank_reconciliation.candidate_columns, amount_matches, suggested_pairs, and profile_summary.\n- Identify likely date, description, amount, balance, and status columns.\n- Prioritize suggested_pairs with high confidence for preliminary reconciliation.\n- Do not delete rows, move data, or change original amounts.\n- If the user only asks to audit/analyze, do not return JSON.\n- If asking to mark or prepare reconciliation, write statuses only in allowed empty cells or use soft colors.\n- Allowed statuses: Reconciled, Pending, Review, Difference, Duplicate.\n- If no empty status column exists, mark cells with background and explain the criteria.\n- Do not change cells outside allowed_cells or generated_allowed_cells when applicable.",
        "For analysis: natural text with Summary, Detected Columns, Matches, Pending, and Risks.\nFor changes: briefly explain and return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
        '```json\n{"changes":[{"cell":"E2","value":"Reconciled","formula":false,"background":"#D9EAD3"},{"cell":"E3","value":"Review","formula":false,"background":"#FFF2CC"}],"summary":"Marks preliminary bank reconciliation"}\n```',
    )


def calc_audit_sheet(user_prompt, ctx):
    return _block(
        "You are a senior LibreOffice Calc spreadsheet auditor.",
        "Audit quality, risks, and consistency of the selection.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Use profile_summary.quality_findings, column_profiles, duplicate_rows, duplicate_values, blank_cells, and formula_cells.\n- Review gaps, duplicates, numbers-as-text, dates-as-text, suspicious negatives, mixed formulas, and dubious totals.\n- If the user only asks to audit/review, do not return JSON or propose actionable changes.\n- If asking to mark problems, use soft colors and do not change original values.\n- Do not delete rows, columns, or content.\n- Do not change cells outside allowed_cells.",
        "For audit without changes: natural text with High Risk, Medium Risk, Low Risk, Recommendations.\nFor marking: return JSON with this contract:\n" + CALC_ACTION_SCHEMA,
        '```json\n{"changes":[{"cell":"A7","background":"#F4CCCC"},{"cell":"C12","background":"#FFF2CC"}],"summary":"Marks detected audit risks"}\n```',
    )


def calc_audit_report(user_prompt, ctx):
    return _block(
        "You are a senior LibreOffice Calc spreadsheet auditor.",
        "Create an audit report in a new sheet using findings from the selected range.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Always use target_sheet=\"Audit Report IA\" unless the user specifies another destination sheet.\n- Write only within audit_report_allowed_cells, normally starting from A1.\n- Do not modify the source table or its values.\n- Use profile_summary.quality_findings, formula_audit.suspect_cells, formula_audit.visible_errors, duplicate_rows, duplicate_values, blank_cells, and bank_reconciliation.suggested_pairs.\n- Recommended structure: title, audited range, date/status if available, executive summary, findings table.\n- Suggested findings table: Severity, Type, Location, Detail, Recommendation.\n- If no findings exist, still create a report stating that no obvious problems were detected.\n- Use soft colors: high #F4CCCC, medium #FFF2CC, low #D9EAD3, headers #D9EAF7.\n- Do not invent problems not supported by the context.",
        "Briefly explain and return a single JSON in ```json with this contract:\n"
        + '{"target_sheet":"Audit Report IA","changes":[{"cell":"A1","value":"Audit Report","formula":false,"bold":true,"background":"#D9EAF7","border":true,"width":3500}],"summary":"Create audit report"}',
        '```json\n{"target_sheet":"Audit Report IA","changes":[{"cell":"A1","value":"Audit Report","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"A3","value":"Severity","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"B3","value":"Type","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"C3","value":"Location","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"D3","value":"Detail","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"E3","value":"Recommendation","formula":false,"bold":true,"background":"#D9EAF7"}],"summary":"Creates audit report in new sheet"}\n```',
    )


def calc_formula_audit(user_prompt, ctx):
    return _block(
        "You are an expert formula auditor for LibreOffice Calc.",
        "Audit formulas, column patterns, broken references, and inconsistent formulas.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Use formula_audit.suspect_cells, formula_audit.visible_errors, formula_cells, and column_profiles[].formula_patterns.\n- Detect visible errors (#VALUE, #REF, #DIV/0, #N/A) and formulas that do not follow the column pattern.\n- If the user only asks to audit, do not return JSON.\n- If proposing a fix, it must start with = and be within allowed_cells.\n- Explain why the formula is suspicious before proposing a change.\n- Do not replace formulas without sufficient evidence.",
        "For audit: natural text with Reviewed Formulas, Inconsistencies, Risks, Suggested Fixes.\nFor changes: return JSON with this contract:\n" + CALC_ACTION_SCHEMA,
        '```json\n{"changes":[{"cell":"D8","value":"=B8*C8","formula":true,"background":"#D9EAD3"}],"summary":"Fixes inconsistent formula in D8"}\n```',
    )


def calc_summary_table_builder(user_prompt, ctx):
    return _block(
        "You are a data analyst and summary table builder for LibreOffice Calc.",
        "Create a summary table (pivot-table-style phase 1), using the selected range as the source.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This does NOT create a real DataPilot yet; it creates an editable summary table with headers, formulas, or aggregated values.\n- Use profile_summary.likely_dimension_columns and likely_metric_columns to choose dimensions and metrics.\n- For summaries and pivot-table-phase-1 always use target_sheet=\"Summary IA\" unless the user specifies another destination sheet.\n- In target_sheet use cells within summary_allowed_cells, normally starting from A1.\n- You may use LibreOffice Calc-compatible formulas like SUMA, SUMAR.SI, CONTAR.SI, SUMAR.SI.CONJUNTO, and CONTAR.SI.CONJUNTO.\n- Do not alter the source table.\n- Do not change cells outside summary_allowed_cells when using target_sheet.",
        "Briefly explain the structure and return a single JSON in ```json with this contract:\n"
        + '{"target_sheet":"Summary IA","changes":[{"cell":"A1","value":"Title","formula":false,"bold":true,"background":"#D9EAF7","font_color":"#000000","border":true,"width":3000}],"summary":"brief summary"}',
        '```json\n{"target_sheet":"Summary IA","changes":[{"cell":"A1","value":"Summary","formula":false,"bold":true,"background":"#D9EAF7"},{"cell":"A2","value":"Category","formula":false,"bold":true},{"cell":"B2","value":"Total","formula":false,"bold":true}],"summary":"Creates base summary table"}\n```',
    )


def calc_pivot_table(user_prompt, ctx):
    return _block(
        "You are a DataPilot/pivot table expert for LibreOffice Calc.",
        "Create a real pivot table using the selected data range as source.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This creates a REAL DataPilot pivot table using LibreOffice's native API.\n- Use the range from context (e.g., '" + (ctx.get("range") or "A1:E20") + "') as the source_range.\n- Use profile_summary.likely_dimension_columns as candidates for row_fields or column_fields.\n- Use profile_summary.likely_metric_columns as candidates for data_fields.\n- row_fields: columns to group by in rows (dimensions like Category, Region, Month, etc.)\n- column_fields: columns to group by in columns (optional, creates a 2D pivot table)\n- data_fields: numeric columns to aggregate with function: sum, count, average, max, min\n- dest_cell: where to place the pivot table top-left corner (default: A1)\n- dest_sheet: sheet name for the pivot table (a new sheet will be created)\n- Do NOT return regular cell changes; return the pivot table action.\n- Do NOT alter the source data.",
        "Return a single JSON in ```json with this contract:\n" + CALC_PIVOT_SCHEMA,
        'Request: "Create pivot table by category with sum of amounts"\n```json\n{"action":"create_pivot_table","summary":"Creates pivot table by Category with Sum of Amount","source_range":"A1:E50","row_fields":["Category"],"column_fields":[],"data_fields":[{"field":"Amount","function":"sum","name":"Total Amount"}],"dest_cell":"G1","dest_sheet":"Pivot IA"}\n```',
    )


def calc_profile_data(ctx):
    return _block(
        "You are a data profiler for LibreOffice Calc.",
        "Profile the selected table and explain if it is ready for analysis.",
        ctx,
        COMMON_RULES + "\n- Do not return JSON.\n- Do not modify or propose actionable changes.\n- Use column_profiles, profile_summary, headers, header_confidence, type_counts, and blank_cells.\n- For each important column mention type, blanks, unique/duplicate count, and numeric summary if available.\n- Indicate dimension columns, metrics, and possible keys.",
        "Return natural text with sections: Table Summary, Columns, Data Quality, Detected Metrics, Recommendations.",
    )


def calc_format(user_prompt, ctx):
    return _block(
        "You are a formatting specialist for LibreOffice Calc spreadsheets.",
        "Convert the request into applicable format/cell changes.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Allowed formats: bold, italic, background, font_color, border, width.\n- Colors in hexadecimal #RRGGBB.\n- Do not change cells outside allowed_cells.",
        "Briefly explain and return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
        'Request: "make headers yellow and bold"\n```json\n{"changes":[{"cell":"A1","bold":true,"background":"#FFF2CC"},{"cell":"B1","bold":true,"background":"#FFF2CC"}],"summary":"Highlights headers"}\n```',
    )


def calc_format_table(user_prompt, ctx):
    return _block(
        "You are a table designer for LibreOffice Calc.",
        "Apply readable table formatting: highlighted headers, simple borders, soft colors, important columns, and reasonable width.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Do not alter values unless explicitly requested.\n- Use header_confidence and headers to prioritize headers.\n- Allowed formats: bold, italic, background, font_color, border, width.",
        "Briefly explain and return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
        '```json\n{"changes":[{"cell":"A1","bold":true,"background":"#D9EAF7","border":true},{"cell":"B1","bold":true,"background":"#D9EAF7","border":true}],"summary":"Formats headers"}\n```',
    )


def calc_preview(user_prompt, ctx):
    lower = user_prompt.lower()
    if any(word in lower for word in (
        "reporte de auditoria", "reporte de auditoría", "informe de auditoria", "informe de auditoría",
        "hoja de auditoria", "hoja de auditoría", "crear auditoria", "creá auditoría",
        "crear auditoría", "creá auditoria",
        "audit report", "create audit", "make audit", "build audit",
    )):
        return calc_audit_report(user_prompt, ctx)
    if any(word in lower for word in (
        "tabla dinamica real", "tabla dinámica real", "datapilot", "data pilot",
        "pivot table real", "crear pivot", "creá pivot", "tabla cruzada",
        "real pivot", "true pivot", "pivot verdadero",
    )):
        return calc_pivot_table(user_prompt, ctx)
    if any(word in lower for word in (
        "tabla resumen", "resumen por", "reporte por",
        "sumá importes por", "suma importes por", "crear resumen", "creá resumen", "hoja de resumen",
        "summary table", "summary by", "report by", "sum amounts by", "create summary",
    )):
        return calc_summary_table_builder(user_prompt, ctx)
    if any(word in lower for word in (
        "audita formula", "auditá formula", "auditar formula", "audita fórmula",
        "auditá fórmula", "auditar fórmula", "formulas rotas", "fórmulas rotas",
        "formula inconsistente", "fórmula inconsistente",
        "audit formula", "audit formulas", "broken formula", "broken formulas",
        "inconsistent formula", "inconsistent formulas",
    )):
        return calc_formula_audit(user_prompt, ctx)
    if any(word in lower for word in (
        "audita", "auditá", "auditar", "riesgo", "riesgos", "controla", "controlá",
        "controlar totales", "problemas de calidad",
        "audit", "risk", "risks", "quality issues", "data quality",
    )):
        return calc_audit_sheet(user_prompt, ctx)
    if any(word in lower for word in (
        "conciliacion", "conciliación", "conciliar", "banco", "bancaria", "bancario",
        "extracto", "movimientos bancarios", "libro banco",
        "reconciliation", "reconcile", "bank", "banking", "bank statement", "movements", "ledger",
    )):
        return calc_reconciliation_advanced(user_prompt, ctx)
    if any(word in lower for word in (
        "presupuesto", "inventario", "cronograma", "flujo de caja", "cashflow",
        "control de gastos", "crear hoja", "crea una hoja", "crear tabla", "crea una tabla",
        "planilla", "dashboard", "kpi",
        "budget", "inventory", "schedule", "timeline", "gantt", "cash flow",
        "expense tracker", "create sheet", "create a sheet", "create table", "create a table",
        "spreadsheet", "template", "dashboard", "kpi",
    )):
        return calc_sheet_builder(user_prompt, ctx)
    if any(word in lower for word in (
        "error", "falla", "#valor", "#ref", "#div", "#n/a", "arreglar formula",
        "arreglar fórmula", "arregla la formula", "arregla la fórmula",
        "arreglar la formula", "arreglar la fórmula",
        "corregir formula", "corregir fórmula", "corregi la formula", "corregi la fórmula",
        "fix formula", "fix formulas", "fix the formula", "fix the formulas",
        "fix this formula", "fix my formula", "fix a formula",
        "correct formula", "correct formulas", "correct the formula", "correct this formula",
    )):
        return calc_formula_debug(user_prompt, ctx)
    if any(word in lower for word in (
        "aleatorio", "aleatoria", "aleatorios", "aleatorias", "random", "ficticio",
        "ficticios", "ficticia", "ficticias", "inventado", "inventados", "sintetico",
        "sinteticos", "al azar", "datos aleatorios", "datos de prueba", "datos falsos",
        "datos ficticios", "datos mock", "datos fake", "datos random", "datos de ejemplo",
        "datos demo", "datos inventados", "datos sinteticos",
        "fictional", "fictitious", "synthetic", "dummy", "test data", "sample data",
        "fake data", "mock data", "example data", "demo data",
    )):
        return calc_random_fill(user_prompt, ctx)
    if any(word in lower for word in (
        "rellenar", "copiar hacia abajo", "hacia abajo", "toda la columna", "llenar columna",
        "fill down", "fill column", "copy down", "drag down",
    )):
        return calc_formula_fill(user_prompt, ctx)
    if any(word in lower for word in (
        "duplicado", "duplicados", "repetido", "repetidos", "faltantes",
        "duplicate", "duplicates", "repeated", "missing",
    )):
        return calc_duplicate_finder(user_prompt, ctx)
    if any(word in lower for word in (
        "limpiar", "espacios", "fechas", "numeros como texto", "números como texto", "normalizar",
        "clean", "spaces", "whitespace", "trim", "normalize", "numbers as text",
    )):
        return calc_clean_advanced(ctx)
    if any(word in lower for word in (
        "formato", "color", "fondo", "negrita", "cursiva", "resaltar", "pintar", "bordes", "ancho",
        "format", "background", "bold", "italic", "highlight", "paint", "borders", "width",
    )):
        return calc_format_table(user_prompt, ctx)
    if any(word in lower for word in (
        "detectar", "estructura", "problemas", "encabezados", "tabla",
        "detect", "structure", "issues", "headers", "table",
    )):
        return calc_format_table(user_prompt, ctx)
    if any(word in lower for word in (
        "formula", "fórmula", "sumar", "promedio", "contar", "calcular", "=",
        "sum", "average", "avg", "count", "calculate", "compute",
    )):
        return calc_formula(user_prompt, ctx)
    return _block(
        "You are an advanced assistant for LibreOffice Calc.",
        "Convert the request into safe applicable changes.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- You may change values, formulas, and basic formats.\n- Do not change cells outside allowed_cells.",
        "Briefly explain and return a single JSON in ```json with this contract:\n" + CALC_ACTION_SCHEMA,
    )
