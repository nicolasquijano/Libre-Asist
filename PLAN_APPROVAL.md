# Plan: fix hang en `Validando propuesta...` + menu de aprobacion por alcance

Fecha: 2026-06-20
Modulo afectado: `~/.config/libreoffice/4/user/Scripts/python/libre_asist/`

## Contexto

El usuario reporta dos problemas en el panel `Libre Asist`:

1. **Bug**: al pedir "Crea un email formal" sobre un Writer vacio, el status
   queda colgado en "Validando propuesta..." y nunca aparece la propuesta.
2. **Feature**: quiere un menu de aprobacion con tres alcances cuando hay una
   propuesta pendiente:
   - aprobar **una vez** (comportamiento actual),
   - aprobar **en esta sesion** (auto-aplicar por el resto de la sesion),
   - aprobar **para siempre** (recordar la regla en disco).

Este plan cubre el fix del hang y deja la feature de aprobacion detallada
para una segunda iteracion, pero ya con el diseno completo para no rehacer
trabajo.

---

## Parte 1 — Fix del hang

### Causa

En `panel.py:_prepare_pending_action` (lineas 833-860) el flujo es:

```
1. self._ask(prompt_text)            # 1ra llamada HTTP -> OK
2. set_status("Validando propuesta...")
3. validate_preview(...)
4. SI empty_writer_create Y action en non_insert_actions:
       try:
           self._ask(retry_prompt)   # 2da llamada HTTP -> puede colgar
           validate_preview(...)
       except Exception:
           fallback al template local
       if action != "insert_text":
           fallback al template local
```

El hang es la **2da llamada HTTP**. La 1ra ya volvio (porque el status
cambio a "Validando propuesta..."), entro al `if empty_writer_create`, y la
retry espera respuesta del proveedor. `urllib.request.urlopen` tiene
`timeout=60` por default pero si el servidor acepta la conexion TCP y nunca
envia respuesta el tiempo real puede ser mayor, y aun con 60s exactos es
inaceptablemente lento para algo que el template local resuelve al instante.

Ademas, el retry es logicamente inutil: si el modelo devolvio
`replace_document` (u otra accion que no aplica sobre doc vacio), el template
local es estrictamente mejor que pedirle otra vez lo mismo. La unica
excepcion era `format_document`, donde el reintento podria traer `insert_text`
de una segunda tirada — pero ese caso ya esta cubierto por el template local
tambien.

### Cambio concreto

Archivo: `panel.py`, region 833-860.

Reemplazar el bloque:

```python
if empty_writer_create and proposal.get("action") in non_insert_actions:
    try:
        retry_prompt = skills.writer_rewrite(
            (self.current_request or "")
            + "\n\nIMPORTANTE: el documento esta vacio. "
              "No uses format_document, replace_document, replace_text ni format_selection. "
              "Devuelve obligatoriamente action insert_text con blocks y texto completo.",
            self.last_context or {},
        )
        data = actions.extract_json(self._ask(retry_prompt))
        proposal = actions.validate_preview(data, doc_kind=kind, allowed_cells=allowed)
    except Exception:
        proposal = self._local_writer_creation_proposal_dict(kind, allowed)
    if proposal.get("action") != "insert_text":
        proposal = self._local_writer_creation_proposal_dict(kind, allowed)
```

por:

```python
if empty_writer_create and proposal.get("action") in non_insert_actions:
    proposal = self._local_writer_creation_proposal_dict(kind, allowed)
```

Esto elimina la 2da llamada HTTP, elimina el `try/except` ya innecesario, y
mantiene `non_insert_actions` (sigue siendo util para que el chequeo entre
solo en el caso correcto). El helper `_local_writer_creation_proposal_dict`
(ya agregado en la iteracion anterior) se queda como esta.

### Verificacion del fix

```bash
pkill -f soffice.bin
PYTHONPATH=/usr/lib/libreoffice/program:/home/nicolas/.config/libreoffice/4/user/Scripts/python:/home/nicolas/.config/libreoffice/4/user/Scripts/python/libre_asist \
  python3 -m py_compile \
    /home/nicolas/.config/libreoffice/4/user/Scripts/python/LibreAsist.py \
    /home/nicolas/.config/libreoffice/4/user/Scripts/python/libre_asist/*.py
```

Smoke test (stubs de `uno`/`unohelper` como en la sesion anterior):

