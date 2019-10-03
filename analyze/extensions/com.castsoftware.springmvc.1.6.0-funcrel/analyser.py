import cast_upgrade_1_6_1  # @UnusedImport
import cast.analysers.jee
from cast.analysers import create_link, log, Method as JeeMethod
from lxml import etree
import traceback
from normalize import normalize_path
import logger
from cast.application import open_source_file
from mappings import remove_utf8_from_web_xml, remove_xmlns_from_web_xml, \
            extract_mappings_from_PropertiesMethodNameResolver, \
            initialize_call_back_methods, get_servlet_config_locations, \
            extract_url_handler_mappings, \
            extract_mappings_with_ParameterMethodNameResolver

def escape(str):
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str

def get_web_xml_data(fileContent, urlPatterns):
    """
    We take interest in following part of web.xml file:
    
<web-app xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://java.sun.com/xml/ns/javaee" xmlns:web="http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" xsi:schemaLocation="http://java.sun.com/xml/ns/javaee http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" id="WebApp_ID" version="2.5">
    <servlet>
        <servlet-name>spring</servlet-name>
        <servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>
        <load-on-startup>1</load-on-startup>
    </servlet>
    
    <servlet-mapping>
        <servlet-name>spring</servlet-name>
        <url-pattern>*.html</url-pattern>
    </servlet-mapping>
</web-app>
    
    We search for url patterns corresponding to springMVC (<servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>)
    
    """
    try:
        if isinstance(fileContent, str):
            pass
        else:
            with open_source_file(fileContent.get_path()) as myfile:
                fileContent=myfile.read()
                
        fileContent = remove_utf8_from_web_xml(fileContent)
        fileContent = remove_xmlns_from_web_xml(fileContent)
        tree = etree.fromstring(fileContent)
      
        servletMappings = {}
     
        for servletMapping in tree.xpath('/web-app/servlet-mapping'):
            name = servletMapping.find('servlet-name').text
            urlPattern = servletMapping.find('url-pattern').text
            if name and urlPattern:
                servletMappings[name] = urlPattern
      
        for servlet in tree.xpath('/web-app/servlet'):
            
            # not mandatory, example <jsp-file> ...
            servletClassNode = servlet.find('servlet-class')
            if servletClassNode is None:
                continue
            
            servletClass = servletClassNode.text.strip()
            if not servletClass == 'org.springframework.web.servlet.DispatcherServlet':
                continue
            servletName = servlet.find('servlet-name').text
            if not servletName:
                continue
            if servletName in servletMappings:
                log.info('pattern ' + servletMappings[servletName] + ' found')
                if not servletMappings[servletName] in urlPatterns:
                    urlPatterns.append(servletMappings[servletName])
    except Exception as e:
        logger.warning('SPMVC-001', 'Internal issue: ' + e.args[0])
        if isinstance(fileContent, str):
            log.warning(fileContent)



def read_properties_file(path):
    log.debug('reading file ' + path)
    with open_source_file(path) as f:
        
        content = {}
        for line in f:
            if '=' in line:
                
                position = line.find('=')
                name = line[:position]
                value = line[position+1:].strip()
                
                content[name] = value
        return content

    
class Mapping:
    
    def __init__(self):
        
        self.pathes = []
        self.methods = []
    
    def __repr__(self):
        
        return 'Mapping %s %s' % (self.pathes, self.methods)
    

