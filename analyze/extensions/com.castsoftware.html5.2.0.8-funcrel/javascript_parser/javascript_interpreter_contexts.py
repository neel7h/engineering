from javascript_parser.symbols import Identifier, Resolution
from collections import OrderedDict

class Context:

    def __init__(self, parentContext, statement, wasPreprocessed = False):
        
        self.statement = statement
        self.parentContext = parentContext
        self.functions = OrderedDict() # list of functions by name
        self.classes = OrderedDict() # list of classes by name
        self.variables = OrderedDict() # list of variables by name
        self.variablesDeclaredWithVar = OrderedDict() # list of variables declared with var by name
        self.disableResolution = False
        self.identifiersToResolve = []
        self.wasPreprocessed = wasPreprocessed
        if parentContext and not parentContext.wasPreprocessed:
            self.wasPreprocessed = False
        self.unresolvedIdentifiers = []
        self.newAssignments = {}    # myVar = new myClass() --> key = myVar, value = [ myClass ]
        
    def is_variable_declared(self, key):
         
        if not self.parentContext:
            if key in self.variables:
                return True
            return False
         
        if key in self.variables:
            return True
             
        return self.parentContext.is_variable_declared(key)
            
    def getNewAssignments(self, key):
        if key in self.newAssignments:
            return self.newAssignments[key]
        if self.parentContext:
            return self.parentContext.getNewAssignments(key)
        return None
    
    def registerNewAssignment(self, leftOper, fcallpart):
        if self.parentContext:
            self.parentContext.registerNewAssignment(leftOper, fcallpart)
        
    def registerNewAssignmentInternal(self, leftOper, fcallpart):

        try:
            key = leftOper.get_name()
            value = fcallpart.identifier_call.get_name()
            if key in self.newAssignments:
                l = self.newAssignments[key]
            else:
                l = []
                self.newAssignments[key] = l
            l.append(value)
            
        except:
            pass
    
    def add_require(self, leftOperand, param):
        if self.parentContext:
            self.parentContext.add_require(leftOperand, param)
        
    def update_require_callee(self, leftOperand, kbObject):
        if self.parentContext:
            self.parentContext.update_require_callee(leftOperand, kbObject)
        
    def update_require_object(self, leftOperand, objectName):
        if self.parentContext:
            self.parentContext.update_require_object(leftOperand, objectName)
        
    def get_require(self, name):
        if self.parentContext:
            return self.parentContext.get_require(name)
    
    def add_unresolved_identifier(self, ident, recursive = True):
        
        self.unresolvedIdentifiers.append(ident)
        if recursive and self.parentContext:
            self.parentContext.add_unresolved_identifier(ident)
        
    def remove_unresolved_identifier(self, ident):
        
        self.unresolvedIdentifiers.remove(ident)
        if self.parentContext:
            self.parentContext.remove_unresolved_identifier(ident)
        
    def add_identifier_to_resolve(self, identToResolve):
        if self.parentContext:
            self.parentContext.add_identifier_to_resolve(identToResolve)
            
    def get_function(self, functionName):
        func = self.functions.get(functionName)
        if func:
            return func
        if self.parentContext:
            return self.parentContext.get_function(functionName)
        else:
            return None
            
    def get_class(self, className):
        func = self.classes.get(className)
        if func:
            return func
        if self.parentContext:
            return self.parentContext.get_class(className)
        else:
            return None
        
    def disable_resolution(self):
        self.disableResolution = True
        
    def enable_resolution(self):
        self.disableResolution = False

    def is_resolution_enabled(self):
        return not self.disableResolution

    def is_resolution_disabled(self):
        return self.disableResolution

    def is_loop(self):
        return False

    def is_for_block(self):
        return False
        
    def attach(self, expr):
        pass
    
    def is_file_context(self):
        return False
    
    def is_object_value_context(self):
        return False
    
    def is_function_context(self):
        return False
    
    def is_method_context(self):
        return False
    
    def is_class_context(self):
        return False
    
    def is_assignment_context(self):
        return False
    
    def is_function_call_context(self):
        return False
    
    def is_js_function_call_context(self):
        return False
    
    def is_statements_block(self):
        return False
    
    def add_function(self, function):
        
        if self.parentContext:
            self.parentContext.add_function(function)
    
    def add_class(self, cl):
        
        if self.parentContext:
            self.parentContext.add_class(cl)
    
    def add_function_internal(self, key, function):
        
        if not key or '_PARAM_' in key:
            return
        # example: v1.v2.f
        # we register f with key 'f' in currentContext
        # then f with key v2.f before previous objectValue context
        # then f with key v1.v2.f before previous previous objectValue context
        keyWithoutPrototype = key
        if '.prototype.' in key:
            keyWithoutPrototype = keyWithoutPrototype.replace('prototype.', '')

        if self.is_object_value_context():
            self.functions[keyWithoutPrototype] = function
            if key != keyWithoutPrototype:
                self.functions[key] = function
            if self.name:
                self.functions[self.name + '.' + keyWithoutPrototype] = function
                if key != keyWithoutPrototype:
                    self.functions[self.name + '.' + key] = function
        else:
            previousKbContext = self.get_last_statements_block_context()
            if not keyWithoutPrototype in previousKbContext.functions: 
                previousKbContext.functions[keyWithoutPrototype] = function
            else:
                oldFunc = previousKbContext.functions[keyWithoutPrototype]
                if not function.get_prefix_internal() or (oldFunc.get_prefix_internal() and len(function.get_prefix_internal()) < len(oldFunc.get_prefix_internal())):
                    previousKbContext.functions[keyWithoutPrototype] = function
            if key != keyWithoutPrototype:
                previousKbContext.functions[key] = function
            
        fullname = function.get_fullname()
        if key != fullname:
            prefix = fullname[0:-len(key)-1]
            index = prefix.rfind('.')
            if index >= 0:
                nextKey = prefix[index+1:] + '.' + key
            else:
                nextKey = prefix + '.' + key
