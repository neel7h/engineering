import re
import os
import cast.analysers.ua
from javascript_parser.symbols import SymbolLink, AstString, HtmlTextWithPosition, HttpCall, StrutsAction, AppletReference, BeanMethodReference
from cast.analysers import Bookmark
from collections import OrderedDict
from java_parser.parser import parse as jvparse
import traceback

def evaluate(variableName, javaText):
    
    values = []
    try:

        if javaText:
            results = jvparse(javaText)
            elements = results[-1].parent.get_element(variableName)
            for element in elements:
                try:
                    ev = element.initialisation.evaluate_as_constant()
                    if ev:
                        values.append(ev)
                except:
                    cast.analysers.log.debug('Internal issue when parsing java code: ' + str(traceback.format_exc()))
    except:
        cast.analysers.log.debug('Internal issue when parsing java code: ' + str(traceback.format_exc()))
    return values

class HtmlContext:

    def __init__(self, parent, tagName, tagWithPos, ast):
        
        self.current_tag = ( tagName.lower() if tagName else None )
        self.current_language_is_supported = True
        self.current_ast = ast
        self.currentStrutsAction = None
        self.hiddenStrutsActions = []
        self.currentServletMapping = None
        self.tagWithPos = tagWithPos
        self.valuesByAttributes = {}
        self.astValuesByAttributes = {}
        self.current_text = ''
        self.razor_text = ''
        self.parent = parent
        # for <c:url var="saveProductFile" value="/admin/products/product/saveDigitalProduct.html" />
        # it contains the table value by var
        self.urlVars = OrderedDict()
        self.params = OrderedDict()
        self.containsId = False

    def get_current_context_with_tag(self, tagName):
        if self.current_tag == tagName.lower() or (self.current_tag and ':' in self.current_tag and self.current_tag.endswith( ':' + tagName.lower() )):
            return self
        if self.parent:
            return self.parent.get_current_context_with_tag(tagName)
        return None
                
    def is_in_form_with_id(self):
        if self.current_tag == 'form' and self.containsId:
            return True
        if self.parent:
            return self.parent.is_in_form_with_id()
        return False
    
    def is_body(self):
        return False
        
    def is_video_or_audio(self):
        return ( self.current_tag in ['video', 'audio'] )
    
    def evaluate_spring_url(self, action):
        if action in self.urlVars:
            return self.urlVars[action]
        if self.parent:
            return self.parent.evaluate_spring_url(action)
        return '{}'
        
class BodyContext(HtmlContext):

    def __init__(self, parent, tagName, tagWithPos, ast):
        HtmlContext.__init__(self, parent, tagName, tagWithPos, ast)
        self.inputAutofocusPresent = False
        
    def is_body(self):
        return True
        
class TopLevelContext(HtmlContext):

    def __init__(self):
        HtmlContext.__init__(self, None, None, None, None)

class AttributeValueWithPosition:

    def __init__(self):
        
        self.attribute = None # AstString
        self.value = None     # AstString
        
    def get_attribute(self):
        return self.attribute
        
    def get_value(self):
        return self.value
    
    def __repr__(self):
        return self.attribute.__repr__() + ', ' + self.value.__repr__()

ngReferenceAttributesList = [ 'ng-app', 'data-ng-app',
                          'ng-controller', 'data-ng-controller',
                          'ng-include', 'data-ng-include'
                        ]

ngReferenceAttributes = { 'ngApp' : [ 'ng-app', 'data-ng-app' ],
                          'ngController' : [ 'ng-controller', 'data-ng-controller' ],
                          'ngInclude' : [ 'ng-include', 'data-ng-include' ]
                        }

def extract_javascript_code(txt):
    if not '<%' in txt or not '%>' in txt:
        return txt
    text = txt
    ltext = list(txt)
    l = len(text)

    while True:
        index = text.find('<%')
        if index < 0:
            break
        while index < l and text[index:index + 2] != '%>':
            if text[index] != '\n':
                ltext[index] = ' '
            index += 1
        if index >= 0:
            ltext[index] = ' '
            ltext[index + 1] = ' '
            index += 2
        else:
            break
        text = ''.join(ltext)
        
    return ''.join(ltext)
    
class HtmlInterpreter:
    
    def __init__(self, analyser, htmlContent, violations):
        
        self.analyser = analyser
        self.stack_context = []
        self.current_context = None
        self.lastPoppedContext = None
        self.htmlFile = htmlContent.file
        lowerHtmlPath = self.htmlFile.get_path().lower()
        if lowerHtmlPath.endswith(('.jsp', '.jsf', '.jsff', '.jspx', '.asp', '.aspx', '.htc')):
            self.jsp = True
        else:
            self.jsp = False
        self.htmlContent = htmlContent
        self.violations = violations
        self.in_text = False
        self.current_text = None
        self.current_text_ast_start = None
        self.current_text_ast_end = None
        self.in_javascript_code = False
        self.in_java_code = False
        self.in_css_code = False
        self.in_body = False
        self.in_builtin = False
        self.in_builtin_equal = False
        self.in_builtin_at = False
        
        self.strutsPrefix = None    # prefix in <%@ taglib prefix="s" uri="/struts-tags"%>
        self.strutsTilesPrefix = None    # prefix in <%@ taglib prefix="tiles" uri="/WEB-INF/struts-tiles"%>
        self.strutsBeanPrefix = None    # prefix in <%@ taglib prefix="bean" uri="/WEB-INF/struts-bean"%>
        self.strutsHtmlPrefix = 'html'    # prefix in <%@ taglib prefix="html" uri="/WEB-INF/struts-html"%>
        self.strutsFormPrefix = None    # prefix in <%@ taglib prefix="form" uri="/WEB-INF/struts-form"%>
        self.springFormPrefix = None    # <%@ taglib uri="http://www.springframework.org/tags/form" prefix="form"%>
        self.jadeFormPrefix = None    # <%@ taglib uri="WEB-INF/euamtags.tld" prefix="Euam" %>
        self.javaCorePrefix = None    # <%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c"%>
        self.pagerPrefix = None    # <%@ taglib prefix="pg" uri="http://jsptags.com/tags/navigation/pager"%>
        self.filePrefix = None    # <%@ include file="header.jsp"%>
        self.current_context = TopLevelContext()
        self.stack_context.append(self.current_context)
        self.urlsById = {}  # stores the content of <s:url action="banque" method="consulter" id="urlAcceuil"/>
        
    def finish(self):
        
        while self.current_context:
            self.end_tag('')
        
    def pop_context(self):
        
        poppedContext = self.stack_context.pop()
        if poppedContext:
            if self.stack_context:
                self.stack_context[-1].razor_text += poppedContext.razor_text
