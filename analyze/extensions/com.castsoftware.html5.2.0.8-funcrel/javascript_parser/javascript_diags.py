from javascript_parser.symbols import JSFunctionCall
import re
import cast.analysers.ua
import traceback
    
class ViolationSuspension:
    def __init__(self, artifact, ast):
        self.artifact = artifact
        self.ast = ast

class Html5Diag:
    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.file = interpreter.file
        self.violations = interpreter.violations
        
    def get_current_function(self):
        return self.interpreter.get_current_function()
    
    def get_current_context(self):
        return self.interpreter.get_current_context()

    def pop_context(self, context):
        return

    def start_function(self, ast):
        return

    def end_function(self, context):
        return
    
    def end_js_content(self):
        return

    def start_function_call_part(self, identifier, functionCallPart):
        return

    def end_class(self):
        return

    def start_function_call(self, fcall):
        return
        
    def start_assignment(self, assignment):
        return

    def start_object_value(self, ov):
        return
    
    def start_binary_expression(self, expr):
        return
    
    def start_string(self, s):
        return
    
    def end_any_statement(self, statement):
        return

    def start_try_catch_block(self, block):
        return

    def end_switch_block(self, switchBlock):
        return
    
    def start_identifier(self, identifier, n):
        return

    def end_any_expression(self, statement):
        return
    
    def end_delete_statement(self, statement):
        return
    
    def end_loop(self):
        return

class QuerySelectorAllDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def start_function_call_part(self, identifier, functionCallPart):
        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name == 'querySelectorAll':
                    f = self.get_current_function()
                    if f:
                        self.violations.add_querySelectorAll_violation(f, functionCallPart.create_bookmark(self.file))

class JsonParseStringifyWithoutTryCatchDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def start_function_call_part(self, identifier, functionCallPart):
        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name in ['parse', 'stringify'] and identifier.prefix and identifier.prefix == 'JSON':
                    f = self.get_current_function()
                    if f:
                        kbFunc = f.get_kb_object()
                        if kbFunc:
                            kbFunc.save_property('CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsJSONParseOrStringify', 1)
                    else:
                        kbFunc = self.interpreter.currentContext.statement.get_kb_object()
                        if kbFunc:
                            kbFunc.save_property('CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsJSONParseOrStringify', 1)
                    try:
                        if f and not self.interpreter.currentContext.is_in_try_catch_in_current_function():
                            self.violations.add_json_parse_stringify_without_try_catch_violation(f, functionCallPart.create_bookmark(self.file))
                    except:
                        cast.analysers.log.debug(str(traceback.format_exc()))

class ConsoleLogDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def start_function_call_part(self, identifier, functionCallPart):
        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name == 'log' and identifier.prefix == 'console':
                    f = self.get_current_function()
                    if f:
                        self.violations.add_console_log_violation(f, functionCallPart.create_bookmark(self.file))

class DatabaseDirectAccessDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def start_function_call_part(self, identifier, functionCallPart):
        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name == 'executeSql':
                    f = self.get_current_function()
                    if f:
                        self.violations.add_database_direct_access_violation(f, functionCallPart.create_bookmark(self.file))

class ForEachDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def start_function_call_part(self, identifier, functionCallPart):
        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name == 'forEach':
                    if not identifier.get_prefix_internal():
                        return
                    if identifier.get_prefix_internal() in ['angular', '_']:
                        return
                    f = self.get_current_function()
                    if f:
                        self.violations.add_forEach_violation(f, functionCallPart.create_bookmark(self.file))

class EvalDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def start_function_call_part(self, identifier, functionCallPart):
        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name == 'eval':
                    f = self.get_current_function()
                    if f:
                        self.violations.add_eval_violation(f, functionCallPart.create_bookmark(self.file))

class SetTimeoutDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def start_function_call_part(self, identifier, functionCallPart):
        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name == 'setTimeout':
                    f = self.get_current_function()
                    if f:
                        kbFunc = f.get_kb_object()
                        if kbFunc:
                            kbFunc.save_property('CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsSetTimeout', 1)
                    else:
                        kbFunc = self.interpreter.currentContext.statement.get_kb_object()
                        if kbFunc:
                            kbFunc.save_property('CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsSetTimeout', 1)
                    params = functionCallPart.get_parameters()
                    if f and len(params) >= 2:
                        firstParam = params[0]
                        if firstParam.is_string():
                            self.violations.add_setTimeout_violation(f, functionCallPart.create_bookmark(self.file))
                        elif firstParam.is_identifier():
                            evs = firstParam.evaluate()
                            if evs:
                                self.violations.add_setTimeout_violation(f, functionCallPart.create_bookmark(self.file))

class SetIntervalDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def start_function_call_part(self, identifier, functionCallPart):
        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name == 'setInterval':
                    f = self.get_current_function()
                    if f:
                        self.violations.add_setInterval_violation(f, functionCallPart.create_bookmark(self.file))
  
class ForInLoopDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def end_loop(self):
        
        if self.interpreter.get_current_context().is_for_loop():
                
            block = self.interpreter.get_current_context().statement
            try:
                startExprs = block.get_start_expressions()
                if startExprs[0] and startExprs[0].is_in_expression():
                    f = self.get_current_function()
                    if f:
                        self.violations.add_for_in_loop_violation(f, block.get_start_expressions()[0].create_bookmark(self.file))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))
    
class DeleteOnArrayDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def end_delete_statement(self, statement):

        obj = statement.elements[1]
        if not obj.is_identifier():
            return
        if obj.is_bracketed_identifier():
            try:
                f = self.get_current_function()
                if f:
                    if obj.get_resolutions():
                        for resolution in obj.resolutions:
                            callee = resolution.callee
                            try:
                                if callee.parent and callee.parent.is_assignment() and callee.parent.get_right_operand().is_list():
                                    self.violations.add_deleteOnArray_violation(f, statement.create_bookmark(self.file))
                                    break
                            except:
                                cast.analysers.log.debug(str(traceback.format_exc()))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))
            return

class DeleteWithNoObjectPropertiesDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def end_delete_statement(self, statement):

        obj = statement.elements[1]
        if not obj.is_identifier():
            return
        if obj.is_bracketed_identifier():
            return
        
        if not obj.get_prefix_internal():
            try:
                f = self.get_current_function()
                if f:
                    self.violations.add_deleteWithNoObjectProperties_violation(f, statement.create_bookmark(self.file))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))

class WebSocketInsideLoopDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def end_any_expression(self, statement):

        fcall = statement.elements[1]
        fcallpart = fcall.get_function_call_parts()[0]
        identifierCall = fcallpart.identifier_call
        if identifierCall.get_name() == 'WebSocket':
            try:
                f = self.get_current_function()
                if f:
                    if self.interpreter.loopLevel >= 1:
                        self.violations.add_WebSocketInsideLoop_violation(f, identifierCall.create_bookmark(self.file))
                    kbFunc = f.get_kb_object()
                    if kbFunc:
                        kbFunc.save_property('CAST_HTML5_JavaScript_Function_Properties.containsWebSocket', 1)
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))

class XMLHttpRequestInsideLoopDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def end_any_expression(self, statement):

        fcall = statement.elements[1]
        fcallpart = fcall.get_function_call_parts()[0]
        identifierCall = fcallpart.identifier_call
        if identifierCall.get_name() == 'XMLHttpRequest':
            try:
                f = self.get_current_function()
                if f:
                    if self.interpreter.loopLevel >= 1:
                        self.violations.add_XMLHttpRequestInsideLoop_violation(f, identifierCall.create_bookmark(self.file))
                    kbFunc = f.get_kb_object()
                    if kbFunc:
                        kbFunc.save_property('CAST_HTML5_JavaScript_Function_Properties.containsXMLHttpRequest', 1)
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))

