"""Writer prompt skills for Libre Asist."""

from skills_common import *


def writer_correct(ctx):
    return writer_rewrite("Fix spelling, grammar, punctuation, and clarity while keeping the original meaning.", ctx)


def writer_rewrite(user_prompt, ctx):
    has_selection = bool((ctx or {}).get("has_selection"))
    has_document_text = bool(str((ctx or {}).get("text", "")).strip())
    target_rule = (
        "- There is a selection: use replace_selection to edit existing text."
        if has_selection else
        "- No selection but there is document text: use replace_document to modify, change, adapt, or correct the existing document."
        if has_document_text else
        "- No selection and no prior text: use insert_text to create new text."
    )
    creation_rules = ""
    if not has_selection and not has_document_text:
        creation_rules = "\n- The document is empty, so format_document, format_selection, replace_document, and replace_text are forbidden.\n- You must create new content using action insert_text.\n- If the user requests a modern style, include style/page_style/blocks inside insert_text.\n- Your response must include a ```json block with action insert_text; do not respond with only natural text."
    return _block(
        "You are a professional editor for LibreOffice Writer.",
        "Modify the text according to the request.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + WRITER_STYLE_RULES + "\n" + target_rule + creation_rules + "\n"
        + "- ALWAYS return a single ```json code block. Never respond in plain natural language only.\n"
        + "- If the request is genuinely ambiguous and you cannot determine what to do, return action append_text with text starting with '[Clarification needed: ' followed by a brief, specific question (max 200 chars). Do NOT invent content.\n"
        + "- When the user says 'below this', 'debajo de este', 'abajo de esto', 'under this' without an explicit selection and the document has content, use action append_text with a clearly marked placeholder text starting with '[Bloque nuevo solicitado - editar]'.\n"
        + "- When the user says 'after section X', 'despues de X', 'luego de X' but X is not a literal substring of the document, fall back to append_text and flag the ambiguity in the placeholder.\n"
        + "- If the user asks to write, draft, create, or generate new text and the document is empty, use insert_text.\n"
        + "- If the user asks to change names, recipients, dates, words, or short phrases, prefer replace_text with concrete replacements.\n"
        + "- If the user asks to complete placeholders or missing fields with concrete data, use replace_text and replace exactly the placeholders present in document_context.placeholders.\n"
        + "- Do not replace placeholders if the user did not provide the concrete data to fill in.\n"
        + "- If the user asks to fix, modify, change, adapt, transform, or rewrite existing text, never use insert_text or append_text.\n"
        + "- If there is no selection and the user explicitly asks to add at the end, use append_text.\n"
        + "- For replace_document, return the complete final document, not just the changed fragment.\n"
        + "- For replace_text, the find field must match exactly the visible text in document_context.selection, document_context.text, document_context.text_tail, or document_context.placeholders[].text.\n"
        + "- If the text to replace does not appear in the available context, do not invent a find value; use replace_document only if you can return the complete final document, or explain that the fragment needs to be selected.\n"
        + "- The text field must contain only the final text to be inserted in the document.\n"
        + "- Do not include instructions, suggestions, format lists, recommended fonts, margins, line spacing, or notes about LibreOffice inside the text field.\n"
        + "- If the user requests a modern or attractive style, use blocks for titles/sections and style/page_style for real formatting.\n"
        + "- Preserve the language, tone, and proper names unless told otherwise.",
        "Briefly explain and return a single JSON in ```json. Allowed contracts:\n"
        + WRITER_ACTION_SCHEMA + "\n"
        + '{"action":"replace_text","summary":"...","replacements":[{"find":"My dear:","replace":"Laura:","match_case":true}]}\n'
        + '{"action":"replace_document","summary":"...","text":"complete final document","style":{"font_size":12}}\n'
        + '{"action":"insert_text","summary":"...","style":{"font_size":12,"font_name":"Liberation Sans","line_spacing":1.15},"blocks":[{"text":"Title","style":{"paragraph_style":"Heading 1","font_size":18,"bold":true}},{"text":"Paragraph text","style":{"paragraph_style":"Text Body","font_size":12}}]}\n'
        + '{"action":"append_text","text":"text at the end","summary":"...","style":{"font_size":12,"align":"justify"}}\n'
        + '{"action":"append_text","text":"[Clarification needed: indique que seccion modificar]","summary":"..."}\n',
        'Request: "write a simple letter with modern style"\n```json\n{"action":"insert_text","summary":"Inserts a modern letter","page_style":{"left_margin":2500,"right_margin":2500,"top_margin":2200,"bottom_margin":2200},"style":{"font_name":"Liberation Sans","font_size":12,"line_spacing":1.15,"space_after":180},"blocks":[{"text":"[Your name]\\n[City] | [email]","style":{"font_size":11,"font_color":"#555555"}},{"text":"Subject: [letter topic]","style":{"paragraph_style":"Heading 2","font_size":14,"bold":true,"font_color":"#1F4E79"}},{"text":"Hello, [Name]:","style":{"font_size":12}},{"text":"I am writing to you...","style":{"font_size":12,"align":"justify"}},{"text":"Best regards,\\n[Your name]","style":{"font_size":12}}]}\n```\n\n'
        'Request: "below this paragraph add a thank-you section" (no selection, doc has content)\n```json\n{"action":"append_text","text":"[Bloque nuevo solicitado - editar]\\n\\nAgradecemos su atencion y quedamos a su disposicion.","summary":"Agrega una seccion al final","style":{"align":"justify"}}\n```\n\n'
        'Request: "debajo de este hacer una nuevo" (no selection)\n```json\n{"action":"append_text","text":"[Bloque nuevo solicitado - editar con tu contenido]","summary":"Agrega un bloque nuevo al final (placeholder editable)"}\n```\n\n'
        'Request with selection: "make it more formal"\n```json\n{"action":"replace_selection","text":"Dear ...","summary":"Rewrites selection in formal tone"}\n```\n\n'
        'Request without selection on existing document: "address it to Laura"\n```json\n{"action":"replace_text","summary":"Changes the letter greeting","replacements":[{"find":"My dear:","replace":"Laura:","match_case":true}]}\n```\n\n'
        'Request: "complete [Name] with Laura"\n```json\n{"action":"replace_text","summary":"Completes the pending name","replacements":[{"find":"[Name]","replace":"Laura","match_case":true}]}\n```\n\n'
        'Request: "change the date to 2026-12-31"\n```json\n{"action":"replace_text","summary":"Updates the date","replacements":[{"find":"[Date]","replace":"2026-12-31","match_case":false}]}\n```\n\n'
        'Ambiguous request: "arregla esto" (no selection, no clear target)\n```json\n{"action":"append_text","text":"[Clarification needed: que parte del documento queres arreglar? Selecciona el texto o describe que seccion modificar.]","summary":"Necesito mas informacion"}\n```\n\n'
        'Full request without selection: "rewrite the whole letter more formally"\n```json\n{"action":"replace_document","text":"complete final document...","summary":"Rewrites the whole letter in formal tone"}\n```',
    )


