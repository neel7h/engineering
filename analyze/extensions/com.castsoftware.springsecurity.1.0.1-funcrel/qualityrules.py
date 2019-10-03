'''
Created on July 13, 2018
@author: RUP
'''

from cast.analysers import log, Bookmark, CustomObject
from cast.application import open_source_file


class QualityRules():

    def __init__(self):
        self.ast = None

    def interpret_violations_in_xml_config(self, xml_file, xml_file_root):
        """ Check violations in xml confiuration files for rules:
            1.qr_NeverEnableSpringBootDevtoolsInProduction
            2.qr_csrfProtectionMustNotBeDisabled
            3.qr_ensurettpBasicAuthentication
            4.qr_ensureContentSecurityPolicy()
            5.qr_cookiesMustBeDeletedDuringLogout()
            6.qr_ensureInvalidatingHttpSessionDuringLogout()
            7.qr_specifyPermitAllOrUserRoleToAccessUrl()
            8.qr_setXFrameOptiontoAvoidClickjackingAttack()"""

        def qr_NeverEnableSpringBootDevtoolsInProduction():
            rule_name = 'CAST_Java_Metric_NeverEnableSpringBootDevtoolsInProduction.NeverEnableSpringBootDevtoolsInProduction'

            def saveViolation(elem):

                if xml_file in xml_file_objects_dict.keys():
                    xml_file_object = xml_file_objects_dict[xml_file]

                else:
                    xml_file_object = QR_Common_Operations().create_xmlFileObject(
                        xml_file)

                line = elem.sourceline + 1
                bookmark = Bookmark(
                    xml_file.get_position().get_file(), line, 1, line, -1)
                self.save_violations(xml_file_object,
                                     rule_name,
                                     violation_bookmark=bookmark)

            def check_optional_tag(elem_parent, elem):

                optional_tag = 'optional'
                is_optional_tag = elem_parent.find('.//%s' % optional_tag)

                if is_optional_tag is not None:

                    if is_optional_tag.text == 'false':
                        saveViolation(is_optional_tag)

                else:

                    saveViolation(elem)

            bean_namespace = {'project': "http://maven.apache.org/POM/4.0.0"}
            search_elem = "artifactId"
            element_in_bean = xml_file_root.findall(
                ".//%s" % search_elem, bean_namespace)
            for elem in element_in_bean:

                if elem.text == 'spring-boot-devtools':
                    elem_parent = elem.getparent()
                    # Calling method to check for the presence of <optional>
                    # tag.
                    check_optional_tag(elem_parent, elem)

        def qr_csrfProtectionMustNotBeDisabled():
            """ Save violation if csrf protection is disabled """

            rule_name = 'CAST_Java_Metric_SpringSecurityCSRFProtectionMustNotBeDisabled.CSRFProtection'
            fileObj_bookmark_tuple = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                 xml_file_root,
                                                                                                 "csrf[@disabled='true']")

            if fileObj_bookmark_tuple:
                file_object = fileObj_bookmark_tuple[0]
                bookmark = fileObj_bookmark_tuple[1]
                self.save_violations(file_object,
                                     rule_name,
                                     violation_bookmark=bookmark)

        def qr_ensureHttpBasicAuthentication():
            """ Save violation if not authenticated with http-basic in xml configuration """

            rule_name = 'CAST_Java_Metric_EnsureRequestIsAuthenticatedWithHTTPBasic.AuthenticationWithHTTPBasic'

            fileObj_bookmark_tuple1 = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                  xml_file_root,
                                                                                                  "http-basic")
            fileObj_bookmark_tuple2 = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                  xml_file_root,
                                                                                                  "authentication-manager")

            if fileObj_bookmark_tuple2 and not fileObj_bookmark_tuple1:
                xml_file_obj = fileObj_bookmark_tuple2[0]
                authentication_bookmark = fileObj_bookmark_tuple2[1]
                self.save_violations(xml_file_obj,
                                     rule_name,
                                     violation_bookmark=authentication_bookmark)

        def qr_ensureContentSecurityPolicy():
            """ Save violation if content security policy is not validated with headers """

            rule_name = 'CAST_Java_Metric_EnsureContentSecurityPolicy.ContentSecurityPolicy'

            fileObj_bookmark_tuple1 = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                  xml_file_root,
                                                                                                  "content-security-policy")
            fileObj_bookmark_tuple2 = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                  xml_file_root,
                                                                                                  "headers")

            if fileObj_bookmark_tuple2 and not fileObj_bookmark_tuple1:
                xml_file_obj = fileObj_bookmark_tuple2[0]
                header_bookmark = fileObj_bookmark_tuple2[1]
                self.save_violations(xml_file_obj, rule_name,
                                     violation_bookmark=header_bookmark)

        def qr_cookiesMustBeDeletedDuringLogout():
            """ Save violation if cookies are not deleted during logout """

            rule_name = 'CAST_Java_Metric_DeleteCookiesDuringLogout.DeleteCookiesDuringLogout'

            fileObj_bookmark_tuple1 = QR_Common_Operations().trace_violation_in_xml_configuration(
                xml_file, xml_file_root, "logout[@delete-cookies]")
            fileObj_bookmark_tuple2 = QR_Common_Operations(
            ).trace_violation_in_xml_configuration(xml_file, xml_file_root, "logout")

            if fileObj_bookmark_tuple2 and not fileObj_bookmark_tuple1:
                xml_file_obj = fileObj_bookmark_tuple2[0]
                logout_bookmark = fileObj_bookmark_tuple2[1]

                self.save_violations(xml_file_obj,
                                     rule_name,
                                     violation_bookmark=logout_bookmark)

        def qr_ensureInvalidatingHttpSessionDuringLogout():
            """ Save violation if http session is not invalidated during logout """

            fileObj_bookmark_tuple1 = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                  xml_file_root,
                                                                                                  "logout[@invalidate-session='true']")
            fileObj_bookmark_tuple2 = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                  xml_file_root,
                                                                                                  "logout")

            if fileObj_bookmark_tuple2 and not fileObj_bookmark_tuple1:
                xml_file_obj = fileObj_bookmark_tuple2[0]
                logout_bookmark = fileObj_bookmark_tuple2[1]
                self.save_violations(xml_file_obj,
                                     'CAST_Java_Metric_EnsureInvalidatingHttpSessionDuringLogout.InvalidatingHttpSessionDuringLogout',
                                     violation_bookmark=logout_bookmark)

        def qr_specifyPermitAllOrUserRoleToAccessUrl():
            """ Save violation when permitAll() or User role is not defined for accessing URl """

            fileObj_bookmark_tuple1 = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                  xml_file_root,
                                                                                                  "intercept-url[@pattern]")
            fileObj_bookmark_tuple2 = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                  xml_file_root,
                                                                                                  "intercept-url[@access]",
                                                                                                  search_elem_obj=True)

            if fileObj_bookmark_tuple1 and fileObj_bookmark_tuple2:
                intercept_url_list = fileObj_bookmark_tuple2[2]

                for intercept_url in intercept_url_list:
                    role = intercept_url.attrib.get('access')

                    if role == 'permitAll' or role.startswith('hasRole'):
                        pass
                    else:
                        xml_file_obj = fileObj_bookmark_tuple2[0]
                        violation_bookmark = fileObj_bookmark_tuple2[1]
                        self.save_violations(xml_file_obj,
                                             'CAST_Java_Metric_SpecifyPermitAllOrUserRoleToAccessUrlOfApplication.SpecifyPermitAllOrUserRoleToAccessUrl',
                                             violation_bookmark=violation_bookmark)

        def qr_setXFrameOptiontoAvoidClickjackingAttack():
            """ Save violation if frame option is not set correctly """

            fileObj_bookmark_tuple1 = QR_Common_Operations().trace_violation_in_xml_configuration(xml_file,
                                                                                                  xml_file_root,
                                                                                                  "frame-options",
                                                                                                  search_elem_obj=True)
            if fileObj_bookmark_tuple1:
                frame_options_list = fileObj_bookmark_tuple1[2]

                for option in frame_options_list:
                    valid_option = option.attrib.get('policy')
                    disabled_option = option.attrib.get('disabled')
                    valid_option_list = ['SAMEORIGIN', 'DENY']

                    if valid_option not in valid_option_list or disabled_option == 'true':
                        xml_file_obj = fileObj_bookmark_tuple1[0]
                        violation_bookmark = fileObj_bookmark_tuple1[1]

                        self.save_violations(xml_file_obj,
                                             'CAST_Java_Metric_SetXFrameOptionCorrectlyToAvoidClickjackingAttack.SetXFrameOptionCorrectlyToAvoidClickjackingAttack',
                                             violation_bookmark=violation_bookmark)

        if xml_file and xml_file_root:
            qr_csrfProtectionMustNotBeDisabled()
            qr_ensureHttpBasicAuthentication()
            qr_ensureContentSecurityPolicy()
            qr_cookiesMustBeDeletedDuringLogout()
            qr_ensureInvalidatingHttpSessionDuringLogout()
            qr_specifyPermitAllOrUserRoleToAccessUrl()
            qr_setXFrameOptiontoAvoidClickjackingAttack()
            qr_NeverEnableSpringBootDevtoolsInProduction()

    def qr_StrictHttpFirewallShouldBeDefaultHttpFirewall(self, xml_file=None, root=None, import_token=None, project_obj=None, java_file=None):
        """ Check for violation in xml configuration and java configuration for the rule :StrictHttpFirewallShouldBeDefaultHttpFirewall """
        defaultHttpClass = "org.springframework.security.web.firewall.DefaultHttpFirewall"
        strictHttpClass = "org.springframework.security.web.firewall.StrictHttpFirewall"

        def check_violation_in_java_config():
            """Check if violation is present for the rule:StrictHttpFirewallShouldBeDefaultHttpFirewall
            in java confiuration file"""
            begin_line = import_token.get_begin_line()
            begin_column = import_token.get_begin_column()
            end_line = import_token.get_end_line()
            end_column = import_token.get_end_column()

            violation_bookmark = Bookmark(
                java_file, begin_line, begin_column, end_line, end_column)

            if import_token.get_name() == "org.springframework.security.web.firewall.DefaultHttpFirewall":
                project_obj.save_violation('CAST_Java_StrictHttpFirewallShouldBeDefaultHttpFirewall.StrictHttpFirewallShouldBeDefaultHttpFirewall',
                                           violation_bookmark)

                return True

        def check_http_firewall(firewall_class_name):
            """ Check if there is a present of http firewall in code"""

            bean_namespace = {
                'beans': 'http://www.springframework.org/schema/beans'}
            search_elem = 'http-firewall'
            element_in_bean = root.findall(".//%s" % search_elem)

            if element_in_bean:
                ref = element_in_bean[0].attrib.get('ref')
                ref1 = 'bean'

                element_beans = root.findall(
                    ".//beans:%s" % ref1, bean_namespace)

                if element_beans:
                    for bean in element_beans:
                        if bean.attrib.get('id') == ref and bean.attrib.get('class') == firewall_class_name:

                            return True, bean

        def check_violation_in_xml_config():
            """Check if violation is present for the rule:StrictHttpFirewallShouldBeDefaultHttpFirewall
            in xml confiuration file"""

            is_strictHttpFirewall = check_http_firewall(strictHttpClass)
            is_defaultHttpFirewall = check_http_firewall(defaultHttpClass)

            if is_defaultHttpFirewall and not is_strictHttpFirewall:
                line = is_defaultHttpFirewall[1].sourceline + 1

                xml_file_project = xml_file.get_project()

                violation_bookmark = Bookmark(xml_file, line, 1, line, -1)
                xml_file_project.save_property(
                    "CAST_Java_SpringSecurity_Version.SpringSecurityVersion", 1)
                xml_file_project.save_violation('CAST_Java_StrictHttpFirewallShouldBeDefaultHttpFirewall.StrictHttpFirewallShouldBeDefaultHttpFirewall',
                                                violation_bookmark)
                return True

        if root:
            if check_violation_in_xml_config():
                return True

        if import_token:
            if check_violation_in_java_config():
                return True

    def interpret_violations_in_java_config(self, java_parser=None, member=None, annotation_object=None,
                                            class_object=None):
        """ Check violations in java confiuration files for rules:
            1.qr_csrfProtectionMustNotBeDisabled
            2.qr_ensureFormLoginIsDeclaredAfterAuth()
            3.qr_ensurettpBasicAuthentication
            4.qr_ensureContentSecurityPolicy()
            5.qr_cookiesMustBeDeletedDuringLogout()
            6.qr_ensureInvalidatingHttpSessionDuringLogout()
            7.qr_specifyPermitAllOrUserRoleToAccessUrl()
            8.qr_setXFrameOptiontoAvoidClickjackingAttack()
            9.qr_avoidUsingSpringSecurityDebugMode()
            10.qr_setXFrameOptiontoAvoidClickjackingAttack()
            11.qr_ensureHttpMethodsInRequestMapping()"""

        if java_parser and member is not None:
            self.ast = java_parser.get_object_ast(member)

        def qr_csrfProtectionMustNotBeDisabled():
            """ Save violation if CSRF protection is disabled in java configuration """

            csrf_protection_disabled = '.disable'
            csrf_protection_tags = ['.csrf', 'http.csrf', 'csrf']
            bookmark_list = QR_Common_Operations().trace_violation_in_java_configuration(ast, csrf_protection_tags,
                                                                                         csrf_protection_disabled)
            if bookmark_list:
                for bookmark_tuple in bookmark_list:
                    bookmark = Bookmark(member.get_position().get_file(), bookmark_tuple[0], bookmark_tuple[1],
                                        bookmark_tuple[0], bookmark_tuple[2] + 3)

                    self.save_violations(member,
                                         'CAST_Java_Metric_SpringSecurityCSRFProtectionMustNotBeDisabled.CSRFProtection',
                                         violation_bookmark=bookmark)

        def qr_ensureHttpBasicAuthentication():
            """ Save violation if not authenticated with http-basic in java configuration """

            http_basic_authentication_tags = ['.httpBasic', 'http.httpBasic']
            authorization_tags = [
                '.authorizeRequests', 'http.authorizeRequests', 'authorizeRequests']

            dictViolation_elems = QR_Common_Operations().trace_violation_in_java_configuration(ast,
                                                                                               http_basic_authentication_tags,
                                                                                               authorization_tags,
                                                                                               'True')

            if dictViolation_elems:
                for violationElem in dictViolation_elems.values():
                    self.save_violations(member,
                                         'CAST_Java_Metric_EnsureRequestIsAuthenticatedWithHTTPBasic.AuthenticationWithHTTPBasic',
                                         violationElem=violationElem)

        def qr_ensureContentSecurityPolicy():
            """ Save violation if content security policy is not validated with headers """
            content_security_policy_tags = [
                '.contentSecurityPolicy', 'contentSecurityPolicy']
            headers_tags = ['.headers', 'http.headers', 'headers']

            dictViolation_elems = QR_Common_Operations().trace_violation_in_java_configuration(ast,
                                                                                               content_security_policy_tags,
                                                                                               headers_tags, 'True')

            if dictViolation_elems:
                for violationElem in dictViolation_elems.values():
                    self.save_violations(member, 'CAST_Java_Metric_EnsureContentSecurityPolicy.ContentSecurityPolicy',
                                         violationElem=violationElem)

        def qr_ensureFormLoginIsDeclaredAfterAuth():
            """ Save violation if form login is declared before authorization """

            form_login_tags = ['.formLogin', 'http.formLogin', 'formLogin']
            authorization_tags = [
                '.authorizeRequests', 'http.authorizeRequests', 'authorizeRequests']

            dictViolation_elems = QR_Common_Operations().trace_violation_in_java_configuration(ast, authorization_tags,
                                                                                               form_login_tags, 'True')

            if dictViolation_elems:
                for violationElem in dictViolation_elems.values():
                    self.save_violations(member,
                                         'CAST_Java_Metric_EnsureFormLoginAfterAuthenticationAndAuthorization.FormLoginDeclaration',
                                         violationElem=violationElem)

        def qr_cookiesMustBeDeletedDuringLogout():
            """ Save violation if cookies are not deleted during logout in java configuration """

            delete_cookies_tags = ['deleteCookies', '.deleteCookies']
            logout_tags = ['.logout', 'logout']

            dictViolation_elems = QR_Common_Operations().trace_violation_in_java_configuration(ast, delete_cookies_tags,
                                                                                               logout_tags, 'True')

            if dictViolation_elems:
                for violationElem in dictViolation_elems.values():
                    self.save_violations(member, 'CAST_Java_Metric_DeleteCookiesDuringLogout.DeleteCookiesDuringLogout',
                                         violationElem=violationElem)

        def qr_ensureInvalidatingHttpSessionDuringLogout():
            """ Save violation if http session is not invalidated during logout """

            httpsession_invalidate_tags = [
                '.invalidateHttpSession', 'invalidateHttpSession']
            logout_tags = ['.logout', 'logout']

            def getViolationElem(req_ast):

                if req_ast:
                    violation_elements = [tok for tok in req_ast[0].get_children() if
                                          tok.text in httpsession_invalidate_tags]
                    token_elems = req_ast[0].children
                    for child_token in violation_elements:
                        paren_token = None
                        req_index = token_elems.index(child_token, ) + 1
                        if token_elems[req_index].get_type() == 'Parenthesis':
                            paren_token = token_elems[req_index]

                        elif token_elems[req_index + 1].get_type() == 'Parenthesis':
                            paren_token = token_elems[req_index + 1]

                        if paren_token:
                            http_session_value = [http_session.text for http_session in paren_token.get_children() if
                                                  http_session.text == 'false']
                            if http_session_value:
                                self.save_violations(member,
                                                     'CAST_Java_Metric_EnsureInvalidatingHttpSessionDuringLogout.InvalidatingHttpSessionDuringLogout',
                                                     violationElem=child_token)

            curlybracket_ast = [ast_child for ast_child in ast.get_children(
            ) if ast_child.get_type() == 'CurlyBracket']
            getViolationElem(curlybracket_ast)

            for statement_ast in ast.get_statements():
                getViolationElem([statement_ast])

            dictViolation_elems = QR_Common_Operations().trace_violation_in_java_configuration(ast,
                                                                                               httpsession_invalidate_tags,
                                                                                               logout_tags, 'True')
            if dictViolation_elems:
                for violationElem in dictViolation_elems.values():
                    self.save_violations(member,
                                         'CAST_Java_Metric_EnsureInvalidatingHttpSessionDuringLogout.InvalidatingHttpSessionDuringLogout',
                                         violationElem=violationElem)

        def qr_avoidUsingSpringSecurityDebugMode():
            """ Save violation when Spring Security Debug mode is on """

            class_ast = java_parser.get_object_ast(class_object)
            annotation_ast = class_ast.get_annotations()
            violationElem = [
                anno for anno in annotation_ast if anno.get_type_name() == 'EnableWebSecurity']
            if violationElem is not None:
                self.save_violations(class_object,
                                     'CAST_Java_Metric_AvoidUsingSpringSecurityDebugMode.AvoidSpringSecurityDebugMode',
                                     violationElem=violationElem[0])

        def qr_specifyPermitAllOrUserRoleToAccessUrl():
            """ Save violation when permitAll() or User role is not defined for accessing URl """

            ant_matchers_tag = [
                'antMatchers', 'loginPage', '.antMatchers', '.loginPage']
            access_tag = [
                'hasRole', '.hasRole', 'permitAll', '.permitAll', 'access', '.access']

            dictViolation_elems = QR_Common_Operations().trace_violation_in_java_configuration(ast, access_tag,
                                                                                               ant_matchers_tag, 'True')

            if dictViolation_elems:
                for violationElem in dictViolation_elems.values():
                    self.save_violations(member,
                                         'CAST_Java_Metric_SpecifyPermitAllOrUserRoleToAccessUrlOfApplication.SpecifyPermitAllOrUserRoleToAccessUrl',
                                         violationElem=violationElem)

        def qr_setXFrameOptiontoAvoidClickjackingAttack():
            """ Save violation if frame option is not set correctly """

            headers_tags = ['frameOptions', '.frameOptions']
            x_frameoptions_tags = [
                '.sameOrigin', 'sameOrigin', '.deny', 'deny']

            dictViolation_elems = QR_Common_Operations().trace_violation_in_java_configuration(ast, x_frameoptions_tags,
                                                                                               headers_tags, 'True')

            if dictViolation_elems:
                for violationElem in dictViolation_elems.values():
                    self.save_violations(member,
                                         'CAST_Java_Metric_SetXFrameOptionCorrectlyToAvoidClickjackingAttack.SetXFrameOptionCorrectlyToAvoidClickjackingAttack',
                                         violationElem=violationElem)

        def qr_ensureHttpMethodsInRequestMapping():
            """ Save violation when Spring Security Debug mode is on """

            annotation_ast = self.ast.get_annotations()
            violationElem = [
                anno for anno in annotation_ast if anno.get_type_name() == 'RequestMapping']
            if violationElem is not None:
                self.save_violations(member,
                                     'CAST_Java_Metric_EnsureToSpecifyHttpMethodsInRequestMapping.EnsureToSpecifyHttpMethodsInRequestMapping',
                                     violationElem=violationElem[0])

        if self.ast:
            ast = self.ast
            qr_csrfProtectionMustNotBeDisabled()
            qr_ensureHttpBasicAuthentication()
            qr_ensureContentSecurityPolicy()
            qr_ensureFormLoginIsDeclaredAfterAuth()
            qr_cookiesMustBeDeletedDuringLogout()
            qr_ensureInvalidatingHttpSessionDuringLogout()
            qr_specifyPermitAllOrUserRoleToAccessUrl()
            qr_setXFrameOptiontoAvoidClickjackingAttack()
            qr_ensureHttpMethodsInRequestMapping()

        if annotation_object and class_object is not None:
            qr_avoidUsingSpringSecurityDebugMode()

    def add_parameterization(self, options):
        """ This method performs parameterization to get the parameters of the method access. This is to check for the
        qr: 'Specify permitAll or hasRole for accessing url'
         """
        options.add_parameterization(
            'org.springframework.security.config.annotation.web.configurers.ExpressionUrlAuthorizationConfigurer.AuthorizedUrl.access(java.lang.String)',
            [1], self.callback)

    def callback(self, values, caller, line, column):

        if values:
            try:
                if 'hasRole' in values[1][0] or 'permitAll' in values[1][0]:
                    pass

                else:
                    bookmark = Bookmark(
                        caller.get_position().get_file(), line, column, line, -1)
                    self.save_violations(caller,
                                         'CAST_Java_Metric_SpecifyPermitAllOrUserRoleToAccessUrlOfApplication.SpecifyPermitAllOrUserRoleToAccessUrl',
                                         violation_bookmark=bookmark)

            except ValueError:
                pass

    def save_violations(self, violation_object, violation_name, violation_bookmark=None, violationElem=None):
        """ Save violation for java configuration and xml configuration """

        if violationElem and not violation_bookmark:
            line = violationElem.get_begin_line()
            begin_column = violationElem.get_begin_column()
            end_column = violationElem.get_end_column()

            violation_bookmark = Bookmark(violation_object.get_position().get_file(), line, begin_column, line,
                                          end_column + 3)
        violation_object.save_violation(violation_name, violation_bookmark)

    def AvoidUsingGenericAuthenticationExceptionClass(self, java_parser, methods_list):
        """Check for te violation for the rule: AvoidUsingGenericAuthenticationExceptionClass"""

        for method in methods_list:

            ast = java_parser.get_object_ast(method)

            if ast:
                for child in ast.children:

                    try:
                        if child.text == 'AuthenticationException':
                            self.save_violations(method,
                                                 'CAST_Java_Metric_AvoidUsingGenericAuthenticationExceptionClass.AvoidUsingGenericAuthenticationExceptionClass',
                                                 violationElem=child)
                    except:
                        pass

                for annotation in ast.get_annotations():
                    annotation_token = [
                        token for token in annotation.children if token.text == '@ExceptionHandler']
                    if annotation_token:

                        req_token = [token for token in annotation.children if
                                     token.get_type() == 'Parenthesis' and str(token).find(
                                         'AuthenticationException.class') > -1]

                        if req_token:

                            self.save_violations(method,
                                                 'CAST_Java_Metric_AvoidUsingGenericAuthenticationExceptionClass.AvoidUsingGenericAuthenticationExceptionClass',
                                                 violationElem=req_token[0])

    def AvoidUsingControllerAdviceAndHandlerExceptionResolverSimultaneously(self, java_parser,
                                                                            HandlerExceptionResolver_method_list,
                                                                            ControllerAdvice_class_list):
        """Check for the violation for the rule:AvoidUsingControllerAdviceAndHandlerExceptionResolverSimultaneously"""

        def get_bookmark(violation_obj, violationElem):
            line = violationElem.get_begin_line()
            begin_column = violationElem.get_begin_column()
            end_column = violationElem.get_end_column()

            violation_bookmark = Bookmark(violation_obj.get_position().get_file(), line, begin_column, line,
                                          end_column + 3)
            return violation_bookmark

        def isHandlerExceptionResolver(method_list):

            for method in method_list:
                ast = java_parser.get_object_ast(method)
                if ast:
                    try:
                        req_token = [c for child in ast.children if child.get_type() == 'Parenthesis' for c in
                                     child.children if str(c.get_type()) == 'HandlerExceptionResolver']

                        if req_token:
                            return [method, req_token]

                    except:
                        pass

        def isControllerAdvice(class_list):

            for exception_class in class_list:
                ast = java_parser.get_object_ast(exception_class)
                if ast:
                    req_anno = [anno_child for anno in ast.get_annotations() for anno_child in anno.children if
                                anno_child.text == '@ControllerAdvice']
                    return [exception_class, req_anno]

        result1 = isHandlerExceptionResolver(
            HandlerExceptionResolver_method_list)
        result2 = isControllerAdvice(ControllerAdvice_class_list)
        if result1 and result2:
            bookmark1 = get_bookmark(result1[0], result1[1][0])
            bookmark2 = get_bookmark(result2[0], result2[1][0])
            project = result1[0].get_position().get_file().get_project()
            project.save_violation(
                'CAST_Java_Metric_AvoidUsingControllerAdviceAndHandlerExceptionResolverSimultaneously.AvoidUsingControllerAdviceAndHandlerExceptionResolverSimultaneously',
                bookmark1, [bookmark2])

    def SpringSecurityEnsuretoEnableSpringBootActuatorEndpoint(self, properties_files):
        """ Check for violation in xml configuration and java configuration files for the rule: EnsuretoEnableSpringBootActuatorEndpoint """

        def trace_violation():

            endpoint_name = key_value[0].strip()
            endpoint_value = key_value[1].strip()
            if endpoint_name == 'management.security.enabled' and endpoint_value == 'false':
                violation_bookmark = Bookmark(properties_file[0].get_position().get_file(), line_no + 1, 1, line_no + 1,
                                              -1)
                properties_file[0].save_violation(
                    'CAST_Java_Metric_EnsureToEnableSpringBootActuatorEndpoint.EnsureToEnableSpringBootActuatorEndpoint',
                    violation_bookmark)

            if endpoint_name == 'endpoints.health.sensitive' and endpoint_value == 'false':
                violation_bookmark = Bookmark(properties_file[0].get_position().get_file(), line_no + 1, 1, line_no + 1,
                                              -1)
                properties_file[0].save_violation(
                    'CAST_Java_Metric_EnsureToEnableSpringBootActuatorEndpoint.EnsureToEnableSpringBootActuatorEndpoint',
                    violation_bookmark)

            if (endpoint_name == 'endpoints.shutdown.enabled' and endpoint_value == 'true') or \
               (endpoint_name == 'management.endpoint.shutdown.enabled' and endpoint_value == 'true'):
                violation_bookmark = Bookmark(properties_file[0].get_position().get_file(), line_no + 1, 1, line_no + 1,
                                              -1)
                properties_file[0].save_violation(
                    'CAST_Java_Metric_EnsureSpringBootShutdownActuatorEndpointisDisabled.EnsureSpringBootShutdownActuatorEndpointisDisabled',
                    violation_bookmark)

            if endpoint_name == 'spring.application.admin.enabled' and endpoint_value == 'false':
                violation_bookmark = Bookmark(properties_file[0].get_position().get_file(), line_no + 1, 1, line_no + 1,
                                              -1)
                properties_file[0].save_violation(
                    'CAST_Java_Metric_EnsureToEnableSpringBootAdminMBean.EnsureToEnableSpringBootAdminMBean',
                    violation_bookmark)

        for properties_file_path, properties_file in properties_files.items():
            sep = "="
            comment_char = "#"

            with open_source_file(properties_file_path) as f:
                for line_no, line in enumerate(f):
                    line = line.strip()
                    if line and not line.startswith(comment_char):
                        key_value = line.split(sep)
                        if len(key_value) >= 2:
                            trace_violation()