class SuperClassKnowingSubClassDiag(Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def end_any_expression(self, statement):

        fcall = statement.elements[1]
        fcallpart = fcall.get_function_call_parts()[0]
        identifierCall = fcallpart.identifier_call
        currentClass = self.interpreter.currentContext.get_class()
        if currentClass and identifierCall.get_name() in self.interpreter.globalClassesByName:
                clList = self.interpreter.globalClassesByName[identifierCall.get_name()]
                if clList:
                    for cl in clList:
                        clSuperClass = cl.get_super_class()
                        cmpt = 0
                        while clSuperClass:
                            if cmpt == 100:
                                break
                            if clSuperClass.get_name() == currentClass.get_name():
                                self.violations.add_superclass_knowing_subclass_violation(currentClass, identifierCall.create_bookmark(self.file))
                                break
                            clSuperClass = clSuperClass.get_super_class()
                            cmpt += 1

class TooMuchDotNotationInLoopDiag (Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def start_identifier(self, identifier, n):

        if n == 3:
            try:
                f = self.get_current_function()
                if f:
                    if self.interpreter.loopLevel >= 1:
                        self.violations.add_tooMuchDotNotationInLoop_violation(f, identifier.create_bookmark(self.file))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))

class WebSQLDatabaseDiag (Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def start_identifier(self, identifier, n):

        fn = identifier.get_fullname()
        if fn == 'window.openDatabase':
            try:
                f = self.get_current_function()
                if f:
                    self.violations.add_webSQLDatabase_violation(f, identifier.create_bookmark(self.file))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))

class DocumentAllDiag (Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def start_identifier(self, identifier, n):

        fn = identifier.get_fullname()
        if ( 'document.all.' in fn or fn.endswith('document.all') ):
            try:
                f = self.get_current_function()
                if f:
                    self.violations.add_documentAll_violation(f, identifier.create_bookmark(self.file))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))

class UnsecuredCookieDiag (Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def start_identifier(self, identifier, n):

        fn = identifier.get_fullname()
        if ( 'document.cookie' == fn ):
                try:
                    f = self.get_current_function()
                    parent = identifier.get_parent()
                    if parent.is_assignment() and parent.get_left_operand() == identifier:
                        rightOper = parent.get_right_operand()
                        evs = rightOper.evaluate()
                        secureViolationFound = False
                        httpOnlyViolationFound = False
                        overlyBroadPathViolationFound = False
                        overlyBroadDomainViolationFound = False
                        for ev in evs:
                            if ev:
                                if not secureViolationFound and not 'secure' in ev:
                                    secureViolationFound = True
                                    if f:
                                        self.violations.add_unsecured_cookie_violation(f, identifier.create_bookmark(self.file))
                                    else:
                                        self.violations.add_unsecured_cookie_violation(self.interpreter.currentContext.statement, identifier.create_bookmark(self.file))
                                if not httpOnlyViolationFound and not 'HttpOnly' in ev:
                                    httpOnlyViolationFound = True
                                    if f:
                                        self.violations.add_cookie_without_setting_httpOnly_violation(f, identifier.create_bookmark(self.file))
                                    else:
                                        self.violations.add_cookie_without_setting_httpOnly_violation(self.interpreter.currentContext.statement, identifier.create_bookmark(self.file))
                                if not overlyBroadPathViolationFound and 'path' in ev:
                                    # name=test; path=/
                                    params = ev.split(';')
                                    for param in params:
                                        p = param.strip()
                                        if not p.startswith('path'):
                                            continue
                                        index = p.find('=')
                                        if index <= 0:
                                            continue
                                        p = p[index + 1:].strip()
                                        if not p == '/':
                                            continue
                                        overlyBroadPathViolationFound = True
                                        if f:
                                            self.violations.add_overly_broad_path_cookie_violation(f, identifier.create_bookmark(self.file))
                                        else:
                                            self.violations.add_overly_broad_path_cookie_violation(self.interpreter.currentContext.statement, identifier.create_bookmark(self.file))
                                        break
                                if not overlyBroadDomainViolationFound and 'domain' in ev:
                                    # name=test; path=/
                                    params = ev.split(';')
                                    for param in params:
                                        p = param.strip()
                                        if not p.startswith('domain'):
                                            continue
                                        index = p.find('=')
                                        if index <= 0:
                                            continue
                                        p = p[index + 1:].strip()
                                        if not p.startswith('.'):
                                            continue
                                        overlyBroadDomainViolationFound = True
                                        if f:
                                            self.violations.add_overly_broad_domain_cookie_violation(f, identifier.create_bookmark(self.file))
                                        else:
                                            self.violations.add_overly_broad_domain_cookie_violation(self.interpreter.currentContext.statement, identifier.create_bookmark(self.file))
                                        break
                        if f:
                            kbFunc = f.get_kb_object()
                            if kbFunc:
                                kbFunc.save_property('CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsDocumentCookie', 1)
                        else:
                            kbFunc = self.interpreter.currentContext.statement.get_kb_object()
                            if kbFunc:
                                kbFunc.save_property('CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsDocumentCookie', 1)
                except:
                    cast.analysers.log.debug(str(traceback.format_exc()))

class SwitchNoDefaultDiag (Html5Diag):

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def end_switch_block(self, switchBlock):
        
        if not switchBlock.default_block:
            try:
                f = self.get_current_function()
                if f:
                    self.violations.add_switch_no_default_violation(f, switchBlock.create_bookmark(self.file))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))
    