#             self.functions[nextKey] = function
#             self.functions[key] = function
            if function.isThis:
                self.functions['this.' + key] = function
            else:
                self.functions[key] = function
                self.functions[nextKey] = function
                self.functions[fullname] = function
            if self.is_function_context() and self.statement.name and '_PARAM_' in self.statement.name:
                return
            
            if self.parentContext:
                previousKbContext = self.parentContext.get_last_statements_block_context()
            else:
                previousKbContext = self.get_last_statements_block_context()
                
            if previousKbContext:
                previousKbContext.add_function_internal(nextKey, function)
    
    def add_class_internal(self, key, cl):
        
        keyWithoutPrototype = key

        if self.is_object_value_context():
            self.classes[keyWithoutPrototype] = cl
            if key != keyWithoutPrototype:
                self.classes[key] = cl
            if self.name:
                self.classes[self.name + '.' + keyWithoutPrototype] = cl
                if key != keyWithoutPrototype:
                    self.classes[self.name + '.' + key] = cl
        else:
            previousKbContext = self.get_last_statements_block_context()
            if not keyWithoutPrototype in previousKbContext.classes: 
                previousKbContext.classes[keyWithoutPrototype] = cl
            else:
                oldClass = previousKbContext.classes[keyWithoutPrototype]
                if not cl.get_prefix_internal() or (oldClass.get_prefix_internal() and len(cl.get_prefix_internal()) < len(oldClass.get_prefix_internal())):
                    previousKbContext.classes[keyWithoutPrototype] = cl
            if key != keyWithoutPrototype:
                previousKbContext.classes[key] = cl
            
        fullname = cl.get_fullname()
        if key != fullname:
            prefix = fullname[0:-len(key)-1]
            index = prefix.rfind('.')
            if index >= 0:
                nextKey = prefix[index+1:] + '.' + key
            else:
                nextKey = prefix + '.' + key
