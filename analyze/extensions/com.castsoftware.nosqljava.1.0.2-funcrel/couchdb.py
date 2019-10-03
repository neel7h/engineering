import cast.analysers.jee
from cast.analysers import log, create_link, Bookmark, CustomObject
# from functools import lru_cache

class JEEAllEvents(cast.analysers.jee.Extension):
    class TypeContext:
        def __init__(self, typ):
            self.currentClass = typ
                
    def __init__(self):
        self.java_parser = None
        self.couchdb_connection = None
        self.couchdb_connection_unknown = None
        self.couchdb_database = None
        self.couchdb_database_unknown = None
        
        self.list_of_couchdb_connections = ([])
        self.list_of_couchdb_collections = ([])
        self.list_of_couchdb_databases = ([])
        self.list_of_couchdb_append_databases  = ([])
        
        self.list_of_couchdb_removed_collections = ([])
        self.list_of_couchdb_updated_collections = ([])
        self.list_of_couchdb_selected_collections = ([])
        self.list_of_couchdb_inserted_collections = ([])
                        
        self.list_of_methods_by_database = []
        self.unknown_list_of_methods_by_database = []
        self.list_of_methods_by_connection = []
        self.unknown_list_of_methods_by_connection = []
                
#     @lru_cache(maxsize=1)
#     def read_caller_lines (self, file):
#         fp = open(file, 'r')
#         lines = fp.readlines()
#         fp.close()
# #         log.info('cache_info for read_caller_lines %s ' % str(self.read_caller_lines.cache_info()))
#         return lines
                                    
    def append_couchdb_connections(self, values, caller, line, column):
#         log.info('connections values %s, caller %s, line %s, column %s' % (values, caller, line, column))
        if values and values[1][0].lower() not in ('null', 'connection'):
#             log.info('values is %s' % values[1][0])
            t = [values[1][0], caller, line, column]
        else:
            t = ['Unknown', caller, line, column]
            
        self.list_of_couchdb_connections.append(t)

    def append_couchdb_databases(self, values, caller, line, column):
#         log.info('databases values %s, caller %s, line %s, column %s' % (values, caller, line, column))
        if values and values[1][0].lower() not in ('null', 'database'):
            t = [values[1][0], caller, line, column]
        else:
            t = ['Unknown', caller, line, column]
        
        self.list_of_couchdb_append_databases.append(t)
            
    def append_couchdb_collection(self, values, caller, line, column):
#         log.info('collections values %s, caller %s, line %s, column %s' % (values, caller, line, column))
        if values and values[1][0].lower() not in ('null', 'collection'):
            t = [values[1][0], caller, line, column]
        else:
            t = ['Unknown', caller, line, column]
            
        self.list_of_couchdb_collections.append(t)

    def append_couchdb_removed_collections(self, values, caller, line, column):
#         log.info('removed collections %s, caller %s, line %s, column %s' % (values, caller, line, column))
        if values:
            t = [values[1][0], caller, line, column]
        else:
            t = ['Unknown', caller, line, column]
        
        self.list_of_couchdb_removed_collections.append(t)           

    def append_couchdb_inserted_collections(self, values, caller, line, column):
#         log.info('inserted collections %s, caller %s, line %s, column %s' % (values, caller, line, column))
        if values:
            t = [values[1][0], caller, line, column]
        else:
            t = ['Unknown', caller, line, column]
        
        self.list_of_couchdb_inserted_collections.append(t) 

    def append_couchdb_selected_collections(self, values, caller, line, column):
#         log.info('selected collections %s, caller %s, line %s, column %s' % (values, caller, line, column))
        if values:
            t = [values[1][0], caller, line, column]
        else:
            t = ['Unknown', caller, line, column]
        
        self.list_of_couchdb_selected_collections.append(t) 
                
    def append_couchdb_updated_collections(self, values, caller, line, column):
