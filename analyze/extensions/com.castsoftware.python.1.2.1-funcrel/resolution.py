'''
Resolution for python.


General notes
-------------

there is one scope 
- per class
- per function

the scope of a function is not a sub scope of the class !!
the scope of a inner class  is not a sub scope of the class !!
there is no scope per block
an inner function's scope has the parent function scope as parent  


==> so it is pretty simple  

          PackageScope
               |
         ModuleScope (File)
                         \
ClassScope               FunctionScope
                              |
                         FunctionScope

'''
from collections import defaultdict, OrderedDict
from light_parser import Walker
from symbols import Class, Function, Module
from python_parser import is_identifier, is_dot_access, is_assignement,\
    is_method_call, is_function
from cast.analysers import log
import traceback



def resolve_globals(symbol, library, module=None, context=None, modules_in_resolution=set()):
    """
    Perform resolution of globals elements : imports and inheritance
    
    :param modules_in_resolution: list of modules currently in resolution 
    :param context: Context a resolution context
    :param module: module in current resolution
    """

    # top level
    if not module or module == symbol:
        module = symbol
    
        # avoid infinite loop at top level
        if module in modules_in_resolution:
            return
        modules_in_resolution.add(module)
        
        log.info('resolving ' + str(module.get_path()))

        # avoid resolving twice (saturation)
        if module.has_imports_resolved():
            return 
        module.set_imports_resolved()

    
    if not context:
        # top level context
        context = Context(symbol)
    else:
        # sub context (only for functions)
        if symbol.metamodel_type == Function.metamodel_type:
            context = Context(symbol, parent=context)
    
    
    # first resolve imports and feed resolution context    
    for _import in symbol.get_imports():
        
        try:
            for reference in _import.get_module_references():
            
                import_name = reference.get_name()
                
                if import_name[0] != '.':
                    # absolute import
                    reference._resolutions = library.get_modules_per_absolute_import(import_name, module)
                else:
                    # relative 
                    reference._resolutions = library.get_modules_per_relative_import(import_name, module)
                
                # recurse and saturate : will do weird things on recursive imports...
                # maybe we need to do module level first, then deep...
                for imported_module in reference._resolutions:
                    resolve_globals(imported_module, library, imported_module, None, modules_in_resolution)
            
            # from ... import .., .., ..
            for method_or_class_reference in _import.get_imported_elements():
                
                name = method_or_class_reference.get_name()
                
                # each imported element is resolved in all possibilities
                for imported_module in reference._resolutions:
                    
                    if name == '*':
                        method_or_class_reference._resolutions += imported_module.get_all_symbols()
                        
                    else:
                        # search first as local symbols
                        method_or_class_reference._resolutions += imported_module.find_local_symbols(name)
                        
                        if not method_or_class_reference._resolutions:
                            
                            # search as module 
                            # e.g., from package import module
                            method_or_class_reference._resolutions = library.get_modules_per_absolute_import(import_name + '.' + name, module)
                        
            context.use_import(_import)
            
        except:
            log.debug(str(_import))
            log.debug('Issue during %s : %s' %(module.get_path(), traceback.format_exc()))
        
    # resolve class inheritances
    try:
        for class_reference in symbol.get_inheritance():
            class_reference._resolutions = context.resolve_class(class_reference.get_name(), symbol)

    except:
        # not a class
        pass
        
    # recurse in sub symbols
    for child in symbol.get_all_symbols():
        
        resolve_globals(child, library, module, context, modules_in_resolution)
    


def resolve(module, library):
    """
    Resolve the content of a file (a module or package)
    
    :param module: Package or Module
    :param library: Library
    """

    # force full parsing
    if not module.get_ast():
        module.fully_parse()
    
    # walk the forest
    walker = Walker()
    
    interpreter = ResolutionInterpreter(module, library)
    
    walker.register_interpreter(interpreter)
    walker.walk(module.get_ast())
    
    interpreter.finish()    
    
