import cast.analysers.jee
import itertools
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
        self.mongo_database = None
        self.mongo_connection = None
        self.connection_parent = None
        self.java_parser = None
        self.classType = None
        self.typename = None
        self.values = ([])
        self.val = None 
        self.conn_parent = None
        
#         self.modal_class = None
        
        
        self.next_cont = False
        self.flag_index = False
        self.flag_BasicDBObject = False
        self.user_authentication = ([])
        self.class_list = ([])
        self.method_obj = ([])
        self.list_of_mongodb_connections = ([])
        self.list_of_mongodb_aliases_connections = ([])
        self.list_of_mongodb_collections = ([])
        self.list_of_mongodb_databases = ([])
        self.list_of_mongodb_database_connection_list = ([])
        self.anonymous_callers = ([])
        self.member_list = ([])
        self.mongodb_connection_objects = ([])
        self.list_of_mongodb_aliases_databases = ([])
        
        self.list_of_mongodb_collections_update = ([])
        self.list_of_mongodb_collections_insert = ([])
        self.list_of_mongodb_collections_delete = ([])
        self.list_of_mongodb_collections_select = ([])
        
        #the case of jongo for mongo
        self.list_of_jongo_mongo_connections = ([])
        self.append_jongo_mongodb_match = ([])
        self.list_of_jongo_collections = ([])
        self.list_of_jongo_called_collections = ([])
        self.list_of_collections_name = ([])
        self.list_of_collection_object = ([])
        self.list_of_beans = ([])
        self.list_of_spring_connection_violation = ([])
        
        self.list_of_unknown_databases = ([])
        
        self.list_of_violation_mongodb_compound_indexing = ([])
        self.list_index = ([])
        self.list_with_explain =([])
        self.list_connection_with_violation = ([])
        self.valid_connections = ([])
        self.list_spring_connection_with_violation = ([])
        self.mongoOperation_bookmark = ([])
        self.constructor_bookmark = ([])
        
        self.collection_with_index = {}
        self.collection_dictionary = {}
        self.keyspace_map_dict = {}
        self.class_anno_dict = {}
        self.dict_method_class_obj_mapping = {}
        
        
                   
    # receive a java parser from platform
    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def receive_java_parser(self, parser):
        self.java_parser = parser

    @lru_cache(maxsize=1)
    def read_caller_lines (self, caller):
        fp = open(caller.get_position().get_file().get_path(), 'r')
        lines = fp.readlines()
        fp.close()
#         log.info('cache_info for read_caller_lines %s ' % str(self.read_caller_lines.cache_info()))
        return lines

    @lru_cache(maxsize=1)
    def get_ast_caller (self, caller):
        self.java_parser.parse(caller.get_position().get_file().get_path())
        ast = self.java_parser.get_object_ast(caller) 
#         log.info('cache_info for get_ast_caller %s ' % str(self.get_ast_caller.cache_info()))
        return ast
    
    def get_member_informations(self, member, line, column):     
        ast = self.get_ast_caller(member)    
#         log.info('get_file %s %s ' % (member, member.get_position().get_file()))
        new_member = member
        if str( member).find('.<anonymous>.') > -1:
            anonymous_cut_to = str(member).find('.<anonymous>.')
            existing_member_name = str(member)[0:anonymous_cut_to].replace('Method(','')
#             log.info('<anonymous> detected, we should get the parent name = %s' % existing_member_name)
            for check_for_member in self.member_list:
                if check_for_member[0] == existing_member_name:
                    new_member= check_for_member[1]
                    break 
                                    
        # MongoClientURI mongoClientURI = new MongoClientURI(mongohqUrl);
        lines = self.read_caller_lines(member)
        new_position = lines[line - 1].find('new')
        line_len =  len(lines[line - 1])
        connection_name = lines[line - 1][new_position:line_len].lstrip()

        _connection_name = lines[line - 1][0:new_position]
        _connection_name = _connection_name.lstrip()
        equal_position = _connection_name.find('=')
        first_empty_space = _connection_name.find(' ')
        alias_connection_name = _connection_name[first_empty_space:equal_position].lstrip().rstrip()
            
        if not ast:            
            MongoClientURI_position = connection_name.find('MongoClientURI')
            connection_name = connection_name[MongoClientURI_position:line_len]
            
            MongoClientURI_openpar = connection_name.find('(')
            connection_name = connection_name[MongoClientURI_openpar + 1:line_len]
            
            MongoClientURI_closepar = connection_name.find(')')
            connection_name = connection_name[0:MongoClientURI_closepar]

            t = [connection_name, new_member, line, column]
            self.list_of_mongodb_connections.append(t)     
            
            t = [connection_name, alias_connection_name]
            self.list_of_mongodb_aliases_connections.append(t)
#             log.info('not ast %s %s' %(connection_name, alias_connection_name))
        else:
            def get_var_connections(children):
                mongoclient_connection_detected = False
                new_detected = False
                for child in children.get_children():
                    if child.get_children():
                        if mongoclient_connection_detected and child.get_type() == "Parenthesis":
                            for sub_child in child.get_children():
                                mongoclient_connection_detected = False
                                if not sub_child in ['(',')']:
                                    t = [sub_child.text, new_member, sub_child.get_begin_line(), sub_child.get_begin_column()]
                                    self.list_of_mongodb_connections.append(t)
                                    t = [sub_child.text, alias_connection_name]
                                    self.list_of_mongodb_aliases_connections.append(t)
        #                             log.info('ast %s %s' %(connection.text, alias_connection_name))
                        get_var_connections(child)
                    else:
                        if child.text == "new":
                            new_detected = True
                        elif child.text.find("MongoClientURI")  >= 0 and new_detected:
                            mongoclient_connection_detected = True
                            new_detected = False
                            continue
            children = ast.get_children()
            new_detected = False
            for child in children:
                if child.get_children():
                    get_var_connections(child)
                 
    def append_mongodb_MongoClientURI_connections(self, values, caller, line, column):
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t)
        if values:
            t = [values[1], caller, line, column]
            self.list_of_mongodb_connections.append(t)
        else:
            self.get_member_informations(caller, line, column)  
            
     
                                 
    def append_mongodb_connections(self, values, caller, line, column):
        self.values.append(values)
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t)
    
        if values:
