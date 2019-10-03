import cast_upgrade_1_5_25 # @UnusedImport
from cast.application import open_source_file # @UnresolvedImport
import cast.analysers.jee
from cast.analysers import create_link, Bookmark, log
from lxml import etree
from collections import OrderedDict
import traceback

def remove_utf8_from_web_xml(fileContent):
    """
    Removes the header from the file content.
    
<?xml version="1.0" encoding="UTF-8"?>
    """
    indexStart = fileContent.find('<?xml')
    if indexStart < 0:
        return fileContent
    
    indexStart = fileContent.find('<', indexStart + 2)
    if indexStart < 0:
        return fileContent

    return fileContent[indexStart:]

def remove_xmlns_from_web_xml(fileContent):
    """
    Removes the "xmlns=" part from file content because lxml api supports this part only by specifying exactly
    its value whenever we want to access a part of xml content, and its value can change between web.xml files.
    
<web-app xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://java.sun.com/xml/ns/javaee" xmlns:web="http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" xsi:schemaLocation="http://java.sun.com/xml/ns/javaee http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" id="WebApp_ID" version="2.5">
</web-app>
    """
    if not 'xmlns=' in fileContent:
        return fileContent
    
    indexStart = fileContent.find('xmlns=')
    indexValueStart = fileContent.find('"', indexStart)
    if indexValueStart < 0:
        return fileContent
    indexValueEnd = fileContent.find('"', indexValueStart + 1)
    if indexValueEnd < 0:
        return fileContent

    return fileContent.replace(fileContent[indexStart:indexValueEnd + 1], '')

def get_web_xml_data(f, urlPatternsByClassFullname):
    """
    We take interest in following part of web.xml file:
    
<web-app xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://java.sun.com/xml/ns/javaee" xmlns:web="http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" xsi:schemaLocation="http://java.sun.com/xml/ns/javaee http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" id="WebApp_ID" version="2.5">
    <servlet>
        <servlet-name>FrontController</servlet-name>
        <servlet-class>com.serviceware.eadm.servlets.AdminNavigationEngine</servlet-class>
        <load-on-startup>1</load-on-startup>
    </servlet>
    
    <servlet-mapping>
        <servlet-name>FrontController</servlet-name>
        <url-pattern>/ne</url-pattern>
    </servlet-mapping>
</web-app>
    
    We search for url patterns corresponding to springMVC (<servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>)
    
    """
    try:
        webappRoot = f.get_path()
        index = webappRoot.rfind('\\WEB-INF\\')
        if index >= 0:
            webappRoot = webappRoot[:index]
        fileContent = None
        with open_source_file(f.get_path()) as myfile:
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
            
            servletClass = servletClassNode.text
            servletName = servlet.find('servlet-name').text
            if not servletName:
                continue
            if not servletClass:
                continue
            if servletName in servletMappings:
                log.info('pattern ' + servletMappings[servletName] + ' found')
                if servletClass in urlPatternsByClassFullname:
                    l = urlPatternsByClassFullname[servletClass]
                else:
                    l = set()
                    urlPatternsByClassFullname[servletClass] = l
                
                # check for existence of same servlet/class/mapping in another file
                exists = False
                for mapping in l:
                    if mapping[0] == servletMappings[servletName]:
                        exists = True
                        break
                if not exists:
                    l.add((servletMappings[servletName], webappRoot))
                
    except Exception as e:
        log.warning('Internal issue: ' + e.args[0])
        if isinstance(fileContent, str):
            log.warning(fileContent)

def getClassInheritances(ast):
    
    l = []
    try:
        extends = ast.get_extends()
        if extends:
            for extend in extends:
                l.append(extend.get_type_name())
    except:
        pass
    return l
    
def get_servlet_url(ast):
    
    try:
        for child in ast.get_children():
            try:
                if child.text.startswith('"/'):
                    return child.text[1:-1]
            except:
                pass
        for child in ast.get_children():
            url = get_servlet_url(child)
            if url:
                return url
    except:
        return None
    return None

