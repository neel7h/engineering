from cast.analysers import log
from collections import defaultdict
from lxml import etree
from cast.application import open_source_file
import itertools
import os


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


def get_servlet_config_locations(fileContent):
    """
    Return locations of context configuration files.
    Locations are given relative to the parent folder of '/WEB-INF'
    """

    if isinstance(fileContent, str):
        pass
    else:
        path = fileContent.get_path()
        with open_source_file(path) as myfile:
            fileContent = myfile.read()

    fileContent = remove_utf8_from_web_xml(fileContent)
    fileContent = remove_xmlns_from_web_xml(fileContent)
    tree = etree.fromstring(fileContent)

    locations = []
    for servlet in tree.xpath('/web-app/servlet/servlet-class/..'):
        name_class = servlet.find('servlet-class').text.strip()
        if not name_class.endswith('.DispatcherServlet'):
            continue
            
        location = None
        for init_param in servlet.findall('init-param'):
            param_name = init_param.find('param-name')
            if param_name is not None:
                param_name = param_name.text.strip()
            if param_name == 'contextConfigLocation':
                param_value = init_param.find('param-value')
                if param_value is not None:
                    location = os.path.normpath(param_value.text.strip())
                continue

        if not location:
            # default name
            servlet_name = servlet.find('servlet-name').text.strip()
            location = '/WEB-INF/' + servlet_name + '-servlet.xml'
            location = os.path.normpath(location)
        locations.append(location)

    return locations

def extract_controllerClassNameHandler_mappings(tree):

    mappings = defaultdict(list)
    has_ControllerClassNameHandlerMapping = tree.xpath('//bean[@class="org.springframework.web.servlet.mvc.support.ControllerClassNameHandlerMapping"]')
    if not has_ControllerClassNameHandlerMapping:
        return mappings

    for controller in tree.xpath("//bean[@class]"):
        controller_fullname = controller.attrib['class']
        urlpath = controller_fullname.split('.')[-1].lower()
        urlpath = urlpath.split("controller")[0] + '/{}'
        mappings[controller_fullname].append(urlpath)

    return mappings


def extract_url_handler_mappings(tree):
    """Returns mappings from
            - beanNameUrlHandlerMapping
            - simpleUrlHandlerMapping
            - controllerClassNameHandlerMapping
    """
    mapping0 = extract_mappings_from_beanNameUrlHandlerMapping(tree)
    mapping1 = extract_mappings_from_simpleUrlHandlerMapping_mode1(tree)
    mapping2 = extract_mappings_from_simpleUrlHandlerMapping_mode2(tree)
    mapping3 = extract_mappings_from_simpleUrlHandlerMapping_mode3(tree)
    mapping4 = extract_controllerClassNameHandler_mappings(tree)

    url_handler_mappings = defaultdict(list)
    url_handler_mappings.update(mapping0)

    # merge mappings based on simpleUrlHandlerMapping
    for mapping in [mapping1, mapping2, mapping3, mapping4]:
        for key, value in mapping.items():
            if not value in url_handler_mappings[key]:
                url_handler_mappings[key].extend(value)
            else:
                # this might indicate the use of priority orders
                log.debug("Overloaded mapping detected for url path: {}".format(value))

    return url_handler_mappings


def extract_mappings_from_beanNameUrlHandlerMapping(tree):
    """
    We assume usage of beanNameUrlHandlerMapping (handler mapping 
    provided by default in Spring MVC) when finding url-like 
    pattern in bean name:
    
        <bean name="/welcome.htm" 
                class="com.mkyong.common.controller.HelloWorldController" /> 
    """
    mappings = defaultdict(list)

    for bean in tree.xpath("//bean[@name][@class]"):
        url = bean.attrib['name']
        if not url.startswith("/"):
            # not a url
            continue

        clazz = bean.attrib['class']
        mappings[clazz].append(url)
    
    return mappings


