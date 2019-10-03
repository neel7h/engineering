"""
Linking for message queue.

"""
from cast.application import ApplicationLevelExtension, create_link
import logging
from collections import defaultdict
import re


class ServiceCall:
    """
    Client side
    """
    def __init__(self,sender_exchange_name,routing_key,sender_ex_type,o=None):
        """
        :param sender_exchange_name: name of the exchange to which sender sends msg to
        :param routing_key: Routing key of msg
        :param sender_ex_type: Type of exchange at sender
        :param o: kb object representing the service (may be None for tests) 
        """
        
        self.sender_exchange_name = sender_exchange_name
        self.sender_exchange_type = sender_ex_type
        self.routing_key = routing_key
        self.object = o
    
       
class Service:
    """
    Server side
    """
    def __init__(self,exchange_name,exchange_type,binding_key,o=None):
        """
        :param exchange_name: exchange name at receiver
        :param exchange_type: type of exchange at receiver
        :param binding_key: binding key of queue
        :param o: kb object representing the service (may be None for tests) 
        """
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type
        self.binding_key = binding_key
        self.object = o
        
        
def link(service_calls, services):
    """
    :param service_calls: list of ServiceCall
    :param services: list of Service
    
    :return: list of couple service_call, service for links
    """
    services_map = defaultdict(list)

    for service in services:
        logging.info("service for loop" + str(service))
        exchange_name = service.exchange_name
        exchange_type = service.exchange_type
        binding_key = service.binding_key
        
        services_map[exchange_name].append((exchange_type,binding_key,service))
        logging.info("services map " + str(services_map))
        
    
    result = []

    logging.info('resolving %s queue calls...', len(service_calls))
    number_of_resolved = 0
    
    for call in service_calls:
      
        key = call.sender_exchange_name
        routingkey = call.routing_key
        ex_type = call.sender_exchange_type
        
        
        if key:
            logging.debug('Searching for key %s', key)
            
            resolved = False
            
            called_queues = set()            
           
            try:
                for service in services_map[key]:                    
                    
                    if service[0] == "default-exchange":
                        if ex_type == "default-exchange" and routingkey == service[1]:
                            logging.debug('creating link')
                            result.append((call, service[2]))
                            called_queues.add(service[2])
                            
                    if service[0] == "direct-exchange" and service[1] == routingkey:
                        if ex_type == "undefined" or ex_type == service[0]:                       
                                logging.debug('creating link')
                                result.append((call, service[2]))
                                called_queues.add(service[2])
                        
                                
                    elif service[0] == 'fanout-exchange':
                        if ex_type == "undefined" or ex_type == service[0]:
                            result.append((call,service[2]))
                            called_queues.add(service[2])
                            
                         
                    elif service[0] == 'topic-exchange':
                        if ex_type == "undefined" or ex_type == service[0]:
                            pattern = service[1]
                            pattern = pattern.split('.')
                            for index,val in enumerate(pattern):
                                if val == '*':
                                    if index == 0:
                                        pattern[index] = '^\\w+'
                                    elif index == len(pattern)-1:
                                        pattern[index] = '\\w+$'
                                    else:
                                        pattern[index] = '\\w+'
                                elif val == '#':
                                    pattern[index] = '(\w+|\.)*'
                                    
                            final_pattern = re.compile('\\.'.join(pattern))
                            if final_pattern.match(routingkey):                               
                                logging.debug('creating topic link')
                                result.append((call, service[2]))
                                called_queues.add(service[2])
                            
 
                    
                resolved = True
            except:
                pass
            

    logging.info('resolved %s queue calls out of %s', number_of_resolved, len(service_calls))
    
    return result
    
    
class ExtensionApplication(ApplicationLevelExtension):

    def end_application(self, application):        
        
        service_calls = [ServiceCall(call.get_property('CAST_RabbitMQ_Exchange.exchangeName'), 
                                     call.get_property('CAST_RabbitMQ_Exchange.routingKey'),call.get_property('CAST_RabbitMQ_Exchange.senderExchangeType'),
                                     call) for call in application.objects().has_type('CAST_RabbitMQ_Exchange').load_property('CAST_RabbitMQ_Exchange.exchangeName').load_property('CAST_RabbitMQ_Exchange.routingKey').load_property('CAST_RabbitMQ_Exchange.senderExchangeType')]
        
                
        if not service_calls:
            # nothing to link...
         
            return
        
        services = [Service(service.get_property('CAST_RabbitMQ_Queue.exchangeName'), 
                            service.get_property('CAST_RabbitMQ_Queue.exchangeType'), 
                            service.get_property('CAST_RabbitMQ_Queue.bindingKey'),
                            service) for service in application.objects().has_type('CAST_RabbitMQ_Queue').load_property('CAST_RabbitMQ_Queue.exchangeName').load_property('CAST_RabbitMQ_Queue.exchangeType').load_property('CAST_RabbitMQ_Queue.bindingKey')]
                
        
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
        