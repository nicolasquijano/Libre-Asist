# Libre Asist - Plan de Implementacion

## Objetivo

Convertir `libre_asist` en un asistente tipo ChatGPT para LibreOffice Calc y Writer: capaz de entender el documento activo, proponer cambios seguros, aplicar modificaciones confirmadas por chat y ofrecer herramientas practicas de oficina.

El foco no es solo responder preguntas, sino ayudar a crear, editar, formatear, analizar y corregir documentos reales.

## Principios de Producto

- El usuario escribe en lenguaje natural.
- El asistente analiza el documento activo antes de actuar.
- Si el pedido modifica el documento, primero muestra una propuesta clara.
- La aplicacion ocurre solo despues de confirmacion conversacional.
- Si hay seleccion, la seleccion es el objetivo principal.
- Si no hay seleccion, Writer puede analizar y modificar el documento completo.
- En Calc, los cambios deben mantenerse dentro de rangos permitidos o acciones explicitamente seguras.
- El JSON del modelo nunca se aplica sin validacion local.
- Toda accion importante debe ser reversible en una fase futura.

## Estado Actual

Ya existe una base funcional:

- Ventana flotante tipo chat para LibreOffice.
- Soporte Calc y Writer.
- Configuracion de proveedor/modelo/API key.
- Flujo de propuesta pendiente con confirmacion por chat.
- Indicador de trabajo/carga.
- Validacion local de acciones en `actions.py`.
- Operaciones Calc en `calc_ops.py`.
- Operaciones Writer en `writer_ops.py`.
- Prompts/skills separados por dominio: `skills_calc.py`, `skills_writer.py`, `skills_common.py`; `skills.py` queda como router compatible.
- Soporte Writer para insertar, reemplazar seleccion, reemplazar documento, aplicar estilos basicos y formato por bloques.
- Soporte Calc para cambios de celda, formulas y formato basico.

## Prioridad 1 - Seguridad y Confianza

### 1. Deshacer ultimo cambio

Estado: implementado inicial.

Notas:

- Writer guarda snapshot completo del texto antes de aplicar y restaura el documento completo.
- Calc guarda snapshot de las celdas afectadas y restaura valor/formula/formato basico.
- El comando `deshacer`, `undo`, `revertir ultimo cambio` o `volver atras` se resuelve localmente, sin llamar a la IA.
- El historial actual vive solo durante la sesion de la ventana.

Implementar una pila simple de historial local.

Comportamiento esperado:

- Antes de aplicar cambios, guardar snapshot minimo del contenido afectado.
- Agregar comando por chat: `deshacer`, `undo`, `revertir ultimo cambio`.
- Mostrar en chat que se revirtio la ultima accion.
- Si no hay historial, avisar que no hay cambios para deshacer.

Writer:

- Para `replace_selection`, guardar texto anterior de la seleccion.
- Para `replace_document`, guardar texto completo anterior.
- Para `insert_text` y `append_text`, guardar rango aproximado insertado si UNO lo permite; si no, guardar documento completo antes de aplicar.
- Para formato, guardar propiedades principales cuando sea viable.

Calc:

- Para cada celda modificada, guardar valor, formula y formato basico anterior.
- Revertir solo las celdas afectadas.

Archivos principales:

- `panel.py`: detectar comando de deshacer y manejar historial.
- `actions.py`: describir acciones reversibles.
- `calc_ops.py`: snapshot y restauracion de celdas.
- `writer_ops.py`: snapshot y restauracion de texto/documento.

Pruebas:

- Aplicar cambio Writer y deshacer.
- Aplicar cambio Calc y deshacer.
- Intentar deshacer sin historial.
- Confirmar que deshacer no llama a la IA.

## Prioridad 2 - Writer Como Asistente de Documento

### 2. Plantillas inteligentes

Agregar skills para crear documentos completos:

- carta formal;
- carta informal;
- carta de amor;
- reclamo;
- email profesional;
- CV simple;
- informe;
- minuta/reunion;
- propuesta comercial.

Comportamiento esperado:

- Si el documento esta vacio, usar `insert_text` o bloques.
- Si el documento tiene contenido y el usuario pide “convertir en carta/informe”, usar `replace_document`.
- Usar `blocks` para titulos, subtitulos, cuerpo y firma.
- Aplicar `page_style` y `style` sin pegar instrucciones de formato dentro del texto.

Archivos principales:

- `skills.py`: nuevas skills Writer.
- `actions.py`: validar bloques y estilos.
- `writer_ops.py`: aplicar bloques con estilo.

Pruebas:

- Crear carta desde documento vacio.
- Convertir texto existente en carta formal.
- Crear informe con titulo, secciones y cierre.
- Verificar que no se pegan sugerencias de formato.

### 3. Buscar y reemplazar inteligente

Estado: implementado inicial.

Notas:

- Se agrego accion Writer `replace_text`.
- Valida reemplazos concretos con `find`, `replace` y `match_case`.
- Aplica reemplazos sobre el documento activo y se integra con `deshacer`.
- Por ahora no usa regex ni condiciones por seccion/titulo.

Agregar accion Writer para reemplazos dirigidos sin reescribir todo.

Contrato propuesto:

```json
{
  "action": "replace_text",
  "summary": "Cambia destinatario",
  "replacements": [
    {"find": "Mi amor:", "replace": "Laura:"}
  ]
}
```