#             log.info('values is %s' % values[1][0])
            
            t = [values[1][0], caller, line, column]
            self.list_of_mongodb_connections.append(t)
            for val in self.list_of_mongodb_connections:
                if val[0][0].find('mongodb://') > -1 and val[0][0].find('@localhost') > -1:
                    list_conn_string1 = val[0][0].split('//')
                    list_conn_string2 = list_conn_string1[1].split('@')
                    list_conn_string3 = list_conn_string2[0].split(':')
                    if list_conn_string3[0] and list_conn_string3[1]:
                        self.valid_connections.append([[val[0][0]],val[1], val[2], val[3]])
            self.list_connection_with_violation = [item for item in self.list_of_mongodb_connections if item not in self.valid_connections]       
            for value in self.list_connection_with_violation:
                prop_qr_auth = '''CAST_Java_MongoDB_Metric_ensureAuthenticationPriorAccess.authenticationCheck'''
                value.append(prop_qr_auth)
           
    def append_mongodb_spring_connection(self, values, caller, line, column):
      
        if values:
            if 1 in values:
                t = [values[1], caller, line, column]
                self.list_of_beans.append(t)
       
    def append_mongodb_databases(self, values, caller, line, column):   
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t)
        if values:
            t = [values[1], caller, line, column]
            self.list_of_mongodb_databases.append(t)
        else:
            ast = self.get_ast_caller(caller)     

            new_member = caller
            if str( caller).find('.<anonymous>.') > -1:
                anonymous_cut_to = str(caller).find('.<anonymous>.')
                existing_member_name = str(caller)[0:anonymous_cut_to].replace('Method(','')
    #             log.info('<anonymous> detected, we should get the parent name = %s' % existing_member_name)
                for check_for_member in self.member_list:
                    if check_for_member[0] == existing_member_name:
                        new_member = check_for_member[1]
                        break 
                                        
            # MongoClientURI mongoClientURI = new MongoClientURI(mongohqUrl);
            lines = self.read_caller_lines(caller)
            new_position = lines[line - 1].find('new')
            line_len =  len(lines[line - 1])
            database_name = lines[line - 1][new_position:line_len].lstrip()
    
            _database_name = lines[line - 1][0:new_position]
            _database_name = _database_name.lstrip()
            equal_position = _database_name.find('=')
            first_empty_space = _database_name.find(' ')
            alias_database_name = _database_name[first_empty_space:equal_position].lstrip().rstrip()
                    
            if ast:
                statements = ast.get_statements()
                for statement in statements:   
                    if str(statement).find('MongoClient')>=0 and str(statement).find('getDB')>str(statement).find('MongoClient'):
                        for con in self.list_of_mongodb_aliases_connections:
                            if str(statement).find(con[1]) >=0 or str(statement).find(con[0]) > 0:
                                # connection detected, con[0] is the name, con[1] is the alias
                                database_name = str(con[0]+'.getDB')
                                t = [con[0], database_name, caller, line, column]
                                self.list_of_mongodb_database_connection_list.append (t)
                                t = [database_name, alias_database_name]
                                self.list_of_mongodb_aliases_databases.append(t)
#                                 log.info('file and aliases (%s %s %s)' % (t, caller, caller.get_position().get_file().get_path()))

            if not ast:          
                MongoDatabaseURI_position = database_name.find('getDB')
                database_name = database_name[MongoDatabaseURI_position:line_len]
                
                MongoDatabaseURI_openpar = database_name.find('(')
                database_name = database_name[MongoDatabaseURI_openpar + 1:line_len]

                MongoDatabaseURI_closepar = database_name.find(')')
                database_name = database_name[0:MongoDatabaseURI_closepar]

                database_name = database_name.replace('(', '')   
                connection_name = database_name[0:database_name.find('.')]
                                        
                t = [database_name, alias_database_name]
                self.list_of_mongodb_aliases_databases.append(t)
