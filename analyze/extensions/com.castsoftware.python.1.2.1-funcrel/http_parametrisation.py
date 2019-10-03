"""
Handle http service calls

@todo: find a better strategy (for similar situations in future) to deal with 
  synonyms when creating request objects (see @hack). It should prevent ambiguity in resolution of 'get' etc methods.
  See also the method declare_system() in python_parser.py
"""
from light_parser import Walker
from python_parser import is_method_call, is_assignement, is_dot_access, is_identifier, is_for, is_while
from evaluation import evaluate
import symbols
from cast.analysers import log
from collections import namedtuple


def analyse(module):
    """
    Analyse a module code for searching http calls 
    
    :type module: symbols.Module 
    
    mode should be resolved and parsed
    """
    walker = Walker()
    walker.register_interpreter(HttpInterpreter(module))
    walker.walk(module.get_ast())



class HttpInterpreter:
    
    def __init__(self, module):
        
        self.__module = module
        self.__httpConnectionVariables = {'requests':[], 
                                          'httplib':[], 
                                          'httplib2':[], 
                                          'aiohttp':[], 
                                          'urllib':[],
                                          'urllib2':[],
                                          'http':[]}
        
        self.__variable_to_parameters = {}
        
        self.__symbol_stack = [module]
        
        # the depth of loop
        self.__loop_level = 0 
        
    def push_symbol(self, symbol):
        
        return self.__symbol_stack.append(symbol)

    def pop_symbol(self):

        self.__symbol_stack.pop()

    def get_current_symbol(self):
        
        return self.__symbol_stack[-1]

    def declare_connection_variable(self, framework, variable):
        """
        Stores that a variable is assigned a framework connection object
        """
        self.__httpConnectionVariables[framework].append(variable)
    
    def get_http_variables(self, framework):
        
        return self.__httpConnectionVariables[framework]

    def start_ClassBlock(self, _ast_class):
        """
        Resolve class inheritances
        """
        _class = self.get_current_symbol().get_class(_ast_class.get_name(), _ast_class.get_begin_line())
        if not _class:
            
            log.warning("no class found for %s under %s" % (str(_ast_class.get_name()), str(self.get_current_symbol())))
        
        self.push_symbol(_class)

    def end_ClassBlock(self, _ast_class):
        self.pop_symbol()

    def start_FunctionBlock(self, ast_function):
        self.start_Function(ast_function)

    def start_FunctionOneLine(self, ast_function):
        self.start_Function(ast_function)
        
    def start_Function(self, ast_function):
        """
        @type ast_function: python_parser.Function
        """
        name = ast_function.get_name()
        function = self.get_current_symbol().get_function(name, ast_function.get_begin_line())
        
        if not function:
            
            log.warning("no function found for %s under %s" % (str(name), str(self.get_current_symbol())))
        
        self.push_symbol(function)

    def end_FunctionBlock(self, ast_function):
        self.end_Function(ast_function)

    def end_FunctionOneLine(self, ast_function):
        self.end_Function(ast_function)
        
    def end_Function(self, ast_function):
        self.pop_symbol()

    def start_WithBlock(self, ast):
        self.start_With(ast)

    def start_ForBlock(self, ast):
        self.__loop_level += 1

    def end_ForBlock(self, ast):
        self.__loop_level -= 1
    
    def start_ForOneLine(self, ast):    
        self.__loop_level += 1

    def end_ForOneLine(self, ast):
        self.__loop_level -= 1
    
    # to avoid reporting url call inside the condition of a for/while
    def start_BinaryOperation(self, ast):
        try:
            if is_for(ast.parent) or is_while(ast):
                self.__loop_level -= 1
        except AttributeError:
            pass
            
    def end_BinaryOperation(self, ast):
        try:
            if is_for(ast.parent) or is_while(ast):
                self.__loop_level += 1
        except AttributeError:
            pass
    
    def start_WhileBlock(self, ast):
        self.__loop_level += 1

    def end_WhileBlock(self, ast):
        self.__loop_level -= 1
    
    def start_WhileOneLine(self, ast):    
        self.__loop_level += 1

    def end_WhileOneLine(self, ast):
        self.__loop_level -= 1

    def start_WithOneLine(self, ast):
        self.start_With(ast)
        
    def start_With(self, ast):
        """
        @type ast: With
        """
        identifier = ast.get_identifier()
        expression = ast.get_expression()
        
        self.handle_connection_variable(identifier, expression)

    def start_Assignement(self, assignement):
        """
        Search for connection types
        """
        variable = assignement.get_left_expression()
        method_call = assignement.get_right_expression()
        self.handle_connection_variable(variable, method_call)
    
    def handle_connection_variable(self, variable, method_call):
        if not is_method_call(method_call):
            return
        # constructors of various connection types
        signature_to_framework = {'requests.Session.__init__':'requests',
                                  'requests.session.__init__':'requests',
                                  'requests.sessions.Session.__init__':'requests',
                                  'requests.sessions.session.__init__':'requests',
                                  'httplib.HTTPConnection.__init__':'httplib',
                                  'httplib2.Http.__init__':'httplib2',
                                  'aiohttp.ClientSession.__init__':'aiohttp',
                                  'urllib.request.Request.__init__':'urllib',
                                  'urllib2.Request.__init__':'urllib2',
                                  'http.client.HTTPConnection.__init__':'http',
                                  'http.client.HTTPSConnection.__init__':'http'}
        
        for function in method_call.get_resolutions():
            try:
                framework = signature_to_framework[function.get_qualified_name()]
                self.declare_connection_variable(framework, variable)
                if framework in ['urllib', 'urllib2']:
                    # number of parameters is important :
                    self.__variable_to_parameters[variable] = len(method_call.get_parameters())
            except:
                pass


    def create_web_service_call(self, framework, _type, uri_ast, ast):
        """
        :type ast: python_parser.MethodCall
        """
        type_per_framework = {'requests':symbols.RequestsService,
                              'httplib' :symbols.HttplibService,
                              'httplib2':symbols.Httplib2Service,
                              'aiohttp' :symbols.AiohttpService,
                              'urllib'  :symbols.UrllibService,
                              'urllib2' :symbols.Urllib2Service,
                              # @todo: create new/generic WebService object for http
                              'http'    :symbols.HttplibService}
        
        Rules = namedtuple('Rules', ['service', 'loop']) 

        rules_per_framework = {'requests' : Rules('useOfRequestsWebService', 'requestsWebServiceInsideLoop'),
                               'httplib'  : Rules('useOfHttplibWebService' , 'httplibWebServiceInsideLoop' ),
                               'httplib2' : Rules('useOfHttplib2WebService', 'httplib2WebServiceInsideLoop'),
                               'aiohttp'  : Rules('useOfAiohttpWebService' , 'aiohttpWebServiceInsideLoop' ),
                               'urllib'   : Rules('useOfUrllibWebService'  , 'urllibWebServiceInsideLoop'  ),
                               'urllib2'  : Rules('useOfUrllib2WebService' , 'urllib2WebServiceInsideLoop' ),
                               # draft
                               'http'     : Rules('useOfHttplibWebService' , 'httplibWebServiceInsideLoop' )}
        
        if is_assignement(uri_ast):
            uri_ast = uri_ast.get_right_expression()
        
        # to have same bookmarks on links 
        ast = ast.get_method()
        try:
            ast= ast.get_expression()
        except:
            pass
        
        service = type_per_framework[framework](_type, _type.upper(), uri_ast, ast, self.get_current_symbol().get_fullname())
        self.__module.add_resource_service(service)
        service.caller = self.get_current_symbol()
        
        try:
            rules = rules_per_framework[framework]
        except KeyError:
            return
        
        category = 'CAST_Python_Rule.'
        
        rule = category + rules.service
        self.get_current_symbol().set_property(rule, 1)
        
        if self.__loop_level > 0:
            rule = category + rules.loop
            self.get_current_symbol().add_violation(rule, ast)
    
    
    def get_param_value(self, param):
        """
        This function returns the value of the parameter passed in the method
        Our main aim is to check for the method ssl._create_unverified_context()
        used for disabling certificates
        e.g. urllib2.urlopen(url, context = ssl._create_unverified_context())
        
        > If the parameter passed is a method call then :
            
            >> Get the number of parameters passed in that method call
            >> This  is done because if no argument is passed in method 
               ssl._create_unverified_context() then certification requirement is None
               by default i.e. disabling of certification === > violation
            >> If number of parameters == 0 then extract the full name of the method 
                and return to the calling function
                i.e. ssl._create_unverified_context
            >> If number of paramters > 0 then no need to perform any further check because
              e.g. ssl._create_unverified_context(cert_reqs = ssl.CERT_NONE) or
              Above case will be handled by start_DOTACCESS
        
        > If the parameter passed is just an identifier then return its name 
          to the calling function
        """
        #This condition is when the parameter is a method or function call
        if is_method_call(param):
            method_parameters = len(param.get_parameters())
            if method_parameters == 0:
                method_name = param.get_method().get_name()
                method = param.get_method()
                
                # If the method belongs to some class or module
                # e.g. ssl._create_unverified_context()
                if is_dot_access(method):
                    expr = method.get_expression().get_name()
                    method_name = expr +"." + method_name 
                return method_name
            
        # If the parameter is an identifier then just return the name
        elif is_identifier(param):
            return param.get_name()
        
        return None
    
    def is_certificate_check_disabled_using_context(self, ast_method):
        has_violation = False
        param_value_ls = []
        
        parameters = ast_method.get_parameters()
        # Do further checking only if parameters > 1
        # If only one parameter is given then it is url which is to be opened
        if len(parameters) > 1 :
            
            for param in parameters:
                to_be_decoded = param
                
                if is_assignement(param):
                    to_be_decoded = list(param.get_children())[-1]
                    
                param_value = self.get_param_value(to_be_decoded)
                param_value_ls.append(param_value)
               
            disabling_terms = ['ssl.CERT_NONE', 'ssl._create_unverified_context']
            
            disabling_certificate = self.check_for_common_elements(disabling_terms, param_value_ls)
           
            if disabling_certificate :
                has_violation = True
                        
        return has_violation
        
    def check_for_common_elements(self, banned_ls, actual_ls):
        """
        Returns true if there is at least on common element in both the lists.
        """
        return not set(banned_ls).isdisjoint(set(actual_ls))   

    def start_DotAccess(self, ast_dot_access):
        value = self.get_value(ast_dot_access)
        ssl_constants_for_disabling = ['ssl.CERT_NONE']
        
        if value in ssl_constants_for_disabling :
            self.get_current_symbol().add_violation('CAST_Python_Rule.avoidDisablingCertificateCheckWhenRequestingSecuredURLs', ast_dot_access)
        
    def get_value(self, ast_dot_access):
        value = None
        expr = ast_dot_access.get_expression()
        if is_identifier(expr):
            expr = expr.get_name()
            identifier = ast_dot_access.get_identifier().text
            value = expr + "."+ identifier
        return value

    def is_certificate_check_disabled_using_verify(self, module_name, ast_method):
        """
        :type ast_method: python_parser.MethodCall
        :module_name : Name of the module used for connecting to url
        
        Return type : True/False
        
        > This function scans different methods or different modules 
        > to check for the presence and value of parameter used for disabling ssl certificate check
        
        > Different modules have different parameters. 
            
            >>> Module         Method / Constructor     Parameter              Value for disabling
            ========================================================================================
            >>> aiohttp      TCPConnector()            verify_ssl                       False
            >>> httplib2     Http()              disable_ssl_certificate_validation     True
            >>> requests     get()                        verify                        False
        
        Limitations:
        Ideally, below case should result in a violation but as per the 
        current implementation, value of the parameter verify_param 
        will not be decoded. verify_param will be treated as any value 
        and since it is not equal to False, so this will not result in violation
        
        >>> verify_param = False
        >>> requests.get(url = "www.quora.com", verify = False)
        """
        has_violation = False
        
        parameters = len(ast_method.get_parameters())
                
        # >To use requests.get().... atleast one parameter ie. url is required 
        # >> To disable certificate, explicitly value of optional parameter param
        # >> as False has to be passed. 
        # >> By default verify is True.
         
        # >To use httplib2.Http constructor, no parameter is explicity required
        # >> All the default values are taken.
        # >> Default value for parameter 
        # >> disable_ssl_certificate_validation is False. 
        # >> To disable, value of parameter should be made to True.
        
        # > To use aiohttp.TCPConstructor, no parameter is explicitly requrired
        # >> All the default values will be taken.
        # >> Parameters of checking ssl certificate is verify_ssl, True be default
        # >> To disable, value of parameter should be made to False
        
        if module_name == "requests":
            parameters_threshold = 1
            param_name = "verify"
            bool_value = "False"
        
        elif module_name == "httplib2":
            parameters_threshold = 0
            param_name = "disable_ssl_certificate_validation"
            bool_value = "True"
        
        elif module_name == "aiohttp":
            parameters_threshold = 0
            param_name = "verify_ssl"
            bool_value = "False" 
            
        if parameters > parameters_threshold:
            
            for param in ast_method.get_parameters():
                
                # To deal with argument assignment such as 
                # requests.get(url = "https://...", verify = False)
                if is_assignement(param):
                    verify_param_value = ast_method.get_argument(None, param_name)
                    
                    if verify_param_value and is_identifier(verify_param_value):
                        if verify_param_value.get_name() == bool_value:
                            has_violation = True
                            return has_violation
                        
        return has_violation
    
    def start_MethodCall(self, method_call):
        """
        :type method_call: python_parser.MethodCall
        
        Search various method call names connected to 
        web service libraries. Performs url resolution.
        
        @todo : move url validation to operation.save 
          where @type operation -> WebServerOperation        
        """                
        
        # fully qualified names of that method call
        names = [function.get_qualified_name() for function in method_call.get_resolutions()]
        
        # Checking for disabling of certificates in requests, httplib2 and aiohttp
        module_name = None
        request_methods =  ['requests.get', 'requests.put', 
                            'requests.delete','requests.post',
                            'requests.session.get', 'requests.Session.get',
                            'requests.session.put', 'requests.Session.put',
                            'requests.session.post', 'requests.Session.post',
                            'requests.sessionn.delete', 'requests.Session.delete',]
                               
        
        connection_attempt = self.check_for_common_elements(request_methods, names)
        
        if connection_attempt :
            module_name = "requests"
            
        elif 'httplib2.Http.__init__' in names:
            module_name = "httplib2"
            
        elif 'aiohttp.TCPConnector.__init__' in names:
            module_name = "aiohttp"
        
        if module_name:   
            violation_found = self.is_certificate_check_disabled_using_verify(module_name = module_name,
                                                                              ast_method = method_call)
            if violation_found :
                self.get_current_symbol().add_violation('CAST_Python_Rule.avoidDisablingCertificateCheckWhenRequestingSecuredURLs', method_call)
        
        # Checking for disabling of certificates in urllib2, urllib and http.client 
        methods_using_context = ['urllib2.urlopen', 'urllib.request.urlopen', 'http.client.HTTPSConnection.__init__']
        connection_attempt =  self.check_for_common_elements(methods_using_context, names)
        
        if connection_attempt :
            violation_found = self.is_certificate_check_disabled_using_context(method_call)
            
            if violation_found :
                self.get_current_symbol().add_violation('CAST_Python_Rule.avoidDisablingCertificateCheckWhenRequestingSecuredURLs', method_call)
        
        request_methods = ['requests.Session', 'requests.session', 'requests.sessions.Session', 'requests.sessions.session']
        for fname in ['get', 'post', 'put', 'delete']:
            if any(method+'.'+fname in names for method in request_methods):
                self.create_web_service_call('requests', fname, method_call.get_argument(0, 'url'), method_call)                     
                                        
        # @todo: think if check here the url or later when saving
        if 'httplib2.Http.request' in names:
            if len(method_call.get_parameters()) >= 2:
                param = method_call.get_argument(1, 'method')
                types_ = evaluate(param)
                for type_ in types_:
                    self.create_web_service_call('httplib2', type_.lower(), method_call.get_argument(0, 'uri'), method_call)                   
            elif len(method_call.get_parameters()) == 1:
                self.create_web_service_call('httplib2', 'get', method_call.get_argument(0, 'uri'), method_call)

        http_methods =  ['http.client.HTTPConnection.request', 'http.client.HTTPSConnection.request']
        if any(method in names for method in http_methods):
            types_ = evaluate(method_call.get_argument(0, 'method'))
            for type_ in types_:
                self.create_web_service_call('http', type_.lower(), method_call.get_argument(1, 'url'), method_call)
                                        
        if 'httplib.HTTPConnection.request' in names:
            types_ = evaluate(method_call.get_argument(0, 'method'))
            for type_ in types_:
                self.create_web_service_call('httplib', type_.lower(), method_call.get_argument(1, 'url'), method_call)

        for f_name in ['get', 'post', 'put', 'delete']:
            if 'aiohttp.ClientSession.' + f_name in names:
                arg = method_call.get_argument(0, 'url')
                urls = evaluate(arg)

                url_signatures = ['http', '/']
                                
                valid_urls = []
                for url in urls:                                         
                    if any(url.startswith(s) for s in url_signatures):
                        valid_urls.append(url)                

                if valid_urls:
                    self.create_web_service_call('aiohttp', f_name, arg, method_call)
            
                  
            if 'requests.' + f_name in names:
                self.create_web_service_call('requests', f_name, method_call.get_argument(0, 'url'), method_call)
            
        
        # constructor call to  requests.Request
        if 'requests.Request.__init__' in names and len(method_call.get_parameters()) > 1:
            
            types_ = evaluate(method_call.get_argument(0, 'method'))
            for type_ in types_:
                self.create_web_service_call('requests', type_.lower(), method_call.get_argument(1, 'url'), method_call)

        # urllib.request.urlopen(url, data=None, [timeout, ]*, cafile=None, capath=None, cadefault=False, context=None)  [3.4 - 3.6]
        urllib_methods =  ['urllib.request.urlopen', 'urllib.request.urlretrieve']
        if any(m in names for m in urllib_methods) and method_call.get_parameters():   
            http_method = 'get'  # default

            #[3.3 - 3.6] class urllib.request.Request(url, data=None, headers={}, origin_req_host=None, unverifiable=False, method=None)

            url = method_call.get_argument(0, 'url')
            
            try:
                definition = url.get_resolutions()[0]
            except:
                definition = None
            
            if definition:
                has_method = False
                if is_identifier(definition):
                    
                    try:
                        assignment = definition.parent
                        _method_call = assignment.get_right_expression()
                        method = _method_call.get_method()
                         
                        # we assume urllib.request.Request
                        if method.get_name() == 'Request':
                            http_method = _method_call.get_argument(5,'method').get_string_value()
                            url = _method_call.get_argument(0,'url').get_string_value()
                            has_method = True       
                    except:
                        pass
                    
                if url:
                    if definition in self.get_http_variables('urllib'):
                        
                        if self.__variable_to_parameters[definition] > 1 and not has_method:
                            http_method = 'post'
            
            self.create_web_service_call('urllib', http_method, url, method_call)
                
            
        # urllib2.urlopen(url[, data[, timeout[, cafile[, capath[, cadefault[, context]]]]])    [2.7]
        if 'urllib2.urlopen' in names and method_call.get_parameters():
            
            http_method = 'get'
            
            url = method_call.get_argument(0, 'url') 
            if url and url.get_resolutions():
                definition = url.get_resolutions()[0]
                
                if definition in self.get_http_variables('urllib2'):
                    
                    if self.__variable_to_parameters[definition] > 1:
                        http_method = 'post'
            
            self.create_web_service_call('urllib2', http_method, url, method_call)
    