class ResolutionInterpreter:
    """
    Resolve the ast of a module.
    """
    
    def __init__(self, module, library):
        """
        :param module: symbols.Module
        :param library: symbols.Library
        """
        self.__library = library
    
        # stack of context
        self.__context_stack = []
        
        context = Context(symbol=module)
        # first context : module level
        self.push_context(context)
        
        # stack of symbols
        self.__symbol_stack = [module]
        
        self.__inference = TypeInference()
        
        # make builtins resolvable
        builtins = library.get_external_modules()[0]
        for name, symbol in builtins.symbols.items():
            symbol = symbol[0]
            context.add_imported_symbol(name, symbol)
    
    def finish(self):
        self.__inference.infer()
    
    def push_context(self, context):
        """
        Add a new context to the stack.
        
        @type context: Context
        """
        for _import in context.get_symbol().get_imports():
            context.use_import(_import)
        
        self.__context_stack.append(context)
        
    def pop_context(self):
        
        self.__context_stack.pop()
        
    def get_current_context(self):
        """
        @rtype: Context
        """
        return self.__context_stack[-1]
    
    def push_symbol(self, symbol):
        
        return self.__symbol_stack.append(symbol)
    
    def pop_symbol(self):

        self.__symbol_stack.pop()
    
    def get_current_symbol(self):
        """
        @rtype: symbols.Symbol
        """
        return self.__symbol_stack[-1]
    
    def get_current_class(self):
        """
        @rtype : symbols.Class
        """
        
        symbol = self.get_current_symbol()
        """
        @type symbol: symbols.Symbol
        """
        while symbol and not isinstance(symbol, Class):         
            symbol = symbol.get_parent_symbol()
            
        
        return symbol
        
        
    
    def get_current_module(self):
        """
        @type: Module
        """
        return self.__symbol_stack[0]
                
    def start_ClassBlock(self, _ast_class):
        """
        
        """
        _class = self.get_current_symbol().get_class(_ast_class.get_name(), _ast_class.get_begin_line())
        if not _class:
            
            log.warning("no class found for %s under %s" % (str(_ast_class.get_name()), str(self.get_current_symbol())))
        
        _class._ast = _ast_class

        self.push_symbol(_class)
        
        # class do not constitute a context

    def end_ClassBlock(self, _ast_class):
        self.pop_symbol()

    def start_FunctionBlock(self, ast_function):
        self.start_Function(ast_function)

    def start_FunctionOneLine(self, ast_function):
        self.start_Function(ast_function)
        
    def start_Function(self, ast_function):
        """
        @type ast_function: python_parser.Function
        """
        name = ast_function.get_name()
        
        function = self.get_current_symbol().get_function(name, ast_function.get_begin_line())
        
        if not function:
            
            log.warning("no function found for %s under %s" % (str(name), str(self.get_current_symbol())))
        
        function._ast = ast_function
        self.push_symbol(function)
        
        # functions are a local context 
        self.push_context(Context(symbol=function, parent=self.get_current_context()))
        
        # declare formal parameters of function as local variables
        for parameter in ast_function.get_parameters():
            
            identifier = parameter
            
            if is_assignement(parameter):
                identifier = parameter.get_left_expression()
            
#             try:
#                 identifier.get_name()
#             except:
#                 print(ast_function.get_begin_line())
            
            self.get_current_context().declare_variable(identifier.get_name(), identifier)
            self.__inference.add_variable(identifier)

    def end_FunctionBlock(self, ast_function):
        self.end_Function(ast_function)
        

    def end_FunctionOneLine(self, ast_function):
        self.end_Function(ast_function)
        
    def end_Function(self, ast_function):
        self.pop_context()
        self.pop_symbol()
    
    def start_MethodCall(self, ast):
        """
        Resolution of a method call
        
        @type ast: python_parser.MethodCall
        
        
        @todo : performance issues...
        """
        
        def get_fullname(expression):
            """
            In case of DotAccess only or identifier, return the dotted name
            Returns None else
            """
            if is_dot_access(expression):
                
                left_name = get_fullname(expression.get_expression())
                if left_name:
                    return left_name + '.' + expression.get_name()
            elif is_identifier(expression):
                return expression.get_name()
            
            return None

