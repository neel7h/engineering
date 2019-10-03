"""
Doc struts 1 : https://web.archive.org/web/20130104113217/http://struts.apache.org/1.3.10/userGuide/index.html
"""
import cast_upgrade_1_5_11 # @UnusedImport
import cast.analysers.jee
from cast.analysers import create_link, log
from cast.application import open_source_file # @UnresolvedImport
from lxml import etree
from collections import OrderedDict
import glob
import traceback
import os.path
import binascii
from collections import defaultdict
import re

def CRC32_from_file(filename):
    buf = open(filename,'rb').read()
    buf = (binascii.crc32(buf) & 0xFFFFFFFF)
    return "%08X" % buf

class ActionMapping:
    def __init__(self, path, _type, file, parameter, method, struts_version):
        """
        :param struts_version: 1 or 2
        """
        self.path = path
        self._type = _type
        self.file = file
        self.parameter = parameter
        self.method = method
        self.struts_version = struts_version

    def __repr__(self):
        return str(self.path) + ' --> ' + str(self._type)

class Struts(cast.analysers.jee.Extension):
    """
    Parse ...
    """
    class TypeContext:
        def __init__(self, typ):
            self.currentClass = typ
            self.strutsActionClass = None
            self.isInStrutsAction = False
    
    def pushContext(self, typ):
        self.currentContext = self.TypeContext(typ)
        self.contextStack.append(self.currentContext)
        return self.currentContext
    
    def popContext(self):
        self.contextStack.pop()
        if self.contextStack:
            self.currentContext = self.contextStack[-1]
        else:
            self.currentContext = None
            
    class strutsActionClass:

        def __init__(self, _class, strutsVersion, removeActionFromName, inheritedClassName = None):
            self._class = _class
            self.strutsVersion = strutsVersion
            self.implementsSessionAware = False
            self.implementsSelectAction = False
            self.implementsActionSupport = False
            self.inheritedClassesFullnames = []
            self.executeMethod = None
            self.methodsByName = {}
            self.operationCreated = False
            self.actionMapping = None
            self.removeActionFromName = removeActionFromName
            self.createExclamationPath = False
            self.inheritedClassName = inheritedClassName

        def addMethod(self, member):
            name = member.get_name()
            if name in self.methodsByName:
                self.methodsByName[name].append(member)
            else:
                l = []
                l.append(member)
                self.methodsByName[name] = l
                
        def findExecuteMethod(self, strutsActionClasses):
            if 'execute' in self.methodsByName:
                return self.methodsByName['execute'][0]
            for inheritedClassFullname in self.inheritedClassesFullnames:
                if inheritedClassFullname in strutsActionClasses:
                    execute = strutsActionClasses[inheritedClassFullname].findExecuteMethod(strutsActionClasses)
                    if execute:
                        return execute
            if 'perform' in self.methodsByName:
                return self.methodsByName['perform'][0]
            return None
        
        def __repr__(self):
            return self._class.get_fullname() + ' (' + ( self.executeMethod.get_name() if self.executeMethod else 'No execute method' ) + ')'
        
    def __init__(self):
        self.operationsByFullname = {}
        self.web_xml_files = set()
        
    # receive a java parser from platform
    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def receive_java_parser(self, parser):
        log.debug('receive_java_parser')
        self.java_parser = parser
        
    def start_analysis(self, execution_unit):
        log.info('start_analysis')
        self.currentContext = None
        self.contextStack = []
        self.strutsFiltersFullnames = []    # fullnames of classes which contain a doFilter method (they can be referenced in web.xml file for struts2)
        self.strutsActionClassesByFullname = {}   # classes which inherit from org.apache.struts.action.Action (type strutsActionClass)
        
        # all xml files
        self.strutsXmlFiles = []
        self.strutsXmlFilesMain = []

# prepa to struts modules STRUTS-18
        self.strutsXmlIncludes = OrderedDict()
#         self.strutsXmlIncludes = []
        self.nbOperations = 0
        self.urlPatternsAsString = ''
        self.xmlFilesAlreadyReceived = []
        self.webXmlFiles = []
        self.webInfPathes = []
        self.filesByCrc = OrderedDict()
# struts 1
        execution_unit.handle_xml_with_xpath('/struts-config')
# struts 2
        execution_unit.handle_xml_with_xpath('/struts')
#         execution_unit.handle_xml_with_xpath('/validators')
        
        # spring beans
        execution_unit.handle_xml_with_xpath('/beans')

    def retrieve_action_mappings(self, actionMappings, beans, aliases):
            
        for actionMapping in actionMappings:
            # due to spring aliases, one mapping wan generate several receivers
            # default case is having one
            pathes = [actionMapping.path]             
            
            
            # spring framework on top of struts
            # see https://docs.spring.io/spring/docs/2.5.x/javadoc-api/org/springframework/web/struts/DelegatingActionProxy.html
            
            if actionMapping._type == 'org.springframework.web.struts.DelegatingActionProxy':
                log.debug('spring framework...')
                try:
                    actionMapping._type = beans[actionMapping.path]
                    log.debug('using bean instead ' + str(actionMapping))
                    
                    # adding alternate names if exist
                    pathes += aliases[actionMapping.path]
                    
                except KeyError:
                    pass
            
            if actionMapping.struts_version == 1 and actionMapping._type in self.strutsActionClassesByFullname:
                # struts 1
                strutsActionClass = self.strutsActionClassesByFullname[actionMapping._type]
                strutsActionClass.actionMapping = actionMapping
                if strutsActionClass.strutsVersion == '1':
                    
                    for path in pathes:
                        actionMapping.path = path
                        self.createOperation_struts1(actionMapping, strutsActionClass, 'CAST_Struts_Operation')
            
            if actionMapping.struts_version == 2:
                # struts 2
                # do not really know what to do when wildcard + bean...
                if '{' not in actionMapping._type and not actionMapping._type in self.strutsActionClassesByFullname:
    
                    # case spring + struts 2
                    if actionMapping._type in beans:
                        actionMapping._type = beans[actionMapping._type]
                        log.debug('using bean instead ' + str(actionMapping._type))
                    else:
                        log.warning('No class exists for action mapping ' + str(actionMapping))
                        continue
                
                # default
                if not actionMapping.method:
                               
                    actionMapping.method = 'execute'
                
                if '*' in actionMapping.path:
                    
                    # only consider {1} for now
                    
                    log.debug('Wildcard ' + str(actionMapping._type) + ' ' + str(actionMapping.path))
                    class_pattern = actionMapping._type
                    class_pattern = class_pattern.replace('.', '\\.')
                    class_pattern = class_pattern.replace('{1}', '(.*)')
