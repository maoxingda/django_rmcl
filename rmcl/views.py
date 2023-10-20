import os
import re
import shutil
from datetime import datetime, timedelta

import sqlparse
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from jinja2 import Template

from rmcl.models import WorkDir, SqlFile, Task
from rmcl.utils import remove_comments, remove_procedure


def refresh_change_list(request):
    work_dirs = WorkDir.objects.all()

    sql_files = set()
    for work_dir in work_dirs:
        for root, dirs, files in os.walk(work_dir.path):
            for file in files:
                if file.endswith('.sql'):
                    path = os.path.join(root, file).replace(work_dir.path, '')
                    sql_files.add(path)

    values_list = SqlFile.objects.values_list('path', flat=True)
    deleted_sql_files = set(values_list) - sql_files
    new_sql_files = sql_files - set(values_list)

    SqlFile.objects.filter(path__in=deleted_sql_files).delete()
    SqlFile.objects.bulk_create([SqlFile(path=path) for path in new_sql_files])

    messages.info(request, '刷新成功')

    return redirect('admin:rmcl_sqlfile_changelist')


def render_sqlfile(request, pk):
    task = get_object_or_404(Task, pk=pk)
    work_dir = WorkDir.objects.first().path
    sql_file_path = os.path.join(work_dir, task.sql_file.path)

    no_context = request.GET.get('no-context')
    context = {
        'limit': 1,
        'offset': 0,
        'corp_id_list': '1, 2, 3',
        'mealplan_snowflake_id_list': '1, 2, 3',
        'get_corp_ids_posix_from_input(delivery_mealplan_ids)': '',
        'get_corp_ids_posix_from_input(dinner_in_mealplan_ids)': '',
    }
    if no_context:
        with open(sql_file_path) as f:
            sql = f.read()
            sql = sql.replace('{{get_corp_ids_posix_from_input(delivery_mealplan_ids)}}', '')
            sql = sql.replace('{{get_corp_ids_posix_from_input(dinner_in_mealplan_ids)}}', '')
            sql = Template(sql).render(**context)
            stmts = []
            for stmt in sqlparse.split(sql):
                stmts.append(remove_comments(stmt))
            sql = '\n'.join(stmts)

            sql = re.sub(r'(?:\n\s*){3,}', '\n\n', sql)
            sql = re.sub(r'^\n\n', '', sql)

        with open(sql_file_path, 'w') as f:
            f.write(sql)
        task.render_sql_file = sql_file_path
    else:
        sql_file_bak = f'{sql_file_path}.bak.sql'
        shutil.copyfile(sql_file_path, sql_file_bak)

        with open(sql_file_bak) as f:
            sql = f.read()

        latest_partition = (task.etl_start_date - timedelta(days=1)).strftime('%Y/%m/%d/16')
        eold_partition = task.etl_end_date.strftime('%Y/%m/%d/16~')
        dw_latest_utc_timestamp = (datetime.strptime(latest_partition[:10] + f' {latest_partition[11:]}:00:00', '%Y/%m/%d %H:00:00')).isoformat()

        if '$dw_latest_partition' in sql or '$dw_eold_partition' in sql:
            sql = sql.replace('$dw_latest_partition', latest_partition)
            sql = sql.replace('$dw_eold_partition', eold_partition)
            sql = sql.replace('$dw_latest_utc_timestamp', dw_latest_utc_timestamp)

            if task.is_delete_comment:
                sql = remove_comments(sql)
                if task.sql_file.is_procedure:
                    sql = remove_procedure(sql)

            ctas_pattern = re.compile(r'create\s+table\s+(\w+)\.(\w+)\s+as', flags=re.IGNORECASE)
            what = ctas_pattern.findall(sql)
            if what:
                for schema_name, table_name in what:
                    sql = ctas_pattern.sub(r'create temp table \2 as', sql)
                    sql = sql.replace(f'{schema_name}.{table_name}', f'{table_name}')

            stg_create_table_pattern = re.compile(r'create\s+table\s+(\w+)\.(\w+(_stg|_temp|_tmp))', flags=re.IGNORECASE)
            stg_pattern = re.compile(r'(\w+)\.(\w+(_stg|_temp|_tmp))', flags=re.IGNORECASE)
            sql = stg_create_table_pattern.sub(r'create temp table \2', sql)
            sql = stg_pattern.sub(r'\2', sql)

            select_into_pattern = re.compile(r"select\s+('[^'+]{13,}')\s+into\s+(\w+)\s*;", flags=re.IGNORECASE | re.DOTALL)
            for partition, variable_name in select_into_pattern.findall(sql):
                sql = select_into_pattern.sub('', sql)
                sql = sql.replace(variable_name, partition)

            raise_pattern = re.compile(r'raise\s+(?:info|warning|exception|log)\s+[^;]*;', flags=re.IGNORECASE)
            sql = raise_pattern.sub('', sql)

            sql = re.sub(r'(?:\n\s*){3,}', '\n\n', sql)
            sql = re.sub(r'^\n\n', '', sql)

            sql = Template(sql).render(**context)

            with open(sql_file_bak, 'w') as f:
                f.write(sql)
        else:
            with open(sql_file_bak) as f:
                sql = f.read().replace(f'{latest_partition}', '$dw_latest_partition')
                sql = sql.replace(f'{eold_partition}', '$dw_eold_partition')
                sql = sql.replace(f'{dw_latest_utc_timestamp}', '$dw_latest_utc_timestamp')

            sql = Template(sql).render(**context)

            with open(sql_file_bak, 'w') as f:
                f.write(sql)

        task.render_sql_file = sql_file_bak

    task.is_render = True
    task.save()

    messages.info(request, '渲染成功')

    return redirect(task)


def open_sqlfile(request, pk):
    import subprocess

    work_dir = WorkDir.objects.first().path
    task = get_object_or_404(Task, pk=pk)

    subprocess.run(["open", f'{os.path.join(work_dir, task.render_sql_file)}'], check=True)

    messages.info(request, '打开成功')

    return redirect(task)
