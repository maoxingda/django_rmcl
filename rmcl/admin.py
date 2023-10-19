from django.contrib import admin

from rmcl.models import SqlFile, WorkDir, Task


@admin.register(WorkDir)
class WorkDirAdmin(admin.ModelAdmin):
    pass


@admin.register(SqlFile)
class SqlFileAdmin(admin.ModelAdmin):
    search_fields = ('path',)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    autocomplete_fields = ('sql_file',)
    list_display = ('name', 'etl_start_date', 'etl_end_date', 'is_render', 'is_delete_comment')
