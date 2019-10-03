import cast.analysers.ua
from cast.analysers import Bookmark, create_link, log
from cast.application import open_source_file # @UnresolvedImport
from nodejs_parser import analyse, create_link_nodeJS
from server_analysis import LoopBackAnalysis, SailsAnalysis, SailsJSApplications
from collections import OrderedDict
from symbols import Violations, PotentialController, ExternalLibrary, nodejs_open_source_file
from microservice_analysis import Seneca
import traceback
import os
import json
from cast import Event
from collections import defaultdict

from data_support_analysis import Knexsupport
from AMPQ_analysis import MQTT

def get_short_uri(uri):
    shortUri = uri
    if '?' in uri:
        shortUri = uri[:uri.find('?')]
    if shortUri.endswith('/'):
        shortUri = shortUri[:-1]
    return shortUri
    
class NodeJS(cast.analysers.ua.Extension):

    class ParsingResults:

        def __init__(self):
            self.requires = []
            self.services = []
            self.httpRequests = []
            self.mongooseConnections = []
            self.mongooseModels = []
            self.dbConnections = []
            self.marklogicDatabases = []
            self.couchdbDatabases = []
            self.couchdbCalls = []
            self.violations = Violations()
            self.isApplication = False
            self.potentialExpressControllerClasses = []
            self.potentialExpressControllerRoutesFCall = []
            self.externalLibraries = {}
            self.externalLibrariesFunctionCalls = {}
            self.externalLibrariesMethodCalls = {}

            # loopback flag infos
            self.LoopbackServer = False
            self.loopbackRemoteMethods = []
            self.linkSuspensions = []

            # Sails info
            self.database_sails = None
            self.models_sails = []
            self.model_infos = []
            self.service_sails = []
            self.action_sails = []
            self.table_name = {}
            self.adapter_sql = {}
            self.function_sql = defaultdict(list)

            # Knex
            self.knex_require = False
            self.bookshelf_require = False
            self.model_knex_infos = []
            self.knex_config = None

            # mqtt
            self.mqtt_require = False
            self.mqtt_methods = []
            self.mqtt_events = []
            
            # package.json dependencies have info of nodejs project.
            self.is_node_project = False

            # seneca-micro-service
            self.seneca_require = False
            self.seneca_uses = []
            self.add_call = []
            self.act_call = []

    """
    Parse .js files and create NodeJS services.
    """
    def __init__(self):
        
        self.bFirstJabascriptFileAnalysis = True
        self.currentFile = None
        self.currentSourceCode = None
        self.currentFilename = None
        self.mongooseConnectionsByName = {}
        self.mongooseConnectionsByAst = {}
        self.mongooseModelsByConnectionByName = {}
