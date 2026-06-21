"""Internationalization: locale-aware string lookup."""

import json
import os

_LOCALE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")

_STRINGS = {}
_LANG = "es"


def detect_language():
    try:
        import uno
        ctx = uno.getComponentContext()
        cp = ctx.getByName(
            "/singletons/com.sun.star.deployment.PackageInformationProvider"
        )
        loc = cp.getImplementationLocale()
        return loc.split("-")[0].split("_")[0]
    except Exception:
        return "es"


def load(lang=None):
    global _STRINGS, _LANG
    if lang is None:
        lang = detect_language()
    _LANG = lang
    path = os.path.join(_LOCALE_DIR, f"{lang}.json")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            _STRINGS.clear()
            _STRINGS.update(json.load(f))


def _(key, *args, **kwargs):
    text = _STRINGS.get(key, key)
    if args or kwargs:
        return text.format(*args, **kwargs)
    return text


load()