#             self.functions[nextKey] = function
#             self.functions[key] = function
            self.classes[key] = cl
            self.classes[nextKey] = cl
            self.classes[fullname] = cl
            
            if self.parentContext:
                previousKbContext = self.parentContext.get_last_statements_block_context()
            else:
                previousKbContext = self.get_last_statements_block_context()
                
            if previousKbContext:
                previousKbContext.add_class_internal(nextKey, cl)
        
    def add_variable(self, variable, isDeclaredWithVar):
        
        try:
            if self.parentContext:
                self.parentContext.add_variable(variable, isDeclaredWithVar)
        except:
            pass
        
    def add_variable_internal(self, key, variable, isDeclaredWithVar):
        
        if not isinstance(variable, Identifier):
            return
        
        if not isDeclaredWithVar:
            lastKbContext = self.get_last_declaration_context()
            if lastKbContext and lastKbContext != self:
                if not lastKbContext.is_variable_declared(key):
                    return lastKbContext.add_variable_internal(key, variable, isDeclaredWithVar)
                else:
                    return
        
        # example: v1.v2.f
        # we register f with key 'f' in currentContext
        # then f with key v2.f before previous objectValue context
        # then f with key v1.v2.f before previous previous objectValue context
        if self.is_object_value_context():
            if variable.get_prefix() == 'this':
                newKey = variable.get_fullname()
            else:
                newKey = key
                if self.name:
                    variable.set_name(variable.get_name(), self.name + '.' + variable.get_name())
                    variable.set_prefix(self.name)
            if not newKey in self.variables:
                self.variables[newKey] = variable
                if isDeclaredWithVar:
                    self.variablesDeclaredWithVar[newKey] = variable
                if self.name:
                    self.variables[self.name + '.' + newKey] = variable
                    if isDeclaredWithVar:
                        self.variablesDeclaredWithVar[self.name + '.' + newKey] = variable
            if key != newKey and not key in self.variables:
                self.variables[key] = variable
                if isDeclaredWithVar:
                    self.variablesDeclaredWithVar[key] = variable
                if self.name:
                    self.variables[self.name + '.' + key] = variable
                    if isDeclaredWithVar:
                        self.variablesDeclaredWithVar[self.name + '.' + key] = variable
        else:
            if isDeclaredWithVar:
                previousKbContext = self.get_last_kb_context()
            else:
                previousKbContext = self.get_last_statements_block_context()
                
            if not key in previousKbContext.variables:
                previousKbContext.variables[key] = variable
                if isDeclaredWithVar:
                    previousKbContext.variablesDeclaredWithVar[key] = variable
                # verrue pour le prototype
                if key.startswith('this.'):
                    previousKbContext.variables[key[5:]] = variable
                    if isDeclaredWithVar:
                        previousKbContext.variablesDeclaredWithVar[key[5:]] = variable
                    if previousKbContext.parentContext and isinstance(previousKbContext.parentContext, FileContext):
                        if not key in previousKbContext.parentContext.variables:
                            previousKbContext.parentContext.variables[key] = variable

            if isDeclaredWithVar:
                previousKbContext = self.get_last_statements_block_context()
                if not key in previousKbContext.variables:
                    previousKbContext.variables[key] = variable
                    previousKbContext.variablesDeclaredWithVar[key] = variable
        fullname = variable.get_fullname()
        if key != fullname:
            prefix = fullname[0:-len(key)-1]
            index = prefix.rfind('.')
            if index >= 0:
                nextKey = prefix[index+1:] + '.' + key
            else:
                if prefix:
                    nextKey = prefix + '.' + key
                else:
                    nextKey = variable.get_fullname()
            previousKbContext = self.get_last_statements_block_context()
            if previousKbContext and previousKbContext != self:
                previousKbContext.add_variable_internal(nextKey, variable, isDeclaredWithVar)

    def get_last_kb_context(self):
        
        return self.parentContext.get_last_kb_context()

    def get_last_declaration_context(self):
        
        return self.parentContext.get_last_declaration_context()

    def get_last_statements_block_context(self):
        
        return self.parentContext.get_last_statements_block_context()
        
    def resolve_identifier(self, identifier, linkType, recursive = True, originalIdentifier = None, onlyWithVar = False):
        return []
            
    def resolve_identifier_as_method_call(self, identifier):

        # search if it is a constructor call
        if not identifier.get_prefix_internal():
            cl = self.classes.get(identifier.name)
            if cl:
                meth = cl.get_method(identifier.name)
                if meth:
                    return meth
            return None

        if identifier.get_prefix_internal() == 'super':
            return None
        
        if identifier.get_prefix_internal() == 'this' or identifier.get_prefix_internal().startswith('this.'):
            cl = self.parentContext.statement
            identName = identifier.name
            if identName == 'bind':
                identName = identifier.get_prefix_internal()
                index = identName.rfind('.')
                if index >= 0:
                    identName = identName[index+1:]
            meth = cl.get_method(identName)
            if meth:
                return meth
            
        classes = self.getNewAssignments(identifier.get_prefix_internal())
        if classes:
            lastClass = classes[-1]
            if lastClass in self.classes:
                meth = self.classes[lastClass].get_method(identifier.name)
                if meth:
                    return meth
            elif lastClass in self.functions:
                meth = self.functions[lastClass].get_prototype_function(identifier.name)
                if meth:
                    return meth
        return None

    def resolve_identifier_internal(self, identifier, linkType, recursive = True, originalIdentifier = None, onlyWithVar = False):
                
        nameToSearch = identifier.get_fullname()
        if not nameToSearch:
            return None
        
        nameStartsWithThis = False
        if ( 'this.' in nameToSearch or 'self.' in nameToSearch ):
            nameStartsWithThis = True
        if (not self.is_object_value_context() or identifier.is_func_call()) and nameStartsWithThis:
            nameToSearch = nameToSearch[5:]
        if identifier.is_func_call():
            if nameToSearch.endswith('.bind'):
                nameToSearch = nameToSearch[0: -len('.bind')]
                linkType = None
            elif nameToSearch.endswith('.apply'):
                nameToSearch = nameToSearch[0: -len('.apply')]
                linkType = 'callLink'
            elif nameToSearch.endswith('.call'):
                nameToSearch = nameToSearch[0: -len('.call')]
                linkType = 'callLink'
            try:
                func = self.resolve_identifier_as_method_call(identifier)
            except:
                func = None
            if not func:
                func = self.functions.get(nameToSearch)
            if not func:
                func = self.resolve_name(nameToSearch, None)
            if not func:
                if not self.is_function_context() or not nameStartsWithThis:
                    if onlyWithVar:
                        func = self.variablesDeclaredWithVar.get(nameToSearch)
                    else:
                        func = self.variables.get(nameToSearch)
            if func:
                if type(func) is list and len(func) == 1:
                    func = func[0]
                if func.is_function():
                    return Resolution(func.get_kb_symbol(), linkType,  originalIdentifier == None)
                else:
                    return Resolution(func, None, not identifier.is_func_call())
            if nameStartsWithThis:
                for key, function in self.functions.items():
                    if key.endswith('.' + nameToSearch):
                        func = function
                        return Resolution(func.get_kb_symbol(), linkType, originalIdentifier == None)
            if self.is_function_context() or self.is_object_value_context():
                index = nameToSearch.rfind('.')
                if index >= 0:
                    n = nameToSearch[0:index]
                    if onlyWithVar:
                        v = self.variablesDeclaredWithVar.get(n)
                    else:
                        v = self.variables.get(n)
                    if v:
                        newStringToSearch = None
                        try:
                            if v.parent and v.parent.is_assignment():
                                rightOper = v.parent.get_right_operand()
                                if rightOper.is_new_expression():
                                    newStringToSearch = rightOper.elements[1].get_function_call_parts()[0].identifier_call.get_fullname_internal()
                        except:
                            pass
                        if not newStringToSearch:
                            return Resolution(v, None, originalIdentifier == None)
                        newIdent = Identifier(None, newStringToSearch + '.' + identifier.name, None)
                        newIdent.set_is_func_call(identifier.is_func_call())
                        return self.resolve_identifier_internal(newIdent, linkType, recursive, identifier, onlyWithVar)
            return []
        else:
            if nameToSearch.endswith('.bind'):
                nameToSearch = nameToSearch[0: -len('.bind')]
                linkType = None
            elif nameToSearch.endswith('.apply'):
                nameToSearch = nameToSearch[0: -len('.apply')]
                linkType = 'callLink'
            elif nameToSearch.endswith('.call'):
                nameToSearch = nameToSearch[0: -len('.call')]
                linkType = 'callLink'
            ident = self.classes.get(nameToSearch)
            if not ident:
                ident = self.functions.get(nameToSearch)
                if not ident:
                    if onlyWithVar:
                        ident = self.variablesDeclaredWithVar.get(nameToSearch)
                    else:
                        if nameStartsWithThis and isinstance(self, FileContext):
                            ident = self.variables.get('this.' + nameToSearch)
                        else:
                            ident = self.variables.get(nameToSearch)
            if ident == identifier:
                ident = None
            if not ident:
                ident = self.functions.get(nameToSearch)
            # avoid having url value resolved to url key in an object value containing url : url
            if ident and ident.get_parent() != identifier.get_parent():
                    if ident.get_kb_symbol():
                        return Resolution(ident.get_kb_symbol(), linkType, originalIdentifier == None)
                    else:
                        return Resolution(ident, linkType, originalIdentifier == None)

            index = nameToSearch.rfind('.')
            if index < 0:
                return []
            nameToSearch = nameToSearch[:index]
            newIdent = Identifier(None, nameToSearch, None)
            if originalIdentifier:
                return self.resolve_identifier_internal(newIdent, None, True, originalIdentifier, onlyWithVar)
            else:
                return self.resolve_identifier_internal(newIdent, None, True, identifier, onlyWithVar)
            
        return None
    
    def resolve_class(self, linkType, identifier):
        cl = self.get_class(identifier.get_name())
        if cl and cl.get_fullname() == identifier.get_fullname():
            identifier.add_resolution(cl, linkType)
            return True
        elif self.parentContext:
            return self.parentContext.resolve_class(linkType, identifier)
        else:
            return False
            
    def resolve_name(self, name, prefix, cl = None):
        
        if cl:
            res = cl.get_method(name)
            return res
        
        res = self.functions.get(name)
        if res:
            if prefix:
                fullname = prefix + '.' + name
            else:
                fullname = name
            resFullname = res.get_fullname()
            if resFullname.startswith('NONAME'):
                index = resFullname.find('.')
                if index > 0:
                    resFullname = resFullname[index+1:]
            if res and resFullname != fullname:
                pref = None
                if self.is_function_context():
                    pref = self.statement.get_fullname() 
                if not pref or resFullname != pref + '.' + fullname:
                    res = None
        if not res and self.parentContext:
            res = self.parentContext.resolve_name(name, prefix)
        return res

    def get_last_function_context(self):
        
        return self.parentContext.get_last_function_context()
    
