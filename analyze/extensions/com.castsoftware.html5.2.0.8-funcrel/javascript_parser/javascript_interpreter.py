import difflib
import os
import re
from javascript_parser.symbols import JsContent, Identifier, Function, AstList, AstBlock, Define, Require, FunctionCall, JSFunctionCall, FunctionCallPart, Assignment, AnyStatement, AnyExpression, ObjectValue, AstToken, IfStatement, IfBlock, ElseIfBlock, ElseBlock, Expression, DoBlock, WhileBlock, ForEachBlock, ForBlock, SwitchStatement, SwitchCaseBlock, SwitchDefaultBlock, TryCatchBlock, CatchBlock, FinallyBlock, Resolution, GlobalFunction, GlobalVariable, VarDeclaration, AstOperator, BinaryExpression, EqualBinaryExpression, NotEqualBinaryExpression, AdditionExpression, OrExpression, InExpression, UnaryExpression, NotExpression, IdentifierToResolve, IfTernaryExpression, HttpCall, ArrowFunction, Class, GlobalClass, Method, ExecuteSQL, JsxExpression, ImportStatement, KbSymbol, ObjectDestructuration
from collections import OrderedDict
from cast.analysers import File
from javascript_parser.javascript_interpreter_contexts import Context, ObjectValueContext, FunctionContext, AnyStatementContext, AssignmentContext, FunctionCallContext, FileContext, VarDeclarationContext, IfContext, IfBlockContext, SwitchContext, SwitchCaseContext, ParameterContext, BracketedBlockContext, CurlyBracketedBlockContext, JsxContext, FunctionCallPartContext, ImportStatementContext, RequireContext, IdentifierContext, DefineContext, AnyExpressionContext, BinaryExpressionContext, UnaryExpressionContext, TernaryExpressionContext, ClassContext, MethodContext, ObjectDestructurationContext
from javascript_parser.javascript_resolution import resolve_all, resolve_element
import cast.analysers.ua
import traceback

def is_identifier(ast):
    try:
        return ast.is_identifier()
    except:
        return False

def is_function_call(ast):
    try:
        return ast.is_function_call()
    except:
        return False

def is_bracketed_identifier(ast):
    try:
        return ast.is_bracketed_identifier()
    except:
        return False
    
def get_resolution_callees(identifier):
    
    if not identifier.get_resolutions():
        return []
    
    res = []
    for resol in identifier.get_resolutions():
        res.append(resol.callee)
    return res

class JavascriptInterpreter:
    
#     class used to store xhttp.open("GET", "ajax_info.txt", false);
    class OpenCall:
        
        def __init__(self, requestType, url, ast, caller, file):
            self.ast = ast  # functionCall ast
            self.requestType = requestType
            self.url = url
            self.urlValues = None
            self.caller = caller
            self.file = file
            self.parameters = None

