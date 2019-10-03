from nodejs_interpreter_framework import NodeJSInterpreterFramework
from cast.analysers import log
from symbols import Service, LinkSuspension, ExternalLibrary, HttpRequest


def is_assignment(ast):
    try:
        return ast.is_assignment()
    except:
        return False


class NodeJSInterpreterExpress(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)
        self.expressRouterIdentifier = None
        self.http2ConnectVariables = []
        self.createClassVariables = {}

    def manage_express_service_or_request(self, firstCallPart):
        '''
        * ERROR CAN FACE: another frameworl use the same method to create webservice.
        * => add condition to know that we are using express.
        '''
        firstCallPartIdentifierCall = firstCallPart.identifier_call

        if firstCallPartIdentifierCall.get_prefix_internal():
            callName = firstCallPartIdentifierCall.get_name()

        requireDeclaration = self.get_require_declaration(firstCallPartIdentifierCall)
        if requireDeclaration:

            if requireDeclaration.reference in ['express', 'loopback'] and firstCallPart.parameters and len(firstCallPart.parameters) >= 2:
                '''
                * In case of 'express' is directly imported and use method.
                '''
                handler = firstCallPart.parameters[-1]
                routerReference = None
                if handler.is_identifier() and handler.get_resolutions():
                    try:
                        firts_resolution = handler.resolutions[0].callee
                        if firts_resolution.get_name() in self.callerInterpreter.require_declarations:
                            requireDecl = self.callerInterpreter.require_declarations[firts_resolution.get_name()]
                            routerReference = requireDecl.reference
                        else:
                            if firts_resolution.is_identifier():
                                '''
                                * Missing verify if calleefn is a require a router. 
                                * The light parser has no enough info to resolve at the end.(the require needd)
                                * Condition added actually just valid if var named by 'router'
                                '''
                                handlerfn = handler.get_fullname()
                                calleefn = firts_resolution.get_fullname()

                                # if not handler == contacts.something and callee == contact for example
                                if not handlerfn.startswith(calleefn + '.') and calleefn in ['router']:
                                    routerReference = handler.resolutions[0].callee
#                                 if handlerfn == calleefn:
#                                     routerReference = handler.resolutions[0].callee
#                                 else:
#                                     routerReference = handler.resolutions[0].callee