#         self.marklogicDatabasesByConnectionVariable = {}
        self.nbOperations = 0
        self.nbMongooseModels = 0
        self.nbMarklogicDatabases = 0
        self.nbMarklogicCollections = 0
        self.nbCouchDBDatabases = 0
        self.nbDbAccesses = 0
        self.nbApplications = 0
        self.unknownTablesByName = {}
        self.httpRequestGuids = {}
        self.servicesByFilename = {}
        self.nodejsVersionsByDirname = {}

        jsonPath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.json'))
        self.config = json.loads(nodejs_open_source_file(jsonPath))

        self.marklogicDatabasesByConnectionParameter = {}

        self.parsingResultsToKeepByJSContent = OrderedDict()

        self.potentialExpressControllers = OrderedDict()
        self.potentialExpressControllerRoutesFCall = []

        self.externalLibrariesParent = None
        self.externalLibraries = {}

        self.jsonFilesByPathname = {}
        self.loopback_analysis = LoopBackAnalysis()
        self.potentialLoopbackServerFiles = []
        self.nbLoopbackModels = 0

        # Sails
        self.sails_apps = SailsJSApplications()

        # Knex support
        self.knex_support = Knexsupport()
    
        # mqtt
        self.mqtt = MQTT()

        # seneca
        self.seneca = Seneca()

        self.node_project_path = ''

    @Event('com.castsoftware.html5', 'start_json_content')
    def start_json_content(self, file):

        filename = file.get_path()
        if filename.lower().endswith('middleware.json'):
            self.loopback_analysis.search_for_loopback_application(filename)

        if not filename.lower().endswith('package.json'):
            self.jsonFilesByPathname[filename] = file
            return
         
        try:

            '''
            * package.json resolution
            '''
            jsonContent = json.loads(nodejs_open_source_file(filename))
            if 'engines' in jsonContent:
                if 'node' in jsonContent['engines']:
                    file.save_property('sourceFile.html5', 1)
                    nodeVersion = jsonContent['engines']['node']
                    parentDir = os.path.dirname(filename)
                    bm = Bookmark(file, 1, 1, 1, 1)
                    try:
                        enginesFound = False
                        nodeFound = False
                        infile = open_source_file(filename)
                        nLine = 1
                        for line in infile:
                            if '"engines"' in line:
                                enginesFound = True
                                if '"node"' in line:
                                    nodeFound = True
                            elif enginesFound:
                                if '"node"' in line:
                                    nodeFound = True
                            if nodeFound:
                                index = line.find("node")
                                indexBegin = line.find('"', index + 6)
                                if indexBegin:
                                    indexEnd = line.find('"', indexBegin + 1)
                                else:
                                    indexEnd = -1
                                if indexEnd > 0:
                                    bm = Bookmark(file, nLine, indexBegin + 2, nLine, indexEnd + 1)
                                break
                            nLine += 1
                        infile.close()
                    except:
                        log.debug(traceback.format_exc())
                    self.nodejsVersionsByDirname[parentDir] = { 'version': nodeVersion.strip(), 'position' : bm }
                    log.info('NodeJS version (' + str(nodeVersion) + ') found in ' + file.get_path())
            
            def is_node_dependencies(json_content):
                is_node_dependencies = ['express', 'hapi', 'sail', 'loopback', 'koa', 'seneca']

                for elm in is_node_dependencies:
                    if elm in json_content['dependencies']:
                        return True

                return False

            if 'name' in jsonContent and 'main' in jsonContent and 'dependencies' in jsonContent and is_node_dependencies(jsonContent):
                self.node_project_path = filename.replace('package.json', '')

            '''
            * .sailrc file detection.
            '''

            sail_config = filename.replace('package.json', '.sailsrc')
            routes_config = filename.replace('package.json', 'config\\routes.js')
            api_controler = filename.replace('package.json', 'api\\controllers')
            api_models = filename.replace('package.json', 'api\\models')
            is_sails = os.path.exists(sail_config) and os.path.exists(routes_config) and os.path.exists(api_controler)

            if is_sails:
                fullname = os.path.abspath(sail_config.replace('\\.sailsrc', ''))
                name = fullname.split('\\')[-1]
                sails_app = SailsAnalysis(fullname, name)

                if api_models:
                    list_models = os.listdir(api_models)
                    sails_app.set_list_models(list_models)

                self.sails_apps.append(sails_app)

        except:
            log.debug(traceback.format_exc())

    @Event('com.castsoftware.html5', 'start_analysis_root')
    def start_analysis_root(self, rootDir):
        log.info('start root analysis ' + rootDir)
        self.currentFile = None
        self.currentSourceCode = None
        self.currentFilename = None

    @Event('com.castsoftware.html5', 'end_analysis_root')
    def end_analysis_root(self, rootDir):
        log.info('end root analysis ' + rootDir)
    
    def process_before_javascript_analyses(self):
        for pathname, jsonFile in self.jsonFilesByPathname.items():
            dirname = os.path.dirname(pathname)
            self.loopback_analysis.process(dirname, jsonFile)

    @Event('com.castsoftware.html5', 'start_javascript_content')
    def start_javascript_content(self, jsContent):

        self.loopback_analysis.jsContent = jsContent
        
        if self.bFirstJabascriptFileAnalysis:
            self.process_before_javascript_analyses()
            self.bFirstJabascriptFileAnalysis = False
            
        self.currentFile = jsContent.get_file()
        self.currentFilename = os.path.abspath(self.currentFile.get_path())
        self.currentSourceCode = jsContent.kbObject
        
        versions = None
        for dirName, version in self.nodejsVersionsByDirname.items():
            if self.currentFilename.startswith(dirName):
                if versions == None:
                    versions = []
                versions.append(version)
        
        parsingResults = self.ParsingResults()

        sails_app = self.sails_apps.get_server_from_path(self.currentFilename)
        if sails_app:
            parsingResults.models_sails = sails_app.list_models
            parsingResults.database_sails = sails_app.database_sails
            parsingResults.table_name = sails_app.table_name
            parsingResults.adapter_sql = sails_app.adapter_sql
            parsingResults.function_sql = sails_app.function_sql
            parsingResults.is_node_project = True

        if not parsingResults.is_node_project and self.node_project_path and '\\client\\' not in self.currentFilename:
            parsingResults.is_node_project = self.node_project_path in self.currentFilename

        parsingResults.LoopbackServer = self.loopback_analysis.server

        try:
            analyse(jsContent, self.config, self.loopback_analysis, parsingResults, self.currentFile, versions)
        except:
            pass
        
        '''
        * Create model.
        * Sails save model infos, service infos...
        ''' 
        
        if sails_app:
            for model in sails_app.list_models:
                name_model = '\\api\\models\\' + model + '.js'
                if name_model in self.currentFilename and model not in sails_app.model_objects.keys():
                    sails_app.model_objects[model] = jsContent
            
            for service in parsingResults.service_sails:
                service.parent = jsContent.kbObject
                sails_app.append_services(service)

            sails_app.extend_model_infos(parsingResults.model_infos, jsContent.get_kb_object())
            sails_app.extend_actions(parsingResults.action_sails)

            if '\\api\\controllers' in self.currentFilename:
                sails_app.append_controllers(jsContent)
            
            if self.currentFilename.endswith('app.js'):
                sail_src = self.currentFilename.replace('app.js', '.sailsrc')
                if os.path.exists(sail_src):
                    kb = self.create_application(jsContent)
                    sails_app.set_kb(kb)
            
            if not sails_app.database_sails and parsingResults.database_sails:
                sails_app.database_sails = parsingResults.database_sails
            
        '''
        * express, hapi, loopback
        '''
        if parsingResults.isApplication:
            self.create_application(jsContent)
        if parsingResults.LoopbackServer and not self.loopback_analysis.server:
            self.create_loopback_server(jsContent)
            self.loopback_analysis.server = True
        for loopbackRemoteMethod in parsingResults.loopbackRemoteMethods:
            self.loopback_analysis.create_loopback_operation(loopbackRemoteMethod[0], loopbackRemoteMethod[1], loopbackRemoteMethod[2], loopbackRemoteMethod[3], jsContent.get_kb_object(), self.currentFile, loopbackRemoteMethod[4], loopbackRemoteMethod[5], loopbackRemoteMethod[6])
        for linkSuspension in parsingResults.linkSuspensions:
            create_link_nodeJS(linkSuspension.linkType, linkSuspension.caller, linkSuspension.callee, linkSuspension.callPart.create_bookmark(self.currentFile))

        for name, ast in parsingResults.externalLibraries.items():
            self.create_external_library(name, ast, \
                    parsingResults.externalLibrariesFunctionCalls[name] if name in parsingResults.externalLibrariesFunctionCalls else [], \
                    parsingResults.externalLibrariesMethodCalls[name] if name in parsingResults.externalLibrariesMethodCalls else [])
            
        if parsingResults.potentialExpressControllerClasses:
            for cl in parsingResults.potentialExpressControllerClasses:
                self.potentialExpressControllers[cl] = PotentialController(cl, jsContent.get_file()) 
        if parsingResults.potentialExpressControllerRoutesFCall:
            self.potentialExpressControllerRoutesFCall.extend(parsingResults.potentialExpressControllerRoutesFCall)
            
        for service in parsingResults.services:
            filename = self.currentFile.get_path()
            if filename in self.servicesByFilename:
                l = self.servicesByFilename[filename]
            else:
                l = []
                self.servicesByFilename[filename] = l
            service.sourceCode = self.currentSourceCode
            l.append(service)
        for dbConnection in parsingResults.dbConnections:
            self.create_database_accesses(dbConnection)
        for httpRequest in parsingResults.httpRequests:
            self.create_http_request(httpRequest)
                    
        if parsingResults.couchdbDatabases or parsingResults.marklogicDatabases or parsingResults.mongooseConnections or parsingResults.mongooseModels:
            self.parsingResultsToKeepByJSContent[jsContent] = parsingResults
            
        parsingResults.violations.save()

        # Save all infos

        # knex save info:
        self.knex_support.set_infos(parsingResults)

        # mqtt save infos
        self.mqtt.set_infos(parsingResults)

        # seneca save infos
        self.seneca.set_infos(parsingResults, jsContent)

    @Event('com.castsoftware.html5', 'end_javascript_contents')
    def end_javascript_contents(self):
        
        guids = {}
        couchDBByName = {}

        mongooseModelsByIdentifier = {}
        
        for _, parsingResults in self.parsingResultsToKeepByJSContent.items():
            for mongooseModel in parsingResults.mongooseModels:
                if mongooseModel.variableIdentifier:
                    mongooseModelsByIdentifier[mongooseModel.variableIdentifier] = mongooseModel
        
        for jsContent, parsingResults in self.parsingResultsToKeepByJSContent.items():
            
            for marklogicDatabase in parsingResults.marklogicDatabases:
                try:
                    self.create_marklogic_database(marklogicDatabase, jsContent, guids)
                except:
                    log.debug('Internal issue when creating create_marklogic_database: ' + str(traceback.format_exc()))
                
            for mongooseConnection in parsingResults.mongooseConnections:
                try:
                    self.create_mongoose_connection(mongooseConnection, jsContent)
                except:
                    log.debug('Internal issue when creating create_marklogic_database: ' + str(traceback.format_exc()))
            for mongooseModel in parsingResults.mongooseModels:
                try:
                    self.create_mongoose_model(mongooseModel, jsContent, mongooseModelsByIdentifier, guids)
                except:
                    log.debug('Internal issue when creating create_marklogic_database: ' + str(traceback.format_exc()))
            for couchdbDatabase in parsingResults.couchdbDatabases:
                try:
                    self.create_couchdb_database(couchdbDatabase, jsContent, guids, couchDBByName)
                except:
                    log.debug('Internal issue when creating create_marklogic_database: ' + str(traceback.format_exc()))
            for couchdbCall in parsingResults.couchdbCalls:
                try:
                    self.create_couchdb_call(couchdbCall, couchDBByName, jsContent)
                except:
                    log.debug('Internal issue when creating create_marklogic_database: ' + str(traceback.format_exc()))

        guids = {}  # contains guids as key and number as value to avoid duplicated guids
        for file_name, services in self.servicesByFilename.items():
            for service in services:
                if service.routerReference:
                    serviceDirname = os.path.dirname(service.sourceCode.parent.get_path())
