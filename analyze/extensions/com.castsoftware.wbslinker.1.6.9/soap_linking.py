from cast.application import ApplicationLevelExtension, create_link, Bookmark
import cast_upgrade_1_5_25 # @UnusedImport
import logging
import traceback
from collections import defaultdict



def get_linking_key(fullname, name):
    
    parent_name = fullname[:-len(name)-1].split('.')
    return    parent_name[-1] + '.' + name 


class ServiceCall:
    """
    Client side
    """
    def __init__(self, key, o=None):
        """
        :param key: porttype.operation
        :param o: kb object representing the service (may be None for tests) 
        """
        self.key = key
        self.object = o
    
    
class Service:
    """
    Server side
    """
    def __init__(self, fullname, name, o=None):
        """
        :param fullname: fullname of the service
        :param name: name of the service
        :param o: kb object representing the service (may be None for tests) 
        """
        self.fullname = fullname
        self.name= name
        self.object = o
        
def link(service_calls, services):
    """
    :param service_calls: list of ServiceCall
    :param services: list of Service
    
    :return: list of couple service_call, service for links
    """
    services_map = defaultdict(list)
    
    for service in services:
        
        fullname = service.fullname
        name = service.name
        logging.info('registering key %s', get_linking_key(fullname, name))
        services_map[get_linking_key(fullname, name)].append(service)
        
    
    result = []
    
    for call in service_calls:
        
        key = call.key
        if key:
            logging.info('Searching for key %s', key)
            try:
                for service in services_map[key]:
                    logging.info('creating link')
                    result.append((call, service))
            except:
                pass
        
    return result


    
class ExtensionApplication(ApplicationLevelExtension):

    def end_application(self, application):

        logging.info('Linking SOAP services')

        # load calls
        service_calls = [ServiceCall(call.get_property('CAST_SOAP_OperationCall.operationFullName'), 
                                     call) for call in application.objects().has_type('CAST_SOAP_OperationCall').load_property('CAST_SOAP_OperationCall.operationFullName')]

        if not service_calls:
            # nothing to link...
            return
        
        # load services
        services = [Service(service.get_fullname(), 
                            service.get_name(), 
                            service) for service in application.objects().has_type('CAST_SOAP_Operation')]
        
        if not services:
            # nothing to link...
            return
        
        # main
        links = link(service_calls, services)
        
        # create links
        for call, service in links:
            
            create_link('callLink', call.object, service.object)
        
        