def writer_expand(user_prompt, ctx):
    return writer_rewrite("Expand and develop the text with more detail. " + user_prompt, ctx)


def writer_summarize(ctx):
    return _block(
        "You are an editor and summarizer for LibreOffice Writer.",
        "Summarize the selected text or the document context.",
        ctx,
        COMMON_RULES + "\n- Do not return JSON.\n- Keep main ideas, tone, and proper names.",
        "Return natural text with a summary and, if useful, key points.",
    )


def writer_bullet_summary(ctx):
    return _block(
        "You are an editor and summarizer for LibreOffice Writer.",
        "Summarize the selected text or the document context as key points.",
        ctx,
        COMMON_RULES + "\n- Do not return JSON.\n- Do not modify the document.\n- Return only key points in bullet format.\n- Use dashes (-) or asterisks (*) for each point.\n- Each point must be a concise idea (max 15 words).\n- Group related points if appropriate.\n- Keep the original language and proper names.",
        "Return a list of key points in bullet points. No additional narrative text.",
    )


def writer_review(user_prompt, ctx):
    return _block(
        "You are a professional reviewer for LibreOffice Writer.",
        "Review the document or selection without modifying anything.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Do not return JSON.\n- Do not propose an actionable change.\n- Do not say you will modify or have already modified.\n- Evaluate clarity, spelling, grammar, tone, structure, placeholders, inconsistencies, and missing data.\n- If the user later asks for changes, they can do so in another message.",
        "Return natural text with brief sections: Summary, Problems, Suggested Improvements, Risks or Doubts, Recommended Next Step.",
    )