#         log.debug('start_MethodCall ' + str(ast))
        self.__inference.add_method_call(ast)
        
        context = self.get_current_context()
        
        method_expression = ast.get_method()
        method_name = None

        # special case : self.m inside a class
        if is_dot_access(method_expression):
            
            method_name = method_expression.get_name()
            
            left_expression = method_expression.get_expression()
            if is_identifier(left_expression):
                if left_expression.get_name() == 'self':
                
                    _class = self.get_current_class()
                    if _class:
                        ast._resolutions = _class.find_method(method_name)
                        return 
        
        try:
            # a.b.c.m()
            import_name = get_fullname(method_expression)
            if import_name:
                
                result = context.resolve(import_name, kinds=[Class, Function])
#                 log.debug('start_MethodCall after resolution')
                
                if result:
                    
                    for element in result:
                        
                        # either a class or a method
                        if element.is_function():
                            ast._resolutions.append(element)
                        elif element.is_class():
                            method_expression._resolutions.append(element)
                            init = element.find_local_symbols('__init__')
                            if init:
                                ast._resolutions += init
                    return
                elif method_name == '__init__':
                    # unresolved : do not try to link to all planet
                    return
            
            # local variable...
            if is_identifier(method_expression) and context.resolve_variable(method_expression.get_name()):
                return
                
                
            
            # get left most identifier    
            temp = method_expression
            while is_dot_access(temp):
                
                temp = temp.get_expression()
            
            if is_identifier(temp):
                
                # search it as import name...
                resolved_as_import = context.resolve_as_import(temp.get_name())
                if resolved_as_import and not resolved_as_import.get_resolutions():
                    # an unresolved import
                    # HEURISTIC : 
                    # os.path.f() ... is more frequently a function from an unknown module than 
                    # 'path' being a variable from module os called with method f
                    # we had too many false links due to some submodules mixed up with methods call
                    return

            # map name -> methods
            methods = self.__library.get_method_by_name(method_name)
            intersection = []
            
            # filter by accessibility
            for method in methods:
                if context.is_accessible(method.get_parent_symbol()):
                    intersection.append(method)
            
            ast._resolutions = intersection

        except:
            print(traceback.format_exc())
            # no method name, for example self.filters[mode](conf) : nothing we can do now
            pass
#         log.debug('start_MethodCall end')
            
    def end_MethodCall(self, ast):
        
        # link back from called method to method call
        for resolution in ast.get_resolutions():
            
            if resolution.get_ast():
                
#                 print(id(resolution.get_ast()))
#                 print(resolution.get_ast())
            
                try:
                    resolution.get_ast().add_caller(ast)
                except:
                    # should not happen as it called should be a function
                    log.debug('issue in end_MethodCall for token %s' % str(ast))

    def start_Identifier(self, ast):
        """
        @type ast: Identifier
        """
        if not ast._resolutions:
            resolution = self.get_current_context().resolve_variable(ast.get_name())
            if resolution:
                ast._resolutions.append(resolution)
            # here we handle edge case where ....
            else:
                context = self.get_current_context()
                res = context.resolve(ast.get_name(), kinds=[Class])
                if not res:
                    ast._resolutions = [None]
                else:
                    for element in res:
                        if element.is_class():
                            ast._resolutions.append(element)

    def start_Assignement(self, ast):
        """
        @type ast: Assignement
        """
        self.__inference.add_assignement(ast)

        identifier = ast.get_left_expression()
        
        try:
            self.get_current_context().declare_variable(identifier.get_name(), identifier)
            self.__inference.add_variable(identifier)
            
            function = self.get_current_symbol()
            
            if function.get_name() == '__init__' and is_dot_access(identifier):
                
                _self = identifier.get_expression()
                if is_identifier(_self) and _self.get_name() == 'self':
                    
                    _class = function.get_parent_symbol()
                    if _class and isinstance(_class, Class):
                        
                        _class.declare_member(identifier.get_name(), identifier)
        except:
            # for example (..., ...) = ...
            pass
        
