'''
Created on 26 nov. 2014

@author: iboillon
'''
import cast.analysers.ua
from cast.analysers import Bookmark, log
from cast.application import open_source_file # @UnresolvedImport
from collections import OrderedDict
import os
import json
import traceback

def nodejs_open_source_file(filepath, utf8Before = True):
    
    text = None
    f = None
    if utf8Before:
        try:
            f = open(filepath, 'r', encoding="utf8")
            text = f.read()
        except:
            if f:
                f.close()
            try:
                f = open(filepath, 'r')
                text = f.read()
            except:
                if f:
                    f.close()
                f = open_source_file(filepath)
                text = f.read()
                f.close()
    else:
        try:
            f = open(filepath, 'r')
            text = f.read()
        except:
            if f:
                f.close()
            try:
                f = open(filepath, 'r', encoding="utf8")
                text = f.read()
            except:
                if f:
                    f.close()
                f = open_source_file(filepath)
                text = f.read()
                f.close()
    return text

class LinkSuspension:
    
    def __init__(self, linkType, caller, callee, callPart):
        self.callPart = callPart
        self.linkType = linkType
        self.caller = caller
        self.callee = callee
        self.infos = {}

class ExternalLibrary:
         
    functionListByLibName = {'fs' : ['read', 'readFile', 'readSync', 'readFileSync', 'write', 'writeFile', 'writeSync', 'writeFileSync']}
    functionCreatingClassListByLibName = {'fs' : ['createReadStream', 'createWriteStream']}
    functionReturnsClassByLibName = {'fs' : {'createReadStream' : 'ReadStream', 'createWriteStream' : 'WriteStream'}}
    classListByLibName = {'fs': { 'ReadStream' : [ 'read', 'pipe' ] 
                                 , 'WriteStream' : [ 'write' ] }
                          }
    methodList = [ 'read', 'write', 'pipe' ]
    
    def __init__(self, name):
 
        self.functions = {}
        self.classes = {}
        self.kbObject = None
        self.name = name
             
        if name in ExternalLibrary.functionListByLibName:
            for funcName in ExternalLibrary.functionListByLibName[name]:
                self.functions[funcName] = None
        if name in ExternalLibrary.classListByLibName:
            for className, methods in ExternalLibrary.classListByLibName[name].items():
                self.classes[className] = {}
                for methodName in methods:
                    self.classes[className][methodName] = None
                
    def get_kb_function(self, name):
        if name in self.functions:
            return self.functions[name]
        return None

    def get_kb_method(self, className, methodName):
        if className in self.classes:
            cl = self.classes[className]
            if methodName in cl:
                return cl[methodName]
        return None
                    
    def create_objects(self, parent, parentFullname):

            lib = cast.analysers.CustomObject()
            self.kbObject = lib
            lib.set_name(self.name)
            lib.set_type('CAST_HTML5_JavaScript_SourceCode')
            lib.set_parent(parent)
            fullname = parentFullname + '.' + self.name
            lib.set_guid(fullname)
            lib.set_external()
            lib.set_fullname(fullname)
            lib.save()
             
            if self.name in ExternalLibrary.functionListByLibName:
                for funcName in ExternalLibrary.functionListByLibName[self.name]:
                    obj = cast.analysers.CustomObject()
                    obj.set_name(funcName)
                    obj.set_type('CAST_HTML5_JavaScript_Function')
                    obj.set_parent(lib)
                    fullname = 'NodeJS Standard library.' + self.name + '.' + funcName
                    obj.set_guid(fullname)
                    obj.set_external()
                    obj.set_fullname(fullname)
                    obj.save()
                    self.functions[funcName] = obj
             
            if self.name in ExternalLibrary.classListByLibName:
                for className, methods in ExternalLibrary.classListByLibName[self.name].items():
                    objClass = cast.analysers.CustomObject()
                    objClass.set_name(className)
                    objClass.set_type('CAST_HTML5_JavaScript_Class')
                    objClass.set_parent(lib)
                    fullname = 'NodeJS Standard library.' + self.name + '.' + className
                    objClass.set_guid(fullname)
                    objClass.set_external()
                    objClass.set_fullname(fullname)
                    objClass.save()
                    self.classes[className] = {}
                    
                    for methodName in methods:
                        obj = cast.analysers.CustomObject()
                        obj.set_name(methodName)
                        obj.set_type('CAST_HTML5_JavaScript_Method')
                        obj.set_parent(objClass)
                        fullname = 'NodeJS Standard library.' + self.name + '.' + className + '.' + methodName
                        obj.set_guid(fullname)
                        obj.set_external()
                        obj.set_fullname(fullname)
                        obj.save()
                        self.classes[className][methodName] = obj
        