#         log.info('updated collections %s, caller %s, line %s, column %s' % (values, caller, line, column))
        if values:
            t = [values[1][0], caller, line, column]
        else:
            t = ['Unknown', caller, line, column]
        
        self.list_of_couchdb_updated_collections.append(t)        
                                                                        
    def start_analysis(self, options):
        """
        Called at the beginning of analysis

        :param cast.analysers.JEEExecutionUnit options: analysis option

        @type options: cast.analysers.JEEExecutionUnit
        """

        # couchdb
        
        # ektorp
        options.add_parameterization("org.ektorp.CouchDbConnector", [1], self.append_couchdb_connections) 
        
        options.add_parameterization("org.ektorp.CouchDbConnector.createDatabaseIfNotExists()", [1], self.append_couchdb_databases)
        options.add_parameterization("org.ektorp.CouchDbConnector.get", [1], self.append_couchdb_databases)
        options.add_parameterization("org.ektorp.CouchDbConnector.get(java.lang.Class<T>,java.lang.String)", [1], self.append_couchdb_databases)
        options.add_parameterization("org.ektorp.CouchDbConnector.get(java.lang.Class<T>,java.lang.String,org.ektorp.Options)", [1], self.append_couchdb_databases)
        options.add_parameterization("org.ektorp.CouchDbInstance.createConnector(java.lang.String,boolean)", [1], self.append_couchdb_databases)

        options.add_parameterization("org.ektorp.CouchDbConnector.create(java.lang.Object)", [1], self.append_couchdb_collection)               
        options.add_parameterization("org.ektorp.CouchDbConnector.create(java.lang.String,java.lang.Object)", [1], self.append_couchdb_collection)
        options.add_parameterization("org.ektorp.util.Documents.getId(java.lang.Object)", [1], self.append_couchdb_collection)
        options.add_parameterization("org.ektorp.util.Documents.setId(java.lang.Object,java.lang.String)", [1], self.append_couchdb_collection)
        options.add_parameterization("org.ektorp.support.CouchDbDocument()", [1], self.append_couchdb_collection)
        

        options.add_parameterization("org.ektorp.CouchDbConnector.find(java.lang.Class<T>,java.lang.String)", [1], self.append_couchdb_selected_collections)
        options.add_parameterization("org.ektorp.CouchDbConnector.find(java.lang.Class<T>,java.lang.String,org.ektorp.Options)", [1], self.append_couchdb_selected_collections)
        options.add_parameterization("org.ektorp.CouchDbConnector.queryView(org.ektorp.ViewQuery)", [1], self.append_couchdb_selected_collections)


        options.add_parameterization("org.ektorp.CouchDbConnector.update(java.lang.Object)", [1], self.append_couchdb_updated_collections)
        options.add_parameterization("org.ektorp.CouchDbConnector.copy(java.lang.String,java.lang.String)", [1], self.append_couchdb_updated_collections)
        options.add_parameterization("org.ektorp.CouchDbConnector.copy(java.lang.String,java.lang.String,java.lang.String)", [1], self.append_couchdb_updated_collections)


        options.add_parameterization("org.ektorp.CouchDbConnector.delete(java.lang.Object)", [1], self.append_couchdb_removed_collections)
        options.add_parameterization("org.ektorp.CouchDbConnector.delete(java.lang.String,java.lang.String)", [1], self.append_couchdb_removed_collections)
        options.add_parameterization("org.ektorp.CouchDbConnector.purge(java.util.Map<java.lang.String,java.util.List<java.lang.String>>)", [1], self.append_couchdb_removed_collections)

        
        # lightcouch
        options.add_parameterization("org.lightcouch.CouchDbClient.CouchDbClient(org.lightcouch.CouchDbProperties)", [1], self.append_couchdb_databases)
        options.add_parameterization("org.lightcouch.CouchDbClient.CouchDbClient(java.lang.String)", [1], self.append_couchdb_databases)

        options.add_parameterization("org.lightcouch.CouchDbClientBase.save(java.lang.Object)", [1], self.append_couchdb_collection)
        options.add_parameterization("org.lightcouch.CouchDbClientBase.batch(java.lang.Object)", [1], self.append_couchdb_collection)
        options.add_parameterization("org.lightcouch.CouchDbClientBase.contains(java.lang.String)", [1], self.append_couchdb_collection)
        options.add_parameterization("org.lightcouch.CouchDbClientBase.bulk(java.util.List<?>, boolean)", [1], self.append_couchdb_collection)
        
        options.add_parameterization("org.lightcouch.CouchDbClientBase.remove(java.lang.Object)", [1], self.append_couchdb_removed_collections)
        options.add_parameterization("org.lightcouch.CouchDbClientBase.remove(java.lang.String,java.lang.String)", [1], self.append_couchdb_removed_collections)
        options.add_parameterization("org.lightcouch.CouchDbClientBase.update(java.lang.Object)", [1], self.append_couchdb_updated_collections)
        options.add_parameterization("org.lightcouch.CouchDbClientBase.bulk(java.util.List<?>, boolean)", [1], self.append_couchdb_updated_collections)
        options.add_parameterization("org.lightcouch.CouchDbClientBase.view(java.lang.String)", [1], self.append_couchdb_selected_collections)
        options.add_parameterization("org.lightcouch.CouchDbClientBase.post(java.lang.Object)", [1], self.append_couchdb_inserted_collections)
                                               
        options.add_parameterization("com.couchbase.lite.Manager.getExistingDatabase(java.lang.String)", [1], self.append_couchdb_databases)
                                                                                                           
        options.add_classpath('couchdb')

    def end_analysis(self):
        # add Unknown collection
        method = None
        if  len(self.list_of_couchdb_connections) == 0:
            if  len(self.list_of_couchdb_append_databases) > 0:
                method = self.list_of_couchdb_append_databases [0][1]
            elif len(self.list_of_couchdb_collections) > 0:
                method = self.list_of_couchdb_collections [0][1]
            if method:
                self.add_unknown_connection(method)
        
        # add Unknown database check names of detect one  (the case when variable is not resolved) 
        if  len(self.list_of_couchdb_append_databases) > 0:
            for database in self.list_of_couchdb_append_databases:
                if len(database[0]) == 1 or database[0].isdigit():
                    log.info('the case when is not really detected')
                    new_name = 'Unknown'
