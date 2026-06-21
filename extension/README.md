# Libre Asist - LibreOffice Extension

AI assistant for LibreOffice Calc and Writer. Write in natural language and the assistant proposes changes to your document.

## Features

- **Calc**: Formulas, pivot tables, formatting, data analysis, duplicates, bank reconciliation
- **Writer**: Rewrite, format, lists, tables, hyperlinks, footnotes, export

## Installation

### Option 1: .oxt file (Recommended)

1. Download `libre_asist.oxt`
2. Open LibreOffice (Calc or Writer)
3. Go to **Tools > Extensions > Extension Manager**
4. Click **Add**
5. Select the `libre_asist.oxt` file
6. Restart LibreOffice
7. Go to **Tools > Macros > Run Macro** and execute `LibreAsist.show_panel`

### Option 2: Manual Installation

1. Copy the `libre_asist` folder to:
   - Linux: `~/.config/libreoffice/4/user/Scripts/python/`
   - Windows: `%APPDATA%\LibreOffice\4\user\Scripts\python\`
   - macOS: `~/Library/Application Support/LibreOffice/4/user/Scripts/python/`

2. Configure a macro to run `libre_asist.show_panel`

## Configuration

1. Open the Libre Asist panel
2. Click the **Config** button
3. Enter your AI API URL (OpenAI, Ollama, Anthropic, etc.)
4. Enter the API key if required
5. Click **Save**

## Usage

1. Open a Calc or Writer document
2. Select cells or text (optional in Calc)
3. Write your request in natural language
4. The assistant will propose changes
5. Confirm with "yes" or "confirm"

## Languages

- Spanish (default)
- English
- Chinese

## License

Mozilla Public License 2.0