# Used to store information on following statement:
# var a = require('./otherFile.js').Object
class RequireDecl:
    
    def __init__(self, param):
        self.param = param              # './otherFile.js' for the simple code
        self.jsContentCallee = None     # the JSContent pointed by require('./otherFile.js')
        self.objectName = None          # 'Object' for the sample code
    
class FileContext(Context):

    def __init__(self, parentContext, currentStatement):
        
        Context.__init__(self, parentContext, currentStatement, True)
        self.requires = {}
        
    def registerNewAssignment(self, leftOper, fcallpart):
        self.registerNewAssignmentInternal(leftOper, fcallpart)

    def add_require(self, leftOperand, param):
        try:
            self.requires[leftOperand.name] = RequireDecl(param)
        except:
            pass

    def update_require_callee(self, leftOperand, kbObject):
        try:
            self.requires[leftOperand.name].jsContentCallee = kbObject
        except:
            pass

    def update_require_object(self, leftOperand, objectName):
        try:
            self.requires[leftOperand.name].objectName = objectName
        except:
            pass

    def get_require(self, name):
        if name in self.requires:
            return self.requires[name]
        else:
            return None

    def is_file_context(self):
        return True

    def is_statements_block(self):
        return True

    def get_last_kb_context(self):
        
        return self

    def get_last_declaration_context(self):
        
        return self

    def get_last_statements_block_context(self):
        
        return self

    def get_last_function_context(self):
        
        return self
    
    def add_function(self, function):
        self.add_function_internal(function.get_name(), function)
    
    def add_class(self, cl):
        self.add_class_internal(cl.get_name(), cl)
    
    def add_variable(self, variable, isDeclaredWithVar):
        try:
            self.add_variable_internal(variable.get_fullname(), variable, isDeclaredWithVar)
        except:
            pass
    
    def resolve_identifier(self, identifier, linkType, recursive = True, originalIdentifier = None, onlyWithVar = False):

        # We are in FileContext
        if not identifier.is_bracketed_identifier():
            
            res = self.resolve_identifier_internal(identifier, linkType, recursive, originalIdentifier, onlyWithVar)
            if res:
                # case of MotorBike.prototype = Bicycle.prototype for example and we are on right operand
                if identifier.get_name() == 'prototype' and identifier.parent and identifier.parent.is_assignment() and identifier.parent.get_right_operand() == identifier:
                    leftOper = identifier.parent.get_left_operand()
                    if leftOper.get_resolutions():
                        for resol in leftOper.resolutions:
                            try:
                                resol.callee.update_prototype_functions(res.callee)
                            except:
                                pass
                    return [ res ]
                
                # ex: var datab = anal;
                #     datab.f();
                # with, in another file:
                #     var anal = {
                #           f: function() {}
                #         }
                # datab.f() has link to "var datab = anal", then we can replace prefix with anal before global resolution.
                if originalIdentifier and originalIdentifier.is_func_call() and not identifier.is_func_call() and originalIdentifier.get_prefix():
                    try:
                        if res.callee.parent.is_assignment():
                            if res.callee.parent.get_right_operand().is_identifier():
                                prefixValue = res.callee.parent.get_right_operand().get_fullname()
                            elif res.callee.parent.get_right_operand().is_function_call():
                                # var datab = require('...').anal;
                                callparts = res.callee.parent.get_right_operand().get_function_call_parts()
                                if len(callparts) == 2 and callparts[0].identifier_call.get_fullname() == 'require': 
                                    prefixValue = callparts[1].identifier_call.get_fullname()
                            if prefixValue:
                                originalIdentifier.set_prefix(prefixValue)
                                originalIdentifier.set_name(originalIdentifier.get_name(), prefixValue + '.' + originalIdentifier.get_name())
                                return []
                        return [ res ]
                    except:
                        return [ res ]
                else:
                    return [ res ]
            
            if identifier.is_func_call():
                newIdent = Identifier(None, identifier.get_fullname(), None)
                if originalIdentifier:
                    res = self.resolve_identifier(newIdent, None, recursive, originalIdentifier, onlyWithVar)
                else:
                    res = self.resolve_identifier(newIdent, None, recursive, identifier, onlyWithVar)
                if res:
                    return res
            else:
                nameToSearch = identifier.get_fullname()
                if not nameToSearch:
                    return []
                index = nameToSearch.rfind('.')
                if index < 0:
                    return []
                nameToSearch = nameToSearch[:index]
                newIdent = Identifier(None, nameToSearch, None)
                if originalIdentifier:
                    res = self.resolve_identifier(newIdent, None, recursive, originalIdentifier, onlyWithVar)
                else:
                    res = self.resolve_identifier(newIdent, None, recursive, identifier, onlyWithVar)
                if res:
                    return res
            
        if identifier.is_bracketed_identifier():
            newIdents = identifier.create_identifiers_from_evaluation()
            results = []
            for newIdent in newIdents:
                result = self.resolve_identifier_internal(newIdent, linkType, recursive, originalIdentifier, onlyWithVar)
                if result:
                    results.append(result)
            return results
        return []
        
    def add_identifier_to_resolve(self, identToResolve):
        self.identifiersToResolve.append(identToResolve)
            
