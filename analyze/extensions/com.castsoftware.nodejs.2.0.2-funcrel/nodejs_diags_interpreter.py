from cast.analysers import log
import re
import traceback
from semver import rtr, ltr, valid_range, eq, valid


def statement_uses_identifier(statement, strIdentifier):
    if statement.is_identifier():
        if statement.get_name() == strIdentifier or statement.get_fullname().startswith(strIdentifier + '.'):
            return True
        else:
            return False
    for child in statement.get_children():
        if not child:
            continue
        if child.is_function():
            continue
        usesIdentifier = statement_uses_identifier(child, strIdentifier)
        if usesIdentifier:
            return True
    return False

def is_identifier(identifier):
    try:
        return identifier.is_identifier()
    except:
        return False
        
def is_string(_str):
    try:
        return _str.is_string()
    except:
        return False
      
def init_context(context):
    context.openFiles = []
    context.openSyncFiles = []
     
class NodeJSDiagsInterpreter:
        
    def __init__(self, violations, file, nodejsInterpreter):

        self.file = file
        self.nodejsInterpreter = nodejsInterpreter
        self.contextsStack = []
        self.push_context(nodejsInterpreter.current_context)
        self.violations = violations
        self.config = nodejsInterpreter.config
        self.jsContent = None
        self.contentSecurityPolicy = False
        self.noCache = False
        self.https = False
        self.XPoweredBy = False
        self.XXSProtection = False
        self.XFrameOptions = False
        self.useExpress = False
        self.useNodeCurl = False
        self.useTls = False
        self.useExpressSession = False
        self.useFs = False
        self.useMarked = False
        self.useExpressRouter = False
        self.useWebsocketIo = False
        self.useHttp = False
        self.useHttp2 = False
        self.usePath = False
        self.useCrypto = False
        self.useHttps = False
        self.useHelmet = False
        self.useHidePoweredBy = False
        self.useXXSSProtection = False
        self.useXFrameOptions = False
        self.useNoCache = False
        self.useCSRF = False
        self.markedSanitized = False
        self.isApp = False
        
    @staticmethod
    def is_version_compatible_with_tls_internal(version):
        """
        * Verision not compatible : <=9.11.1 or 10.0.0 <= v < 10.4.1.
        * https://devhints.io/semver. Explain version:
            ~1.2.3    is >=1.2.3 <1.3.0     
            ^1.2.3    is >=1.2.3 <2.0.0     
            ^0.2.3    is >=0.2.3 <0.3.0    (0.x.x is special)
            ^0.0.1    is =0.0.1    (0.0.x is special)
            ^1.2    is >=1.2.0 <2.0.0    (like ^1.2.0)
            ~1.2    is >=1.2.0 <1.3.0    (like ~1.2.0)
            ^1    is >=1.0.0 <2.0.0     
            ~1    same     
            1.x    same     
            1.*    same     
            1    same     
            *    any version     
            x    same
        """
        try:
            range_v = valid_range(version, True)
            # max(rang_v) < 9.11.2
            cond_1 = rtr('9.11.2', range_v, True)
            # min(rang_v) >= 10.0.0 and max(rang_v) < 10.4.1
            cond_2 = ltr('9.99.99', range_v, True) and rtr('10.4.1', range_v, True)
    
            return not (cond_1 or cond_2)
        except:

            return True
        
    @staticmethod
    def is_version_compatible_with_http2_internal(version):
         
        try:
            range_v = valid_range(version, True)
            # max(rang_v) < 8.11.3
            cond_1 = rtr('8.11.3', range_v, True)
            # min(rang_v) >= 9.0.0 and max(rang_v) < 9.11.2
            cond_2 = ltr('8.99.99', range_v, True) and rtr('9.11.2', range_v, True)
            # min(rang_v) >= 10.0.0 and max(rang_v) < 10.4.1
            cond_3 = ltr('9.99.99', range_v, True) and rtr('10.4.1', range_v, True)

            return not (cond_1 or cond_2 or cond_3)
        except:

            return True

    @staticmethod
    def is_version_compatible_with_path_internal(version):

        try:
            range_v = valid_range(version, True)
            if valid(range_v, True):
                return not eq(range_v, '8.5.0')
            else:
                return True

        except:

            return True

    def is_version_compatible_with(self, positions, name):
        versions = self.nodejsInterpreter.versions
        ret = True

        if not versions:
            return ret

        for v in versions:
            try:
                if name == 'tls':
                    ret = self.is_version_compatible_with_tls_internal(v['version'])
                
                elif name == 'http2':
                    ret = self.is_version_compatible_with_http2_internal(v['version'])
                
                elif name == 'path':
                    ret = self.is_version_compatible_with_path_internal(v['version'])   
                
            except:
                log.info('Unsupported nodejs version : ' + v['version'] + ' in file ' + v['position'].get_file().get_path())
                log.debug(traceback.format_exc())
                ret = True
            if not ret:
                positions.append(v['position'])
                break

        return ret

    def violation_with_version(self, firstCallPartIdentifierCall, name_require):
        requireDeclaration = self.nodejsInterpreter.get_require_declaration(firstCallPartIdentifierCall)

        if requireDeclaration and requireDeclaration.reference == name_require:
            positions = []
            if not self.is_version_compatible_with(positions, name_require):
                return positions

        return None

    def is_application(self):
        return self.isApp
     
    def start_source_code(self, jsContent):
        self.jsContent = jsContent
        
    def get_current_function(self):
        return self.nodejsInterpreter.get_current_kb_function()
    
    def push_context(self, context):
        self.contextsStack.append(context)
        init_context(context)
    
    def pop_context(self):
        try:
            context = self.contextsStack[-1]
        except:
            return
        
        if context.openFiles:
            self.violations.add_unclosed_filesystem(self.jsContent, context.openFiles[-1].create_bookmark(self.file))
        if context.openSyncFiles:
            self.violations.add_unclosed_filesystem(self.jsContent, context.openSyncFiles[-1].create_bookmark(self.file))
        self.contextsStack.pop()

    def start_function(self, function, context):
        self.exit_code_process_exit = False
        self.push_context(context)
        
        if not function.get_kb_symbol() or not function.kbObject:  # get_kb_symbol and kbObject => continue
            return

        function.kbObject.save_property('CAST_NodeJS_Metrics_Category.isnodejs', 1)
        parameters = function.get_parameters()

        if not parameters:
            return

        firstParam = parameters[0]
        try:
            if firstParam.is_identifier() and re.match(self.config['handle-callback-err'], firstParam.get_name()):
                firstErrParameter = firstParam.get_name()
                if not statement_uses_identifier(function, firstErrParameter):
                    self.violations.add_lack_of_error_handling_violation(function, function.create_bookmark(self.file))
        except:
            pass
    
    def end_function(self):
        self.pop_context()

    def start_function_call(self, fcall):
        
        callParts = fcall.get_function_call_parts()
        firstCallPart = True
        firstCallPartIdentifierCall = None
        loopDepth = self.nodejsInterpreter.loopDepth

        for callPart in callParts:
            
            if firstCallPart:

                firstCallPartIdentifierCall = callPart.identifier_call
                requireDeclaration = self.nodejsInterpreter.get_require_declaration(firstCallPartIdentifierCall)

                if self.useExpress:
                    if firstCallPartIdentifierCall.get_name() == 'express':
                        self.isApp = True

                    else:
                        # 'express' in this case is just a name convention.
                        params = callPart.get_parameters()
                        direct_call = firstCallPartIdentifierCall.get_name() == 'require' and len(params) == 1 and params[0].get_text() == 'express'
                        assigment_pr = fcall.parent

                        if direct_call and assigment_pr.is_assignment():
                            left_opr = assigment_pr.get_left_operand()

                            if left_opr.is_identifier() and left_opr.get_text() in ['app', 'server']:
                                self.isApp = True

                elif self.useWebsocketIo and firstCallPartIdentifierCall.get_name() == 'listen':
                    self.isApp = True

                if loopDepth > 0 and firstCallPartIdentifierCall.get_prefix_internal():
                    callName = firstCallPartIdentifierCall.get_name()
                    if callName in ['get', 'request']:
                        if firstCallPartIdentifierCall.get_resolutions():
                            for resol in firstCallPartIdentifierCall.get_resolutions():
                                try:
                                    if resol.callee.get_name() in self.nodejsInterpreter.require_declarations and self.nodejsInterpreter.require_declarations[resol.callee.get_name()].reference in ['http', 'https']:
                                        self.violations.add_http_get_or_request_inside_loop_violation(self.jsContent, callPart.create_bookmark(self.file))
                                except:
                                    pass
    
            if firstCallPartIdentifierCall.get_prefix_internal() or not firstCallPart:
    
                callName = firstCallPartIdentifierCall.get_name()
                
                if callName == 'exit' and firstCallPartIdentifierCall.get_prefix_internal() == 'process':
                    f = self.get_current_function()

                    if f and not self.exit_code_process_exit:
                        self.violations.add_process_exit_violation(f, callPart.create_bookmark(self.file))

                elif callName in ['header', 'disable']:
                    if callPart.get_parameters():
                        firstParam = callPart.get_parameters()[0]
                        try:
                            evals = firstParam.evaluate()
                            for ev in evals:

                                if callName == 'header' and ev == 'Content-Security-Policy':
                                    self.contentSecurityPolicy = True
                                    break

                                elif callName == 'disable' and ev == 'x-powered-by':
                                    self.XPoweredBy = True
                                    break
                        except:
                            pass

                elif callName == 'csp':
                    if self.useHelmet:
                        self.contentSecurityPolicy = True

                elif callName in ['frameguard', 'noCache', 'hsts']:

                    if self.useHelmet and requireDeclaration and requireDeclaration.reference == 'helmet':

                        if callName == 'frameguard':
                            self.XFrameOptions = True

                        elif callName == 'noCache':

                            self.noCache = True
                        elif callName == 'hsts':

                            self.https = True

                elif callName == 'setOptions':
                    if self.useExpress and self.useMarked:
                        if requireDeclaration and requireDeclaration.reference == 'marked':
                            params = callPart.get_parameters()
                            if len(params) > 0:
                                param = params[0]
                                try:
                                    if param.is_object_value():
                                        sanitize = param.get_item('sanitize')
                                        if sanitize:
                                            if sanitize.get_name() == 'true':
                                                self.markedSanitized = True
                                    elif param.resolutions:
                                        callee = param.resolutions[0].callee
                                        if callee.parent.is_assignment():
                                            rightOper = callee.parent.get_right_operand()
                                            if rightOper.is_object_value():
                                                sanitize = rightOper.get_item('sanitize')
                                                if sanitize:
                                                    if sanitize.get_name() == 'true':
                                                        self.markedSanitized = True
                                except:
                                    pass

                elif firstCallPart and callName == 'createServer':
                    if (self.useHttps or self.useHttp) and requireDeclaration:
                        if requireDeclaration.reference == 'http':
                            self.violations.add_missing_https_protocol(self.jsContent, callPart.create_bookmark(self.file))

                        if requireDeclaration.reference in ['http', 'https']:
                            self.jsContent.get_kb_object().save_property('CAST_NodeJS_UseHTTPCreateServer.numberOfHTTPCreateServer', 1)

                elif firstCallPart and callName == 'check':
                    prefix = firstCallPartIdentifierCall.get_prefix_internal()

                    if prefix and prefix in self.nodejsInterpreter.require_declarations and self.nodejsInterpreter.require_declarations[prefix].reference == 'express-csrf':
                        self.useCSRF = True
                            
                elif callName in ['open', 'openSync'] and firstCallPartIdentifierCall.get_prefix_internal():
                    if requireDeclaration and requireDeclaration.reference == 'fs':
                        self.register_open_file(callPart, callName == 'openSync')

                elif callName in ['close', 'closeSync'] and firstCallPartIdentifierCall.get_prefix_internal():
                    if requireDeclaration and requireDeclaration.reference == 'fs':
                        self.register_closeFile(callPart, callName == 'closeSync')

                elif firstCallPart and callName == 'createHash':
                    if self.useCrypto and requireDeclaration and requireDeclaration.reference == 'crypto':
                        self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useCreateHash', 1)
                        params = callPart.get_parameters()
                        if params:
                            firstParam = params[0]
                            evs = firstParam.evaluate()
                            if evs:
                                for ev in evs:
                                    if ev.lower() not in ['md5', 'sha1']:
                                        continue

                                    self.violations.add_risky_cryptographic_hash(self.jsContent, callPart.create_bookmark(self.file))

                elif callName == 'createSecureContext' and self.useTls:
                    positions = self.violation_with_version(firstCallPartIdentifierCall, 'tls')
                    if positions:
                        self.violations.add_avoid_using_tls_on_old_node_versions_violation(self.jsContent, callPart.create_bookmark(self.file), positions)

                elif callName == 'connect' and self.useHttp2:
                    positions = self.violation_with_version(firstCallPartIdentifierCall, 'http2')
                    if positions:
                        self.violations.add_avoid_using_http2_on_old_node_versions_violation(self.jsContent, callPart.create_bookmark(self.file), positions)
                
                elif callName == 'normalizeStringWin32' and self.usePath:
                    positions = self.violation_with_version(firstCallPartIdentifierCall, 'path')
                    if positions:
                        self.violations.add_avoid_using_path_on_old_node_versions_violation(self.jsContent, callPart.create_bookmark(self.file), positions)

            if not firstCallPartIdentifierCall.get_prefix_internal():
                callName = firstCallPartIdentifierCall.get_name()
                if callName == 'helmet' and self.useHelmet:
                    if requireDeclaration and requireDeclaration.reference == 'helmet':
                        self.XXSProtection = True
                        self.XFrameOptions = True

                elif callName == 'csrf':
                    self.useCSRF = True
                else:
                    if self.useNoCache:
                        if requireDeclaration and requireDeclaration.reference == 'nocache':
                            self.noCache = True
                    if self.useNodeCurl:
                        requireDeclaration = self.nodejsInterpreter.get_require_declaration(firstCallPartIdentifierCall)
                        if requireDeclaration and requireDeclaration.reference == 'node-curl':
                            params = callPart.get_parameters()
                            if len(params) >= 3:
                                param2 = params[1]
                                if param2.is_object_value():
                                    item = param2.get_item('SSL_VERIFYPEER')
                                    if item:
                                        try:
                                            if item.get_name() == '0':
                                                self.violations.add_disable_ssl_verification_node_curl_violation(self.jsContent, callPart.create_bookmark(self.file))
                                        except:
                                            pass
                    if firstCallPartIdentifierCall.get_resolutions():
                        for resol in firstCallPartIdentifierCall.get_resolutions():
                            try:
                                if resol.callee.get_name() in self.nodejsInterpreter.require_declarations and self.nodejsInterpreter.require_declarations[resol.callee.get_name()].reference == 'csurf':
                                    self.useCSRF = True
                            except:
                                pass
                    if self.useExpressSession:
                        self.start_function_call_cookie(callPart)
                
            if self.useHidePoweredBy or self.useXXSSProtection:

                if requireDeclaration:
                    if requireDeclaration.reference == 'hide-powered-by':
                        self.XPoweredBy = True
                    elif requireDeclaration.reference == 'x-xss-protection':
                        self.XXSProtection = True
            
            firstCallPart = False

    def start_function_call_cookie(self, callPart):
                        
        requireDeclaration = self.nodejsInterpreter.get_require_declaration(callPart.identifier_call)
        if requireDeclaration and requireDeclaration.reference == 'express-session':
            params = callPart.get_parameters()
            if len(params) > 0:
                param = params[0]
                try:
                    if param.is_object_value():
                        cookie = param.get_item('cookie')
                        if not cookie:
                            self.violations.add_cookie_no_httpOnly_option(self.jsContent, callPart.create_bookmark(self.file))
                            self.violations.add_unsecured_cookie(self.jsContent, callPart.create_bookmark(self.file))
                        elif not cookie.is_object_value():
                            self.violations.add_cookie_no_httpOnly_option(self.jsContent, callPart.create_bookmark(self.file))
                            self.violations.add_unsecured_cookie(self.jsContent, callPart.create_bookmark(self.file))
                        else:
                            httpOnly = cookie.get_item('httpOnly')
                            if not httpOnly or not httpOnly.get_name() == 'true':
                                self.violations.add_cookie_no_httpOnly_option(self.jsContent, callPart.create_bookmark(self.file))
                            secure = cookie.get_item('secure')
                            if not secure or not secure.get_name() == 'true':
                                self.violations.add_unsecured_cookie(self.jsContent, callPart.create_bookmark(self.file))
                            path = cookie.get_item('path')
                            if path and path.get_name() == '/':
                                self.violations.add_cookie_overly_broad_path(self.jsContent, callPart.create_bookmark(self.file))
                            domain = cookie.get_item('domain')
                            if domain and domain.get_name().startswith('.'):
                                self.violations.add_cookie_overly_broad_domain(self.jsContent, callPart.create_bookmark(self.file))
                    elif param.resolutions:
                        callee = param.resolutions[0].callee
                        if callee.parent.is_assignment():
                            rightOper = callee.parent.get_right_operand()
                            if rightOper.is_object_value():
                                cookie = rightOper.get_item('cookie')
                                if not cookie:
                                    self.violations.add_cookie_no_httpOnly_option(self.jsContent, callPart.create_bookmark(self.file))
                                    self.violations.add_unsecured_cookie(self.jsContent, callPart.create_bookmark(self.file))
                                elif not cookie.is_object_value():
                                    self.violations.add_cookie_no_httpOnly_option(self.jsContent, callPart.create_bookmark(self.file))
                                    self.violations.add_unsecured_cookie(self.jsContent, callPart.create_bookmark(self.file))
                                else:
                                    httpOnly = cookie.get_item('httpOnly')
                                    if not httpOnly or not httpOnly.get_name() == 'true':
                                        self.violations.add_cookie_no_httpOnly_option(self.jsContent, callPart.create_bookmark(self.file))
                                    secure = cookie.get_item('secure')
                                    if not secure or not secure.get_name() == 'true':
                                        self.violations.add_unsecured_cookie(self.jsContent, callPart.create_bookmark(self.file))
                                    path = cookie.get_item('path')
                                    if path and path.get_name() == '/':
                                        self.violations.add_cookie_overly_broad_path(self.jsContent, callPart.create_bookmark(self.file))
                                    domain = cookie.get_item('domain')
                                    if domain and domain.get_name().startswith('.'):
                                        self.violations.add_cookie_overly_broad_domain(self.jsContent, callPart.create_bookmark(self.file))
                except:
                    pass
    
    def register_open_file(self, callPart, sync = False):
        if sync:
            self.contextsStack[-1].openSyncFiles.append(callPart)
        else:
            self.contextsStack[-1].openFiles.append(callPart)
    
    def register_closeFile(self, callPart, sync = False):
        context = self.contextsStack[-1]
        if sync:
            try:
                param1 = callPart.get_parameters()[0]
                calleeName = param1.resolutions.callee.get_name()
            except:
                param1 = None
            try:
                if len(context.openSyncFiles) == 1:
                    context.openSyncFiles.pop()
                else:
                    for openSyncFile in context.openSyncFiles:
                        try:
                            assignment = openSyncFile.parent.parent
                            if assignment.get_left_operand().get_name() == calleeName:
                                context.openSyncFiles.remove(openSyncFile)
                                break
                        except:
                            pass
            except:
                pass
        else:
            while not context.openFiles:
                context = context.parent
                if not context:
                    break
            if context:
                context.openFiles.pop()
                  
    def start_require(self, name, bSimple = True):
        if name == 'express':
            if bSimple:
                self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useExpress', 1)
                self.useExpress = True
        elif name == 'websocket.io':
            self.useWebsocketIo = True
        elif name == 'marked':
            if bSimple:
                self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useMarked', 1)
                self.useMarked = True
        elif name == 'http':
            self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useHttp', 1)
            self.useHttp = True
        elif name == 'https':
            self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useHttp', 1)
            self.useHttps = True
        elif name == 'http2':
            self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useHttp', 1)
            self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useHttp2', 1)
            self.useHttp2 = True
        elif name == 'helmet':
            self.useHelmet = True
        elif name == 'hide-powered-by':
            self.useHidePoweredBy = True
        elif name == 'x-xss-protection':
            self.useXXSSProtection = True
        elif name == 'nocache':
            self.useNoCache = True
        elif name == 'express-session':
            if bSimple:
                self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useExpressSession', 1)
                self.useExpressSession = True
        elif name == 'fs':
            if bSimple:
                self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useFs', 1)
                self.useFs = True
        elif name == 'crypto':
            self.useCrypto = True
        elif name == 'node-curl':
            self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useNodeCurl', 1)
            self.useNodeCurl = True
        elif name == 'tls':
            self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.useTls', 1)
            self.useTls = True
        elif name == 'path':
            self.jsContent.get_kb_object().save_property('CAST_HTML5_JavaScript_SourceCode.usePath', 1)
            self.usePath = True

    def finalize(self):
        if self.useExpress and self.isApp:
            if not self.contentSecurityPolicy:
                self.violations.add_non_activated_content_security_policy_violation(self.jsContent, self.jsContent.objectDatabaseProperties.bookmarks[0])
            if not self.noCache:
                self.violations.add_missing_nocache_violation(self.jsContent, self.jsContent.objectDatabaseProperties.bookmarks[0])
            if not self.https:
                self.violations.add_missing_https_communication(self.jsContent, self.jsContent.objectDatabaseProperties.bookmarks[0])
            if not self.XPoweredBy:
                self.violations.add_non_disabled_x_powered_by_header_violation(self.jsContent, self.jsContent.objectDatabaseProperties.bookmarks[0])
            if not self.XXSProtection:
                self.violations.add_non_enabled_x_xss_protection_header_violation(self.jsContent, self.jsContent.objectDatabaseProperties.bookmarks[0])
            if not self.XFrameOptions:
                self.violations.add_x_frame_options_header_not_setup_violation(self.jsContent, self.jsContent.objectDatabaseProperties.bookmarks[0])
            if self.useMarked and not self.markedSanitized:
                self.violations.add_no_sanitized_marked(self.jsContent, self.jsContent.objectDatabaseProperties.bookmarks[0])
            if not self.useCSRF:
                self.violations.add_missing_csrf_protection(self.jsContent, self.jsContent.objectDatabaseProperties.bookmarks[0])
                
        if self.nodejsInterpreter.require_declarations:
            self.jsContent.get_kb_object().save_property('CAST_NodeJS_Metrics_Category.isnodejs', 1)
                
        self.pop_context()
        
    def start_addition_expression(self, expression):
        
        left_operand = expression.get_left_operand()
        if left_operand:
            if is_identifier(left_operand) and left_operand.get_name() in [ '__dirname', '__filename' ]:
                f = self.get_current_function()
                if f:
                    self.violations.add_string_concat_with_filename_dirname_violation(f, left_operand.create_bookmark(self.file))
                return
        right_operand = expression.get_right_operand()
        if right_operand:
            if is_identifier(right_operand) and right_operand.get_name() in [ '__dirname', '__filename' ]:
                f = self.get_current_function()
                if f:
                    self.violations.add_string_concat_with_filename_dirname_violation(f, right_operand.create_bookmark(self.file))
                    
    def start_assignment(self, assign):
        
        leftOper = assign.get_left_operand()

        if not is_identifier(leftOper):
            return

        if leftOper.get_text() == 'process.exitCode':
            rightOper = assign.get_right_operand()

            if hasattr(rightOper, 'get_text') and rightOper.get_text() == '1':
                self.exit_code_process_exit = True

        elif leftOper.get_name().endswith('NODE_TLS_REJECT_UNAUTHORIZED'):
            rightOper = assign.get_right_operand()

            if is_string(rightOper) and rightOper.get_name() == '0':
                self.violations.add_NODE_TLS_REJECT_UNAUTHORIZED_violation(self.jsContent, assign.create_bookmark(self.file))