#     class used to store WebSocket(param);
    class WebSocket:
        
        def __init__(self, param, ast, caller, file):
            self.ast = ast  # functionCall ast
            self.param = param
            self.urlValues = None
            self.caller = caller
            self.file = file
                
    def __init__(self, parent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, jsContent, bFullAnalysis, htmlContentsByJS = None, htmlContentsByName = None, resolve = True):
        
        self.config = config
        self.jsContent = jsContent
        self.parent = parent
        self.file = self.get_file()
        self.currentAst = parent
        self.currentContext = None
        self.contextStack = []
        self.globalVariablesByName = globalVariablesByName
        self.globalFunctionsByName = globalFunctionsByName
        self.globalClassesByName = globalClassesByName
        self.bFullParsing = bFullAnalysis
        self.htmlContentsByJS = htmlContentsByJS
        self.htmlContentsByName = htmlContentsByName
        self.jsContentsByFilename = jsContentsByFilename
        self.emptyLines = None
        self.lastHttpCall = None
        self.resolvingHtmlValues = False
        self.currentAxiosCreates = []
        self.currentAxiosCallWithVariables = []
        self.axiosVariableName = ''
        self.imports = {}   # import identifiers by name
        self.serverEvents = {}  # list of serverEvents HttpCall, key is variable name in serverEvents = new EventSource(eventsUrl);
        self.requiresToEvaluate = []
        self.namespacePrefixes = {} # var self = {} --> self.namespacePrefixes['self'] contains the current file basename 
        self.probableHttpRequest = None
        self.submitCallEncontered = False
        self.fetchFunctionName = 'fetch'
        self.bracketedIdentifiersToEvaluate = []

    def add_namespace_prefix(self, name):
        
        if self.currentContext and self.currentContext.is_file_context() and not name in self.namespacePrefixes:
            basename = os.path.basename(self.file.get_path())
            self.namespacePrefixes[name] = basename[: basename.rfind('.') ]
                        
    def get_file(self):
        if isinstance(self.parent, File):
            return self.parent
        return self.parent.get_file()
    
    def get_current_prefix_old(self):
        
        if not isinstance(self.currentContext, ObjectValueContext):
            return ''
        context = self.currentContext.parentContext
        if not context:
            return ''
        if not isinstance(context, AnyStatementContext) or not context.statement.is_return_statement():
            return ''
        context = context.parentContext
        if not context:
            return ''
        if not isinstance(context, FunctionContext):
            return ''
        return context.statement.get_fullname()
    # returns prefix f if we are in following context:
    # function f() {
    #    return { g: function() {} };
    # }
    def get_current_prefix(self):
        
        try:
            if not isinstance(self.currentContext, ObjectValueContext):
                return ''
            context = self.currentContext.parentContext
            if not context:
                return ''
            isReturn = True
            if not isinstance(context, AnyStatementContext) or not context.statement.is_return_statement():
                isReturn = False
                if not isinstance(context, AssignmentContext):
                    return ''
            context = context.parentContext
            if not context:
                return ''
            if not isinstance(context, FunctionContext):
                return ''
            if context.statement.get_name() and not context.statement.get_name().startswith('NONAME'):
                return context.statement.get_fullname()
            else:
                if context.parentContext and isinstance(context.parentContext, FunctionCallContext) and context.parentContext.isJSFunctionCall:
                    context = context.parentContext.parentContext
                    if isinstance(context, AssignmentContext):
                        if isReturn and context.parentContext and ( isinstance(context.parentContext, FileContext) or (isinstance(context.parentContext, VarDeclarationContext) and isinstance(context.parentContext.parentContext, FileContext))):
                            return ''
                        return context.statement.get_left_operand().get_fullname()
            return ''
        except:
            return ''
        
    def add_global(self, obj, isVar, prefix = None, cl = None, addPrefixToName = False, otherFullname = None):
        
        try:
            fullname = obj.get_fullname()
            if addPrefixToName:
                fullname = prefix + '.' + fullname
            if fullname.startswith('module.exports.'):
                fullname = fullname[15:]
            elif fullname.startswith('exports.'):
                fullname = fullname[8:]
            pref = self.get_current_prefix()
            if pref:
                if '.' in pref:
                    index = pref.find('.')
                    if pref[index+1:].startswith('NONAME'):
                        pref = pref[:index]
                if not fullname.startswith(pref + '.'):
                    fullname = pref + '.' + fullname
            if fullname.startswith('NONAME') and '.' in fullname:
                fullname = fullname[fullname.find('.')+1:]
            nameWithoutPrototype = fullname
            
            if '.prototype.' in nameWithoutPrototype:
                nameWithoutPrototype = nameWithoutPrototype.replace('prototype.', '')
            if '.statics.' in nameWithoutPrototype:
                nameWithoutPrototype = nameWithoutPrototype.replace('statics.', '')
            if '.this.' in nameWithoutPrototype:
                index = nameWithoutPrototype.find('.this.')
                nameWithoutPrototype = nameWithoutPrototype[:index] + nameWithoutPrototype[index + 5:]
            elif nameWithoutPrototype.endswith('.this.'):
                nameWithoutPrototype = nameWithoutPrototype[:index]

            if '.this.' in fullname:
                index = fullname.find('.this.')
                fullname = fullname[:index] + fullname[index + 5:]
            elif fullname.endswith('.this.'):
                fullname = fullname[:index]
        
            globalModuleContainer = None
            if isinstance(obj, Class):
                globalContainer = self.globalClassesByName
                if self.jsContent.is_module() and obj.get_begin_line() <= self.jsContent.module.lastLine:
                    globalModuleContainer = self.jsContent.module.globalClassesByName
                gfunc = GlobalClass(fullname, obj, self.file)
                if nameWithoutPrototype != fullname:
                    gfunc2 = GlobalClass(nameWithoutPrototype, obj, self.file)
            elif isinstance(obj, Method):
                if cl.name in self.globalClassesByName:
                    for globalClass in self.globalClassesByName[cl.name]:
                        if globalClass.kbSymbol == cl.get_kb_symbol():
                            globalClass.add_method(obj)
                            return
            elif isinstance(obj, Function):
                globalContainer = self.globalFunctionsByName
                if self.jsContent.is_module() and obj.get_begin_line() <= self.jsContent.module.lastLine:
                    globalModuleContainer = self.jsContent.module.globalFunctionsByName
                gfunc = GlobalFunction(fullname, obj, self.file)
                if nameWithoutPrototype != fullname:
                    gfunc2 = GlobalFunction(nameWithoutPrototype, obj, self.file)
                elif nameWithoutPrototype.startswith('window.'):
                    gfunc2 = GlobalFunction(nameWithoutPrototype[7:], obj, self.file)
            else:
                globalContainer = self.globalVariablesByName
                if self.jsContent.is_module() and obj.get_begin_line() <= self.jsContent.module.lastLine:
                    globalModuleContainer = self.jsContent.module.globalVariablesByName
                gfunc = GlobalVariable(fullname, obj, isVar, self.file)
                if nameWithoutPrototype != fullname:
                    gfunc2 = GlobalVariable(nameWithoutPrototype, obj, isVar, self.file)
            
            if globalModuleContainer != None:
                globalContainer = globalModuleContainer
               
            if prefix and not addPrefixToName:
                fullname = prefix + '.' + fullname
            if globalModuleContainer != None:
                if '.' in fullname:
                    if not fullname in globalContainer:
                        flist = []
                        globalContainer[fullname] = flist
                    else:
                        flist = globalContainer[fullname]
                    flist.append(gfunc)
                    fullname = fullname[fullname.find('.') + 1:]
                if '.' in nameWithoutPrototype:
                    nameWithoutPrototype = nameWithoutPrototype[nameWithoutPrototype.find('.') + 1:]

            if not fullname in globalContainer:
                flist = []
                globalContainer[fullname] = flist
            else:
                flist = globalContainer[fullname]
            flist.append(gfunc)
            if otherFullname:
                if not otherFullname in globalContainer:
                    flist = []
                    globalContainer[otherFullname] = flist
                else:
                    flist = globalContainer[otherFullname]
                flist.append(gfunc)

            if nameWithoutPrototype != fullname:
                if not nameWithoutPrototype in globalContainer:
                    flist2 = []
                    globalContainer[nameWithoutPrototype] = flist2
                else:
                    flist2 = globalContainer[nameWithoutPrototype]
                flist2.append(gfunc2)
            elif nameWithoutPrototype.startswith('window.'):
                if not nameWithoutPrototype[7:] in globalContainer:
                    flist2 = []
                    globalContainer[nameWithoutPrototype[7:]] = flist2
                else:
                    flist2 = globalContainer[nameWithoutPrototype[7:]]
                flist2.append(gfunc2)

        except Exception as e:
            pass
    
    def get_global_variables(self, fullname):
        
        if not fullname in self.globalVariablesByName:
            return None
        return self.globalVariablesByName[fullname]

    def push_context(self, context):
        
        self.currentContext = context
        self.contextStack.append(self.currentContext)

    def pop_context(self):
        
        self.contextStack.pop()
        if len(self.contextStack) > 0:
            self.currentContext = self.contextStack[-1]
        else:
            self.currentContext = None

    def start_js_content(self, parent, text, firstRow = 1, firstCol = 1, jsContent = None):
        
        if self.bFullParsing:
            if jsContent:
                self.jsContent = jsContent
            else:
                self.jsContent.init_range()
            self.jsContent.startRow_in_file = firstRow
            self.jsContent.startCol_in_file = firstCol
            
            # empty lines count
            regex = r'\n[\s]*\n'
            nb = 0
            for txt in re.findall(regex, text):
                n = ( txt.count('\n') - 1 )
                if n < 0:
                    n = 0
                nb += n
            self.jsContent.objectDatabaseProperties.nbEmptyLines = nb

        else:
            if not jsContent:
                self.jsContent = JsContent(None, parent, self.file, self.config, firstRow, firstCol)
            else:
                self.jsContent = jsContent
        self.push_context(FileContext(None, self.jsContent))
        return self.jsContent
    
    def end_js_content(self):
        
        if self.requiresToEvaluate:
            requiresToKeep = []
            for requireToEvaluate in self.requiresToEvaluate:
                b = self.evaluate_require(requireToEvaluate[0], requireToEvaluate[1], True)
                if not b:
                    requiresToKeep.append(requireToEvaluate)
            self.requiresToEvaluate = requiresToKeep

        currentContext = self.contextStack[-1]
            
        if self.bFullParsing:
            resolve_all(self.jsContent, self.config.functionCallThroughParametersIdentifiers, self.jsContentsByFilename, self.htmlContentsByJS, self.htmlContentsByName, self.globalFunctionsByName, self.globalVariablesByName, self.globalClassesByName)
            
            for bracketedIdentifierToEvaluate in self.bracketedIdentifiersToEvaluate:
                b = bracketedIdentifierToEvaluate.evaluate_identifier()
                try:
                    if b and bracketedIdentifierToEvaluate.parent.parent.is_function_call():
                        resolve_element(bracketedIdentifierToEvaluate.parent.parent, self.jsContent, self.config.functionCallThroughParametersIdentifiers, self.jsContentsByFilename, self.htmlContentsByJS, self.htmlContentsByName, self.globalFunctionsByName, self.globalVariablesByName, self.globalClassesByName)
                except:
                    pass

        for openCall in self.jsContent.openCalls:
            try:
                evals = openCall.url.evaluate()
                if evals:
                    openCall.urlValues = []
                    for ev in evals:
                        openCall.urlValues.append(ev)
                if openCall.parameters:
                    evals = openCall.parameters.evaluate()
                    if evals:
                        newUrlValues = []
                        for ev in evals:
                            if ev:
                                for url in openCall.urlValues:
                                    newUrlValues.append(url + '?' + ev)
                        openCall.urlValues = list(set(newUrlValues))
            except:
                pass 
            
        for webSocket in self.jsContent.webSockets:
            try:
                evals = webSocket.param.evaluate()
                if evals:
                    webSocket.urlValues = []
                    for ev in evals:
                        webSocket.urlValues.append(ev)
            except:
                pass 
            
        self.finalize_http_requests()
        
        self.jsContent = None
        self.currentStatement = None
        self.pop_context()
        self.jsContent = None

    def start_js_content_init(self, parent):
        pass

    def end_js_content_init(self):
        pass
        
    def finalize_http_request(self, httpReq):
            
            try:
                if httpReq.ast.is_function_call():
                    firstCallPart = httpReq.ast.get_function_call_parts()[0]
                    if firstCallPart.identifier_call.name == 'request':
                        config = firstCallPart.get_parameters()[0]
                        if config.get_resolutions():
                            for resol in config.resolutions:
                                callee = resol.callee
                                if callee.parent and callee.parent.is_assignment():
                                    ov = callee.parent.get_right_operand()
                                    if ov.is_object_value():
                                        method = ov.get_item('method')
                                        url = ov.get_item('url')
                                        if method:
                                            callType = method.get_name().upper()
                                            if not callType in ['GET', 'POST', 'PUT', 'DELETE']:
                                                callType = 'GET'
                                            httpReq.setType(callType)
                                        if url:
                                            httpReq.url = url
                    elif firstCallPart.identifier_call.name in ['fetch', self.fetchFunctionName]:
                        config = firstCallPart.get_parameters()[1]
                        if config.is_identifier() and config.get_resolutions():
                            for resol in config.resolutions:
                                callee = resol.callee
                                if callee.parent and callee.parent.is_assignment():
                                    ov = callee.parent.get_right_operand()
                                    if ov.is_object_value():
                                        method = ov.get_item('method')
                                        if method:
                                            callType = method.get_name().upper()
                                            if not callType in ['GET', 'POST', 'PUT', 'DELETE']:
                                                callType = 'GET'
                                            httpReq.setType(callType)
            except:
                pass
        
    def finalize_http_requests(self):
            
        for httpReq in self.jsContent.httpRequests:
            self.finalize_http_request(httpReq)
            
        for fcall in self.currentAxiosCallWithVariables:
            firstCallPart = fcall.get_function_call_parts()[0]
            callees = get_resolution_callees(firstCallPart.identifier_call)
            for callee in callees:
#                 var instance = axios.create({});
#                 instance.get('/longRequest', {});
                try:
                    if callee in self.currentAxiosCreates:  # axios
                        try:
                            url = firstCallPart.get_parameters()[0]
                            lastKbObject = self.currentContext.statement.get_first_kb_parent()
                            httpCall = HttpCall(firstCallPart.identifier_call.get_name().upper(), url, fcall, lastKbObject, self.file)
                            httpCall.setType(firstCallPart.identifier_call.get_name().upper())
                            self.jsContent.httpRequests.append(httpCall)
                        except:
                            pass
                    elif self.currentContext.get_require(callee.get_name()):
                        if self.currentContext.get_require(callee.get_name()).param in ['superagent', 'axios']:
                            self.add_http_call(fcall, firstCallPart)
                    elif callee.parent and ( callee.parent.is_assignment() or callee.parent.is_var_declaration() ):
                        rightOper = callee.parent.get_right_operand()
                        if rightOper:
                            if rightOper.is_function_call():
                                if rightOper.get_function_call_parts()[0].get_name() == 'request':
                                    self.add_http_call(fcall, firstCallPart)
                except:
                    pass

    def start_bracketed_block(self, ast, lightObject):

        currentContext = self.contextStack[-1]
        currentStatement = currentContext.statement
        if lightObject:
            block = lightObject
        else:
            block = AstList(ast, currentStatement)
        if isinstance(currentContext, ParameterContext):
            currentContext.statement.add_parameter(block, currentContext.rang)
        self.push_context(BracketedBlockContext(self.contextStack[-1], block))
        
        return block
        
    def add_list_value(self, ast):

        currentStatement = self.contextStack[-1].statement
        currentStatement.add_value(ast)
    
    def add_module_parameter(self, param, ref):
        if self.jsContent.module:
            self.jsContent.module.parameters[param] = ref
    
    def end_bracketed_block(self):
        
        self.pop_context()
        
    def start_if_statement(self, ast):

        currentStatement = self.contextStack[-1].statement
        ifStatement = IfStatement(ast, currentStatement)
        currentStatement.add_statement(ifStatement)
        self.push_context(IfContext(self.contextStack[-1], ifStatement))
        return ifStatement
    
    def end_if_statement(self):
        
        self.pop_context()

    def start_if_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        currentStatement.increment_complexity()
        ifBlock = IfBlock(ast, currentStatement)
        currentStatement.set_if_block(ifBlock)
        self.push_context(IfBlockContext(self.contextStack[-1], ifBlock))
        return ifBlock
    
    def end_if_block(self):
        
        self.pop_context()

    def start_elseif_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        currentStatement.increment_complexity()
        ifBlock = ElseIfBlock(ast, currentStatement)
        currentStatement.add_else_if_block(ifBlock)
        self.push_context(IfBlockContext(self.contextStack[-1], ifBlock))
        return ifBlock
    
    def end_elseif_block(self):
        
        self.pop_context()

    def start_else_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        ifBlock = ElseBlock(ast, currentStatement)
        currentStatement.set_else_block(ifBlock)
        self.push_context(IfBlockContext(self.contextStack[-1], ifBlock))
        return ifBlock
    
    def end_else_block(self):
        
        self.pop_context()
        
    def start_switch_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        block = SwitchStatement(ast, currentStatement)
        currentStatement.add_statement(block)
        self.push_context(SwitchContext(self.contextStack[-1], block))
        return block
    
    def end_switch_block(self):
        
        self.pop_context()
        
    def start_switch_case_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        currentStatement.increment_complexity()
        caseBlock = SwitchCaseBlock(ast, currentStatement)
        currentStatement.add_case_block(caseBlock)
        self.push_context(SwitchCaseContext(self.contextStack[-1], caseBlock))
        return caseBlock
        
    def end_switch_case_block(self):
        self.pop_context()
        
    def start_switch_default_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        defaultBlock = SwitchDefaultBlock(ast, currentStatement)
        currentStatement.set_default_block(defaultBlock)
        self.push_context(SwitchCaseContext(self.contextStack[-1], defaultBlock))
        return defaultBlock
        
    def end_switch_default_block(self):
        self.pop_context()
       
    def start_loop(self, ast):
        currentStatement = self.contextStack[-1].statement
        currentStatement.increment_complexity()
       
    def end_loop(self):
        pass
      
    def start_do_block(self, ast):

        self.start_loop(ast)
        currentStatement = self.contextStack[-1].statement
        block = DoBlock(ast, currentStatement)
        currentStatement.add_statement(block)
        self.push_context(Context(self.contextStack[-1], block, False))
        return block
    
    def end_do_block(self):
        
        self.pop_context()
        self.end_loop()
        
    def start_while_block(self, ast):

        self.start_loop(ast)
        currentStatement = self.contextStack[-1].statement
        block = WhileBlock(ast, currentStatement)
        currentStatement.add_statement(block)
        self.push_context(Context(self.contextStack[-1], block, False))
        return block
    
    def end_while_block(self):
        
        self.pop_context()
        self.end_loop()
        
    def start_for_block(self, ast):

        self.start_loop(ast)
        currentStatement = self.contextStack[-1].statement
        block = ForBlock(ast, currentStatement)
        currentStatement.add_statement(block)
        self.push_context(Context(self.contextStack[-1], block, False))
        return block
    
    def end_for_block(self):
        
        self.pop_context()
        self.end_loop()
        
    def start_for_each_block(self, ast):

        self.start_loop(ast)
        currentStatement = self.contextStack[-1].statement
        block = ForEachBlock(ast, currentStatement)
        currentStatement.add_statement(block)
        self.push_context(Context(self.contextStack[-1], block, False))
        return block
    
    def end_for_each_block(self):
        
        self.pop_context()
        self.end_loop()

        
    def start_try_catch_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        currentStatement.increment_complexity()
        block = TryCatchBlock(ast, currentStatement)
        currentStatement.add_statement(block)
        self.push_context(Context(self.contextStack[-1], block, False))
        return block
    
    def set_try_block(self, block):

        currentStatement = self.contextStack[-1].statement
        currentStatement.block = block
        
    def start_catch_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        currentStatement.increment_complexity()
        block = CatchBlock(ast, currentStatement)
        currentStatement.add_catch_block(block)
        self.push_context(Context(self.contextStack[-1], block, False))
        return block

    def end_catch_block(self):
        
        self.pop_context()
        
    def start_finally_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        block = FinallyBlock(ast, currentStatement)
        currentStatement.set_finally_block(block)
        self.push_context(Context(self.contextStack[-1], block, False))
        return block

    def end_finally_block(self):
        
        self.pop_context()

    def end_try_catch_block(self):
        
        self.pop_context()
        
    def start_expression(self, ast):

        currentStatement = self.contextStack[-1].statement
        expr = Expression(ast, currentStatement)
        currentStatement.expression = expr
        return expr
        
    def set_expression(self, expr):

        currentStatement = self.contextStack[-1].statement
        if currentStatement:
            currentStatement.set_expression(expr)
        
    def add_start_expression(self, expr):

        currentStatement = self.contextStack[-1].statement
        if currentStatement:
            currentStatement.add_start_expression(expr)
        
    def set_termination_expression(self, expr):

        currentStatement = self.contextStack[-1].statement
        if currentStatement:
            currentStatement.set_termination_expression(expr)
        
    def set_forward_expression(self, expr):

        currentStatement = self.contextStack[-1].statement
        if currentStatement:
            currentStatement.set_forward_expression(expr)
        
    def start_start_expression(self):
        self.currentContext.is_in_start_expression = True
        
    def end_start_expression(self):
        self.currentContext.is_in_start_expression = False
        
    def start_termination_expression(self):
        self.currentContext.is_in_termination_expression = True
        
    def end_termination_expression(self):
        self.currentContext.is_in_termination_expression = False
        
    def start_forward_expression(self):
        self.currentContext.is_in_forward_expression = True
        
    def end_forward_expression(self):
        self.currentContext.is_in_forward_expression = False
        
    def add_expression_element(self, ast):

        currentStatement = self.contextStack[-1].statement
        currentStatement.expression.add_element(ast)
        
    def end_expression(self):
        
        pass

    def start_ast_block(self, ast):

        currentStatement = self.contextStack[-1].statement
        block = AstBlock(ast, currentStatement)
        if hasattr(currentStatement, 'block'):
            currentStatement.block = block
        else:
            try:
                currentStatement.statements.append(block)
            except:
                pass
        self.push_context(CurlyBracketedBlockContext(self.contextStack[-1], block, False))
        return block
        
    def end_generic_block(self, onlyWithVar, resolLinkType = True):
        self.pop_context()

    def end_ast_block(self):
        self.end_generic_block(True)
        
    def start_object_value(self, name, ast, lightObject):

        currentContext = self.contextStack[-1]
        currentStatement = currentContext.statement
        if lightObject:
            block = lightObject
        else:
            block = None
        if not block:
            block = ObjectValue(ast, currentStatement)
        if isinstance(currentContext, ParameterContext):
            currentContext.statement.add_parameter(block, currentContext.rang)
        self.push_context(ObjectValueContext(self.contextStack[-1], name, block))
        
        return block
    
    def end_object_value(self):
        self.end_generic_block(False, False)
        
    def start_object_destructuration(self, ast, lightObject):

        currentContext = self.contextStack[-1]
        currentStatement = currentContext.statement
        if lightObject:
            block = lightObject
        else:
            block = None
        if not block:
            block = ObjectDestructuration(ast, currentStatement)
        if isinstance(currentContext, ParameterContext):
            currentContext.statement.add_parameter(block, currentContext.rang)
        self.push_context(ObjectDestructurationContext(self.contextStack[-1], block))
        
        return block
    
    def end_object_destructuration(self):
        self.end_generic_block(False, False)

    def add_object_value_variable(self, ident):
        self.currentContext.add_variable(ident, True)

    def get_js_function_call_function(self):
        # returns the function if we are directly under a js function call (function () {})();
        if self.currentContext.parentContext and self.currentContext.parentContext.is_js_function_call_context():
            return self.currentContext.parentContext.statement.function;
        return None
    
    def create_function(self, bArrow, name, prefix, parent, token, file = None, isThis = False, emptyLines = False):

        if bArrow:
            return ArrowFunction(name, prefix, parent, token, file, isThis, emptyLines)
        return Function(name, prefix, parent, token, file, isThis, emptyLines)
    
    def start_function(self, name, prefix, ast, is_statement = False, lightFunc = None, funcDirectlyCalled = False, bArrow = False, exportDefault = False):

        try:
            fullname = name
            if prefix and name:
                fullname = prefix + '.' + name
                
            if not self.bFullParsing:
                if self.currentContext.is_function_context() or ( self.currentContext.is_object_value_context() and self.currentContext.parentContext and self.currentContext.parentContext.is_function_context() and not isinstance(self.currentContext.parentContext.statement, ArrowFunction)):
    #             if self.currentContext.is_function_context():
                    currentFunctionPrefix = prefix
                    if prefix and fullname and fullname.startswith('self.'):
                        if currentFunctionPrefix == 'self':
                            currentFunctionPrefix = ''
                        else:
                            currentFunctionPrefix = currentFunctionPrefix[:5]
                    elif not prefix:
                        currentFunctionPrefix = ''
                    statementFullname = ''
                    try:
    #                     statementFullname = self.currentContext.statement.get_fullname()
                        if self.currentContext.is_function_context():
                            statementFullname = self.currentContext.statement.get_fullname()
                        else:
                            if self.currentContext.parentContext:
                                statementFullname = self.currentContext.parentContext.statement.get_fullname()
                            else:
                                statementFullname = self.currentContext.statement.get_fullname()
                        while '.NONAME' in statementFullname:
                            statementFullname = statementFullname[:statementFullname.find('.NONAME')]
                        if fullname.startswith('self.') or fullname.startswith('this.'):
                            globalFullname = statementFullname + '.' + fullname[5:]
                        else:
                            globalFullname = statementFullname + '.' + fullname
                    except:
                        globalFullname = fullname
                        
                    if globalFullname and globalFullname.startswith('NONAME') and '.' in globalFullname:
                        globalFullname = globalFullname[globalFullname.find('.')+1:]
                        
                    if currentFunctionPrefix:
                        if currentFunctionPrefix == 'self' or currentFunctionPrefix == 'this':
                            function = self.create_function(bArrow, name, statementFullname, None, ast, self.file, True, self.emptyLines)
                        else:
                            if statementFullname:
                                function = self.create_function(bArrow, name, statementFullname + '.' + currentFunctionPrefix, None, ast, self.file, False, self.emptyLines)
                            else:
                                function = self.create_function(bArrow, name, currentFunctionPrefix, None, ast, self.file, False, self.emptyLines)
                    else:
                        function = self.create_function(bArrow, name, statementFullname, None, ast, self.file, False, self.emptyLines)
                else:
                    globalFullname = fullname
                    function = self.create_function(bArrow, name, prefix, None, ast, self.file, False, self.emptyLines)
                    self.currentContext.add_function(function)
                    
                if function and exportDefault:
                    self.jsContent.defaultExportedAst = function
                if name:
                    otherGlobalFullname = None
                    pref = self.get_current_prefix()
                    if pref:
                        globalFullname = pref + '.' + globalFullname
                    if self.currentContext and self.currentContext.is_file_context() and '.' in globalFullname:
                        pref = globalFullname[: globalFullname.find('.')]
                        if pref in self.namespacePrefixes:
                            otherGlobalFullname = self.namespacePrefixes[pref] + globalFullname[globalFullname.find('.'):]
                        
                    self.jsContent.add_global_function(globalFullname, function)
                        
                    if globalFullname.startswith('module.exports.'):
                        self.jsContent.add_global_function(globalFullname[15:], function)
                    elif globalFullname.startswith('exports.'):
                        self.jsContent.add_global_function(globalFullname[8:], function)
                    self.add_global(function, True, None, None, False, otherGlobalFullname)
                self.push_context(FunctionContext(self.contextStack[-1], function))
                function.directlyCalled = funcDirectlyCalled
                function.lineCount = function.get_line_count(self.emptyLines)
                return function
            
            currentContext = self.contextStack[-1]
            currentStatement = currentContext.statement
            function = None
            if self.currentContext.parentContext and (self.currentContext.parentContext.is_function_context() or (isinstance(self.currentContext.parentContext, VarDeclarationContext) and self.currentContext.parentContext.parentContext and self.currentContext.parentContext.parentContext.is_function_context())):
                try:
                    if self.currentContext.parentContext.is_function_context():
                        if fullname.startswith('self.') or fullname.startswith('this.'):
                            globalFullname = self.currentContext.parentContext.statement.get_fullname() + '.' + fullname[5:]
                        else:
                            if self.currentContext.is_object_value_context():
                                globalFullname = fullname
                            else:
                                globalFullname = self.currentContext.parentContext.statement.get_fullname() + '.' + fullname
                    else:
                        if fullname.startswith('self.') or fullname.startswith('this.'):
                            globalFullname = self.currentContext.parentContext.parentContext.statement.get_fullname() + '.' + fullname[5:]
                        else:
                            globalFullname = self.currentContext.parentContext.parentContext.statement.get_fullname() + '.' + fullname
                except:
                    globalFullname = fullname
            else:
                jsFunction = self.get_js_function_call_function()
                if jsFunction and jsFunction.name:
                    globalFullname = jsFunction.name + '.' + fullname
                else:
                    if currentContext.parentContext and currentContext.parentContext.parentContext and currentContext.parentContext.parentContext.is_assignment_context():
                        if currentContext.parentContext.parentContext.statement.get_left_operand().get_name():