#             print(poppedContext.current_text)
        
        if len(self.stack_context) > 0:
            self.current_context = self.stack_context[-1]
        else:
            self.current_context = None
            
        return poppedContext
        
    def push_context(self, tagName, tagWithPos, ast):
        
        if tagName and tagName == 'body':
            self.current_context = BodyContext(self.current_context, tagName, tagWithPos, ast)
        else:
            self.current_context = HtmlContext(self.current_context, tagName, tagWithPos, ast)
        self.stack_context.append(self.current_context)
   
    # returns True if we are inside a tag whose name is tagName
    def is_in_tag(self, tagName):
        
        if not self.stack_context:
            return False
        
        upperTagname = tagName.upper()
        for context in reversed(self.stack_context):
            if context.current_tag and context.current_tag.upper() == upperTagname:
                return True
        return False
        
    def get_current_body_context(self):
        if not self.stack_context:
            return None
        for context in reversed(self.stack_context):
            if context.is_body():
                return context
        return None
        
    def get_current_video_or_audio_context(self):
        if not self.stack_context:
            return None
        for context in reversed(self.stack_context):
            if context.is_video_or_audio():
                return context
        return None
    
    def get_javascript_fragments(self):
        return self.htmlContent.get_javascript_fragments()
        
    def get_css_fragments(self):
        return self.htmlContent.get_css_fragments()

    """ Rules for tags which do not need to be closed explicitly:
        IMG closes when other tag opens.
        DT closes when DD or DT opens or DL closes.
        DD closes when DD or DT opens or DL closes.
        LI closes when LI opens or OL or UL closes.
        P closes when other tag opens.
    """
    def start_tag(self, tagName, ast):
        
        tagNameLower = tagName.lower()
        if self.current_context:
            if self.current_context.current_tag in ['img', 'input', 'br', 'meta'] and tagNameLower != 'a':
                self.end_tag(self.current_context.current_tag)
            elif self.current_context.current_tag in ['dt', 'dd']:
                if tagNameLower in ['dt', 'dd']:
                    self.end_tag(self.current_context.current_tag)
            elif self.current_context.current_tag == 'li':
                if tagNameLower == 'li':
                    self.end_tag('li')
        tagWithPos = HtmlTextWithPosition()
        tagWithPos.text = tagNameLower
        tagWithPos.token = ast
        self.push_context(tagNameLower, tagWithPos, ast)
        
        if tagNameLower == 'script':
            self.in_javascript_code = True
            self.current_text = ''
        elif tagNameLower == 'style':
            self.in_css_code = True
        elif tagNameLower == 'body':
            self.in_body = True
        elif tagNameLower == 'iframe':
            if self.is_in_tag('a'):
                self.violations.add_iframeInsideATag_violation(self.htmlContent, tagWithPos.create_bookmark(self.htmlFile))
        elif tagNameLower[0:2] == '%@':
            self.start_builtin_at(tagNameLower[2:].strip(), ast)
                
        if self.analyser:
            self.analyser.broadcast('start_html_tag', tagWithPos)
            
        return self.current_context

    def start_builtin_equal(self, tagName, ast):
        
        tagNameLower = tagName.lower()
        tagWithPos = HtmlTextWithPosition()
        tagWithPos.text = tagNameLower
        tagWithPos.token = ast
        self.push_context(tagNameLower, tagWithPos, ast)
         
        self.in_builtin_equal = True
        
        if self.analyser:
            self.analyser.broadcast('start_builtin', tagWithPos)    

    def start_builtin_at(self, tagName, ast):
        
        tagNameLower = tagName.lower()
        tagWithPos = HtmlTextWithPosition()
        tagWithPos.text = tagNameLower
        tagWithPos.token = ast
        self.push_context(tagNameLower, tagWithPos, ast)
         
        self.in_builtin_at = True
        
        if self.analyser:
            self.analyser.broadcast('start_builtin', tagWithPos)    

    def start_builtin(self, tagName, ast):
        
        tagNameLower = tagName.lower()
        tagWithPos = HtmlTextWithPosition()
        tagWithPos.text = tagNameLower
        tagWithPos.token = ast
        self.push_context(tagNameLower, tagWithPos, ast)   
        self.in_builtin = True
        if tagName == '<%':
            self.in_java_code = True
        
        if self.analyser:
            self.analyser.broadcast('start_builtin', tagWithPos)    

    def end_builtin(self, tagName):
        
        tagNameLower = tagName.lower()
        if self.analyser:
            self.analyser.broadcast('end_builtin', tagNameLower)

        if self.in_builtin_at:
            # We check struts presence
            # <%@ taglib prefix="s" uri="/struts-tags"%>
            # or
            # <%@ include file="header.jsp"%>
            if self.current_context and 'prefix' in self.current_context.valuesByAttributes and 'uri' in self.current_context.valuesByAttributes:
                uri = self.current_context.valuesByAttributes['uri']
                if uri == '/struts-tags':
                    self.strutsPrefix = self.current_context.valuesByAttributes['prefix']
                elif uri == '/WEB-INF/struts-tiles':
                    self.strutsTilesPrefix = self.current_context.valuesByAttributes['prefix']
                elif uri.startswith('/WEB-INF/struts-bean'):
                    self.strutsBeanPrefix = self.current_context.valuesByAttributes['prefix']
                elif uri.startswith(('/WEB-INF/struts-html', '/tags/struts-html', 'http://jakarta.apache.org/struts/tags-html')):
                    self.strutsHtmlPrefix = self.current_context.valuesByAttributes['prefix']
                elif uri.startswith('/WEB-INF/struts-form'):
                    self.strutsFormPrefix = self.current_context.valuesByAttributes['prefix']
                elif uri == 'http://www.springframework.org/tags/form':
                    self.springFormPrefix = self.current_context.valuesByAttributes['prefix']
                elif uri.endswith('/euamtags.tld'):
                    self.jadeFormPrefix = self.current_context.valuesByAttributes['prefix'].lower()
                elif uri in ['http://java.sun.com/jsp/jstl/core', 'http://java.sun.com/jstl/core']:
                    self.javaCorePrefix = self.current_context.valuesByAttributes['prefix']
                elif uri == 'http://jsptags.com/tags/navigation/pager':
                    self.pagerPrefix = self.current_context.valuesByAttributes['prefix']
            elif self.current_context and self.current_context.tagWithPos and self.current_context.tagWithPos.text == 'include' and 'file' in self.current_context.valuesByAttributes:
                filename = self.current_context.valuesByAttributes['file']
                fullpath = self.htmlContent.add_js_file(filename, self.current_context.astValuesByAttributes['file'], self.analyser)
                if filename.endswith(('.jsp', '.jsf', '.jsff', '.jspx')) and fullpath:
                    self.filePrefix = fullpath
                    if os.path.isfile(fullpath) and fullpath in self.analyser.taglibsByJspFullpath:
                        taglibs = self.analyser.taglibsByJspFullpath[fullpath]
                        for prefix, uri in taglibs.items():
                            if uri == '/struts-tags':
                                self.strutsPrefix = prefix
                            elif uri == '/WEB-INF/struts-tiles':
                                self.strutsTilesPrefix = prefix
                            elif uri.startswith('/WEB-INF/struts-bean'):
                                self.strutsBeanPrefix = prefix
                            elif uri.startswith(('/WEB-INF/struts-html', '/tags/struts-html', 'http://jakarta.apache.org/struts/tags-html')):
                                self.strutsHtmlPrefix = prefix
                            elif uri.startswith('/WEB-INF/struts-form'):
                                self.strutsFormPrefix = prefix
                            elif uri == 'http://www.springframework.org/tags/form':
                                self.springFormPrefix = prefix
                            elif uri.endswith('/euamtags.tld'):
                                self.jadeFormPrefix = prefix.lower()
                            elif uri == 'http://java.sun.com/jsp/jstl/core':
                                self.javaCorePrefix = prefix
                            elif uri == 'http://jsptags.com/tags/navigation/pager':
                                self.pagerPrefix = prefix
        
        self.pop_context()

        self.in_javascript_code = False
        self.in_css_code = False
        self.in_builtin = False
        self.in_builtin_equal = False    
        self.in_builtin_at = False
        self.in_java_code = False    

    def replace_variables(self, value):
        newV = None
        v = value
        if value.startswith('%{'):
            v = value[2:-1]
            if v in self.urlsById:
                v = self.urlsById[v]
            else:
                v = value
        if ' action=' in v:
            """
            In case of
            <a href="<s:url action="backtoNotification.action"/>?accountNumber=<s:property value="accountNumber" />&orderNumber=<s:property value="orderNumber"/>&productType=<s:property value="productType" />&serviceCenter=<s:property value="serviceCenter" />"></a>
            We must recompose the following url inside href:
            <s:url action="backtoNotification.action"/>?accountNumber=<s:property value="accountNumber" />&orderNumber=<s:property value="orderNumber"/>&productType=<s:property value="productType" />&serviceCenter=<s:property value="serviceCenter" />
            """
            exclamationPoint = False
            if self.strutsPrefix and self.strutsPrefix + ':url' in v:
                exclamationPoint = True
                
            doubleQuotes = False
            index1 = v.find(' action="')
            if index1 < 0:
                index1 = v.find(" action='")
            else:
                doubleQuotes = True
            if index1 >= 0:
                if doubleQuotes:
                    index2 = v.find('"', index1 + 9) if index1 >= 0 else -1
                else:
                    index2 = v.find("'", index1 + 9) if index1 >= 0 else -1
                if index2 > 0:
                    newV = v[index1 + 9:index2]
                if newV:
                    doubleQuotes = False
                    index1_1 = v.find(' method="')
                    if index1_1 < 0:
                        index1_1 = v.find(" method='")
                    else:
                        doubleQuotes = True
                    if index1_1 >= 0:
                        if doubleQuotes:
                            index2_1 = v.find('"', index1_1 + 9) if index1_1 >= 0 else -1
                        else:
                            index2_1 = v.find("'", index1_1 + 9) if index1_1 >= 0 else -1
                        if index2_1 > 0:
                            newV = newV + ( '/' if not exclamationPoint else '!' ) + v[index1_1 + 9:index2_1]
                    if exclamationPoint and not newV.lower().endswith('.action'):
                        newV += '.action'
                    if '?' in v:
                        index = v.find('?', index2)
                        newV += '?'
                        while index > 0:
                            indexEqual = v.find('=', index + 1)
                            if indexEqual > 0:
                                newV += v[index + 1:indexEqual + 1]
                                if v[indexEqual + 1] == '<':
                                    index = v.find('>', indexEqual + 2)
                                    if index > 0:
                                        index = v.find('&', indexEqual + 1)
                                        if index > 0:
                                            newV += '&'
                                    else:
                                        index = -1
                                else:
                                    index = v.find('&', indexEqual + 1)
                                    if index > 0:
                                        newV += v[indexEqual + 1:index + 1]
                                    else:
                                        newV += '&'
                            else:
                                break
                            if index == -1:
                                break
                            index = v.find('&', index)
            
        if newV:
            return newV
        return v
        
    def add_attribute_value(self, attribute, attributeAst, value, valueAst):
        
        attributeLower = attribute.lower()
        # case with class is for jade where <body class="row rowButton"> becomes body.row.rowButton
        if attributeLower == 'class':
            if attributeLower in self.current_context.valuesByAttributes:
                self.current_context.valuesByAttributes[attributeLower] += (' ' + str(value))
            else:
                self.current_context.valuesByAttributes[attributeLower] = str(value)
        else:
            self.current_context.valuesByAttributes[attributeLower] = value
        if attributeLower == 'language' and ( not value or not value.upper() in ['JAVASCRIPT', 'JSCRIPT'] ):       
            self.current_context.current_language_is_supported = False
            
        if self.current_context.current_tag == 'script':
            if attributeLower == 'language':
                if value and value.upper() in ['JAVASCRIPT', 'JSCRIPT']:
                    self.in_javascript_code = True
                else:
                    self.in_javascript_code = False
            elif attributeLower == 'type':
                if value and value.upper() == 'TEXT/JAVASCRIPT':
                    self.in_javascript_code = True
                else:
                    self.in_javascript_code = False
            
        attributeValue = AttributeValueWithPosition()
        attributeValue.attribute = HtmlTextWithPosition(attribute, attributeAst)
        attributeValue.value = HtmlTextWithPosition(value, valueAst)
        self.current_context.astValuesByAttributes[attributeLower] = attributeValue.value
        
        if self.current_context.current_tag == 'script' and attributeLower == 'src':
            if '?' in value:
                index = value.find('?')
                self.htmlContent.add_js_file(value[:index], valueAst, self.analyser)
                attributeValue.value.text = value[:index]
            elif value.startswith('<') and value.endswith('>'):
                if ':url' in value or ':out' in value:
                    # case of <script type="text/javascript" src="<c:url value="/assets/js/managers/vvb/att-mobile-vvb-design-solution.js"/>"></script>
                    index = value.find('"')
                    indexEnd = value.rfind('"')
                    if index < 0:
                        index = value.find("'")
                        indexEnd = value.rfind("'")
                    if indexEnd > index:
                        newValue = value[index+1:indexEnd]
                        if newValue.startswith('${') and '}' in newValue:
                            _var = newValue[2:newValue.find('}')]
                            _value = self.current_context.evaluate_spring_url(_var)
                            if _value:
                                newValue = _value + newValue[newValue.find('}') + 1:]
                                self.htmlContent.add_js_file(newValue, valueAst, self.analyser)
                                attributeValue.value.text = newValue
                            else:
                                index += ( newValue.find('}') + 1 )
                                self.htmlContent.add_js_file(value[index+1:indexEnd], valueAst, self.analyser)
                                attributeValue.value.text = value[index+1:indexEnd]
                        else:
                            self.htmlContent.add_js_file(value[index+1:indexEnd], valueAst, self.analyser)
                            attributeValue.value.text = value[index+1:indexEnd]
                else:
                    self.htmlContent.add_js_file(value, valueAst, self.analyser)
            else:
                self.htmlContent.add_js_file(value, valueAst, self.analyser)