#                             if handler.resolutions[0].callee.is_identifier():
#                                 routerReference = handler.resolutions[0].callee
                    except:
                        routerReference = None
                service = Service(firstCallPart.parameters[0], callName, handler, firstCallPart)
                if self.callerInterpreter.loopDepth > 0:
                    service.inLoop = True
                if routerReference:
                    service.routerReference = routerReference
                self.parsingResults.services.append(service)

            elif requireDeclaration.reference == 'https' and firstCallPart.parameters and len(firstCallPart.parameters) >= 2:

                paramHandler = firstCallPart.parameters[1]
                if self.callerInterpreter.stack_contexts:
                    func = self.callerInterpreter.stack_contexts[-1].get_function()
                    path = firstCallPart.parameters[0]
                    if func:
                        request = HttpRequest(path, firstCallPartIdentifierCall.get_name().upper(), func, paramHandler, firstCallPart)
                    else:
                        request = HttpRequest(path, firstCallPartIdentifierCall.get_name().upper(), self.callerInterpreter.jsContent, paramHandler, firstCallPart)
                self.parsingResults.httpRequests.append(request)
                if not paramHandler.is_function() and paramHandler.get_resolutions():
                    for resolution in paramHandler.get_resolutions():
                        if resolution.callee:
                            request.handler = resolution.callee

        elif self.expressRouterIdentifier and firstCallPartIdentifierCall.get_resolutions() and firstCallPartIdentifierCall.resolutions[0].callee == self.expressRouterIdentifier:
            if len(firstCallPart.parameters) >= 2:
                service = Service(firstCallPart.parameters[0], callName, firstCallPart.parameters[-1], firstCallPart)
                if self.callerInterpreter.loopDepth > 0:
                    service.inLoop = True
                service.isRouter = True
                self.parsingResults.services.append(service)

        elif firstCallPartIdentifierCall.get_resolutions() and firstCallPartIdentifierCall.resolutions[0].callee.parent.is_function() and firstCallPartIdentifierCall.resolutions[0].callee in firstCallPartIdentifierCall.resolutions[0].callee.parent.get_parameters():
            '''
            * In the case that: exportName = function (app, ...){
            *     app.get(...)
            * } 
            * TO DO: Must add more restrict condition: param must contain a string as url.
            '''

            func = firstCallPartIdentifierCall.resolutions[0].callee.parent
            if firstCallPartIdentifierCall.get_prefix() and firstCallPartIdentifierCall.get_prefix() in ['app', 'server'] and len(firstCallPart.parameters) >= 2:  # approximation because too difficul when one file is parsed after the other
                service = Service(firstCallPart.parameters[0], callName, firstCallPart.parameters[-1], firstCallPart)
                if self.callerInterpreter.loopDepth > 0:
                    service.inLoop = True
                self.parsingResults.services.append(service)

        else:
            '''
            * Verify uri param and handler function.
            * This scope must be improved in the future.   
            '''

            params = firstCallPart.get_parameters()

            try:
                if len(params) == 3 and params[0].is_string() and params[2].is_function_call():
                    identCall = params[2].get_function_call_parts()[0].identifier_call

                    if identCall.get_resolutions():
                        for resol in identCall.get_resolutions():
                            callee = resol.callee
                            service = Service(params[0], firstCallPart.identifier_call.get_name(), callee, firstCallPart)
                            break
                    else:
                        service = Service(params[0], firstCallPart.identifier_call.get_name(), None, firstCallPart)

                    self.parsingResults.potentialExpressControllerRoutesFCall.append(service)
            except:
                pass

    # return a dictionary with, for each key, the list of evaluations
    def evaluate_object_value(self, ov, keys):

        res = {}
        for key in keys:
            item = ov.get_item(key)
            if not item:
                res[key] = None
            ev = item.evaluate(None, None, None, '???')
            res[key] = ev
        return res

    # return a dictionary with, for each key, the list of evaluations
    def evaluate_http_options(self, options, pathKeyName, methodKeyName):

        ovEvals = self.evaluate_object_value(options, [pathKeyName, methodKeyName])
        if ovEvals:
            pathes = ovEvals[pathKeyName]
            newPathes = []
            for path in pathes:
                # insert {} between // in url except after ://
                newpath = path.replace('???', '{}')
                if '?' in newpath:
                    index = newpath.find('?')
                    newpath = newpath[0:index]
                newPathes.append(newpath)
            ovEvals[pathKeyName] = newPathes
        return ovEvals

    def manage_request(self, firstCallPart):

        firstCallPartIdentifierCall = firstCallPart.identifier_call

        requireDeclaration = self.get_require_declaration(firstCallPartIdentifierCall)
        if requireDeclaration:

            if requireDeclaration.reference in ['http', 'https'] and firstCallPart.parameters and len(firstCallPart.parameters) >= 2:

                options = firstCallPart.parameters[0]
                optionsEvals = []
                if options.is_object_value():
                    optionsEv = self.evaluate_http_options(options, 'path', 'method')
                    if optionsEv:
                        optionsEvals.append(optionsEv)
                elif options.is_identifier() and options.get_resolutions():
                    for resol in options.get_resolutions():
                        if resol.callee.parent and resol.callee.parent.is_assignment():
                            rightOperand = resol.callee.parent.get_right_operand()
                            if rightOperand.is_object_value():
                                optionsEv = self.evaluate_http_options(rightOperand, 'path', 'method')
                                if optionsEv:
                                    optionsEvals.append(optionsEv)

                if not optionsEvals:
                    return

                pathsByMethod = {}
                for optionsEval in optionsEvals:
                    methods = optionsEval['method']
                    pathes = optionsEval['path']
                    for method in methods:
                        for path in pathes:
                            if method in pathsByMethod:
                                l = pathsByMethod[method]
                            else:
                                l = []
                                pathsByMethod[method] = l
                            if not path in l:
                                l.append(path)
                                paramHandler = firstCallPart.parameters[1]
                                if self.callerInterpreter.stack_contexts:
                                    func = self.callerInterpreter.stack_contexts[-1].get_function()
                                    if func:
                                        request = HttpRequest(path, method, func, paramHandler, firstCallPart)
                                    else:
                                        request = HttpRequest(path, method, self.callerInterpreter.jsContent, paramHandler, firstCallPart)
                                self.parsingResults.httpRequests.append(request)
                                if not paramHandler.is_function() and paramHandler.get_resolutions():
                                    for resolution in paramHandler.get_resolutions():
                                        if resolution.callee:
                                            request.handler = resolution.callee
        else:
            callees = self.callerInterpreter.get_resolution_callees(firstCallPartIdentifierCall)
            for callee in callees:
                if callee in self.http2ConnectVariables:
                    if self.callerInterpreter.loopDepth > 0:
                        self.callerInterpreter.diagsInterpreter.violations.add_http_get_or_request_inside_loop_violation(self.callerInterpreter.jsContent, firstCallPart.create_bookmark(self.file))
                    options = firstCallPart.parameters[0]
                    optionsEvals = []
                    if options.is_object_value():
                        optionsEv = self.evaluate_http_options(options, ':path', ':method')
                        if optionsEv:
                            optionsEvals.append(optionsEv)

                    if not optionsEvals:
                        return

                    pathsByMethod = {}
                    for optionsEval in optionsEvals:
                        methods = optionsEval[':method']
                        pathes = optionsEval[':path']
                        for method in methods:
                            for path in pathes:
                                if method in pathsByMethod:
                                    l = pathsByMethod[method]
                                else:
                                    l = []
                                    pathsByMethod[method] = l
                                if not path in l:
                                    l.append(path)
                                    paramHandler = None
                                    if self.callerInterpreter.stack_contexts:
                                        func = self.callerInterpreter.stack_contexts[-1].get_function()
                                        if func:
                                            request = HttpRequest(path, method, func, paramHandler, firstCallPart)
                                        else:
                                            request = HttpRequest(path, method, self.callerInterpreter.jsContent, paramHandler, firstCallPart)
                                    self.parsingResults.httpRequests.append(request)
                                    if paramHandler and not paramHandler.is_function() and paramHandler.get_resolutions():
                                        for resolution in paramHandler.get_resolutions():
                                            if resolution.callee:
                                                request.handler = resolution.callee

    def is_express_router(self, firstCallPart):

        requireDeclaration = self.get_require_declaration(firstCallPart.identifier_call)
        if requireDeclaration:

            if requireDeclaration.reference in ['express', 'loopback']:
                return True

        return False

    def router_process(self, fcall):
        if not fcall.parent or not fcall.parent.is_assignment():
            return

        # verify :  var router = new Router()
        if not fcall.parent.get_right_operand().is_new_expression():
            return

        if not self.expressRouterIdentifier:
            return

        firstCallPart = fcall.get_function_call_parts()[0]
        if firstCallPart.identifier_call.get_resolutions() and firstCallPart.identifier_call.resolutions[0].callee == self.expressRouterIdentifier:
            self.expressRouterIdentifier = fcall.parent.get_left_operand()

        elif firstCallPart.get_parameters():
            for param in firstCallPart.get_parameters():
                try:
                    if not param.get_resolutions() or not param.resolutions[0].callee == self.expressRouterIdentifier:
                        continue

                    if not firstCallPart.identifier_call.get_resolutions():
                        continue

                    for resol in firstCallPart.identifier_call.get_resolutions():
                        if resol.callee.is_method():
                            self.parsingResults.potentialExpressControllerClasses.append(resol.callee.parent)
                except:
                    pass

    def start_function_call(self, fcall):

        self.router_process(fcall)

        callParts = fcall.get_function_call_parts()
        firstCallPart = True

        for callPart in callParts:

            firstCallPartIdentifierCall = callPart.identifier_call
            if firstCallPart:
                if firstCallPartIdentifierCall.get_fullname() in self.callerInterpreter.functionListFullNames:
                    caller = self.get_current_caller()
                    self.callerInterpreter.externalLibFunctionCalls.append(LinkSuspension('callLink', caller, None, callPart))
                elif firstCallPartIdentifierCall.get_fullname() in self.callerInterpreter.functionCreatingClassListFullNames:
                    if fcall.parent and is_assignment(fcall.parent):
                        v = fcall.parent.get_left_operand()
                        if v.is_identifier():
                            n = firstCallPartIdentifierCall.get_name()
                            if n in self.createClassVariables:
                                l = self.createClassVariables[n]
                            else:
                                l = []
                                self.createClassVariables[n] = l
                            l.append(v)
                elif firstCallPartIdentifierCall.get_name() in ExternalLibrary.methodList:
                    callees = self.callerInterpreter.get_resolution_callees(firstCallPartIdentifierCall)
                    for callee in callees:
                        for createClassMethod, _vars in self.createClassVariables.items():
                            if callee in _vars:
                                caller = self.get_current_caller()
                                ls = LinkSuspension('callLink', caller, None, callPart)
                                ls.infos['createClass'] = callee.parent.get_right_operand().get_function_call_parts()[0].get_identifier()
                                ls.infos['createClassMethod'] = createClassMethod
                                self.callerInterpreter.externalLibMethodCalls.append(ls)
                                break

            if firstCallPartIdentifierCall.get_prefix_internal() or not firstCallPart:

                callName = firstCallPartIdentifierCall.get_name()

                if callName in ['put', 'get', 'post', 'delete', 'use']:
                    self.manage_express_service_or_request(callPart)

                elif callName == 'request':
                    self.manage_request(callPart)

                elif callName == 'connect':
                    firstCallPart = fcall.get_function_call_parts()[0]
                    firstCallPartIdentifierCall = firstCallPart.identifier_call
                    requireDeclaration = self.get_require_declaration(firstCallPartIdentifierCall)
                    if requireDeclaration:
                        if requireDeclaration.reference == 'http2' and firstCallPart.parameters and len(firstCallPart.parameters) >= 1:
                            if fcall.parent and fcall.parent.is_assignment():
                                self.http2ConnectVariables.append(fcall.parent.get_left_operand())

                elif callName == 'on':
                    paramHandler = callPart.parameters[1]
                    if callPart.parameters and len(callPart.parameters) >= 2:
                        if self.callerInterpreter.stack_contexts:
                            try:
                                currentFunction = self.callerInterpreter.stack_contexts[-1].get_function()
                            except:
                                currentFunction = None
                        else:
                            currentFunction = None

                        if paramHandler.is_function():
                            if paramHandler in self.callerInterpreter.onHandlersSuspensions:
                                l = self.callerInterpreter.onHandlersSuspensions[paramHandler]
                            else:
                                l = []
                                self.callerInterpreter.onHandlersSuspensions[paramHandler] = l
                            if not currentFunction in l:
                                l.append(currentFunction)
                        elif paramHandler.get_resolutions():
                            for resolution in paramHandler.get_resolutions():
                                if resolution.callee in self.callerInterpreter.onHandlersSuspensions:
                                    l = self.callerInterpreter.onHandlersSuspensions[resolution.callee]
                                else:
                                    l = []
                                    self.callerInterpreter.onHandlersSuspensions[resolution.callee] = l
                                if not currentFunction in l:
                                    l.append(currentFunction)

                elif callName == 'Router':
                    if self.is_express_router(callPart):
                        assignment = fcall.parent
                        if assignment.is_assignment():
                            self.expressRouterIdentifier = assignment.get_left_operand()
            else:
                pass

            firstCallPart = False

    def start_assignment(self, assign):
        pass
    
    def end_function_call(self):
        pass