class FunctionContext(Context):

    def __init__(self, parentContext, currentFunction, wasPreprocessed = True):
        
        Context.__init__(self, parentContext, currentFunction, wasPreprocessed)
        
    def registerNewAssignment(self, leftOper, fcallpart):
        self.registerNewAssignmentInternal(leftOper, fcallpart)
    
    def is_function_context(self):
        return True
        
    def start_parameters(self):
        self.disable_resolution()

    def end_parameters(self):
        self.enable_resolution()

    def is_statements_block(self):
        return True

    def get_last_kb_context(self):
        
        return self

    def get_last_declaration_context(self):
        
        return self

    def get_last_statements_block_context(self):
        
        return self

    def get_last_function_context(self):
        
        return self
    
    def add_function(self, function):
        self.add_function_internal(function.get_name(), function)
        if self.parentContext and self.parentContext.is_js_function_call_context():
            self.parentContext.add_function(function)
    
    def add_variable(self, variable, isDeclaredWithVar):
        try:
            self.add_variable_internal(variable.get_fullname(), variable, isDeclaredWithVar)
        except:
            pass
    def add_identifier_to_resolve(self, identToResolve):
        self.identifiersToResolve.append(identToResolve)
    
    def resolve_identifier(self, identifier, linkType, recursive = True, originalIdentifier = None, onlyWithVar = False):
        # We are in FunctionContext
        if not identifier.is_bracketed_identifier():
            
            res = self.resolve_identifier_internal(identifier, linkType, recursive, originalIdentifier, onlyWithVar)
            if res:
                return [ res ]
            
        if identifier.is_bracketed_identifier():
            newIdents = identifier.create_identifiers_from_evaluation()
            results = []
            for newIdent in newIdents:
                result = self.resolve_identifier_internal(newIdent, linkType, recursive, originalIdentifier, onlyWithVar)
                if result:
                    results.append(result)
            return results
        return []
            