#                     log.info(str(pattern))

                    log.debug('actionMapping.method ' + actionMapping.method)

                    method_pattern = actionMapping.method
                    method_pattern = method_pattern.replace('{1}', '(.*)')
                    
                    
                    
                    for class_fullname in self.strutsActionClassesByFullname:
#                         log.info(class_fullname)
                        class_match = re.search(class_pattern, class_fullname)
                        if not class_match:
                            continue
                        log.debug('matching ' + str(class_fullname) + ' ' + str(len(class_match.groups())))
                        
                        action_path = actionMapping.path
                        
                        if len(class_match.groups()) > 0:
                            action_path = action_path.replace('*', class_match.group(1))
                            log.info(str(action_path))
                        
                        strutsActionClass = self.strutsActionClassesByFullname[class_fullname]
                        file = actionMapping.file
                        
                        if 'execute' in strutsActionClass.methodsByName and actionMapping.method == '{1}':
                            # see : https://struts.apache.org/getting-started/wildcard-method-selection.html#wildcard-method-selection-1
                            #   If there is no value in front of Person, then the Struts 2 framework will call the execute method of the class PersonAction.
                            temp_action_path = action_path.replace('*', '')
                            self.createOperation_struts2(temp_action_path, strutsActionClass, file, strutsActionClass.methodsByName['execute'][0], 'CAST_Struts_Operation')
                        
                        for name, methods in strutsActionClass.methodsByName.items():
                            
                            if name.startswith(('get', 'set')) or name == strutsActionClass._class.get_name():
                                continue
                            
                            log.debug('scanning method ' + name + ' pattern ' + method_pattern)
                            method_match = re.search(method_pattern, name)
                            if not method_match:
                                continue
                            log.debug('matching ' + str(name) + ' ' + str(len(method_match.groups())))
                            
                            temp_action_path = action_path
                            
                            if len(method_match.groups()) > 0:
                                temp_action_path = temp_action_path.replace('*', method_match.group(1))
                                log.debug(str(temp_action_path))
                            
                            # we have found our method
                            # create object and link 
                            for method in methods:                        
                                ast = self.java_parser.get_object_ast(method)
                                if not ast:
                                    continue
                                isPublic = False
                                mods = ast.get_modifiers()
                                if mods:
                                    for mod in mods:
                                        if mod.text == 'public':
                                            isPublic = True
                                            types = ast.type
    #                                         if not types or not astContains(types[0], 'String') or not astContains(ast, 'throws') or astContains(ast, '@Override'):
                                            if not types or not astContains(types[0], 'String') or astContains(ast, '@Override'):
                                                isPublic = False
                                            break
                                if isPublic:
                                    self.createOperation_struts2(temp_action_path, strutsActionClass, file, method, 'CAST_Struts_Operation')
                            
                                    
                else:
                
                    strutsActionClass = self.strutsActionClassesByFullname[actionMapping._type]
                    strutsActionClass.actionMapping = actionMapping
                        
                    # normal case
                    if actionMapping.method in strutsActionClass.methodsByName:
                        meths = strutsActionClass.methodsByName[actionMapping.method]
                        file = strutsActionClass.actionMapping.file
                        for meth in meths:
                            self.createOperation_struts2(actionMapping.path, strutsActionClass, file, meth, 'CAST_Struts_Operation')
                

    def end_analysis(self):
        log.info('end_analysis')
            
        for webInfPath in self.webInfPathes:
            webXmlPath = os.path.join(webInfPath, 'web.xml')
            if not os.path.exists(webXmlPath):
                continue
            if not webXmlPath in self.webXmlFiles:
                self.manage_web_xml(webXmlPath)

        for _class in self.strutsActionClassesByFullname.values():
            log.debug(str(_class))

        # scan bean files 
        beans = {}
        aliases = defaultdict(list)
        for _file in self.strutsXmlFiles:
            if type(_file) is str:
                filepath = _file
            else:
                filepath = _file.get_path()
            log.info("Gets beans and aliases in" + filepath)
            get_beans_and_aliases(_file, beans, aliases)

        for xmlFile in self.strutsXmlFilesMain:
            log.info('Get struts actions in ' + xmlFile.get_path())
            actionMappings = get_struts_action_mapping(xmlFile, self.strutsXmlIncludes)
            self.retrieve_action_mappings(actionMappings, beans, aliases)
            if xmlFile.get_path() in self.strutsXmlIncludes: 
                del self.strutsXmlIncludes[xmlFile.get_path()]
            
        for xmlFile in self.strutsXmlFiles:
            
            # usefull for testing 
            if type(xmlFile) is str:
                filepath = xmlFile
            else:
                filepath = xmlFile.get_path()
                
                
            if not filepath in self.strutsXmlIncludes:
                if not filepath.endswith('web.xml'):
                    log.debug(filepath + ' is not included in web.xml file')
                continue
            log.debug(filepath)
            log.info('Get struts actions in ' + xmlFile.get_path())
            actionMappings = get_struts_action_mapping(xmlFile, self.strutsXmlIncludes)
            self.retrieve_action_mappings(actionMappings, beans, aliases)
            if filepath in self.strutsXmlIncludes:
                del self.strutsXmlIncludes[filepath]
            
        for xmlFile in self.strutsXmlIncludes.keys():
            filepath = xmlFile
            log.debug(filepath)
            log.info('Get struts actions in ' + str(xmlFile))
            actionMappings = get_struts_action_mapping(xmlFile, self.strutsXmlIncludes)
            self.retrieve_action_mappings(actionMappings, beans, aliases)
        self.strutsXmlIncludes.clear()
                    
        for strutsActionClass in self.strutsActionClassesByFullname.values():
            # if wildcard was used in the action mapping or if method was specified
            # the operation were created at retrieve_action_mappings level
            if strutsActionClass.operationCreated:
                continue

            if strutsActionClass.strutsVersion == '2':
                if strutsActionClass.implementsSessionAware or strutsActionClass.implementsActionSupport:
                    executeMethod = strutsActionClass.executeMethod

                    if not executeMethod:
                        executeMethod = strutsActionClass.findExecuteMethod(self.strutsActionClassesByFullname)

                    if executeMethod:
                        log.debug('Execute method found ' + executeMethod.get_fullname())
                        if strutsActionClass.actionMapping:
                            path = strutsActionClass.actionMapping.path
                            file = strutsActionClass.actionMapping.file
                        else:
                            path = '/' + strutsActionClass._class.get_name()
                            file = executeMethod.get_positions()[0].get_file()
                        if strutsActionClass.removeActionFromName and path.endswith('Action'):
                            if not strutsActionClass.actionMapping :
                                path = path[:-6]

                        ast = self.java_parser.get_object_ast(executeMethod)

                        # here we consider the heuristics of creating a link to a specialized execute method
                        # see for example expresspay_brass test
                        for methodName, methods in strutsActionClass.methodsByName.items():
                            if astContains(ast, methodName):
                                log.debug('astContains ' + methodName)
                                for method in methods:
                                    self.createOperation_struts2(path, strutsActionClass, file, method, 'CAST_Struts_Operation')

                # create operations for DMI (Dynamic Method Invocation)
                for _, methods in strutsActionClass.methodsByName.items():
                    for method in methods:
                        methodName = method.get_name()
                        if methodName.startswith(('get', 'set')) or methodName == strutsActionClass._class.get_name():
                            continue

                        ast = self.java_parser.get_object_ast(method)
                        if not ast:
                            continue
                        isPublic = False
                        mods = ast.get_modifiers()
                        if mods:
                            for mod in mods:
                                if mod.text == 'public':
                                    isPublic = True
                                    types = ast.type
                                    if not types or not astContains(types[0], 'String') or astContains(ast, '@Override'):
                                        isPublic = False
                                    break
                        if isPublic:
                            path = '/' + strutsActionClass._class.get_name()
                            file = method.get_positions()[0].get_file()
                            # for struts2 if no action mapping was found
                            # we create an Operation with the Action name (removing the ending Action if needed)
                            if strutsActionClass.removeActionFromName and path.endswith('Action'):
                                if not strutsActionClass.actionMapping :
                                    path = path[:-6]
                            path += ('!' + method.get_name())
                            log.debug(str(strutsActionClass.actionMapping))
                            self.createOperation_struts2(path, strutsActionClass, method.get_positions()[0].get_file(), method, 'CAST_Struts_Operation')
        
        self.strutsActionClassesByFullname = {}
        # debrief 
        log.info(str(self.nbOperations) + ' Struts web service operations created.')
        
    def manage_web_xml(self, path):
        self.webXmlFiles.append(path)
        dirname = os.path.dirname(path)
        if not dirname in self.webInfPathes:
            self.webInfPathes.append(dirname)
        log.info('Web xml file ' + str(path) + ' received.')
        try:
            urlPatterns = []
            get_web_xml_data(path, urlPatterns, self.strutsFiltersFullnames, self.strutsXmlIncludes)

            urlPatterns_splitted = self.urlPatternsAsString.split(";")
            for pattern in urlPatterns:
                if pattern in urlPatterns_splitted:
                    continue
                if not self.urlPatternsAsString:
                    self.urlPatternsAsString = pattern
                else:
                    self.urlPatternsAsString += (';' + str(pattern))
        except Exception as e:
            log.warning('Internal issue: ' + str(e.args[0]))
            log.debug(traceback.format_exc())
        
    def start_web_xml(self, file):

        # strange : from 8.2.0 and above, jee is sending web.xml several times
        if file.get_path() in self.web_xml_files:
            return
        self.web_xml_files.add(file.get_path())
        # avoid scanning it twice
        
        path = os.path.normpath(file.get_path())
        if os.path.exists(path):
            self.manage_web_xml(path)
        
    def start_xml_file(self, file):
        path = os.path.normpath(file.get_path())
        if not path or not os.path.isfile(path):
            return
        
        dirname = os.path.dirname(path)
        if not dirname in self.webInfPathes and dirname.lower().endswith('web-inf'):
            self.webInfPathes.append(dirname)
        if path in self.xmlFilesAlreadyReceived:
            return
        
        # @todo check for some specific files only :
        # web xml
        # struts
        # <beans>
        
        
        self.xmlFilesAlreadyReceived.append(path)
        log.info('File ' + str(path) + ' received.')
        
        # In some cases, a xml file found in src directory and a copy of the same xml file found in build/classes directory 
        # is sent, then duplicate guids appear on operations. Then we must remove the duplicate before.
        crc = CRC32_from_file(path)
        if not crc in self.filesByCrc:
            self.filesByCrc[crc] = path
            if file.get_path().endswith('struts.xml') or file.get_path().endswith('struts-config.xml'):
                self.strutsXmlFilesMain.append(file)
            else:
                self.strutsXmlFiles.append(file) 
        else:
            old_filename = self.filesByCrc[crc]
            new_filename = path
            if os.sep + 'classes' + os.sep in old_filename and not os.sep + 'classes' + os.sep in new_filename:
                log.debug('The same file was found in two directories (only the second one is considered): ' + old_filename + ' and ' + new_filename)
                if file.get_path().endswith('struts.xml') or file.get_path().endswith('struts-config.xml'):
                    self.strutsXmlFilesMain.append(file)
                else:
                    self.strutsXmlFiles.append(file) 
            else:
                log.debug('The same file was found in two directories (only the first one is considered): ' + old_filename + ' and ' + new_filename)
                
    def start_type(self, typ):
        
        if typ.get_name() == '<anonymous>':
            return
        
        log.debug('start_type ' + str(typ))
        self.pushContext(typ)

        # struts 1
        if self.inherits_from(typ, 'org.apache.struts.actions.DispatchAction', True):
            log.info('class inheriting from org.apache.struts.actions.DispatchAction: ' + str(typ))
            self.currentContext.strutsActionClass = self.strutsActionClass(typ, '1', False, 'DispatchAction')

        elif self.inherits_from(typ, 'org.apache.struts.actions.LookupDispatchAction', True):
            log.info('class inheriting from org.apache.struts.actions.LookupDispatchAction: ' + str(typ))
            self.currentContext.strutsActionClass = self.strutsActionClass(typ, '1', False, 'LookupDispatchAction')
        
        elif self.inherits_from(typ, 'org.apache.struts.action.Action', True):
            log.info('class inheriting from org.apache.struts.action.Action: ' + str(typ))
            self.currentContext.strutsActionClass = self.strutsActionClass(typ, '1', False)

        elif self.inherits_from(typ, 'net.jspcontrols.dialogs.actions.SelectAction', True):
            log.info('class inheriting from net.jspcontrols.dialogs.actions.SelectAction: ' + str(typ))
            self.currentContext.strutsActionClass = self.strutsActionClass(typ, '1', False)
            self.currentContext.strutsActionClass.implementsSelectAction = True
        
        # struts 2
        if self.inherits_from(typ, 'org.apache.struts2.interceptor.SessionAware', False):
            log.info('class implementing org.apache.struts2.interceptor.SessionAware: ' + str(typ))
            self.currentContext.strutsActionClass = self.strutsActionClass(typ, '2', True)
            self.currentContext.strutsActionClass.implementsSessionAware = True

        if self.inherits_from(typ, 'com.opensymphony.xwork2.ActionSupport', True):
            log.info('class inheriting from com.opensymphony.xwork2.ActionSupport: ' + str(typ))
            self.currentContext.strutsActionClass = self.strutsActionClass(typ, '2', True)
            self.currentContext.strutsActionClass.implementsActionSupport = True

        if self.currentContext.strutsActionClass:
            for parentTyp in typ.get_inherited_types():
                self.currentContext.strutsActionClass.inheritedClassesFullnames.append(parentTyp.get_fullname())
            self.strutsActionClassesByFullname[typ.get_fullname()] = self.currentContext.strutsActionClass
            self.currentContext.isInStrutsAction = True
            return

        try:
            compilation_unit = self.java_parser.parse(typ.get_position().get_file().get_path())
            ast = self.java_parser.get_object_ast(typ)
            annotations = ast.get_annotations()
            for annotation in annotations:
                name = annotation.get_type_name()
                possible_names = compilation_unit.get_possible_qualified_names(name)
                if 'org.apache.struts2.config.Results' in possible_names:
                    if astContains(annotation, 'ActionChainResult.class') or astContains(annotation, 'TilesResult.class'):
                        log.info('class with org.apache.struts2.config.Results annotation: ' + str(typ))
                        self.currentContext.strutsActionClass = self.strutsActionClass(typ, '2', True)
                        self.currentContext.strutsActionClass.createExclamationPath = True
                        self.strutsActionClassesByFullname[typ.get_fullname()] = self.currentContext.strutsActionClass
                        self.currentContext.isInStrutsAction = True
                        return
        except:
            log.debug(traceback.format_exc())

    def end_type(self, typ):
        
        if typ.get_name() == '<anonymous>':
            return
        
        log.debug('end_type ' + str(typ))
        self.popContext()

    def start_member(self, member):
        # @type member:cast.analayzer.Member
        
        if '<anonymous>' in member.get_fullname():
            return
        
        if not self.currentContext:
            return
        if not isinstance(member, cast.analysers.Method):
            return
        log.debug('start_member ' + str(member))
        if self.currentContext.isInStrutsAction:
            if member.get_name() in ['execute', 'perform']:
                log.info('execute method found' + str(member.get_fullname()))
                self.currentContext.strutsActionClass.executeMethod = member
            self.currentContext.strutsActionClass.addMethod(member)
            return
        if member.get_name() == 'doFilter':
            self.strutsFiltersFullnames.append(self.currentContext.currentClass.get_fullname())

    def createOperation(self, operationName, operationFullname, operationType, position, parentObject, file, isStruts2):
                       
        if operationFullname in self.operationsByFullname:
            # we create only the the link to the operation created first
            return self.operationsByFullname[operationFullname]
        else:
            operation_object = cast.analysers.CustomObject()
            operation_object.set_type(operationType)
            operation_object.set_name(operationName)
            operation_object.set_parent(parentObject)
            log.info('creating operation ' + operationFullname)
            operation_object.set_fullname(operationFullname)
            operation_object.set_guid(operationFullname)
            try:
                operation_object.save()
                self.operationsByFullname[operationFullname] = operation_object        
                if not type(file) is str:
                    operation_object.save_position(position)
            
                try:
                    if self.urlPatternsAsString == None:
                        self.urlPatternsAsString = '*.action' if isStruts2 else '*.do'
                    if isStruts2:
                        if not '*.action' in self.urlPatternsAsString:
                            self.urlPatternsAsString += ';*.action'
                    else:
                        if not '*.do' in self.urlPatternsAsString:
                            self.urlPatternsAsString += ';*.do'
                    operation_object.save_property('CAST_WebService_Operation.urlPatterns', self.urlPatternsAsString)
                except:
                    log.warning('Internal issue saving CAST_WebService_Operation.urlPatterns')
                    
                self.nbOperations += 1
            except:
                log.warning('Internal issue saving Struts 1 operation')
                log.debug(traceback.format_exc())
                return None
        return operation_object
        
    def createOperation_struts1(self, actionMapping, strutsActionClass, operationType):
        
        actionMappingPath = actionMapping.path
        file = actionMapping.file
        if type(file) is str:
            filepath = file
        else:
            filepath = file.get_path()

        if strutsActionClass.inheritedClassName in ['DispatchAction', 'LookupDispatchAction'] and actionMapping.parameter:
            for methods in strutsActionClass.methodsByName.values():
                for method in methods:
                    # keep only specific methods
                    if not self.is_struts1_action_method(method):
                        continue

                    name = actionMappingPath + '?' + str(actionMapping.parameter) + '=' + method.get_name()
                    if actionMappingPath.startswith('/'):
                        fullname = filepath + '/' + operationType + name
                    else:
                        fullname = filepath + '/' + operationType + '/' + name
                    operation_object = self.createOperation(name, fullname, operationType, method.get_positions()[0], strutsActionClass._class, file, False)
                    if not operation_object:
                        continue
                    create_link('callLink', operation_object, method, method.get_positions()[0])
            return

        if strutsActionClass.implementsSelectAction :
            try :
                key_method = strutsActionClass.methodsByName['getKeyMethodMap'][0]
                ast = self.java_parser.get_object_ast(key_method)
                statements = ast.get_statements()
                methods_aliases = OrderedDict()
                for statement in statements:
                    if statement.get_type() == "ExpressionStatement" :
                        for child in statement.get_children():
                            if child.get_type() == "Parenthesis":
                                paren_children = list(child.get_children())
                                break

                        if paren_children[1].text != "getInitKey":
                            log.info("Could not interpret getKeyMethodMap. No Operation will be created for this SelectAction.")

                        for i, tok in enumerate(paren_children):
                            if tok.text == "+":
                                methods_aliases[paren_children[i + 3].text[1:-1]] = "DIALOG-EVENT" + paren_children[i + 1].text[1:-1]
            except :
                return

            for methods in strutsActionClass.methodsByName.values():
                for method in methods:
                    if method.get_name() == "getKeyMethodMap":
                        continue
                    # keep only specific methods
                    if not self.is_struts1_action_method(method):
                        continue
                    if not method.get_name() in methods_aliases:
                        continue
                    name = actionMappingPath + '?' + methods_aliases[method.get_name()]
                    if actionMappingPath.startswith('/'):
                        fullname = filepath + '/' + operationType + name
                    else:
                        fullname = filepath + '/' + operationType + '/' + name
                    operation_object = self.createOperation(name, fullname, operationType, method.get_positions()[0], strutsActionClass._class, file, False)
                    if not operation_object:
                        continue
                    create_link('callLink', operation_object, method, method.get_positions()[0])
            return
        
        strutsActionClass.operationCreated = True
        if actionMappingPath.startswith('/'):
            fullname = filepath + '/' + operationType + actionMappingPath
        else:
            fullname = filepath + '/' + operationType + '/' + actionMappingPath
        operation_object = self.createOperation(actionMappingPath, fullname, operationType, strutsActionClass._class.get_positions()[0], strutsActionClass._class, file, False)
        if not operation_object:
            return

        executeMethod = strutsActionClass.findExecuteMethod(self.strutsActionClassesByFullname)
        if executeMethod:
            log.debug('Execute method found ' + executeMethod.get_fullname())
            ast = self.java_parser.get_object_ast(executeMethod)
            
            # here we consider the heuristics of creating a link to a specialized execute method
            # see for example expresspay_brass test
            for methodName, methods in strutsActionClass.methodsByName.items():
                if astContains(ast, methodName):
                    log.debug('astContains ' + methodName)
                    for method in methods:
                        create_link('callLink', operation_object, method, method.get_positions()[0])                        

    def createOperation_struts2(self, actionMappingPath, strutsActionClass, file, meth, operationType):
        
        if not strutsActionClass.createExclamationPath:
            strutsActionClass.operationCreated = True
            if actionMappingPath.startswith('/'):
                fullname = strutsActionClass._class.get_fullname() + '/' + operationType + actionMappingPath
            else:
                fullname = strutsActionClass._class.get_fullname() + '/' + operationType + '/' + actionMappingPath
            operation_object = self.createOperation(actionMappingPath, fullname, operationType, meth.get_positions()[0], strutsActionClass._class, file, True)
            if not operation_object:
                return
    
            create_link('callLink', operation_object, meth, meth.get_positions()[0])
            
            return
        
        className = strutsActionClass._class.get_name()

        if className.endswith('Action'):
            operationName = actionMappingPath
            fullname = strutsActionClass._class.get_fullname() + '/' + operationType + operationName
            operation_object = self.createOperation(operationName, fullname, operationType, meth.get_positions()[0], strutsActionClass._class, file, True)
            if not operation_object:
                return
            create_link('callLink', operation_object, meth, meth.get_positions()[0])
        

    def inherits_from(self, typ, fullname, recursive = True):
        """
        True if a given class inherits from a class whose fullname is @fullname
        
        :param typ: cast.analyzer.Type
        :param fullname: str
        """
        for parentTyp in typ.get_inherited_types():
            if parentTyp.get_fullname() == fullname:
                return True
        if not recursive:
            compilation_unit = self.java_parser.parse(typ.get_position().get_file().get_path())
            ast = self.java_parser.get_object_ast(typ)
            if ast:
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
        
        # second chance : using alternate technique        
        compilation_unit = self.java_parser.parse(typ.get_position().get_file().get_path())
        ast = self.java_parser.get_object_ast(typ)
        if ast:
            names = getClassInheritances(ast)
            for name in names:
                possible_names = compilation_unit.get_possible_qualified_names(name)
                if possible_names:
                    for possible_name in possible_names:
                        if possible_name == fullname:
                            return True
        return False
        
    def is_struts1_action_method(self, method):
        """
        True when a method has the correct signature of an execute method
        """
        compilation_unit = self.java_parser.parse(method.get_position().get_file().get_path())
        ast = self.java_parser.get_object_ast(method)
        
        modifiers = ast.get_modifiers()
        log.debug(str(modifiers))
        if 'public' not in modifiers:
            log.debug('not public')
            return False

        # @todo wait for some enhancement to check the return type
        
        # check the parameter types
        parameters = ast.get_parameters()
        if len(parameters) != 4:
            log.debug('not the correct profile')
            return False
            
        def parameter_has_type(index, type_full_name):
            parameter = parameters[index]
            try :
                return type_full_name in compilation_unit.get_possible_qualified_names(parameter.get_type().get_type_name())
            except AttributeError:
                log.debug("Type name not found for " + str(parameter))
                return False

        if parameter_has_type(0, 'org.apache.struts.action.ActionMapping') and \
           parameter_has_type(1, 'org.apache.struts.action.ActionForm') and \
           parameter_has_type(2, 'javax.servlet.http.HttpServletRequest') and \
           parameter_has_type(3, 'javax.servlet.http.HttpServletResponse'):
            return True
        else:
            return False
        
        
        
