import cast_upgrade_1_5_25 # @UnusedImport
from cast.application import ApplicationLevelExtension, create_link # @UnresolvedImport
import logging
from urllib.parse import urlparse, parse_qs
from collections import defaultdict


def normalize_url(url):
    """
    Little bit of normalisation.
    """
    if not url:
        return url
    
    result = url
    
    if '?' in url and url[-1] == '/':
        # remove final / wrongly added on url with parameters
        result = result[:-1]
    
    # consider backslashes as slashes, but do not know why
    result = result.replace('\\', '/')
    
    # consider // as /{}/
    result = result.replace('//', '/{}/')
    
    # some simplifications 
    
    # a little basic but will work : remove leading '..' (case of relative urls)
    if result.startswith('..'):
        result = result[2:]   
    
    
    return result.lower() # simpler
    


def get_url_names(url):
    """
    Get all the fragments of an URL path.
    
        path = a/b/c --> returns ['a', 'b', 'c'}
    
    Without parameters, i.e., remove '' and {...}
    
    @todo: remove also {} inside fragments : 
        /public/user{} --> ['public', 'user']
    """
    url = normalize_url(url)
    
    if not url:
        return []
    
    return [element for element in urlparse(url).path.split('/') if element and not(len(element) >= 2 and element[0] == '{' and element[-1] == '}')]


def split_url(url):
    """
    take an URL and returns : 
    
    - the path
    - the parameters, even empty
    
    remove the first and last / of the path
    """
    url = normalize_url(url)
    
    temp = urlparse(url)
    path = temp.path
    if path.startswith('/'):
        path = path[1:]
    if path.endswith('/'):
        path = path[:-1]
    return path, parse_qs(temp.query, keep_blank_values=True)


def url_contains_password(url):
    """
    For quality rule
    
    :param url: str
    """
    parameters = urlparse(url).query
    
    if not parameters:
        return False

    searchStrings = ['password', 'pass', 'pwd']
    
    for key in parse_qs(parameters):
#         print('examining : ', key)
        if key in searchStrings:
            return True


def is_core(call):
    """
    True when a call to url is from CAIP Core
    """
    try:
    
        if call.get_metamodel_type().inherit_from('CAST_WebServiceLinker_Resource'):
            return True
    
    except:
        return False



def get_url_patterns(operation):
    """
    Access to urlPatterns
    """
    try:
        result = operation.get_property('CAST_WebServiceLinker_Operation.urlPatterns')
        if result:
            logging.debug('%s', str(result))
            return result
    except KeyError:
        pass
    return operation.get_property('CAST_WebService_Operation.urlPatterns')


def get_url_patterns_by_kind(operation):
    """
    For an operation returns a triplet 
    - extension mappings, i.e., ['*.do', '*.html']
    - exact matches, i.e., ['MyServlet']
    - path mappings, i.e., ['/path/*']
    
    From : https://download.oracle.com/otn-pub/jcp/servlet-3.0-fr-eval-oth-JSpec/servlet-3_0-final-spec.pdf?AuthParam=1553078757_3f292e68b4f416b9011ad433228e8d51
    Section 12.2
    
        In the Web application deployment descriptor, the following syntax is used to define
        mappings:
        - A string beginning with a ‘/’ character and ending with a ‘/*’ suffix is used for
        path mapping.
        - A string beginning with a ‘*.’ prefix is used as an extension mapping.
        - The empty string ("") is a special URL pattern that exactly maps to the
        application's context root, i.e., requests of the form http://host:port/<contextroot>/.
        In this case the path info is ’/’ and the servlet path and context path is
        empty string (““).
        - A string containing only the ’/’ character indicates the "default" servlet of the
        application. In this case the servlet path is the request URI minus the context path
        and the path info is null.
        - All other strings are used for exact matches only.            
    """
    
    
    extension_mappings = []
    exact_matches = []
    path_mappings = []
    
    url_patterns = get_url_patterns(operation)
    if url_patterns:
        for url_pattern in set(url_patterns.split(';')):
            
            pattern = url_pattern.strip()
            
            # we are interested mostly in those *.x
            if pattern.startswith('*.'):
                extension_mappings.append(pattern)
            elif pattern.endswith('*'):
                path_mappings.append(pattern)
            elif '*' not in pattern:
                exact_matches.append(pattern)
    
    return extension_mappings, exact_matches, path_mappings
    
     