def writer_comments(user_prompt, ctx):
    return _block(
        "You are a professional reviewer for LibreOffice Writer.",
        "Insert review comments/annotations in the document without changing the text.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Do not rewrite the document.\n- Do not use replace_document or replace_selection.\n- Use action insert_comment.\n- If there is a selection, you may leave marker_text empty to anchor the comment to the selection/cursor.\n- If there is no selection, use marker_text with exact text present in document_context.text, document_context.text_tail, or document_context.selection.\n- Comments must be brief, useful, and actionable.\n- Maximum 8 comments unless the user asks for more.\n- If you cannot find an exact marker, create one general comment with empty marker_text.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_COMMENT_SCHEMA,
        'Request: "add review comments"\n```json\n{"action":"insert_comment","summary":"Adds review comments","comments":[{"marker_text":"exact text from the document","comment":"This point should be clarified so the recipient understands the objective.","author":"Libre Asist"}]}\n```',
    )


def writer_placeholder_review(user_prompt, ctx):
    return _block(
        "You are a Writer document auditor specialized in placeholders, missing data, and inconsistencies.",
        "Detect incomplete fields, placeholders, and data the user must fill in without modifying the document.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- Do not return JSON.\n- Do not modify or propose actionable changes.\n- Use document_context.placeholders if it exists.\n- Detect placeholders like [Name], [Date], <Company>, {TAX_ID}, generic text, and pending fields.\n- Indicate priority: critical if it prevents using/sending the document, medium if it should be completed, low if optional.\n- If there are no obvious placeholders, say so clearly.",
        "Return natural text with sections: Pending Fields, Inconsistencies, Recommendations, Next Step.",
    )


def writer_format(user_prompt, ctx):
    has_selection = bool((ctx or {}).get("has_selection"))
    lower = user_prompt.lower()
    titles_or_areas = any(word in lower for word in ("titulo", "título", "titulos", "títulos", "areas", "áreas", "important", "secciones", "encabezad", "subrayad"))
    wants_bullets = any(word in lower for word in ("viñeta", "vineta", "vinetas", "bullets", "con vinetas", "con bullets", "aplicar vinetas", "aplicar bullets", "dar vinetas", "dar bullets"))
    action_contract = (
        '{"action":"format_document","summary":"Apply bold to titles and important areas of the document",'
        '"bold":true,"font_name":"Liberation Sans","font_size":12,'
        '"font_color":"#222222","align":"justify","line_spacing":1.15,'
        '"page_style":{"left_margin":2500,"right_margin":2500,"top_margin":2200,"bottom_margin":2200}}'
        if titles_or_areas else
        '{"action":"format_document","summary":"Apply modern formatting to the document",'
        '"bold":true,"font_name":"Liberation Sans","font_size":12,'
        '"font_color":"#222222","align":"justify","line_spacing":1.15,'
        '"page_style":{"left_margin":2500,"right_margin":2500,"top_margin":2200,"bottom_margin":2200}}'
        if not has_selection else
        '{"action":"format_selection","bold":true,"italic":false,"font_size":12,'
        '"font_name":"Liberation Sans","font_color":"#111111","background":"#FFFFFF",'
        '"align":"justify","line_spacing":1.15,"space_before":0,"space_after":180,'
        '"paragraph_style":"Text Body","page_style":{"left_margin":2500,"right_margin":2500},'
        '"summary":"..."}'
    )
    selection_rule = (
        "- The user asked to format titles or important areas: use format_document to apply to the full document."
        if titles_or_areas else
        "- No selection: use format_document to apply formatting to the full document. No selection is needed to format."
        if not has_selection else
        "- There is a selection: use format_selection to apply formatting to the selected text."
    )
    return _block(
        "You are a formatting assistant for LibreOffice Writer.",
        "Convert the request into applicable formatting.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + WRITER_STYLE_RULES + "\n" + selection_rule + "\n- format_document does not change the text; it only applies formatting to existing paragraphs. No selection is required.\n- format_selection requires that text is selected.\n- If there is no selection and the user requests formatting, bold, color, bullets, or any style change, always use format_document.\n- structure_mode can be professional, letter, report, or minimal.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + action_contract,
    )


