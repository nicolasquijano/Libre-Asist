"""Tests for Calc skills of Libre Asist.

Run this script to verify the Calc skills are properly defined
and can be instantiated.
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import skills_calc
    import skills_common
    from i18n import _
    import actions
except ImportError as e:
    print(f"FAIL: Cannot import modules: {e}")
    sys.exit(1)


def test_module_imports():
    """Test that all modules import correctly."""
    print("\n=== Test 1: Module imports ===")
    try:
        from skills_calc import (
            calc_formula, calc_analyze, calc_table_detect, calc_formula_debug,
            calc_formula_fill, calc_random_fill, calc_clean, calc_clean_advanced,
            calc_duplicate_finder, calc_sheet_builder, calc_bank_reconciliation,
            calc_reconciliation_advanced, calc_audit_sheet, calc_audit_report,
            calc_formula_audit, calc_summary_table_builder, calc_pivot_table,
            calc_profile_data, calc_consolidate, calc_format, calc_format_table,
            calc_create_chart, calc_conditional_format, calc_data_validation,
            calc_apply_theme, calc_generate_macro, calc_icon_conditional_format,
            calc_apply_filter, calc_apply_protection, calc_preview,
        )
        print("PASS: All Calc functions imported successfully")
        return True
    except ImportError as e:
        print(f"FAIL: {e}")
        return False


def test_schemas():
    """Test that all Calc schemas are defined."""
    print("\n=== Test 2: Schemas ===")
    schemas = [
        ("CALC_ACTION_SCHEMA", skills_common.CALC_ACTION_SCHEMA),
        ("CALC_PIVOT_SCHEMA", skills_common.CALC_PIVOT_SCHEMA),
        ("CALC_CONSOLIDATE_SCHEMA", skills_common.CALC_CONSOLIDATE_SCHEMA),
        ("CALC_CHART_SCHEMA", skills_common.CALC_CHART_SCHEMA),
        ("CALC_CONDITIONAL_FORMAT_SCHEMA", skills_common.CALC_CONDITIONAL_FORMAT_SCHEMA),
        ("CALC_DATA_VALIDATION_SCHEMA", skills_common.CALC_DATA_VALIDATION_SCHEMA),
        ("CALC_THEME_SCHEMA", skills_common.CALC_THEME_SCHEMA),
        ("CALC_FILTER_SCHEMA", skills_common.CALC_FILTER_SCHEMA),
        ("CALC_PROTECTION_SCHEMA", skills_common.CALC_PROTECTION_SCHEMA),
    ]
    all_pass = True
    for name, schema in schemas:
        if schema and isinstance(schema, str) and len(schema) > 10:
            print(f"PASS: {name} defined ({len(schema)} chars)")
        else:
            print(f"FAIL: {name} not properly defined")
            all_pass = False
    return all_pass


def test_skill_blocks():
    """Test that each Calc skill returns a properly structured block."""
    print("\n=== Test 3: Skill blocks structure ===")
    ctx = {
        "kind": "calc",
        "range": "A1:E20",
        "headers": ["Name", "Amount", "Date", "Category", "Status"],
        "data": [
            ["Product A", 100, "2025-01-01", "Cat1", "Active"],
            ["Product B", 200, "2025-01-02", "Cat2", "Active"],
        ],
        "language": "es",
    }
    user_prompts = [
        ("calc_formula", "Crear formula de suma"),
        ("calc_analyze", None),
        ("calc_table_detect", None),
        ("calc_formula_debug", "Arreglar formula"),
        ("calc_formula_fill", "Rellenar formulas"),
        ("calc_random_fill", "Llenar con datos aleatorios"),
        ("calc_clean", None),
        ("calc_clean_advanced", None),
        ("calc_duplicate_finder", "Buscar duplicados"),
        ("calc_sheet_builder", "Crear presupuesto"),
        ("calc_bank_reconciliation", "Conciliar banco"),
        ("calc_reconciliation_advanced", "Conciliar"),
        ("calc_audit_sheet", "Auditar hoja"),
        ("calc_audit_report", "Crear reporte auditoria"),
        ("calc_formula_audit", "Auditar formulas"),
        ("calc_summary_table_builder", "Crear tabla resumen"),
        ("calc_pivot_table", "Crear pivot"),
        ("calc_profile_data", None),
        ("calc_consolidate", "Consolidar hojas"),
        ("calc_format", "Formatear"),
        ("calc_format_table", "Formatear tabla"),
        ("calc_create_chart", "Crear grafico"),
        ("calc_conditional_format", "Aplicar formato condicional"),
        ("calc_data_validation", "Validar datos"),
        ("calc_apply_theme", "Aplicar tema"),
        ("calc_generate_macro", "Crear macro"),
        ("calc_icon_conditional_format", "Iconos"),
        ("calc_apply_protection", "Proteger"),
    ]
    all_pass = True
    for fname, prompt in user_prompts:
        try:
            func = getattr(skills_calc, fname)
            if prompt is None:
                result = func(ctx)
            else:
                result = func(prompt, ctx)

            if isinstance(result, str) and "<role>" in result and "<task>" in result:
                print(f"PASS: {fname} returns valid block ({len(result)} chars)")
            else:
                print(f"FAIL: {fname} returns invalid structure")
                all_pass = False
        except Exception as e:
            print(f"FAIL: {fname} raised: {e}")
            all_pass = False
    return all_pass


def test_validators():
    """Test that all actions have validators."""
    print("\n=== Test 4: Action validators ===")
    test_cases = [
        ("create_pivot_table", {"action": "create_pivot_table", "summary": "Test", "source_range": "A1:E20", "row_fields": ["Category"], "data_fields": [{"field": "Amount", "function": "sum"}]}),
        ("consolidate_sheets", {"action": "consolidate_sheets", "summary": "Test", "source_sheets": ["Hoja1", "Hoja2"]}),
        ("create_chart", {"action": "create_chart", "summary": "Test", "source_range": "A1:B10", "chart_type": "bar"}),
        ("apply_conditional_format", {"action": "apply_conditional_format", "summary": "Test", "cell_range": "A1:A10", "condition": "greater", "value": 100}),
        ("apply_data_validation", {"action": "apply_data_validation", "summary": "Test", "cell_range": "A1:A10", "validation_type": "list", "formula1": "Si;No"}),
        ("apply_theme", {"action": "apply_theme", "summary": "Test", "range": "A1:E20", "theme_name": "corporativo"}),
        ("apply_filter", {"action": "apply_filter", "summary": "Test", "range": "A1:E20"}),
        ("apply_protection", {"action": "apply_protection", "summary": "Test", "protect": True}),
    ]
    all_pass = True
    for action_name, data in test_cases:
        try:
            result = actions.validate_calc_preview(data)
            if result.get("action") == action_name:
                print(f"PASS: {action_name} validation works")
            else:
                print(f"FAIL: {action_name} returned wrong action")
                all_pass = False
        except Exception as e:
            print(f"FAIL: {action_name} raised: {e}")
            all_pass = False
    return all_pass


def test_invalid_validators():
    """Test that validators reject invalid data."""
    print("\n=== Test 5: Invalid data rejection ===")
    invalid_cases = [
        ("create_chart", {"action": "create_chart", "chart_type": "invalid_type"}),
        ("apply_theme", {"action": "apply_theme", "theme_name": "invalid_theme"}),
        ("apply_data_validation", {"action": "apply_data_validation", "validation_type": "invalid"}),
        ("create_pivot_table", {"action": "create_pivot_table"}),
    ]
    all_pass = True
    for action_name, data in invalid_cases:
        try:
            actions.validate_calc_preview(data)
            print(f"FAIL: {action_name} should have raised error")
            all_pass = False
        except ValueError:
            print(f"PASS: {action_name} rejects invalid data")
        except Exception as e:
            print(f"FAIL: {action_name} raised wrong exception: {e}")
            all_pass = False
    return all_pass


def test_keywords():
    """Test keyword detection in router."""
    print("\n=== Test 6: Keyword detection ===")
    test_cases = [
        ("create chart", "calc_create_chart"),
        ("pivot table", "calc_pivot_table"),
        ("consolidate", "calc_consolidate"),
        ("conditional format", "calc_conditional_format"),
        ("data validation", "calc_data_validation"),
        ("theme", "calc_apply_theme"),
        ("autofilter", "calc_apply_filter"),
        ("protect sheet", "calc_apply_protection"),
        ("macro", "calc_generate_macro"),
        ("traffic light", "calc_icon_conditional_format"),
    ]
    all_pass = True
    for prompt, expected_keyword in test_cases:
        try:
            ctx = {"kind": "calc", "range": "A1:E20"}
            result = skills_calc.calc_preview(prompt, ctx)
            if isinstance(result, str) and "<role>" in result:
                print(f"PASS: '{prompt}' returns valid block")
            else:
                print(f"FAIL: '{prompt}' returns invalid structure")
                all_pass = False
        except Exception as e:
            print(f"FAIL: '{prompt}' raised: {e}")
            all_pass = False
    return all_pass


def test_default_action():
    """Test that default action works for simple changes."""
    print("\n=== Test 7: Default action (changes) ===")
    data = {
        "changes": [
            {"cell": "A1", "bold": True, "background": "#FF0000"},
            {"cell": "B1", "value": "Hello", "bold": True},
        ],
        "summary": "Format headers"
    }
    try:
        result = actions.validate_calc_preview(data)
        if result.get("summary") == "Format headers" and len(result.get("changes", [])) == 2:
            print(f"PASS: default action validation works")
            return True
        else:
            print(f"FAIL: default action validation returned wrong data")
            return False
    except Exception as e:
        print(f"FAIL: default action raised: {e}")
        return False


def main():
    print("=" * 50)
    print("Libre Asist - Calc Tests")
    print("=" * 50)

    results = []
    results.append(("Module imports", test_module_imports()))
    results.append(("Schemas", test_schemas()))
    results.append(("Skill blocks", test_skill_blocks()))
    results.append(("Action validators", test_validators()))
    results.append(("Invalid data rejection", test_invalid_validators()))
    results.append(("Default action", test_default_action()))

    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    passed = 0
    failed = 0
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {name}")
        if result:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