class AstToken:

    def __init__(self, name, token):
        
        self.name = name
        self.token = token
        
    def get_code_only_crc(self):

        if self.token:        
            return self.token.get_code_only_crc()
        else:
            return 0
    
class Object:
    
    def __init__(self, name):
        self.kb_symbol = None
        self.ast = None
        self.name = name
        self.fullname = None

    def get_kb_object(self):
        return self.kb_symbol

    def get_code_only_crc(self):

        if self.ast:        
            return self.ast.get_code_only_crc()
        else:
            return 0

    def _get_code_only_crc(self):

        if self.ast:        
            return self.ast._get_code_only_crc()
        else:
            return 0
        
class Service(Object):
    """
    A nodeJS service.
    """

    def __init__(self, uri, _type, handler, ast):
        Object.__init__(self, None)
        self.type = _type
        self.uri = uri
        self.handler = handler
        self.ast = ast
        self.kbObject = None
        self.isRouter = False
        self.routerReference = None
        self.sourceCode = None
        self.inLoop = False
        self.koa_router = None
        self.koa_use = False
    
    def get_uri_evaluation(self):

        def uri_str_eva(uri):
            if uri == '/':
                return uri

            uris = uri.split('/')
            uri = None
            if uris:
                uri = ''
                for part in uris:
                    if part:
                        if part.startswith(':') or part.startswith('{'):
                            uri += '{}/'
                        else:
                            uri += (part + '/')

            return uri

        if not self.uri:
            return None
                 
        if isinstance(self.uri, str):
            uri = self.uri
        
        elif hasattr(self.uri, 'get_values'):
            '''
            * APLNJS-125: False violation -Avoid having multiple routes for the same path with Node.js
            '''
            res = []
            for ur in self.uri.get_values():
                if hasattr(ur, 'get_text'):
                    uri = uri_str_eva(ur.get_text())
                    if uri:
                        res.append(uri)
        
            return res

        else:
            uri = self.uri.evaluate(None, None, None, '****')
             
        if uri:
            if isinstance(uri, str):
                return uri_str_eva(uri)
            else:
                res = []
                for ur in uri:
                    uris = ur.split('/')
                    ur = None
                    if uris:
                        ur = ''
                        for part in uris:
                            if part:
                                if part.startswith(':'):
                                    ur += '{}/'
                                elif '?' in part:
                                    ur += part[:part.find('?')]
                                    if not ur.endswith('/'):
                                        ur += '/'
                                else:
                                    ur += ( part + '/' )
                        res.append(ur)
                if len(res) == 1:
                    return res[0]
                return res
    
    def __repr__(self):
        
        result = "nodejs.service(" + str(self.type) + ',' + str(self.uri) + ")"
        return result
        
class HttpRequest(Object):
    """
    A http.request
    """

    def __init__(self, uri, _type, caller, handler, ast):
        Object.__init__(self, None)
        self.type = _type
        self.uri = uri
        self.handler = handler
        self.ast = ast
        self.kbObject = None
        self.caller = caller
        self.onFunctions = []
    
    def get_uri_evaluation(self):
        return self.ast.get_uri_evaluation(self.uri, '{}', None)
    
    def __repr__(self):
        
        result = "nodejs.HttpRequest(" + self.type + ',' + self.uri + ")"
        return result

class MongooseConnection(Object):
    """
    A mongoose connection.
    """
    def __init__(self, url, ast, caller):
        Object.__init__(self, None)
        self.url = url
        self.ast = ast
        self.caller = caller
    
    def __repr__(self):
        
        result = "mongoose.connect(" + self.url + ")"
        return result