xml_file_objects_dict = {}


class QR_Common_Operations():
    """ This class performs operations which are common for checking the violation in java configuration
       and xml configuration of spring security.For Eg:
       > Getting violation tag through Ast.
       > Parsing through xml file."""

    def __init__(self):
        self.bookmarks = []

    def create_xmlFileObject(self, xml_file):
        """Creating xml file object for the xml file in which violation is encountered """
        xml_file_object = CustomObject()
        xml_file_object.set_name(xml_file.get_name())
        xml_file_object.set_type('CAST_SpringSecurity_Configuration')
        xml_file_object.set_parent(xml_file)
        xml_file_object.set_guid(xml_file.get_fullname())
        xml_file_object.save()
        xml_file_object.save_position(xml_file.get_position())
        # maintaining dictionary to avoid creating duplicate objects.
        xml_file_objects_dict[xml_file] = xml_file_object
        return xml_file_object

    def trace_violation_in_xml_configuration(self, xml_file_object, root, search_elem, search_elem_obj=False):
        """ This method performs parsing of xml files and search for the given tag.
        -search_elem: This element needs to be searched in the given xml file.
          this element specifies the presence of violation in xml configuration

        -xml_file_object: object of xml file which is to be parsed.
        :rtype: tuple"""

        try:
            security_namespace = {
                'security': 'http://www.springframework.org/schema/security'}

            element_in_bean = root.findall(".//%s" % search_elem)
            element_in_security_bean = root.findall(
                ".//security:%s" % search_elem, security_namespace)

            if element_in_bean:
                violation_elem = element_in_bean
            elif element_in_security_bean:
                violation_elem = element_in_security_bean
            else:
                violation_elem = None

            if violation_elem:

                line = violation_elem[0].sourceline + 1
                bookmark = Bookmark(
                    xml_file_object.get_position().get_file(), line, 1, line, -1)

                if xml_file_object in xml_file_objects_dict.keys():
                    xml_file_custom_obj = xml_file_objects_dict[
                        xml_file_object]

                else:

                    xml_file_custom_obj = self.create_xmlFileObject(
                        xml_file_object)
                if search_elem_obj:
                    return (xml_file_custom_obj, bookmark, violation_elem)

                return (xml_file_custom_obj, bookmark)

        except Exception:
            log.warning(
                'An error occurred in file ' + str(xml_file_object.get_path()))

        return None

    def trace_violation_in_java_configuration(self, ast, violation_tags, config_tags, dict_required=False):
        """ This method performs ast operation on the given java file and check for the violation """

        def get_violationElem(curlybracket_ast):

            if curlybracket_ast:
                violation_elements = [tok for tok in curlybracket_ast[0].get_children() if
                                      tok.text and tok.text in violation_tags]
                config_elements = [tok for tok in curlybracket_ast[0].get_children() if
                                   tok.text and tok.text in config_tags]

                return violation_elements, config_elements

        def get_fromAst(violation_elements, config_elements):

            if config_elements:
                self.config_elems_dict = {}

                for elem in config_elements:
                    self.config_elems_dict[elem.get_begin_line()] = elem

                if violation_elements:

                    for violation_token in violation_elements:

                        if self.config_elems_dict.keys():
                            takeClosest = lambda vioElem1_line, vioElem2_line: min(vioElem2_line,
                                                                                   key=lambda x: abs(x - vioElem1_line))
                            match_no = takeClosest(
                                violation_token.get_begin_line(), self.config_elems_dict.keys())

                            line = violation_token.get_begin_line()
                            begin_column = violation_token.get_begin_column()
                            end_column = self.config_elems_dict[
                                match_no].get_end_column()

                            self.bookmarks.append(
                                (line, begin_column, end_column))
                            del self.config_elems_dict[match_no]
                return self.config_elems_dict

        curlybracket_ast = [ast_child for ast_child in ast.get_children(
        ) if ast_child.get_type() == 'CurlyBracket']
        violation_elements, config_elements = get_violationElem(
            curlybracket_ast)

        for statement_ast in ast.get_statements():

            violation_elementsInStatement, config_elementsInStatement = get_violationElem(
                [statement_ast])

            if violation_elementsInStatement:
                violation_elements = violation_elements + \
                    violation_elementsInStatement
            if config_elementsInStatement:
                config_elements = config_elements + config_elementsInStatement

        config_elems_dict = get_fromAst(violation_elements, config_elements)

        if dict_required:
            return config_elems_dict

        elif self.bookmarks:
            return self.bookmarks
