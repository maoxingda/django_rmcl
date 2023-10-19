from django.db import models


class WorkDir(models.Model):
    class Meta:
        verbose_name = '工作目录'
        verbose_name_plural = '工作目录'

    path = models.CharField(max_length=255, unique=True, verbose_name='工作目录路径')

    def __str__(self):
        return self.path


class SqlFile(models.Model):
    class Meta:
        verbose_name = '脚本文件'
        verbose_name_plural = '脚本文件'

        ordering = ('path',)

    path = models.CharField(max_length=255, unique=True, verbose_name='Sql文件路径', editable=False)
    is_procedure = models.BooleanField(default=False, verbose_name='是否存储过程')

    def __str__(self):
        return self.path

    def get_absolute_url(self):
        return f'/rmcl/sqlfile/{self.pk}/'


class Task(models.Model):
    class Meta:
        verbose_name = '任务'
        verbose_name_plural = '任务'
        ordering = ('name',)

    sql_file = models.ForeignKey(SqlFile, on_delete=models.CASCADE, verbose_name='脚本文件')
    name = models.CharField(max_length=255, verbose_name='任务名称')
    desc = models.TextField(verbose_name='任务描述', blank=True, null=True)
    etl_start_date = models.DateField(verbose_name='ETL开始时间')
    etl_end_date = models.DateField(verbose_name='ETL结束时间')
    is_delete_comment = models.BooleanField(default=False, verbose_name='是否删除注释')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/rmcl/task/{self.pk}/'