class MongooseModel(Object):
    """
    A mongoose model.
    """
    def __init__(self, name, fcallpartConnection, ast, caller, variableIdentifier, jsContent, callerIdentifier = None):
        Object.__init__(self, name)
        self.jsContent = jsContent
        self.fcallpartConnection = fcallpartConnection
        self.ast = ast
        self.caller = caller
        self.linkSuspensions = []
        self.variableIdentifier = variableIdentifier
        self.callerIdentifier = callerIdentifier    # if callerIdentifier.findById(...) and the model represented by callerIdentifier is in another file
#         self.modelInstances = []
    
    def __repr__(self):
        
        result = "mongoose.model(" + self.name + ")"
        return result

class DatabaseConnection(Object):
    """
    A database connection.
    """
    def __init__(self, name, ast, caller):
        Object.__init__(self, None)
        self.ast = ast
        self.caller = caller
        self.linkSuspensions = []
        self.user = None
        self.password = None
        self.connectString = None
    
    def __repr__(self):
        
        result = "dbConnection"
        return result

class MarklogicDatabase(Object):
    """
    A marklogic database.
    """
    def __init__(self, connectionParameter, ast, caller):
        Object.__init__(self, None)
        self.connectionParameter = None
        try:
            if connectionParameter.resolutions:
                self.connectionParameter = connectionParameter.resolutions[0].callee
        except:
            pass
        if not self.connectionParameter:
            self.connectionParameter = connectionParameter
        if connectionParameter.is_object_value():
            try:
                host = connectionParameter.get_item('host')
                port = connectionParameter.get_item('port')
                if host:
                    if port:
                        self.name = host.get_name() + ':' + port.get_name()
                    else:
                        self.name = host.get_name()
                else:
                    self.name = 'NONAME'
                self.fullname = self.name
            except:
                self.name = 'NONAME'
                self.fullname = self.name
        else:
            self.name = connectionParameter.get_name()
            self.fullname = connectionParameter.get_fullname()
        self.ast = ast
        self.caller = caller
        self.collections = OrderedDict()
        self.collectionsByName = OrderedDict()
        self.linksToCollections = []    # list of LinkSuspension
        self.referencedDatabase = None
    
    def add_collection(self, name, kbObject = None):
        self.collections[name] = kbObject
    
    def add_collection_by_name(self, name, kbObject = None):
        self.collectionsByName[name] = kbObject
    
    def set_collection_kb_object(self, name, kbObject):
        if name in self.collections:
            self.collections[name] = kbObject
            
    def add_link_to_collection(self, linkType, caller, collectionName, callPart):
        self.linksToCollections.append(LinkSuspension(linkType, caller, collectionName, callPart))
             
    def __repr__(self):
        
        result = "marklogic.createDatabaseClient(" + ")"
        return result

class CouchDBDatabase(Object):
    """
    A CouchDB database.
    """
    def __init__(self, name, ast, caller):
        Object.__init__(self, name)
        self.ast = ast
        self.caller = caller
        self.linksToDatabase = []    # list of LinkSuspension
    
    def add_link_to_database(self, linkType, caller, callPart):
        self.linksToDatabase.append(LinkSuspension(linkType, caller, self, callPart))
             
    def __repr__(self):
        
        result = "couch.createDatabase(" + self.name + ")"
        return result

class CouchDBCall():
    
    def __init__(self, variableName, linkType, caller, ast):
        self.variableName = variableName
        self.linkType = linkType
        self.caller = caller
        self.ast = ast
        
class SymbolLink:
    
    def __init__(self, type = None, caller = None, callee = None, bookmark = None):
        
        self.type = type
        self.caller = caller
        self.callee = callee
        self.bookmark = bookmark

class Violation:
    
    def __init__(self, metamodelProperty, bookmark, function, bookmarks = None):
        self.metamodelProperty = metamodelProperty
        self.bookmark = bookmark
        self.function = function
        self.additionalBookmarks = bookmarks
        