#             if self.in_body:
#                 self.violations.add_javaScriptBlockingPageLoading_violation(self.htmlContent, attributeValue.attribute.create_bookmark(self.htmlFile))
        elif attributeLower == 'formaction':
            self.violations.add_markupWithFormAndFormAction_violation(self.htmlContent, attributeValue.attribute.create_bookmark(self.htmlFile))
        elif attributeLower == 'id':
            self.current_context.containsId = True
        elif attributeLower == 'type' and value == 'submit':
            if self.current_context.current_tag == 'input' and self.current_context.is_in_form_with_id():
                self.violations.add_IdAttributesAndSubmitForForms_violation(self.htmlContent, attributeValue.attribute.create_bookmark(self.htmlFile))
        elif self.current_context.current_tag == 'video' and attributeLower == 'poster':
            self.violations.add_videoPosterAttribute_violation(self.htmlContent, attributeValue.attribute.create_bookmark(self.htmlFile))
        elif attributeLower == 'style' and value:
            if value.startswith('behavior:url('):
                indexStart = value.find('(')
                indexEnd = value.rfind(')')
                if indexEnd > 0:
                    htcFragment = HtmlTextWithPosition(value[indexStart + 1: indexEnd], valueAst)
                    self.htmlContent.add_htc_reference(htcFragment)
            else:
                cssFragment = HtmlTextWithPosition(value, valueAst)
                self.htmlContent.add_css_fragment(cssFragment)
        elif attributeLower == 'autofocus' and self.current_context.current_tag == 'input':
            bodyContext = self.get_current_body_context()
            if bodyContext:
                bodyContext.inputAutofocusPresent = True
        elif attributeLower == 'dirname' and self.current_context.current_tag == 'input':
            self.violations.add_dirnameInUserGeneratedContent_violation(self.htmlContent, attributeValue.attribute.create_bookmark(self.htmlFile))
        elif attributeLower == 'href' and value and not value.startswith('#') and not value.lower().startswith('javascript:'):
            self.htmlContent.httpRequests.append(HttpCall('href', self.replace_variables(value), attributeValue.value, self.htmlContent, self.htmlFile))
        elif attributeLower in ['editurl', 'cellurl', 'surl'] and value and not value.startswith('#') and not value.lower().startswith('javascript:'):
            self.htmlContent.httpRequests.append(HttpCall('GET', self.replace_variables(value), attributeValue.value, self.htmlContent, self.htmlFile))
        elif attributeLower == 'editoptions' and value and not value.startswith('#') and not value.lower().startswith('javascript:'):
            # value has format {dataUrl : '%{dataURL}'}
            try:
                values = value.strip(' {}').split(',')
                for value in values:
                    if not ':' in value:
                        continue
                    index = value.find(':')
                    _value = value[:index].strip()
                    if _value == 'dataUrl': 
                        self.htmlContent.httpRequests.append(HttpCall('editoptions', self.replace_variables(value[index + 1:].strip()[1:-1]), attributeValue.value, self.htmlContent, self.htmlFile))
            except:
                pass
        elif attributeLower == 'autocomplete' and value == 'on':
            self.violations.add_autocomplete_on_violation(self.htmlContent, attributeValue.attribute.create_bookmark(self.htmlFile))
        else:
            if self.strutsTilesPrefix:
                if self.current_context.current_tag == self.strutsTilesPrefix + ':put':
                    if attributeLower == 'value':
                        jspRef = attributeValue.value
                        self.htmlContent.add_struts_tile(jspRef)
                        
            if self.strutsBeanPrefix:
                if self.current_context.current_tag == self.strutsBeanPrefix + ':write':
                    if attributeLower == 'name':
                        beanName = attributeValue.value
                        self.htmlContent.add_struts_scoped_bean(beanName)
                  
            if self.in_builtin_at:      
                if attributeLower == 'import':
                    self.htmlContent.add_class_import(attributeValue.value)
        
        if (value and attributeLower.startswith('on')) or ( value and value.lower().startswith('javascript:') ):
            if self.current_context.current_language_is_supported and not self.current_context.current_tag.startswith('asp:'):
                if value.lower().startswith('javascript:'):
                    jsFragment = HtmlTextWithPosition(value[11:], valueAst)
                else:
                    jsFragment = HtmlTextWithPosition(value, valueAst)
                self.htmlContent.add_javascript_value(jsFragment)

