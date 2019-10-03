from javascript_parser.symbols import Identifier, ForBlock
from javascript_parser.javascript_resolution_contexts import NamespaceContext, JSContext, FunctionContext, ClassContext, MethodContext, ObjectValueContext, BlockContext
from javascript_parser.javascript_resolution_contexts import is_assignment, is_object_destructuration, is_class, is_method, is_identifier, is_function, is_object_value, is_import_statement, is_var_declaration, is_block, is_jsx_expression, is_string, is_function_call, is_new_expression, is_return_new_statement, is_bracketed_identifier, is_html_content, is_top_function, is_var, is_function_call_part
import os
import difflib
import cast.analysers.ua
import traceback

# Used to store information on following statement:
# var a = require('./otherFile.js').Object
class RequireDecl:
    
    def __init__(self, param):
        self.param = param              # './otherFile.js' for the simple code
        self.jsContentCallees = []     # the JSContent pointed by require('./otherFile.js')
        self.objectName = None          # 'Object' for the sample code
      
def resolve_all(jsContent, functionCallThroughParametersIdentifiers, jsContentsByFilename, htmlContentByJS, htmlContentsByName, globalFunctionsByName, globalVariablesByName, globalClassesByName):
    resolver = JavascriptResolverNew(jsContent, functionCallThroughParametersIdentifiers, jsContentsByFilename, htmlContentByJS, htmlContentsByName, globalFunctionsByName, globalVariablesByName, globalClassesByName)
    resolver.resolve()
      
def resolve_element(element, jsContent, functionCallThroughParametersIdentifiers, jsContentsByFilename, htmlContentByJS, htmlContentsByName, globalFunctionsByName, globalVariablesByName, globalClassesByName):
    resolver = JavascriptResolverNew(jsContent, functionCallThroughParametersIdentifiers, jsContentsByFilename, htmlContentByJS, htmlContentsByName, globalFunctionsByName, globalVariablesByName, globalClassesByName)
    resolver.resolve_element(element)
    