def get_call_url(call):
    """
    Access to url of a web service call 
    """
    try:
        
        result = call.get_property('CAST_ResourceService.uri')
        if result:
            return result 
    except KeyError:
        # not found in core and maybe uri is empty
        pass
    
    return call.get_property('CAST_WebServiceLinker_Resource.uri')





def get_operation_url(opearation):
    
    return opearation.get_name()


def get_rest_action(o):
    """
    Give the 'action' of a service call or receive.
    
    :param o: cast.application.Object
    :return: 'GET', 'PUT', 'POST', 'DELETE', 'ANY'
    """
    # @type o: cast.application.Object
    
    _type = o.get_metamodel_type()
    
    # @type _type: cast.application.internal.metamodel.Category
    try:
        # categories from core available at a certain CAIP version
        if _type.inherit_from('CAST_WebServiceLinker_GetResource') or _type.inherit_from('CAST_WebServiceLinker_GetOperation'):
            return 'GET'
        if _type.inherit_from('CAST_WebServiceLinker_PutResource') or _type.inherit_from('CAST_WebServiceLinker_PutOperation'):
            return 'PUT'
        if _type.inherit_from('CAST_WebServiceLinker_PostResource') or _type.inherit_from('CAST_WebServiceLinker_PostOperation'):
            return 'POST'
        if _type.inherit_from('CAST_WebServiceLinker_DeleteResource') or _type.inherit_from('CAST_WebServiceLinker_DeleteOperation'):
            return 'DELETE'
        if _type.inherit_from('CAST_WebServiceLinker_AnyOperation'):
            return 'ANY'
    except KeyError:
        pass
    
    if _type.inherit_from('CAST_WebService_GetOperation') or _type.inherit_from('CAST_GetResourceService'):
        return 'GET'
    if _type.inherit_from('CAST_WebService_PutOperation') or _type.inherit_from('CAST_PutResourceService'):
        return 'PUT'
    if _type.inherit_from('CAST_WebService_PostOperation') or _type.inherit_from('CAST_PostResourceService'):
        return 'POST'
    if _type.inherit_from('CAST_WebService_DeleteOperation') or _type.inherit_from('CAST_DeleteResourceService'):
        return 'DELETE'
    if _type.inherit_from('CAST_WebService_AnyOperation'):
        return 'ANY'



def is_parameter(url_path_fragment):
    """
    Given an url path fragment, say if it is of the form {...} or empty (objective-c)
    """
    
    if not url_path_fragment:
        return True # special case for objective-c which is very limited in string evaluations

    return  url_path_fragment.startswith('{') and url_path_fragment.endswith('}')


def match_end(call_elements, receive_elements, common_names):
    """
    True when one end is included in the other. 
    
    b/{}, a/b/c
    a/b/{}, b/{}
    etc..; 
            
    """
    # recursion stop
    if not receive_elements:
        return True
    
    # recursion stop
    if not call_elements:
        return True
    
    # compare last elements of list
    call_element = call_elements[-1].lower()        
    receive_element = receive_elements[-1].lower()        
    
    
    # if receive is {}, then keep going
    # if both are equals also
    if (is_parameter(receive_element) and call_element not in common_names) or call_element == receive_element:
        return match_end(call_elements[:-1], receive_elements[:-1], common_names)
    
    # otherwise... 
    return False


def is_exact_path_match(call_url, receive_url, mappings):
    """
    Two URLs are exact match if one path end is included in the other one.
    And both path are not pathologically empty.
    
    Parameters on receiving side are allowed to match anything.
    
    Examples:
        
        'A/B' matches 'X/A/B'
        'A/B' matches 'X/A/{}'
        'A/{}' matches 'X/A/{}'
        'A/{}' do not matches 'X/A/B'
        'X/A/B' matches 'A/B'
         
    :param call_url: str
    :param receive_url: str
    :param mappings: list of str
    """
    extension_mappings = [mapping for mapping in mappings if mapping.startswith('*')]
    path_mappings = [mapping for mapping in mappings if mapping.endswith('/*')]
    
    if not path_mappings:
        
        return is_exact_path_match_2(call_url, receive_url, extension_mappings)
    
    else:
        
        
        
        for path_mapping in path_mappings:
            
            if receive_url.startswith('/'):
                new_receive_url = path_mapping.replace('/*', receive_url)
            else:
                new_receive_url = path_mapping.replace('*', receive_url)
                
            if is_exact_path_match_2(call_url, new_receive_url, extension_mappings):
                return True
        
        return False
    