Comportamiento esperado:

- El modelo propone reemplazos concretos.
- La validacion limita cantidad y longitud.
- La aplicacion reemplaza coincidencias en el documento activo.
- La propuesta muestra que textos se van a reemplazar.

Archivos principales:

- `actions.py`: validar `replace_text`.
- `writer_ops.py`: aplicar reemplazos.
- `skills.py`: instruir cuando usar `replace_text`.

Pruebas:

- Cambiar destinatario de una carta sin seleccionar.
- Reemplazar nombre en todo el documento.
- Rechazar reemplazos vacios o demasiado amplios.

### 4. Revisor sin modificar

Estado: implementado inicial.

Notas:

- Se agrego skill Writer `writer_review`.
- Pedidos como `revisa`, `que errores tiene`, `que mejorarias`, `sin modificar` responden en chat.
- No genera JSON ni propuesta pendiente.
- El router evalua revision antes de acciones para evitar modificaciones accidentales.

Agregar modo de revision que no aplica cambios.

Pedidos esperados:

- “revisa este documento”;
- “que puedo mejorar”;
- “hay errores o inconsistencias”;
- “detecta placeholders”.

Salida esperada:

- Problemas encontrados.
- Recomendaciones.
- Riesgos.
- Propuesta opcional de cambio si el usuario pide aplicar.

Archivos principales:

- `skills.py`: skill `writer_review`.
- `panel.py`: enrutar revision como chat, no como accion.

Pruebas:

- Revisar carta con placeholders.
- Revisar texto con errores.
- Confirmar que no queda propuesta pendiente si solo se pidio revision.

## Prioridad 3 - Calc Como Copiloto de Planillas

## Prioridad 2.5 - Writer Datos Faltantes

### Detector de placeholders y datos faltantes

Estado: implementado inicial.

Notas:

- Writer detecta placeholders locales como `[Nombre]`, `{Fecha}`, `<Email>` y campos genericos frecuentes.
- El contexto Writer incluye `placeholders`.
- Pedidos como `detecta placeholders`, `que datos faltan` o `campos pendientes` responden sin modificar.
- Pedidos como `completa [Nombre] con Laura` se enrutan como accion aplicable mediante `replace_text`.
- Las sugerencias contextuales priorizan campos faltantes cuando el documento tiene placeholders.

### Formato por estructura

Estado: implementado inicial.

Notas:

- Se agrego accion Writer `format_document`.
- Aplica formato estructural al documento completo sin cambiar el texto.
- Detecta de forma local primer parrafo como titulo, lineas tipo asunto/subtitulo, cuerpo y firma.
- Soporta modos `professional`, `letter`, `report` y `minimal`.
- Usa estilos/parrafo, fuente, alineacion, interlineado y margenes de pagina.

### 5. Crear hoja completa desde cero

Estado: implementado inicial.

Notas:

- Se agrego skill Calc `calc_sheet_builder`.
- Desde una celda unica, el panel permite un area generada controlada de hasta 30 filas x 12 columnas.
- La IA puede crear encabezados, formulas, totales y formato dentro de esa area.
- Todavia no crea hojas nuevas con nombre ni graficos; trabaja desde la celda seleccionada.

Agregar skill para generar planillas completas.

Casos iniciales:

- presupuesto;
- inventario;
- cronograma;
- flujo de caja;
- control de gastos;
- tablero KPI simple.

Comportamiento esperado:

- Si la seleccion esta vacia o es una celda inicial, crear estructura desde ahi.
- Generar encabezados, formulas, totales y formato.
- Mantener cambios dentro de un rango razonable calculado localmente.

Contrato:

- Reutilizar `changes` por celda.
- Agregar soporte futuro para `sheet_name` si se crea hoja nueva.

Archivos principales:

- `skills.py`: skill `calc_sheet_builder`.
- `calc_ops.py`: helpers para rango destino ampliado.
- `actions.py`: validar rango generado.

Pruebas:

- Crear presupuesto mensual desde A1.
- Crear inventario simple.
- Crear flujo de caja con formulas.

### 6. Duplicados y limpieza guiada

Estado: implementado inicial.

Notas:

- El contexto Calc ahora incluye `duplicate_rows` y `duplicate_values`.
- Se agrego skill `calc_duplicate_finder`.
- La accion marca duplicados/faltantes con formato o notas dentro del rango permitido.
- No borra filas ni columnas.

Agregar deteccion y accion de duplicados.

Comportamiento esperado:

- Detectar filas duplicadas o valores repetidos.
- No borrar filas automaticamente en v1.
- Marcar duplicados con color o columna auxiliar.
- Proponer normalizaciones seguras.

Archivos principales:

- `calc_ops.py`: analizar duplicados.
- `skills.py`: skill `calc_duplicate_finder`.
- `actions.py`: validar marcas/formato.

Pruebas:

- Detectar duplicados en columna.
- Marcar duplicados sin borrar.
- Probar rango sin duplicados.

### 7. Conciliacion bancaria inicial

Estado: implementado inicial.

Notas:

- El contexto Calc ahora incluye `bank_reconciliation` con columnas candidatas de fecha, descripcion, importe y estado.
- Detecta posibles coincidencias por importe absoluto en `amount_matches`.
- Se agrego skill `calc_bank_reconciliation`.
- La accion marca estados como Conciliado, Revisar, Pendiente o Diferencia dentro del rango seleccionado.
- No borra, no mueve filas y no crea conciliaciones fuera de `allowed_cells`.