#                             globalFullname = currentContext.parentContext.parentContext.statement.get_left_operand().get_name() + '.' + str(fullname)
                            pref = self.get_current_prefix()
                            if pref:
                                globalFullname = pref + '.' + str(fullname)
                            else:
                                globalFullname = str(fullname)
                        else:
                            globalFullname = str(fullname)
                    else:
                        pref = self.get_current_prefix()
                        if pref:
                            globalFullname = pref + '.' + str(fullname)
                        else:
                            globalFullname = fullname
    #                 globalFullname = fullname
            if currentContext.wasPreprocessed and globalFullname:
                function = self.jsContent.get_global_function(globalFullname, True)
            elif exportDefault and self.jsContent.defaultExportedAst:
                function = self.jsContent.defaultExportedAst
            if function:
                if funcDirectlyCalled:
                    currentContext.statement.function = function
                function.set_parent(currentStatement)
                function.set_name(function.get_name(), function.get_fullname())
                if is_statement:
                    currentStatement.add_statement(function)
            if lightFunc:
                function = lightFunc
            if not function:
                function = self.create_function(bArrow, name, prefix, currentStatement, ast, self.file, False, self.emptyLines)
                if funcDirectlyCalled:
                    currentContext.statement.function = function
                if is_statement:
                    currentStatement.add_statement(function)
    
            if self.bFullParsing:
                
                if funcDirectlyCalled:
                    p = function.parent.get_first_kb_parent()
                    if p:
                        p.add_resolution(function, 'callLink')
    
                if isinstance(currentContext, ParameterContext):
                    currentContext.statement.add_parameter(function, currentContext.rang)
        
                if name:
                    currentContext.add_function(function)
                        
            self.push_context(FunctionContext(self.contextStack[-1], function))
            return function
        except:
            cast.analysers.log.debug(str(traceback.format_exc()))
            return None
      
    def end_function(self, bArrow = False):

        if not self.bFullParsing:
            self.pop_context()
            return

        self.end_generic_block(False)
        
        if self.probableHttpRequest:
            if self.submitCallEncontered:
                self.jsContent.httpRequests.append(self.probableHttpRequest)
                self.submitCallEncontered = False
            self.probableHttpRequest = None

    def start_arrow_function(self, name, prefix, ast, is_statement = False, lightFunc = None, funcDirectlyCalled = False):

        return self.start_function(name, prefix, ast, is_statement, lightFunc, funcDirectlyCalled, True)
      
    def end_arrow_function(self):

        return self.end_function(True)
        
    def start_unknown_token(self, token):
        
        currentContext = self.contextStack[-1]
        currentStatement = currentContext.statement
        if not isinstance(token, AstToken):
            astToken = AstToken(token, currentStatement)
        else:
            astToken = token
        if isinstance(currentContext, ParameterContext):
            currentContext.statement.add_parameter(astToken, currentContext.rang)
        return astToken

    def end_unknown_token(self, token):
        
        pass
        
    def start_jsx_expression(self, token):
        
        currentContext = self.contextStack[-1]
        currentStatement = currentContext.statement
        astExpr = JsxExpression(token, currentStatement)
        self.push_context(JsxContext(currentContext, astExpr))
#         if isinstance(currentStatement, JsxExpression):
#             currentStatement.subExpressions.append(astExpr)
        return astExpr

    def end_jsx_expression(self):
        self.pop_context()
    
    def start_operator_token(self, token):
        
        currentContext = self.contextStack[-1]
        currentStatement = currentContext.statement
        astToken = AstOperator(token, currentStatement)
        if isinstance(currentContext, ParameterContext):
            currentContext.statement.add_parameter(astToken, currentContext.rang)
        return astToken

    def end_operator_token(self, token):
        
        pass
    
    def start_function_call(self, identifier, parenthesedBlock, isStatement = True):
        
        currentContext = self.contextStack[-1]
            
        currentStatement = currentContext.statement
        previous = False
        isLoop = False
        if identifier.name in self.config.functionCallWithAreLoops:
            isLoop = True
        functionCall = FunctionCall(identifier, identifier, currentStatement, isLoop)
