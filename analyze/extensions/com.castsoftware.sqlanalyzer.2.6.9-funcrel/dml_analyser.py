'''
Analysis switched to DDL common part on 2 feb. 2019
Added internal scope

@author: DOP
'''
from light_parser import Lookahead

from select_parser import SelectResult, parse_select, analyse_select, ExecuteDynamicString4
from dml_parser import Convert_SpoolDefine

from cast.analysers import external_link, create_link, Bookmark, log
from symbols import Schema, Table, View, TableSynonym, ViewSynonym, Synonym,\
            Function, Procedure, Method, FunctionSynonym, ProcedureSynonym

from parser_common import parse_identifier

def analyse_dml_select(f, scope=None):
    
    stream_has_been_replaced, replaced_stream, initial_stream = Convert_SpoolDefine(f)

    if stream_has_been_replaced:
        stream = Lookahead(replaced_stream)
    else:
        stream = initial_stream

    result = SelectResult()
    analyse_select(parse_select(stream), result, scope)
        
    return result

def analyse_dml(f, caller, file, scope):
    f.seek(0)
    result = analyse_dml_select(f, scope)
    schemas = scope.find_symbols(scope.get_schema_name(), [Schema])

    link_type = 'useSelectLink'
    for selected_table in result.tables:
        table = selected_table[0]
        table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
        
        try:
            table.reference = get_internal_callee(schemas, table) if schemas else None
        except Exception as table_cannot_be_resolved:
            log.debug('Table %s cannot be resolved (%s).' % (table.name, table_cannot_be_resolved))
        
        try:
            add_new_link(file, link_type, caller, table) 
        except Exception as link_cannot_be_added:
            log.debug('%s cannot be added for %s (%s).' % (link_type, table.name, link_cannot_be_added))
  
    link_type = 'useInsertLink'
    for inserted_table in result.insert_references:
        table = inserted_table [0]
        table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
        try:
            table.reference = get_internal_callee(schemas, table) if schemas else None
        except Exception as table_cannot_be_resolved:
            log.debug('Table %s cannot be resolved (%s).' % (table.name, table_cannot_be_resolved))
        try:
            add_new_link(file, link_type, caller, table) 
        except Exception as link_cannot_be_added:
            log.debug('%s cannot be added for %s (%s).' % (link_type, table.name, link_cannot_be_added))

    link_type = 'useUpdateLink'
    for updated_table in result.update_references:
        table = updated_table [0]
        table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
        try:
            table.reference = get_internal_callee(schemas, table) if schemas else None
        except Exception as table_cannot_be_resolved:
            log.debug('Table %s cannot be resolved (%s).' % (table.name, table_cannot_be_resolved))
            
        try:
            add_new_link(file, link_type, caller, table) 
        except Exception as link_cannot_be_added:
            log.debug('%s cannot be added for %s (%s).' % (link_type, table.name, link_cannot_be_added))

    link_type = 'useDeleteLink'
    for deleted_table in result.delete_references:
        # the case when is a list vs identifier
        try:
            table = deleted_table[0][0]
        except:
            table = deleted_table[0]
        table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
    
        try:
            table.reference = get_internal_callee(schemas, table) if schemas else None
            if isinstance(table.reference, list) and len(table.reference) == 0:
                table.reference = None
        except Exception as table_cannot_be_resolved:
            log.debug('Table %s cannot be resolved (%s).' % (table.name, table_cannot_be_resolved))
            
        try:
            add_new_link(file, link_type, caller, table) 
        except Exception as link_cannot_be_added:
            log.debug('%s cannot be added for %s (%s).' % (link_type, table.name, link_cannot_be_added))                             

    link_type = 'callLink'
    for proc in result.functions:
        proc.types = [Function, Procedure, Method, FunctionSynonym, ProcedureSynonym, Synonym]
        try:
            proc.reference = get_internal_callee(schemas, proc) if schemas else None
        except Exception as proc_cannot_be_resolved:
            log.debug('Procedure/Function %s cannot be resolved (%s).' % (proc.name, proc_cannot_be_resolved))
            
        try:
            add_new_link(file, link_type, caller, proc) 
        except Exception as link_cannot_be_added:
            log.debug('%s cannot be added for %s (%s).' % (link_type, proc.name, link_cannot_be_added))

    # the case of EXECUTE <PROCEDURE>
    for proc in result.dexecutes:
        if isinstance(proc, ExecuteDynamicString4):
            tokens = proc.get_children()
            # skip EXECUTE
            next(tokens)
            proc = parse_identifier(tokens, force_parse=True)
            proc.types = [Function, Procedure, Method, FunctionSynonym, ProcedureSynonym, Synonym]

            try:
                proc.reference = get_internal_callee(schemas, proc) if schemas else None
            except Exception as proc_cannot_be_resolved:
                log.debug('Procedure/Function %s cannot be resolved (%s).' % (proc.name, proc_cannot_be_resolved))
                             
            try:                      
                add_new_link(file, link_type, caller, proc) 
            except Exception as link_cannot_be_added:
                log.debug('%s cannot be added for %s (%s).' % (link_type, proc.name, link_cannot_be_added))

def get_internal_callee(schemas, obj):
    obj.reference = None
    
    for schema in schemas:
        obj.reference = schema.resolve_reference(obj)
        if obj.reference:
            break
    return obj.reference

def get_bookmark(file, identifier):
    bookmark = None
    
    if identifier.get_name():
        begin = identifier.tokens[0]
        end = identifier.tokens[-1]
        bookmark = Bookmark(file, begin.get_begin_line(), begin.get_begin_column(), end.get_end_line(), end.get_end_column()) 
        
    return bookmark 

def add_new_link(file, link_type, caller, callee_internal):
    # add link with bookmark
    bookmark = None
    try:
        bookmark = get_bookmark (file, callee_internal)
    except Exception as bookmark_issue:
        log.debug('Issue detected when calculate bookmark : %s' % bookmark_issue)
    
    if not bookmark:
        return

    # links between DML and DDL AU in the same application
    try:
        if callee_internal.reference:
            callee_internal_reference = callee_internal.reference[0]
            create_link(link_type, caller, callee_internal_reference.kb_symbol, bookmark)
    except Exception as link_cannot_be_added:
        log.debug('%s cannot be added %s (%s).' % (link_type, callee_internal.name, link_cannot_be_added)) 

    link_added = None 
    
    # links between DML and other RDBMS, linked by via dependency and external_link module
    
    # 1. search by full name
    try:
        for callee in external_link.find_objects(callee_internal.get_fullname(), 'APM Server objects'):
            create_link(link_type, caller, callee, bookmark)
            link_added = True
    except Exception as link_cannot_be_added:
        log.debug('%s cannot be added %s (%s).' % (link_type, callee_internal.name, link_cannot_be_added)) 

    # 2. no link has been added, search again by name
    if not link_added:
        try:
            for callee in external_link.find_objects(callee_internal.name, 'APM Server objects'):
                create_link(link_type, caller, callee, bookmark)
        except Exception as link_cannot_be_added:
            log.debug('%s cannot be added %s (%s).' % (link_type, callee_internal.name, link_cannot_be_added)) 