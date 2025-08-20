from typing import Optional, Literal
from pydantic import BaseModel, HttpUrl, conint, conlist

class Reference(BaseModel):
    title: str
    url: HttpUrl
    # "Docs" для офиц. документации, остальное — пермиссивные лицензии
    license: Literal["MIT", "BSD", "Apache-2.0", "CC-BY", "Docs"]

class Module(BaseModel):
    title: str
    # pydantic v2: min_length / max_length
    objectives: conlist(str, min_length=3, max_length=8)
    lessons: conint(ge=2, le=8)      # кол-во уроков в модуле
    quiz_items: conint(ge=5, le=15)  # кол-во вопросов для проверки
    project: Optional[str] = None

class CourseBlueprint(BaseModel):
    topic: str
    level: Literal["beginner", "intermediate", "advanced"]
    duration_weeks: conint(ge=1, le=52)
    prerequisites: conlist(str, min_length=0, max_length=10) = []
    learning_outcomes: conlist(str, min_length=5, max_length=12)
    modules: conlist(Module, min_length=3, max_length=20)
    capstone: str
    references: conlist(Reference, min_length=2, max_length=12)




class CodeFile(BaseModel):
    filename: str
    content: str

class QuizItem(BaseModel):
    type: Literal["mcq", "short", "code_output"]  # можно расширить типы позже
    question: str
    options: Optional[conlist(str, min_length=2, max_length=8)] = None  # для mcq
    answer: str  # для mcq можно хранить индекс как строку "2" или текст
    explain: Optional[str] = None

class Exercise(BaseModel):
    task: str
    starter_files: conlist(CodeFile, min_length=0, max_length=10) = []
    tests: conlist(CodeFile, min_length=0, max_length=10) = []
    rubric: conlist(str, min_length=0, max_length=10) = []

class LessonContent(BaseModel):
    title: str
    reading_time_min: conint(ge=5, le=30)
    objectives: conlist(str, min_length=2, max_length=6)
    theory_md: str
    code_examples: conlist(CodeFile, min_length=0, max_length=10) = []
    quiz: conlist(QuizItem, min_length=3, max_length=15)
    exercise: Exercise
    further_reading: conlist(Reference, min_length=0, max_length=8) = []