class SpringMVC(cast.analysers.jee.Extension):
    """
    Parse ...
    """

    call_back_methods = initialize_call_back_methods()


    class PathContext:
        
        def __init__(self):
            
            self.port = None
            self.port_fullname = None
            self.path = None
            
    
    class TypeContext:
        
        def __init__(self, typ):
            self.currentClass = typ
            self.currentNbMethods = 0
            self.currentNbMethods = 0
            self.operationGuids = {}
            self.portlet = False

            self.currentPort = None
            self.currentPortFullname = []
            self.currentClassPath = []
            
            
            self.class_path = []
        
    def __init__(self):
        
        self.nbOperations = 0
        self.contextStack = []
        self.currentContext = None
        
        # a java parser for annotations
        self.java_parser = None
        self.flow = ""
        
        # handling of properties
        self.properties = []
        self.has_ambiguity_for_properties = False
        self.properties_files_used = []
        self.has_unresolved_property = True

        # mappings from xml-based configuration
        self.url_handler_mappings = dict()
        self.properties_method_name_resolver_mappings = dict()
        self.parameter_method_name_resolver_values = dict()
    
    # receive a java parser from platform
    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def receive_java_parser(self, parser):
        self.java_parser = parser
    
    def pushContext(self, typ):
        self.currentContext = self.TypeContext(typ)
        self.contextStack.append(self.currentContext)
    
    def popContext(self):
        self.contextStack.pop()
        if self.contextStack:
            self.currentContext = self.contextStack[-1]
        else:
            self.currentContext = None
        
    def start_analysis(self, execution_unit):
        self.urlPatterns = []
        self.urlPatternsAsString = ''
        
        # properties files
        self.properties = [path for path in execution_unit.get_source_files() if path.endswith('.properties')]
        
        self.paths_xml = [path for path in execution_unit.get_source_files() if path.endswith('.xml')]

    def end_analysis(self):
        
        # debrief 
        log.info(str(self.nbOperations) + ' Spring-MVC web service operations created.')
        
        if self.has_ambiguity_for_properties:
            log.info('Some properties were found several times in different property files')
            log.info('  The properties files used are')
            for path in self.properties_files_used:
                log.info('    ' + path)
        
        
        bb = """<?xml version="1.0" encoding="utf-8"?>
<BlackBox name="SpringMVCServiceEntryPoints" xmlns="http://tempuri.org/BlackBoxes.xsd">
  <Class mangling="generated.EntryPoints">
    <Methods>
      <Method signature="CallEntryPoints()">
        <Flow mode="call" callee="[cast#lib]Network.read()">
          <returnValue lval="v1" />
        </Flow>
        %s
      </Method>
    </Methods>
  </Class>
</BlackBox>
         
        """ % self.flow
        
        with self.get_intermediate_file("ServiceEntryPoints.blackbox.xml") as f:
            f.write(bb)
        
        
    def start_web_xml(self, file):

        log.info('File ' + file.get_path() + ' received.')
        
        try:
            get_web_xml_data(file, self.urlPatterns)
            
            self.urlPatternsAsString = None
            
            for pattern in self.urlPatterns:
                if not self.urlPatternsAsString:
                    self.urlPatternsAsString = pattern
                else:
                    self.urlPatternsAsString += (';' + pattern)
        except Exception as e:
            log.warning('Internal issue: ' + e.args[0])

        locations = get_servlet_config_locations(file)
        paths_config = [path for path in self.paths_xml if
                            path.endswith(tuple(locations))]

        for path in paths_config:
            log.info("Analyzing servlet configuration file: {}".format(path))
            text = None
            with open_source_file(path) as f:
                text = f.read()
            if not text:
                continue

            # simplify xml treatemnt by ignoring xml-namespacing
            text = remove_utf8_from_web_xml(text)
            text = remove_xmlns_from_web_xml(text)
            tree = etree.fromstring(text)

            self.url_handler_mappings = extract_url_handler_mappings(tree)
            self.properties_method_name_resolver_mappings = extract_mappings_from_PropertiesMethodNameResolver(tree)
            self.parameter_method_name_resolver_values = extract_mappings_with_ParameterMethodNameResolver(tree)

    def start_type(self, typ):

        def get_return_type(ast):
            try:
                token = ast.type[0]
                return token.text
            except (AttributeError, IndexError):
                pass

        self.pushContext(typ)
        
        # Scenario 1:
        #     use mappings defined by annotations to create web services
        for mapping in self.get_mappings(typ):
             
            for path in mapping.pathes:
                
                if path in ['VIEW', 'HELP', 'EDIT']:
                    # not an url mapping
                    # portlet : not a webservice
                    self.currentContext.portlet = True
                    return
                
                if not path.startswith('/'):
                    
                    path = '/' + path
                
                
                
                path_context = SpringMVC.PathContext()
                path_context.path = path
                self.currentContext.class_path.append(path_context)
                
                
                self.create_web_service(typ, path)
            break    

        # scenario 2:
        #    mappings to controllers inside the SimpleUrlHandlerMapping
        #    handler mapping bean (in .xml files)

        # Two approaches are used to get the extensions of a class:
        #     (1) recovering the name of the extension class as a string using
        #         the 'ast' returned by the "plugged" java parser.
        #     (2) one recovers the cast.analysers.Type using the provided API.
        #
        # The latter approach is only useful when the class is resolvable (its code is present),
        # which is not the case for external code such as a third-party framework like spring-mvc).
        # The "ast" however returns just the name of the inherited class
        # independently of its resolution. Combining these two approaches one
        # could inspect the ancestry up to the Controller-type class.
        #
        # Note: java_parser.parser.Class.get_extends() does not discern between implements/extends
        #
        # Limitation: only two level ancestry-depth is supported A->B->C

        fullname = typ.get_fullname()

        if fullname in self.url_handler_mappings:
            ast = self.java_parser.get_object_ast(typ)
            if ast:
                extends = ast.get_extends()

                for extended_class in extends:
                    name_extended_class = extended_class.get_type_name()

                    methods_type = []
                    controller_class_name = name_extended_class
                    
                    if not name_extended_class in self.call_back_methods.keys():

                        # search multilevel
                        inherits_from_controller = False

                        ancestors = typ.get_inherited_types()
                        for ancestor in ancestors:
                            ast_ancestor = self.java_parser.get_object_ast(ancestor)
                            if ast_ancestor:
                                extends_ancestor = ast_ancestor.get_extends()
                                for sup_extend in extends_ancestor:
                                    name_sup_extended_class = sup_extend.get_type_name() 
                                    if name_sup_extended_class in self.call_back_methods:
                                        inherits_from_controller = True
                                        methods_type = ancestor.get_children()
                                        controller_class_name = name_sup_extended_class
                                        break

                        if not inherits_from_controller:
                            break

                    methods_type += typ.get_children()
                    
                    call_backs = []
                    for method in methods_type:
                        if not isinstance(method, JeeMethod):
                            continue

                        # overriden methods
                        if method.get_name() in self.call_back_methods[controller_class_name]:
                            call_backs.append(method)

                        # constructor: we modelize the implicit call to the constructor
                        # at this point
                        elif method.get_name() == typ.get_name():
                            call_backs.append(method)

                    # special treatment for multicontroller
                    if name_extended_class == 'MultiActionController':
                        method_names = [method.get_name() for method in call_backs]
                        if not 'handleRequestInternal' in method_names:
                            continue
                            
                    operationType = "ANY"

                    for operation_path in self.url_handler_mappings[fullname]:
                        self.create_operation2(operationType, operation_path, typ, call_backs)

                    if not call_backs:
                        log.debug("No callback methods found for operation {}".format(operation_path))

        # scenario 3:
        #    mappings to user-defined methods using the "methodNameResolver"
        #    property inside controller beans of type MultiActionController
        #    (in .xml files)
        if fullname in self.properties_method_name_resolver_mappings:
            urls = {url for (url, _) in self.properties_method_name_resolver_mappings[fullname]}
            for operation_path in urls:
                call_back_methods = [method for (_url, method) in self.properties_method_name_resolver_mappings[fullname]
                                                if _url == operation_path]
                methods = typ.get_children()
                call_backs = []
                for method in methods:
                    if not isinstance(method, JeeMethod):
                        continue
                    if method.get_name() in call_back_methods:
                        call_backs.append(method)

                # add the lead fragment of the path
                if fullname in self.url_handler_mappings:
                    for lead_url in self.url_handler_mappings[fullname]:
                        operation_path = lead_url.replace('/*', '') + operation_path.replace('/*','')
                        operationType = "ANY"
                        self.create_operation2(operationType, operation_path, typ, call_backs)
                else:
                    operationType = "ANY"
                    self.create_operation2(operationType, operation_path, typ, call_backs)

        # scenario 4:
        #    mappings to methods with the ParameterMethodNameResolver property
        if fullname in self.parameter_method_name_resolver_values:
            methods = typ.get_children()
            for method in methods:
                call_backs = []
                if not isinstance(method, JeeMethod):
                        continue
                ast = self.java_parser.get_object_ast(method)
                if get_return_type(ast) == 'ModelAndView':
                    call_backs.append(method)
                    operationType = "ANY"  # query parameters can be included also in POST
                    urlpaths = self.parameter_method_name_resolver_values[fullname]
                    for urlpath in urlpaths:
                        operation_path = urlpath + method.get_name()
                        self.create_operation2(operationType, operation_path, typ, call_backs)

    def end_type(self, typ):

        if self.currentContext.currentNbMethods == 0:
            # compensate a bug : members of abstract classes are not visited...
            for child in typ.get_children():
                try:
                    self.parse_member(child)
                except:
                    log.warning('Internal issue parsing member for SpringMVC type ' + str(typ))

        self.popContext()

    def start_member(self, member):
        
        
        if not self.currentContext:
            return
        
        
        if member.get_name() == 'initErrorHandlerWindow':
            pass

        self.currentContext.currentNbMethods += 1
        self.parse_member(member)

    def parse_member(self, member):
        
        if not self.currentContext.currentClass:
            return
        
        if self.currentContext.portlet:
            # portlet : not a web service
            return
        
        for mapping in self.get_mappings(member):
            
            # @RequestMapping at class level is optional
            if not self.currentContext.class_path:
                
                path_context = SpringMVC.PathContext()
                path_context.path = '/'
                self.currentContext.class_path.append(path_context)
                
                self.create_web_service(self.currentContext.currentClass, '/')
                
            
            for path in mapping.pathes:
                
                for method in mapping.methods:
                    
                    operationType = None
                    
                    if method == 'GET':
                        operationType = 'GET'
                    elif method == 'POST':
                        operationType = 'POST'
                    elif method == 'PUT':
                        operationType = 'PUT'
                    elif method == 'DELETE':
                        operationType = 'DELETE'
                    else:
                        operationType = 'ANY'
                    
                    self.create_operation(operationType, path, member)

                
    def create_web_service(self, javaClass, path):
        
        web_service_object = cast.analysers.CustomObject()
        web_service_object.set_name(path)
        web_service_object.set_type('CAST_SpringMVC_Service')
        parentFile = self.currentContext.currentClass.get_position().get_file()
        web_service_object.set_parent(parentFile)
        wsFullname = parentFile.get_fullname() + path
        web_service_object.set_fullname(wsFullname)
        web_service_object.set_guid(wsFullname)
        web_service_object.save()
        web_service_object.save_position(javaClass.get_position())

        self.create_port(wsFullname, web_service_object, javaClass, path)
                
    def create_port(self, wsFullname, webService, javaClass, path):
        
        port_object = cast.analysers.CustomObject()
        
        port_object.set_name(path)
        port_object.set_type('CAST_SpringMVC_Port')
        port_object.set_parent(webService)
        
        currentPortFullname = wsFullname + '/PORT'
        self.currentContext.class_path[-1].port_fullname = currentPortFullname
        self.currentContext.class_path[-1].port = port_object
        

        port_object.set_fullname(currentPortFullname)
        port_object.set_guid(currentPortFullname)
        port_object.save()
        port_object.save_position(javaClass.get_position())
        
        create_link('prototypeLink', port_object, self.currentContext.currentClass, self.currentContext.currentClass.get_position())


    def create_operation(self, operationType, operationPath, method):
        
        self.generate_bb(method)
        
        for path_context in self.currentContext.class_path:
            
            operationName = path_context.path
            if operationPath:
                if not operationPath.startswith('/'):
                    operationName = operationName + '/' + operationPath
                else:
                    operationName = operationName + operationPath
            else:
                operationName = operationName + '/'
    
            operationName = normalize_path(operationName)
    
            # limit case : everything is '/'        
            if not operationName and operationPath == '/':
                operationName = "/"
            
            if not operationName:
                return
            
            log.debug('creating operation ' + str(operationName) + ' ' + str(operationType))
            operation_object = cast.analysers.CustomObject()
            operation_object.set_name(operationName)
            operation_object.set_parent(path_context.port)
            fullname = path_context.port_fullname + '/'
    
            # @todo replace by callLink
            
            linkType = 'callLink'
            if operationType == 'DELETE':
                operation_object.set_type('CAST_SpringMVC_DeleteOperation')
                fullname += 'DELETE'
            elif operationType == 'PUT':
                operation_object.set_type('CAST_SpringMVC_PutOperation')
                fullname += 'PUT'
            elif operationType == 'POST':
                operation_object.set_type('CAST_SpringMVC_PostOperation')
                fullname += 'POST'
            elif operationType == 'ANY':
                operation_object.set_type('CAST_SpringMVC_AnyOperation')
                fullname += 'ANY'
            else:
                operation_object.set_type('CAST_SpringMVC_GetOperation')
                fullname += 'GET'
                
            fullname += ( '/' + operationName )
            if fullname in self.currentContext.operationGuids:
                nr = self.currentContext.operationGuids[fullname]
                nr += 1
                self.currentContext.operationGuids[fullname] = nr
                fullname += ('_' + str(nr))
            else:
                self.currentContext.operationGuids[fullname] = 0
                
            operation_object.set_fullname(fullname)
            operation_object.set_guid(fullname)
            try:
                operation_object.save()
                operation_object.save_position(method.get_position())
                create_link(linkType, operation_object, method, method.get_position())
                
                self.nbOperations += 1
            except:
                log.warning('Internal issue saving SpringMVC operation')
                return
    
            try:
                if self.urlPatternsAsString:
                    operation_object.save_property('CAST_WebService_Operation.urlPatterns', self.urlPatternsAsString)
            except:
                log.warning('Internal issue saving CAST_WebService_Operation.urlPatterns')

    def create_operation2(self, operationType, operation_path, typ, methods):
        """
        Slightly different version of the original 
        "create_operation" method
        
        Note: we don't call to:  self.generate_bb(method)        
        """
        operationName = normalize_path(operation_path)

        # should we call generate_bb?

        log.debug('creating operation ' + str(operationName) + ' ' + str(operationType))
        operation_object = cast.analysers.CustomObject()
        operation_object.set_name(operationName)
        file = typ.get_position().get_file()
        operation_object.set_parent(file)

        fullname = file.get_fullname() + '/'

        linkType = 'callLink'
        if operationType == 'DELETE':
            operation_object.set_type('CAST_SpringMVC_DeleteOperation')
            fullname += 'DELETE'
        elif operationType == 'PUT':
            operation_object.set_type('CAST_SpringMVC_PutOperation')
            fullname += 'PUT'
        elif operationType == 'POST':
            operation_object.set_type('CAST_SpringMVC_PostOperation')
            fullname += 'POST'
        elif operationType == 'ANY':
            operation_object.set_type('CAST_SpringMVC_AnyOperation')
            fullname += 'ANY'
        else:
            operation_object.set_type('CAST_SpringMVC_GetOperation')
            fullname += 'GET'

        fullname += ('/' + operationName)

        if fullname in self.currentContext.operationGuids:
            nr = self.currentContext.operationGuids[fullname]
            nr += 1
            self.currentContext.operationGuids[fullname] = nr
            fullname += ('_' + str(nr))
        else:
            self.currentContext.operationGuids[fullname] = 0

        operation_object.set_fullname(fullname)
        operation_object.set_guid(fullname)
        try:
            operation_object.save()
            operation_object.save_position(typ.get_position())
            for method in methods:
                position = method.get_position()
                file_path = method.get_position().get_file().get_path()
                if not file_path:
                    # we skip 'default' constructors
                    # they don't seem to be important in the call-graph
                    # (they have empty bookmarks later on: Bookmark(,1,1,1,1))
                    continue
                
                create_link(linkType, operation_object, method, position)

            self.nbOperations += 1
        except:
            log.warning('Internal issue saving SpringMVC operation')
            return

        try:
            if self.urlPatternsAsString:
                operation_object.save_property('CAST_WebService_Operation.urlPatterns', self.urlPatternsAsString)
        except:
            log.warning('Internal issue saving CAST_WebService_Operation.urlPatterns')

    def generate_bb(self, method):

        try:
            current_method = """
            <Flow mode="call" callee="%s(%s)">
              %s
            </Flow>
            """
            
            fullname = method.get_fullname()
            parameters_type = ""
            
            parameters = ""
            
            param_order = 1
            
            for _name, _type in method.get_parameters().items():
                
                if parameters_type:
                    parameters_type += ','
                
                type_fullname = 'java.lang.Object' # defaulting in case of non resolution
                if _type and hasattr(_type, 'get_fullname'):
                    type_fullname = _type.get_fullname()
                
                elif _type and hasattr(_type, 'get_name'):
                    type_fullname = _type.get_name()
                    if type_fullname == 'String':
                        type_fullname = 'java.lang.String'
    
                parameters_type += type_fullname
                
                if not type_fullname.endswith('HttpServletResponse'):
                    
                    parameters += """<inParam index="%s" rval="v1" />""" % param_order
                
                param_order += 1
    
            self.flow += current_method % (fullname, escape(parameters_type), parameters)
        except:
            pass
    
    def get_property_values(self, property_name):
        """
        Return a list of possible values for _property
        """
        result = set()
        
        for path in self.properties:
            
            content = read_properties_file(path)
            try:
                result.add(content[property_name])
                self.properties_files_used.append(path)
            except KeyError:
                pass
        
        if len(result) > 1:
            # ambiguity
            self.has_ambiguity_for_properties = True
        
        return result
    
    def replace_property(self, value):
        """
        In case of ${}
        May return several values
        """
        if value.startswith('${'):
            
            property_name = value[2:-1]
            
            values = self.get_property_values(property_name)
            if values:
                return values
            # else property not found still return the original name
            self.has_unresolved_property = True
            logger.warning('SPMVC-002', "Could not find '%s' property" % property_name)
            # still keep max produced info 
            return [value]
        
        return [value]

    def get_mappings(self, o):
        """
        Get the mappings
        
        RequestMapping and their values...
        """
        result = []
        
        
        def create_mapping(annotation):
            
            mapping = Mapping()
            
            named_parameters = annotation.get_named_parameters()
