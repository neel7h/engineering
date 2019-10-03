"""
Register and analyse web framework elements
"""

from light_parser import Walker
from cast.analysers import log
from symbols import FlaskServerOperation, AiohttpServerOperation
from python_parser import is_dot_access, is_constant, is_identifier
from python_parser import Constant, Identifier, Assignement, Array
from evaluation import evaluate
import re

def analyse(module):
    """
    Analyse an AST 
    """      
    walker = Walker()
    walker.register_interpreter(FlaskServer(module))
    walker.register_interpreter(AiohttpServer(module))
    
    walker.walk(module.get_ast())

def parse_methods_keyword_argument(expr):
    
    operations = []
    
    # resolve oplist :  app.add_url_rule(..., methods = oplist, ...)
    if isinstance(expr, Identifier):
        resolutions = expr.get_resolutions()
        enclosing = resolutions[0].get_enclosing_statement()
        assignment = enclosing.get_expression()
        
        expr = assignment.get_right_expression()
    
    operation_types = []
    
    if isinstance(expr, Array):
        operation_types = expr.get_values()
    
    for optype in operation_types:
        if isinstance(optype, (Constant, Identifier)):
            ops = evaluate(optype) 
            for op in ops:
                operations.append(op)
                
    return operations

def parse_flask_annotation(decorator, begin_line):
    """
    Extracts flask annotation elements
    
    @type decorator: light_parser.Lookahead
    
    :rtype: tuple ([str, ..], [str, ..])
    
    """
    uris = []
    operations = []
    
    parenthesis = next(decorator)
    nodes = parenthesis.get_sub_nodes()
    
    for node in nodes:
        # extract uri 
        if is_constant(node) or is_identifier(node):
            uris = evaluate(node)
        
        # keyword argument
        if isinstance(node, Assignement):
            keyword = node.get_left_expression()
            keyword = keyword.get_name()
            
            if keyword == 'methods':
                expr = node.get_right_expression()
                operations = parse_methods_keyword_argument(expr)
                
                if not operations:
                    return (uris, operations) # avoid default GET        
                
    # default when no 'methods' keyword
    if not operations:
        operations.append('GET')
    
    return (uris, operations)

class BaseInterpreter(object):
    def __init__(self,module):
        self._module = module
      
        self.__symbol_stack = [module]
    
    def push_symbol(self, symbol):
        
        return self.__symbol_stack.append(symbol)

    def pop_symbol(self):

        self.__symbol_stack.pop()
    
    def get_current_symbol(self):
        return self.__symbol_stack[-1]
    
    def start_ClassBlock(self, _ast_class):
        self.start_Class(_ast_class)
    
    def start_ClassOneLine(self, _ast_class):
        self.start_Class(_ast_class)
    
    def start_Class(self, _ast_class):
        """
        Resolve class inheritances
        """
        _class = self.get_current_symbol().get_class(_ast_class.get_name(), _ast_class.get_begin_line())
        if not _class:
            
            log.warning("no class found for %s under %s" % (str(_ast_class.get_name()), str(self.get_current_symbol())))
        
        self.push_symbol(_class)
    
    def end_ClassOneLine(self, _ast_class):
        self.end_Class(_ast_class)
    
    def end_ClassBlock(self, _ast_class):
        self.end_Class(_ast_class)
        
    def end_Class(self, _ast_class):
        self.pop_symbol()
      
    def start_FunctionBlock(self, ast_function):
        self.start_Function(ast_function)
            
    def start_FunctionOneLine(self, ast_function): 
        self.start_Function(ast_function)
        
    def start_Function(self, ast_function):
        
        name = ast_function.get_name()
        function = self.get_current_symbol().get_function(name, ast_function.get_begin_line())           
        
        self.push_symbol(function)

    def end_FunctionBlock(self, ast_function):
        self.end_Function(ast_function)
            
    def end_FunctionOneLine(self, ast_function): 
        self.end_Function(ast_function)
                
    def end_Function(self,ast_function):
        self.pop_symbol()


