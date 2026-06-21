#!/bin/bash
# Script para crear la extensión .oxt de Libre Asist
# Uso: ./build.sh

EXTENSION_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$EXTENSION_DIR"

# Crear directorio temporal para copiar archivos
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Copiar estructura
cp -r extension/* "$TEMP_DIR/"

# Copiar archivos Python (excluyendo __pycache__)
find . -maxdepth 1 -name "*.py" -exec cp {} "$TEMP_DIR/Scripts/python/libre_asist/" \;

# Copiar directorio locale
cp -r locale "$TEMP_DIR/Scripts/python/libre_asist/"

# Crear el archivo .oxt
cd "$TEMP_DIR"
zip -r "$EXTENSION_DIR/libre_asist.oxt" . -x "*.DS_Store" -x "__pycache__/*" -x "*.pyc"

echo "Extension creada: $EXTENSION_DIR/libre_asist.oxt"
echo ""
echo "Para instalar:"
echo "1. Abre LibreOffice"
echo "2. Herramientas > Extensiones > Gestor de extensiones"
echo "3. Haz clic en 'Agregar' y selecciona libre_asist.oxt"
echo "4. Reinicia LibreOffice"