"""Advanced prompt skills for LibreOffice Calc and Writer."""

import json
from i18n import _


CALC_ACTION_SCHEMA = (
    '{"changes":[{"cell":"A1","value":"new value or formula","formula":false,'
    '"bold":true,"italic":false,"background":"#FFF2CC","font_color":"#000000","border":true,"width":2500}],'
    '"summary":"brief summary"}'
)

CALC_PIVOT_SCHEMA = (
    '{"action":"create_pivot_table","summary":"Create pivot table",'
    '"source_range":"A1:E20","row_fields":["Category"],"column_fields":[],'
    '"data_fields":[{"field":"Amount","function":"sum","name":"Total Amount"}],'
    '"dest_cell":"G1","dest_sheet":"Pivot IA"}'
)

CALC_CONSOLIDATE_SCHEMA = (
    '{"action":"consolidate_sheets","summary":"Consolidate sheets",'
    '"source_sheets":["Hoja1","Hoja2"],"dest_sheet_name":"Consolidado","has_headers":true}'
)

CALC_CHART_SCHEMA = (
    '{"action":"create_chart","summary":"Create chart",'
    '"source_range":"A1:B10","chart_type":"bar","title":"Ventas por Mes",'
    '"dest_cell":"D1","dest_sheet_name":null}'
)

CALC_CONDITIONAL_FORMAT_SCHEMA = (
    '{"action":"apply_conditional_format","summary":"Apply conditional format",'
    '"cell_range":"A1:A10","condition":"greater","value":1000,'
    '"style_type":"color","style_value":"#FF0000"}'
)

CALC_DATA_VALIDATION_SCHEMA = (
    '{"action":"apply_data_validation","summary":"Apply data validation",'
    '"cell_range":"A1:A10","validation_type":"list","formula1":"Si;No;Talvez",'
    '"show_input_message":true,"input_title":"Seleccionar","input_message":"Elija una opcion",'
    '"show_error":true,"error_title":"Error","error_message":"Valor no valido","error_style":"stop"}'
)

WRITER_ACTION_SCHEMA = (
    '{"action":"replace_selection","text":"final text","summary":"brief summary",'
    '"style":{"font_size":12,"font_name":"Liberation Sans","bold":false,"italic":false,'
    '"font_color":"#111111","background":"#FFFFFF","align":"left","line_spacing":1.15,'
    '"space_before":0,"space_after":180,"left_margin":0,"right_margin":0,'
    '"first_line_indent":0,"paragraph_style":"Text Body"},'
    '"page_style":{"left_margin":2500,"right_margin":2500,"top_margin":2500,"bottom_margin":2500},'
    '"blocks":[{"text":"Title","style":{"paragraph_style":"Heading 1","font_size":18,"bold":true}}],'
    '"replacements":[{"find":"current text","replace":"new text","match_case":true}]}'
)

WRITER_LIST_SCHEMA = (
    '{"action":"apply_list","summary":"Apply list to selection",'
    '"list_style":"bullet","level":0,"start_at":1}'
)

WRITER_HYPERLINK_SCHEMA = (
    '{"action":"insert_hyperlink","summary":"Insert hyperlink",'
    '"text":"visible text","url":"https://example.com","apply_to_selection":false}'
)

WRITER_TABLE_SCHEMA = (
    '{"action":"insert_table","summary":"Insert table",'
    '"rows":4,"cols":3,"headers":["Product","Price","Stock"],'
    '"rows_data":[["Item 1","100","5"],["Item 2","200","3"]],'
    '"style":{"header_background":"#D9EAF7","header_bold":true}}'
)

WRITER_HEADER_FOOTER_SCHEMA = (
    '{"action":"set_header_footer","summary":"Set header and footer",'
    '"header":{"text":"My document","alignment":"center","page_numbers":false},'
    '"footer":{"text":"Page ","alignment":"right","page_numbers":true},'
    '"first_page_different":false}'
)

WRITER_FOOTNOTE_SCHEMA = (
    '{"action":"insert_footnote","summary":"Insert footnote",'
    '"marker_text":"X","note_text":"Explanation of X"}'
)

WRITER_COMMENT_SCHEMA = (
    '{"action":"insert_comment","summary":"Insert review comments",'
    '"comments":[{"marker_text":"optional exact text","comment":"review comment",'
    '"author":"Libre Asist"}]}'
)

WRITER_EXPORT_SCHEMA = (
    '{"action":"export_document","summary":"Export document",'
    '"format":"pdf","path":"/optional/path.pdf"}'
)

WRITER_STYLE_RULES = """
- Allowed Writer style keys: font_size, font_name, bold, italic, font_color, background, align, line_spacing, space_before, space_after, left_margin, right_margin, first_line_indent, paragraph_style.
- align must be one of: left, center, right, justify.
- Colors always in hexadecimal #RRGGBB.
- Margins and spacing are expressed in hundredths of a millimeter; 2500 equals 2.5 cm.
- page_style supports: left_margin, right_margin, top_margin, bottom_margin.
- For documents with titles or sections use blocks: each block is a paragraph with its own text and style.
- Do not write formatting instructions inside text; formatting goes in style, page_style, or blocks[].style.
"""


def _json(ctx):
    if not ctx:
        return "No context available."
    return json.dumps(ctx, ensure_ascii=False, indent=2)


def _block(role, task, ctx, rules, output_contract, examples=""):
    return (
        "<role>\n" + role.strip() + "\n</role>\n\n"
        "<task>\n" + task.strip() + "\n</task>\n\n"
        "<document_context>\n" + _json(ctx) + "\n</document_context>\n\n"
        "<rules>\n" + rules.strip() + "\n</rules>\n\n"
        "<output_contract>\n" + output_contract.strip() + "\n</output_contract>\n\n"
        "<examples>\n" + examples.strip() + "\n</examples>"
    )


COMMON_RULES = """
- ALWAYS respond in the same language as the user's request.
- Do not invent cells, ranges, or content that is not in the context.
- If information is missing, explain the question and propose a conservative action.
- Never say you have already modified the document; only propose changes for the user to confirm in the chat.
- For actionable changes, include a single valid ```json code block.
"""


__all__ = [
    "CALC_ACTION_SCHEMA",
    "CALC_PIVOT_SCHEMA",
    "CALC_CONSOLIDATE_SCHEMA",
    "CALC_CHART_SCHEMA",
    "CALC_CONDITIONAL_FORMAT_SCHEMA",
    "CALC_DATA_VALIDATION_SCHEMA",
    "WRITER_ACTION_SCHEMA",
    "WRITER_LIST_SCHEMA",
    "WRITER_HYPERLINK_SCHEMA",
    "WRITER_TABLE_SCHEMA",
    "WRITER_HEADER_FOOTER_SCHEMA",
    "WRITER_FOOTNOTE_SCHEMA",
    "WRITER_COMMENT_SCHEMA",
    "WRITER_EXPORT_SCHEMA",
    "WRITER_STYLE_RULES",
    "COMMON_RULES",
    "_json",
    "_block",
    "chat",
]


def chat(user_prompt, ctx):
    app = "Writer" if (ctx or {}).get("kind") == "writer" else "Calc"
    return _block(
        _("prompt.system_role", app),
        "Respond to the user's request without modifying the document.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- If the request implies changes, explain that you can prepare a proposal for confirmation.",
        "Return natural language text. Do not return JSON unless the user explicitly asks for an actionable change.",
    )
