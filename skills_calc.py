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
            "\n\nCRITICAL COMPLETENESS RULE: When the user explicitly requests a specific number of rows, "
            "generate EXACTLY that many rows. Do NOT stop after a few rows. Emit every change entry for every cell "
            "of every row. Completeness > brevity."
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


def calc_consolidate(user_prompt, ctx):
    return _block(
        "You are a data consolidation specialist for LibreOffice Calc.",
        "Consolidate data from multiple sheets into a single summary sheet.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This action consolidates data from multiple sheets into one.\n- Use source_sheets to list specific sheet names, or omit to use all sheets.\n- Set has_headers=true if the first row contains column headers.\n- The destination sheet will be named as specified (default: 'Consolidado').\n- Headers from the first sheet will be used; data rows from all sheets will be combined.\n- Do not alter the source sheets.",
        "Return a single JSON in ```json with this contract:\n" + CALC_CONSOLIDATE_SCHEMA,
        'Request: "Consolidate Hoja1 and Hoja2"\n```json\n{"action":"consolidate_sheets","summary":"Consolidates data from Hoja1 and Hoja2","source_sheets":["Hoja1","Hoja2"],"dest_sheet_name":"Consolidado","has_headers":true}\n```',
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


def calc_create_chart(user_prompt, ctx):
    return _block(
        "You are a data visualization expert for LibreOffice Calc.",
        "Create a chart from the selected data range.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This creates a real chart in the spreadsheet.\n- Use the range from context (e.g., '" + (ctx.get("range") or "A1:B10") + "') as the source_range.\n- chart_type options: bar, line, pie, area, scatter.\n- title is optional and sets the chart title.\n- dest_cell is where the chart will be placed (default: A1).\n- Do NOT return regular cell changes; return the chart action.\n- Detect if data has labels in first column or first row to set up the chart correctly.",
        "Return a single JSON in ```json with this contract:\n" + CALC_CHART_SCHEMA,
        'Request: "Create a bar chart with sales data"\n```json\n{"action":"create_chart","summary":"Creates bar chart from sales data","source_range":"A1:B12","chart_type":"bar","title":"Ventas por Mes","dest_cell":"D1"}\n```',
    )


def calc_conditional_format(user_prompt, ctx):
    return _block(
        "You are a formatting expert for LibreOffice Calc.",
        "Apply conditional formatting to a cell range based on conditions.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This applies conditional formatting to a range.\n- Use the range from context (e.g., '" + (ctx.get("range") or "A1:A10") + "') as the cell_range.\n- condition options: greater, less, equal, between, contains.\n- value is the threshold (number, text, or date) for the condition.\n- style_type: color (font color), background (cell color), bold, italic.\n- style_value: hex color like #FF0000 or true/false for bold/italic.\n- Do NOT return regular cell changes.",
        "Return a single JSON in ```json with this contract:\n" + CALC_CONDITIONAL_FORMAT_SCHEMA,
        'Request: "Highlight values greater than 1000 in red"\n```json\n{"action":"apply_conditional_format","summary":"Highlights values > 1000 in red","cell_range":"A1:A10","condition":"greater","value":1000,"style_type":"color","style_value":"#FF0000"}\n```',
    )


def calc_data_validation(user_prompt, ctx):
    return _block(
        "You are a data validation expert for LibreOffice Calc.",
        "Apply data validation (dropdown lists, number ranges, dates) to a cell range.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This applies data validation to a range.\n- Use the range from context (e.g., '" + (ctx.get("range") or "A1:A10") + "') as the cell_range.\n- validation_type: list (dropdown), number, date, time, textlength.\n- formula1: for list use semicolon-separated values like 'Si;No;Talvez'.\n- For number/date use a value like 100 or '>=10'.\n- show_input_message: show tooltip when cell is selected.\n- show_error: show error when invalid data entered.\n- error_style: stop (blocks input), warning, information.\n- Do NOT return regular cell changes.",
        "Return a single JSON in ```json with this contract:\n" + CALC_DATA_VALIDATION_SCHEMA,
        'Request: "Add dropdown with Si, No, Talvez"\n```json\n{"action":"apply_data_validation","summary":"Adds dropdown list","cell_range":"A1:A10","validation_type":"list","formula1":"Si;No;Talvez","show_input_message":true,"input_title":"Seleccionar","input_message":"Elija una opcion","show_error":true,"error_title":"Error","error_message":"Valor no valido","error_style":"stop"}\n```',
    )


def calc_apply_theme(user_prompt, ctx):
    return _block(
        "You are a styling expert for LibreOffice Calc.",
        "Apply a professional theme to the selected data range.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This applies a predefined color theme to a range.\n- Use the range from context (e.g., '" + (ctx.get("range") or "A1:E20") + "') as the range.\n- Theme options: corporativo (blue), analisis (green), presentacion (purple), azul_profesional, verde_financiero, moderno (gray).\n- include_totals: set to true if last row contains totals.\n- Headers get bold text and theme background color.\n- Alternating rows get subtle background colors.\n- Borders are applied for clean look.\n- Do NOT return regular cell changes.",
        "Return a single JSON in ```json with this contract:\n" + CALC_THEME_SCHEMA,
        'Request: "Apply corporate theme"\n```json\n{"action":"apply_theme","summary":"Applies corporate theme","range":"A1:E20","theme_name":"corporativo","include_totals":false}\n```',
    )


def calc_generate_macro(user_prompt, ctx):
    return _block(
        "You are a LibreOffice Basic macro expert.",
        "Generate LibreOffice Basic code for the requested automation.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This generates LibreOffice Basic macro code.\n- Return ONLY the macro code, no explanations, no JSON.\n- Use proper Basic syntax with Sub/End Sub.\n- Include comments in Spanish explaining the code.\n- The code should be ready to paste into a Basic module.\n- Do NOT return JSON or any other format.",
        "Return ONLY the LibreOffice Basic macro code in a code block.\nDo NOT add explanations outside the code block.",
        "Request: Create a macro to format all headers in bold\n```basic\nSub FormatearEncabezados\n    REM Formatea todas las celdas de encabezado en negrita\n    Dim oDoc As Object\n    Dim oHoja As Object\n    Dim oCelda As Object\n    Dim i As Long\n    \n    oDoc = ThisComponent\n    oHoja = oDoc.getSheets().getByIndex(0)\n    \n    For i = 0 To oHoja.getColumns().getCount() - 1\n        oCelda = oHoja.getCellByPosition(i, 0)\n        oCelda.CharWeight = com.sun.star.awt.FontWeight.BOLD\n    Next i\n    \n    MsgBox \"Encabezados formateados exitosamente!\", 64, \"Libre Asist\"\nEnd Sub\n```",
    )


def calc_icon_conditional_format(user_prompt, ctx):
    return _block(
        "You are a data visualization expert for LibreOffice Calc.",
        "Apply icon-based conditional formatting (traffic lights, arrows, gauges) to a range.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This applies icon-based conditional formatting to a range.\n- Use the range from context (e.g., A1:A10) as the cell_range.\n- icon_style options: traffic_light, arrows_up_down, arrows_gray, stars, bars.\n- thresholds: list of values like [33, 67] for traffic light ranges.\n- Do NOT return regular cell changes.",
        "Return a single JSON in ```json with this contract:\n" + CALC_CONDITIONAL_FORMAT_SCHEMA,
        'Request: Add traffic light icons for status column\n```json\n{"action":"apply_conditional_format","summary":"Adds traffic light icons","cell_range":"A1:A10","condition":"greater","value":0,"style_type":"icon","style_value":"traffic_light"}\n```',
    )


def calc_preview(user_prompt, ctx):
    return _block(
        "You are a data filtering expert for LibreOffice Calc.",
        "Apply a filter to the selected data range.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This applies an autofilter to a range.\n- Use the range from context (e.g., '" + (ctx.get("range") or "A1:E20") + "') as the range.\n- filter_type: autofilter adds dropdown buttons to column headers.\n- criteria: advanced filter with specific conditions (future).\n- show_filter_buttons: whether to show filter dropdowns.\n- Do NOT return regular cell changes.",
        "Return a single JSON in ```json with this contract:\n" + CALC_FILTER_SCHEMA,
        'Request: "Apply filter to this data"\n```json\n{"action":"apply_filter","summary":"Applies autofilter","range":"A1:E20","filter_type":"autofilter","show_filter_buttons":true}\n```',
    )


def calc_apply_filter(user_prompt, ctx):
    return _block(
        "You are a data filtering expert for LibreOffice Calc.",
        "Apply a filter to the selected data range.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This applies an autofilter to a range.\n- Use the range from context (e.g., A1:E20) as the range.\n- filter_type: autofilter adds dropdown buttons to column headers.\n- criteria: advanced filter with specific conditions.\n- Do NOT return regular cell changes.",
        "Return a single JSON in ```json with this contract:\n" + CALC_FILTER_SCHEMA,
        'Request: "Apply filter to this data"\n```json\n{"action":"apply_filter","summary":"Applies autofilter","range":"A1:E20","filter_type":"autofilter","show_filter_buttons":true}\n```',
    )


def calc_apply_protection(user_prompt, ctx):
    return _block(
        "You are a spreadsheet protection expert for LibreOffice Calc.",
        "Apply or remove protection from a sheet.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- This protects or unprotects a sheet.\n- sheet_name: name of the sheet to protect (optional, uses active sheet).\n- protect: true to protect, false to unprotect.\n- password: optional password for protection.\n- protect_formulas: if true, formulas are also protected.\n- Do NOT return regular cell changes.",
        "Return a single JSON in ```json with this contract:\n" + CALC_PROTECTION_SCHEMA,
        'Request: "Protect this sheet"\n```json\n{"action":"apply_protection","summary":"Protects sheet","protect":true,"password":null,"protect_formulas":true}\n```',
    )


def calc_preview(user_prompt, ctx):
    lower = user_prompt.lower()
    # Charts
    if any(word in lower for word in (
        "create chart", "make chart", "bar chart", "line chart", "pie chart", "area chart",
        "scatter plot", "build chart", "generate chart",
    )):
        return calc_create_chart(user_prompt, ctx)
    # Pivot tables
    if any(word in lower for word in (
        "pivot table", "datapilot", "data pilot", "pivot", "cross table",
    )):
        return calc_pivot_table(user_prompt, ctx)
    # Consolidate sheets
    if any(word in lower for word in (
        "consolidate", "combine sheets", "merge sheets", "join sheets",
        "aggregate sheets", "merge data",
    )):
        return calc_consolidate(user_prompt, ctx)
    # Summary table
    if any(word in lower for word in (
        "summary table", "summary by", "create summary", "sum amounts by",
        "report by", "aggregate",
    )):
        return calc_summary_table_builder(user_prompt, ctx)
    # Formula audit
    if any(word in lower for word in (
        "audit formula", "audit formulas", "broken formula", "broken formulas",
        "formula error", "formulas rotas",
    )):
        return calc_formula_audit(user_prompt, ctx)
    # Audit sheet
    if any(word in lower for word in (
        "audit", "audit report", "risk", "quality issues", "data quality",
    )):
        return calc_audit_sheet(user_prompt, ctx)
    # Reconciliation
    if any(word in lower for word in (
        "reconciliation", "reconcile", "bank reconciliation", "bank statement",
        "conciliación", "conciliar",
    )):
        return calc_reconciliation_advanced(user_prompt, ctx)
    # Conditional format
    if any(word in lower for word in (
        "conditional format", "highlight if", "color if", "bold if",
        "format if", "color by value",
    )):
        return calc_conditional_format(user_prompt, ctx)
    # Data validation
    if any(word in lower for word in (
        "data validation", "dropdown", "input validation", "restrict cell",
        "validación de datos",
    )):
        return calc_data_validation(user_prompt, ctx)
    # Theme
    if any(word in lower for word in (
        "apply theme", "theme", "style", "corporate style", "professional colors",
        "estilo", "tema",
    )):
        return calc_apply_theme(user_prompt, ctx)
    # Filter
    if any(word in lower for word in (
        "apply filter", "autofilter", "filter data", "filter",
    )):
        return calc_apply_filter(user_prompt, ctx)
    # Protection
    if any(word in lower for word in (
        "protect", "unprotect", "lock", "protect sheet", "protect cells",
        "bloquear", "proteger",
    )):
        return calc_apply_protection(user_prompt, ctx)
    # Macro
    if any(word in lower for word in (
        "macro", "basic code", "automation", "create macro", "generate macro",
    )):
        return calc_generate_macro(user_prompt, ctx)
    # Icon conditional format
    if any(word in lower for word in (
        "traffic light", "icon", "data bars", "icon sets", "semaforo",
    )):
        return calc_icon_conditional_format(user_prompt, ctx)
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
