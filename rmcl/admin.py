from django.contrib import admin

from rmcl.models import SqlFile, WorkDir


@admin.register(WorkDir)
class WorkDirAdmin(admin.ModelAdmin):
    pass


@admin.register(SqlFile)
class SqlFileAdmin(admin.ModelAdmin):
    search_fields = ('path',)