#                     lines = self.read_caller_lines(database[1].get_position().get_file().get_path())
#                     parameter = str(lines[database[2]-1][lines[database[2]-1].find('getExistingDatabase(')+20:lines[database[2]-1].find(database[0])].replace('+', '').replace('"', ''))
#                     new_name = (parameter.strip() + str(database[0]).strip())
                    t = [new_name, database[1], database[2], database[3]]
                else:
                    t = [str(database[0]) , database[1], database[2], database[3]]
                self.list_of_couchdb_databases.append(t)
                
        elif len(self.list_of_couchdb_collections) > 0:
            method = self.list_of_couchdb_collections [0][1]
            self.add_unknown_database(method)
            
        if len(self.list_of_couchdb_connections) > 0 or len(self.list_of_couchdb_databases) or len(self.list_of_couchdb_collections):          
            log.info('Start couchdb analysis')
            self.add_couchdb_connections() 
            self.add_couchdb_databases()          
            self.add_couchdb_collections()           
            log.info('End couchdb analysis')    

    def add_couchdb_connections(self):
        list_of_connections = []
        for connection in self.list_of_couchdb_connections:
            unknown_object = False
            if connection[0] == 'Unknown':
                unknown_object = True
                object_type = 'CAST_Java_Unknown_Couchbase_Connection'
                self.unknown_list_of_methods_by_connection.append(connection[1])
            else:
                object_type = 'CAST_Java_Couchbase_Connection'
                self.list_of_methods_by_connection.append(connection[1])
                
            if str(connection[0]) not in list_of_connections:
                list_of_connections.append(str(connection[0]))
                result = CustomObject()
                result.set_name(str(connection[0]))
                result.set_type(object_type)
                result.set_parent(connection[1].get_project())
                result.save()
    
                if unknown_object:
                    self.couchdb_connection_unknown = result
                else:
                    self.couchdb_connection = result
            else:
                result.set_name(str(connection[0]))
                result.set_type(object_type)