class JavascriptResolverNew:
    
    def __init__(self, jsContent, functionCallThroughParametersIdentifiers, jsContentsByFilename, htmlContentByJS, htmlContentsByName, globalFunctionsByName, globalVariablesByName, globalClassesByName):
        self.jsContent = jsContent
        self.functionCallThroughParametersIdentifiers = functionCallThroughParametersIdentifiers
        self.globalFunctionsByName = globalFunctionsByName
        self.globalVariablesByName = globalVariablesByName
        self.globalClassesByName = globalClassesByName
        self.moduleExport = None    # module.export = XXX
        self.moduleExports = {}     # module.exports.XXX = XXX
        self.currentContext = None
        self.contextStack = []
        self.jsContentsByFilename = jsContentsByFilename
        self.htmlContentsByName = htmlContentsByName
        self.push_context(JSContext(None, jsContent, htmlContentByJS, globalFunctionsByName, globalVariablesByName, globalClassesByName))
        for fs in self.jsContent.globalFunctions.values():
            for f in fs:
                fn = f.get_fullname()
                self.currentContext.add_function(f, fn)
                if '.prototype.' in fn:
                    fn = fn.replace('.prototype.', '.')
                    self.currentContext.add_function(f, fn)
                if '.' in fn:
                    if is_assignment(f.parent) and f.parent.get_left_operand().get_fullname().startswith('this') and is_function(f.parent.parent):
                        self.currentContext.add_function(f, 'this.' + f.get_name())                    
                    names = fn.split('.')[:-1]
                    nbNamespaceContexts = 0
                    for name in names:
                        if name == 'prototype':
                            continue
                        if self.push_namespace_context(name):
                            nbNamespaceContexts += 1
                    self.currentContext.add_function(f, fn.replace('prototype.', ''))
                    for _ in range(0, nbNamespaceContexts):
                        self.pop_context()
            
        for fs in self.jsContent.globalVariables.values():
            for f in fs:
                fn = f.get_fullname()
                self.currentContext.add_variable(f, fn)
                if '.prototype.' in fn:
                    fn = fn.replace('.prototype.', '.')
                    self.currentContext.add_variable(f, fn)
        
    def push_context(self, context):
        self.currentContext = context
        self.contextStack.append(context)
        
    def push_namespace_context(self, name):
        
        if str(name).startswith('NONAME'):
            return False
        
        contextAdded = False
        try:
            fullname = name
            prefix = None
            if isinstance(self.currentContext, NamespaceContext):
                if self.currentContext.prefix:
                    prefix = self.currentContext.prefix + '.' + self.currentContext.name
                else:
                    prefix = self.currentContext.name
                fullname = prefix + '.' + name
            elif isinstance(self.currentContext, FunctionContext):
                if self.currentContext.statement.get_fullname():
                    prefix = self.currentContext.statement.get_fullname()
                    fullname = prefix + '.' + name
            else:
                prefix = None
            context = self.currentContext.get_namespace_context(fullname)
            if context:
                context.level += 1
                if context.level == 1:
                    context.parent = self.currentContext
                    self.currentContext = context
                    self.contextStack.append(self.currentContext)
                    contextAdded = True
            else:
                self.currentContext = NamespaceContext(self.currentContext, name, prefix)
                self.currentContext.level += 1
                self.currentContext.parent.add_namespace_context(fullname, self.currentContext)
                self.contextStack.append(self.currentContext)
                contextAdded = True
        except:
            cast.analysers.log.debug(str(traceback.format_exc()))
            print(str(traceback.format_exc()))

        return contextAdded
            
    def pop_context(self):
        if isinstance(self.currentContext, NamespaceContext):
            self.currentContext.level -= 1
            if self.currentContext.level <= 0:
                if self.contextStack:
                    self.contextStack.pop()
                if self.contextStack:
                    self.currentContext = self.contextStack[-1]
                else:
                    self.currentContext = None
            return
        
        if self.contextStack:
            self.contextStack.pop()
        if self.contextStack:
            self.currentContext = self.contextStack[-1]
        else:
            self.currentContext = None
        
    def resolve(self):
        
        if self.jsContent.module:
            for param, paramRef in self.jsContent.module.parameters.items(): 
                callee = self.get_include(paramRef + '.js')
                if callee:
                    self.jsContent.module.parameters[param] = callee

        for child in self.jsContent.get_children():
            self.resolve_element(child)

    def resolve_element(self, element, functionAllowed = True):
        
        if not element:
            return
        if is_import_statement(element):
            for _what in element._what:
                self.currentContext.add_import(_what)
        elif is_identifier(element):
            if element.parent and is_assignment(element.parent) and element.parent.parent and is_var_declaration(element.parent.parent) and element == element.parent.get_left_operand():
                self.currentContext.add_variable(element, element.get_fullname())
            self.resolve_identifier(element, functionAllowed)
        elif is_class(element):
            self.currentContext.add_class(element)
            self.push_context(ClassContext(self.currentContext, element))
            self.resolve_class(element)
            self.pop_context()
        elif is_method(element):
            self.push_context(MethodContext(self.currentContext, element))
            for param in element.get_parameters():
                if is_identifier(param):
                    self.currentContext.add_variable(param, param.get_name())
            self.resolve_method(element)
            self.pop_context()
        elif is_function(element):
            if not is_object_value(element.parent):
                fn = element.get_fullname()
                if fn:
                    if self.currentContext.get_fullname() and fn.startswith(str(self.currentContext.get_fullname()) + '.'):
                        fn = fn[len(self.currentContext.get_fullname()) + 1:]
                    while fn.startswith('NONAME') and '.' in fn:
                        fn = fn[fn.find('.') + 1:]
                    self.currentContext.add_function(element, fn)
            self.push_context(FunctionContext(self.currentContext, element))
            # in case un function call occurs before definition
            self.scan_first_level_functions(element)
            self.resolve_function(element)
            self.pop_context()
        elif is_block(element):
            self.push_context(BlockContext(self.currentContext, element))
            self.resolve_block(element)
            self.pop_context()
        elif is_object_value(element):
            name = None
            if element.parent and is_assignment(element.parent):
                leftOper = element.parent.get_left_operand()
                if is_identifier(leftOper):
                    name = leftOper.get_fullname()
            elif element.parent and is_object_value(element.parent):
                for key, item in element.parent.get_items_dictionary().items():
                    if item == element:
                        name = key.get_name()
            self.push_context(ObjectValueContext(self.currentContext, element, name))
            self.resolve_block(element)
            self.pop_context()
        elif is_function_call(element):
            self.resolve_function_call(element)
        elif is_var_declaration(element):
            self.resolve_var_declaration(element)
        elif is_assignment(element):
            self.resolve_assignment(element)
        elif is_string(element):
            self.resolve_string(element)
        elif is_jsx_expression(element):
            self.resolve_jsx_expression(element)
        else:
            for child in element.get_children():
                isLeftOper = False
                try:
                    if type(child.parent.parent) is ForBlock and child == child.parent.get_left_operand():
                        isLeftOper = True
                except:
                    pass
                if not isLeftOper:
                    self.resolve_element(child)

    def resolve_class(self, element):
        for child in element.get_children():
            self.resolve_element(child)

    def resolve_method(self, element):
        for child in element.get_children():
            self.resolve_element(child)

    def scan_first_level_functions(self, element):
        parentFullname = element.get_fullname()
        for child in element.get_children():
            if is_assignment(child) and is_function(child.get_right_operand()):
                fn = child.get_right_operand().get_fullname()
                if parentFullname:
                    if fn.startswith(parentFullname + '.'):
                        fn = fn[len(parentFullname) + 1:]
                self.currentContext.add_function(child.get_right_operand(), fn)
                self.currentContext.add_function(child.get_right_operand(), 'this.' + fn)
                fn = child.get_left_operand().get_fullname()
                self.currentContext.add_function(child.get_right_operand(), fn)
            elif is_function(child):
                fn = child.get_fullname()
                if parentFullname:
                    if fn.startswith(parentFullname + '.'):
                        fn = fn[len(parentFullname) + 1:]
                self.currentContext.add_function(child, fn)
                self.currentContext.add_function(child, 'this.' + fn)

    def resolve_function(self, element):
        try:
                for child in element.get_children():
                    if is_function(child):
                        self.currentContext.add_function(child, child.get_fullname())
                    elif is_assignment(child) and is_function(child.get_right_operand()):
                            func = child.get_right_operand()
                            fn = func.get_fullname()
                            self.currentContext.add_function(func, fn)
                            if '.' in fn:
                                names = fn.split('.')[:-1]
                                nbNamespaceContexts = 0
                                for name in names:
                                    if name == 'prototype':
                                        continue
                                    if self.push_namespace_context(name):
                                        nbNamespaceContexts += 1
                                self.currentContext.add_function(func, fn.replace('prototype.', ''))
                                for _ in range(0, nbNamespaceContexts):
                                    self.pop_context()
                        
        except:
                print(str(traceback.format_exc()))
                cast.analysers.log.debug(str(traceback.format_exc()))
        for child in element.get_children():
            self.resolve_element(child)

    def resolve_block(self, element):
        
        def record(ov, prefix = None):
             
            for child in ov.get_children():
                if is_function(child):
                    self.currentContext.add_function(child, 'this.' + child.get_name())
                    if prefix:
                        self.currentContext.add_function(child, 'this.' + prefix + '.' + child.get_name())
                elif is_object_value(child):
                    ovName = None
                    if is_assignment(child.parent):
                        ovName = child.parent.get_left_operand().get_name()
                    if prefix:
                        record(child, prefix + '.' + ovName)
                    else:
                        record(child, ovName)
        
        """
        Functions must be loaded before parsing
        if () {
            f();
            function f() {}
        }
        """
        if isinstance(self.currentContext, BlockContext) and element.block:
            if type(element) is ForBlock:
                for startExpr in element.startExpressions:
                    try:
                        _var = startExpr.get_left_operand()
                        if is_identifier(_var):
                            self.currentContext.add_variable(_var, _var.get_name())
                    except:
                        pass
            try:
                for child in element.block.get_children():
                    if is_function(child):
                        self.currentContext.add_function(child, child.get_fullname())
                    elif is_assignment(child) and is_function(child.get_right_operand()):
                        func = child.get_right_operand()
                        fn = func.get_fullname()
                        self.currentContext.add_function(func, fn)
                        if '.' in fn:
                            names = fn.split('.')[:-1]
                            nbNamespaceContexts = 0
                            for name in names:
                                if name == 'prototype':
                                    continue
                                if self.push_namespace_context(name):
                                    nbNamespaceContexts += 1
                            self.currentContext.add_function(func, fn.replace('prototype.', ''))
                            for _ in range(0, nbNamespaceContexts):
                                self.pop_context()
                        
            except:
                print(str(traceback.format_exc()))
                cast.analysers.log.debug(str(traceback.format_exc()))
        
        elif isinstance(self.currentContext, ObjectValueContext):
            record(element)

        for child in element.get_children():
            self.resolve_element(child)

    def resolve_bracketed_function_call(self, callpart, callpartFullnames):

        _evals = callpart.identifier_call.get_identifier_evaluations()
        if _evals:
            if len(_evals) == 1:
                callpartFullname = callpart.identifier_call.get_fullname() + '.' + _evals[0]
            else:
                callpartFullname = callpart.identifier_call.get_fullname() + '.' + _evals[0]
                for _eval in _evals:
                    callpartFullnames.append(callpart.identifier_call.get_fullname() + '.' + _eval)
        else:
            callpartFullname = callpart.get_fullname()
        for identEval in callpart.identifier_call.get_identifier_evaluations():
            callpartFullname = callpart.identifier_call.get_fullname() + '.' + identEval
        return callpartFullname
    
    def get_include(self, param):
        currentDir = os.path.dirname(self.jsContent.file.get_path())
        calleeFile = os.path.normpath(os.path.join(currentDir, param))
        if calleeFile in self.jsContentsByFilename:
            callee = self.jsContentsByFilename[calleeFile]
            return callee
        return None

    def resolve_require(self, element, callpart, fcallparts):
        resolved = False
        if is_assignment(element.parent):
            """
            var RpcParameter = require('./RpcParameter').RpcParameter;
            --> We search for module.exports.RpcParameter = ... in the pointed file
            """
            ident = element.parent.get_left_operand()
            if callpart.get_parameters():
                param = callpart.get_parameters()[0]
                try:
                    evs = param.evaluate()
                    if evs:
                        for param in evs:
                            try:
                                callee = self.get_include(param + ('.js' if not param.endswith('.js') else ''))
                                if not callee and not param.endswith('.js'):
                                    callee = self.get_include(param + '/index.js')
                                if callee:
                                    req = RequireDecl(param)
                                    req.jsContentCallees.append(callee)
                                    if len(fcallparts) > 1:
                                        req.objectName = fcallparts[1].identifier_call.get_fullname()
                                        f = callee.get_module_exports(req.objectName)
                                        if f:
                                            try:
                                                if is_function(f) and fcallparts[1].identifier_call.is_func_call():
                                                    linkType = 'callLink'
                                                else:
                                                    linkType = None
                                            except:
                                                linkType = None
                                            callpart.identifier_call.add_resolution(f, linkType)
                                    elif element.parent.get_left_operand().is_object_destructuration():
                                        cmpt = 0
                                        for key, value in element.parent.get_left_operand().items.items():
                                            if not value:
                                                if cmpt == 0:
                                                    req1 = req
                                                else:
                                                    req1 = RequireDecl(param)
                                                    req1.jsContentCallees.append(callee)
                                                self.currentContext.add_require(key, req1)
                                                req1.objectName = key.get_fullname()
                                                f = callee.get_module_exports(req1.objectName)
                                                if f:
                                                    key.add_resolution(f, None)
                                                cmpt += 1
                                    else:
                                        element.parent.get_left_operand().add_resolution(callee, None)
                                    self.currentContext.add_require(ident, req)
                            except:
                                print(str(traceback.format_exc()))
                                cast.analysers.log.debug(str(traceback.format_exc()))
                except:
                    print(str(traceback.format_exc()))
                    cast.analysers.log.debug(str(traceback.format_exc()))
                resolved = True
        elif callpart.get_other_parameters():
            """
            require('./session')(app, mongoose, config);
            --> we search for module.exports = ... in the pointed file
            """
            param = callpart.get_parameters()[0]
            try:
                evs = param.evaluate()
                if evs:
                    for param in evs:
                        try:
                            callee = self.get_include(param + ('.js' if not param.endswith('.js') else ''))
                            if not callee and not param.endswith('.js'):
                                callee = self.get_include(param + '/index.js')
                            if callee:
                                f = callee.get_module_exports()
                                if is_function(f):
                                    callpart.identifier_call.add_resolution(f, 'callLink')
                                else:
                                    callpart.identifier_call.add_resolution(f, None)
                        except:
                            print(str(traceback.format_exc()))
                            cast.analysers.log.debug(str(traceback.format_exc()))
            except:
                print(str(traceback.format_exc()))
                cast.analysers.log.debug(str(traceback.format_exc()))

        elif callpart.get_parameters():
            """
            fcall(require('./session');
            --> we search for module.exports = ... in the pointed file
            """
            param = callpart.get_parameters()[0]
            try:
                evs = param.evaluate()
                if evs:
                    for param in evs:
                        try:
                            callee = self.get_include(param + ('.js' if not param.endswith('.js') else ''))
                            if not callee and not param.endswith('.js'):
                                callee = self.get_include(param + '/index.js')
                            if callee:
                                f = callee.get_module_exports()
                                if is_function(f):
                                    callpart.identifier_call.add_resolution(f, 'callLink')
                                else:
                                    callpart.identifier_call.add_resolution(f, None)
                        except:
                            print(str(traceback.format_exc()))
                            cast.analysers.log.debug(str(traceback.format_exc()))
            except:
                print(str(traceback.format_exc()))
                cast.analysers.log.debug(str(traceback.format_exc()))
                    
        return resolved

    def resolve_simple_function_call_with_identifier(self, callpartFullnameToSearch, callpart_identifier, linkType):
        """
        function f() {}
        var f2 = f;
        f2();
        or
        function f() {}
        var f2 = f.bind();
        f2();
        """
        resolved = False
        vs = self.currentContext.get_variables(callpartFullnameToSearch)
        for v in vs:
            if v.parent and is_assignment(v.parent):
                rightOper = v.parent.get_right_operand()
                if is_function_call(rightOper):
                    rightOper = rightOper.get_function_call_parts()[0].identifier_call
                if rightOper.get_resolutions():
                    for resol in rightOper.get_resolutions():
                        if is_function(resol.callee):
                            callpart_identifier.add_resolution(resol.callee, linkType)
                            resolved = True
                else:
                    callpart_identifier.add_resolution(v, None)
                    resolved = True
            else:
                callpart_identifier.add_resolution(v, None)
                resolved = True
        return resolved

    def resolve_composed_function_call_with_identifier(self, callpartFullnameToSearch, callpart, linkType):
        
        resolved = False
        callpartFullnameToSearchInitial = callpartFullnameToSearch
        index = callpartFullnameToSearch.rfind('.')
        if index < 1:
            return False
        
        vs = []
        fullnameRemovedPart = ''
        while not vs and index >= 1:
            fullnameRemovedPart = callpartFullnameToSearch[index:]
            callpartFullnameToSearch = callpartFullnameToSearch[:index]
            vs = self.currentContext.get_variables(callpartFullnameToSearch)
            if not vs and not callpartFullnameToSearch.startswith('this.'):
                vs = self.currentContext.get_variables('this.' + callpartFullnameToSearch)
            index = callpartFullnameToSearch.rfind('.')
            
        for vv in vs:
            linkFound = False
            try:
                if vv.get_resolutions() and vv.resolutions[0].callee.get_fullname() == vv.get_fullname():
                    v = vv.resolutions[0].callee
                else:
                    v = vv
            except:
                v = vv
            if v.parent and is_assignment(v.parent):
                cl = self.currentContext.get_class_of_instance(v.get_fullname())
                if cl and is_class(cl):
                    meths = self.currentContext.get_methods_of_class(cl.get_name(), fullnameRemovedPart)
                    for m in meths:
                        callpart.identifier_call.add_resolution(m, linkType)
                    resolved = True
                    linkFound = True
                    continue
                rightOper = v.parent.get_right_operand()
                if is_identifier(rightOper) and rightOper.get_fullname() == 'this':
                    callpartFullnameToSearch = callpartFullnameToSearchInitial.replace(callpartFullnameToSearch, 'this')
                    fs = self.currentContext.get_functions(callpartFullnameToSearch)
                    for f in fs:
                        callpart.identifier_call.add_resolution(f, linkType)
                        resolved = True
                        linkFound = True
                elif is_identifier(rightOper):
                    """
                    var datab = AnalyzerLauncherDB;
                    datab.f();
                    """
                    callpartFullnameToSearch = callpartFullnameToSearchInitial.replace(callpartFullnameToSearch, rightOper.get_fullname())
                    fs = self.currentContext.get_functions(callpartFullnameToSearch)
                    for f in fs:
                        callpart.identifier_call.add_resolution(f, linkType)
                        resolved = True
                        linkFound = True
                elif is_new_expression(rightOper) and is_function_call(rightOper.elements[1]):
                    """
                    solution.CommonSolutionManager = function() {
                        this.handleStepDidChange = function() {
                        };
                    };
                                        
                    solution.MisExpressSolutionManager = function() {
                        var commonSolutionManager = new solution.CommonSolutionManager();
                        function handleStepDidChange2() {
                            commonSolutionManager.handleStepDidChange();
                        }
                    };
                    """
                    fcallpartIdent = rightOper.elements[1].get_function_call_parts()[0].identifier_call
                    if fcallpartIdent.get_resolutions():
                        for resol in fcallpartIdent.get_resolutions():
                            try:
                                calleeFullname = resol.callee.get_fullname()
                                funcToCall = calleeFullname + fullnameRemovedPart
                                fs = self.currentContext.get_functions(funcToCall)
                                linkFound = False
                                if len(fs) > 1:
                                    for f in fs:
                                        fname = f.get_name()
                                        if f.isThis:
                                            fname = 'this.' + f.get_name()
                                        if fname == callpartFullnameToSearch:
                                            callpart.identifier_call.add_resolution(f, linkType)
                                            resolved = True
                                            linkFound = True
                                if not linkFound:
                                    for f in fs:
                                        callpart.identifier_call.add_resolution(f, linkType)
                                        resolved = True
                                        linkFound = True
                            except:
                                pass
            if not linkFound:
                callpart.identifier_call.add_resolution(v, None)
                resolved = True
        return resolved

    def resolve_internal_function_call_with_method(self, element, callpartFullnameToSearch, callpart, linkType, secondCallpart = None):
        
        # we see if it is a constructor call
        cls = self.currentContext.get_classes(callpartFullnameToSearch)
        linkFound = False
        if cls:
            for cl in cls:
                try:
                    self.currentContext.classInstances[callpart.parent.parent.get_left_operand().get_fullname()] = cl
                except:
                    print(str(traceback.format_exc()))
                    cast.analysers.log.debug(str(traceback.format_exc()))
                constr = cl.get_method(callpartFullnameToSearch)
                if constr:
                    callpart.identifier_call.add_resolution(constr, linkType)
                    linkFound = True
                else:
                    callpart.identifier_call.add_resolution(cl, linkType)
                    linkFound = True
            if secondCallpart:
                for cl in cls:
                    meth = cl.get_method(secondCallpart.get_name())
                    if meth:
                        secondCallpart.identifier_call.add_resolution(meth, linkType)
            if linkFound:
                return True
            
        if self.currentContext.is_in_class():
            cl = self.currentContext.get_current_class()
            if callpartFullnameToSearch.startswith('this.'):
                methodName = callpartFullnameToSearch[callpartFullnameToSearch.rfind('.') + 1:]
                m = cl.get_method(methodName)
                if m:
                    callpart.identifier_call.add_resolution(m, linkType)
                    return True
            
        # we see if it is a method call
        """
        r = Rectangle();    call to a class constructor
        r.meth();
        """
        resolved = False
        prefix = ''
        if '.' in callpartFullnameToSearch:
            prefix = callpartFullnameToSearch[:callpartFullnameToSearch.find('.')]
            cl = self.currentContext.get_class_of_instance(prefix)
            if cl and is_class(cl):
                m = cl.get_method(callpartFullnameToSearch[callpartFullnameToSearch.find('.') + 1:])
                if m:
                    callpart.identifier_call.add_resolution(m, linkType)
                    resolved = True
            if not cl:
                methodName = callpartFullnameToSearch[callpartFullnameToSearch.rfind('.') + 1:]
                meths = self.currentContext.get_methods_of_class(prefix, methodName)
                for m in meths:
                    callpart.identifier_call.add_resolution(m, linkType)
                    resolved = True

        return resolved
        
    def resolve_internal_function_call(self, element, callpartFullnameToSearch, callpart, linkType, secondCallpart = None):
        
        bFound = self.resolve_internal_function_call_with_method(element, callpartFullnameToSearch, callpart, linkType, secondCallpart)
        if bFound:
            return True
            
        prefix = ''
        if '.' in callpartFullnameToSearch:
            prefix = callpartFullnameToSearch[:callpartFullnameToSearch.find('.')]

        # We search for a function
        fs = self.currentContext.get_functions(callpartFullnameToSearch, callpart.identifier_call)

        isJsp = False
        if fs and len(fs) >= 2:
            # If more than 5 functions found, filter on common file root path
            commonRootPath = ''
            calleeCandidates = []
            currentPath = self.jsContent.file.get_path()
            if currentPath.lower().endswith('.jsp'):
                isJsp = True
            for f in fs:
                calleePath = f.file.get_path()
                matches = difflib.SequenceMatcher(None, currentPath, calleePath).get_matching_blocks()
                for firstMatch in matches:
                    if firstMatch.a == 0 and firstMatch.b == 0:
                        rootPath = calleePath[:firstMatch.size - 1]
                        if len(rootPath) > len(commonRootPath):
                            commonRootPath = rootPath
                            calleeCandidates.clear()
                            calleeCandidates.append(f)
                        elif len(rootPath) == len(commonRootPath):
                            calleeCandidates.append(f)
                    break
            if calleeCandidates:
                fs = calleeCandidates
        
        if not fs or (len(fs) >= 5 and not isJsp):
            # if no function found or more than 5 found in other file than jsp
            if prefix:
                _vars = self.currentContext.get_variables(prefix)
                if _vars:
                    for vv in _vars:
                        
                        if vv.get_resolutions() and vv.resolutions[0].callee.get_fullname() == vv.get_fullname():
                            _var = vv.resolutions[0].callee
                        else:
                            _var = vv
                            if self.jsContent.module and _var in self.jsContent.module.parameters:
                                module = self.jsContent.module 
                                refJsContent = module.parameters[_var]
                                refModule = None
                                try:
                                    refModule = refJsContent.module
                                except:
                                    pass
                                if refModule:
                                    fname = callpartFullnameToSearch[len(prefix) + 1:]
                                    if fname in refModule.globalFunctionsByName:
                                        for f in refModule.globalFunctionsByName[fname]:
                                            fs.append(f.kbSymbol)
                        
                        if _var.parent and is_assignment(_var.parent):
                            cl = self.currentContext.get_class_of_instance(_var.get_name())
                            if not cl or not is_class(cl):
                                rightOper = _var.parent.get_right_operand()
                                if is_identifier(rightOper) and rightOper.get_name() == 'this':
                                    callpartFullnameToSearch = callpartFullnameToSearch.replace(prefix + '.', 'this.')
                                    fs = self.currentContext.get_functions(callpartFullnameToSearch, callpart.identifier_call)
            if not fs and not callpartFullnameToSearch.startswith('this.'):
                fs = self.currentContext.get_functions('this.' + callpartFullnameToSearch, callpart.identifier_call)
        if fs:
            linkFound = False
            # If several possibilities found, we see if one is better considering this. or not this.
            if len(fs) > 1:
                for f in fs:
                    fname = f.get_name()
                    if f.isThis:
                        fname = 'this.' + f.get_name()
                    if fname == callpartFullnameToSearch:
                        callpart.identifier_call.add_resolution(f, linkType)
                        linkFound = True
            # If link not found            
            if not linkFound:
                for f in fs:
                    """
                    In this code the called function is not itself
                    function Learn()
                    {
                        return new Learn();
                    };
                    """
                    if ( not is_new_expression(element.parent) or not f == self.currentContext.statement ) and ( not is_return_new_statement(element.parent) or not f == self.currentContext.statement ):
                        callpart.identifier_call.add_resolution(f, linkType)
                        linkFound = True
            if linkFound:
                return True
            
        else:        
            # If not found, We search for a variable
            vs = []
            vs = self.currentContext.get_variables(callpartFullnameToSearch)
            if not vs:
                if not callpartFullnameToSearch.startswith('this.'):
                    vs = self.currentContext.get_variables('this.' + callpartFullnameToSearch)
                        
            linkFound = False
            # If several possibilities found, we see if one is better considering this. or not this.
            if len(vs) > 1:
                for v in vs:
                    fname = v.get_name()
                    if fname == callpartFullnameToSearch:
                        callpart.identifier_call.add_resolution(v, None)
                        linkFound = True
            if linkFound:
                return True
            if vs:
                for v in vs:
                    """
                    function f() {}
                    var f2 = f;
                    f2();
                    """
                    if is_assignment(v.parent) or (is_object_destructuration(v.parent) and is_assignment(v.parent.parent)):
                        if is_assignment(v.parent):
                            rightOper = v.parent.get_right_operand()
                        else:
                            rightOper = v.parent.parent.get_right_operand()
                        if is_identifier(rightOper) and rightOper.get_resolutions():
                            for resol in rightOper.get_resolutions():
                                if is_function(resol.callee):
                                    callpart.identifier_call.add_resolution(resol.callee, linkType)
                                    linkFound = True
                                elif is_identifier(resol.callee):
                                    callpart.identifier_call.add_resolution(resol.callee, None)
                                    linkFound = True
                        elif is_function_call(rightOper) and rightOper.get_function_call_parts()[0].identifier_call.get_resolutions():
                            if not is_assignment(element.parent) or not is_new_expression(element.parent.get_right_operand()): 
                                for resol in rightOper.get_function_call_parts()[0].identifier_call.get_resolutions():
                                    if is_function(resol.callee):
                                        callpart.identifier_call.add_resolution(resol.callee, linkType)
                                        linkFound = True
                                    elif is_identifier(resol.callee):
                                        if resol.callee.get_name() == callpartFullnameToSearch:
                                            callpart.identifier_call.add_resolution(resol.callee, None)
                                            linkFound = True
                    if not linkFound:
                        callpart.identifier_call.add_resolution(v, None)
                return True
                                    
        # If nothing found, if function call is a.b.c(), we try with a.b in searching a variable, then a
        # we search for an identifier
        index = callpartFullnameToSearch.rfind('.')
        if index >= 1:
            linkFound = self.resolve_composed_function_call_with_identifier(callpartFullnameToSearch, callpart, linkType)
        else:
            linkFound = self.resolve_simple_function_call_with_identifier(callpartFullnameToSearch, callpart.identifier_call, linkType)
                
        if not linkFound and callpartFullnameToSearch.startswith('this.') and isinstance(self.currentContext, FunctionContext) and self.currentContext.prototypeName:
            callpartFullnameToSearchNew = callpartFullnameToSearch.replace('this', self.currentContext.prototypeName)
            linkFound = self.resolve_internal_function_call(element, callpartFullnameToSearchNew, callpart, linkType)

        return linkFound
        
    def resolve_function_call(self, element):
        
        fcallparts = element.get_function_call_parts()
        callpartFullnames = []
        callpart = fcallparts[0]

        fn = callpart.identifier_call.get_fullname()
        nbNamespaceContexts = 0
        if '.' in fn:
            names = fn.split('.')[:-1]
            for name in names:
                if self.push_namespace_context(name):
                    nbNamespaceContexts += 1

        secondCallpart = None
        if len(fcallparts) >= 2:
            secondCallpart = fcallparts[1]
        if is_bracketed_identifier(callpart.identifier_call):   # prefix['a']('myParam') is equivalent to prefix.a or prefix[v ? 'a' : 'b']('myParam')
            callpartFullname = self.resolve_bracketed_function_call(callpart, callpartFullnames)
        else:
            callpartFullname = callpart.get_fullname()
            
        if len(fcallparts) <= 2 and callpartFullname == 'require' and len(callpart.get_parameters()) <= 2:    # require('XXX');
            for child in element.get_children():
                self.resolve_element(child)
            self.resolve_require(element, callpart, fcallparts)
            if nbNamespaceContexts > 0:
                for _ in range(0, nbNamespaceContexts):
                    self.pop_context()
            return
        else:
            if callpartFullname.startswith('window.'):
                if is_html_content(self.jsContent.parent):
                    callee = self.jsContent.parent  # htmlContent
                else:
                    callee = self.jsContent
                callpart.identifier_call.add_resolution(callee, 'accessReadLink')
                
            callpartFullnameToSearchList = []
            if callpartFullname.endswith('.bind'):
                linkType = None
                callpartFullnameToSearchList.append(callpartFullname[:-5])
            elif callpartFullname.endswith('.call'):
                linkType = 'callLink'
                callpartFullnameToSearchList.append(callpartFullname[:-5])
            elif callpartFullname.endswith('.apply'):
                linkType = 'callLink'
                callpartFullnameToSearchList.append(callpartFullname[:-6])
            else:
                linkType = 'callLink'
                if callpartFullnames:
                    callpartFullnameToSearchList = callpartFullnames
                else:
                    callpartFullnameToSearchList.append(callpartFullname)
                    
            for callpartFullnameToSearch in callpartFullnameToSearchList:
                self.resolve_internal_function_call(element, callpartFullnameToSearch, callpart, linkType, secondCallpart)

        for child in element.get_children():
            self.resolve_element(child)

        if nbNamespaceContexts > 0:
            for _ in range(0, nbNamespaceContexts):
                self.pop_context()

    def resolve_var_declaration(self, element):
        for child in element.elements:
            if is_assignment(child):
                self.resolve_assignment(child, True)
            elif is_identifier(child):
                """ var url; """
                self.currentContext.add_variable(child, child.get_fullname())

    def resolve_assignment(self, element, isVarDecl = False):
        leftOper = element.get_left_operand()
        rightOper = element.get_right_operand()
        nbNamespaceContexts = 0
        if is_identifier(leftOper):
            try:
                # Motorbike.prototype = Bicycle.prototype;
                if leftOper.get_fullname().endswith('.prototype') and rightOper.get_fullname().endswith('.prototype'):
                    self.currentContext.duplicate_functions_for_prototype(rightOper.get_fullname()[:-10], leftOper.get_fullname()[:-10])
            except:
                pass
            if leftOper.get_fullname().startswith('module.exports'):
                pass
            elif not isVarDecl:
                fn = leftOper.get_fullname()
                self.resolve_identifier(leftOper, False)
                try:
                    if len(leftOper.tokens) >= 2 and leftOper.tokens[0].text != 'this':
                        nb = len(leftOper.tokens)
                        for i in range(0, nb-1):
                            try:
                                text = leftOper.tokens[i].text
                            except:
                                text = leftOper.tokens[i].get_name()
                            if text == 'prototype' or not text:
                                continue
                            if is_object_value(rightOper) or is_function(rightOper) or is_top_function(rightOper):
                                if self.push_namespace_context(text):
                                    nbNamespaceContexts += 1
                except:
                    print(str(traceback.format_exc()))
                if not is_function(rightOper):
                    self.currentContext.add_variable(leftOper, fn.replace('prototype.', ''))
                    if type(self.currentContext) is BlockContext:
                        """
                        if (form.valid()) {
                            context = 'a';
                        }
                        else {
                            context = 'b';
                        }
                        v = context;
                        """
                        vs = self.currentContext.parent.get_variables(fn)
                        if not vs:
                            self.currentContext.parent.add_variable(leftOper, fn)
                    elif type(self.currentContext) is NamespaceContext and type(self.currentContext.parent) is BlockContext:
                        """
                        if (form.valid()) {
                            context = 'a';
                        }
                        else {
                            context = 'b';
                        }
                        v = context;
                        """
                        vs = self.currentContext.parent.parent.get_variables(fn)
                        if not vs:
                            self.currentContext.parent.parent.add_variable(leftOper, fn)
            else:
                fn = leftOper.get_fullname()
                if not isVarDecl:
                    self.resolve_identifier(leftOper)
                try:
                    if len(leftOper.tokens) >= 2 and leftOper.tokens[0].text != 'this':
                        nb = len(leftOper.tokens)
                        for i in range(0, nb-1):
                            if leftOper.tokens[i].text == 'prototype' or not leftOper.tokens[i].text:
                                continue
                            if is_object_value(rightOper) or is_function(rightOper) or is_top_function(rightOper):
                                if self.push_namespace_context(leftOper.tokens[i].text):
                                    nbNamespaceContexts += 1
                except:
                    cast.analysers.log.debug(str(traceback.format_exc()))
                    print(str(traceback.format_exc()))
                if not is_function(rightOper):
                    self.currentContext.add_variable(leftOper, leftOper.get_fullname())
                    """
                    if (a) { 
                        var vm = '';
                    }
                    b = vm;
                    """
                    if type(self.currentContext) is BlockContext:
                        if is_var(leftOper.parent):
                            self.currentContext.parent.add_variable(leftOper, leftOper.get_fullname())
                    if type(self.currentContext) is NamespaceContext and type(self.currentContext.parent) is BlockContext:
                        vs = self.currentContext.parent.parent.get_variables(leftOper.get_fullname())
                        if not vs:
                            self.currentContext.parent.parent.add_variable(leftOper, leftOper.get_fullname())
        elif is_function_call(leftOper):
            self.resolve_element(leftOper)
            
        self.resolve_element(element.get_right_operand())
        
        if nbNamespaceContexts > 0:
            for i in range(0, nbNamespaceContexts):
                self.pop_context()

    def resolve_identifier_internal(self, element, name, includeFunctions = True):

        resolved = False
        functionsAlreadySearched = False
        
        if includeFunctions:
            _vars = self.currentContext.get_variables_and_functions(name, element, True)
            if _vars:
                funcs = []
                _varss = []
                for v in _vars:
                    if is_function(v):
                        if not v.parent == element.parent:
                            if is_function_call_part(element.parent) and element in element.parent.get_parameters():
                                funcs.append((v, 'callLink'))
                            elif is_jsx_expression(element.parent):
                                funcs.append((v, 'callLink'))
                            else:
                                funcs.append((v, None))
                            resolved = True
                    else:
                        _varss.append(v)
                        resolved = True
                if funcs:
                    for func in funcs:
                        element.add_resolution(func[0], func[1])
                else:
                    for v in _varss:
                        element.add_resolution(v, None)
        else:
            _vars = self.currentContext.get_variables(name, True)
            
        if not _vars and includeFunctions:
            functionsAlreadySearched = True
            funcs = self.currentContext.get_functions(name)
            for func in funcs:
                if not func.parent == element.parent:
                    if is_function_call_part(element.parent) and element in element.parent.get_parameters():
                        if is_function(func) or is_method(func):
                            element.add_resolution(func, 'callLink')
                        else:
                            element.add_resolution(func, None)
                    elif is_jsx_expression(element.parent):
                        element.add_resolution(func, 'callLink')
                    else:
                        element.add_resolution(func, None)
                    resolved = True
 
        if resolved:
            return resolved
        
        if not _vars:
            _vars = self.currentContext.get_variables(name)

        if _vars:
                for vv in _vars:
                    if vv.get_resolutions() and vv.resolutions[0].callee.get_fullname() == vv.get_fullname():
                        v = vv.resolutions[0].callee
                    else:
                        v = vv
                    if not includeFunctions:
                        if is_assignment(v.parent) and is_function(v.parent.get_right_operand()):
                            continue
                        if is_object_value(v.parent) and is_function(v.parent.get_item(v.get_name())):
                            continue
                    if element != v:
                        if v.parent and is_assignment(v.parent) and is_function(v.parent.get_right_operand()):
                            if includeFunctions:
                                element.add_resolution(v.parent.get_right_operand(), None)
                            else:
                                element.add_resolution(v, None)
                            resolved = True
                        else:
                            if not v.parent == element.parent: 
                                element.add_resolution(v, None)
                                resolved = True

        if resolved:
            return resolved

        if includeFunctions and not functionsAlreadySearched:
            funcs = self.currentContext.get_functions(name)
            for func in funcs:
                if not func.parent == element.parent:
                    if is_function_call_part(element.parent) and element in element.parent.get_parameters():
                        element.add_resolution(func, 'callLink')
                    else:
                        element.add_resolution(func, None)
                    resolved = True

        return resolved
        
    def resolve_identifier(self, element, includeFunctions = True):
                        
        name = element.get_fullname()
        if not name:
            return False

        if name.startswith('window.'):
            if is_html_content(self.jsContent.parent):
                callee = self.jsContent.parent  # htmlContent
            else:
                callee = self.jsContent
            element.add_resolution(callee, 'accessReadLink')
            return True

        if name == 'this':
            return False
        
        resolved = self.resolve_identifier_internal(element, name, includeFunctions)
        if not resolved and not name.startswith('this.'):
            resolved = self.resolve_identifier_internal(element, 'this.' + name, includeFunctions)
        
        prefix = element.get_prefix()
        
        if not resolved and prefix:
            resolved = self.resolve_identifier_internal(element, prefix, includeFunctions)
            if not resolved and not prefix.startswith('this.'):
                resolved = self.resolve_identifier_internal(element, 'this.' + prefix, includeFunctions)
        
        if not includeFunctions:
            return resolved
        
        if not resolved:
            """
            function f() {}
            var f2 = f;
            """
            funcs = self.currentContext.get_functions(name)
            for func in funcs:
                element.add_resolution(func, None)
                resolved = True
                        
        if not resolved and not name.startswith('this.'):
            funcs = self.currentContext.get_functions('this.' + name)
            for func in funcs:
                element.add_resolution(func, None)
                resolved = True
        return resolved
        
    def resolve_identifier_textWithPosition(self, name, textWithPos, parent, includeFunctions = True):

        if '.' in name:
            index = name.rfind('.') + 1
        else:
            index = 0
        ident = Identifier(parent, name[index:])
        if index > 0:
            ident.prefix = name[:index - 1]                
        if name == 'this':
            return False
        resolved = self.resolve_identifier_internal(ident, name, includeFunctions)
        if not resolved and not name.startswith('this.'):
            resolved = self.resolve_identifier_internal(ident, 'this.' + name, includeFunctions)
        
        prefix = ident.get_prefix()
        
        if not resolved and prefix:
            resolved = self.resolve_identifier_internal(ident, prefix, includeFunctions)
            if not resolved and not prefix.startswith('this.'):
                resolved = self.resolve_identifier_internal(ident, 'this.' + prefix, includeFunctions)
        
        if not includeFunctions:
            textWithPos.resolutions = ident.get_resolutions()
            return resolved
        
        if not resolved:
            """
            function f() {}
            var f2 = f;
            """
            funcs = self.currentContext.get_functions(name)
            for func in funcs:
                ident.add_resolution(func, None)
                resolved = True
                        
        if not resolved and not name.startswith('this.'):
            funcs = self.currentContext.get_functions('this.' + name)
            for func in funcs:
                ident.add_resolution(func, None)
                resolved = True
        textWithPos.resolutions = ident.get_resolutions()
        return resolved
    
    def resolve_string(self, s):
        # resolve link to html file
        text = s.get_text()
        currentFilename = self.jsContent.file.get_path()
        commonRootPath = ''
        htmlCandidates = []
        if '.html' in text and self.htmlContentsByName:
            for htmlBaseName, htmlContents in self.htmlContentsByName.items():
                if self.stringMatchesFile(text, htmlBaseName):
                    for htmlContent in htmlContents:
                        htmlFilename = htmlContent.file.get_path()
                        matches = difflib.SequenceMatcher(None, currentFilename, htmlFilename).get_matching_blocks()
                        for firstMatch in matches:
                            if firstMatch.a == 0 and firstMatch.b == 0:
                                rootPath = htmlFilename[:firstMatch.size - 1]
                                if len(rootPath) > len(commonRootPath):
                                    commonRootPath = rootPath
                                    htmlCandidates.clear()
                                    htmlCandidates.append(htmlContent)
                                elif len(rootPath) == len(commonRootPath):
                                    htmlCandidates.append(htmlContent)
                            break
        for htmlContent in htmlCandidates:
            s.add_resolution(htmlContent.htmlSourceCode, 'useLink', True)

        for child in s.get_children():
            self.resolve_element(child)
    
    def resolve_jsx_expression(self, expr):

        for textWithPos in expr.attributeValues.values():
            text = textWithPos.get_text()
            if text.startswith('{') and text.endswith('}'):
                text = text[1:-1]
                self.resolve_identifier_textWithPosition(text, textWithPos, expr, True)

        for child in expr.get_children():
            self.resolve_element(child)
    
    def stringMatchesFile(self, text, baseName):
        
        # todomvc-index.html does not match index.html
        l = text.find(baseName)
        if l < 0:
            return False
        
        if l == 0:
            return True
        
        charBeforeName = text[l-1]
        if charBeforeName in ['/', '\\', ' ']:
            return True 

        return False
