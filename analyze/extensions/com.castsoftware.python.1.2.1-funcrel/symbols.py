import cast_upgrade_1_5_23 # @UnresolvedImport @UnusedImport
from collections import defaultdict, OrderedDict
import os
from pygments.token import is_token_subtype, Literal, Name, Comment, Token as PygmentToken
from python_parser import parse, light_parse, IndentBlock, is_function, is_import, is_constant, \
        PythonSimpleStatement, is_if_then_else, is_binary_operation, is_identifier, is_class,\
    is_dot_access, BadIndentation, LineFeed, StartLine, DocString, IncreaseIndent
from light_parser import Node, Walker, Token, TokenIterator
from discoverer import Discoverer
from cast.analysers import CustomObject, Bookmark, log, create_link, get_cast_version
from cast.application import open_source_file # @UnresolvedImport
import re
from distutils.version import StrictVersion


class Namespace:
    """
    Dictionary of symbols
    """
    def __init__(self):

        # defined symbols
        self.symbols = OrderedDict()

    def add_symbol(self, name, symbol):
        """
        Register a symbol
        """
        try:
            self.symbols[name].append(symbol)
        except:
            self.symbols[name] = [symbol]

    def get_local_symbols(self):
        """
        Access to all symbols as a dict(list)
        """
        return self.symbols

    def get_all_symbols(self):
        """
        Access to all symbols as a list
        """
        import itertools
        return list(itertools.chain.from_iterable(self.symbols.values()))

    def find_local_symbols(self, name, types=[]):
        """
        Search for a symbol of a given name with optional possible types
        """
        if not name:
            return []
        
        type_names = [_type.metamodel_type for _type in types]
        
        if name in self.symbols:
            symbols = self.symbols[name]
            if types:
                return [symbol for symbol in symbols if symbol.metamodel_type in type_names]
            else:
                return symbols
        else:
            return []

    def print(self, ident=0):
        """
        Pretty print.
        """
        result = ' '*ident + '%s %s\n' % (type(self).__name__, self.get_name())
        for symbols in self.symbols.values():
            for symbol in symbols:
                result += symbol.print(ident + 1)
                
        
        return result



