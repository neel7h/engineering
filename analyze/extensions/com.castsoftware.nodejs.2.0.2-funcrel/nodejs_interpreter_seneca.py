from nodejs_interpreter_framework import NodeJSInterpreterFramework
from cast.analysers import log


class NodeJSInterpreterSeneca(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)

    def start_function_call(self, fcall):
        try:

            callParts = fcall.get_function_call_parts()
            callPart = callParts[0]
            identifier = callPart.identifier_call

            if fcall.is_require():
                param = callPart.get_parameters()[0]
                if param.get_text() == 'seneca' and len(callParts) == 1:
                    self.parsingResults.seneca_require = True

                elif (param.get_text() == 'seneca' and len(callParts) > 1 and callParts[1].get_name() == 'use'):
                    self.parsingResults.seneca_uses.append(callParts)
                
            elif callPart.get_name() == 'use':
                id_call = callPart.identifier_call

                resolutions = id_call.get_resolutions()

                if self.is_from_require(resolutions, 'seneca'):
                    self.parsingResults.seneca_uses.append(callParts)
            
            elif callPart.get_name() == 'act' and identifier.get_prefix() in ['this', 'seneca'] :
                self.parsingResults.act_call.append(callParts)
            
            elif callPart.get_name() == 'add' and identifier.get_prefix() in ['this', 'seneca']:
                self.parsingResults.add_call.append(callParts)

        except:
            pass
        
    def start_assignment(self, assign):
        try:
            right_operand = assign.get_right_operand()
    
            if not right_operand.is_function_call() or not right_operand.is_require():
                return

        except:
            pass

    def end_function_call(self):
        pass