#                 create_link('useLink', connection[1], result, Bookmark(connection[1].get_position().get_file(), int(connection[2]), int(connection[3]), int(connection[2]) + 1, 0))
            result.save_position(Bookmark(connection[1].get_position().get_file(), int(connection[2]), int(connection[3]), int(connection[2]) + 1, 0)) 
            create_link('useLink', connection[1], result, Bookmark(connection[1].get_position().get_file(), int(connection[2]), int(connection[3]), int(connection[2]) + 1, 0))


    def add_unknown_connection(self, method):
        result = CustomObject()
        result.set_name('Unknown')
        result.set_type('CAST_Java_Unknown_Couchbase_Connection')
        result.set_parent(method.get_project())
        result.save()
        self.couchdb_connection = result
        result.save_position(Bookmark(method.get_position().get_file(), 0, 0, 0, 0))                                                                                                                                                  
        return                    

    def add_unknown_database(self, method):
        result = CustomObject()
        result.set_name('Unknown')
        result.set_type('CAST_Java_Unknown_Couchbase_Database')
        result.set_parent(self.couchdb_connection)
        result.save()
        self.couchdb_database = result   
        result.save_position(Bookmark(method.get_position().get_file(), 0, 0, 0, 0))        
        return   
          
    def add_couchdb_databases(self):            
        list_of_databases = []
         
        for database in self.list_of_couchdb_databases:
            unknown_object = False
            if database[0] == 'Unknown':
                unknown_object = True
                object_type = 'CAST_Java_Unknown_Couchbase_Database'
                self.unknown_list_of_methods_by_database.append(database[1])
            else:
                object_type = 'CAST_Java_Couchbase_Database'
                self.list_of_methods_by_database.append(database[1])

            if database[1] in self.list_of_methods_by_connection:
                object_parent = self.couchdb_connection
            elif database[1] in self.unknown_list_of_methods_by_connection:
                object_parent = self.couchdb_connection_unknown
            else:
                object_parent = self.couchdb_connection
                       
            if str(database[0]) not in list_of_databases:
                list_of_databases.append(str(database[0]))
                result = CustomObject()
                result.set_name(str(database[0]))
                result.set_type(object_type)
                result.set_parent(object_parent)
                result.save()
                
                # normally it should be a single one
                if unknown_object:
                    self.couchdb_database_unknown = result  
                else:
                    self.couchdb_database = result
            else:
                result.set_name(str(database[0]))
                result.set_type(object_type)
                       
            result.save_position(Bookmark(database[1].get_position().get_file(), int(database[2]), int(database[3]), int(database[2]) + 1, 0))
            create_link('useLink', database[1], result, Bookmark(database[1].get_position().get_file(), int(database[2]), int(database[3]), int(database[2]) + 1, 0)) 
 
    def add_couchdb_collections(self):            
        list_of_collections = []

        for collection in self.list_of_couchdb_collections:
            if collection[0] == 'Unknown':
                object_type = 'CAST_Java_Unknown_Couchbase_Collection'
            else:
                object_type = 'CAST_Java_Couchbase_Collection'

            if collection[1] in self.list_of_methods_by_database:
                object_parent = self.couchdb_database
            elif collection[1] in self.unknown_list_of_methods_by_database:
                object_parent = self.couchdb_database_unknown
            else:
                object_parent = self.couchdb_database_unknown
                
            if str(collection[0]) not in list_of_collections:
                list_of_collections.append(str(collection[0]))
                result = CustomObject()
                result.set_name(str(collection[0]))
                result.set_type(object_type)
                result.set_parent(object_parent)
                result.save()
            
                for remove_link in self.list_of_couchdb_removed_collections:
                    if str(collection[0]) == str(remove_link[0]):
#                         log.info('use delete link %s %s ' % (str(collection[0]), remove_link[1]))
                        create_link('useDeleteLink', remove_link[1], result, Bookmark(remove_link[1].get_position().get_file(), int(remove_link[2]), int(remove_link[3]), int(remove_link[2]) + 1, 0))

                for update_link in self.list_of_couchdb_updated_collections:
                    if str(collection[0]) == str(update_link[0]):
#                         log.info('use update link %s %s ' % (str(collection[0]), update_link[1]))
                        create_link('useUpdateLink', update_link[1], result, Bookmark(update_link[1].get_position().get_file(), int(update_link[2]), int(update_link[3]), int(update_link[2]) + 1, 0))

                for select_link in self.list_of_couchdb_selected_collections:
                    if str(collection[0]) == str(select_link[0]):
#                         log.info('use select link %s %s ' % (str(collection[0]), select_link[1]))
                        create_link('useSelectLink', select_link[1], result, Bookmark(select_link[1].get_position().get_file(), int(select_link[2]), int(select_link[3]), int(select_link[2]) + 1, 0))

                for insert_link in self.list_of_couchdb_inserted_collections:
#                     log.info('use insert link %s %s ' % (str(collection[0]), insert_link[1]))
                    if str(collection[0]) == str(insert_link[0]):
                        create_link('useInsertLink', insert_link[1], result, Bookmark(insert_link[1].get_position().get_file(), int(insert_link[2]), int(insert_link[3]), int(insert_link[2]) + 1, 0))

            else:
                result.set_name(str(collection[0]))
                result.set_type(object_type)
#                 create_link('useLink', collection[1], result, Bookmark(collection[1].get_position().get_file(), int(collection[2]), int(collection[3]), int(collection[2]) + 1, 0))                       
            
            result.save_position(Bookmark(collection[1].get_position().get_file(), int(collection[2]), int(collection[3]), int(collection[2]) + 1, 0))                                                                                                                                                  
            create_link('useLink', collection[1], result, Bookmark(collection[1].get_position().get_file(), int(collection[2]), int(collection[3]), int(collection[2]) + 1, 0))                       

