from cast.analysers import log, CustomObject, create_link


def same_position(pos1, pos2):
    try:
        path_1 = pos1.get_file().get_path()
        path_2 = pos2.get_file().get_path()
        
        return path_1 == path_2 and pos1.get_begin_line() == pos1.get_begin_line() and\
                pos1.get_begin_column() == pos2.get_begin_column() and \
                pos1.get_end_line() == pos2.get_end_line() and \
                pos1.get_end_column() == pos2.get_end_column()
        
    except:
        return False

class MQTTClient:
    
    def __init__(self, parent, callPart, name, file, metal_type, connection=None):
        self.parent = parent
        self.callPart = callPart
        self.name = name
        self.file = file
        self.metal_type = metal_type
        self.connection = connection
        self.kbObject = self.__create_object()

    def get_position_connection(self):
        if self.connection:
            return self.connection.position()

        return None

    def position(self):
        return self.callPart.create_bookmark(self.file)

    def __create_object(self):

        position = self.position()
        kbObject = CustomObject()
        kbObject.set_name(self.name)
        kbObject.set_parent(self.parent.kbObject)
        kbObject.set_type(self.metal_type)
        kbObject.set_guid(self.name + ': ' + str(position))
        kbObject.save()
        kbObject.save_position(position)

        if self.metal_type == 'CAST_NodeJS_MQTT_Subscriber':
            kbObject.save_property('CAST_MQE_QueueReceive.queueName', self.name)
            kbObject.save_property('CAST_MQE_QueueReceive.messengingSystem', 'MQTT')

        elif self.metal_type == 'CAST_NodeJS_MQTT_Publisher':
            kbObject.save_property('CAST_MQE_QueueCall.queueName', self.name)
            kbObject.save_property('CAST_MQE_QueueCall.messengingSystem', 'MQTT')

        if not self.metal_type == 'CAST_NodeJS_MQTT_Subscriber':
            create_link('callLink', self.parent.kbObject, kbObject, position)
            log.info('Create link ' + str(self.parent) + ' and ' + self.name + ' ' + self.metal_type)
        else:
            log.info('Subcriber: ' + self.name)

        return kbObject

        
class Publisher(MQTTClient):
    pass

class Subscriber(MQTTClient):
    pass

class Connection(MQTTClient):
    pass

class MQTT:

    def __init__(self):
        self.is_mqtt = False
        self.mqtt_methods = []
        self.mqtt_events = []

        self.subscribers = []
        self.publishers = []
        self.connections = []

    def set_infos(self, parsingResult):
        if parsingResult.mqtt_require:
            self.is_mqtt = parsingResult.mqtt_require

        self.mqtt_methods.extend(parsingResult.mqtt_methods)

        self.mqtt_events.extend(parsingResult.mqtt_events)


    def is_mqtt_method(self, callPart):
        try:
            identifier = callPart.identifier_call
            resolution = identifier.get_resolutions()[0]

            parent_id = resolution.callee.parent
            
            if not parent_id.is_assignment():
                return None

            right_operation = parent_id.get_right_operand()

            if not right_operation.is_function_call():
                return None
            
            _callPart = right_operation.get_function_call_parts()[0]
            
            param = _callPart.get_parameters()[0]

            if _callPart.get_name() == 'require' and param.get_text() == 'mqtt':
                return callPart
            
            elif _callPart.get_name() in ['connect', 'store', 'client']:
                return self.is_mqtt_method(_callPart)
                               
        except:
            log.debug('is mqtt method-------')
            return None

        return None

    def get_subscriber(self, connection):
        res = []
        for subscriber in self.subscribers:
            if same_position(subscriber.get_position_connection(), connection):
                res.append(subscriber)
        
        return res

    def get_publisher(self, connection):
        res = []
        for publisher in self.publishers:
            if same_position(publisher.get_position_connection(), connection):
                res.append(publisher)
        
        return res

    def get_connection(self, pos_connection):
        try:
            for connection in self.connections:
                if same_position(connection.position(), pos_connection):
                    return connection

        except:
            return None
        
        return None     

    def resolve_sender(self, callPart, file):
        try:
            # Return a connection for instance.
            mqtt_obj = self.is_mqtt_method(callPart)
            
            if not mqtt_obj:
                return
            
            param = callPart.get_parameters()[0]
            parent = callPart
            while not parent.is_function() and not parent.is_js_content():
                parent = parent.parent

            if callPart.get_name() == 'connect':
                self.connections.append(Connection(parent, callPart, param.get_text(), file, 'CAST_NodeJS_MQTT_Connection'))
                return

            pos_connection = mqtt_obj.create_bookmark(file) 
            connection = self.get_connection(pos_connection)

            if 'subscribe' in callPart.get_name():
                self.subscribers.append(Subscriber(parent, callPart, param.get_text(), file, 'CAST_NodeJS_MQTT_Subscriber', connection))

            elif 'publish' in callPart.get_name():
                self.publishers.append(Publisher(parent, callPart, param.get_text(), file, 'CAST_NodeJS_MQTT_Publisher', connection))

        except:
            log.warning('from MQTT sender resolution:' + str(callPart))

    def resolve_event(self, callPart, file):
        try:
            # Return a connection for instance.
            mqtt_obj = self.is_mqtt_method(callPart)

            if not mqtt_obj:
                return

            param = callPart.get_parameters()[0]
            function = callPart.get_parameters()[1]
            
            if param.get_text() not in ['message'] or not function.is_function():
                return

            pos_connection = mqtt_obj.create_bookmark(file)

            subs = self.get_subscriber(pos_connection)
            for sub in subs:
                if sub.kbObject:
                    create_link('callLink', sub.kbObject, function.kbObject)
                    log.info('create link between ' + sub.name + ' subscriber and ' + function.get_name() + ' event')

        except:
            log.warning('from MQTT event resolution:' + str(callPart))

    def compute(self):
        if not self.is_mqtt:
            return

        for mqtt_method in self.mqtt_methods:
            self.resolve_sender(mqtt_method[0], mqtt_method[1])
            
        for mqtt_event in self.mqtt_events:
            self.resolve_event(mqtt_event[0], mqtt_event[1])

