from django.core.management.base import BaseCommand
from pathlib import Path
from textwrap import dedent
import json

PY = "https://docs.python.org/3/"
PEP8 = "https://peps.python.org/pep-0008/"

FILES = {
    # БАЗА
    "python_basics.md": f"""\
# Python Basics
Variables, expressions, printing, and the REPL.
- Variables are created by assignment: `x = 10`
- Built-in types: int, float, str, bool, list, tuple, dict, set
- `print()` for output, f-strings for formatting
See: {PY}""",

    "control_flow.md": f"""\
# Control Flow
if/elif/else, for, while, break, continue, pass.
- Ternary: `a if cond else b`
- Pattern matching (3.10+): `match x: case 0: ...`
See: {PY}tutorial/controlflow.html""",

    "functions.md": f"""\
# Functions
def, return, docstrings, default args, *args/**kwargs.
- First-class functions, closures
- Lambda, map/filter, list comprehensions
See: {PY}tutorial/controlflow.html#defining-functions""",

    "comprehensions.md": f"""\
# Comprehensions
List/Dict/Set comprehensions, generator expressions.
- `[x*x for x in range(10) if x%2==0]`
- `{k:v for k,v in pairs}`
See: {PY}tutorial/datastructures.html""",

    "datastructures.md": f"""\
# Data Structures
List/tuple/dict/set, deque, heapq, collections.
- Mutability, copying vs references
- Sorting: key, reverse, custom
See: {PY}tutorial/datastructures.html""",

    "iterators_generators.md": f"""\
# Iterators & Generators
- Iter protocol: __iter__/__next__
- `yield`, generator functions, send/throw/close
- itertools basics
See: {PY}library/itertools.html""",

    "decorators.md": f"""\
# Decorators
- Higher-order funcs, @decorator
- functools.wraps, caching with lru_cache
See: {PY}library/functools.html""",

    "typing.md": f"""\
# Typing
- type hints, `list[int]`, `dict[str,int]`
- `TypedDict`, `Protocol`, `dataclasses`
- `mypy` basics
See: {PY}library/typing.html""",

    "files_io.md": f"""\
# Files & IO
- `with open(..., encoding="utf-8") as f:`
- read/readlines/iter lines; json/csv basics
See: {PY}tutorial/inputoutput.html""",

    "exceptions.md": f"""\
# Exceptions
- try/except/else/finally
- raise, custom exceptions
- Context managers
See: {PY}tutorial/errors.html""",

    "modules_packages.md": f"""\
# Modules & Packages
- imports, __init__.py, sys.path
- venv, pip basics
See: {PY}tutorial/modules.html""",

    "testing_pytest.md": f"""\
# Testing with pytest
- test_*.py, assert style
- parametrize, fixtures, tmp_path
See: https://docs.pytest.org/""",

    "style_pep8.md": f"""\
# Code Style (PEP 8)
- Naming, imports, whitespace, line length
- Tools: black, ruff
See: {PEP8}""",

    "oop.md": f"""\
# OOP
- classes, __init__, methods, properties
- inheritance vs composition
See: {PY}tutorial/classes.html""",

    "asyncio.md": f"""\
# Asyncio
- async/await, tasks, gather
- aiohttp basics
See: {PY}library/asyncio.html""",

    "sqlite.md": f"""\
# SQLite
- sqlite3 connect, execute, parameterized queries
- context management
See: {PY}library/sqlite3.html""",

    "http_requests.md": f"""\
# HTTP Requests
- urllib.request basics
- requests (3rd party) intro
See: {PY}library/urllib.request.html""",

    "regex.md": f"""\
# Regular Expressions
- re: compile, search, match, findall, groups
- common patterns, flags
See: {PY}library/re.html""",

    "algorithms_basics.md": f"""\
# Algorithms Basics
- Big-O, arrays, linked lists, stacks, queues
- Sorting: bubble, insertion, merge, quick (high-level)
- Searching: linear, binary
""",

    "git_basics.md": f"""\
# Git Basics
- init, clone, status, add, commit, log
- branch, merge, rebase (intro)
- .gitignore
""",

    "cli_projects.md": f"""\
# CLI Projects
- argparse for flags
- structuring small tools
See: {PY}library/argparse.html""",
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
        {"title": "Python Official Docs", "url": PY, "license": "Docs"},
        {"title": "PEP 8", "url": PEP8, "license": "Docs"}
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
