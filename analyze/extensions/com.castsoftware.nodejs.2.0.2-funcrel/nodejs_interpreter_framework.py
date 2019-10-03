class Context:
        
    def __init__(self, parentContext, ast = None):
        self.parent = parentContext
        self.ast = ast
        
    def get_function(self):
        return None
        
    def get_kb_function(self):
        return None
        
    def get_class(self):
        return None
        
    def is_findOne(self):
        return False
        
    def is_findOne_return_variable(self, identifierName):
        if self.parent:
            return self.parent.is_findOne_return_variable(identifierName)
        else:
            return False
        
    def is_execute(self):
        return False
    
    def is_marklogic(self):
        return False
    
    def get_marklogic_context(self):
        if self.parent:
            return self.parent.get_marklogic_context()
        return None
    
    def get_current_function(self):
        if self.parent:
            return self.parent.get_current_function()
        else:
            return None
    
    def get_current_class(self):
        if self.parent:
            return self.parent.get_current_class()
        else:
            return None

    def is_open_connection(self):
        return False

    def get_openConnection_context(self):
        if self.parent:
            return self.parent.get_openConnection_context()
        return None
        
class NodeJSInterpreterFramework:

    def __init__(self, file, config, parsingResults, callerInterpreter):

        self.parsingResults = parsingResults
        self.callerInterpreter = callerInterpreter
        self.require_declarations = self.callerInterpreter.require_declarations
        self.file = file

    def get_current_context(self):
        return self.callerInterpreter.current_context
            
    def get_current_caller(self):
        return self.callerInterpreter.get_current_caller()
            
    def push_context(self, context):
        return self.callerInterpreter.push_context(context)

    def get_require_declaration(self, firstCallPartIdentifierCall):
        return self.callerInterpreter.get_require_declaration(firstCallPartIdentifierCall)
            
    def pop_context(self):
        return self.callerInterpreter.pop_context()
    
    def add_require(self, assignment):
        pass
 
    def require_contain(self, name):
        if not self.require_declarations:
            return False

        for value in self.require_declarations.values():
            if name == value.reference:
                return True

        return False

    def start_assignment(self, assign):
        pass
    
    def start_function_call(self, fcall):
        pass
        
    def end_function_call(self):
        pass
    
    def check_violation_dataservice_loop(self, callPart):
        # in case not else:

        f_parent = callPart

        while f_parent and hasattr(f_parent, 'is_loop') and not f_parent.is_loop():
            f_parent = f_parent.parent

        if f_parent and hasattr(f_parent, 'is_loop') and f_parent.is_loop():
            obj = f_parent
            while obj and hasattr(obj, 'is_function') and not obj.is_function():
                obj = obj.parent

            if obj and hasattr(obj, 'is_function') and obj.is_function():
                self.parsingResults.violations.add_avoid_using_the_call_of_data_service_with_Nodejs_inside_a_loop(obj, callPart.create_bookmark(self.file))
            else:
                self.parsingResults.violations.add_avoid_using_the_call_of_data_service_with_Nodejs_inside_a_loop(self.callerInterpreter.jsContent, callPart.create_bookmark(self.file))

    def normalize_uri(self, uri):
        result = ''
        try:
            elements = uri.split('/')

            for elm in elements:
                if elm.startswith(':'):
                    list_elm = list(elm)
                    list_elm[0] = '{'
                    list_elm.append('}')
                    elm = ''.join(list_elm)

                if elm:
                    result += '/' + elm
            if result:
                return result
            else:
                return '/'
        except:
            return uri

    def is_from_require(self, resolutions, requrie_name):
        try:
            for resolution in resolutions:
                parent_assign = resolution.callee.parent

                if not parent_assign.is_assignment():
                    continue

                right_exp = parent_assign.get_right_operand()

                if not right_exp.is_require():
                    continue

                firstCallPart = right_exp.functionCallParts[0]

                name = ''

                if firstCallPart.parameters and len(firstCallPart.parameters) == 1 and firstCallPart.parameters[0].is_string():
                    name = firstCallPart.parameters[0].get_name()

                return name == requrie_name

        except:
            return False