# Deactivated because done on JEE side
#         if value and ('${' in value or '#{' in value):
#             if '${' in value:
#                 prefix = '${'
#             else:
#                 prefix = '#{'
#             while prefix in value:
#                 indexStart = value.find(prefix)
#                 indexEnd = value.find('}', indexStart)
#                 if indexEnd < 0:
#                     break
#                 _value = value[indexStart:indexEnd + 1]
#                 if _value and '.' in _value:
#                     p = re.compile('[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*[\.[a-zA-Z_][a-zA-Z0-9_]*]*')
#                     vs = p.findall(_value)
#                     bOneFound = False
#                     for v in vs:
#                         if not v.startswith(('pageScope.', 'requestScope.', 'sessionScope.', 'applicationScope.', 'param.', 'paramValues.', 'header.', 'headerValues.', 'cookie.', 'initParam.', 'pageContext.')):
#                             bOneFound = True
#                             break
#                     if bOneFound:
#                         cast.analysers.log.debug(_value)
#                         self.htmlContent.beanMethodReferences.append(BeanMethodReference(_value, attributeValue.value))
#                 value = value[indexEnd:]
                

        if self.analyser:
            self.analyser.broadcast('start_html_attribute_value', attributeValue)    

    def end_struts_form(self, isFormInput = False, _type = 'POST'):
        
        strutsActions = []
        newVals = []
        if 'action' in self.current_context.astValuesByAttributes:
            astValue = self.current_context.astValuesByAttributes['action']
            if astValue and not astValue.text and '<%=' in astValue.token.text:
                begin = astValue.token.text.find('<%=')
                end = astValue.token.text.find('%>')
                if end >= 0:
                    values = evaluate(astValue.token.text[begin+3:end].strip(), self.htmlContent.java_code)
                    for value in values:
                        newVal = astValue.token.text.replace(astValue.token.text[begin-1:end+3], value)
                        if newVal and not newVal in newVals:
                            newVals.append(newVal)
            
            if newVals:
                for newVal in newVals:
                    strutsAction = StrutsAction(astValue, _type, newVal)
                    strutsActions.append(strutsAction)
            elif str(astValue.text) != '#':
                strutsAction = StrutsAction(astValue, _type)
                strutsActions.append(strutsAction)
            
            for strutsAction in strutsActions:
                if 'method' in self.current_context.astValuesByAttributes:
                    astValue = self.current_context.astValuesByAttributes['method']
                    strutsAction._type = astValue.text.upper()
    
        for strutsAction in strutsActions:
            if not self.current_context.hiddenStrutsActions:
                self.htmlContent.add_struts_action(strutsAction)
            else:
                oneCreated = False
                bFirstHidden = True
                for hiddenStrutsAction in self.current_context.hiddenStrutsActions:
                    if not hiddenStrutsAction.value:
                        continue
                    if hiddenStrutsAction.property:
                        if bFirstHidden or hiddenStrutsAction.inputType != 'hidden':
                            newStrutsAction = hiddenStrutsAction
                            newStrutsAction._type = strutsAction._type
                            if not '?' in strutsAction.action.text:
                                if strutsAction.action.text.endswith('/'):
                                    txt = strutsAction.action.text[:-1]
                                else:
                                    txt = strutsAction.action.text
                                if txt:
                                    params = '?'
                                else:
                                    params = '{}?'
                            else:
                                txt = strutsAction.action.text
                                if txt.startswith('?'):
                                    txt = '{}' + txt
                                params = '&'
                            self.htmlContent.add_struts_action(newStrutsAction)
                        else:
                            params += '&'
                        params += ( hiddenStrutsAction.property + '=' + hiddenStrutsAction.value.text )
                        if isFormInput:
                            newStrutsAction.action.text = txt + params
                        else:
                            newStrutsAction.value.text = txt + params
                        bFirstHidden = False
                        oneCreated = True
                    else:
                        exclamationPoint = False
                        if self.strutsPrefix and self.current_context.current_tag == self.strutsPrefix + ':form':
                            exclamationPoint = True
                        actionText = strutsAction.action.text + ( '!' if exclamationPoint else '/')
                        self.htmlContent.add_struts_action(hiddenStrutsAction)
                        actionText += hiddenStrutsAction.value.text
                        if isFormInput:
                            hiddenStrutsAction.action.text = actionText
                        else:
                            hiddenStrutsAction.value.text = actionText
                        oneCreated = True
                if not oneCreated:
                    self.htmlContent.add_struts_action(strutsAction)

    def end_struts_submit(self, tagName):
        
        if 'method' in self.current_context.astValuesByAttributes:
            astValue = self.current_context.astValuesByAttributes['method']
            formContext = self.current_context.get_current_context_with_tag(tagName[:-6] + 'form')
            if formContext:
                strutsAction = StrutsAction(astValue, 'POST')
                strutsAction.value = astValue
                formContext.hiddenStrutsActions.append(strutsAction)

    def end_struts_hidden(self, tagName):
        
        if not self.strutsHtmlPrefix or tagName != self.strutsHtmlPrefix + ':hidden':
            return
        
        strutsAction = None
        if 'property' in self.current_context.astValuesByAttributes:
            astValue = self.current_context.astValuesByAttributes['property']
            formContext = self.current_context.get_current_context_with_tag(tagName[:-6] + 'form')
            if formContext:
                strutsAction = StrutsAction(None, 'POST')
                strutsAction.inputType = 'hidden'
                formContext.hiddenStrutsActions.append(strutsAction)
                strutsAction.property = astValue.text
        if 'value' in self.current_context.astValuesByAttributes:
            astValue = self.current_context.astValuesByAttributes['value']
            if not strutsAction:
                formContext = self.current_context.get_current_context_with_tag(self.current_context.current_tag[:-6] + 'form')
                if formContext:
                    strutsAction = StrutsAction(astValue, 'POST')
                    strutsAction.inputType = 'hidden'
                    formContext.hiddenStrutsActions.append(strutsAction)