#         functionCall = FunctionCall(identifier, None, currentStatement, isLoop)
        if identifier.name == 'require':
            functionCall.isRequire = True
                
        if isinstance(currentStatement, JsContent) or isinstance(currentStatement, Function) or isinstance(currentStatement, Class) or isinstance(currentStatement, AstBlock):
            if not previous:
                if isStatement:
                    currentStatement.add_statement(functionCall)

        if self.bFullParsing:
            if isinstance(currentContext, ParameterContext):
                currentContext.statement.add_parameter(functionCall, currentContext.rang)
    
            functionCall.add_token(parenthesedBlock)
            functionCall.add_token(identifier.tokens[0])
            functionCall.add_token(parenthesedBlock)

        self.push_context(FunctionCallContext(self.contextStack[-1], functionCall))
        return functionCall
    
    def start_function_call_part(self, identifier, tokens):
        
        currentContext = self.contextStack[-1]
        functionCall = self.contextStack[-1].statement
        functionCallPart = FunctionCallPart(identifier, tokens)
        
        if 'submit' in identifier.get_name().lower():
            self.submitCallEncontered = True

        if identifier.is_identifier():
            if identifier.is_func_call():
                # if we are in case of "return new f()" in "f" function, we don't do resolution to avoid link to itself.
                newItself = False
                try:
                    if functionCall.parent.is_return_new_statement():
                        lastFunctionContext = currentContext.get_last_kb_context()
                        if lastFunctionContext:
                            funcName = lastFunctionContext.statement.get_name()
                            if funcName == identifier.get_name():
                                newItself = True
                except:
                    pass
                if not newItself:
                    currentContext.add_unresolved_identifier(IdentifierToResolve(identifier, self.currentContext.statement, None, identifier.create_bookmark(self.file), 'callLink'))
            
        functionCallPart.parent = functionCall
        self.push_context(FunctionCallPartContext(self.contextStack[-1], functionCallPart))
        functionCall.functionCallParts.append(functionCallPart)
        return functionCallPart
    
    def start_parameter(self, rang = -1):
        
        self.push_context(ParameterContext(self.contextStack[-1], self.contextStack[-1].statement, rang))
    
    def end_parameter(self):
        
        self.pop_context()

    def add_unresolved_identifier(self, identifier, callType):
        self.currentContext.add_unresolved_identifier(IdentifierToResolve(identifier, self.currentContext.statement, None, identifier.create_bookmark(self.file), callType))
        
    def add_identifier(self, identifier, bResolve = True):
        
        if not isinstance(identifier, Identifier):
            return
        
        currentContext = self.contextStack[-1]
              
        if isinstance(currentContext, ImportStatementContext):
            return
          
        if isinstance(currentContext, ParameterContext):
            currentContext.statement.add_parameter(identifier, currentContext.rang)
    
    def add_string(self, s):
        
        currentContext = self.contextStack[-1]
        if currentContext.statement:
            s.parent = currentContext.statement
            
        if isinstance(currentContext, ParameterContext):
            currentContext.statement.add_parameter(s, currentContext.rang)
            
        if self.bFullParsing:
            text = s.get_text()
            index = 0
            index = text.find('${', index)
            while index >= 0:
                end = text.find('}', index + 1)
                varName = text[index+2: end]
                ident = Identifier(s, varName, s.tokens[0])
                self.add_identifier(ident)
                s.add_identifier(ident)
                index = text.find('${', end)
    
    def start_function_parameters(self):
        self.currentContext.start_parameters()

    def end_function_parameters(self):
        self.currentContext.end_parameters()
        
    def start_js_function_call(self, func, funcParenthesedBlock, callToken, parenthesedBlock, isExpression = False):
        
        currentStatement = self.contextStack[-1].statement
        functionCall = JSFunctionCall(callToken, func, currentStatement)
        if isExpression:
            self.currentContext.attach(functionCall)
        else:
            currentStatement.add_statement(functionCall)
        self.push_context(FunctionCallContext(self.contextStack[-1], functionCall, True))
        functionCall.add_token(funcParenthesedBlock)
        if callToken:
            functionCall.add_token(callToken)
        functionCall.add_token(parenthesedBlock)
        return functionCall
    
    def start_define(self, token):
        
        currentStatement = self.contextStack[-1].statement
        define = Define(token, currentStatement)
        currentStatement.add_statement(define)
        self.push_context(DefineContext(self.contextStack[-1], define))
        return define
      
    def start_require(self, token):
        
        currentStatement = self.contextStack[-1].statement
        require = Require(token, currentStatement)
        currentStatement.add_statement(require)
        self.push_context(RequireContext(self.contextStack[-1], require))
        return require
    
    def start_identifier(self, identifier):
        self.push_context(IdentifierContext(self.contextStack[-1]))

    def end_identifier(self):
        self.pop_context()

    def add_parameter(self, paramName, param):
        
        currentStatement = self.currentContext.statement
        
        if currentStatement.is_function():
            param.parent = currentStatement
            self.currentContext.add_variable(param, True)
        
        currentStatement.add_parameter(param)
        
        parentContext = self.currentContext.parentContext
        if parentContext:
            parentContext = parentContext.parentContext
            if parentContext:
                parentContext = parentContext.parentContext
                if parentContext:
                    try:
                        if parentContext.statement.module:
                            paramName = param.get_name()
                            if paramName in parentContext.statement.module.parameters:
                                ref = parentContext.statement.module.parameters[paramName]
                                parentContext.statement.module.parameters[param] = ref
                                del parentContext.statement.module.parameters[paramName]
                    except:
                        pass
        
    def evaluate_require(self, fcall, fcallpart, withEvaluation = True):
        
            try:
                if withEvaluation:
                    evs = fcallpart.parameters[0].evaluate()
                    if evs:
                        param = evs[0]
                    else:
                        param = None
                elif fcallpart.parameters[0].is_string():
                    param = fcallpart.parameters[0].name
                else:
                    return False
                
                try:
                    originalParam = param
                    if not param.endswith('.js'):
                        param += '.js'
                    try:
                        identifier = fcall.parent.get_left_operand()
                        if originalParam == 'node-fetch':
                            self.fetchFunctionName = identifier.get_name()
                        elif originalParam == 'axios':
                            self.axiosVariableName = identifier.get_name()
                        if identifier.is_object_destructuration():
                            for key in identifier.items.keys:
                                self.currentContext.add_require(key, originalParam)
                        else:
                            self.currentContext.add_require(identifier, originalParam)
                    except:
                        identifier = None
                        
                except:
                    return True
            except:
                return True
            return True
        
    def end_function_call(self):
        # we resolve here require statement
        fcall = self.currentContext.statement
        fcallparts = fcall.get_function_call_parts()
        firstCallPart = fcallparts[0]
        if firstCallPart.identifier_call.name == 'require':
            # evaluation can not be done here because resolution is not done when requireparameter needs an evaluation
            b = self.evaluate_require(fcall, firstCallPart, False)
            if not b:
                self.requiresToEvaluate.append((fcall, firstCallPart))

        elif firstCallPart.identifier_call.name in ['fetch', self.fetchFunctionName] and not firstCallPart.identifier_call.get_prefix():

            lastKbObject = self.currentContext.statement.get_first_kb_parent()
            callType = 'GET'
            secondParameter = None
            cfg = None
            try:
                secondParameter = firstCallPart.get_parameters()[1]
                if secondParameter.is_object_value():
                    typ = secondParameter.get_item('method')
                    if typ:
                        callType = typ.get_name()
                else:
                    cfg = secondParameter
            except:
                secondParameter = None
            httpCall = HttpCall(callType, firstCallPart.get_parameters()[0], fcall, lastKbObject, self.file)
            httpCall.config = cfg
            httpCall.setType(callType)
            self.jsContent.httpRequests.append(httpCall)

        elif firstCallPart.identifier_call.name == 'EventSource' and not firstCallPart.identifier_call.get_prefix():

            lastKbObject = self.currentContext.statement.get_first_kb_parent()
            callType = 'GET'
            firstParameter = None
            try:
                firstParameter = firstCallPart.get_parameters()[0]
                httpCall = HttpCall(callType, firstParameter, fcall, lastKbObject, self.file)
                httpCall.setType(callType)
                self.jsContent.eventSourceRequests.append(httpCall)
                assign = fcall.get_current_assignment()
                if assign:
                    leftOperand = assign.get_left_operand()
                    self.serverEvents[leftOperand.get_name()] = httpCall
            except:
                pass

        elif firstCallPart.identifier_call.get_prefix() in ['axios', 'request']:
            httpCall = self.add_http_call(fcall, firstCallPart)
            if firstCallPart.identifier_call.get_name() == 'request':
                httpCall.ovUrlName = 'url'
                httpCall.ovTypeName = 'method'
        elif firstCallPart.identifier_call.get_prefix() and  firstCallPart.identifier_call.get_name() in ['request', 'create']:
            requireDecl = self.currentContext.get_require(firstCallPart.identifier_call.get_prefix())
            if requireDecl and requireDecl.param == 'axios':
                httpCall = self.add_http_call(fcall, firstCallPart)
                if firstCallPart.identifier_call.get_name() == 'request':
                    httpCall.ovUrlName = 'url'
                    httpCall.ovTypeName = 'method'
        elif firstCallPart.identifier_call.get_name() in ['get', 'post', 'put', 'delete']:
            if firstCallPart.identifier_call.get_prefix():
                requireDecl = self.currentContext.get_require(firstCallPart.identifier_call.prefix)
                if requireDecl:
                    if requireDecl.param == 'superagent':
                        self.add_http_call(fcall, firstCallPart)
                    elif requireDecl.param == 'axios':
                        self.currentAxiosCallWithVariables.append(fcall)
                else:
                    self.currentAxiosCallWithVariables.append(fcall)
            else:
                self.currentAxiosCallWithVariables.append(fcall)
        elif firstCallPart.identifier_call.get_name() == 'request' and not firstCallPart.identifier_call.get_prefix() and len(firstCallPart.get_parameters()) >= 2:
            self.add_http_call(fcall, firstCallPart, True)
        elif firstCallPart.identifier_call.name in ['axios', self.axiosVariableName]:
            try:
                callType = 'GET'
                firstParam = firstCallPart.get_parameters()[0]
                if firstParam.is_object_value():
                    callType = firstParam.get_item('method').get_name().upper()
                    url = firstParam.get_item('url')
                else:
                    url = firstParam
    
                lastKbObject = self.currentContext.statement.get_first_kb_parent()
                httpCall = HttpCall(callType, url, fcall, lastKbObject, self.file)
                httpCall.setType(callType)
                self.jsContent.httpRequests.append(httpCall)
            except:
                pass
            
        self.pop_context()

    def add_http_call(self, fcall, firstCallPart, firstParamIsUrl = False):
            httpCall = None
            try:
                cfg = None
                callType = 'GET'
                create = True
                url = firstCallPart.get_parameters()[0]
                if firstCallPart.identifier_call.name in ['get', 'head']:
                    callType = 'GET'
                elif firstCallPart.identifier_call.name == 'post':
                    callType = 'POST'
                elif firstCallPart.identifier_call.name == 'delete':
                    callType = 'DELETE'
                elif firstCallPart.identifier_call.name == 'put':
                    callType = 'PUT'
                elif firstCallPart.identifier_call.name == 'request':
                    if firstParamIsUrl:
                        callType = 'GET'
                    else:
                        config = firstCallPart.get_parameters()[0]
                        if config.is_object_value():
                            method = config.get_item('method')
                            url = config.get_item('url')
                            if method:
                                callType = method.get_name().upper()
                                if not callType in ['GET', 'POST', 'PUT', 'DELETE']:
                                    callType = 'GET'
                        else:
                            cfg = config
                else:
                    create = False
                    if firstCallPart.identifier_call.name == 'create' and fcall.parent and fcall.parent.is_assignment():
                        self.currentAxiosCreates.append(fcall.parent.get_left_operand())
    
                if create:
#                     lastKbObject = self.currentContext.statement.get_first_kb_parent()
                    lastKbObject = fcall.get_first_kb_parent()
                    httpCall = HttpCall(callType, url, fcall, lastKbObject, self.file)
                    httpCall.config = cfg
                    httpCall.setType(callType)
                    self.jsContent.httpRequests.append(httpCall)
            except:
                pass
            return httpCall
        
    def end_function_call_part(self):
        
#       Stores following kinds of statements  xhttp.open("GET", "ajax_info.txt", false);
        functionCallPart = self.currentContext.statement
        if functionCallPart.get_name() == 'open' and functionCallPart.identifier_call.get_prefix():
            if functionCallPart.identifier_call.get_prefix() == 'window':
                params = functionCallPart.get_parameters()
                if params and len(params) >= 1:
                    firstParam = functionCallPart.get_parameters()[0]
                    lastKbObject = functionCallPart.get_first_kb_parent()
                    self.jsContent.httpRequests.append(HttpCall('window.open', firstParam, firstParam, lastKbObject, self.file))
            else:
                params = functionCallPart.get_parameters()
                if params and len(params) >= 2:
                    firstParam = functionCallPart.get_parameters()[0]
                    if firstParam.is_string():
                        secondParam = functionCallPart.get_parameters()[1]
                        lastKbObject = functionCallPart.get_first_kb_parent()
                        self.jsContent.openCalls.append(self.OpenCall(firstParam.get_text(), secondParam, functionCallPart, lastKbObject, self.file))
        
        elif functionCallPart.get_name() == 'send' and functionCallPart.identifier_call.get_prefix():
            if self.jsContent.openCalls and functionCallPart.get_parameters():
                openCall = self.jsContent.openCalls[-1]
                try:
                    if self.jsContent.xmlHttpRequests and self.jsContent.xmlHttpRequests[-1].get_name() == functionCallPart.identifier_call.get_prefix():
                        openCall.parameters = functionCallPart.get_parameters()[0]
                except:
                    pass
                
        elif functionCallPart.get_name().lower() == 'executesql':
            params = functionCallPart.get_parameters()
            if params and len(params) >= 1:
                firstParam = functionCallPart.get_parameters()[0]
                lastKbObject = functionCallPart.get_first_kb_parent()
                self.jsContent.executeSqls.append(ExecuteSQL(firstParam, firstParam, lastKbObject.get_kb_symbol(), self.file))

        self.pop_context()

    def set_jscontent_ast(self, statements, jsContentAst):
        jsContentAst.children = statements
        
        if not self.jsContent.tokens:
            self.jsContent.tokens.append(jsContentAst)
        
        self.jsContent.lineCount = self.jsContent.get_line_count(self.emptyLines)
        
    def end_js_function_call(self):
        
        unresolvedToRemove = []
        currentContext = self.contextStack[-1]
        self.pop_context()

    def end_define(self):
        
        self.pop_context()

    def end_require(self):
        
        self.pop_context()

    def start_import_statement(self, token, isType):
        
        currentStatement = self.contextStack[-1].statement
        if self.bFullParsing:
            stmt = ImportStatement(token, currentStatement, isType)
            currentStatement.add_statement(stmt)
            self.push_context(ImportStatementContext(self.contextStack[-1], stmt))
            return stmt
        return None

    def end_import_statement(self):
        if self.bFullParsing:
            importStatement = self.currentContext.statement
            _from = importStatement._from
            fileToSearch1 = ''
            fileToSearch2 = ''
            try:
                text = _from.get_text() # filename
                currentFilepath = os.path.dirname(os.path.abspath(self.file.get_path()))
                fileToSearch1 = os.path.abspath(os.path.join(currentFilepath, text + ('.js' if not text.endswith('.js') else '')))
                fileToSearch2 = os.path.abspath(os.path.join(currentFilepath, text + ('.jsx' if not text.endswith('.jsx') else '')))
                fileToSearch3 = os.path.abspath(os.path.join(os.path.join(currentFilepath, text), 'index.js'))
                fileToSearch4 = os.path.abspath(os.path.join(os.path.join(currentFilepath, text), 'index.jsx'))
                pass
            except:
                pass
            for what in importStatement._what:
                try:
                    text = what[0].get_name()
                    self.imports[text] = what[0]
                    resolved = False
                    if text in self.globalClassesByName:
                        for cl in self.globalClassesByName[text]:
                            if cl.file.get_path() in [fileToSearch1, fileToSearch2, fileToSearch3, fileToSearch4]:
                                what[0].add_resolution(cl.kbSymbol, None)
                                resolved = True
                    if not resolved and text in self.globalFunctionsByName:
                        for func in self.globalFunctionsByName[text]:
                            if func.file.get_path() in [fileToSearch1, fileToSearch2, fileToSearch3, fileToSearch4]:
                                what[0].add_resolution(func.kbSymbol, None)
                                resolved = True
                    if not resolved and text in self.globalVariablesByName:
                        for v in self.globalVariablesByName[text]:
                            if v.file.get_path() in [fileToSearch1, fileToSearch2, fileToSearch3, fileToSearch4]:
                                what[0].add_resolution(v.identifier, None)
                                resolved = True
                    if not resolved:
                        if fileToSearch1 in self.jsContentsByFilename:
                            jsContent = self.jsContentsByFilename[fileToSearch1]
                            try:
                                exportedDefault = jsContent.get_exported_default()
                            except:
                                exportedDefault = jsContent.get_exported_default()
                            if exportedDefault:
                                what[0].add_resolution(exportedDefault, None)
                                resolved = True
                            elif text == '*':
                                what[0].add_resolution(jsContent, None)
                                pass
                    if not resolved:
                        if fileToSearch3 in self.jsContentsByFilename:
                            jsContent = self.jsContentsByFilename[fileToSearch3]
                            try:
                                exportedDefault = jsContent.get_exported_default()
                            except:
                                exportedDefault = jsContent.get_exported_default()
                            if exportedDefault:
                                what[0].add_resolution(exportedDefault, None)
                                resolved = True
                except:
                    pass
            self.pop_context()
        
    def start_any_statement(self, token, isReturnOv = False, bFullParsing = True):
        
        currentStatement = self.contextStack[-1].statement
        stmt = AnyStatement(token, currentStatement)
        if bFullParsing:
            currentStatement.add_statement(stmt)
        if stmt.is_continue_statement():
            currentStatement.increment_complexity()
        self.push_context(AnyStatementContext(self.contextStack[-1], stmt, isReturnOv))
        return stmt

    def end_any_statement(self):
        currentStatement = self.contextStack[-1].statement
        if currentStatement.is_export_default_statement():
            self.jsContent.defaultExportedAst = currentStatement.elements[-1]
        self.pop_context()

    def add_simple_expression(self, token):
        
        self.currentContext.attach(token)
        return token

    def start_any_expression(self, token):
        
        currentStatement = self.contextStack[-1].statement
        expr = AnyExpression(token, currentStatement)
        self.currentContext.attach(expr)
        self.push_context(AnyExpressionContext(self.contextStack[-1], expr))
        return expr

    def add_any_expression_item(self, item):
        
        expr = self.contextStack[-1].statement
        if isinstance(expr, AnyExpression):
            expr.add_element(item)

    def end_any_expression(self):
        self.pop_context()

    def start_binary_expression(self, operatorToken, tokenList):
        
        currentStatement = self.contextStack[-1].statement
        textOperator = operatorToken.name
        if textOperator.startswith('=='):
            expr = EqualBinaryExpression(tokenList, currentStatement)
        elif textOperator.startswith('!='):
            expr = NotEqualBinaryExpression(tokenList, currentStatement)
        else:
            expr = BinaryExpression(tokenList, currentStatement)
            if expr.get_operator_text() in ['&&', '||']:
                expr.increment_complexity()
        self.currentContext.attach(expr)
        self.push_context(BinaryExpressionContext(self.contextStack[-1], expr))
        return expr

    def end_binary_expression(self):
        
        self.pop_context()

