import cast_upgrade_1_5_22 # @UnusedImport

from cast.application import create_link, ApplicationLevelExtension, Bookmark, open_source_file
from select_parser import SelectResult, analyse_select, parse_select
from light_parser import create_lexer, Lookahead
from sqlscript_lexer import SqlLexer
from symbols import ResolutionScope, Table, Schema, View, Index, Column
from traceback import format_exc
from logging import debug, info
from functools import lru_cache
from parser_common import Identifier

class ClientServerQRs(ApplicationLevelExtension):

        
    def end_application(self, application):
        def local_analyse_select(text, schema_name):
            lexer = create_lexer(SqlLexer)
            stream = Lookahead(lexer.get_tokens(text))
            self.scope.current_schema_name = schema_name.name
            self.scope.parent_scope = self.database
                                    
            result_select = SelectResult()
            analyse_select(parse_select(stream), result_select, self.scope, True)
            
            return result_select

        def make_sense(application):
            value = []
            # make sense to run calculations for CS with at least links
            val_1 = application.links().load_positions().has_caller(application.objects().has_type('SQLScript_Metric_ClientServer')).count() 
            if val_1 > 0:
                value.append([1, val_1])# 1st case
            
            val_2 = application.objects().load_property(138293).has_type('CAST_SQL_MetricableQuery').count()
            if val_2 > 0:
                value.append([2, val_2]) # 2nd case   
            
            val_3 = application.objects().load_property(138977).has_type('JSP_PROPERTY_MAPPING').count() 
            if val_3 > 0:                                                      
                value.append([3, val_3] ) # 3rd case  
                         
            return value
    
        def load_database(application):
            # first we load the schemas, table, view, index using parentship (case of several AUs with same name of schemas)
            indexes_by_id = {}   
            
            # first load all tables/views and their properties : but do not register them yet
            for t in application.objects().has_type(['SQLScriptTable', 'SQLScriptView']).load_property(1101002):
                
                if t.get_metamodel_type().inherit_from('SQLScriptTable'):
                    table = Table()
                else:
                    table = View()
                table.name = t.get_name()
                table.fullname = t.get_fullname()
                table.tablesize = t.get_property(1101002)
                table.kb_symbol = t
                table.id = t.id
                self.tables_by_id[t.id] = table # store them in a map for further retrieve
                        
            # then scan schemas 
            for s in application.objects().has_type('SQLScriptSchema').load_property(1101002).load_property(1101022):
                schema = Schema()
                schema.name = s.get_name()
                schema.fullname = s.get_fullname()
                schema.xxl_treshold = s.get_property(1101002) # XXL threshold
                if not schema.xxl_treshold:
                    schema.xxl_treshold = 100000
                schema.xxl_size = schema.xxl_treshold
                schema.xxs_threshold = s.get_property(1101022) # XXS threshold
                if not schema.xxs_threshold:
                    schema.xxs_threshold = 10
                schema.xxs_size = schema.xxs_threshold
                schema.kb_symbol = s
                self.database.add_symbol(schema.name, schema)
                #self.scope.add_symbol(schema.name, schema)
                # take their child for having correct schema->table parentship
                for child in s.load_children():
                    # @type child : cast.application.Object
                    is_table = child.get_metamodel_type().inherit_from('SQLScriptTable')
                    is_view = child.get_metamodel_type().inherit_from('SQLScriptView')
                    
                    if is_table or is_view:
                        
                        table = self.tables_by_id[child.id]
                        
                        # now we can know xxl/xxs status regarding to schema
                        if table.tablesize and schema.xxl_treshold:
                            if table.tablesize >= schema.xxl_treshold:
                                table.is_xxl = True
                        
                        if table.tablesize and schema.xxs_threshold:
                            if table.tablesize <= schema.xxs_threshold:
                                table.is_xxs = True
                        
                        # register it
                        schema.add_symbol(table.name, table)
                        table.parent = schema
                        table.reference = schema.find_symbol(table.name, [Table, View])
                        
                        # column loading for that table/view
                        for column in child.load_children():
                            if column.get_metamodel_type().inherit_from('SQLScriptTableColumn'):
                         
                                symbol_column = Column()
                                symbol_column.name = column.get_name()
                                symbol_column.fullname =  column.get_fullname() 
                                symbol_column.kb_symbol = column
                                symbol_column.id = column.id
                                # weird to have something different here...
                                if is_table:
                                    try: 
                                        table.register_column(symbol_column) 
                                    except:
                                        print('issue with register_column on table')
                                        pass   
                                if is_view:
                                    try: 
                                        table.columns.append(symbol_column)
                                    except:
                                        print('issue with register_column on view')
                                        pass                            
                                self.columns_by_id[column.id] = symbol_column

            # property for indexes 
            # NOTe : we do not add indexes in schema as it is not really needed (schema is here for resolution) 
            for i in application.objects().has_type('SQLScript_IndexProperties').load_property('SQLScript_IndexProperties.columns'):
                   
                index = Index()
                index.name = i.get_name()
                index.fullname = i.get_fullname()
                index.kb_symbol = i
                
                ciValues = i.get_property('SQLScript_IndexProperties.columns')
                if ciValues :
                    index.columns = ciValues.split(';')
                indexes_by_id[i.id] = index 
    #         print('database is <after indexes> :'  , database) 
                           
            # links from index to table 
            for link in application.links().has_callee(application.objects().has_type(['SQLScriptTable', 'SQLScriptView'])).has_caller(application.objects().has_type('SQLScript_IndexProperties')):
            
                table = link.get_callee()
                index = link.get_caller()
            
                symbol_table = self.tables_by_id[table.id]
                symbol_index = indexes_by_id[index.id]
            
                columns = []
                for column_name in symbol_index.columns:    
                    columns.append(symbol_table.find_column(column_name))        
                symbol_index.table = symbol_table
                symbol_index.columns = columns
                symbol_table.indexes.append(symbol_index)
                self.scope.add_symbol(symbol_table.name, symbol_table)
