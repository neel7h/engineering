"""
Created on July 13, 2018
@author: RUP
"""

import cast.analysers.jee
from lxml import etree as ET
import cast_upgrade_1_5_9
from qualityrules import QualityRules
from cast.analysers import log
from cast.application import open_source_file
from distutils.version import StrictVersion
import os


def remove_utf8_from_xml(file_content):
    """
    Removes the header from the file content.

<?xml version="1.0" encoding="UTF-8"?>
    """
    indexStart = file_content.find('<?xml')
    if indexStart < 0:
        return file_content

    indexStart = file_content.find('<', indexStart + 2)
    if indexStart < 0:
        return file_content

    return file_content[indexStart:]


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


class SpringSecurity(cast.analysers.jee.Extension):
    """ Main analyser Class"""

    def __init__(self):

        self.java_parser = None
        self.httpFirewallInJava = None
        self.xml_files = []
        self.quality_rules_obj = QualityRules()
        self.properties_files = {}
        self.http_methods = ['org.springframework.web.bind.annotation.RequestMethod.GET',
                             'org.springframework.web.bind.annotation.RequestMethod.PUT',
                             'org.springframework.web.bind.annotation.RequestMethod.POST',
                             'org.springframework.web.bind.annotation.RequestMethod.DELETE',
                             'org.springframework.web.bind.annotation.RequestMethod.PATCH']

        self.HandlerExceptionResolver_methods = []
        self.parent_generic_class = []
        self.methods_list = []
        self.HandlerExceptionResolver_class = []
        self.ControllerAdvice_class = []
        self.project = None
        self.version_list = ['4.1.5', '4.2.4', '5.0.1']
        self.springsecurity_version = False
        self.defaultFirewall = 'org.springframework.security.web.firewall.DefaultHttpFirewall'
        self.strictHttpFirewall = 'org.springframework.security.web.firewall.StrictHttpFirewall'
        self.defaulthttp_firewall_in_xml = False
        self.defaulthttp_firewall_in_java = False
        self.pom_files = []

    # receive a java parser from platform

    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def receive_java_parser(self, parser):
        self.java_parser = parser

    def start_analysis(self, options):

        options.handle_xml_with_xpath('/beans')
        options.handle_xml_with_xpath('/project')
        options.handle_xml_with_xsd('/beans:beans')
        options.handle_xml_with_xsd('/bean:beans')
        options.add_classpath('jars')
        self.quality_rules_obj.add_parameterization(options)
        self.pom_files = [
            file for file in options.get_source_files() if file.endswith('pom.xml')]

    def start_type(self, _type):

        try:
            self.project = _type.get_position().get_file().get_project()
        except:
            pass

        def check_imports():
            """ Checks for required imports in java file """
            allTokens = self.java_parser.parse(
                _type.get_position().get_file().get_path())

            if allTokens is not None:
                allImports = allTokens.imports

                for import_st in allImports:
                    # For the rule:StrictHttpFirewall should be set as the
                    # HttpFirewall
                    if import_st.get_name() == self.defaultFirewall or import_st.get_name() == self.strictHttpFirewall:

                        self.httpFirewallInJava = [
                            import_st, _type.get_position().get_file()]

                    if import_st.get_name() == 'org.springframework.web.servlet.HandlerExceptionResolver':

                        parent_file = _type.get_position(
                        ).get_file().get_path()
                        if parent_file not in self.HandlerExceptionResolver_class:
                            self.HandlerExceptionResolver_class.append(
                                parent_file)

                    if import_st.get_name() == 'org.springframework.web.bind.annotation.ControllerAdvice':

                        self.ControllerAdvice_class.append(_type)

                    if import_st.get_name() == 'org.springframework.security.core.AuthenticationException':
                        parent_file = _type.get_position(
                        ).get_file().get_path()
                        if parent_file not in self.parent_generic_class:
                            self.parent_generic_class.append(parent_file)

        def check_annotations():
            """ Check for required annotations in java file """

            file_path = _type.get_position().get_file().get_path()
            if file_path:
                check_imports()
            try:
                class_annotations = _type.get_annotations()
                for annotation in class_annotations:

                    if annotation[0].get_name() == 'EnableWebSecurity' and annotation[1].get('debug') == 'true':
                        self.quality_rules_obj.interpret_violations_in_java_config(
                            java_parser=self.java_parser, annotation_object=annotation[0], class_object=_type)

            except:
                pass

        check_annotations()

    def start_xml_file(self, file):

        if file:
            self.xml_files.append(file)

    def start_web_xml(self, file):

        if file:
            self.xml_files.append(file)

    def start_properties_file(self, file):

        file_path = file.get_path()
        self.properties_files[file_path] = []
        self.properties_files[file_path].append(file)

    def start_member(self, member):

        def check_for_member_parent():
            """ Checks for the presence of member-parent, for the rule: AvoidUsingGenericAuthenticationExceptionClass """
            member_parent = member.get_position().get_file().get_path()

            if member_parent in self.parent_generic_class:
                self.methods_list.append(member)

            if member_parent in self.HandlerExceptionResolver_class:
                self.HandlerExceptionResolver_methods.append(member)

        def get_configure_method():
            """ check for the presence of method which has name:Configure and Parameter as HttpSecurity """
            try:
                parameter_type = list(member.get_parameters().items())[0][1]

                if member.get_name() == 'configure' and parameter_type.get_name() == 'HttpSecurity':
                    self.quality_rules_obj.interpret_violations_in_java_config(
                        java_parser=self.java_parser, member=member)

            except:
                pass

        def get_member_annotations():
            """ Check for the presence of annotation: RequestMapping, 
            for the quality rule:EnsureToSpecifyHttpMethodsInRequestMapping """
            try:
                annotation_member = member.get_annotations()
                for annotation in annotation_member:

                    if annotation[0].get_name() == 'RequestMapping':
                        if annotation[1].get('method') not in self.http_methods:
                            self.ast = self.java_parser.get_object_ast(member)
                            self.quality_rules_obj.interpret_violations_in_java_config(
                                java_parser=self.java_parser, member=member)
            except:
                pass

        check_for_member_parent()
        get_configure_method()
        get_member_annotations()

    def check_springsecurity_version(self):
        """ Checks the version of spring security by checking 'spring-security-core' jar in lib 
            folder of WEB_INF
        """
        def get_version_from_jar():
            springsecurity_version = None

            # If WEB_INF is present, get the path of lib folder
            if web_inf_path:
                springsecurity_jar = [
                    i for i in os.listdir(web_inf_path) if 'spring-security-core-' in i]

                springsecurity_version = springsecurity_jar[
                    0].strip('spring-security-core-')

                if self.compare_springsecurity_versions(springsecurity_version[:5]):
                    self.springsecurity_version = True

            if springsecurity_version:
                self.project.save_property(
                    "CAST_Java_SpringSecurity_Version.SpringSecurityVersion", 1)
                return True

        web_inf_path = None
        for xml_file in self.xml_files:
            if 'WEB-INF' in xml_file.get_path():
                web_inf_path = self.get_webInf_dirPath(xml_file.get_path())
                if web_inf_path:
                    break

        # If there is no spring security jar file in lib folder, check in
        # pom.xml file
        if not get_version_from_jar():
            springsecurity_version = self.check_version_in_pom_file()
            if springsecurity_version:
                self.springsecurity_version = True

    def get_webInf_dirPath(self, path):
        """
       get the path of web_inf directory,
       this path is further used to get the path of lib folder which will contain spring security jar files
        """

        path_split = path.split(os.path.sep)[::-1]

        folders_deep = 1
        for token in path_split[0:folders_deep]:
            path = path.replace(os.sep + token, "")

            for root, dirs, files in os.walk(path, topdown=False):

                for name in dirs:
                    if "lib" in name:
                        return(os.path.join(root, name))

                    else:
                        continue
        return None

    def compare_springsecurity_versions(self, version):
        """ Compare if spring security version is < ['4.1.5', '4.2.4', '5.0.1'] ,
            then check for violation """

        if (StrictVersion(version) < StrictVersion('4.1.5')):
                return True
        if (StrictVersion(version) < StrictVersion('4.2.4')) and (StrictVersion(version) >= StrictVersion('4.2.0')):
                return True     
        if (StrictVersion(version) < StrictVersion('5.0.1')) and (StrictVersion(version) >= StrictVersion('5.0.0')):
                return True

        else:
            return None

    def check_version_in_pom_file(self):
        """ check spring security version in pom.xml file if the spring security jar is not present """

        def get_version_from_property_tag():
            try:
                for property_tag in root.xpath('/project/properties'):
                    springsecurity_version = property_tag.find(
                        version_tag.strip('${}'))
                    if str(springsecurity_version):
                        springsecurity_version = springsecurity_version.text[
                            :5]
                        if self.compare_springsecurity_versions(springsecurity_version):
                            return springsecurity_version
                        else:
                            self.project.save_property(
                                "CAST_Java_SpringSecurity_Version.SpringSecurityVersion", 1)
            except:
                pass

        for pom_file in self.pom_files:
            root = self.get_root_of_xml_file(pom_file)
            if root:
                for dependency in root.xpath('/project/dependencies/dependency'):
                    if dependency.find('groupId').text == 'org.springframework.security':
                        version_tag = dependency.find('version').text
                        if version_tag and version_tag.startswith('${'):
                            return get_version_from_property_tag()

    def get_root_of_xml_file(self, xml_file_path):
        """ Returns the root of xml file when xml file path is provided """
        try:
            if os.path.exists(xml_file_path):
                """If xml file path exists, proceed to check violations """
                with open_source_file(xml_file_path) as f:
                    file_content = f.read()
                    file_content = remove_utf8_from_xml(file_content)
                    file_content = remove_xmlns_from_xml(file_content)
                    root = ET.fromstring(file_content)

                    return root
        except:
            pass

    def end_analysis(self):
        """ Call methods to check for violations in xml, java or properties configuration files """

        self.check_springsecurity_version()

        def check_violation_in_xml_file():

            for xml_file in self.xml_files:
                xml_file_path = xml_file.get_path()
                root = self.get_root_of_xml_file(xml_file_path)
                if root:
                    self.quality_rules_obj.interpret_violations_in_xml_config(
                        xml_file, root)

                    """ Call method to check violation: StrictHttpFirewallShouldBeDefaultHttpFirewall, in xml file """
                    if self.springsecurity_version:
                        is_default_http_firewall_in_xml = self.quality_rules_obj.qr_StrictHttpFirewallShouldBeDefaultHttpFirewall(
                            xml_file=xml_file, root=root)

                        if is_default_http_firewall_in_xml:
                            self.defaulthttp_firewall_in_xml = True
                else:
                    pass

        def check_violation_in_java_file():
            """ Call method present in the file:qualityrules.py, to check for violation:AvoidUsingControllerAdviceAndHandlerExceptionResolverSimultaneously """
            if self.HandlerExceptionResolver_methods and self.ControllerAdvice_class:
                self.quality_rules_obj.AvoidUsingControllerAdviceAndHandlerExceptionResolverSimultaneously(
                    self.java_parser, self.HandlerExceptionResolver_methods, self.ControllerAdvice_class)

            """ Call method present in the file:qualityrules.py to check for violation:AvoidUsingGenericAuthenticationExceptionClass """
            self.quality_rules_obj.AvoidUsingGenericAuthenticationExceptionClass(
                self.java_parser, self.methods_list)

            """ Call method present in the file:qualityrules.py to check for violation:StrictHttpFirewallShouldBeDefaultHttpFirewall """
            if self.springsecurity_version:

                if self.httpFirewallInJava:
                    self.defaulthttp_firewall_in_java = self.quality_rules_obj.qr_StrictHttpFirewallShouldBeDefaultHttpFirewall(
                        import_token=self.httpFirewallInJava[0], project_obj=self.project, java_file=self.httpFirewallInJava[1])

                if not self.defaulthttp_firewall_in_java and not self.defaulthttp_firewall_in_xml:

                    self.project.save_violation('CAST_Java_StrictHttpFirewallShouldBeDefaultHttpFirewall.StrictHttpFirewallShouldBeDefaultHttpFirewall',
                                                self.project.get_position())

        def check_violation_in_properties_file():
            """ Call method present in the file:qualityrules.py, to check for the rule:SpringSecurityEnsuretoEnableSpringBootActuatorEndpoint"""
            if self.properties_files:
                self.quality_rules_obj.SpringSecurityEnsuretoEnableSpringBootActuatorEndpoint(
                    self.properties_files)

        check_violation_in_xml_file()
        check_violation_in_java_file()
        check_violation_in_properties_file()