def get_overriden(_type, member):
    """
    Get the ancestor's member this member overrides
    """
    
    member_name = member.get_name()
    
    result = []
    
    for parent in _type.get_inherited_types():
        
        for child in parent.get_children():
            if child.get_name() == member_name:
                result.append(child)
        
        result += get_overriden(parent, member)
        
    return result

def get_struts_action_mapping(fileContent, includes = None):
    """
    We take interest in following part of xml file:
    
<struts-config>
  <action-mappings>
    
    <action path="/creditPolicy" 
        type="com.sbc.epay.ecommerceorder.struts.creditpolicy.StrutsActionCreditPolicy"
         name="creditPolicyForm" validate="false" scope="session">
        <forward name="autoPayOnly" path="xpayswot/AutopayOnly.jsp"/>
        <forward name="autoPayWithPayment" path="xpayswot/AutopayWithPayment.jsp"/>
        <forward name="securityDeposit" path="xpayswot/SecurityDeposit.jsp"/>
        <forward name="advancePayment" path="xpayswot/AdvancePayment.jsp"/>
        <forward name="creditPolicyForward" path="xpayswot/CreditPolicyPageForward.jsp"/>
        <forward name="systemError"  path="xpayswot/SystemError.jsp"/>
    </action>
    ...
  </action-mappings>
</struts-config>

Or:

<struts>
    <package name="chapterFivePublic" namespace="/chapterFive" extends="struts-default">
    
        <action name="Login" class="manning.chapterFive.Login" method="populatePool">
                    <result type="redirect">/chapterFive/secure/AdminPortfolio.action</result>
                    <result name="input">/chapterFive/Login.jsp</result>
        </action>

    </package>
</struts>
    
    """
    f = fileContent
    try:
        if type(fileContent) is str:
            filepath = fileContent
        else:
            filepath = fileContent.get_path()
        if not os.path.isfile(filepath):
            log.debug('file does not exist: ' + filepath)
            return []
        
        with open_source_file(filepath) as myfile:
            fileContent=myfile.read()
                
        fileContent = remove_utf8_from_web_xml(fileContent)
        fileContent = remove_xmlns_from_web_xml(fileContent)
        tree = etree.fromstring(fileContent)

        if includes != None:
            for include in tree.xpath('/struts/include'):
                file = include.get('file')
                if file:
                    fullpath = os.path.abspath(os.path.join(os.path.dirname(f.get_path()), file))
                    if not fullpath in includes:
#                         includes.append(fullpath)
                        includes[fullpath] = ''
                        log.info('include ' + fullpath)
      
        actionMappings = []
        
        # struts 1
        for actionMapping in tree.xpath('/struts-config/action-mappings/action'):
            path = actionMapping.get('path')
            if includes != None and filepath in includes:
                subapp = includes[filepath]
                if subapp:
#                     path = '/' + subapp + path
# As a first approx, if filepath = 'struts-<something>.xml', take <something> in lowercase as prefix (as in html5 extension for client jsp part)
                    basename = os.path.basename(filepath).lower()
                    if basename.startswith('struts-') and basename.endswith('.xml'):
                        subapp = os.path.basename(filepath)[7:-4]
                        path = '/' + subapp + path
                        
            _type = actionMapping.get('type')
            parameter = actionMapping.get('parameter')
            actionMappings.append(ActionMapping(path, _type, f, parameter, None, 1))

        # struts 2
        for actionMapping in tree.xpath('/struts/package/action'):
            # @todo handle namespace and do not add / if it already starts by / ?
            path = actionMapping.get('name')
            if not path.startswith('/'):
                path = '/' + path
            _type = actionMapping.get('class')
            method = actionMapping.get('method')
            if _type:
                actionMappings.append(ActionMapping(path, _type, f, None, method, 2))
        
        return actionMappings

    except Exception:
        # BEWARE!! We can not filter this kind of generated file in the start_xml_file method because at this time,
        # the get_file() gives a real path in LISA directory.
        # JEE analyzer must modify the path of the file object.
        if type(f) is str:
            filepath = f
        else:
            filepath = f.get_path()
        if '.jar]' in filepath:
            return []
        log.warning('Internal issue during parsing of ' + filepath)
        log.debug(traceback.format_exc())
        if isinstance(fileContent, str):
            log.warning(fileContent)
        return []
    