class MethodContext(FunctionContext):

    def __init__(self, parentContext, currentFunction, wasPreprocessed = True):
        
        FunctionContext.__init__(self, parentContext, currentFunction, wasPreprocessed)
        
    def registerNewAssignment(self, leftOper, fcallpart):
        self.registerNewAssignmentInternal(leftOper, fcallpart)
    
    def is_function_context(self):
        return False
    
    def is_method_context(self):
        return True

    def add_function(self, function):
        self.add_function_internal(function.get_name(), function)
    
    def add_variable(self, variable, isDeclaredWithVar):
        try:
            self.add_variable_internal(variable.get_fullname(), variable, isDeclaredWithVar)
        except:
            pass
    
    def resolve_identifier(self, identifier, linkType, recursive = True, originalIdentifier = None, onlyWithVar = False):
        # We are in MethodContext
        if not identifier.is_bracketed_identifier():
            
            res = self.resolve_identifier_internal(identifier, linkType, recursive, originalIdentifier, onlyWithVar)
            if res:
                return [ res ]
            
        if identifier.is_bracketed_identifier():
            newIdents = identifier.create_identifiers_from_evaluation()
            results = []
            for newIdent in newIdents:
                result = self.resolve_identifier_internal(newIdent, linkType, recursive, originalIdentifier, onlyWithVar)
                if result:
                    results.append(result)
            return results
        return []
            
class ClassContext(Context):

    def __init__(self, parentContext, currentClass, wasPreprocessed = True):
        
        Context.__init__(self, parentContext, currentClass, wasPreprocessed)
        
    def registerNewAssignment(self, leftOper, fcallpart):
        self.registerNewAssignmentInternal(leftOper, fcallpart)
    
    def is_class_context(self):
        return True
        
    def is_statements_block(self):
        return True

    def get_last_kb_context(self):
        
        return self

    def get_last_declaration_context(self):
        
        return self

    def get_last_statements_block_context(self):
        
        return self

    def get_last_class_context(self):
        
        return self
    
    def add_function(self, function):
        self.add_function_internal(function.get_name(), function)
        self.statement.add_method(function)
        if self.parentContext and self.parentContext.is_js_function_call_context():
            self.parentContext.add_function(function)
    
    def add_variable(self, variable, isDeclaredWithVar):
        try:
            self.add_variable_internal(variable.get_fullname(), variable, isDeclaredWithVar)
        except:
            pass
    def add_identifier_to_resolve(self, identToResolve):
        self.identifiersToResolve.append(identToResolve)
    
    def resolve_identifier(self, identifier, linkType, recursive = True, originalIdentifier = None, onlyWithVar = False):
        # We are in FunctionContext
        if not identifier.is_bracketed_identifier():
            
            res = self.resolve_identifier_internal(identifier, linkType, recursive, originalIdentifier, onlyWithVar)
            if res:
                return [ res ]
            
        if identifier.is_bracketed_identifier():
            newIdents = identifier.create_identifiers_from_evaluation()
            results = []
            for newIdent in newIdents:
                result = self.resolve_identifier_internal(newIdent, linkType, recursive, originalIdentifier, onlyWithVar)
                if result:
                    results.append(result)
            return results
        return []
            
    def resolve_name(self, name, prefix, cl = None):

        if name.startswith('super.'):
            if self.parentContext and self.statement.inheritanceIdentifier and self.statement.inheritanceIdentifier.get_resolutions():
                return self.parentContext.resolve_name(name[6:], prefix, self.statement.inheritanceIdentifier.resolutions[0].callee) 
        
        return Context.resolve_name(self, name, prefix)
        
