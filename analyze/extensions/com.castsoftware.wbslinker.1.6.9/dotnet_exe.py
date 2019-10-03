'''
Creates programs for dotnet technology for linking 

The exe name is in the project file 
    <AssemblyName>NugetServerCleaner</AssemblyName>

The main is a method named Main
'''
import traceback
from lxml import etree
from cast.application import open_source_file
from cast.analysers import dotnet, log, CustomObject, create_link


class CreateDotnetExe(dotnet.Extension):

    def __init__(self):
        
        # @type self.current_exe_name:str
        self.current_exe_name = None

        # @type self.current_class:[cast.analyzers.Type]
        self.current_class = []

        self.count = 0

    def start_project(self, project):
        # @type project:cast.analysers.AnalysisUnit
        # scan project for exe name
        for project in project.get_source_projects():
            self.current_exe_name = get_exe_name(project)
            break
        
    
    def end_project(self):
        self.current_exe_name = None

    def start_type(self, _type):
        self.current_class.append(_type)
        
    def end_type(self, _):
        self.current_class.pop()

    def start_member(self, member):
        # @type member:cast.analyzers.Member
        if member.get_name() == 'Main':
            
            if not self.current_exe_name:
                log.debug('could not find the current executable name')
                return
            if not self.current_class:
                log.debug('could not find the current class')
                return
                
            program = CustomObject()
            program.set_type('CAST_DotNet_Executable')
            program.set_parent(self.current_class[-1])
            program.set_name(self.current_exe_name)
            program.save()
            
            program.save_position(member.get_position())
            
            create_link('callLink', program, member)
            
            self.count += 1

    def end_analysis(self):
        
        log.info('%s .NET programs created.' % self.count)


def get_exe_name(project_path):
    """
    :param project_path: the path of the project
    
    For .csproj, .vbproj, .vcxproj :
        <AssemblyName>NugetServerCleaner</AssemblyName>

    """
    try:
        root = read_xml_file(project_path)
        
        for assembly_name in root.xpath('//AssemblyName'):
            
            name = assembly_name.text
            return name
        
    except:
        log.debug(traceback.format_exc()) 
    return None
    



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


