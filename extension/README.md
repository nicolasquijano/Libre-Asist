# Libre Asist - Extension para LibreOffice

Asistente de IA para LibreOffice Calc y Writer. Escribe en lenguaje natural y el asistente propone cambios para tu documento.

## Características

- **Calc**: Fórmulas, tablas dinámicas, formatos, análisis de datos, duplicados, conciliación bancaria
- **Writer**: Reescribir, formatear, listas, tablas, hipervínculos, notas al pie, exportar

## Instalación

### Opción 1: Archivo .oxt (Recomendado)

1. Descarga `libre_asist.oxt`
2. Abre LibreOffice (Calc o Writer)
3. Ve a **Herramientas > Extensiones > Gestor de extensiones**
4. Haz clic en **Agregar**
5. Selecciona el archivo `libre_asist.oxt`
6. Reinicia LibreOffice
7. Ve a **Herramientas > Macros > Ejecutar macro** y ejecuta `LibreAsist.show_panel`

### Opción 2: Instalación manual

1. Copia la carpeta `libre_asist` a:
   - Linux: `~/.config/libreoffice/4/user/Scripts/python/`
   - Windows: `%APPDATA%\LibreOffice\4\user\Scripts\python\`
   - macOS: `~/Library/Application Support/LibreOffice/4/user/Scripts/python/`

2. Configura una macro para ejecutar `libre_asist.show_panel`

## Configuración

1. Abre el panel de Libre Asist
2. Haz clic en el botón **Config**
3. Ingresa la URL de tu API de IA (OpenAI, Ollama, Anthropic, etc.)
4. Ingresa la clave API si es necesario
5. Haz clic en **Guardar**

## Uso

1. Abre un documento de Calc o Writer
2. Selecciona celdas o texto (opcional en Calc)
3. Escribe tu solicitud en lenguaje natural
4. El asistente propondrá cambios
5. Confirma con "si" o "confirmar"

## Idiomas

- Español (predeterminado)
- Inglés
- Chino

## Licencia

Mozilla Public License 2.0