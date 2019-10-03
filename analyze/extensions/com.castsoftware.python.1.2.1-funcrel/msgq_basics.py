import cast.analysers
from cast.analysers import CustomObject, create_link
from python_parser import is_method, FunctionBlock, is_identifier, is_constant 
from symbols import Module
from evaluation import evaluate


class Message_Queue:
    """
    This class is a base class for different message queue systems.
    """
    
    def __init__(self, module):
        
        self.module = module        
        self.role = None  # role of MQ method call - producer/consumer
        self.queue_name = None  # message queue name
        self.caller_object = None  # caller object of queue    
        
        self.obj_creation = Queue_Object_Creation()  # Composition
        self.msgq_imports = []  # List of imports specific to ActiveMQ


def parametrisation(method_call, keyword , index_position):
    """
    This function performs parameterisation of MQ method calls(ActiveMQ/RabbitMQ)
       :param method_call : MQ method call((ActiveMQ-send/subscribe)/(RabbitMQ - basic_publish/basic_consume))
       :param keyword : MQ keyword associated with queue name in method_call
       
           >For ActiveMQ, the keyword is "destination"
           >For RabbitMQ, the keyword  "routing_key" / "queue"
           
       :param index_position : position of the argument containing the queue name in the method_calls
       
       
    > Get the queue parameter using keyword. If the keyword is not present, get the queue parameter via position
    > Check if the queue parameter is a Constant/Identifier
        > If it is a Constant, get the string value
        > If it is an Identifier, use evaluate to get the queue name
        
    """
    queue_argument = method_call.get_argument(None, keyword)  # fetching the queue parameter by keyword
  
    if queue_argument is None and len(method_call.get_parameters()) > 0 :
        queue_argument = method_call.get_parameters()[index_position]  # fetch the queue parameter by position
      
    elif queue_argument is None :
        cast.analysers.log.info('Queue is not defined')
        return 
    
    if is_constant(queue_argument):
        queue_name = queue_argument.get_string_value()
        
    elif is_identifier(queue_argument):
        queue_name = str(evaluate(queue_argument)).strip('[]').strip('\'')
        
    return queue_name
 
 
class Queue_Object_Creation:
    """
    This class checks the caller object of queues and creates Queue Call and Queue Receive objects and links.
    """
    
    def __init__(self):
        self.caller = None  # caller object of queue
      
    def check_caller(self, module, parent_caller_obj): 
        """ 
        This method gives the caller object of queue.
        :param module : current file
        :param parent_caller_obj : immediate parent of ActiveMQ\RabbitMQ queue method_call
        
        > The immediate parent of the method_call is obtained and is checked if it is a method/function/module.
            
            > If the parent is a function, get the function object using get_function() passing parent_caller object's name 
              and begin line
            > If the parent is a method, then the method object is obtained by invoking the method - get_function_object() 
              with its arguments as module and parent_caller object name
            > If the parent is a module, get the module object using get_kb_object()
        
        > If the immediate parent is not a function/method/module, then invoke self(i.e - recursive call to check_caller),giving 
         that parent as argument.
        """
        if isinstance(parent_caller_obj, FunctionBlock):  # check if the parent is a function
            
            if is_method(parent_caller_obj):  # check if the parent is a method
                method_obj = self.get_method_object(module , parent_caller_obj.get_name())  # get the method object by invoking the method get_function_objrct()
                self.caller = method_obj.get_kb_object()  # get custom object and assign it to caller
                  
            else:
                func_object = module.get_function(parent_caller_obj.get_name(),
                                                  parent_caller_obj.get_begin_line())  # get the function object
                self.caller = func_object.get_kb_object()  # get custom object and set it as caller object
                
        elif isinstance(parent_caller_obj, Module):  # if the parent is a Module
            self.caller = parent_caller_obj.get_kb_object()  # get custom object
        
        else:
            self.check_caller(module, parent_caller_obj.parent)  # recursive call
            
        return self.caller  # return caller object of queue
    
    def get_method_object(self, module, method_name):
        
        """
        This method is invoked to get the method objects that are the caller objects of queue
        :param module : current module
        :param function_name : name of the function whose object is to be obtained
        
        > Get all the classes of module
        > Get all the functions of the classes.
            > If the name of the function matches with the one passed as argument(function_name), then return that function 
        
        """
        class_objects = module.get_all_symbols()
        method_object = [method_obj for class_object in class_objects \
                         for method_obj in class_object.get_all_symbols() \
                         if method_obj.get_name() == method_name]
        
        return method_object[0]
    
    def create_queue_object(self, module, queue_name, role, parent_object, caller_object, queue_obj_type, position, messaging_system=None):
        """
        This method creates 
        > Queue Call and Queue Receive object
        > Call link between Queue Call/Queue Receive objects and their respective parent caller objects.
        
        :param queue_name: name of the queue obtained from parametrisation
        :param role: role of the module- Producer/Consumer
        :param parent_object: file object (file containing the queue method call)
        :param caller_object: method/function/module enclosing calling the queue method call.
        :param queue_obj_type: type of queue object to be created, that is defined in metamodel
        :param position: position of the queue method call
        :param messaging_system: RabbitMQ/ActiveMQ or None
        
        > Queue Call/Queue Receive objects are created with name as queue_name and type as queue_obj_type
        > If the role is 'producer'
            > Set the properties - queueName and messenging_system for the category CAST_MQE_QueueCall
            > create callLink from  caller object to queue call object
        
        > If the role is 'consumer'
            > Set the properties - queueName and messenging_system for the category CAST_MQE_QueueReceive
            > create callLink from queue receive object to caller object
        """
            
        fullname = parent_object.get_fullname() + '\\' + queue_name
        guid = module.get_final_guid(fullname)
        library = module.get_library()
        
        queue_object = CustomObject()
        queue_object.set_name(queue_name)
        queue_object.set_type(queue_obj_type)
        queue_object.set_parent(parent_object)
        queue_object.set_fullname(fullname)
        queue_object.set_guid(guid)
        queue_object.save()
         
        queue_object.save_position(position)
        
        if messaging_system == "ActiveMQ":
            library.nbActiveMQ_queue_objects += 1
            
        if messaging_system == "IBMMQ":
            library.nbIBMMQ_queue_objects += 1

        if role == "producer":
            queue_object.save_property('CAST_MQE_QueueCall.messengingSystem', messaging_system)  # set the messaging system
            queue_object.save_property('CAST_MQE_QueueCall.queueName', queue_name)
            create_link("callLink", caller_object, queue_object, position)
        
        elif role == 'consumer':
            queue_object.save_property('CAST_MQE_QueueReceive.messengingSystem', messaging_system)  # set the messenging system:activemq/rabbitmq.
            queue_object.save_property('CAST_MQE_QueueReceive.queueName', queue_name)  # set the queuename as property.This property is set to match the queuename of queuecall and queuereceive object at application level.
            create_link("callLink", queue_object, caller_object, position)
             
        if messaging_system is None:
            cast.analysers.log.debug("Messaging system was not found. Queue call-Queue Receive links are created based on queue name matching only")
    