#     shortForm = True if "+="
    def start_addition(self, tokenList, shortForm = False, bFullParsing = True):
        
        currentStatement = self.contextStack[-1].statement
        expr = AdditionExpression(tokenList, currentStatement, shortForm)
        if shortForm:
            currentStatement.add_statement(expr)
        self.currentContext.attach(expr)
        self.push_context(BinaryExpressionContext(self.contextStack[-1], expr))
        return expr

    def end_addition(self):
        
        self.end_binary_expression()

    def start_or(self, tokenList):
        
        currentStatement = self.contextStack[-1].statement
        expr = OrExpression(tokenList, currentStatement)
        self.currentContext.attach(expr)
        self.push_context(BinaryExpressionContext(self.contextStack[-1], expr))
        return expr

    def end_or(self):
        
        self.end_binary_expression()

    def start_in(self, tokenList):
        
        currentStatement = self.contextStack[-1].statement
        expr = InExpression(tokenList, currentStatement)
        self.currentContext.attach(expr)
        self.push_context(BinaryExpressionContext(self.contextStack[-1], expr))
        return expr

    def end_in(self):
        
        self.end_binary_expression()

    def start_unary_expression(self, tokenList):
        
        currentStatement = self.contextStack[-1].statement
        expr = UnaryExpression(tokenList, currentStatement)
        self.currentContext.attach(expr)
        self.push_context(UnaryExpressionContext(self.contextStack[-1], expr))
        return expr

    def end_unary_expression(self):
        
        self.pop_context()

    def start_not_expression(self, tokenList):
        
        currentStatement = self.contextStack[-1].statement
        expr = NotExpression(tokenList, currentStatement)
        self.currentContext.attach(expr)
        self.push_context(UnaryExpressionContext(self.contextStack[-1], expr))
        return expr

    def end_not_expression(self):
        
        self.end_unary_expression()

    def is_global_context(self, currentContext):
        
        if currentContext.is_file_context():
            # FileContext is global
            return True
        
        if currentContext.is_function_context():
            if self.contextStack[-2].is_file_context():
                # FunctionContext directly under FileContext is global
                # Example: f is global
                #    function f() {
                #    }
                return True
            elif self.contextStack[-2].is_function_call_context() and self.contextStack[-2].isJSFunctionCall and self.contextStack[-3].is_file_context():
                # FunctionContext directly under FileContext is global
                # Example: f is global
                #    (function f() {
                #    })()
                return True
            elif self.contextStack[-2].is_assignment_context():
                if self.contextStack[-3].is_file_context():
                    # FunctionContext directly under FileContext is global
                    # Example: f is global
                    #    f = function() {
                    #    }
                    return True
                elif self.contextStack[-4].is_file_context():
                    # FunctionContext directly under FileContext is global
                    # Example: f is global
                    #    var f = function() {
                    #    }
                    return True
        
        # We are no more directly in global FileContext

        if not isinstance(currentContext, VarDeclarationContext) and not isinstance(currentContext, AssignmentContext):
            return False
                
        if self.contextStack[-2].is_file_context():
            # Example: v is global
            #    var v = 1;
            return True
        
        if self.contextStack[-2].is_function_context():
            if self.contextStack[-3].is_file_context():
                # Example: v is global (can be called through f.v
                # function f() {
                #    var v = 1;
                # }
                return True
            elif self.contextStack[-3].is_assignment_context():
                if self.contextStack[-4].is_file_context():
                    # Example: v is global (can be called through f.v)
                    # f = function() {
                    #    var v = 1;
                    # }
                    return True
                elif self.contextStack[-5].is_file_context():
                    # Example: v is global (can be called through f.v)
                    # var f = function() {
                    #    var v = 1;
                    # }
                    return True
            elif self.contextStack[-3].is_function_call_context() and self.contextStack[-3].isJSFunctionCall:
                if self.contextStack[-4].is_file_context():
                    # Example: v is global (can be called through f.v)
                    # (f = function() {
                    #    var v = 1;
                    # })();
                    return True
        
        return False
        
    def start_assignment(self, isVar, token, exported = False):

        currentContext = self.contextStack[-1]

        if not self.bFullParsing:
            fn = ''
            try:
                fn = token.get_fullname()
            except:
                pass
            if currentContext.is_file_context():
                try:
                    self.jsContent.add_global_variable(token.get_fullname(), token)
                    return True
                except:
                    pass
            elif currentContext.is_function_context() and ( isVar or fn.startswith('module.exports') or fn.startswith('this') ):
                if currentContext.parentContext.is_file_context():
                    try:
                        self.jsContent.add_global_variable(token.get_fullname(), token)
                        return True
                    except:
                        pass
                elif currentContext.parentContext.is_function_call_context() and currentContext.parentContext.isJSFunctionCall and currentContext.parentContext.parentContext and currentContext.parentContext.parentContext.is_file_context():
                    try:
                        self.jsContent.add_global_variable(token.get_fullname(), token)
                        return True
                    except:
                        pass
            return False
        
        currentStatement = currentContext.statement
        
        if isVar and self.bFullParsing:
            try:
                assignment = currentStatement.elements[currentContext.current_element_index]
                if currentContext.is_file_context():
                    gvar = self.jsContent.get_global_variable(token.get_fullname())
                    if gvar:
                        assignment.set_left_operand(gvar) 
                        gvar.set_parent(assignment) 
            except IndexError:
                assignment = None
        else:
            assignment = None
            
        if not assignment:
            assignment = Assignment(token, currentStatement, isVar, exported)
#             if currentContext.is_file_context() or (isinstance(currentContext, VarDeclarationContext) and (self.contextStack[-2].is_file_context() or (self.contextStack[-2].is_function_context() and self.contextStack[-3].is_file_context()))):
            if self.is_global_context(currentContext):
                try:
                    gvar = self.jsContent.get_global_variable(token.get_fullname())
                    if gvar:
                        assignment.set_left_operand(gvar)
                        gvar.set_parent(assignment) 
                except:
                    pass
            if not isinstance(currentStatement, VarDeclaration):
                currentStatement.add_statement(assignment)
        self.push_context(AssignmentContext(self.contextStack[-1], assignment))
        return assignment

    def start_left_operand(self):
        
        if isinstance(self.currentContext, BinaryExpressionContext):
            self.currentContext.is_left_operand = True
            self.currentContext.is_right_operand = False

    def end_left_operand(self):
        
        if isinstance(self.currentContext, BinaryExpressionContext):
            self.currentContext.is_left_operand = False

    def start_right_operand(self):
        
        if isinstance(self.currentContext, BinaryExpressionContext):
            self.currentContext.is_left_operand = False
            self.currentContext.is_right_operand = True

    def end_right_operand(self):
        
        if isinstance(self.currentContext, BinaryExpressionContext):
            self.currentContext.is_right_operand = False

    def set_var_declaration(self, ident):

        currentContext = self.contextStack[-1]
        if isinstance(currentContext, VarDeclarationContext):
            currentContext = self.contextStack[-2]
        currentContext.add_variable(ident, True)
    
    def set_left_operand(self, token):
        
        if isinstance(self.currentContext, BinaryExpressionContext):
            self.currentContext.statement.set_left_operand(token)
            return
        
        currentStatement = self.currentContext.statement
        currentStatement.set_left_operand(token)
        token.parent = currentStatement
        if currentStatement.is_var():
            currentContext = self.contextStack[-2]
            if isinstance(currentContext, VarDeclarationContext):
                currentContext = self.contextStack[-3]
            currentContext.add_variable(token, True)
        elif token.is_identifier():
            if token.starts_with_this():
                cmpt = -2
                previousOvContext = self.contextStack[cmpt]
                previousContext = previousOvContext
                while previousOvContext and not isinstance(previousOvContext, ObjectValueContext):
                    cmpt -= 1
                    try:
                        previousOvContext = self.contextStack[cmpt]
                    except IndexError:
                        previousOvContext = None
                if previousOvContext:
                    previousOvContext.add_variable(token, False)
                else:
                    previousContext.add_variable(token, False)
            else:
                cmpt = -2
                try:
                    previousContext = self.contextStack[cmpt]
                except IndexError:
                    previousContext = None
                if previousContext:
                    previousContext.add_variable(token, False)

    def update_left_operand(self):
        
        currentStatement = self.currentContext.statement
        token = currentStatement.get_left_operand()
        if currentStatement.is_var():
            currentContext = self.contextStack[-2]
            if isinstance(currentContext, VarDeclarationContext):
                currentContext = self.contextStack[-3]
            currentContext.add_variable(token, True)
        elif token.is_identifier():
            if token.starts_with_this():
                cmpt = -2
                previousOvContext = self.contextStack[cmpt]
                while previousOvContext and not isinstance(previousOvContext, ObjectValueContext):
                    cmpt -= 1
                    try:
                        previousOvContext = self.contextStack[cmpt]
                    except IndexError:
                        previousOvContext = None
                if previousOvContext:
                    previousOvContext.add_variable(token, False)
            else:
                cmpt = -2
                try:
                    previousContext = self.contextStack[cmpt]
                except IndexError:
                    previousContext = None
                if previousContext:
                    previousContext.add_variable(token, False)

    def set_operand(self, token):
        
        if isinstance(self.currentContext, UnaryExpressionContext):
            self.currentContext.statement.set_operand(token)
            return

    def set_right_operand(self, token):
        
        if isinstance(self.currentContext, BinaryExpressionContext):
            self.currentContext.statement.set_right_operand(token)
            return
        
        currentStatement = self.currentContext.statement
        currentStatement.set_right_operand(token)
        
    def end_assignment(self):

        if not self.bFullParsing:
            return

