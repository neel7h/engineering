import cast.analysers.jee
from cast.analysers import log, create_link, Bookmark, CustomObject
from functools import lru_cache

class JEEAllEvents(cast.analysers.jee.Extension):
    """
    Logs all jee callbacks
    """

    class TypeContext:
        def __init__(self, typ):
            self.currentClass = typ
                
    def __init__(self):
        self.indentation = 0
        self.database = None
        self.connection_parent = None
        self.java_parser = None
        
        self.member_list = ([])
        
        self.list_of_marklogic_databases = ([])
        self.list_of_marklogic_duplicated_databases = ([])      
        self.list_of_marklogic_collections = ([])

        self.list_of_marklogic_queries = ([])
        self.list_of_marklogic_called_databases = ([])
        
        self.list_of_marklogic_collections_calls = ([])
        self.list_of_marklogic_database_calls = ([])
        self.list_of_marklogic_database_links = ([])
        self.list_of_marklogic_called_documents = ([])
        
        self.list_of_marklogic_selects = ([])
        self.list_of_marklogic_updates = ([])
        self.list_of_marklogic_deletes = ([])
        self.list_of_marklogic_inserts = ([])

        self.list_of_marklogic_unresolved_queries = ([])
        self.collection_dml_links  = ([])    
        
        self.variable_dictionary = {}
       
    @lru_cache(maxsize=1)
    def read_caller_lines (self, file):
        fp = open(file, 'r')
        lines = fp.readlines()
        fp.close()
#         log.info('cache_info for read_caller_lines %s ' % str(self.read_caller_lines.cache_info()))
        return lines
                                    
    # receive a java parser from platform
    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def receive_java_parser(self, parser):
        self.java_parser = parser

    @lru_cache(maxsize=1)
    def get_ast_caller (self, caller):
        self.java_parser.parse(caller.get_position().get_file().get_path())
        ast = self.java_parser.get_object_ast(caller) 