#                     routerDirname = os.path.abspath(os.path.join(serviceDirname, service.routerReference) + '.js')
                    if isinstance(service.routerReference, str):
                        routerDirname = os.path.abspath(os.path.join(serviceDirname, service.routerReference) + '.js')
                    else:
                        try:
                            routerDirname = service.routerReference.get_file().get_path()
                        except:
                            routerDirname = ''
                    if routerDirname in self.servicesByFilename:
                        routerServices = self.servicesByFilename[routerDirname]
                        for routerService in routerServices:
                            if routerService.isRouter:
                                self.create_operation(routerService, guids, service.get_uri_evaluation())
                    else:
                        self.create_operation(service, guids)

                elif service.koa_router:
                    if service.koa_use:
                        def uri_real(router_info, url):
                            try:
                                router = router_info.get_resolutions()[0].callee

                                if not router.is_identifier():

                                    return False

                                while not router.is_js_content():
                                    router = router.parent
    
                                routerDirname = router.get_file().get_path()

                                if routerDirname not in self.servicesByFilename.keys():
                                    return False
                                routerServices = self.servicesByFilename[routerDirname]
                                
                                if file_name == routerDirname:
                                    for routerService in routerServices:
                                        log.debug('final -----' + (url))
                                        self.create_operation(routerService, guids, url)
                                    return
                                
                                for routerService in routerServices:
                                    old_url = url
                                    if routerService.koa_router and not routerService.isRouter:
                                        url = url + routerService.get_uri_evaluation()
                                        if not uri_real(routerService.koa_router, url):
                                            url = old_url
                                        
                                    elif routerService.koa_router and routerService.isRouter:
                                        self.create_operation(routerService, guids, url)

                                    url = old_url

                                return True

                            except:
                                return False

                        uri_real(service.koa_router, '')

                elif not service.isRouter:
                    self.create_operation(service, guids)
                    
        self.create_express_controllers()
        
        self.sails_apps.compute()
        self.knex_support.compute()
        self.mqtt.compute()
        self.seneca.compute()

        self.nbOperations = self.nbOperations + self.loopback_analysis.nbOperations_loop_back

        log.info(str(self.nbApplications) + ' NodeJS applications created.')
        log.info(str(self.nbOperations) + ' NodeJS web service operations created.')
        log.info(str(self.nbMongooseModels) + ' NodeJS mongoose models created.')
        log.info(str(self.nbDbAccesses) + ' NodeJS database accesses found.')
        log.info(str(self.nbMarklogicDatabases) + ' NodeJS marklogic databases created.')
        log.info(str(self.nbMarklogicCollections) + ' NodeJS marklogic collections created.')
        log.info(str(self.nbCouchDBDatabases) + ' NodeJS CouchDB databases created.')
        log.info(str(self.loopback_analysis.nbLoopbackModels) + ' NodeJS loopback models created.')
    
    def create_express_controllers(self):
        guids = {}
        for potentialExpressControllerRoutesFCall in self.potentialExpressControllerRoutesFCall:
            parentClass = potentialExpressControllerRoutesFCall.ast.parent
            while parentClass and hasattr(parentClass, 'is_class') and not parentClass.is_class():
                parentClass = parentClass.parent
            if parentClass:
                if parentClass in self.potentialExpressControllers:
                    ctrl = self.potentialExpressControllers[parentClass]
                    if not ctrl.kbObject:
                        self.create_express_controller(ctrl)
                    potentialExpressControllerRoutesFCall.sourceCode = parentClass.parent
                    self.create_operation(potentialExpressControllerRoutesFCall, guids, None, ctrl.kbObject)

    def create_express_controller(self, ctrl):
        
        ctrl_object = cast.analysers.CustomObject()
        ctrl.kbObject = ctrl_object
        ctrl_object.set_name(ctrl.cl.get_name())
        ctrl_object.set_parent(ctrl.cl.get_kb_object())
        fullname = ctrl.cl.get_kb_object().guid + '/EXPRESS_CTRL'
        displayfullname = ctrl.cl.get_kb_object().fullname + '/EXPRESS_CTRL'
        ctrl_object.set_fullname(displayfullname)
        ctrl_object.set_guid(fullname)
        ctrl_object.set_type('CAST_NodeJS_Express_Controller')
        ctrl_object.save()
        ctrl_object.save_position(ctrl.cl.create_bookmark(ctrl.file))
        
    def normalize_path(self, operationPath):

        service_names = operationPath.split('/')
        service_name = None
        if service_names:
            service_name = ''
            for part in service_names:
                if part: 
                    if part.startswith('{') or part.startswith(':'):
                        service_name += '{}/'
                    else:
                        service_name += ( part + '/' )
        return service_name

    def create_single_operation(self, service, guids, routedUrl, operationName, localGuids, parentKbObject = None):

        operationType = service.type
        handler = service.handler
        ast = service.ast
                
        try:
            routedUrl = routedUrl.replace('****', '')
        except:
            pass
        if routedUrl:
            if operationName.startswith('/'):
                operationName = routedUrl + operationName[1:]
            else:
                operationName = routedUrl + operationName

        if not operationName:
            operationName = '/'
           
        name = operationName.replace('****', '')
        if name == '/':
            if parentKbObject:
                fullname = parentKbObject.guid + '/' + operationType + '/'
                displayfullname = parentKbObject.fullname + '.' + operationType + '.'
            else:
                fullname = service.sourceCode.guid + '/' + operationType + '/'
                displayfullname = service.sourceCode.fullname + '.' + operationType + '.'
        else:
            if parentKbObject:
                fullname = parentKbObject.guid + '/' + operationType + '/' + name
                displayfullname = parentKbObject.fullname + '.' + operationType + '.' + name
            else:
                fullname = service.sourceCode.guid + '/' + operationType + '/' + name
                displayfullname = service.sourceCode.fullname + '.' + operationType + '.' + name
                    
        if not localGuids or not fullname in localGuids:

            if fullname in guids:
                nr = guids[fullname]
                guids[fullname] = nr + 1
                fullname += ('_' + str(nr + 1))
                try:
                    service.sourceCode.save_violation('CAST_NodeJS_Metric_MultipleRoutesForSamePath.numberOfMultipleRoutesForSamePath', ast.create_bookmark(service.sourceCode.parent))
                except:
                    pass
            else:
                guids[fullname] = 0
                if service.inLoop and not '****' in operationName:
                    try:
                        service.sourceCode.save_violation('CAST_NodeJS_Metric_MultipleRoutesForSamePath.numberOfMultipleRoutesForSamePath', ast.create_bookmark(service.sourceCode.parent))
                    except:
                        pass

            operation_object = cast.analysers.CustomObject()
            operation_object.set_name(name)
            if parentKbObject:
                operation_object.set_parent(parentKbObject)
            else:
                operation_object.set_parent(service.sourceCode)
            operation_object.set_fullname(displayfullname)
            operation_object.set_guid(fullname)
            if localGuids != None:
                localGuids.append(fullname)
    
            linkType = 'fireLink'
            if operationType == 'delete':
                linkType = 'fireDeleteLink'
                operation_object.set_type('CAST_NodeJS_DeleteOperation')
            elif operationType == 'put':
                linkType = 'fireUpdateLink'
                operation_object.set_type('CAST_NodeJS_PutOperation')
            elif operationType == 'post':
                linkType = 'fireUpdateLink'
                operation_object.set_type('CAST_NodeJS_PostOperation')
            elif operationType == 'use':
                linkType = 'fireLink'
                operation_object.set_type('CAST_NodeJS_UseOperation')
            else:
                linkType = 'fireSelectLink'
                operation_object.set_type('CAST_NodeJS_GetOperation')
            operation_object.save()
            operation_object.save_position(ast.create_bookmark(service.sourceCode.parent))
            operation_object.save_property('checksum.CodeOnlyChecksum', ast.get_code_only_crc())
            
            log.debug('create_operation ' + fullname)

            self.nbOperations += 1

            if not handler:
                return

            if handler.get_kb_symbol():
                create_link_nodeJS(linkType, operation_object, handler.kbObject, handler.create_bookmark(service.sourceCode.parent))
            elif handler.get_resolutions():
                for resolution in handler.resolutions:
                    if resolution.callee and resolution.callee.get_kb_object():
                        create_link_nodeJS(linkType, operation_object, resolution.callee.get_kb_object(), handler.create_bookmark(service.sourceCode.parent))

    def create_operation(self, service, guids, routedUrl = None, parentKbObject = None):

        operationName = service.get_uri_evaluation()
        if type(operationName) is list:
            localGuids = []
            for opName in operationName:
                if type(routedUrl) is list:
                    for routed in routedUrl:
                        self.create_single_operation(service, guids, routed, opName, localGuids, parentKbObject)
                else:
                    self.create_single_operation(service, guids, routedUrl, opName, localGuids, parentKbObject)
        else:
            if type(routedUrl) is list:
                for routed in routedUrl:
                    self.create_single_operation(service, guids, routed, operationName, None, parentKbObject)
            else:
                self.create_single_operation(service, guids, routedUrl, operationName, None, parentKbObject)

    def create_mongoose_connection(self, mongooseConnection, jsContent):
        
        evs = self.evaluate_nosql_name(mongooseConnection.url)
