from django.contrib import admin
from django.urls import path
from api.views import ping, generate_blueprint, save_blueprint, list_courses, list_lessons, add_lesson, save_lesson, rag_search


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/ping/", ping),
    path("api/generate/blueprint/", generate_blueprint),
    path("api/courses/save_blueprint/", save_blueprint),
    path("api/courses/", list_courses),
    path("courses/<int:module_id>/lessons/", list_lessons),
    path("courses/<int:module_id>/lessons/add/", add_lesson),
    path("api/lessons/save", save_lesson),
    path("api/rag/search/", rag_search),
]
