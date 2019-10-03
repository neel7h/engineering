from nodejs_interpreter_framework import NodeJSInterpreterFramework
from cast.analysers import log, Bookmark

list_method_models = ['create',
                      'createEach',
                      'find',
                      'findOne',
                      'update',
                      'destroy',
                      'findOrCreate',
                      'count',
                      'native',
                      'query',
                      'stream',
                      'archive',
                      'addToCollection',
                      'avg',
                      'getDatastore',
                      'removeFromCollection',
                      'replaceCollection',
                      'sum',
                      'validate']

databases_sails = ['sails-postgresql', 'sails-mysql', 'sails-mongo', 'sails-disk']

            
class ServiceSailsInfo:

    def __init__(self, request, uri, controller, action, file):

        self.request = request
        self.uri = uri
        self.controller = controller
        self.action = action
        self.file = file

    
class NodeJSInterpreterSails(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)
        
    def analyser_webservice_method(self, ord_dict):
        if not hasattr(ord_dict, 'get_items_dictionary'):
            return
        
        item_dict = ord_dict.get_items_dictionary()

        request = None
        uri = None
        controller = None
        action = None

        for key, value in item_dict.items():

            if not key.is_identifier():
                continue
            
            infos = key.get_text().split(' ')

            if len(infos) < 2:
                continue
            
            # remove the '' after split from ' '.
            while '' in infos:
                infos.remove('')

            req = infos[0].split('.')[1]  # info[0] = route.request

            if not request and req in ['GET', 'POST', 'PUT', 'DELETE']:
                request = req

            res_split = infos[1].split('.')  # uri.(controller or action)
            
            if len(res_split) < 2:
                continue

            if uri == None:
                uri = res_split[0]

            if not controller and res_split[1] == 'controller':
                controller = value.get_text()
            
            elif not action and res_split[1] == 'action':
                action = value.get_text()

        if request and not uri == None:
            uri = self.normalize_uri(uri)
            sails_infos = ServiceSailsInfo(request, uri, controller, action, self.file)
            self.parsingResults.service_sails.append(sails_infos)

    def analyse_database(self, ord_dict, is_prod):                
        if not hasattr(ord_dict, 'get_items_dictionary'):
            return False
        
        item_dict = ord_dict.get_items_dictionary()

        for key, value in item_dict.items():

            if hasattr(key, 'get_text') and 'adapter' in key.get_text() and\
               hasattr(value, 'get_text') and value.get_text() in databases_sails:

                self.parsingResults.database_sails = (value.get_text(), is_prod)
                return True

            else:
                return self.analyse_database(value, is_prod)

        return False

    def database_search(self, list_method, is_prod):
        # https://sailsjs.com/documentation/concepts/extending-sails/adapters/available-adapters
        if self.parsingResults.database_sails and not self.parsingResults.database_sails[1]:
            return

        for element in list_method:
            if hasattr(element, 'get_text') and element.get_text() in databases_sails:
                self.parsingResults.database_sails = (element.get_text(), is_prod)
                return
            
        for ord_dict in list_method:
            if self.analyse_database(ord_dict, is_prod):
                return

    def analysis_model(self, assign, path_file, right_operand):
        left_operand = assign.get_left_operand()
        if not left_operand.is_identifier():
            return

        name_file = path_file.split('\\')[-1]
        name_file = name_file.replace('.js', '')

        if left_operand.get_text() == 'module.exports' and hasattr(right_operand, 'get_items_dictionary'):
            item_dict = right_operand.get_items_dictionary()
        
            for key, value in item_dict.items():
                if not key.is_identifier():
                    continue
                
                if key.get_text() == 'module.exports.tableName' and hasattr(value, 'get_text'):
                    self.parsingResults.table_name[name_file] = value.get_text()
                
                elif key.get_text() == 'module.exports.adapter' and hasattr(value, 'get_text'):
                    self.parsingResults.adapter_sql[name_file] = value.get_text()
                
                elif hasattr(value, 'is_function') and value.is_function():
                    self.parsingResults.function_sql[name_file].append(value)

        elif left_operand.get_text() == 'self.tableName' and hasattr(right_operand, 'get_text'):
            self.parsingResults.table_name[name_file] = right_operand.get_text()
        
        elif left_operand.get_text() == 'self.adapter' and hasattr(right_operand, 'get_text'):
            self.parsingResults.adapter_sql[name_file] = right_operand.get_text()
        
        elif hasattr(right_operand, 'is_function') and right_operand.is_function():
            self.parsingResults.function_sql[name_file].append(right_operand)
                    
    def start_assignment(self, assign):
        
        if not self.parsingResults.is_node_project:
            return

        path_file = self.file.get_path()
        right_operand = assign.get_right_operand()

        if r'\api\models' in path_file:
            try:
                self.analysis_model(assign, path_file, right_operand)
            except:
                return
            
            return
        '''
        * Resovle config.
        '''

        if not hasattr(right_operand, 'get_items'):
            return

        list_method = right_operand.get_items()
                    
        if r'\config\routes.js' in path_file:
            for ord_dict in list_method:
                self.analyser_webservice_method(ord_dict)

        elif r'\config\env\production.js' in self.file.get_path():
            self.database_search(list_method, True)
                
        elif r'\config\datastores.js' in self.file.get_path() or r'\config\connection.js' in self.file.get_path():
            self.database_search(list_method, False)
            
    def start_function_call(self, fcall):
        try:
            call_name = fcall.get_children()[0]

            if not hasattr(call_name, 'identifier_call'):
                return

            text = call_name.identifier_call.get_text()

            infos = text.split('.')

            if not len(infos) == 2:
                return

            if infos[0] in self.parsingResults.models_sails:
                f_parent = fcall

                while f_parent.parent and hasattr(f_parent, 'is_function') and not f_parent.is_function():
                    f_parent = f_parent.parent

                if not f_parent.is_function() or not f_parent.get_kb_object():
                    f_parent = self.callerInterpreter.jsContent
                
                position = Bookmark(self.file, call_name.get_begin_line(), call_name.get_begin_column(), call_name.get_end_line(), call_name.get_end_column())
                
                sql_method = False
                if infos[1] in list_method_models:
                    sql_method = True

                sql_query = None
                if infos[1] == 'query' and call_name.get_parameters():
                    sql_query = call_name.get_parameters()[0]

                self.parsingResults.model_infos.append((infos[0], infos[1], f_parent, position, sql_query, sql_method))

        except:
            log.warning('Failed in function call of sails framework interpreter')

    def end_function_call(self):
        pass