#         if not evs:
#             ident = None
#             try:
#                 if mongooseConnection.url.resolutions:
#                     ident = mongooseConnection.url.resolutions[0].callee
#             except:
#                 pass
#             if not ident:
#                 ident = mongooseConnection.url
#             if ident and ident.is_identifier():
#                 evs.append(ident.get_name())
            
        for url in evs:

            if mongooseConnection.name:
                url = mongooseConnection.name + '/' + url
        
            if url in self.mongooseConnectionsByName:
                continue
            
            self.mongooseConnectionsByName[url] = mongooseConnection
            self.mongooseConnectionsByAst[mongooseConnection.ast] = mongooseConnection
            
            ast = mongooseConnection.ast
            
            mongooseConnection_object = cast.analysers.CustomObject()
            mongooseConnection.kb_symbol = mongooseConnection_object
            
            mongooseConnection_object.set_name(url)
            mongooseConnection_object.set_parent(jsContent.get_kb_object())
            fullname = jsContent.file.get_path() + '/CAST_NodeJS_MongoDB_Connection/' + url
            displayfullname = jsContent.file.get_path() + '.CAST_NodeJS_MongoDB_Connection.' + url
            mongooseConnection.fullname = fullname
            mongooseConnection_object.set_fullname(displayfullname)
            mongooseConnection_object.set_guid(fullname)
            mongooseConnection_object.set_type('CAST_NodeJS_MongoDB_Connection')
            mongooseConnection_object.save()
            mongooseConnection_object.save_position(ast.create_bookmark(jsContent.file))
            mongooseConnection_object.save_property('checksum.CodeOnlyChecksum', ast.get_code_only_crc())
            
            log.debug('create_mongodb_connection ' + fullname)

    def evaluate_nosql_name(self, identName):
        
        evs = identName.evaluate()

        if not evs:
            callee = None
            try:
                if identName.resolutions:
                    callee = identName.resolutions[0].callee
            except:
                pass
            if not callee:
                callee = identName
            if callee and callee.is_identifier():
                """
                var config = { collection: 'myCollection' }
                var collectionName = config.collection
                
                If config.collection is resolved to config, then we keep config as name for collection, and not config.
                """
                try:
                    identFullname = identName.get_fullname()
                    if '.' in identFullname and identFullname.startswith(callee.get_name()):
                        evs.append(identName.get_name())
                    else:
                        evs.append(callee.get_name())
                except:
                    evs.append(callee.get_name())
        return evs
        
    def create_mongoose_model(self, mongooseModel, jsContent, mongooseModelsByIdentifier, guids):

        def get_model_by_name(name):
            for model in mongooseModelsByIdentifier.values():
                if model.name.get_text() == name.get_text():
                    return model
            return None

        caller_id = mongooseModel.callerIdentifier
        if caller_id:
            realMongooseModel = None
            try:
                if caller_id in mongooseModelsByIdentifier:
                    realMongooseModel = mongooseModelsByIdentifier[caller_id]
    
                elif caller_id.is_function_call():
                    callpart = caller_id.get_function_call_parts()[0]
    
                    if not callpart.get_name() == 'model':
                        return
    
                    name_model = callpart.get_parameters()[0]
                    realMongooseModel = get_model_by_name(name_model)
    
            except:
                log.warning('can not resolve identifier caller')
                return

            if not realMongooseModel:
                return

            if not realMongooseModel.kb_symbol:
                self.create_mongoose_model(realMongooseModel, realMongooseModel.jsContent, mongooseModelsByIdentifier, guids)

            if not realMongooseModel.kb_symbol:
                return

            for linkSuspension in mongooseModel.linkSuspensions:
                create_link_nodeJS(linkSuspension.linkType, linkSuspension.caller, realMongooseModel.kb_symbol, linkSuspension.callPart.create_bookmark(jsContent.file))
            return
        
        if mongooseModel.kb_symbol:
            return
        
        if mongooseModel.fcallpartConnection in self.mongooseConnectionsByAst:
            parent = self.mongooseConnectionsByAst[mongooseModel.fcallpartConnection].get_kb_object()
