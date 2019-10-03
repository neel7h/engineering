import sqlparse
from sqlparse.sql import IdentifierList, Identifier
from sqlparse.tokens import Keyword, DML

def is_subselect(parsed):
    if not parsed.is_group():
        return False
    for item in parsed.tokens:
        if item.ttype is DML and item.value.upper() == 'SELECT':
            return True
    return False

def extract_first_keyword(parsed):
    for item in parsed.tokens:
        if item.ttype is Keyword:
            return item.normalized
    return None

def extract_table_identifiers(parsed, tables):
    from_seen = False
    join_seen = False
    firstKeyword = None
    for item in parsed.tokens:
        if not firstKeyword and item.ttype is Keyword.DML:
            firstKeyword = item.normalized
        if from_seen:
            if is_subselect(item):
                extract_table_identifiers(item, tables)
            elif item.ttype is Keyword:
                return
            else:
                if isinstance(item, IdentifierList):
                    from_seen = False
                    for identifier in item.get_identifiers():
                        if firstKeyword:
                            tables.append({ 'name' : identifier.get_name(), 'operation' : firstKeyword })
                        else:
                            tables.append({ 'name' : identifier.get_name() })
                elif isinstance(item, Identifier):
                    from_seen = False
                    if firstKeyword:
                        tables.append({ 'name' : item.value, 'operation' : firstKeyword })
                    else:
                        tables.append({ 'name' : item.value })
                # It's a bug to check for Keyword here, but in the example
                # above some tables names are identified as keywords...
                elif item.ttype is Keyword:
                    from_seen = False
                    if firstKeyword:
                        tables.append({ 'name' : item.value, 'operation' : firstKeyword })
                    else:
                        tables.append({ 'name' : item.value })
        elif join_seen:
            if isinstance(item, Identifier):
                join_seen = False
                if firstKeyword:
                    tables.append({ 'name' : item.value, 'operation' : firstKeyword })
                else:
                    tables.append({ 'name' : item.value })
            # It's a bug to check for Keyword here, but in the example
            # above some tables names are identified as keywords...
            elif item.ttype is Keyword:
                join_seen = False
                if firstKeyword:
                    tables.append({ 'name' : item.value, 'operation' : firstKeyword })
                else:
                    tables.append({ 'name' : item.value })
        elif item.ttype is Keyword and item.value.upper() == 'FROM':
            from_seen = True
        elif item.ttype is Keyword and item.value.upper().endswith('JOIN'):
            join_seen = True

def extract_tables(query):
    
    tables = []
    extract_table_identifiers(sqlparse.parse(query)[0], tables)
    return tables