#     def end_Assignement(self, ast):
#         
#         identifier = ast.get_left_expression()
#         call = ast.get_right_expression()
#         if not is_method_call(call):
#             return
#         # @type call: python_parser.MethodCall
#         try:
#             for _class in call.get_method().get_resolutions():
#                 if _class:
#                     self.get_current_context().add_constructor_assignement(identifier, _class)
#         except:
#             pass
#         
#         pass
        
        
    def start_DotAccess(self, ast):
        
        function = self.get_current_symbol()
        if not function:
            return
        _self = ast.get_expression()
        if not is_identifier(_self) or _self.get_name() != 'self':
            return
        
        if not isinstance(function, Function):
            return
                
        _class = function.get_parent_symbol()
        if not _class or not isinstance(_class, Class):
            return
        
        ast._resolutions = _class.find_member(ast.get_name())

    def start_WithBlock(self, ast):
        self.start_With(ast)

    def start_WithOneLine(self, ast):
        self.start_With(ast)
        
    def start_With(self, ast):
        """
        @type ast: With
        """
        identifier = ast.get_identifier()
        """
        @todo handle (identifier1, identifier2) e.g.,  

            with f() as (v1, v2):
                pass
        """
        
        if identifier and is_identifier(identifier): # identifier is optional in a with
            self.get_current_context().declare_variable(identifier.get_name(), identifier)

    def start_ForBlock(self, ast):
        self.start_For(ast)

    def start_ForOneLine(self, ast):
        self.start_For(ast)
    
    def start_ComprehensionLoop(self, ast):
        
        # not really true because comprehension for loop creates a new resolution context (...) 
        self.start_For(ast.get_comprehension_for())
    
    def start_For(self, ast):
        
        for identifier in ast.get_identifiers():
            self.get_current_context().declare_variable(identifier.get_name(), identifier)
    