class ObjectValueContext(Context):

    def __init__(self, parentContext, name, block, wasPreprocessed = True):
        
        Context.__init__(self, parentContext, block, wasPreprocessed)
        self.identifiersToResolve = []
        self.name = name    # name is a if a = { ... }
    
    def is_object_value_context(self):
        return True

    def get_last_declaration_context(self):
        return self
    
    def add_function(self, function):
        self.add_function_internal(function.get_name(), function)
    
    def add_variable(self, variable, isDeclaredWithVar):
        self.add_variable_internal(variable.get_name(), variable, isDeclaredWithVar)
    
    def get_last_statements_block_context(self):
        return self
        
    def resolve_identifier(self, identifier, linkType, recursive = True, originalIdentifier = None, onlyWithVar = False):
        # We are in ObjectValueContext
        if not identifier.is_bracketed_identifier():
            
            res = self.resolve_identifier_internal(identifier, linkType, recursive, originalIdentifier, onlyWithVar)
            if res:
                return [ res ]
            
            if identifier.is_func_call():
                newIdent = Identifier(None, identifier.get_fullname(), None)
                res = self.resolve_identifier(newIdent, None, recursive, identifier, onlyWithVar)
                if res:
                    return res
                
            nameToSearch = identifier.get_fullname()
            if not nameToSearch:
                return []
            linkType = None
            if nameToSearch.endswith('.bind'):
                nameToSearch = nameToSearch[0:-len('.bind')]
            elif nameToSearch.endswith('.apply'):
                nameToSearch = nameToSearch[0:-len('.apply')]
                linkType = 'callLink'
            elif nameToSearch.endswith('.call'):
                nameToSearch = nameToSearch[0:-len('.call')]
                linkType = 'callLink'
            index = nameToSearch.rfind('.')
            if index < 0:
                return []
            nameToSearch = nameToSearch[:index]
            newIdent = Identifier(None, nameToSearch, None)
            res = self.resolve_identifier(newIdent, linkType, recursive, identifier, onlyWithVar)
            if res:
                return res
            
        if identifier.is_bracketed_identifier():
            newIdents = identifier.create_identifiers_from_evaluation()
            results = []
            for newIdent in newIdents:
                result = self.resolve_identifier_internal(newIdent, linkType, recursive, originalIdentifier, onlyWithVar)
                if result:
                    results.append(result)
            return results
        return []
            
    def resolve_remaining_identifiers(self):
        
        for identifier in self.identifiersToResolve:
            
            identifierName = identifier.name
            nameToSearch = identifierName
            prefix = identifier.get_prefix()
            if prefix:
                fullname = prefix + '.' + identifierName
            else:
                fullname = identifierName
                
            linkType = 'callLink'
            if identifierName == 'bind' and prefix:
                linkType = None
                index = prefix.rfind('.')
                if index >= 0:
                    nameToSearch = prefix[index + 1:]
                    prefix = prefix[:index]
                    fullname = prefix + '.' + nameToSearch
                else:
                    nameToSearch = prefix
                    prefix = None
                    fullname = nameToSearch
                    
            res = self.functions.get(nameToSearch)
            if res:
                if res.get_fullname() != fullname:
                    if not identifier.starts_with_this():
                        res = None
                if res:
                    identifier.add_resolution(res, linkType)
        
class ObjectDestructurationContext(ObjectValueContext):

    def __init__(self, parentContext, block, wasPreprocessed = True):
        ObjectValueContext.__init__(self, parentContext, None, block, wasPreprocessed)

class CurlyBracketedBlockContext(Context):
 
    def __init__(self, parentContext, block, wasPreprocessed = True):
         
        Context.__init__(self, parentContext, block, wasPreprocessed)

    def is_statements_block(self):
        return True

    def get_last_statements_block_context(self):
        
        return self
    
    def add_function(self, function):
        self.add_function_internal(function.get_name(), function)
    
    def add_variable(self, variable, isDeclaredWithVar):
        try:
            self.add_variable_internal(variable.get_fullname(), variable, isDeclaredWithVar)
        except:
            pass
    def add_identifier_to_resolve(self, identToResolve):
        self.identifiersToResolve.append(identToResolve)
    
    def resolve_identifier(self, identifier, linkType, recursive = True, originalIdentifier = None, onlyWithVar = False):
        # We are in CurlyBracketedBlockContext
        if not identifier.is_bracketed_identifier():
            
            res = self.resolve_identifier_internal(identifier, linkType, recursive, originalIdentifier, onlyWithVar)
            if res:
                return [ res ]

            if identifier.is_func_call():
                newIdent = Identifier(None, identifier.get_fullname(), None)
                if originalIdentifier:
                    res = self.resolve_identifier(newIdent, None, recursive, originalIdentifier, True)
                else:
                    res = self.resolve_identifier(newIdent, None, recursive, identifier, True)
                if res:
                    return res
            
        if identifier.is_bracketed_identifier():
            newIdents = identifier.create_identifiers_from_evaluation()
            results = []
            for newIdent in newIdents:
                result = self.resolve_identifier_internal(newIdent, linkType, recursive, originalIdentifier, onlyWithVar)
                if result:
                    results.append(result)
            return results
        return []

class BracketedBlockContext(Context):

    def __init__(self, parentContext, block):
        
        Context.__init__(self, parentContext, block, False)

class IfContext(Context):

    def __init__(self, parentContext, block):
        
        Context.__init__(self, parentContext, block, False)

    def is_statements_block(self):
        return True

    def get_last_statements_block_context(self):
        
        return self

