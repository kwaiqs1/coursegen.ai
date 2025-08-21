from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status

from pydantic import ValidationError
from .ollama_client import call_ollama, parse_json_loose
from .schemas import CourseBlueprint, LessonContent

from django.db import transaction
from .models import Course, Module, Lesson

from pathlib import Path
from .rag import BM25Index

from django.http import HttpResponse
from .exporter import export_course_zip

# ──────────────────────────────────────────────────────────────────────────────
# ЖЕСТКИЕ ИНСТРУКЦИИ ДЛЯ МОДЕЛИ
# ──────────────────────────────────────────────────────────────────────────────
BLUEPRINT_INSTRUCTIONS = """
You are Course Architect AI.

Generate a STRICT JSON object for a programming course blueprint that matches EXACTLY this schema:

{
  "topic": string,
  "level": "beginner" | "intermediate" | "advanced",
  "duration_weeks": integer (1..52),
  "prerequisites": string[],                    // 0..10
  "learning_outcomes": string[],                // 5..12, measurable
  "modules": [                                  // 3..20 modules
    {
      "title": string,
      "objectives": string[],                   // 3..8 items, action verbs
      "lessons": integer,                       // 2..8
      "quiz_items": integer,                    // 5..15
      "project": string | null
    }
  ],
  "capstone": string,
  "references": [                               // 2..12
    {"title": string, "url": string, "license": "MIT" | "BSD" | "Apache-2.0" | "CC-BY" | "Docs"}
  ]
}

HARD RULES (must always be satisfied):
- Return JSON ONLY. No prose, no markdown.
- learning_outcomes: at least 5 items (5..12).
- modules: between 3 and 20 items.
- For each module:
  - objectives: 3..8 items (add realistic extra ones if needed).
  - lessons: integer 2..8 (never above 8).
  - quiz_items: integer 5..15 (never below 5).
- Use official docs or permissive-licensed sources only (license 'Docs' for official docs).
- If the user's duration_weeks is short, adjust scope so all numeric constraints still hold.
"""

# ──────────────────────────────────────────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ "АВТО-РЕМОНТА" JSON
# ──────────────────────────────────────────────────────────────────────────────
def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(n)))

ACTION_VERBS = [
    "Understand", "Explain", "Apply", "Implement", "Debug",
    "Refactor", "Test", "Optimize", "Use", "Design"
]

def pad_objectives(obj_list, topic: str, need: int):
    base = list(obj_list or [])
    while len(base) < need:
        base.append(f"Apply {topic} concepts in small tasks")
    return base[:8]

def pad_outcomes(lo_list, topic: str, min_len: int = 5):
    base = list(lo_list or [])
    verbs = iter(ACTION_VERBS)
    while len(base) < min_len:
        v = next(verbs, "Apply")
        base.append(f"{v} {topic} to build small practical programs")
    return base[:12]

def ensure_references(refs, topic: str):
    base = list(refs or [])
    # добавим минимум официальных доков (валидные ссылки и license="Docs")
    essentials = [
        {"title": "Python Official Docs", "url": "https://docs.python.org/3/", "license": "Docs"},
        {"title": "pip User Guide", "url": "https://pip.pypa.io/en/stable/", "license": "Docs"},
    ]
    # не дублируем существующие по url
    have = {r.get("url") for r in base if isinstance(r, dict)}
    for r in essentials:
        if r["url"] not in have:
            base.append(r)
    return base[:12]

def repair_blueprint_data(data: dict) -> dict:
    """Подправляем поля до мин/макс ограничений схемы."""
    topic = (data.get("topic") or "the topic").strip()

    # learning_outcomes: 5..12
    data["learning_outcomes"] = pad_outcomes(data.get("learning_outcomes"), topic, 5)

    # modules: 3..20 (если меньше 3 — продублируем/упростим; если больше 20 — обрежем)
    modules = list(data.get("modules") or [])
    if len(modules) < 3 and modules:
        while len(modules) < 3:
            # добавляем упрощённую копию последнего модуля
            clone = dict(modules[-1])
            clone["title"] = f"{clone.get('title', 'Module')} (extended)"
            modules.append(clone)
    data["modules"] = modules[:20]

    # правим каждый модуль
    fixed_modules = []
    for m in data["modules"]:
        m = dict(m or {})
        m["lessons"] = clamp(m.get("lessons", 4), 2, 8)
        m["quiz_items"] = clamp(m.get("quiz_items", 8), 5, 15)
        m["objectives"] = pad_objectives(m.get("objectives") or [], topic, 3)
        fixed_modules.append(m)
    data["modules"] = fixed_modules

    # references: минимум 2
    data["references"] = ensure_references(data.get("references"), topic)

    # prerequisites: максимум 10; если None — в пустой список
    prereq = data.get("prerequisites") or []
    data["prerequisites"] = list(prereq)[:10]

    # duration_weeks границы 1..52 (на всякий)
    data["duration_weeks"] = clamp(data.get("duration_weeks", 4), 1, 52)

    # level нормализуем
    level = (data.get("level") or "beginner").lower()
    if level not in {"beginner", "intermediate", "advanced"}:
        level = "beginner"
    data["level"] = level

    return data