```python
import actions, panel as pmod
class C: pass
ctrl = C()
ctrl.current_request = "Crea un email formal"
ctrl.__class__ = type("PC", (pmod.PanelController,), {})
fb = ctrl._local_writer_creation_proposal_dict("writer", [])
assert fb["action"] == "insert_text"
assert len(fb["blocks"]) >= 5
```

E2E:

1. Writer con doc vacio.
2. `abrir_libre_asist`.
3. Click en la sugerencia "Crea un email formal".
4. Esperado: status "Validando propuesta..." aparece brevemente (milisegundos)
   y luego llega la propuesta con los 5 bloques del email. Sin hang.

Repetir con "Redacta una carta formal" -> 7 bloques + `page_style`.

### Riesgo

- **Ninguno** sobre el flujo feliz (`insert_text` correcto en la 1ra llamada):
  el `if` ni se entra.
- **Ninguno** sobre docs no vacios: el `if` requiere `not text`, asi que
  `replace_document`/`replace_text`/`format_*` siguen funcionando normal.
- **Reducido** sobre `format_document` valido: antes reintentaba una vez para
  ver si el modelo corregia a `insert_text`; ahora va directo al template.
  El template es estrictamente mejor para un doc vacio, asi que no se pierde
  calidad.

---

## Parte 2 — Feature: menu de aprobacion por alcance (opcion B)

### Diseno

Tres niveles de aprobacion, scope en cascada:

| Nivel | Etiqueta UI | Persistencia | Cuando aplica |
|-------|-------------|--------------|---------------|
| `once` | "Aplicar" | ninguna | default, igual que hoy |
| `session` | "Aplicar en esta sesion" | `self.auto_apply_session` en `PanelController` | todo lo que coincida en esta corrida |
| `always` | "Aplicar siempre" | `~/.config/libreoffice/4/user/libre_asist/auto_apply.json` | futuras corridas tambien |

Reglas de auto-aplicacion:

- Se almacenan como `[(kind, action, scope), ...]`.
- Matching: por `kind` (`writer`/`calc`) y `action` (`insert_text`, etc.).
  Opcionalmente una **signature** del pedido (hash simple del texto del
  request) para mas precision, pero **fuera de scope de esta iteracion**.
- Evaluacion en `_prepare_pending_action`, justo despues de validar y antes
  de mostrar la propuesta: si la regla aplica, salta directo a
  `_confirm_pending_action` sin pedir confirmacion al usuario.
- Si la regla esta en `session`, se elimina del dict al cerrar el panel.
- Si esta en `always`, se persiste y sobrevive cierres de LibreOffice.

### Archivos a tocar

#### `config.py`

Agregar dos helpers nuevos, sin romper el schema actual:

```python
AUTO_APPLY_PATH = os.path.expanduser(
    "~/.config/libreoffice/4/user/libre_asist/auto_apply.json"
)

def load_auto_apply():
    if not os.path.isfile(AUTO_APPLY_PATH):
        return {"always": []}
    try:
        with open(AUTO_APPLY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"always": []}
        if not isinstance(data.get("always"), list):
            data["always"] = []
        return data
    except Exception:
        return {"always": []}

def save_auto_apply(rules):
    try:
        os.makedirs(os.path.dirname(AUTO_APPLY_PATH), exist_ok=True)
        with open(AUTO_APPLY_PATH, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
```

`load()` no necesita cambios. La regla vive en archivo separado para no
mezclar credenciales con preferencias.

#### `panel.py`

Cambios:

1. **Estado nuevo en `PanelController.__init__`** (panel.py ~170):

   ```python
   self.auto_apply_session = []  # lista de tuplas (kind, action)
   self.auto_apply_persistent = config.load_auto_apply()
   ```

2. **Helpers**:

   ```python
   def _auto_apply_key(self, proposal):
       return (proposal.get("doc_kind"), proposal.get("action"))

   def _should_auto_apply(self, proposal):
       key = self._auto_apply_key(proposal)
       if key in self.auto_apply_session:
           return "session"
       if key in [tuple(x) for x in self.auto_apply_persistent.get("always", [])]:
           return "always"
       return None
   ```

3. **En `_prepare_pending_action`**, despues de validar la propuesta y antes
   de setear `pending_action`:

   ```python
   auto = self._should_auto_apply(proposal)
   if auto:
       self.pending_action = proposal
       self.add_assistant("Auto-aplicando por regla " + auto + ": " + actions.preview_to_text(proposal))
       self._confirm_pending_action()
       return
   ```