def is_exact_path_match_2(call_url, receive_url, extension_mappings):
    """
    Two URLs are exact match if one path end is included in the other one.
    And both path are not pathologically empty.
    
    Parameters on receiving side are allowed to match anything.
    
    Examples:
        
        'A/B' matches 'X/A/B'
        'A/B' matches 'X/A/{}'
        'A/{}' matches 'X/A/{}'
        'A/{}' do not matches 'X/A/B'
        'X/A/B' matches 'A/B'
         
    :param call_url: str
    :param receive_url: str
    :param extension_mappings: list of str
    
        
    The last path element of receive_url can be 'replaced' by one of the extension_mappings
    
        call_url: 'xxx/yyy'
        receive_url: 'xxx/yyy.do'
        extension_mappings : ['*.do']
        
        --> will match
    """
    # discard empty like receive urls
    if not get_url_names(receive_url):
        return False

    # discard empty like calling urls
    if not get_url_names(call_url):
        return False
    
    call_path, _ = split_url(call_url)
    receive_path, _ = split_url(receive_url)
    
    
    # to list
    call_elements = call_path.split('/')    
    receive_elements = receive_path.split('/')    

#     print(call_elements)
#     print(receive_elements)
    
    # try to avoid replacing names that are common    
    common_names = set(name.lower() for name in call_elements if not is_parameter(name)) & set(name.lower() for name in receive_elements if not is_parameter(name))
    
#     print(common_names)
    
    if match_end(call_elements, receive_elements, common_names):
        return True
    
    # try with extension_mappings
    last_receive_element = receive_elements[-1]

    for extension_mapping in extension_mappings:
        
        receive_elements[-1] = extension_mapping.replace('*', last_receive_element)
        if match_end(call_elements, receive_elements, common_names):
            return True
        
    return False 


def is_second_best_path_match(call_url, receive_url, extension_mappings):
    """
    Two URLs are best match if one path end is included in the other one, removing the ending parameters
    And both path are not pathologically empty.
    
    Parameters are allowed to match anything.
    
    :param call_url: str
    :param receive_url: str
    
    The last path element of receive_url can be 'replaced' by one of the extension_mappings
    
        call_url: 'xxx/yyy'
        receive_url: 'xxx/yyy.do'
        extension_mappings : ['*.do']
        
        --> will match
    """
    call_path, _ = split_url(call_url)
    receive_path, _ = split_url(receive_url)
    
    # to list
    call_elements = call_path.split('/')    
    receive_elements = receive_path.split('/')    

    if not call_elements:
        return False

    if not receive_elements:
        return False

    # we allow to remove one parameter at the end of each one
    if is_parameter(call_elements[-1]) and is_exact_path_match('/'.join(call_elements[:-1]), receive_url, extension_mappings):
        return True
    
    if is_parameter(receive_elements[-1]) and is_exact_path_match(call_url, '/'.join(receive_elements[:-1]), extension_mappings):
        return True

    # we allow to remove 2 parameters at the end of call
    if is_parameter(call_elements[-1]) and is_second_best_path_match('/'.join(call_elements[:-1]), receive_url, extension_mappings):
        return True

    # we also allow to remove final {} even part of a text : 
    # user{} will be considered as user 
    # case of badly evaluated url on client side
    if call_elements[-1].endswith('{}'):
        new_call_url = '/'.join(call_elements[:-1]) + '/' + call_elements[-1][:-2]
        if is_exact_path_match(new_call_url, receive_url, extension_mappings):
            return True

    return False


def is_jade_operation(operation):
    """
    We have a special case for EAD4J
    """
    # will ever work because we checking by type name.
    return operation.get_type() == 'CAST_EAD4J_Operation'
   