class Context:
    """
    Base class for python interpreter context

    Resolution is done by escalating contexts. 
    As soon as a resolution is found at a context level, the resolution is supposed to be finished.
    """
    def __init__(self, symbol, parent=None):
        """
        :param parent: parent context
        @type parent: Context
        """
        self.__current_symbol = symbol
        
        # parent context
        self.__parent = parent
        
        # imported modules by fullname
        self.__modules_by_fullname = OrderedDict()
    
        # imported symbols by name (class or method or modules)
        self.__symbols_by_name = OrderedDict()
    
        # local variables
        self.__local_variables = {}

        # identifier for imported elements by name
        self.__imports_by_name = OrderedDict()
        
        self.__all_accessible_classes = []
    
    def get_symbol(self):
        return self.__current_symbol

    def use_import(self, _import):
        """
        Use a resolved import
        
        An import declare locally some names. 
        """
        for reference in _import.get_module_references():
        
            import_name = reference.get_name()
        
            if reference.get_alias():
                import_name = reference.get_alias()
        
            if not _import.get_imported_elements():
                
                # simple import a.b
                # import all symbols of module
                
                self.__imports_by_name[import_name] = reference
                
                for module in reference._resolutions:
                    
                    for name, symbols in module.get_local_symbols().items():
                        
                        for symbol in symbols:
                            # define a.b.C, a.b.D, etc...
                            self.add_imported_symbol(import_name + '.' + name, symbol)
    
                    for name, symbols in module.get_imported_symbols().items():
                        
                        for symbol in symbols:
                            # define a.b.C, a.b.D, etc...
                            self.add_imported_symbol(import_name + '.' + name, symbol)
                        
            else:
                # from ... import .., .., ..
                for method_or_class_reference in _import.get_imported_elements():
                    
                    name = method_or_class_reference.get_name()
                    
                    # each imported element is already resolved to all possibilities
                
                    # if element is imported as an alias it became its local name
                    if method_or_class_reference.get_alias():
                        name = method_or_class_reference.get_alias()
                        
                    self.__imports_by_name[name] = method_or_class_reference
                    
                    # register it 
                    for symbol in method_or_class_reference._resolutions:
                        
                        if name != '*':
                            self.add_imported_symbol(name, symbol)
                        else:
                            self.add_imported_symbol(symbol.get_name(), symbol)
                    
                    if name == '*':
                        for module in reference._resolutions:
                            
                            for name, symbols in module.get_imported_symbols().items():
                                
                                for symbol in symbols:
                                    # define C, D, etc...
                                    self.add_imported_symbol(name, symbol)
                        
        
    
    def add_imported_module(self, fullname, module):
        
        if fullname not in self.__modules_by_fullname:
            self.__modules_by_fullname[fullname] = []
        self.__modules_by_fullname[fullname].append(module)

    def add_imported_symbol(self, fullname, symbol):
        
        if fullname not in self.__symbols_by_name:
            self.__symbols_by_name[fullname] = []
        self.__symbols_by_name[fullname].append(symbol)
    
    
    def resolve(self, name, kinds=[], originating_symbol=None):
        """
        Resolve a name as a symbol of a type in @param kinds.
        
        :param name: str, named searched, can be qualified
        :param kinds: list of type, the searched types for symbols for example [Class], [Class, Function] etc...
        :param originating_symbol: symbol from whom the query is originating, used for class A(A): resolution... 
        
        """
        # search locally first
        
        # name can be qualified
        qname = name.split('.')
        if len(qname) == 1:
            current_symbols = [self.__current_symbol]
        else:
            # split names and search them 
            current_symbols = [self.__current_symbol]
            # @type current_symbols: list(symbols.Class)
            
            # local variable ... no need to go further 
            # @todo we could track local assignment of variables and do something... 
            if self.resolve_variable(qname[0]):
                return []
            
            for local_name in qname[:-1]:
                
                next_symbols = []
                
                for current_symbol in current_symbols:
                    
                    next_symbols += current_symbol.find_local_symbols(local_name, [Class, Module])
                        
                current_symbols = next_symbols
                if not current_symbols:
                    break

        if current_symbols:
                
            results = []
            
            for current_symbol in current_symbols:
                
                if Function in kinds and current_symbol.is_class(): 
                    temp_results = current_symbol.find_method(qname[-1])
                    if temp_results:
                        results += temp_results
                    
                results += current_symbol.find_local_symbols(qname[-1], kinds)

            # for class A(A): ...
            if originating_symbol in results:
                
                results.remove(originating_symbol)
                
            if results:
                
                return results
            
        # search in imported symbols 
        # @todo : may return unexpected types...
        if name in self.__symbols_by_name:
            kind_names = [kind.metamodel_type for kind in kinds]
            by_name = [symbol for symbol in self.__symbols_by_name[name] if symbol.metamodel_type in kind_names]
            if by_name:
                return by_name
        
        # search in parent context
        if self.__parent:
            return self.__parent.resolve(name, kinds, originating_symbol)
        
        return []
    
    def resolve_class(self, class_name, originating_class=None):
        """
        Resolve a class.
        
        @rtype: list of Class
        """
        return self.resolve(class_name, [Class], originating_class)
        
    def resolve_function(self, function_name):
        """
        Resolve a function.

        @rtype: list of Function
        """
        as_function = self.resolve(function_name, [Function])
        if as_function:
            return as_function
        
        result = []
        # search as a constructor
        for _class in self.resolve(function_name, [Class], self.__current_symbol):
            
            result += _class.find_local_symbols('__init__', [Function])
        
        return result
    
    def is_accessible(self, _class):
        
        if _class in self.get_all_accessible_classes():
            return True
        
        # recurse
        if self.__parent:
            return self.__parent.is_accessible(_class)
        
        return False
    
    def get_all_accessible_classes(self):
        """
        Return all accessible classes.
        """
        if not self.__all_accessible_classes:
        
            def add_class(result, _class):
                """
                Add a class and all its inheritance
                """
                # @type _class:symbols.Class
                result.add(_class)
                for reference in _class.get_inheritance():
                    for parent in reference.get_resolutions():
                        if parent in result:
                            # skip buggy resolution to avoid 
                            # recursion error
                            continue
                        add_class(result, parent)

                
            result = set()
        
            # all classes defined in Module
            if type(self.__current_symbol) == Module:
                
                # @todo recode ...
                for _, symbols in self.__current_symbol.get_local_symbols().items():
                    
                    for _class in symbols:
                        if type(_class) == Class:
                            add_class(result, _class)
                            
                        
            
            # imported classes
            for symbols in self.__symbols_by_name.values():

                for _class in symbols:
                    if type(_class) == Class:
                        add_class(result, _class)
            
            # caching
            self.__all_accessible_classes = result
        
        return self.__all_accessible_classes
    
    def declare_variable(self, name, identifier):
        """
        Declare a local variable
        
        if already declared, do not redeclare it.
        """
        if not name in self.__local_variables:
            self.__local_variables[name] = identifier
        
    def resolve_variable(self, name):
        
        try:
            return self.__local_variables[name]
        except:
            
            if self.__parent:
                
                return self.__parent.resolve_variable(name)
            return None
        

    def resolve_as_import(self, name):
        
        if name in self.__imports_by_name:
            return self.__imports_by_name[name]
        
        if self.__parent:
            return self.__parent.resolve_as_import(name)

        return None