#                 log.info('file and aliases (%s %s %s)' % (t, caller, caller.get_position().get_file().get_path()))
                for conn in self.list_of_mongodb_aliases_connections:
                    # the case of alias
                    if conn[1] == connection_name:
                        t = [conn[0], database_name, new_member, line, column]
                        self.list_of_mongodb_database_connection_list.append (t)

    def append_jongo_mongodb_connections(self, values, caller, line, column):  
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t)
        lines = self.read_caller_lines(caller)
        
        new_position = lines[line].find('new')
        l = 0
        jongo_alias = None
        if new_position == -1:
            new_position = lines[line-1].find('new')
            l += 1
            if new_position == -1:
                new_position = lines[line-2].find('new')
                l += 1
                
        if new_position >= 0:  
            jongo_alias = lines[line - l][0:new_position].lstrip()
            equal_position = jongo_alias.find('=')
            return_position = jongo_alias.find('return')
            if equal_position == -1 and return_position >= 0:
                jongo_alias = None
            elif equal_position >=0:
                jongo_alias = jongo_alias[0:equal_position-1].lstrip()
                
                first_empty_space = jongo_alias.find(' ')
                if first_empty_space >= 0:
                    jongo_alias = jongo_alias[first_empty_space:len(jongo_alias)].lstrip()
        if values:
            t = [line, column, caller.get_position().get_file(), values[1][0], caller, jongo_alias]
        else:         
            t = [line, column, caller.get_position().get_file(), None,  caller, jongo_alias]
        self.list_of_jongo_mongo_connections.append(t)
        
    def append_jongo_mongodb_collections(self, values, caller, line, column):  
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t)
        def detect_collection_name (lines, collection_detect_variable_name):
            for line in lines:
                if line.find(collection_detect_variable_name)>= 0 and line.find('=')>= 0 and line.find('"')>= 0:
                    return (line[line.find('"')+1:line.rfind('"')])

        lines = self.read_caller_lines(caller)
        new_position = lines[line].find('.getCollection')
        l = 0
        collection_detect_jongo_alias = None
        collection_alias = None
        if new_position == -1:
            new_position = lines[line-1].find('.getCollection')
            l += 1
            if new_position == -1:
                new_position = lines[line-2].find('.getCollection')
                l += 1
                
        real_collection_name = None
        if new_position >= 0:  
            collection_detect_jongo_alias = lines[line - l][0:new_position].lstrip()
            collection_detect_variable_name = lines[line - l][new_position+15:lines[line - l].find(');')].lstrip()
            if len(collection_detect_variable_name) >= 1:
                # we should first detect collection name stored in a variable
                real_collection_name = detect_collection_name (lines, collection_detect_variable_name)
                
            equal_position = collection_detect_jongo_alias.find('=')
            return_position = collection_detect_jongo_alias.find('return')
            if return_position >= 0:
                if lines[line - l - 1].find('{') > 0 and lines[line - l - 1].rfind('()') > 0:
                    rfind_function = lines[line - l - 1][0:lines[line - l - 1].rfind('()')+2]
                    collection_alias = rfind_function[rfind_function.rfind(' '):len(rfind_function)].lstrip()
                collection_detect_jongo_alias = collection_detect_jongo_alias[return_position+7:len(collection_detect_jongo_alias)]
            elif equal_position == -1:
                collection_detect_jongo_alias = None
            elif equal_position >=0:
                collection_alias = collection_detect_jongo_alias[0:equal_position-1].lstrip()
                collection_detect_jongo_alias = collection_detect_jongo_alias[equal_position+1:len(collection_detect_jongo_alias)].lstrip()
                
                first_empty_space = collection_alias.find(' ')
                if first_empty_space >= 0:
                    collection_alias = collection_alias[first_empty_space:len(collection_alias)].lstrip()
  
        if collection_alias or collection_detect_jongo_alias: 
            if real_collection_name:
                collection_alias = real_collection_name
            else : 
                collection_alias = collection_alias.replace('\n', '')
            # if you can, resolve them 
            if values:
                t = [line, column, caller.get_position().get_file(), values[1][0], caller, collection_detect_jongo_alias, collection_alias]
            else:
                t = [line, column, caller.get_position().get_file(), None,  caller, collection_detect_jongo_alias, collection_alias]
            self.list_of_jongo_collections.append(t)

    def append_mongodb_collections(self, values, caller, line, column):
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t)
        if values:
            t = [values[1], caller, line, column]
            self.list_of_mongodb_collections.append(t) 
            
    def append_jongo_mongodb_collections_insert_links(self, values, caller, line, column): 
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t) 
        if values:
            t = [line, column, caller.get_position().get_file(), values[1][0], caller, 'useInsertLink']
        else:
            t = [line, column, caller.get_position().get_file(), None,  caller, 'useInsertLink']
        self.list_of_jongo_called_collections.append(t)

    def append_jongo_mongodb_collections_update_links(self, values, caller, line, column):    
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t)                                          
        if values:
            t = [line, column, caller.get_position().get_file(), values[1][0], caller, 'useUpdateLink']
        else:
            t = [line, column, caller.get_position().get_file(), None,  caller, 'useUpdateLink']
        self.list_of_jongo_called_collections.append(t)
        
    def append_jongo_mongodb_collections_remove_links(self, values, caller, line, column):  
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t)
        if values:
            t = [line, column, caller.get_position().get_file(), values[1][0], caller, 'useDeleteLink']
        else:
            t = [line, column, caller.get_position().get_file(), None,  caller, 'useDeleteLink']
        self.list_of_jongo_called_collections.append(t)
        
    def append_jongo_mongodb_collections_select_links(self, values, caller, line, column): 
        t = [str(caller)[str(caller).find('(')+1:len(str(caller))-1], caller]
        if not t in self.member_list:
            self.member_list.append(t)                              
        if values:
            t = [line, column, caller.get_position().get_file(), values[1][0], caller, 'useSelectLink']
        else:
            t = [line, column, caller.get_position().get_file(), None,  caller, 'useSelectLink']
        self.list_of_jongo_called_collections.append(t)
    
    def start_type(self, _type):
        # only register types in files importing mongodb
        compilation_unit = self.java_parser.parse(_type.get_position().get_file().get_path())
        if not compilation_unit:
            return
        if not any('.mongodb.' in imp.get_name() for imp in compilation_unit.imports):
            return

        self.get_anno(_type)
        self.typename = _type
        
    def start_member(self, member):
        compilation_unit = self.java_parser.parse(member.get_position().get_file().get_path())
        if not compilation_unit:
            return
        if not any('.mongodb.' in imp.get_name() for imp in compilation_unit.imports):
            return
        
        self.method_obj.append(member)
        
        if self.typename == self.classType:
            if (member.get_typename() == 'JV_FIELD'):
                if self.typename not in self.keyspace_map_dict:
                    self.keyspace_map_dict[self.typename] = []
                t = [member, member.get_position().get_begin_line(), member.get_position().get_begin_column(), member.get_position().get_end_line(), member.get_position().get_end_column()]
                self.keyspace_map_dict[self.typename].append(t) 
               
    def get_anno(self, classType):
        self.flag_getting_anno_key = False
        self.flag_getting_anno_doc = False
        self.flag_getting_class = False
        self.not_getting_value_parameter = False
        ast = self.java_parser.get_object_ast(classType)
        key_value = None
        if ast:
            if str(ast.get_type()) in ["Class", "Method", "VariableDeclaration", "Constructor"]:    
                method_name = ast.get_children
                annotations = ast.get_annotations()
                if annotations:
                    for anno in annotations:
                        if anno.get_type_name() == "Document":
                            self.flag_getting_anno_doc = True
                            self.classType = classType
                            val = anno.get_named_parameters()
                            if str(val.keys()) == "dict_keys(['collection'])":
                                key_value = [anno.get_named_parameters()['collection']]
                                t = [key_value, classType, anno.get_begin_line(), anno.get_begin_column()]
                                self.list_of_mongodb_collections.append(t)
                            else:
                                self.not_getting_value_parameter = True
                                
                        elif anno.get_type_name() == "KeySpace":
                            self.flag_getting_anno_key = True
                            self.classType = classType
                            val = anno.get_named_parameters()
                            if val:
                                key_value = [anno.get_named_parameters()['value']]
                                t = [key_value, classType, anno.get_begin_line(), anno.get_begin_column()]
                                self.list_of_mongodb_collections.append(t)
        if ast:
            token_list = []
            children = ast.get_children()
            for child in children:
                if not child.get_children() and child.text:
                    if child.text.split():
                            token_list.append(child)
            child_list = token_list   
            for token in token_list:   
                if token.text == "class":
                    if self.flag_getting_anno_key or self.flag_getting_anno_doc:
                        self.flag_getting_class = True
                        index_class = token_list.index(token)
                        class_value = token_list[index_class + 1]
                        if key_value:
                            self.class_anno_dict[key_value[0]] = [class_value.text, classType]
                        
                elif self.flag_getting_class:
                    self.class_list.append(child.text)
                
                if self.not_getting_value_parameter and self.flag_getting_class:
                    if not token.text == "class":
                        t = [[token.text], classType, token.get_begin_line(), token.get_begin_column()]
                        self.list_of_mongodb_collections.append(t)
                        self.class_anno_dict[token.text] = [token.text, classType]
                        self.flag_getting_class = False
                            
    def start_analysis(self, options):
     
        """
        Called at the beginning of analysis

        :param cast.analysers.JEEExecutionUnit options: analysis option

        @type options: cast.analysers.JEEExecutionUnit
        """

        # mongodb
        options.add_parameterization("org.springframework.beans.factory.BeanFactory.getBean(java.lang.String)", [1], self.append_mongodb_spring_connection)
        options.add_parameterization("com.mongodb.MongoClient.MongoClient", [1], self.append_mongodb_connections)     
        options.add_parameterization("com.mongodb.MongoClient.MongoClient(java.lang.String,int)", [1], self.append_mongodb_connections)    
        options.add_parameterization("com.mongodb.MongoClient.MongoClient(java.lang.String)", [1], self.append_mongodb_connections)  
        options.add_parameterization("com.mongodb.MongoClient.MongoClient(java.lang.String,com.mongodb.MongoClientOptions)", [1], self.append_mongodb_connections) 
        options.add_parameterization("com.mongodb.MongoClient.MongoClient(com.mongodb.ServerAddress)", [1], self.append_mongodb_connections)

        options.add_parameterization("com.mongodb.Mongo.getDB(java.lang.String)", [1], self.append_mongodb_databases)           
        options.add_parameterization("com.mongodb.DB.getCollection(java.lang.String)",  [1], self.append_mongodb_collections)
        
        options.add_parameterization("com.mongodb.client.MongoDatabase.getCollection(java.lang.String)", [1], self.append_mongodb_collections )
	
        options.add_parameterization("com.mongodb.MongoClientURI.MongoClientURI(java.lang.String)", [1], self.append_mongodb_MongoClientURI_connections)        
        options.add_parameterization("com.mongodb.MongoClientURI.MongoClientURI(java.lang.String,com.mongodb.MongoClientOptions.Builder)", [1], self.append_mongodb_MongoClientURI_connections)        