class Library:
    """
    A collection of Package and Module. 
    The 'source code' of the analysis. 
    Each python file is there.   
    """
    
    def __init__(self):
        
        self.__modules = []
        self.__external_modules = []
        
        self.__resolved = False
        # root path, import path discoverer
        self.__discoverer = Discoverer()
        
        self.__module_per_name = OrderedDict()
        self.__module_per_path = {}
        
        # map of methods by name 
        self.__methods = OrderedDict()
        
        self.declare_builtins()
        self.declare_system()
        
        # statistics        
        #   client
        self.nbRequestsServices = 0
        self.nbHttplibServices = 0
        self.nbHttplib2Services = 0
        self.nAiohttpServices = 0
        self.nUrllibServices = 0
        self.nUrllib2Services = 0
        
        #   server
        self.nbFlaskServerOperations = 0
        self.nbAiohttpServerOperations = 0
        
        #   query
        self.nbSqlQueries = 0
        
        #   Messaging queues
        self.nbActiveMQ_queue_objects = 0
        self.nbRabbitMQ_queue_objects = 0
        self.nbIBMMQ_queue_objects = 0

        # specific PYTHON-129 DIAG-3797 :  violation candidates
        self.violation_candidates = []
        self.adding_violation_candidates = True
    
    def save_std_library(self):
        
        file = self.__modules[-1].get_file()  # beware first modules defined by declare_system(), so no file. Take last added.
        
        std_lib = CustomObject()
        std_lib.set_name('Standard library')
        std_lib.set_type('CAST_Python_External_Library')
        std_lib.set_fullname('standardLibrary')
        std_lib.set_guid('standardLibrary')
        std_lib.set_external()
        std_lib.set_parent(file)
        std_lib.save()
        
        create_link('parentLink', std_lib, file.get_project())

        blt = CustomObject()
        blt.set_name('builtins.py')
        blt.set_type('CAST_Python_SourceCode')
        blt.set_fullname('builtins')
        blt.set_guid('standardLibrary.builtins')
        blt.set_external()
        blt.set_parent(std_lib)
        blt.save()
        
        create_link('parentLink', blt, std_lib)
        
        builtin = self.__external_modules[0]
        builtin._Symbol__kb_symbol = blt
        
        def save_sub_symbols(symbol, custom_object):
            for fname, flist in symbol.symbols.items():
                
                function = flist[0]
                func = CustomObject()
                func.set_name(fname)
                
                if isinstance(function, Function):
                    _type = 'CAST_Python_Method'
                elif isinstance(function, Class):
                    _type = 'CAST_Python_Class'
                else:
                    log.debug("Error saving standard library")
                    return
                
                func.set_type(_type)
                
                func.set_fullname('builtins.'+fname)
                func.set_guid('standardLibrary.builtins.'+fname)
                func.set_external()
                func.set_parent(custom_object)
                func.save()
                
                create_link('parentLink', func, custom_object)
                
                function._Symbol__kb_symbol = func
                
                if _type == 'CAST_Python_Class':
                    save_sub_symbols(function, func)
        
        save_sub_symbols(builtin, blt)
        log.info("Saved standard library objects")
    
    
    def declare_builtins(self):
        module = Module('builtins.py')
        module._import_name = 'builtins'
        
        self.add_external_module(module)
        
        # 'file' belongs to Python2 but not for Python3
        # In Python3 -> _io.TextIOWrapper object
        _class = Class('file', module)
        module.add_symbol('file', _class)
        _class.add_symbol('read', Function('read', _class))
        _class.add_symbol('readline', Function('readline', _class))
        _class.add_symbol('readlines', Function('readlines', _class))
        _class.add_symbol('write', Function('write', _class))
        _class.add_symbol('writelines', Function('writelines', _class))
        _class.add_symbol('close', Function('close', _class))
        
        module.add_symbol('open', Function('open', module, return_type = _class))
    
    
    def declare_system(self):
        """
        Create a minimal set of libraries, classes and methods for http.
        """
        module = Module('requests.py')
        self.add_module(module)
        
        _class = Class('Session', module)
        module.add_symbol('Session', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        _class.add_symbol('get', Function('get', _class))
        _class.add_symbol('put', Function('put', _class))
        _class.add_symbol('post', Function('post', _class))
        _class.add_symbol('delete', Function('delete', _class))
        
        # we add only once
        module.add_symbol('get', Function('get', module))
        module.add_symbol('post', Function('post', module))
        module.add_symbol('put', Function('put', module))
        module.add_symbol('delete', Function('delete', module))

        _class = Class('Request', module)
        module.add_symbol('Request', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        
        # synonyms
        _class = Class('session', module)
        module.add_symbol('session', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        _class.add_symbol('get', Function('get', _class))
        _class.add_symbol('put', Function('put', _class))
        _class.add_symbol('post', Function('post', _class))
        _class.add_symbol('delete', Function('delete', _class))
                
        module = Module('requests.sessions.py')
        self.add_module(module)
                
        _class = Class('Session', module)
        module.add_symbol('Session', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        _class.add_symbol('get', Function('get', _class))
        _class.add_symbol('put', Function('put', _class))
        _class.add_symbol('post', Function('post', _class))
        _class.add_symbol('delete', Function('delete', _class))
        
        _class = Class('session', module)
        module.add_symbol('session', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        _class.add_symbol('get', Function('get', _class))
        _class.add_symbol('put', Function('put', _class))
        _class.add_symbol('post', Function('post', _class))
        _class.add_symbol('delete', Function('delete', _class))

        module = Module('httplib.py')
        self.add_module(module)

        _class = Class('HTTPConnection', module)
        module.add_symbol('HTTPConnection', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        _class.add_symbol('request', Function('request', _class))

        module = Module('http.client.py')
        self.add_module(module)
        
        _class = Class('HTTPConnection', module)
        module.add_symbol('HTTPConnection', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        _class.add_symbol('request', Function('request', _class))
        
        _class = Class('HTTPSConnection', module)
        module.add_symbol('HTTPSConnection', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        _class.add_symbol('request', Function('request', _class))

        module = Module('httplib2.py')
        self.add_module(module)

        _class = Class('Http', module)
        module.add_symbol('Http', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        _class.add_symbol('request', Function('request', _class))
        
        module = Module('aiohttp.py')
        self.add_module(module)
        
        _class = Class('ClientSession', module)
        module.add_symbol('ClientSession', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        _class.add_symbol('get', Function('get', _class))
        _class.add_symbol('put', Function('put', _class))
        _class.add_symbol('post', Function('post', _class))
        _class.add_symbol('delete', Function('delete', _class))

        
        _class = Class('TCPConnector', module)
        module.add_symbol('TCPConnector', _class)
        _class.add_symbol('__init__', Function('__init__', _class))
        
        
        # urllib.request.urlopen
        module = Module('urllib/__init__.py')
        self.add_module(module)
        
        module = Module('urllib/request.py')
        self.add_module(module)
        
        module.add_symbol('urlopen', Function('urlopen', module))
        module.add_symbol('urlretrieve', Function('urlretrieve', module))
    
        _class = Class('Request', module)
        module.add_symbol('Request', _class)
        _class.add_symbol('__init__', Function('__init__', _class))

        # urllib2
        module = Module('urllib2/__init__.py')
        self.add_module(module)

        module.add_symbol('urlopen', Function('urlopen', module))

        _class = Class('Request', module)
        module.add_symbol('Request', _class)
        _class.add_symbol('__init__', Function('__init__', _class))

    def add_module(self, module):
        """
        Add a module.
        
        :param module: Module
        """
        self.__modules.append(module)
        self.__discoverer.add_path(module.get_path())
    
        module._library = self
        
    def add_external_module(self, module):
        """
        Add an external module.
        
        :param module: Module
        """
        self.__external_modules.append(module)
        #self.__discoverer.add_path(module.get_path())
        
        module._library = self
        
    def get_modules(self):
        
        return [module for module in self.__modules if module.is_analysed()] 
    
    def get_external_modules(self):

        return [module for module in self.__external_modules]

    def get_modules_per_absolute_import(self, import_name, module):
        """
        Get module from an absolute import name : a.b

        :param module: The module from which we do the import 
        @type module: Module
        """
        self.__resolve()
        
        if import_name in self.__module_per_name:
            return self.__module_per_name[import_name]
        else:
            # try in relative
            result = self.get_modules_per_relative_import(import_name, module)
            if result:
                return result
        
        # last chance search in all pathes
        result = []
        path = import_name.replace('.', '\\') + '.py'

        for candidate in self.__modules + self.__external_modules:
            
            candidate_path = candidate.get_path()
            if candidate_path.endswith(path):
                result.append(candidate)
        
        # caching for the next time...
        self.__module_per_name[import_name] = result
            
        return result

    def get_modules_per_relative_import(self, import_name, module):
        """
        Get module from a relative import :
        - .a   : module in the same folder 
        - ..a  : module in parent folder  
        - ...a : etc...

        :param module: The module from which we do the import 
        :param import_name: the imported name
        @type module: Module
        """
        self.__resolve()
        
        # build the relative path
        folder_path = module.get_path()
        if import_name and import_name[0] == '.':
            while import_name and import_name[0] == '.':
                folder_path = os.path.dirname(folder_path)
                import_name = import_name[1:]
        else:
            folder_path = os.path.dirname(folder_path)
        
        if not import_name:
            # from . import ...
            import_name = '__init__'
        path = os.path.join(folder_path, import_name.replace('.', '/')) + '.py'
        
        try:
            return [self.__module_per_path[path]]
        except:
            # @todo : probably quite costly for perfs
             
            # still not found per 'perfect' rule of import
            # we use 'fuzzy' resolution to be 'cool' 
            result = []
            
            for candidate_import_name in self.__module_per_name:
                if candidate_import_name.endswith('.' + import_name):
                    result +=  self.__module_per_name[candidate_import_name]
            
            return result

    def get_module_per_path(self, path):
        """
        Match by the end of the path
        If several result return None
        """
        path = os.path.normpath(path)
        candidates = []
        for module in self.__modules:
            
            if os.path.normpath(module.get_path()).endswith(path):
                candidates.append(module)
        
        if len(candidates) == 1:
            return candidates[0]

        return None
    
    def discover(self):
        """
        Perform discovery
        """
        self.__resolve()

    def light_parse(self):
        """
        First pass of parsing.
        """
        for module in self.get_modules():
            
            module.light_parse()

    def resolve_globals(self):
        """
        First pass of resolution
        """
        for module in self.get_modules():
            
            module.resolve_globals()
            
    def add_method(self, method):
        
        name = method.get_name()
        if name in self.__methods:
            self.__methods[name].add(method)
        else:
            self.__methods[name] = set([method])

    def get_method_by_name(self, name):
        """
        Get all method having name.
        """
        try:
            return self.__methods[name]
        except:
            return set()
        

    def __resolve(self):
        """
        Use discoverer.Discoverer to determine map the import names to the files.
        """
        # do it once only
        if self.__resolved:
            return
        
        for module in self.__modules:
            
            import_name = self.__discoverer.get_import_name(module.get_path())
            module._import_name = import_name
            
            if import_name not in self.__module_per_name:
                self.__module_per_name[import_name] = []
            self.__module_per_name[import_name].append(module)
            self.__module_per_path[module.get_path()] = module
            
        self.__resolved = True
        


class Symbol(Namespace):
    """
    base class for symbols
    """    
    def __init__(self, name, parent=None):
        Namespace.__init__(self)
        self.__name = name
        self.__parent = parent

        # for saving
        self.__kb_symbol = None
        self.subObjectsGuids = {}

        self.__start_line = None
        # constructed latter during parsing
        self._ast = None
        self.__imports = []
        self._statements = []
        
        # violations for quality rules property name --> ast's
        self.__violations = defaultdict(list)
        # idem
        self.__properties = {}
        
        # imported symbols
        self.__imported_symbols_by_name = OrderedDict()
        self.__imported_symbols_by_name_calculated = False


    def get_parent_symbol(self):
        
        return self.__parent
    
    def get_root_symbol(self):
        
        if self.__parent:
            return self.__parent.get_root_symbol()
        
        return self
    
    def get_name(self):
        """
        Return name
        """
        return self.__name
    
    def get_qualified_name(self):
        """
        Qualified name
        """
        
        if self.__parent:
            result = self.__parent.get_qualified_name() + "." + self.__name
        else:
            # module
            result = os.path.splitext(self.__name)[0]
        
        return result
    
    def get_ast(self):
        """
        Access to AST of symbol.
        """
        return self._ast
    
    def print_tree(self, depth=0):
        """
        Print as a tree.
        """
        indent = ' ' * (depth * 2)
        print(indent, self.__class__.__name__)
        
        for token in self._ast:
            token.print_tree(depth+1)

    def get_imports(self):
        """
        Return the imports of the element 
        """
        return self.__imports

    def get_statements(self):
        """
        Get the statements of the symbol.
        """
        if not self._statements:
        
            for block in self._ast.get_sub_nodes(IndentBlock):
                self._statements = list(block.get_sub_nodes())
                break
            else:
                self._statements = list(self._ast.get_sub_nodes(PythonSimpleStatement))                
                
        return self._statements
    
    def get_decorators(self):
        """
        Access to decorators : @...() 
        """
        return self._ast.get_decorators()
    
    def get_class(self, name, begin_line=None):
        """
        Return a class by name.
        From the classes inside that symbol.
        """
        try:
            _locals = self.find_local_symbols(name, [Class])
            if len(_locals) == 1:
                return _locals[0]
            if locals:
                for local in _locals:
                    if local.__start_line == begin_line:
                        return local
            else:
                return None
        except:
            return None

    def get_function(self, name, begin_line=None):
        """
        Return a function by name
        From the functions inside that symbol.
        """
        try:
            _locals = self.find_local_symbols(name, [Function])
            if len(_locals) == 1:
                return _locals[0]
            if locals:
                for local in _locals:
                    if local.__start_line == begin_line:
                        return local
            else:
                return None
        except:
            return None

    def add_import(self, _import):
        """
        Add an import
        """
        self.__imports.append(_import)

    def _light_parse(self, stream):
        """
        Create symbols and sub symbols.
        """
        symbol = self
        
        for node in stream:
            
            if is_import(node):
                self.add_import(node)
            
            if is_class(node):
                # create a class
                name = node.get_name()
                symbol = Class(name, self)
                symbol.__start_line = node.get_begin_line()
                symbol._ast = node
                self.add_symbol(name, symbol)
                symbol._inheritance = node.get_inheritance()
                symbol._light_parse(node.get_sub_nodes())
                
            elif is_function(node):
                
                name = node.get_name()
                symbol = Function(name, self)
                symbol.__start_line = node.get_begin_line()
                symbol._ast = node
                self.add_symbol(name, symbol) 
                symbol._light_parse(node.get_sub_nodes())
                
                if name == '__init__':
                    
                    # current class...
                    current_class = self
                    while not isinstance(current_class, Class) and current_class.get_parent_symbol():
                        current_class = current_class.get_parent_symbol()
                    
                    if current_class:
                        # probably a constructor, extract class members
                        for member in node.get_members():
                            current_class.add_member(member.text)
                
            elif isinstance(node, Node):
                # recurse
                self._light_parse(node.get_sub_nodes())
       
    def _fully_parse(self, stream):
        
        for node in stream:
            
            symbol = self
            
            if is_class(node):
                # search the class
                symbol = self.get_class(node.get_name(), node.get_begin_line())
                symbol._ast = node
                
            elif is_function(node):

                symbol = self.get_function(node.get_name(), node.get_begin_line())
                symbol._ast = node
            
            if isinstance(node, Node):
                # recurse
                symbol._fully_parse(node.get_sub_nodes())
        
        
    def get_kb_object(self):
        """
        Return the CAST knowledge base symbol. 
        """
        return self.__kb_symbol
            
    def get_header_comments_line_count(self):
        
        comments = self.get_header_comments()
        if not comments:
            return 0
        
        return comments.count('\n')
        

    def get_body_comments_line_count(self):

        comments = self.get_body_comments()
        if not comments:
            return 0
        
        return comments.count('\n')
            
    def get_line_count(self, exclude_docstring=True):
        
        def get_all_tokens(ast_node):
            """
            Iterates on all tokens of a tree or forest
            """
            if type(ast_node) is Token:
                yield ast_node
            elif type(ast_node) is list:
                for token in ast_node:
                    for sub in get_all_tokens(token):
                        yield sub
            else:
                for token in ast_node.children:
                    for sub in get_all_tokens(token):
                        yield sub
        
        def get_code_only_line_count(ast_node):
            
            if type(ast_node) is Token:
                # only for nodes or list of tokens
                return 0
            
            else:
                result = 0
                
                seen_non_blank = False
                
                for token in get_all_tokens(ast_node):
                    
                    if token.text:
                        
                        if is_token_subtype(token.type, Name.Decorator):
                            result += 1
                        elif token.text == '\n':
                            
                            if seen_non_blank:
                                result += 1
                            # reset
                            seen_non_blank = False
                        elif token.is_whitespace():
                            # blanks or 'fake' tokens
                            pass
                        elif token.is_comment():
                            if seen_non_blank:  # => inline comment
                                result += 1
                            # reset
                            seen_non_blank = False
                            
                        elif is_token_subtype(token.type, Literal.String.Doc): # @UndefinedVariable
                            if exclude_docstring:
                                pass
                            else:
                                result += token.text.count('\n')
                        else:
                            # non blanks
                            seen_non_blank = True
                    
                return result
        
        return get_code_only_line_count(self._ast)


    def get_header_comments(self):
        
        if not self._ast:
            return ''
        
        if type(self._ast) is list:
            comments = self._ast[0].get_header_comments()
            # here not sure... @todo check
            return ''.join(comment.text for comment in comments)
        else:
            
            comments = ''
            
            try:
                docstring = self._ast.get_docstring()
                if docstring:
                    comments = docstring + '\n'
            except:
                # no docstring
                pass
            
            for comment in self._ast.get_header_comments():
                comments += comment.text 
            return comments
            
    def get_body_comments(self, include_raw_token=False):
        """concatenate all comments from sub-nodes, adding a "\n" separator
        allowing straightforward comment line count 
        """ 
        if type(self._ast) is list:
            allComments = ''
            for token in self._ast:
                
                if token.type == Comment:
                    comments = [token]
                else:
                    comments = token.get_body_comments()
                
                allComments += ''.join(comment.text+'\n' for comment in comments)
                
            return allComments
        
        else:
            comments = ''
            for comment in self._ast.get_body_comments():
                comments += comment.text
                comments += "\n" 
            return comments
                

    def get_code_only_crc(self):
        
        node = self._ast
        
        if type(self._ast) is list:
            # build a fake node
            node = Node()
            node.children = self._ast
        
        # so that we reuse common code 
        return node.get_code_only_crc()
            
    def get_final_guid(self, guid):
        if not guid in self.subObjectsGuids:
            self.subObjectsGuids[guid] = 0
            return guid
        value = self.subObjectsGuids[guid]
        self.subObjectsGuids[guid] = value+1
        return guid + '_' + str(value+1) 

    def get_begin_line(self):
        
        if type(self._ast) is list:
            if not self._ast:
                return 1
            return self._ast[0].get_begin_line()
        else:
            return self._ast.get_begin_line()
    
#     Gets the current ast first column of first line
    def get_begin_column(self):
        
        
        if type(self._ast) is list:
            if not self._ast or not self._ast[0].get_begin_column():
                return 1
            
            return self._ast[0].get_begin_column()
        
        else:
            if not self._ast.get_begin_column():
                log.info(str(self._ast))
            
            return self._ast.get_begin_column()
    
#     Gets the current ast last line
    def get_end_line(self):
        
        if type(self._ast) is list:
        
            if not self._ast:
                return 1
            line = None
            shift = 0
            for token in reversed(self._ast):
                line = token.get_end_line()
                if line:
                    if token.text == "\n" or token.type == PygmentToken.LineFeed:
                        shift = 1
                    return line - shift
            return 0
        
        else:
            return self._ast.get_end_line()
    
#     Gets the current ast last column of last line
    def get_end_column(self):
        
        if type(self._ast) is list:
            
            if not self._ast:
                return 1
            line = None
            for token in reversed(self._ast):
                if token.text == "\n":
                    return token.get_begin_column()
                line = token.get_end_column()
                if line:
                    return line
            return 0
        
        else:
            return self._ast.get_end_column()

    def get_violations(self, property_name):
        """
        Returns all violations for a given rule.
        """
        try:
            return self.__violations[property_name]
        except:
            return []

    def add_violation(self, property_name, ast, *additional_asts):
        """
        Add a violation for a quality rule.
        
        :param property_name: fullname of the property
        :param ast: location of the violation
        """
        if additional_asts:
            ast = [ast]
            ast.extend(additional_asts)

        self.__violations[property_name].append(ast)

    def set_property(self, property_name, value):
        """
        Used to set a generic property on object
        
        mainly used for quality rules

        :param property_name: fullname of the property
        :param value: value of the property
        """
        self.__properties[property_name] = value
        
    def get_imported_symbols(self):
        """
        Access to all symbols imported with name
        """
        self._read_imports()
        return self.__imported_symbols_by_name
    
    def is_class(self):
        return False

    def is_function(self):
        return False
    
    def _read_imports(self):
        """
        Feed map of imported elements
        
        @todo : investigate the fact that we add a great number of times the exact same element
        in the case from ... import <module> 
        """


        for _import in self.get_imports():
            #   @type _import: python_parser.Import
            
            for method_or_class_reference in _import.get_imported_elements():
                
                imported_name = method_or_class_reference.get_name()
                if method_or_class_reference.get_alias():
                    imported_name = method_or_class_reference.get_alias()
                
                if imported_name != '*':
                    if imported_name not in self.__imported_symbols_by_name:
                        self.__imported_symbols_by_name[imported_name] = set()
                    self.__imported_symbols_by_name[imported_name] |= set(method_or_class_reference._resolutions)
                else:
                    for symbol in method_or_class_reference._resolutions:
                        if symbol.get_name() not in self.__imported_symbols_by_name:
                            self.__imported_symbols_by_name[symbol.get_name()] = set()
                        self.__imported_symbols_by_name[symbol.get_name()].add(symbol)
            
            if not _import.get_imported_elements():
                
                for reference in _import.get_module_references():
                
                    if reference.get_alias():
                        # import a.b as x
                        #  defines x as a name for module a.b
                        import_name = reference.get_alias()
                        
                        if import_name not in self.__imported_symbols_by_name:
                            self.__imported_symbols_by_name[import_name] = set()
                        self.__imported_symbols_by_name[import_name] |= set(reference._resolutions)
    
                    else:
                        # import a.b
                        #  defines a as a name for module a
                        import_name = reference.get_name()
                        
                        # take the first one 
                        import_name = import_name.split('.')[0]
                        
                        if import_name not in self.__imported_symbols_by_name:
                            self.__imported_symbols_by_name[import_name] = set()
                        self.__imported_symbols_by_name[import_name] |= set(self._library.get_modules_per_absolute_import(import_name, self))
        
            
    def save(self, file=None):
        """
        Save the objects and all its children to the KB.
        """
        if self.get_name() == 'builtins.py':
            return 

        if not file:
            file = self.get_file()
        
        if not self.__kb_symbol:
            
            fullname = self.get_fullname()
            
            if self.get_parent_symbol():
                fullname = self.get_parent_symbol().get_final_guid(self.get_fullname())
                parent = self.__parent.get_kb_object()
            else:
                parent = file
                
            kb_symbol = CustomObject()
            self.__kb_symbol = kb_symbol
            kb_symbol.set_name(self.__name)
            kb_symbol.set_type(self.metamodel_type)
            
            kb_symbol.set_parent(parent)
            kb_symbol.set_guid(fullname)
            kb_symbol.set_fullname(self.get_qualified_name())
            kb_symbol.save()
            crc = self.get_code_only_crc()
            kb_symbol.save_property('checksum.CodeOnlyChecksum', crc)

            # do not save line count for class and file content...            
            if self.metamodel_type not in [Module.metamodel_type, Class.metamodel_type]: 
                codeLines = self.get_line_count()
                kb_symbol.save_property('metric.CodeLinesCount', codeLines)
            
            # special case for sourceFiles
            if self.metamodel_type == Module.metamodel_type:
                version = get_cast_version()
                if (version >= StrictVersion('8.2.11') and version < StrictVersion('8.3.0')) \
                    or version >= StrictVersion('8.3.4'):
                    
                    # in those version range, UA do not calculate LOC on sourceFile so we do it ourself
                    # due to the usage of <languagePattern id="Python" UsedByUA="false">
                    file.save_property('metric.CodeLinesCount', self.get_line_count(exclude_docstring=False))
                    file.save_property('metric.BodyCommentLinesCount', self.get_body_comments_line_count())
                    file.save_property('metric.LeadingCommentLinesCount', self.get_header_comments_line_count())
                    file.save_property('comment.sourceCodeComment', self.get_body_comments())
                    file.save_property('comment.commentBeforeObject', '')
            
            headerCommentsLines = self.get_header_comments_line_count()
            if headerCommentsLines:
                kb_symbol.save_property('metric.LeadingCommentLinesCount', headerCommentsLines)
                kb_symbol.save_property('comment.commentBeforeObject', self.get_header_comments())
            bodyCommentsLines = self.get_body_comments_line_count()
            if bodyCommentsLines:
                kb_symbol.save_property('metric.BodyCommentLinesCount', bodyCommentsLines)
                kb_symbol.save_property('comment.sourceCodeComment', self.get_body_comments())
            
            self._save_position(file)

            if self.metamodel_type == Module.metamodel_type:
                docstring = True
                for token in TokenIterator(self.get_ast()):
                    if token.type in [StartLine, LineFeed]:
                        continue
                    else:
                        if is_token_subtype(token.type, DocString):
                            kb_symbol.save_property('CAST_Python_Metric.has_docstring', 1)
                            break
            else:
                try:
                    docstring = self.get_ast().get_docstring()
                except AttributeError:
                    pass
                else:
                    if docstring:
                        kb_symbol.save_property('CAST_Python_Metric.has_docstring', 1)

        # recurse...
        for symbol in self.get_all_symbols():
            symbol.save(file=file)

    def _save_position(self, file):
        
        self.__kb_symbol.save_position(Bookmark(file,
                                                self.get_begin_line(),
                                                self.get_begin_column(),
                                                self.get_end_line(),
                                                self.get_end_column()))

    def save_violations(self, file=None):
        
        def get_bookmark(file, ast):
            bookmark = Bookmark(file,
                    ast.get_begin_line(),
                    ast.get_begin_column(),
                    ast.get_end_line(),
                    ast.get_end_column())
            
            return bookmark
        
        # save the violations
        for rule in self.__violations:
            
            for ast in self.__violations[rule]:
                if ast and isinstance(ast, list):
                    position = get_bookmark(file, ast[0])
                    extended_positions = []
                    if len(ast) > 1:
                        for ext_pos in ast[1:]:
                            extended_positions.append(get_bookmark(file, ext_pos))
                    try:
                        if extended_positions:
                            self.__kb_symbol.save_violation(rule, position, extended_positions)
                        else:
                            self.__kb_symbol.save_violation(rule, position)
                    except:
                        log.debug("Error saving violation: {}".format(rule))
                        
                else:
                    position = get_bookmark(file, ast)
                    try:
                        self.__kb_symbol.save_violation(rule, position)
                    except RuntimeError:
                        log.debug("Error saving violation: {}".format(rule))
        
        
        # and the properties
        for property_name in self.__properties:
            self.__kb_symbol.save_property(property_name, self.__properties[property_name])
        
        # recurse on children
        for symbol in self.get_all_symbols():
            symbol.save_violations(file=file)

    def save_candidate_violations(self, rule_name, file=None):

        # save the violations
        for ast in self.__violations[rule_name]:

            try:
                self.__kb_symbol.save_violation(rule_name, Bookmark(file,
                                                               ast.get_begin_line(),
                                                               ast.get_begin_column(),
                                                               ast.get_end_line(),
                                                               ast.get_end_column()))
            except RuntimeError:
#                     import traceback
#                     log.warning(traceback.format_exc())
                log.debug("Error saving violation: {}".format(rule_name))

        # recurse on children
        for symbol in self.get_all_symbols():
            symbol.save_candidate_violations(rule_name=rule_name, file=file)


class Module(Symbol):
    """
    A python file.
    """

    metamodel_type = 'CAST_Python_SourceCode'
    
    def __init__(self, path, _file=None, text=None):
        """
        :param path: file path
        :param _file: cast.analyser.File the cast object representing the file
        
        :param text: str (for unit tests)
        """
        Symbol.__init__(self, os.path.basename(path))
        
        self.__path = path.replace('/', '\\') # normalise
        self.__text = text
        
        # KB object representing the file
        self.__file = _file
        
        # parsing result
        # a main is a block of code :
        #if __name__ == 'main':
        #     # ...
        self.__main = None
        
        # remote calls to urls
        self.__resource_services = []
        
        self.__server_operations = []
        
        self.__database_queries = []
        
        # import name 
        self._import_name = ''
        
        self._library = None
        
        self.__resolved_imports = False
        
        
        
    def light_parse(self):
        """
        First pass on a module, create sub symbols.
        """
        try:
            self._ast = list(light_parse(self.get_text()))        
        except BadIndentation:
            log.info('File seems to have incorrect indentation, skipping')
            self._ast = []
            
        self._light_parse(self._ast)

    def resolve_globals(self):
        """
        First pass of resolution, resolve imports and inheritance.
        """
        from resolution import resolve_globals
        resolve_globals(self, self._library, module=self)

    def set_imports_resolved(self):
        """
        Tell that the imports are resolved.
        """
        self.__resolved_imports = True

    def has_imports_resolved(self):
        """
        True when the import are resolved.
        """
        return self.__resolved_imports

    def is_package(self):
        """
        True when module is a package.
        """
        return self.get_name() == '__init__.py'

    def fully_parse(self):
        """
        Fully parse the module.
        
        - fill the import list
        - assign the ast for each element
        """
        try:
            self._ast = list(parse(self.get_text()))
        except BadIndentation:
            self._ast = []
        
        
        for node in self._ast:
            
            # top level nodes have the module as parent
            setattr(node, 'parent', self)
            
            if isinstance(node, Node):
                self._statements.append(node)

            if is_if_then_else(node) and not node.is_else():
                # search for main
                expression = node.get_expression()
                if not is_binary_operation(expression):
                    continue
                    
                left = expression.get_left_expression()

                if not is_identifier(left) or left.get_name() != '__name__':
                    continue
                
                right = expression.get_right_expression()
                if not is_constant(right) or right.get_value()[1:-1] != '__main__':
                    continue
                
                if not self.__main:
                
                    main = Main(os.path.basename(self.get_path()), self)
                    main._ast = [node]
                    self.__main = main
                else:
                    self.__main._ast.append(node)
        
        self._fully_parse(self._ast)        
        
    def get_path(self):
        
        return self.__path
    
    def get_file(self):
        return self.__file
    
    def get_library(self):
        """
        Library containing the module.
        """
        return self._library
    
    def get_qualified_name(self):
        """
        Qualified name
        """
        return self._import_name
    
    def is_analysed(self):
        """
        True when it is an analysed module.
        """
        return self.__text or self.__file
        
        
    def get_text(self):
        """
        Return something to pass to parsing method.
        - text (for unit testing)
        - or opened file 
        """
        if self.__text is not None:
            return self.__text
        
        return open_source_file(self.get_path())
    
    def get_statements(self):
        """
        Get the statements of the symbol.
        """
        return self._statements
    
    
    def get_main(self):
        """
        Return the 'main' found in that module 
        """
        return self.__main
    
    def add_resource_service(self, service):
        
        self.__resource_services.append(service)
        
    def get_resource_services(self):
        """
        Get the resource services found in module
        """
        return self.__resource_services
    
    def add_server_operation(self, operation):
        
        self.__server_operations.append(operation)
        
    def get_server_operations(self):
        """
        Get the server operations found in module
        """
        return self.__server_operations
    
    def add_db_query(self, query):
        
        self.__database_queries.append(query)
        
    def get_db_queries(self):
        
        return self.__database_queries
    
    def get_fullname(self):
        return self.__path + '/CAST_Python_SourceCode'
    
    def find_local_symbols(self, name, types=[]):
        """
        Override for modules. 
        """

        def filter_symbols(symbols, type_names):
            if types:
                return [symbol for symbol in symbols if symbol.metamodel_type in type_names]
            else:
                return symbols
            
        result = Namespace.find_local_symbols(self, name, types)
        if result:
            return result

        # search in imports @todo pull up because any body can have imports
        type_names = [_type.metamodel_type for _type in types]
        
        try:
            result = filter_symbols(self.get_imported_symbols()[name], type_names)
        except:
            pass
            
        if result:
            # local has precedence over sub modules
            return result
        
        # search in sub modules
        if self.is_package():
            return filter_symbols(self._library.get_modules_per_relative_import(name, self), type_names)
        
        return result


    
    def save_main(self):
        """
        Special save for main
        """
        if not self.__main:
            return
        
        self.__main.save(file=self.get_file())

        kb_object = self.__main.get_kb_object()
        ast = self.__main.get_ast()[0]
        
        create_link('callLink', 
                    kb_object, 
                    self.get_kb_object(), 
                    Bookmark(self.get_file(), 
                             ast.get_begin_line(),
                             ast.get_begin_column(),
                             ast.get_end_line(),
                             ast.get_end_column()))

        
    def save_links(self):
        """
        Save all the links.
        """
        walker = Walker()
        walker.register_interpreter(LinkInterpreter(self))
        walker.walk(self.get_ast())
        
    def save_services(self):
        """
        Save all services.
        """
        for service in self.__resource_services:
            service.save(self)
            
    def save_operations(self):
        """
        Save all web server operations.
        """
        for operation in self.__server_operations:
            operation.save(self)
            
    def save_db_queries(self):
        """
        Save all web server operations.
        """
        for query in self.__database_queries:
            query.save(self)
        
    def __repr__(self):
        
        return "Module %s" % self.get_path()

        
class LinkInterpreter:
    """
    Creates links.
    """
    def __init__(self, module):
        
        # current file
        self.file = module.get_file()
        
        # stack of symbols
        self.__symbol_stack = [module]
        
        self.handle_imports(module)
        
    def push_symbol(self, symbol):
        
        self.__symbol_stack.append(symbol)
        # for each one ...
        self.handle_imports(symbol)
    
    def pop_symbol(self):

        self.__symbol_stack.pop()

    def get_current_kb_symbol(self):
        
        return self.__symbol_stack[-1].get_kb_object()
    
    def get_current_symbol(self):
        
        return self.__symbol_stack[-1]

    def create_bookmark(self, ast):
        """
        Create a bookmark from an ast node
        """
        return Bookmark(self.file, ast.get_begin_line(), ast.get_begin_column(), ast.get_end_line(), ast.get_end_column())        
    
    
    def handle_imports(self, symbol):
        """
        Create links for all imports of a symbol
        """
        for _import in symbol.get_imports():
            self.handle_import(_import)
        
    def handle_import(self, import_ast):
        """
        Create links on import
        """
        # create include links
        for reference in import_ast.get_module_references():
                
            for target in reference.get_resolutions():
                if target.get_kb_object():
                    create_link('includeLink', self.get_current_kb_symbol(), target.get_kb_object(), self.create_bookmark(reference))
        
            # imported elements
            for method_or_class_reference in import_ast.get_imported_elements():
                
                for target in method_or_class_reference.get_resolutions():
                    if target.get_kb_object():
                        create_link('referLink', self.get_current_kb_symbol(), target.get_kb_object(), self.create_bookmark(method_or_class_reference))
    

    def start_ClassBlock(self, ast_class):
        
        _class = self.get_current_symbol().get_class(ast_class.get_name(), ast_class.get_begin_line())
        self.push_symbol(_class)
    
        # inheritance links
        for class_reference in _class.get_inheritance():
            for target in class_reference.get_resolutions():
                if target.get_kb_object():
                    create_link('inheritLink', self.get_current_kb_symbol(), target.get_kb_object(), self.create_bookmark(class_reference))
            
    
    def end_ClassBlock(self, ast_class):
        
        self.pop_symbol()

    def start_FunctionBlock(self, ast_function):
        self.start_Function(ast_function)

    def start_FunctionOneLine(self, ast_function):
        self.start_Function(ast_function)
        
    def start_Function(self, ast_function):
        
        function = self.get_current_symbol().get_function(ast_function.get_name(), ast_function.get_begin_line())
        self.push_symbol(function)
        
    def start_MethodCall(self, ast):
        # @type ast: python_parser.MethodCall
        
        bookmark_ast = ast.get_method()
        if is_dot_access(bookmark_ast):
            # @type bookmark_ast: python_parser.DotAccess
            bookmark_ast = bookmark_ast.get_identifier()

        for target in ast.get_resolutions():
            if target.get_kb_object():
                create_link('callLink', self.get_current_kb_symbol(), target.get_kb_object(), self.create_bookmark(bookmark_ast))
        
        
        method_expression = ast.get_method()
        
        for target in method_expression.get_resolutions():
            try:
                if target.metamodel_type == Class.metamodel_type and target.get_kb_object():
                    create_link('referLink', self.get_current_kb_symbol(), target.get_kb_object(), self.create_bookmark(method_expression))
            except:
                # other cases
                pass
            
    def end_FunctionBlock(self, ast_function):
        self.end_Function(ast_function)

    def end_FunctionOneLine(self, ast_function):
        self.end_Function(ast_function)
        
    def end_Function(self, ast_function):
        self.pop_symbol()


class Class(Symbol):
    """
    A python class
    """
    
    metamodel_type = 'CAST_Python_Class'
    
    def __init__(self, name, parent):
        Symbol.__init__(self, name, parent)
        
        self._inheritance = []
        
        # class members
        self.__members = {}
        
    def get_inheritance(self):
        """
        Inherited classes.
        
        :rtype: list of python_parser.Reference
        """
        return self._inheritance

    def find_method(self, name):
        """
        Find a method of the class, using inheritance
        """
        local = self.find_local_symbols(name, [Function])
        if local:
            return local
        
        for inheritance in self._inheritance:
            
            # first one wins, depth left first inheritance
            candidates = []
            for parent_class in inheritance.get_resolutions():
                
                candidates += parent_class.find_method(name)
            
            if candidates:
                return candidates
                
        
        return []
    
    def find_member(self, name):
        
        if name in self.__members:
            return [self.__members[name]]
        
        for inheritance in self._inheritance:
            
            candidates = []
            for parent_class in inheritance.get_resolutions():
                
                if parent_class == self:
                    continue
                
                candidates += parent_class.find_member(name)
            
            if candidates:
                return candidates
            
        return []
    
    def is_callable(self, method):
        """
        Says that :param method: is callable on that class.
        
        Handle override.
        """
        name = method.get_name()
        
        possible = self.find_method(name)

        if possible:
            # in case of override should be the same method
            return possible[0] == method
        
        for reference in self.get_inheritance():
            
            for inherited in reference.get_resolutions():
                
                if inherited.is_callable(method):
                    
                    return True
        
        return False

    def get_fullname(self):
        return self.get_parent_symbol().get_fullname() + '/CAST_Python_Class/' + self.get_name()

    def get_members(self):
        
        return self.__members

    def get_classes(self):
        
        return  {symbol.get_name(): symbol for symbol in self.get_all_symbols() if is_class(symbol)}
    
    def get_functions(self):
        
        return  {symbol.get_name(): symbol for symbol in self.get_all_symbols() if is_function(symbol)}

    def add_member(self, name):
        
        self.__members[name] = Member(name)

    def declare_member(self, name, ast):
        
        if name in self.__members:
            self.__members[name]._ast = ast

    def is_class(self):
        return True

    def __repr__(self):
        
        return "Class %s" % self.get_qualified_name()


class Function(Symbol):

    metamodel_type = 'CAST_Python_Method'
    
    def __init__(self, name, parent, return_type = None):
        Symbol.__init__(self, name, parent)
        self.return_type = return_type
        if parent and parent.is_class():
            module = self.get_root_symbol()
            library = module.get_library()
            if library:
                library.add_method(self)

    def get_fullname(self):
        return self.get_parent_symbol().get_fullname() + '/CAST_Python_Method/' + self.get_name()

    def is_function(self):
        return True

    def __repr__(self):
        
        return "Function %s" % self.get_qualified_name()


class Main(Symbol):
    """
    Main method of a script.
    """
    
    metamodel_type = 'CAST_Python_Script'
    
    def __init__(self, name, parent):
        Symbol.__init__(self, name)
        
        self.__file = parent
        
    def get_fullname(self):
        return self.__file.get_path() + '/CAST_Python_Script'

    def _save_position(self, file):
        
        kb_object = self.get_kb_object()
        
        # put several positions
        for ast in self.get_ast():
            kb_object.save_position(Bookmark(file,
                                             ast.get_begin_line(),
                                             ast.get_begin_column(),
                                             ast.get_end_line(),
                                             ast.get_end_column()))


def _get_uri_evaluation(uriToEvaluate, idList = None):
    """
    if not None, isList will contain ids present in the url, at the end of method
    evaluates uriToEvaluate replacing ids with {} and evaluating values of variables if present in uriToEvaluate
    """
    if isinstance(uriToEvaluate, str):
        uri = uriToEvaluate
    else:
        from evaluation import evaluate
        uri = evaluate(uriToEvaluate, charForUnknown='{}')

    if uri:
        if isinstance(uri, str):
            uris = uri.split('/')
            uri = None
            if uris:
                uri = ''
                for part in uris:
                    if part:
                        if part.startswith('http:'):
                            uri += 'http://'
                        elif part.startswith('https:'):
                            uri += 'https://'
                        elif part.startswith(':'):
                            if idList != None:
                                idList.append(part[1:])
                            uri += '{}/'
                        elif '?' in part:
                            uri += part[:part.find('?')]
                            uri += '/'
                        else:
                            uri += ( part + '/' )
            if not uri:
                return ['']
            return [uri]
        else:
            res = []
            for ur in uri:
                uris = ur.split('/')
                ur = None
                if uris:
                    ur = ''
                    for part in uris:
                        if part:
                            if part.startswith('http:'):
                                ur += 'http://'
                            elif part.startswith('https:'):
                                ur += 'https://'
                            elif part.startswith(':'):
                                if idList != None:
                                    idList.append(part[1:])
                                ur += '{}/'
                            elif '?' in part:
                                ur += part[:part.find('?')]
                                ur += '/'
                            else:
                                ur += ( part + '/' )
                    res.append(ur)
            return res
            
    return ['']


class Member():
    
    def __init__(self, name):
        
        self.__name = name
        self._ast = None
         
    def get_name(self):
        
        return self.__name
    
    def get_ast(self):
        return self._ast


class WebService:
    """
    Stores a service present on the client side to communicate to the server by http requests.
    """
    def __init__(self, name, typ, uri, ast, parentFullname):
        """
        name is the service name
        type is GET, POST, PUT or DELETE as a string
        uri is the url as an AST expression
        ast is the ast used for position
        parent is the resource parent
        """
        self.name = name
        self.ast = ast
        self.uri = uri
        self.type = typ    # GET/PUT/POST/DELETE
        self.kbObjects = []
        self.kbCallers = []
        self.parent = None
        self.parentFullname = parentFullname
        self.caller = None
        self.file = None
                
    # if not None, isList will contain ids present in the url, at the end of method
    def get_uri_evaluation(self, idList = None):
        """
        Evaluate urls values and normalise them 
        """
        return _get_uri_evaluation(self.uri, idList)
    
    def get_type(self):
        
        return self.type
    
    def get_kb_objects(self):
        return self.kbObjects
    
    def save(self, module):
        """
        Save to KB.
        """
        fullname = self.parentFullname + '/' + self.get_metamodel_type()
        checksum = self.ast.get_code_only_crc()
        position = Bookmark(module.get_file(), 
                            self.ast.get_begin_line(), 
                            self.ast.get_begin_column(), 
                            self.ast.get_end_line(), 
                            self.ast.get_end_column())
        
        fm = self.get_framework_name()
        
        library = module.get_library()
        
        for uri in self.get_uri_evaluation():
            service_object = CustomObject()
            service_object.set_name(self.name)
            service_object.set_type(self.get_metamodel_type())
                            
            service_object.set_parent(module.get_kb_object())
            
            guid = module.get_final_guid(fullname)
                    
            service_object.set_guid(guid)
            service_object.set_fullname(fullname)
            service_object.save()
                            
            service_object.save_property('CAST_ResourceService.uri', uri)
            service_object.save_property('checksum.CodeOnlyChecksum', checksum)
            service_object.save_position(position)
            
            if self.caller:
                create_link('callLink', self.caller.get_kb_object(), service_object, position)
                
            if fm == 'requests':
                library.nbRequestsServices += 1
            elif fm == 'httplib':
                library.nbHttplibServices += 1
            elif fm == 'httplib2':
                library.nbHttplib2Services += 1
            elif fm == 'aiohttp':
                library.nAiohttpServices += 1
            elif fm == 'urllib':
                library.nUrllibServices += 1
            elif fm == 'urllib2':
                library.nUrllib2Services += 1


class RequestsService(WebService):

    def __init__(self, name, typ, uri, ast, parentFullname):
        WebService.__init__(self, name, typ, uri, ast, parentFullname)
        
    def get_metamodel_type(self):
        if self.type == 'POST':
            return 'CAST_Python_PostRequestsService'
        elif self.type == 'PUT':
            return 'CAST_Python_PutRequestsService'
        elif self.type == 'DELETE':
            return 'CAST_Python_DeleteRequestsService'
        else:
            return 'CAST_Python_GetRequestsService'
        
    def get_framework_name(self):
        return 'requests'


class HttplibService(WebService):

    def __init__(self, name, typ, uri, ast, parentFullname):
        WebService.__init__(self, name, typ, uri, ast, parentFullname)
        
    def get_metamodel_type(self):
        if self.type == 'POST':
            return 'CAST_Python_PostHttplibService'
        elif self.type == 'PUT':
            return 'CAST_Python_PutHttplibService'
        elif self.type == 'DELETE':
            return 'CAST_Python_DeleteHttplibService'
        else:
            return 'CAST_Python_GetHttplibService'
        
    def get_framework_name(self):
        return 'httplib'

class Httplib2Service(WebService):

    def __init__(self, name, typ, uri, ast, parentFullname):
        WebService.__init__(self, name, typ, uri, ast, parentFullname)
        
    def get_metamodel_type(self):
        if self.type == 'POST':
            return 'CAST_Python_PostHttplib2Service'
        elif self.type == 'PUT':
            return 'CAST_Python_PutHttplib2Service'
        elif self.type == 'DELETE':
            return 'CAST_Python_DeleteHttplib2Service'
        else:
            return 'CAST_Python_GetHttplib2Service'
        
    def get_framework_name(self):
        return 'httplib2'

class AiohttpService(WebService):

    def __init__(self, name, typ, uri, ast, parentFullname):
        WebService.__init__(self, name, typ, uri, ast, parentFullname)
        
    def get_metamodel_type(self):
        if self.type == 'POST':
            return 'CAST_Python_PostAiohttpService'
        elif self.type == 'PUT':
            return 'CAST_Python_PutAiohttpService'
        elif self.type == 'DELETE':
            return 'CAST_Python_DeleteAiohttpService'
        else:
            return 'CAST_Python_GetAiohttpService'
        
    def get_framework_name(self):
        return 'aiohttp'

class UrllibService(WebService):

    def __init__(self, name, typ, uri, ast, parentFullname):
        WebService.__init__(self, name, typ, uri, ast, parentFullname)
        
    def get_metamodel_type(self):
        if self.type == 'POST':
            return 'CAST_Python_PostUrllibService'
        elif self.type == 'PUT':
            return 'CAST_Python_PutUrllibService'
        elif self.type == 'DELETE':
            return 'CAST_Python_DeleteUrllibService'
        else:
            return 'CAST_Python_GetUrllibService'
        
    def get_framework_name(self):
        return 'urllib'


class Urllib2Service(WebService):

    def __init__(self, name, typ, uri, ast, parentFullname):
        WebService.__init__(self, name, typ, uri, ast, parentFullname)
        
    def get_metamodel_type(self):
        if self.type == 'POST':
            return 'CAST_Python_PostUrllib2Service'
        elif self.type == 'PUT':
            return 'CAST_Python_PutUrllib2Service'
        elif self.type == 'DELETE':
            return 'CAST_Python_DeleteUrllib2Service'
        else:
            return 'CAST_Python_GetUrllib2Service'
        
    def get_framework_name(self):
        return 'urllib2'


class WebServerOperation():
    def __init__(self, operation_type, uri, ast, parentFullname):

        self.name = None
        self.type = operation_type
        self.ast = ast
        self.uri = uri
        self.kbObjects = []
        self.kbCallers = []
        self.parent = None
        self.parentFullname = parentFullname
        self.callee = None
        self.file = None

    @classmethod
    def adapt_uri(cls, uri):
        """
        to be implemented by derived classes if needed
        """
        return uri
     
    def get_kb_objects(self):
        return self.kbObjects
    
    def update_operation_number(self, library):
        """
        to be implemented by derived classes if needed
        """
        pass
     
    def save(self, module):
        """
        Save to KB.
        """
        fullname = self.parentFullname + '/' + self.type
        checksum = self.ast.get_code_only_crc()
        position = Bookmark(module.get_file(), 
                            self.ast.get_begin_line(), 
                            self.ast.get_begin_column(), 
                            self.ast.get_end_line(), 
                            self.ast.get_end_column())

        library = module.get_library()
        
        self.name = self.adapt_uri(self.uri) 
         
        operation_object = CustomObject()
        operation_object.set_name(self.name)
        operation_object.set_type(self.get_metamodel_type())
                         
        operation_object.set_parent(module.get_kb_object())
         
        guid = module.get_final_guid(fullname)
                 
        operation_object.set_guid(guid)
        operation_object.set_fullname(fullname)
        operation_object.save()
                                     
        operation_object.save_property('checksum.CodeOnlyChecksum', checksum)
        operation_object.save_position(position)
         
        if self.callee:
            create_link('callLink', operation_object, self.callee.get_kb_object(), position)
        
        self.update_operation_number(library)

    
class FlaskServerOperation(WebServerOperation):
    # Note: there is no PATCH, HEAD, OPTIONS operation types additionally found in Flask 
    # defined within CAST_... : 
    #   CAST_WebService_GetOperation, CAST_WebService_PostOperation, 
    #   CAST_WebService_PutOperation, CAST_WebService_DeleteOperation, CAST_WebService_AnyOperation
    #   

    @classmethod
    def adapt_uri(cls, uri):
        """
        Adapt flask annotation uri to CAST KB format convention.
        
        Implementation assumes no "/" inside parameter <abc>
        """
        if not uri.endswith("/"):
            uri = uri + "/"
        uri = re.sub('<[^/]+>','{}',uri)
        uri = re.sub('//','/{}/',uri)
        
        return uri
    
    def get_metamodel_type(self):
        if self.type == 'POST':
            return 'CAST_Python_Flask_PostOperation'
        elif self.type == 'PUT':
            return 'CAST_Python_Flask_PutOperation'
        elif self.type == 'DELETE':
            return 'CAST_Python_Flask_DeleteOperation'
        else:            
            return 'CAST_Python_Flask_GetOperation'
    
    def update_operation_number(self, library):
        library.nbFlaskServerOperations += 1



class AiohttpServerOperation(WebServerOperation):
    
    @classmethod
    def adapt_uri(cls, uri):
        """
        Transforms path with variables to CAST format
        
        '/a/{name}/c'  -->  '/a/{}/c'
        """
        
        if not uri.endswith("/"):
            uri = uri + "/"
            
        uri = re.sub('{[^/]+}','{}', uri) # to avoid capturing non-rearest brackets  { }/{ }
        uri = re.sub('//','/{}/', uri)
        
        return uri
    
    def get_metamodel_type(self):
        if self.type == 'POST':
            return 'CAST_Python_Aiohttp_PostOperation'
        elif self.type == 'PUT':
            return 'CAST_Python_Aiohttp_PutOperation'
        elif self.type == 'DELETE':
            return 'CAST_Python_Aiohttp_DeleteOperation'
        else:            
            return 'CAST_Python_Aiohttp_GetOperation'
    
    def update_operation_number(self, library):
        library.nbAiohttpServerOperations += 1
