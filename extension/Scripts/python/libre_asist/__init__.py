"""libre_asist - LibreOffice Python extension.

Entry points callable from the LO Basic IDE or via menu integration.
Or via the LO macro runner (Tools > Macros > Run Macro...).
"""

import sys
import os

try:
    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _THIS_DIR = os.path.dirname(os.path.abspath((lambda: 0).__code__.co_filename))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)


def show_panel(*args):
    import panel
    panel.show_panel()


def show_config_dialog(*args):
    import panel
    panel.show_config_dialog()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        fn_name = sys.argv[1]
        fn = globals().get(fn_name)
        if fn is not None:
            fn()
        else:
            print("Unknown function:", fn_name)
    else:
        print("Usage: python __init__.py {show_panel|show_config_dialog}")
