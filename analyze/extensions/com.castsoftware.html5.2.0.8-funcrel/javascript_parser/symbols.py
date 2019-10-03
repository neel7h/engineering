'''
Created on 26 nov. 2014

@author: iboillon
'''
import cast_upgrade_1_5_25 # @UnusedImport
import os
import cast.analysers.ua
from cast.analysers import Object, File, Bookmark, create_link
from cast.application import open_source_file # @UnresolvedImport
from collections import OrderedDict
from pygments.token import Keyword, Number, is_token_subtype, Comment, String
import copy
import traceback
import itertools

self_resolve = False

def html5_open_source_file(filepath, utf8Before = True):
    
    text = None
    f = None
    if utf8Before:
        try:
            f = open(filepath, 'r', encoding="utf8")
            text = f.read()
            char = u"\uFFFD"
            if text.startswith(char):
                text = text.replace(char, ' ', 1)
            
        except:
            if f:
                f.close()
            try:
                f = open(filepath, 'r')
                text = f.read()
            except:
                if f:
                    f.close()
                f = open_source_file(filepath)
                text = f.read()
                f.close()
    else:
        try:
            f = open(filepath, 'r')
            text = f.read()
        except:
            if f:
                f.close()
            try:
                f = open(filepath, 'r', encoding="utf8")
                text = f.read()
            except:
                if f:
                    f.close()
                f = open_source_file(filepath)
                text = f.read()
                f.close()
    return text

def is_object_in_list(val, returnValues):
    for key, value in val.items():
        if not key in returnValues:
            return False
        if not value.value == returnValues[key].value:
            return False
    return True
    
def is_return(obj):
    try:
        return obj.is_return_statement()
    except:
        return False
    
def get_return_statements(obj, recursive = True):
    
    results = []
    if not obj:
        return results
    
    for child in obj.get_children():
        if not child:
            continue
        try:
            if is_return(child):
                results.append(child)
                if recursive:
                    res = get_return_statements(child, recursive)
                    results.extend(res)
            elif recursive:
                res = get_return_statements(child, recursive)
                results.extend(res)
        except:
            pass
    return results

def create_link_internal(linkType, caller, callee, bm):

    success = True
    if isinstance(caller, File):
        create_link(linkType, caller, callee, bm)
        return True
    
    clr = caller
    if isinstance(caller, JsContent):
        clr = caller.create_javascript_initialisation()

    try:
        create_link(linkType, clr.get_kb_object(), callee, bm)
    except:
            try:
                create_link(linkType, clr.get_kb_object(), callee.get_kb_object(), bm)
            except:
                try:
                    create_link(linkType, clr, callee, bm)
                except:
                    try:
                        create_link(linkType, clr, callee.get_kb_object(), bm)
                    except:
                        try:
                            if callee.get_kb_object() != None:
                                cast.analysers.log.debug(str(traceback.format_exc()))
                        except:
                            cast.analysers.log.debug('create_link_internal ' + str(caller) + str(callee))
                            cast.analysers.log.debug(str(traceback.format_exc()))
                        success = False
    return success

class JSPFile:
    
    def __init__(self, file):
        self.file = file
        self.sourceCode = None
        
class ASPFile:
    
    def __init__(self, file):
        self.file = file
        self.sourceCode = None

class HtmlTextWithPosition:

    def __init__(self, text = None, token = None, token_end = None):
        
        self.text = text
        self.token = token
        self.token_end = token_end
        
    def get_text(self):
        return self.text
        
    def get_token(self):
        if type(self.token) is list:
            try:
                return self.token[0]
            except:
                return None
        else:
            return self.token
        
    def get_tokens(self):
        if type(self.token) is list:
            return self.token
        else:
            return [ self.token, self.token_end ]
        
    def get_token_end(self):
        return self.token_end

    def create_bookmark(self, file):
        if type(self.token) is list:
            return Bookmark(file, self.token[0].get_begin_line(), self.token[0].get_begin_column(), self.token[-1].get_end_line(), self.token[-1].get_end_column())
        else:
            return Bookmark(file, self.token.get_begin_line(), self.token.get_begin_column(), self.token.get_end_line(), self.token.get_end_column())

    def get_begin_line(self):
        if type(self.token) is list:
            return self.token[0].get_begin_line()
        else:
            return self.token.get_begin_line()

    def get_end_line(self):
        if type(self.token) is list:
            return self.token[-1].get_end_line()
        else:
            return self.token.get_end_line()

    def get_begin_column(self):
        if type(self.token) is list:
            return self.token[0].get_begin_column()
        else:
            return self.token.get_begin_column()

    def get_end_column(self):
        if type(self.token) is list:
            return self.token[-1].get_end_column()
        else:
            return self.token.get_end_column()
    
    def get_resolutions(self):
        try:
            return self.resolutions
        except:
            return []
        
    def add_resolution(self, callee, linkType, addEvenIfResolutionExists = False):
        
        if not callee:
            return
            
        if not hasattr(self, 'resolutions'):
            self.resolutions = []

        if not self.get_resolutions() or addEvenIfResolutionExists:
            self.get_resolutions().append(Resolution(callee, linkType))
            try:
                if callee.is_function():
                    callee.add_call(self)
            except:
                pass
            return
        try:
            if callee.is_function():
                toRemove = []
                for res in self.get_resolutions():
                    try:
                        if res.callee.is_identifier():
                            toRemove.append(res)
                    except:
                        pass
                for res in toRemove:
                    self.get_resolutions().remove(res)
                
                callee.add_call(self)
        except:
            pass
        self.get_resolutions().append(Resolution(callee, linkType))
    
    def get_name(self):
        name = self.text.strip()
        if name.startswith('{'):
            name = name[1:-1]
        if not '.' in name:
            return name
        index = name.rfind('.')
        return name[index+1:]
    
    def get_fullname(self):
        return self.get_name()
    
    def get_prefix(self):
        return self.get_prefix_internal()
    
    def get_prefix_internal(self):
        name = self.text.strip()
        if not '.' in name:
            return ''
        if name.startswith('{'):
            name = name[1:-1]
        index = name.rfind('.')
        return name[:index]
    
    def is_bracketed_identifier(self):
        return False
    
    def is_func_call(self):
        return False
    
    def get_parent(self):
        return None
    
    def starts_with_this(self):
        return False
    
    def evaluate(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None):
        evs = self.evaluate_with_trace(None, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter)
        return [ev.value for ev in evs]

    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None):
        
        if evalCounter:
            if evalCounter.isOver():
                return []
        resols = self.get_resolutions()
        if not resols:
            return [ Value(self.text.strip(), self) ]

        ret = []
        for resol in resols:
            try:
                prefix = self.get_prefix()
                if prefix and resol.callee.parent and resol.callee.parent.is_function() and resol.callee.parent.parent and resol.callee.parent.parent.is_function_call_part():
                    # callee is a function parameter 
                    fcallIdent = resol.callee.parent.parent.get_identifier() 
                    if fcallIdent.get_name() == 'map':
                        if fcallIdent.get_resolutions():
                            # menuItems.map((item, index) => (
                            for resol in fcallIdent.get_resolutions():
                                callee = resol.callee
                                # menuItems = [ {}, {} ];
                                if callee.parent.is_assignment():
                                    value = callee.parent.get_right_operand()
                                    if value.is_list():
                                        for elt in value.values:
                                            if elt.is_object_value():
                                                name = self.get_name()
                                                value = elt.get_item(name)
                                                if value:
                                                    evs = value.evaluate_with_trace(memberNames, None, None, None, None, constants)  
                                                    if evs:
                                                        for ev in evs:
                                                            if not ev.is_in_list(ret):
                                                                ret.append(ev)
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))
            evs = resol.callee.evaluate_with_trace(memberNames, None, None, None, None, constants)
            if evs:
                for ev in evs:
                    if not ev.is_in_list(ret):
                        ret.append(ev)
        return ret

    def __repr__(self):
        return self.text

class Position:
    def __init__(self, begin_line, begin_col, end_line, end_col):
        self.begin_line = begin_line
        self.begin_col = begin_col
        self.end_line = end_line
        self.end_col = end_col
    
class StrutsAction:
    def __init__(self, action, _type, name = None):
        self.name = name
        self.action = action
        self._type = _type
        self.property = None
        self.value = None
        self.inputType = None
# for example converts
# <c:out value="${epayCustomer.absoluteBaseWithContextPath}"/>/dlife/autoPayUnenroll.perform
# to /dlife/autoPayUnenroll.perform
    def get_action_value(self):

        if self.name:
            return self.name

        astValue = self.action.text
        if not astValue:
            return ''
        
        # remove ${...}
        dollarFirst = False
        index = astValue.find('${')
        try:
            while index >= 0:
                if index == 0:
                    dollarFirst = True
                astValue = astValue[0:index] + astValue[astValue.find('}', index) + 1:]
                index = astValue.find('${')
        except:
            pass

        # search for <c:out...> and replace with what is in value (<c:out value="something"/>)
        index = astValue.find('<c:')
        index_ = astValue.find('</c:')
        if index_ >= 0 and index_ < index:
            index = index_
        if index == -1:
            index = index_
        while index >= 0:
            index2 = astValue.find('>', index)
            if index2 >= 0:
                s = astValue[index + 1: index2]
                if 'value' in s:
                    j1 = s.find('value')
                    j1 = s.find('"', j1)
                    j2 = s.find('"', j1 + 1)
                    if j2 >= 0:
                        s = s[j1 + 1:j2].strip()
                        astValue = astValue[:index] + s + astValue[index2 + 1:]
                    else:
                        astValue = astValue[:index] + astValue[index2 + 1:]
                else:
                    astValue = astValue[:index] + astValue[index2 + 1:]
                index = astValue.find('<c:')
                index_ = astValue.find('</c:')
                if index_ >= 0 and  index_ < index:
                    index = index_
                if index == -1:
                    index = index_
            else:
                break
        if dollarFirst:
            astValue = astValue.lstrip('/ \t\n\r')
        else:
            astValue = astValue.lstrip(' \t\n\r')
        if astValue.startswith('?'):
            astValue = '{}' + astValue
            
        return astValue
            
class HtmlContent:
    
    def __init__(self, file, htmlSourceCode):
        
        self.file = file
        self.htmlSourceCode = htmlSourceCode
        self.jsFiles = {}
        self.javascript_fragments = []
        self.javascript_values = []
        self.css_fragments = []
        self.htc_references = []
        self.strutsActions = []    # HtmlTextWithPosition corresponding to action in 
                                    # <s:form method="post" action="showAccountsManager" id="form" namespace="/admin" theme="simple">
        self.strutsTiles = []       # list of HtmlTextWithPosition corresponding to jsp reference in  
                                    # <tiles:put name="body" value="/jsp/intranet/activite/activiteBody.jsp" />
        self.servletMappings = []    # HtmlTextWithPosition corresponding to action in <form NAME="changePWD" action=siu  METHOD="POST" >
        self.strutsScopedBeans = []       # list of HtmlTextWithPosition corresponding to scoped bean reference in  
                                    # <td align="left">N° client : <bean:write name="contactClientForm" property="intervention.ndPrincipal"/></td>
        self.beanMethodReferences = []
        self.classImports = []       # list of HtmlTextWithPosition corresponding to class imports in  
                                    # <%@ page import="com.francetelecom.pidi.commun.util.ApplicationManager" %>
        self.httpRequests = []      # list of http present in href
        self.appletReferences = []   # list of applet references found in jsp:plugin tags
        self.java_code = ''

    def is_html_content(self):
        return True
        
    def get_path(self):
        return self.file.get_path()

    def get_kb_object(self, recursiveInParents = False):
        return self.htmlSourceCode
    
    def get_file(self):
        return self.file
    
    def search_in_roots(self, _filename, analyzer = None):
        
        if not analyzer:
            return _filename
        
        found = False
        if _filename.startswith(('/', '\\')):
            newFilename = _filename[1:]
        else:
            newFilename = _filename
        for webappFolder in analyzer.webappsFolders:
            _fn = os.path.normpath(os.path.join(webappFolder, newFilename))
            if os.path.exists(_fn):
                newFilename = _fn
                found = True
                break
        if not found:
            for publicFolder in analyzer.publicFolders:
                _fn = os.path.normpath(os.path.join(publicFolder, newFilename))
                if os.path.exists(_fn):
                    newFilename = _fn
                    found = True
                    break
        if not found:
            dirname = os.path.dirname(self.file.get_path())
            while not os.path.exists(os.path.join(dirname, 'web.config')) or not os.path.exists(os.path.join(dirname, newFilename)):
                oldDirname = dirname
                dirname = os.path.dirname(dirname)
                if oldDirname == dirname:
                    break
            if os.path.exists(os.path.join(dirname, 'web.config')):
                if os.path.exists(os.path.join(dirname, newFilename)):
                    newFilename = os.path.normpath(os.path.join(dirname, newFilename))
                    found = True
        if not found:
            dirname = os.path.dirname(self.file.get_path())
            while not os.path.exists(os.path.join(dirname, 'assets')):
                oldDirname = dirname
                dirname = os.path.dirname(dirname)
                if oldDirname == dirname:
                    break
            if os.path.exists(os.path.join(dirname, 'assets')):
                if os.path.exists(os.path.join(os.path.join(dirname, 'assets'), newFilename)):
                    newFilename = os.path.normpath(os.path.join(os.path.join(dirname, 'assets'), newFilename))
                    found = True
        if not found:
            dirname = os.path.dirname(self.file.get_path())
            while not os.path.exists(os.path.join(dirname, 'lib')):
                oldDirname = dirname
                dirname = os.path.dirname(dirname)
                if oldDirname == dirname:
                    break
            if os.path.exists(os.path.join(dirname, 'lib')):
                if os.path.exists(os.path.join(os.path.join(dirname, 'lib'), newFilename)):
                    newFilename = os.path.normpath(os.path.join(os.path.join(dirname, 'lib'), newFilename))
                    found = True
                
        return newFilename
    
    def search_in_web_config_root(self, _filename):
        
        if _filename.startswith('~'):
            newFilename = _filename[2:]
        else:
            newFilename = _filename
            
        dirname = os.path.dirname(self.file.get_path())
        while not os.path.exists(os.path.join(dirname, 'web.config')) or not os.path.exists(os.path.join(dirname, newFilename)):
            oldDirname = dirname
            dirname = os.path.dirname(dirname)
            if oldDirname == dirname:
                break
           
        if os.path.exists(os.path.join(dirname, newFilename)):
            newFilename = os.path.normpath(os.path.join(dirname, newFilename))
        
        return newFilename
    
    def search_in_app_start_root(self, _filename):
        
        if _filename.startswith('~'):
            newFilename = _filename[2:]
        else:
            newFilename = _filename
            
        dirname = os.path.dirname(self.file.get_path())
        while not os.path.exists(os.path.join(dirname, 'App_Data')) and not os.path.exists(os.path.join(dirname, 'App_Start')):
            oldDirname = dirname
            dirname = os.path.dirname(dirname)
            if oldDirname == dirname:
                break
           
        if os.path.exists(os.path.join(dirname, newFilename)):
            newFilename = os.path.normpath(os.path.join(dirname, newFilename))
        
        return newFilename
    
    def add_js_file(self, filename, ast, analyzer = None):
        if filename.startswith('/'):
            jsFile = HtmlTextWithPosition(filename, ast)
            _filename = os.path.normpath(filename)
            if '${JAVA_SCRIPT}' in _filename:
                _filename = _filename.replace('${JAVA_SCRIPT}', 'js')
            if '${' in _filename:
                index = _filename.rfind('}')
                if index >= 0:
                    _filename = _filename[index + 1:]
            if analyzer and not '${' in _filename:
                _filename = self.search_in_roots(_filename, analyzer)
            self.jsFiles[_filename] = jsFile
            return _filename
        else:
            jsFile = HtmlTextWithPosition(filename, ast)
            _filename = filename
            if '${JAVA_SCRIPT}' in _filename:
                _filename = _filename.replace('${JAVA_SCRIPT}', 'js')
            if '${' in filename:
                index = _filename.rfind('}')
                if index >= 0:
                    _filename = _filename[index + 1:]
                if analyzer and not '${' in _filename:
                    _filename = self.search_in_roots(_filename, analyzer)
                self.jsFiles[_filename] = jsFile
            else:
                if _filename.startswith('http'):
                    self.jsFiles[_filename] = jsFile
                else:
                    if _filename.startswith('~'):
                        _filename = self.search_in_web_config_root(_filename)
                        self.jsFiles[_filename] = jsFile
                    else:
                        _filename = os.path.normpath(os.path.join(os.path.dirname(self.file.get_path()), _filename))
                        self.jsFiles[_filename] = jsFile
            return _filename
        
    def add_javascript_fragment(self, fragment):
        self.javascript_fragments.append(fragment)
        
    def add_javascript_value(self, fragment):
        self.javascript_values.append(fragment)
        
    def add_struts_action(self, strutsAction):
        self.strutsActions.append(strutsAction)
        
    def add_struts_scoped_bean(self, strutsScopedBean):
        self.strutsScopedBeans.append(strutsScopedBean)
        
    def add_class_import(self, classImport):
        self.classImports.append(classImport)
        
    def add_servlet_mapping(self, servletMapping):
        self.servletMappings.append(servletMapping)
        
    def add_struts_tile(self, jspRef):
        self.strutsTiles.append(jspRef)
        
    def add_css_fragment(self, fragment):
        self.css_fragments.append(fragment)
        
    def add_htc_reference(self, fragment):
        filename = fragment.text
        if filename.startswith('/'):
            fragment.text = os.path.normpath(filename)
        else:
            fragment.text = os.path.normpath(os.path.join(os.path.dirname(self.file.get_path()), filename))
        self.htc_references.append(fragment)
        
    def get_js_files(self):
        
        return self.jsFiles
        
    def get_javascript_fragments(self):
        return self.javascript_fragments
        
    def get_javascript_values(self):
        return self.javascript_values
        
    def get_struts_actions(self):
        return self.strutsActions
        
    def get_servlet_mappings(self):
        return self.servletMappings

    def get_struts_scoped_beans(self):
        return self.strutsScopedBeans

    def get_class_imports(self):
        return self.classImports
        
    def get_css_fragments(self):
        return self.css_fragments

    def get_htc_references(self):
        return self.htc_references
    
    def has_js_file(self, filename):
        normFilename = os.path.normpath(filename)
        if normFilename in self.jsFiles:
            return self.jsFiles[normFilename]
        else:
            return None
    
    def resolve_absolute_js_files(self, jsFilesByBasename):
        index = -1
        filesToPop = []
        filesToAdd = {}
        for jsFilename, jsFile in self.jsFiles.items():
            currentJSFile = jsFile
            index += 1
            if not jsFilename.startswith(os.sep):
                continue
            basename = os.path.basename(jsFilename)
            if basename in jsFilesByBasename:
                for foundJS in jsFilesByBasename[basename]:
                    if jsFilename in foundJS.get_path():
                        if not jsFilename in filesToPop:
                            filesToPop.append(jsFilename)
                        filesToAdd[foundJS.get_path()] = currentJSFile
                        
        for filename in filesToPop:
            self.jsFiles.pop(filename)
        for filename, jsFile in filesToAdd.items():
            self.jsFiles[filename] = jsFile

class CssContent:
    
    def __init__(self, file, cssSourceCode):
        
        self.file = file
        self.cssSourceCode = cssSourceCode
        
    def get_path(self):
        return self.file.get_path()

    def get_kb_object(self, recursiveInParents = False):
        return self.cssSourceCode
    
    def get_file(self):
        return self.file
        
class KbObject:
        
    def __init__(self, fullname, file):
        self.fullname = fullname
        self.display_fullname = fullname
        self.file = file
        self.kbObject = None
    
    def get_kb_object(self, recursiveInParents = False):
        return self.kbObject
        
    def get_fullname(self):
        return self.fullname
        
    def get_display_fullname(self):
        return self.display_fullname
    
    def get_fullname_internal(self):
        return self.fullname
    
    def get_file(self):
        return self.file

    def get_file_name(self):
        if self.file:
            return self.file.get_path()
        else:
            return None
        
    def __repr__(self):
        return self.fullname

class GlobalVariable:
        
    def __init__(self, fullname, identifier, isVar, file):
        self.identifier = identifier
        self.file = file
        self.isVar = isVar
        
    def get_fullname(self):
        return self.identifier.get_fullname()
    
    def get_file(self):
        return self.file
    
    def get_identifier(self):
        return self.identifier

    def get_file_name(self):
        return self.file.get_path()
            
class GlobalFunction:
        
    def __init__(self, fullname, function, file):
        self.kbSymbol = function.get_kb_symbol()
        self.kbObject = None
        self.file = file
        self.fullname = fullname
        
    def get_fullname(self):
        return self.fullname

    def get_file(self):
        return self.file
    
    def get_kb_symbol(self):
        return self.kbSymbol
    
    def get_function(self):
        return self.kbSymbol
    
    def get_kb_object(self, recursiveInParents = False):
#         return self.kbSymbol.get_kb_object()
        if not self.kbObject:
            if self.kbSymbol:
                if self.kbSymbol.kbObject:
                    return self.kbSymbol.kbObject
                else:
                    return self.kbSymbol
            return self.kbSymbol
        return self.kbObject
        
    def get_file_name(self):
        return self.file.get_path()
            
class GlobalClass:
        
    def __init__(self, fullname, cl, file):
        self.kbSymbol = cl.get_kb_symbol()
        self.kbObject = None
        self.file = file
        self.fullname = fullname
        self.inheritanceIdentifier = None
        self.methodsByName = {} # values are list of 2 items [ kbSymbol, kbObject ]

    def get_super_class(self):
        if not self.inheritanceIdentifier:
            return None
        if not self.inheritanceIdentifier.resolutions:
            return None
        return self.inheritanceIdentifier.resolutions[0].callee
        
    def get_fullname(self):
        return self.fullname
    
    def add_method(self, method):
        self.methodsByName[method.get_name()] = [ method.get_kb_symbol(), None ]
        
    def get_method(self, name):
        if name in self.methodsByName:
            return self.methodsByName[name][0]
        return None
        
    def get_inheritance_identifier(self):
        return self.inheritanceIdentifier
    
    def get_file(self):
        return self.file
    
    def get_class(self):
        return self.kbSymbol
    
    def get_kb_symbol(self):
        return self.kbSymbol
    
    def get_kb_object(self, recursiveInParents = False):
#         return self.kbSymbol.get_kb_object()
        if not self.kbObject:
            return self.kbSymbol
        return self.kbObject
        
    def get_file_name(self):
        return self.file.get_path()
        
class Unknown:
    """
    Unknown statement.
    """
    def __init__(self):
        self.text = None

    def __repr__(self):
        return 'UnknownStatement'

