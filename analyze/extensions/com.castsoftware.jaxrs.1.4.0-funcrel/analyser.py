import cast.analysers.jee
from cast.analysers import create_link, log
        


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


class JSR(cast.analysers.jee.Extension):
    """
    Parse ...
    """
    class TypeContext:
        def __init__(self, typ):
            self.currentClass = typ
            self.currentClassPath = None
            self.currentPort = None
            self.currentPortFullname = None
    class MethodPathConainer:
        def __int__(self):
            self.meth = None
            self.pathVariables = [] 
            self.col = None   
            
    def __init__(self):
        
        self.nbOperations = 0
        self.contextStack = []
        self.currentContext = None
        # a java parser for annotations
        self.java_parser = None
        self.flow = ""
        self.lineNumFunCall = {}
    def pushContext(self, typ):
        self.currentContext = self.TypeContext(typ)
        self.contextStack.append(self.currentContext)
    
    def popContext(self):
        self.contextStack.pop()
        if self.contextStack:
            self.currentContext = self.contextStack[-1]
        else:
            self.currentContext = None
    
    # receive a java parser from platform
    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def receive_java_parser(self, parser):
        self.java_parser = parser
    def formAndCreateClientLinks(self):
        temp = []
        tempObj = None
        for ele in sorted(self.lineNumFunCall.keys()):
            if len(self.lineNumFunCall[ele].pathVariables) < 2: #package and class name (2)
                if tempObj is not None:
                    if self.lineNumFunCall[ele].col < tempObj.col:
                        temp.append(tempObj.pathVariables[0])
                        temp.append(self.lineNumFunCall[ele].pathVariables[0])
                    else:
                        temp.append(self.lineNumFunCall[ele].pathVariables[0])
                        temp.append(tempObj.pathVariables[0])
                    tempObj = None
                    self.lineNumFunCall[ele].pathVariables = temp
                    temp=[]
                    
                else:
                    tempObj = self.lineNumFunCall[ele]
                
                                    
            if len(self.lineNumFunCall[ele].pathVariables) == 2: #package and class name (2)
                obj = cast.analysers.CustomObject()
                obj.set_type('CAST_JAXRS_GetResourceService')
                
                parentFile = self.lineNumFunCall[ele].meth.get_position().get_file()
                obj.set_parent(parentFile)
                objFullname = self.lineNumFunCall[ele].meth.get_fullname() + '.wscall' + str(ele)
                name = 'wscall' + str(ele)
                obj.set_fullname(objFullname)   
                obj.set_name(name)
                obj.save()
                obj.save_position(self.lineNumFunCall[ele].meth.get_position())      
                log.debug(str(ele)+'---'+str(self.lineNumFunCall[ele].pathVariables)+'---'+str(self.lineNumFunCall[ele].meth))
                path = "/".join(self.lineNumFunCall[ele].pathVariables)
                obj.save_property('CAST_ResourceService.uri', "/"+path) 
                create_link('callLink',self.lineNumFunCall[ele].meth,obj)       
        
    def end_analysis(self):
        cast.analysers.log.info(str(self.nbOperations) + ' JAX-RS web service operations created.')
        self.formAndCreateClientLinks()
        
        bb = """<?xml version="1.0" encoding="utf-8"?>
<BlackBox name="JAXRSServiceEntryPoints" xmlns="http://tempuri.org/BlackBoxes.xsd">
  <Class mangling="com.castsoftware.jaxrs">
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
            
        
    def start_analysis(self,options):
        options.add_classpath('jars')
        options.add_parameterization("javax.ws.rs.client.WebTarget.path(java.lang.String)",[1],self.handlePath) 
        
    def handlePath(self,values, caller, line, column):
        log.debug('handlePath triggered with '+ str(values[1][0]))
        self.pName = values 
        
        if line not in self.lineNumFunCall.keys():
            tempObj = self.MethodPathConainer()
            tempObj.meth = caller
            tempObj.pathVariables=[values[1][0]]
            tempObj.col = column
            
            self.lineNumFunCall[line] = tempObj
        else:
            if self.lineNumFunCall[line].col < column:
                self.lineNumFunCall[line].pathVariables.append(values[1][0])
            else:
                self.lineNumFunCall[line].pathVariables.insert(0,values[1][0])
        
    def start_type(self, typ):
#         log.info('start type' + str(typ))
        self.pushContext(typ)
        
        def search_path_in_hierarchy(_class):
            
            path = self.get_type_path(_class)
            if path:
                return path
            
            for parent in _class.get_inherited_types():
                
                path = search_path_in_hierarchy(parent)
                if path:
                    return path
                
        
        
        path = search_path_in_hierarchy(typ)
        
        
        
#         log.info(str(path))
        if path:
            self.currentContext.currentClass = typ
            self.currentContext.currentClassPath = path
            if not self.currentContext.currentClassPath.startswith('/'):
                self.currentContext.currentClassPath = '/' + self.currentContext.currentClassPath
            self.create_web_service(typ)

    def end_type(self, typ):

        self.popContext()

    def start_member(self, member):
        
        if not self.currentContext or not self.currentContext.currentClass:
            return
        
        has_annotation, operationPath, operationType = self.get_member_informations(member)

#         log.info(str(has_annotation))
#         log.info(str(operationPath))
#         log.info(str(operationType))
                
        if self.currentContext.currentClassPath and not has_annotation:
            # inheritance case
            # @see http://stackoverflow.com/questions/25916796/inheritance-with-jax-rs
            
            for overriden in get_overriden(self.currentContext.currentClass, member):
                has_annotation, operationPath, operationType = self.get_member_informations(overriden)
                if has_annotation:
                    break
                
        if not operationType:
            return
        
        self.create_operation(operationType, operationPath, member, operationName = self.currentContext.currentClassPath)
                
    def create_web_service(self, javaClass):
        
        web_service_object = cast.analysers.CustomObject()
        web_service_object.set_name(self.currentContext.currentClassPath)
        web_service_object.set_type('CAST_JAXRS_Service')
        parentFile = self.currentContext.currentClass.get_position().get_file()
        web_service_object.set_parent(parentFile)
        wsFullname = parentFile.get_fullname() + self.currentContext.currentClassPath
        web_service_object.set_fullname(wsFullname)
        web_service_object.set_guid(wsFullname)
        web_service_object.save()
        web_service_object.save_position(javaClass.get_position())

        self.create_port(wsFullname, web_service_object, javaClass)
                
    def create_port(self, wsFullname, webService, javaClass):
        
        port_object = cast.analysers.CustomObject()
        self.currentContext.currentPort = port_object
        port_object.set_name(self.currentContext.currentClassPath)
        port_object.set_type('CAST_JAXRS_Port')
        port_object.set_parent(webService)
        self.currentContext.currentPortFullname = wsFullname + '/PORT'
        port_object.set_fullname(self.currentContext.currentPortFullname)
        port_object.set_guid(self.currentContext.currentPortFullname)
        port_object.save()
        port_object.save_position(javaClass.get_position())
        
        create_link('prototypeLink', port_object, self.currentContext.currentClass, self.currentContext.currentClass.get_position())

    def normalize_path(self, operationPath):

        service_names = operationPath.split('/')
        service_name = None
        if service_names:
            service_name = ''
            for part in service_names:
                if part: 
                    if part.startswith('{'):
                        service_name += '{}/'
                    else:
                        service_name += ( part + '/' )
        return service_name

    def create_operation(self, operationType, operationPath, method, operationName):
        
        self.generate_bb(method)
        
        # happens sometimes : the class has no annotation, no need to crash on startswith/endswith...
        if not operationName:
            return
        
        if operationPath:
            if not operationPath.startswith('/'):
                if operationName.endswith('/'):
                    operationName = operationName + operationPath
                else:
                    operationName = operationName + '/' + operationPath
            else:
                if operationName.endswith('/'):
                    operationName = operationName + operationPath[1:]
                else:
                    operationName = operationName + operationPath
        else:
            if operationName.endswith('/'):
                operationName = operationName
            else:
                operationName = operationName + '/'
        operationName = self.normalize_path(operationName)
        
        if not operationName:
            return None
        
        operation_object = cast.analysers.CustomObject()
        operation_object.set_name(operationName)
        operation_object.set_parent(self.currentContext.currentPort)
        if operationName.endswith('/'):
            fullname = self.currentContext.currentPortFullname + '/' + operationName + method.get_name()
        else:
            fullname = self.currentContext.currentPortFullname + '/' + operationName + '/' + method.get_name()
        operation_object.set_fullname(fullname)
        operation_object.set_guid(fullname)

        # @todo replace by callLink
        linkType = 'fireLink'
        if operationType == 'DELETE':
            linkType = 'fireDeleteLink'
            operation_object.set_type('CAST_JAXRS_DeleteOperation')
        elif operationType == 'PUT':
            linkType = 'fireUpdateLink'
            operation_object.set_type('CAST_JAXRS_PutOperation')
        elif operationType == 'POST':
            linkType = 'fireUpdateLink'
            operation_object.set_type('CAST_JAXRS_PostOperation')
        else:
            linkType = 'fireSelectLink'
            operation_object.set_type('CAST_JAXRS_GetOperation')

        operation_object.save()
        operation_object.save_position(method.get_position())
        cast.analysers.log.debug('create_operation ' + fullname + ' ' + operationName + ' ' + str(operationType))

        create_link(linkType, operation_object, method, method.get_position())
        
        self.nbOperations += 1
        
    
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
    
            self.flow += current_method % (fullname, parameters_type, parameters)
        except:
            pass
    
    
    def get_member_informations(self, member):
        """
        Scan member to get the annotations 
        @return : if has JAX annotations, the path, the type
        """
        
        compilation_unit = self.java_parser.parse(member.get_position().get_file().get_path())
        ast = self.java_parser.get_object_ast(member)
        
#         log.info('ast = ' + str(ast))
        
        operationPath = '/'
        operationType = None
        
        # do we have local annotations or not ?
        has_annotation = False
        
        try:
            annotations = ast.get_annotations()
            
            for annotation in annotations:
                
                name = annotation.get_type_name()
                possible_names = compilation_unit.get_possible_qualified_names(name)
                if 'javax.ws.rs.Path' in possible_names:
                    named_parameters = annotation.get_named_parameters()
    #                     log.info(str(named_parameters))
                    
                    # default value
                    try:
                        operationPath = named_parameters['value']
                    except:
                        # try as positional first element
                        positionals = annotation.get_positional_parameters()
    #                         log.info(str(positionals))
                        try:
                            operationPath =  positionals[0]
                        except:
                            pass
                        
                    has_annotation = True
                    
                elif 'javax.ws.rs.GET' in possible_names:
                    operationType = 'GET'
                    has_annotation = True
                elif 'javax.ws.rs.PUT' in possible_names:
                    operationType = 'PUT'
                    has_annotation = True
                elif 'javax.ws.rs.POST' in possible_names:
                    operationType = 'POST'
                    has_annotation = True
                elif 'javax.ws.rs.DELETE' in possible_names:
                    operationType = 'DELETE'
                    has_annotation = True
        except:
            log.debug('Cannot find ast for ' + str(member))
#         log.info(str((has_annotation, operationPath, operationType)))
        return has_annotation, operationPath, operationType
    
    def get_type_path(self, _type):
        
        compilation_unit = self.java_parser.parse(_type.get_position().get_file().get_path())
        ast = self.java_parser.get_object_ast(_type)
        
#         log.info('ast = ' + str(ast))
        
        try:
            annotations = ast.get_annotations()
            for annotation in annotations:
                name = annotation.get_type_name()
                possible_names = compilation_unit.get_possible_qualified_names(name)
                if 'javax.ws.rs.Path' in possible_names:
                    
                    return annotation.get_named_parameters()['value']
                
        except:
            pass
