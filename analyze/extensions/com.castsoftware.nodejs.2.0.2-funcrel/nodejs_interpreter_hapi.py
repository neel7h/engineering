from nodejs_interpreter_framework import NodeJSInterpreterFramework
from cast.analysers import log
from symbols import Service
      
class NodeJSInterpreterHapi(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)
        self.server = None
        self.name_var = None
        self.import_hapi = False
        
    def add_requires(self, assignment):
        pass

    def create_services(self, list_dict, element=None, is_dyn=False):
        uri = None
        handler = None

        for Ord in list_dict:
            if not hasattr(Ord, 'get_items'):
                continue

            method = Ord.get_item('method')

            if not method:
                continue

            # Check if method is a list ast
            if hasattr(method, 'get_values'):
                res = []
                for elm in method.get_values():
                    res.append(elm.get_text())

                method = res
            elif hasattr(method, 'get_text'):
                method = [method.get_text()]

            for method_request in method:

                if method_request not in ['GET', 'POST', 'PUT', 'DELETE']:
                    continue

                uri = Ord.get_item('path')
                
                if not uri:
                    continue
                
                handler = Ord.get_item('handler')
                config = Ord.get_item('config')

                if not handler and not config:
                    return
                elif not handler and config:
                    handler = config.get_item('handler')

                if not handler:
                    continue

                uri = self.normalize_uri(uri)

                service = Service(uri, method_request.lower(), handler, element)
                self.parsingResults.services.append(service)

    def start_function_call(self, fcall):

        # server can be created anywhere.
        try:
            name_router = '.route'
            element = fcall.get_children()[0]
    
            if not hasattr(element, 'identifier_call') or not element.identifier_call.get_text().endswith(name_router):
                return
    
            params = element.get_parameters()[0]
            if not hasattr(params, 'get_values'):
                params = [params]
            else:
                params = params.get_values()
            
            self.create_services(params, element)

        except:
            log.warning('hapi webservice resolution warninng')

    def find_require_hapi(self, function_call, left_exp):
        '''
        * Vefirfy if the import hapi is done.
        '''

        if not function_call.is_require():
            return
        try:
            firstCallPart = function_call.functionCallParts[0]
            name = ''

            if firstCallPart.parameters and len(firstCallPart.parameters) == 1 and firstCallPart.parameters[0].is_string():
                name = firstCallPart.parameters[0].get_name()

            if name == 'hapi' and left_exp.is_identifier():
                self.import_hapi = True
                self.name_var = left_exp.get_text()
        except:
            log.warning('Required warning')

    def find_declaration_server(self, right_exp, left_exp):
        '''
        * Vefirfy if the server is created by 'hapi'.
        '''

        if not self.import_hapi or not self.name_var:
            return

        try:
            name_dec = self.name_var + '.Server'
            for child in right_exp.get_children():
                if child.is_function_call():
                    declaration_server = child.get_token()  # first token in tokens list.
                    
                    if name_dec == declaration_server.get_text() and left_exp.is_identifier():
                        self.server = left_exp.get_text()
                        self.parsingResults.isApplication = True
                        return

                elif child.is_function_call_part():
                    declaration_server = child.get_tokens()
                    if declaration_server[0] == self.name_var and \
                       declaration_server[1] == 'server' and \
                       left_exp.is_identifier():

                        self.server = left_exp.get_text()
                        self.parsingResults.isApplication = True
                        return
        except:
            log.warning('server init warning')

    def start_assignment(self, assign):
        '''
        * Check condition.
        '''
        right_exp = assign.get_right_operand()
        left_exp = assign.get_left_operand()

        self.find_require_hapi(right_exp, left_exp)

        self.find_declaration_server(right_exp, left_exp)

        if not hasattr(right_exp, 'get_values'):
            return

        try:
            self.create_services(right_exp.get_values(), assign, True)
        except:
            return

    def end_function_call(self):
        pass