# ──────────────────────────────────────────────────────────────────────────────
# ЭНДПОИНТЫ
# ──────────────────────────────────────────────────────────────────────────────
@api_view(["GET"])
def ping(request):
    return Response({"status": "ok"})

@api_view(["POST"])
def generate_blueprint(request):
    """
    Input JSON:
    {
      "topic": "Python basics",
      "level": "beginner",         # optional
      "duration_weeks": 4,         # optional
      "goals": ["prepare..."]      # optional
    }
    """
    data = request.data or {}
    topic = (data.get("topic") or "").strip()
    level = (data.get("level") or "beginner").strip().lower()
    duration_weeks = int(data.get("duration_weeks") or 4)
    goals = data.get("goals") or []

    if not topic:
        return Response({"detail": "topic is required"}, status=status.HTTP_400_BAD_REQUEST)

    goals_str = ""
    if goals and isinstance(goals, list):
        goals_str = "User goals:\n- " + "\n- ".join([str(g) for g in goals])

    user_block = f"User input:\n- topic: {topic}\n- level: {level}\n- duration_weeks: {duration_weeks}\n{goals_str}"
    prompt = f"{BLUEPRINT_INSTRUCTIONS}\n\n{user_block}\n\nReturn JSON now."

    try:
        # 1) вызов модели
        raw = call_ollama(prompt)
        as_json = parse_json_loose(raw)

        # 2) пробуем строгую валидацию
        try:
            blueprint = CourseBlueprint(**as_json)
            return Response(blueprint.model_dump(mode="json"), status=200)
        except ValidationError:
            # 3) авто-ремонт, затем повторная валидация
            repaired = repair_blueprint_data(as_json)
            blueprint = CourseBlueprint(**repaired)
            return Response(blueprint.model_dump(mode="json"), status=200)

    except Exception as e:
        return Response(
            {"detail": f"generation_error: {type(e).__name__}: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )






@api_view(["POST"])
def save_blueprint(request):
    """
    Принимает ровно тот JSON, который возвращает /api/generate/blueprint/,
    создаёт Course и связные Module в БД, возвращает id курса.
    """
    data = request.data or {}
    # валидация pydantic (на всякий случай)
    try:
        bp = CourseBlueprint(**data)
    except Exception as e:
        return Response({"detail": f"invalid_blueprint: {e}"}, status=400)

    with transaction.atomic():
        course = Course.objects.create(
            owner=request.user if request.user.is_authenticated else None,
            topic=bp.topic,
            level=bp.level,
            duration_weeks=bp.duration_weeks,
            prerequisites_json=bp.prerequisites,
            learning_outcomes_json=bp.learning_outcomes,
            capstone=bp.capstone,
            references_json=[r.model_dump(mode="json") for r in bp.references],
        )
        for idx, m in enumerate(bp.modules, start=1):
            Module.objects.create(
                course=course,
                order=idx,
                title=m.title,
                objectives_json=m.objectives,
                lessons=m.lessons,
                quiz_items=m.quiz_items,
                project=m.project,
            )

    return Response({"course_id": course.id}, status=201)




@api_view(["GET"])
def list_courses(request):
    qs = Course.objects.all().order_by("-created_at")
    out = []
    for c in qs:
        out.append({
            "id": c.id,
            "topic": c.topic,
            "level": c.level,
            "duration_weeks": c.duration_weeks,
            "created_at": c.created_at.isoformat(),
            "modules": c.modules.count(),
        })
    return Response(out, status=200)






@api_view(["GET"])
def list_courses(request):
    qs = Course.objects.all().order_by("-created_at")
    out = []
    for c in qs:
        out.append({
            "id": c.id,
            "topic": c.topic,
            "level": c.level,
            "duration_weeks": c.duration_weeks,
            "created_at": c.created_at.isoformat(),
            "modules": c.modules.count(),
        })
    return Response(out, status=200)


# ───────────────────────────────────────────────
# STEP C: Работа с уроками
# ───────────────────────────────────────────────

@api_view(["GET"])
def list_lessons(request, module_id: int):
    """Вернуть все уроки конкретного модуля"""
    try:
        module = Module.objects.get(id=module_id)
    except Module.DoesNotExist:
        return Response({"detail": "Module not found"}, status=404)

    lessons = module.lesson_set.all().order_by("order")
    data = [
        {
            "id": l.id,
            "order": l.order,
            "title": l.title,
            "content_json": l.content_json,
        }
        for l in lessons
    ]
    return Response(data, status=200)


@api_view(["POST"])
def add_lesson(request, module_id: int):
    """Добавить новый урок в модуль"""
    try:
        module = Module.objects.get(id=module_id)
    except Module.DoesNotExist:
        return Response({"detail": "Module not found"}, status=404)

    data = request.data or {}
    title = data.get("title") or "Untitled lesson"
    content_json = data.get("content_json") or {}
    order = int(data.get("order") or (module.lesson_set.count() + 1))

    lesson = Lesson.objects.create(
        module=module,
        order=order,
        title=title,
        content_json=content_json,
    )

    return Response({
        "id": lesson.id,
        "order": lesson.order,
        "title": lesson.title,
        "content_json": lesson.content_json,
    }, status=201)








@api_view(["POST"])
def save_lesson(request):
    """
    Input:
    {
      "module_id": 1,
      "lesson_order": 1,
      "lesson": { ... LessonContent JSON ... }
    }
    """
    body = request.data or {}
    module_id = int(body.get("module_id") or 0)
    lesson_order = int(body.get("lesson_order") or 1)
    lesson_data = body.get("lesson") or {}

    try:
        lc = LessonContent(**lesson_data)
    except Exception as e:
        return Response({"detail": f"invalid_lesson: {e}"}, status=400)

    module = get_object_or_404(Module, id=module_id)

    obj, created = Lesson.objects.update_or_create(
        module=module,
        order=lesson_order,
        defaults={
            "title": lc.title,
            "content_json": lc.model_dump(mode="json"),
        }
    )
    return Response({"lesson_id": obj.id, "created": created}, status=201 if created else 200)
















RAG_INDEX_PATH = Path("rag_index.pkl")

@api_view(["POST"])
def rag_search(request):
    """
    Input: {"query": "python loops", "top_k": 5}
    """
    payload = request.data or {}
    q = (payload.get("query") or "").strip()
    top_k = int(payload.get("top_k") or 5)
    if not q:
        return Response({"detail": "query is required"}, status=400)

    idx = BM25Index()
    if not RAG_INDEX_PATH.exists():
        return Response({"detail": "RAG index not found. Run ingest_rag first."}, status=400)
    idx.load(RAG_INDEX_PATH)

    results = idx.search(q, top_k=top_k)
    out = [{"passage": p, "score": s} for p, s in results]
    return Response({"results": out}, status=200)











LESSON_INSTR = """
You are Course Lesson Writer AI.

Return STRICT JSON ONLY matching this schema:
{
  "title": string,
  "reading_time_min": integer (5..30),
  "objectives": string[] (2..6 items, action verbs),
  "theory_md": string,
  "code_examples": [{"filename": string, "content": string}],
  "quiz": [{"type":"mcq"|"short"|"code_output","question":string,"options":string[],"answer":string,"explain":string|null}] (3..15),
  "exercise": {"task":string,"starter_files":[{"filename":string,"content":string}],"tests":[{"filename":string,"content":string}],"rubric":string[]},
  "further_reading": [{"title":string,"url":string,"license":"MIT"|"BSD"|"Apache-2.0"|"CC-BY"|"Docs"}] (0..8)
}

HARD RULES:
- JSON ONLY. No prose. No markdown fences.
- All URLs in further_reading MUST be absolute http(s) links (e.g., https://docs.python.org/3/). DO NOT use relative links or markdown like [text](#anchor).
- Code must be runnable and minimal. No nonexistent libs.
- Respect the student's level and module objectives.
"""




def build_rag_context(query: str, k: int = 5) -> str:
    idx = BM25Index()
    if not RAG_INDEX_PATH.exists():
        return ""
    idx.load(RAG_INDEX_PATH)
    results = idx.search(query, top_k=k)
    blocks = []
    for p, s in results:
        blocks.append(f"[CTX score={s:.2f}]\n{p}")
    return "\n\n".join(blocks)




def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(n)))




