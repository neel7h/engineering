import cast_upgrade_1_5_22 # @UnusedImport

from cast.application import  ApplicationLevelExtension, Bookmark, LinkType
from select_parser import SelectResult, analyse_select, parse_select
from light_parser import create_lexer, Lookahead
from sqlscript_lexer import SqlLexer
from symbols import ResolutionScope, Table, Schema, View
import traceback
import logging
from cast.application import create_link

class UseLinks(ApplicationLevelExtension):
      
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
            
            val_1 = application.objects().load_property(138293).has_type('CAST_SQL_NamedQuery').count()
            if val_1 > 0:
                value.append([1, val_1]) # 1st case   
            
            val_2 = application.objects().load_property(138977).has_type('JSP_PROPERTY_MAPPING').count() 
            if val_2 > 0:                                                  
                value.append([2, val_2]) # 2nd case  
                         
            return value
    
        def load_database(application):
            
            # first load all tables/views and their properties : but do not register them yet
            for t in application.objects().has_type(['SQLScriptTable', 'SQLScriptView']):
                
                if t.get_metamodel_type().inherit_from('SQLScriptTable'):
                    table = Table()
                else:
                    table = View()
                table.name = t.get_name()
                table.fullname = t.get_fullname()
                table.kb_symbol = t
                table.id = t.id
                self.tables_by_id[t.id] = table # store them in a map for further retrieve
                        
            # then scan schemas 
            for s in application.objects().has_type('SQLScriptSchema'):
                schema = Schema()
                schema.name = s.get_name()
                schema.fullname = s.get_fullname()
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
                        
                        # register it
                        schema.add_symbol(table.name, table)
                        table.parent = schema
                        table.reference = schema.find_symbol(table.name, [Table, View])
    
            # links from the client to table 
            has_table_type = ['SQLScriptTable', 'SQLScriptView']
            for link in application.links().has_type(LinkType.useSelect).has_callee(application.objects().is_dbms().is_table().has_type(has_table_type)).has_caller(application.objects().has_type(['CAST_SQL_NamedQuery', 'JSP_PROPERTY_MAPPING'])):
                table = link.get_callee()
                client = link.get_caller()
                symbol_table = self.tables_by_id[table.id]
                self.client_table_select_links_by_id[symbol_table] = client.id

            for link in application.links().has_type(LinkType.useUpdate).has_callee(application.objects().is_dbms().is_table().has_type(has_table_type)).has_caller(application.objects().has_type(['CAST_SQL_NamedQuery', 'JSP_PROPERTY_MAPPING'])):
                table = link.get_callee()
                client = link.get_caller()
                symbol_table = self.tables_by_id[table.id]
                self.client_table_update_links_by_id[symbol_table] = client.id

            for link in application.links().has_type(LinkType.useDelete).has_callee(application.objects().is_dbms().is_table().has_type(has_table_type)).has_caller(application.objects().has_type(['CAST_SQL_NamedQuery', 'JSP_PROPERTY_MAPPING'])):
                table = link.get_callee()
                client = link.get_caller()
                symbol_table = self.tables_by_id[table.id]
                self.client_table_delete_links_by_id[symbol_table] = client.id

            for link in application.links().has_type(LinkType.useInsert).has_callee(application.objects().is_dbms().is_table().has_type(has_table_type)).has_caller(application.objects().has_type(['CAST_SQL_NamedQuery', 'JSP_PROPERTY_MAPPING'])):
                table = link.get_callee()
                client = link.get_caller()
                symbol_table = self.tables_by_id[table.id]
                self.client_table_insert_links_by_id[symbol_table] = client.id
                                                           
            return self.database  

        def add_use_links (application, database, list_of_schemas, case, number_of_lines):
            # sql named query & map property
            def calculate_U_links_for_tables (schema, tables, kindOfLink):
                for table in tables:
                    symbol_table = None
                    
                    try:
                        tok = table[0]
                        symbol_table = schema.find_symbol(tok.get_fullname(), [Table, View])
                    except AttributeError:
                        tok = table[0][0]
                        symbol_table = schema.find_symbol(tok.get_fullname(), [Table, View])
                        
                    # if the link exists
                    if symbol_table:
                        try:
                            # the link exists
                            if (kindOfLink == 'useSelectLink' and self.client_table_select_links_by_id[symbol_table] == client.id) \
                                or (kindOfLink == 'useUpdateLink' and self.client_table_update_links_by_id[symbol_table] == client.id)\
                                or (kindOfLink == 'useDeleteLink' and self.client_table_delete_links_by_id[symbol_table] == client.id)\
                                or (kindOfLink == 'useInsertLink' and self.client_table_insert_links_by_id[symbol_table] == client.id):
                                continue
                        except KeyError:
                            # there is no link
                            begin = tok.tokens[0]
                            end = tok.tokens[-1]
                            symbol_bookmark = Bookmark(client, begin.get_begin_line(), begin.get_begin_column(), end.get_end_line(), end.get_end_column())
                            print('    Add ', kindOfLink, ' between ', client.fullname,' and ',  symbol_table.fullname, ', bookmark=(', symbol_bookmark, ')')
                            logging.debug("    Add %s between %s and %s, bookmark=(%s)" % (kindOfLink, client.fullname, symbol_table.fullname, symbol_bookmark))
                            create_link(kindOfLink, client, symbol_table, symbol_bookmark)
                            self.added_links += 1
                    
            list_of_queries = []
            
            if case == 1 and number_of_lines > 0:
                # Sql Query (138293) for Refers to a SQL Query, contains properties that will be processed by Metric Assistant (CAST_SQL_MetricableQuery)

                for client in application.objects().load_property(138293).has_type('CAST_SQL_MetricableQuery'):    #           
                    query = ''
                    query = client.get_property(138293) 
                    if query:
                        t = [client, query]
                        list_of_queries.append(t)
                        
            elif case == 2 and number_of_lines > 0:
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
                print("There are ", len(list_of_queries), " SQL queries to be processed.")
                logging.info("There are %s SQL queries to be processed." % len(list_of_queries))
                for one_by_one_query in list_of_queries:
                    client = one_by_one_query[0]
                    query = one_by_one_query [1]                           
                    try: 
                        list_of_queries.remove(one_by_one_query)  
                        for schema in list_of_schemas:   
                            result = local_analyse_select(query, schema) 

                            if result.tables:
                                calculate_U_links_for_tables (schema, result.tables, 'useSelectLink')
                            
                            if result.update_references:
                                calculate_U_links_for_tables (schema, result.update_references, 'useUpdateLink')

                            if result.delete_references:
                                calculate_U_links_for_tables (schema, result.delete_references, 'useDeleteLink')

                            if result.insert_references:
                                calculate_U_links_for_tables (schema, result.insert_references, 'useInsertLink')
                                                                                                
                    except:
                        logging.debug('Internal issue when add links on the object : %s ' % traceback.format_exc()) 
                
                list_of_queries = [] 
            else:
                print("There is no SQL query to be processed." )
                logging.info("There is no SQL query to be processed.")                    
                
        
        # the case of unit test, when we don't have a KB
        self.scope = ResolutionScope()
        self.database = ResolutionScope()
        self.symbol_table = None
        self.tables_by_id = {}
        self.client_table_select_links_by_id = {}
        self.client_table_update_links_by_id = {}
        self.client_table_delete_links_by_id = {}
        self.client_table_insert_links_by_id = {}
        self.added_links = 0
     
        print("Start adding missing links between SQL Named Queries, Java Properties Mapping and SQL Tables / Views for application " , application.name)
        logging.info("Start adding missing links between SQL Named Queries, Java Properties Mapping and SQL Tables / Views for application %s" % application.name)

        question = make_sense(application)
                
        if len(question) == 0:
            logging.info("There is no query object to be scanned")
        else:
            logging.info("1. Loading database")
            self.database = load_database(application)
            if len(self.database.symbols)== 0:
                logging.info("There is no database to be loaded")
            else:
                list_of_schemas = set() 
                for obj in self.tables_by_id:
                    table_schema = self.tables_by_id[obj].parent
                    if table_schema not in list_of_schemas:
                        list_of_schemas.add(table_schema)

                for line in question:
                    if line[0] == 1 and line[1] > 0:   
                        print('2. Scanning queries object for SQL Named Queries (', line[1], ')' )
                        logging.info('2. Start Scanning queries object for SQL Named Queries (%s).' % line[1])
                        add_use_links (application, self.database, list_of_schemas, line[0], line[1])
                    if line[0] == 2 and line[1] > 0:
                        print('3. Scanning queries object for Java Properties Mapping (', line[1], ')' )
                        logging.info('3. Scanning queries object for Java Properties Mapping (%s)' % line[1])
                        add_use_links (application, self.database, list_of_schemas, line[0], line[1])
                 
                list_of_schemas = set()
        
        if self.added_links > 0:
            suffix_message = ('Added %s new links.' % self.added_links)
        else:
            suffix_message = 'No new link have been added.'

        print("End adding missing links between SQL Named Queries, Java Properties Mapping and SQL objects for application ", application.name, '.', suffix_message)
        logging.info("End adding missing links between SQL Named Queries, Java Properties Mapping and SQL objects for application %s. %s" % (application.name, suffix_message))
        