#         # Jongo connection to the database
        options.add_parameterization("org.jongo.Jongo.Jongo(com.mongodb.DB)",  [1], self.append_jongo_mongodb_connections)
        options.add_parameterization("org.jongo.Jongo.Jongo(com.mongodb.DB,org.jongo.Mapper)",  [1], self.append_jongo_mongodb_connections)
        
        # Jongo collections
        options.add_parameterization("org.jongo.Jongo.getCollection(java.lang.String)",  [1], self.append_jongo_mongodb_collections)
 
        # Jongo collection links
        options.add_parameterization("org.jongo.MongoCollection.findOne(java.lang.String,java.lang.Object[])",  [1], self.append_jongo_mongodb_collections_select_links)
        options.add_parameterization("org.jongo.MongoCollection.findOne(java.lang.String)",  [1], self.append_jongo_mongodb_collections_select_links)
        options.add_parameterization("org.jongo.MongoCollection.count(java.lang.String,java.lang.Object[])",  [1], self.append_jongo_mongodb_collections_select_links)   
        options.add_parameterization("org.jongo.MongoCollection.distinct(java.lang.String)",  [1], self.append_jongo_mongodb_collections_select_links)
        options.add_parameterization("org.jongo.MongoCollection.ensureIndex(java.lang.String)",  [1], self.append_jongo_mongodb_collections_select_links)
        options.add_parameterization("org.jongo.MongoCollection.find",  [1], self.append_jongo_mongodb_collections_select_links)
        options.add_parameterization("org.jongo.MongoCollection.find(java.lang.String,java.lang.Object[])",  [1], self.append_jongo_mongodb_collections_select_links)
        
        options.add_parameterization("org.jongo.MongoCollection.insert(java.lang.Object[])",  [1], self.append_jongo_mongodb_collections_insert_links)
        
        options.add_parameterization("org.jongo.MongoCollection.update(java.lang.String)",  [1], self.append_jongo_mongodb_collections_update_links)
        options.add_parameterization("org.jongo.MongoCollection.update(java.lang.String,java.lang.Object[])",  [1], self.append_jongo_mongodb_collections_update_links)

        options.add_parameterization("org.jongo.MongoCollection.remove",  [1], self.append_jongo_mongodb_collections_remove_links)
        options.add_parameterization("org.jongo.MongoCollection.remove(java.lang.String,java.lang.Object[])",  [1], self.append_jongo_mongodb_collections_remove_links)
                                                                                                            
        options.add_classpath('mongo')

    def end_analysis(self):
        def get_ast(childrens, meth_obj):
            for child in childrens.children:
                try:
                    if child.get_children():
                        get_ast(child, meth_obj)
                    else:
                        if child.text:
                            if child.text.split():
                                token_list.append(child)
                except AttributeError:
                    pass
            child_list = token_list
            for token in token_list:
                for dict_val in  self.class_anno_dict.values():
                    if token.text == dict_val[0]:
                        if meth_obj not in self.dict_method_class_obj_mapping:
                            self.dict_method_class_obj_mapping[meth_obj] = [dict_val[1], token.get_begin_line(), token.get_begin_column(), token.get_end_line(), token.get_end_line()]
                index_mongooperations_next = None
                if token.text == "MongoOperations":
                    index_mongooperations = token_list.index(token)
                    if token_list[-1] != token:
                        index_mongooperations_next = token_list[index_mongooperations +1]
                    for val in self.list_of_beans:
                        if val[2] == token.get_begin_line():
                            if val not in self.list_of_mongodb_connections:
                                self.list_of_mongodb_connections.append(val)
                                self.connection = val   
                    if index_mongooperations_next != ")":
                        self.connection_object = index_mongooperations_next.text
                        
                    del child_list[index_mongooperations]
                    
                if token.text == "new":
                    index_new_next = None
                    index_new = token_list.index(token)
                    del child_list[index_new]
                    try:
                        index_new_next = token_list[index_new ]
                    except:
                        pass
                    index_new_previous = token_list[index_new -3]
                    
                    for val in self.class_list:
                        if index_new_next:
                            if val == index_new_next and val == index_new_previous:
                                t = [obj, index_new_previous.text, index_new_previous.get_begin_line(), index_new_previous.get_begin_column(), index_new_previous.get_end_line(), index_new_previous.get_end_column()]
                                if t not in self.constructor_bookmark:
                                    self.constructor_bookmark.append(t)
                                constructor_token = token_list[index_new -2]
                                self.constructor_object = constructor_token.text
                if self.connection_object:
                    if token.text == self.connection_object + ".save":
                        index_mongooperation_save = token_list.index(token)
                        index_mongooperation_save_next = token_list[index_mongooperation_save + 2]
                       
                        if index_mongooperation_save_next.text != "(":
                            
                            if index_mongooperation_save_next.text != self.constructor_object:
                                t = [obj, token.text, token.get_begin_line(), token.get_begin_column(), token.get_end_line(), token.get_end_column()]
                                if t not in self.mongoOperation_bookmark:
                                    self.mongoOperation_bookmark.append(t)
                                prop_qr = '''CAST_Java_MongoDB_Metric_ensureAuthenticationPriorAccess.authenticationCheck'''
                                if self.connection:
                                    if prop_qr not in self.connection:
                                        self.connection.append(prop_qr)
                                        
                                    if self.connection not in self.list_of_spring_connection_violation:
                                        self.list_of_spring_connection_violation.append(self.connection)
                                        
                        del child_list[index_mongooperation_save]
            
        for obj in self.method_obj:
            token_list = []
            self.connection_object = None
            self.constructor_object = None
            self.connection = None
            ast = self.java_parser.get_object_ast(obj)
            if ast:     
                childrens = ast.children
                for child in childrens:
                    
                    if child.get_children():
                        
                        get_ast(child, obj)
                        
                    else:
                        if self.flag_getting_anno_doc:
                            
                            if child.text:
                                if child.text.split():
                                    token_list.append(child)
                            child_list = token_list
