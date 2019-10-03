from cast.analysers import Bookmark, CustomObject, create_link
from light_parser import Walker
import msgq_basics
import cast.analysers


"""This file analyses RabbitMQ python code"""

def analyse(module):
    """

    Analyse a module code for RabbitMQ analysis 
    
    :type module: symbols.Module 
    
    mode should be resolved and parsed
    """
    walker = Walker()
    walker.register_interpreter(RabbitMQ(module))     #registering RabbitMQ_Python class
    walker.walk(module.get_ast())

class RabbitMQ (msgq_basics.Message_Queue):   
     
    def __init__(self, module):
        
        msgq_basics.Message_Queue.__init__(self, module)
        
        self.msg_queue_imports = ['pika']
        self.import_flag = self.check_msgq_import()
        self.rabbitmq_methodcalls = ['basic_consume', 'basic_publish', 'exchange_declare', 'queue_bind']                 #list containing rabbitmq method names
        self.exchange_dict = {}                          
        
        self.queue_bind_dict = {}
        self.exchange_map = {'fanout': 'fanout-exchange', 'topic':'topic-exchange', 'direct':'direct-exchange', 'default-exchange':'default-exchange'}
                
        
    def check_msgq_import(self):
        
        """
        Method to check presence of imports specific to RabbitMQ
        If the import is present, self.import_flag is set as True
        """
        
        queue_imports = self.module.get_imports()
        
        for child in queue_imports:
            
            tokens = child.get_children()
            tokens.move_to("import")
            token  = next(tokens)
            
            if token.text in self.msg_queue_imports:
                return True    
   
        return False 
    
    def start_MethodCall (self, method_call):      
    
        """       
        This method gets called for every method_call in source code.
            :param method_call: python_parser.MethodCall
            
        This method performs following tasks:
        > Checks the method_name:'basic_publish' or 'basic_consume' or 'exchange_declare' or 'queue_bind'
        > Invokes parameterisation() function from msg_param_obj_crtn file to 
          get exchange name, exchange type, routing key/binding key and queue name
        > Invokes check_caller() method from msg_param_obj_crtn file to get caller_object of queue/exchange        
        > Calls create_queue_object() method and create_exchange_object() to create exchange object and queue object 
          and links
                
         """ 
         
        binding_key = None        
        consumer_queue = None
        
        
        
        if self.import_flag :   # If the file is message queue, then only proceed ahead with the method calls
            
            method = method_call.get_method()     #get the method from method_call
            
            try :
                method_name = method.get_name()       #get the name of the method
            except AttributeError :
                return 
            
            if method_name not in self.rabbitmq_methodcalls :     # If required methods are not found, then dont proceed with paramterization
                return
            
            cast.analysers.log.debug('Analyzing RabbitMQ')
            if method_name == 'exchange_declare':                
                exchange_name = msgq_basics.parametrisation(method_call = method_call, 
                                                         keyword = 'exchange', 
                                                         index_position = 0)
                exchange_type = msgq_basics.parametrisation(method_call = method_call, 
                                                         keyword = 'exchange_type', 
                                                         index_position = 1)
                
                '''store exchange type and exchange name in a dictionary'''
                
                if exchange_name and exchange_type:
                    if exchange_name not in self.exchange_dict:
                        self.exchange_dict[exchange_name] = exchange_type                    
                
            
            if method_name == 'basic_publish':
                sender_dict = {}
                sender_exchange = None
                routing_key = None
                sender_exchange = msgq_basics.parametrisation(method_call = method_call, 
                                                         keyword = 'exchange', 
                                                         index_position = 0)
                routing_key = msgq_basics.parametrisation(method_call = method_call, 
                                                         keyword = 'routing_key', 
                                                         index_position = 1)
                
                if routing_key.strip() == '':
                    routing_key = 'undefined'
                    
                    
                if sender_exchange is not None and routing_key is not None:
                
                    if sender_exchange.strip() == '':
                        sender_exchange_type = "default-exchange"
                        sender_exchange = "default_exchange"
                        
                    else:                    
                        if self.exchange_dict is not None:
                            sender_exchange_type = self.exchange_dict[sender_exchange]
                            
                    if sender_exchange_type:                            
                        sender_dict[sender_exchange] = (routing_key, self.module, method_call, self.exchange_map[sender_exchange_type])                      
                        self.create_exchange_object(sender_dict)
                        
                
            if method_name=='queue_bind':
                recv_exchange = msgq_basics.parametrisation(method_call = method_call, 
                                                         keyword = 'exchange', 
                                                         index_position = 0)
                recv_queue = msgq_basics.parametrisation(method_call = method_call, 
                                                         keyword = 'queue', 
                                                         index_position = 1)
                try:
                    binding_key = msgq_basics.parametrisation(method_call = method_call, 
                                                             keyword = 'routing_key', 
                                                             index_position = 2)
                except:
                    pass
                
                
                if recv_exchange and recv_queue:
                    if self.exchange_dict:
                        recv_exchange_type = self.exchange_dict[recv_exchange]
                        if recv_exchange_type == 'fanout':
                            binding_key = 'undefined'
                     
                        '''store queue-exchange biding details in a dictionary'''
                    
                        if recv_queue not in self.queue_bind_dict:
                            self.queue_bind_dict[recv_queue] = []
                            
                        self.queue_bind_dict[recv_queue].append((recv_exchange,self.exchange_map[recv_exchange_type],binding_key))
                             
                 
            if method_name == 'basic_consume':
                receiver_dict = {}
                consumer_queue = msgq_basics.parametrisation(method_call = method_call, 
                                                         keyword = 'queue', 
                                                         index_position = 1)
                
                if consumer_queue is not None:
                    if self.queue_bind_dict is not None and consumer_queue in self.queue_bind_dict:
                        
                        exch_details = self.queue_bind_dict[consumer_queue]
                    else:
                        exch_details = [("default_exchange","default-exchange", consumer_queue)]
                       
                    receiver_dict[consumer_queue] = (exch_details,self.module,method_call)                    
                    self.create_queue_object(receiver_dict)
        return 
    
    
    def create_exchange_object(self, sender_dict):
        """
        This method creates 
        > RabbitMQ exchange object        
        > Call link between RabbitMQ exchange objects and their respective parent caller objects.
        
        :param sender_dict: dictionary containing exchange details at the sender side
        
        The structure of sender_dict:
        
        sender_dict = {exchange_name1: (routing_key_1, module1, method_call_1, exchange_type_1),                                        
                       exchange_name2: (routing_key_1, module1, method_call_1, exchange_type_1),...}
                
        > The following properties are set on exchange object - 
            exchange name, routing key, exchange type        
        
        """
        
        for exchange in sender_dict:
            module = sender_dict[exchange][1]
            
            parent_object = module.get_file()                
            library = module.get_library()
            methodCall = sender_dict[exchange][2]
            
            position = Bookmark(parent_object, 
                               methodCall.get_begin_line(), 
                               methodCall.get_begin_column(), 
                               methodCall.get_end_line(), 
                               methodCall.get_end_column())
            
            exchange_object = CustomObject()            
            exchange_object.set_name(exchange)                 
            exchange_object.set_parent(parent_object)
            exchange_object.set_type('CAST_RabbitMQ_Python_Exchange')
            exchange_object.save()
            exchange_object.save_position(position)
            
            library.nbRabbitMQ_queue_objects += 1
            
            cast.analysers.log.debug("RabbitMQ exchange object created "  + str(exchange_object))
            caller_obj = methodCall.parent
            caller_object = self.obj_creation.check_caller(module,caller_obj)
            
            link = create_link('callLink',caller_object, exchange_object, position)
            cast.analysers.log.debug("Link " + str(link) + " created between exchange object and caller")
            
            exchange_object.save_property('CAST_RabbitMQ_Exchange.exchangeName', exchange)
            exchange_object.save_property('CAST_RabbitMQ_Exchange.senderExchangeType', sender_dict[exchange][3])
            exchange_object.save_property('CAST_RabbitMQ_Exchange.routingKey', sender_dict[exchange][0])
 
        
        
    def create_queue_object(self, receiver_dict):
        """
        This method creates 
        > RabbitMQ queue object        
        > Call link between RabbitMQ queue objects and their respective parent caller objects.
        
        :param receiver_dict: dictionary containing queue-exchange binding details at the receiver side
        
        The structure of receiver_dict:
        
        receiver_dict = {queue_name1: [([(exchangeName1, exchangeType1, bindingKey1),
                                        (exchangeName2, exchangeType2, bindingKey2),..],
                                        module1, methodCall1),.......]}                                     
                                        
        > The following properties are set on RabbitMQ queue object - 
            exchange name, exchange type, binding key 
        
        """
        
        for queue in receiver_dict:
            for queue_info in receiver_dict[queue][0]:  
                module = receiver_dict[queue][1]        
                parent_object = module.get_file()                
                library = module.get_library()
                methodCall = receiver_dict[queue][2]
                
                position = Bookmark(parent_object, 
                                   methodCall.get_begin_line(), 
                                   methodCall.get_begin_column(), 
                                   methodCall.get_end_line(), 
                                   methodCall.get_end_column())
                
                queue_object = CustomObject()
                queue_object.set_name(queue)
                queue_object.set_type('CAST_RabbitMQ_Python_Queue')
                queue_object.set_parent(parent_object)
                queue_object.save()
                queue_object.save_position(position)
                
                library.nbRabbitMQ_queue_objects += 1
                
                cast.analysers.log.debug("RabbitMQ Queue object created "  + str(queue_object))
                rcv_caller_obj = methodCall.parent
                rcv_caller_object = self.obj_creation.check_caller(module, rcv_caller_obj)
                
                link = create_link("callLink", queue_object, rcv_caller_object, position)
                cast.analysers.log.debug("Link " + str(link) + " created between queue object and caller")
                queue_object.save_property('CAST_RabbitMQ_Queue.exchangeName', queue_info[0])
                queue_object.save_property('CAST_RabbitMQ_Queue.exchangeType', queue_info[1])
                queue_object.save_property('CAST_RabbitMQ_Queue.bindingKey', queue_info[2])
                    
                        
                    
             
