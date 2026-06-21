"""Skill router facade for LibreOffice Calc and Writer.

The concrete prompt skills live in skills_calc.py and skills_writer.py.
This module keeps the old public API used by panel.py and prompts.py.
"""

from skills_common import chat
from skills_calc import *
from skills_writer import *


def route(skill_name, user_prompt, ctx):
    kind = (ctx or {}).get("kind", "calc")
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