class FlaskServer(BaseInterpreter):    
        
    def create_flask_operations(self, uris, operations, function):
        ast_function = function.get_ast()
        for op in operations:
            if op in ['GET', 'POST', 'PUT', 'DELETE']:
                for uri in uris:
                    operation = FlaskServerOperation(op, uri, ast_function, self._module.get_fullname())
                    self._module.add_server_operation(operation)
                    operation.callee = function
    
    def start_Function(self, ast_function):
                        
        name = ast_function.get_name()
        function = self.get_current_symbol().get_function(name, ast_function.get_begin_line())           
         
        self.push_symbol(function)
        
        if not ast_function.get_decorators():
            return
           
        for decorator in ast_function.get_decorators():
            
            begin_line = decorator.get_begin_line()
            decorator = decorator.get_children()
            
            token = next(decorator)
            flask_route_match = re.search('@.+\.route', token.text)
            
            if flask_route_match:
                uris, operations = parse_flask_annotation(decorator, begin_line)
                
                if uris and operations:
                    log.debug("Flask route annotation URL : %s " % uris) 
                    self.create_flask_operations(uris, operations, function)
                else:
                    log.debug("Skipped route annotation at line {}".format(begin_line))
        
        
    
    def start_MethodCall(self, method_call):
        """
        :type method_call: python_parser.MethodCall
        
        Parse the alternative app.add_url_rule flask routing method.
        
        API doc:
        
            add_url_rule(rule, endpoint=None, view_func=None, **options)
        
            Connects a URL rule. Works exactly like the route() decorator. 
            If a view_func is provided it will be registered with the endpoint.
            
        @todo : treat general case where endpoint != view_func
        """
        
        try:
            parent = method_call.parent
        except:
            return  # skip potential issues with 'builtin' module
        
        if is_dot_access(parent):
            return
        
        method = method_call.get_method()
        
        if not is_dot_access(method):
            return
        
        name = method.get_name()
        if not name == 'add_url_rule':
            return
        
        rule = method_call.get_argument(0, 'rule')
        
        if rule:
            uris = evaluate(rule)
            endpoint = None  # type: Constant python_parser
            operations = []
            
            endpoint = method_call.get_argument(1, 'endpoint')
            methods = method_call.get_argument(None, 'methods')
            
            if methods:
                operations = parse_methods_keyword_argument(methods)
                
            if not operations:
                operations.append('GET')
            
            if endpoint:
                # skip string interpolation
                if not is_constant(endpoint):
                    return
                
                function_name = endpoint.get_string_value()
                function = self._module.get_function(function_name)
                
                if not function:
                    return
                
                try:
                    self.create_flask_operations(uris, operations, function)
                except:
                    log.debug("Error creating flask operations from 'add_url_rule' method call")

class AiohttpServer(BaseInterpreter):

    def create_aiohttp_operations(self, uris, operations, function):
        ast_function = function.get_ast()
        for op in operations:
            if op in ['GET', 'POST', 'PUT', 'DELETE']:
                for uri in uris:
                    operation = AiohttpServerOperation(op, uri, ast_function, self._module.get_fullname())
                    self._module.add_server_operation(operation)
                    operation.callee = function

    def start_MethodCall(self, method_call):
        """
        :type method_call: python_parser.MethodCall
        
        Recognizes method calls of the form 
        
            <a>.<b>...<c>.router.add_<x> 
            
        where x = {get, post, put, delete, route} as potential aiohttp web service operations. 
        It extracts uri, paths and operation names from method arguments or method names themselves.
        
        No further validity on aiohttp imports is checked. 
                        
        @todo : more complex cases with add_resource, add_static? 
        """   
        method = method_call.get_method()
        
        if not is_dot_access(method):
            return
        
        name = method.get_name()
        
        if name in ['add_get', 'add_post', 'add_put', 'add_delete', 'add_route']:
            
            expr = method.get_expression()
            
            # additional constraint in call form: a.b.c.route.add_get
            if is_dot_access(expr):
                instance_name = expr.get_name()
                if not instance_name == 'router':
                    return
            
            pad = 0
            operations = []  
            if name == 'add_route':
                method_ = method_call.get_argument(0, 'method')

                if not method_:
                    return                

                operations = evaluate(method_)  # potentially many values from conditional branches
                
                if not operations:
                    return                

                if '*' in operations:
                    operations = ['GET', 'PUT', 'POST', 'DELETE']

                pad = 1 
            
            path = method_call.get_argument(0 + pad, 'path')
            if not path:
                return
            uris = evaluate(path)
            
            handler = method_call.get_argument(1 + pad, 'handler')
            if not is_identifier(handler):
                return
            
            function_name = handler.get_name()
            function = self._module.get_function(function_name)  # @todo: test functions with same name
            
            if not operations:                
                operations.append( name.split('_')[1] )  # extraction from method name : add_get, ...
                        
            operations = [op.upper() for op in operations] # uppercase
            
            self.create_aiohttp_operations(uris, operations, function)