class IfBlockContext(Context):

    def __init__(self, parentContext, block):
        
        Context.__init__(self, parentContext, block, False)

    def is_statements_block(self):
        return True

    def get_last_statements_block_context(self):
        
        return self

class SwitchContext(Context):

    def __init__(self, parentContext, block):
        
        Context.__init__(self, parentContext, block, False)

    def is_statements_block(self):
        return True

    def get_last_statements_block_context(self):
        
        return self

class SwitchCaseContext(Context):

    def __init__(self, parentContext, block):
        
        Context.__init__(self, parentContext, block, False)

    def is_statements_block(self):
        return True

    def get_last_statements_block_context(self):
        
        return self

class DefineContext(Context):

    def __init__(self, parentContext, define, wasPreprocessed = True):
        
        Context.__init__(self, parentContext, define, wasPreprocessed)
    
class RequireContext(Context):

    def __init__(self, parentContext, require, wasPreprocessed = True):
        
        Context.__init__(self, parentContext, require, wasPreprocessed)

class FunctionCallContext(Context):

    def __init__(self, parentContext, functionCall, isJSFunctionCall = False):
        
        Context.__init__(self, parentContext, functionCall, (True if isinstance(parentContext, FileContext) and parentContext.statement.is_module() else False))
        if isJSFunctionCall or ( isinstance(parentContext, FileContext) and parentContext.statement.is_module() ):
            self.wasPreprocessed = True
        self.isJSFunctionCall = isJSFunctionCall
        if isJSFunctionCall and parentContext:
            for ident in parentContext.unresolvedIdentifiers:
                self.add_unresolved_identifier(ident, False)
    
    def is_function_call_context(self):
        return True
    
    def is_js_function_call_context(self):
        if self.isJSFunctionCall:
            return True
        return False
    
    def add_function(self, function):
        self.add_function_internal(function.get_name(), function)

class FunctionCallPartContext(Context):

    def __init__(self, parentContext, functionCallPart):
        
        Context.__init__(self, parentContext, functionCallPart, parentContext.wasPreprocessed)

class ParameterContext(Context):

    def __init__(self, parentContext, functionCallPart, rang):
        
        Context.__init__(self, parentContext, functionCallPart, False)
        self.rang = rang
        
    def attach(self, expr):
        self.statement.add_parameter(expr, self.rang)

class AnyStatementContext(Context):

    def __init__(self, parentContext, stmt, wasPreprocessed = False):
        
        Context.__init__(self, parentContext, stmt, wasPreprocessed)

class ImportStatementContext(Context):

    def __init__(self, parentContext, stmt, wasPreprocessed = False):
        
        Context.__init__(self, parentContext, stmt, wasPreprocessed)

class AnyExpressionContext(Context):

    def __init__(self, parentContext, stmt):
        
        Context.__init__(self, parentContext, stmt, False)
        
    def attach(self, expr):
        self.statement.elements.append(expr)

class JsxContext(Context):

    def __init__(self, parentContext, stmt):
        
        Context.__init__(self, parentContext, stmt, False)
        
    def attach(self, expr):
        pass
    
    def resolve_identifier(self, identifier, linkType, recursive = True, originalIdentifier = None, onlyWithVar = False):
        res = self.resolve_identifier_internal(identifier, linkType, recursive, originalIdentifier, onlyWithVar)
        if res:
            return [ res ]
        return [ ]

class BinaryExpressionContext(Context):

    def __init__(self, parentContext, stmt):
        
        Context.__init__(self, parentContext, stmt, False)
        self.is_left_operand = True
        self.is_right_operand = False
        
    def attach(self, expr):
        if self.is_left_operand:
            self.statement.leftOperand = expr
        elif self.is_right_operand:
            self.statement.rightOperand = expr
        expr.parent = self.statement

class TernaryExpressionContext(Context):

    def __init__(self, parentContext, stmt):
        
        Context.__init__(self, parentContext, stmt, False)
        self.is_if_operand = True
        self.is_then_operand = False
        self.is_else_operand = False
        
    def attach(self, expr):
        if self.is_if_operand:
            self.statement.ifOperand = expr
        elif self.is_then_operand:
            self.statement.thenOperand = expr
        elif self.is_else_operand:
            self.statement.elseOperand = expr
        expr.parent = self.statement

class UnaryExpressionContext(Context):

    def __init__(self, parentContext, stmt):
        
        Context.__init__(self, parentContext, stmt, False)

    def attach(self, expr):
        self.statement.operand = expr

class AssignmentContext(Context):

    def __init__(self, parentContext, assignment, wasPreprocessed = True):
        
        Context.__init__(self, parentContext, assignment, wasPreprocessed)
    
    def is_assignment_context(self):
        return True

class VarDeclarationContext(Context):

    def __init__(self, parentContext, varDecl, wasPreprocessed = True):
        
        Context.__init__(self, parentContext, varDecl, wasPreprocessed)
        self.current_element_index = -1

class IdentifierContext(Context):

    def __init__(self, parentContext, wasPreprocessed = True):
        
        Context.__init__(self, parentContext, None, wasPreprocessed)
