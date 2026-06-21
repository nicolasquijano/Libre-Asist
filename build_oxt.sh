#!/bin/bash
# Script para crear la extensión .oxt de Libre Asist
# Uso: ./build_oxt.sh (ejecutar desde el directorio principal)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Crear directorio temporal para copiar archivos
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copiar estructura base de la extensión
cp -r extension/META-INF "$TEMP_DIR/"
cp -r extension/description.xml "$TEMP_DIR/"
cp -r extension/registry "$TEMP_DIR/"

# Crear directorio para Scripts
mkdir -p "$TEMP_DIR/Scripts/python/libre_asist"

# Copiar archivos Python (excluyendo __pycache__)
find . -maxdepth 1 -name "*.py" -exec cp {} "$TEMP_DIR/Scripts/python/libre_asist/" \;

# Copiar directorio locale
cp -r locale "$TEMP_DIR/Scripts/python/libre_asist/"

# Crear el archivo .oxt
cd "$TEMP_DIR"
zip -r "$SCRIPT_DIR/libre_asist.oxt" . -x "*.DS_Store" -x "__pycache__/*" -x "*.pyc"

echo ""
echo "=========================================="
echo "Extensión creada: $SCRIPT_DIR/libre_asist.oxt"
echo "=========================================="
echo ""
echo "Para instalar:"
echo "1. Abre LibreOffice"
echo "2. Herramientas > Extensiones > Gestor de extensiones"
echo "3. Haz clic en 'Agregar' y selecciona libre_asist.oxt"
echo "4. Reinicia LibreOffice"