def _is_http_url(s: str) -> bool:
    return isinstance(s, str) and (s.startswith("http://") or s.startswith("https://"))




def _sanitize_further_reading(items, topic: str):
    allowed = {"MIT", "BSD", "Apache-2.0", "CC-BY", "Docs"}
    out = []
    for it in list(items or []):
        t = (it or {}).get("title") or "Official Docs"
        u = (it or {}).get("url") or ""
        lic = (it or {}).get("license") or "Docs"
        if not _is_http_url(u):
            # Подставляем безопасный дефолт, чтобы пройти валидацию.
            # Для Python-тем по умолчанию ведём на оф. доки.
            u = "https://docs.python.org/3/"
            lic = "Docs"
        if lic not in allowed:
            lic = "Docs"
        out.append({"title": t, "url": u, "license": lic})
    if not out:
        out = [{"title": "Python Official Docs", "url": "https://docs.python.org/3/", "license": "Docs"}]
    return out[:8]





def repair_lesson(data: dict, topic: str) -> dict:
    data = dict(data or {})
    data.setdefault("title", f"{topic}: Lesson")
    data["reading_time_min"] = clamp(data.get("reading_time_min", 10), 5, 30)

    objs = list(data.get("objectives") or [])
    while len(objs) < 2:
        objs.append(f"Apply {topic} basics in small tasks")
    data["objectives"] = objs[:6]

    quiz = list(data.get("quiz") or [])
    while len(quiz) < 3:
        quiz.append({
            "type": "mcq",
            "question": f"Basic concept of {topic}?",
            "options": ["Option A", "Option B", "Option C"],
            "answer": "Option A",
            "explain": "A simple recall question."
        })
    data["quiz"] = quiz[:15]

    ex = dict(data.get("exercise") or {})
    ex.setdefault("task", f"Write a small program related to {topic}.")
    ex.setdefault("starter_files", [{"filename": "main.py", "content": "# TODO\n"}])
    ex.setdefault("tests", [{"filename": "test_basic.py", "content": "def test_true():\n    assert True\n"}])
    ex.setdefault("rubric", ["Correctness", "Style", "Edge cases"])
    data["exercise"] = ex

    data["code_examples"] = list(data.get("code_examples") or [])[:10]
    data["further_reading"] = _sanitize_further_reading(data.get("further_reading"), topic)

    return data