class KbSymbol:

    def __init__(self, name, fullname, displayName, parent):

        self.anonymousFunctionsNumber = 0
        self.set_kb_parent(parent)
        self.set_kb_name(name, fullname, displayName)
        self.display_fullname = displayName
    
    def get_kb_symbol(self):
        return self
    
    def add_method(self, method):
        if not hasattr(self, 'methods'):
            self.methods = OrderedDict()
        self.methods[method.get_name()] = method.get_kb_symbol()

    def get_kb_parent(self):
        return self.kbParent

    def set_kb_parent(self, parent):
        
        if isinstance(parent, Function) or isinstance(parent, JsContent): # case of Function, JsContent
            self.kbParent = parent         # KbSymbol
        elif isinstance(parent, Class): # case of Class
            self.kbParent = parent         # KbSymbol
        elif isinstance(parent, HtmlContent):
            self.kbParent = parent.htmlSourceCode   # CustomObject
        else:
            self.kbParent = parent
        
    def initialize(self, name, fullname, displayName, parent):

        self.anonymousFunctionsNumber = 0
        self.set_kb_parent(parent)
        self.set_kb_name(name, fullname, displayName)
        
    def get_kb_fullname(self):
        return self.kb_fullname

    def get_display_fullname(self):
        return self.display_fullname
    
    def get_kb_name(self):
        try:
            return self.kb_name
        except:
            return ''
    
    def set_kb_name(self, name, fullname, displayName):
        
        global nr_first_range_unnamed_functions
        if name:
            self.kb_name = name
            if self.kbParent:
                if isinstance(self.kbParent, KbSymbol): # case of Function, JsContent
                    self.kb_fullname = self.kbParent.kb_fullname + '.' + name
                    self.display_fullname = self.kbParent.display_fullname + '.' + name
                else:
                    self.kb_fullname = fullname
                    if not fullname and isinstance(self.kbParent, File):
                        self.kb_fullname = self.kbParent.get_path() + '/' + name
                        self.display_fullname = self.kbParent.get_path() + '.' + name
            else:
                self.kb_fullname = fullname
                self.display_fullname = displayName
        else:
            if self.kbParent:
                if isinstance(self.kbParent, KbSymbol):
                    self.kbParent.anonymousFunctionsNumber += 1
                    nr = self.kbParent.anonymousFunctionsNumber
                    if nr > 1:
                        self.kb_name = 'NONAME_' + str(nr)
                    else:
                        self.kb_name = 'NONAME'
                    self.kb_fullname = self.kbParent.kb_fullname + '.' + self.kb_name
                    self.display_fullname = self.kbParent.display_fullname + '.' + self.kb_name
                else:
                    nr_first_range_unnamed_functions += 1
                    nr = nr_first_range_unnamed_functions
                    if nr > 1:
                        self.kb_name = 'NONAME_' + str(nr)
                    else:
                        self.kb_name = 'NONAME'
                    self.kb_fullname = self.kbParent.get_path() + '/' + self.kb_name
                    self.display_fullname = self.kbParent.get_path() + '.' + self.kb_name
            else:
                nr_first_range_unnamed_functions += 1
                nr = nr_first_range_unnamed_functions
                if nr > 1:
                    self.kb_name = 'NONAME_' + str(nr)
                else:
                    self.kb_name = 'NONAME'
                self.kb_fullname = self.kb_name
                self.display_fullname = 'NONAME'
        
        nr = 1
        fullname = self.kb_fullname
        if not fullname.endswith('CAST_HTML5_JavaScript_SourceCode_Fragment'):  # javascript fragments in html files are merged during objects creation  
            while fullname in fullnames:
                nr += 1
                try:
                    fullname = self.kb_fullname + '_' + str(nr)
                except:
                    pass
        self.kb_fullname = fullname
        fullnames.append(fullname)

    def __repr__(self):
        if self.kb_fullname:
            return 'KbSymbol ' + self.kb_fullname
        else:
            return 'KbSymbol ' + self.kb_name

class Resolution:
    
    def __init__(self, callee, linkType, sameType = True):
        self.callee = callee
        self.linkType = linkType
        self.sameType = sameType
        
    def get_callee(self):
        return self.callee
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Resolution ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + str(hex(id(self.callee))))
        print(' '.rjust(pad) + '}')

def get_token_max_col(token):
    maxCol = 0
    try:
        maxCol = token.end_column
    except:
        try:
            maxCol = token.get_end_column()
        except:
            pass
    if maxCol == None:
        return 0
    return maxCol

class AstToken:

    def get_max_col_over(self, minCol):
        _minCol = minCol
        col = get_token_max_col(self)
        if col > _minCol:
            _minCol = col
            
        for child in self.get_children():
            try:
                col = child.get_max_col_over(_minCol)
                if col > _minCol:
                    _minCol = col
            except:
                pass
        return _minCol
        
    def __init__(self, token, parent, name = None):
        
        self.tokens = []
        tokenName = name
        if token:
            if type(token) is list:
                self.tokens = token
            else:
                self.tokens.append(token)
                try:
                    if is_token_subtype(token.type, Keyword):
                        self.isKeyword = True
                except:
                    pass
                try:
                    if is_token_subtype(token.type, Number): # Literal
                        tokenName = token.text
                except:
                    pass
        self.parent = parent
        if self.is_keyword():
            self.set_name(token.text)
        else:
            self.set_name(tokenName)
     
    def is_ast_token(self):
        return True
    
    def get_kb_object(self, recursiveInParents = False):
        try:
            result = self.kbObject
        except:
            result = None
            
        if recursiveInParents and not result and self.parent:
            try:
                result = self.parent.get_kb_object(recursiveInParents)
            except:
                pass
            
        return result
        
    def get_calls(self):
        return []
     
    def get_current_assignment(self):
        if self.parent:
            return self.parent.get_current_assignment()
        return None
        
    def get_next_html_fragment_number(self):
        if self.parent:
            return self.parent.get_next_html_fragment_number()
        return -1
        
    def increment_next_html_fragment_number(self):
        if self.parent:
            return self.parent.increment_next_html_fragment_number()
        return -1

    # This method is present here in order to be accessible from other sub-extensions
    def get_uri_evaluation(self, uriToEvaluate, characterForUnknown = '{}', astCalls = None, constants = None):
        return get_uri_evaluation(uriToEvaluate, characterForUnknown, astCalls, constants)

    def decrement_code_lines(self, nb):
        if self.parent:
            self.parent.decrement_code_lines(nb)
    
    def convert_crc(self):
        self.crc = self.get_code_only_crc()

    def is_kb_object(self):
        if hasattr(self, 'isKbObject'):
            return self.isKbObject
        return False

    def set_is_kb_object(self, b = True):
        if b:
            self.isKbObject = True
        else:
            if hasattr(self, 'isKeyword'):
                self.isKbObject = False
    
    def is_try_catch_block(self):
        return False

    def is_keyword(self):
        if hasattr(self, 'isKeyword'):
            return True
        return False
    
    def get_resolutions(self):
        try:
            return self.resolutions
        except:
            return []
        
    def get_js_content(self):
        if self.parent:
            return self.parent.get_js_content()
            
    def get_comments_before_token(self, token):
        if self.parent:
            return self.parent.get_comments_before_token(token)
        return []       

    def get_file(self):
        if self.parent:
            return self.parent.get_file()

    def set_parent(self, parent):
        self.parent = parent
        
    def contains(self, statement):
        if self == statement:
            return True
        try:
            for child in self.get_children():
                try:
                    if child.contains(statement):
                        return True
                except:
                    pass
        except:
            pass
        return False
    
    # function or JSContent
    def is_context_container(self):
        return False
    
    def get_resolutions_callees(self):
        
        vals = []
        for resol in self.get_resolutions():
            if isinstance(resol.callee, KbObject):
                vals.append(self)
            else:
                vals.append(resol.callee)
                
        if len(vals) > 400:
            cast.analysers.log.debug('get_resolutions_callees ' + str(self) + ', ' + str(self.parent))
            cast.analysers.log.debug('len ' + str(len(vals)))
            for v in vals:
                try:
                    cast.analysers.log.debug(str(v) + ', ' + str(v.parent))
                except:
                    cast.analysers.log.debug('exception')
            
        return vals
            
    def get_text(self):
        return self.get_name()
    
    def get_start_row_in_file(self):
        if self.parent:
            return self.parent.get_start_row_in_file()
        return 1
       
    def get_start_col_in_file(self):
        if self.parent:
            return self.parent.get_start_col_in_file()
        return 1

#     Gets the first block container (StatementList)
    def get_block_container(self):
        if self.parent:
            return self.parent.get_block_container()
        return None

#     Gets the first statement container
    def get_statement_container(self):
        if self.parent:
            if isinstance(self.parent, StatementList):
                return self
            else:
                return self.parent.get_statement_container()
        return None

    """ 
    if we have fcall(param1, param2), and param1 or param2 is a string which contains '/', 
    then we take this parameter as evaluation.
    """
    def evaluate_url_including_fcalls(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None):
        evs = self.evaluate_with_trace(None, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter, True)
        return [ev.value for ev in evs]

    def evaluate(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        evs = self.evaluate_with_trace(None, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter, urlIncludingFcall)
        return [ev.value for ev in evs]

#     def evaluate_ov(self, memberNames, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
#         evs = self.evaluate_with_trace(memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter, urlIncludingFcall)
#         return [ev.value for ev in evs]
    
    # AstToken
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 1, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)
        return []

    def evaluate_uri_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None):
        return evaluate_uri_with_trace(self, memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter)
    
    def is_resolved(self):
        return (len(self.get_resolutions()) > 0)

    def add_resolution(self, callee, linkType, addEvenIfResolutionExists = False):
        if not hasattr(self, 'resolutions'):
            self.resolutions = []
        if not callee:
            return
        if not self.get_resolutions() or addEvenIfResolutionExists:
            self.get_resolutions().append(Resolution(callee, linkType))
            return
        if callee.is_function():
            toRemove = []
            for res in self.get_resolutions():
                try:
                    if res.callee.is_identifier():
                        toRemove.append(res)
                except:
                    pass
            for res in toRemove:
                self.get_resolutions().remove(res)
            self.get_resolutions().append(Resolution(callee, linkType))

    def add_nude_resolution(self, callee):
        if not hasattr(self, 'resolutions'):
            self.resolutions = []
        self.resolutions.append(callee)
        
    def get_parent(self):
        return self.parent
    
    def get_token(self):
        if len(self.tokens) > 0:
            return self.tokens[0]
        else:
            return None
    
    def add_token(self, token):
        
        self.tokens.append(token)
    
    def contains_keyword(self, name, tokens = None):

        ret = False
        if self.is_keyword():
            if self.get_text() == name:
                if tokens != None:
                    tokens.append(self)
                ret = True
            
        for child in self.get_children():
            if child and isinstance(child, AstToken):
                b = child.contains_keyword(name, tokens)
                if b:
                    ret = b
        return ret
        
    def is_var_declaration(self):
        return False
        
    def is_let_declaration(self):
        return False
        
    def is_const_declaration(self):
        return False

    def is_new_statement(self):
        return False

    def is_export_statement(self):
        return False

    def is_export_default_statement(self):
        return False
    
    def is_return_statement(self):
        return False
    
    def is_continue_statement(self):
        return False
    
    def is_import_statement(self):
        return False
    
    def is_break_statement(self):
        return False
    
    def is_return_new_statement(self):
        return False
    
    def is_delete_statement(self):
        return False
    
    def is_list_forEach(self):
        return False
        
    def is_top_function(self):
        return False

    def is_new_expression(self):
        return False

    def is_loop(self):
        return False

    def is_for_block(self):
        return False

    def is_for_in_block(self):
        return False

    def is_identifier(self):
        return False
        
    def is_bracketed_identifier(self):
        return False
    
    def is_function(self):
        return isinstance(self, Function)

    def is_class(self):
        return False

    def is_arrow_function(self):
        return False

    def is_js_content(self):
        return False
    
    def is_function_call(self):
        
        return isinstance(self, FunctionCall)
    
    def is_js_function_call(self):
        
        return isinstance(self, JSFunctionCall)
    
    def is_function_call_part(self):
        
        return isinstance(self, FunctionCallPart)
        
#     def is_block_scope(self):
#         return False
    
    def is_define(self):
        
        return isinstance(self, Define)
    
    def is_require(self):
        
        return isinstance(self, Require)
    
    def is_list(self):
        
        return isinstance(self, AstList)
    
    def is_string(self):
        
        return isinstance(self, AstString)

    def is_statement_list(self):
        return False
    
    def is_block(self):
        return False

    def is_ast_block(self):
        return False
    
    def is_assignment(self):
        return isinstance(self, Assignment)
    
    def is_object_value(self):
        return isinstance(self, ObjectValue)
        
    def is_object_destructuration(self):
        return False
        
    def is_operator(self):
        return False
        
    def is_binary_expression(self):
        return False
        
    def is_addition_expression(self):
        return False
        
    def is_or_expression(self):
        return False
        
    def is_in_expression(self):
        return False
        
    def is_unary_expression(self):
        return False
        
    def is_jsx_expression(self):
        return False
         
    def is_if_ternary_expression(self):
        return False
        
    def is_not_expression(self):
        return False
        
    def is_equality_expression(self):
        return False

    def is_switch_block(self):
        return False

    def is_method(self):
        return False

    def is_constructor(self):
        return False
    
    def increment_complexity(self):
        if self.parent:
            self.parent.increment_complexity()

    def get_name(self):
        return self.name
    
    def get_fullname(self):
        return self.name
    
    def get_kb_symbol(self):
        return None

    def set_kb_symbol(self, kbSymbol):
        
        if isinstance(kbSymbol, cast.analysers.CustomObject):
            self.kbObject = kbSymbol
            return
    
    def create_bookmark(self, _file):
        return Bookmark(_file, self.get_begin_line(), self.get_begin_column(), self.get_end_line(), self.get_end_column())

    def convert_ast_list_to_position(self):
        self.position = Position(self.get_begin_line(), self.get_begin_column(), self.get_end_line(), self.get_end_column())
        self.convert_crc()
        try:
            del self.tokens
        except:
            pass

        for child in self.get_children():
            if child and isinstance(child, AstToken):
                child.convert_ast_list_to_position()

    def get_begin_line(self, correctPosition = True):

        try:
            return self.tokens[0].get_begin_line(False) + ( self.get_start_row_in_file() - 1 if correctPosition else 0 )
        except:
            try:
                return self.tokens[0].get_begin_line() + ( self.get_start_row_in_file() - 1 if correctPosition else 0 )
            except:
                try:
                    return self.position.begin_line
                except:
                    return 1
    
    def get_begin_column(self, correctPosition = True):
        
        try:
            if self.tokens[0].get_begin_line() == 1:
                try:
                    return self.tokens[0].get_begin_column(False) + ( self.get_start_col_in_file() - 1 if correctPosition else 0 )
                except:
                    return self.tokens[0].get_begin_column() + ( self.get_start_col_in_file() - 1 if correctPosition else 0 )
            else:
                try:
                    return self.tokens[0].get_begin_column(False)
                except:
                    return self.tokens[0].get_begin_column()
        except:
            try:
                return self.position.begin_col
            except:
                return 1
    
    def get_tokens(self):
            return self.tokens

    def get_end_line(self, correctPosition = True):
        try:
            return self.tokens[-1].get_end_line(False) + ( self.get_start_row_in_file() - 1 if correctPosition else 0 )
        except:
            try:
                return self.tokens[-1].get_end_line() + ( self.get_start_row_in_file() - 1 if correctPosition else 0 )
            except:
                    try:
                        return self.tokens[0].get_begin_line(False) + ( self.get_start_row_in_file() - 1 if correctPosition else 0 )
                    except:
                        try:
                            return self.tokens[0].get_begin_line() + ( self.get_start_row_in_file() - 1 if correctPosition else 0 )
                        except:
                            try:
                                return self.position.end_line
                            except:
                                return 1
    
    def get_end_column(self, correctPosition = True):
        
        try:
            if self.tokens[-1].get_end_line() == 1:
                try:
                    return self.tokens[-1].get_end_column(False) + ( self.get_start_col_in_file() -1 if correctPosition else 0 )
                except:
                    return self.tokens[-1].get_end_column() + ( self.get_start_col_in_file() -1 if correctPosition else 0 )
            else:
                return self.tokens[-1].get_end_column()
        except:
            try:
                if self.tokens[0].get_end_line() == 1:
                    try:
                        return self.tokens[0].get_end_column(False) + ( self.get_start_col_in_file() -1 if correctPosition else 0 )
                    except:
                        return self.tokens[0].get_end_column() + ( self.get_start_col_in_file() -1 if correctPosition else 0 )
                else:
                    try:
                        return self.tokens[0].get_end_column(False)
                    except:
                        return self.tokens[0].get_end_column()
            except:
                try:
                    return self.position.end_col
                except:
                    return 1

    def get_body_comments(self):
        
#         return ''
        s = ''
        try:
            comments = self.tokens[0].get_body_comments()
            for comment in comments:
                s += comment.text
                if s.endswith('*/'):
                    s += '\n'
            return s
        except:
            return s
        
    def _get_code_only_crc(self, crc = 0):
        for token in self.tokens:
            crc = token._get_code_only_crc(crc)
        return crc
        
    def get_code_only_crc(self, crc = 0):
        try:
            lastCrc = 0
            lastAst = None
            lastToken = None
            for token in self.tokens:
                if lastToken:
                    lastCrc = crc
                    lastAst = lastToken
                    crc = lastToken._get_code_only_crc(crc)
                lastToken = token
            if lastToken:
                crc = lastToken.get_code_only_crc(crc)
            elif lastAst:
                crc = lastAst.get_code_only_crc(lastCrc)
            else:
                crc = 0
        except:
            try:
                crc = self.crc
            except:
                crc = 0
        return crc
            
    def set_kb_object(self, name, fullname, kbObject):
        
        if not isinstance(self, KbSymbol):
            return
        
        self.set_is_kb_object()
        kbParent = self.parent
        while kbParent and not isinstance(kbParent, File) and not kbParent.is_kb_object():
            kbParent = kbParent.parent
        if not self.get_kb_symbol():
            KbSymbol.__init__(self, name, fullname, fullname, kbParent)
        else:
            self.get_kb_symbol().initialize(name, fullname, fullname, kbParent)
        self.kbObject = kbObject
        if not self.name:
            self.name = self.get_kb_symbol().get_kb_name()
        
    def set_name(self, name, fullname = None, displayName = None):
        
        self.name = name
        if self.is_kb_object():
            kbParent = self.parent
            while kbParent and not isinstance(kbParent, File) and not kbParent.is_kb_object():
                kbParent = kbParent.parent
            if self.get_kb_symbol():
                KbSymbol.initialize(self, name, fullname, displayName, kbParent)
            else:
                KbSymbol.__init__(self, name, fullname, kbParent, self)

            if not self.name:
                self.name = KbSymbol.get_kb_name(self)
                
    def get_first_kb_parent(self):
        """
        First kb parent is the first parent which is represented in KB, ie a function or a JSContent
        """
        kbParent = self
        while kbParent and not isinstance(kbParent, File) and not kbParent.is_context_container():
            kbParent = kbParent.parent
            
        return kbParent
                
    def get_first_kb_caller(self):
        """
        First kb caller is the first parent which is represented in KB, ie a function or a JSContent
        """
        firstKbParent = self.parent
        while firstKbParent and not isinstance(firstKbParent, File) and not firstKbParent.is_kb_object():
            firstKbParent = firstKbParent.parent
        try:
            if isinstance(firstKbParent, JsContent):
                return firstKbParent.create_javascript_initialisation()
        except:
            pass
        return firstKbParent

    def create_cast_objects(self, parent, config):
        for child in self.get_children():
            if child and isinstance(child, AstToken):
                try:
                    child.create_cast_objects(parent, config)
                except:
                    cast.analysers.log.debug(str(traceback.format_exc()))
    
    def create_cast_links(self, parent, config, suspensionLinks):
        for child in self.get_children():
            if child and isinstance(child, AstToken):
                try:
                    child.create_cast_links(parent, config, suspensionLinks)
                except:
                    pass
    
    def get_children(self):
        return []

    def get_top_resolutions(self, topResolutions, alreadyPassed = []):
        return False
            
    def print(self, pad = 0):
        if self.name:
            print(' '.rjust(pad) + 'AstToken.name : ', self.name)
        else:
            print(' '.rjust(pad) + 'AstToken.name : None')

        if self.get_resolutions():
            print(' '.rjust(pad) + 'AstToken.resolutions :')
            for resolution in self.get_resolutions():
                resolution.print(pad + 3)
        
class AstOperator(AstToken):

    def __init__(self, token, parent, name = None):
        
        AstToken.__init__(self, token, parent, name)
        self.name = token.text
        
    def is_operator(self):
        return True
    
class AstString(AstToken):

    def __init__(self, token, parent, text):
        
        AstToken.__init__(self, token, parent, text)
        if '///' in text:
            pass

    def add_identifier(self, ident):
        try:
            self.identifiers.append(ident)
        except:
            self.identifiers = []
            self.identifiers.append(ident)

    def get_identifiers(self):
        try:
            return self.identifiers
        except:
            return []

    def get_children(self):
        return self.get_identifiers()
            
    def convert_crc(self):
        self.crc = self.get_code_only_crc()
    
    # AstString
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):

        if memberNames:
            return []
        
        def replaceIdentifierInStrings(sList, identifier, values, charForUnknown):
            if not values:
                cmpt = 0
                for s in sList:
                    if charForUnknown:
                        ret = Value(s.value.replace('${' + identifier.get_name() + '}', charForUnknown), s.ast_nodes)
                    else:
                        ret = s
                    sList[cmpt] = ret
                    cmpt += 1
                return sList

            sListNew = []
            for value in values:
                for s in sList:
                    r = s.value.replace('${' + identifier.get_name() + '}', value.value, 1)
                    sListNew.append(Value(r, self))
            return sListNew
        
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 2, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)
        if not self.get_identifiers():
            return [ Value(self.name, self) ]
        identifiersEvaluations = []
        for identifier in self.get_identifiers():
            evs = identifier.evaluate_with_trace(memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            identifiersEvaluations.append(evs)
        cmpt = 0
        sList = []
        sList.append(Value(self.name, self))
        for identifier in self.get_identifiers():
            evs = identifiersEvaluations[cmpt]
            sList = replaceIdentifierInStrings(sList, identifier, evs, charForUnknown)
            cmpt += 1
        return sList

    def create_cast_links(self, parent, config, suspensionLinks):
        
        if not self.get_resolutions():
            return
        
        firstKbParent = self.parent
        while firstKbParent and not isinstance(firstKbParent, File) and not firstKbParent.is_kb_object():
            firstKbParent = firstKbParent.parent
            
        if not firstKbParent:
            return

        file =self.get_js_content().file
#         while not isinstance(file, File):
#             if not file:
#                 pass
#             file = file.parent

        for resol in  self.get_resolutions():
            if resol.linkType:
                create_link_internal(resol.linkType, firstKbParent, resol.callee, self.create_bookmark(file))
        
    def __repr__(self):
        
        return "'" + self.name + "'"
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'AstString ' + str(hex(id(self))) + ' {')
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class EvaluationContext:
    """
    Contains data used during evaluation
    self.caller is the ast at the origin of evaluation
    self.callee is the ast pointed by self.caller after resolution
    self.values is a list containing the possible values of self.caller after evaluation
    """
    def __init__(self, caller, callee):
        self.caller = caller
        self.callee = callee
        self.values = []
        
    def get_values(self):
        return self.values

class Value:
    """
    Represents a computed value, plus the statements that created the value  
    """
    def __init__(self, value, ast_node = None):
        
        self.value = value
        self.ast_nodes = []
        if ast_node:
            if type(ast_node) is list:
                self.ast_nodes.extend(ast_node)
            else:
                self.ast_nodes.append(ast_node)
    
    @staticmethod
    def concat(value1, value2, ast_node):
        """
        Concatenation of values.
        """
        result = Value(value1.value + value2.value)
        result.ast_nodes = value1.ast_nodes + [ast_node] + value2.ast_nodes
        return result
        
    @staticmethod
    def concat_join(value1, constant, value2, ast_node):
        """
        Concatenation of values with a constant in between (for os.path.join)
        """
        result = Value(value1.value + constant + value2.value)
        result.ast_nodes = value1.ast_nodes + [ast_node] + value2.ast_nodes
        return result
    
    def __eq__(self, value):
        
        if type(value) is str:
            return self.value == value
        else:
            return self.value == value.value
    
    def __ne__(self, value):
        
        if type(value) is str:
            return self.value != value
        else:
            return self.value != value.value
    
    def is_in_list(self, values):
        for _val in values:
            if self.value == _val.value:
                return True
        return False
        
    @staticmethod
    def string_is_in_list(_str, _values):
        for _value in _values:
            if _str == _value.value:
                return True
        return False
       
    def __repr__(self):
        
        return self.value
    