class TypeInference:
    """
    Attempt of a type inference
    """
    

    
    def __init__(self):
        
        self.variables = set()
        self.assignements = []
        self.calls = []
        
        # deduced types for a variable
        self.variables_types = defaultdict(set)
        
    def infer(self):
        """
        Pseudo type inference.
        
        freely inspired from http://ftp.python.org/workshops/2000-01/proceedings/papers/aycock/aycock.html
        
        """
        assignements = set()

        
        # assignements and dot expressions defines pseudo variables
        for assignement in self.assignements:
            # @type assignement: python_parser.Assignement
        
            left = Expression(assignement.get_left_expression())
            if left.variable and left.rest:
                
                self.variables.add(left)
                
                # this is an interesting assignement
                assignements.add(assignement)
                
            right = Expression(assignement.get_right_expression())
            if right.variable and right.rest:
                
                self.variables.add(right)
        
        # connect variables by alias
        groups = AliasGroups(self.variables)
        
        aliasings = set()
        
        # assignements connects variable together
        for assignement in self.assignements:
            # @type assignement: python_parser.Assignement
            
            left = Expression(assignement.get_left_expression())
            if not left.variable:
                continue
            
            right = Expression(assignement.get_right_expression())
            if not right.variable:
                continue
            
            groups.connect(left, right)
            aliasings.add(assignement)
        
        # we have seen the aliases
        assignements = assignements - aliasings
        
        constructor_assignements = set()
        
        # assignements of constructor calls give sure types
        for assignement in self.assignements:
            # @type assignement: python_parser.Assignement
            
            expression = Expression(assignement.get_left_expression())
            if not expression.variable:
                continue

            group = groups.find_group(expression)
            if not group:
                continue
            
            call = assignement.get_right_expression()
            
            try:
                obj = call.get_resolutions()[0]
                if obj.return_type:
                    group.add_sure_type(obj.return_type)
                    constructor_assignements.add(assignement)
                    continue
            except AttributeError:
                pass
            except IndexError:
                pass
            
            if not is_method_call(call):
                continue
            # @type call: python_parser.MethodCall
            
            try:
                for _class in call.get_method().get_resolutions():
                    if _class:
                        group.add_sure_type(_class)
                        
                        constructor_assignements.add(assignement)
            except:
                pass
            
        # what left...    
        assignements = assignements - constructor_assignements
        
        for assignement in assignements:
            # @type assignement: python_parser.Assignement
            
            expression = Expression(assignement.get_left_expression())
            if not expression.variable:
                continue

            group = groups.find_group(expression)
            if not group:
                continue
            
            # neither an alias nor a constructor assignement ...
            group.set_as_not_sure()
        # 
        for call in self.calls:
            # @type call: python_parser.MethodCall
            
            method = call.get_method()
            if not is_dot_access(method):
                continue
            
            # @type method: python_parser.DotAccess
            expression = Expression(method.get_expression())
            
            if not expression.variable:
                continue
            
            group = groups.find_group(expression)
            if not group:
                continue

            # we are calling a method x on group 
            ################
            # @todo : ???
            ################

            group.add_called_method_name(method.get_name())
            group.add_call(call)
            
            for function in call.get_resolutions():
                # @type function: symbols.Function
                
                _class = function.get_parent_symbol()
                if isinstance(_class, Class):
                    group.add_possible_type(_class)

        # debugging        
        for group in groups.groups:
            # @type group: AliasGroup
            
            
