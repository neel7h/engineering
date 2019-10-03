from cast.analysers import log
from nodejs_interpreter_framework import Context, NodeJSInterpreterFramework
from symbols import LinkSuspension
import os

def is_resolved_to_function_parameter(elt):
    
    if not elt.get_resolutions():
        return False
    for resol in elt.get_resolutions():
        callee = resol.callee
        try:
            if callee.parent and callee.parent.is_function() and callee in callee.parent.get_parameters():
                return True
        except:
            pass
    return False
      
class NodeJSInterpreterLoopback(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)
        self.analysisContext = callerInterpreter.analysisContext

        self.currentLoopbackApp = None
        self.currentLoopbackModel = None
        self.currentLoopbackModelName = ''
        self.loopback_dec = None
        dirname = os.path.dirname(file.get_path())
        if dirname in self.analysisContext.loopbackApplicationsByModelRootPath: # then file is a loopback model
            self.currentLoopbackApp = self.analysisContext.loopbackApplicationsByModelRootPath[dirname]
            if file.get_path()[:-2] + 'json' in self.currentLoopbackApp.jsonModelFiles:
                for name, model in self.currentLoopbackApp.models.items():
                    if name.lower() == os.path.basename(file.get_path()[:-3]).lower():
                        self.currentLoopbackModel = model
                        self.currentLoopbackModelName = name
                        model['kbObject'].save_position(self.callerInterpreter.analysisContext.jsContent.create_bookmark(file))
                        break
        
    def start_function_call(self, fcall):

        if not self.currentLoopbackModel:
            return

        callParts = fcall.get_function_call_parts()
        firstCallPart = callParts[0]
        firstCallPartIdentifierCall = firstCallPart.identifier_call
        
        if firstCallPartIdentifierCall.get_prefix_internal():
#             if firstCallPartIdentifierCall.get_prefix() == self.currentLoopbackModelName:
            if is_resolved_to_function_parameter(firstCallPartIdentifierCall):
                #   Todo.remoteMethod('stats', {
                #     accepts: {arg: 'filter', type: 'object'},
                #     returns: {arg: 'stats', type: 'object'},
                #     http: { path: '/stats' }
                #   }, Todo.stats);
                if firstCallPartIdentifierCall.get_name() == 'remoteMethod':
                    methodName = firstCallPart.get_parameters()[0]
                    try:
                        param2 = firstCallPart.get_parameters()[1]
                        if param2.is_object_value():
                            http = param2.get_item('http')
                            if http.is_object_value():
                                url = http.get_item('path').evaluate()[0] 
                    except:
                        url = '/' + methodName
                    try:
                        param3 = firstCallPart.get_parameters()[2]
                        if param3.is_function():
                            callee = param3
                        elif param3.get_resolutions():
                            for resol in param3.get_resolutions():
                                callee = resol.callee
                                break
                    except:
                        callee = None
    
                    self.parsingResults.loopbackRemoteMethods.append(('GET', url, self.currentLoopbackApp, self.currentLoopbackModel, 'callLink', callee, methodName))
            
            elif firstCallPartIdentifierCall.get_name() in ['count', 'findOne', 'findById']:
                # this.count(...)
                if firstCallPartIdentifierCall.get_prefix() == 'this':
                    self.parsingResults.linkSuspensions.append(LinkSuspension('useSelectLink', self.get_current_caller(), self.currentLoopbackModel['kbSymbol'], firstCallPart))
                elif firstCallPartIdentifierCall.get_resolutions():
                    for resol in firstCallPartIdentifierCall.get_resolutions():
                        callee = resol.callee
                        try:
                            if callee.parent and callee.parent.is_assignment() and callee.parent.get_right_operand().is_identifier() and callee.parent.get_right_operand().get_name() == 'this':
                                self.parsingResults.linkSuspensions.append(LinkSuspension('useSelectLink', self.get_current_caller(), self.currentLoopbackModel['kbObject'], firstCallPart))
                                break
                        except:
                            pass

    def find_server(self, assign):
        right_operation = assign.get_right_operand()

        if not right_operation.is_function_call():
            return

        firstCallPart = right_operation.functionCallParts[0]
        params = firstCallPart.get_parameters()

        if firstCallPart.get_name() == 'require' and len(params) == 1 and params[0].get_text() == 'loopback':
            self.loopback_dec = assign.get_left_operand()

        if self.loopback_dec and firstCallPart.get_name() == self.loopback_dec.get_name():
            self.parsingResults.LoopbackServer = True
    
    def start_assignment(self, assign):
        if self.require_contain('loopback') and not self.parsingResults.LoopbackServer:
            self.find_server(assign)

    def end_function_call(self):
            
        if not self.currentLoopbackModel:
            return