class HardcodedPasswordDiag (Html5Diag):
    # exactly matches variable name
    pss = [  # english
                'password', 'passcode', 'rootpassword', 'countersign', 'watchword', 'magic_word', 'passphrase',
                'parole', 'passphrase', 'pass_phrase', 'passwd', 'passwrd', 'psswrd', 'pword',
                'pss', 'psw', 'pwd',  # these can raise false positives because of similarity to file extensions
                # spanish
                'contraseña', 'contrasena', 'clave_secreta', 'palabra_accesso', 'clave_seguridad', 'clavecom',
                # chinese
                'mima', 'mìmǎ',
                # french
                'mot_de_passe'  # 'mdp'
               ]  # -> not very evident ..
    pss_ends = pss
    pss_begins = [w + "_" for w in pss]

    @staticmethod
    def identifier_matches_password_variable(ident):
        
        name = ident.get_name().lower()
        if name in HardcodedPasswordDiag.pss:
            return True
        if any(name.endswith(_string) for _string in HardcodedPasswordDiag.pss_ends):
            if name.startswith('is') or 'char' in name:
                return False
            return True
        if any(name.startswith(_string) for _string in HardcodedPasswordDiag.pss_begins) and not 'char' in name:
            return True
        return False

    @staticmethod
    def is_string_possible_password(s):
        try:
            name = s.get_name().lower()
            if not s.is_string() or len(name) < 2:
                return False
            if name in ['none', 'password', 'temp']:
                return False
            if ' ' in name:
                return False
            return True
        except:
            return False

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
        
    def start_function_call(self, fcall):

        try:
            fcallpart = fcall.get_function_call_parts()[0]
            if HardcodedPasswordDiag.identifier_matches_password_variable(fcallpart.identifier_call):
                params = fcallpart.get_parameters()
                if params:
                    param = params[0]
                    if HardcodedPasswordDiag.is_string_possible_password(param):
                        parentFunc = self.get_current_function()
                        if parentFunc:
                            self.violations.add_hardcoded_password_violation(parentFunc, param.create_bookmark(self.file))
        except:
            pass
        
    def start_assignment(self, assignment):
        try:
            leftOper = assignment.get_left_operand()
            if not leftOper.is_identifier():
                return
            if HardcodedPasswordDiag.identifier_matches_password_variable(leftOper):
                rightOper = assignment.get_right_operand()
                if HardcodedPasswordDiag.is_string_possible_password(rightOper):
                    parentFunc = self.get_current_function()
                    if parentFunc:
                        self.violations.add_hardcoded_password_violation(parentFunc, rightOper.create_bookmark(self.file))
            
        except:
            return

    def start_object_value(self, ov):
        try:
            for key, value in ov.items.items():
                if not key.is_identifier() or key.has_been_created_from_string():
                    continue
                if HardcodedPasswordDiag.identifier_matches_password_variable(key):
                    if HardcodedPasswordDiag.is_string_possible_password(value):
                        parentFunc = self.get_current_function()
                        if parentFunc:
                            self.violations.add_hardcoded_password_violation(parentFunc, value.create_bookmark(self.file))
            
        except:
            return
        
    def start_binary_expression(self, expr):
        try:
            if not expr.is_equality_expression():
                return
            leftOper = expr.get_left_operand()
            if not leftOper.is_identifier():
                return
            if HardcodedPasswordDiag.identifier_matches_password_variable(leftOper):
                rightOper = expr.get_right_operand()
                if HardcodedPasswordDiag.is_string_possible_password(rightOper):
                    parentFunc = self.get_current_function()
                    if parentFunc:
                        self.violations.add_hardcoded_password_violation(parentFunc, rightOper.create_bookmark(self.file))
            
        except:
            return
        
    def start_string(self, s):
        
        # b = ';PWD=password1234'
        nameLower = s.get_name().lower()
        if any(_string + '=' in nameLower for _string in HardcodedPasswordDiag.pss):
            violationFound = False
            for pwdString in HardcodedPasswordDiag.pss:
                strToSearch = pwdString + '='
                if nameLower.endswith(strToSearch):
                    # b = ';PWD='
                    continue
                index = nameLower.find(pwdString + '=')
                index = nameLower.find('=', index)
                if nameLower[index + 1] == ';':
                    # b = ';PWD=;xxx'
                    continue
                violationFound = True
                break
            if violationFound:
                parentFunc = self.get_current_function()
                if parentFunc:
                    self.violations.add_hardcoded_password_violation(parentFunc, s.create_bookmark(self.file))
            