Agregar skill orientada a contador/administracion.

Comportamiento esperado:

- Comparar dos columnas o dos tablas: fecha, descripcion, importe.
- Detectar coincidencias exactas y diferencias.
- Marcar posibles conciliaciones.
- No eliminar datos.

Archivos principales:

- `skills.py`: skill `calc_bank_reconciliation`.
- `calc_ops.py`: contexto enriquecido para tablas.
- `actions.py`: permitir marcas y columnas auxiliares dentro del rango permitido.

Pruebas:

- Conciliar extracto vs libro.
- Marcar diferencias.
- Detectar importes iguales con descripcion distinta.

## Prioridad 4 - Experiencia de Chat

### 8. Sugerencias contextuales

Estado: implementado inicial.

Notas:

- El panel muestra hasta 3 sugerencias en el chat segun contexto activo.
- Detecta Writer vacio, Writer con seleccion, Writer con documento, Calc celda unica, Calc tabla y Calc con formulas.
- Evita repetir las mismas sugerencias con una clave de contexto.
- No agrega botones nuevos.

Mostrar sugerencias segun documento activo.

Ejemplos:

- Writer con carta: “hacer mas formal”, “dirigir a otra persona”, “mejorar formato”.
- Writer vacio: “crear carta”, “crear informe”, “crear CV”.
- Calc con tabla: “analizar tabla”, “detectar duplicados”, “formatear encabezados”.

Implementacion:

- No agregar botones grandes.
- Mostrar 2 o 3 sugerencias en el chat inicial o luego de leer contexto.
- El usuario puede copiarlas/escribirlas.

Archivos principales:

- `panel.py`: generar mensajes de sugerencias.
- `skills.py`: helpers de intencion.

Pruebas:

- Abrir Writer vacio.
- Abrir Writer con texto.
- Abrir Calc con tabla.

### 9. Historial de acciones

Estado: implementado inicial.

Notas:

- Se agrego historial local de acciones aplicadas en la sesion.
- Comandos soportados: `historial`, `historial de acciones`, `que hiciste`, `ultimos cambios`.
- Muestra hasta las ultimas 10 acciones con tipo, resumen y cantidad de cambios.

Mostrar que se aplico y cuando.

Comportamiento esperado:

- Luego de aplicar: resumen breve.
- Comando: `historial`.
- Mostrar ultimas acciones de la sesion.

Archivos principales:

- `panel.py`: lista `action_history`.

Pruebas:

- Aplicar dos cambios y pedir historial.
- Confirmar que no incluye API keys ni contenido sensible largo.

## Prioridad 5 - Empaquetado y Distribucion

### 10. Extension `.oxt`

Convertir el macro actual en extension instalable.

Objetivos:

- Instalar desde LibreOffice Extension Manager.
- Incluir comando de menu o toolbar.
- Mantener Python + UNO.
- Preparar estructura para una futura sidebar nativa.

Tareas:

- Crear `description.xml`.
- Crear `META-INF/manifest.xml`.
- Definir entrypoints.
- Empaquetar scripts.
- Documentar instalacion.

Pruebas:

- Instalar en perfil limpio.
- Abrir Calc y Writer.
- Ejecutar Libre Asist desde menu.
- Confirmar que config persiste.

## Prioridad 6 - Nuevas Funciones Writer

### 11. Listas (viñetas, numeradas, multinivel)

Estado: implementado.

Pedidos esperados:

- "convertir esto en lista";
- "numerar estos pasos";
- "agregar viñetas";
- "lista multinivel con guiones".

Contrato propuesto:

```json
{
  "action": "apply_list",
  "summary": "Aplica lista numerada a la seleccion",
  "style": {
    "list_style": "number",
    "start_at": 1,
    "level": 0
  }
}
```

Comportamiento esperado:

- Si hay seleccion, aplica el tipo de lista a los parrafos seleccionados.
- Si no hay seleccion, no aplica nada y avisa al usuario.
- `list_style` puede ser `bullet`, `number` u `outline`.
- `level` controla el nivel de anidamiento (0-10).
- No modifica el texto; solo cambia propiedades de parrafo.

Archivos principales:

- `actions.py`: nueva validacion `_validate_writer_list_style` y entrada en `validate_writer_preview`.
- `writer_ops.py`: nueva funcion `apply_list(doc, style)` usando `com.sun.star.text.NumberingRules` y propiedades `NumberingIsNumber` + `NumberingLevel` + `ParaStyleName` (`List Number`, `List Bullet`).
- `skills.py`: nueva skill `writer_lists` + keywords en `writer_preview`.

Pruebas:

- Convertir parrafos a lista numerada.
- Convertir lista a viñetas.
- Aplicar multinivel de dos niveles.
- Rechazar `level` fuera de rango.

### 12. Transformaciones de texto

Estado: implementado (via IA).

Pedidos esperados:

- "mayusculas";
- "minusculas";
- "tipo titulo";
- "capitalizar";
- "invertir caso".

Comportamiento esperado:

- Resolucion local, sin llamar al modelo.
- Aplica `upper`, `lower`, `title`, `sentence` o `capitalize` sobre la seleccion o el documento completo.
- Se integra con `deshacer` como cualquier otra accion.
- El router de `panel.py` detecta el keyword antes de invocar la IA.