#             fullnamePrefix = self.mongooseConnectionsByAst[mongooseModel.fcallpartConnection].fullname
        else:
            parent = jsContent.get_kb_object()
        fullnamePrefix = jsContent.file.get_path() + '/CAST_NodeJS_MongoDB_Collection'
        displayfullnamePrefix = jsContent.file.get_path() + '.CAST_NodeJS_MongoDB_Collection'

        if mongooseModel.name:
            evs = self.evaluate_nosql_name(mongooseModel.name)
        else:
            evs = []
            
        for name in evs:

            if mongooseModel.fcallpartConnection in self.mongooseModelsByConnectionByName and name in self.mongooseModelsByConnectionByName[mongooseModel.fcallpartConnection]:
                
                modelReference = self.mongooseModelsByConnectionByName[mongooseModel.fcallpartConnection][name]

            else:
                          
                modelReference = mongooseModel
                if mongooseModel.fcallpartConnection in self.mongooseModelsByConnectionByName:
                    l = self.mongooseModelsByConnectionByName[mongooseModel.fcallpartConnection]
                else:
                    l = {}
                    self.mongooseModelsByConnectionByName[mongooseModel.fcallpartConnection] = l
                l[name] = mongooseModel
                
                ast = mongooseModel.ast
                
                mongooseModel_object = cast.analysers.CustomObject()
                mongooseModel.kb_symbol = mongooseModel_object
                
                mongooseModel_object.set_name(name)
                mongooseModel_object.set_parent(parent)
                fullname = fullnamePrefix + '/' + name
                displayfullname = displayfullnamePrefix + '.' + name

                if not fullname in guids:
                    guids[fullname] = 1
                else:
                    guids[fullname] = guids[fullname] + 1
                    fullname += ('_' + str(guids[fullname]))
                
                mongooseModel_object.set_fullname(displayfullname)
                mongooseModel_object.set_guid(fullname)
                mongooseModel_object.set_type('CAST_NodeJS_MongoDB_Collection')
                mongooseModel_object.save()
                mongooseModel_object.save_position(ast.create_bookmark(jsContent.file))
                mongooseModel_object.save_property('checksum.CodeOnlyChecksum', ast.get_code_only_crc())
                
                log.debug('create_mongodb_model ' + fullname)
                self.nbMongooseModels += 1
            
            for linkSuspension in mongooseModel.linkSuspensions:
                create_link_nodeJS(linkSuspension.linkType, linkSuspension.caller, modelReference.kb_symbol, linkSuspension.callPart.create_bookmark(jsContent.file))
                
    def create_marklogic_database(self, marklogicDatabase, jsContent, guids):
        
        if marklogicDatabase.connectionParameter in self.marklogicDatabasesByConnectionParameter:
            db = self.marklogicDatabasesByConnectionParameter[marklogicDatabase.connectionParameter]
            marklogicDatabase_object = db.kb_symbol
            marklogicDatabase.referencedDatabase = db
            marklogicDatabase.kb_symbol = marklogicDatabase_object
        else:
            self.marklogicDatabasesByConnectionParameter[marklogicDatabase.connectionParameter] = marklogicDatabase
            marklogicDatabase_object = None
        
        ast = marklogicDatabase.connectionParameter
        
        if not marklogicDatabase_object:

            marklogicDatabase_object = cast.analysers.CustomObject()
            marklogicDatabase.kb_symbol = marklogicDatabase_object
            
            marklogicDatabase_object.set_name(marklogicDatabase.name)
            marklogicDatabase_object.set_parent(jsContent.get_kb_object())
            fullname = ast.get_file().get_path() + '/CAST_NodeJS_Marklogic_Database/' + marklogicDatabase.name
            displayfullname = ast.get_file().get_path() + '.CAST_NodeJS_Marklogic_Database.' + marklogicDatabase.name
            if not fullname in guids:
                guids[fullname] = 1
            else:
                guids[fullname] = guids[fullname] + 1
                fullname += ('_' + str(guids[fullname]))
    
            log.info('create marklogic database ' + fullname)
            
            marklogicDatabase_object.set_fullname(displayfullname)
            marklogicDatabase_object.set_guid(fullname)
            marklogicDatabase_object.set_type('CAST_NodeJS_Marklogic_Database')
            marklogicDatabase_object.save()
            marklogicDatabase_object.save_position(ast.create_bookmark(marklogicDatabase.connectionParameter.get_file()))
            marklogicDatabase_object.save_property('checksum.CodeOnlyChecksum', ast.get_code_only_crc())
                
            self.nbMarklogicDatabases += 1
        
        collections = {}
        
        for collection in marklogicDatabase.collections.keys():
            kbObject = self.create_marklogic_collection(collection, marklogicDatabase, jsContent, guids)
            collections[collection] = kbObject

        for suspLink in marklogicDatabase.linksToCollections:
            try:
                if suspLink.callee:
                    create_link_nodeJS(suspLink.linkType, suspLink.caller, collections[suspLink.callee], suspLink.callPart.create_bookmark(jsContent.file))
                else:
                    create_link_nodeJS(suspLink.linkType, suspLink.caller, marklogicDatabase_object, suspLink.callPart.create_bookmark(jsContent.file))
            except:
                pass

    def create_marklogic_collection(self, param, marklogicDatabase, jsContent, guids):
        
        evs = self.evaluate_nosql_name(param)

        if evs:
            for n in evs:
                
                if n.startswith('/'):
                    name = n[1:]
                else:
                    name = n

                if marklogicDatabase.referencedDatabase and name in marklogicDatabase.referencedDatabase.collectionsByName:
                    return marklogicDatabase.referencedDatabase.collectionsByName[name]
                if name in marklogicDatabase.collectionsByName:
                    return marklogicDatabase.collectionsByName[name]
        
                marklogicCollection_object = cast.analysers.CustomObject()
                if marklogicDatabase.referencedDatabase:
                    marklogicDatabase.referencedDatabase.add_collection_by_name(name, marklogicCollection_object)
                else:
                    marklogicDatabase.add_collection_by_name(name, marklogicCollection_object)
                
                marklogicCollection_object.set_name(name)
                marklogicCollection_object.set_parent(marklogicDatabase.kb_symbol)
