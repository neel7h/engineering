import javascript_parser.javascript_diags as diags
import cast.analysers.ua
import traceback
            
class Context:

    def __init__(self, parentContext, statement):
        
        self.statement = statement
        self.parentContext = parentContext
        self.identifiersToResolve = []
        self.forLoopsNr = 0
        self.cookieFcall = {}   # cookie() function call parts by identifier fullname
        self.cookieSetHttpOnly = []   # res.cookie.setHttpOnly(true); stores elements as 'res.cookie' as strings
        
    def add_cookie_function_call_part(self, fcallpart):
        if self.parentContext:
            self.parentContext.add_cookie_function_call_part(fcallpart)
        self.cookieFcall[fcallpart.get_fullname()] = fcallpart
        
    def add_cookie_setHttpOnly(self, fcallpart):
        if self.parentContext:
            self.parentContext.add_cookie_setHttpOnly(fcallpart)
        self.cookieSetHttpOnly.append(fcallpart.identifier_call.get_prefix())
            
    def add_prefixed_identifier(self, identifier):
        if self.parentContext:
            return self.parentContext.add_prefixed_identifier(identifier)
        
    def get_last_function_context(self):
        if self.parentContext:
            return self.parentContext.get_last_function_context()
        else:
            return None

    def is_for_loop(self):
        return False

    def is_function_call(self):
        return False

    def is_function(self):
        return False

    def is_loop(self):
        return False
    
    def register_for_loop(self):
        if self.parentContext:
            self.parentContext.register_for_loop()
        else:
            self.forLoopsNr += 1

    def set_singleton(self, isSingleton):
        pass

    def get_class(self):
        if self.parentContext:
            return self.parentContext.get_class()
        return None
        
    def is_in_try_catch(self):
        if self.parentContext:
            return self.parentContext.is_in_try_catch()
        return False
        
    def is_in_try_catch_in_current_function(self):
        if self.parentContext:
            return self.parentContext.is_in_try_catch()
        return False
        
class ClassContext(Context):

    def __init__(self, parentContext, statement):
        
        Context.__init__(self, parentContext, statement)
        self.isSingleton = False
        
    def set_singleton(self, isSingleton):
        self.isSingleton = isSingleton

    def get_class(self):
        return self.statement
        
class FunctionContext(Context):

    def __init__(self, parentContext, statement):
        
        Context.__init__(self, parentContext, statement)
        self.violationSuspensions = []
        self.functionCalls = []

    def get_last_function_context(self):
        return self

    def is_function(self):
        return True
        
    def add_cookie_function_call_part(self, fcallpart):
        self.cookieFcall[fcallpart.get_fullname()] = fcallpart
    
    def add_cookie_setHttpOnly(self, fcallpart):
        self.cookieSetHttpOnly.append(fcallpart.identifier_call.get_prefix())

    def register_for_loop(self):
        self.forLoopsNr += 1
        
    def is_in_try_catch_in_current_function(self):
        return False

class LoopContext(Context):

    def __init__(self, parentContext, block):
        
        Context.__init__(self, parentContext, block)
        self.is_in_start_expression = False
        self.is_in_block = False
        # contains number of identifiers with a prefix with at least 2 dots in a table whose key is a.b
        # Useful for diag CAST_HTML5_Metric_AvoidTooMuchDotNotationInLoop
        self.prefixedIdentifiers = {}
        self.forEach = False
        
    def add_prefixed_identifier(self, identifier):
        prefix = identifier.get_prefix_internal()
        if not prefix or not isinstance(prefix, str):
            return
        nbDot = prefix.count('.')
        n = 0
        if nbDot >= 2:
            v = prefix.split('.', 2)
            s = v[0] + '.' + v[1]
            if s in self.prefixedIdentifiers:
                n = self.prefixedIdentifiers[s] + 1
            else:
                n = 1
            self.prefixedIdentifiers[s] = n
        return n

    def is_loop(self):
        return True

class ForLoopContext(LoopContext):

    def __init__(self, parentContext, block):
        
        LoopContext.__init__(self, parentContext, block)
        self.is_in_termination_expression = False
        self.is_in_forward_expression = False

    def is_for_loop(self):
        return True

class FunctionCallContext(Context):

    def __init__(self, parentContext, statement):
        
        Context.__init__(self, parentContext, statement)

    def is_function_call(self):
        return True

class TryCatchContext(Context):

    def __init__(self, parentContext, statement):
        Context.__init__(self, parentContext, statement)
        self.finallyBlock = statement.finallyBlock
        
    def is_in_try_catch(self):
        return self.statement
        
    def is_in_try_catch_in_current_function(self):
        return True