def writer_lists(user_prompt, ctx):
    has_selection = bool((ctx or {}).get("has_selection"))
    selection_rule = "- There is a selection: apply the list to the selected paragraphs." if has_selection else "- No selection: you cannot apply a list without a selection."
    return _block(
        "You are a list specialist for LibreOffice Writer.",
        "Convert paragraphs into a list according to the request.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + WRITER_STYLE_RULES + "\n" + selection_rule + "\n- list_style can be bullet, number, or outline.\n- level ranges from 0 to 9.\n- start_at is the starting number for numbered lists (default 1).\n- Do not change the text; only the paragraph style.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_LIST_SCHEMA,
        'Request: "convert to numbered list"\n```json\n{"action":"apply_list","summary":"Applies numbered list to selection","list_style":"number","level":0,"start_at":1}\n```\n\n'
        'Request: "make a list with dashes"\n```json\n{"action":"apply_list","summary":"Applies bullet list","list_style":"bullet","level":0}\n```',
    )


def writer_hyperlink(user_prompt, ctx):
    has_selection = bool((ctx or {}).get("has_selection"))
    selection_rule = "- There is a selection: use apply_to_selection=true to convert the selection into a link." if has_selection else "- No selection: insert the link at the cursor."
    return _block(
        "You are a hyperlink specialist for LibreOffice Writer.",
        "Insert or convert to a hyperlink according to the request.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n" + selection_rule + "\n- The URL must be complete (http://, https://, mailto:).\n- If the request specifies visible text, use it in the text field.\n- If apply_to_selection is true, use the selection as the visible text.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_HYPERLINK_SCHEMA,
        'Request: "link this word to https://example.com"\n```json\n{"action":"insert_hyperlink","summary":"Converts selection to hyperlink","url":"https://example.com","apply_to_selection":true}\n```\n\n'
        'Request: "insert link at the end"\n```json\n{"action":"insert_hyperlink","summary":"Inserts link at cursor","text":"Official site","url":"https://example.com"}\n```',
    )


def writer_table(user_prompt, ctx):
    return _block(
        "You are a table designer for LibreOffice Writer.",
        "Create or edit a table according to the request.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- rows and cols define the table size.\n- headers is a list of texts for the first row.\n- rows_data is a list of rows, each a list of values.\n- style allows header_background (hex color), header_bold, and column_widths.\n- Maximum size: 50 rows x 20 columns.\n- Do not invent real data; use editable examples.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_TABLE_SCHEMA,
        'Request: "create a 3-column table with Product, Price, and Stock"\n```json\n{"action":"insert_table","summary":"Inserts table with headers","rows":4,"cols":3,"headers":["Product","Price","Stock"],"rows_data":[["Item 1","100","5"],["Item 2","200","3"]],"style":{"header_background":"#D9EAF7","header_bold":true}}\n```',
    )


def writer_header_footer(user_prompt, ctx):
    return _block(
        "You are a header and footer specialist for LibreOffice Writer.",
        "Configure header and/or footer according to the request.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + WRITER_STYLE_RULES + "\n- header and footer are objects with text, alignment, and page_numbers.\n- alignment can be left, center, or right.\n- page_numbers inserts the automatic page number.\n- first_page_different enables a different header/footer on the first page.\n- Use {{date}} in the text to insert a date field.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_HEADER_FOOTER_SCHEMA,
        'Request: "add centered header with the title"\n```json\n{"action":"set_header_footer","summary":"Sets centered header","header":{"text":"My Document","alignment":"center"}}\n```\n\n'
        'Request: "number pages in the footer"\n```json\n{"action":"set_header_footer","summary":"Adds page numbering","footer":{"text":"Page ","alignment":"center","page_numbers":true}}\n```',
    )


def writer_footnote(user_prompt, ctx):
    return _block(
        "You are a footnote specialist for LibreOffice Writer.",
        "Insert a footnote or endnote according to the request.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- marker_text is the text marking where the note goes.\n- note_text is the content of the note.\n- If marker_text is not found in the document, warn the user.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_FOOTNOTE_SCHEMA,
        'Request: "add footnote on word X"\n```json\n{"action":"insert_footnote","summary":"Inserts footnote","marker_text":"X","note_text":"Explanation of X"}\n```',
    )


def writer_spellcheck(ctx):
    return _block(
        "You are a professional spell-checker for LibreOffice Writer.",
        "Review the spelling of the document or selection without modifying anything.\n\nThere is no user request; use the document context.",
        ctx,
        COMMON_RULES + "\n- Do not return JSON.\n- Do not propose an actionable change.\n- Do not say you will modify.\n- If there are no errors, confirm the text is well-written.\n- For each error, show the word, context, and dictionary suggestions.",
        "Return natural text with sections: Errors Found (if any) and Overall Status.",
    )


