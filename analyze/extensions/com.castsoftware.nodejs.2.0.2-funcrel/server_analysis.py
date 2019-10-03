import os
from cast.analysers import CustomObject, Bookmark, log, create_link, external_link
import traceback
import json
from symbols import nodejs_open_source_file, LoopbackApplication
from nodejs_parser import create_link_nodeJS
from sql_parser import extract_tables
from collections import defaultdict

class NodeJSApplication:

    def __init__(self):
        self.node_server = NodeJSServer()


class NodeJSServer:

    def __init__(self):
        pass


class ExpressServer(NodeJSServer):

    def __init__(self):
        pass


class LoopBackServer(NodeJSServer):

    def __init__(self):
        pass


class HapiServer(NodeJSServer):
    def __init__(self):
        pass


class SailsServer(NodeJSServer):

    def __init__(self):
        pass


def plural(name):
#     analysis -> analyses
#     bear -> bears
    if name.lower().endswith('is'):
        return name[:-2] + 'es'
    return name + 's'

class LoopBackAnalysis:

    def __init__(self):
        self.loopbackApplications = {}
        self.loopbackApplicationsByModelRootPath = {}
        self.jsContent = None
        self.nbOperations_loop_back = 0
        self.nbLoopbackModels = 0
        self.server = False

    def search_for_loopback_application(self, middlewareFilename):

        text = nodejs_open_source_file(middlewareFilename)
        if text and 'loopback' in text:
            app = LoopbackApplication(os.path.dirname(middlewareFilename))
            self.loopbackApplications[os.path.dirname(middlewareFilename)] = app
            for modelRootPath in app.modelRootPathes:
                self.loopbackApplicationsByModelRootPath[modelRootPath] = app

    def process(self,dirname, jsonFile):
        if dirname in self.loopbackApplicationsByModelRootPath:  # then file is a loopback model
            loopbackApp = self.loopbackApplicationsByModelRootPath[dirname]
            self.create_loopback_model(loopbackApp, jsonFile)
            loopbackApp.jsonModelFiles.append(jsonFile.get_path())

    def find_table_json(self, json_model, jsonFile, databases):
        
        def resolve_table(options):
            technos = ['postgresql', 'oracle', 'mysql', 'mssql']
            
            for techno in technos:
                if techno not in databases:
                    continue

                if techno not in options:
                    continue

                tbls = []
                table_info = options[techno]

                if 'table' in table_info:    
                    tableName = table_info['table']
                    tbls = external_link.find_objects(tableName, 'Database Table')

                    if not tbls:
                        tbls = external_link.find_objects(tableName, 'Database View')

                    if not tbls:
                        kbObject = CustomObject()
                        kbObject.set_name(tableName)
                        kbObject.set_type('CAST_NodeJS_Unknown_Database_Table')
                        kbObject.set_parent(jsonFile)
                        fullname = jsonFile.get_path() + '/' + tableName + '/' + 'CAST_NodeJS_Unknown_Database_Table'
                        kbObject.set_guid(fullname)
                        kbObject.set_fullname(fullname)
                        kbObject.save()
                        kbObject.save_position(Bookmark(jsonFile, 1, 1, -1, -1))
                        tbls = [kbObject]

                    log.info('Table external found with option at: ' + jsonFile.get_path())
                    return tbls

                return tbls

            if 'mongodb' in databases:
                name = jsonFile.get_path().split('\\')[-1].replace('.json', '')

                kbObject = CustomObject()
                kbObject.set_name(name)
                kbObject.set_type('CAST_NodeJS_MongoDB_Collection')
                kbObject.set_parent(jsonFile)
                fullname = jsonFile.get_path() + '/' + tableName + '/' + 'CAST_NodeJS_MongoDB_Collection'
                kbObject.set_guid(fullname)
                kbObject.set_fullname(fullname)
                kbObject.save()
                kbObject.save_position(Bookmark(jsonFile, 1, 1, -1, -1))

                return [kbObject]
                log.info('Mongodb collection is created for ' + jsonFile.get_path())
            return []

        if 'options' not in json_model:
            return None
        
        try:
            infos = json_model['options']
            return resolve_table(infos)

        except:
            log.warning('Problem when finding table - loopback')
            return None
        
    def create_loopback_model(self, loopbackApp, jsonFile):
        
        self.nbLoopbackModels += 1

        try:

            jsonModel = json.loads(nodejs_open_source_file(jsonFile.get_path()))
            table_object = self.find_table_json(jsonModel, jsonFile, loopbackApp.databases_connector)

            if 'name' in jsonModel:
                name = jsonModel['name']
            else:
                name = os.path.basename(jsonFile.get_path())[:-5]

            if name not in loopbackApp.models:
                log.warning('model ' + str(name) + ' is not valid')
                return

            model = loopbackApp.models[name]
            
            if table_object:
                model['kbObject'] = table_object[0]
                return
            
            kbModel = CustomObject()
            kbModel.set_name(name)
            kbModel.set_type('CAST_NodeJS_Collection')
            kbModel.set_parent(jsonFile)
            fullname = jsonFile.get_path() + '/CAST_NodeJS_Collection'
            kbModel.set_guid(fullname)
            kbModel.set_fullname(fullname)
            kbModel.save()
    #         crc = jsContent.objectDatabaseProperties.checksum
    #         model.save_property('checksum.CodeOnlyChecksum', crc)
            kbModel.save_position(Bookmark(jsonFile, 1, 1, -1, -1))

            model['kbObject'] = kbModel
            log.info('NodejS loopback model found ' + jsonFile.get_path())
            
            self.create_loopback_operations(name, model, jsonFile, loopbackApp)
            
        except:
            log.warning('Internal issue when creating loopback model: ' + str(traceback.format_exc()))

    def create_loopback_operations(self, name, model, jsonFile, loopbackApp):

        self.create_loopback_operation('GET', '', loopbackApp, model, jsonFile, jsonFile, 'useSelectLink', model['kbObject'])
        self.create_loopback_operation('PUT', '', loopbackApp, model, jsonFile, jsonFile, 'useUpdateLink', model['kbObject'])
        self.create_loopback_operation('POST', '', loopbackApp, model, jsonFile, jsonFile, 'useInsertLink', model['kbObject'])

        self.create_loopback_operation('GET', '{id}/', loopbackApp, model, jsonFile, jsonFile, 'useSelectLink', model['kbObject'])
        self.create_loopback_operation('PUT', '{id}/', loopbackApp, model, jsonFile, jsonFile, 'useUpdateLink', model['kbObject'])
        self.create_loopback_operation('DELETE', '{id}/', loopbackApp, model, jsonFile, jsonFile, 'useDeleteLink', model['kbObject'])

        self.create_loopback_operation('GET', '{id}/exists/', loopbackApp, model, jsonFile, jsonFile, 'useSelectLink', model['kbObject'])
        self.create_loopback_operation('POST', 'change-stream/', loopbackApp, model, jsonFile, jsonFile, 'useInsertLink', model['kbObject'])
        self.create_loopback_operation('GET', 'count/', loopbackApp, model, jsonFile, jsonFile, 'useSelectLink', model['kbObject'])
        self.create_loopback_operation('GET', 'findone/', loopbackApp, model, jsonFile, jsonFile, 'useSelectLink', model['kbObject'])
        self.create_loopback_operation('POST', 'update/', loopbackApp, model, jsonFile, jsonFile, 'useUpdateLink', model['kbObject'])

        self.create_loopback_operation('POST', 'replaceOrCreate/', loopbackApp, model, jsonFile, jsonFile, 'useInsertLink', model['kbObject'])
        self.create_loopback_operation('POST', '{id}/replace/', loopbackApp, model, jsonFile, jsonFile, 'useInsertLink', model['kbObject'])

    def create_loopback_operation(self, operationType, urlEnd, loopbackApp, model, parent, file, linkType, callee, ast=None):

        urlRoot = loopbackApp.restApiRoot.lower()[1:] + '/' + plural(model['name']).lower()
        if urlEnd.startswith('/'):
            url = urlRoot + urlEnd
        else:
            url = urlRoot + '/' + urlEnd
        if not url.endswith('/'):
            url += '/'

        
        if operationType == 'POST':
            objectType = 'CAST_NodeJS_PostOperation'

        elif operationType == 'PUT':
            objectType = 'CAST_NodeJS_PutOperation'

        elif operationType == 'DELETE':
            objectType = 'CAST_NodeJS_DeleteOperation'

        else:
            objectType = 'CAST_NodeJS_GetOperation'

        operation = CustomObject()
        operation.set_name(url)
        operation.set_type(objectType)
        operation.set_parent(parent)
        fullname = file.get_path() + '/' + operationType.lower() + '/' + url
        operation.set_guid(fullname)
        operation.set_fullname(fullname)
        operation.save()
        if ast:
            operation.save_position(ast.create_bookmark(file))
        else:
            operation.save_position(Bookmark(file, 1, 1, -1, -1))

        self.nbOperations_loop_back += 1

        if linkType and callee:
            create_link_nodeJS(linkType, operation, callee)