def astContains(ast, methodName):
    
    try:
        if ast.text == methodName:
            return True
        
        for child in ast.get_children():
            try:
                if child.text == methodName:
                    return True
            except:
                log.debug(traceback.format_exc())
        for child in ast.get_children():
            if astContains(child, methodName):
                return True
    except:
        log.debug(traceback.format_exc())
    return False

def getClassInheritances(ast):
    
    l = []
    try:
        extends = ast.get_extends()
        if extends:
            for extend in extends:
                if hasattr(extend, 'get_type_name'):
                    l.append(extend.get_type_name())
    except:
        log.debug(traceback.format_exc())
    return l

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

def get_web_xml_data(path, urlPatterns, strutsFiltersFullnames, includes):
    """
    We take interest in following part of web.xml file for struts1:
    
<web-app xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://java.sun.com/xml/ns/javaee" xmlns:web="http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" xsi:schemaLocation="http://java.sun.com/xml/ns/javaee http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" id="WebApp_ID" version="2.5">
    <servlet>
        <servlet-name>action</servlet-name>
        <servlet-class>org.apache.struts.action.ActionServlet</servlet-class>
        <load-on-startup>1</load-on-startup>
    </servlet>
    
    <servlet-mapping>
        <servlet-name>action</servlet-name>
        <url-pattern>*.perform</url-pattern>
    </servlet-mapping>
</web-app>
    
    We search for url patterns corresponding to struts 1.1 (<servlet-class>org.apache.struts.action.ActionServlet</servlet-class>)
    
    """
    """
    We take interest in following part of web.xml file for struts2:
    
<web-app xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://java.sun.com/xml/ns/javaee" xmlns:web="http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" xsi:schemaLocation="http://java.sun.com/xml/ns/javaee http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" id="WebApp_ID" version="2.5">
    <filter>
        <display-name>BaseStrutsFilter</display-name>
        <filter-name>BaseStrutsFilter</filter-name>
        <filter-class>br.gov.mapa.sipe.apresentacao.filter.BaseStrutsSipeFilter</filter-class>
        <init-param>
              <param-name>public-url</param-name>
              <param-value>/sipe/imprimirGruPublica.action</param-value>
        </init-param>
    </filter>
    
    <filter-mapping>
        <filter-name>BaseStrutsFilter</filter-name>
        <url-pattern>*.action</url-pattern>
        <dispatcher>REQUEST</dispatcher>
        <dispatcher>FORWARD</dispatcher>
    </filter-mapping>
    <filter>
        <filter-name>struts2</filter-name>
        <filter-class>org.apache.struts2.dispatcher.FilterDispatcher</filter-class>
        <init-param>
            <param-name>actionPackages</param-name>
            <param-value>br.gov.mapa.sipe.apresentacao.action, br.gov.mapa.arquitetura.apresentacao.struts</param-value>
        </init-param>
    </filter>    
    <filter-mapping>
        <filter-name>struts2</filter-name>
        <url-pattern>/*</url-pattern>
        <dispatcher>REQUEST</dispatcher>
        <dispatcher>ERROR</dispatcher> 
    </filter-mapping>
</web-app>
    
    We search for url patterns corresponding to struts 1.1 (<servlet-class>org.apache.struts.action.ActionServlet</servlet-class>)
    
    """
    fileContent = ''
    try:
        with open_source_file(path) as myfile:
            fileContent=myfile.read()
                
        fileContent = remove_utf8_from_web_xml(fileContent)
        fileContent = remove_xmlns_from_web_xml(fileContent)
        tree = etree.fromstring(fileContent)
      
        servletMappings = {}
        struts1Found = False

        for servletMapping in tree.xpath('/web-app/servlet-mapping'):
            name = servletMapping.find('servlet-name').text
            urlPattern = servletMapping.find('url-pattern').text
            if name and urlPattern:
                servletMappings[name] = urlPattern
      
        for servlet in tree.xpath('/web-app/servlet'):

            struts = False
            configName = None
            initParamNodes = servlet.findall('init-param')
            if initParamNodes:
                for param in initParamNodes:
                    try:
                        name = param[0].text
                        log.debug('name ' + name)
                        values = param[1].text.split(',')
                        for value in values:
                            try:
                                if value.startswith('/WEB-INF/'):
                                    filepath = os.path.abspath(os.path.join(os.path.dirname(path), value[9:]))
                                    if '*' in filepath:
                                        l = glob.glob(filepath)
                                        if l:
                                            for filepath in l:
                                                if not filepath in includes:
                                                    log.info('include ' + filepath)
                                                    if value.lower() == '/web-inf/struts-config.xml':
                                                        struts = True
                                                        configName = name
                                                        log.info('configName found  ' + configName)
                                                        includes[filepath] = ''
                                                    else:
                                                        if configName and name.startswith(configName + '/'):
                                                            subApp = name[name.find('/') + 1:]
                                                            log.info('subapplication found: ' + subApp)
                                                            includes[filepath] = subApp
                                                        else:
                                                            includes[filepath] = ''
                                    else:
                                        if not filepath in includes:
                                            log.info('include ' + filepath)
                                            if value.lower() == '/web-inf/struts-config.xml':
                                                struts = True
                                                configName = name
                                                log.info('configName found  ' + configName)
                                                includes[filepath] = ''
                                            else:
                                                if configName and name.startswith(configName + '/'):
                                                    subApp = name[name.find('/') + 1:]
                                                    log.info('subapplication found: ' + subApp)
                                                    includes[filepath] = subApp
                                                else:
                                                    includes[filepath] = ''
                            except:
                                log.debug(traceback.format_exc())
                    except:
                        log.debug(traceback.format_exc())
            
            # not mandatory, example <jsp-file> ...
            servletClassNode = servlet.find('servlet-class')
            if servletClassNode is None:
                continue
            
            servletClass = servletClassNode.text
            if not servletClass == 'org.apache.struts.action.ActionServlet':
                if not struts:
                    continue
            struts1Found = True
            servletName = servlet.find('servlet-name').text
            if not servletName:
                continue
            log.info('servlet ' + servletName)
            if servletName in servletMappings:
                log.info('pattern ' + servletMappings[servletName] + ' found')
                if not servletMappings[servletName] in urlPatterns:
                    urlPatterns.append(servletMappings[servletName])
                    
        if struts1Found:
            return

        filterMappings = {}
     
        for filterMapping in tree.xpath('/web-app/filter-mapping'):
            name = filterMapping.find('filter-name').text
            urlPattern = filterMapping.find('url-pattern')
            # argh... 
            if urlPattern is not None:
                urlPattern = urlPattern.text
            if name and urlPattern:
                filterMappings[name] = urlPattern
        
        for _filter in tree.xpath('/web-app/filter'):
            
            filterClassNode = _filter.find('filter-class')
            if filterClassNode is None:
                continue
            
            filterClass = filterClassNode.text
            listFilters = ['org.apache.struts2.dispatcher.FilterDispatcher'
                           , 'org.apache.struts2.dispatcher.ng.filter.StrutsPrepareAndExecuteFilter'
                           ]
            if filterClass not in listFilters and not filterClass in strutsFiltersFullnames:
                continue
            struts1Found = True
            filterName = _filter.find('filter-name').text
            if not filterName:
                continue
            if filterName in filterMappings:
                log.info('pattern ' + filterMappings[filterName] + ' found')
                if not filterMappings[filterName] in urlPatterns:
                    urlPatterns.append(filterMappings[filterName])

    except Exception as e:
        log.warning('Internal issue: ' + str(e.args[0]))
        log.debug(traceback.format_exc())
        if isinstance(fileContent, str):
            log.warning(fileContent)


