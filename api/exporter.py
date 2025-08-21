from __future__ import annotations

import io
import json
import re
import zipfile
from typing import Dict, Any
from django.utils.text import slugify
from .models import Course, Module, Lesson

def _safe_slug(s: str) -> str:
    s = slugify(s or "item")
    return s or "item"

def _lesson_to_files(lesson: Lesson) -> Dict[str, bytes]:
    """
    Преобразует Lesson.content_json в набор файлов:
    - markdown урока
    - code_examples/*
    - exercise/starter/*, exercise/tests/*
    """
    data: Dict[str, Any] = lesson.content_json or {}
    title = data.get("title") or lesson.title
    theory_md = data.get("theory_md") or ""
    code_examples = data.get("code_examples") or []
    exercise = data.get("exercise") or {}
    ex_starter = exercise.get("starter_files") or []
    ex_tests = exercise.get("tests") or []

    files: Dict[str, bytes] = {}

    # Основной md
    md = [f"# {title}", "", theory_md, ""]
    # Вставим кратко цели
    objs = data.get("objectives") or []
    if objs:
        md.append("## Objectives")
        md.extend([f"- {o}" for o in objs])
        md.append("")
    # Вставим квиз (как текст)
    quiz = data.get("quiz") or []
    if quiz:
        md.append("## Quiz")
        for i, q in enumerate(quiz, 1):
            md.append(f"{i}. {q.get('question','')}")
            opts = q.get("options") or []
            if opts:
                for j, op in enumerate(opts, 1):
                    md.append(f"   {j}) {op}")
        md.append("")
    lesson_md = "\n".join(md).strip() + "\n"
    files["lesson.md"] = lesson_md.encode("utf-8")

    # code_examples
    for f in code_examples:
        name = f.get("filename") or "example.py"
        cnt = f.get("content") or ""
        files[f"code_examples/{name}"] = cnt.encode("utf-8")

    # exercise
    for f in ex_starter:
        name = f.get("filename") or "main.py"
        cnt = f.get("content") or ""
        files[f"exercise/starter/{name}"] = cnt.encode("utf-8")
    for f in ex_tests:
        name = f.get("filename") or "test_basic.py"
        cnt = f.get("content") or ""
        files[f"exercise/tests/{name}"] = cnt.encode("utf-8")

    return files

def export_course_zip(course_id: int) -> bytes:
    course = Course.objects.get(id=course_id)

    manifest = {
        "id": course.id,
        "topic": course.topic,
        "level": course.level,
        "duration_weeks": course.duration_weeks,
        "prerequisites": course.prerequisites_json,
        "learning_outcomes": course.learning_outcomes_json,
        "capstone": course.capstone,
        "references": course.references_json,
        "modules": [],
        "version": 1,
    }

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # Модули
        for m in course.modules.all().order_by("order"):
            mslug = f"{m.order:02d}_{_safe_slug(m.title)}"
            manifest["modules"].append({
                "order": m.order,
                "title": m.title,
                "objectives": m.objectives_json,
                "lessons": [],
                "quiz_items": m.quiz_items,
                "project": m.project,
                "path": f"modules/{mslug}/"
            })

            # Уроки
            for l in m.lesson_set.all().order_by("order"):
                lslug = f"lesson_{l.order:02d}_{_safe_slug(l.title)}"
                subpath = f"modules/{mslug}/{lslug}/"
                # добавим файлы урока
                files = _lesson_to_files(l)
                for rel, content in files.items():
                    z.writestr(subpath + rel, content)
                manifest["modules"][-1]["lessons"].append({
                    "order": l.order,
                    "title": l.title,
                    "path": subpath
                })

        # manifest
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    return buf.getvalue()
