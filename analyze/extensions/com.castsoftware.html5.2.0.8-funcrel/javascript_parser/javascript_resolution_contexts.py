import cast.analysers.ua
import traceback

class Context:
    def __init__(self, parent, statement):
        self.statement = statement
        self.parent = parent
        """
        v = Rectangle() where Rectangle is a class constructor
        an item is put in self.classInstances with key = 'v' as a string and value = the class
        """
        self.classInstances = {}

    def get_requires(self):
        if self.parent:
            return self.parent.get_requires()
        return {}

    def get_imports(self):
        if self.parent:
            return self.parent.get_imports()
        return {}

    def add_namespace_context(self, name, context):
        if self.parent:
            return self.parent.add_namespace_context(name, context)

    def get_namespace_context(self, name):
        if self.parent:
            return self.parent.get_namespace_context(name)
        return None

    def get_fullname(self):
        if self.statement:
            return self.statement.get_fullname()
        return ''
    
    def is_in_class(self):
        if self.parent:
            return self.parent.is_in_class()
        return False

    def get_current_class(self):
        if self.parent:
            return self.parent.get_current_class()
        return None
    
    def get_class_of_instance(self, variableName):
        if variableName in self.classInstances:
            return self.classInstances[variableName]
        if self.parent:
            return self.parent.get_class_of_instance(variableName)
        return None
    
    def add_require(self, ident, req):
        if self.parent:
            return self.parent.add_require(ident, req)

    def add_import(self, ident):
        if self.parent:
            return self.parent.add_import(ident)
        
    def add_function(self, func, keyName):
        if self.parent:
            return self.parent.add_function(func, keyName)

    def add_variable(self, _var, keyName):
        if self.parent:
            return self.parent.add_variable(_var, keyName)

    def add_class(self, _class):
        if self.parent:
            return self.parent.add_class(_class)

    def get_functions(self, name, ast = None):
        if self.parent:
            return self.parent.get_functions(name, ast)
        return []

    def get_methods_of_class(self, classname, methodName):
        if self.parent:
            return self.parent.get_methods_of_class(classname, methodName)
        return []

    def get_variables(self, name, local = False):
        if self.parent:
            return self.parent.get_variables(name, local)
        return []

    def get_variables_and_functions(self, name, ast, local = False):
        if self.parent:
            return self.parent.get_variables_and_functions(name, ast, local)
        return []

    def get_classes(self, name):
        if self.parent:
            return self.parent.get_classes(name)
        return []
    
    def duplicate_functions_for_prototype(self, fromPrefix, toPrefix):
        if self.parent:
            self.parent.duplicate_functions_for_prototype(fromPrefix, toPrefix)

class BlockContext(Context):
    def __init__(self, parent, statement):
        Context.__init__(self, parent, statement)
        self.functionsByName = {}
        self.variablesByName = {}
        self.classesByName = {}
        self.namespaceContexts = {} # namespace contexts by name

    def add_namespace_context(self, name, context):
        self.namespaceContexts[name] = context

    def get_namespace_context(self, name):
        if name in self.namespaceContexts:
            return self.namespaceContexts[name]
        if self.parent:
            return self.parent.get_namespace_context(name)
            
    """
    Motorbike.prototype = Bicycle.prototype;
    """
    def duplicate_functions_for_prototype(self, fromPrefix, toPrefix):
        toAdd = {}
        for name, funcs in self.functionsByName.items():
            newKey = toPrefix + name[len(fromPrefix):]
            if name.startswith(fromPrefix + '.'):
                toAdd[newKey] = funcs
        if toAdd:
            for name, funcs in toAdd.items():
                for func in funcs:
                    self.add_function(func, name)
        if self.parent:
            self.parent.duplicate_functions_for_prototype(fromPrefix, toPrefix)
        
    def add_function(self, func, keyName):
        if keyName:
            kn = keyName
            while 'NONAME' in kn: # NONAME_2.p.kill
                index = kn.find('.', kn.find('NONAME'))
                if index >= 0:
                    kn = kn[:kn.find('NONAME')] + kn[index+1:]
                else:
                    break
            if '.prototype.' in kn:
                kn = kn.replace('.prototype.', '.')
                
            if kn in self.functionsByName:
                l = self.functionsByName[kn]
            else:
                l = []
                self.functionsByName[kn] = l
            if not func in l:
                l.append(func)
        
        if keyName.startswith('$scope.') and self.parent:
            self.parent.add_function(func, keyName)
        
    def add_variable(self, _var, keyName):
        if not is_var(_var.parent) and not is_var_declaration(_var.parent):
            vs = self.get_variables(keyName, True)
            if vs:
                if not is_assignment(vs[0].parent) or not is_function(vs[0].parent.get_right_operand()):
                    return
        
        name = keyName
        if not name.endswith('.prototype'):
            if name in self.variablesByName:
                l = self.variablesByName[name]
            else:
                l = []
                self.variablesByName[name] = l
            if not _var in l and (not _var.get_resolutions() or _var.resolutions[0].callee not in l):
                l.append(_var)
        
        if keyName.startswith('$scope.') and self.parent:
            self.parent.add_variable(_var, keyName)
            
        if self.parent and '.' in keyName:
            prefix = keyName[:keyName.find('.')]
            if not prefix in self.variablesByName:
                self.parent.add_variable(_var, keyName)
        
    def add_class(self, _class):
        name = _class.get_name()
        if name in self.classesByName:
            l = self.classesByName[name]
        else:
            l = []
            self.classesByName[name] = l
        l.append(_class)

    def get_functions(self, name, ast = None):
        if name in self.functionsByName:
            return self.functionsByName[name]
        if self.parent:
            return self.parent.get_functions(name, ast)
        return []

    def get_methods_of_class(self, classname, methodName):
        if self.parent:
            return self.parent.get_methods_of_class(classname, methodName)
        return []

    def get_variables(self, name, local = False):
        v = []
        if name in self.variablesByName:
            v = self.variablesByName[name]
            if v and is_assignment(v[0].parent) and is_function_call(v[0].parent.get_right_operand()) and v[0].parent.get_right_operand().get_function_call_parts()[0].get_name() == 'require':
                if self.parent:
                    return self.parent.get_variables(name, local)
                else:
#                     return v
                    pass
            else:
                return v
        if not local and self.parent:
            return self.parent.get_variables(name, local)
        
#         if v and not name in self.get_requires() and not name in self.get_imports():
#             return v
        return []

    def get_variables_and_functions(self, name, ast, local = False):
        l = []
        if name in self.variablesByName:
            if not self.variablesByName[name][0].get_resolutions():
                l.extend(self.variablesByName[name])
                if l and is_assignment(l[0].parent) and is_function_call(l[0].parent.get_right_operand()) and l[0].parent.get_right_operand().get_function_call_parts()[0].get_name() == 'require':
                    l = []
            else:
                done = False
                for resol in self.variablesByName[name][0].get_resolutions():
                    try:
                        if resol.callee.get_file() == ast.get_file() and resol.callee.get_fullname() == ast.get_fullname():
                            l.append(resol.callee)
                            done = True
                            if l and is_assignment(l[0].parent) and is_function_call(l[0].parent.get_right_operand()) and l[0].parent.get_right_operand().get_function_call_parts()[0].get_name() == 'require':
                                l = []
                    except:
                        pass
                if not done:
                    l.extend(self.variablesByName[name])
                    if l and is_assignment(l[0].parent) and is_function_call(l[0].parent.get_right_operand()) and l[0].parent.get_right_operand().get_function_call_parts()[0].get_name() == 'require':
                        l = []
        
        if name in self.functionsByName:
            l.extend(self.functionsByName[name])
            
        if l:
            return l
        
        if self.parent:
            return self.parent.get_variables_and_functions(name, ast, local)
        return []

    def get_classes(self, name):
        if name in self.classesByName:
            return self.classesByName[name]
        if self.parent:
            return self.parent.get_classes(name)
        return []
    
    def __repr__(self):
        return 'BlockContext ' + str(self.statement)

"""
When we have:
nm.f = function() {};
nm.v = function() { this.f();};
this corresponds to the namespace nm (self.name is nm), then a link should be created from v function to f
these contexts must be kept during all file parsing and reused when we enter back in the context with same name
"""
class NamespaceContext(Context):
    def __init__(self, parent, name, prefix = None):
        Context.__init__(self, parent, None)
        self.prefix = prefix
        self.name = name
        self.functionsByName = {}
        self.variablesByName = {}
#         self.parents = []
        self.level = 0
        
    def add_function(self, func, keyName, thisPrefix = True):

        if '.' in keyName:
            names = keyName.split('.')
            funcname = names[-1]
            names = names[:-1]
            
            for name in reversed(names):
                if name == self.name:
                    if funcname in self.functionsByName:
                        l = self.functionsByName[funcname]
                    else:
                        l = []
                        self.functionsByName[funcname] = l
                    if not func in l:
                        l.append(func)
                    if thisPrefix:
                        if 'this.' + funcname in self.functionsByName:
                            l = self.functionsByName['this.' + funcname]
                        else:
                            l = []
                            self.functionsByName['this.' + funcname] = l
                        if not func in l:
                            l.append(func)
                    break
        if self.parent:
            return self.parent.add_function(func, keyName)

    def add_variable(self, _var, keyName):
        if '.' in keyName:
            prefix = keyName[:keyName.find('.')]
            suffix = keyName[keyName.find('.') + 1:]
            if prefix == self.name and not suffix == 'prototype':
                if suffix in self.variablesByName:
                    l = self.variablesByName[suffix]
                else:
                    l = []
                    self.variablesByName[suffix] = l
                l.append(_var)
        if self.parent:
            return self.parent.add_variable(_var, keyName)

    def get_functions(self, name, ast = None):
#         if name in self.functionsByName:
#             return self.functionsByName[name]
#         if self.parent:
#             return self.parent.get_functions(name, ast)
#         return []
    
        if '.' in name and name in self.functionsByName:
            return self.functionsByName[name]
        if self.parent:
            return self.parent.get_functions(name, ast)
        return []
    
