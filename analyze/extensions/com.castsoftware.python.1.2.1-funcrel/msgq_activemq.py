from light_parser import Walker

from cast.analysers import Bookmark , log
import cast.analysers
import msgq_basics


""" This file analyses ActiveMQ python code"""

def analyse(module):
    """
    Analyse a module code for ActiveMQ analysis 
    
    :type module: symbols.Module 
    
    mode should be resolved and parsed
    """
    walker = Walker()
    walker.register_interpreter(ActiveMQ(module))
    walker.walk(module.get_ast())
    

class ActiveMQ (msgq_basics.Message_Queue):
   
    def __init__(self, module):
        
        msgq_basics.Message_Queue.__init__(self, module)
        
        self.queue_type = None                     #metamodel type of queue        
        self.msgq_imports = ['stomp']              #List of imports specific to ActiveMQ
        self.import_flag = self.check_msgq_import()
        
    def check_msgq_import(self):
        """
        Method to check presence of imports specific to ActiveMQ
        If the import is present, return True else False
        """
        queue_imports = self.module.get_imports()
        
        for child in queue_imports:
            
            tokens = child.get_children()
            tokens.move_to("import")
            token  = next(tokens)
            
            if token.text in self.msgq_imports:
                return True    
   
        return False 
            
            
    def start_MethodCall (self, method_call):
        """
        This method gets called for every method_call in source code.
            :param method_call: ast of python_parser.MethodCall
            
        This method performs following tasks:
        > Checks the method_name:'subscribe' or 'send'
        
        > Calls parameterisation() function from msgq_basics file to get queue name
        
        > If queue name is not None:
        > Assigns the role and queue object type based on the method_name:
        	'subscribe': role='consumer', queue_obj_type='CAST_ActiveMQ_Python_QueueCall' 
        	'send'     : role='producer', queue_obj_type='CAST_ActiveMQ_Python_QueueReceive'
        
        > Calls check_caller() method from msgq_basics module to get caller_object of queue
        		
        > Calls create_queue_object method() from msgq_basics module to create queue call/queue receive objects and links
        """
        if self.import_flag :           # If the file is message queue, then only proceed ahead with the method calls
            
            method = method_call.get_method()           #get the method from method_call
            try :
                method_name = method.get_name()             #get the name of the method
            except AttributeError :
                return
            
            if method_name not in ['subscribe','send'] :  # If required methods are not found, then dont proceed with paramterization  
                return
            
            self.queue_name = msgq_basics.parametrisation(method_call= method_call, keyword= 'destination', index_position= 0)   #invokes parameterisation
        
            if self.queue_name:
                cast.analysers.log.debug('Analysing ActiveMQ')
                
                if method_name == 'subscribe':
                    self.role = 'consumer'
                    self.queue_type = 'CAST_ActiveMQ_Python_QueueReceive'
                
                else:
                    self.role = 'producer'
                    self.queue_type = 'CAST_ActiveMQ_Python_QueueCall'
                
                parent_caller_obj = method_call.parent
                
                self.caller_object = self.obj_creation.check_caller(module= self.module, parent_caller_obj= parent_caller_obj)
        
                parent_object = self.module.get_file()
            
                position = Bookmark(parent_object, 
            					   method_call.get_begin_line(), 
            					   method_call.get_begin_column(), 
            					   method_call.get_end_line(), 
            					   method_call.get_end_column())
            
            
                self.obj_creation.create_queue_object(module = self.module, 
                                                      queue_name = self.queue_name, 
                                                      role= self.role, 
                                                      parent_object = parent_object, 
                                                      caller_object = self.caller_object, 
                                                      queue_obj_type = self.queue_type, 
                                                      position = position, 
                                                      messaging_system = 'ActiveMQ')
            
            return