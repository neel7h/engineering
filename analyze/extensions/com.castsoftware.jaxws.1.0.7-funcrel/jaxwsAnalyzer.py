'''
Created on Oct 27, 2017

@author: RKI
'''
import cast_upgrade_1_5_25 # @UnusedImport
from cast.analysers import log, jee, Bookmark, create_link, CustomObject, get_cast_version
import cast
from lxml import etree
import os
from operation import Operation
from cast.application import open_source_file
from distutils.version import StrictVersion



def read_xml_file(path):
    """
    Read an xml file and return the root node as for lxml.etree
    """
    
    import lxml.etree as ET
    
    def remove_utf8_from_xml(fileContent):
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
    
    def remove_xmlns_from_xml(fileContent):
        """
        Removes the "xmlns=" part from file content because lxml api supports this part only by specifying exactly
        its value whenever we want to access a part of xml content, and its value can change between xml files.
        
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
    
    def remove_namespaces(root):
        """Remove namespaces in the passed document in place."""
        for elem in root.getiterator():
            if elem.tag is not etree.Comment and '}' in elem.tag:
                elem.tag = elem.tag.split('}')[1]

                
    with open_source_file(path) as f:
        file_content = f.read()
        file_content = remove_utf8_from_xml(file_content)
        file_content = remove_xmlns_from_xml(file_content)
        
        result = ET.fromstring(file_content, parser=ET.XMLParser(recover=True))
        remove_namespaces(result)
        
        return result


def get_matched_value(strVal, key):
    retVal =''
    indexStart = strVal.find(key)
    indexValueStart = strVal.find('"', indexStart)
    if indexValueStart > 0:
        indexValueEnd = strVal.find('"', indexValueStart + 1)
        if indexValueEnd > 0:
            retVal = strVal[indexValueStart+1:indexValueEnd]
    return retVal
    
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

def get_parent(_type):
    '''
    Returns the parent of a class. It do not gives the Land.Object
    '''
    for parent in _type.get_inherited_types():
        if parent.get_fullname() != 'java.lang.Object':
            return parent
        
class JAXWS(jee.Extension):
    def __init__(self):
        self.fielPath = ""
        self.wbsClient = None
        self.endPointNameList = []
        self.endPointNamesInXml = []
        self.webMethodNameList = {}
        self.endPoint = None
        self.portType = None
        self.typeList = []
        self.serviceName = None
        self.portTypeName = None
        self.result = None
        self.webServerClass = []
        self.parentIfaceText = None
        self.wsdlPortTypeAndOpNameList = {}
        self.interfaceName = ""
        self.handleChainClassAndMethods = {}
        self.ePoint = False
        self.nbOperations = 0
        self.nbWebService = 0
        self.nbPortType = 0
        self.impleMentingMember = None
        self.allJaxWsEndPoints = []
        self.wsTemplateImportPresent = False
        self.allJaxWsEndPointsBean = {}
        self.isImplementingClass = False
        self.wsTemplateFunctions = ('marshalSendAndReceive','sendSourceAndReceive')
        self.handleChainClass={}
        self.handlerChainRelatedOperations={}
        self.cxfBased = False
        self.qNameImport = False
        self.listOfWsCalledInQname = []
        self.createdJvOperations = {}
        
    def start_web_xml(self, f):
        '''
        Parses the web.xml file and gets the context file name. Then it locates the context file
        and parse it to get the jaxws:endpoint and bean:id
        '''
        log.info('Started Application...')
       
        tree = read_xml_file(f.get_path())
                
        webXmlPath = f.get_path()
        name= None
        
        allNames = []

        for contextFile in tree.xpath('/web-app/context-param/param-value'):
            
            allNames.append(contextFile.text)
            self.cxfBased = True
                 
        if not len(allNames):
            log.debug('The param-value is not found returning...' + str(f))
            return
        
        for elements in allNames:
            webXmlPath = f.get_path()
            name = elements.split('/')[-1].strip()
            if webXmlPath is not None:
                webXmlPath=webXmlPath.replace('web.xml',name) 
             
            
            if not webXmlPath.endswith('.xml'):
                log.debug('Not an xml file to process returning '+ webXmlPath)
                continue 
            
            if os.path.isfile(webXmlPath):
                log.debug('Context file found in the same path as web.xml')
                
            else:
                # file is not present at the same path where web.xml is present
                # it uses web.xml in order to distinguish several cxf files and take only one
                # @todo : remove this ???
                # in fact we do not need to scan the folder as we should already have all the xml files pathes from configuration
                srcIndex = webXmlPath.find('src')
                pathLenth = (len(webXmlPath) - srcIndex) #we need to go uptot hte src folder and search for the file
                newPath = webXmlPath[:-pathLenth]+'src'
                for root,dirs, files in os.walk(newPath):
                    for fileName in files:
                        if fileName == name:
                            webXmlPath = os.path.abspath(os.path.join(root, name))
            log.debug(str(webXmlPath) + ' cxf path')
           
            if os.path.exists(webXmlPath):
                try:
                    tree = etree.parse(webXmlPath)
                    rootn = tree.getroot()
                    for item in rootn: # iterate on all child nodes of root
                        if item.tag is etree.Comment:
                            # skipp comment nodes
                            continue
                        # jaxrs:server also exist in cxf files
                        # see ticket https://castsoftware.zendesk.com/agent/tickets/15685
                        if item.tag.endswith('}server') and 'jaxws' in item.tag:
                            log.debug(str(item.tag))
                            self.allJaxWsEndPoints.append(item.attrib['serviceBean'])
                        if item.tag.endswith('}endpoint') and 'jaxws' in item.tag:
                            self.allJaxWsEndPoints.append(item.attrib['implementor'].strip())
                        if item.tag.endswith('}bean'):
                            try:
                                idd =item.attrib['id']
                                cls = item.attrib['class']
                                self.allJaxWsEndPointsBean[idd] = cls
                            except:
                                log.debug('Start_web_xml: Attribute not found.')
                except etree.XMLSyntaxError: # not always a correct xml file
                    pass
                    
        log.debug(str(self.allJaxWsEndPoints))
        log.debug(str(self.allJaxWsEndPointsBean))
        self.handleCXFType()
        log.info('Web Files read .....')
        
    def parseMethod(self,methodBody):
        if hasattr(methodBody, 'children'):
            for item in methodBody:
                if hasattr(item, 'children'):
                    self.parseMethod(item)
        else:
            if len(methodBody) > 0:
                prevToken = ''
                for inner in methodBody:
                    if str(inner.get_type()).startswith('CurlyBracket'):
                        self.parseMethod(inner.children)
                    else:
                        if str(inner.get_type()).startswith('Token.Generic'):
                            if inner.text == 'QName':
                                prevToken = 'QName'
                                
                        if str(inner.get_type()).startswith('ExpressionStatement'):
                            for ele in inner.children:
                                if ele.get_type()=='Parenthesis' and prevToken == 'QName':
                                    if hasattr(ele, 'children'):
                                        for tok in ele.children:
                                            if tok.text is not None:
                                                if not any (subString in [',',' ','(',')'] for subString in tok.text) and "http://" not in tok.text:
                                                    self.listOfWsCalledInQname.append(tok.text.strip('\"'))
                                    prevToken=''
                        
    
    def start_analysis(self,options):
        '''
        starts the analysis
        '''
        log.info('JAX-WS Analyzer Started')
        self.readWsdlAndCreatePortTypeAndOpNameList(options)
        for key,value in self.wsdlPortTypeAndOpNameList.items():
            for val in value:
                log.info(str(key) + '--->' + val.opName)
        
    # receive a java parser from platform
    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def receive_java_parser(self, parser):
        '''
        Gets the java parser to be used further in the code
        '''
        self.java_parser = parser
        log.debug('Successfully receive_java_parser')
        
    def createWbsObject(self,typ,annoValue):
        '''
        creates the web service object using the attributes from the annotations
        also creates the relyon link between the wbs and the typ
        '''
        if annoValue is None:
            self.serviceName = str(typ.get_name()) + 'Service'
            
        try:
            portNameVal = annoValue['portName']
        except:
            portNameVal = str(typ.get_name()) + 'port'
            
        try:
            self.serviceName = annoValue['serviceName']
            if self.serviceName is None:
                self.serviceName = annoValue['name']
        except:
            try:
                self.serviceName = annoValue['name']
            except:
                pass
        if self.serviceName is None:
            self.serviceName = str(typ.get_name()) + 'Service'
       
        try:
            targetNamespaceVal = annoValue['targetNamespace']
        except:
            targetNamespaceVal = 'NeedToFindOut'

        try:
            wsdlLocationVal = annoValue['wsdlLocation']
        except:
            wsdlLocationVal = 'wsdlLocation'
           
        web_service_object = CustomObject()
        web_service_object.set_name(self.serviceName)
        web_service_object.set_type('SOAP_JV_SERVICE')
        parentFile = typ.get_position().get_file() 
        web_service_object.set_parent(parentFile)
        self.fielPath = parentFile.get_fullname()
        web_service_object.set_fullname(self.serviceName) #Same as name as per legacy c++
        web_service_object.set_guid(self.fielPath+self.serviceName)
        web_service_object.save()
        web_service_object.save_position(typ.get_position())
        create_link('relyonLink',web_service_object,typ)
        log.info('SOAP_JV_SERVICE object created with name '+self.serviceName)
        self.nbWebService += 1
        try:
            self.portTypeName = annoValue['endpointInterface']
            if self.portTypeName is None:
                self.ePoint = False
            else:
                self.ePoint = True
        except:
            self.ePoint = False
        
        portTypeFullName = self.portTypeName
        if self.portTypeName is None:
            self.portTypeName = typ.get_name()
            portTypeFullName = typ.get_fullname()
        else:
            self.portTypeName = self.portTypeName.split('.')[-1]
            portTypeFullName = self.serviceName + '.' + self.portTypeName
        
        self.portType = self.createPortType(parentFile,portTypeFullName,typ)
                   
    def createPortType(self,pFile,portTypeFullName,type):
        '''
        creates the port type where parent is the java file. Port type name  and full name are 
        constructed as per the convention
        '''
        portType = CustomObject()
        portType.set_name(self.portTypeName)
        portType.set_type('SOAP_JV_PORTTYPE')
        portType.set_parent(pFile)
        portType.set_fullname(portTypeFullName)
        portType.set_guid(self.fielPath + portTypeFullName)
        portType.save()
        portType.save_position(type.get_position())
        log.info('SOAP_JV_PORTTYPE object created with name '+ self.portTypeName + ' and FullName '+ portTypeFullName)
        self.nbPortType+=1
        return portType
              
    def createOperation(self,member,param): 
        '''
        creates the operation using the member and the attributes of the annotation
        '''
        
        if not self.serviceName or not self.portTypeName:
            return
        
        excludeParam = 'false'
        if param is not None:
            excludeParam = param.get('exclude','false')
               
        if excludeParam == 'true':
            log.info('Exclude attribute is true so not creating the operation for '+ member.get_name())
            return  
        
        try:
            operationName = param['operationName']
            log.info('OperationName found as  '+operationName)
        except:
            operationName = member.get_name()
            log.info('OperationName not found and set as  '+operationName)
       
        opFullName = self.serviceName + '.'+ self.portTypeName + '.'+operationName
        if self.portType not in self.createdJvOperations.keys():
            self.createdJvOperations[self.portType] = set()
            
        if opFullName.lower() not in self.createdJvOperations[self.portType]:
            
            tempList = [operationName,member,self.portTypeName]
            self.webMethodNameList[member.get_fullname()] = tempList
            opObject = CustomObject()
            opObject.set_name(operationName)
            opObject.set_type('SOAP_JV_OPERATION')
            opObject.set_parent(self.portType)
            opObject.set_fullname(opFullName)  
            #opObject.set_guid(self.fielPath+operationName)
            opObject.save()
            opObject.save_position(member.get_position())
            if(self.impleMentingMember is None):
                create_link('prototypeLink',opObject,member)
            else:
                create_link('prototypeLink',opObject,self.impleMentingMember)
                self.impleMentingMember = None
            self.nbOperations += 1
            log.info('SOAP_JV_OPERATION object created with name '+ operationName + ' and FullName '+opFullName )
            for key,ListOfchainItem in self.handleChainClass.items():
                for itm in ListOfchainItem:
                    if itm == self.typeList[0].get_name():
                        if itm not in self.handlerChainRelatedOperations.keys():
                            self.handlerChainRelatedOperations[itm] = [opObject]
                        else:
                            if opObject not in self.handlerChainRelatedOperations[itm]:
                                self.handlerChainRelatedOperations[itm].append(opObject)
            self.createdJvOperations[self.portType].add(opFullName.lower())                    
    def handleCXFType(self):
        '''
        handles the CXF type of webservice where it uses the generated interface class.
        web.xml and cxf config files are used to get the implementing class
        '''
        log.debug('CXF Started ....')
        log.debug(str(self.allJaxWsEndPoints))
        log.debug('Bean end point  '+str(self.allJaxWsEndPointsBean))
       
        for val in self.allJaxWsEndPoints:
            className = val 
            if className is None:
                return
            if len(className) > 0 and className[0] == '#':
                className = className[1:]
                
                if className in self.allJaxWsEndPointsBean.keys():
                    clsName = self.allJaxWsEndPointsBean[className].split('.')[-1]
                    if clsName not in self.endPointNamesInXml:
                        self.endPointNamesInXml.append(clsName)
                    
            else:
                if className not in self.endPointNamesInXml:
                    self.endPointNamesInXml.append(className)
        log.debug('End Point Names in XML ' + str(self.endPointNamesInXml))

    def checkIfImplementingClass(self,typ):
        filePath = typ.get_position().get_file().get_path()
        with open_source_file(filePath) as f:
            allLines = f.readlines()
        
        classDefinationLine = None                  
        for eachLine in allLines:
            if eachLine.find('implements') >=0:
                log.debug('Line which contains implement is ' + str(eachLine))
                self.isImplementingClass = True
                classDefinationLine = eachLine
                break
               
        return  classDefinationLine   
    def handlechainAnno(self,typ,annotations):
        log.info('Handling Chain Annotation ...')
        handlerClass = []
        name = annotations['file'].split('/')[-1]
        lPath = typ.get_position().get_file().get_path() 
        srcIndex = lPath.find('src')
        pathLenth = (len(lPath) - srcIndex) #we need to go uptot hte src folder and search for the file
        newPath = lPath[:-pathLenth]

        # @todo : check again this walk 
        # we can find the path with the source file list
        for root,dirs, files in os.walk(newPath):
            for fileName in files:
                if fileName == name:
                    newPath = os.path.abspath(os.path.join(root, name))
                    log.debug('Handler-Chain xml File Path '+str(newPath)) 
        if os.path.exists(newPath) and os.path.isfile(newPath):
            root = read_xml_file(newPath)

            for node in root.xpath('//handler-class'):
                tempName = node.text.split('.')[-1]
                if tempName not in self.handleChainClass.keys():
                    self.handleChainClass[tempName] = [typ.get_name()]
                else:
                    self.handleChainClass[tempName].append(typ.get_name())

                
    def start_type(self, _type):
        self.typeList.append(_type)
        allAnnoOfType = _type.get_annotations()
        allTokens = self.java_parser.parse(_type.get_position().get_file().get_path())
        if allTokens is not None:
            allImports = allTokens.imports
            for imp in allImports:
                if imp.get_name() == "org.springframework.ws.client.core.WebServiceTemplate":
                    self.wsTemplateImportPresent = True
                if imp.get_name() == "javax.xml.namespace.QName":
                    self.qNameImport = True
        for anno in allAnnoOfType:
            if anno[0].get_fullname() == 'javax.jws.WebService' and _type.get_typename() == 'JV_CLASS':
                self.createWbsObject(_type,anno[1])
                self.webServerClass.append(_type)
            if anno[0].get_fullname() == 'javax.xml.ws.WebServiceClient':
                self.wbsClient = self.createWbsClient(_type,anno[1])
            if anno[0].get_fullname() == 'javax.jws.HandlerChain':
                self.handlechainAnno(_type,anno[1])
        
        if len(self.endPointNamesInXml) > 0:
            for name in self.endPointNamesInXml:
                log.debug('Checking web service for name ' + name + ' for class '+  _type.get_name() )
                if name == _type.get_name() or name.endswith(_type.get_name()):
                    parent = get_parent(_type)                    
                    if parent is not None:
                        ast = self.java_parser.get_object_ast(parent)
                        if ast is not None:
                            allAnnoOfInterface = ast.get_annotations()
                            for annoInt in allAnnoOfInterface:
                                if annoInt.get_type_name() == 'WebService':
                                    namedParameters = annoInt.get_named_parameters()
                                    self.createWbsObject(parent,namedParameters) 
                                    self.webServerClass.append(parent)     
                    else: # Generated file is not present
                        log.info('Parent not present for ' + _type.get_name())
                        clDefnLine = self.checkIfImplementingClass(_type)
                        if clDefnLine is not None:
                            parentClass = clDefnLine.split('implements',1)[1].split('{')[0]
                            for key, value in self.wsdlPortTypeAndOpNameList.items():
                                log.debug('Key in self.wsdlPortTypeAndOpNameList ' + str(key) + ' and parentClass '+ str(parentClass))
                                if key == parentClass.strip():
                                    log.debug('ParentClass matched from wsdl')
                                    self.createWbsObject(_type, None)
                            
    def readWsdlAndCreatePortTypeAndOpNameList(self,opt):
        '''
        This reads the wsdl file and stores the PortType and Operation Name in a data structure.
        
        @todo : here the 'src' in is not really sufficient, if path is : C:\my_src\... is acts as it was 'src' folder...
        
        '''
        listofWsdlFiles=[]
        pathTosearch=[]
        for pt in opt.get_source_files():
            if 'src' in pt:
                if pt not in pathTosearch:
                    pathTosearch.append(pt)
                
            if pt.endswith('.wsdl'):
                listofWsdlFiles.append(str(pt))
        
        # last chance to get the wsdl files
        # in version 8.1.0 we do not have wsdl files as default options for xml files
        # do not do this when version >= 8.2.0 ? because we already have the wsdl files as sources
        if len(listofWsdlFiles) == 0 and get_cast_version() < StrictVersion("8.2.0"):
            
            log.info('Searching for wdsl files...')
            # to avoid scanning several times the same folder!!
            folders = set()
                        
            for pToSearch in pathTosearch:
                srcIndex = pToSearch.casefold().find('src')
                if srcIndex >= 0:
                    pathLenth = (len(pToSearch) - srcIndex) #we need to go uptot the web-inf or src folder and search for the file
                    
                    newPath = pToSearch[:-pathLenth]
                    folders.add(newPath)
            
            for newPath in  folders:
                log.info('Scanning %s' %newPath)
                for root, _, files in os.walk(newPath):
                    for fileName in files:
                        if fileName.endswith('.wsdl'):
                            webappRoot = os.path.dirname(os.path.join(root, fileName))+'\\'+fileName
                            if webappRoot not in listofWsdlFiles:
                                listofWsdlFiles.append(webappRoot) 
            log.info('...Done searching for wdsl files')
                
        for path in listofWsdlFiles:
            log.info('WSDL path is ' + path)
            try:
                tree = etree.parse(path)
                root = tree.getroot()
                for item in root: # iterate on all child nodes of root
                    if item.tag is etree.Comment:
                        # skipp comment nodes
                        continue
                    
                    if item.tag.endswith('}portType'):
                        operationList = []         
                        name = item.attrib['name']
                        opName = None
                        opInput = None
                        opOutput = None
                        for inner in item.iter(tag=etree.Element):
                            if type(inner) != str:
                                try:
                                    if inner.tag.endswith('}operation'):
                                        opName = inner.attrib['name']
                                    if inner.tag.endswith('}input'):
                                        opInput = inner.attrib['message']
                                    if inner.tag.endswith('}output'):
                                        opOutput = inner.attrib['message']
                                        opObject = Operation(opName,opInput,opOutput)
                                        operationList.append(opObject)
                                        
                                except:
                                    log.debug('Parsing WSDL File: Not a valid object')
                          
                        self.populatePortTypeAndOpNameList(operationList, name)
            except:
                log.debug('Ignoring invalid xml tags')
                pass
        log.debug(str(self.wsdlPortTypeAndOpNameList) + ' all values') 
        
    def populatePortTypeAndOpNameList(self,opList,nm):
        if nm not in self.wsdlPortTypeAndOpNameList.keys():
            self.wsdlPortTypeAndOpNameList[nm]=opList
        else:
            for element in opList:
                found=False
                for items in self.wsdlPortTypeAndOpNameList[nm]:
                    if element.opName == items.opName:
                        found=True
                        break
                if not found:
                    self.wsdlPortTypeAndOpNameList[nm].append(element) 
                     
                         
                             
    def end_type(self,typ):
        if len(self.typeList) > 0:
            self.typeList.pop()
        if len(self.webServerClass) > 0:
            self.webServerClass.pop() 
        self.fielPath = ""
        self.portTypeName = None
        self.wbsClient = None
        self.ePoint = False
        self.isImplementingClass = False
        self.parentIfaceText = None
        self.wsTemplateImportPresent = False
        self.qNameImport = False
        
    def handleWSTemplate(self,mem):
        methodParam = None
        methodHasWSTemplateParm = False
        ast = self.java_parser.get_object_ast(mem)
        try:
            methodParam = ast.get_parameters()
        except:
            log.debug('No Parameters')
        
        if methodParam is not None:
            for item in methodParam:
                itemType = item.get_type()
                try:
                    paramType = itemType.get_type_name()
                    for key, value in self.wsdlPortTypeAndOpNameList.items():
                        for val in value:
                            if paramType == val.opInput.split(':')[-1]:
                                methodHasWSTemplateParm = True
                                break
                except AttributeError:
                    # not a simple type (generics, array etc...)
                    pass
         
        if methodHasWSTemplateParm :
            # https://jira.castsoftware.com/browse/JAXWS-18
            #check for if any WSTemplate marshalxxx call is happening or not
            
            # @todo reopen file : shit. Use AST
            parentFile = mem.get_position().get_file()
            filePath = parentFile.get_path()
            with open_source_file(filePath) as f:
                linesInMethod = f.readlines()[mem.get_position().get_begin_line():mem.get_position().get_end_line()]
                
            for expectedMethName in self.wsTemplateFunctions:
                rowMatch=0
                for eachLine in linesInMethod:
                    rowMatch+=1
                    if eachLine.find(expectedMethName) >=0:
                        funNameFoundIndex = eachLine.replace("\t","    ").find(expectedMethName) #files may have tabs so replace with four spaces (standard)
                        wsTemplateMethod = CustomObject()
                        wsTemplateMethod.set_name(mem.get_name())
                        wsTemplateMethod.set_type('SOAP_JV_CLIENT_OPERATION')
                        wsTemplateMethod.set_parent(parentFile)
                        wsTemplateMethod.set_fullname(mem.get_fullname())  
                        wsTemplateMethod.set_guid(filePath+mem.get_name()+expectedMethName)
                        wsTemplateMethod.save()
                        bb = Bookmark(parentFile,mem.get_position().get_begin_line()+rowMatch,funNameFoundIndex,mem.get_position().get_begin_line()+rowMatch,funNameFoundIndex+len(expectedMethName))
                        wsTemplateMethod.save_position(Bookmark(parentFile,mem.get_position().get_begin_line()+rowMatch,funNameFoundIndex,mem.get_position().get_begin_line()+rowMatch,funNameFoundIndex+len(expectedMethName)))
                        create_link('accessExecLink',mem,wsTemplateMethod)
                        log.info('SOAP_JV_CLIENT_OPERATION for WS Template Method use with name '+ mem.get_name()+ str(bb))
    
    def handleLinkFromOperationToHandler(self,meth):
        if meth.get_name() in ['close','handleMessage','handleFault']:
            log.debug('Handling Link from Operation to Hanlder '+ meth.get_name())
            if self.typeList[0].get_name() not in self.handleChainClassAndMethods.keys():
                self.handleChainClassAndMethods[self.typeList[0].get_name()] = [meth]
            else:
                self.handleChainClassAndMethods[self.typeList[0].get_name()].append(meth)
    
    
    def start_member(self, member):
        #endpoint is null
        
        # skip
        if '<anonymous>' in member.get_fullname():
            return
        
        if self.qNameImport:
            if member.get_typename() == 'JV_METHOD':
                ast = self.java_parser.get_object_ast(member)
                methodBody = [item for item in ast.children if item.get_type() == 'CurlyBracket']
                self.parseMethod(methodBody)
        self.handleLinkFromOperationToHandler(member)
        if self.wsTemplateImportPresent:
            self.handleWSTemplate(member)
        for anno in member.get_annotations():
            if anno[0].get_fullname() == 'javax.xml.ws.WebEndpoint':
                self.endPoint = self.createEndPoint(member,anno[1])
                return
        
        if self.ePoint is False:
            for anno in member.get_annotations():
                if anno[0].get_fullname() == 'javax.jws.WebMethod':
                    self.createOperation(member,anno[1])
                    return
                
            if len(self.webServerClass) > 0 and len(self.typeList) >0:
                filePath = self.webServerClass[0].get_position().get_file().get_path()
                allChildren = self.webServerClass[0].get_children()
                for ele in allChildren:
                    if member.get_name() == ele.get_name() and ele.get_typename() == "JV_METHOD":
                        self.createOperation(member,None)
                        
            memName = member.get_name()
            
            if self.cxfBased and len(self.typeList) > 0:
                if self.isImplementingClass is True and len(self.allJaxWsEndPoints) > 0:
                    if self.typeList[0].get_name() in self.endPointNamesInXml:
                        for key, value in self.wsdlPortTypeAndOpNameList.items():
                            for val in value:
                                if val.opName.casefold() == memName.casefold():
                                    log.info('Creating Operation for Implementing class member ' + memName)
                                    self.createOperation(member,None)
                                    value.remove(val)                
        else:
            ### if endpoint then create operation for all the methods of interface
            for parent in self.typeList[0].get_inherited_types():
                while parent.get_fullname() != 'java.lang.Object':
                    tempList = parent.get_inherited_types()
                    if len(tempList) >0:
                        parent = tempList[0]
                    else:
                        break
                     
                if parent.get_name() != 'Object':
                    samp = parent.get_children()
                    if len(samp) > 0:
                        samp.pop() #api is giving one extra value so poping for the time
                        for child in samp:
                            if child.get_name() == member.get_name():
                                self.java_parser.parse(child.get_position().get_file().get_path())
                                ast = self.java_parser.get_object_ast(child)
                                if ast is not None:
                                    allAnnotations = ast.get_annotations()
                                    
                                    if(len(allAnnotations) > 0):
                                        for anno in allAnnotations:
                                            if anno.get_type_name() == 'WebMethod':
                                                namedParameters = anno.get_named_parameters()
                                                self.impleMentingMember = member
                                                self.createOperation(child,namedParameters) 
                                    else:
                                        self.createOperation(member, None)   
                else:#parent not found and it a webserver class match the methods with the operation name from the wsdl file and create the operation
                    for key, value in self.wsdlPortTypeAndOpNameList.items():
                        for val in value:
                            if val.opName.casefold() == member.get_name().casefold():
                                log.debug('Creating Operation for Implementing class[%s] member[%s]' %(self.typeList[0],member.get_name()))
                                self.createOperation(member,None)
                                value.remove(val)      
                    
    def end_member(self, member):
        self.impleMentingMember = None 

        if member.get_typename() == 'JV_METHOD': 
            tempstr=''
            for ele in self.listOfWsCalledInQname:
                tempstr=tempstr+ele+':'
            if tempstr: 
                member.save_property('CAST_CalledWebService.wsname',tempstr)
            self.listOfWsCalledInQname = []
             
    def createEndPoint(self,member,parameters):
        '''
        creates the End point of the java webservice client
        '''
        if parameters['name'] not in self.endPointNameList:
            self.endPointNameList.append(parameters['name'])
            endPt = CustomObject()
            endPt.set_name(parameters['name'])
            endPt.set_type('SOAP_JV_CLIENT_ENDPOINT')
            endPt.set_parent(self.wbsClient)
            endPt.set_fullname(member.get_fullname())  
            endPt.set_guid(self.fielPath+parameters['name'])
            endPt.save()
            endPt.save_position(member.get_position())
            log.info('SOAP_JV_CLIENT_ENDPOINT with name '+ parameters['name'])
            return endPt
        else:
            return self.endPoint
        
    def createClientOperation(self):
        '''
        creates the client Operation
        
        https://jira.castsoftware.com/browse/JAXWS-9
        '''
        for key,value in self.webMethodNameList.items():
            if self.endPoint is not None:
                clientOperation = CustomObject()
                clientOperation.set_name(str(value[0]))
                clientOperation.set_type('SOAP_JV_CLIENT_OPERATION')
                clientOperation.set_parent(self.endPoint)
                fullNam = str(value[2])+'.'+str(value[0])
                clientOperation.set_fullname(fullNam)  
                clientOperation.set_guid(self.fielPath+key)
                clientOperation.save()
                clientOperation.save_position(value[1].get_position())
                log.info('SOAP_JV_CLIENT_OPERATION is created with name '+ str(value[0])+' full Name '+fullNam)
    def handleChainLinks(self):
        for key,value in self.handleChainClassAndMethods.items():
            if key in self.handleChainClass.keys():
                for element in self.handleChainClass[key]:
                    if element in self.handlerChainRelatedOperations.keys():
                        for methodItem in value:
                            for optItem in self.handlerChainRelatedOperations[element]:
                                log.info('Created link from operation ' + optItem.name + ' to method ' + methodItem.get_name() + ' of '+ key)
                                create_link('callLink',optItem,methodItem)
                        
               
    def end_analysis(self):
        self.handleChainLinks()
        self.handleChainClassAndMethods={}
        self.handleChainClass={}
        self.serviceName
        self.result
        self.endPointNameList = []
        self.createClientOperation()
        self.webMethodNameList = {}
        self.allJaxWsEndPoints = []
        self.allJaxWsEndPointsBean = {}
        self.handleChainClass={}
        self.handlerChainRelatedOperations={}
        log.info(str(self.nbOperations) + ' JAX-WS web service operations created.')
        log.info(str(self.nbWebService) + ' JAX-WS WebService are created')
        log.info(str(self.nbPortType) + ' JAX-WS PortType are created')
        self.cxfBased = False
        log.info("JAX-WS Analyzer Ended")
                
    def createWbsClient(self,typ,annoValue):
        '''
        creates the WebService Client using the annotation attributes
        '''
        try:
            wbsClient = CustomObject()
            wbsClient.set_name(annoValue['name'])
            wbsClient.set_type('SOAP_JV_CLIENT_SERVICE')
            parentFile = typ.get_position().get_file() 
            wbsClient.set_parent(parentFile)
            wbsClient.set_fullname(typ.get_fullname())  
            wbsClient.save()
            wbsClient.save_position(typ.get_position())
            log.info('SOAP_JV_CLIENT_SERVICE object is created with name '+ annoValue['name'])
            return wbsClient;  
        except:
            pass  
