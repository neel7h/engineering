from nodejs_interpreter_framework import NodeJSInterpreterFramework
from cast.analysers import log

method_mqtt = ['connect', 'Client' , 'publish', 'subscribe', 'end', 'removeOutgoingMessage', 'reconnect', 'handleMessage', 'getLastMessageId', 'Store', 'put', 'del', 'createStream', 'close']
event_mqtt = ['connect', 'reconnect', 'close', 'offline', 'error', 'end', 'message', 'packetsend', 'packetreceive']
       

class NodeJSInterpreterMQTT(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)


    def start_function_call(self, fcall):
        try:
            callParts = fcall.get_function_call_parts()
            callPart = callParts[0]
            
            if fcall.is_require():
                param = callPart.get_parameters()[0]
                if param.get_text() == 'mqtt':
                    self.parsingResults.mqtt_require = True
                    return

            identifier = callPart.identifier_call
            resolutions = identifier.get_resolutions()

            # should be list of identifier or function_call(missing info)
            if not resolutions:
                return

            name_call = identifier.get_name()

            if name_call in method_mqtt:
                self.parsingResults.mqtt_methods.append((callPart, self.file))

            elif name_call == 'on':
                param = callPart.get_parameters()[0]

                if hasattr(param, 'get_text') and param.get_text() in event_mqtt:
                    self.parsingResults.mqtt_events.append((callPart, self.file))
        except:
            log.debug('from MQTT interpreter function call')

    def start_assignment(self, assign):
        pass

    def end_function_call(self):
        pass
