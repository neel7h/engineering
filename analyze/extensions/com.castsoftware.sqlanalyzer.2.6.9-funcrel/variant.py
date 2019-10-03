'''
Created on 19 sept. 2016

@author: MRO
'''
from enum import Enum


class Variant(Enum):

    ansisql = 'ansisql'
    
    postgresql = 'postgresql'
    # mysql/mariadb
    mysql = 'mysql'
    db2 = 'db2'
    informix = 'informix'
    oracle = 'oracle'
    # sqlserver/sybase
    sqlserver = 'sqlserver'
    sapsqlscript = 'sapsqlscript'

def detect_variant(file_path, cache=None):
    """
    Tries to detect the SQL variant of a file
    
    :return: 'postgresql', 'mariadb/mysql', 'db2', 'informix', 'oracle', 'sqlserver', 'ansisql'
    
    Searches for given pattern in file.
    """
    from analyser import open_source_file

    
    patterns = {'language plpgsql':Variant.postgresql, 
                '$$;':Variant.postgresql,
                'pg_dump':Variant.postgresql,
                'search_path':Variant.postgresql,
                'from stdin;':Variant.postgresql,
                'set client_encoding':Variant.postgresql,
                'engine=':Variant.mysql,
                'definer=':Variant.mysql,
                'db2look':Variant.db2,
                'db2 admin':Variant.db2,
                '"sysibm"':Variant.db2,
                'sysibm':Variant.db2,
                'sysibmts':Variant.db2,
                'set current sqlid':Variant.db2,
                'informix':Variant.informix,
                'package body':Variant.oracle,
                'type body':Variant.oracle,
                'varchar2':Variant.oracle,
                'nvarchar2':Variant.oracle,
                'nested_table_id':Variant.oracle,
                'nologging':Variant.oracle,
                '[dbo]':Variant.sqlserver,
                '.dbo.':Variant.sqlserver,
                'select top':Variant.sqlserver,
                'sp_executesql':Variant.sqlserver,
                'setuser':Variant.sqlserver,
                'sysobjects':Variant.sqlserver,
                'syb_quit()':Variant.sqlserver,
                '@@rowcount':Variant.sqlserver,
                'execute_prepared_stmt':Variant.sqlserver
                }
    
    # pattern that must be one line (for example a line containing only GO indicates sqlserver 
    one_liner_patterns = {'go':Variant.sqlserver,
                          '/':Variant.oracle}
    
    detected_variant = Variant.ansisql
    with open_source_file(file_path, cache) as f: 
        for line in f:
            # everything lower case
            line = line.lower() 
            for pattern in patterns:
                detected_variant = patterns[pattern]
                if pattern in line and detected_variant != Variant.sqlserver:
                    return detected_variant, False
    
            for pattern in one_liner_patterns:
                if (line == pattern + '\n' or line == pattern) and pattern == 'go':
                    detected_variant = one_liner_patterns[pattern]
                    return detected_variant, True
                elif line == pattern + '\n':
                    detected_variant = one_liner_patterns[pattern]
                    return detected_variant, False

    return Variant.ansisql, False