class ServletsServices(cast.analysers.jee.Extension):
    """
    Parse ...
    """
    def __init__(self):
        self.nbOperations = 0
        self.types = {}
        self.web_files_scanned = set()
        self.java_parser = None

    # receive a java parser from platform
    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def receive_java_parser(self, parser):
        log.debug('receive_java_parser')
        self.java_parser = parser
        
    def start_analysis(self, execution_unit):
#         execution_unit.add_classpath('jars')
        self.urlPatternsByClassFullname = OrderedDict()
        
    def end_analysis(self):
        log.debug('end_analuysis')
        for fullname, typ in self.types.items():
            url = None
            if not fullname in self.urlPatternsByClassFullname:
                if typ.servletUrl:
                    url = typ.servletUrl
                else:
                    continue
             
            serviceMethods = self.get_methods(typ, ['service', 'doGet', 'doPost', 'doPut', 'doDelete'])
            if serviceMethods:
                if url:
                    self.create_operations(serviceMethods, typ, None, url)
                else:
                    self.create_operations(serviceMethods, typ, self.urlPatternsByClassFullname[fullname])
        
        log.info(str(self.nbOperations) + ' Servlet web service operations created.')
                
    def start_web_xml(self, file):
        
        # I do not know why but the same web xml is received several times, 
        # that was leading to duplicate guids 
        path = file.get_path()
        if path in self.web_files_scanned:
            return
        self.web_files_scanned.add(path)
        
        log.info('File ' + path + ' received.')
        
        try:
            get_web_xml_data(file, self.urlPatternsByClassFullname)
            log.debug(str(self.urlPatternsByClassFullname))
        except Exception as e:
            log.warning('Internal issue: ' + e.args[0])

    def get_methods(self, typ, methodNames):

        methods = OrderedDict() # methods by name. Value is of type {method: <method>, class: <class>}
        children = typ.get_children()
        for child in children:
            for methodName in methodNames:
                if child.get_fullname().endswith('.' + methodName):
                    if not methodName in methods:
                        methods[methodName] = { 'method': child, 'class': typ }
            
        inheriteds = typ.get_inherited_types()
        if inheriteds:
            for inherited in inheriteds:
                serviceMethods = self.get_methods(inherited, methodNames)
                for methodName, serviceMethod in serviceMethods.items():
                    if not methodName in methods:
                        methods[methodName] = serviceMethod
        return methods
        
    def inherits_from(self, typ, fullname, recursive = True):
        for parentTyp in typ.get_inherited_types():
            if parentTyp.get_fullname() == fullname:
                return True
        if not recursive:
            compilation_unit = self.java_parser.parse(typ.get_position().get_file().get_path())
            ast = self.java_parser.get_object_ast(typ)
            names = getClassInheritances(ast)
            for name in names:
                possible_names = compilation_unit.get_possible_qualified_names(name)
                if possible_names:
                    for possible_name in possible_names:
                        if possible_name == fullname:
                            return True
            return False
        for parentTyp in typ.get_inherited_types():
            if self.inherits_from(parentTyp, fullname, recursive):
                return True
        compilation_unit = self.java_parser.parse(typ.get_position().get_file().get_path())
        ast = self.java_parser.get_object_ast(typ)
        names = getClassInheritances(ast)
        for name in names:
            possible_names = compilation_unit.get_possible_qualified_names(name)
            if possible_names:
                for possible_name in possible_names:
                    if possible_name == fullname:
                        return True
        return False
        
    def start_type(self, typ):
        
        fullname = typ.get_fullname()
        typ.servletUrl = None
        
        # to avoid memorizing all classes
        serviceMethods = self.get_methods(typ, ['service', 'doGet', 'doPost', 'doPut', 'doDelete'])
        if not serviceMethods:
            return

        self.types[fullname] = typ
        
        if not self.inherits_from(typ, 'javax.servlet.http.HttpServlet', True):
            return

        
        # servlet 3.0 : not declared in web.xml but by annotations
        try:
            compilation_unit = self.java_parser.parse(typ.get_position().get_file().get_path())
            ast = self.java_parser.get_object_ast(typ)
            annotations = ast.get_annotations()
            for annotation in annotations:
                name = annotation.get_type_name()
                possible_names = compilation_unit.get_possible_qualified_names(name)
                if not 'javax.servlet.annotation.WebServlet' in possible_names:
                    continue
                servletUrl = get_servlet_url(annotation)
                if servletUrl:
                    log.info('HttpServlet annotation found : ' + servletUrl + ' in ' + str(typ))
                    typ.servletUrl = servletUrl
                    return
        except:
            log.debug(traceback.format_exc())

    def normalize_path(self, operationPath):

        service_name = operationPath
        if service_name.startswith('/'):
            service_name = service_name[1:]
        if not service_name.endswith('/'):
            service_name += '/'
        return service_name
        
    def create_operations(self, serviceMethods, methodClass, patterns, url = None):
        log.debug('create_operations')
        log.debug(str(serviceMethods))
        log.debug(str(methodClass))
        
        for methodName, serviceMethodItem in serviceMethods.items():
            serviceMethod = serviceMethodItem['method']
            serviceMethodClass = serviceMethodItem['class']
            if not serviceMethodClass.get_fullname() in self.types: # extern object
                continue
            operationType = None
            shortOperationType = None
            if methodName == 'doPost':
                operationType = 'CAST_Servlet_PostOperation'
                shortOperationType = 'POST'
            elif methodName == 'doGet':
                operationType = 'CAST_Servlet_GetOperation'
                shortOperationType = 'GET'
            elif methodName == 'doPut':
                operationType = 'CAST_Servlet_PutOperation'
                shortOperationType = 'PUT'
            elif methodName == 'doDelete':
                operationType = 'CAST_Servlet_DeleteOperation'
                shortOperationType = 'DELETE'
            elif methodName == 'service':
                operationType = 'CAST_Servlet_AnyOperation'
                shortOperationType = 'ANY'
            if not operationType:
                return
            
            if url:
                operationName = self.normalize_path(url)
                operation_object = cast.analysers.CustomObject()
                operation_object.set_type(operationType)
                operation_object.set_name(operationName)
                operation_object.set_parent(methodClass)
                fullname = serviceMethod.get_fullname() + '/' + operationName + shortOperationType
        
                operation_object.set_fullname(fullname)
                operation_object.set_guid(fullname)
                try:
                    operation_object.save()
                    operation_object.save_position(serviceMethod.get_position())
                    log.debug('create_operation ' + fullname)
                    
