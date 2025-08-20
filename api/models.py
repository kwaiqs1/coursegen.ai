from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Course(models.Model):
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    topic = models.CharField(max_length=200)
    level = models.CharField(max_length=20)
    duration_weeks = models.PositiveSmallIntegerField(default=4)
    prerequisites_json = models.JSONField(default=list)       # список строк
    learning_outcomes_json = models.JSONField(default=list)   # список строк
    capstone = models.TextField()
    references_json = models.JSONField(default=list)          # [{title,url,license}]
    created_at = models.DateTimeField(auto_now_add=True)

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    order = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    objectives_json = models.JSONField(default=list)          # список строк
    lessons = models.PositiveSmallIntegerField(default=2)
    quiz_items = models.PositiveSmallIntegerField(default=5)
    project = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ["order"]
        unique_together = [("course", "order")]




class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lesson_set")
    order = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    content_json = models.JSONField(default=dict)  # весь структурный контент урока

    class Meta:
        ordering = ["order"]
        unique_together = [("module", "order")]