#                             for token in token_list:
        # clear the cache
        self.read_caller_lines.cache_clear()
        self.get_ast_caller.cache_clear()
                
        if len(self.list_of_mongodb_connections) > 0 or len(self.list_of_mongodb_databases) > 0 \
            or len(self.list_of_mongodb_collections) > 0 or len(self.list_of_jongo_collections) > 0:
            self.add_mongodb_connection()
            self.add_mongodb_databases()
            if len (self.list_of_mongodb_collections) > 0 or len(self.list_of_jongo_collections) > 0:
                parsed_callers = []
                for collection_list in self.list_of_mongodb_collections:
                    if collection_list[1] not in parsed_callers:
                        parsed_callers.append(collection_list[1])
                        self.get_mongodb_type_path(collection_list[1])
                        self.get_mongodb_type_path.cache_clear()
                for collection_list in self.list_of_jongo_collections:
                    if collection_list[4] not in parsed_callers:
                        parsed_callers.append(collection_list[4])
                        self.get_mongodb_type_path(collection_list[4])
                        self.get_mongodb_type_path.cache_clear()
                self.add_mongodb_collections()
                
        for dict_key,dict_value in self.keyspace_map_dict.items():
            for obj in self.list_of_collection_object:
                if obj[1] == dict_key:
                    for each_value in dict_value:
                        create_link('useLink', each_value[0], obj[0], Bookmark(dict_key.get_position().get_file(), each_value[1], each_value[2], each_value[3], each_value[4]))
        
        for dict_key, dict_value in self.dict_method_class_obj_mapping.items():
            for obj in self.list_of_collection_object:
                if obj[1] == dict_value[0]:
                        create_link('useLink', dict_key, obj[0], Bookmark(dict_key.get_position().get_file(), dict_value[1], dict_value[2], dict_value[3], dict_value[4] ))

    @lru_cache(maxsize=1)
    def get_mongodb_type_path(self, _type):
        updated_collections = ([])
        inserted_collections = ([])
        deleted_collections = ([])
        selected_collections = ([])
        all_collections = []

        def find_real_collection (collection_name, childrens):
            collection_detected = False
            real_collection = ''
            for child in childrens.get_children():
                if child.get_children():
                    if collection_detected:
                        parenthesis_detected = False
                        for child_new in child.get_children():
                            if child_new == '(':
                                parenthesis_detected = True
                            elif parenthesis_detected:
                                return child_new.text
                    elif not collection_detected:
                        real_collection = find_real_collection (collection_name, child)
                        if real_collection :
                            return real_collection
                else:
                    if child.text.find(collection_name) > -1 and child.text.find(collection_name + '.') == -1:
                        collection_detected = True
                        
            return real_collection
        
        def check_paren(children):
            if children.get_type()=="Parenthesis" :
                return True
            return False
 
        def check_again_dml (childrens):
            list_index = []
            flag_getting_coll = False
            flag_new = False
            flag_mongoclient = False
            collection_obj = None
            new_line = None
            
            index = ''
            for child in childrens.get_children():
#                 log.info(' child is ** : %s' % child)
                if child.get_children():
                    if check_paren(child) and self.flag_index:
                        for sub_child in child.get_children():
                            if not sub_child.get_children():
                                if sub_child.text.find('BasicDBObject') > -1:
                                    continue
                            if check_paren(sub_child) and sub_child.get_children():
                                index = ''
                                next_cont = False
                                for grand_child in sub_child.get_children():
                                    if grand_child.text.find("-") > -1:
                                        next_cont = True
                                       
                                    elif grand_child.text.find("1") > -1 and next_cont:
                                        index = '-1'
                                        next_cont = False
                                        list_index.append(index)
                                        self.flag_index = False
                                        
                                    elif grand_child.text.find("1") > -1 and next_cont == False:
                                        index = '1' 
                                        list_index.append(index)
                                        self.flag_index = False
                        dummy = []
                        for i,j in itertools.combinations(list_index,2):
                            
                            if i == j:
                                dummy.append(False)
                            else :
                                dummy.append(True)
                        
                        if any(dummy):
                            self.collection_with_index[collection_obj] = True
                        else:
                            self.collection_with_index[collection_obj] = False 
                    
                    
                    
                    check_again_dml (child)
                    
                else:
                    collection_name = ''
                    if child.text.find('.update') > -1 or child.text.find('.updateMulti') > -1 or child.text.find('.findAndModify') > -1 or child.text.find('.save') > -1:
                        collection_name = child.text.replace('.updateMulti', '').replace('.update', '').replace('.findAndModify', '').replace('.save', '')
#                         log.info('.update detected 2 for the collection : %s %s %s %s %s ' % (child.get_begin_line(), child.get_begin_column(), child.get_end_line(), child.get_end_column(), collection_name))
                        t = [collection_name, child.get_begin_line(), child.get_begin_column() + 1 , child.get_end_line(), child.get_end_column() + 1]
                        updated_collections.append(t)
#                         log.info('updated_collections %s' % len(updated_collections))
                    elif child.text.find('.insert') > -1:
                        collection_name = child.text.replace('.insert', '')
#                         log.info('.insert detected 2 for the collection : %s %s %s %s %s' % (child.get_begin_line(), child.get_begin_column(), child.get_end_line(), child.get_end_column(), collection_name))
                        t = [collection_name, child.get_begin_line(), child.get_begin_column() + 1, child.get_end_line(), child.get_end_column() + 1]
                        inserted_collections.append(t)
#                         log.info('inserted_collections %s' % len(inserted_collections))
                    elif child.text.find('.findAndRemove') > -1 or child.text.find('.drop') > -1 or child.text.find('.remove') > -1:
                        collection_name = child.text.replace('.findAndRemove', '').replace('.drop', '').replace('.remove', '')
#                         log.info('.delete detected for the collection : %s %s %s %s %s' % (child.get_begin_line(), child.get_begin_column(), child.get_end_line(), child.get_end_column(), collection_name))
                        t = [collection_name, child.get_begin_line(), child.get_begin_column() + 1, child.get_end_line(), child.get_end_column() + 1]
                        deleted_collections.append(t)
#                         log.info('inserted_collections %s' % len(inserted_collections))
                    elif child.text.find('.getCount') > -1 or child.text.find('.find') > -1 or child.text.find('.distinct') > -1 \
                        or child.text.find('.findOne') > -1:
                        collection_name = child.text.replace('.findOne', '').replace('.find', '').replace('.getCount', '').replace('.distinct', '')