#                 fullname = marklogicDatabase.kb_symbol.fullname + '/' + name
                fullname = jsContent.file.get_path() + '/CAST_NodeJS_Marklogic_Collection/' + name
                displayfullname = jsContent.file.get_path() + '.CAST_NodeJS_Marklogic_Collection.' + name
        
                log.info('create marklogic collection ' + fullname)
                
                if not fullname in guids:
                    guids[fullname] = 1
                else:
                    guids[fullname] = guids[fullname] + 1
                    fullname += ('_' + str(guids[fullname]))
                
                marklogicCollection_object.set_fullname(displayfullname)
                marklogicCollection_object.set_guid(fullname)
                marklogicCollection_object.set_type('CAST_NodeJS_Marklogic_Collection')
                marklogicCollection_object.save()
                try:
                    marklogicCollection_object.save_position(marklogicDatabase.collections[param].create_bookmark(jsContent.file))
                except:
                    pass
                marklogicDatabase.set_collection_kb_object(param, marklogicCollection_object)
                    
                self.nbMarklogicCollections += 1
                
                return marklogicCollection_object

    def create_couchdb_database(self, couchdbDatabase, jsContent, guids, couchDBByName):
        
        names = self.evaluate_nosql_name(couchdbDatabase.name)
        for name in names:
            
            if name in couchDBByName:
                for suspLink in couchdbDatabase.linksToDatabase:
                    try:
                        create_link_nodeJS(suspLink.linkType, suspLink.caller, couchdbDatabase.kb_symbol, suspLink.callPart.create_bookmark(jsContent.file))
                    except:
                        pass
                continue
            
            couchDBByName[name] = couchdbDatabase
            
            ast = couchdbDatabase.ast
            
            couchdbDatabase_object = cast.analysers.CustomObject()
            couchdbDatabase.kb_symbol = couchdbDatabase_object
            
            couchdbDatabase_object.set_name(name)
            couchdbDatabase_object.set_parent(jsContent.get_kb_object())
            fullname = jsContent.file.get_path() + '/CAST_NodeJS_CouchDB_Database/' + name
            displayfullname = jsContent.file.get_path() + '.CAST_NodeJS_CouchDB_Database.' + name
            if not fullname in guids:
                guids[fullname] = 1
            else:
                guids[fullname] = guids[fullname] + 1
                fullname += ('_' + str(guids[fullname]))
    
            log.info('create CouchDB database ' + fullname)
            
            couchdbDatabase_object.set_fullname(displayfullname)
            couchdbDatabase_object.set_guid(fullname)
            couchdbDatabase_object.set_type('CAST_NodeJS_CouchDB_Database')
            couchdbDatabase_object.save()
            couchdbDatabase_object.save_position(ast.create_bookmark(jsContent.file))
            couchdbDatabase_object.save_property('checksum.CodeOnlyChecksum', ast.get_code_only_crc())
                
            self.nbCouchDBDatabases += 1
            
            for suspLink in couchdbDatabase.linksToDatabase:
                try:
                    create_link_nodeJS(suspLink.linkType, suspLink.caller, couchdbDatabase_object, suspLink.callPart.create_bookmark(jsContent.file))
                except:
                    pass

    def create_couchdb_call(self, couchdbCall, couchDBDatabasesByName, jsContent):
                    
        dbNames = couchdbCall.variableName.evaluate()
        if dbNames:
            for name in dbNames:
                if name in couchDBDatabasesByName:
                    db = couchDBDatabasesByName[name]
                    try:
                        create_link_nodeJS(couchdbCall.linkType, couchdbCall.caller, db.kb_symbol, couchdbCall.ast.create_bookmark(jsContent.file))
                    except:
                        pass
        
    def create_database_accesses(self, dbConnection):

        for linkSuspension in dbConnection.linkSuspensions:
            callee = linkSuspension.callee
            if isinstance(callee, str):
                calleeName = callee.upper()
                if calleeName in self.unknownTablesByName:
                    callee = self.unknownTablesByName[calleeName]
                else:
                    callee = cast.analysers.CustomObject()
                    self.unknownTablesByName[calleeName] = callee
                    callee.set_name(calleeName)