class JavascriptDiagsInterpreter:
    
    def __init__(self, file, violations, globalClassesByName):
        
        self.file = file
        self.globalClassesByName = globalClassesByName
        self.violations = violations
        self.loopLevel = 0
        self.loopsStack = []
        self.contextStack = []
        self.currentContext = None
        self.diags = []
        self.diags.append(diags.FunctionInsideLoopDiag(self))
        self.diags.append(diags.UnsafeSingletonDiag(self))
        self.diags.append(diags.FunctionConstructorDiag(self))
        self.diags.append(diags.FunctionCallInTerminationLoopDiag(self))
        self.diags.append(diags.HardcodedPasswordDiag(self))
        self.diags.append(diags.HardcodedNetworkResourceDiag(self))
        self.diags.append(diags.EmptyCatchFinallyBlockDiag(self))
        self.diags.append(diags.SwitchNoDefaultDiag(self))
        self.diags.append(diags.TooMuchDotNotationInLoopDiag(self))
        self.diags.append(diags.WebSQLDatabaseDiag(self))
        self.diags.append(diags.DocumentAllDiag(self))
        self.diags.append(diags.UnsecuredCookieDiag(self))
        self.diags.append(diags.WebSocketInsideLoopDiag(self))
        self.diags.append(diags.XMLHttpRequestInsideLoopDiag(self))
        self.diags.append(diags.SuperClassKnowingSubClassDiag(self))
        self.diags.append(diags.DeleteOnArrayDiag(self))
        self.diags.append(diags.DeleteWithNoObjectPropertiesDiag(self))
        self.diags.append(diags.BreakInForLoopDiag(self))
        self.diags.append(diags.ForInLoopDiag(self))
        self.diags.append(diags.QuerySelectorAllDiag(self))
        self.diags.append(diags.DatabaseDirectAccessDiag(self))
        self.diags.append(diags.ForEachDiag(self))
        self.diags.append(diags.EvalDiag(self))
        self.diags.append(diags.SetTimeoutDiag(self))
        self.diags.append(diags.SetIntervalDiag(self))
        self.diags.append(diags.JsonParseStringifyWithoutTryCatchDiag(self))
        self.diags.append(diags.ConsoleLogDiag(self))
        
    def get_current_context(self):
        return self.currentContext
    
    def push_context(self, context):
        
        self.contextStack.append(context)
        self.currentContext = context
    
    def pop_context(self):
        
        if self.contextStack:
            context = self.contextStack.pop()
            for diag in self.diags:
                diag.pop_context(context)

        if self.contextStack:
            self.currentContext = self.contextStack[-1]
        else:
            self.currentContext = None
    
    def get_current_function(self):
        
        fContext = self.get_current_context().get_last_function_context()
        if not fContext:
            return None
        return fContext.statement

    def start_js_content(self, ast):
        self.push_context(Context(None, ast))

    def end_js_content(self):
        
        if self.get_current_context().forLoopsNr > 1:
            self.get_current_context().statement.forLoopsNr = self.get_current_context().forLoopsNr

        for diag in self.diags:
            diag.end_js_content()
        
        self.pop_context()
        
    def start_function(self, ast):
        
        for diag in self.diags:
            diag.start_function(ast)
        self.push_context(FunctionContext(self.currentContext, ast))

    def end_function(self):
        currentContext = self.get_current_context()
        func = currentContext.statement
        if currentContext.forLoopsNr >= 1:
            try:
                if func.get_kb_object():
                    func.get_kb_object().save_property('CAST_HTML5_Metric_NumberOfForLoops.numberOfForLoops', currentContext.forLoopsNr)
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))
        
        self.pop_context()

        for diag in self.diags:
            diag.end_function(currentContext)
    
    def start_function_call(self, fcall):
        
        for diag in self.diags:
            diag.start_function_call(fcall)
                
    def start_function_call_part(self, identifier, functionCallPart):
        
        functionContext = self.get_current_context().get_last_function_context()
        if functionContext:
            for resol in identifier.get_resolutions():
                functionContext.functionCalls.append(resol.callee)
        
        for diag in self.diags:
            diag.start_function_call_part(identifier, functionCallPart)

        if identifier.is_identifier():
            if identifier.is_func_call():
                name = identifier.get_name()
                if name == 'forEach':
                    if not identifier.get_prefix_internal():
                        self.push_context(FunctionCallContext(self.currentContext, functionCallPart))
                        return
                    if identifier.get_prefix_internal() in ['angular', '_']:
                        self.push_context(FunctionCallContext(self.currentContext, functionCallPart))
                        return
                elif name == 'cookie' and identifier.prefix and not identifier.prefix == '$':
                    try:
                        if functionContext:
                            functionContext.add_cookie_function_call_part(functionCallPart)
                        else:
                            self.currentContext.add_cookie_function_call_part(functionCallPart)
                        f = self.get_current_function()
                        if f:
                            kbFunc = f.get_kb_object()
                            if kbFunc:
                                kbFunc.save_property('CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsCookieCall', 1)
                        else:
                            kbFunc = self.currentContext.statement.get_kb_object()
                            if kbFunc:
                                kbFunc.save_property('CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsCookieCall', 1)

                    except:
                        cast.analysers.log.debug(str(traceback.format_exc()))
                elif name == 'setHttpOnly' and identifier.prefix and not identifier.prefix == '$' and identifier.prefix.endswith('.cookie'):
                    try:
                        params = functionCallPart.get_parameters()
                        if params:
                            firstParam = params[0]
                            if firstParam and firstParam.is_ast_token() and firstParam.name == 'true':
                                if functionContext:
                                    functionContext.add_cookie_setHttpOnly(functionCallPart)
                                else:
                                    self.currentContext.add_cookie_setHttpOnly(functionCallPart)
                    except:
                        cast.analysers.log.debug(str(traceback.format_exc()))

        self.push_context(FunctionCallContext(self.currentContext, functionCallPart))

    def end_function_call_part(self):
        self.pop_context()
    
    def start_loop(self, ast):
        if ast.is_for_block():
            self.push_context(ForLoopContext(self.currentContext, ast))
        else:
            context = LoopContext(self.currentContext, ast)
            if ast.is_function_call(): # foreach loop
                context.forEach = True
            self.push_context(context)
        self.loopsStack.append(ast)
        self.loopLevel += 1

    def end_loop(self):
        
        if self.get_current_context().is_for_loop():
            
            if not self.get_current_context().statement.is_for_in_block():
                self.get_current_context().register_for_loop()

        for diag in self.diags:
            diag.end_loop()
            
        self.loopLevel -= 1
        self.loopsStack.pop()
        self.pop_context()
        
    def start_termination_expression(self):
        self.currentContext.is_in_termination_expression = True
        
    def end_termination_expression(self):
        self.currentContext.is_in_termination_expression = False

    def has_parent(self, statement, parent):
        par = statement.parent
        while par:
            if par == parent:
                return True
            par = par.parent
        return False
    
    def end_any_statement(self, statement):

        for diag in self.diags:
            diag.end_any_statement(statement)
        
        if statement.is_return_statement():
            if self.currentContext.statement.is_constructor() and self.currentContext.parentContext:
                self.currentContext.parentContext.set_singleton(True)

    def end_any_expression(self, statement):
        
        if len(statement.elements) < 2:
            return

        if not statement.is_new_expression():
            return
        
        fcall = statement.elements[1]
        if not fcall.is_function_call():
            return

        for diag in self.diags:
            diag.end_any_expression(statement)

    def end_delete_statement(self, statement):
        
        if not statement.is_delete_statement():
            return
        if len(statement.elements) < 2:
            return
        
        obj = statement.elements[1]
        if not obj.is_identifier():
            return

        for diag in self.diags:
            diag.end_delete_statement(statement)
    
    def start_identifier(self, identifier):
        
        prefix = identifier.get_prefix_internal()
        if not prefix or not isinstance(prefix, str):
            return
        n = self.get_current_context().add_prefixed_identifier(identifier)
        for diag in self.diags:
            diag.start_identifier(identifier, n)

    def end_switch_block(self, switchBlock):

        for diag in self.diags:
            diag.end_switch_block(switchBlock)

    def start_try_catch_block(self, block):
        
        self.push_context(TryCatchContext(self.currentContext, block))

        for diag in self.diags:
            diag.start_try_catch_block(block)

    def end_try_catch_block(self):
        self.pop_context()
    
    def start_class(self, ast):
        self.push_context(ClassContext(self.currentContext, ast))

    def end_class(self):
        
        for diag in self.diags:
            diag.end_class()
        self.pop_context()
        
    def start_assignment(self, assignment):
        for diag in self.diags:
            diag.start_assignment(assignment)
        
    def start_object_value(self, ov):
        for diag in self.diags:
            diag.start_object_value(ov)
        
    def start_binary_expression(self, expr):
        for diag in self.diags:
            diag.start_binary_expression(expr)
        
    def start_string(self, s):

        for diag in self.diags:
            diag.start_string(s)