def writer_export(user_prompt, ctx):
    return _block(
        "You are a document export specialist for LibreOffice Writer.",
        "Export the active document to the indicated format.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- format can be pdf, docx, odt, or txt.\n- If path is empty, a save dialog will open.\n- If path has a value, it exports directly to that path.\n- Does not modify the document.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_EXPORT_SCHEMA,
        'Request: "export to PDF"\n```json\n{"action":"export_document","summary":"Exports document to PDF","format":"pdf","path":""}\n```\n\n'
        'Request: "save as DOCX to /tmp/my_doc.docx"\n```json\n{"action":"export_document","summary":"Saves as DOCX","format":"docx","path":"/tmp/my_doc.docx"}\n```',
    )


WRITER_MARKDOWN_SCHEMA = (
    '{"action":"insert_markdown","summary":"Insert Markdown content in Writer",'
    '"markdown_text":"# Title\\n\\nDocument text...",'
    '"mode":"insert_text"}'
)


def writer_markdown_import(user_prompt, ctx):
    return _block(
        "You are a Markdown conversion specialist for LibreOffice Writer.",
        "Convert the provided Markdown text into Writer content.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- markdown_text contains the Markdown to convert.\n- mode can be insert_text (at cursor), replace_document (replaces all), or append_text (at the end).\n- The parser supports: # ## ### for titles, **bold**, *italic*, `code`, [text](url), lists with - or numbers.\n- Do not invent content; use exactly the text from the given Markdown.\n- If the Markdown is empty, do not generate content.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_MARKDOWN_SCHEMA,
        'Request: "convert this Markdown to Writer"\n```json\n{"action":"insert_markdown","summary":"Inserts Markdown as document","markdown_text":"# My Report\\n\\n## Introduction\\n\\nThis is the first paragraph.","mode":"replace_document"}\n```',
    )


def writer_markdown_export(ctx):
    return _block(
        "You are a Markdown conversion specialist for LibreOffice Writer.",
        "Convert the active Writer document to Markdown format.\n\nThere is no user request; use the document context.",
        ctx,
        COMMON_RULES + "\n- Do not return JSON.\n- Do not modify the document.\n- Return the document text formatted as Markdown.\n- Use # for titles (Heading 1), ## for subtitles (Heading 2), ### for subsubtitles.\n- Use - for list items.\n- Preserve each paragraph's text as-is.",
        "Return the document content in Markdown format.",
    )


WRITER_TRACK_SCHEMA = (
    '{"action":"track_changes","summary":"Enable change tracking",'
    '"enabled":true}'
)

WRITER_REDLINES_LIST_SCHEMA = (
    '{"action":"accept_all_redlines","summary":"Accept all changes"}\n'
    '{"action":"reject_all_redlines","summary":"Reject all changes"}'
)