Archivos principales:

- `panel.py`: nuevo handler `_handle_text_transform(prompt)` previo a la llamada a la IA.
- `writer_ops.py`: nueva funcion `transform_selection_or_document(doc, mode)`.
- `actions.py`: contrato de transformacion (validar `mode` y modo de aplicacion).

Pruebas:

- Convertir seleccion a mayusculas.
- Convertir documento completo a tipo titulo.
- Pedir transformacion con documento vacio.

### 13. Estadisticas del documento o seleccion

Estado: implementado.

Pedidos esperados:

- "cuantas palabras tiene";
- "caracteres de la seleccion";
- "tiempo de lectura";
- "estadisticas del documento".

Comportamiento esperado:

- Resolucion local usando `doc.WordCount` o contando `getString()` de la seleccion.
- Muestra en chat: palabras, caracteres con y sin espacios, parrafos, oraciones estimadas, tiempo de lectura (200 ppm por defecto).
- No modifica el documento.
- Sin llamada a la IA.

Archivos principales:

- `panel.py`: nuevo handler `_handle_statistics(ctx)`.
- `writer_ops.py`: helper `get_text_stats(doc, selection_text)`.

Pruebas:

- Contar palabras en seleccion de 1 parrafo.
- Contar palabras en documento vacio.
- Mostrar tiempo de lectura estimado.

### 14. Hipervinculos

Estado: implementado.

Pedidos esperados:

- "vincular 'X' a https://ejemplo.com";
- "agregar enlace al final";
- "convertir esta palabra en link".

Contrato propuesto:

```json
{
  "action": "insert_hyperlink",
  "summary": "Inserta hipervinculo",
  "text": "Sitio oficial",
  "url": "https://ejemplo.com"
}
```

O aplicar a la seleccion:

```json
{
  "action": "insert_hyperlink",
  "summary": "Convierte seleccion en hipervinculo",
  "url": "https://ejemplo.com",
  "apply_to_selection": true
}
```

Comportamiento esperado:

- Si `apply_to_selection` es true y hay seleccion, aplica el enlace al texto seleccionado.
- Si no, inserta el texto + enlace en el cursor.
- Valida que la URL no este vacia y tenga formato basico (http/https/mailto).

Archivos principales:

- `actions.py`: nueva validacion `_validate_writer_hyperlink`.
- `writer_ops.py`: `insert_hyperlink(doc, text, url, apply_to_selection)` usando `com.sun.star.text.TextField` tipo `HyperlinkURL` o `Hyperlink`.
- `skills.py`: skill `writer_hyperlink` + keywords en `writer_preview`.

Pruebas:

- Insertar enlace en cursor vacio.
- Convertir seleccion en enlace.
- Rechazar URL vacia o mal formada.

### 15. Insertar y editar tablas

Estado: implementado.

Pedidos esperados:

- "crear tabla de 3x4 con encabezados Producto, Precio, Stock";
- "agregar fila a la tabla";
- "agregar columna Cantidad";
- "eliminar ultima fila".

Contrato propuesto:

```json
{
  "action": "insert_table",
  "summary": "Inserta tabla con datos",
  "rows": 4,
  "cols": 3,
  "headers": ["Producto", "Precio", "Stock"],
  "rows_data": [
    ["Teclado", "15000", "10"],
    ["Mouse", "5000", "25"]
  ],
  "style": {
    "header_background": "#D9EAF7",
    "header_bold": true,
    "column_widths": [3000, 2500, 2000],
    "borders": true
  }
}
```

Comportamiento esperado:

- Si el cursor esta en una tabla existente y se pide "agregar fila/columna", modifica la tabla actual.
- Si no, crea una nueva tabla en el cursor.
- Tamanio maximo razonable: 50 filas x 20 columnas.
- Limitar texto por celda (ej. 500 caracteres).

Archivos principales:

- `actions.py`: nueva validacion `_validate_writer_table` con limites.
- `writer_ops.py`: `insert_table(doc, rows, cols, headers, rows_data, style)` usando `com.sun.star.text.TextTable` con `initialize(rows, cols)` + setear celdas.
- `writer_ops.py`: `modify_table(doc, operation, ...)` para agregar fila/columna.
- `skills.py`: skill `writer_tables` + keywords en `writer_preview`.

Pruebas:

- Crear tabla 3x3 con datos.
- Crear tabla solo con encabezados.
- Rechazar tabla fuera de limites.
- Verificar bordes y formato de encabezado.

### 16. Encabezado, pie de pagina y numeros de pagina

Estado: implementado.

Pedidos esperados:

- "agregar encabezado con el titulo del documento";
- "numerar paginas";
- "pie con la fecha";
- "encabezado solo en la primera pagina".

Contrato propuesto:

```json
{
  "action": "set_header_footer",
  "summary": "Configura encabezado y pie",
  "header": {
    "text": "Mi documento",
    "alignment": "center"
  },
  "footer": {
    "text": "{{date}}",
    "alignment": "right",
    "page_numbers": true
  },
  "first_page_different": false
}
```

Comportamiento esperado:

- Si `header` o `footer` existen, los crea o actualiza en el `PageStyle` activo.
- `{{date}}` se reemplaza con un campo de fecha automatico.
- `page_numbers` inserta un campo `PageNumber`.
- `first_page_different` habilita encabezado/pie separado en la primera pagina.