class Violations:
    
    def __init__(self):
        
        self.violations = []

    def add_violation(self, metamodelProperty, bookmark, function, bookmarks = None):
        self.violations.append(Violation(metamodelProperty, bookmark, function, bookmarks))
        
    def add_lack_of_error_handling_violation(self, function, bookmark):
        self.add_violation('CAST_NodeJS_Metric_AvoidLackErrorHandlingInCallbacks.numberOfCallbacksWithoutErrorHandling', bookmark, function)
        
    def add_process_exit_violation(self, function, bookmark):
        self.add_violation('CAST_NodeJS_Metric_AvoidUsingProcessExit.numberOfProcessExitCalls', bookmark, function)
        
    def add_string_concat_with_filename_dirname_violation(self, function, bookmark):
        self.add_violation('CAST_NodeJS_Metric_AvoidUsingStringConcatWithDirnameOrFilename.numberOfStringConcatWithDirnameOrFilename', bookmark, function)
        
    def add_non_activated_content_security_policy_violation(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_EnsureContentSecurityPolicyActivation.numberOfNonActivatedContentSecurityPolicy', bookmark, obj)
        
    def add_missing_nocache_violation(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_EnsureBrowserCanNotCachePage.numberOfMissingNoCache', bookmark, obj)
        
    def add_missing_https_communication(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_AllowOnlyHTTPSCommunication.numberOfNoHTTPSCommunication', bookmark, obj)
        
    def add_missing_https_protocol(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_UseSecureHTTPSProtocol.numberOfNoHTTPSProtocol', bookmark, obj)
        
    def add_missing_csrf_protection(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_CSRFProtectionEnabled.numberOfNoCSRFProtection', bookmark, obj)
        
    def add_no_sanitized_marked(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_MarkedIsSanitized.numberOfNoSanitizedMarked', bookmark, obj)

    def add_non_disabled_x_powered_by_header_violation(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_EnsureXPoweredByHeaderDisabled.numberOfXPoweredByHeaderNotDisabled', bookmark, obj)
        
    def add_non_enabled_x_xss_protection_header_violation(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_EnsureXXSSProtectionHeaderEnabled.numberOfXXSSProtectionHeaderNotEnabled', bookmark, obj)
        
    def add_x_frame_options_header_not_setup_violation(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_EnsureXFrameOptionsHeaderSetup.numberOfXFrameOptionsHeaderNotSetup', bookmark, obj)
        
    def add_multiple_routes_for_same_path_violation(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_MultipleRoutesForSamePath.numberOfMultipleRoutesForSamePath', bookmark, obj)
        
    def add_http_get_or_request_inside_loop_violation(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_httpGetOrRequestInsideLoop.numberOfHttpGetOrRequestInsideLoop', bookmark, obj)
        
    def add_cookie_no_httpOnly_option(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_CookieWithoutHTTPOnly.numberOfCookieWithoutHTTPOnly', bookmark, obj)
        
    def add_unclosed_filesystem(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_UnclosedFileSystem.numberOfUnclosedFileSystem', bookmark, obj)
        
    def add_risky_cryptographic_hash(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_AvoidUsingRiskyCryptographicHash.numberOfRiskyCryptographicHash', bookmark, obj)
        
    def add_unsecured_cookie(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_UnsecuredCookie.numberOfUnsecuredCookie', bookmark, obj)
        
    def add_NODE_TLS_REJECT_UNAUTHORIZED_violation(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_BypassSelfSignedSSLCertificate.numberOfBypassSelfSignedSSLCertificate', bookmark, obj)
        
    def add_disable_ssl_verification_node_curl_violation(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_AvoidDisablingSSLVerificationInNodeCurl.numberOfDisablingSSLVerificationInNodeCurl', bookmark, obj)
        
    def add_cookie_overly_broad_path(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_AvoidCookieWithOverlyBroadPath.numberOfCookieWithOverlyBroadPath', bookmark, obj)
        
    def add_cookie_overly_broad_domain(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_AvoidCookieWithOverlyBroadDomain.numberOfCookieWithOverlyBroadDomain', bookmark, obj)
        
    def add_avoid_using_tls_on_old_node_versions_violation(self, obj, bookmark, additionalBookmarks):
        self.add_violation('CAST_NodeJS_Metric_AvoidUsingTlsBeforeNodeVersions.numberOfTlsUsagesBeforeNodeVersions', bookmark, obj, additionalBookmarks)
        
    def add_avoid_using_http2_on_old_node_versions_violation(self, obj, bookmark, additionalBookmarks):
        self.add_violation('CAST_NodeJS_Metric_AvoidUsingHttp2BeforeNodeVersions.numberOfHttp2UsagesBeforeNodeVersions', bookmark, obj, additionalBookmarks)

    def add_avoid_using_path_on_old_node_versions_violation(self, obj, bookmark, additionalBookmarks):
        self.add_violation('CAST_NodeJS_Metric_AvoidUsingTheFilePathValidationBeforeNodeVersions.numberOfPathUsagesBeforeNodeVersions', bookmark, obj, additionalBookmarks)

    def add_avoid_using_the_call_of_data_service_with_Nodejs_inside_a_loop(self, obj, bookmark):
        self.add_violation('CAST_NodeJS_Metric_AvoidUsingTheCallOfDataServiceWithNodeJSInsideALoop.numberOfUsingTheCallOfDataServiceWithNodeJSInsideALoop', bookmark, obj)

    def save(self):
        
        for violation in self.violations:
            try:
                if violation.additionalBookmarks:
                    violation.function.get_kb_object().save_violation(violation.metamodelProperty, violation.bookmark, violation.additionalBookmarks)
                else:
                    violation.function.get_kb_object().save_violation(violation.metamodelProperty, violation.bookmark)
            except:
                log.debug('Internal issue ' + str(traceback.format_exc()))
            
class PotentialController:
    
    def __init__(self, cl, file):
        self.cl = cl
        self.file = file
        self.kbObject = None
        
class LoopbackApplication:

        class Database:
            
            def __init__(self, name = '', connector = ''):
                self.name = name
                self.connector = connector
                
        def __init__(self, serverRootPath):

            self.serverFile = None
            self.serverRootPath = serverRootPath
            self.restApiRoot = '/api'
            self.databases = {}
            self.modelRootPathes = []
            self.models = {}
            self.jsonModelFiles = []
            self.kbObject = None
            self.databases_connector = []

            '''
            * Info of loopback server will be found with app = loopback()
            '''

            jsonConfigFilename = os.path.join(serverRootPath, 'config.json')
            if os.path.exists(jsonConfigFilename):
                config = json.loads(nodejs_open_source_file(jsonConfigFilename))
                if 'restApiRoot' in config:
                    self.restApiRoot = config['restApiRoot']
                    if not self.restApiRoot.startswith('/'):
                        self.restApiRoot = '/' + self.restApiRoot
                    if self.restApiRoot.endswith('/'):
                        self.restApiRoot = self.restApiRoot[:-1]

            jsonDatasourcesFilename = os.path.join(serverRootPath, 'datasources.json')
            if os.path.exists(jsonDatasourcesFilename):
                datasources = json.loads(nodejs_open_source_file(jsonDatasourcesFilename))
                try:
                    for dbRoots in datasources.values():
                        if type(dbRoots) is list:
                            for dbRoot in dbRoots:
                                if 'name' in dbRoot:
                                    db = self.Database(dbRoot['name'])
                                    self.databases[db.name] = db
                                    if 'connector' in dbRoot:
                                        db.connector = dbRoot['connector']
                                        if db.connector not in self.databases_connector:
                                            self.databases_connector.append(db.connector)

                        else:
                            if 'name' in dbRoots:
                                db = self.Database(dbRoots['name'])
                                self.databases[db.name] = db
                                if 'connector' in dbRoots:
                                    db.connector = dbRoots['connector']
                                    if db.connector not in self.databases_connector:
                                        self.databases_connector.append(db.connector)

                except:
                    log.warning('internal issue from datasource.json of loopback app')

            jsonModelConfigFilename = os.path.join(serverRootPath, 'model-config.json')
            if os.path.exists(jsonModelConfigFilename):
                modelConfig = json.loads(nodejs_open_source_file(jsonModelConfigFilename))
                for key, value in modelConfig.items():
                    if key == '_meta' and 'sources' in value:
                        for source in value['sources']:
                            self.modelRootPathes.append(os.path.normpath(os.path.join(serverRootPath, source)))

                    elif 'dataSource' in value and value['dataSource'] in self.databases:
                        self.models[key] = {}
                        self.models[key]['name'] = key
                        self.models[key]['database'] = self.databases[value['dataSource']]
        
        def get_kb_object(self):
            return self.kbObject