#             print('AliasGroup')
#             for variable in group.variables:
#                 print('   ', variable)
#             print('  Possibles')
#             for _type in group.possible_types:
#                 print('   ', _type.get_qualified_name())
#               
#             print('  Methods')
#             for method in group.called_method_names:
#                 print('   ', method)
#   
#             print('  Sures')
#             for _type in group.sure_types:
#                 print('   ', _type.get_qualified_name())
#               
#             print('  Contains parameter ?', group.contains_parameter())
#   
#             print('  Calls')
#             for call in group.calls:
#                 print('   ', call)
            
            
            if group.contains_self():
                pass
            elif group.is_sure() and group.sure_types:
                # we do not have assignement from a parameter and we have found sure types
                # ==> reset all calls with sure types only
                apply_types_to_calls(group.calls, group.sure_types)
                
            else:
                
                apply_types_to_calls(group.calls, group.get_possible_types())
                

    def is_variable(self, expression):
        
        return expression in self.variables

    def add_variable(self, variable):
        """
        A variable definition...
        """
        if is_identifier(variable):
            self.variables.add(Expression(variable))
        
    def add_assignement(self, assignement):
        """
        @type assignement: python_parser.Assignement
        """
        self.assignements.append(assignement)
        
    def add_method_call(self, call):
        
        self.calls.append(call)
    

def apply_types_to_calls(calls, types):
    """
    Restricts the call resolution to a set of types deduced for the expression.
    """
    for call in calls:
        resolutions = []
        for method in call.get_resolutions():
            for _class in types:
                try:
                    if _class.is_callable(method):
                        resolutions.append(method)
                except:
                    # happens when we have variable of type 'class'
                    # var = MyClass
                    # x = var() 
                    pass
        
        # handling of "inverse link" of _resolutions
        # used by evaluation
        # remove old ones
        for resolution in call._resolutions:
             
            if resolution.get_ast():
                 
                try:
                    resolution.get_ast().remove_caller(call)
                except:
                    # should not happen as it called should be a function
                    log.debug('Issue in end_MethodCall for token %s' % str(call))
         
        # add new ones
        call._resolutions = resolutions
 
        for resolution in call.get_resolutions():
             
            if resolution.get_ast():
                 
                try:
                    resolution.get_ast().add_caller(call)
                except:
                    # should not happen as it called should be a function
                    log.debug('Issue in end_MethodCall for token %s' % str(call))
    

def extract_variable_and_rest(node):
    """
    For a complex expression e.g., 
    - v.a.b ==> v, '.a.b'
    
    """
    if is_identifier(node):
        if node.get_resolutions():
        
            return node.get_resolutions()[0], ''
        
        else:
            return node, ''
        
    if is_dot_access(node):
        
        var, rest = extract_variable_and_rest(node.get_expression())
        if not rest:
            return None, None
        rest += '.' + node.get_name()
        
        return var, rest
    
    return None, None
        