def is_jade_path_match(call_url, receive_url, exact_extension_mappings):
    """
    3rd chance of mapping
    
    :param exact_extension_mappings: url mappin,gs that do not contains '*'
    
    Example of match 
        call_url : /EUAM/DOCGateway    
        receive_url : /EUAM
        exact_extension_mappings : /DOCGateway
    """
    
    call_path, _ = split_url(call_url)
    receive_path, _ = split_url(receive_url)
    
    
    for exact_extension_mapping in exact_extension_mappings:
        
        new_receive_path = receive_path + exact_extension_mapping
        
        if is_exact_path_match(call_path, new_receive_path, []):
            return True

    return False


def get_best_action_matches(call, operations):
    """
    Get the bests matches by REST action (POST, PUT, GET, ...)    
    
    Can degrade to GET --> POST when nothing else matches
    
    :param call:cast.application.Object
    :param operations:list of cast.application.Object
    """
    
    call_action = get_rest_action(call)
    
    result = []
    
    for operation in operations:
        operation_action = get_rest_action(operation)
        if call_action == operation_action or operation_action == 'ANY':
            result.append(operation)

    if not result and call_action == 'GET':
        
        for operation in operations:
            operation_action = get_rest_action(operation)
            if operation_action == 'POST':
                result.append(operation)
    
    return result
            
            
def get_best_parameter_matches(call, operations):
    """
    Get the bests matches by parameters values
    
    :param call:cast.application.Object or str (url)
    :param operations:list of cast.application.Object or str (url)
    """
    result = []
    
    # allow variadic parameter
    call_url = call if type(call) is str else get_call_url(call)
    _, call_parameters = split_url(call_url)

    max_score = 0

    for operation in operations:
        
        # for each operation we will calculate a score 
        operation_score = 0
        
        # allow variadic parameter
        operation_url = operation if type(operation) is str else get_operation_url(operation)
        
        _, operation_parameters = split_url(operation_url)
        
        # generally, on server side, there will be only one param
        
        for parameter in operation_parameters:
            
            operation_parameter_values = operation_parameters[parameter]
            
            try:
                call_parameter_values = call_parameters[parameter]
                operation_score += 1
                
                if call_parameter_values:
                    if call_parameter_values[0] in operation_parameter_values:
                        operation_score += 1
                
                
            except KeyError:
                # not present
                pass

        if operation_score > max_score:    
            max_score = operation_score
            result.clear()
            
        if operation_score == max_score:
            result.append(operation)


    return result



def filter_less_replacements(operations):
    """
    Keep the operations that have the less number of parameters
    
    Gives fine results.
    """
    
    result = [] 
    minimum = -1

    for operation in operations:
        
        count = 0
        operation_path, _ = split_url(get_operation_url(operation))
        for fragment in operation_path.split('/'):
            if is_parameter(fragment):
                count += 1
        
        if minimum < 0:
            minimum = count
        
        if count < minimum:
            minimum = count
            result =   []
            
        if count == minimum:
            result.append(operation)
    
    return result



