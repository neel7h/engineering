from light_parser import Walker

from cast.analysers import Bookmark, log
import cast.analysers
import msgq_basics

""" This file analyses IBMMQ python code"""


def analyse(module):
    """
    Analyse a module code for IBMMQ analysis 

    :type module: symbols.Module 

    mode should be resolved and parsed
    """
    walker = Walker()
    walker.register_interpreter(IbmMQ(module))
    walker.walk(module.get_ast())


class IbmMQ (msgq_basics.Message_Queue):

    def __init__(self, module):

        msgq_basics.Message_Queue.__init__(self, module)
        self.queue_type = None  # metamodel type of queue
        # List of imports specific to IBMMQ
        self.msgq_imports = ['pymqi', 'mqlight']
        self.import_flag = self.check_msgq_import()
        self.pymqi_dict = {}

    def check_msgq_import(self):
        """
        Method to check presence of imports specific to IBMMQ
        If the import is present, return True else False
        """
        queue_imports = self.module.get_imports()

        for child in queue_imports:

            tokens = child.get_children()
            tokens.move_to("import")
            token = next(tokens)

            if token.text in self.msgq_imports:
                return True

        return False

    def start_MethodCall(self, method_call):
        """
        This method gets called for every method_call in source code.
            :param method_call: ast of python_parser.MethodCall

        This method performs following tasks:
        > Checks the method_name:'subscribe' or 'send'

        > Calls parameterisation() function from msgq_basics file to get queue name

        > If queue name is not None:
        > Assigns the role and queue object type based on the method_name:
                'subscribe': role='consumer', queue_obj_type='CAST_IBMMQ_Python_QueueCall' 
                'send'     : role='producer', queue_obj_type='CAST_IBMMQ_Python_QueueReceive'

        > Calls check_caller() method from msgq_basics module to get caller_object of queue

        > Calls create_queue_object method() from msgq_basics module to create queue call/queue receive objects and links
        """
        if self.import_flag:  # If the file is message queue, then only proceed ahead with the method calls

            method = method_call.get_method()  # get the method from method_call
            try:
                method_name = method.get_name()  # get the name of the method
            except AttributeError:
                return

            # If required methods are not found, then dont proceed with
            # paramterization
            if method_name not in ['subscribe', 'send', 'Queue', 'put', 'get']:
                return

            if method_name == 'Queue':  # In the Pymqi library, Queue definition is in a separate method and Sender/Receiver is in a separate method
                self.queue_name = msgq_basics.parametrisation(
                    method_call=method_call, keyword='queue_name', index_position=1)  # invokes parameterisation
                filename_value = self.module.get_file().get_name()
                self.pymqi_dict[filename_value] = self.queue_name
                return
            # Check if the Queue and the Sender/Receiver are in the same file
            # for Pymqi library
            elif method_name == 'put' or method_name == 'get':
                if self.pymqi_dict is not None and self.module.get_file().get_name() in self.pymqi_dict:
                    self.queue_name = self.pymqi_dict[self.module.get_file(
                    ).get_name()]
                else:
                    return
            else:
                self.queue_name = msgq_basics.parametrisation(
                    method_call=method_call, keyword='destination', index_position=0)

            if self.queue_name:
                cast.analysers.log.debug('Analysing IBM MQ')

                if method_name == 'get' or method_name == 'subscribe':
                    self.role = 'consumer'
                    self.queue_type = 'CAST_IBMMQ_Python_QueueReceive'

                elif method_name == 'put' or method_name == 'send':
                    self.role = 'producer'
                    self.queue_type = 'CAST_IBMMQ_Python_QueueCall'

                parent_caller_obj = method_call.parent

                self.caller_object = self.obj_creation.check_caller(
                    module=self.module, parent_caller_obj=parent_caller_obj)

                parent_object = self.module.get_file()

                position = Bookmark(parent_object,
                                    method_call.get_begin_line(),
                                    method_call.get_begin_column(),
                                    method_call.get_end_line(),
                                    method_call.get_end_column())

                log.info('Creating a ' + self.role + ' object')
                self.obj_creation.create_queue_object(module=self.module,
                                                      queue_name=self.queue_name,
                                                      role=self.role,
                                                      parent_object=parent_object,
                                                      caller_object=self.caller_object,
                                                      queue_obj_type=self.queue_type,
                                                      position=position,
                                                      messaging_system='IBMMQ')

            return