#         log.info('cache_info for get_ast_caller %s ' % str(self.get_ast_caller.cache_info()))
        return ast
    
    def start_analysis(self, options):
        """
        Called at the beginning of analysis

        :param cast.analysers.JEEExecutionUnit options: analysis option

        @type options: cast.analysers.JEEExecutionUnit
        """
                                                                                                 
        # marklogic, only supported methods     
        options.add_parameterization("com.marklogic.client.DatabaseClientFactory.newClient(java.lang.String,int)", [1], self.append_marklogic_databases)         
        options.add_parameterization("com.marklogic.client.DatabaseClientFactory.newClient(java.lang.String,int,java.lang.String)",  [1,3], self.append_marklogic_databases)      
        options.add_parameterization("com.marklogic.client.DatabaseClientFactory.newClient(java.lang.String,int,com.marklogic.client.DatabaseClientFactory.SecurityContext)", [1,3], self.append_marklogic_databases) 
        options.add_parameterization("com.marklogic.client.DatabaseClientFactory.newClient(java.lang.String,int,java.lang.String,com.marklogic.client.DatabaseClientFactory.SecurityContext)",  [1,3], self.append_marklogic_databases)       
        options.add_parameterization("com.marklogic.client.DatabaseClientFactory.newClient(java.lang.String,int,java.lang.String,java.lang.String,com.marklogic.client.DatabaseClientFactory.Authentication)", [1], self.append_marklogic_databases) 
        
        options.add_parameterization("com.marklogic.client.query.StructuredQueryBuilder.collection(java.lang.String[])", [1], self.append_marklogic_collections)                                  
        options.add_parameterization("com.marklogic.client.query.QueryDefinition.setCollections(java.lang.String[])", [1], self.append_marklogic_collections)                                  

        options.add_parameterization("com.marklogic.client.DatabaseClient.newTextDocumentManager", [1], self.append_triky_marklogic_collections)  
        options.add_parameterization("com.marklogic.client.DatabaseClient.newXMLDocumentManager", [1], self.append_triky_marklogic_collections)  
        options.add_parameterization("com.marklogic.client.document.XMLDocumentManager", [1], self.append_triky_marklogic_collections)  
        options.add_parameterization("com.marklogic.client.query.QueryManager.search.search <SearchHandle>", [1], self.append_marklogic_collections_select_links) 
                            
                            
        options.add_parameterization("com.marklogic.client.document.DocumentManager.read(java.lang.String[])", [1], self.append_marklogic_collections_select_links)  
        options.add_parameterization("com.marklogic.client.document.DocumentManager.search(com.marklogic.client.query.QueryDefinition,long)", [1], self.append_marklogic_collections_select_links)  
        options.add_parameterization("com.marklogic.client.document.XMLDocumentManager.read(java.lang.String[])", [1], self.append_marklogic_collections_select_links)  
        options.add_parameterization("com.marklogic.client.document.XMLDocumentManager.search(com.marklogic.client.query.QueryDefinition,long)", [1], self.append_marklogic_collections_select_links)  
        options.add_parameterization("com.marklogic.client.document.TextDocumentManager.read(java.lang.String[])", [1], self.append_marklogic_collections_select_links)  
        options.add_parameterization("com.marklogic.client.document.TextDocumentManager.search(com.marklogic.client.query.QueryDefinition,long)", [1], self.append_marklogic_collections_select_links)  
        
        options.add_parameterization("com.marklogic.client.document.DocumentManager.write(com.marklogic.client.document,com.marklogic.client.io.marker)", [1], self.append_marklogic_collections_insert_links)  
        options.add_parameterization("com.marklogic.client.document.DocumentManager.write(java.lang.String,com.marklogic.client.io.marker.AbstractWriteHandle)", [1], self.append_marklogic_collections_insert_links)  
        options.add_parameterization("com.marklogic.client.bitemporal.TemporalDocumentManager.write(java.lang.String,com.marklogic.client.io.marker.DocumentMetadataWriteHandle,com.marklogic.client.io.marker.AbstractWriteHandle,com.marklogic.client.document.ServerTransform,com.marklogic.client.Transaction,java.lang.String)", [1], self.append_marklogic_collections_insert_links)          
        options.add_parameterization("com.marklogic.client.document.XMLDocumentManager.write(java.lang.String,com.marklogic.client.io.marker.DocumentMetadataWriteHandle,com.marklogic.client.io.marker.AbstractWriteHandle,com.marklogic.client.document.ServerTransform,com.marklogic.client.Transaction,java.lang.String)", [1], self.append_marklogic_collections_insert_links)  
        options.add_parameterization("com.marklogic.client.document.TextDocumentManager.write(java.lang.String,com.marklogic.client.io.marker.DocumentMetadataWriteHandle,com.marklogic.client.io.marker.AbstractWriteHandle,com.marklogic.client.document.ServerTransform,com.marklogic.client.Transaction,java.lang.String)", [1], self.append_marklogic_collections_insert_links)  

        options.add_parameterization("com.marklogic.client.document.DocumentManager.delete(java.lang.String)", [1], self.append_marklogic_collections_delete_links)  
                       
        options.add_classpath('marklogic')
        
    def start_member(self, member):
        if member.get_typename() == "JV_FIELD":
            ast = self.get_ast_caller(member)  
           
            if ast:
                children = ast.children
            token_list = []
            token_val = []
            list_val = []
            token_equal_index = 0
            token_equal_line = 0
            try:
                for child in children:
                        token_list.append(child)
            except:
                pass
            
            
            
            for token in token_list:
               
                if token.text == "=":
                    
                    token_equal_line = token.get_begin_line()
                    token_equal_index = token_list.index(token)
                    token_equal_val = token_list[token_equal_index]
                    token_variable_val = token_list[token_equal_index-1]
                    token_constant = token_list[token_equal_index:]
                    token_constant_val = token_constant[1:]
                    
                    if len(token_constant_val) == 2:
                        for val in token_constant_val:
                            if not val == ";" and val.get_type() == "ConstantString":
                                self.variable_dictionary[token_variable_val.text] = val.value
                    if len(token_constant_val) > 2:
                        
                        for val in token_constant_val:
                            if not val in[';', '+']:
                                if val.get_type() == "ConstantString":
                                    list_val.append(val.value)
                                else:
                                    if val.text in self.variable_dictionary.keys():
                                        dict_val = self.variable_dictionary.get(val.text)
                                        list_val.append(dict_val)
                                    else:
                                        list_val.append(val.text)
               
                        result = ""
                        if list_val:
                            for element in list_val:
                                if element:
                                    element = element.strip('"')
                                    result += str(element)
                        self.variable_dictionary[token_variable_val.text] = result

    def end_analysis(self): 
        for member in self.member_list:
            try:
                self.get_marklogic_member_path(member)
            except:
                pass

        def look_for_equal(line, lines):
            equal_line = line-1
            if lines[equal_line].find('=') == -1:
                equal_line = look_for_equal(equal_line, lines)
                
            return equal_line
                 
        for query in self.list_of_marklogic_unresolved_queries:
            collection_name = str(query[2][1]).replace("'", '').replace('[', '').replace(']', '')
            for key,val in self.variable_dictionary.items():
                if val == collection_name:
                    collection_var = key
                    
            lines = self.read_caller_lines(query[0].get_position().get_file().get_path())
            min_lines = int(query[1])-5
            max_lines = int(query[1])+5
            alias_collection = None
            for line in range(min_lines, max_lines):
                if lines[line].find('{') > 0 or lines[line].find('}') > 0:
                    break
                try:
                    if lines[line].find(collection_name) > 0 or lines[line].find(collection_var) > 0:
                        equal_line =  look_for_equal (line, lines)
                        lines[equal_line].find('=')
                        equal_position = lines[equal_line].find('=')
                        alias_string_01 = lines[equal_line][0:equal_position-1].rstrip()
                        empty_space_position = alias_string_01.rfind(' ')
                        alias_collection = alias_string_01[empty_space_position:len(alias_string_01)].lstrip()
                        for select_line in range(line, max_lines):
                            if lines[select_line].find('{') > 0 or lines[select_line].find('}') > 0:
                                break
                            try:
                                alias_position = lines[select_line].rfind(alias_collection)
                                dml_position = lines[select_line].find('.search')
                                if dml_position > 0 and alias_position > dml_position:
                                   
                                    t = [collection_name, 'useSelectLink', query[0], Bookmark(query[0].get_position().get_file(), select_line + 1, alias_position, select_line + 1, alias_position + len(alias_collection)) ]