def writer_track_changes(user_prompt, ctx):
    lower = user_prompt.lower()
    if any(word in lower for word in ("activar", "encender", "activar control", "habilitar control", "empezar a rastrear")):
        return _block(
            "You are a change-tracking specialist for LibreOffice Writer.",
            "Enable change tracking to record edits.\n\nRequest: " + user_prompt,
            ctx,
            COMMON_RULES + "\n- enabled=true activates change tracking.\n- enabled=false deactivates it.\n- Only activate; do not accept or reject changes yet.",
            "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_TRACK_SCHEMA,
            'Request: "enable change tracking"\n```json\n{"action":"track_changes","summary":"Enables change tracking","enabled":true}\n```\n\n'
            'Request: "disable change tracking"\n```json\n{"action":"track_changes","summary":"Disables change tracking","enabled":false}\n```',
        )
    if any(word in lower for word in ("desactivar", "apagar", "desactivar control", "deshabilitar control", "dejar de rastrear")):
        return _block(
            "You are a change-tracking specialist for LibreOffice Writer.",
            "Disable change tracking.\n\nRequest: " + user_prompt,
            ctx,
            COMMON_RULES + "\n- enabled=false deactivates change tracking.\n- Only deactivate.",
            "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_TRACK_SCHEMA,
            'Request: "disable change tracking"\n```json\n{"action":"track_changes","summary":"Disables change tracking","enabled":false}\n```',
        )
    if any(word in lower for word in ("aceptar todos", "aceptar cambios", "aplicar todos los cambios", "confirmar todos")):
        return _block(
            "You are a change-tracking specialist for LibreOffice Writer.",
            "Accept all pending changes in the document.\n\nRequest: " + user_prompt,
            ctx,
            COMMON_RULES + "\n- Accepts all pending redlines (changes).\n- Do not reject them.\n- Confirm the number of changes affected.",
            "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_REDLINES_LIST_SCHEMA,
            'Request: "accept all changes"\n```json\n{"action":"accept_all_redlines","summary":"Accepts all pending changes"}\n```',
        )
    if any(word in lower for word in ("rechazar todos", "rechazar cambios", "cancelar todos los cambios", "deshacer todos")):
        return _block(
            "You are a change-tracking specialist for LibreOffice Writer.",
            "Reject all pending changes in the document.\n\nRequest: " + user_prompt,
            ctx,
            COMMON_RULES + "\n- Rejects all pending redlines (changes).\n- Do not accept them.\n- Confirm the number of changes affected.",
            "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_REDLINES_LIST_SCHEMA,
            'Request: "reject all changes"\n```json\n{"action":"reject_all_redlines","summary":"Rejects all pending changes"}\n```',
        )
    return _block(
        "You are a change-tracking specialist for LibreOffice Writer.",
        "Manage the document's change tracking.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + "\n- If the user wants to activate or deactivate change tracking, use track_changes.\n- If they want to accept all changes, use accept_all_redlines.\n- If they want to reject them, use reject_all_redlines.\n- If they only ask about the current status, respond without JSON.",
        "Briefly explain and return a single JSON in ```json with contract:\n" + WRITER_TRACK_SCHEMA + "\n" + WRITER_REDLINES_LIST_SCHEMA,
    )


def writer_tone(user_prompt, ctx, tone):
    tones = {
        "formal": "formal, professional, and respectful",
        "informal": "informal and friendly",
        "persuasive": "persuasive and compelling",
        "technical": "technical and precise",
        "friendly": "friendly and warm",
        "academic": "academic and rigorous",
        "casual": "casual and relaxed",
        "tecnico": "technical and precise",
        "amigable": "friendly and warm",
        "academico": "academic and rigorous",
        "persuasivo": "persuasive and compelling",
    }
    tone_desc = tones.get(tone, tone)
    return _block(
        "You are a professional editor for LibreOffice Writer.",
        "Rewrite the selected text or the full document in " + tone_desc + " tone.\n\nRequest: " + user_prompt,
        ctx,
        COMMON_RULES + WRITER_STYLE_RULES + "\n- Preserve the content and main ideas.\n- Adapt the tone and register as requested.\n- If there is a selection use replace_selection; otherwise use replace_document.",
        "Briefly explain and return a single JSON in ```json. Allowed contracts:\n"
        + WRITER_ACTION_SCHEMA + "\n"
        + '{"action":"replace_document","summary":"...","text":"complete final document in ' + tone + ' tone"}',
    )