#                     strutsAction.value = astValue.text
                    strutsAction.value = astValue
            else:
                strutsAction.value = astValue
                strutsAction.action = astValue

    def end_struts_input(self, tagName):
        
        if 'name' in self.current_context.astValuesByAttributes and 'value' in self.current_context.astValuesByAttributes:
            if 'type' in self.current_context.astValuesByAttributes:
                inputType = self.current_context.astValuesByAttributes['type'].text
                if inputType == 'hidden':
                    astValue = self.current_context.astValuesByAttributes['value']
                    astName = self.current_context.astValuesByAttributes['name']
                    if astName.text:
                        formContext = self.current_context.get_current_context_with_tag('form')
                        if formContext:
                            strutsAction = StrutsAction(astValue, 'POST')
                            strutsAction.property = astName.text
                            strutsAction.value = astValue
                            strutsAction.inputType = inputType
                            formContext.hiddenStrutsActions.append(strutsAction)
                else:
                    astValue = self.current_context.astValuesByAttributes['value']
                    astName = self.current_context.astValuesByAttributes['name']
                    if astName.text:
                        formContext = self.current_context.get_current_context_with_tag('form')
                        if formContext and self.strutsHtmlPrefix and formContext.current_tag == self.strutsHtmlPrefix + ':form':
                            strutsAction = StrutsAction(astValue, 'POST')
                            strutsAction.property = astName.text
                            strutsAction.value = astValue
                            strutsAction.inputType = inputType
                            formContext.hiddenStrutsActions.append(strutsAction)

    def end_struts_link(self):

        astValue = None
        if 'action' in self.current_context.astValuesByAttributes:
            astValue = self.current_context.astValuesByAttributes['action']
        if not astValue and 'page' in self.current_context.astValuesByAttributes:
            astValue = self.current_context.astValuesByAttributes['page']
        if astValue and astValue.text != '#':
            strutsAction = StrutsAction(astValue, 'POST')
            self.htmlContent.add_struts_action(strutsAction)

    def end_struts_a(self):

        astValue = None
        if 'action' in self.current_context.astValuesByAttributes:
            astValue = self.current_context.astValuesByAttributes['action']
        if astValue and astValue.text != '#':
            strutsAction = StrutsAction(astValue, 'POST')
            self.htmlContent.add_struts_action(strutsAction)

    def end_struts_url(self):

        _id = None
        if 'var' in self.current_context.astValuesByAttributes:
            _id = self.current_context.astValuesByAttributes['var'].text
        if not _id and 'id' in self.current_context.astValuesByAttributes:
            _id = self.current_context.astValuesByAttributes['id'].text
        if not _id:
            return
        
        url = None
        if 'action' in self.current_context.astValuesByAttributes:
            url = self.current_context.astValuesByAttributes['action'].text
        if not url or url == '#':
            return

        if 'method' in self.current_context.astValuesByAttributes:
            if self.strutsPrefix and self.current_context.current_tag and self.current_context.current_tag == self.strutsPrefix + ':url':
                url += ('!' + self.current_context.astValuesByAttributes['method'].text)
                if not url.endswith('.action'):
                    url += '.action'
            else:
                url += ('/' + self.current_context.astValuesByAttributes['method'].text)
            
        bFirst = True
        for key, value in self.current_context.params.items():
            if bFirst:
                url += '?'
            else:
                url += '&'
            url += key + '=' + str(value)
            bFirst = False
            
        self.urlsById[_id] = url

    def end_struts_param(self, tagName):
        
        if 'name' in self.current_context.astValuesByAttributes:
            astValue = self.current_context.astValuesByAttributes['name']
            urlContext = self.current_context.get_current_context_with_tag(self.current_context.current_tag[:-5] + 'url')
            if urlContext:
                urlContext.params[astValue.text] = self.current_context.current_text.strip()
    
    def end_tag(self, tagName, token = None):
        
        if not self.current_context:
            return
        
        if tagName and self.current_context.current_tag and tagName.lower() != self.current_context.current_tag.lower():
            context = self.current_context.get_current_context_with_tag(tagName)
            if not context: # this closing tag has no corresponding opening
                if tagName == 'A':
                    pass
                if token:
                    cast.analysers.log.debug('Ending tag "' + str(tagName) + '" with no corresponding opening on line ' + str(token.begin_line) + '.')
                else:
                    cast.analysers.log.debug('Ending tag "' + str(tagName) + '" with no corresponding opening.')
                return
            
        tagName = self.current_context.current_tag
            
        if tagName:
            tagNameLower = tagName.lower()
        else:
            tagNameLower = tagName
        if self.analyser:
            self.analyser.broadcast('end_html_tag', tagNameLower)
            
        poppedContext = None
        
        if self.current_context:
            if self.current_context.currentServletMapping and self.current_context.currentServletMapping.action:
                self.htmlContent.add_servlet_mapping(self.current_context.currentServletMapping)

