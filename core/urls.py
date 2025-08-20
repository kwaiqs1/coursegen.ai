from django.contrib import admin
from django.urls import path
from api.views import ping, generate_blueprint, save_blueprint, list_courses


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/ping/", ping),
    path("api/generate/blueprint/", generate_blueprint),
    path("api/courses/save_blueprint/", save_blueprint),
    path("api/courses/", list_courses),
]