#                                     log.info('t is %s' %t)
                                    if not t in self.collection_dml_links:
                                        self.collection_dml_links.append(t) 
                                        break
                            except:
                                pass  
                        
                        break
                except:
                    pass                            
            
        # when the parametrization is not enough
        list_of_files = []     
        list_of_files_as_string = []   
        list_of_selected_files_to_scan = ([])
        if len(self.list_of_marklogic_selects) > 0:
            for caller in self.list_of_marklogic_selects:
                t = [caller[1].get_position().get_file().get_path(), caller[1], caller[2]]
                if not t in list_of_selected_files_to_scan:
                    list_of_selected_files_to_scan.append(t)
                if not str(caller[1].get_position().get_file()) in list_of_files_as_string:
                    list_of_files.append(caller[1].get_position().get_file().get_path())
                    list_of_files_as_string.append(str(caller[1].get_position().get_file()))

        list_of_inserted_files_to_scan = ([])      
        if  len(self.list_of_marklogic_inserts) > 0:
            for caller in self.list_of_marklogic_inserts:
                t = [caller[1].get_position().get_file().get_path(), caller[1], caller[2]]
                if not t in list_of_inserted_files_to_scan:
                    list_of_inserted_files_to_scan.append(t)
                if not str(caller[1].get_position().get_file()) in list_of_files_as_string:
                    list_of_files.append(caller[1].get_position().get_file().get_path())
                    list_of_files_as_string.append(str(caller[1].get_position().get_file()))
                                       
        list_of_updated_files_to_scan = ([])      
        if  len(self.list_of_marklogic_updates) > 0:
            for caller in self.list_of_marklogic_updates:
                t = [caller[1].get_position().get_file().get_path(), caller[1], caller[2]]
                if not t in list_of_updated_files_to_scan:
                    list_of_updated_files_to_scan.append(t)
                if not str(caller[1].get_position().get_file()) in list_of_files_as_string:
                    list_of_files.append(caller[1].get_position().get_file().get_path())
                    list_of_files_as_string.append(str(caller[1].get_position().get_file()))
         
        list_of_deleted_files_to_scan = ([])   
        if  len(self.list_of_marklogic_deletes) > 0:
            for caller in self.list_of_marklogic_deletes:
                t = [caller[1].get_position().get_file().get_path(), caller[1], caller[2]]
                if not t in list_of_deleted_files_to_scan:
                    list_of_deleted_files_to_scan.append(t)
                if not str(caller[1].get_position().get_file()) in list_of_files_as_string:
                    list_of_files.append(caller[1].get_position().get_file().get_path())
                    list_of_files_as_string.append(str(caller[1].get_position().get_file()))
       
        for file in list_of_files:
            lines = self.read_caller_lines(file)
            for select in list_of_selected_files_to_scan:
                line_number = select[2]
                if select[0] == file:                   
                    line_number = select[2]
                    if lines [select[2]].find('.search') > 0 and lines [select[2]].find('.read') > 0 or \
                        lines [select[2] - 1].find('.search') > 0 or lines [select[2] - 1].find('.read') > 0:
#                         log.info('line_number %s %s' % (line_number, lines [line_number]))
                        t = [line_number, Bookmark(select[1].get_position().get_file(), line_number, 0, line_number + 1, 0), select[1], 'useSelectLink']
                        if t not in self.list_of_marklogic_database_calls:
                            self.list_of_marklogic_database_calls.append(t)                                                                
                        
            # call_query, child, file, kind_of_cal
            # t = [call_query, child, file, kind_of_call]
            for insert in list_of_inserted_files_to_scan:
                if insert[0] == file:
                    line_number = insert[2]
                    if lines [insert[2]].find('.write') > 0 or lines [insert[2] - 1].find('.write') > 0 or\
                        lines [insert[2]].find('.create') > 0 or lines [insert[2] - 1].find('.create') > 0:
#                         log.info('line_number %s %s' % (line_number, lines [line_number]))
                        t = [line_number, Bookmark(insert[1].get_position().get_file(), line_number, 0,line_number + 1, 0),  insert[1], 'useInsertLink']
                        if t not in self.list_of_marklogic_database_calls:
                            self.list_of_marklogic_database_calls.append(t)  
                            
            for update in list_of_updated_files_to_scan:
                if update[0] == file:
                    line_number = update[2]
                    if lines [update[2]].find('.patch') > 0 or lines [update[2] - 1].find('.patch') > 0:
#                         log.info('line_number %s %s' % (line_number, lines [line_number]))
                        t = [line_number, Bookmark(update[1].get_position().get_file(), line_number, 0,line_number + 1, 0),  update[1], 'useUpdateLink']
                        if t not in self.list_of_marklogic_database_calls:
                            self.list_of_marklogic_database_calls.append(t)    

            for delete in list_of_deleted_files_to_scan:
                if delete[0] == file:
                    line_number = delete[2]
                    if lines [delete[2]].find('.delete') > 0 or lines [delete[2] - 1].find('.delete') > 0:
                        t = [line_number, Bookmark(delete[1].get_position().get_file(), line_number, 0,line_number + 1, 0),  delete[1], 'useDeleteLink']
                        if t not in self.list_of_marklogic_database_calls:
                            self.list_of_marklogic_database_calls.append(t)   

        # t = [term, caller, line, column]
        for t in self.list_of_marklogic_databases:
            for database_call in self.list_of_marklogic_database_calls:
                if database_call[2].get_position().get_file() == t[1].get_position().get_file():
                    try:
                        next_t = [t[0], database_call[2], Bookmark(database_call[2].get_position().get_file(), database_call[1].get_begin_line(), database_call[1].get_begin_column(),database_call[1].get_end_line(), database_call[1].get_end_column() + 1),database_call[3]]
                    except:
                        # the case before, when bookmark is in the position 0+1
                        next_t = [t[0], database_call[2], database_call[1], database_call[3]]
                        
                    if next_t not in self.list_of_marklogic_database_links:
                        self.list_of_marklogic_database_links.append(next_t)
                        
        if len(self.list_of_marklogic_databases) > 0:
            log.info('Start marklogic analysis')
            self.add_marklogic_databases()
            self.add_marklogic_collections()                    
            log.info('End marklogic analysis')

    def get_marklogic_member_path(self, caller):
        def detect_marklogic_collection_calls(child, tokens, kind_of_call):
            for call_query in self.list_of_marklogic_queries:
                for detect_query in tokens:
                    if detect_query.get_children():
                        tokensparenthesis = detect_query.get_children()
                        if tokensparenthesis.move_to(call_query[0]) == call_query[0]:
                            t = [call_query[0], child, kind_of_call]
                            if t not in self.list_of_marklogic_collections_calls:
                                self.list_of_marklogic_collections_calls.append(t)  

        def detect_marklogic_delete_database(child, tokens, file, kind_of_call):
            for call_query in self.list_of_marklogic_called_databases:
                if tokens.text.find(call_query[0]+'.') >= 0:
                    t = [call_query, child, file, kind_of_call]
                    self.list_of_marklogic_database_calls.append(t) 

        def detect_marklogic_call_document(child, file, kind_of_call):
            for call_query in self.list_of_marklogic_called_documents:
                if child.text.find(call_query[0]+'.') >= 0:
                    t = [call_query[1], child, file, kind_of_call]
                    self.list_of_marklogic_database_calls.append(t) 
                                                                                                
        def check_againg_child (childrens):
            query_name = ''
            client_name = None
            alias_client_name = None
            for child in childrens:
#                 log.info('child is %s' % child)
                try:
                    if child.get_children():    
                        check_againg_child (child.get_children())
                    elif child.text.find('.search') >= 0 or child.text.find('.read') >= 0 or child.text.find('.write') >= 0 \
                        or child.text.find('.create') >= 0 \
                        or child.text.find('.delete') >= 0 or child.text.find('.patch') >= 0:
                            try:
                                list_of_the_next_childrens = next(childrens)
                            except:
                                continue
                            tokens = list_of_the_next_childrens.get_children()
                            
                            if child.text.find('.search') >= 0:
                                detect_marklogic_collection_calls (child, tokens, 'useSelectLink')
    
                            elif child.text.find('.read') >= 0:
                                detect_marklogic_call_document (child, caller, 'useSelectLink')
                                
                            elif child.text.find('.write') >= 0 or child.text.find('.create') >= 0:
                                detect_marklogic_call_document (child, caller, 'useInsertLink')
                                                    
                            elif child.text.find('.delete') >= 0:
                                if client_name:
                                    detect_marklogic_delete_database (child, client_name,  caller, 'useDeleteLink')
                                else:
                                    detect_marklogic_call_document (child, caller, 'useDeleteLink')
    
                            elif child.text.find('.patch') >= 0:
                                detect_marklogic_call_document (child, caller, 'useUpdateLink')
                                                    
                    elif child.text.find('.setCollections') > 0:
                        query_name = child.text.replace('.setCollections','')
                        t = [query_name, child]
                        if t not in self.list_of_marklogic_queries:
                            self.list_of_marklogic_queries.append(t)