4. **UI**: agregar 3 botones en el panel principal (despues de `btnApply`
   existente, o reemplazandolo), solo visibles cuando hay `pending_action`:

   - `btnApply` -> confirmar (actual `_confirm_pending_action`).
   - `btnApplySession` -> `self.auto_apply_session.append(key); _confirm_pending_action()`.
   - `btnApplyAlways` -> `self.auto_apply_persistent.setdefault("always", []).append(list(key)); config.save_auto_apply(self.auto_apply_persistent); _confirm_pending_action()`.

   Alternativa sin botones nuevos (menos descubrible pero zero cambios de
   UI): interpretar `si siempre`, `si sesion`, `si esta vez` en el prompt.
   **Recomendado**: botones, porque el usuario los pidio como "menu".

5. **Config dialog**: agregar una seccion "Aprobaciones automaticas" con:

   - ListBox mostrando las reglas `always` actuales.
   - Boton "Borrar todas" -> `self.auto_apply_persistent = {"always": []}; config.save_auto_apply(...)`.
   - Boton "Borrar seleccionada" -> pop por indice.

   Usar los helpers `_add_label`, `_add_listbox`, `_add_button` que ya
   existen en `panel.py:89-128`.

#### `skills_common.py`

Sin cambios.

#### `actions.py`

Sin cambios. El `preview_to_text` ya existe y sirve.

### Verificacion

Smoke test del auto-apply:

```python
import panel as pmod
ctrl = type("PC", (pmod.PanelController,), {})()
proposal = {
    "doc_kind": "writer",
    "action": "insert_text",
    "blocks": [{"text": "x"}],
    "summary": "x",
}
# 1) Sin reglas -> no aplica
assert ctrl._should_auto_apply(proposal) is None
# 2) Regla de sesion -> aplica
ctrl.auto_apply_session.append(("writer", "insert_text"))
assert ctrl._should_auto_apply(proposal) == "session"
# 3) Regla always -> aplica y persiste
ctrl.auto_apply_session.clear()
ctrl.auto_apply_persistent["always"] = [["writer", "insert_text"]]
assert ctrl._should_auto_apply(proposal) == "always"
```

E2E:

1. Writer vacio, pedir "Crea un email formal".
2. Llega propuesta. Usuario clickea "Aplicar en esta sesion".
3. Email se inserta.
4. Writer vacio, pedir "Crea una carta formal".
5. Esperado: la carta se inserta sin pedir confirmacion (mismo `(writer,
   insert_text)`).
6. Cerrar y reabrir LibreOffice.
7. Writer vacio, pedir "Crea una carta formal".
8. Esperado: vuelve a pedir confirmacion (la regla de sesion se fue).
9. Repetir con "Aplicar siempre" -> sobrevive al reinicio.

### Riesgos / cosas a NO cambiar

- El esquema JSON, validadores, snapshots y undo quedan intactos.
- El comportamiento para docs no vacios no cambia.
- El flujo `once` (escribir "si" en el prompt) sigue funcionando; los
  botones son adicionales.
- `_should_auto_apply` se evalua DESPUES de validar, asi que un JSON
  invalido sigue mostrando el error "[Propuesta no aplicable]" como hoy.
- El archivo `auto_apply.json` queda en el mismo dir que `config.json`
  (nota: dir distinto a \`Scripts/python/libre_asist/\` — esto ya esta
  documentado en AGENTS.md).
- No se introducen dependencias nuevas.
- No se rompe el contrato `ctx` (kind/action yaestan en `proposal`).

---

## Orden sugerido de implementacion

1. **Parte 1 (fix del hang)**: 1 edit en `panel.py`, ~10 lineas.
   Bump de `CACHE_BUSTER` para forzar recarga.
2. Smoke test + E2E del fix.
3. **Parte 2 (feature de aprobacion)**:
   a. `config.py`: `load_auto_apply` + `save_auto_apply`.
   b. `panel.py`: estado + helpers + atajo en `_prepare_pending_action`.
   c. `panel.py`: UI (3 botones + listeners + seccion en Config dialog).
   d. Smoke test + E2E.
4. Bump final de `CACHE_BUSTER`.

## Cosas fuera de scope

- Signature-based auto-apply (matching por contenido del request).
- Notificaciones de "esta accion se aplico por auto-aprobacion".
- Sync de reglas entre maquinas.
- UI para editar reglas existentes (solo borrar).