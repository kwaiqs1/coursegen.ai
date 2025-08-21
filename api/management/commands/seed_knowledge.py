from django.core.management.base import BaseCommand
from pathlib import Path
from textwrap import dedent
import json

PY_DOC = "https://docs.python.org/3/"

FILES = {
    "python_basics.md": f"""\
# Python Basics
Variables, expressions, printing, and the REPL.
- Variables are created by assignment: `x = 10`
- Use `print()` for output
- Built-in types: int, float, str, bool, list, tuple, dict, set
- Conversions: `int("3")`, `str(42)`
See: {PY_DOC}
""",
    "control_flow.md": f"""\
# Control Flow
`if/elif/else`, `for` loops, `while` loops, `break`/`continue`, `pass`.
- `if x > 0: ... elif x == 0: ... else: ...`
- `for item in iterable:`
- `while condition:`
- `break` exits loop; `continue` skips to next iteration.
See: {PY_DOC}tutorial/controlflow.html
""",
    "functions.md": f"""\
# Functions
Defining, calling, returning values, docstrings.
- `def add(a, b): return a + b`
- Default args, keyword args, *args, **kwargs
- Pure functions and side effects
See: {PY_DOC}tutorial/controlflow.html#defining-functions
""",
    "modules_packages.md": f"""\
# Modules & Packages
- `import math`, `from pathlib import Path import`
- `pip` and virtual environments
- Project layout and `__init__.py`
See: {PY_DOC}tutorial/modules.html
""",
    "files_io.md": f"""\
# Files & IO
Open/read/write text files safely.
- `with open("file.txt","r",encoding="utf-8") as f:`
- `.read()`, `.readlines()`, iterate lines
- Errors & exceptions for IO
See: {PY_DOC}tutorial/inputoutput.html
""",
    "exceptions.md": f"""\
# Exceptions
- `try/except/else/finally`
- `raise ValueError("message")`
- Custom exceptions
See: {PY_DOC}tutorial/errors.html
""",
    "oop.md": f"""\
# OOP in Python
Classes, objects, methods, inheritance, `__init__`.
- `class Point: def __init__(self,x,y): self.x=x; self.y=y`
- Dunder methods, `__repr__`
- Composition vs inheritance
See: {PY_DOC}tutorial/classes.html
""",
    "testing.md": f"""\
# Testing
- `unittest` basics
- `pytest` simple tests
- Arrange-Act-Assert pattern
See: {PY_DOC}library/unittest.html
""",
    "style_pep8.md": f"""\
# Code Style (PEP 8)
- Naming, line length, imports, whitespace
- `black`, `ruff` for automation
See: https://peps.python.org/pep-0008/
""",
    "cli_projects.md": f"""\
# CLI Projects
- `argparse` for parameters
- packaging simple tools
See: {PY_DOC}library/argparse.html
""",
}

GOLDEN_COURSE = {
    "topic": "Python Basics",
    "level": "beginner",
    "duration_weeks": 4,
    "prerequisites": ["Familiarity with basic computer concepts"],
    "learning_outcomes": [
        "Understand Python syntax and core data types",
        "Use control flow to implement logic",
        "Define and call functions with arguments",
        "Work with files and handle exceptions",
        "Write simple tests for functions"
    ],
    "modules": [
        {"title": "Intro & Types", "objectives": ["Understand REPL", "Use basic types", "Apply printing"], "lessons": 3, "quiz_items": 6, "project": None},
        {"title": "Control Flow", "objectives": ["Use if/elif/else", "Implement loops", "Trace simple programs"], "lessons": 3, "quiz_items": 6, "project": None},
        {"title": "Functions", "objectives": ["Define functions", "Use parameters", "Return values"], "lessons": 3, "quiz_items": 6, "project": None},
        {"title": "Files & Exceptions", "objectives": ["Read/write files", "Handle exceptions", "Design small CLI"], "lessons": 3, "quiz_items": 6, "project": "Mini CLI tool"},
    ],
    "capstone": "Build a small command-line utility that processes a text file.",
    "references": [
        {"title": "Python Official Docs", "url": PY_DOC, "license": "Docs"},
        {"title": "PEP 8", "url": "https://peps.python.org/pep-0008/", "license": "Docs"}
    ]
}

class Command(BaseCommand):
    help = "Seed knowledge/ and golden_course/ with starter content"

    def add_arguments(self, parser):
        parser.add_argument("--knowledge", default="knowledge", help="Folder to write docs")
        parser.add_argument("--golden", default="golden_course", help="Folder to write golden blueprint JSON")

    def handle(self, *args, **opts):
        kdir = Path(opts["knowledge"]).resolve()
        gdir = Path(opts["golden"]).resolve()
        kdir.mkdir(parents=True, exist_ok=True)
        gdir.mkdir(parents=True, exist_ok=True)

        # write knowledge files
        for name, content in FILES.items():
            p = kdir / name
            p.write_text(dedent(content), encoding="utf-8")
            self.stdout.write(self.style.SUCCESS(f"wrote {p}"))

        # write golden course blueprint
        (gdir / "python_basics_blueprint.json").write_text(
            json.dumps(GOLDEN_COURSE, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        self.stdout.write(self.style.SUCCESS(f"wrote {gdir / 'python_basics_blueprint.json'}"))