#       Stores following kinds of statements  var xhttp = new XMLHttpRequest();
        rightOp = self.currentContext.statement.get_right_operand()
        try:
            if rightOp.is_function_call() and len(rightOp.get_function_call_parts()) == 1:
                # r = MyClass();
                self.currentContext.registerNewAssignment(self.currentContext.statement.get_left_operand(), rightOp.get_function_call_parts()[0])
            elif rightOp.is_new_expression() and len(rightOp.elements) > 1:
                # r = new MyClass();
                self.currentContext.registerNewAssignment(self.currentContext.statement.get_left_operand(), rightOp.elements[1].get_function_call_parts()[0])
        except:
            pass
        parent = rightOp.parent
        if parent.is_assignment():
            try:
                if rightOp.is_new_expression():
                    fcallpart = rightOp.elements[1].get_function_call_parts()[0]
                    if fcallpart.get_name() == 'XMLHttpRequest':
                        identifier = parent.get_left_operand()
                        if identifier.is_identifier():
                            self.jsContent.xmlHttpRequests.append(identifier)
                    elif fcallpart.get_name() == 'WebSocket':
                        params = fcallpart.get_parameters()
                        if len(params) >= 1:
                            lastKbObject = fcallpart.get_first_kb_parent()
                            self.jsContent.webSockets.append(self.WebSocket(params[0], fcallpart, lastKbObject, self.file))
            except:
                pass

        leftOp = self.currentContext.statement.get_left_operand()
        if is_identifier(leftOp) and leftOp.get_fullname() == 'window.location.href':
            lastKbObject = self.currentContext.statement.get_first_kb_parent()
            self.jsContent.httpRequests.append(HttpCall('window.location', rightOp, rightOp, lastKbObject, self.file))
        elif is_identifier(leftOp) and leftOp.get_fullname() == 'document.location.href':
            lastKbObject = self.currentContext.statement.get_first_kb_parent()
            self.jsContent.httpRequests.append(HttpCall('window.location', rightOp, rightOp, lastKbObject, self.file))
        elif is_identifier(leftOp) and leftOp.get_fullname() == 'window.location':
            lastKbObject = self.currentContext.statement.get_first_kb_parent()
            self.jsContent.httpRequests.append(HttpCall('window.location', rightOp, rightOp, lastKbObject, self.file))

        elif is_identifier(leftOp) and leftOp.get_name() in ['onmessage', 'onerror', 'onopen'] and leftOp.get_prefix():
            try:
                if rightOp.is_function():
                    if leftOp.get_prefix() in self.serverEvents:
                        httpCall = self.serverEvents[leftOp.get_prefix()]
                        httpCall.add_listener(rightOp)
            except:
                pass
        elif ((is_bracketed_identifier(leftOp) or is_identifier(leftOp)) and leftOp.get_fullname().endswith('.action') and 'document.' in leftOp.get_fullname()) \
                or (is_function_call(leftOp) and leftOp.get_function_call_parts()[-1].identifier_call.get_fullname() == 'action' and leftOp.get_function_call_parts()[0].identifier_call.get_fullname() == '$'):
            lastKbObject = self.currentContext.statement.get_first_kb_parent()
            self.lastHttpCall = HttpCall('POST', rightOp, rightOp, lastKbObject, self.file)
            self.jsContent.httpRequests.append(self.lastHttpCall)
        elif is_identifier(leftOp) and leftOp.get_fullname().endswith('.action') and leftOp.get_fullname().count('.') == 1:
            # to avoid too much services where they are not, take only if fullname contains 1 dot
            # then check there is a functionCall with submit in name (case insensitive) in the same function
            lastKbObject = self.currentContext.statement.get_first_kb_parent()
            self.lastHttpCall = HttpCall('POST', rightOp, rightOp, lastKbObject, self.file)
            self.probableHttpRequest = self.lastHttpCall
#             self.jsContent.httpRequests.append(self.lastHttpCall)
        elif self.lastHttpCall and (is_bracketed_identifier(leftOp) or is_identifier(leftOp)) and leftOp.get_fullname().endswith('.actionType.value') and 'document.' in leftOp.get_fullname():
            try:
                typeIsSetToDefault = self.lastHttpCall.setType(rightOp.name)
                if typeIsSetToDefault:
                    self.lastHttpCall.setType('POST')
            except:
                pass

        self.pop_context()

    def start_var_declaration(self, token, isLet = False, isConst = False):
        
        currentStatement = self.contextStack[-1].statement
        varDecl = VarDeclaration(token, currentStatement, isLet, isConst)
        currentStatement.add_statement(varDecl)
        self.push_context(VarDeclarationContext(self.contextStack[-1], varDecl))
        return varDecl
    
    def start_var_declaration_element(self):
        currentContext = self.contextStack[-1]
        currentContext.current_element_index += 1

    def end_var_declaration_element(self):
        pass

    def add_var_declaration_element(self, elt):
        currentContext = self.contextStack[-1]
        currentStatement = currentContext.statement
        if len(currentStatement.elements) <= currentContext.current_element_index:
            currentStatement.add_element(elt)
            elt.parent = currentStatement
            
    def end_var_declaration(self):
        
        self.pop_context()

    def start_if_ternary_expression(self, tokenList, bFullParsing = True):
        
        currentStatement = self.contextStack[-1].statement
        expr = IfTernaryExpression(tokenList, currentStatement)
        self.currentContext.attach(expr)
        self.push_context(TernaryExpressionContext(self.contextStack[-1], expr))
        return expr

    def end_if_ternary_expression(self):
        self.pop_context()

    def start_if_operand(self):
        
        if isinstance(self.currentContext, TernaryExpressionContext):
            self.currentContext.is_if_operand = True
            self.currentContext.is_then_operand = False
            self.currentContext.is_else_operand = False

    def end_if_operand(self):
        
        if isinstance(self.currentContext, TernaryExpressionContext):
            self.currentContext.is_if_operand = False

    def start_then_operand(self):
        
        if isinstance(self.currentContext, TernaryExpressionContext):
            self.currentContext.is_if_operand = False
            self.currentContext.is_then_operand = True
            self.currentContext.is_else_operand = False

    def end_then_operand(self):
        
        if isinstance(self.currentContext, TernaryExpressionContext):
            self.currentContext.is_then_operand = False

    def start_else_operand(self):
        
        if isinstance(self.currentContext, TernaryExpressionContext):
            self.currentContext.is_if_operand = False
            self.currentContext.is_then_operand = False
            self.currentContext.is_else_operand = True

    def end_else_operand(self):
        
        if isinstance(self.currentContext, TernaryExpressionContext):
            self.currentContext.is_else_operand = False
    
    def is_class_context(self):
        return isinstance(self.currentContext, ClassContext)
    
    def start_class(self, name, prefix, ast, is_statement = False, lightClass = None, exportDefault = False):

        fullname = name
        if prefix and name:
            fullname = prefix + '.' + name
            
        if not self.bFullParsing:

            if self.currentContext.is_function_context():
                currentFunctionPrefix = prefix
                if not prefix:
                    currentFunctionPrefix = ''
                try:
                    globalFullname = self.currentContext.statement.get_fullname() + '.' + fullname
                except:
                    globalFullname = fullname

                if currentFunctionPrefix:
                    cl = Class(name, self.currentContext.statement.get_fullname() + '.' + currentFunctionPrefix, None, ast, self.file, self.emptyLines)
                else:
                    cl = Class(name, self.currentContext.statement.get_fullname(), None, ast, self.file, self.emptyLines)
            else:
                globalFullname = fullname
                cl = Class(name, prefix, None, ast, self.file, self.emptyLines)
                
            if exportDefault:
                self.jsContent.defaultExportedAst = cl

            if name:
                self.jsContent.add_global_class(globalFullname, cl)
                if globalFullname.startswith('module.exports.'):
                    self.jsContent.add_global_class(globalFullname[15:], cl)
                self.add_global(cl, True)
                self.currentContext.add_class(cl)
            self.push_context(ClassContext(self.contextStack[-1], cl))
            cl.lineCount = cl.get_line_count(self.emptyLines)
            return cl
        
        currentContext = self.contextStack[-1]
        currentStatement = currentContext.statement
        cl = None
        if self.currentContext.parentContext and (self.currentContext.parentContext.is_function_context() or (isinstance(self.currentContext.parentContext, VarDeclarationContext) and self.currentContext.parentContext.parentContext and self.currentContext.parentContext.parentContext.is_function_context())):
            try:
                if self.currentContext.parentContext.is_function_context():
                    globalFullname = self.currentContext.parentContext.statement.get_fullname() + '.' + fullname
                else:
                    globalFullname = self.currentContext.parentContext.parentContext.statement.get_fullname() + '.' + fullname
            except:
                globalFullname = fullname
        else:
            globalFullname = fullname
        if currentContext.wasPreprocessed:
            cl = self.jsContent.get_global_class(globalFullname, True)
        if cl:
            cl.set_parent(currentStatement)
            cl.set_name(cl.get_name(), cl.get_fullname())
            if is_statement:
                currentStatement.add_statement(cl)
        if lightClass:
            cl = lightClass
        if not cl:
            cl = Class(name, prefix, currentStatement, ast, self.file, self.emptyLines)
            if is_statement:
                currentStatement.add_statement(cl)

        if name:
            currentContext.add_class(cl)
                    
        self.push_context(ClassContext(self.contextStack[-1], cl))
        return cl
    
    def set_class_inheritance(self, identifier):
        if not self.bFullParsing:
            self.currentContext.statement.inheritanceIdentifier = identifier
            identifier.parent = self.currentContext.statement
            self.currentContext.resolve_class('inheritLink', identifier)
            classes = self.globalClassesByName[self.currentContext.statement.get_name()]
            for cl in classes:
                if cl.get_kb_symbol() == self.currentContext.statement.get_kb_symbol():
                    cl.inheritanceIdentifier = identifier
                    break
      
    def end_class(self):

        if not self.bFullParsing:
            self.pop_context()
            return

        self.end_generic_block(False)
    
    def start_method(self, name, ast, static = False):

        isConstructor = False
        if name == 'constructor':
            n = self.currentContext.statement.name
            isConstructor = True
        else:
            n = name       
        if not self.bFullParsing:
            method = Method(n, self.currentContext.statement, ast, self.file, self.emptyLines, isConstructor)
            if static:
                method.static = static
            self.currentContext.statement.add_method(method)
            self.add_global(method, True, None, self.currentContext.statement)
            self.push_context(MethodContext(self.contextStack[-1], method))
            method.lineCount = method.get_line_count(self.emptyLines)
            return method
        
        currentContext = self.contextStack[-1]
        currentStatement = currentContext.statement
        method = None
        if currentContext.wasPreprocessed:
            method = currentStatement.get_method(n, static)
        if method:
            method.set_parent(currentStatement)
            method.set_name(method.get_name(), method.get_fullname())
            currentStatement.add_statement(method)
        else:
            method = Method(n, currentStatement, ast, self.file, self.emptyLines, isConstructor)
            currentStatement.add_statement(method)
        
        if n:
            currentContext.add_function(method)

        self.push_context(MethodContext(currentContext, method))
        return method
      
    def end_method(self):

        if not self.bFullParsing:
            self.pop_context()
            return

        self.end_generic_block(False)
        