class RestLinker(ApplicationLevelExtension):
    
    def __init__(self):
        
        # all operations indexed by fragment of URL
        self.operations_by_name = defaultdict(list)
        self.caip_82 = False        
        
    def end_application(self, application):
        # @type application: cast.application.Application
        logging.info('Linking REST calls')
        
        #### Loading of operations Done
        logging.info('Loading REST operations')
        
        operations = application.objects().is_web_service_operation().load_property('CAST_WebService_Operation.urlPatterns')
        # in version >= 8.2.0 we also have a Core category/property for that
        try:
            operations = operations.load_property('CAST_WebServiceLinker_Operation.urlPatterns')
        except KeyError:
            # the category does not exists , so we are in old version
            pass
        
        has_operations = False
        
        operation_count = 0
        
        # loading and indexing
        for operation in operations:
            operation_count += 1
            has_operations = True
            
            """
            From : https://download.oracle.com/otn-pub/jcp/servlet-3.0-fr-eval-oth-JSpec/servlet-3_0-final-spec.pdf?AuthParam=1553078757_3f292e68b4f416b9011ad433228e8d51
            Section 12.2
            
            In the Web application deployment descriptor, the following syntax is used to define
            mappings:
            - A string beginning with a ‘/’ character and ending with a ‘/*’ suffix is used for
            path mapping.
            - A string beginning with a ‘*.’ prefix is used as an extension mapping.
            - The empty string ("") is a special URL pattern that exactly maps to the
            application's context root, i.e., requests of the form http://host:port/<contextroot>/.
            In this case the path info is ’/’ and the servlet path and context path is
            empty string (““).
            - A string containing only the ’/’ character indicates the "default" servlet of the
            application. In this case the servlet path is the request URI minus the context path
            and the path info is null.
            - All other strings are used for exact matches only.            
            
            
            Here we use 'exact' match for special case of jade.
            
            """
            extension_mappings, exact_matches, _ = get_url_patterns_by_kind(operation)
            
            url = get_operation_url(operation)
            
            for name in get_url_names(url):

                self.operations_by_name[name].append(operation)
                
                # we also replace *.do to correctly index
                for pattern in extension_mappings:
                    new_name = pattern.replace('*', name)
                    self.operations_by_name[new_name].append(operation)
                # we also index with exact match for jade
                for pattern in exact_matches:
                    self.operations_by_name[pattern].append(operation)

        if not has_operations:
            logging.info('No REST operations : nothing to do')     
        
        logging.info('%s REST operations loaded', operation_count)
        
        #### Loading of operations Done
        
        logging.info('Scanning REST calls')

        calls = application.objects().is_web_service_call().load_property('CAST_ResourceService.uri').load_positions()
        # in version >= 8.2.0 we also have a Core category/property for that
        try:
            calls = calls.load_property('CAST_WebServiceLinker_Resource.uri')
        except KeyError:
            # the category does not exists , so we are in old version
            pass
        
        number_call = 0
        number_linked = 0        
        
        number_of_violations = 0
        application.declare_property_ownership('CAST_WebService_Metric_PasswordInUrl.numberOfPasswordInUrl',['CAST_WebService_Metric_PasswordInUrl'])
        
        for call in calls:
            
            number_call += 1
            
            call_url = get_call_url(call)             
            
            if not is_core(call):
                # calculate rule
                if url_contains_password(call_url):
                    
                    positions = call.get_positions()
                    if positions and positions[0].file:
                        call.save_violation('CAST_WebService_Metric_PasswordInUrl.numberOfPasswordInUrl', positions[0])
                        number_of_violations += 1
                    
                
            
            # first select some receiver candidates that at least share a name with the calling url
            candidates = set()
            for name in get_url_names(call_url):
            
                try:
                    for operation in self.operations_by_name[name]:
                        candidates.add(operation)
                except KeyError:
                    pass
            
            # operations that have exact path match
            exact_path_matches = []

            # second best path match (skip trailing /{})
            second_best_path_matches = []

            # jade matches
            jade_path_matches = []

            for operation in candidates:
                
                receive_url = get_operation_url(operation)
                
                extension_mappings, exact_matches, path_mappings = get_url_patterns_by_kind(operation)
                
                if is_exact_path_match(call_url, receive_url, extension_mappings + path_mappings):
                    exact_path_matches.append(operation)
                elif is_second_best_path_match(call_url, receive_url, extension_mappings):
                    second_best_path_matches.append(operation)
                elif is_jade_operation(operation) and is_jade_path_match(call_url, receive_url, exact_matches):
                    jade_path_matches.append(operation)
            
            current_matches = []
            
            # if we have exact path matches, we search in them
            if exact_path_matches:
                current_matches = get_best_parameter_matches(call, get_best_action_matches(call, exact_path_matches))
            # else we search in second best
            if not current_matches and second_best_path_matches:
                current_matches = get_best_parameter_matches(call, get_best_action_matches(call, second_best_path_matches))
            # special case of jade...
            if not current_matches and jade_path_matches:
                current_matches = get_best_parameter_matches(call, get_best_action_matches(call, jade_path_matches))
            # ...
            
            if current_matches:
                number_linked += 1
            
            # we keep only those that have the less number of parameters
            for match in filter_less_replacements(current_matches):
                
                create_link('callLink', call, match)
        
        if number_call:
            percent = number_linked/number_call*100
            
            logging.info("Scanned %s calls", number_call)
            logging.info("Linked %s percent of calls", percent)
        else:
            logging.info('No REST calls : nothing to do')
            
        logging.info(str(number_of_violations) + ' violations found')