#                   Due to a bug in the framework, we can not create an object whose parent is a project anymore
#                     callee.set_parent(self.currentFile.get_project())
                    callee.set_parent(self.currentFile)
                    fullname = self.currentFile.get_project().get_fullname() + '/CAST_NodeJS_Unknown_Database_Table/' + calleeName
                    displayfullname = self.currentFile.get_project().get_fullname() + '.CAST_NodeJS_Unknown_Database_Table.' + calleeName
                    callee.set_fullname(displayfullname)
                    callee.set_guid(fullname)
                    callee.set_type('CAST_NodeJS_Unknown_Database_Table')
                    callee.save()
                    create_link('parentLink', callee, self.currentFile.get_project())
                     
                    log.debug('create_unresolved table ' + calleeName)
            if callee:
                self.nbDbAccesses += 1
                if linkSuspension.caller:
                    create_link_nodeJS(linkSuspension.linkType, linkSuspension.caller, callee, linkSuspension.callPart.create_bookmark(self.currentFile))
                else:
                    create_link_nodeJS(linkSuspension.linkType, self.currentSourceCode, callee, linkSuspension.callPart.create_bookmark(self.currentFile))

#         self.type = type
#         self.uri = uri
#         self.handler = handler
#         self.ast = ast
#         self.kbObject = None
    def create_http_request(self, httpRequest, uri = None):
            
        if uri == None:
            uris = httpRequest.get_uri_evaluation()
            if type(uris) is list:
                for uri in uris:
                    self.create_http_request(httpRequest, uri)
                return
            _uri = uris
        else:
            _uri = uri

        if httpRequest.type == 'GET':
            objectType = 'CAST_NodeJS_GetHttpRequestService'
        elif httpRequest.type == 'POST':
            objectType = 'CAST_NodeJS_PostHttpRequestService'
        elif httpRequest.type == 'PUT':
            objectType = 'CAST_NodeJS_PutHttpRequestService'
        elif httpRequest.type == 'DELETE':
            objectType = 'CAST_NodeJS_DeleteHttpRequestService'
        else:
            objectType = 'CAST_NodeJS_GetHttpRequestService'
        
        obj = cast.analysers.CustomObject()
        name = get_short_uri(_uri)
        obj.set_name(name)
        obj.set_type(objectType)
        obj.set_parent(self.currentSourceCode)
        fullname = httpRequest.caller.get_kb_symbol().get_kb_fullname() + '/' + objectType + '/' + name
        displayfullname = httpRequest.caller.get_kb_symbol().get_display_fullname() + '.' + httpRequest.type.lower() + '.' + name
        n = 0
        if fullname in self.httpRequestGuids:
            n = self.httpRequestGuids[fullname] + 1
            finalFullname = fullname + '_' + str(n)
        else:
            finalFullname = fullname
        self.httpRequestGuids[fullname] = n
        obj.set_guid(finalFullname)
        obj.set_fullname(displayfullname)
        obj.save()
        obj.save_property('CAST_ResourceService.uri', _uri)
        crc = httpRequest.ast.tokens[0].get_code_only_crc()
        obj.save_property('checksum.CodeOnlyChecksum', crc)
        obj.save_position(httpRequest.ast.create_bookmark(self.currentFile))
     
        create_link_nodeJS('callLink', httpRequest.caller, obj)
        
        if httpRequest.handler:
            create_link_nodeJS('callLink', obj, httpRequest.handler.get_kb_object())
            
        for onFunction in httpRequest.onFunctions:
            create_link_nodeJS('callLink', obj, onFunction.get_kb_object())
    
    def create_application(self, jsContent):

        log.info('NodejS application found ' + self.currentFile.get_path())
        self.nbApplications += 1
        
        app = cast.analysers.CustomObject()
        name = self.currentSourceCode.name[:-3]
        app.set_name(name)
        app.set_type('CAST_NodeJS_Application')
        app.set_parent(self.currentFile)
        fullname = self.currentFile.get_path() + '/CAST_NodeJS_Application'
        displayfullname = self.currentFile.get_path() + '.CAST_NodeJS_Application'
        app.set_guid(fullname)
        app.set_fullname(displayfullname)
        app.save()
        crc = jsContent.objectDatabaseProperties.checksum
        app.save_property('checksum.CodeOnlyChecksum', crc)
        app.save_position(jsContent.create_bookmark(self.currentFile))
     
        create_link_nodeJS('relyonLink', app, self.currentSourceCode)
        
        return app

    def create_loopback_server(self, jsContent):

        dirname = os.path.dirname(self.currentFile.get_path())

        log.info('NodejS loopback server found ' + self.currentFile.get_path())
        app = self.create_application(jsContent)

        if dirname in self.loopback_analysis.loopbackApplications:
            appli = self.loopback_analysis.loopbackApplications[dirname]
            appli.kbObject = app
            for model in appli.models.values():
                if 'kbObject' in model:
                    create_link_nodeJS('referLink', appli, model['kbObject'])
                
                else:
                    log.warning('model found in model-config is not defined: ' + str(model['name']))
    
    def create_external_library(self, name, ast, externalLibrariesFunctionCalls=[], externalLibrariesMethodCalls=[]):
        
        parentFullname = 'NodeJS.externalLibrary'
        if not self.externalLibrariesParent:
            self.externalLibrariesParent = cast.analysers.CustomObject()
            self.externalLibrariesParent.set_name('NodeJS Standard library')
            self.externalLibrariesParent.set_type('CAST_NodeJS_External_Library')
            self.externalLibrariesParent.set_parent(self.currentFile.get_project())
            self.externalLibrariesParent.set_guid(parentFullname)
            self.externalLibrariesParent.set_external()
            self.externalLibrariesParent.set_fullname(parentFullname)
            self.externalLibrariesParent.save()
         
        if name in self.externalLibraries:
            extLib = self.externalLibraries[name]
            obj = extLib.kbObject
        else:
            extLib = ExternalLibrary(name)
            extLib.create_objects(self.externalLibrariesParent, parentFullname)
            self.externalLibraries[name] = extLib
            obj = extLib.kbObject
        create_link_nodeJS('useLink', self.currentSourceCode, obj, ast.create_bookmark(self.currentFile))
        
        for linkSusp in externalLibrariesFunctionCalls:
            func = extLib.get_kb_function(linkSusp.callPart.get_identifier().get_name())
            if func:
                create_link_nodeJS('callLink', linkSusp.caller, func, linkSusp.callPart.create_bookmark(self.currentFile))
        
        for linkSusp in externalLibrariesMethodCalls:
            createClassMethod = linkSusp.infos['createClassMethod']
            try:
                className = ExternalLibrary.functionReturnsClassByLibName[extLib.name][createClassMethod]
                meth = extLib.get_kb_method(className, linkSusp.callPart.get_identifier().get_name())
                if meth:
                    create_link_nodeJS('callLink', linkSusp.caller, meth, linkSusp.callPart.create_bookmark(self.currentFile))
            except:
                log.debug('Internal issue when creating link to external method: ' + str(traceback.format_exc()))
        
    