#                             log.info('add in list_of_marklogic_queries %s' %t )
                                
                    elif child and child.text.find('.newClient') > 0 and client_name:
                        t = [client_name.text, child]
                        if t not in self.list_of_marklogic_called_databases:
                            self.list_of_marklogic_called_databases.append(t)
                            client_name = None
                                
                    elif child and child.text.find('.new') > 0 and client_name:
                        if  child.text.find('.') == child.text.find('.new'):
                            alias_client_name = child.text[0:child.text.find('.')]
                        else:
                            alias_client_name = child.text[child.text.find('.')+1:child.text.find('.new')]

                        t = [client_name.text, alias_client_name, child]
                        if t not in self.list_of_marklogic_called_documents:
                            self.list_of_marklogic_called_documents.append(t)
                            
                    elif (child.text != '=' and child.text !='(' and child.text != ')' and child.text !='{' and child.text !='}'):
                        client_name = child
                except:
                    pass
                                                
        ast = self.get_ast_caller(caller)                            
        try:           
            for child in ast.get_children():
                if child.get_children():
                    check_againg_child (child.get_children())                    
        except:
            pass
        

            
    def append_marklogic_databases(self, values, caller, line, column):
        if not caller in self.member_list:
            self.member_list.append(caller)

        val = []
        if len(values) == 0:
            return
            
        try:
            if len(values) == 2:
                for term1 in values[1]:
                    if term1 and term1.lower() != 'null' and (term1.lower().find('-') == -1 or term1.lower().find('-') > 1) and term1.lower().find('.marklogic.com') == -1 and str(term1) not in val:
                        for term3 in values[3]:
                            if term3 and term3.lower() != 'null' and (term3.lower().find('-') == -1 or term3.lower().find('-') > 1) and term3.lower().find('.marklogic.com') == -1 and str(term1)+ ' ' + str(term3) not in val:
                                val.append(str(term1)+ ' ' + str(term3))
                            elif str(term1) not in val:
                                val.append(term1)
        except:
            pass
        try:
            if len(values) == 1 and values[1]:
                for term1 in values[1]:
                    if term1 and term1.lower() != 'null' and (term1.lower().find('-') == -1 or term1.lower().find('-') > 1) and term1.lower().find('.marklogic.com') == -1 and str(term1) not in val:
                        val.append(str(term1))  
        except:
            pass

        try:                     
            if len(values) == 1 and values[3]:
                for term3 in values[3]:
                    if term3 and term3.lower() != 'null' and (term3.lower().find('-') == -1 or term3.lower().find('-') > 1) and term3.lower().find('.marklogic.com') == -1 and str(term3) not in val:
                        val.append(str(term3)) 

        except:
            pass
   
        
        if len(val) >= 1:
            for term in val:
                same_position = [caller, line, column]
                if same_position not in self.list_of_marklogic_duplicated_databases:
                    self.list_of_marklogic_duplicated_databases.append(same_position)
                    t = [term, caller, line, column]
                    if t not in self.list_of_marklogic_databases:
                        self.list_of_marklogic_databases.append(t)

    def append_triky_marklogic_collections(self, values, caller, line, column):
        if not caller in self.member_list:
            self.member_list.append(caller)
#         log.info(' append_triky_marklogic_collections : %s , caller : %s, line : %s, column : %s' % (values,  caller, line, column))

    def append_marklogic_collections(self, values, caller, line, column):
        t = [caller, line, values]
        if not t in self.list_of_marklogic_unresolved_queries:
            self.list_of_marklogic_unresolved_queries.append(t)
#             log.info('list_of_marklogic_unresolved_queries %s' % t)
        if not caller in self.member_list:
            self.member_list.append(caller)
        if len(values) >= 1:
            t = [values[1], caller, line, column]
            self.list_of_marklogic_collections.append(t)
                        
    def append_marklogic_collections_select_links(self, values, caller, line, column):
#         log.info('append_marklogic_collections_select_links : (%s %s %s %s)' % (values, caller, line, column))	
        t = [values, caller, line, column]
        self.list_of_marklogic_selects.append (t)

    def append_marklogic_collections_update_links(self, values, caller, line, column):
        if not caller in self.member_list:
            self.member_list.append(caller)
#         log.info('append_marklogic_collections_update_links : (%s %s %s %s)' % (values, caller, line, column))    
        t = [values, caller, line, column]
        self.list_of_marklogic_updates.append (t)

    def append_marklogic_collections_insert_links(self, values, caller, line, column):
        if not caller in self.member_list:
            self.member_list.append(caller)
