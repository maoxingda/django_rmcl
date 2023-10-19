import re


def remove_comments(sql_text):
    """
    删除sql_text中的注释
    @param sql_text: 包含注释的SQL文本
    @return: 删除sql_text中的注释之后剩下的文本
    """
    # /*
    # ...
    # */
    multiline_comment_pattern = re.compile(r'''
        /\*  # start with /*
        .*?  # any characters, contains newline(\n), non-greedy mode
        \*/  # end with */
    ''', re.VERBOSE | re.DOTALL)

    # -- ...
    single_line_pattern = re.compile(r'''
        --   # start with --
        .*   # any characters, not contains newline(\n)
    ''', re.VERBOSE)

    sql_text = multiline_comment_pattern.sub('', sql_text)
    sql_text = single_line_pattern.sub('', sql_text)

    sql_text = sql_text.replace('/**/', '')

    return sql_text


def remove_procedure(sql_text):
    """
    删除存储过程
    @param sql_text: 包含存储过程的SQL文本
    @return: 删除存储过程之后剩下的文本
    """
    procedure_pattern = re.compile(r'create\s+(?:or replace\s+)procedure\s+\w+\(.*begin(.*)end;', re.DOTALL | re.IGNORECASE)

    what = procedure_pattern.search(sql_text)
    if what:
        sql_text = what.group(1)

    return sql_text