class EvaluationCounter:
    
    def __init__(self):
        self.count = 0
    def increment(self):
        self.count += 1
    def isOver(self):
        if self.count > 1000:
            cast.analysers.log.debug('Maximum (1000) has been reached during evaluation.')
            return True
        return False
        
class Identifier(AstToken):
    """
    A identifier a or a.b or a.b.c ...
    """
    def __init__(self, parent = None, name = None, token = None):
        AstToken.__init__(self, token, parent)
#         if token:
#             self.tokens.append(token)
        self.name = name

    def get_prefix_internal(self):
        try:
            return self.prefix
        except:
            return None

    def set_prefix_internal(self, prefix):
        if prefix:
            self.prefix = prefix
        elif self.get_prefix_internal():
            del self.prefix
        
    def get_left_operand(self):
        return self
        
    def get_right_operand(self):
        return None
    
    def convert_crc(self):
        self.crc = self.get_code_only_crc()
        AstToken.convert_crc(self)

    def get_text(self):
        return self.get_fullname()

    def is_identifier(self):
        return True

    def starts_with_this(self):
        try:
            return self.startsWithThis
        except:
            return False

    def get_prefix(self, evenIfExpr = False):

        if not isinstance(self.get_prefix_internal(), str):
            if evenIfExpr:
                return self.get_prefix_internal()
            else:
                return ''        
        return self.get_prefix_internal()
    
    def set_prefix(self, prefix):
        self.prefix = prefix
        if prefix and prefix.startswith('this'):
            self.startsWithThis = True
        elif self.starts_with_this():
            self.startsWithThis = False

    def prefix_starts_with(self, name):
        if not self.get_prefix():
            return False
        return self.get_prefix().startswith(name)

    def prefix_ends_with(self, name):
        if not self.get_prefix():
            return False
        return self.get_prefix().endswith(name)

    def prefix_contains(self, name):
        if not self.get_prefix():
            return -1
        return self.get_prefix().find(name)
        
    def add_prototype_resolution(self, resolution):
        try:
            self.prototypeResolutions.append(resolution)
        except:
            self.prototypeResolutions = []
            self.prototypeResolutions.append(resolution)
        resolution.add_prototype_function(self)
    
    def has_prototype_resolution(self):
        try:
            return self.prototypeResolutions
        except:
            return False
        
    def set_name(self, name, fullname = None):
        
        self.name = name
        if fullname and fullname != name:
            self.fullname = fullname
    
    def get_fullname(self):
        if self.get_prefix_internal():
            if isinstance(self.prefix, str):
                return str(self.prefix) + '.' + self.name
            else:
                return self.name
        else:
            return self.name

    def is_prototype(self):
        try:
            return self.isPrototype
        except:
            return False

    def set_prototype_true(self):
        self.isPrototype = True
        
    def has_been_created_from_string(self):
        """ this is the case for ov where keys are strings
        """
        try:
            if self.tokens and is_token_subtype(self.tokens[0].type, String):
                return True
        except:
            return False
        return False
        
    def add_resolution(self, callee, linkType, addEvenIfResolutionExists = False):
        
        if not callee:
            return
            
        if not hasattr(self, 'resolutions'):
            self.resolutions = []

        if not self.get_resolutions() or addEvenIfResolutionExists:
            self.get_resolutions().append(Resolution(callee, linkType))
            try:
                if callee.is_function():
                    callee.add_call(self)
            except:
                pass
            return
        try:
            if callee.is_function():
                toRemove = []
                for res in self.get_resolutions():
                    try:
                        if res.callee.is_identifier():
                            toRemove.append(res)
                    except:
                        pass
                for res in toRemove:
                    self.get_resolutions().remove(res)
                
                callee.add_call(self)
        except:
            pass
        self.get_resolutions().append(Resolution(callee, linkType))
            
    # var $todoApp = $('#todoapp');
    # var $main = $todoApp.find('#main');
    # var $todoList = $main.find('#todo-list');
    # var list = $todoList;
    # list.on('click', '.destroy', destroy.bind(this));
    #
    # If identifier is list.on, this function returns:
    # list of functioncalls $('#todoapp') and $main.find('#todo-list')
    def get_top_resolutions(self, topResolutions, alreadyPassed = []):

        if len(alreadyPassed) > 10000:
            return False
        alreadyPassed.append(self)
        b = False
        if self.get_resolutions():
            for resolution in self.get_resolutions():
                callee = resolution.callee
                try:
                    if callee.parent and callee.parent.is_assignment():
                        rightOperand = callee.parent.rightOperand
                        if not rightOperand == self and not rightOperand in topResolutions and not rightOperand.get_top_resolutions(topResolutions, alreadyPassed):
                            topResolutions.append(rightOperand)
                            b = True
                except:
                    pass
        return b

    def create_cast_links(self, parent, config, suspensionLinks):
        
        if not self.get_resolutions():
            return
        
        firstKbParent = self.parent
        while firstKbParent and not isinstance(firstKbParent, File) and not firstKbParent.is_kb_object():
            firstKbParent = firstKbParent.parent

        if not firstKbParent:
            return

        file =self.get_js_content().file

        for resol in  self.get_resolutions():
            if resol.linkType:
                if not create_link_internal(resol.linkType, firstKbParent, resol.callee, self.create_bookmark(file)):
                    suspensionLinks.append(SuspensionLink(resol.linkType, firstKbParent, resol.callee, self.create_bookmark(file)))

    # Identifier
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):

        def find(element, json):
            try:
                keys = element.split('.')
                rv = json
                for key in keys:
                    rv = rv[key]
                return rv
            except:
                return None        

        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 3, heap size = ' + str(len(objectsPassed)) + ' ' + str(self))
            return []