def extract_mappings_from_simpleUrlHandlerMapping_mode1(tree):
    """Extract mappings using 'urlMap' property of the form:
    
 <bean id="handlerMapping" class="org.springframework.web.servlet.handler.SimpleUrlHandlerMapping">
  <property name="urlMap">
      <map>
            <entry key="/mainMenu">
              <ref local="mainMenuController"/>
            </entry>
            
     --- or alternatively ---
     
            <entry key="/mainMenu" value-ref="mainMenuController"/>

    Limitations
    -----------
    The search of referenced beans is done
    only in the current file
    """

    mappings = defaultdict(list)

    for entry in tree.xpath("//bean[@class='org.springframework.web.servlet.handler.SimpleUrlHandlerMapping']/property[@name='urlMap']/map/entry"):

        urlpath = entry.attrib['key']
        id_controller = None
        if 'value-ref' in entry.attrib:
            id_controller = entry.attrib['value-ref']
        else:
            ref = entry.find('ref')
            if ref is None:
                continue

            for attr in ref.attrib.keys():
                if attr in ['local', 'bean']:
                    id_controller = ref.attrib[attr]

        if not id_controller:
            continue

        try:
            controller = tree.xpath("/beans/bean[@id='{}']".format(id_controller))[0]
        except (IndexError, TypeError):
            continue
        controller_fullname = controller.attrib['class']
        if controller_fullname:
            if controller_fullname in mappings:
                if urlpath in mappings[controller_fullname]:
                    log.info("Found duplicated entry for path: {}".format(urlpath))
                    continue

            mappings[controller_fullname].append(urlpath)

    urlpaths = list(itertools.chain.from_iterable(mappings.values()))
    for path in set([x for x in urlpaths if urlpaths.count(x) > 1]):
        log.info("Found multiple controllers for path: {}".format(path))

    return mappings





def extract_mappings_from_simpleUrlHandlerMapping_mode2(tree):
    """Extract mappings using 'mappings' property of the form:
    
<bean id="SomeUrlMappings"
    class="org.springframework.web.servlet.handler.SimpleUrlHandlerMapping">
    <property name="mappings">
        <value>
            /flow/*=flowController
            /download=defaultController
        </value>
    </property>
    <property name="order" value="1" />
</bean>
    """

    mappings = defaultdict(list)

    for mapping_value in tree.xpath("//bean[@class='org.springframework.web.servlet.handler.SimpleUrlHandlerMapping']/property[@name='mappings']/value"):
        text = mapping_value.text
        parts = text.split()

        for p in parts:
            try:
                urlpath, controller = p.split('=')
            except ValueError:
                continue

            try:
                controller_bean = tree.xpath("/beans/bean[@id='{}']".format(controller))[0]
            except IndexError:
                continue

            controller_fullname = controller_bean.attrib['class']
            mappings[controller_fullname].append(urlpath)

    return mappings

def extract_mappings_from_simpleUrlHandlerMapping_mode3(tree):
    """Extract mappings using 'mappings' property of the form:
    
<bean id="SomeUrlMappings"
        class="org.springframework.web.servlet.handler.SimpleUrlHandlerMapping">
    <property name="mappings">
       <props>
            <prop key="home.htm">homeController</prop>
            ...
</bean>
    """

    mappings = defaultdict(list)

    for prop in tree.xpath("//bean[@class='org.springframework.web.servlet.handler.SimpleUrlHandlerMapping']"
                            "/property[@name='mappings']/props/prop"):

        controller = prop.text.strip()
        try:
            controller_bean = tree.xpath("/beans/bean[@id='{}']".format(controller))[0]
        except IndexError:
            continue

        controller_fullname = controller_bean.attrib['class']
        urlpath = prop.attrib['key']
        mappings[controller_fullname].append(urlpath)

    return mappings


def extract_mappings_from_PropertiesMethodNameResolver(tree):
    """
    Return mappings defined by the property "methodNameResolver" of the form

<bean id="manageSomeController"
    class="com.cingular.km.lbs.gearsadmin.web.controller.SomeController">
    ...
    <property name="methodNameResolver">
       <bean
         class="org.springframework.web.servlet.mvc.multiaction.PropertiesMethodNameResolver">
         <property name="mappings">
           <props>
             <prop key="/*/deleteAddress">deleteAddress</prop>
    """

    mappings = defaultdict(list)

    for bean_with_resolver in tree.xpath("*/property[@name='methodNameResolver']/.."):
        controller_fullname = bean_with_resolver.attrib['class']
        # TODO : bean can be a ref !!!
        props_list = bean_with_resolver.xpath("property/bean/property[@name='mappings']/props")
        for props in props_list:
            for prop in props.getchildren():
                url = prop.attrib['key']
                method_name = prop.text.strip()
                url_method_pair = (url, method_name)
                mappings[controller_fullname].append(url_method_pair)