#         if name in self.functionsByName:
#             if not '.' in name:
#                 l = []
#                 for f in self.functionsByName[name]:
#                     if f.get_prefix():
#                         continue
#                     l.append(f)
#                 if l:
#                     return l
#         if self.parent:
#             l = self.parent.get_functions(name, ast)
#             if not l and name in self.functionsByName:
#                 return self.functionsByName[name]
#         return []

    def get_variables(self, name, local = False):
        if name in self.variablesByName:
            return self.variablesByName[name]
        if self.parent:
            return self.parent.get_variables(name, local)
        return []

    def get_variables_and_functions(self, name, ast, local = False):
        l = []
        if name in self.variablesByName:
            l.extend(self.variablesByName[name])

        if '.' in name and name in self.functionsByName:
            l.extend(self.functionsByName[name])
            
        if l:
            return l
        
        if self.parent:
            return self.parent.get_variables_and_functions(name, ast, local)
        return []
    
    def __repr__(self):
        return 'NamespaceContext ' + str(self.name)

class JSContext(BlockContext):
    def __init__(self, parent, statement, htmlContentsByJS, globalFunctionsByName, globalVariablesByName, globalClassesByName):
        BlockContext.__init__(self, parent, statement)
        self.globalFunctionsByName = globalFunctionsByName
        self.globalVariablesByName = globalVariablesByName
        self.globalClassesByName = globalClassesByName
        self.htmlContentsByJS = htmlContentsByJS
        self.requires = {}          # a = require('XXX'); or a = require('XXX').YYY
        """
        import { fetchProductsReferences, fetchProductReference } from '../../../actions/stock/products';
        is stored with keys fetchProductsReferences and fetchProductReference and values are resolution callees
        """
        self.imports = {}

    def get_requires(self):
        return self.requires

    def get_imports(self):
        return self.imports
    
    def add_require(self, ident, req):
        self.requires[ident.get_name()] = req

    def add_import(self, ident):
        try:
            if ident[0].get_resolutions():
                for resol in ident[0].get_resolutions():
                    self.imports[ident[0].get_name()] = resol.callee
                    break
        except:
            print(str(traceback.format_exc()))
            cast.analysers.log.debug(str(traceback.format_exc()).replace('Traceback (most recent call last)', 'add_import issue'))        

    def get_global_function(self, jsContent, name):
        if name in self.globalFunctionsByName:
            for glob in self.globalFunctionsByName[name]:
                if glob.file == jsContent.file:
                    return glob.get_kb_symbol()
        moduleExports = jsContent.get_module_exports()
        if moduleExports:
            try:
                if moduleExports.get_name() + '.' + name in self.globalFunctionsByName:
                    for glob in self.globalFunctionsByName[moduleExports.get_name() + '.' + name]:
                        if glob.file == jsContent.file:
                            return glob.get_kb_symbol()
                elif moduleExports.get_name() in self.globalClassesByName:
                    for glob in self.globalClassesByName[moduleExports.get_name()]:
                        if glob.file == jsContent.file:
                            cl = glob.get_kb_symbol()
                            meths = cl.get_methods(name)
                            if meths:
                                return meths[0]
                else:
                    if is_assignment(moduleExports.parent):
                        if is_new_expression(moduleExports.parent.get_right_operand()):
                            fcall = moduleExports.parent.get_right_operand().elements[1].get_function_call_parts()[0]
                            fn = fcall.get_name() + '.' + name
                            if fn in self.globalFunctionsByName:
                                for glob in self.globalFunctionsByName[fn]:
                                    if glob.file == jsContent.file:
                                        return glob.get_kb_symbol()
            except:
                pass
        return None
        
    def get_global_variable(self, jsContent, name):
        if name in self.globalVariablesByName:
            for glob in self.globalVariablesByName[name]:
                if glob.file == jsContent.file:
                    if glob.identifier.get_fullname().startswith('module.exports.') and glob.identifier.parent and is_object_value(glob.identifier.parent):
                        ident = glob.identifier.parent.get_item(name)
                        if ident and ident.get_resolutions():
                            return ident.get_resolutions()[0].callee
                        else:
                            return glob.identifier
                    else:
                        return glob.identifier
        return None
        
    def get_functions_globally(self, name):
        # We search globally
        if name in self.globalFunctionsByName:
            l = []
            if len(self.globalFunctionsByName[name]) > 1:
                oneConnected = False
                for glob in self.globalFunctionsByName[name]:
#                     find if one htmlContent contains both js files
                    if self.jsfiles_are_connected(self.statement.get_file(), glob.file):
                        oneConnected = True
                        l.append(glob.kbSymbol)
            else:
                oneConnected = False
            if not oneConnected:
                for glob in self.globalFunctionsByName[name]:
                    l.append(glob.kbSymbol)
            return l

        if name in self.globalClassesByName:
            # We search for a class constructor
            l = []
            for glob in self.globalClassesByName[name]:
                if self.jsfiles_are_connected(self.statement.get_file(), glob.file):
                    cl = glob.kbSymbol
                    m = cl.get_method(name)
                    if m:
                        l.append(m)
                        return l
        return []
        
    def get_functions(self, name, ast = None):
        if name.startswith('window.'):
            return BlockContext.get_functions(self, name[7:], ast)
        # We search locally
        fs = BlockContext.get_functions(self, name, ast)
        if fs:
            return fs
        
        # we search through require()
        if self.requires:
            if '.' in name:
                prefix = name[:name.find('.')]
                if prefix in self.requires:
                    req = self.requires[prefix]
                    l = []
                    for jsContent in req.jsContentCallees:
                        if req.objectName:
                            func = self.get_global_function(jsContent, req.objectName + name[name.find('.'):])
                            if func:
                                return [ func ]
                        else:
                            func = jsContent.get_module_exports(name[name.find('.') + 1:])
                            if func:
                                return [ func ]
                            
                            if prefix in self.globalClassesByName:
                                globs = self.globalClassesByName[prefix]
                                if globs:
                                    for glob in globs:
                                        if glob.file == jsContent.file: 
                                            m = glob.get_method(name[name.find('.') + 1:])
                                            if m:
                                                return [ m ]
                                            return []
                        func = self.get_global_function(jsContent, name[name.find('.') + 1:])
                        if func:
                            l.append(func)
                    if l:
                        return l
            else:
                """
                const ProductsController = require('./app2');
                var products = new ProductsController(apiRouter); --> class constructor call
                """
                """
                const { f } = require('./app2');
                f();
                """
                if name in self.requires:
                    req = self.requires[name]
                    l = []
                    for jsContent in req.jsContentCallees:
                        if name in self.globalClassesByName:
                            globs = self.globalClassesByName[name]
                            if globs:
                                for glob in globs:
                                    if glob.file == jsContent.file: 
                                        m = glob.get_method(name)
                                        if m:
                                            return [ m ]
                                        return []
                    for jsContent in req.jsContentCallees:
                        if name in self.globalFunctionsByName:
                            globs = self.globalFunctionsByName[name]
                            if globs:
                                for glob in globs:
                                    if glob.file == jsContent.file: 
                                        m = glob.get_kb_symbol()
                                        if m:
                                            return [ m ]
                                        return []
        
        # we search through imports
        if self.imports:
            if name in self.imports:
                imp = self.imports[name]
                if is_class(imp):
                    constr = imp.get_methods(imp.get_name())
                    if constr:
                        return constr
                    else:
                        return []
                else:
                    return [ imp ]
                return []
            if '.' in name:
                prefix = name[:name.find('.')]
                if prefix in self.imports:
                    imp = self.imports[prefix]
                    if is_class(imp):
                        suffix = name[name.find('.') + 1]
                        m = imp.get_method(suffix)
                        if m:
                            return [ m ]
                        else:
                            return []
        
        # We search globally
        l = self.get_functions_globally(name)
        if l:
            return l
                    
        if self.statement.module:
            for param, value in self.statement.module.parameters.items():
                if name == param.get_name() or name.startswith(param.get_name() + '.'):
                    if type(value) is str:
                        nameToSearch = value.replace('/', '.') + name[name.find('.'):]
                        l = self.get_functions_globally(nameToSearch)
                        if l:
                            return l
                    break
        return []

    def get_methods_of_class(self, classname, methodName):

        l = []
        if classname in self.globalClassesByName:
            # We search for a class constructor
            oneConnected = False
            for glob in self.globalClassesByName[classname]:
                if self.jsfiles_are_connected(self.statement.get_file(), glob.file):
                    oneConnected = True
                    cl = glob.kbSymbol
                    m = cl.get_method(methodName, False, True)
                    if m:
                        l.append(m)
                        return l
            if not oneConnected:
                for glob in self.globalClassesByName[classname]:
                    cl = glob.kbSymbol
                    m = cl.get_method(methodName, False, True)
                    if m:
                        l.append(m)
        return l

    def get_variables_and_functions_globally(self, name):
        
        vs = []
        # We search globally
        if name in self.globalVariablesByName:
            if len(self.globalVariablesByName[name]) > 1:
                oneConnected = False
                for glob in self.globalVariablesByName[name]:
#                     find if one htmlContent contains both js files
                    if self.jsfiles_are_connected(self.statement.get_file(), glob.file):
                        oneConnected = True
                        if glob.identifier.get_fullname() == name:
                            vs.append(glob.identifier)
            else:
                oneConnected = False
            if not oneConnected:
                for glob in self.globalVariablesByName[name]:
                    if glob.identifier.get_fullname() == name:
                        vs.append(glob.identifier)
                        
        if name in self.globalFunctionsByName:
            if len(self.globalFunctionsByName[name]) > 1:
                oneConnected = False
                for glob in self.globalFunctionsByName[name]:
#                     find if one htmlContent contains both js files
                    if self.jsfiles_are_connected(self.statement.get_file(), glob.file):
                        oneConnected = True
                        vs.append(glob.kbSymbol)
            else:
                oneConnected = False
            if not oneConnected:
                for glob in self.globalFunctionsByName[name]:
                    vs.append(glob.kbSymbol)

        elif name in self.globalClassesByName:
            # We search for a class constructor
            for glob in self.globalClassesByName[name]:
                if self.jsfiles_are_connected(self.statement.get_file(), glob.file):
                    cl = glob.kbSymbol
                    m = cl.get_method(name)
                    if m:
                        vs.append(m)
                        
        return vs

    def get_variables_and_functions(self, name, ast, local = False):
        # We search locally
        vs = BlockContext.get_variables(self, name, local)
        if name.startswith('window.'):
            vs.extend(BlockContext.get_functions(self, name[7:], ast))
        else:
            # We search locally
            vs.extend(BlockContext.get_functions(self, name, ast))
        
        if vs or local:
            return vs

        # we search through require()
        if self.requires:
            if '.' in name:
                prefix = name[:name.find('.')]
                if prefix in self.requires:
                    req = self.requires[prefix]
                    l = []
                    for jsContent in req.jsContentCallees:
                        if req.objectName:
                            vs.append(self.get_global_variable(jsContent, req.objectName + name[name.find('.'):]))
                        if not vs:
                            v = self.get_global_variable(jsContent, name[name.find('.') + 1:])
                            if v:
                                vs.append(v)
            else:
                if name in self.requires:
                    req = self.requires[name]
                    l = []
                    for jsContent in req.jsContentCallees:
                        if req.objectName:
                            v = self.get_global_variable(jsContent, req.objectName + name)
                            if v:
                                vs.append(v)
                        else:
                            moduleExports = jsContent.get_module_exports()
                            if moduleExports:
                                if is_identifier(moduleExports) or is_function_call(moduleExports) or is_new_expression(moduleExports):
                                    return [ moduleExports ]
                                else:
                                    return [ ]
                            else:
                                v = self.get_global_variable(jsContent, name)
                                if v:
                                    vs.append(v)
                        
                        if not vs:
                            v = self.get_global_variable(jsContent, name)
                            if v:
                                vs.append(v)
                                
            vs2 = []
            if '.' in name:
                prefix = name[:name.find('.')]
                if prefix in self.requires:
                    req = self.requires[prefix]
                    l = []
                    for jsContent in req.jsContentCallees:
                        if req.objectName:
                            func = self.get_global_function(jsContent, req.objectName + name[name.find('.'):])
                            if func:
                                vs2.append(func)
                        else:
                            if prefix in self.globalClassesByName:
                                globs = self.globalClassesByName[prefix]
                                if globs:
                                    for glob in globs:
                                        if glob.file == jsContent.file: 
                                            m = glob.get_method(name[name.find('.') + 1:])
                                            if m:
                                                vs2.append(m)
                        if not vs2:
                            func = self.get_global_function(jsContent, name[name.find('.') + 1:])
                            if func:
                                vs2.append(func)
            else:
                """
                const ProductsController = require('./app2');
                var products = new ProductsController(apiRouter); --> class constructor call
                """
                if name in self.requires:
                    req = self.requires[name]
                    l = []
                    for jsContent in req.jsContentCallees:
                        if name in self.globalClassesByName:
                            globs = self.globalClassesByName[name]
                            if globs:
                                for glob in globs:
                                    if glob.file == jsContent.file: 
                                        m = glob.get_method(name)
                                        if m:
                                            vs2.append(m)
            vs.extend(vs2)
            
        if vs:
            return vs
        
        # we search through imports
        if self.imports:
            if name in self.imports:
                imp = self.imports[name]
                if is_class(imp):
                    constr = imp.get_methods(imp.get_name())
                    if constr:
                        vs.extend(constr)
                else:
                    vs.append(imp)
            elif '.' in name:
                prefix = name[:name.find('.')]
                if prefix in self.imports:
                    imp = self.imports[prefix]
                    if is_class(imp):
                        suffix = name[name.find('.') + 1]
                        m = imp.get_method(suffix)
                        if m:
                            vs.append(m)
        if vs:
            return vs
        
        # We search globally
        vs = self.get_variables_and_functions_globally(name)
        if vs:
            return vs
        
        if self.statement.module:
            for param, value in self.statement.module.parameters.items():
                if name == param.get_name() or name.startswith(param.get_name() + '.'):
                    if type(value) is str:
                        nameToSearch = value.replace('/', '.') + name[name.find('.'):]
                        vs = self.get_variables_and_functions_globally(nameToSearch)
                        if vs:
                            return vs
                    break
        return vs

    def get_variables_globally(self, name):
        # We search globally
        if name in self.globalVariablesByName:
            l = []
            if len(self.globalVariablesByName[name]) > 1:
                oneConnected = False
                for glob in self.globalVariablesByName[name]:
#                     find if one htmlContent contains both js files
                    if self.jsfiles_are_connected(self.statement.get_file(), glob.file):
                        oneConnected = True
                        if glob.identifier.get_fullname() == name:
                            l.append(glob.identifier)
            else:
                oneConnected = False
            if not oneConnected:
                for glob in self.globalVariablesByName[name]:
                    if glob.identifier.get_fullname() == name:
                        l.append(glob.identifier)
            return l
        return []        

    def get_variables(self, name, local = False):
        # We search locally
        vs = BlockContext.get_variables(self, name, local)
        if vs:
            return vs
        if local:
            return vs
                    
        # we search through require()
        if self.requires:
            if '.' in name:
                prefix = name[:name.find('.')]
                if prefix in self.requires:
                    req = self.requires[prefix]
                    l = []
                    for jsContent in req.jsContentCallees:
                        if req.objectName:
                            v = self.get_global_variable(jsContent, req.objectName + name[name.find('.'):])
                            if v:
                                return [ v ]
                        v = self.get_global_variable(jsContent, name[name.find('.') + 1:])
                        if v:
                            l.append(v)
                    if l:
                        return l
            else:
                if name in self.requires:
                    req = self.requires[name]
                    l = []
                    for jsContent in req.jsContentCallees:
                        if req.objectName:
                            v = self.get_global_variable(jsContent, req.objectName + name)
                            if not v:
                                v = self.get_global_variable(jsContent, req.objectName)
                            if v:
                                return [ v ]
                        else:
#                             v = jsContent.get_global_variable('module.exports')
#                             if v:
#                                 if is_assignment(v.parent) and is_identifier(v.parent.get_right_operand()):
#                                     return [ v.parent.get_right_operand() ]
                            moduleExports = jsContent.get_module_exports()
                            if moduleExports:
                                if is_identifier(moduleExports) or is_function_call(moduleExports) or is_new_expression(moduleExports) or is_object_value(moduleExports):
                                    return [ moduleExports ]
                                else:
                                    return [ ]
                            else:
                                v = self.get_global_variable(jsContent, name)
                                if v:
                                    return [ v ]
                        
                        v = self.get_global_variable(jsContent, name)
                        if v:
                            l.append(v)
        
        # We search globally
        l = self.get_variables_globally(name)
        if l:
            return l
        
        if self.statement.module:
            for param, value in self.statement.module.parameters.items():
                if name == param.get_name() or name.startswith(param.get_name() + '.'):
                    if type(value) is str:
                        nameToSearch = value.replace('/', '.') + name[name.find('.'):]
                        l = self.get_variables_globally(nameToSearch)
                        if l:
                            return l
                    break

        return []
        
    def jsfiles_are_connected(self, jsFile1, jsFile2):
        
        if jsFile1 == jsFile2:
            return True
        
        path1 = jsFile1.get_path()
        path2 = jsFile2.get_path()
        
        try:
            # if we are in a html or jsp file (self.parent is then an HtmlContent        
            if self.statement.parent.jsFiles:
                if path2 in self.statement.parent.jsFiles:
                    return True
                else:
                    return False
            else:
                return False
        except:
            pass
        
        if not self.htmlContentsByJS:   # case if one file is a jsp
            if not path1.endswith('.js') or not path2.endswith('.js'):
                return True
        
        if not path1 in self.htmlContentsByJS:
            if path2 in self.htmlContentsByJS:
                for htmlContent in self.htmlContentsByJS[path2]:
                    if path1 == htmlContent.file.get_path():
                        return True
            return False
        elif not path2 in self.htmlContentsByJS:
            return False
        
        return set(self.htmlContentsByJS[path1]).intersection(self.htmlContentsByJS[path2])
    
    def __repr__(self):
        return 'JSContext ' + str(self.statement)
    
class FunctionContext(BlockContext):
    def __init__(self, parent, statement):
        BlockContext.__init__(self, parent, statement)
        if statement.get_fullname() and '.prototype.' in statement.get_fullname():
            self.prototypeName = statement.get_prefix()[:-10]
        else:
            self.prototypeName = None
        for param in statement.get_parameters():
            if is_identifier(param):
                self.add_variable(param, param.get_name())
    
    def add_function(self, func, kn):
        keyName = kn
        if '.' in keyName and keyName.startswith('NONAME'):
            keyName = keyName[keyName.find('.') + 1:]
        if '.prototype.' in keyName:
            keyName = keyName.replace('.prototype.', '.')
            if keyName.startswith('this.'):
                keyName = keyName[5:]
        if keyName:
            if keyName in self.functionsByName:
                l = self.functionsByName[keyName]
            else:
                l = []
                self.functionsByName[keyName] = l
            if not func in l:
                l.append(func)
            
            if self.statement.get_name():
                if isinstance(self.parent, FunctionContext):
                    newKeyname = self.statement.get_name() + '.' + keyName
                    newKeyname = newKeyname.replace('.this.', '.')
                    newKeyname = newKeyname.replace('.self.', '.')
                    self.parent.add_function(func, newKeyname)
                    self.parent.add_function(func, 'this.' + newKeyname)
                    if is_assignment(self.statement.parent) and self.statement.parent.get_left_operand().get_fullname().startswith('this.'):
                        self.parent.add_function(func, 'this.' + keyName)
#                     self.parent.add_function(func, 'self.' + newKeyname)
                elif isinstance(self.parent, NamespaceContext):
                    newKeyname = self.statement.get_name() + '.' + keyName
                    newKeyname = newKeyname.replace('.this.', '.')
