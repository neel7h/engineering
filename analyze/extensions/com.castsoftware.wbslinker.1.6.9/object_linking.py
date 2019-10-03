"""
Linking for message queue.

"""
from cast.application import ApplicationLevelExtension, create_link
import logging
from collections import defaultdict


def get_linking_key(name, rcvsystem):
    
    if rcvsystem:
        return rcvsystem + '.' + name
    else:
        return '.' + name 


class ServiceCall:
    """
    Client side
    """
    def __init__(self, key, system, o=None):
        """
        :param key: name of the queue
        :param system: 'RabbitMQ', 'ActiveMQ', ...
        :param o: kb object representing the service (may be None for tests) 
        """
        self.key = key
        self.object = o
        self.system = system
    
    
class Service:
    """
    Server side
    """
    def __init__(self, fullname, name, rcvsystem, o=None):
        """
        :param fullname: fullname of the service
        :param name: name of the queue
        :param rcvsystem: 'RabbitMQ', 'ActiveMQ', ...
        :param o: kb object representing the service (may be None for tests) 
        """
        self.fullname = fullname
        self.name= name
        self.rcvsystem = rcvsystem 
        self.object = o
        
        
def link(service_calls, services):
    """
    :param service_calls: list of ServiceCall
    :param services: list of Service
    
    :return: list of couple service_call, service for links
    """
    services_map = defaultdict(list)
    
    # only with queue name
    all_service_by_queue_name = defaultdict(list)
    
    for service in services:
        
        name = service.name
        rcvsystem = service.rcvsystem
        logging.debug('registering key %s', get_linking_key(name, rcvsystem))
        services_map[get_linking_key(name, rcvsystem)].append(service)
        all_service_by_queue_name[name].append(service)
    
    logging.info('registering %s queue receivers...', len(services))
    
    result = []

    logging.info('resolving %s queue calls...', len(service_calls))
    number_of_resolved = 0
    
    for call in service_calls:
        
        key = get_linking_key(call.key, call.system)
        
        if key:
            logging.debug('Searching for key %s', key)
            
            resolved = False
            
            called_queues = set()
            
            # first try using queue system             
            try:
                for service in services_map[key]:
                    
                    logging.debug('creating link')
                    result.append((call, service))
                    called_queues.add(service)
                    
                resolved = True
            except:
                pass
            
            # second try using anonymous queue system
            if call.system:
                key = '.' + call.key
                try:
                    for service in services_map[key]:
                        
                        logging.debug('creating link')
                        result.append((call, service))
                    
                    resolved = True
                except:
                    pass
            else: 
                # calling with no system name : using queue name only
                try:
                    for service in all_service_by_queue_name[call.key]:
                        
                        if service not in called_queues: # to avoid linking twice
                            logging.debug('creating link')
                            result.append((call, service))
                    
                    resolved = True
                except:
                    pass
            
            if resolved:            
                number_of_resolved += 1
            
    

    logging.info('resolved %s queue calls out of %s', number_of_resolved, len(service_calls))
    
    return result
    
    
class ExtensionApplication(ApplicationLevelExtension):

    def end_application(self, application):
        
        service_calls = [ServiceCall(call.get_property('CAST_MQE_QueueCall.queueName'), 
                                     call.get_property('CAST_MQE_QueueCall.messengingSystem'), 
                                     call) for call in application.objects().has_type('CAST_MQE_QueueCall').load_property('CAST_MQE_QueueCall.queueName').load_property('CAST_MQE_QueueCall.messengingSystem')]

        
        
        if not service_calls:
            # nothing to link...
           
            return
        
        # load services
        services = [Service(service.get_fullname(), 
                            service.get_name(), 
                            service.get_property('CAST_MQE_QueueReceive.messengingSystem'),
                            service) for service in application.objects().has_type('CAST_MQE_QueueReceive').load_property('CAST_MQE_QueueReceive.messengingSystem')]
        
        # nothing to link
        if not services:
            return

        logging.info('Linking message queues')
                
        # main
        links = link(service_calls, services)
        
        # create links
        for call, service in links:
            create_link('callLink', call.object, service.object)
        
        logging.info('Done')
        