#         if not memberNames and constants and self.get_fullname() in constants:
        if not memberNames and constants:
            fulln = self.get_fullname()
            if fulln in constants:
                return [ Value(constants[fulln], self) ]
            _val = find(fulln, constants)
            if not _val and '.' in fulln:
                _val = find(fulln[fulln.find('.') + 1:], constants)
            if _val:
                return [ Value(_val, self) ]
        objectsPassed.append(self)
        """
        Evaluates the possible values for the identifier
        """
        try:
            if not originalCaller:
                originalCaller = self
                
            # If the identifier is not part of an assignment or if it has not be resolved to a definition,
            # it can not be evaluated.
            if not self.get_resolutions() and self.parent.is_object_value():
                for key, value in self.parent.items.items():
                    if key == self:
                        newObjectsPassed = list(objectsPassed)
                        retValues = value.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                        return retValues
                if charForUnknown:
                    if memberNames:
                        ret = {}
                        for memberN in memberNames:
                            ret[memberN] = Value(charForUnknown, self)
                        return [ ret ]
                    else:
                        return [ Value(charForUnknown, self) ]
                else:
                    return [ ]
            # If the identifier is not part of an assignment or if it has not be resolved to a definition,
            # it can not be evaluated.
            if not self.get_resolutions() and not self.parent.is_assignment() and not self.parent.is_var_declaration():
                if charForUnknown:
                    if memberNames:
                        ret = {}
                        for memberN in memberNames:
                            ret[memberN] = Value(charForUnknown, self)
                        return [ ret ]
                    else:
                        return [ Value(charForUnknown, self) ]
                else:
                    return [ ]
            
            if evaluationContext:
                caller = evaluationContext.caller
            else:
                caller = self
    
            # if context callee is not the same as self.resolutions.callee, we reevaluate current identifier from scratch.
            # This is the case for example with "a = b + c" when we want to evaluate a, which require the evaluation of b and c
            # which have not the same callee as a.
            callees = self.get_resolutions_callees()
            if evaluationContext and self.get_resolutions() and not evaluationContext.callee in callees:
                evaluationContext = None
                caller = self
                
            returnValues = []
            
            if not evaluationContext:
                # determine the callee
                callees = caller.get_resolutions_callees()
                if not callees:
                    callees = [ caller ]
                
                if True:
                    for callee in callees:
                        # If callee is a function parameter, we get all the calls to the function to try to evaluate
                        # the identifier
                        vals = []
                        if callee.parent and callee.parent.is_function() and callee in callee.parent.parameters:
                            paramNumber = 0
                            while not callee == callee.parent.parameters[paramNumber]:
                                paramNumber += 1
                            
                            if callee.parent.parent.is_function_call_part() and callee.parent.parent.get_name() == 'forEach':
                                fcall = callee.parent.parent.parent
                                if fcall.parent and isinstance(fcall.parent, AnyStatement) and fcall.parent.elements[0].is_list():
                                    _list = fcall.parent.elements[0]
                                    for _value in _list.values:
                                        newObjectsPassed = list(objectsPassed)
                                        _vals = _value.evaluate_with_trace(memberNames, None, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                                        if _vals:
                                            for paramVal in _vals:
                                                if not paramVal.is_in_list(vals):
                                                    vals.append(paramVal)
                              
                            for call in callee.parent.get_calls():
                                fcallpart = call.parent
                                try:
                                    if len(fcallpart.parameters) > paramNumber:
                                        param = fcallpart.parameters[paramNumber]
                                        newObjectsPassed = list(objectsPassed)
                                        paramVals = param.evaluate_with_trace(memberNames, None, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                                        if paramVals:
                                            _tempVals = []
                                            for paramVal in paramVals:
                                                if memberNames:
                                                    if not is_object_in_list(paramVal, _tempVals):
                                                        for value in paramVal.values():
                                                            value.ast_nodes.append(fcallpart)
                                                        vals.append(paramVal)
                                                        _tempVals.append(paramVal)
                                                else:
                                                    if not paramVal.is_in_list(_tempVals):
                                                        if paramVal.value != charForUnknown:
                                                            paramVal.ast_nodes.append(fcallpart)
                                                        vals.append(paramVal)
                                                        _tempVals.append(paramVal)
                                except:
                                    pass
                            if vals:
                                returnValues = vals
#                                 for val in vals:
#                                     if memberNames:
#                                         if not is_object_in_list(val, returnValues):
#                                             returnValues.append(val)
#                                     else:
#                                         if not val.is_in_list(returnValues):
#                                             returnValues.append(val)
                            continue
                        
                        elif callee.parent and callee.parent.is_object_value():
    
                            newObjectsPassed = list(objectsPassed)
                            evals = callee.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                            for ev in evals:
                                returnValues.append(ev)
                            continue          
    
                        elif callee.parent and callee.parent.is_assignment() and callee.parent.get_right_operand().is_object_value():
    #                     We are in case of: var a = { key : value } and we want to evaluate a.
    #                     We have to check originalCaller if it is of kind a.key
                            ov = callee.parent.get_right_operand()
                            if originalCaller and originalCaller.get_prefix_internal() and ov.get_item(originalCaller.get_name()):
                                value = ov.get_item(originalCaller.get_name())
                                newObjectsPassed = list(objectsPassed)
                                evals = value.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                                for ev in evals:
                                    returnValues.append(ev)
                                continue          
                        
                        if not callee.parent or (not callee.parent.is_assignment() and not callee.parent.is_var_declaration()):
                            continue
                        evaluationContext = EvaluationContext(caller, callee)
                        
                        callerContainer = None
                        calleeAssignment = callee.parent
                        if calleeAssignment.parent and calleeAssignment.parent.is_var_declaration() and len(calleeAssignment.parent.elements) == 1:
                            calleeAssignment = calleeAssignment.parent
                        
                        callerContainer = caller.get_block_container()
                            
                        currentStatement = self.get_statement_container()
                        
                        if caller == callee:
                            newObjectsPassed = list(objectsPassed)
                            vals = currentStatement.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                            if evaluationContext:
                                # check
                                if (evaluationContext.values):
                                    for val in evaluationContext.values:
                                        if not val.is_in_list(returnValues):
                                            returnValues.append(val)
                                continue
                            else:
                                if vals:
                                    for val in vals:
                                        if not val.is_in_list(returnValues):
                                            returnValues.append(val)
                                continue
                            
                        # Ex of a block containing following statements: 
                        #   statement1 
                        #   var a = 1; 
                        #   other statements; 
                        #   f(a); 
                        #   other statements; 
                        # If we want to evaluate a on line 4, we get the calleeContainer which is all the block, 
                        # we go to each statement from the first one, we do nothing until a declaration (line 2),
                        # and we evaluate a on each statement after declaration and until line 4.
                        # we do not enter in function declarations.
                        
                        # Other example: 
                        #   var a = 1; 
                        #   other statements; 
                        #   function f() { 
                        #      g(a); 
                        #   } 
                        # If we want to evaluate a on line 4, we get the calleeContainer which is all the JSContent block, 
                        # we get the callerContainer which is all the function block.
                        # As both containers are different, we evaluate the declaration of a (line 1), then we go to each statement of the function,
                        # and we evaluate a on each statement until line 4.
    
                        calleeFunctionContainer = calleeAssignment.get_block_container()
                        callerFunctionContainer = caller.get_block_container()
                        
                        if callerFunctionContainer and callerFunctionContainer.contains(calleeFunctionContainer):
                            calleeFunctionContainer = callerFunctionContainer
                            
                        if calleeFunctionContainer != callerFunctionContainer:
                            afterDeclaration = False
                            for statement in calleeFunctionContainer.statements:
                                if statement.is_function():
                                    pass
                                try:
                                    if statement.contains(callerFunctionContainer):
                                        if statement.is_function():
                                            statement.evaluate_content_with_trace(evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants)
                                        else:
                                            statement.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                                        break
                                    try:
                                        isVarDecl = statement.is_var_declaration()
                                    except:
                                        isVarDecl = False
                                    newObjectsPassed = list(objectsPassed)
                                    if memberNames:
                                        statement.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                                    else:
                                        statement.evaluate(evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                                    afterDeclaration = True
                                    if statement == currentStatement:
                                        break
                                except:
                                    pass
                        else:
                            afterDeclaration = False
                            
                            if callerContainer:
                                for statement in callerContainer.statements:
                                    try:
                                        isVarDecl = statement.is_var_declaration()
                                    except:
                                        isVarDecl = False
                                    try:
                                        if not afterDeclaration and statement != calleeAssignment and not ( isVarDecl and calleeAssignment in statement.elements ) and not statement.contains(calleeAssignment):
                                            continue
                                        else:
                                            newObjectsPassed = list(objectsPassed)
                                            if memberNames:
                                                statement.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                                            else:
                                                statement.evaluate(evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                                            afterDeclaration = True
                                                 
                                            if statement == currentStatement:
                                                break
                                    except:
                                        continue
                        if (evaluationContext.values):
                            for val in evaluationContext.values:
                                if memberNames:
                                    if not is_object_in_list(val, returnValues):
                                        returnValues.append(val)
                                else:
                                    if not val.is_in_list(returnValues):
                                        returnValues.append(val)
                        continue
                        # end for callee in callees
                
                if not memberNames and charForUnknown and not returnValues:
                    returnValues.append(Value(charForUnknown, self))
                
                return returnValues
            
            else:
                
                statement = self.get_statement_container()
                newObjectsPassed = list(objectsPassed)
                returnValues = statement.evaluate_with_trace(memberNames, evaluationContext, None, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                return returnValues
        except:
            return []

    def get_fullname_internal(self):
        try:
            return self.fullname
        except:
            return self.name
        
    def __repr__(self):
        
        if self.get_fullname_internal():
            return str(self.get_fullname_internal())
        else:
            return self.name
        
    def is_func_call(self):
        try:
            return self.isFuncCall
        except:
            return False
        
    def is_await(self):
        try:
            return self.isAwait
        except:
            return False
        
    def set_is_func_call(self, b):
        if b or self.is_func_call():
            self.isFuncCall = b
        
    def set_is_await(self, b):
        if b:
            self.isAwait = b
        
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Identifier ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'prefix : ', self.get_prefix_internal())
        print(' '.rjust(pad + 3) + 'isFuncCall : ', self.is_func_call())
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class BracketedIdentifier(Identifier):
    """
    A identifier a[...]
    """
    def __init__(self, identifier):
        Identifier.__init__(self, identifier.tokens[0], identifier.parent)
        self.tokens = identifier.tokens
        self.name = identifier.name

        if identifier.get_fullname_internal():
            self.fullname = identifier.get_fullname_internal()
        if identifier.get_prefix_internal():
            self.prefix = identifier.get_prefix_internal()
        if identifier.starts_with_this():
            self.startsWithThis = True
        if identifier.is_func_call():
            self.isFuncCall = identifier.is_func_call()
        if identifier.is_prototype():
            self.isPrototype = identifier.isPrototype
        if identifier.has_prototype_resolution():
            self.prototypeResolutions = identifier.prototypeResolutions
        
        if identifier.is_keyword():
            self.isKeyword = True
        self.parent = identifier.parent
        self.set_is_kb_object(identifier.is_kb_object())
        self.set_kb_symbol(identifier.get_kb_symbol())
        if identifier.get_resolutions():
            self.resolutions = identifier.get_resolutions()
        if identifier.is_bracketed_identifier():
            if identifier.get_bracketed_expression():
                self.bracketedExpression = identifier.bracketedExpression
            if identifier.get_identifier_evaluations():
                self.identifierEvaluations = identifier.identifierEvaluations
        
    def get_identifier_evaluations(self):
        try:
            return self.identifierEvaluations
        except:
            return []
        
    def set_identifier_evaluations(self, l):
        self.identifierEvaluations = l
        
    def get_bracketed_expression(self):
        try:
            return self.bracketedExpression
        except:
            return None
        
    def is_bracketed_identifier(self):
        return True
    
    def get_fullnames(self):

        fullnames = []
        if not self.get_identifier_evaluations():
            fullnames.append(self.get_fullname())
            return fullnames
        
        prefix = self.get_fullname()
        for _eval in self.identifierEvaluations:
            fullnames.append(prefix + '.' + _eval)
        return fullnames
            
    def evaluate_identifier(self):
        if not self.get_bracketed_expression():
            return False
        
        if self.bracketedExpression.get_resolutions():
            callee = self.bracketedExpression.resolutions[0].callee
            if callee.parent and callee.parent.is_function() and callee in callee.parent.parameters:
                values = []
                paramNumber = 0
                while not callee == callee.parent.parameters[paramNumber]:
                    paramNumber += 1
                            
                for call in callee.parent.get_calls():
                    fcallpart = call.parent
                    try:
                        if len(fcallpart.parameters) > paramNumber:
                            param = fcallpart.parameters[paramNumber]
                            vals = param.evaluate(None, None, None, '', None, None, True)
                            if type(vals) is str:
                                values.append(vals)
#                                 if astCallsInitial != None:
#                                     add_ast_call(vals, fcallpart, astCallsInitial)
                            elif vals:
                                values.extend(vals)
#                                 if astCallsInitial != None:
#                                     add_ast_call(vals, fcallpart, astCallsInitial)
                    except:
                        pass
                if values:
                    self.set_identifier_evaluations(values)
                    return True
                return False
        
        evaluations = self.bracketedExpression.evaluate()
        if not evaluations:
            return False
        self.set_identifier_evaluations(evaluations)
        return True
        
    def create_identifiers_from_evaluation(self):
        res = []
        fullnames = self.get_fullnames()
        for fullname in fullnames:
            index = fullname.rfind('.')
            if index >= 0:
                prefix = fullname[0:index]
                name = fullname[index+1:]
            else: 
                prefix = ''
                name = fullname
            newIdent = copy.copy(self)
            newIdent.set_prefix_internal(prefix)
            newIdent.name = name
            res.append(newIdent)
        return res

class AstStatement(AstToken):

    def __init__(self, token, parent):
        
        AstToken.__init__(self, token, parent)

    def print(self, pad = 0):
        AstToken.print(self, pad)

class StatementList(AstToken):

    def __init__(self, token, parent):
        
        AstToken.__init__(self, token, parent)
        self.statements = []
            
    def get_comments_before_token(self, token):
        
        l = []
        try:
            for tok in self.tokens[0].children[-1].children:
                if tok == token and tok.begin_line == token.begin_line and tok.begin_column == token.begin_column:
                    break
                if is_token_subtype(tok.type, Comment):
                    l.append(tok)
                else:
                    l.clear()
        except:
            pass
        return l

    def get_block_container(self):
        return self
    
    def set_expression(self, expr):
        self.statements.append(expr)
        
    def get_statements(self):
        
        return self.statements
    
    def add_statement(self, statement):
        
        self.statements.append(statement)

    def is_statement_list(self):
        return True
    
    def get_children(self):
        return self.statements

    # StatementList
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 4, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)
        for statement in self.statements:
            newObjectsPassed = list(objectsPassed)
            statement.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            if evaluationContext and statement.contains(evaluationContext.caller):
                break
        return evaluationContext.values

    def print(self, pad = 0):
        print(' '.rjust(pad) + 'StatementList.statements :')
        for statement in self.statements:
            statement.print(pad + 3)
        AstToken.print(self, pad)

class AstBlock(StatementList):
    
    def __init__(self, token, parent):
        StatementList.__init__(self, token, parent)
    
    def is_ast_block(self):
        return True

    def get_block_container(self):
        return self
    
    def print(self, pad = 0):
        StatementList.print(self, pad)

class Expression(AstToken):   

    def __init__(self, token, parent):
        AstToken.__init__(self, token, parent)
        self.elements = []
        
    def get_elements(self):
        return self.elements()
    
    def add_element(self, ast):
        
        self.elements.append(ast)
    
    def get_children(self):
        return self.elements
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Expression.elements :')
        for element in self.elements:
            element.print(pad + 3)
        AstToken.print(self, pad)

class Block(AstToken):
    
    def __init__(self, token, parent):
        AstToken.__init__(self, token, parent)
        self.block = None # type AstBlock

    def get_block(self):
        return self.block
    
    def get_children(self):
        return [ self.block ]
    
    def is_block(self):
        return True

    # Block
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 5, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)
        for statement in self.block.statements:
            newObjectsPassed = list(objectsPassed)
            statement.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
        return evaluationContext.values

    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Block ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class ExpressionBlock(Block):
    
    def __init__(self, token, parent):
        Block.__init__(self, token, parent)
        self.expression = None  # type Expression

    def set_expression(self, expr):
        self.expression = expr

    def get_expression(self):
        return self.expression
    
    def get_children(self):
        if self.expression:
            return [ self.expression, self.block ]
        else:
            return [ self.block ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'ExpressionBlock ' + str(hex(id(self))) + ' {')
        if self.expression:
            print(' '.rjust(pad + 3) + 'expression :')
            self.expression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class IfStatement(AstToken):
    """
    Represents an If... Then...Else block.
    """
    def __init__(self, token, parent):
        AstToken.__init__(self, token, parent)
        self.if_block = None    # instance of IfBlock
        self.else_if_blocks = None  # list of instances of ElseIfBlock
        self.else_block = None  # instance of ElseBlock

    def set_if_block(self, block):
        self.if_block = block

    def set_else_block(self, block):
        self.else_block = block

    def add_else_if_block(self, block):
        if self.else_if_blocks == None:
            self.else_if_blocks = []
        self.else_if_blocks.append(block)
        
    def get_children(self):
        children = []
        if self.if_block:
            children.append(self.if_block)
        if self.else_if_blocks:
            for block in self.else_if_blocks:
                children.append(block)
        if self.else_block:
            children.append(self.else_block)
        return children

    # IfStatement
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 6, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)
        """
        Evaluates an identifier defined in the context parameter when we go through an If statement
        Ex: var a = 'a';
            if ()
                a += 'b';
            else
                a += 'c';
            f(a);
        On last line, a can be evaluated to 'ab' or 'ac'
        """
        try:
            # we save evaluationContext values in initial value ('a' in our example):
            initialValues = evaluationContext.values
            ifBlockVals = None
            elseifBlocksVals = []
            elseBlockVals = None
            
            if self.if_block:
                newObjectsPassed = list(objectsPassed)
                ifBlockVals = self.if_block.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            if self.else_if_blocks:
                for block in self.else_if_blocks:
                    evaluationContext.values = initialValues
                    newObjectsPassed = list(objectsPassed)
                    elseifBlockVals = block.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                    elseifBlocksVals.append(elseifBlockVals)
            if self.else_block:
                evaluationContext.values = initialValues
                newObjectsPassed = list(objectsPassed)
                elseBlockVals = self.else_block.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            else:
                if not initialValues and ifBlockVals:
                    elseBlockVals = [ ]
                else:
                    elseBlockVals = [ ]
              
            if self.else_block:
                vals = ifBlockVals
            else:
                if not initialValues:
                    if not self.contains(evaluationContext.caller):
                        if ifBlockVals or elseifBlockVals:
                            vals = [ Value('', self) ]
                        else:
                            vals = [ ]
                else:
                    vals = initialValues
                vals.extend(ifBlockVals)
            for elseifBlockVals in elseifBlocksVals:
                for elseifBlockVal in elseifBlockVals:
                    if not elseifBlockVal in vals:
                        vals.append(elseifBlockVal)
            for elseBlockVal in elseBlockVals:
                if not elseBlockVal in vals:
                    vals.append(elseBlockVal)
                
            evaluationContext.values = []
            if vals:
                for v in vals:
                    if not v.is_in_list(evaluationContext.values):
                        evaluationContext.values.append(v)
            vals = evaluationContext.values
            return vals
        except:
            return []

    def print(self, pad = 0):
        print(' '.rjust(pad) + 'IfStatement ')
    
class IfBlock(ExpressionBlock):
    """
    Represents an If block (the If part of an If statement)
    """
    def __init__(self, token, parent):
        ExpressionBlock.__init__(self, token, parent)
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'IfBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'expression :')
        self.expression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class ElseIfBlock(ExpressionBlock):
    """
    Represents an Else If block (the else if part of an If statement)
    """
    def __init__(self, token, parent):
        ExpressionBlock.__init__(self, token, parent)
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'ElseIfBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'expression :')
        self.expression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class ElseBlock(Block):
    """
    Represents an Else block (the else part of an If statement)
    """
    def __init__(self, token, parent):
        Block.__init__(self, token, parent)
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'ElseBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class LoopBlock(Block):
    
    def __init__(self, token, parent):
        Block.__init__(self, token, parent)

    def is_loop(self):
        return True

class WhileBlock(LoopBlock):
    
    def __init__(self, token, parent):
        LoopBlock.__init__(self, token, parent)
        self.expression = None

    def set_expression(self, expr):
        self.expression = expr

    def get_expression(self):
        return self.expression
    
    def get_children(self):
        if self.expression:
            return [ self.expression, self.block ]
        else:
            return [ self.block ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'WhileBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'expression :')
        self.expression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class ForBlock(LoopBlock):
    
    def __init__(self, token, parent):
        LoopBlock.__init__(self, token, parent)
        self.startExpressions = None
        self.terminationExpression = None
        self.forwardExpression = None

    def is_for_block(self):
        return True

    def is_for_in_block(self):
        try:
            if self.startExpressions:
                for expr in self.startExpressions:
                    if expr.is_in_expression(): 
                        return True
        except:
            pass
        return False
    
    def add_start_expression(self, expr):
        if not self.startExpressions:
            self.startExpressions = []
        self.startExpressions.append(expr)

    def set_termination_expression(self, expr):
        self.terminationExpression = expr

    def set_forward_expression(self, expr):
        self.forwardExpression = expr

    def get_start_expressions(self):
        return self.startExpressions

    def get_termination_expression(self):
        return self.terminationExpression

    def get_forward_expression(self):
        return self.forwardExpression
    
    def get_children(self):
        v = []
        if self.startExpressions:
            v.extend(self.startExpressions)
        if self.terminationExpression:
            v.append(self.terminationExpression)
        if self.forwardExpression:
            v.append(self.forwardExpression)
        v.append(self.block)
        return v
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'ForBlock ' + str(hex(id(self))) + ' {')
        if self.startExpressions:
            print(' '.rjust(pad + 3) + 'startExpressions :')
            for expr in self.startExpressions:
                expr.print(pad + 6)
        print(' '.rjust(pad + 3) + 'terminationExpression :')
        self.terminationExpression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'forwardExpression :')
        self.forwardExpression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class ForEachBlock(LoopBlock):
    
    def __init__(self, token, parent):
        LoopBlock.__init__(self, token, parent)
        self.expression = None

    def set_expression(self, expr):
        self.expression = expr

    def get_expression(self):
        return self.expression
    
    def get_children(self):
        if self.expression:
            return [ self.expression, self.block ]
        else:
            return [ self.block ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'ForEachBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'expression :')
        self.expression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class SwitchStatement(AstToken):
    
    def __init__(self, token, parent):
        AstToken.__init__(self, token, parent)
        self.expression = None
        self.case_blocks = None
        self.default_block = None
        
    def is_switch_block(self):
        return True

    def set_expression(self, expr):
        self.expression = expr
        
    def set_default_block(self, block):
        self.default_block = block

    def add_case_block(self, block):
        if self.case_blocks == None:
            self.case_blocks = []
        self.case_blocks.append(block)
        
    def get_children(self):
        children = []
        if self.expression:
            children.append(self.expression)
        if self.case_blocks:
            for block in self.case_blocks:
                children.append(block)
        if self.default_block:
            children.append(self.default_block)
        return children
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'SwitchBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'expression :')
        self.expression.print(pad + 6)
        print(' '.rjust(pad) + '}')
    
class SwitchCaseBlock(ExpressionBlock):
    """
    Represents a switch case block (the case part of an switch statement)
    """
    def __init__(self, token, parent):
        ExpressionBlock.__init__(self, token, parent)

    def print(self, pad = 0):
        print(' '.rjust(pad) + 'SwitchCaseBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'expression :')
        self.expression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')
    
class SwitchDefaultBlock(Block):
    """
    Represents a switch default block (the default part of an switch statement)
    """
    def __init__(self, token, parent):
        Block.__init__(self, token, parent)
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'SwitchDefaultBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class CatchBlock(ExpressionBlock):
    
    def __init__(self, token, parent):
        ExpressionBlock.__init__(self, token, parent)
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'CatchBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'expression :')
        self.expression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class FinallyBlock(Block):
    
    def __init__(self, token, parent):
        Block.__init__(self, token, parent)
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'FinallyBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad)
        print(' '.rjust(pad) + '}')

class TryCatchBlock(AstToken):
    
    def __init__(self, token, parent):
        AstToken.__init__(self, token, parent)
        self.block = None # type AstBlock
        self.catchBlocks = [] # type CatchBlock
        self.finallyBlock = None # type FinallyBlock

    def is_try_catch_block(self):
        return True
    
    def get_try_block(self):
        return self.block

    def get_catch_blocks(self):
        return self.catchBlocks

    def get_finally_block(self):
        return self.finallyBlock
    
    def add_catch_block(self, block):
        
        self.catchBlocks.append(block)

    def set_finally_block(self, block):
        
        self.finallyBlock = block
    
    def get_children(self):
        
        children = []
        children.append(self.block)
        children.extend(self.catchBlocks)
        children.append(self.finallyBlock)
        return children
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'TryCatchBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        print(' '.rjust(pad + 3) + 'catchBlocks :')
        for block in self.catchBlocks:
            block.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class DoBlock(LoopBlock):
    
    def __init__(self, token, parent):
        LoopBlock.__init__(self, token, parent)
        self.expression = None

    def set_expression(self, expr):
        self.expression = expr

    def get_expression(self):
        return self.expression
    
    def get_children(self):
        if self.expression:
            return [ self.expression, self.block ]
        else:
            return [ self.block ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'DoBlock ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'expression :')
        self.expression.print(pad + 6)
        print(' '.rjust(pad + 3) + 'block :')
        self.block.print(pad + 6)
        AstToken.print(self, pad = 3)
        print(' '.rjust(pad) + '}')

nr_first_range_unnamed_functions = 0
fullnames = []

def initFullnames():
    
    global fullnames
    fullnames.clear()

"""
Following object is used for

define([
    "./_base/array",
    "./_base/lang",
    /*===== "./_base/declare", =====*/
    "./number",
    "./i18n", "./i18n!./cldr/nls/currency",
    "./cldr/monetary"
], function(darray, lang, /*===== declare, =====*/ dnumber, i18n, nlsCurrency, cldrMonetary){});

management.
"""
class Module:
    
    def __init__(self, name = None):
        self.name = name
        self.parameters = OrderedDict() # contains key = darray, value = fullpath corresponding to file "./_base/array"
        self.globalFunctionsByName = {}
        self.globalVariablesByName = {}
        self.globalClassesByName = {}
        self.lastLine = -1
        
    def add_parameter(self, param, ref):
        self.parameters[param] = ref
        
    def get_function(self, name):
        if name in self.globalFunctionsByName:
            return self.globalFunctionsByName[name][0].kbSymbol
        return None
        
    def get_variable(self, name):
        if name in self.globalVariablesByName:
            return self.globalVariablesByName[name][0].identifier
        return None
        
    def get_class(self, name):
        if name in self.globalClassesByName:
            return self.globalClassesByName[name][0].kbSymbol
        return None

class JsContent(KbSymbol, StatementList):

    def __init__(self, token, parent, file = None, config = None, startRow = 1, startCol = 1):
        StatementList.__init__(self, token, parent)
        global nr_first_range_unnamed_functions
        global fullnames
        # represent all javascript code directly included in javascript file without being inside a function
        self.javascriptInitialisation = None
        nr_first_range_unnamed_functions = 0
        self.lineCount = -1
        self.complexity = 1
        self.globalFunctions = {}
        self.globalFunctionsTemp = {}
        self.globalVariables = {}
        self.globalClasses = {}
        self.globalClassesTemp = {}
        self.file = file
        self.config = config
        self.startRow_in_file = startRow
        self.startCol_in_file = startCol
        self.current_statement_nr = -1
        self.htmlCallingFiles = []
        self.kbObject = None
        self.set_is_kb_object()
        self.objectDatabaseProperties = ObjectDatabaseProperties()
        self.name = os.path.basename(parent.get_path())
        sourceCodeType = ''
        if config:
            if self.name.lower().endswith('.jsx'):
                sourceCodeType = config.objectTypes.jsxSourceCodeType
            else:
                sourceCodeType = config.objectTypes.sourceCodeType
            if sourceCodeType:
                displayName = parent.get_path()
                fullname = parent.get_path() + '/' + sourceCodeType
            else:
                fullname = '[' + parent.get_path() + ']'
                displayName = fullname
                self.kbObject = parent
            KbSymbol.__init__(self, self.name, fullname, displayName, parent)

        self.xmlHttpRequests = []   # list of identifiers corresponding to new XMLHttpRequest()
        self.openCalls = []   # list of identifiers corresponding to new XMLHttpRequest()
        self.webSockets = []   # list of identifiers corresponding to new new WebSocket(url or config)

#        window.location.href = "home.do";
#        window.location.replace("home.do");
#        window.location='/rotw/public/rotwLoginInput.action';
#        form.action = "ViewCSPUserDetailsAction.do?&step=Submit";
#        window.open(url,...);
        self.httpRequests = []   # list of identifiers corresponding to new XMLHttpRequest()
        self.eventSourceRequests = []   # list of new EventSource()

#        ExecuteSQL("select * from authors")
        self.executeSqls = []   # list of calls to ExecuteSQL()
        self.keepFile = False
        self.codeLines = 0
        self.nextHtmlFragmentNumber = 0
        self.defaultExportedAst = None
        # stores module.exports = ... module.exports.myobject = ... (key = left operand fullname)
        self.moduleExports = {}
        self.module = None

    def increment_complexity(self):
        self.complexity += 1

    def is_module(self):
        return True if self.module else False
            
    def get_fullname(self):
        return self.file.get_path()
    
    def get_exported_default(self):
        return self.defaultExportedAst
    
    def get_module_exports(self, name = None):
        if name:
            if 'module.exports.' + name in self.moduleExports:
                return self.moduleExports['module.exports.' + name]
            elif 'exports.' + name in self.globalFunctions:
                return self.globalFunctions['exports.' + name][0]
            return None
        else:
            if 'module.exports' in self.moduleExports:
                return self.moduleExports['module.exports']
            return None
        
    def get_next_html_fragment_number(self):
        return self.nextHtmlFragmentNumber
        
    def increment_next_html_fragment_number(self):
        self.nextHtmlFragmentNumber += 1
        return self.nextHtmlFragmentNumber

    def decrement_code_lines(self, nb):
        self.codeLines -= nb
        if self.codeLines < 0:
            self.codeLines = 0

    def is_js_content(self):
        return True
    
    def get_js_content(self):
        return self

    def get_file(self):
        return self.file

    def update_globals_with_cast_objects(self, globalVariablesByName, globalFunctionsByName):
         
        for funcName, lst in self.globalFunctions.items():
            if not funcName in globalFunctionsByName:
                continue
            globLst = globalFunctionsByName[funcName]
            for func in lst:
                for globFunc in globLst:
                    if func.get_kb_symbol() == globFunc.kbSymbol:
                        globFunc.kbObject = globFunc.kbSymbol.get_kb_object()
#                         globFunc.kbSymbol = None
                        break
    
    def is_context_container(self):
        return True

    def empty(self):
        self.statements = None

    def get_top_object(self):
        if self.file.get_path().endswith('.html'):
            return self.parent
        else:
            return self
    
    def add_global_function(self, name, function):

        nameWithoutPrototype = name
        if '.prototype.' in nameWithoutPrototype:
            nameWithoutPrototype = nameWithoutPrototype.replace('prototype.', '')
        if '.statics.' in nameWithoutPrototype:
            nameWithoutPrototype = nameWithoutPrototype.replace('statics.', '')
            
        if not nameWithoutPrototype in self.globalFunctions:
            lst = []
            self.globalFunctions[nameWithoutPrototype] = lst
            lstTemp = []
            self.globalFunctionsTemp[nameWithoutPrototype] = lstTemp
            if name != nameWithoutPrototype:
                if not name in self.globalFunctions:
                    lst2 = []
                    self.globalFunctions[name] = lst2
                    lstTemp2 = []
                    self.globalFunctionsTemp[name] = lstTemp2
                else:
                    lst2 = self.globalFunctions[name]
                    lstTemp2 = self.globalFunctionsTemp[name]
            elif name.startswith('window.'):
                name = name[7:]
                if not name in self.globalFunctions:
                    lst2 = []
                    self.globalFunctions[name] = lst2
                    lstTemp2 = []
                    self.globalFunctionsTemp[name] = lstTemp2
                else:
                    lst2 = self.globalFunctions[name]
                    lstTemp2 = self.globalFunctionsTemp[name]
        else:
            lst = self.globalFunctions[nameWithoutPrototype]
            lstTemp = self.globalFunctionsTemp[nameWithoutPrototype]
            if name != nameWithoutPrototype:
                if not name in self.globalFunctions:
                    lst2 = []
                    self.globalFunctions[name] = lst2
                else:
                    lst2 = self.globalFunctions[name]
                if not name in self.globalFunctionsTemp:
                    lstTemp2 = []
                    self.globalFunctionsTemp[name] = lstTemp2
                else:
                    lstTemp2 = self.globalFunctionsTemp[name]
        lst.append(function)
        lstTemp.append(function)
        if name != nameWithoutPrototype:
            lst2.append(function)
            lstTemp2.append(function)
    
    def add_global_variable(self, name, variable):

        if not name in self.globalVariables:
            lst = []
            self.globalVariables[name] = lst
        else:
            lst = self.globalVariables[name]
        lst.append(variable)
    
    def add_global_class(self, name, cl):

        nameWithoutPrototype = name
            
        if not nameWithoutPrototype in self.globalClasses:
            lst = []
            self.globalClasses[nameWithoutPrototype] = lst
            lstTemp = []
            self.globalClassesTemp[nameWithoutPrototype] = lstTemp
            if name != nameWithoutPrototype:
                if not name in self.globalClasses:
                    lst2 = []
                    self.globalClasses[name] = lst2
                    lstTemp2 = []
                    self.globalClassesTemp[name] = lstTemp2
                else:
                    lst2 = self.globalClasses[name]
                    lstTemp2 = self.globalClassesTemp[name]
        else:
            lst = self.globalClasses[nameWithoutPrototype]
            lstTemp = self.globalClassesTemp[nameWithoutPrototype]
            if name != nameWithoutPrototype:
                lst2 = self.globalClasses[name]
                lstTemp2 = self.globalClassesTemp[name]
        lst.append(cl)
        lstTemp.append(cl)
        if name != nameWithoutPrototype:
            lst2.append(cl)
            lstTemp2.append(cl)
    
    def get_global_function(self, name, temp = False, remove = True):
        if self.module and '.' in name:
            func = self.module.get_function(name)
            if func:
                return func
            newName = name[name.find('.') + 1:]
            func = self.module.get_function(newName)
            if func:
                return func
            
        if temp:
            globalFunctions = self.globalFunctionsTemp
        else:
            globalFunctions = self.globalFunctions
        if name in globalFunctions and globalFunctions[name]:
            func = globalFunctions[name][0]
            if remove:
                globalFunctions[name].remove(func)
            return func
        return None
    
    def get_global_variable(self, name, remove = True):
        if self.module and '.' in name:
            func = self.module.get_variable(name)
            if func:
                return func
            newName = name[name.find('.') + 1:]
            func = self.module.get_variable(newName)
            if func:
                return func

        if name in self.globalVariables and self.globalVariables[name]:
            variable = self.globalVariables[name][0]
            if remove:
                self.globalVariables[name].remove(variable)
            return variable
        return None
    
    def get_global_class(self, name, temp = False):
        if self.module and '.' in name:
            func = self.module.get_class(name)
            if func:
                return func
            newName = name[name.find('.') + 1:]
            func = self.module.get_class(newName)
            if func:
                return func

        if temp:
            globalClasses = self.globalClassesTemp
        else:
            globalClasses = self.globalClasses
        if name in globalClasses and globalClasses[name]:
            cl = globalClasses[name][0]
            globalClasses[name].remove(cl)
            return cl
        return None
        
    def add_bookmark(self, bm):
        self.objectDatabaseProperties.add_bookmark(bm)
    
    def get_start_row_in_file(self):
        return self.startRow_in_file
       
    def get_start_col_in_file(self):
        return self.startCol_in_file
    
    def add_html_calling_file(self, htmlContent):
        self.htmlCallingFiles.append(htmlContent)
       
    def get_html_calling_files(self):
        return self.htmlCallingFiles
         
    def init_range(self):
        global nr_first_range_unnamed_functions
        nr_first_range_unnamed_functions = 0
        self.current_statement_nr = -1
        
    def get_next_statement(self):
        self.current_statement_nr += 1
        return self.statements[self.current_statement_nr]
        
    def get_previous_statement(self):
        self.current_statement_nr -= 1
        return self.statements[self.current_statement_nr]

    def create_javascript_initialisation(self):
        
        if self.javascriptInitialisation:
            return self.javascriptInitialisation
        
        filename = self.file.get_path()
        if not filename.endswith('.js') and not filename.endswith('.jsx'):
            return self
        
        obj = cast.analysers.CustomObject()
        obj.set_type('CAST_HTML5_JavaScript_Initialisation')
        obj.set_name(self.get_name())
        obj.set_parent(self.get_kb_object())
        fullname = self.get_kb_object().guid + '/INIT'
        displayname = self.get_kb_object().fullname + '/INIT'
        obj.set_guid(fullname)
        obj.set_fullname(displayname)
        obj.save()
        obj.save_position(self.create_bookmark(self.file))
        self.javascriptInitialisation = obj
        create_link('callLink', self.get_kb_object(), obj, Bookmark(self.file, 1, 1, 1, 1))
        return obj

    def create_cast_objects(self, file, parent = None, name = None, kbObject = None):
        
        codeLinesComputed = False
        part = parent
        if not part:
            part = file
            
        if kbObject:
            self.kbObject = kbObject
            for bookmark in  self.objectDatabaseProperties.bookmarks:
                self.kbObject.save_position(bookmark)
            
        if not self.kbObject:
            
            self.kbObject = cast.analysers.CustomObject()
            n = name
            if not n:
                n = os.path.basename(file.get_path())
            self.kbObject.set_name(n)
            if n.lower().endswith('.jsx'):
                self.kbObject.set_type(self.config.objectTypes.jsxSourceCodeType)
            else:
                self.kbObject.set_type(self.config.objectTypes.sourceCodeType)
                 
            self.kbObject.set_parent(part)
            fullname = KbSymbol.get_kb_fullname(self)
            displayFullname = KbSymbol.get_display_fullname(self)
            self.kbObject.set_guid(fullname)
            self.kbObject.set_fullname(displayFullname)
            self.kbObject.save()
            
            maxCol = self.get_max_col_over(0)
            self.kbObject.save_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.complexity', self.complexity)
            self.kbObject.save_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.lengthOfTheLongestLine', maxCol)
            self.objectDatabaseProperties.checksum = self.tokens[0].get_code_only_crc()
            self.kbObject.save_property('checksum.CodeOnlyChecksum', self.objectDatabaseProperties.checksum)

            for bookmark in  self.objectDatabaseProperties.bookmarks:
                self.kbObject.save_position(bookmark)

        else:
            self.codeLines = self.get_line_count()
            try:
                self.kbObject.save_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.complexity', self.complexity)
                maxCol = self.get_max_col_over(0)
                self.kbObject.save_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.lengthOfTheLongestLine', maxCol)
                self.kbObject.save_property('CAST_HTML5_JavaScript_SourceCode_metrics.totalCodeLinesCount', self.codeLines)
            except:
                pass
            codeLinesComputed = True
            
        for statement in self.statements:
            statement.create_cast_objects(self.kbObject, self.config)

        if codeLinesComputed:
            self.kbObject.save_property('metric.CodeLinesCount', self.codeLines)

    def create_cast_links(self, parent, suspensionLinks):
            
        for resolution in self.get_resolutions():
            try:
                if resolution.linkType and resolution.callee.get_kb_object():
                    caller = self.create_javascript_initialisation()
                    create_link_internal(resolution.linkType, caller, resolution.callee, resolution.callee.create_bookmark(self.file))
            except:
                pass

        for statement in self.statements:
            statement.create_cast_links(self, self.config, suspensionLinks)
       
    def get_line_count(self, emptyLines = None):
        
        if self.lineCount >= 0:
            return self.lineCount
        if not self.tokens:
            self.lineCount = 0
            return 0
        
        try:
            lineCountIncludingComments = self.tokens[0].get_line_count()
        except:
            lineCountIncludingComments = 0
        self.lineCount = lineCountIncludingComments - self.tokens[0].get_comments_whole_line_count()
        
        if emptyLines:
            begin = self.get_begin_line()
            end = self.get_end_line()
            for line, count in emptyLines.items():
                if begin <= line and line <= end:
                    self.lineCount -= count
        return self.lineCount
            
    def get_comments_before_token(self, token):
        
        l = []
        for tok in self.tokens[0].children:
            if tok == token:
                break
            if is_token_subtype(tok.type, Comment):
                l.append(tok)
            else:
                l.clear()
        return l
            
    def get_header_comments(self, mustBeCorrected = True):
        
        comments = self.tokens[0].get_header_comments()
        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'
        return s
            
    def get_body_comments(self):
        
        comments = self.tokens[0].get_body_comments()
        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'
        return s
            
    def get_header_comments_line_count(self, mustBeCorrected = True):
        result = self.get_header_comments(mustBeCorrected).count('\n')
        return result
            
    def get_body_comments_line_count(self, includingFunctionHeaders = False):
        result = self.tokens[0].get_body_comments_line_count(includingFunctionHeaders)
        return result
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'JsContent ' + str(hex(id(self))) + ' {')
        StatementList.print(self, pad)
        print(' '.rjust(pad) + '}')

class AstList(AstToken):
    """
    A bracketed block.
    """
    def __init__(self, token, parent):
        AstToken.__init__(self, token, parent)
        self.values = [] # list of AstToken

    def get_values(self):
        
        return self.values
    
    def add_value(self, value):
        
        self.values.append(value)
    
    def get_children(self):
        return self.values
            
    def __repr__(self):
        
        return str(self.values)
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'AstList ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'values :')
        for value in self.values:
            value.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class ObjectValue(AstToken):
    """
    A curly bracketed block.
    """
    def __init__(self, token, parent):
        
        AstToken.__init__(self, token, parent)
        self.items = OrderedDict() # list of pairs of AstToken
        self.itemsList = [] # same as self.items to keep order, because visit must be made in good order

    def convert_crc(self):
        self.crc = self.get_code_only_crc()
        AstToken.convert_crc(self)
        
    def add_item(self, paramName, value):
        
        self.items[paramName] = value
        self.itemsList.append(value)
        if value:
            value.parent = self
    
    def get_item(self, name):
        
        for n, item in self.items.items():
            if isinstance(n, Identifier):
                if n.get_name() == name:
                    return item
            elif n == name:
                return item
        return None

    def get_value_fullname(self, value):

        key = None
        for n, item in self.items.items():
            if item == value:
                key = n
                break
        
        if not key:
            return None
        
        ovParent = self.parent
        if ovParent.is_assignment():
            return ovParent.get_left_operand().get_name() + '.' + key.get_name()

        return key
    
    def get_items(self):
        
        return self.itemsList
    
    def get_items_dictionary(self):
        
        return self.items
                
    def get_children(self):
        return self.itemsList
            
    def __repr__(self):
        
        try:
            return str(self.items)
        except:
            return 'self.items'
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'ObjectValue ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'items :')
        for key, item in self.items.items():
            print(' '.rjust(pad + 6) + 'key:')
            if isinstance(key, str):
                print(' '.rjust(pad + 9) + 'str:', str(key))
            else:
                key.print(pad + 9)
            print(' '.rjust(pad + 6) + 'value:')
            item.print(pad + 9)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

"""
Used for ObjectValue ({...}) which is the left operand of an assignment, as in :

let {
    title: englishTitle,// rename
    translations: [
        {
            title: localeTitle,// rename
        },
    ],
} = metadata;
"""
class ObjectDestructuration(ObjectValue):
    """
    A curly bracketed block on the left operand of an assignment.
    """
    def __init__(self, token, parent):
        ObjectValue.__init__(self, token, parent)
        
    def is_object_destructuration(self):
        return True

class Function(KbSymbol, StatementList):
    """
    A function.
    """
    def __init__(self, name, prefix, parent, token, file = None, isThis = False, emptyLines = None):
        
        StatementList.__init__(self, token, parent)
        self.isThis = isThis
        self.lineCount = -1
        self.complexity = 1
        self.kbObject = None
        self.lineCount = self.get_line_count(emptyLines)
        self.directlyCalled = False
        if isinstance(parent, JSFunctionCall):
            self.set_is_kb_object(False)
        else:
            self.set_is_kb_object(True)
        self.parameters = []
        if prefix and name:
            self.set_name(name, prefix + '.' + name, prefix + '.' + name)
        else:
            self.set_name(name, name, name)
        if prefix:
            self.prefix = prefix
        if prefix and prefix.startswith('this'):
            self.startsWithThis = True
        elif self.starts_with_this():
            self.startsWithThis = False
        self.file = file
        if prefix:
            if 'prototype' in prefix or 'statics' in prefix:
                self.isPrototype = True
        self.calls = [] # function call which points to this function
        self.codeLines = 0
        self.nextHtmlFragmentNumber = 0
        if not name or '_PARAM_' in name or (self.parent and self.parent.is_return_statement()):
            self.isAnonymous = True

    def get_max_col_over(self, minCol):
        if minCol > 0:
            return minCol
        return StatementList.get_max_col_over(self, minCol)

    def increment_complexity(self):
        self.complexity += 1

    def set_function_constructor(self):
        self.isFunctionConstructor = True
        
    def is_function_constructor(self):
        try:
            return self.isFunctionConstructor
        except:
            return False
    
    def add_call(self, fcall):
        self.calls.append(fcall)
        
    def get_calls(self):
        return self.calls
        
    def is_anonymous(self):
        try:
            return self.isAnonymous
        except:
            return False
        
    def get_next_html_fragment_number(self):
        return self.nextHtmlFragmentNumber
        
    def increment_next_html_fragment_number(self):
        self.nextHtmlFragmentNumber += 1
        return self.nextHtmlFragmentNumber
    
    def add_prototype_function(self, func):
        tbl = None
        try:
            tbl = self.prototypeFunctions
        except:
            tbl = {}
            self.prototypeFunctions = tbl
        name = func.get_name()
        if not name in tbl:
            tbl[name] = func
    
    def get_prototype_function(self, name):
        try:
            if name in self.prototypeFunctions:
                func = self.prototypeFunctions[name].parent.get_right_operand()
                if func.is_function():
                    return func
            return None
        except:
            return None

    def update_prototype_functions(self, ast):
        for name, func in ast.prototypeFunctions.items():
            f = self.get_prototype_function(name)
            if not f:
                self.add_prototype_function(func)

    def decrement_code_lines(self, nb):
        self.codeLines -= nb
        if self.codeLines < 0:
            self.codeLines = 0

    def has_prototype_resolution(self):
        try:
            return self.prototypeResolutions
        except:
            return False
        
    def set_parent(self, parent):
    
        StatementList.set_parent(self, parent)
        if isinstance(parent, JSFunctionCall):
            self.set_is_kb_object(False)
        else:
            self.set_is_kb_object(True)
    
    def convert_crc(self):
        self.crc = self.get_code_only_crc()
        StatementList.convert_crc(self)

    def is_context_container(self):
        return True
        
    def get_file(self):
        return self.file
    
    def get_prefix_internal(self):
        try:
            return self.prefix
        except:
            return None

    def set_prefix_internal(self, prefix):
        if prefix:
            self.prefix = prefix
        elif self.get_prefix_internal():
            del self.prefix
        
    def set_prefix(self, prefix):
        self.set_internal(prefix)
        if prefix and prefix.startswith('this'):
            self.startsWithThis = True
        elif self.starts_with_this():
            self.startsWithThis = False

    def starts_with_this(self):
        try:
            return self.startsWithThis
        except:
            False
    
    def prefix_starts_with(self, name):
        if not self.get_prefix_internal():
            return False
        return self.prefix.startswith(name)
    
    def prefix_ends_with(self, name):
        if not self.get_prefix_internal():
            return False
        return self.prefix.endswith(name)

    def prefix_contains(self, name):
        if not self.get_prefix_internal():
            return -1
        return self.prefix.find(name)

    def add_prototype_resolution(self, resolution):
        try:
            self.prototypeResolutions.append(resolution)
        except:
            self.prototypeResolutions = []
            self.prototypeResolutions.append(resolution)
        
    def is_prototype(self):
        try:
            return self.isPrototype
        except:
            return False

    def set_prototype_true(self):
        self.isPrototype = True
        
    def get_prefix(self):
        try:
            if not isinstance(self.prefix, str):
                return ''
        except:
            return ''        
        return self.prefix

    def get_fullname(self):
        if self.get_prefix_internal():
            return str(self.prefix) + '.' + str(self.name)
        else:
            return self.name
    
    def get_parameters(self):
        
        return self.parameters
    
    def add_parameter(self, param, rang = -1):
        
        self.parameters.append(param)
        param.parent = self
        
    def create_cast_objects(self, parent, config, createChildrenOnly = False):
        
        codeLinesComputed = False
        if not createChildrenOnly:
            if self.get_kb_object():
                function_object = self.kbObject
            else:         
                function_object = cast.analysers.CustomObject()
                self.kbObject = function_object
                function_object.set_name(self.name)
                function_object.set_type(config.objectTypes.functionType)
                function_object.set_parent(parent)
                function_object.set_guid(KbSymbol.get_kb_fullname(self))
                function_object.set_fullname(KbSymbol.get_display_fullname(self))
                function_object.save()
                function_object.save_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.complexity', self.complexity)
                maxCol = self.get_max_col_over(0)
                function_object.save_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.lengthOfTheLongestLine', maxCol)
                
                if self.is_anonymous():
                    function_object.save_property('CAST_HTML5_JavaScript_Function.anonymous', 1)
                else:
                    if not self.parent.is_object_value() and not self.get_prefix() and not self.calls:
                        function_object.save_property('CAST_HTML5_JavaScript_Object_Properties.unreferencedFunctionEnabled', 1)
                crc = self.tokens[0].get_code_only_crc()
                function_object.save_property('checksum.CodeOnlyChecksum', crc)
                if len(self.parameters) > 0:
                    function_object.save_property('CAST_HTML5_WithParameters.numberOfParameters', len(self.parameters))
                self.codeLines = self.get_line_count()
                codeLinesComputed = True
                headerCommentsLines = self.get_header_comments_line_count()
                if headerCommentsLines:
                    function_object.save_property('metric.LeadingCommentLinesCount', headerCommentsLines)
                    function_object.save_property('comment.commentBeforeObject', self.get_header_comments())
                bodyCommentsLines = self.get_body_comments_line_count()
                if bodyCommentsLines:
                    function_object.save_property('metric.BodyCommentLinesCount', bodyCommentsLines)
                    function_object.save_property('comment.sourceCodeComment', self.get_body_comments())
                file = self.parent
                while not isinstance(file, File) and not isinstance(file, HtmlContent) and not isinstance(file, Object):
                    file = file.parent
                if isinstance(file, HtmlContent):
                    file = file.get_file()
                elif isinstance(file, Object):
                    file =self.get_js_content().file
        
                function_object.save_position(Bookmark(file, self.get_begin_line(), self.get_begin_column(), self.get_end_line(), self.get_end_column()))

                if config.objectTypes.functionType == 'CAST_Javascript_ClientSide_Method':
                    function_object.save_property('CAST_Legacy_WithKeyProp.keyprop', 33554432)
                    function_object.save_property('CAST_Javascript_ClientSide_Method.HTML5', 1)
                
        if createChildrenOnly:            
            StatementList.create_cast_objects(self, parent, config)
        else:
            StatementList.create_cast_objects(self, function_object, config)
            
        if codeLinesComputed:
            function_object.save_property('metric.CodeLinesCount', self.codeLines)
            self.parent.decrement_code_lines(self.get_line_count())
        
    def create_cast_links(self, parent, config, suspensionLinks, createChildrenOnly = False):
        
        if createChildrenOnly:
            StatementList.create_cast_links(self, parent, config, suspensionLinks)
        else:
            StatementList.create_cast_links(self, self.kbObject, config, suspensionLinks)
            
    def get_line_count(self, emptyLines = None):
        
        if self.lineCount >= 0:
            return self.lineCount
        
        lineCountIncludingComments = self.tokens[0].get_line_count()
        self.lineCount = lineCountIncludingComments - self.get_header_comments_line_count(False) - self.get_body_comments_line_count()
        if emptyLines:
            begin = self.get_begin_line()
            end = self.get_end_line()
            for line, count in emptyLines.items():
                if begin <= line and line <= end:
                    self.lineCount -= count
        return self.lineCount
            
    def get_header_comments(self, mustBeCorrected = True):
        
        comments = []
        commentsComputed = False
        try:
            if self.parent.is_function_call_part():
                return ''
            elif mustBeCorrected and self.parent.is_assignment():
                if self.parent.parent.is_var_declaration():
                    token = self.parent.parent.tokens[0]
                else:
                    token = self.parent.tokens[0]
                try:
                    token = token.tokens[0]
                except:
                    pass
                comments = self.parent.get_comments_before_token(token)
                commentsComputed = True
        except:
            pass

        if not commentsComputed:
            comments = self.tokens[0].get_header_comments()
        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'
        return s
            
    def get_body_comments(self):
        
        comments = self.tokens[0].get_body_comments()
        
        # remove comments in function parameters
        if comments:
            for token in self.tokens[0].get_children():
                try:
                    if token.is_parenthesed_block():
                        for token2 in token.children:
                            if token2 == comments[0]:
                                comments.pop(0)
                except:
                    pass
        
        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'
        return s
            
    def get_header_comments_line_count(self, mustBeCorrected = True):
        result = self.get_header_comments(mustBeCorrected).count('\n')
        return result
            
    def get_body_comments_line_count(self):
        result = self.get_body_comments().count('\n')
        return result

    # Function
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        return []

    def evaluate_content_with_trace(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None):

        return StatementList.evaluate_with_trace(self, None, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter())

    def evaluate_return(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None):

        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 7, heap size = ' + str(len(objectsPassed)))
            return []

        if not self.statements:
            return []
        
        returnStatements = get_return_statements(self)
        if not returnStatements:
            return []
 
        results = []        
        for returnStatement in returnStatements:
            evs = returnStatement.evaluate(evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter())
            if evs:
                for ev in evs:
                    if not ev in results:
                        results.append(ev)
        return results
            
    def __repr__(self):
        
        result = "function('" + str(self.name) + "')"
        return result
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Function ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'parameters :')
        for param in self.parameters:
            param.print(pad + 6)
        StatementList.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class ArrowFunction(Function):
    """
    A function.
    """
    def __init__(self, name, prefix, parent, token, file = None, isThis = False, emptyLines = None):
        
        Function.__init__(self, name, prefix, parent, token, file, isThis, emptyLines)
            
    def is_arrow_function(self):
        return True
    
    def get_line_count(self, emptyLines = None):
        
        if self.lineCount >= 0:
            return self.lineCount
        
        try:
            lineCountIncludingComments = self.tokens[-1].get_line_count()
            self.lineCount = lineCountIncludingComments - self.get_header_comments_line_count() - self.get_body_comments_line_count()
            if emptyLines:
                begin = self.get_begin_line()
                end = self.get_end_line()
                for line, count in emptyLines.items():
                    if begin <= line and line <= end:
                        self.lineCount -= count
        except:
            self.lineCount = 1
        return self.lineCount

    def get_header_comments(self, mustBeCorrected = True):
        
        return '';
            
    def get_body_comments(self):
        
        comments = self.tokens[-1].get_body_comments()
        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'
        return s
            
    def get_header_comments_line_count(self, mustBeCorrected = True):
        result = self.get_header_comments(mustBeCorrected).count('\n')
        return result
            
    def get_body_comments_line_count(self):
        result = self.get_body_comments().count('\n')
        return result
            
    def __repr__(self):
        
        result = str(self.parameters) + " => '"
        return result

class FunctionCallPart(AstToken):

    def __init__(self, identifier, tokens):
        
        AstToken.__init__(self, tokens, None, identifier.get_name())
        self.identifier_call = identifier
        identifier.parent = self
        self.parameters = []
        # if fcall(a)(b1, b2)(c1, c2)
        # self.parameters contains a
        # self.other_parameter_sets[0] is a list and contains b1 and b2
        # self.other_parameter_sets[1] is a list and contains c1 and c2
        
    # FunctionCallPart
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 8, heap size = ' + str(len(objectsPassed)))
            return []

        if memberNames and self.identifier_call.get_fullname() == 'Object.assign':
            params = self.get_parameters()
            for param in params:
                if param.is_object_value():
                    # evaluate all members
                    valsMembers = [ [] for _ in memberNames ]
                    nuplesByAstNodes = {}
                    cmpt = 0
                    for memberN in memberNames:
                        if param.get_item(memberN):
                            valsMembers[cmpt] = param.get_item(memberN).evaluate_with_trace(None, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter, urlIncludingFcall)
                        else:
                            valsMembers[cmpt] = []
                        cmpt += 1
                        
                    # compare common ast_nodes to get pairs
                    if valsMembers and valsMembers[0]:
                        cmpt = 0
                        for memberN in memberNames:
                            for elt in valsMembers[cmpt]:
                                if elt.ast_nodes[-1] in nuplesByAstNodes:
                                    nuples = nuplesByAstNodes[elt.ast_nodes[-1]]
                                else:
                                    nuples = [ [] for _ in memberNames ]
                                    nuplesByAstNodes[elt.ast_nodes[-1]] = nuples
                                nuples[cmpt].append(elt)
                            cmpt += 1
                        
                        completeList = []
                        for value in nuplesByAstNodes.values():
                            l = []
                            for lst in value:
                                l.append(lst)
                            completeList.extend(itertools.product(*l))
                            
                        evaluationContext.values = []
                        for nuple in completeList:
                            ov = {}
                            cmpt = 0
                            for memberN in memberNames:
                                ov[memberN] = nuple[cmpt]
                                cmpt += 1
                            evaluationContext.values.append(ov)
                            
                        vals = evaluationContext.values
                        return vals
            
        if not memberNames:
            fname = self.identifier_call.get_name().lower()
        for param in self.parameters:
            if memberNames:
                if param.is_identifier():
                    vals = param.evaluate_with_trace(memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter, urlIncludingFcall)
                    if vals:
                        evaluationContext.values = []
                        for v in vals:
                            for memberN in memberNames:
                                v[memberN].ast_nodes.append(self)
                            evaluationContext.values.append(v)
                        vals = evaluationContext.values
                        return vals
            else:
                if param.is_function():
                    ev = param.evaluate_content_with_trace(evaluationContext, originalCaller, objectsPassed, charForUnknown, constants)
                    if ev:
                        return ev
                elif urlIncludingFcall and param.is_string() and 'url' in fname :
                    name = param.get_name()
                    if '/' in name and len(name) > 1:
                        return [ Value(name, param) ]
        return []

    def convert_crc(self):
        self.crc = self.get_code_only_crc()
        
    def add_parameter(self, parameter, rang = -1):
        if rang == -1:
            self.parameters.append(parameter)
        else:
            if not hasattr(self, 'other_parameter_sets'):
                self.other_parameter_sets = []

            if len(self.other_parameter_sets) <= rang:
                l = []
                self.other_parameter_sets.append(l)
            else:
                l = self.other_parameter_sets[rang]
            l.append(parameter)
        parameter.parent = self
        
    def get_identifier(self):
        
        return self.identifier_call
        
    def get_parameters(self):
        
        return self.parameters
            
    def get_name(self):
        return self.identifier_call.name

    def prefix_starts_with(self, name):
        if not self.identifier_call.get_prefix():
            return False
        return self.identifier_call.get_prefix().startswith(name)

    def prefix_ends_with(self, name):
        if not self.identifier_call.get_prefix():
            return False
        return self.identifier_call.get_prefix().endswith(name)

    def prefix_contains(self, name):
        if not self.identifier_call.get_prefix():
            return -1
        return self.identifier_call.get_prefix().find(name)
            
    def get_fullname(self):
        if self.identifier_call.get_prefix_internal():
            return str(self.identifier_call.prefix) + '.' + self.identifier_call.name
        else:
            return self.identifier_call.name
    
    def create_bookmark(self, _file):
        
        if len(self.parameters) > 0:
            return Bookmark(_file, self.identifier_call.get_begin_line(), self.identifier_call.get_begin_column(), self.parameters[-1].get_end_line(), self.parameters[-1].get_end_column())
        else:
            return Bookmark(_file, self.identifier_call.get_begin_line(), self.identifier_call.get_begin_column(), self.identifier_call.get_end_line(), self.identifier_call.get_end_column())

    def convert_ast_list_to_position(self):
        
        if len(self.parameters) > 0:
            self.position = Position(self.identifier_call.get_begin_line(), self.identifier_call.get_begin_column(), self.parameters[-1].get_end_line(), self.parameters[-1].get_end_column())
        else:
            self.position = Position(self.identifier_call.get_begin_line(), self.identifier_call.get_begin_column(), self.identifier_call.get_end_line(), self.identifier_call.get_end_column())
        self.convert_crc()

        try:
            del self.tokens
        except:
            pass

        self.identifier_call.convert_ast_list_to_position()
        for parameter in self.parameters:
            if isinstance(parameter, AstToken):
                parameter.convert_ast_list_to_position()

    def _get_code_only_crc(self, crc = 0):
        
        crc = self.identifier_call._get_code_only_crc(crc)
            
        for param in self.parameters:
            crc = param._get_code_only_crc(crc)
        return crc
        
    def get_code_only_crc(self, crc = 0):
        
        try:
            lastCrc = 0
            lastAst = None
            if len(self.parameters) == 0:
                crc = self.identifier_call.get_code_only_crc(crc)
                return crc
            else:
                lastCrc = crc
                lastAst = self.identifier_call
                crc = self.identifier_call._get_code_only_crc(crc)
                
            lastParam = None
            for param in self.parameters:
                if lastParam:
                    lastCrc = crc
                    lastAst = lastParam
                    crc = lastParam._get_code_only_crc(crc)
                lastParam = param
            if lastParam:
                crc = lastParam.get_code_only_crc(crc)
            elif lastAst:
                crc = lastAst.get_code_only_crc(lastCrc)
            else:
                crc = 0
        except:
            try:
                crc = self.crc
            except:
                crc = 0
        return crc

    def create_cast_objects(self, parent, firstKbParent, config):
        
        for parameter in self.get_all_parameters():
            try:
                parameter.create_cast_objects(parent, config)
            except:
                pass

    def create_cast_links(self, parent, firstKbParent, config, suspensionLinks):
        
        global self_resolve

        file =self.get_js_content().file
                        
        for parameter in self.get_all_parameters():
            if parameter.is_function():
                create_link_internal('callLink', firstKbParent, parameter.kbObject, parameter.create_bookmark(file))
            elif parameter.is_object_value():
                for item in parameter.get_items():
                    try:
                        if item.is_function():
                            create_link_internal('callLink', firstKbParent, item.kbObject, item.create_bookmark(file))
                    except:
                        pass
            elif parameter.is_identifier() and parameter.get_resolutions():
                for resolution in parameter.get_resolutions():
                    try:
                        if resolution.callee.is_function():
                            if isinstance(firstKbParent, File):
                                if resolution.callee.get_kb_object():
                                    create_link_internal('callLink', firstKbParent, resolution.callee.get_kb_object(), parameter.create_bookmark(file))
                                else:
                                    suspensionLinks.append(SuspensionLink('callLink', firstKbParent, resolution.callee, parameter.create_bookmark(file)))
                            else:
                                if resolution.callee.get_kb_object():
                                    create_link_internal('callLink', firstKbParent, resolution.callee.get_kb_object(), parameter.create_bookmark(file))
                                else:
                                    suspensionLinks.append(SuspensionLink('callLink', firstKbParent.kbObject, resolution.callee, parameter.create_bookmark(file)))
                    except:
                        pass
            parameter.create_cast_links(parent, config, suspensionLinks)

        if self.get_name() == 'require' and self.get_other_parameters() and self.identifier_call.get_resolutions():
                for resolution in self.identifier_call.get_resolutions():
                    try:
                        if isinstance(resolution.callee, cast.analysers.CustomObject):
                            create_link_internal('callLink', firstKbParent, resolution.callee, self.create_bookmark(file))
                    except:
                        pass

        if not self.identifier_call:
            return
        
        for resol in  self.identifier_call.get_resolutions():
            if isinstance(firstKbParent, File):
                create_link_internal(resol.linkType, firstKbParent, resol.callee.get_kb_object(), self.identifier_call.create_bookmark(file))
            else:
                if resol.linkType:
                    if isinstance(resol.callee, File):
                        create_link_internal(resol.linkType, firstKbParent, resol.callee, self.identifier_call.create_bookmark(file))
                    else:
                        if isinstance(firstKbParent, cast.analysers.CustomObject) and resol.callee:
                            if isinstance(resol.callee, cast.analysers.CustomObject):
                                create_link_internal(resol.linkType, firstKbParent, resol.callee, self.identifier_call.create_bookmark(file))
                            elif resol.callee.get_kb_object():
                                create_link_internal(resol.linkType, firstKbParent, resol.callee, self.identifier_call.create_bookmark(file))
                            else:
                                suspensionLinks.append(SuspensionLink(resol.linkType, firstKbParent, resol.callee, self.identifier_call.create_bookmark(file)))
                        elif firstKbParent.kbObject and resol.callee:
                            if type(resol.callee) is list:
                                pass
                            if isinstance(resol.callee, cast.analysers.CustomObject):
                                create_link_internal(resol.linkType, firstKbParent, resol.callee, self.identifier_call.create_bookmark(file))
                            elif resol.callee.get_kb_object():
                                create_link_internal(resol.linkType, firstKbParent, resol.callee.get_kb_object(), self.identifier_call.create_bookmark(file))
                            else:
                                suspensionLinks.append(SuspensionLink(resol.linkType, firstKbParent.kbObject, resol.callee, self.identifier_call.create_bookmark(file)))
                        else:
                            suspensionLinks.append(SuspensionLink(resol.linkType, firstKbParent.kbObject, resol.callee, self.identifier_call.create_bookmark(file)))
                    
    def get_all_parameters(self):
                    
        if not hasattr(self, 'other_parameter_sets'):
            return self.parameters

        l = []
        l.extend(self.parameters)
        
        for params in self.other_parameter_sets:
            l.extend(params)
        return l
                    
    def get_other_parameters(self):
                    
        if not hasattr(self, 'other_parameter_sets'):
            return []
        return self.other_parameter_sets
                    
    def get_children(self):

        bracketedExpr = None
        try:
            if self.identifier_call.is_bracketed_identifier():
                bracketedExpr = self.identifier_call.bracketedExpression
        except:
            pass
        
        if not self.get_other_parameters():
            if bracketedExpr:
                v = [ bracketedExpr ]
                v.extend(self.parameters)
                return v
            else:
                return self.parameters
        else:
            l = []
            l.extend(self.parameters)
            for k in self.get_other_parameters():
                l.extend(k)
            if bracketedExpr:
                v = [ bracketedExpr ]
                v.extend(l)
                return v
            else:
                return l

    def get_top_resolutions(self, topResolutions, alreadyPassed = []):

        if len(alreadyPassed) > 10000:
            return False
        alreadyPassed.append(self)
        return self.identifier_call.get_top_resolutions(topResolutions, alreadyPassed)

    def __repr__(self):
        
        return str(self.identifier_call.get_fullname_internal()) + '(' + str(self.parameters) + ')' + ('(' + str(self.get_other_parameters()) + ')' if self.get_other_parameters() else '')
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'FunctionCallPart ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'identifier_call :')
        self.identifier_call.print(pad + 6)
        print(' '.rjust(pad + 3) + 'parameters :')
        for param in self.parameters:
            param.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')
        
class FunctionCall(AstToken):
    """
    A function call. f() or f().g() ...
    """
    def __init__(self, identifier, token, parent, isLoop = False):
        
        AstToken.__init__(self, token, parent, identifier.name if identifier else '')
        self.functionCallParts = []
        self.isRequire = False
        self.isLoop = isLoop
        
    def copy_from(self, fcall):
        self.functionCallParts = fcall.functionCallParts
        self.isLoop = fcall.isLoop
        self.isRequire = fcall.isRequire
        self.name = fcall.name
        self.parent = fcall.parent
        self.tokens = fcall.tokens
    
    def convert_crc(self):
        self.crc = self.get_code_only_crc()

    def is_await(self):
        try:
            return self.isAwait
        except:
            return False
        
    def set_is_await(self, b):
        if b:
            self.isAwait = b
        
    def is_loop(self):
        return self.isLoop
    
    def is_require(self):
        return self.isRequire
    
    def add_function_call_part(self, identifier, tokens):
        
        callPart = FunctionCallPart(identifier, tokens)
        self.functionCallParts.append(callPart)
        callPart.parent = self
        
    def get_function_call_parts(self):
        
        return self.functionCallParts
    
    def create_cast_objects(self, parent, config):
        
        firstKbParent = self.parent
        while firstKbParent and not isinstance(firstKbParent, File) and not firstKbParent.is_kb_object():
            firstKbParent = firstKbParent.parent
        
        for functionCallPart in self.functionCallParts:
            functionCallPart.create_cast_objects(parent, firstKbParent, config)

    def create_cast_links(self, parent, config, suspensionLinks):
        
        firstKbParent = self.parent
        while firstKbParent and not isinstance(firstKbParent, File) and not firstKbParent.is_kb_object():
            firstKbParent = firstKbParent.parent
        
        for functionCallPart in self.functionCallParts:
            functionCallPart.create_cast_links(parent, firstKbParent, config, suspensionLinks)

    # FunctionCall
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 9, heap size = ' + str(len(objectsPassed)))
            return []
        for callPart in self.functionCallParts:
            ev = callPart.evaluate_with_trace(memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            if ev:
                return ev
        return []
    
    def get_children(self):
        return self.functionCallParts

    def get_top_resolutions(self, topResolutions, alreadyPassed = []):

        try:
            if len(alreadyPassed) > 10000:
                return False
            alreadyPassed.append(self)
            return self.functionCallParts[-1].get_top_resolutions(topResolutions, alreadyPassed)
        except:
            pass
            
    def __repr__(self):
        
        return str(self.functionCallParts)
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'FunctionCall ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'functionCallParts :')
        for part in self.functionCallParts:
            part.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class AnyExpression(AstToken):
    """
    expression which is not detailed
    """
    def __init__(self, token, parent):
        AstToken.__init__(self, token, parent, None)
        self.elements = []
        
    def get_elements(self):
        return self.elements
    
    def add_element(self, elt):
        
        self.elements.append(elt)

    def is_new_expression(self):
        try:
            firstElement = self.elements[0]
            if isinstance(firstElement, AstToken):
                try:
                    if firstElement.get_name() == 'new':
                        return True
                except:
                    pass
        except:
            return False
    
    def get_children(self):
        return self.elements
        
    def create_cast_objects(self, parent, config, createChildrenOnly = False):
        AstToken.create_cast_objects(self, parent, config)

    # AnyExpression
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 9, heap size = ' + str(len(objectsPassed)))
            return []
        for element in self.elements:
            try:
                ev = element.evaluate_with_trace(memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                if ev:
                    return ev
            except:
                pass
        return []
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'AnyExpression ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'elements :')
        for elt in self.elements:
            elt.print(pad + 6)
        AstToken.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class ImportStatement(AstStatement):
    """
    import 'react-select/dist/react-select.css';
    import React from 'react';
    import { isGeneratedId } from "devtools-source-map";
    import type { SymbolDeclaration, AstLocation } from "../reducers/types";
    import * as Actions from './img-context-menu-actions';
    """
    def __init__(self, token, parent, isType):
        
        AstStatement.__init__(self, token, parent)
        self.isType = isType
        self._from = None
        self._what = []
    
    def add_what(self, _what, _as = None):
        self._what.append((_what, _as))
    
    def set_from(self, _from):
        self._from = _from

    def get_what(self):
        return self._what

    def get_from(self):
        return self._from

    def is_type(self):
        return self.isType
    
    def is_import_statement(self):
        return True
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'ImportStatement ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + '_from :')
        print(' '.rjust(pad + 6) + str(self._from))
        print(' '.rjust(pad + 3) + '_what :')
        for elt in self._what:
            elt.print(pad + 6)
        AstStatement.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class AnyStatement(AstStatement):
    """
    statements which are not detailed
    """
    def __init__(self, token, parent):
        
        AstStatement.__init__(self, token, parent)
        self.elements = []
        
    def get_elements(self):
        return self.elements
    
    def add_element(self, func):
        
        self.elements.append(func)
    
    def is_new_statement(self):
        if not self.elements:
            return False
        
        try:
            firstElement = self.elements[0]
            if firstElement.get_name() == 'new':
                return True
        except:
            pass
        return False
    
    def is_return_statement(self):
        try:
            firstElement = self.elements[0]
            if firstElement.get_name() == 'return':
                return True
        except:
            pass
        return False
    
    def is_continue_statement(self):
        try:
            firstElement = self.elements[0]
            if firstElement.get_name() == 'continue':
                return True
        except:
            pass
        return False
    
    def is_export_statement(self):
        try:
            firstElement = self.elements[0]
            if firstElement.get_name() == 'export':
                return True
        except:
            pass
        return False

    def is_export_default_statement(self):
        if not self.elements:
            return False
        firstElement = self.elements[0]
        try:
            secondElement = self.elements[1]
            if firstElement.get_name() == 'export' and secondElement.get_name() == 'default':
                return True
        except:
            pass
        return False
    
    def is_break_statement(self):
        firstElement = self.elements[0]
        try:
            if firstElement.get_name() == 'break':
                return True
        except:
            pass
        return False
    
    def is_return_new_statement(self):
        if not self.is_return_statement():
            return False
        if len(self.elements) < 2:
            return False
        secondElement = self.elements[1]
        try:
            if secondElement.get_name() == 'new':
                return True
        except:
            pass
        return False
    
    def is_delete_statement(self):
        firstElement = self.elements[0]
        try:
            if firstElement.get_name() == 'delete':
                return True
        except:
            pass
        return False
    
    def is_list_forEach(self):
        
        if not self.elements:
            return False
        if not len(self.elements) == 2:
            return False
        
        try:
            if not self.elements[0].is_list():
                return False
            if self.elements[1].is_function_call() and self.elements[1].get_name() == 'forEach':
                return True
        except:
            return False

        return False

    def get_children(self):
        return self.elements

    # AnyStatement
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):

        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 10, heap size = ' + str(len(objectsPassed)))
            return []

        if not self.is_return_statement():
            return []

        s = ''
        try:
            for element in self.elements[1:]:
                evals = element.evaluate_with_trace(memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                if evals:
                    s += evals[0].value
        except:
            return [ Value(s, self) ]
        return [ Value(s, self) ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'AnyStatement ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'elements :')
        for elt in self.elements:
            elt.print(pad + 6)
        AstStatement.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class JSFunctionCall(AstStatement):
    """
    A JS function call. (function() {}).call(...)
    """
    def __init__(self, token, func, parent):
        
        AstStatement.__init__(self, token, parent)
        self.function = func
        self.parameters = []
        
    def is_top_function(self):
        return True
    
    def get_function(self):
        return self.function
    
    def get_parameters(self):
        return self.parameters
    
    def add_parameter(self, parameter, rang = -1):
        self.parameters.append(parameter)
        parameter.parent = self
        
    def create_cast_objects(self, parent, config):
        
        if self.function:
            self.function.create_cast_objects(parent, config, True)
        
    def create_cast_links(self, parent, config, suspensionLinks):
        
        if self.function:
            self.function.create_cast_links(parent, config, suspensionLinks, True)
    
    def get_children(self):
        return [ self.function ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'JSFunctionCall ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'function :')
        self.function.print(pad + 6)
        print(' '.rjust(pad + 3) + 'parameters :')
        for param in self.parameters:
            param.print(pad + 6)
        AstStatement.print(self, pad + 3)
        print(' '.rjust(pad) + '}')
    
class Define(AstStatement):
    """
    A define statement. define([...], function(..) {});
    """
    def __init__(self, token, parent):
        
        AstStatement.__init__(self, token, parent)
        self.function = None
        self.parameters = []
        
    def get_function(self):
        
        return self.function
    
    def get_parameters(self):
        
        return self.parameters
    
    def set_function(self, func):
        
        self.function = func
        
    def add_parameter(self, param, rang = -1):
        
        self.parameters.append(param)
        param.parent = self
    
    def get_children(self):
        return [ self.function ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Define ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'function :')
        self.function.print(pad + 6)
        print(' '.rjust(pad + 3) + 'parameters :')
        for param in self.parameters:
            param.print(pad + 6)
        AstStatement.print(self, pad + 3)
        print(' '.rjust(pad) + '}')
    
class Require(AstStatement):
    """
    A require statement. require([...], function(..) {});
    """
    def __init__(self, token, parent):
        
        AstStatement.__init__(self, token, parent)
        self.function = None
        self.parameters = []
        
    def get_function(self):
        
        return self.function
    
    def get_parameters(self):
        
        return self.parameters
    
    def set_function(self, func):
        
        self.function = func
        
    def add_parameter(self, param, rang = -1):
        
        self.parameters.append(param)
        param.parent = self
    
    def get_children(self):
        return [ self.function ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Require ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'function :')
        self.function.print(pad + 6)
        print(' '.rjust(pad + 3) + 'parameters :')
        for param in self.parameters:
            param.print(pad + 6)
        AstStatement.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class UnaryExpression(AstToken):
    """
    A unary expression.
    """
    def __init__(self, token, parent):
         
        AstToken.__init__(self, token, parent)
#         self.operand = None
         
    def get_operand(self):
        return self.operand
    
    def is_unary_expression(self):
        return True
    
#     def set_operand(self, operand):
#         self.operand = operand
    
    def get_children(self):
        return [ self.operand ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'UnaryExpression.operand :')
        try:
            self.operand.print(pad + 3)
        except:
            pass
        AstStatement.print(self, pad)

class BinaryExpression(AstToken):
    """
    A binary expression.
    """
    def __init__(self, token, parent):
         
        AstToken.__init__(self, token, parent)
        self.leftOperand = None
        self.rightOperand = None
#         self.operator = None
     
    def get_operator_text(self):
        try:
            return self.tokens[1].get_name()
        except:
            return ''
    
    def get_left_operand(self):
        return self.leftOperand
     
    def get_right_operand(self):
        return self.rightOperand
       
    def is_binary_expression(self):
        return True
    
    def set_left_operand(self, operand):
        self.leftOperand = operand
         
    def set_right_operand(self, operand):
        self.rightOperand = operand
    
    def get_children(self):
        return [ self.leftOperand, self.rightOperand ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'BinaryExpression.leftOperand :')
        self.leftOperand.print(pad + 3)
        print(' '.rjust(pad) + 'BinaryExpression.rightOperand :')
        self.rightOperand.print(pad + 3)
        AstToken.print(self, pad)

class EqualBinaryExpression(BinaryExpression):
    """
    A == binary expression.
    """
    def __init__(self, token, parent):
        BinaryExpression.__init__(self, token, parent)

    def is_equality_expression(self):
        return True

class NotEqualBinaryExpression(BinaryExpression):
    """
    A != binary expression.
    """
    def __init__(self, token, parent):
        BinaryExpression.__init__(self, token, parent)

    def is_equality_expression(self):
        return True

class IfTernaryExpression(AstToken):
    """
    A If ternary expression.
    """
    def __init__(self, token, parent):
         
        AstToken.__init__(self, token, parent)
        self.ifOperand = None
        self.thenOperand = None
        self.elseOperand = None
     
    def get_if_operand(self):
        return self.ifOperand
     
    def get_then_operand(self):
        return self.thenOperand
     
    def get_else_operand(self):
        return self.elseOperand

    def set_if_operand(self, operand):
        self.ifOperand = operand
         
    def set_then_operand(self, operand):
        self.thenOperand = operand
         
    def set_else_operand(self, operand):
        self.elseOperand = operand
         
    def is_if_ternary_expression(self):
        return True
    
    def get_children(self):
        return [ self.ifOperand, self.thenOperand, self.elseOperand ]

    # IfTernaryExpression
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 11, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)
        """
        Evaluates an identifier defined in the context parameter when we go through an If ternary expression
        Ex: var a = 'a';
            f(... ? a + 'b' : a + 'c');
        On last line, expression can be evaluated to 'ab' or 'ac'
        """
        try:
            # we save evaluationContext values in initial value ('a' in our example):
            if evaluationContext:
                initialValues = evaluationContext.values
            else:
                initialValues = []
            
            ifBlockVals = None
            elseBlockVals = None
            
            if self.thenOperand:
                newObjectsPassed = list(objectsPassed)
                ifBlockVals = self.thenOperand.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            if self.elseOperand:
                newObjectsPassed = list(objectsPassed)
                elseBlockVals = self.elseOperand.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            else:
                elseBlockVals = initialValues
                
            vals = ifBlockVals
            for elseBlockVal in elseBlockVals:
                if not elseBlockVal in vals:
                    vals.append(elseBlockVal)
                
            return vals
        except:
            return []

    def __repr__(self):
            return 'IfTernaryExpression'
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'IfTernaryExpression.ifOperand :')
        self.ifOperand.print(pad + 3)
        print(' '.rjust(pad) + 'IfTernaryExpression.thenOperand :')
        self.thenOperand.print(pad + 3)
        print(' '.rjust(pad) + 'IfTernaryExpression.elseOperand :')
        self.elseOperand.print(pad + 3)
        AstToken.print(self, pad)

class AdditionExpression(BinaryExpression):
    """
    An addition expression.
    self.shortForm = True if addition is of "+=" form (expression as a statement)
    """
    def __init__(self, token, parent, shortForm = False):
         
        BinaryExpression.__init__(self, token, parent)
        self.shortForm = shortForm

    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 12, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)
        """
        Evaluates an identifier defined in a context parameter when in addition
        """
        try:
            assignToCaller = False
            leftEvaluationValues = []
            rightEvaluationValues = []
            if self.leftOperand:
                if evaluationContext:
                    # if left operand has the same definition of callee in context
                    leftCallees = self.leftOperand.get_resolutions_callees()
                    if self.leftOperand.get_resolutions() and evaluationContext.callee in leftCallees:
                        if self.shortForm:
                            assignToCaller = True
                        leftEvaluationValues = evaluationContext.values
                    # if left operand has not the same definition of callee in context
                    else:
                        newObjectsPassed = list(objectsPassed)
                        leftCallees = self.leftOperand.get_resolutions_callees()
                        if self.shortForm and evaluationContext and leftCallees:
                            same = False
                            for leftCallee in leftCallees:
                                if leftCallee == evaluationContext.callee:
                                    same = True
                                    break
                            if not same:
                                return []
                        leftEvaluationValues = self.leftOperand.evaluate_with_trace(memberNames, None, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                else:
                    newObjectsPassed = list(objectsPassed)
                    leftEvaluationValues = self.leftOperand.evaluate_with_trace(memberNames, None, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            if self.rightOperand:
                # if right operand has the same definition of callee in context
                rightCallees = self.rightOperand.get_resolutions_callees()
                if evaluationContext and self.rightOperand.get_resolutions() and evaluationContext.callee in rightCallees:
                    rightEvaluationValues = evaluationContext.values
                else:
                    newObjectsPassed = list(objectsPassed)
                    rightEvaluationValues = self.rightOperand.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)

            # we compute the addition and put the result in values
            values = []            
            if leftEvaluationValues:
                if rightEvaluationValues:
                    if len(leftEvaluationValues)*len(rightEvaluationValues) < 10000:    # avoid explosion
                        for i in range(len(leftEvaluationValues)):
                            for j in range(len(rightEvaluationValues)):
                                if not Value.string_is_in_list(leftEvaluationValues[i].value + rightEvaluationValues[j].value, values):
                                    values.append(Value(leftEvaluationValues[i].value + rightEvaluationValues[j].value, leftEvaluationValues[i].ast_nodes + [ self ] + rightEvaluationValues[j].ast_nodes ))
                else:
                    values = leftEvaluationValues
            else:
                if rightEvaluationValues:
                    values = rightEvaluationValues
                
            if assignToCaller:
                evaluationContext.values = []
                if values:
                    for v in values:
                        if not v.is_in_list(evaluationContext.values):
                            evaluationContext.values.append(v)
                values = evaluationContext.values
            return values
        except:
            return []
         
    def is_addition_expression(self):
        return True
    
    def is_short_form(self):
        return self.shortForm
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'AdditionExpression ' + str(hex(id(self))) + ' {')
        BinaryExpression.print(' '.rjust(pad + 3))
        print(' '.rjust(pad) + '}')

class OrExpression(BinaryExpression):
    """
    An || expression.
    """
    def __init__(self, token, parent):
         
        BinaryExpression.__init__(self, token, parent)
         
    def is_or_expression(self):
        return True


    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 12, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)

        try:
            assignToCaller = False
            leftEvaluationValues = []
            rightEvaluationValues = []
            if self.leftOperand:
                if evaluationContext:
                    # if left operand has the same definition of callee in context
                    leftCallees = self.leftOperand.get_resolutions_callees()
                    if self.leftOperand.get_resolutions() and evaluationContext.callee in leftCallees:
                        if self.shortForm:
                            assignToCaller = True
                        leftEvaluationValues = evaluationContext.values
                    # if left operand has not the same definition of callee in context
                    else:
                        newObjectsPassed = list(objectsPassed)
#                         leftCallees = self.leftOperand.get_resolutions_callees()
                        leftEvaluationValues = self.leftOperand.evaluate_with_trace(memberNames, None, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                else:
                    newObjectsPassed = list(objectsPassed)
                    leftEvaluationValues = self.leftOperand.evaluate_with_trace(memberNames, None, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            if self.rightOperand:
                # if right operand has the same definition of callee in context
                rightCallees = self.rightOperand.get_resolutions_callees()
                if evaluationContext and self.rightOperand.get_resolutions() and evaluationContext.callee in rightCallees:
                    rightEvaluationValues = evaluationContext.values
                else:
                    newObjectsPassed = list(objectsPassed)
                    rightEvaluationValues = self.rightOperand.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)

            # we compute the addition and put the result in values
            values = []
            if leftEvaluationValues:
                values.extend(leftEvaluationValues)
            if rightEvaluationValues:
                values.extend(rightEvaluationValues)
                
            if assignToCaller:
                evaluationContext.values = []
                if values:
                    for v in values:
                        if not v in evaluationContext.values:
                            evaluationContext.values.append(v)
                values = evaluationContext.values
            return values
        except:
            return []
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'OrExpression ' + str(hex(id(self))) + ' {')
        BinaryExpression.print(' '.rjust(pad + 3))
        print(' '.rjust(pad) + '}')

class InExpression(BinaryExpression):
    """
    A in expression.
    """
    def __init__(self, token, parent):
         
        BinaryExpression.__init__(self, token, parent)
         
    def is_in_expression(self):
        return True
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'InExpression ' + str(hex(id(self))) + ' {')
        BinaryExpression.print(' '.rjust(pad + 3))
        print(' '.rjust(pad) + '}')

