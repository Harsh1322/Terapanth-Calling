from django.contrib import admin
from django.urls import path
from tracker import views
urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("members/", views.members, name="members"),
    path("members/<int:user_id>/delete/", views.delete_member, name="delete_member"),
    path("contacts/import/", views.import_contacts, name="import_contacts"),
    path("contacts/<int:contact_id>/status/", views.update_status, name="update_status"),
    path("contacts/export.xlsx", views.export_excel, name="export_excel"),
    path("extension/import/", views.extension_import, name="extension_import"),
]