@api_view(["POST"])
def generate_lesson(request):
    """
    Input:
    {
      "course_id": 1,
      "module_order": 1,
      "lesson_order": 1
    }
    """
    body = request.data or {}
    course_id = int(body.get("course_id") or 0)
    module_order = int(body.get("module_order") or 1)
    lesson_order = int(body.get("lesson_order") or 1)

    course = get_object_or_404(Course, id=course_id)
    module = get_object_or_404(Module, course=course, order=module_order)

    # RAG-контекст под тему и модуль
    q = f"{course.topic} {module.title} {' '.join(module.objectives_json)}"
    rag_ctx = build_rag_context(q, k=5)

    context = f"""
Course topic: {course.topic}
Level: {course.level}
Module: {module.title}
Module objectives:
- """ + "\n- ".join(module.objectives_json)

    if rag_ctx:
        context += "\n\nRAG CONTEXT (authoritative excerpts, do not contradict):\n" + rag_ctx

    prompt = f"{LESSON_INSTR}\n\n{context}\n\nReturn JSON for lesson #{lesson_order}."

    try:
        raw = call_ollama(prompt)
        as_json = parse_json_loose(raw)
        try:
            lc = LessonContent(**as_json)
            return Response(lc.model_dump(mode='json'), status=200)
        except ValidationError:
            repaired = repair_lesson(as_json, course.topic)
            lc = LessonContent(**repaired)
            return Response(lc.model_dump(mode='json'), status=200)
    except Exception as e:
        return Response({"detail": f"generation_error: {type(e).__name__}: {e}"}, status=500)







@api_view(["GET"])
def export_course(request, course_id: int):
    try:
        payload = export_course_zip(course_id)
    except Course.DoesNotExist:
        return Response({"detail": "Course not found"}, status=404)

    resp = HttpResponse(payload, content_type="application/zip")
    resp["Content-Disposition"] = f'attachment; filename="course_{course_id}.course.zip"'
    return resp