import os
import re
import shutil
from datetime import datetime, timedelta

from django.shortcuts import redirect, get_object_or_404

from rmcl.models import WorkDir, SqlFile
from rmcl.utils import remove_comments, remove_procedure


def refresh_change_list(request):
    work_dirs = WorkDir.objects.all()

    sql_file_paths = []
    start_date = (datetime.utcnow() - timedelta(hours=16)).date()
    end_date = start_date
    for work_dir in work_dirs:
        for root, dirs, files in os.walk(work_dir.path):
            for file in files:
                if file.endswith('.sql'):
                    path = os.path.join(root, file).replace(work_dir.path, '')
                    sql_file_paths.append(SqlFile(path=path, etl_start_date=start_date, etl_end_date=end_date))

    SqlFile.objects.all().delete()
    SqlFile.objects.bulk_create(sql_file_paths)

    return redirect('admin:rmcl_sqlfile_changelist')


def render_sqlfile(request, pk):
    sql_file = get_object_or_404(SqlFile, pk=pk)
    work_dir = WorkDir.objects.first().path
    sql_file_path = os.path.join(work_dir, sql_file.path)

    sql_file_bak = f'{sql_file_path}.bak.sql'
    shutil.copyfile(sql_file_path, sql_file_bak)

    with open(sql_file_bak) as f:
        sql = f.read()

    latest_partition = (sql_file.etl_start_date - timedelta(days=1)).strftime('%Y/%m/%d/16')
    eold_partition = sql_file.etl_end_date.strftime('%Y/%m/%d/16~')
    dw_latest_utc_timestamp = (datetime.strptime(latest_partition[:10] + f' {latest_partition[11:]}:00:00', '%Y/%m/%d %H:00:00')).isoformat()

    if '$dw_latest_partition' in sql or '$dw_eold_partition' in sql:
        sql = sql.replace('$dw_latest_partition', latest_partition)
        sql = sql.replace('$dw_eold_partition', eold_partition)
        sql = sql.replace('$dw_latest_utc_timestamp', dw_latest_utc_timestamp)

        if sql_file.is_delete_comment:
            sql = remove_comments(sql)
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

        with open(sql_file_bak, 'w') as f:
            f.write(sql)
    else:
        with open(sql_file_bak) as f:
            sql = f.read().replace(f'{latest_partition}', '$dw_latest_partition')
            sql = sql.replace(f'{eold_partition}', '$dw_eold_partition')
            sql = sql.replace(f'{dw_latest_utc_timestamp}', '$dw_latest_utc_timestamp')

        with open(sql_file_bak, 'w') as f:
            f.write(sql)

    return redirect(sql_file)
