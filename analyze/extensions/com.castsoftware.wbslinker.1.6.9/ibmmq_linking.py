"""
Linking for IBM message queue.

"""
from cast.application import ApplicationLevelExtension, create_link
import logging
from collections import defaultdict


class Publisher:
    """
    Client side
    """
    def __init__(self, queue_name, topics, queue_managers, o=None):
        """
        :param queue_name: name of the queu
        :param topics: list of strings
        :param queue_managers: list of strings
        :param o: kb object representing the service (may be None for tests) 
        """
        self.queue_name = queue_name
        self.topics = topics
        self.queue_managers = queue_managers
        self.object = o
    
       
class Receiver:
    """
    Server side
    """
    def __init__(self, queue_name, topics, queue_managers, o=None):
        """
        :param queue_name: name of the queue
        :param topics: list of strings
        :param queue_managers: list of strings
        :param o: kb object representing the service (may be None for tests) 
        """
        self.queue_name = queue_name
        self.topics = topics
        self.queue_managers = queue_managers
        self.object = o
        
        
def link(publishers, receivers):
    """
    :param publishers: list of Publisher
    :param receivers: list of Receiver
    
    :return: list of couple service_call, service for links
    """
    receivers_map = defaultdict(list)

    for receiver in receivers:
        # @type receiver:Receiver
        receivers_map[receiver.queue_name].append(receiver)
       
    
    result = []

    logging.info('resolving %s IBM MQ publishers...', len(publishers))
    number_of_resolved = 0
    
    for publisher in publishers:
        # @type publisher:Publisher
        try:
            
            # first filter by topics 
            receivers_with_compatible_topics = []
            
            point_to_point = False
            if not publisher.topics:
                point_to_point = True
            
            for receiver in receivers_map[publisher.queue_name]:
                # @type receiver:Receiver
                if point_to_point and not receiver.topics:
                    receivers_with_compatible_topics.append(receiver)
                
                elif not point_to_point:
                    
                    for topic in receiver.topics:
                        
                        if topic in publisher.topics:
                            # subscribed to a publiched topic : add it
                            receivers_with_compatible_topics.append(receiver)
                            break # on topics
            
            elligible_receivers = []

            for receiver in receivers_with_compatible_topics:
                # @type receiver:Receiver
                
                if not publisher.queue_managers and not receiver.queue_managers:
                    elligible_receivers.append(receiver)
                    
                else:
                                       
                    for queue_manager in receiver.queue_managers:
                        
                        if queue_manager in publisher.queue_managers:
                            elligible_receivers.append(receiver)
                            break # on queue managers
            
                                                                
            for receiver in elligible_receivers:
                result.append((publisher, receiver))
            
            if elligible_receivers:
                number_of_resolved += 1
            
        except:
            pass

    logging.info('resolved %s queue calls out of %s', number_of_resolved, len(publishers))
    
    return result
    
    
class ExtensionApplication(ApplicationLevelExtension):

    def end_application(self, application):        
        
        try:
            application.get_knowledge_base().metamodel.get_category(name='CAST_IBM_MQ_Publisher')
            application.get_knowledge_base().metamodel.get_category(name='CAST_IBM_MQ_Subscriber')
        except KeyError:
            # we are in a CAIP version that is too old and do not contain those categories : nothing to do
            return
            
        publishers = [Publisher(call.get_property('CAST_IBM_MQ_Publisher.queueName'), 
                                call.get_property('CAST_IBM_MQ_Publisher.topics'),
                                call.get_property('CAST_IBM_MQ_Publisher.queueManagerName'),
                                call) 
                                
                                for call in application.objects().has_type('CAST_IBM_MQ_Publisher').load_property('CAST_IBM_MQ_Publisher.queueName').load_property('CAST_IBM_MQ_Publisher.topics').load_property('CAST_IBM_MQ_Publisher.queueManagerName')]
        
                
        if not publishers:
            # nothing to link...
         
            return
        
        receivers = [Receiver(service.get_property('CAST_IBM_MQ_Subscriber.queueName'), 
                              service.get_property('CAST_IBM_MQ_Subscriber.topics'), 
                              service.get_property('CAST_IBM_MQ_Subscriber.queueManagerName'),
                              service) 
                              
                              for service in application.objects().has_type('CAST_IBM_MQ_Subscriber').load_property('CAST_IBM_MQ_Subscriber.queueName').load_property('CAST_IBM_MQ_Subscriber.topics').load_property('CAST_IBM_MQ_Subscriber.queueManagerName')]
                
        
        # nothing to link
        if not receivers:
            return

        logging.info('Linking IBM message queues')
                
        # main
        links = link(publishers, receivers)
        
        # create links
        for call, service in links:
            create_link('callLink', call.object, service.object)
        
        logging.info('Done')
        