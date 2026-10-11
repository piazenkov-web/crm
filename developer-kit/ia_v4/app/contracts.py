"""Executable contract harness. No vendor adapters or database writes."""
from pathlib import Path
import json
from jsonschema import Draft202012Validator, FormatChecker
ROOT=Path(__file__).resolve().parents[1]
CATALOG=json.loads((ROOT/'contracts/tool_catalog.json').read_text())
TOOLS={t['name']:t for t in CATALOG['tools']}
def validate_input(name, payload):
    Draft202012Validator(TOOLS[name]['input_schema'],format_checker=FormatChecker()).validate(payload)
def validate_output(name, payload):
    Draft202012Validator(TOOLS[name]['output_schema'],format_checker=FormatChecker()).validate(payload)