#         ref_list = bean_with_resolver.xpath("property[@name='methodNameResolver']/ref")
#         for ref in ref_list:
#             id_resolver = ref.attrib['bean']  # it can be a mapping
#             try:
#                 resolver = tree.xpath("/beans/bean[@id='{}']".format(id_resolver))[0]
#             except (IndexError, TypeError):
#                 continue
#             else:
#                 paramName = resolver.find('property')
#                 if not paramName.attrib['name'] == 'paramName':
#                     continue
#                 value = paramName.find('value')

    return mappings


def extract_mappings_with_ParameterMethodNameResolver(tree):
    """
    We treat two different cases:
        CASE 1: in combination with simpleUrlHandlerMapping
        CASE 2: in combination with ControllerClassNameHandlerMapping
    """

    mappings = defaultdict(list)

    # CASE 1
    for entry in tree.xpath("//bean[@class='org.springframework.web.servlet.handler.SimpleUrlHandlerMapping']/property[@name='urlMap']/map/entry"):

        urlpath = entry.attrib['key']
        ref = entry.find('ref')
        if ref is None:
            continue

        id_controller = None
        for attr in ref.attrib.keys():
            if attr in ['local', 'bean']:
                id_controller = ref.attrib[attr]
        if not id_controller:
            continue

        try:
            controller = tree.xpath("/beans/bean[@id='{}']".format(id_controller))[0]
        except (IndexError, TypeError):
            continue
        controller_fullname = controller.attrib['class']
        if controller_fullname:
            resolvers = controller.xpath("property[@name='methodNameResolver']")
            for resolver in resolvers:
                ref_bean_resolver = resolver.find("ref")
                if ref_bean_resolver == None:
                    continue
                id_resolver = ref_bean_resolver.attrib['bean']

                resolver_bean = tree.xpath("/beans/bean[@id='{}']".format(id_resolver))[0]

                paramName = resolver_bean.find('property')
                if not paramName or not paramName.attrib['name'] == 'paramName':
                    continue
                value = paramName.find('value').text
                if value:
                    value = value.strip()
                    urlpath_with_method = urlpath + "?" + value + "="
                    mappings[controller_fullname].append(urlpath_with_method)

    has_mapping = tree.xpath('//bean[@class="org.springframework.web.servlet.mvc.support.ControllerClassNameHandlerMapping"]')
    if not has_mapping:
        return mappings

    # CASE 2
    # we now search controllers having property "methodNameResolver"
    # and not captured by previous block to
    for controller in tree.xpath("//bean[@class]/property[@name='methodNameResolver']/.."):
        controller_fullname = controller.attrib['class']
        if controller_fullname and not controller_fullname in mappings:
            resolvers = controller.xpath("property[@name='methodNameResolver']")
            for resolver in resolvers:
                ref_bean_resolver = resolver.find("ref")
                if ref_bean_resolver is not None:
                    id_resolver = ref_bean_resolver.attrib['bean']

                    resolver_bean = tree.xpath("/beans/bean[@id='{}']".format(id_resolver))[0]

                else:
                    resolver_bean = resolver.find("bean")
                if not resolver_bean:
                    continue

                paramName = resolver_bean.find('property')
                if paramName is None or not paramName.attrib['name'] == 'paramName':
                    continue
                value = paramName.attrib['value']
                if not value:
                    # try by element
                    value = paramName.find('value').text
                if value:
                    value = value.strip()
                    urlpath = controller_fullname.split('.')[-1].lower()
                    urlpath = urlpath.split("controller")[0] + '/*'
                    urlpath_with_method = urlpath + "?" + value + "="
                    mappings[controller_fullname].append(urlpath_with_method)

    return mappings