class NotExpression(UnaryExpression):
    """
    A not expression.
    """
    def __init__(self, token, parent):
         
        UnaryExpression.__init__(self, token, parent)
         
    def is_not_expression(self):
        return True
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'NotExpression ' + str(hex(id(self))) + ' {')
        UnaryExpression.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class VarDeclaration(AstStatement):
    """
    A var declaration.
    var a = 1, b, d = function() {};
    """
    def __init__(self, token, parent, isLet = False, isConst = False):
        
        AstStatement.__init__(self, token, parent)
        self.elements = []  # an element is an identifier or assignment
        self.isLet = isLet
        self.isConst = isConst

    def is_var_declaration(self):
        return True

    def is_let_declaration(self):
        return self.isLet

    def is_const_declaration(self):
        return self.isConst
    
    def is_assignment(self):
        if self.elements:
            try:
                return self.elements[0].is_assignment()
            except:
                return False
        return False
       
    def get_elements(self):
        return self.elements
    
    def get_left_operand(self):
        if self.is_assignment():
            return self.elements[0].get_left_operand()
        return None
        
    def get_right_operand(self):
        if self.is_assignment():
            return self.elements[0].get_right_operand()
        return None
        
    def add_element(self, elt):
        self.elements.append(elt)
    
    def get_children(self):
        return self.elements
    
    # VarDeclaration
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 13, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)
        if self.elements:
            vals = []
            for element in self.elements:
                newObjectsPassed = list(objectsPassed)
                vals = element.evaluate_with_trace(memberNames, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
            return vals    

    def print(self, pad = 0):
        print(' '.rjust(pad) + 'VarDeclaration {')
        print(' '.rjust(pad + 3) + 'elements :')
        for element in self.elements:
            element.print(pad + 6)
        print(' '.rjust(pad) + '}')

class Assignment(AstStatement):
    """
    An assignment.
    """
    def __init__(self, token, parent, isVar = False, exported = False):
        
        AstStatement.__init__(self, token, parent)
        self.leftOperand = None
        self.rightOperand = None
        if isVar:
            self.isVar = isVar
        if exported:
            self.isExported = True
      
    def get_current_assignment(self):
        return self
    
    def set_is_var(self):
        self.isVar = True
    
    def is_var(self):
        try:
            return self.isVar
        except:
            return False
    
    def is_exported(self):
        try:
            return self.isExported
        except:
            return False
        
    def get_left_operand(self):
        return self.leftOperand
    
    def get_right_operand(self):
        return self.rightOperand
       
    # Assignment 
    def evaluate_with_trace(self, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None, urlIncludingFcall = False):
        if evalCounter:
            if evalCounter.isOver():
                return []
        if not objectsPassed:
            objectsPassed = []
        if self in objectsPassed:
            if evalCounter:
                evalCounter.increment()
            cast.analysers.log.debug('Object already passed in evaluation 14, heap size = ' + str(len(objectsPassed)))
            return []
        objectsPassed.append(self)
        """
        Evaluates an identifier when in an assignment
        """
        try:
            if memberNames:
                if self.rightOperand and self.rightOperand.is_object_value():
                    ret = []
                    for memberN in memberNames:
                        if self.rightOperand.get_item(memberN):
                            vals = self.rightOperand.get_item(memberN).evaluate_with_trace(None, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter, urlIncludingFcall)
                            if vals:
                                evaluationContext.values = []
                                for v in vals:
                                    v.ast_nodes.append(self)
                                    ov = {}
                                    ov[memberN] = v
                                    evaluationContext.values.append(ov)
                                ret.extend(evaluationContext.values)
                    return ret
                         
                if self.leftOperand and self.leftOperand.is_identifier() and self.leftOperand.get_prefix_internal() and self.leftOperand.get_prefix_internal() == originalCaller.get_name(): 
                    for memberN in memberNames:
                        if self.leftOperand.get_name() == memberN:
                            vals = self.rightOperand.evaluate_with_trace(None, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter, urlIncludingFcall)
                            if vals:
                                evaluationContext.values = []
                                for v in vals:
                                    ov = {}
                                    ov[memberN] = v
                                    v.ast_nodes.append(self)
                                    evaluationContext.values.append(ov)
                                vals = evaluationContext.values
                            return vals
                 
                return self.rightOperand.evaluate_with_trace(memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter, urlIncludingFcall)
            else:
                leftOperand = self.get_left_operand()
                if leftOperand != evaluationContext.callee:
                    if not leftOperand.get_resolutions():
                        return []
                if leftOperand != evaluationContext.callee:
                    leftCallees = leftOperand.get_resolutions_callees()
                    if not evaluationContext.callee in leftCallees:
                        return []
                
                vals = self.get_right_operand().evaluate_with_trace(memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter if evalCounter else EvaluationCounter(), urlIncludingFcall)
                if vals:
                    evaluationContext.values = []
                    for v in vals:
                        if not v in evaluationContext.values:
                            v.ast_nodes.append(self)
                            evaluationContext.values.append(v)
                    vals = evaluationContext.values
                    return vals
                return []
        except:
            return []

    def is_part_of_var_declaration(self):
        return self.is_var()
    
    def set_left_operand(self, operand):
        self.leftOperand = operand
        
    def set_right_operand(self, operand):
        self.rightOperand = operand
        self.tokens.extend(operand.tokens)
    
    def get_children(self):
        return [ self.leftOperand, self.rightOperand ]
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Assignment {')
        print(' '.rjust(pad + 3) + 'leftOperand :')
        self.leftOperand.print(pad + 6)
        print(' '.rjust(pad + 3) + 'rightOperand :')
        self.rightOperand.print(pad + 6)
        AstStatement.print(self, pad)
        print(' '.rjust(pad) + '}')
        
class SymbolLink:
     
    def __init__(self):
         
        self.type = None
        self.caller = None
        self.callee = None
        self.bookmark = None

class ObjectDatabaseProperties:
    
    def __init__(self):
        self.bookmarks = []
        self.checksum = 0
        self.codeLinesCount = 0
        self.nbEmptyLines = 0
        self.headerCommentLinesCount = 0
        self.bodyCommentLinesCount = 0
        self.headerComment = None
        self.bodyComment = None
        
    def add_bookmark(self, bm):
        self.bookmarks.append(bm)

class IdentifierToResolve:
    
    def __init__(self, ident, caller, resolvedPrefix, bookmark, linkType):
        self.identifier = ident
        self.caller = caller
        self.linkType = linkType
        self.resolvedPrefix = resolvedPrefix
        self.bookmark = bookmark

    def __repr__(self):
        return str(self.linkType) + ', ' + str(self.caller) + ', ' + str(self.identifier) 

class Violation:
    
    def __init__(self, metamodelProperty, bookmark, artifactObject):
        self.metamodelProperty = metamodelProperty
        self.bookmark = bookmark
        self.artifactObject = artifactObject
        
class Violations:
    
    def __init__(self):
        
        self.violations = []

    def add_violation(self, metamodelProperty, bookmark, function):
        self.violations.append(Violation(metamodelProperty, bookmark, function))
        
    def add_querySelectorAll_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUsingQuerySelectorAll.numberOfQuerySelectorAllCalls', bookmark, function)
        
    def add_function_call_in_termination_loop_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidFunctionCallInTerminationLoop.numberOfFunctionCallsInTerminationLoop', bookmark, function)
        
    def add_for_in_loop_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidForInLoop.numberOfForInLoop', bookmark, function)
        
    def add_break_in_for_loop_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidBreakInForLoop.numberOfBreakInForLoop', bookmark, function)
        
    def add_forEach_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidForEach.numberOfForEach', bookmark, function)
        
    def add_WebSocketInsideLoop_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidWebSocketInsideLoop.numberOfWebSocketInsideLoop', bookmark, function)
        
    def add_XMLHttpRequestInsideLoop_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidXMLHttpRequestInsideLoop.numberOfXMLHttpRequestInsideLoop', bookmark, function)
        
    def add_tooMuchDotNotationInLoop_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidTooMuchDotNotationInLoop.numberOfTooMuchDotNotationInLoop', bookmark, function)
        
    def add_webSQLDatabase_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUsingWebSQLDatabases.numberOfWebSQLDatabaseAccesses', bookmark, function)
        
    def add_javaScriptBlockingPageLoading_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidJavaScriptBlockingPageLoading.numberOfJavaScriptBlockingPageLoading', bookmark, htmlSourceCode)
        
    def add_markupWithFormAndFormAction_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUsingMarkupWithFormAndFormAction.numberOfMarkupWithFormAndFormAction', bookmark, htmlSourceCode)
        
    def add_IdAttributesAndSubmitForForms_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidIdAttributesAndSubmitForForms.numberOfIdAttributesAndSubmitForForms', bookmark, htmlSourceCode)
        
    def add_autofocusWithOnfocus_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidAutofocusWithOnfocus.numberOfAutofocusWithOnfocus', bookmark, htmlSourceCode)
        
    def add_autofocusWithOnblur_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidAutofocusWithOnblur.numberOfAutofocusWithOnblur', bookmark, htmlSourceCode)
        
    def add_videoPosterAttribute_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidVideoPosterAttribute.numberOfVideoPosterAttribute', bookmark, htmlSourceCode)
        
    def add_javascriptOrExpressionInCss_violation(self, cssSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidJavascriptOrExpressionInCss.numberOfJavascriptOrExpressionInCss', bookmark, cssSourceCode)
        
    def add_HostingHTMLCodeInIframeSrcdoc_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidHostingHTMLCodeInIframeSrcdoc.numberOfHostingHTMLCodeInIframeSrcdoc', bookmark, htmlSourceCode)
        
    def add_onscrollWithAutofocusInput_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUsingOnscrollEventWithAutofocusInput.numberOfOnscrollEventWithAutofocusInput', bookmark, htmlSourceCode)
        
    def add_functionsInsideLoops_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidFunctionsInsideLoops.numberOfFunctionsInsideLoops', bookmark, htmlSourceCode)
        
    def add_deleteWithNoObjectProperties_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidDeleteWithNoObjectProperties.numberOfDeleteWithNoObjectProperties', bookmark, htmlSourceCode)
        
    def add_iframeInsideATag_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidIframeInsideATag.numberOfIframeInsideATag', bookmark, htmlSourceCode)
        
    def add_setDataInOndragstartWithDraggableTrue_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidSetDataInOndragstartWithDraggableTrue.numberOfSetDataInOndragstartWithDraggableTrue', bookmark, htmlSourceCode)
        
    def add_oninputInBodyContainingInputAutofocus_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidOninputInBodyContainingInputAutofocus.numberOfOninputInBodyContainingInputAutofocus', bookmark, htmlSourceCode)
        
    def add_sourceTagInVideoAudioWithEventHandler_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidSourceTagInVideoOrAudioWithEventHandler.numberOfSourceTagInVideoOrAudioWithEventHandler', bookmark, htmlSourceCode)
        
    def add_dirnameInUserGeneratedContent_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidWhiteListingDirnameAttribute.numberOfWhiteListingDirnameAttribute', bookmark, htmlSourceCode)
        
    def add_importWithExternalURI_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidImportWithExternalURI.numberOfImportWithExternalURI', bookmark, htmlSourceCode)
        
    def add_autocomplete_on_violation(self, htmlSourceCode, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidEnablingAutocompleteOn.numberOfAutocompleteOn', bookmark, htmlSourceCode)
        
    def add_deleteOnArray_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidDeleteOnArrays.numberOfDeleteOnArrays', bookmark, function)
        
    def add_documentAll_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidDocumentAll.numberOfDocumentAll', bookmark, function)
        
    def add_eval_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUsingEval.numberOfEval', bookmark, function)
        
    def add_setTimeout_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUsingSetTimeout.numberOfSetTimeout', bookmark, function)
        
    def add_setInterval_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUsingSetInterval.numberOfSetInterval', bookmark, function)
        
    def add_switch_no_default_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidMissingDefaultInSwitch.numberOfSwitchNoDefault', bookmark, function)
        
    def add_console_log_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUsingConsoleLog.numberOfConsoleLog', bookmark, function)
        
    def add_unsafe_singleton_class_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUnsafeSingleton.numberOfUnsafeSingleton', bookmark, function)
        
    def add_superclass_knowing_subclass_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidSuperclassKnowingSubclass.numberOfSuperclassKnowingSubclass', bookmark, function)
        
    def add_function_constructor_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidJavascriptFunctionConstructor.numberOfJavascriptFunctionConstructor', bookmark, function)
        
    def add_empty_catch_block_violation(self, function, bookmark):
#         self.add_violation('CAST_DotNet_Metric_AvoidEmptyCatchBlocks.number', bookmark, function)
        self.add_violation('CAST_HTML5_Metric_AvoidEmptyCatchBlocks.numberOfEmptyCatchBlocks', bookmark, function)
        
    def add_empty_finally_block_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidEmptyFinallyBlocks.numberOfEmptyFinallyBlocks', bookmark, function)
        
    def add_return_in_finally_block_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidReturnInFinallyBlock.numberOfReturnInFinallyBlock', bookmark, function)
        
    def add_hardcoded_network_resource_name_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidHardcodedNetworkResourceNames.numberOfHardcodedNetworkResourceNames', bookmark, function)
        
    def add_database_direct_access_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidDatabaseDirectAccess.numberOfDatabaseDirectAccess', bookmark, function)
        
    def add_cookie_without_setting_httpOnly_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidCookieWithoutHttpOnly.numberOfCookieWithoutHttpOnly', bookmark, function)
        
    def add_unsecured_cookie_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidUnsecuredCookie.numberOfUnsecuredCookie', bookmark, function)
        
    def add_overly_broad_path_cookie_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidOverlyBroadPathCookie.numberOfOverlyBroadPathCookie', bookmark, function)
        
    def add_overly_broad_domain_cookie_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidOverlyBroadDomainCookie.numberOfOverlyBroadDomainCookie', bookmark, function)
        
    def add_json_parse_stringify_without_try_catch_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_UseJSONParseAndStringifyWithoutTryCatch.numberOfJSONParseAndStringifyWithoutTryCatch', bookmark, function)
        
    def add_hardcoded_password_violation(self, function, bookmark):
        self.add_violation('CAST_HTML5_Metric_AvoidHardcodedPassword.numberOfHardcodedPassword', bookmark, function)
        
    def save(self):
                
        for violation in self.violations:
            if not violation.artifactObject:
                cast.analysers.log.debug('Internal issue in Violations.save: NULL object')
                continue
            kbObject = violation.artifactObject.get_kb_object()
            if kbObject:
                kbObject.save_violation(violation.metamodelProperty, violation.bookmark)
        
class SuspensionLink:
    
    def __init__(self, _type, callerKbObject, callee, bookmark):
        self.type = _type
        self.callerKbObject = callerKbObject
        self.callee = callee
        self.bookmark = bookmark
        
def decode_c_out(coutPart):
    
    # decode <c:out value="/product/${product.id}"/>
    value = ''
    index = coutPart.find('"')
    index2 = coutPart.rfind('"')
    if index >= 0 and index2 >= 0 and index != index2:
        value = coutPart[index + 1:index2]
    if not value:
        return value
    
    index = 0
    index2 = 0
    while index >= 0 and index2 >= 0:
        index = value.find('${')
        index2 = value.find('}', index)
        if index >= 0 and index2 >= 0:
            value = value[:index] + '{}' + value[index2 + 1:]
        else:
            break
    return value

def evaluate_url_string(url):

        # If evaluation gives something like that product/<c:out value="${product.id}"/>/somethingelse,
        # then replace <c:out value="${product.id}"/> with "{}"

        # If evaluation gives something like that product/<c:out value="/product/${product.id}"/>/somethingelse,
        # then replace <c:out value="/product/${product.id}"/> with "/product/{}"
        
        # Same with <c:url
        value = url
        if '<c:' in value and '>' in value:
            index = 0
            index2 = 0
            while index >= 0 and index2 >= 0:
                index = value.find('<c:')
                index2 = value.find('>', index)
                coutPart = value[index:index2]
                res = decode_c_out(coutPart)
                if index >= 0 and index2 >= 0:
                    value = value[:index] + res + value[index2 + 1:]
                else:
                    break

        
        value = value.strip()
        return value

def add_ast_call(urls, fcall, astCallers):
    
    if astCallers == None:
        return
    
    if not urls:
        astCallers.append(None)
    elif type(urls) is str:
        astCallers.append(fcall)
    elif urls:
        for _ in urls:
            astCallers.append(fcall)

global_configJsonObjectByRootDir = None

def set_nodejs_config(configJsonObjectByRootDir):
    global global_configJsonObjectByRootDir
    global_configJsonObjectByRootDir = configJsonObjectByRootDir

def get_nodejs_config(astNode):
        
        if not global_configJsonObjectByRootDir:
            return None
        try:
            nodeFile = os.path.normpath(os.path.dirname(astNode.get_file().get_path()))
            cmpt = 0
            while cmpt < 50 and nodeFile and not nodeFile in global_configJsonObjectByRootDir:
                nodeFile = os.path.normpath(os.path.dirname(nodeFile))
                cmpt += 1
            if cmpt < 50 and nodeFile:
                return global_configJsonObjectByRootDir[nodeFile]
            else:
                return None
        except:
            return None
    
def get_uri_evaluation(uriToEvaluate, characterForUnknown = '{}', astCalls = None, _constants = None):
       
    global global_configJsonObjectByRootDir
    if _constants:
        constants = _constants
    elif global_configJsonObjectByRootDir:
        constants = get_nodejs_config(uriToEvaluate)
    else:
        constants = None
    
    values = []
    if astCalls != None:
        astCallsInitial = []
    else:
        astCallsInitial = None
    if isinstance(uriToEvaluate, str):
        values.append(uriToEvaluate)
        if astCallsInitial != None:
            astCallsInitial.append(None)
    elif isinstance(uriToEvaluate, AstString):
        evs = uriToEvaluate.evaluate(None, None, None, characterForUnknown, constants, None, True)
        if evs:
            values.extend(evs)
        if astCallsInitial != None:
            for _ in evs:
                astCallsInitial.append(None)
    else:
        try:
            if uriToEvaluate.is_function_call():
                callPart0 = uriToEvaluate.get_function_call_parts()[0]
                if callPart0.parameters:
                    uri = callPart0.parameters[0].evaluate(None, None, None, characterForUnknown, constants, None, True)
                    if type(uri) == str:
                        values.append(uri)
                    elif uri:
                        values.extend(uri)
                    add_ast_call(uri, None, astCallsInitial)
                else:
                    uri = None
                    values.append(None)
                    add_ast_call(uri, None, astCallsInitial)
            else:
                servicesCreated = False
                if uriToEvaluate.is_identifier() and len(uriToEvaluate.get_resolutions()) == 1:
                    callee = uriToEvaluate.resolutions[0].callee
                    if callee.parent and callee.parent.is_function() and callee in callee.parent.parameters:
                        servicesCreated = True
                        try:
                            _vals = uriToEvaluate.evaluate(None, None, None, characterForUnknown, constants, None, True)
                            evs = uriToEvaluate.evaluate_with_trace(None, None, None, None, characterForUnknown, constants)
                            vals = []
                            for _ev in evs:
                                vals.append(_ev.value)
                                if astCallsInitial != None:
                                    firstFunctionCallPart = None
                                    for astNode in _ev.ast_nodes:
                                        try:
                                            if astNode.is_function_call_part():
                                                firstFunctionCallPart = astNode
                                                break
                                        except:
                                            pass
                                    if firstFunctionCallPart:
                                        astCallsInitial.append(firstFunctionCallPart)
                                    else:
                                        if _ev.ast_nodes:
                                            astCallsInitial.append(_ev.ast_nodes[-1])
                                        else:
                                            astCallsInitial.append(None)
                            values.extend(vals)
                        except:
                            pass
                if not servicesCreated:
                    values = uriToEvaluate.evaluate(None, None, None, characterForUnknown, constants, None, True)
                    if astCallsInitial != None:
                        astCallsInitial.clear()
                        add_ast_call(values, None, astCallsInitial)
        except:
            return []

    if not values:
        return []
    
    rets = []
    j = -1
    for uri in values:
            j += 1
            # decoding <s:url action="vincularEspecieCategoriaAnimalFasesCriacao" method="excluir"/>
            if uri.startswith('<') and uri.endswith('/>') and 'action' in uri and 'method' in uri:
                index1 = uri.find('=', uri.find('action'))
                index2 = uri.find('=', uri.find('method'))
                if index1 != index2 and index1 > 0 and index2 > 0:
                    action = ''
                    method = ''
                    
                    beginAction = uri.find('"', index1)
                    endAction = -1
                    if beginAction < 0:
                        beginAction = uri.find("'", index1)
                        if beginAction > 0:
                            endAction = uri.find("'", beginAction + 1)
                    else:
                        endAction = uri.find('"', beginAction + 1)
                    if beginAction > 0 and endAction > 0:
                        action = uri[beginAction + 1: endAction]
           
                    beginMethod = uri.find('"', index2)
                    endMethod = -1
                    if beginMethod < 0:
                        beginMethod = uri.find("'", index2)
                        if beginMethod > 0:
                            endMethod = uri.find("'", beginMethod + 1)
                    else:
                        endMethod = uri.find('"', beginMethod + 1)
                    if beginMethod > 0 and endMethod > 0:
                        method = uri[beginMethod + 1: endMethod]
                    if action and method:
                        if ':url' in uri:
                            uri = action + '!' + method + '.action/'
                        else:
                            uri = action + '/' + method + '/'
            uris = evaluate_url_string(uri).split('/')
            uri = None
            if uris:
                uri = ''
                for part in uris:
                    if part:
                        if part.startswith('http:'):
                            uri += 'http://'
                        elif part.startswith('https:'):
                            uri += 'https://'
                        else:
                            uri += ( part.strip() + '/' )

            if uri:
                s = uri.strip()
                if s.startswith(':'):
                    s = s[1:]
                while s.startswith('/ '):
                    s = s[2:]
                    s = s.strip()
                if s.startswith('/'):
                    s = s[1:]
                end = 0
                while '${' in s:
                    begin = s.find('${', end)
                    end = s.find('}', begin)
                    if end > 0:
                        s = s[:begin] + '{}' + s[end+1:]
                    else:
                        break
                while s.startswith('{}/'):
                    s = s[3:]
                while s.startswith('{}'):
                    s = s[2:]
                if s.startswith('/'):
                    s = s[1:]
                if not s or s == '/':
                    s = '{}/'
                if s.startswith('?'):
                    s = '{}' + s
                if '(' in s:
                    s = s[:s.find('(')]
                if s.startswith('~/'):
                    rets.append(s[2:])
                else:
                    rets.append(s)
                if astCalls != None:
                    astCalls.append(astCallsInitial[j])
       
    if not rets:
        rets = []
        rets.append('{}/')
        if astCalls != None:
            astCalls.append(None)
    if len(rets) == 1:
        return rets

    i = 0
    urlMaxSizes = OrderedDict() # by root/ast
    
    for url in rets:

        interrogation = url.find('?')
        _ampersand = url.find('&')
        _equal = url.find('=')
        if interrogation < 0:
            if _ampersand >= 0 or _equal >= 0:
                if _ampersand >= 0 and url[:_ampersand]:
                    cast.analysers.log.debug('url : ' + str(url) + ' is transformed into ' + str(url[:_ampersand]))
                    url = url[:_ampersand]
                else:
                    cast.analysers.log.debug('url is ignored: ' + str(url))
                    i += 1
                    continue
            if url.endswith('/'):
                root = url[:-1]
            else:
                root = url
            try:
                _astCall = astCalls[i] if astCalls != None else None
            except:
                _astCall = None
            if not root in urlMaxSizes:
                urlMaxSizes[root] = OrderedDict()
                urlMaxSizes[root][_astCall] = []
            else:
                if not _astCall in urlMaxSizes[root]:
                    urlMaxSizes[root][_astCall] = []
            urlMaxSizes[root][_astCall].append([url, _astCall])
        else:
            if _ampersand >= 0 and _ampersand < interrogation:
                if url[:_ampersand]:
                    cast.analysers.log.debug('url : ' + str(url) + ' is transformed into ' + str(url[:_ampersand]))
                    url = url[:_ampersand]
                else:
                    cast.analysers.log.debug('url is ignored: ' + str(url))
                    i += 1
                    continue
            elif _equal >= 0 and _equal < interrogation:
                cast.analysers.log.debug('url is ignored: ' + str(url))
                i += 1
                continue
            root = url[:interrogation]
            try:
                _astCall = astCalls[i] if astCalls != None else None
            except:
                _astCall = None
            if not root in urlMaxSizes:
                urlMaxSizes[root] = OrderedDict()
                urlMaxSizes[root][_astCall] = []
            else:
                if not _astCall in urlMaxSizes[root]:
                    urlMaxSizes[root][_astCall] = []
            urlMaxSizes[root][_astCall].append([url, _astCall])
        i += 1
        
    if astCalls != None:
        astCalls.clear()
    results = []
    for _url, _dict in urlMaxSizes.items():
        for _astCall, l in _dict.items():
            if len(l) <= 10:
#             if True:
                cast.analysers.log.debug('less than 10 urls ' + str(_url))
                for value in l:
                    results.append(value[0])
                    cast.analysers.log.debug('   append ' + str(value))
                    if astCalls != None:
                        astCalls.append(value[1])
            else:
                cast.analysers.log.debug('more than 10 urls ' + str(_url))
                i = 0
                cmpt = 0
                maxLen = 0
                for value in l:
                    if len(value[0]) > maxLen:
                        maxLen = len(value[0])
                        i = cmpt
                    cmpt += 1 
                cast.analysers.log.debug('   append ' + str(l[i]))
                results.append(l[i][0])
                if astCalls != None:
                    astCalls.append(l[i][1])

    return results

def evaluate_uri_with_trace(uriToEvaluate, memberNames = None, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, constants = None, evalCounter = None):
    rets = uriToEvaluate.evaluate_with_trace(memberNames, evaluationContext, originalCaller, objectsPassed, charForUnknown, constants, evalCounter)
#     return rets
    if not rets or len(rets) == 1:
        return rets

    urlMaxSizes = OrderedDict() # by root/ast
    
    for _value in rets:

        url = _value.value
        interrogation = url.find('?')
        _ampersand = url.find('&')
        _equal = url.find('=')
        if interrogation < 0:
            if _ampersand >= 0 or _equal >= 0:
                if _ampersand >= 0 and url[:_ampersand]:
                    cast.analysers.log.debug('url : ' + str(url) + ' is transformed into ' + str(url[:_ampersand]))
                    url = url[:_ampersand]
                else:
                    cast.analysers.log.debug('url is ignored: ' + str(url))
                    continue
            if url.endswith('/'):
                root = url[:-1]
            else:
                root = url
            try:
                _astCall = _value.ast_nodes[0]
            except:
                _astCall = None
            if not root in urlMaxSizes:
                urlMaxSizes[root] = OrderedDict()
                urlMaxSizes[root][_astCall] = []
            else:
                if not _astCall in urlMaxSizes[root]:
                    urlMaxSizes[root][_astCall] = []
            urlMaxSizes[root][_astCall].append(_value)
        else:
            if _ampersand >= 0 and _ampersand < interrogation:
                if url[:_ampersand]:
                    cast.analysers.log.debug('url : ' + str(url) + ' is transformed into ' + str(url[:_ampersand]))
                    url = url[:_ampersand]
                else:
                    cast.analysers.log.debug('url is ignored: ' + str(url))
                    continue
            elif _equal >= 0 and _equal < interrogation:
                cast.analysers.log.debug('url is ignored: ' + str(url))
                continue
            root = url[:interrogation]
            try:
                _astCall = _value.ast_nodes[0]
            except:
                _astCall = None
            if not root in urlMaxSizes:
                urlMaxSizes[root] = OrderedDict()
                urlMaxSizes[root][_astCall] = []
            else:
                if not _astCall in urlMaxSizes[root]:
                    urlMaxSizes[root][_astCall] = []
            urlMaxSizes[root][_astCall].append(_value)
        
    results = []
    for _url, _dict in urlMaxSizes.items():
        for _astCall, l in _dict.items():
            if len(l) <= 10:
#             if True:
                cast.analysers.log.debug('less than 10 urls ' + str(_url))
                for _value in l:
                    results.append(_value)
                    cast.analysers.log.debug('   append ' + str(_value))
            else:
                cast.analysers.log.debug('more than 10 urls ' + str(_url))
                i = 0
                cmpt = 0
                maxLen = 0
                for value in l:
                    if len(value[0]) > maxLen:
                        maxLen = len(value[0])
                        i = cmpt
                    cmpt += 1 
                cast.analysers.log.debug('   append ' + str(l[i]))
                results.append(l[i])

    return results


def get_uri_ov_evaluation(memberNames, uriToEvaluate, characterForUnknown = '{}', astCalls = None, _constants = None):

    def get_uri_ov_evaluation_with_trace(uriToEvaluate, memberNames, characterForUnknown, constants, astCallsInitial):
        
        evs = uriToEvaluate.evaluate_with_trace(memberNames, None, None, None, characterForUnknown, constants, None, True)
        values = evs
        return values

    global global_configJsonObjectByRootDir
    if _constants:
        constants = _constants
    elif global_configJsonObjectByRootDir:
        constants = get_nodejs_config(uriToEvaluate)
    else:
        constants = None
        
    values = []
    if astCalls != None:
        astCallsInitial = []
    else:
        astCallsInitial = None
    if isinstance(uriToEvaluate, str):
        values.append(uriToEvaluate)
        if astCallsInitial != None:
            astCallsInitial.append(None)
    elif isinstance(uriToEvaluate, AstString):
        values = get_uri_ov_evaluation_with_trace(uriToEvaluate, memberNames, characterForUnknown, constants, astCallsInitial)
    else:
        try:
            if uriToEvaluate.is_function_call():
                callPart0 = uriToEvaluate.get_function_call_parts()[0]
                if callPart0.parameters:
                    values = get_uri_ov_evaluation_with_trace(callPart0.parameters[0], memberNames, characterForUnknown, constants, astCallsInitial)
                else:
                    uri = None
                    values.append(None)
                    add_ast_call(uri, None, astCallsInitial)
            else:
                servicesCreated = False
                if uriToEvaluate.is_identifier() and len(uriToEvaluate.get_resolutions()) == 1:
                    callee = uriToEvaluate.resolutions[0].callee
                    if callee.parent and callee.parent.is_function() and callee in callee.parent.parameters:
                        servicesCreated = True
                        paramNumber = 0
                        while not callee == callee.parent.parameters[paramNumber]:
                            paramNumber += 1
                if not servicesCreated:
                    values = get_uri_ov_evaluation_with_trace(uriToEvaluate, memberNames, characterForUnknown, constants, astCallsInitial)
        except:
            return []

    if not values:
        return []
    
    j = -1
    for _val in values:
            uri = _val[memberNames[0]].value
            j += 1
            # decoding <s:url action="vincularEspecieCategoriaAnimalFasesCriacao" method="excluir"/>
            if uri.startswith('<') and uri.endswith('/>') and 'action' in uri and 'method' in uri:
                index1 = uri.find('=', uri.find('action'))
                index2 = uri.find('=', uri.find('method'))
                if index1 != index2 and index1 > 0 and index2 > 0:
                    action = ''
                    method = ''
                    
                    beginAction = uri.find('"', index1)
                    endAction = -1
                    if beginAction < 0:
                        beginAction = uri.find("'", index1)
                        if beginAction > 0:
                            endAction = uri.find("'", beginAction + 1)
                    else:
                        endAction = uri.find('"', beginAction + 1)
                    if beginAction > 0 and endAction > 0:
                        action = uri[beginAction + 1: endAction]
           
                    beginMethod = uri.find('"', index2)
                    endMethod = -1
                    if beginMethod < 0:
                        beginMethod = uri.find("'", index2)
                        if beginMethod > 0:
                            endMethod = uri.find("'", beginMethod + 1)
                    else:
                        endMethod = uri.find('"', beginMethod + 1)
                    if beginMethod > 0 and endMethod > 0:
                        method = uri[beginMethod + 1: endMethod]
                    if action and method:
                        uri = action + '/' + method + '/'
            uris = evaluate_url_string(uri).split('/')
            uri = None
            if uris:
                uri = ''
                for part in uris:
                    if part:
                        if part.startswith('http:'):
                            uri += 'http://'
                        elif part.startswith('https:'):
                            uri += 'https://'
                        else:
                            uri += ( part.strip() + '/' )

            if uri:
                s = uri.strip()
                if s.startswith(':'):
                    s = s[1:]
                while s.startswith('/ '):
                    s = s[2:]
                    s = s.strip()
                if s.startswith('/'):
                    s = s[1:]
                end = 0
                while '${' in s:
                    begin = s.find('${', end)
                    end = s.find('}', begin)
                    if end > 0:
                        s = s[:begin] + '{}' + s[end+1:]
                    else:
                        break
                while s.startswith('{}/'):
                    s = s[3:]
                while s.startswith('{}'):
                    s = s[2:]
                if s.startswith('/'):
                    s = s[1:]
                if not s or s == '/':
                    s = '{}/'
                if s.startswith('?'):
                    s = '{}' + s
                if '(' in s:
                    s = s[:s.find('(')]
                if s.startswith('~/'):
                    _val[memberNames[0]].value = s[2:]
                else:
                    _val[memberNames[0]].value = s
       
    return values

#     class used to store any other http request
class HttpCall:
        
    def __init__(self, requestType, url, ast, caller, file):
        self.ast = ast
        self.setType(requestType)
        self.url = url
        self.urlValues = None
        self.caller = caller
        self.file = file
        self.config = None
        self.ovUrlName = None
        self.ovTypeName = None
        self.beginLine = -1
        
    def get_begin_line(self):
        return self.beginLine
        
    def setType(self, typeName):
        typeSetToDefault = False
        self.requestType = typeName.upper()
        if self.requestType not in ['GET', 'POST', 'PUT', 'DELETE']:
            self.requestType = 'GET'
            typeSetToDefault = True
        return typeSetToDefault
    
    def add_listener(self, func):
        try:
            self.calledListeners.append(func)
        except:
            self.calledListeners = []
            self.calledListeners.append(func)
    
    def get_listeners(self):
        try:
            return self.calledListeners
        except:
            return []

class AppletReference:
        
    def __init__(self, className, ast):
        self.ast = ast
        self.className = className

class BeanMethodReference:
        
    def __init__(self, methodName, ast):
        self.ast = ast
        self.methodName = methodName

#     class used to store any other ExecuteSQL call
class ExecuteSQL:
        
    def __init__(self, query, ast, caller, file):
        self.ast = ast
        self.query = query
        self.caller = caller
        self.file = file

class Class(KbSymbol, StatementList):
    """
    A class.
    """
    def __init__(self, name, prefix, parent, token, file = None, emptyLines = None):
        
        StatementList.__init__(self, token, parent)
        self.kbObject = None
        self.lineCount = -1
        self.lineCount = self.get_line_count(emptyLines)
        self.isKbObject = True
        if prefix and name:
            self.set_name(name, prefix + '.' + name, prefix + '.' + name)
        else:
            self.set_name(name, name, name)
        self.file = file
        self.methods = OrderedDict()    # Method by name
        self.inheritanceIdentifier = None
        self.codeLines = 0

    def get_inheritance_identifier(self):
        return self.inheritanceIdentifier
    
    def decrement_code_lines(self, nb):
        self.codeLines -= nb
        if self.codeLines < 0:
            self.codeLines = 0
    
    def get_super_class(self):
        if not self.inheritanceIdentifier:
            return None
        if not self.inheritanceIdentifier.get_resolutions():
            return None
        return self.inheritanceIdentifier.resolutions[0].callee
    
    def convert_crc(self):
        self.crc = self.get_code_only_crc()

    def set_parent(self, parent):
        StatementList.set_parent(self, parent)

    def is_context_container(self):
        return True

    def is_class(self):
        return True
        
    def get_file(self):
        return self.file

    def get_prefix_internal(self):
        try:
            return self.prefix
        except:
            return None

    def set_prefix_internal(self, prefix):
        if prefix:
            self.prefix = prefix
        elif self.get_prefix_internal():
            del self.prefix
        
    def set_prefix(self, prefix):
        if prefix or self.get_prefix_internal():
            self.prefix = prefix
        
    def get_prefix(self):
        if not isinstance(self.get_prefix_internal(), str):
            return ''        
        return self.prefix

    def get_fullname(self):
        if self.get_prefix_internal():
            return str(self.prefix) + '.' + self.name
        else:
            return self.name
    
    def add_method(self, method):
        if not method.name in self.methods:
            l = []
            self.methods[method.name] = l
        else:
            l = self.methods[method.name]
        if not method in l:
            l.append(method)
    
    def get_method(self, name, static = False, includeInheritance = False):
        if name in self.methods:
            l= self.methods[name]
            if len(l) == 1:
                return l[0]
            for meth in l:
                isStatic = False
                if meth.is_method():
                    isStatic = meth.is_static()
                if static:
                    if isStatic:
                        return meth
                else:
                    if not isStatic:
                        return meth
        if includeInheritance:
            if self.inheritanceIdentifier and self.inheritanceIdentifier.get_resolutions():
                for resol in self.inheritanceIdentifier.get_resolutions():
                    cl = resol.callee
                    res = cl.get_method(name, static, includeInheritance)
                    if res:
                        return res
        return None
    
    def get_methods(self, name):
        if name in self.methods:
            return self.methods[name]
        return []
        
    def create_cast_objects(self, parent, config, createChildrenOnly = False):
        
        codeLinesComputed = False
        if not createChildrenOnly:
            if self.get_kb_object():
                class_object = self.kbObject
            else:         
                class_object = cast.analysers.CustomObject()
                self.kbObject = class_object
                class_object.set_name(self.name)
                class_object.set_type(config.objectTypes.classType)
                class_object.set_parent(parent)
                class_object.set_guid(KbSymbol.get_kb_fullname(self))
                class_object.set_fullname(KbSymbol.get_display_fullname(self))
                class_object.save()
                crc = self.tokens[0].get_code_only_crc()
                class_object.save_property('checksum.CodeOnlyChecksum', crc)
                self.codeLines = self.get_line_count()
                codeLinesComputed = True
                headerCommentsLines = self.get_header_comments_line_count()
                if headerCommentsLines:
                    class_object.save_property('metric.LeadingCommentLinesCount', headerCommentsLines)
                    class_object.save_property('comment.commentBeforeObject', self.get_header_comments())
                bodyCommentsLines = self.get_body_comments_line_count()
                if bodyCommentsLines:
                    class_object.save_property('metric.BodyCommentLinesCount', bodyCommentsLines)
                    class_object.save_property('comment.sourceCodeComment', self.get_body_comments())
                file = self.parent
                while not isinstance(file, File) and not isinstance(file, HtmlContent) and not isinstance(file, Object):
                    file = file.parent
                if isinstance(file, HtmlContent):
                    file = file.get_file()
                elif isinstance(file, Object):
                    file =self.get_js_content().file
        
                class_object.save_position(Bookmark(file, self.get_begin_line(), self.get_begin_column(), self.get_end_line(), self.get_end_column()))
        
        if createChildrenOnly:            
            StatementList.create_cast_objects(self, parent, config)
        else:
            StatementList.create_cast_objects(self, class_object, config)

        if codeLinesComputed:
            class_object.save_property('metric.CodeLinesCount', self.codeLines)
            self.parent.decrement_code_lines(self.get_line_count())
        
    def create_cast_links(self, parent, config, suspensionLinks, createChildrenOnly = False):
        
        if self.inheritanceIdentifier:
            self.inheritanceIdentifier.create_cast_links(parent, config, suspensionLinks)
            
        if createChildrenOnly:
            StatementList.create_cast_links(self, parent, config, suspensionLinks)
        else:
            StatementList.create_cast_links(self, self.kbObject, config, suspensionLinks)
            
    def get_line_count(self, emptyLines = None):
        
        if self.lineCount >= 0:
            return self.lineCount
        
        lineCountIncludingComments = self.tokens[0].get_line_count()
        self.lineCount = lineCountIncludingComments - self.get_header_comments_line_count() - self.get_body_comments_line_count()
        if emptyLines:
            begin = self.get_begin_line()
            end = self.get_end_line()
            for line, count in emptyLines.items():
                if begin <= line and line <= end:
                    self.lineCount -= count
        return self.lineCount
            
    def get_header_comments(self, mustBeCorrected = True):
        
        comments = self.tokens[0].get_header_comments()
#         return ''.join(comment.text for comment in comments)
        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'
        return s
            
    def get_body_comments(self):
        
        comments = self.tokens[0].get_body_comments()
        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'
        return s
            
    def get_header_comments_line_count(self, mustBeCorrected = True):
        result = self.get_header_comments(mustBeCorrected).count('\n')
        return result
            
    def get_body_comments_line_count(self):
        result = self.get_body_comments().count('\n')
        return result
            
    def __repr__(self):
        
        result = "function('" + self.name + "')"
        return result
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Class ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad) + '}')

class Method(Function):
    """
    A method.
    """
    def __init__(self, name, parent, token, file, emptyLines, isConstructor):
        
        self.isConstructor = isConstructor
        if name == 'constructor':
            n = parent.name
        else:
            n = name
        Function.__init__(self, n, None, parent, token, file, False, emptyLines)

    def is_method(self):
        return True
    
    def is_static(self):
        try:
            return self.static
        except:
            return False

    def is_constructor(self):
        return self.isConstructor
        
    def convert_crc(self):
        self.crc = self.get_code_only_crc()

    def create_cast_objects(self, parent, config, createChildrenOnly = False):
        
        codeLinesComputed = False
        if not createChildrenOnly:
            if self.get_kb_object():
                method_object = self.kbObject
            else:         
                method_object = cast.analysers.CustomObject()
                self.kbObject = method_object
                method_object.set_name(self.name)
                if self.isConstructor:
                    method_object.set_type(config.objectTypes.constructorType)
                else:
                    method_object.set_type(config.objectTypes.methodType)
                method_object.set_parent(parent)
                method_object.set_guid(KbSymbol.get_kb_fullname(self))
                method_object.set_fullname(KbSymbol.get_display_fullname(self))
                method_object.save()
                crc = self.tokens[0].get_code_only_crc()
                method_object.save_property('checksum.CodeOnlyChecksum', crc)
                method_object.save_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.complexity', self.complexity)
                maxCol = self.get_max_col_over(0)
                method_object.save_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.lengthOfTheLongestLine', maxCol)
                if len(self.parameters) > 0:
                    method_object.save_property('CAST_HTML5_WithParameters.numberOfParameters', len(self.parameters))
                self.codeLines = self.get_line_count()
                codeLinesComputed = True
                headerCommentsLines = self.get_header_comments_line_count()
                if headerCommentsLines:
                    method_object.save_property('metric.LeadingCommentLinesCount', headerCommentsLines)
                    method_object.save_property('comment.commentBeforeObject', self.get_header_comments())
                bodyCommentsLines = self.get_body_comments_line_count()
                if bodyCommentsLines:
                    method_object.save_property('metric.BodyCommentLinesCount', bodyCommentsLines)
                    method_object.save_property('comment.sourceCodeComment', self.get_body_comments())
                file = self.parent
                while not isinstance(file, File) and not isinstance(file, HtmlContent) and not isinstance(file, Object):
                    file = file.parent
                if isinstance(file, HtmlContent):
                    file = file.get_file()
                elif isinstance(file, Object):
                    file =self.get_js_content().file
        
                method_object.save_position(Bookmark(file, self.get_begin_line(), self.get_begin_column(), self.get_end_line(), self.get_end_column()))

                if config.objectTypes.functionType == 'CAST_Javascript_ClientSide_Method':
                    method_object.save_property('CAST_Legacy_WithKeyProp.keyprop', 33554432)
                    method_object.save_property('CAST_Javascript_ClientSide_Method.HTML5', 1)
        
        if createChildrenOnly:            
            StatementList.create_cast_objects(self, parent, config)
        else:
            StatementList.create_cast_objects(self, method_object, config)

        if codeLinesComputed:
            method_object.save_property('metric.CodeLinesCount', self.codeLines)
            self.parent.decrement_code_lines(self.get_line_count())
            
    def get_line_count(self, emptyLines = None):
         
        if self.lineCount >= 0:
            return self.lineCount
         
        lineCountIncludingComments = self.tokens[-1].get_line_count()
        self.lineCount = lineCountIncludingComments - self.get_header_comments_line_count() - self.get_body_comments_line_count()
        if emptyLines:
            begin = self.get_begin_line()
            end = self.get_end_line()
            for line, count in emptyLines.items():
                if begin <= line and line <= end:
                    self.lineCount -= count
        return self.lineCount
             
    def get_header_comments(self, mustBeCorrected = True):

        comments = self.tokens[0].get_header_comments()
        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'
        return s
             
    def get_body_comments(self):
         
        comments = self.tokens[0].get_body_comments()
        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'
        return s
                         
    def __repr__(self):
        
        result = "method('" + self.name + "')"
        return result
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'Method ' + str(hex(id(self))) + ' {')
        print(' '.rjust(pad + 3) + 'parameters :')
        for param in self.parameters:
            param.print(pad + 6)
        StatementList.print(self, pad + 3)
        print(' '.rjust(pad) + '}')

class JsxExpression(AstToken):
    """
    A jsx expression <tag1 attr1=value1 attr2=value2>...</tag1>
    """
    def __init__(self, token, parent):
         
        AstToken.__init__(self, token, parent)
        self.tag = None     # HtmlTextWithPosition
        self.attributeValues = {}
        self.text = None
        self.subExpressions = []
        self.kbObject = None
        if isinstance(parent, Function):
            parent.add_statement(self)
    
    def set_tag(self, token):
        self.tag = HtmlTextWithPosition(token.text, token)
    
    def get_tag(self):
        return self.tag
    
    def get_attributes_values(self):
        return self.attributeValues
    
    def add_attribute_value(self, attrName, valueToken):
        ret = None
        if type(valueToken) is list:
            try:
                text = ''
                for val in valueToken:
                    text += val.text
                if text.startswith(('"', "'")):
                    text = text[1:-1]
            except:
                text = ''
            ret = self.attributeValues[attrName] = HtmlTextWithPosition(text, valueToken)
        else:
            try:
                text = valueToken.text
                if text.startswith(('"', "'")):
                    text = text[1:-1]
            except:
                text = ''
            ret = self.attributeValues[attrName] = HtmlTextWithPosition(text, valueToken)
        return ret
        
    def is_jsx_expression(self):
        return True

    def get_children(self):
        return self.subExpressions
        
    def get_kb_object(self, recursiveInParents = False):
        return self.kbObject
        
        parent = self.parent
        while parent:
            if parent.is_jsx_expression():
                return parent.get_kb_object()
            elif parent.is_function():
                return parent.get_kb_object()
            parent = parent.parent
        return None

    def is_sub_jsx_expression(self):
        parent = self.parent
        while parent:
            try:
                if parent.is_jsx_expression():
                    return True
            except:
                return False
            parent = parent.parent
        return False
            
    def create_cast_objects(self, parent, config, createChildrenOnly = False):
        
        fragment_object = None
        
        if not self.is_sub_jsx_expression() and not createChildrenOnly:
            if self.get_kb_object():
                fragment_object = self.kbObject
            else:         
                fragment_object = cast.analysers.CustomObject()
                self.kbObject = fragment_object
                nextFragmentNr = self.parent.increment_next_html_fragment_number()
                name = parent.name + '_fragment_' + str(nextFragmentNr)
                fragment_object.set_name(name)
                fragment_object.set_type(config.objectTypes.htmlFragmentType)
                fragment_object.set_parent(parent)
                fullname = parent.guid + '_fragment_' + str(nextFragmentNr)
                displayName = parent.fullname + '_fragment_' + str(nextFragmentNr)
                fragment_object.set_guid(fullname)
                fragment_object.set_fullname(displayName)
                fragment_object.save()
                file = self.parent
                while not isinstance(file, File) and not isinstance(file, HtmlContent) and not isinstance(file, Object):
                    file = file.parent
                if isinstance(file, HtmlContent):
                    file = file.get_file()
                elif isinstance(file, Object):
                    file =self.get_js_content().file
        
                fragment_object.save_position(Bookmark(file, self.get_begin_line(), self.get_begin_column(), self.get_end_line(), self.get_end_column()))
                
        if createChildrenOnly:            
            StatementList.create_cast_objects(self, parent, config)
        else:
            if fragment_object:
                StatementList.create_cast_objects(self, fragment_object, config)
            else:
                StatementList.create_cast_objects(self, parent, config)
    
    def print(self, pad = 0):
        print(' '.rjust(pad) + 'jsxExpression ' + str(self.tag))
