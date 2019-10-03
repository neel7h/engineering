from nodejs_interpreter_framework import NodeJSInterpreterFramework
from cast.analysers import log

# https://devhints.io/knex
knex_method = ['save', 'destroy', 'query', 'fetch', 'insert', 'update', 'del', 'select',
               'join', 'where', 'distinct']

book_self = ['bookshelf', 'Bookshelf']

class NodeJSInterpreterKnex(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)



    def start_function_call(self, fcall):
        try:
            callParts = fcall.get_function_call_parts()
            callPart = callParts[0]
            
            if fcall.is_require():
                param = callPart.get_parameters()[0]
                if param.get_text() == 'knex':
                    self.parsingResults.knex_require = True
                    self.parsingResults.knex_config = callPart.get_other_parameters()[0][0]

                if param.get_text() == 'bookshelf':
                    self.parsingResults.bookshelf_require = True

            identifier = callPart.identifier_call
            
            resolutions = identifier.get_resolutions()
                     
            # should be list of identifier or function_call(missing info)
            if not resolutions:
                return
            
            prefix = identifier.get_prefix()
            if prefix in knex_method or \
                len(callParts) >= 2 and callParts[1].get_text() in knex_method:
                self.parsingResults.model_knex_infos.append(callParts)
        
        except:
            log.warning('warning from knew interpreter')
        
    def start_assignment(self, assign):
        pass

    def end_function_call(self):
        pass
