from nodejs_interpreter_framework import NodeJSInterpreterFramework
from cast.analysers import log
from symbols import Service

class NodeJSInterpreterKoa(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)
        self.koa_name = None

    def start_assignment(self, assign):

        right_exp = assign.get_right_operand()
        left_exp = assign.get_left_operand()

        try:

            if hasattr(left_exp, 'is_identifier') and left_exp.is_identifier() and left_exp.get_name() in ['app', 'server']:

                callpart = None

                if right_exp.is_new_expression():
                    elm = right_exp.get_elements()[-1]
                    callpart = elm.get_function_call_parts()[0]
                elif right_exp.is_function_call():
                    callpart = right_exp.get_function_call_parts()[0]

                if not callpart:
                    return

                resolutions = callpart.identifier_call.get_resolutions()

                if self.is_from_require(resolutions, 'koa'):
                    self.parsingResults.isApplication = True

        except:
            log.debug('Koa app finding warning')

    def is_router_koa(self, resolutions):
        if not resolutions:
            return False

        # Try to verify if the require is from koa-router.
        for resolution in resolutions:
            try:
                parent_assign = resolution.callee.parent

                if not parent_assign.is_assignment():
                    continue

                right_exp = parent_assign.get_right_operand()

                if right_exp.is_function_call() and right_exp.get_name() == 'require':
                    callpart = right_exp.get_function_call_parts()[0]
                    params = callpart.get_parameters()

                    if params[0].get_text() == 'koa-router':
                        return True

                if not right_exp.is_new_expression():
                    continue

                call_f = right_exp.get_children()[-1].get_function_call_parts()[0]
                id_call_router = call_f.identifier_call
                res_router = id_call_router.get_resolutions()

                if self.is_from_require(res_router, 'koa-router'):
                    return True

            except:
                continue

        return False

    def resolve_service(self, callpart):
        try:

            identifier_call = callpart.identifier_call
            name_call = identifier_call.name
            if name_call in ['get', 'post', 'put', 'del', 'use']:
                resolutions = identifier_call.get_resolutions()
    
                if identifier_call.get_text() in ['app.use', 'server.use']:
                    param = callpart.get_parameters()[0]
                    if param.is_function_call() and param.get_name() in ['routes', 'middleware']:
                        service = Service('/', name_call, None, callpart)
                        service.koa_router = param.get_function_call_parts()[0].identifier_call
                        service.koa_use = True
                        self.parsingResults.services.append(service)
                        return
    
                if not self.is_router_koa(resolutions) or not len(callpart.get_parameters()) >= 2:
                    return
    
                # This is a operation service of koa
                params = callpart.get_parameters()
                uri = params[0]
                handler = params[-1]
                if handler.is_function_call():
                    callpart_hdl = handler.get_function_call_parts()[0]
                    handler = callpart_hdl.identifier_call
                    
                if not handler.is_identifier() and not handler.is_function():
                    return

                if name_call == 'del':
                    name_call = 'delete'

                service = Service(uri, name_call, handler, callpart)

                if not name_call == 'use':
                    service.isRouter = True

                service.koa_router = handler
                self.parsingResults.services.append(service)

        except:
            log.warning('koa operation service is not correct')
            pass

    def start_function_call(self, fcall):

        callpart = fcall.get_function_call_parts()[0]
        self.resolve_service(callpart)

    def end_function_call(self):
        pass