def get_beans_and_aliases(path, beans, aliases):
    """
    Scan a bean file searching for bean definitions and aliases
    """
    if type(path) is str:
        filepath = path
    else:
        filepath = path.get_path()
    if not os.path.isfile(filepath):
        log.debug('file does not exist: ' + filepath)
        return []
    
    with open_source_file(filepath) as myfile:
        fileContent=myfile.read()
            
    fileContent = remove_utf8_from_web_xml(fileContent)
    fileContent = remove_xmlns_from_web_xml(fileContent)
    # see https://stackoverflow.com/questions/18692965/how-do-i-skip-validating-the-uri-in-lxml
    tree = etree.fromstring(fileContent, parser=etree.XMLParser(recover=True))
    if not tree :
        log.debug("problem with file:  " + filepath)
        return []

    for bean in tree.xpath('/beans/bean'):
        
        # see https://stackoverflow.com/questions/874505/difference-between-using-bean-id-and-name-in-spring-configuration-file
        # name, id acts as aliases, name can be ',' ';' or ' ' separated
        name = bean.get('name')
        _id = bean.get('id')
        _class = bean.get('class')

        if name and _class:
            # not sure we can mix different separators
            if ',' in name:
                names = name.split(',')
            elif ';' in name:
                names = name.split(';')
            else:
                names = name.split(' ')
            for small_name in names:
                log.debug('found bean ' + small_name + ' ' + _class)
                beans[small_name] = _class
        
        if _id and _class:
            log.debug('found bean ' + _id + ' ' + _class)
            beans[_id] = _class

    for alias in tree.xpath('/beans/alias'):
        
        # name of the alias
        alias_name = alias.get('alias')
        # bean name
        bean_name = alias.get('name')

        if alias_name and bean_name:
            
            log.debug('found alias ' + alias_name + ' ' + bean_name)
            aliases[bean_name].append(alias_name)
           
    
            
        