#             print('database is <after linking tables with indexes> :' , self.database)
            
            return self.database  
                   
        def declare_property_ownership_by_application (application):
            try:
                application.declare_property_ownership('SQLScript_Metric_ClientServer.scanned',['SQLScript_Metric_ClientServer'])
                
                application.declare_property_ownership('SQLScript_Metric_UseOfCartesianProduct.number',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_UseOfCartesianProductXXL.number',['SQLScript_Metric_ClientServer'])
                
                application.declare_property_ownership('SQLScript_Metric_NoIndexCanSupport.number',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_NoIndexCanSupportXXL.number',['SQLScript_Metric_ClientServer'])
                            
                application.declare_property_ownership('SQLScript_Metric_HasNonAnsiJoin.hasNonAnsiJoin',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_MissingParenthesisInsertClause.missingParenthesis',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_HasNumbersInOrderBy.hasNumbers',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_NaturalJoin.isNaturalJoin',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_NonSARGable.isNonSARGable',['SQLScript_Metric_ClientServer'])
    
                application.declare_property_ownership('SQLScript_Metric_UseMinusExcept.has_NotInNotExists',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnion',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnionAndUnionAll',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_ExistsIndependentClauses.has_independent_exists',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_DistinctModifiers.has_distinct',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_NonAnsiOperators.has_non_ansi_operator',['SQLScript_Metric_ClientServer'])
                application.declare_property_ownership('SQLScript_Metric_OrClausesTestingEquality.has_or_on_the_same_identifier',['SQLScript_Metric_ClientServer'])
                                                                                      
            except AttributeError:
                pass     

        def calculate_CS_links (result, client, table, save_bookmark=None): 
            # access = 0 Read, = 1 Write
            def resolve_the_table (table, table_column_alias, access):
                if access == 0:
                    for tab in result.tables:
                        if isinstance(tab[0], list) and tab[0][0].name.lower() == table.name.lower():
                            return table
                        elif (isinstance(tab[0], Identifier) and tab[0].get_name().lower() == table.name.lower() and not tab[1]) or \
                            (isinstance(tab[0], Identifier) and tab[0].get_name().lower() == table.name.lower() and tab[1] and tab[1].lower() == table_column_alias.lower()):
                            return table
                        elif not isinstance(tab[0], list) and not isinstance(tab[0], Identifier) and tab[0].name.lower() == table.name.lower() and tab[1].lower() == table_column_alias.lower():
                            return table

                    for tab in result.delete_references:
                        if isinstance(tab[0], list) and tab[0][0].name.lower() == table.name.lower():
                            return table
                        elif (isinstance(tab[0], Identifier) and tab[0].get_name().lower() == table.name.lower() and not tab[1]) or \
                            (isinstance(tab[0], Identifier) and tab[0].get_name().lower() == table.name.lower() and tab[1] and tab[1].lower() == table_column_alias.lower()):
                            return table
                        elif not isinstance(tab[0], list) and not isinstance(tab[0], Identifier) and tab[0].name.lower() == table.name.lower() and tab[1].lower() == table_column_alias.lower():
                            return table

                    for tab in result.update_references:
                        if isinstance(tab[0], list) and tab[0][0].name.lower() == table.name.lower():
                            return table
                        elif (isinstance(tab[0], Identifier) and tab[0].get_name().lower() == table.name.lower() and not tab[1]) or \
                            (isinstance(tab[0], Identifier) and tab[0].get_name().lower() == table.name.lower() and tab[1] and tab[1].lower() == table_column_alias.lower()):
                            return table
                        elif not isinstance(tab[0], list) and not isinstance(tab[0], Identifier) and tab[0].name.lower() == table.name.lower() and tab[1].lower() == table_column_alias.lower():
                            return table
                                                
                if access == 1:
                    for tab in result.insert_references:
                        if tab[0].name.lower() == table_column_alias.name.lower():
                            return tab[0]
                    
                return None
            
            def add_AR_for_all_columns_table (table):
                table_ = self.tables_by_id[table.id]
                for column in table_.columns:
                    column_ = self.columns_by_id[column.id]
                    create_link('accessReadLink', client, column_, save_bookmark)                            

            def add_AR_for_all_columns_aliased_table (table, table_column_alias):
                table_ = self.tables_by_id[table.id]
                for column in table_.columns:
                    column_ = self.columns_by_id[column.id]
                    create_link('accessReadLink', client, column_, save_bookmark)   
                
                                                                    
            # access = 0 Read, = 1 Write
            def resolve_the_column (column_name, table_column_alias, symbol_table, access):
                table = None
                table_r = None
                if symbol_table:
                    table = self.tables_by_id[symbol_table.id]
                if table_column_alias:
                    table_r = resolve_the_table (table, table_column_alias, access)

                if not table and not table_r:
                    return (None)
                if not table and table_r:
                    table = table_r

                if table.find_column_insensitive(column_name):
                    for column in table.columns:
                        if column_name.lower() == column.name.lower() and table.fullname in column.fullname:                               
                            return(self.columns_by_id[column.id])
                                             
                return (None)   
            
            # AccessRead links
            try:                        
                for selected_column in result.columns:
                    if isinstance(selected_column, list) and len(selected_column) == 2:
                        column = selected_column[0]
                        table_column_alias = selected_column[1]
                    else:
                        column = selected_column
                        table_column_alias = None

                    # try to resolve the column's bookmark
                    save_bookmark_col, starting_line = None, 0
                    if save_bookmark:
                        starting_line = save_bookmark.begin_line
                    try:
                        save_bookmark_col = Bookmark(client, starting_line + column.tokens[0].begin_line, column.tokens[0].begin_column, starting_line + column.tokens[0].end_line, column.tokens[0].end_column)
                    except:
                        try:
                            save_bookmark_col = Bookmark(client, starting_line + column.begin_line, column.begin_column, starting_line + column.end_line, column.end_column)
                        except:
                            pass
                    
                    # when the bookmark of the column could be detected
                    if save_bookmark_col:
                        save_bookmark = save_bookmark_col
                    
                    check_select_star = None
                    try:
                        check_select_star = column.text
                    except:
                        pass
                    
                    # the case of select all, without alias
                    if check_select_star == '*' and not table_column_alias:
                        add_AR_for_all_columns_table(table)
                        
                    # the case of select all, with alias
                    elif check_select_star == '*' and table_column_alias:
                        table_column_alias = table_column_alias.text
                        table_r = resolve_the_table (table, table_column_alias, 0)
                        if table_r: 
                            add_AR_for_all_columns_aliased_table(table, table_column_alias)
                    
                    # the case when columns are specified 
                    else:
                        column_object = None
                        if check_select_star and not table_column_alias:
                            column_object = resolve_the_column(check_select_star, table_column_alias, table, 0)
                        elif check_select_star and table_column_alias:
                            try:
                                column_object = resolve_the_column(check_select_star, table_column_alias.text, table, 0)
                            except:
                                column_object = None
                        else:
                            try:
                                column_object = resolve_the_column(column.get_name(), table_column_alias, table, 0)
                            except:
                                column_object = None
                        
                        if column_object:
                            debug("    Add accessReadLink between the client %s and the column %s, bookmark=(%s,%s,%s,%s)" % (client.get_fullname(), column_object.fullname, save_bookmark.begin_line, save_bookmark.begin_column, save_bookmark.end_line, save_bookmark.end_column))
                            create_link('accessReadLink', client, column_object, save_bookmark)
                          
            except AttributeError:
                pass

            # AccessWrite link
            try:
                for updated_column in result.write_columns:
                    column = updated_column[0]
                    table_column_alias = updated_column[1]
                    if not save_bookmark:
                        try:
                            save_bookmark = Bookmark(client, column.tokens[0].begin_line, column.tokens[0].begin_column, column.tokens[0].end_line, column.tokens[0].end_column)
                        except:
                            pass

                    try:
                        column_object = resolve_the_column(column.get_name(), table_column_alias, table, 1)
                    except:
                        column_object = resolve_the_column(column.text, table_column_alias, table, 1)
                        
                    if column_object:
                        debug("    Add accessWriteLink between the client %s and the column %s, bookmark=(%s,%s,%s,%s)" % (client.get_fullname(), column_object.fullname, save_bookmark.begin_line, save_bookmark.begin_column, save_bookmark.end_line, save_bookmark.end_column))
                        create_link('accessWriteLink', client, column_object, save_bookmark)
            except AttributeError:
                pass
            
        def based_on_bookmark_property(link, inf, path):
            first_line = 0
            lines = len(inf)
#             table_name = link.get_callee().name
            for line in range(first_line, lines):
                t = inf[line]
                # concatenation is not complete and is not event a ::
                if t.find("* CONCATENATION = NONE") > -1 or t.find("* CONCATENATION = PARTIAL") > -1 or t.find("* UNCERTAIN REQUEST =") > -1:  
                    continue

                start= t.find("= ") + 2
                # concatenation is missing sometimes
                if t.find("* CONCATENATION") !=  -1: end = t.find("* CONCATENATION") - 1
                else: end = t.find("* EXECUTED IN =") - 1
                query = t[start:end]
                                                        
                line_column_exec = t.find("* EXECUTED IN =")
                where_is_located = path + ':' + t[line_column_exec+15:len(t)]
                return (query, where_is_located)
            
            return ("", None) 
                                         
        def calculate_quality_rules_on_bookmarks(self, result, client, table, save_bookmark, impact_analysis):
            has_cartesian_product = False
            no_index_can_support = False
            
            has_cartesian_product_xxl = False  
            no_index_can_support_xxl = False
                                                    
            has_NotInNotExists = 0
            missingParenthesis = 0
            numberOfUnion = 0
            numberOfUnionAndUnionAll = 0
            has_nonAnsiJoin = 0
            has_numbers = 0
            has_naturalJoin = 0
            has_nonSARG = 0
            has_independent_exists = False
            has_distinct = False
            has_non_ansi_operator = False
            has_or_on_the_same_identifier = False
            
            if impact_analysis:
                calculate_CS_links (result, client, table, save_bookmark)

            for select in result.selects: 
                if select.has_cartesian_product and not has_cartesian_product: has_cartesian_product = True
                if select.has_cartesian_product_xxl and not has_cartesian_product_xxl: has_cartesian_product_xxl = True
                if select.no_index_can_support and not no_index_can_support: no_index_can_support = True
                if select.no_index_can_support_xxl and not no_index_can_support_xxl: no_index_can_support_xxl = True
                if select.has_NotInNotExists: has_NotInNotExists = max(has_NotInNotExists, select.has_NotInNotExists)
                if select.missingParenthesis: missingParenthesis = max(missingParenthesis, select.missingParenthesis)
                if select.numberOfUnion: numberOfUnion = max(numberOfUnion, select.numberOfUnion)
                if select.numberOfUnionAndUnionAll: numberOfUnionAndUnionAll = max(numberOfUnionAndUnionAll, select.numberOfUnionAndUnionAll)
                if select.has_nonAnsiJoin: has_nonAnsiJoin = max(has_nonAnsiJoin, select.has_nonAnsiJoin)
                if select.has_numbers: has_numbers = max(has_numbers, select.has_numbers)
                if select.has_naturalJoin: has_naturalJoin = max(has_naturalJoin, select.has_naturalJoin)
                if select.has_nonSARG: has_nonSARG = max(has_nonSARG, select.has_nonSARG) 
                if select.has_independent_exists: has_independent_exists = max(has_independent_exists, select.has_independent_exists)
                if select.has_distinct: has_distinct = max(has_distinct, select.has_distinct)
                if select.has_non_ansi_operator: has_non_ansi_operator = max(has_non_ansi_operator, select.has_non_ansi_operator)
                if select.has_or_on_the_same_identifier: has_or_on_the_same_identifier = max(has_or_on_the_same_identifier, select.has_or_on_the_same_identifier)
          
            try:   
                if has_or_on_the_same_identifier:
                    client.save_violation('SQLScript_Metric_OrClausesTestingEquality.has_or_on_the_same_identifier', save_bookmark)         
            except AttributeError:
                pass
                
            try:   
                if has_non_ansi_operator:
                    client.save_violation('SQLScript_Metric_NonAnsiOperators.has_non_ansi_operator', save_bookmark)         
            except AttributeError:
                pass
                                            
            try:   
                if has_distinct:
                    client.save_violation('SQLScript_Metric_DistinctModifiers.has_distinct', save_bookmark)         
            except AttributeError:
                pass
                
            try:   
                if has_independent_exists:
                    client.save_violation('SQLScript_Metric_ExistsIndependentClauses.has_independent_exists', save_bookmark)         
            except AttributeError:
                pass   
                                 
            try:   
                if has_cartesian_product:
                    client.save_violation('SQLScript_Metric_UseOfCartesianProduct.number', save_bookmark)      
            except AttributeError:
                pass    

            try:    
                if has_cartesian_product_xxl:
                    client.save_violation('SQLScript_Metric_UseOfCartesianProductXXL.number', save_bookmark)          
            except AttributeError:
                pass  
                                
            try:
                if no_index_can_support:
                    client.save_violation('SQLScript_Metric_NoIndexCanSupport.number', save_bookmark) 
            except AttributeError:
                pass

            try:
                if no_index_can_support_xxl: 
                    client.save_violation('SQLScript_Metric_NoIndexCanSupportXXL.number', save_bookmark) 
            except AttributeError:
                pass
                                  
            try:
                if has_NotInNotExists > 0: client.save_violation('SQLScript_Metric_UseMinusExcept.has_NotInNotExists', save_bookmark)
            except AttributeError:
                pass
            
            try:
                if missingParenthesis > 0: client.save_violation('SQLScript_Metric_MissingParenthesisInsertClause.missingParenthesis', save_bookmark)
            except AttributeError:
                pass
            
            try:
                if numberOfUnion > 0:
                    client.save_violation('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnion', save_bookmark)
            except AttributeError:
                pass
             
            try:
                if numberOfUnionAndUnionAll > 0:
                    client.save_violation('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnionAndUnionAll', save_bookmark)
            except AttributeError:
                pass
                                        
            try:
                if has_nonAnsiJoin > 0 :client.save_violation('SQLScript_Metric_HasNonAnsiJoin.hasNonAnsiJoin', save_bookmark)
            except AttributeError:
                pass
                
            try:
                if has_numbers > 0 :client.save_violation('SQLScript_Metric_HasNumbersInOrderBy.hasNumbers', save_bookmark)
            except AttributeError:
                pass
            
            try:
                if has_naturalJoin > 0 :client.save_violation('SQLScript_Metric_NaturalJoin.isNaturalJoin', save_bookmark)
            except AttributeError:
                pass
                 
            try:
                if has_nonSARG > 0 :client.save_violation('SQLScript_Metric_NonSARGable.isNonSARGable', save_bookmark)
            except AttributeError:
                pass
            
            return

        def calculate_quality_rules_based_on_links (application, database, impact_analysis):
            # query 
            list_of_scanned_clients = set()
            list_of_scanned_bookmarks = set()
            list_of_scanned_queries = set()
            list_of_scanned_tables_queries = ([])
            list_of_cobol_bookmarks = ([])
            list_of_cobol_files = set()
            
            #calculate rules based on links : except Cobol 
            try:
                for link in application.links().load_positions().load_property(138788).has_callee(application.objects().is_dbms().is_table()).has_caller(application.objects().has_type('SQLScript_Metric_ClientServer')):
    #                 info("link by link %s" % link)
                    query = ''
                    table_is_in_schema = None
                    path = ''
                    # only for SQL Analyzer
                    if link.get_callee().get_type() not in ('SQLScriptTable', 'SQLScriptView') or \
                        link.get_caller().get_type() in ('SQLScriptFunction', 'SQLScriptProcedure', 'SQLScriptTrigger', 'SQLScriptView', 'SQLScriptMethod'): 
                        continue
                    
                    table = link.get_callee()
                    symbol_table = self.tables_by_id[table.id]
                    table_is_in_schema = symbol_table.parent
                    self.database.current_schema_name = table_is_in_schema
                    self.symbol_table = symbol_table
        
                    client = link.get_caller()
                    bookmark = link.get_positions()
                    inf = link.get_property(138788)  
                        
                    if (bookmark and 'CAST_COBOL' in client.type.name and not (client.type =='CAST_COBOL_SavedProgram')) :
                        # the case of Cobol where statements should be decoded   
#                         info('append bookmark %s' % bookmark)
                        path = bookmark[0].file.get_path()  
                        if path not in list_of_cobol_files:
                            list_of_cobol_files.add(path)                   
                        t = [path, client, bookmark, table_is_in_schema, symbol_table]
                        list_of_cobol_bookmarks.append(t)
                        continue
    
                    if inf : 
                        scanned_bookmark = ''                     
                        query, scanned_bookmark = based_on_bookmark_property(link, inf, path)
                        
                        query_upper = query.upper()
                        if 'SELECT' in query_upper or 'INSERT' in query_upper or 'UPDATE' in query_upper or 'DELETE' in query_upper or 'TRUNCATE' in query_upper \
                                    or 'MERGE' in query_upper:
                            if query not in list_of_scanned_queries: 
                                list_of_scanned_queries.add(query)
                            elif query in list_of_scanned_queries and client not in list_of_scanned_clients:
                                pass 
                            else:
#                                 debug('        query = %s has been already scanned, table %s' % (query,  table.fullname))
#                                 print('query ', query, ' has been already scanned, table', table.fullname)
                                
                                query_table = [query, table.fullname]
                                if query_table not in list_of_scanned_tables_queries:
                                    list_of_scanned_tables_queries.append(query_table)
                                    for boo in bookmark:                                                    
                                        result = local_analyse_select(query, table_is_in_schema)
                                        
                                        if impact_analysis:
                                            calculate_CS_links (result, client, table, boo)
#                                             info('        query = %s' % query)
#                                             info('        table = %s' % table.fullname)
#                                             info('        bookmark = %s' % boo)
                                continue
                            
#                             query_table = [query, table.fullname]
#                             if query_table not in list_of_scanned_tables_queries:
#                                 list_of_scanned_tables_queries.append(query_table)   
                                                                                     
                            if client not in list_of_scanned_clients: 
                                list_of_scanned_clients.add(client)
                                try:
                                    client.save_property('SQLScript_Metric_ClientServer.scanned', 1)
                                except AttributeError:
                                    pass

                            for boo in bookmark:
                                if scanned_bookmark in list_of_scanned_bookmarks: 
                                    continue
                                else: 
                                    list_of_scanned_bookmarks.add(scanned_bookmark)
                                            
                                try:
                                    result = local_analyse_select(query, table_is_in_schema)
#                                     info('        query = %s' % query)
#                                     info('        table = %s' % table.fullname)
#                                     info('        bookmark = %s' % boo)
                                    calculate_quality_rules_on_bookmarks(self, result, client, table, boo, impact_analysis)
                                except:
                                    print('Internal issue with calculate_quality_rules_on_bookmarks : ' , format_exc())
                                    debug('Internal issue with calculate_quality_rules_on_bookmarks : %s ' % format_exc())
            except KeyError:
                pass
            
            #detach memory
            list_of_scanned_bookmarks = set()
            list_of_scanned_tables_queries = ([])
            list_of_scanned_queries = set()
  
            if len(list_of_cobol_files) > 0:
                info("2.1. Start scanning links for Cobol") 
                
                # Cobol case
                list_of_scripts = ([])
                for cobol_file in list_of_cobol_files:
                    with open_source_file(cobol_file) as f:
                        script = f.readlines()
                        script_sql = ''
                        start = False
                        begin_line = 0
                        begin_column = 0
                        end_line = 0
                        end_column = 0
                        count = 0
                        for line in script:
                            line = line.upper()
                            count += 1 
                            if 'EXEC SQL' in line and not 'END-EXEC' in line:
                                start = True
                                if 'SELECT' in line or 'INSERT' in line or 'UPDATE' in line or 'DELETE' in line \
                                    or 'TRUNCATE' in line or 'MERGE' in line:
                                    if 'SELECT' in line:
                                        start_sql = line.find('SELECT')
                                    elif 'INSERT' in line:
                                        start_sql = line.find('INSERT')
                                    elif 'UPDATE' in line:
                                        start_sql = line.find('UPDATE')
                                    elif 'DELETE' in line:
                                        start_sql = line.find('DELETE')
                                    elif 'TRUNCATE' in line:
                                        start_sql = line.find('TRUNCATE')
                                    elif 'MERGE' in line:
                                        start_sql = line.find('MERGE')
                                    end_sql= len(line)
                                    script_sql += line[start_sql:len(line)]
                                else:
                                    start_sql = line.find('EXEC SQL')+ 8
                                    end_sql= line.find('EXEC SQL')
                                    script_sql += line[start_sql:len(line)-end_sql]
                                begin_line = count
                                begin_column = start_sql
                            elif 'EXEC SQL' in line and 'END-EXEC' in line:
                                start = False
                                start_sql = line.find('EXEC SQL')+ 8
                                end_sql= line.find('END-EXEC')
                                script_sql = line[start_sql :end_sql]
                                begin_line = count
                                begin_column = start_sql
                                end_line = count
                                end_column = end_sql
                                if 'SELECT' in script_sql or 'INSERT' in script_sql or 'UPDATE' in script_sql or 'DELETE' in script_sql or 'TRUNCATE' in script_sql \
                                    or 'MERGE' in script_sql:
                                    t = [cobol_file, script_sql, begin_line, begin_column, end_line, end_column]
                                    list_of_scripts.append(t)
                                script_sql = ''
                                start = False
                                begin_line = 0
                                begin_column = 0
                                end_line = 0
                                end_column = 0
                            elif 'EXEC SQL' not in line and 'END-EXEC' in line:
                                start = False
                                end_sql = line.find('END-EXEC')
                                script_sql += line[-1::end_sql]
                                end_line = count
                                end_column = end_sql
                                if 'SELECT' in script_sql or 'INSERT' in script_sql or 'UPDATE' in script_sql or 'DELETE' in script_sql or 'TRUNCATE' in script_sql \
                                    or 'MERGE' in script_sql:
                                    t = [cobol_file, script_sql, begin_line, begin_column,end_line, end_column]
                                    list_of_scripts.append(t)
                                script_sql = ''
                                start = False
                                begin_line = 0
                                begin_column = 0
                                end_line = 0
                                end_column = 0
                            elif start:
                                if line[:6].isdigit():
                                    script_sql += line[7:]
                                else:
                                    script_sql += line
        
#                 info('list_of_scripts %s ' % len(list_of_scripts))

                @lru_cache(maxsize=None)
                def match_bookmark_by_file (cobol_file, begin_line, end_line):
                    matches  = ([])
                    for sql_bookmark in list_of_cobol_bookmarks:
                        if cobol_file == sql_bookmark[0]:
                            table_is_in_schema = sql_bookmark[3]
                            symbol_table = sql_bookmark[4]
                            client = sql_bookmark[1]
                            for boo in sql_bookmark[2]:
                                if boo.begin_line >= begin_line and boo.end_line <= end_line:
                                    t = [client, symbol_table, table_is_in_schema]
                                    if t not in matches:
                                        matches.append(t)
                                        continue
                            
                    return matches
                
                @lru_cache(maxsize=None)
                def retrieve_program(client, not_a_program):
                    for i in application.objects().has_type('CAST_COBOL_SavedProgram').load_property(137685).load_property(139261):
                        if i.get_fullname() == not_a_program or i.get_fullname() == client.fullname:
                            if i.get_fullname() == not_a_program:
                                client = i
                            break
                    
                    return client
            
                list_of_matches  = ([])
                list_of_scanned_clients = set()
                for sql in list_of_scripts:
                    cobol_file = sql[0]
                    script_sql = sql[1]
                    begin_line = sql[2]
                    begin_column = sql[3]
                    end_line = sql[4]
                    end_column = sql[5]
                    del list_of_matches
                    list_of_matches =  match_bookmark_by_file (cobol_file, begin_line, end_line)
                                    
                    if len(list_of_matches) > 0:
                        for match in list_of_matches:
                            cobol_client = match[0]
                            symbol_table = match[1]
                            not_a_program = cobol_client.fullname.replace('.'+ cobol_client.name, '')
                            client = retrieve_program(cobol_client, not_a_program)
                            
                            if client not in list_of_scanned_clients:  
                                list_of_scanned_clients.add(client)
                                try:
                                    client.save_property('SQLScript_Metric_ClientServer.scanned', 1)
                                except:
                                    debug('Internal issue with scanned property : %s ' % format_exc()) 
                                    
                                bookmark = Bookmark(client, begin_line, begin_column, end_line, end_column)
                                result = local_analyse_select(script_sql, match[2])
                                calculate_quality_rules_on_bookmarks(self, result, cobol_client, symbol_table, bookmark, impact_analysis) 
                info("2.1. End scanning links for Cobol") 
                        
        def calculate_quality_rules_on_object(self, result, client):
            has_cartesian_product = False
            no_index_can_support = False
            
            has_cartesian_product_xxl = False  
            no_index_can_support_xxl = False
                                                    
            has_NotInNotExists = 0
            missingParenthesis = False
            numberOfUnion = 0
            numberOfUnionAndUnionAll = 0
            has_nonAnsiJoin = 0
            has_numbers = 0
            has_naturalJoin = 0
            has_nonSARG = 0
            has_independent_exists = False
            has_distinct = False
            has_non_ansi_operator = False
            has_or_on_the_same_identifier = False

            for select in result.selects:           
                if select.has_cartesian_product_xxl and not has_cartesian_product_xxl: has_cartesian_product_xxl = True
                if select.has_cartesian_product and not has_cartesian_product: has_cartesian_product = True
                if select.no_index_can_support_xxl and not no_index_can_support_xxl: no_index_can_support_xxl = True
                if select.no_index_can_support and not no_index_can_support: no_index_can_support = True
                if select.has_NotInNotExists: has_NotInNotExists = max(has_NotInNotExists, select.has_NotInNotExists)
                if select.missingParenthesis: missingParenthesis = max(missingParenthesis, select.missingParenthesis)
                if select.numberOfUnion: numberOfUnion = max(numberOfUnion, select.numberOfUnion)
                if select.numberOfUnionAndUnionAll: numberOfUnionAndUnionAll = max(numberOfUnionAndUnionAll, select.numberOfUnionAndUnionAll)
                if select.has_nonAnsiJoin: has_nonAnsiJoin = max(has_nonAnsiJoin, select.has_nonAnsiJoin)
                if select.has_numbers: has_numbers = max(has_numbers, select.has_numbers)
                if select.has_naturalJoin: has_naturalJoin = max(has_naturalJoin, select.has_naturalJoin)
                if select.has_nonSARG: has_nonSARG = max(has_nonSARG, select.has_nonSARG)  
                if select.has_independent_exists: has_independent_exists = max(has_independent_exists, select.has_independent_exists)
                if select.has_distinct: has_distinct = max(has_distinct, select.has_distinct)
                if select.has_non_ansi_operator: has_non_ansi_operator = max(has_non_ansi_operator, select.has_non_ansi_operator)
                if select.has_or_on_the_same_identifier: has_or_on_the_same_identifier = max(has_or_on_the_same_identifier, select.has_or_on_the_same_identifier)

            try:   
                if has_or_on_the_same_identifier:
                    client.save_property('SQLScript_Metric_OrClausesTestingEquality.has_or_on_the_same_identifier', 1)         
            except:
                debug('Internal issue with has_or_on_the_same_identifier %s' % format_exc())
                
            try:   
                if has_non_ansi_operator:
                    client.save_property('SQLScript_Metric_NonAnsiOperators.has_non_ansi_operator', 1)         
            except:
                debug('Internal issue with has_non_ansi_operator %s' % format_exc())
                                            
            try:   
                if has_distinct:
                    client.save_property('SQLScript_Metric_DistinctModifiers.has_distinct', 1)         
            except:
                debug('Internal issue with has_distinct %s' % format_exc())
                
            try:   
                if has_independent_exists:
                    client.save_property('SQLScript_Metric_ExistsIndependentClauses.has_independent_exists', 1)         
            except:
                debug('Internal issue with has_independent_exists %s' % format_exc())    

            try:   
                if has_cartesian_product:
                    client.save_property('SQLScript_Metric_UseOfCartesianProduct.number', 1)          
            except:
                debug('Internal issue with has_cartesian_product %s' % format_exc()) 
                                
            try:   
                if has_cartesian_product_xxl:
                    client.save_property('SQLScript_Metric_UseOfCartesianProductXXL.number', 1)          
            except:
                debug('Internal issue with has_cartesian_product_xxl %s' % format_exc())    

            try:
                if no_index_can_support:
                    client.save_property('SQLScript_Metric_NoIndexCanSupport.number', 1) 
            except:
                debug('Internal issue with no_index_can_support %s' % format_exc())
                                
            try:
                if no_index_can_support_xxl: 
                    client.save_property('SQLScript_Metric_NoIndexCanSupportXXL.number', 1) 
            except:
                debug('Internal issue with no_index_can_support_xxl %s' % format_exc())
                  
            try:
                if has_NotInNotExists > 0: client.save_property('SQLScript_Metric_UseMinusExcept.has_NotInNotExists', has_NotInNotExists)
            except:
                debug('Internal issue with has_NotInNotExists %s' % format_exc())
            
            try:
                if missingParenthesis: 
                    client.save_property('SQLScript_Metric_MissingParenthesisInsertClause.missingParenthesis', 1)
            except:
                debug('Internal issue with missingParenthesis %s' % format_exc())
            
            try:
                if numberOfUnion > 0:
                    client.save_property('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnion', numberOfUnion)
            except:
                debug('Internal issue with numberOfUnion %s' % format_exc())
             
            try:
                if numberOfUnionAndUnionAll > 0:
                    client.save_property('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnionAndUnionAll', numberOfUnionAndUnionAll)
            except:
                debug('Internal issue with numberOfUnionAndUnionAll %s' % format_exc())
                                        
            try:
                if has_nonAnsiJoin > 0 :client.save_property('SQLScript_Metric_HasNonAnsiJoin.hasNonAnsiJoin', has_nonAnsiJoin)
            except:
                debug('Internal issue with has_nonAnsiJoin %s' % format_exc())
                
            try:
                if has_numbers > 0 :client.save_property('SQLScript_Metric_HasNumbersInOrderBy.hasNumbers', has_naturalJoin)
            except:
                debug('Internal issue with has_numbers in order by clause: %s' % format_exc())
            
            try:
                if has_naturalJoin > 0 :client.save_property('SQLScript_Metric_NaturalJoin.isNaturalJoin', has_naturalJoin)
            except:
                debug('Internal issue with has_naturalJoin : %s' % format_exc())
                 
            try:
                if has_nonSARG > 0 :client.save_property('SQLScript_Metric_NonSARGable.isNonSARGable', has_nonSARG)
            except:
                debug('Internal issue with has_nonSARG %s' % format_exc())

            return
            
        def calculate_quality_rules_based_on_property (application, database, list_of_schemas, impact_analysis, case, number_of_lines):
            # sql named query & map property
            def calculate_AR_links_for_tables (schema, result):
                for table in result.tables:
                    try:
                        symbol_table = schema.find_symbol(table[0].get_fullname(), [Table, View])
                    except AttributeError:
                        symbol_table = schema.find_symbol(table[0][0].get_fullname(), [Table, View])
                        
                    if symbol_table:
#                         debug(' calculate_CS_links_for_tables for the result : %s ' %result)
                        calculate_CS_links (result, client, symbol_table)

                for table in result.update_references:
                    try:
                        symbol_table = schema.find_symbol(table[0].get_fullname(), [Table, View])
                    except AttributeError:
                        symbol_table = schema.find_symbol(table[0][0].get_fullname(), [Table, View])
                        
                    if symbol_table:
#                         debug(' calculate_CS_links_for_tables for the result : %s ' %result)
                        calculate_CS_links (result, client, symbol_table)

                for table in result.delete_references:
                    try:
                        symbol_table = schema.find_symbol(table[0].get_fullname(), [Table, View])
                    except AttributeError:
                        symbol_table = schema.find_symbol(table[0][0].get_fullname(), [Table, View])

                    if symbol_table:
#                         debug(' calculate_CS_links_for_tables for the result : %s ' %result)
                        calculate_CS_links (result, client, symbol_table)
                                                
            def calculate_AW_links_for_tables (schema, result):                            
                for table in result.insert_references:
                    try:
                        symbol_table = schema.find_symbol(table[0].get_fullname(), [Table, View])
                    except AttributeError:
                        symbol_table = schema.find_symbol(table[0][0].get_fullname(), [Table, View])
                        
                    if symbol_table:
#                         debug(' calculate_CS_links_for_tables for the result : %s ' %result)
                        calculate_CS_links (result, client, symbol_table)

            
            if case == 2 and number_of_lines > 0:
                list_of_queries = []
                # Sql Query (138293) for Refers to a SQL Query, contains properties that will be processed by Metric Assistant (CAST_SQL_MetricableQuery)
                for client in application.objects().load_property(138293).has_type('CAST_SQL_MetricableQuery'):
                    query = ''
                    query = client.get_property(138293) 
                    if query:
                        t = [client, query]
                        list_of_queries.append(t)
                        
            if case == 3 and number_of_lines > 0:
                list_of_queries = []
                # Map value (138977) for Java Properties File (JSP_PROPERTY_MAPPING)
                for client in application.objects().load_property(138977).has_type('JSP_PROPERTY_MAPPING'):
                    query = ''
                    query = client.get_property(138977) 
                    if query:
                        query_upper = query.upper()
                        if ('SELECT' in query_upper and 'SELECTED' not in query_upper and 'FROM' in query_upper) \
                            or ('INSERT' in query_upper and ('VALUES' in query_upper or 'SELECT' in query_upper)) \
                            or ('UPDATE' in query_upper and 'SET' in query_upper) \
                            or ('DELETE' in query_upper and 'FROM' in query_upper) \
                            or 'TRUNCATE' in query_upper \
                            or 'MERGE' in query_upper:
                            t = [client, query]
                            list_of_queries.append(t)
                        
            if len(list_of_queries) > 0:
                for one_by_one_query in list_of_queries:
                    client = one_by_one_query[0]
                    query = one_by_one_query [1]
                    info('Scan object=%s, query=%s ' % (client.fullname, query))
                    try:
                        client.save_property('SQLScript_Metric_ClientServer.scanned', 1)
                    except:
                        debug('Internal issue with scanned property : %s ' % format_exc()) 
                                
                    try: 
                        list_of_queries.remove(one_by_one_query)  
                        for schema in list_of_schemas:   
                            result = local_analyse_select(query, schema) 
                            calculate_quality_rules_on_object(self, result, client) 
                            
                            if impact_analysis and result.columns:       
                                calculate_AR_links_for_tables (schema, result)
                            
                            if impact_analysis and result.write_columns:
                                calculate_AW_links_for_tables (schema, result)
                    except:
                        debug('Internal issue when calculate quality rules on the object : %s ' % format_exc())  
                        
                list_of_queries = []

        impact_analysis = False
        list_of_extensions = application.get_knowledge_base().get_extensions()
        
        # the case of unit test, when we don't have a KB
        if len(list_of_extensions) == 0:
            impact_analysis = True
        else:
            for extension in list_of_extensions:
                if extension[0].lower() == 'com.castsoftware.datacolumnaccess':
                    impact_analysis = True
                    break

        if impact_analysis:
            info("Data Column Access is activated")
        
        self.scope = ResolutionScope()
        self.database = ResolutionScope()
        self.symbol_table = None
        self.tables_by_id = {}
        self.columns_by_id = {}
     
        info("Start calculating client server properties for application %s" % application.name)

        question = make_sense(application)
                
        if len(question) == 0:
            info("There is no client server link or query object to be scanned")
        else:
            info("1. Loading database")
            self.database = load_database(application)
            if len(self.database.symbols)== 0:
                info("There is no database to be loaded")
            else:
                declare_property_ownership_by_application(application) 
                list_of_schemas = set() 
                for obj in self.tables_by_id:
                    table_schema = self.tables_by_id[obj].parent
                    if table_schema not in list_of_schemas:
                        list_of_schemas.add(table_schema)

                for line in question:
                    if line[0] == 1 and line[1] > 0:   
                        info("2. Scanning links (%s)" % line[1])
                        calculate_quality_rules_based_on_links (application, self.database, impact_analysis)
                    elif line[0] == 2 and line[1] > 0:
                        info('3. Scanning queries object for SQL Named Queries (%s)' % line[1])
                        calculate_quality_rules_based_on_property (application, self.database, list_of_schemas, impact_analysis, line[0], line[1])
                    elif line[0] == 3 and line[1] > 0:
                        info('3.2 Scanning queries object for Java Properties Mapping (%s)' % line[1])
                        calculate_quality_rules_based_on_property (application, self.database, list_of_schemas, impact_analysis, line[0], line[1])
                 
                list_of_schemas = set()
                
        info("End calculating client server properties for application %s" % application.name)