def initialize_call_back_methods():
    """Initializes the dictionary with the name of defined methods
    in each controller class.
    
    Ideally this list should only include methods that are called
    during the workflow of the Spring MVC framework and that can
    be overridden.
    
    In the official documentation page there are listed many methods.
    We exclude those defined as 'final' since they cannot be overridden.
    
    We add also inherited methods:
    
    ------------------
    AbstractController
        BaseCommandController
            AbstractFormController
                SimpleFormController
                    CancellableFormController
                AbstractWizardFormController
            AbstractCommandController
        AbstractUrlViewController
            UrlFilenameViewController
        ParameterizableViewController
        ServletForwardingController
        ServletWrappingController
        MultiActionController
    -------------------

    NOTE: we might use sets instead of lists to remove potential duplications 
        (ex. handleRequestInternal)
    
    NOTE: constructors are called in a different place
    
    Limitations
    -----------
    We don't handle the potential overriding of internal inter-method calls
    when overriding default implementations.
    
    """

    call_back_methods = {
                    'AbstractController' : ['handleRequest', 'handleRequestInternal'],

                    'BaseCommandController': ['initApplicationContext', 'getCommand', 'bindAndValidate',
                                              'suppressBinding', 'createBinder', 'useDirectFieldAccess',
                                              'initBinder', 'onBind', 'suppressValidation', 'onBindAndValidate'],
                    
                    'AbstractFormController': ['handleRequestInternal', 'isFormSubmission', 'getFormSessionAttributeName',
                                               'getFormSessionAttributeName', 'showNewForm', 'getErrorsForNewForm',
                                               'onBindOnNewForm', 'getCommand', 'formBackingObject', 'currentFormObject',
                                               'showForm', 'referenceData', 'processFormSubmission', 'handleInvalidSubmit'],

                    'SimpleFormController': ['showForm', 'referenceData', 'processFormSubmission', 'suppressValidation',
                                             'isFormChangeRequest', 'onFormChange', 'onSubmit', 'doSubmitAction'],

                    'CancellableFormController': ['isFormSubmission', 'suppressValidation', 'processFormSubmission',
                                                  'isCancelRequest', 'onCancel'],

                    'AbstractWizardFormController': ['onBindAndValidate','isFormSubmission','referenceData','showForm',
                                                    'showPage','getPageCount','getViewName','getInitialPage','getPageSessionAttributeName',
                                                    'handleInvalidSubmit','getCurrentPage','isFinishRequest','isCancelRequest',
                                                    'getTargetPage','validatePagesAndFinish','validatePage','postProcessPage',
                                                    'processFinish', 'processCancel'],

                    'AbstractCommandController': ['handleRequestInternal', 'handle'],

                    'AbstractUrlViewController': ['setAlwaysUseFullPath', 'setUrlDecode', 'setUrlPathHelper',
                                                  'getUrlPathHelper', 'handleRequestInternal', 'getViewNameForRequest'],
                    
                    'UrlFilenameViewController': ['setPrefix', 'getPrefix', 'setSuffix', 'getSuffix',
                                                  'getViewNameForRequest', 'extractOperableUrl', 'getViewNameForUrlPath', 
                                                  'extractViewNameFromUrlPath','postProcessViewName'],

                    'ParameterizableViewController': ['setViewName', 'getViewName', 'handleRequestInternal'],

                    'ServletForwardingController': ['setServletName', 'setBeanName', 'handleRequestInternal', 'useInclude'],

                    'ServletWrappingController': ['setServletClass', 'setServletName', 'setInitParameters',
                                                  'setBeanName', 'afterPropertiesSet', 'handleRequestInternal', 'destroy'],
                    
                    'MultiActionController':['getLastModified', 'handleRequestInternal', 'handleNoSuchRequestHandlingMethod',
                                             'newCommandObject', 'bind', 'createBinder', 'getCommandName', 'initBinder', 'getExceptionHandler']
                    }

    # include inherited methods (important to respect hierarchy order)
    call_back_methods['BaseCommandController'] += call_back_methods['AbstractController']
    call_back_methods['AbstractFormController'] += call_back_methods['BaseCommandController']
    call_back_methods['SimpleFormController'] += call_back_methods['AbstractFormController']
    call_back_methods['CancellableFormController'] += call_back_methods['SimpleFormController']
    call_back_methods['AbstractWizardFormController'] += call_back_methods['AbstractFormController']
    call_back_methods['AbstractCommandController'] += call_back_methods['BaseCommandController']
    call_back_methods['AbstractUrlViewController'] += call_back_methods['AbstractController']
    call_back_methods['UrlFilenameViewController'] += call_back_methods['AbstractUrlViewController']
    call_back_methods['ParameterizableViewController'] += call_back_methods['AbstractController']
    call_back_methods['ServletForwardingController'] += call_back_methods['AbstractController']
    call_back_methods['ServletWrappingController'] += call_back_methods['AbstractController']
    call_back_methods['MultiActionController'] += call_back_methods['AbstractController']

    return call_back_methods
