import cast.analysers.ua
import cast.analysers.jee
# from cast.application import open_source_file
import traceback
import os
# from lxml import etree

def create_link(linkType, caller, callee, bm = None):

    try:    
        clr = caller
        cle = callee
        if bm:
            cast.analysers.create_link(linkType, clr, cle, bm)
        else:
            cast.analysers.create_link(linkType, clr, cle)
    except:
        try:
            cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))
            cast.analysers.log.debug(linkType)
            cast.analysers.log.debug(str(clr))
            cast.analysers.log.debug(str(cle))
            cast.analysers.log.debug(str(bm))
        except:
            pass

def is_type_inherit_from_applet(typ):
    
    try:
        inheritedTypes = typ.get_inherited_types()
        
        for inheritedType in inheritedTypes:
            if inheritedType.get_fullname() == 'javax.swing.JApplet':
                return True
            elif is_type_inherit_from_applet(inheritedType):
                return True
    except:
        cast.analysers.log.debug(str(traceback.format_exc()))
    return False

class HTML5_JEE(cast.analysers.jee.Extension):
    
    class TypeContext:
        
        def __init__(self, typ, isApplet):
            self.currentClass = typ
            self.isApplet = isApplet
            self.methods = {}
            self.currentNbMethods = 0
            
        def add_member(self, member):
            name = member.get_name()
            if not name in self.methods:
                self.methods[name] = member
                self.currentNbMethods += 1
        
    def __init__(self):
        
        self.nbApplets = 0
        self.contextStack = []
        self.currentContext = None

#     def start_analysis(self, execution_unit):
#         # jsf beans http://xmlns.oracle.com/adf/controller
#         execution_unit.handle_xml_with_xpath('/adfc-config')
    
    def pushContext(self, typ, isApplet):
        self.currentContext = self.TypeContext(typ, isApplet)
        self.contextStack.append(self.currentContext)
    
    def popContext(self):
        self.contextStack.pop()
        if self.contextStack:
            self.currentContext = self.contextStack[-1]
        else:
            self.currentContext = None
        
    def start_type(self, typ):

        isApplet = False
        if is_type_inherit_from_applet(typ):
            isApplet = True
            cast.analysers.log.debug('applet found ' + typ.get_name())
        self.pushContext(typ, isApplet)

    def end_type(self, typ):

        if not self.currentContext:
            return
        if self.currentContext.isApplet:
            self.create_applet(typ, self.currentContext.methods)
        
        self.popContext()

    def create_applet(self, typ, methods):

        applet_object = cast.analysers.CustomObject()
        name = typ.get_name()
        cast.analysers.log.info('Creating applet ' + name)
        applet_object.set_name(name)
        applet_object.set_type('CAST_J2EE_HTML5_Applet')
        applet_object.set_parent(typ)
        appletFullname = typ.get_fullname() + '/CAST_J2EE_HTML5_Applet'
        applet_object.set_guid(appletFullname)
        applet_object.set_fullname(typ.get_fullname())
        applet_object.save()
        self.nbApplets += 1
        applet_object.save_position(typ.get_position())
        for _, method in methods.items():
            create_link('callLink', applet_object, method, method.get_position())

    def start_member(self, member):
        
        if not self.currentContext or not self.currentContext.isApplet:
            return
        
        if member.get_name() in ['init', 'start', 'stop', 'destroy']:
            self.currentContext.add_member(member)
    
#     def start_xml_file(self, file):
#  
#         path = os.path.normpath(file.get_path())
#         if not path or not os.path.isfile(path):
#             return
#         
#         cast.analysers.log.info('start_xml_file ' + path)
#          
#         with open_source_file(path) as myfile:
#             fileContent = myfile.read()
#                  
#         fileContent = remove_utf8_from_web_xml(fileContent)
#         fileContent = remove_xmlns_from_web_xml(fileContent)
#         tree = etree.fromstring(fileContent, parser=etree.XMLParser(recover=True))
#      
#         for bean in tree.xpath('/adfc-config/task-flow-definition/managed-bean'):
#             name = bean.find('managed-bean-name').text
#             _class = bean.find('managed-bean-class').text
#             scope = bean.find('managed-bean-scope').text
#             self.create_bean(name, _class, scope)
# 
#     def create_bean(self, name, _class, scope):
#         cast.analysers.log.info('create_bean ' + str(name) + ', ' + str(_class) + ', ' + str(scope))
            
    def end_analysis(self):

        cast.analysers.log.info(str(self.nbApplets) + ' applets created.')
    
# def remove_utf8_from_web_xml(fileContent):
#     """
#     Removes the header from the file content.
#     
# <?xml version="1.0" encoding="UTF-8"?>
#     """
#     indexStart = fileContent.find('<?xml')
#     if indexStart < 0:
#         return fileContent
#     
#     indexStart = fileContent.find('<', indexStart + 2)
#     if indexStart < 0:
#         return fileContent
# 
#     return fileContent[indexStart:]
# 
# 
# def remove_xmlns_from_web_xml(fileContent):
#     """
#     Removes the "xmlns=" part from file content because lxml api supports this part only by specifying exactly
#     its value whenever we want to access a part of xml content, and its value can change between web.xml files.
#     
# <web-app xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://java.sun.com/xml/ns/javaee" xmlns:web="http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" xsi:schemaLocation="http://java.sun.com/xml/ns/javaee http://java.sun.com/xml/ns/javaee/web-app_2_5.xsd" id="WebApp_ID" version="2.5">
# </web-app>
#     """
#     if not 'xmlns=' in fileContent:
#         return fileContent
#     
#     indexStart = fileContent.find('xmlns=')
#     indexValueStart = fileContent.find('"', indexStart)
#     if indexValueStart < 0:
#         return fileContent
#     indexValueEnd = fileContent.find('"', indexValueStart + 1)
#     if indexValueEnd < 0:
#         return fileContent
# 
#     return fileContent.replace(fileContent[indexStart:indexValueEnd + 1], '')