#                         log.info('.insert detected 2 for the collection : %s %s %s %s %s' % (child.get_begin_line(), child.get_begin_column(), child.get_end_line(), child.get_end_column(), collection_name))
                        t = [collection_name, child.get_begin_line(), child.get_begin_column() + 1, child.get_end_line(), child.get_end_column() + 1]
                        selected_collections.append(t)
#                         log.info('inserted_collections %s' % len(inserted_collections))
                     
                    elif child.text.find('.explain') > -1:
                        t = [child.text, child.get_begin_line(), child.get_begin_column(), child.get_end_line(), child.get_end_column(), 'CAST_Java_MongoDB_Metric_AvoidExplainInExecutionCode.explainCheck']
                        self.list_with_explain.append(t)
                            
                    elif child.text.find("DBCollection") > -1:
                        flag_getting_coll = True
                        continue
                    
                    elif child.text and flag_getting_coll:
                        variable = child.text
                        self.collection_dictionary[variable] = []
                        flag_getting_coll = False
                        for value in self.list_of_mongodb_collections:
                            if child.get_begin_line() == value[2]:
                                self.collection_dictionary[child.text] = [value[0][0]]
                                
                    elif child.text.find('.createIndex') > -1 or child.text.find('.ensureIndex') > -1:
                        collection_obj = child.text.split('.')[0]
                        self.collection_with_index[collection_obj] = None
                        self.flag_index = True
                        continue
                    
                    elif child.text.find('new') > -1:
                        flag_new = True
                        new_line = child.get_begin_line()
            
                    elif child.text.find('MongoClient') > -1 or child.text.find('MongoClientURI') > -1:
                        if flag_new == False:
                            flag_mongoclient = True
                        else:
                            if new_line == child.get_begin_line():
                                flag_new= False
                                continue        
                    
                  
                    if collection_name and collection_name not in all_collections:
                        all_collections.append(collection_name)
                        
        ast = self.get_ast_caller(_type)                                            
        try:
            childrens = ast.get_children()
            list_of_childrens = []
            collection_name = ''
            
            for child in childrens:
#                 log.info(' child is ** : %s' % child)
                if child.get_children(): 
                    check_again_dml (child)
                     
            for key_index, value_index in self.collection_with_index.items():
                prop_qr ='''CAST_Java_MongoDB_Metric_ensureSimilarCompoundIndexForCollection.similarCompoundIndex'''
                for key_col, value_col in self.collection_dictionary.items():
                    if key_index == key_col and value_index:
                        value_col.append(prop_qr)
                        self.list_of_violation_mongodb_compound_indexing.append(value_col)
                        
            if len(all_collections) and (len(inserted_collections) or len(updated_collections) or len(deleted_collections) \
                                         or len(selected_collections)) and child not in list_of_childrens:
                list_of_childrens.append(child)            

            for collection_name in all_collections:
                for child in list_of_childrens:
                    real_collection = find_real_collection(collection_name, child)
                    if real_collection:
                        if len(updated_collections) > 0:
                            for updated_colection in updated_collections:
                                if collection_name == updated_colection[0]:
                                    t = [real_collection[1:len(real_collection)-1], updated_colection[1], updated_colection[2], updated_colection[3], updated_colection[4]]                       
                                    self.list_of_mongodb_collections_update.append(t)
                        if len(inserted_collections) > 0:
                            for inserted_colection in inserted_collections:
                                if collection_name == inserted_colection[0]:  
                                    t = [real_collection[1:len(real_collection)-1], inserted_colection[1], inserted_colection[2], inserted_colection[3], inserted_colection[4]]                       
                                    self.list_of_mongodb_collections_insert.append(t) 
                        if len(deleted_collections) > 0:
                            for deleted_colection in deleted_collections:
                                if collection_name == deleted_colection[0]:  
                                    t = [real_collection[0:len(real_collection)], deleted_colection[1], deleted_colection[2], deleted_colection[3], deleted_colection[4]]                       
                                    self.list_of_mongodb_collections_delete.append(t)    
                        if len(selected_collections) > 0:
                            for selected_colection in selected_collections:
                                if collection_name == selected_colection[0]:
                                    t = [real_collection[1:len(real_collection)-1], selected_colection[1], selected_colection[2], selected_colection[3], selected_colection[4]]                       
                                    self.list_of_mongodb_collections_select.append(t)     
                    else:
                        if len(updated_collections) > 0:
                            for updated_colection in updated_collections:
                                if collection_name == updated_colection[0]:
                                    t = [collection_name, updated_colection[1], updated_colection[2], updated_colection[3], updated_colection[4]]                       
                                    self.list_of_mongodb_collections_update.append(t)
                        if len(inserted_collections) > 0:
                            for inserted_colection in inserted_collections:
                                if collection_name == inserted_colection[0]:   
                                    t = [collection_name, inserted_colection[1], inserted_colection[2], inserted_colection[3], inserted_colection[4]]                       
                                    self.list_of_mongodb_collections_insert.append(t) 
                        if len(deleted_collections) > 0:
                            for deleted_colection in deleted_collections:
                                if collection_name == deleted_colection[0]: 
                                    t = [collection_name, deleted_colection[1], deleted_colection[2], deleted_colection[3], deleted_colection[4]]                       
                                    self.list_of_mongodb_collections_delete.append(t)    
                        if len(selected_collections) > 0:
                            for selected_colection in selected_collections:
                                if collection_name == selected_colection[0]:  
                                    t = [collection_name, selected_colection[1], selected_colection[2], selected_colection[3], selected_colection[4]]                       
                                    self.list_of_mongodb_collections_select.append(t)                     
        except:
            pass
                                                                                                       
    def add_mongodb_connection(self):
        list_of_connections = []
        for connection in self.list_of_mongodb_connections:
#             log.info('connection is %s' % connection )
            connection_name = str(connection[0])
            if connection_name not in list_of_connections:
                list_of_connections.append(connection_name)
                result = CustomObject()
                result.set_name(connection_name)
                result.set_type('CAST_Java_MongoDB_Connection')
                result.set_parent(connection[1].get_project())
                result.save()
                result.save_position(Bookmark(connection[1].get_position().get_file(), connection[2], connection[3],  connection[2]+1, 0))
                self.connection_parent = result
                # normally you should have a single connection by analysis
                if str(connection[1]).find('test.') == -1:
                    self.mongo_connection = result
                t = [connection_name, result]
                self.mongodb_connection_objects.append(t)
            else:
                
                result.set_name(connection_name)
                result.set_type('CAST_Java_MongoDB_Connection')
                
            create_link('useLink', connection[1], result, Bookmark(connection[1].get_position().get_file(), connection[2], connection[3],  connection[2]+1, 0))
            if isinstance(connection[0], list):
                
                for violation in self.list_connection_with_violation:
                    if connection[0][0] == violation[0][0]:
                        CustomObject.save_violation(result, violation[4], Bookmark(connection[1].get_position().get_file(), violation[2], violation[3],  violation[2], -1))
                        temp_list = list(self.list_connection_with_violation)
                        temp_list.remove(violation)
                        self.list_conn_violation = tuple(temp_list)
                        
             
                for violation in self.list_of_spring_connection_violation:
                    if connection[0][0] == violation[0][0]:
                        for val in self.constructor_bookmark:
                            for value in self.mongoOperation_bookmark:
                                
                                CustomObject.save_violation(result, violation[4], Bookmark(connection[1].get_position().get_file(), violation[2], violation[3], violation[2], -1), [Bookmark(connection[1].get_position().get_file(), val[2], val[3], val[2], -1), Bookmark(connection[1].get_position().get_file(), value[2], value[3], value[2], -1)])
                        temp_list = list(self.list_of_spring_connection_violation)
                        temp_list.remove(violation)
                        self.list_of_spring_connection_violation = tuple(temp_list)
            else:
                
                for violation in self.list_connection_with_violation:
                    if connection[0] == violation[0]:
                       
                        CustomObject.save_violation(result, violation[4], Bookmark(connection[1].get_position().get_file(), violation[2], violation[3],  violation[2], -1))
                        temp_list = list(self.list_connection_with_violation)
                        temp_list.remove(violation)
                        self.list_conn_violation = tuple(temp_list)
                        
    def add_mongodb_databases(self):
        def unknown_databases (detected_name):
            unknown = False
            if str(detected_name).lower() == 'database' or str(detected_name).find('.get') > 0:
#                 log.info('detected_name %s ' %detected_name )
                database_name = 'Unknown'
                database_type = 'CAST_Java_Unknown_MongoDB_Database'
                unknown = True
            else:
                database_name = str(detected_name)
                database_type = 'CAST_Java_MongoDB_Database'
            return (database_name, database_type, unknown)
        
        list_of_databases = []
        list_of_unknown_connections = []
        parent = None
        for database in self.list_of_mongodb_databases:
#             log.info('database is %s' % database)		 
            unknown = False
            database_name, database_type, unknown = unknown_databases (database[0][0])	
            if not database_name in list_of_databases:
                result = CustomObject()
                result.set_name(database_name)
                result.set_type(database_type)
                
                try:
                    result.set_parent(self.connection_parent)
                    result.set_guid(database[1].get_position().get_file().get_path() + 'CAST_Java_MongoDB_Database')
                    if unknown:
                        parent = self.connection_parent
                except:
                    parent = self.mongo_connection
                    result.set_parent(self.mongo_connection)
                    result.set_guid(database[1].get_position().get_file().get_path() + 'CAST_Java_MongoDB_Database')
                                      
                result.save()
                
                if unknown:
                    t = [parent, result]
                    self.list_of_unknown_databases.append(t)

                result.save_position(Bookmark(database[1].get_position().get_file(), database[2], database[3],  database[2]+1, 0))
            else:
                result.set_name(database_name)
                result.set_type(database_type)
                
                if unknown:
                    result.save_position(Bookmark(database[1].get_position().get_file(), database[2], database[3],  database[2]+1, 0))
                    
            create_link('useLink', database[1], result, Bookmark(database[1].get_position().get_file(), database[2], database[3],  database[2]+1, 0))
            
            
            self.mongo_database = result
        else:
            for database in self.list_of_mongodb_database_connection_list:
#                 log.info('else database is %s' % database)
                unknown = False
                database_name, database_type, unknown = unknown_databases (database[1])
                
                if (not unknown and not database_name in list_of_databases) or (unknown and not database[0] in list_of_unknown_connections):
                    if not database_name in list_of_databases:
                        list_of_databases.append(database_name)
    
                    if unknown:
                        list_of_unknown_connections.append(database[0])
                                      
                    result = CustomObject()
                    result.set_name(database_name)
                    result.set_type(database_type)
                    if self.connection_parent.name == database[0]:
                        for conn in self.mongodb_connection_objects:
                            if database[0] == conn[0]:
                                result.set_parent(conn[1])
                                self.conn_parent = conn[1]
                        result.set_guid(database[2].get_position().get_file().get_path() + 'CAST_Java_Unknown_MongoDB_Database')
                        
                        result.save()
                        if unknown:
                            t = [self.conn_parent, result]
                            self.list_of_unknown_databases.append(t)
                            
                        create_link('useLink', database[2], result, Bookmark(database[2].get_position().get_file(), database[3], database[4],  database[3]+1, 0))

                        for list_of_jongo in self.list_of_jongo_mongo_connections:
                            if list_of_jongo[2] == database[2].get_position().get_file() and list_of_jongo[0] in range (database[3] - 10, database[3] + 10):
                                for list_of_aliases in self.list_of_mongodb_aliases_databases:
                                    if database[1] == list_of_aliases [0]:
                                        t = [result, list_of_aliases [1], list_of_aliases [0], list_of_jongo[0], list_of_jongo[1], list_of_jongo[5], database[2].get_position().get_file()]
                                        self.append_jongo_mongodb_match.append(t)                    
                    else:  
                        for connection_object in self.mongodb_connection_objects:
                            if connection_object[0] == database[0]:
                                result.set_parent(connection_object[1])
                                result.set_guid(database[2].get_position().get_file().get_path() + 'CAST_Java_Unknown_MongoDB_Database')
                        
                                result.save()
                                if unknown:
                                    t = [connection_object[1], result]
                                    self.list_of_unknown_databases.append(t)
                                create_link('useLink', database[2], result, Bookmark(database[2].get_position().get_file(), database[3], database[4],  database[3]+1, 0))
                                
                                for list_of_jongo in self.list_of_jongo_mongo_connections:
                                    if list_of_jongo[2] == database[2].get_position().get_file() and list_of_jongo[0] in range (database[3] - 10, database[3] + 10):
                                        for list_of_aliases in self.list_of_mongodb_aliases_databases:
                                            if database[1] == list_of_aliases [0]:
                                                t = [result, list_of_aliases [1], list_of_aliases [0], list_of_jongo[0], list_of_jongo[1], list_of_jongo[5], database[2].get_position().get_file()]
                                                self.append_jongo_mongodb_match.append(t) 
                                break
                    result.save_position(Bookmark(database[2].get_position().get_file(), database[3], database[4],  database[3]+1, 0))
                    
                else:
                    result.set_name(database_name)
                    result.set_type(database_type)
                    
                    if unknown:
                        result.save_position(Bookmark(database[2].get_position().get_file(), database[3], database[4],  database[3]+1, 0))
        
                    create_link('useLink', database[2], result, Bookmark(database[2].get_position().get_file(), database[3], database[4],  database[3]+1, 0))
                    
                    self.database = result
                    
    def add_mongodb_collections(self):
        def unknown_collections (detected_name):
            if str(detected_name).lower() == 'collection':
                collection_name = 'Unknown'
                collection_type = 'CAST_Java_Unknown_MongoDB_Collection'
            else:
                collection_name = str(detected_name)
                collection_type = 'CAST_Java_MongoDB_Collection'
            return (collection_name, collection_type)
        
        def add_link(collection_list, link_type, real_collection_name, caller, callee, file):
            for test_name in collection_list:
                if test_name[0].strip('"') == real_collection_name or (test_name[0].find('collection') > -1 and real_collection_name == 'Unknown'):
                    try:
                        create_link(link_type, caller, callee, Bookmark(file, test_name[1], test_name[2], test_name[3], test_name[4]))
                    except:
                        pass  

        list_of_collections = []
        for collection in self.list_of_mongodb_collections: 