#                     operation_object.save_property('CAST_WebService_properties.webappRoot', webappRoot)
    
                    create_link('callLink', operation_object, serviceMethod, serviceMethod.get_position())
                    
                    self.nbOperations += 1
                except Exception as e:
                    log.warning('Internal issue saving ' + operationType)
                    log.debug(str(e))
                    return
                return
            
            log.debug(str(patterns))
            
            for patternObject in patterns:
                
                pattern = patternObject[0]
                webappRoot = patternObject[1]
                operationName = self.normalize_path(pattern)
                if not operationName:
                    continue
                
                operation_object = cast.analysers.CustomObject()
                operation_object.set_type(operationType)
                operation_object.set_name(operationName)
                operation_object.set_parent(methodClass)
                fullname = serviceMethod.get_fullname() + '/' + operationName + shortOperationType
        
                operation_object.set_fullname(fullname)
                operation_object.set_guid(fullname)
                try:
                    operation_object.save()
                    operation_object.save_position(serviceMethod.get_position())
                    log.debug('create_operation ' + fullname)
                    
                    operation_object.save_property('CAST_WebService_properties.webappRoot', webappRoot)
    
                    create_link('callLink', operation_object, serviceMethod, serviceMethod.get_position())
                    
                    self.nbOperations += 1
                except Exception as e:
                    log.warning('Internal issue saving ' + operationType)
                    log.debug(str(e))
                    return