#             log.info(str(named_parameters))
            
            # default value
            value = '/'
            try:
                value = named_parameters['value']
            except:
                try:
                    value = named_parameters['path']
                except:
                    pass
            if value:
                
                # normalise to list
                pathes = []
                if type(value) is list:
                    pathes = value
                else:
                    pathes = [value]
                
                # replace property
                for path in pathes:
                    mapping.pathes += self.replace_property(path)
                    
            return mapping
        
        
        compilation_unit = self.java_parser.parse(o.get_position().get_file().get_path())
        ast = self.java_parser.get_object_ast(o)
        
#         log.info(str(o) + ' ast = ' + str(ast))
        
        try:
            
            annotations = ast.get_annotations()
#             log.info(str(annotations))
            for annotation in annotations:
                
                
                name = annotation.get_type_name()
#                 log.debug(str(compilation_unit.get_possible_qualified_names(name)))
                
                possible_names = compilation_unit.get_possible_qualified_names(name)
                
                # classical case + special case for webgoat (custom webgoat annotation)
                # little risk to add custom or fewly used annotations as :
                # possible_names has a clear idea of fullname (it is not reporting something impossible)
                if 'org.springframework.web.bind.annotation.RequestMapping' in possible_names or \
                   'org.owasp.webgoat.assignments.AssignmentPath' in possible_names:
                    # case of requestmapping
                    mapping = create_mapping(annotation)
                    
                    named_parameters = annotation.get_named_parameters()
                    
                    methods = []
                    try:
                        method = named_parameters['method']
                        if type(method) is list:
                            methods = method
                        else:
                            methods = [method]
                    except:
                        pass
                    
                    # normalise methods (keep only POST, GET, ...)
                    for method in methods:
                        splitted = method.split('.')
                        if len(splitted) >= 1:
                            mapping.methods.append(splitted[-1]) 
                    
                    if not mapping.methods:
                        mapping.methods.append('ANY')
                    
                    
                    result.append(mapping)
                elif 'org.springframework.web.bind.annotation.GetMapping' in possible_names:
                    # case of requestmapping
                    mapping = create_mapping(annotation)
                    mapping.methods.append('GET')
                    result.append(mapping)
                elif 'org.springframework.web.bind.annotation.PostMapping' in possible_names:
                    # case of requestmapping
                    mapping = create_mapping(annotation)
                    mapping.methods.append('POST')
                    result.append(mapping)
                elif 'org.springframework.web.bind.annotation.PutMapping' in possible_names:
                    # case of requestmapping
                    mapping = create_mapping(annotation)
                    mapping.methods.append('PUT')
                    result.append(mapping)
                elif 'org.springframework.web.bind.annotation.DeleteMapping' in possible_names:
                    # case of requestmapping
                    mapping = create_mapping(annotation)
                    mapping.methods.append('DELETE')
                    result.append(mapping)
                elif 'org.springframework.web.bind.annotation.PatchMapping' in possible_names:
                    # case of requestmapping
                    mapping = create_mapping(annotation)
                    mapping.methods.append('ANY')
                    result.append(mapping)
                    
        except:
            if '<anonymous>' not in str(o):
                
                log.debug('for object ' + str(o) + ' ' + traceback.format_exc())
                log.debug(str(o.get_position()))
            # else : anonymous elements still not handled...
        
        return result
                    