class SailsJSApplications:

    def __init__(self):
        self.servers = []

    def append(self, server):
        self.servers.append(server)

    def get_server_from_path(self, full_path):

        for server in self.servers:
            if server.path in full_path:
                return server

        return None

    def compute(self):
        for server in self.servers:
            server.compute()

    def nb_services(self):
        nb = 0
        for server in self.servers:
            nb += server.nb_service
        return nb


class SailsAnalysis():

    '''
    * List of models must be set before parsing the code.
    '''

    def __init__(self, path, name):
        self.path = path
        self.name = name
        self.nb_service = 0
        self.actions = []
        self.controllers = []
        self.services = []
        self.kb_object = None
        self.list_models = []
        self.model_infos = []
        self.model_objects = {}
        self.models = {}
        self.table_name = {}
        self.adapter_sql = {}
        self.function_sql = defaultdict(list)
        self.database_sails = None
        
        self.nb_link_model = 0
        self.nb_model = 0

    def extend_actions(self, actions):
        self.actions.extend(actions)

    def append_controllers(self, controllers):
        self.controllers.append(controllers)

    def append_services(self, services):
        self.services.append(services)

    def extend_model_infos(self, model_infos, kb_default):
        for model_info in model_infos:
            if not model_info[2]:
                model_info[2] = kb_default

            self.model_infos.append(model_info)
        
    def set_kb(self, kb):
        self.kb_object = kb

    def set_list_models(self, list_models):
        for models in list_models:
            if models.endswith('.js') and models not in self.list_models:
                model_name = models.replace('.js', '')
                self.list_models.append(model_name)

    def create_model(self, name, jsContent, type_metalmodel):
        
        if name in self.models.keys():
            return self.models[name]
        
        try:
            kbModel = CustomObject()
            kbModel.set_name(name)
            kbModel.set_type(type_metalmodel)
            kbModel.set_parent(jsContent.get_kb_object())
            fullname = jsContent.get_file().get_path() + '/' + name + '/' + type_metalmodel
            kbModel.set_guid(fullname)
            kbModel.set_fullname(fullname)
            kbModel.save()
            kbModel.save_position(Bookmark(jsContent.get_file(), 1, 1, -1, -1))
            
            name_file = jsContent.get_file().get_path().split('\\')[-1]
            
            log.info('Model object has been found at api\\models\\' + name_file + ' with type: ' + type_metalmodel)
            self.models[name] = kbModel
            self.nb_model += 1
            return kbModel

        except:
            pass
        
        
    def create_operation(self, service):
        if service.request not in ['GET', 'PUT', 'POST', 'DELETE'] or not service.uri:
            return None

        uri = service.uri

        if service.request == 'POST':
            objectType = 'CAST_NodeJS_PostOperation'

        elif service.request == 'PUT':
            objectType = 'CAST_NodeJS_PutOperation'

        elif service.request == 'DELETE':
            objectType = 'CAST_NodeJS_DeleteOperation'

        else:
            objectType = 'CAST_NodeJS_GetOperation'

        file = service.file

        operation = CustomObject()
        operation.set_name(uri)
        operation.set_type(objectType)
        operation.set_parent(service.parent)
        fullname = file.get_path() + '/' + service.request.lower() + uri
        operation.set_guid(fullname)
        operation.set_fullname(fullname)
        operation.save()

        log.info('Create ' + objectType + ' at ' + self.name + '/config/routes.js: ' + uri)
        self.nb_service += 1
        
        try:
            operation.save_position(file.get_position())
        except:
            operation.save_position(Bookmark(file, 1, 1, -1, -1))

        return operation

    def find_callee(self, service):
        if service.controller:
            controller_name = service.controller + 'Controller.js'

            for controller in self.controllers:
                file_name = controller.get_file().get_path()

                if not file_name.endswith(controller_name):
                    continue
                
                if not service.action:
                    return controller.get_kb_object()

                for action in self.actions:
                    path_file = os.path.abspath(action.get_file().get_path())

                    if controller_name in path_file and service.action in action.get_name():
                        return action.get_kb_object()

        elif service.action:
            action_norm = os.path.normpath(service.action)

            for controller in self.controllers:
                file_name = os.path.normpath(controller.get_file().get_path())

                if action_norm in file_name:
                    return controller.get_kb_object()

        return None

    def create_sql_named_query(self, query, parent, position):
        name = parent.get_name() + '_' + 'SQLquery'

        query_object = CustomObject()

        query_object.set_name(name)

        query_object.set_type('CAST_SQL_NamedQuery')

        query_object.set_parent(parent.get_kb_object())

        name_file = position.get_file().get_path().split('\\')[-1]
        full_name = name + '_' + name_file + '_' + str(position.get_begin_line()) + '_' + str(position.get_begin_column()) + '_' + str(position.get_end_line()) + '_' + str(position.get_end_column())
        guid = query + '_' + str(position)

        query_object.set_guid(guid)
        query_object.set_fullname(full_name)
        query_object.save()

        query_object.save_position(position)

        query_object.save_property("CAST_SQL_MetricableQuery.sqlQuery", query)

        create_link('callLink', parent.get_kb_object(), query_object, position)

        log.debug('Create SQL NameQuery: ' + name)

        return query_object
    
    def find_external_links_from_query(self, query, function_parent, position, name_collection):

        if not query:
            return False
        
        func = None

        try:
            func = getattr(external_link, 'analyse_embedded')
        except AttributeError:
            pass

        if func:
            embeddedResults = func(query)
        else:
            embeddedResults = None

        query_obj = self.create_sql_named_query(query, function_parent, position)

        if not embeddedResults or not func:
            tables = extract_tables(query)
            for table in tables:
                tableName = table['name']
                tableOperation = table['operation']
                linkType = None
                if tableOperation == 'SELECT':
                    linkType = 'useSelectLink'
                elif tableOperation == 'DELETE':
                    linkType = 'useDeleteLink'
                else:
                    linkType = 'useLink'
                  
                tbls = None
                if not func:
                    try:
                        tbls = external_link.find_objects(tableName, 'Database Table')
                        if not tbls:
                            tbls = external_link.find_objects(tableName, 'Database View')
                        
                        if tbls:
                            for tbl in tbls:
                                create_link(linkType, query_obj, tbl, position)
                                log.info('create link between query object and table: ' + tableName)
                        else:
                            elm = self.create_model(tableName, self.model_objects[name_collection], 'CAST_NodeJS_Unknown_Database_Table')
                            create_link(linkType, query_obj, elm, position)

                    except:
                        pass

                else:
                    elm = self.create_model(tableName, self.model_objects[name_collection], 'CAST_NodeJS_Unknown_Database_Table')
                    create_link(linkType, query_obj, elm, position)

        elif embeddedResults:
        
            for embeddedResult in embeddedResults:
                for linkType in embeddedResult.types:
                    create_link(linkType, query_obj, embeddedResult.callee, position)
                    log.info('create link between query object and table')

        return True

    def create_link_model(self, model_info):
        if model_info[0] not in self.model_objects:
            return
        
        if model_info[4] and model_info[4].is_identifier() and model_info[4].evaluate():
            query = model_info[4].evaluate()[0]
            if self.find_external_links_from_query(query, model_info[2], model_info[3], model_info[0]):
                return
        
        link_type = 'useLink'

        if model_info[1] == 'destroy':
            link_type = 'useDeleteLink'
        
        elif model_info[1] in ['update', 'replaceCollection', 'removeFromCollection']:
            link_type = 'useUpdateLink'

        elif model_info[1] in ['create', 'createEach', 'addToCollection']:
            link_type = 'useInsertLink'
        
        elif model_info[1] in ['find', 'findOne', 'findOrCreate', 'getDatastore']:
            link_type = 'useSelectLink'

        if self.database_sails:
            techno_name = self.database_sails[0]

        elif model_info[0] in self.adapter_sql:
            techno_name = self.adapter_sql[model_info[0]]

        else: 
            log.warning('Not found database config for this project')
            return
                
        model_objects = []

        if techno_name == 'sails-mongo':
            elm = self.create_model(model_info[0], self.model_objects[model_info[0]], 'CAST_NodeJS_MongoDB_Collection')
            model_objects.append(elm)
        
        elif techno_name in ['sails-postgresql', 'sails-mysql', 'MySQL']:
            try:
                name_table = model_info[0].lower()
                if model_info[0] in self.table_name.keys():
                    name_table = self.table_name[model_info[0]]

                model_objects = external_link.find_objects(name_table, 'Database Table')
                if not model_objects:
                    model_objects = external_link.find_objects(name_table, 'Database View')

                if model_objects:
                    log.info('found table from sql: ' + name_table)

            except:
                model_object = []

        if not model_objects:
            elm = self.create_model(model_info[0], self.model_objects[model_info[0]], 'CAST_NodeJS_Unknown_Database_Table')
            model_objects.append(elm)

        for model_object in model_objects:
            create_link(link_type, model_info[2].get_kb_object(), model_object, model_info[3])

        self.nb_link_model += 1

    def create_link_method_model(self, model_info):
        if model_info[0] not in self.function_sql:
            return

        for function in self.function_sql[model_info[0]]:
            if function.get_text() == model_info[1] and hasattr(model_info[2], 'get_kb_object'):
                create_link('callLink', model_info[2].get_kb_object(), function.get_kb_object(), model_info[3])
                log.info('link from controller and model: ' + str(model_info[2].get_text()) + ' - ' + str(function.get_text()))

    def compute(self):
        '''
        * Create service operation.
        * Create transaction with model
        '''
        nb_link = 0

        for service in self.services:
            operation = self.create_operation(service)

            if not operation or (not service.controller and not service.action):
                continue

            callee_ws = self.find_callee(service)

            if callee_ws:
                nb_link += 1
                create_link('callLink', operation, callee_ws)
            else:
                log.warning('something wrong from sails webservice creation' + str(service))

        for model_info in self.model_infos:
            try:
                if model_info[5]:
                    self.create_link_model(model_info)
                else:
                    self.create_link_method_model(model_info)
            except:
                log.warning('Something wrong in compute sails.js info')

        log.info('callLink created from config\\routes of sails framework: ' + str(nb_link))
        log.info('Number of model: ' + str(self.nb_model))
        log.info('Number link to model: ' + str(self.nb_link_model))
        log.info(str(self.nb_service) + ' Sails NodeJS web service operations created.')