#                     newKeyname = newKeyname.replace('.self.', '.')
                    self.parent.add_function(func, newKeyname)
            if keyName.startswith('$scope.') and self.parent:
                self.parent.add_function(func, keyName)
        if self.statement.get_name() == None and self.parent:
            self.parent.add_function(func, kn)

    def get_functions(self, name, ast = None):
        newName = name
#         if name.startswith('self.') and self.statement.get_name():
#             if not self.statement.parent or not is_object_value(self.statement.parent):
#                 n = self.statement.get_name()+ name[4:]
#             else:
#                 n = self.statement.get_name()+ name[4:]
#             if n in self.functionsByName:
#                 return self.functionsByName[n]
        if name.startswith('this.') and self.statement.get_name():
            if self.prototypeName:
                newName = name.replace('this', self.prototypeName)
                n = newName
            else:
                if not self.statement.parent or not is_object_value(self.statement.parent):
                    n = self.statement.get_name()+ newName[4:]
                else:
                    n = self.statement.get_name()+ newName[4:]
            if n in self.functionsByName:
                return self.functionsByName[n]
#         if name.startswith('this.') and self.statement.get_name():
#             funcs = self.parent.get_functions(name.replace('this.', self.statement.get_name() + '.'))
#             if funcs:
#                 return funcs
        if name.startswith('this.'):
            if self.statement.get_name():
                if is_object_value(self.statement.get_parent()):
                    funcs = self.parent.get_functions(name)
                else:
                    funcs = self.parent.get_functions(name.replace('this.', self.statement.get_name() + '.'))
                if funcs:
                    return funcs
        return BlockContext.get_functions(self, newName, ast)

    def add_variable(self, _var, keyName):
        name = keyName
        if name in self.variablesByName:
            l = self.variablesByName[name]
        else:
            l = []
            self.variablesByName[name] = l
        if not _var in l and (not _var.get_resolutions() or _var.resolutions[0].callee not in l):
            l.append(_var)
        """
        function tabpanel() {
          this.tabs = this.$panel.find('.toggle-header');
        }
        tabpanel.prototype.bindHandlers = function() {
          this.tabs.focus(function() {});
        """
        if keyName.startswith('this.') and self.statement.get_fullname():
            self.parent.add_variable(_var, self.statement.get_fullname() + keyName[4:])
            
        if is_object_value(self.statement.parent):
            """
var App = {
        cacheElements: function () {
            this.$todoList = 1;
        },
        bindEvents: function () {
            var list = this.$todoList;
        }
};
            """
            if not is_assignment(_var.parent) or not is_var(_var.parent):
                self.parent.add_variable(_var, keyName)
        
        if keyName.startswith('$scope.') and self.parent:
            self.parent.add_variable(_var, keyName)
            
        if '.' in keyName:
            prefix = keyName[:keyName.find('.')]
            if not prefix in self.variablesByName:
                self.parent.add_variable(_var, keyName)
    
    def __repr__(self):
        return 'FunctionContext ' + str(self.statement)

class ClassContext(Context):
    def __init__(self, parent, statement):
        Context.__init__(self, parent, statement)

    def is_in_class(self):
        return True

    def get_current_class(self):
        return self.statement

    def get_methods(self, name):
        newName = name
        if name.startswith('this.'):
            newName = newName[5:]
            meth = self.statement.get_method(newName)
            if meth:
                return [ meth ]
            else:
                return []
        elif name.startswith('super.'):
            newName = newName[6:]
            superClass = self.statement.get_super_class()
            if superClass:
                meth = superClass.get_method(newName)
                if meth:
                    return [ meth ]
                else:
                    return []
        return []

    def get_functions(self, name, ast = None):
        if name.startswith(('this', 'super')):
            ms = self.get_methods(name)
            if ms:
                return ms
        return self.parent.get_functions(name, ast)

    def get_methods_of_class(self, classname, methodName):

        if classname == self.statement.get_name():
            return self.get_methods(methodName)
        return self.parent.get_methods_of_class(classname, methodName)
    
    def __repr__(self):
        return 'ClassContext ' + str(self.statement)

class MethodContext(FunctionContext):
    def __init__(self, parent, statement):
        FunctionContext.__init__(self, parent, statement)

    def get_methods(self, name):
        return self.parent.get_methods(name)
        
    def __repr__(self):
        return 'MethodContext ' + str(self.statement)

class ObjectValueContext(Context):
    def __init__(self, parent, statement, name):
        Context.__init__(self, parent, statement)
        self.name = name
        self.functionsByName = {}
        self.variablesByName = {}
        for key, item in statement.get_items_dictionary().items():
            if is_function(item):
#                 self.add_function(item, item.get_name())
                self.add_function(item, 'this.' + item.get_name())
                parent = self.parent
                keyname = str(self.name) + '.' + item.get_name()
                while parent and isinstance(parent, (ObjectValueContext, NamespaceContext)):