class HardcodedNetworkResourceDiag (Html5Diag):
        
    IP4Regexp = '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)'
    IP6Regexp = '((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:)))(%.+)?s*(\/([0-9]|[1-9][0-9]|1[0-1][0-9]|12[0-8]))?'
    
    @staticmethod
    def match_ipv4(text):
        res = re.search(HardcodedNetworkResourceDiag.IP4Regexp, text)
        if not res:
            return None
        start = res.start()
        if start > 0 and text[start-1] != '/':
            return None
        end = res.end()
        l = len(text)
        if end == l or text[end] in ['/', ':']: 
            return res
        return None
        
    @staticmethod
    def match_ipv6(text):
        res = re.search(HardcodedNetworkResourceDiag.IP6Regexp, text)
        if not res:
            return None
        if text.startswith(':'):
            return None
        start = res.start()
        if start > 0 and text[start-1] != '/':
            return None
        end = res.end()
        l = len(text)
        if end == l and text.endswith('::'):
            return None
        if end == l or text[end] in ['/', ':']: 
            return res
        return None

    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
        
    def start_string(self, s):
        
        name = s.get_name()
        searched = HardcodedNetworkResourceDiag.match_ipv4(name)
        if not searched:
            searched = HardcodedNetworkResourceDiag.match_ipv6(name)
        if searched:
            try:
                f = self.get_current_function()
                if f:
                    self.violations.add_hardcoded_network_resource_name_violation(f, s.create_bookmark(self.file))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))        
            
class FunctionCallInTerminationLoopDiag (Html5Diag):
    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)

    def start_function_call(self, fcall):

        if self.interpreter.get_current_context().is_for_loop() and self.interpreter.get_current_context().is_in_termination_expression:
            f = self.get_current_function()
            if f:
                self.violations.add_function_call_in_termination_loop_violation(f, fcall.create_bookmark(self.file))

class FunctionInsideLoopDiag (Html5Diag):
    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def pop_context(self, context):
        
        if context:
            if context.is_function():
                for violationSuspension in context.violationSuspensions:
                    if violationSuspension.ast.get_kb_symbol() in context.functionCalls:
                        self.violations.add_functionsInsideLoops_violation(violationSuspension.artifact, violationSuspension.ast.create_bookmark(self.file))
                    elif violationSuspension.ast.parent and isinstance(violationSuspension.ast.parent, JSFunctionCall):
                        self.violations.add_functionsInsideLoops_violation(violationSuspension.artifact, violationSuspension.ast.create_bookmark(self.file))

    def start_function(self, ast):
        if self.interpreter.loopLevel > 0:
            f = self.get_current_function()
            if f:
                currentContext = self.get_current_context()
                if currentContext.is_loop() and not currentContext.forEach and not currentContext.is_function_call():
                    functionContext = currentContext.get_last_function_context()
                    if functionContext:
                        functionContext.violationSuspensions.append(ViolationSuspension(f, ast))