Archivos principales:

- `actions.py`: nueva validacion `_validate_writer_header_footer`.
- `writer_ops.py`: `set_header_footer(doc, header, footer, first_page_different)` usando `PageStyle.HeaderText` / `FooterText` + `PageStyle.HeaderTextLeft/Right/First`.
- `skills.py`: skill `writer_header_footer` + keywords en `writer_preview`.

Pruebas:

- Agregar encabezado centrado.
- Agregar pie con numero de pagina.
- Habilitar primera pagina diferente.
- Limpiar encabezado existente.

### 17. Notas al pie y notas al final

Estado: implementado.

Pedidos esperados:

- "agregar nota al pie donde dice X";
- "insertar cita al final del parrafo".

Contrato propuesto:

```json
{
  "action": "insert_footnote",
  "summary": "Inserta nota al pie",
  "marker_text": "X",
  "note_text": "Aclaracion sobre X"
}
```

Variantes: `insert_endnote` con la misma estructura.

Comportamiento esperado:

- Busca `marker_text` en el documento (o la seleccion) y coloca el cursor ahi.
- Inserta la nota al pie (o al final) con el texto indicado.
- Si `marker_text` no se encuentra, avisa al usuario.

Archivos principales:

- `actions.py`: nueva validacion para `insert_footnote` / `insert_endnote`.
- `writer_ops.py`: `insert_footnote(doc, marker_text, note_text)` usando `com.sun.star.text.Footnote` + `Footnote.createInstance()`.
- `skills.py`: skill `writer_notes` + keywords en `writer_preview`.

Pruebas:

- Insertar nota al pie con marcador existente.
- Insertar nota al final del documento.
- Rechazar marcador no encontrado.

### 18. Comandos rapidos de formato (sin IA)

Estado: implementado.

Pedidos esperados:

- "centrar esto";
- "justificar";
- "sangria francesa";
- "espacio doble";
- "quitar formato";
- "agregar espacio 1.5".

Comportamiento esperado:

- Resolucion local, sin llamar al modelo.
- Mapeo directo keyword a propiedades de parrafo (`ParaAdjust`, `ParaFirstLineIndent`, `ParaLineSpacing`, `ParaStyleName="Default Paragraph Style"`).
- Se integra con `deshacer`.
- El router detecta antes de invocar la IA.

Archivos principales:

- `panel.py`: nuevo handler `_handle_format_shortcut(prompt, ctx)` con tabla de mapeos.
- `writer_ops.py`: nueva funcion `apply_format_shortcut(doc, shortcut)`.

Pruebas:

- Centrar parrafo seleccionado.
- Aplicar interlineado 1.5.
- Quitar formato y volver a `Default Paragraph Style`.

### 19. Cambiar tono o voz del texto

Estado: implementado.

Pedidos esperados:

- "hacerlo mas formal";
- "mas persuasivo";
- "mas tecnico";
- "mas amigable";
- "tono academico".

Comportamiento esperado:

- Reutiliza `writer_rewrite` con un parametro `tone` que se inyecta en el prompt.
- Tonos soportados: `formal`, `informal`, `persuasive`, `technical`, `friendly`, `academic`, `casual`.
- Cero cambios en `actions.py` ni en el contrato JSON; solo afecta el prompt en `skills.py`.
- Si hay seleccion usa `replace_selection`; si no, `replace_document` (mismas reglas que ya estan).

Archivos principales:

- `skills.py`: nueva skill `writer_tone(prompt, ctx, tone)` que envuelve `writer_rewrite`.
- `panel.py`: router detecta keyword de tono y mapea al parametro.

Pruebas:

- Reescribir seleccion en tono formal.
- Reescribir documento en tono persuasivo.
- Verificar que se usa la accion correcta segun haya seleccion o no.

### 20. Exportar a PDF / DOCX / ODT / TXT

Estado: implementado.

Pedidos esperados:

- "exportar a PDF";
- "guardar como DOCX";
- "exportar a TXT".

Contrato propuesto:

```json
{
  "action": "export_document",
  "summary": "Exporta el documento a PDF",
  "format": "pdf",
  "path": "/ruta/opcional.pdf"
}
```

Comportamiento esperado:

- `format` puede ser `pdf`, `docx`, `odt`, `txt`.
- Si `path` esta vacio, abrir el dialogo `Save As` de LibreOffice con el filtro correcto.
- Si `path` tiene valor, usar `storeToURL` con el `MediaType` correspondiente:
  - `application/pdf`
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
  - `application/vnd.oasis.opendocument.text`
  - `text/plain`
- No modifica el documento.
- Devuelve mensaje con la ruta final.

Archivos principales:

- `actions.py`: nueva validacion `_validate_writer_export`.
- `writer_ops.py`: `export_document(doc, format, path)` usando `storeToURL`.
- `skills.py`: skill `writer_export` + keywords en `writer_preview`.

Pruebas:

- Exportar a PDF con ruta explicita.
- Exportar a DOCX.
- Rechazar formato no soportado.
- Verificar que el archivo se genera en la ruta correcta.

### 21. Conversion Markdown a Writer (y viceversa)

Estado: implementado.

Pedidos esperados:

- "convertir este Markdown a Writer";
- "pegar este Markdown como documento";
- "convertir documento a Markdown".

Comportamiento esperado:

- Parser Markdown propio (sin dependencias externas) que soporte: headings (`#`, `##`, `###`), listas (`-`, `*`, `1.`), negrita (`**`), cursiva (`*`), code (`` ` ``), links (`[texto](url)`), parrafos y saltos de linea.
- Salida: `insert_text` con `blocks` y estilos equivalentes (Heading 1/2/3, List Bullet, List Number, negrita/cursiva).
- Para "convertir a Markdown", el resultado se devuelve en chat (no se modifica el documento).
- Solo aplica a Writer; Calc no se ve afectado.

Archivos principales:

- `actions.py`: nueva validacion para `insert_markdown` con `markdown_text` y `mode` (`replace_document` | `insert_text` | `append_text`).
- `writer_ops.py`: nuevo modulo `markdown_parser.py` (o funcion interna) que convierte MD a lista de `blocks` Writer.
- `writer_ops.py`: `markdown_to_writer(doc, markdown_text, mode)` reutilizando `_insert_blocks_at_cursor` / `replace_document_with_blocks`.
- `skills.py`: skill `writer_markdown` + keywords en `writer_preview`.

Pruebas:

- Convertir "# Titulo\n- item 1\n- item 2" a Writer.
- Convertir parrafo con **negrita** y *cursiva*.
- Convertir documento Writer a Markdown y mostrar en chat.
- Rechazar markdown vacio o muy largo.

### 22. Corrector ortografico del documento

Estado: implementado.

Pedidos esperados:

- "revisar ortografia";
- "que palabras estan mal escritas";
- "corregir errores ortograficos".

Comportamiento esperado:

- Usa `com.sun.star.linguistic2.ProofreadingIterator` o el `SpellChecker` de UNO.
- Lista en chat los terminos dudosos con contexto (parrafo + oracion).
- Si el usuario confirma "corregir", propone una accion `replace_text` con los reemplazos validos (palabras marcadas con sugerencias del diccionario).
- Solo aplica a Writer; usa el idioma del documento.

Archivos principales:

- `writer_ops.py`: `find_spelling_issues(doc, locale)` retorna lista de `{word, suggestions, paragraph_index}`.
- `panel.py`: handler `_handle_spell_check` que muestra resultados y, si el usuario confirma, prepara propuesta `replace_text`.
- `skills.py`: skill `writer_spellcheck` (modo chat) + comando para aplicar.

Pruebas:

- Detectar palabra mal escrita conocida.
- Detectar en documento vacio.
- Confirmar que la propuesta usa `replace_text` y respeta `match_case`.

### 23. Resumen ejecutivo en bullets

Estado: implementado.

Pedidos esperados:

- "dame los puntos clave";
- "resumen en bullets";
- "puntos principales".

Comportamiento esperado:

- Variante de `writer_summarize` con `format="bullets"`.
- Solo cambia el prompt; sin tocar Writer ni el contrato.
- Mantiene el resto del flujo (seleccion vs documento completo, no modifica).

Archivos principales:

- `skills.py`: nuevo helper `writer_bullet_summary(ctx)` que reutiliza la logica de `writer_summarize` con prompt adaptado.
- `panel.py`: router detecta keywords de resumen en bullets.

Pruebas:

- Resumir seleccion en 5 bullets.
- Resumir documento completo.
- Verificar que no se genera propuesta aplicable.

### 24. Plantillas explicitas de documentos

Estado: mencionado en el plan original, todavia no implementado de forma centralizada.

Plantillas objetivo:

- carta formal;
- carta informal;
- carta de amor;
- reclamo;
- email profesional;
- CV simple;
- informe;
- minuta de reunion;
- propuesta comercial.

Comportamiento esperado:

- Skill `writer_template` que recibe un `template_id` y un `mode` (`new` | `from_existing`).
- Si el documento esta vacio y `mode=new`, usa `insert_text` con `blocks` y `page_style`.
- Si el documento tiene contenido y `mode=from_existing`, usa `replace_document`.
- Esqueleto de cada plantilla centralizado en `skills.py` (no en prompts sueltos).
- Sin llamada a la IA para generar el esqueleto: solo el contenido concreto del usuario (nombre, destinatario, motivo) se obtiene del chat.

Archivos principales:

- `skills.py`: diccionario `TEMPLATES` con bloques y `page_style` por plantilla.
- `skills.py`: nueva skill `writer_template(template_id, ctx, mode)`.
- `panel.py`: router detecta "crea una carta de...", "redacta un reclamo...", etc. y mapea a `template_id`.

Pruebas:

- Crear carta formal desde documento vacio.
- Convertir texto libre en una minuta (replace_document).
- Verificar que el formato se aplica correctamente (margenes, estilo de titulos).
- Verificar que no se pega texto de formato dentro de los bloques.

### 25. Seguimiento de cambios (Track Changes)

Estado: implementado.

Pedidos esperados:

- "activar control de cambios";
- "desactivar control de cambios";
- "mostrar mis cambios";
- "aceptar todos los cambios".

Comportamiento esperado:

- Accion simple sobre `doc.RecordChanges` y `doc.IsRedlineProtected`.
- Para "mostrar mis cambios", consulta `doc.TextSections` / `Redline` o enumera `RedlineText` y devuelve resumen en chat.
- "Aceptar todos" usa `doc.acceptAllRedlines()` (sin pedir confirmacion si lo pidio el usuario).
- Se integra con `deshacer` cuando es posible.

Archivos principales:

- `actions.py`: nueva validacion para `track_changes` con `enabled` y `protect`.
- `writer_ops.py`: `set_track_changes(doc, enabled, protect)` + `accept_all_changes(doc)` + `get_redlines_summary(doc)`.
- `skills.py`: skill `writer_track_changes` + keywords en `writer_preview`.

Pruebas:

- Activar y desactivar.
- Verificar que nuevos cambios se registran como redlines.
- Aceptar todos los cambios de un documento con redlines.

### 26. Comentarios y anotaciones Writer

Estado: implementado inicial.

Pedidos esperados:

- "agregá comentarios de revisión";
- "comentá este párrafo";
- "dejá anotaciones sobre problemas";
- "insertá comentarios sin cambiar el texto".

Comportamiento esperado:

- No modifica el texto del documento.
- Inserta comentarios/anotaciones Writer usando `insert_comment`.
- Si hay selección, ancla el comentario a la selección.
- Si no hay selección, busca `marker_text` exacto en el documento.
- Si no encuentra marcador, ancla en el cursor.
- Requiere confirmación conversacional antes de aplicar.

Archivos principales:

- `skills_writer.py`: skill `writer_comments`.
- `actions.py`: validación `insert_comment`.
- `writer_ops.py`: `insert_comments()`.

## Roadmap Calc Avanzado - Conciliacion, Auditoria y Resumenes

Objetivo:

- Convertir Calc en un asistente de analisis, conciliacion y auditoria de planillas, con foco contable/administrativo.
- Mantener confirmacion conversacional antes de modificar cualquier celda.
- Priorizar acciones explicables, reversibles y validadas localmente.

### 26. Conciliacion bancaria avanzada

Estado: implementado inicial.

Pedidos esperados:

- "conciliá banco contra libro";
- "marcá movimientos conciliados";
- "buscá diferencias entre extracto y contabilidad";
- "detectá pendientes de conciliación";
- "conciliá con tolerancia de 1 peso y 3 días".

Comportamiento esperado:

- Detectar columnas probables: fecha, descripcion/concepto, debito, credito, importe, saldo, comprobante, estado.
- Comparar banco vs libro dentro de la seleccion o entre dos rangos/hojas cuando sea posible.
- Soportar tolerancias por importe y fecha.
- Marcar estados: `Conciliado`, `Diferencia`, `Duplicado`, `Pendiente`, `Revisar`.
- Si no existe columna de estado, proponer crear una dentro del rango permitido o usar colores.
- Mostrar resumen: total conciliado, total pendiente, diferencias, duplicados y casos para revisar.

Archivos principales:

- `calc_ops.py`: enriquecer deteccion de columnas financieras y candidatos de conciliacion.
- `skills_calc.py`: nueva skill `calc_reconciliation_advanced`.
- `actions.py`: validar cambios de estado/formato sin borrar ni mover datos.

Notas de implementacion inicial:

- El contexto incluye `bank_reconciliation.suggested_pairs` con pares de importes repetidos u opuestos.
- La IA debe usar esos pares como candidatos, no como conciliacion definitiva.

### 27. Auditoria de planillas Calc

Estado: implementado inicial.

Pedidos esperados:

- "auditá esta planilla";
- "detectá errores y riesgos";
- "revisá datos faltantes";
- "marcá problemas de calidad";
- "controlá totales".

Comportamiento esperado:

- Detectar celdas vacias en columnas obligatorias o de alta densidad.
- Detectar numeros como texto, fechas invalidas, importes negativos sospechosos y valores fuera de rango.
- Detectar filas duplicadas y claves repetidas.
- Detectar totales que no coinciden cuando haya filas de total.
- Devolver revision sin modificar cuando el usuario pida solo auditar.
- Si el usuario pide marcar, generar propuesta con colores/notas dentro del rango permitido.

Archivos principales:

- `calc_ops.py`: perfiles por columna, totales, inconsistencias y outliers.
- `skills_calc.py`: nueva skill `calc_audit_sheet`.
- `actions.py`: resumen legible de hallazgos marcados.

### 28. Auditoria de formulas Calc

Estado: implementado inicial.

Pedidos esperados:

- "auditá las fórmulas";
- "encontrá fórmulas rotas";
- "detectá fórmulas distintas en esta columna";
- "revisá referencias";
- "arreglá esta fórmula".

Comportamiento esperado:

- Listar formulas existentes y errores visibles.
- Detectar patrones por columna y marcar formulas que no siguen el patron.
- Detectar referencias rotas, rangos incompletos y formulas copiadas incorrectamente.
- Explicar la causa probable antes de proponer cambios.
- Proponer correcciones solo cuando sean seguras y dentro de `allowed_cells`.

Archivos principales:

- `calc_ops.py`: comparar formulas normalizadas por columna/fila.
- `skills_calc.py`: nueva skill `calc_formula_audit`.
- `actions.py`: validar que la formula corregida empiece con `=` y no salga del rango permitido.

Notas de implementacion inicial:

- El contexto incluye `formula_audit.suspect_cells` y `formula_audit.visible_errors`.
- Las formulas sospechosas se detectan comparando patrones normalizados por columna.

### 29. Tablas resumen y tablas dinamicas Calc

Estado: implementado inicial para tabla resumen con formulas/valores en hoja destino `Resumen IA`; DataPilot real queda pendiente para fase 2.

Pedidos esperados:

- "creá una tabla dinámica";
- "resumí ventas por mes y cliente";
- "armá reporte por categoría";
- "sumá importes por proveedor";
- "creá hoja de resumen".

Comportamiento esperado fase 1:

- Crear una hoja o bloque de resumen con formulas compatibles con Calc.
- Usar `SUMAR.SI.CONJUNTO`, `CONTAR.SI.CONJUNTO`, `PROMEDIO.SI.CONJUNTO` cuando aplique.
- Detectar dimensiones probables: fechas/mes, categoria, cliente, proveedor, estado.
- Detectar metricas probables: importe, cantidad, saldo, total.
- Formatear encabezados, totales y columnas importantes.

Comportamiento esperado fase 2:

- Investigar e implementar DataPilot/TablePilot real de LibreOffice cuando la API UNO sea estable en el entorno.
- Permitir filas, columnas, valores y filtros como configuracion derivada del pedido.
- Crear tabla dinamica en hoja nueva sin alterar datos fuente.

Archivos principales:

- `calc_ops.py`: crear hoja resumen, escribir formulas agregadas y eventualmente DataPilot.
- `skills_calc.py`: nueva skill `calc_summary_table_builder`.
- `actions.py`: permitir creacion controlada de bloques/hojas de resumen.

### 30. Perfilado de datos Calc

Estado: implementado inicial.

Pedidos esperados:

- "perfilá esta tabla";
- "decime qué columnas hay";
- "detectá tipos de datos";
- "mostrá resumen de calidad";
- "está lista para analizar?".

Comportamiento esperado:

- Para cada columna: tipo probable, vacios, unicos, duplicados, minimo, maximo, suma/promedio cuando sea numerica.
- Detectar encabezados, columna clave probable y columnas de fecha/importe/categoria.
- Devolver un reporte en chat sin modificar.
- Servir como contexto para auditoria, conciliacion y tablas resumen.

Archivos principales:

- `calc_ops.py`: perfiles estadisticos por columna.
- `skills_calc.py`: nueva skill `calc_profile_data`.

### 31. Reporte de auditoria Calc en hoja

Estado: implementado inicial.

Pedidos esperados:

- "creá reporte de auditoría";
- "crear informe de auditoria";
- "generá hoja de auditoría";
- "armá reporte con hallazgos".

Comportamiento esperado:

- Crear o actualizar hoja destino `Auditoria IA`.
- No modificar la tabla fuente.
- Usar hallazgos locales: `profile_summary.quality_findings`, `formula_audit`, duplicados, blancos y conciliacion.
- Escribir encabezados, resumen y tabla de hallazgos.
- Requiere confirmacion conversacional antes de aplicar.

Archivos principales:

- `skills_calc.py`: skill `calc_audit_report`.
- `calc_ops.py`: `audit_report_allowed_cells`.
- `panel.py`: permisos de escritura para hoja de auditoria.

## Criterios de Aceptacion Generales

- Ninguna modificacion se aplica sin confirmacion.
- Las acciones aplicables no muestran JSON crudo al usuario.
- Si el modelo devuelve JSON invalido, no se toca el documento.
- Si la accion es riesgosa, el resumen debe decir el alcance.
- Writer debe poder editar documento completo sin seleccion cuando haya contexto.
- Calc no debe modificar celdas fuera del rango permitido salvo acciones explicitamente disenadas para crear estructura.
- Los errores deben aparecer en el chat con mensajes claros.

## Orden Recomendado de Implementacion

1. Deshacer ultimo cambio.
2. Buscar y reemplazar inteligente en Writer.
3. Plantillas inteligentes Writer.
4. Crear hoja completa Calc.
5. Duplicados y limpieza guiada Calc.
6. Conciliacion bancaria inicial.
7. Revisor sin modificar.
8. Sugerencias contextuales.
9. Historial de acciones.
10. Auditoria avanzada Calc.
11. Tablas resumen Calc.
12. Empaquetado `.oxt`.

### Siguiente ola (Prioridad 6)

1. Listas (viñetas, numeradas, multinivel).
2. Transformaciones de texto sin IA.
3. Estadísticas del documento o selección.
4. Hipervínculos.
5. Insertar y editar tablas.
6. Encabezado, pie de página y números de página.
7. Notas al pie y notas al final.
8. Comandos rápidos de formato (sin IA).
9. Cambiar tono o voz del texto.
10. Exportar a PDF / DOCX / ODT / TXT.
11. Conversión Markdown ⇄ Writer.
12. Corrector ortográfico del documento.
13. Resumen ejecutivo en bullets.
14. Plantillas explícitas de documentos.
15. Seguimiento de cambios (Track Changes).

## Notas Tecnicas

- Mantener `AIClient.ask()` como unica entrada de IA por ahora.
- Seguir usando JSON por prompt + validacion local.
- Evitar dependencias externas hasta que el empaquetado `.oxt` este definido.
- No migrar a Java todavia; Python + UNO sigue siendo mejor para iterar rapido.
- Para Excel/Word se requeriria otra implementacion con Office.js; no reutiliza UNO.