#                     parent.add_function(item, keyname)
                    parent.add_function(item, 'this.' + keyname)
                    keyname = str(parent.name) + '.' + keyname
                    parent = parent.parent
                parent.add_function(item, 'this.' + keyname)
            else:
                if key.get_name():
                    self.add_variable(key, 'this.' + key.get_name())
        
    def add_function(self, func, keyName):
        if keyName:
            if keyName in self.functionsByName:
                l = self.functionsByName[keyName]
            else:
                l = []
                self.functionsByName[keyName] = l
            if not func in l:
                l.append(func)
            return

        name = func.get_name()
        if name in self.functionsByName:
            l = self.functionsByName[name]
        else:
            l = []
            self.functionsByName[name] = l
        if not func in l:
            l.append(func)
        if 'this.' + name in self.functionsByName:
            l = self.functionsByName['this.' + name]
        else:
            l = []
            self.functionsByName['this.' + name] = l
        if not func in l:
            l.append(func)
        if func.get_prefix():
            name = func.get_fullname()
            if name in self.functionsByName:
                l = self.functionsByName[name]
            else:
                l = []
                self.functionsByName[name] = l
            if not func in l:
                l.append(func)
                
        if self.parent and isinstance(self.parent, ObjectValueContext):
            self.parent.add_function(func, keyName)
        
        if keyName.startswith('$scope.') and self.parent:
            self.parent.add_function(func, keyName)
        
    def add_variable(self, _var, keyName):
        name = keyName
        if not name.startswith('this'):
            """
            Avoid having both this.userModel and userModel in ov context
            ov = {
                userModel : null,
                f : function() {
                    userModel = ...
                }
            }
            """
            newName = 'this.' + name
            if newName in self.variablesByName:
                return
        if name in self.variablesByName:
            l = self.variablesByName[name]
        else:
            l = []
            self.variablesByName[name] = l
        if not _var in l and (not _var.get_resolutions() or _var.resolutions[0].callee not in l):
            l.append(_var)

        if self.name:
            newKeyname = self.name + '.' + keyName
            newKeyname = newKeyname.replace('.this.', '.')
            newKeyname = newKeyname.replace('.self.', '.')
            self.parent.add_variable(_var, newKeyname)
        
        if keyName.startswith('$scope.') and self.parent:
            self.parent.add_variable(_var, keyName)
        
    def get_name(self):
        return self.name

    def get_functions(self, name, ast = None):
        n = name
        if n in self.functionsByName:
            return self.functionsByName[n]
        if self.parent:
            return self.parent.get_functions(name, ast)
        return []

    def get_variables(self, name, local = False):
        if name in self.variablesByName:
            return self.variablesByName[name]
        if name.startswith('this.'):
            return []
        if self.parent:
            return self.parent.get_variables(name, local)
        return []

    def get_variables_and_functions(self, name, ast, local = False):
        l = []
        if name in self.variablesByName:
            l.extend(self.variablesByName[name])
        if name in self.functionsByName:
            l.extend(self.functionsByName[name])
        if l:
            return l

        if name.startswith('this.'):
            return []
        
        if l:
            return l
        
        if self.parent:
            return self.parent.get_variables_and_functions(name, ast, local)
        return []
    
    def __repr__(self):
        return 'ObjectValueContext (' + str(self.name) + ') ' + str(self.statement)
        
def is_new_expression(element):
    try:
        return element.is_new_expression()
    except:
        return False
        
def is_return_new_statement(element):
    try:
        return element.is_return_new_statement()
    except:
        return False
        
def is_identifier(element):
    try:
        return element.is_identifier()
    except:
        return False
        
def is_class(element):
    try:
        return element.is_class()
    except:
        return False
    
def is_method(element):
    try:
        return element.is_method()
    except:
        return False
    
def is_function(element):
    try:
        return element.is_function()
    except:
        return False
    
def is_js_content(element):
    try:
        return element.is_js_content()
    except:
        return False
    
def is_assignment(element):
    try:
        return element.is_assignment()
    except:
        return False
    
def is_object_destructuration(element):
    try:
        return element.is_object_destructuration()
    except:
        return False
    
def is_var(element):
    try:
        return element.is_var()
    except:
        return False
    
def is_string(element):
    try:
        return element.is_string()
    except:
        return False
    
def is_jsx_expression(element):
    try:
        return element.is_jsx_expression()
    except:
        return False
    
def is_top_function(element):
    try:
        return element.is_top_function()
    except:
        return False

def is_object_value(element):
    try:
        return element.is_object_value()
    except:
        return False
    
def is_block(element):
    try:
        return element.is_block()
    except:
        return False

def is_var_declaration(element):
    try:
        return element.is_var_declaration()
    except:
        return False

def is_function_call(element):
    try:
        return element.is_function_call()
    except:
        return False

def is_bracketed_identifier(element):
    try:
        return element.is_bracketed_identifier()
    except:
        return False

def is_function_call_part(element):
    try:
        return element.is_function_call_part()
    except:
        return False

def is_import_statement(element):
    try:
        return element.is_import_statement()
    except:
        return False

def is_html_content(element):
    try:
        return element.is_html_content()
    except:
        return False
