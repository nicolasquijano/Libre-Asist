# CACHE_BUSTER: 1781326001
"""Floating Calc assistant styled as a ChatGPT-like spreadsheet sidebar."""

import os
import sys
import threading

try:
    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _THIS_DIR = os.path.dirname(os.path.abspath((lambda: 0).__code__.co_filename))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import uno
import unohelper
from com.sun.star.awt import XActionListener, XItemListener, XKeyListener

try:
    from com.sun.star.awt.PosSize import POSSIZE as POS_SIZE
except ImportError:
    POS_SIZE = 15

try:
    from com.sun.star.awt.Key import RETURN as KEY_RETURN
except ImportError:
    KEY_RETURN = 1281

import actions
import calc_ops
import config
import prompts
import skills
import writer_ops
from ai_client import AIClient, AIError
from i18n import _


SIZES = {
    "compact": (620, 900),
    "normal": (720, 1040),
    "large": (820, 1180),
}


def _ctx():
    return uno.getComponentContext()


def _smgr():
    return _ctx().getServiceManager()


def _desktop():
    return _smgr().createInstanceWithContext("com.sun.star.frame.Desktop", _ctx())


def _toolkit():
    return _smgr().createInstanceWithContext("com.sun.star.awt.Toolkit", _ctx())


def _active_doc():
    return _desktop().getCurrentComponent()


def _is_calc(doc):
    return doc is not None and doc.supportsService("com.sun.star.sheet.SpreadsheetDocument")


def _is_writer(doc):
    return doc is not None and doc.supportsService("com.sun.star.text.TextDocument")


def _new(model, service):
    return model.createInstance(service)


def _set(ctrl, **props):
    for key, value in props.items():
        ctrl.setPropertyValue(key, value)
    return ctrl


def _add_button(model, name, label, default=False):
    ctrl = _new(model, "com.sun.star.awt.UnoControlButtonModel")
    _set(ctrl, Name=name, Label=label, DefaultButton=default, Enabled=True)
    model.insertByName(name, ctrl)


def _add_label(model, name, label):
    ctrl = _new(model, "com.sun.star.awt.UnoControlFixedTextModel")
    _set(ctrl, Name=name, Label=label)
    model.insertByName(name, ctrl)


def _add_text(model, name, multi=False, readonly=False, echo_char=None):
    ctrl = _new(model, "com.sun.star.awt.UnoControlEditModel")
    _set(ctrl, Name=name, MultiLine=multi, VScroll=multi, HScroll=False, ReadOnly=readonly)
    if echo_char:
        ctrl.setPropertyValue("EchoChar", ord(echo_char))
    model.insertByName(name, ctrl)


def _add_listbox(model, name, items, selected_index=0):
    ctrl = _new(model, "com.sun.star.awt.UnoControlListBoxModel")
    _set(ctrl, Name=name, DefaultSelection=selected_index)
    uno.invoke(ctrl, "setPropertyValue", ("StringItemList", uno.Any("[]string", tuple(items))))
    model.insertByName(name, ctrl)


def _add_checkbox(model, name, label, checked=False):
    ctrl = _new(model, "com.sun.star.awt.UnoControlCheckBoxModel")
    _set(ctrl, Name=name, Label=label, State=(1 if checked else 0))
    model.insertByName(name, ctrl)


def _build_panel_dialog():
    model = _smgr().createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", _ctx())
    _set(model, Title=_("panel.title"), Closeable=True, Moveable=True, Sizeable=True, Width=720, Height=1040)

    for name, label in (
        ("btnConfig", _("btn.config")),
        ("btnDock", _("btn.dock")),
        ("btnCompact", _("btn.compact")),
        ("btnNormal", _("btn.normal")),
        ("btnLarge", _("btn.large")),
        ("btnSend", _("btn.send")),
        ("btnApply", _("btn.apply")),
        ("btnApplySession", _("btn.apply.session")),
        ("btnApplyAlways", _("btn.apply.always")),
    ):
        _add_button(model, name, label, default=(name == "btnSend"))

    for name in ("btnApply", "btnApplySession", "btnApplyAlways"):
        model.getByName(name).setPropertyValue("Enabled", False)

    _add_label(model, "lblContext", _("lbl.context.default"))
    _add_label(model, "lblStatus", _("lbl.status.ready"))
    _add_text(model, "txtChat", multi=True, readonly=True)
    _add_text(model, "txtPrompt", multi=True, readonly=False)

    dialog = _smgr().createInstanceWithContext("com.sun.star.awt.UnoControlDialog", _ctx())
    dialog.setModel(model)
    dialog.setPosSize(0, 0, 720, 1040, POS_SIZE)
    dialog.createPeer(_toolkit(), None)
    return dialog


def _build_config_dialog():
    model = _smgr().createInstanceWithContext("com.sun.star.awt.UnoControlDialogModel", _ctx())
    _set(model, Title=_("panel.title.config"), Closeable=True, Moveable=True, Sizeable=True, Width=720, Height=900)

    _add_label(model, "lblProvider", _("lbl.provider"))
    _add_text(model, "txtProvider")
    _add_label(model, "lblUrl", _("lbl.url"))
    _add_text(model, "txtUrl")
    _add_label(model, "lblModel", _("lbl.model"))
    _add_text(model, "txtModel")
    _add_label(model, "lblKey", _("lbl.key"))
    _add_text(model, "txtKey", echo_char="*")
    _add_label(model, "lblSysPreset", _("lbl.sys_preset"))
    _add_text(model, "txtSystemPreset")
    _add_label(model, "lblSys", _("lbl.sys_prompt"))
    _add_text(model, "txtSystem", multi=True)
    _add_checkbox(model, "chkWebSearch", _("chk.web_search"), checked=False)
    _add_button(model, "btnSave", _("btn.save"), default=True)
    _add_button(model, "btnCancel", _("btn.cancel"))

    dialog = _smgr().createInstanceWithContext("com.sun.star.awt.UnoControlDialog", _ctx())
    dialog.setModel(model)
    dialog.setPosSize(0, 0, 720, 900, POS_SIZE)
    dialog.createPeer(_toolkit(), None)
    return dialog