# prepa to struts modules STRUTS-18
            if tagNameLower == 'form':
                if 'action' in self.current_context.astValuesByAttributes:
                    
                    if self.current_context.hiddenStrutsActions:
                        self.end_struts_form(True, 'GET')
                    else:
                        astValue = self.current_context.astValuesByAttributes['action']
                        if astValue.text != '#':
                            strutsAction = StrutsAction(astValue, 'GET')
                            if 'method' in self.current_context.astValuesByAttributes:
                                astValue = self.current_context.astValuesByAttributes['method']
                                strutsAction._type = astValue.text.upper()
                            self.htmlContent.add_struts_action(strutsAction)
            elif tagNameLower == 'body':
                self.in_body = False
                if self.current_context.is_body() and self.current_context.inputAutofocusPresent:
                    if 'onscroll' in self.current_context.valuesByAttributes:
                        self.violations.add_onscrollWithAutofocusInput_violation(self.htmlContent, self.current_context.tagWithPos.create_bookmark(self.htmlFile))
                    if 'oninput' in self.current_context.valuesByAttributes:
                        self.violations.add_oninputInBodyContainingInputAutofocus_violation(self.htmlContent, self.current_context.tagWithPos.create_bookmark(self.htmlFile))
            elif tagNameLower == 'script':
                if self.in_body:
                    if 'src' in self.current_context.valuesByAttributes and ( not 'async' in self.current_context.valuesByAttributes and not 'defer' in self.current_context.valuesByAttributes ):
                        self.violations.add_javaScriptBlockingPageLoading_violation(self.htmlContent, self.current_context.astValuesByAttributes['src'].create_bookmark(self.htmlFile))
            elif tagNameLower == 'source':
                videoOrAudioContext = self.get_current_video_or_audio_context()
                if videoOrAudioContext:
                    if 'onerror' in videoOrAudioContext.valuesByAttributes or 'onerror' in self.current_context.valuesByAttributes:
                        self.violations.add_sourceTagInVideoAudioWithEventHandler_violation(self.htmlContent, self.current_context.tagWithPos.create_bookmark(self.htmlFile))
            elif tagNameLower == 'link':
                if 'rel' in self.current_context.valuesByAttributes and self.current_context.valuesByAttributes['rel'] == 'import' and 'href' in self.current_context.valuesByAttributes:
                    self.violations.add_importWithExternalURI_violation(self.htmlContent, self.current_context.tagWithPos.create_bookmark(self.htmlFile))
            elif self.javaCorePrefix and tagName == self.javaCorePrefix + ':url':
                if 'var' in self.current_context.valuesByAttributes and 'value' in self.current_context.valuesByAttributes:
                    self.current_context.parent.urlVars[self.current_context.valuesByAttributes['var']] = self.current_context.valuesByAttributes['value']
            elif self.pagerPrefix and tagName == self.pagerPrefix + ':pager':
                if 'url' in self.current_context.valuesByAttributes:
                    self.htmlContent.httpRequests.append(HttpCall('POST', self.current_context.valuesByAttributes['url'], self.current_context.astValuesByAttributes['url'], self.htmlContent, self.htmlFile))
            elif self.springFormPrefix and tagName == self.springFormPrefix + ':form':
                if 'method' in self.current_context.valuesByAttributes and 'action' in self.current_context.valuesByAttributes:
                    action = self.current_context.valuesByAttributes['action']
                    url = None
                    if action.startswith('${'):
                        action = action[2:-1]
                        url = self.current_context.evaluate_spring_url(action)
                    else:
                        if action == '#':
                            url = ''
                        else:
                            if action:
                                url = action
                            elif 'commandname' in self.current_context.valuesByAttributes:
                                url = self.current_context.valuesByAttributes['commandname']
                            else:
                                url = ''
                    self.htmlContent.httpRequests.append(HttpCall(self.current_context.valuesByAttributes['method'], url, self.current_context.astValuesByAttributes['action'], self.htmlContent, self.htmlFile))
            elif self.jadeFormPrefix and tagName == self.jadeFormPrefix + ':form':
                if 'action' in self.current_context.valuesByAttributes:
                    action = self.current_context.valuesByAttributes['action']
                    if str(action) != '#':
                        url = action
                        self.htmlContent.httpRequests.append(HttpCall('POST', url, self.current_context.astValuesByAttributes['action'], self.htmlContent, self.htmlFile))
            
            elif self.strutsPrefix or self.strutsHtmlPrefix or self.strutsFormPrefix:

                if tagName in self.strutsTags('form'):
                    self.end_struts_form()
                            
                elif tagName in self.strutsTags('submit'):
                    self.end_struts_submit(tagName)
                            
                elif tagName == 'input':
                    self.end_struts_input(tagName)
                            
                elif tagName in self.strutsTags('hidden'):
                    self.end_struts_hidden(tagName)
    
                elif tagName in self.strutsTags('link'):
                    self.end_struts_link()
    
                elif tagName in self.strutsTags('a'):
                    self.end_struts_a()
    
                elif tagName in self.strutsTags('url'):
                    self.end_struts_url()
    
                elif tagName in self.strutsTags('param'):
                    self.end_struts_param(tagName)
            
            if tagNameLower == 'jsp:plugin':
                code = None
                _type = None
                if 'code' in self.current_context.valuesByAttributes:
                    code = self.current_context.valuesByAttributes['code']
                if 'type' in self.current_context.valuesByAttributes:
                    _type = self.current_context.valuesByAttributes['type']
                if code and _type and _type == 'applet' and code.endswith('.class'):
                    self.htmlContent.appletReferences.append(AppletReference(code[:- len('.class')], self.current_context.astValuesByAttributes['code']))
            elif tagNameLower == 'jsp:forward':
                if 'page' in self.current_context.valuesByAttributes:
                    url = self.current_context.valuesByAttributes['page']
                    if not url.lower().endswith(('.jsp', '.html', '.jsf')):
                        self.htmlContent.httpRequests.append(HttpCall('POST', url, self.current_context.astValuesByAttributes['page'], self.htmlContent, self.htmlFile))
                        
            if 'autofocus' in self.current_context.valuesByAttributes:
                if 'onfocus' in self.current_context.valuesByAttributes:
                    self.violations.add_autofocusWithOnfocus_violation(self.htmlContent, self.current_context.tagWithPos.create_bookmark(self.htmlFile))
                if 'onblur' in self.current_context.valuesByAttributes:
                    self.violations.add_autofocusWithOnblur_violation(self.htmlContent, self.current_context.tagWithPos.create_bookmark(self.htmlFile))
            if tagNameLower == 'iframe' and 'srcdoc' in self.current_context.valuesByAttributes and not 'sandbox' in self.current_context.valuesByAttributes:
                self.violations.add_HostingHTMLCodeInIframeSrcdoc_violation(self.htmlContent, self.current_context.tagWithPos.create_bookmark(self.htmlFile))
            
            if 'ondragstart' in self.current_context.valuesByAttributes and 'draggable' in self.current_context.valuesByAttributes:
                draggable = self.current_context.valuesByAttributes['draggable']
                if draggable == 'true':
                    ondragstart = self.current_context.valuesByAttributes['ondragstart']
                    if '.setData(' in ondragstart:
                        self.violations.add_setDataInOndragstartWithDraggableTrue_violation(self.htmlContent, self.current_context.tagWithPos.create_bookmark(self.htmlFile))
                
            # check that the post must really be done
            # example <img src="images/icon_stop.gif" width="30" height="30"/></img>
            #         <video><source onerror="alert(1)"></video>
            if not tagNameLower or (self.current_context and tagNameLower == self.current_context.current_tag):
                poppedContext = self.pop_context()
            elif len(self.stack_context) >= 2 and self.stack_context[-2] and tagNameLower == self.stack_context[-2].current_tag:
                poppedContext = self.pop_context()
                poppedContext = self.pop_context()

        self.in_javascript_code = False
        self.in_css_code = False
        
        return poppedContext

    def start_text(self):
        if self.in_builtin_equal:
            pass
        elif self.in_builtin_at:
            pass
        elif self.in_builtin:
            pass
        else:
            self.in_text = True

    def end_text(self):
        
        if self.current_text:

            if self.in_javascript_code:
                if self.jsp:
                    txt = extract_javascript_code(self.current_text)
                else:
                    txt = self.current_text

                if txt.strip().startswith('<!--'):
                    txt = txt.replace('<!--', '    ')
                    
                jsFragment = HtmlTextWithPosition(txt, self.current_text_ast_start)
                self.htmlContent.add_javascript_fragment(jsFragment)

            elif self.in_css_code:
                cssFragment = HtmlTextWithPosition(self.current_text, self.current_text_ast_start, self.current_text_ast_end)
                self.htmlContent.add_css_fragment(cssFragment)
            
            if self.analyser:
                if self.in_javascript_code:
                    self.analyser.broadcast('start_javascript_text', jsFragment)
                elif self.in_css_code:
                    self.analyser.broadcast('start_css_text', cssFragment)
                else:
                    txtFragment = HtmlTextWithPosition(self.current_text, self.current_text_ast_start)
                    self.analyser.broadcast('start_html_text', txtFragment)

        self.current_text = None
        self.current_text_ast_start = None
        self.current_text_ast_end = None
        self.in_text = False

    def add_text(self, txt, ast):
        
        if self.current_context:
            self.current_context.current_text += txt
#             if txt.strip().startswith('@'):
            if not self.in_javascript_code:
                self.current_context.razor_text += txt
            if self.in_java_code:
                self.htmlContent.java_code += txt
        
        if not self.in_text and not self.in_builtin and not self.in_builtin_equal:
            return
        
#         <%= js_include("/javascripts/lib/jquery.js") %>
        if self.in_builtin_equal:
            text = txt.strip()
            if text.startswith('js_include('):
                index = text.rfind(')')
                filename = text[11:index][1:-1]
                self.htmlContent.add_js_file(filename, ast, self.analyser)
                return
        
        if not self.current_text:
            self.current_text_ast_start = ast
            if not txt.strip():
                return
            self.current_text = txt
        else:
            self.current_text_ast_end = ast
            self.current_text += txt
                            
    def manage_attribute(self, attribute, tokenAttribute, value, tokenValue):
         
        return True

    def strutsTags(self, tagName):
        l = []
        if self.strutsHtmlPrefix:
            l.append(self.strutsHtmlPrefix + ':' + tagName)
        if self.strutsFormPrefix:
            l.append(self.strutsFormPrefix + ':' + tagName)
        if self.strutsPrefix:
            l.append(self.strutsPrefix + ':' + tagName)
        return l
