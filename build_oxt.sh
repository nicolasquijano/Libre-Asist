#!/bin/bash
# Script para crear la extension .oxt de Libre Asist
# Uso: ./build_oxt.sh (se ejecuta desde cualquier directorio)

# Cambiar al directorio del script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "Directorio de trabajo: $SCRIPT_DIR"

# Verificar que existen los archivos necesarios
if [ ! -d "extension" ]; then
    echo "Error: directorio 'extension' no encontrado en $SCRIPT_DIR"
    exit 1
fi

if [ ! -d "locale" ]; then
    echo "Error: directorio 'locale' no encontrado en $SCRIPT_DIR"
    exit 1
fi

# Crear directorio temporal para copiar archivos
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "Directorio temporal: $TEMP_DIR"

# Copiar estructura base de la extension
mkdir -p "$TEMP_DIR"
cp -r extension/META-INF "$TEMP_DIR/" 2>/dev/null || echo "Advertencia: META-INF no copiado"
cp extension/description.xml "$TEMP_DIR/" 2>/dev/null || echo "Advertencia: description.xml no copiado"
cp -r extension/registry "$TEMP_DIR/" 2>/dev/null || echo "Advertencia: registry no copiado"

# Crear directorio para Scripts
mkdir -p "$TEMP_DIR/Scripts/python/libre_asist"

# Copiar archivos Python (excluyendo __pycache__ y tests)
for pyfile in *.py; do
    if [ -f "$pyfile" ]; then
        case "$pyfile" in
            test_*) continue ;;
        esac
        cp "$pyfile" "$TEMP_DIR/Scripts/python/libre_asist/"
    fi
done

# Copiar directorio locale
cp -r locale "$TEMP_DIR/Scripts/python/libre_asist/"

# Copiar README si existe
if [ -f "README.md" ]; then
    cp README.md "$TEMP_DIR/"
fi

# Eliminar .oxt existente
rm -f "$SCRIPT_DIR/libre_asist.oxt"

# Crear el archivo .oxt
cd "$TEMP_DIR" || exit 1
zip -r "$SCRIPT_DIR/libre_asist.oxt" . -x "*.DS_Store" -x "__pycache__/*" -x "*.pyc" 2>&1 | tail -5

echo ""
echo "=========================================="
echo "Extension creada: $SCRIPT_DIR/libre_asist.oxt"
echo "=========================================="
echo ""
echo "Para instalar:"
echo "1. Abre LibreOffice"
echo "2. Herramientas > Extensiones > Gestor de extensiones"
echo "3. Haz clic en 'Agregar' y selecciona libre_asist.oxt"
echo "4. Reinicia LibreOffice"