#             log.info('collection full mongo %s' % collection)
            # the case when the object name is finally the type of the object will consider it as Unknown
            collection_name, collection_type = unknown_collections(collection[0][0])               
            if not collection_name in list_of_collections:
                result = CustomObject()
                result.set_name(collection_name)
                result.set_type(collection_type)
                try:
                    if self.mongo_database:
                        result.set_parent(self.mongo_database)
                    else:
                        result.set_parent(collection[1].get_position().get_file())
                except:
                    result.set_parent(self.database)
                
                result.save()
                
                result.save_position(Bookmark(collection[1].get_position().get_file(), collection[2], collection[3],  collection[2]+1, 0))
              
                self.list_of_collection_object.append((result,collection[1]))
            else:
                result.set_name(collection_name)
                result.set_type(collection_type)
            
            create_link('useLink', collection[1], result, Bookmark(collection[1].get_position().get_file(), collection[2], collection[3],  collection[2]+1, 0))
            
            # add dml links
            real_collection_name = collection_name
            add_link (self.list_of_mongodb_collections_insert, 'useInsertLink', real_collection_name, collection[1], result, collection[1].get_position().get_file())
            add_link (self.list_of_mongodb_collections_update, 'useUpdateLink', real_collection_name, collection[1], result, collection[1].get_position().get_file())
            add_link (self.list_of_mongodb_collections_delete, 'useDeleteLink', real_collection_name, collection[1], result, collection[1].get_position().get_file())
            add_link (self.list_of_mongodb_collections_select, 'useSelectLink', real_collection_name, collection[1], result, collection[1].get_position().get_file())
            
            for violation_col in self.list_of_violation_mongodb_compound_indexing:
                
                if violation_col[0] == collection[0][0]:
                   
                    CustomObject.save_violation(result, violation_col[1], Bookmark(collection[1].get_position().get_file(), collection[2], collection[3], collection[2], -1))
                    
                    temp_list = list(self.list_of_violation_mongodb_compound_indexing)
                    temp_list.remove(violation_col)
                    self.list_of_violation_mongodb_compound_indexing = tuple(temp_list)

            for violation_explain in self.list_with_explain:
                if violation_explain[1] == collection[2]:
                    CustomObject.save_violation(result, violation_explain[5], Bookmark(collection[1].get_position().get_file(), collection[2], collection[3], violation_explain[3], violation_explain[4] ) )
                    temp_list = list(self.list_with_explain)
                    temp_list.remove(violation_explain)
                    self.list_with_explain = tuple(temp_list)            


        # Jongo for MongoDB
        list_of_collections = []         
        #  0 line, 
#          1       column, 
#          2       caller.get_position().get_file(), 
#          3       values[1][0],  # name
#          4       caller, # call link
#          5       collection_detect_jongo_alias, to be linked with append_jongo_mongodb_match
#          6       collection_alias] # to be linked with list_of_jongo_ADDED/removed/selected_collections
        for collection in self.list_of_jongo_collections: 
#        database match result, list_of_aliases [1], list_of_aliases [0], list_of_jongo[0], list_of_jongo[1], list_of_jongo[5], database[2].get_position().get_file()]
            collection_name = collection[3]
            # normally there is only one connection by group of java sources
            collection_parent = self.mongo_connection
            if not collection_name and collection[6]:
                collection_name = collection[6]
            
            collection_name, collection_type = unknown_collections(collection_name) 
            if str(collection_name) not in list_of_collections:
                result = CustomObject()
                result.set_name(collection_name)
                result.set_type(collection_type)
                for jongo_mongo in self.append_jongo_mongodb_match:  
                    if collection[5] == jongo_mongo [5]:
                        # parent is result jongo_mongo [0]
                        collection_parent = jongo_mongo[0]
                        break
                        
                if  collection_parent.typename ==  'CAST_Java_MongoDB_Connection':
                    for parent in self.list_of_unknown_databases:
                        if parent[0] == collection_parent:
                            collection_parent = parent[1]
                            break

                result.set_parent(collection_parent)
                result.save()
                result.save_position(Bookmark(collection[4].get_position().get_file(), collection[0], collection[1],  collection[0]+1, 0))
            else:
                result.set_name(collection_name)
                result.set_type(collection_type)
            
            create_link('useLink', collection[4], result, Bookmark(collection[4].get_position().get_file(), collection[0], collection[1],  collection[0]+1, 0))
            
            collection_rfind = collection[4].get_fullname().rfind('.')
            for called_collection in self.list_of_jongo_called_collections:
                #  0 line, 
        #          1       column, 
        #          2       caller.get_position().get_file(), 
        #          3       values[1][0],  # name
        #          4       caller, # call link
        #          5       link type of link 
                called_collection_rfind = called_collection[4].get_fullname().rfind('.')
                if collection[4].get_fullname()[0:collection_rfind] == called_collection[4].get_fullname()[0:called_collection_rfind]:
                    create_link(called_collection[5], called_collection[4], result, Bookmark(called_collection[4].get_position().get_file(), called_collection[0], called_collection[1],  called_collection[0]+1, 0))

            add_link (self.list_of_mongodb_collections_delete, 'useDeleteLink', collection_name, collection[4], result, collection[4].get_position().get_file())
            add_link (self.list_of_mongodb_collections_select, 'useSelectLink', collection_name, collection[4], result, collection[4].get_position().get_file())
            add_link (self.list_of_mongodb_collections_update, 'useUpdateLink', collection_name, collection[4], result, collection[4].get_position().get_file())
            add_link (self.list_of_mongodb_collections_insert, 'useInsertLink', collection_name, collection[4], result, collection[4].get_position().get_file())            