class PanelController:
    def __init__(self):
        self.dialog = None
        self.config_dialog = None
        self.cfg = config.load()
        self.chat = []
        self.pending_action = None
        self.last_context = None
        self.current_request = ""
        self.undo_stack = []
        self.action_history = []
        self.last_suggestions_key = ""
        self.busy = False
        self.auto_apply_session = []
        self.auto_apply_persistent = config.load_auto_apply()

    def show(self):
        if self.dialog is not None:
            try:
                self.dialog.setVisible(True)
                self.dialog.toFront()
                return
            except Exception:
                self.dialog = None
        self.dialog = _build_panel_dialog()
        self._wire_events()
        self._set_size("normal")
        self.dialog.setVisible(True)
        self.add_assistant(_("greeting"))
        self._try_initial_context_suggestions()

    def _wire_events(self):
        listeners = {
            "btnConfig": ConfigListener,
            "btnDock": DockListener,
            "btnCompact": CompactListener,
            "btnNormal": NormalListener,
            "btnLarge": LargeListener,
            "btnSend": SendListener,
            "btnApply": ApplyListener,
            "btnApplySession": ApplySessionListener,
            "btnApplyAlways": ApplyAlwaysListener,
        }
        for name, cls in listeners.items():
            self.dialog.getControl(name).addActionListener(cls(self))
        self.dialog.getControl("txtPrompt").addKeyListener(PromptKeyListener(self))

    def _pos(self, name, x, y, w, h):
        try:
            self.dialog.getControl(name).setPosSize(x, y, w, h, POS_SIZE)
        except Exception:
            pass

    def _set_size(self, name):
        width, height = SIZES[name]
        try:
            pos = self.dialog.getPosSize()
            self.dialog.setPosSize(pos.X, pos.Y, width, height, POS_SIZE)
        except Exception:
            pass
        self._layout(width, height)

    def _layout(self, width, height):
        m = 14
        gap = 10
        full = width - (m * 2)
        y = 14

        size_w = 42
        self._pos("btnConfig", m, y, 90, 38)
        self._pos("btnDock", m + 102, y, 108, 38)
        self._pos("btnCompact", width - m - (size_w * 3) - (gap * 2), y, size_w, 30)
        self._pos("btnNormal", width - m - (size_w * 2) - gap, y, size_w, 30)
        self._pos("btnLarge", width - m - size_w, y, size_w, 30)
        y += 50

        self._pos("lblContext", m, y, full, 30)
        y += 34
        self._pos("lblStatus", m, y, full, 30)
        y += 38

        prompt_h = 150
        send_h = 44
        apply_h = 44
        chat_h = max(380, height - y - apply_h - prompt_h - send_h - (gap * 3) - 24)
        self._pos("txtChat", m, y, full, chat_h)
        y += chat_h + gap

        apply_total = full
        apply_btn = (apply_total - (gap * 2)) // 3
        self._pos("btnApply", m, y, apply_btn, apply_h)
        self._pos("btnApplySession", m + apply_btn + gap, y, apply_btn, apply_h)
        self._pos("btnApplyAlways", m + (apply_btn + gap) * 2, y, apply_btn, apply_h)
        y += apply_h + gap

        self._pos("txtPrompt", m, y, full, prompt_h)
        y += prompt_h + gap
        self._pos("btnSend", m, y, full, send_h)
        self._refresh_context_label()

    def dock_right(self):
        try:
            pos = self.dialog.getPosSize()
            self.dialog.setPosSize(1280 - pos.Width - 24, 60, pos.Width, pos.Height, POS_SIZE)
        except Exception:
            self.add_assistant(_("error.docked"))

    def _chat_text(self):
        return "\n\n".join(self.chat[-20:])

    def _set_chat_text(self):
        text = self._chat_text()
        chat = self.dialog.getControl("txtChat")
        chat.setText(text)
        try:
            selection = uno.createUnoStruct("com.sun.star.awt.Selection")
            selection.Min = len(text)
            selection.Max = len(text)
            chat.setSelection(selection)
        except Exception:
            try:
                chat.setFocus()
                chat.setSelection((len(text), len(text)))
            except Exception:
                pass

    def add_user(self, text):
        self.chat.append(_("chat.prefix.user", text.strip()))
        self._set_chat_text()

    def add_assistant(self, text):
        self.chat.append(_("chat.prefix.assistant", str(text).strip()))
        self._set_chat_text()

    def set_status(self, text):
        status = _("chat.prefix.assistant", str(text).strip())
        try:
            self.dialog.getControl("lblStatus").setText(str(text).strip())
        except Exception:
            pass
        if self.chat and self._is_status_message(self.chat[-1]):
            self.chat[-1] = status
        else:
            self.chat.append(status)
        self._set_chat_text()

    def clear_status(self):
        try:
            self.dialog.getControl("lblStatus").setText(_("lbl.status.ready"))
        except Exception:
            pass
        if self.chat and self._is_status_message(self.chat[-1]):
            self.chat.pop()
            self._set_chat_text()

    def _is_status_message(self, text):
        return text.startswith("Libre Asist:\n") and any(
            marker in text for marker in ("Trabajando", "Validando", "Aplicando")
        )

    def _run_background(self, status, target, *args):
        if self.busy:
            self.add_assistant(_("error.busy"))
            return
        self.busy = True
        self.set_status(status)

        def runner():
            try:
                target(*args)
            except AIError as e:
                self.clear_status()
                self.add_assistant(_("error.ai.prefix", str(e)))
            except Exception as e:
                self.clear_status()
                self.add_assistant(_("error.unexpected.prefix", str(e)))
            finally:
                self.busy = False

        thread = threading.Thread(target=runner)
        thread.daemon = True
        thread.start()

    def _prompt_text(self):
        return self.dialog.getControl("txtPrompt").getText().strip()

    def _clear_prompt(self):
        self.dialog.getControl("txtPrompt").setText("")

    def _active_supported_doc(self):
        doc = _active_doc()
        if not (_is_calc(doc) or _is_writer(doc)):
            self.add_assistant(_("error.no_doc"))
            return None
        return doc

    def _selection_context(self):
        doc = self._active_supported_doc()
        if doc is None:
            return None
        if _is_calc(doc):
            ctx = calc_ops.get_selection_context(doc)
            if ctx is not None:
                ctx["kind"] = "calc"
            else:
                # For Calc, we don't require selection - ctx will be None only if doc is invalid
                return None
        else:
            ctx = writer_ops.get_context(doc)
        if ctx is None:
            # For Writer, we still require selection or document content
            self.add_assistant(_("error.no_selection"))
            return None
        self.last_context = ctx
        self._refresh_context_label()
        self._maybe_show_context_suggestions(ctx)
        return ctx

    def _try_initial_context_suggestions(self):
        try:
            doc = _active_doc()
            if _is_calc(doc):
                ctx = calc_ops.get_selection_context(doc)
                if ctx is not None:
                    ctx["kind"] = "calc"
                    self.last_context = ctx
                    self._refresh_context_label()
                    self._maybe_show_context_suggestions(ctx)
            elif _is_writer(doc):
                ctx = writer_ops.get_context(doc)
                if ctx is not None:
                    self.last_context = ctx
                    self._refresh_context_label()
                    self._maybe_show_context_suggestions(ctx)
        except Exception:
            pass

    def _context_suggestions_key(self, ctx):
        if not ctx:
            return ""
        if ctx.get("kind") == "writer":
            return "writer:" + str(bool(ctx.get("has_selection"))) + ":" + str(bool(str(ctx.get("text", "")).strip()))
        return "calc:" + str(ctx.get("range", "")) + ":" + str(ctx.get("header_confidence", "")) + ":" + str(bool(ctx.get("formula_cells")))

    def _maybe_show_context_suggestions(self, ctx):
        key = self._context_suggestions_key(ctx)
        if not key or key == self.last_suggestions_key:
            return
        suggestions = self._context_suggestions(ctx)
        if not suggestions:
            return
        self.last_suggestions_key = key
        self.add_assistant(_("suggestions.header", "\n- ".join(suggestions[:3])))

    def _context_suggestions(self, ctx):
        if not ctx:
            return []
        if ctx.get("kind") == "writer":
            text = str(ctx.get("text", "") or "").strip()
            if ctx.get("has_selection"):
                return [
                    _("suggestions.writer.selection.review"),
                    _("suggestions.writer.selection.clarity"),
                    _("suggestions.writer.selection.format"),
                ]
            if not text:
                return [
                    _("suggestions.writer.empty.letter"),
                    _("suggestions.writer.empty.report"),
                    _("suggestions.writer.empty.email"),
                ]
            if ctx.get("placeholders"):
                return [
                    _("suggestions.writer.placeholder.detect"),
                    _("suggestions.writer.placeholder.fill"),
                    _("suggestions.writer.placeholder.review"),
                ]
            return [
                _("suggestions.writer.content.review"),
                _("suggestions.writer.content.improve"),
                _("suggestions.writer.content.format"),
            ]
        rows = int(ctx.get("rows_total", 0) or 0)
        cols = int(ctx.get("cols_total", 0) or 0)
        if rows <= 1 and cols <= 1:
            return [
                _("suggestions.calc.single.budget"),
                _("suggestions.calc.single.expense"),
                _("suggestions.calc.single.structure"),
            ]
        if ctx.get("formula_cells"):
            return [
                _("suggestions.calc.formulas.review"),
                _("suggestions.calc.formulas.risks"),
                _("suggestions.calc.formulas.format"),
            ]
        bank = ctx.get("bank_reconciliation", {})
        candidates = bank.get("candidate_columns", {}) if isinstance(bank, dict) else {}
        if candidates.get("amount") and (candidates.get("date") or candidates.get("description")):
            return [
                _("suggestions.calc.bank.reconcile"),
                _("suggestions.calc.bank.match"),
                _("suggestions.calc.bank.duplicates"),
            ]
        if ctx.get("header_confidence") in ("high", "medium"):
            return [
                _("suggestions.calc.headers.analyze"),
                _("suggestions.calc.headers.issues"),
                _("suggestions.calc.headers.format"),
            ]
        return [
            _("suggestions.calc.generic.analyze"),
            _("suggestions.calc.generic.clean"),
            _("suggestions.calc.generic.format"),
        ]

    def _refresh_context_label(self):
        try:
            ctx = self.last_context
            if ctx:
                if ctx.get("kind") == "writer":
                    text = _("context.writer.prefix") + (_("context.writer.selection") if ctx.get("has_selection") else _("context.writer.cursor"))
                    if ctx.get("truncated"):
                        text += _("context.writer.truncated")
                else:
                    text = _("context.calc.prefix") + ctx["sheet"] + "!" + ctx["range"]
                    if ctx.get("truncated"):
                        text += _("context.calc.truncated")
            else:
                text = _("lbl.context.default")
            self.dialog.getControl("lblContext").setText(text)
        except Exception:
            pass

    def _ask(self, prompt_text):
        client = AIClient(self.cfg)
        return client.ask(prompt_text)

    def do_send(self):
        text = self._prompt_text()
        if not text:
            self.add_assistant(_("error.no_prompt"))
            return
        self.add_user(text)
        self._clear_prompt()

        if self._is_confirmation(text):
            self._confirm_pending_action()
            return
        if self._is_cancellation(text):
            self._cancel_pending_action()
            return
        if self._is_undo_request(text):
            self._undo_last_change()
            return
        if self._is_history_request(text):
            self._show_action_history()
            return
        if self.pending_action:
            self.pending_action = None
            self.add_assistant(_("error.discarded"))

        ctx = self._selection_context()
        if ctx is None:
            return
        self._run_background(_("status.working"), self._do_send_work, text, ctx)

    def _do_send_work(self, text, ctx):
        self.current_request = text
        if self._looks_like_placeholder_review(text):
            reply = self._ask(skills.route("placeholder_review", text, ctx))
            self.clear_status()
            self.add_assistant(reply)
        elif self._looks_like_calc_readonly_analysis(text, ctx):
            reply = self._ask(self._calc_analysis_prompt(text, ctx))
            self.clear_status()
            self.add_assistant(reply)
        elif self._looks_like_review(text):
            reply = self._ask(skills.route("review", text, ctx))
            self.clear_status()
            self.add_assistant(reply)
        elif self._looks_like_action(text, ctx):
            if ctx.get("kind") == "writer" and self._has_selection_reference(text) and not ctx.get("has_selection"):
                self.clear_status()
                self.add_assistant(
                    _("error.no_selection_ref")
                )
                return
            prompt = self._augment_prompt_with_references(skills.route("preview", text, ctx), text, ctx)
            self._prepare_pending_action(prompt)
        else:
            reply = self._ask(self._chat_prompt(text, ctx))
            self.clear_status()
            self.add_assistant(reply)

    def _is_confirmation(self, text):
        normalized = text.strip().lower().replace("í", "i")
        confirmations = (
            "si", "ok", "dale", "aplicar", "confirmar", "confirmo", "hacelo", "ejecutar",
            "yes", "y", "yep", "yeah", "apply", "confirm", "go", "go ahead", "do it",
            "execute", "run", "proceed", "sure",
        )
        return (
            normalized in confirmations
            or normalized.startswith("si ")
            or normalized.startswith("dale ")
            or normalized.startswith("yes ")
            or normalized.startswith("go ahead")
        )

    def _is_cancellation(self, text):
        normalized = text.strip().lower()
        cancellations = (
            "no", "cancelar", "cancela", "descartar", "descarta", "olvidar", "olvidalo", "parar", "stop",
            "cancel", "discard", "drop", "skip", "abort", "nevermind", "never mind",
            "don't", "dont", "nope", "nah",
        )
        return normalized in cancellations

    def _is_undo_request(self, text):
        normalized = text.strip().lower()
        requests = (
            "deshacer", "undo", "revertir", "revertir ultimo cambio",
            "revertir último cambio", "deshacer ultimo cambio",
            "deshacer último cambio", "volver atras", "volver atrás",
            "revert", "undo last change", "revert last change",
            "roll back", "rollback", "undo that",
        )
        return normalized in requests

    def _is_history_request(self, text):
        normalized = text.strip().lower()
        requests = (
            "historial", "historial de acciones", "que hiciste",
            "qué hiciste", "ultimos cambios", "últimos cambios",
            "acciones", "ver historial",
            "history", "action history", "what did you do", "what have you done",
            "last changes", "recent changes", "show history", "show actions",
        )
        return normalized in requests

    def _looks_like_review(self, text):
        lower = text.lower()
        review_phrases = (
            "revisa", "revisá", "revision", "revisión", "analiza este documento",
            "analizá este documento", "que errores", "qué errores",
            "que problemas", "qué problemas", "que mejorarias", "qué mejorarías",
            "que deberia mejorar", "qué debería mejorar", "sugerencias",
            "evalua", "evaluá", "diagnostico", "diagnóstico", "sin modificar",
            "no modifiques", "solo revisa", "solo revisá",
            "review", "check", "analyze this document", "what errors",
            "what problems", "what would you improve", "suggestions",
            "evaluate", "diagnostic", "without modifying", "do not modify",
            "don't modify", "only review", "just review", "audit", "report issues",
            "find issues", "look for issues",
        )
        return any(phrase in lower for phrase in review_phrases)

    def _looks_like_placeholder_review(self, text):
        lower = text.lower()
        if any(word in lower for word in (
            "completa", "completar", "reemplaza", "reemplazar", "cambia", "cambiar",
            "complete", "fill", "fill in", "populate", "replace", "substitute",
            "change", "swap", "fix", "correct",
        )):
            return False
        phrases = (
            "placeholder", "placeholders", "campos faltantes", "datos faltantes",
            "campos pendientes", "datos pendientes", "que falta", "qué falta",
            "que datos faltan", "qué datos faltan", "faltan datos",
            "faltan campos", "campos incompletos", "datos incompletos",
            "detectar campos", "detecta campos", "revisar campos", "revisá campos",
            "missing fields", "missing data", "empty fields", "blank fields",
            "what is missing", "what's missing", "incomplete fields", "incomplete data",
            "detect fields", "detect placeholders", "review placeholders", "check placeholders",
        )
        return any(phrase in lower for phrase in phrases)

    def _looks_like_action(self, text, ctx):
        lower = text.lower()
        action_words = (
            "escrib", "escribí", "redact", "redactá", "crea", "creá", "crear", "genera", "generá", "generar", "insert", "insertá",
            "agrega", "agregá", "agregar", "corrige", "corregir", "modifica", "modificar",
            "reescrib", "cambia", "cambiar", "pon", "poner", "formatea", "formatear",
            "sumar", "suma", "calcular", "calcula", "total", "totales",
            "rellenar", "rellena", "rellená", "llenar", "llena", "llená", "completar", "completa", "completá",
            "limpiar", "pintar", "resaltar",
            "marca", "marcá", "marcar",
            "alinear", "justificar", "margen", "margenes", "márgenes", "interlineado",
            "fuente", "color", "titulo", "título", "estilo", "profesional",
            "moderno", "minimalista",
            "busca", "buscar", "detecta", "detectar", "duplicado", "duplicados",
            "faltante", "faltantes", "presupuesto", "inventario", "cronograma",
            "flujo de caja", "cashflow", "planilla", "dashboard", "kpi",
            "conciliar", "conciliacion", "conciliación", "banco", "bancaria",
            "bancario", "extracto", "movimientos bancarios", "libro banco",
            "tabla dinamica", "tabla dinámica", "tabla resumen", "reporte", "resumen por",
            "reporte de auditoria", "reporte de auditoría", "informe de auditoria",
            "informe de auditoría", "hoja de auditoria", "hoja de auditoría",
            "placeholder", "placeholders", "campos faltantes", "datos faltantes",
            "destinatario", "destinataria", "saludo", "apellido", "nombre", "email", "correo",
            "comentario", "comentarios", "anotacion", "anotación", "anotaciones", "comentar", "comentá",
            "se llame", "se llama", "sea ",
            "aleatorio", "aleatorios", "aleatoria", "aleatorias", "random", "mock", "fake",
            "ficticio", "ficticios", "ficticia", "ficticias", "inventado", "inventados", "sintetico", "sinteticos",
            "al azar",
            "datos de prueba", "datos falsos", "datos ficticios", "datos aleatorios",
            "datos mock", "datos fake", "datos random", "datos de ejemplo", "datos demo",
            "datos inventados", "datos sinteticos",
            "write", "draft", "compose", "create", "make", "build", "produce", "insert", "add",
            "fix", "correct", "repair", "modify", "edit", "rewrite", "replace", "substitute",
            "swap", "set", "put", "format", "style",
            "fill", "fill in", "populate", "complete", "clean", "clear", "paint", "highlight",
            "mark", "flag", "tag",
            "align", "justify", "margin", "line spacing",
            "font", "bold", "italic", "title", "professional", "modern", "minimalist",
            "sum", "average", "avg", "count", "calculate", "compute", "total", "subtotal",
            "search", "find", "detect", "duplicate", "duplicates",
            "missing", "budget", "inventory", "schedule", "timeline", "gantt",
            "cash flow", "spreadsheet", "sheet", "dashboard", "kpi",
            "reconcile", "reconciliation", "bank", "banking", "bank statement", "movements", "ledger",
            "pivot table", "summary table", "report", "report by", "summary by",
            "audit report", "audit sheet",
            "missing fields", "missing data",
            "recipient", "greeting", "surname", "first name", "email", "mail",
            "comment", "comments", "annotation", "annotations", "annotate",
            "be called", "is called", "should be",
            "fictional", "fictitious", "synthetic", "dummy",
            "test data", "sample data", "fake data", "mock data", "example data", "demo data",
        )
        question_words = (
            "explica", "explicar", "analiza", "analizar", "que ", "qué ", "como ", "cómo ", "?",
            "explain", "what", "how", "why", "tell me", "describe", "is it", "are there",
        )
        if any(word in lower for word in action_words):
            return True
        if (ctx or {}).get("kind") == "writer" and not any(word in lower for word in question_words):
            return True
        return False

    def _looks_like_writer_edit(self, text):
        lower = text.lower()
        edit_words = (
            "modifica", "modificar", "editar", "edita", "cambia", "cambiar",
            "corrige", "corregir", "reescrib", "reemplaza", "reemplazar",
            "dirigida", "dirigido", "para que sea", "que sea", "hace que",
            "haz que", "converti", "convertí", "transforma", "destinatario",
            "destinataria", "saludo", "se llame", "se llama",
            "modify", "edit", "change", "fix", "correct", "rewrite", "replace", "substitute",
            "addressed to", "to be", "so that", "make it", "convert", "transform",
            "recipient", "greeting", "be called", "is called",
        )
        return any(word in lower for word in edit_words)

    def _looks_like_writer_create(self, text):
        lower = text.lower()
        create_words = (
            "escrib", "escribí", "redact", "redactá", "crea", "creá", "crear", "genera", "generá", "generar",
            "hacer", "hacé", "armar", "armá",
            "carta", "email", "correo", "informe", "presentacion", "presentación",
            "texto nuevo", "nuevo bloque", "nueva seccion", "nueva sección",
            "write", "draft", "compose", "create", "make", "build", "generate", "produce",
            "letter", "email", "mail", "report", "presentation",
            "new text", "new block", "new section",
        )
        return any(word in lower for word in create_words)

    def _looks_like_calc_create(self, text):
        lower = text.lower()
        create_words = (
            "crea", "creá", "crear", "genera", "generá", "generar",
            "arma", "armá", "modelo", "balance", "publicacion", "publicación",
            "plantilla", "planilla", "tabla", "presupuesto", "inventario",
            "cronograma", "flujo de caja", "cashflow", "dashboard", "kpi",
            "create", "make", "build", "generate", "produce",
            "assemble", "template", "spreadsheet", "sheet", "table",
            "budget", "inventory", "schedule", "timeline", "gantt",
            "cash flow", "dashboard", "kpi",
        )
        return any(word in lower for word in create_words)

    def _looks_like_writer_format_only(self, text):
        lower = text.lower()
        format_words = (
            "formato", "negrita", "cursiva", "fuente", "tamano", "tamaño",
            "alinear", "justificar", "centrar", "interlineado", "margen",
            "margenes", "márgenes", "color", "fondo", "espaciado",
            "profesional", "moderno", "minimalista",
            "format", "bold", "italic", "font", "size",
            "align", "justify", "center", "line spacing", "margin", "margins",
            "color", "background", "spacing",
            "professional", "modern", "minimalist",
        )
        content_words = (
            "escrib", "redact", "crea", "crear", "genera", "generar", "carta",
            "write", "draft", "create", "make", "generate", "letter",
        )
        return any(word in lower for word in format_words) and not any(word in lower for word in content_words)

    def _looks_like_calc_readonly_analysis(self, text, ctx):
        if (ctx or {}).get("kind") != "calc":
            return False
        lower = text.lower()
        modifying_words = (
            "marca", "marcá", "marcar", "pintar", "resaltar", "corregir",
            "arreglar", "crear", "crea", "creá", "generar", "genera", "generá",
            "conciliar", "conciliá", "conciliacion", "conciliación",
            "mark", "paint", "highlight", "correct", "fix", "repair",
            "create", "make", "build", "generate", "produce",
            "reconcile",
        )
        if any(word in lower for word in modifying_words):
            return False
        analysis_words = (
            "audita", "auditá", "auditar", "auditoria", "auditoría",
            "perfila", "perfilá", "perfilar", "perfilado", "calidad de datos",
            "detecta errores", "detectá errores", "detectar errores",
            "detecta problemas", "detectá problemas", "detectar problemas",
            "detecta riesgos", "detectá riesgos", "detectar riesgos",
            "busca errores", "buscá errores", "buscar errores",
            "busca duplicados", "buscá duplicados", "buscar duplicados",
            "revisa formulas", "revisá formulas", "revisa fórmulas", "revisá fórmulas",
            "formula inconsistente", "fórmula inconsistente", "formulas rotas", "fórmulas rotas",
            "esta lista para analizar", "está lista para analizar",
            "audit", "profile", "data quality",
            "detect errors", "find errors", "look for errors",
            "detect issues", "find issues", "look for issues",
            "detect risks", "find risks", "look for risks",
            "find duplicates", "look for duplicates", "search for duplicates",
            "review formulas", "audit formulas", "check formulas",
            "broken formulas", "inconsistent formula", "inconsistent formulas",
            "ready to analyze", "is it ready",
        )
        return any(word in lower for word in analysis_words)

    def _calc_analysis_prompt(self, text, ctx):
        lower = text.lower()
        if any(word in lower for word in ("perfila", "perfilá", "perfilar", "perfilado", "calidad de datos", "esta lista para analizar", "está lista para analizar")):
            return skills.route("profile", text, ctx)
        if any(word in lower for word in ("formula", "fórmula", "formulas", "fórmulas")):
            return skills.route("formula_audit", text, ctx)
        return skills.route("audit", text, ctx)

    def _chat_prompt(self, text, ctx):
        if (ctx or {}).get("kind") != "calc":
            if self._looks_like_placeholder_review(text):
                return skills.route("placeholder_review", text, ctx)
            if self._looks_like_review(text):
                return skills.route("review", text, ctx)
            return prompts.chat(text, ctx)
        lower = text.lower()
        if any(word in lower for word in (
            "detectar", "estructura", "problemas", "encabezados", "tabla", "analiz", "insight",
            "detect", "structure", "headers", "analyze", "analyse", "insight", "insights",
        )):
            return skills.calc_table_detect(ctx)
        if any(word in lower for word in (
            "error", "falla", "#valor", "#ref", "#div", "#n/a", "arreglar formula", "arreglar fórmula",
            "error", "fail", "failure", "fix formula", "fix formulas", "broken formula",
        )):
            return skills.calc_formula_debug(text, ctx)
        if any(word in lower for word in (
            "perfilar", "perfilá", "perfilado", "calidad de datos",
            "profile", "data quality",
        )):
            return skills.route("profile", text, ctx)
        if any(word in lower for word in (
            "auditar", "auditá", "auditoria", "auditoría",
            "audit",
        )):
            return skills.route("audit", text, ctx)
        return prompts.chat(text, ctx)

    def _has_selection_reference(self, text):
        import re
        lower = text.lower()
        words = set(re.findall(r"[a-záéíóúñü]+", lower))
        deictic = {"este", "esta", "eso", "esa", "esto", "estos", "estas", "esos", "esas",
                   "this", "that", "these", "those"}
        if words & deictic:
            return True
        phrases = (
            "esta parte", "esa parte", "este texto", "este parrafo", "este párrafo",
            "el seleccionado", "la seleccionada", "lo seleccionado",
            "la seleccion", "la selección",
            "lo que esta seleccionado", "lo que está seleccionado",
            "this text", "this paragraph", "the selected", "selected text",
        )
        return any(p in lower for p in phrases)

    def _split_paragraphs(self, text):
        if not text:
            return []
        parts = text.replace("\r\n", "\n").split("\n\n")
        out = []
        for p in parts:
            s = p.strip()
            if s:
                out.append(s)
        return out

    def _find_first_heading(self, paragraphs):
        for p in paragraphs:
            stripped = p.lstrip("#").strip()
            if p.startswith("#") and stripped:
                return stripped[:200]
        for p in paragraphs:
            stripped = p.strip()
            if stripped.isupper() and 3 < len(stripped) < 80:
                return stripped[:200]
        for p in paragraphs:
            stripped = p.strip()
            if 3 < len(stripped) < 80 and "\n" not in stripped:
                return stripped[:200]
        return ""

    def _find_date_pattern(self, text):
        import re
        if not text:
            return ""
        m = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
        if m:
            return m.group(0)
        m = re.search(r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b", text)
        if m:
            return m.group(0)
        return ""

    def _resolve_references(self, text, ctx):
        if not ctx or ctx.get("kind") != "writer":
            return ""
        body = ctx.get("text", "")
        if not body or not body.strip():
            return ""
        lower = (text or "").lower()
        paragraphs = self._split_paragraphs(body)
        if not paragraphs:
            return ""
        additions = []

        if any(w in lower for w in ("el titulo", "la cabecera", "el encabezado", "el titulo principal",
                                     "the title", "the header", "el encabezado principal")):
            heading = self._find_first_heading(paragraphs)
            if heading:
                additions.append(_("ref.title", heading))

        if any(w in lower for w in ("el saludo", "la salutacion", "la salutación", "the greeting", "the salutation")):
            if paragraphs:
                additions.append(_("ref.greeting", paragraphs[0][:200]))

        if any(w in lower for w in ("la fecha", "el dia", "el día", "the date")):
            date = self._find_date_pattern(body)
            if date:
                additions.append(_("ref.date", date))

        if any(w in lower for w in ("la firma", "el firmante", "the signature", "the signoff")):
            if len(paragraphs) >= 2:
                additions.append(_("ref.signature", paragraphs[-1][:200]))
            elif paragraphs:
                additions.append(_("ref.signature", paragraphs[-1][:200]))

        if any(w in lower for w in ("primer parrafo", "primer párrafo", "first paragraph")):
            if len(paragraphs) >= 1:
                additions.append(_("ref.first_paragraph", paragraphs[0][:200]))
        if any(w in lower for w in ("ultimo parrafo", "último parrafo", "último párrafo", "last paragraph")):
            if paragraphs:
                additions.append(_("ref.last_paragraph", paragraphs[-1][:200]))

        import re
        m = re.search(r"parrafo\s+(\d+)|párrafo\s+(\d+)|paragraph\s+(\d+)", lower)
        if m:
            n = int(m.group(1) or m.group(2) or m.group(3))
            if 1 <= n <= len(paragraphs):
                additions.append(_("ref.paragraph_n", str(n), paragraphs[n-1][:200]))
            else:
                additions.append("REFERENCIA 'parrafo " + str(n) + _("ref.paragraph_out_of_range", str(len(paragraphs))))

        if "debajo de este" in lower or "abajo de este" in lower or "below this" in lower:
            additions.append(_("ref.below_this"))

        if not additions:
            return ""
        return _("ref.header", "\n- ".join(a for a in additions))

    def _augment_prompt_with_references(self, base_prompt, text, ctx):
        addition = self._resolve_references(text, ctx)
        if not addition:
            return base_prompt
        if isinstance(base_prompt, dict):
            base_prompt["document_context"] = base_prompt.get("document_context", "") + addition
            return base_prompt
        marker = "</document_context>"
        if marker in base_prompt:
            return base_prompt.replace(marker, "\n" + addition + "\n" + marker, 1)
        return base_prompt + addition

    def _prepare_pending_action(self, prompt_text):
        try:
            reply = self._ask(prompt_text)
            self.clear_status()
            self.set_status(_("status.validating"))
            kind = (self.last_context or {}).get("kind", "calc")
            allowed = self._allowed_cells_for_request(kind)
            try:
                data = actions.extract_json(reply)
            except Exception as extract_err:
                if kind == "writer" and self._looks_like_writer_create(self.current_request or ""):
                    data = self._retry_writer_creation_json()
                elif kind == "writer" and self._looks_like_action(self.current_request or "", self.last_context or {}):
                    data = self._retry_writer_action_json()
                elif kind == "calc" and self._looks_like_calc_create(self.current_request or ""):
                    data = self._retry_calc_creation_json()
                elif kind == "calc" and self._looks_like_action(self.current_request or "", self.last_context or {}):
                    data = self._retry_calc_action_json()
                else:
                    raise ValueError(
                        _("error.no_json", str(extract_err))
                    )
            proposal = actions.validate_preview(data, doc_kind=kind, allowed_cells=allowed)
            empty_writer_create = (
                kind == "writer"
                and self._looks_like_writer_create(self.current_request or "")
                and not (self.last_context or {}).get("text")
            )
            non_insert_actions = {
                "format_document", "format_selection", "replace_document",
                "replace_text", "apply_list", "insert_hyperlink", "insert_table",
                "set_header_footer", "insert_footnote", "insert_comment",
                "insert_markdown", "track_changes", "accept_all_redlines",
                "reject_all_redlines", "export_document",
            }
            if empty_writer_create and proposal.get("action") in non_insert_actions:
                proposal = self._local_writer_creation_proposal_dict(kind, allowed)
            has_text_format = any(key in proposal for key in actions.WRITER_STYLE_KEYS)
            if kind == "writer" and proposal.get("action") == "format_selection" and not (self.last_context or {}).get("has_selection") and has_text_format:
                raise ValueError(_("error.format_no_selection"))
            if kind == "writer" and self._looks_like_writer_edit(self.current_request or ""):
                if (self.last_context or {}).get("has_selection") and proposal.get("action") in ("insert_text", "append_text"):
                    proposal["action"] = "replace_selection"
                elif not (self.last_context or {}).get("has_selection") and (self.last_context or {}).get("text") and proposal.get("action") in ("insert_text", "append_text", "replace_selection"):
                    proposal["action"] = "replace_document"
                elif not (self.last_context or {}).get("has_selection") and not (self.last_context or {}).get("text"):
                    raise ValueError(_("error.no_text_to_edit"))
            proposal["doc_kind"] = kind
            self.pending_action = proposal
            self.clear_status()
            self._refresh_apply_buttons()
            auto_scope = self._should_auto_apply(proposal)
            if auto_scope:
                scope_text = "sesion" if auto_scope == "session" else "siempre"
                self.add_assistant(
                    _("info.auto_applied", scope_text, actions.preview_to_text(proposal))
                )
                self._confirm_pending_action()
                return
            self.add_assistant(
                _("info.proposal_ready", actions.preview_to_text(proposal))
            )
        except Exception as e:
            self.clear_status()
            self.pending_action = None
            self._refresh_apply_buttons()
            self.add_assistant(_("error.proposal_not_applicable", str(e)))

    def _auto_apply_key(self, proposal):
        kind = proposal.get("doc_kind") or (self.last_context or {}).get("kind")
        action = proposal.get("action")
        return (kind, action)

    def _should_auto_apply(self, proposal):
        key = self._auto_apply_key(proposal)
        if key in self.auto_apply_session:
            return "session"
        always_keys = [tuple(x) for x in self.auto_apply_persistent.get("always", []) if isinstance(x, (list, tuple)) and len(x) == 2]
        if key in always_keys:
            return "always"
        return None

    def _refresh_apply_buttons(self):
        if self.dialog is None:
            return
        enabled = self.pending_action is not None
        try:
            model = self.dialog.getModel()
        except Exception:
            model = None
        for name in ("btnApply", "btnApplySession", "btnApplyAlways"):
            updated = False
            if model is not None:
                try:
                    model.getByName(name).setPropertyValue("Enabled", enabled)
                    updated = True
                except Exception:
                    pass
            if not updated:
                try:
                    self.dialog.getControl(name).setPropertyValue("Enabled", enabled)
                except Exception:
                    pass

    def apply_pending_once(self):
        if not self.pending_action:
            self.add_assistant(_("info.no_pending_apply"))
            return
        self._confirm_pending_action()

    def apply_pending_session(self):
        if not self.pending_action:
            self.add_assistant(_("info.no_pending_apply"))
            return
        key = self._auto_apply_key(self.pending_action)
        if key not in self.auto_apply_session:
            self.auto_apply_session.append(key)
        self.add_assistant(_("info.rule_session_added", str(key[0]), str(key[1])))
        self._confirm_pending_action()

    def apply_pending_always(self):
        if not self.pending_action:
            self.add_assistant(_("info.no_pending_apply"))
            return
        key = self._auto_apply_key(self.pending_action)
        always = self.auto_apply_persistent.setdefault("always", [])
        if list(key) not in always:
            always.append(list(key))
        if config.save_auto_apply(self.auto_apply_persistent):
            self.add_assistant(_("info.rule_persistent_saved", str(key[0]), str(key[1])))
        else:
            self.add_assistant(_("info.rule_save_failed"))
        self._confirm_pending_action()

    def _retry_writer_creation_json(self):
        retry_prompt = skills.writer_rewrite(
            (self.current_request or "")
            + "\n\n" + _("prompt.retry.writer_creation"),
            self.last_context or {},
        )
        try:
            return actions.extract_json(self._ask(retry_prompt))
        except Exception:
            return self._local_writer_creation_proposal(self.current_request or "")

    def _local_writer_creation_proposal(self, request_text):
        lower = request_text.lower()
        if "email" in lower or "correo" in lower:
            return {
                "action": "insert_text",
                "summary": _("template.email.title"),
                "style": {"font_name": "Liberation Sans", "font_size": 11, "line_spacing": 1.15, "space_after": 160},
                "blocks": [
                    {"text": "Asunto: [Motivo del mensaje]", "style": {"paragraph_style": "Heading 2", "font_size": 13, "bold": True, "font_color": "#1F4E79"}},
                    {"text": "Estimado/a [Nombre]:", "style": {"font_size": 11}},
                    {"text": "Me comunico con usted para [explicar el motivo principal del mensaje de forma clara y breve].", "style": {"font_size": 11, "align": "justify"}},
                    {"text": "Quedo a disposicion para ampliar la informacion o coordinar los proximos pasos.", "style": {"font_size": 11, "align": "justify"}},
                    {"text": "Saludos cordiales,\n[Tu nombre]", "style": {"font_size": 11}},
                ],
            }
        return {
            "action": "insert_text",
            "summary": _("template.letter.title"),
            "page_style": {"left_margin": 2500, "right_margin": 2500, "top_margin": 2200, "bottom_margin": 2200},
            "style": {"font_name": "Liberation Sans", "font_size": 11, "line_spacing": 1.15, "space_after": 160},
            "blocks": [
                {"text": "[Tu nombre]\n[Ciudad] | [Telefono] | [Email]", "style": {"font_size": 10, "font_color": "#555555"}},
                {"text": "Asunto: [Motivo de la carta]", "style": {"paragraph_style": "Heading 2", "font_size": 13, "bold": True, "font_color": "#1F4E79"}},
                {"text": "Estimado/a [Nombre del destinatario]:", "style": {"font_size": 11}},
                {"text": "Me dirijo a usted para presentarme y expresar mi interes en [objetivo o motivo principal].", "style": {"font_size": 11, "align": "justify"}},
                {"text": "Cuento con experiencia en [area o sector] y considero que puedo aportar valor mediante [fortaleza principal].", "style": {"font_size": 11, "align": "justify"}},
                {"text": "Quedo a disposicion para ampliar la informacion o coordinar una conversacion.", "style": {"font_size": 11, "align": "justify"}},
                {"text": "Saludos cordiales,\n[Tu nombre]", "style": {"font_size": 11}},
            ],
        }

    def _local_writer_creation_proposal_dict(self, kind, allowed):
        template = self._local_writer_creation_proposal(self.current_request or "")
        data = {
            "summary": template.get("summary"),
            "action": "insert_text",
            "blocks": template.get("blocks", []),
        }
        if "style" in template:
            data["style"] = template["style"]
        if "page_style" in template:
            data["page_style"] = template["page_style"]
        return actions.validate_preview(data, doc_kind=kind, allowed_cells=allowed)

    def _local_writer_append_proposal(self, request_text):
        lower = (request_text or "").lower()
        if any(w in lower for w in ("abajo", "debajo", "al final", "agrega al final", "suma al final")):
            return {
                "action": "append_text",
                "summary": _("template.append.title"),
                "text": _("template.append.text"),
            }
        return {
            "action": "append_text",
            "summary": _("template.append.title"),
            "text": _("template.append.text"),
        }

    def _retry_writer_action_json(self):
        retry_prompt = skills.writer_rewrite(
            (self.current_request or "")
            + "\n\n" + _("prompt.retry.writer_action"),
            self.last_context or {},
        )
        try:
            return actions.extract_json(self._ask(retry_prompt))
        except Exception:
            return self._local_writer_append_proposal(self.current_request or "")

    def _retry_calc_action_json(self):
        retry_prompt = _("prompt.retry.calc_action", self.current_request or "")
        try:
            return actions.extract_json(self._ask(retry_prompt))
        except Exception:
            return {
                "summary": _("template.calc.fallback"),
                "changes": [{"cell": "A1", "value": "=ESBLANCO()", "formula": True}],
            }

    def _retry_calc_creation_json(self):
        retry_prompt = skills.calc_sheet_builder(
            (self.current_request or "")
            + "\n\n" + _("prompt.retry.calc_creation"),
            self.last_context or {},
        )
        try:
            return actions.extract_json(self._ask(retry_prompt))
        except Exception:
            return self._local_calc_creation_proposal(self.current_request or "")

    def _local_calc_creation_proposal(self, request_text):
        lower = request_text.lower()
        if "balance" in lower and ("publicacion" in lower or "publicación" in lower):
            return {
                "summary": "Crea modelo de balance de publicacion",
                "changes": [
                    {"cell": "A1", "value": "Modelo de balance de publicacion", "formula": False, "bold": True, "background": "#D9EAF7", "border": True},
                    {"cell": "A3", "value": "Concepto", "formula": False, "bold": True, "background": "#E2F0D9", "border": True, "width": 4200},
                    {"cell": "B3", "value": "Cantidad", "formula": False, "bold": True, "background": "#E2F0D9", "border": True, "width": 2200},
                    {"cell": "C3", "value": "Costo unitario", "formula": False, "bold": True, "background": "#E2F0D9", "border": True, "width": 2800},
                    {"cell": "D3", "value": "Ingreso unitario", "formula": False, "bold": True, "background": "#E2F0D9", "border": True, "width": 2800},
                    {"cell": "E3", "value": "Costo total", "formula": False, "bold": True, "background": "#E2F0D9", "border": True, "width": 2600},
                    {"cell": "F3", "value": "Ingreso total", "formula": False, "bold": True, "background": "#E2F0D9", "border": True, "width": 2600},
                    {"cell": "G3", "value": "Resultado", "formula": False, "bold": True, "background": "#E2F0D9", "border": True, "width": 2600},
                    {"cell": "A4", "value": "Tirada / ejemplares", "formula": False},
                    {"cell": "A5", "value": "Precio de venta", "formula": False},
                    {"cell": "A6", "value": "Impresion", "formula": False},
                    {"cell": "A7", "value": "Diseno / maquetacion", "formula": False},
                    {"cell": "A8", "value": "Correccion / edicion", "formula": False},
                    {"cell": "A9", "value": "Distribucion", "formula": False},
                    {"cell": "A10", "value": "Marketing", "formula": False},
                    {"cell": "A11", "value": "Otros costos", "formula": False},
                    {"cell": "B4", "value": "1000", "formula": False},
                    {"cell": "D5", "value": "0", "formula": False},
                    {"cell": "E6", "value": "=B4*C6", "formula": True},
                    {"cell": "E7", "value": "=C7", "formula": True},
                    {"cell": "E8", "value": "=C8", "formula": True},
                    {"cell": "E9", "value": "=B4*C9", "formula": True},
                    {"cell": "E10", "value": "=C10", "formula": True},
                    {"cell": "E11", "value": "=C11", "formula": True},
                    {"cell": "F5", "value": "=B4*D5", "formula": True},
                    {"cell": "G5", "value": "=F5-SUMA(E6:E11)", "formula": True, "bold": True},
                    {"cell": "A13", "value": "Totales", "formula": False, "bold": True, "background": "#FFF2CC"},
                    {"cell": "E13", "value": "=SUMA(E6:E11)", "formula": True, "bold": True, "background": "#FFF2CC"},
                    {"cell": "F13", "value": "=F5", "formula": True, "bold": True, "background": "#FFF2CC"},
                    {"cell": "G13", "value": "=F13-E13", "formula": True, "bold": True, "background": "#FFF2CC"},
                    {"cell": "A15", "value": "Punto de equilibrio", "formula": False, "bold": True},
                    {"cell": "B15", "value": "=SI(D5>0;E13/D5;0)", "formula": True},
                ],
            }
        return {
            "summary": "Crea modelo de planilla editable",
            "changes": [
                {"cell": "A1", "value": "Modelo", "formula": False, "bold": True, "background": "#D9EAF7", "border": True},
                {"cell": "A3", "value": "Concepto", "formula": False, "bold": True, "background": "#E2F0D9", "border": True},
                {"cell": "B3", "value": "Valor", "formula": False, "bold": True, "background": "#E2F0D9", "border": True},
                {"cell": "C3", "value": "Notas", "formula": False, "bold": True, "background": "#E2F0D9", "border": True},
            ],
        }

    def _confirm_pending_action(self):
        if not self.pending_action:
            self.add_assistant(_("info.no_pending_confirm"))
            return
        doc = self._active_supported_doc()
        if doc is None:
            return
        active_kind = "writer" if _is_writer(doc) else "calc"
        if self.pending_action.get("doc_kind") != active_kind:
            self.add_assistant(_("info.wrong_doc_kind", self.pending_action.get("doc_kind", "otro documento")))
            return
        snapshot = self.pending_action
        self.pending_action = None
        self._refresh_apply_buttons()
        self._run_background(_("status.applying"), self._do_apply_work, doc, snapshot)

    def _cancel_pending_action(self):
        if not self.pending_action:
            self.add_assistant(_("info.no_pending_cancel"))
            return
        self.pending_action = None
        self._refresh_apply_buttons()
        self.add_assistant(_("info.proposal_cancelled"))

    def _allowed_cells_for_request(self, kind):
        if kind != "calc":
            return []
        ctx = self.last_context or {}
        lower = (self.current_request or "").lower()
        create_words = (
            "crea", "crear", "armá", "arma", "generá", "genera", "generar",
            "tabla", "planilla", "presupuesto", "inventario", "cronograma",
            "flujo de caja", "cashflow", "control de gastos", "estructura",
            "modelo", "balance", "publicacion", "publicación", "plantilla",
            "tabla dinamica", "tabla dinámica", "tabla resumen", "reporte",
            "resumen", "hoja de resumen", "auditoria", "auditoría",
            "informe de auditoria", "informe de auditoría", "reporte de auditoria",
            "reporte de auditoría", "hoja de auditoria", "hoja de auditoría",
        )
        audit_report_words = (
            "reporte de auditoria", "reporte de auditoría", "informe de auditoria",
            "informe de auditoría", "hoja de auditoria", "hoja de auditoría",
            "crear auditoria", "crear auditoría", "creá auditoria", "creá auditoría",
        )
        summary_words = (
            "tabla dinamica", "tabla dinámica", "tabla resumen", "reporte",
            "resumen por", "hoja de resumen", "crear resumen", "creá resumen",
        )
        if any(word in lower for word in audit_report_words):
            return ctx.get("audit_report_allowed_cells", ctx.get("summary_allowed_cells", ctx.get("allowed_cells", [])))
        if any(word in lower for word in summary_words):
            return ctx.get("summary_allowed_cells", ctx.get("generated_allowed_cells", ctx.get("allowed_cells", [])))
        if int(ctx.get("rows_total", 0) or 0) <= 1 and int(ctx.get("cols_total", 0) or 0) <= 1 and any(word in lower for word in create_words):
            return ctx.get("generated_allowed_cells", ctx.get("allowed_cells", []))
        return ctx.get("allowed_cells", [])

    def _do_apply_work(self, doc, proposal):
        snapshot = None
        if proposal.get("doc_kind") == "writer":
            snapshot = writer_ops.make_undo_snapshot(doc, proposal)
        else:
            snapshot = calc_ops.make_undo_snapshot(doc, proposal)
        if proposal.get("doc_kind") == "writer":
            count = writer_ops.apply_preview(doc, proposal)
        else:
            count = calc_ops.apply_preview(doc, proposal)
        self.clear_status()
        if count:
            if snapshot:
                snapshot["summary"] = proposal.get("summary", "Ultimo cambio")
                self.undo_stack.append(snapshot)
                self.undo_stack = self.undo_stack[-10:]
            self._record_action(proposal, count)
            self.add_assistant(_("info.changes_applied", count))
        else:
            self.add_assistant(_("info.no_changes_applied"))
        self.pending_action = None

    def _record_action(self, proposal, count):
        item = {
            "kind": proposal.get("doc_kind", "calc"),
            "summary": proposal.get("summary", "Cambio aplicado"),
            "count": count,
        }
        if proposal.get("action"):
            item["action"] = proposal.get("action")
        elif proposal.get("changes"):
            item["action"] = "calc_changes"
        self.action_history.append(item)
        self.action_history = self.action_history[-20:]

    def _show_action_history(self):
        if not self.action_history:
            self.add_assistant(_("info.empty_history"))
            return
        lines = [_("info.history_header")]
        for idx, item in enumerate(self.action_history[-10:], 1):
            lines.append(
                str(idx) + ". "
                + item.get("kind", "?") + " / "
                + item.get("action", "accion") + ": "
                + item.get("summary", "Cambio aplicado")
                + " (" + str(item.get("count", 0)) + " cambio(s))"
            )
        self.add_assistant("\n".join(lines))

    def _undo_last_change(self):
        if not self.undo_stack:
            self.add_assistant(_("info.nothing_to_undo"))
            return
        doc = self._active_supported_doc()
        if doc is None:
            return
        snapshot = self.undo_stack[-1]
        active_kind = "writer" if _is_writer(doc) else "calc"
        if snapshot.get("kind") != active_kind:
            self.add_assistant(_("info.undo_wrong_doc", snapshot.get("kind", "otro documento")))
            return
        self._run_background(_("status.undoing"), self._do_undo_work, doc, snapshot)

    def _do_undo_work(self, doc, snapshot):
        if snapshot.get("kind") == "writer":
            count = writer_ops.restore_snapshot(doc, snapshot)
        else:
            count = calc_ops.restore_snapshot(doc, snapshot)
        self.clear_status()
        if count:
            self.undo_stack.pop()
            self.add_assistant(_("info.undone", snapshot.get("summary", "ultimo cambio")))
        else:
            self.add_assistant(_("info.undo_failed"))

    def show_config(self):
        if self.config_dialog is not None:
            try:
                self.config_dialog.setVisible(True)
                return
            except Exception:
                self.config_dialog = None
        try:
            dlg = _build_config_dialog()
            self._populate_config(dlg)
            self.config_dialog = dlg
            self._layout_config(dlg)
            dlg.setVisible(True)
            dlg.getControl("btnSave").addActionListener(SaveConfigListener(self, dlg))
            dlg.getControl("btnCancel").addActionListener(CancelConfigListener(self, dlg))
        except Exception as e:
            self.add_assistant(_("error.config", str(e)))

    def _layout_config(self, dlg):
        items = [
            ("lblProvider", 20, 20, 680, 30), ("txtProvider", 20, 58, 680, 44),
            ("lblUrl", 20, 120, 680, 30), ("txtUrl", 20, 158, 680, 44),
            ("lblModel", 20, 220, 680, 30), ("txtModel", 20, 258, 680, 44),
            ("lblKey", 20, 320, 680, 30), ("txtKey", 20, 358, 680, 44),
            ("lblSysPreset", 20, 420, 680, 30), ("txtSystemPreset", 20, 458, 680, 44),
            ("lblSys", 20, 520, 680, 30), ("txtSystem", 20, 558, 680, 86),
            ("chkWebSearch", 20, 660, 680, 36),
            ("btnSave", 20, 780, 320, 44),
            ("btnCancel", 380, 780, 320, 44),
        ]
        for name, x, y, w, h in items:
            dlg.getControl(name).setPosSize(x, y, w, h, POS_SIZE)

    def _populate_config(self, dlg):
        cfg = self.cfg
        dlg.getControl("txtProvider").setText(cfg.get("provider", "Custom"))
        dlg.getControl("txtUrl").setText(cfg.get("api_url", ""))
        dlg.getControl("txtModel").setText(cfg.get("model", ""))
        dlg.getControl("txtKey").setText(cfg.get("api_key", ""))
        dlg.getControl("txtSystemPreset").setText(cfg.get("system_preset", "General"))
        dlg.getControl("txtSystem").setText(cfg.get("system_prompt", ""))
        chk = dlg.getControl("chkWebSearch")
        chk.setState(1 if cfg.get("enable_web_search", False) else 0)

    def do_save_config(self, dlg):
        new_cfg = dict(self.cfg)
        new_cfg["provider"] = dlg.getControl("txtProvider").getText() or "Custom"
        new_cfg["api_url"] = dlg.getControl("txtUrl").getText()
        new_cfg["api_key"] = dlg.getControl("txtKey").getText()
        new_cfg["system_preset"] = dlg.getControl("txtSystemPreset").getText() or "General"
        new_cfg["system_prompt"] = dlg.getControl("txtSystem").getText()
        new_cfg["enable_web_search"] = bool(dlg.getControl("chkWebSearch").getState())
        config.save(new_cfg)
        self.cfg = new_cfg
        dlg.setVisible(False)
        self.config_dialog = None
        self.add_assistant(_("info.config_saved"))

    def do_cancel_config(self, dlg):
        dlg.setVisible(False)
        self.config_dialog = None

    def on_provider_change(self, dlg, provider):
        new_cfg = config.apply_preset(dict(self.cfg), provider)
        dlg.getControl("txtUrl").setText(new_cfg["api_url"])
        dlg.getControl("txtModel").setText(new_cfg["model"])

    def on_system_change(self, dlg, preset):
        if preset in config.SYSTEM_PROMPTS:
            dlg.getControl("txtSystem").setText(config.SYSTEM_PROMPTS[preset])


def _local():
    g = globals()
    if "_panel_controller" not in g:
        g["_panel_controller"] = PanelController()
    return g["_panel_controller"]


def show_panel(*args):
    _local().show()


def show_config_dialog(*args):
    _local().show_config()


class _Base(unohelper.Base):
    def __init__(self, controller):
        self.controller = controller

    def disposing(self, ev):
        pass


class ConfigListener(_Base, XActionListener):
    def actionPerformed(self, ev):
        self.controller.show_config()


class DockListener(_Base, XActionListener):
    def actionPerformed(self, ev):
        self.controller.dock_right()


class CompactListener(_Base, XActionListener):
    def actionPerformed(self, ev):
        self.controller._set_size("compact")


class NormalListener(_Base, XActionListener):
    def actionPerformed(self, ev):
        self.controller._set_size("normal")


class LargeListener(_Base, XActionListener):
    def actionPerformed(self, ev):
        self.controller._set_size("large")


class SendListener(_Base, XActionListener):
    def actionPerformed(self, ev):
        self.controller.do_send()


class ApplyListener(_Base, XActionListener):
    def actionPerformed(self, ev):
        self.controller.apply_pending_once()


class ApplySessionListener(_Base, XActionListener):
    def actionPerformed(self, ev):
        self.controller.apply_pending_session()


class ApplyAlwaysListener(_Base, XActionListener):
    def actionPerformed(self, ev):
        self.controller.apply_pending_always()


class SaveConfigListener(_Base, XActionListener):
    def __init__(self, controller, dlg):
        super().__init__(controller)
        self.dlg = dlg

    def actionPerformed(self, ev):
        self.controller.do_save_config(self.dlg)


class CancelConfigListener(_Base, XActionListener):
    def __init__(self, controller, dlg):
        super().__init__(controller)
        self.dlg = dlg

    def actionPerformed(self, ev):
        self.controller.do_cancel_config(self.dlg)


class ProviderChangeListener(_Base, XItemListener):
    def __init__(self, controller, dlg):
        super().__init__(controller)
        self.dlg = dlg

    def itemStateChanged(self, ev):
        try:
            provider = ev.Source.getSelectedItem()
        except Exception:
            provider = ""
        self.controller.on_provider_change(self.dlg, provider)


class SystemChangeListener(_Base, XItemListener):
    def __init__(self, controller, dlg):
        super().__init__(controller)
        self.dlg = dlg

    def itemStateChanged(self, ev):
        try:
            preset = ev.Source.getSelectedItem()
        except Exception:
            preset = ""
        self.controller.on_system_change(self.dlg, preset)


class PromptKeyListener(_Base, XKeyListener):
    def keyPressed(self, ev):
        try:
            if ev.KeyCode == KEY_RETURN and not (ev.Modifiers & 1):
                self.controller.do_send()
        except Exception:
            pass

    def keyReleased(self, ev):
        pass