class Expression:
    
    def __init__(self, node):
        
        self.node = node
        
        self.variable, self.rest = extract_variable_and_rest(node)
        
    def __eq__(self, expression):    
        
        try:
            return self.variable == expression.variable and self.rest == expression.rest
        except:
            return False 
    
    
    def __hash__(self):
        
        return hash((self.variable, self.rest))
        
    def __repr__(self):
        
        return 'Expression ' + str(self.variable) + ' ' + str(self.rest)
    

def is_formal_parameter(node):
    """
    True when node is a parameter of a method
    @todo : decide for parameter that can be either Identifier or Assignement
    """
    statement = node.get_enclosing_statement()
    
    if not is_function(statement):
        return False
    
    # @type statement:  python_parser.Function
    for parameter in statement.get_parameters():
        
        if parameter == node:
            return True
        
        if is_assignement(parameter) and node == parameter.get_left_expression():
            return True
    
    return False

    
class AliasGroup:
    """
    A group of variables.
    """
    def __init__(self):
        self.variables = []
        self.possible_types = set()
        self.called_method_names = set()
        self.sure_types = set()
        self.calls = []
        self.sure = True
        
    def add_sure_type(self, _type):
        """
        Say that _type is a sure type
        
        :type _type: symbols.Class
        
        """
        self.sure_types.add(_type)
        
    def add_possible_type(self, _type):
        """
        Say that _type is a possible type
        """
        self.possible_types.add(_type)
    
    def add_called_method_name(self, name):
        self.called_method_names.add(name)
    
    def add_call(self, call):
        self.calls.append(call)

    def is_sure(self):
        """
        True when assigned types can be considered as sure.
        
        Whenever something with unclear type is assigned to one of the expression ,then it is unsure.
        
        """
        if not self.sure:
            return False
        
        # by essence, parameters have unknown type
        if self.contains_parameter():
            return False
        
        return True
    
    def set_as_not_sure(self):
        
        self.sure = False
    
    def contains_parameter(self):
        """
        Return true when this group contains a formal parameter
        """
        for expression in self.variables:
            # @type expression: Expression
            if is_formal_parameter(expression.variable):
                return True
            
        return False

    def contains_self(self):
        """
        Return true when this group contains a formal parameter
        """
        for expression in self.variables:
            # @type expression: Expression
            if expression.variable.get_name() == 'self':
                return True
            
        return False
    
    def get_possible_types(self):
        """
        Get all the possible types
        
        Heuristic - restrict by keeping only types that contains all methods called on variables
        """
        result = []
        for _type in self.possible_types:
            # @type _type: symbols.Class
            ok = True
            
            for method_name in self.called_method_names:
                if not _type.get_function(method_name):
                    ok = False
                    break
            
            if ok:
                result.append(_type)
        
        return result
    
    def contains(self, variable):
        return variable in self.variables
        
    @staticmethod
    def create(variable):
        result = AliasGroup()
        result.variables = [variable]
        return result

    @staticmethod
    def merge(group1, group2):
        result = AliasGroup()
        result.variables = group1.variables + group2.variables
        return result
        
        
class AliasGroups:
    
    def __init__(self, variables):
        self.groups = []
        for variable in variables:
            self.groups.append(AliasGroup.create(variable))

    def find_group(self, variable):
        result = None
        for group in self.groups:
            if group.contains(variable):
                result = group
                break
        return result

    def connect(self, tr1, tr2):

        # find groups
        # remove them
            
        group1 = self.find_group(tr1)
        group2 = self.find_group(tr2)
        
        if group1 and group2 and group1 != group2:
            self.groups.remove(group1)
            self.groups.remove(group2)
            # replace by merged
            self.groups.append(AliasGroup.merge(group1, group2))
    
    
        
        