#         log.info('append_marklogic_collections_update_links : (%s %s %s %s)' % (values, caller, line, column))    
        t = [values, caller, line, column]
        self.list_of_marklogic_inserts.append (t)
        
    def append_marklogic_collections_delete_links(self, values, caller, line, column):
        if not caller in self.member_list:
            self.member_list.append(caller)
#         log.info('append_marklogic_collections_delete_links : (%s %s %s %s)' % (values, caller, line, column))    
        t = [values, caller, line, column]
        self.list_of_marklogic_deletes.append (t)
                
    def add_marklogic_databases(self):            
        list_of_databases = []
        duplicates_links = []

        def find_nth(haystack, needle, n):
            start = haystack.find(needle)
            while start >= 0 and n > 1:
                start = haystack.find(needle, start+len(needle))
                n -= 1
            return start
                    
        for database in self.list_of_marklogic_databases:
            if str(database[0]) not in list_of_databases:
                list_of_databases.append(str(database[0]))
                result = CustomObject()
                result.set_name(str(database[0]))
                result.set_type('CAST_Java_MarkLogic_Database')
                result.set_parent(database[1].get_project())
                result.save()
                
                result.save_position(Bookmark(database[1].get_position().get_file(), int(database[2]), int(database[3]), int(database[2]) + 1, 0))
                
                create_link('parentLink', result, database[1].get_project())
                self.database = result
            else:
                result.set_name(str(database[0]))
                result.set_type('CAST_Java_MarkLogic_Database')
            
            for link in self.list_of_marklogic_database_links:
                link_string = link[3] + str(link [0])+str(link [1])+ str(link[2])[0 : find_nth(str(link[2]), ',', 2)]
                if not link_string in duplicates_links and str(link[0]) == str(database[0]):
                    duplicates_links.append(link_string)
                    try:
                        create_link(link[3], link[1], result, link[2])
                    except:
                        pass

            create_link('useLink', database[1], result, Bookmark(database[1].get_position().get_file(), int(database[2]), int(database[3]), int(database[2]) + 1, 0))

    def add_marklogic_collections(self):     
        list_of_marklogic_collections_names = ([])  
              
        for collection in self.list_of_marklogic_collections: 
            if str(collection[0][0]) not in list_of_marklogic_collections_names:
                list_of_marklogic_collections_names.append(collection[0][0])
                result = CustomObject()
                result.set_name(str(collection[0][0]))
                result.set_type('CAST_Java_MarkLogic_Collection')
                # same assumption as for mondogo db, there is a single top object, database
                result.set_parent(self.database)
                result.save()
                result.save_position(Bookmark(collection[1].get_position().get_file(), collection[2], collection[3],  collection[2]+1, 0))
                for marklogic_link in self.collection_dml_links:
                    if str(collection[0][0]) == marklogic_link[0]:
                        create_link( marklogic_link[1], marklogic_link[2], result, marklogic_link[3])

                create_link('useLink', collection[1], result, Bookmark(collection[1].get_position().get_file(), collection[2], collection[3],  collection[2]+1, 0))
                for marklogic_query in self.list_of_marklogic_queries:
                    if collection[2] == marklogic_query[1].get_begin_line() and collection[3] == marklogic_query[1].get_begin_column():
                        for colsel in self.list_of_marklogic_collections_calls:
                            if colsel[0] == marklogic_query[0]:
                                create_link(colsel[2], collection[1], result, \
                                            Bookmark(collection[1].get_position().get_file(), \
                                                      colsel[1].get_begin_line(),colsel[1].get_begin_column(), colsel[1].get_end_line(), colsel[1].get_end_column()))
            else:
                result.set_name(str(collection[0][0]))
                result.set_type('CAST_Java_MarkLogic_Collection')
                result.save_position(Bookmark(collection[1].get_position().get_file(), collection[2], collection[3],  collection[2]+1, 0))
            



            
            