class UnsafeSingletonDiag (Html5Diag):
    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
        self.unsafeSingletonClassesByName = {}

    def end_js_content(self):
        
        if self.unsafeSingletonClassesByName:
            for cl in self.unsafeSingletonClassesByName.values():
                self.violations.add_unsafe_singleton_class_violation(cl, cl.get_method(cl.get_name()).create_bookmark(self.file))

    def start_function_call_part(self, identifier, functionCallPart):

        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name == 'freeze' and identifier.prefix == 'Object':
                    try:
                        param = functionCallPart.get_parameters()[0]
                        if param.get_resolutions():
                            for resol in param.resolutions:
                                try:
                                    callee = resol.callee
                                    if callee.parent.is_assignment():
                                        rightOper = callee.parent.get_right_operand()
                                        if rightOper.is_new_expression():
                                            newCall = rightOper.elements[1]
                                            classCallName = newCall.get_function_call_parts()[0].identifier_call.get_name()
                                            if classCallName in self.unsafeSingletonClassesByName:
                                                self.unsafeSingletonClassesByName.pop(classCallName)
                                                break
                                except:
                                    pass
                    except:
                        cast.analysers.log.debug(str(traceback.format_exc()))

    def end_class(self):
        try:
            if self.interpreter.currentContext.isSingleton:
                self.unsafeSingletonClassesByName[self.interpreter.currentContext.statement.get_name()] = self.interpreter.currentContext.statement
        except:
            cast.analysers.log.debug(str(traceback.format_exc()))

class FunctionConstructorDiag (Html5Diag):
    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def end_function(self, currentContext):
        
        func = currentContext.statement
        if func.is_function_constructor():
            try:
                parentFunc = self.get_current_function()
                if parentFunc:
                    self.violations.add_function_constructor_violation(parentFunc, func.create_bookmark(self.file))
                else:
                    self.violations.add_function_constructor_violation(self.interpreter.contextStack[0].statement, func.create_bookmark(self.file))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))

class BreakInForLoopDiag (Html5Diag):
    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def end_any_statement(self, statement):

        if statement.is_break_statement():
            try:
                f = self.get_current_function()
                if f:
                    if self.interpreter.loopLevel >= 1 and self.interpreter.loopsStack[-1].is_for_block() and not self.interpreter.loopsStack[-1].is_for_in_block():
                        self.violations.add_break_in_for_loop_violation(f, statement.create_bookmark(self.file))
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))
            return
    
class EmptyCatchFinallyBlockDiag (Html5Diag):
    def __init__(self, interpreter):
        Html5Diag.__init__(self, interpreter)
    
    def end_any_statement(self, statement):

        if statement.is_return_statement():
            tryCatchBlock = self.interpreter.currentContext.is_in_try_catch()
            if tryCatchBlock and tryCatchBlock.finallyBlock and self.interpreter.has_parent(statement, tryCatchBlock.finallyBlock):
                try:
                    f = self.get_current_function()
                    if f:
                        self.violations.add_return_in_finally_block_violation(f, statement.create_bookmark(self.file))
                except:
                    cast.analysers.log.debug(str(traceback.format_exc()))

    def start_try_catch_block(self, block):
        
        if block.catchBlocks:
            for catchBlock in block.catchBlocks:
                if not catchBlock.block or not catchBlock.block.statements:
                    try:
                        f = self.get_current_function()
                        if f:
                            self.violations.add_empty_catch_block_violation(f, catchBlock.create_bookmark(self.file))
                    except:
                        cast.analysers.log.debug(str(traceback.format_exc()))
        if block.finallyBlock:
            if block.finallyBlock.block and not block.finallyBlock.block.statements:
                try:
                    f = self.get_current_function()
                    if f:
                        self.violations.add_empty_finally_block_violation(f, block.finallyBlock.create_bookmark(self.file))
                except:
                    cast.analysers.log.debug(str(traceback.format_exc()))
            