def writer_preview(user_prompt, ctx):
    lower = user_prompt.lower()
    if any(word in lower for word in (
        "completa placeholder", "completar placeholder", "reemplaza placeholder", "reemplazar placeholder",
        "completa campos", "completar campos", "datos faltantes",
        "complete placeholder", "fill placeholder", "fill placeholders", "missing data", "missing fields",
    )):
        return writer_rewrite(user_prompt, ctx)
    if any(word in lower for word in (
        "tabla", "tablas", "crear tabla", "agregar tabla", "insertar tabla", "nueva tabla",
        "table", "tables", "create table", "add table", "insert table", "new table",
    )):
        return writer_table(user_prompt, ctx)
    if any(word in lower for word in (
        "comentario", "comentarios", "anotacion", "anotación", "anotaciones",
        "nota de revision", "nota de revisión", "comentar", "comentá", "comenta",
        "comment", "comments", "annotation", "annotations", "review note", "review notes", "annotate",
    )):
        return writer_comments(user_prompt, ctx)
    if any(word in lower for word in (
        "encabezado", "encabezados", "pie de pagina", "pie de página", "pies de pagina", "pies de página",
        "numerar paginas", "numerar páginas", "numero de pagina", "número de página",
        "header", "headers", "footer", "footers",
        "page number", "page numbers", "number pages",
    )):
        return writer_header_footer(user_prompt, ctx)
    if any(word in lower for word in (
        "puntos clave", "puntos principales", "resumen en bullets", "puntos del documento",
        "dame los puntos", "resumir en bullets", "resumen bullet",
        "key points", "main points", "bullet summary", "document points",
        "give me the points", "summarize in bullets", "bullet recap",
    )):
        return writer_bullet_summary(ctx)
    if any(word in lower for word in (
        "nota al pie", "nota al final", "footnote", "footnotes", "endnote", "endnotes",
    )):
        return writer_footnote(user_prompt, ctx)
    if any(word in lower for word in (
        "hipervinculo", "hipervínculo", "hipervinculos", "hipervínculos",
        "vincular", "enlace", "enlaces",
        "link", "links", "hyperlink", "hyperlinks", "anchor",
        "insertar link", "insert link", "convertir en link", "convert to link",
    )):
        return writer_hyperlink(user_prompt, ctx)
    if any(word in lower for word in (
        "exportar a pdf", "guardar como docx", "exportar a docx", "exportar a odt",
        "convertir a pdf", "convertir a docx",
        "export to pdf", "save as docx", "export to docx", "export to odt",
        "convert to pdf", "convert to docx",
    )):
        return writer_export(user_prompt, ctx)
    if any(word in lower for word in (
        "control de cambios", "track changes", "seguimiento de cambios", "rastrear cambios",
        "registrar cambios", "activar control", "desactivar control",
        "aceptar todos los cambios", "rechazar todos los cambios",
        "aceptar cambios", "rechazar cambios", "cambios pendientes",
    )):
        return writer_track_changes(user_prompt, ctx)
    if any(word in lower for word in (
        "convertir a markdown", "convertir a md", "exportar a markdown", "exportar a md",
        "mostrar como markdown", "mostrar como md", "a markdown",
        "convert to markdown", "export to markdown", "show as markdown",
    )):
        return writer_markdown_export(ctx)
    if any(word in lower for word in (
        "convertir markdown a writer", "convertir md a writer", "importar markdown", "importar md",
        "pegar markdown", "insertar markdown", "markdown a writer",
        "convert markdown to writer", "import markdown", "paste markdown", "insert markdown",
    )):
        return writer_markdown_import(user_prompt, ctx)
    if any(word in lower for word in (
        "lista", "listas", "viñeta", "viñetas", "vineta", "vinetas", "numerar",
        "convertir en lista", "hacer lista", "convertir en bullets", "hacer bullets", "crear bullets",
        "list", "lists", "bullet", "bullets", "number",
        "convert to list", "make list", "convert to bullets", "make bullets", "create bullets",
    )):
        return writer_lists(user_prompt, ctx)
    if any(word in lower for word in (
        "negrita", "cursiva", "tamano", "tamaño", "formato", "margen", "margenes", "márgenes",
        "alinear", "justificar", "centrar", "interlineado", "fuente", "color", "fondo",
        "titulo", "título", "viñeta", "vineta", "vinetas", "bullets",
        "bold", "italic", "size", "format", "margin", "margins", "align", "justify", "center",
        "line spacing", "font", "background", "title",
    )):
        return writer_format(user_prompt, ctx)
    if any(word in lower for word in (
        "tono", "formal", "informal", "persuasivo", "tecnico", "amigable", "academico", "casual",
        "tone", "persuasive", "technical", "friendly", "academic",
    )):
        for tone in ("formal", "informal", "persuasive", "technical", "friendly", "academic", "casual",
                     "persuasivo", "tecnico", "amigable", "academico"):
            if tone in lower:
                return writer_tone(user_prompt, ctx, tone)
    if any(word in lower for word in (
        "resum", "sintetiz", "summar", "synthesiz",
    )):
        return writer_summarize(ctx)
    if any(word in lower for word in (
        "amplia", "desarroll", "expand", "elaborate", "develop",
    )):
        return writer_expand(user_prompt, ctx)
    if any(word in lower for word in (
        "carta", "email", "correo", "escrib", "escribí", "redact", "redactá",
        "crear", "crea", "creá", "generar", "genera", "generá",
        "insert", "insertá", "agregar", "agrega", "agregá",
        "letter", "mail", "write", "draft", "compose", "create", "make", "build",
        "generate", "produce",
    )):
        return writer_rewrite(user_prompt, ctx)
    return writer_rewrite(user_prompt, ctx)
