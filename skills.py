"""Skill router facade for LibreOffice Calc and Writer.

The concrete prompt skills live in skills_calc.py and skills_writer.py.
This module keeps the old public API used by panel.py and prompts.py.
"""

from skills_common import chat
from skills_calc import *
from skills_writer import *


# Keywords that strongly indicate a request is for one document type
_CALC_KEYWORDS = {
    "spreadsheet", "sheet", "cell", "cells", "column", "row", "range",
    "formula", "formulas", "pivot", "table", "tabla", "hoja", "celda",
    "celdas", "columna", "fila", "rango", "formula", "formulas",
    "chart", "graph", "grafico", "gráfico", "auto-filter", "autofilter",
    "conditional formatting", "validation", "dropdown",
    "formato condicional", "validacion", "validación",
    "suma", "sum", "average", "promedio", "count", "contar",
    "spreadsheet", "planilla", "xls", "xlsx", "ods",
}

_WRITER_KEYWORDS = {
    "paragraph", "document", "doc", "sentence", "letter", "email",
    "report", "article", "essay", "blog", "post",
    "parrafo", "párrafo", "documento", "oración", "oracion",
    "carta", "correo", "email", "reporte", "informe", "articulo",
    "artículo", "ensayo", "blog", "publicacion", "publicación",
    "rewrite", "reescribir", "summarize", "resumir",
    "spell check", "orthography", "ortografia", "ortografía",
    "grammar", "gramatica", "gramática",
    "style", "estilo", "tone", "tono", "voice", "voz",
    "footnote", "nota al pie", "header", "encabezado",
    "footer", "pie de pagina", "página",
    "docx", "odt", "pdf",
}


def detect_intent_kind(user_prompt):
    """Detect whether the user's request is for Calc or Writer based on keywords.

    Returns:
        "calc" if request seems to be for a spreadsheet
        "writer" if request seems to be for a document
        None if ambiguous
    """
    if not user_prompt:
        return None
    lower = user_prompt.lower()

    calc_score = sum(1 for kw in _CALC_KEYWORDS if kw in lower)
    writer_score = sum(1 for kw in _WRITER_KEYWORDS if kw in lower)

    if calc_score > writer_score:
        return "calc"
    if writer_score > calc_score:
        return "writer"
    return None


def check_doc_kind_mismatch(user_prompt, active_kind):
    """Check if user's request is for a different document type.

    Args:
        user_prompt: The user's request text
        active_kind: The currently active document kind ("calc" or "writer")

    Returns:
        str with mismatch message if there's a problem, None otherwise
    """
    if not user_prompt or not active_kind:
        return None

    intent = detect_intent_kind(user_prompt)
    if intent is None or intent == active_kind:
        return None

    # If active is calc but intent is writer (or vice versa)
    return intent


def route(skill_name, user_prompt, ctx):
    kind = (ctx or {}).get("kind", "calc")

    # Cross-check document type vs user intent
    if kind == "calc" and skill_name not in ("chat", "audit_report"):
        mismatch = check_doc_kind_mismatch(user_prompt, kind)
        if mismatch == "writer":
            return _doc_kind_mismatch_block(user_prompt, "writer", ctx)
    elif kind == "writer" and skill_name not in ("chat",):
        mismatch = check_doc_kind_mismatch(user_prompt, kind)
        if mismatch == "calc":
            return _doc_kind_mismatch_block(user_prompt, "calc", ctx)

    if kind == "writer":
        if skill_name == "chat":
            return chat(user_prompt, ctx)
        if skill_name == "review":
            return writer_review(user_prompt, ctx)
        if skill_name == "placeholder_review":
            return writer_placeholder_review(user_prompt, ctx)
        if skill_name in ("explain", "analyze", "summarize"):
            return writer_summarize(ctx) if skill_name == "summarize" else writer_review(user_prompt or "Analyze and explain the text without modifying it.", ctx)
        if skill_name == "clean":
            return writer_correct(ctx)
        if skill_name == "format":
            return writer_format(user_prompt, ctx)
        if skill_name == "bullet_summary":
            return writer_bullet_summary(ctx)
        return writer_preview(user_prompt, ctx)
    if skill_name == "chat":
        return chat(user_prompt, ctx)
    if skill_name == "formula":
        return calc_formula(user_prompt, ctx)
    if skill_name == "analyze":
        return calc_analyze(ctx)
    if skill_name == "clean":
        return calc_clean_advanced(ctx)
    if skill_name == "format":
        return calc_format_table(user_prompt, ctx)
    if skill_name == "sheet_builder":
        return calc_sheet_builder(user_prompt, ctx)
    if skill_name == "duplicate_finder":
        return calc_duplicate_finder(user_prompt, ctx)
    if skill_name == "bank_reconciliation":
        return calc_reconciliation_advanced(user_prompt, ctx)
    if skill_name == "audit":
        return calc_audit_sheet(user_prompt, ctx)
    if skill_name == "profile":
        return calc_profile_data(ctx)
    if skill_name == "formula_audit":
        return calc_formula_audit(user_prompt, ctx)
    if skill_name == "summary_table":
        return calc_summary_table_builder(user_prompt, ctx)
    if skill_name == "audit_report":
        return calc_audit_report(user_prompt, ctx)
    if skill_name == "table_detect":
        return calc_table_detect(ctx)
    if skill_name == "formula_debug":
        return calc_formula_debug(user_prompt, ctx)
    if skill_name == "formula_fill":
        return calc_formula_fill(user_prompt, ctx)
    return calc_preview(user_prompt, ctx)


def _doc_kind_mismatch_block(user_prompt, requested_kind, ctx):
    """Return a block explaining that the request is for a different document type."""
    from skills_common import _block
    if requested_kind == "writer":
        msg = (
            "The request seems to be about a document/paragraph/text (Writer). "
            "But the active document is a Calc spreadsheet. "
            "Open a Writer document to perform this action, or rephrase your request "
            "to ask for something Calc can do (formulas, formatting, charts, etc.)."
        )
    else:
        msg = (
            "The request seems to be about a spreadsheet (cells, formulas, charts). "
            "But the active document is a Writer document. "
            "Open a Calc spreadsheet to perform this action, or rephrase your request "
            "to ask for something Writer can do (text rewriting, formatting, etc.)."
        )
    return (
        "<role>\nYou are a helpful assistant for LibreOffice.\n</role>\n\n"
        "<task>\n" + msg + "\n</task>\n\n"
        "<document_context>\n" + str(ctx)[:500] + "\n</document_context>\n\n"
        "<rules>\n- Be brief and clear.\n- Suggest the correct program.\n- Do NOT take any action.\n- Respond in the same language as the user.\n</rules>\n\n"
        "<output_contract>\nRespond in plain text, no JSON.\n</output_contract>"
    )