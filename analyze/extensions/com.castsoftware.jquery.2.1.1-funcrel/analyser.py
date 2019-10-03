import cast.analysers.ua
from cast.analysers import Bookmark, create_link
from jquery_parser import analyse
from symbols import Violations
from collections import OrderedDict
import traceback
import os
import re
from distutils.version import StrictVersion
from cast import Event
        
def get_short_uri(uri):
    shortUri = uri
    if '?' in uri:
        shortUri = uri[:uri.find('?')]
    if shortUri.endswith('/'):
        shortUri = shortUri[:-1]
    return shortUri

class JQueryStrictVersion(StrictVersion):
    
    jquery_version_re = re.compile(r'^(\d+) \. (\d+) (\. (\d+))? ((\-)?([ab]|[r][c])(\d+))?$', re.VERBOSE | re.ASCII)

    def parse (self, vstring):
        match = self.jquery_version_re.match(vstring)
        if not match:
            raise ValueError("invalid version number '%s'" % vstring)

        (major, minor, patch, prerelease, prerelease_num) = \
            match.group(1, 2, 4, 5, 6)

        if patch:
            self.version = tuple(map(int, [major, minor, patch]))
        else:
            self.version = tuple(map(int, [major, minor])) + (0,)

        if prerelease:
            if prerelease[0] == '-':
                self.prerelease = (prerelease[1:-1], int(prerelease[-1]))
            else:
                self.prerelease = (prerelease[0], int(prerelease_num))
        else:
            self.prerelease = None
    
class JQuery(cast.analysers.ua.Extension):
    
    class LinkSuspension:
            
        def __init__(self, type, caller, callee, bookmark):
            self.type = type
            self.caller = caller
            self.callee = callee
            self.bookmark = bookmark
    
    class ParsingResults:
        
        def __init__(self):
            self.containsAjaxCall = False
            self.containsJQueryDialog = False
            self.nbAjaxInLoop = 0
            self.ajaxCallsInLoop = []
            self.ajaxCallsWithoutDatatype = []
            self.dialogWithCloseText = []
            self.appendOrAfter = []
            self.attr = []
            self.html = []
            self.dialog = []
            self.tooltip = []
            self.locationHash = []
            self.containsJQuery = False
            self.events = []
            self.ajax_calls = []
            self.calls_to_events_suspensions = [] 
            self.links_suspensions = [] 
            self.violations = Violations()
            
        def add_link_suspension(self, typ, caller, callee, bookmark):
            self.links_suspensions.append(self.LinkSuspension(typ, caller, callee, bookmark))
        
    """
    Parse .js files and create jquery events.
    """
    def __init__(self):
        
        self.frameworks = ['jquery', 'jquery-ui']
        self.currentFile = None
        self.currentSourceCode = None
        self.nbSelectors = 0
        self.nbResourceServices = 0
        self.guidsToNotDuplicate = {}
        self.linkSuspensions = []
        self.jqueryReferencesByFile = OrderedDict()

        self.framework_versions = {}
        self.maxFrameworkStrictVersion = {}
        self.maxFrameworkVersion = {}   # equal to n for version n.m.p
        self.maxFrameworkSubVersion = {}   # equal to m for version n.m.p
        self.maxFrameworkSubSubVersion = {}   # equal to p for version n.m.p
        for fmk in self.frameworks:
            self.framework_versions[fmk] = {}
            self.maxFrameworkVersion[fmk] = 0
            self.maxFrameworkSubVersion[fmk] = 0
            self.maxFrameworkSubSubVersion[fmk] = 0
            self.maxFrameworkStrictVersion[fmk] = None

    @Event('com.castsoftware.html5', 'start_analysis_root')
    def start_analysis_root(self, rootDir):
        cast.analysers.log.info('start root analysis ' + rootDir)
        self.currentFile = None
        self.currentSourceCode = None

    @Event('com.castsoftware.html5', 'end_analysis_root')
    def end_analysis_root(self, rootDir):
        cast.analysers.log.info('end root analysis ' + rootDir)

    
    @Event('com.castsoftware.html5', 'end_html_content')
    def end_html_content(self, htmlContent):
        self.end_html(htmlContent)
    
    @Event('com.castsoftware.html5', 'end_jsp_content')
    def end_jsp_content(self, htmlContent):
        self.end_html(htmlContent)
    
    @Event('com.castsoftware.html5', 'end_asp_content')
    def end_asp_content(self, htmlContent):
        self.end_html(htmlContent)
    
    @Event('com.castsoftware.html5', 'end_aspx_content')
    def end_aspx_content(self, htmlContent):
        self.end_html(htmlContent)
    
    @Event('com.castsoftware.html5', 'end_cshtml_content')
    def end_cshtml_content(self, htmlContent):
        self.end_html(htmlContent)
    
    @Event('com.castsoftware.html5', 'end_htc_content')
    def end_htc_content(self, htmlContent):
        self.end_html(htmlContent)

    @Event('com.castsoftware.html5', 'start_html_javascript_content')
    def start_html_javascript_content(self, jsContent):
        self.start_javascript(jsContent, True)
    
    @Event('com.castsoftware.html5', 'start_cshtml_javascript_content')
    def start_cshtml_javascript_content(self, jsContent):
        self.start_javascript(jsContent, True)
    
    @Event('com.castsoftware.html5', 'start_jsp_javascript_content')
    def start_jsp_javascript_content(self, jsContent):
        self.start_javascript(jsContent, True)
    
    @Event('com.castsoftware.html5', 'start_asp_javascript_content')
    def start_asp_javascript_content(self, jsContent):
        self.start_javascript(jsContent, True)
    
    @Event('com.castsoftware.html5', 'start_aspx_javascript_content')
    def start_aspx_javascript_content(self, jsContent):
        self.start_javascript(jsContent, True)
    
    @Event('com.castsoftware.html5', 'start_htc_javascript_content')
    def start_htc_javascript_content(self, jsContent):
        self.start_javascript(jsContent, True)
    
    @Event('com.castsoftware.html5', 'start_javascript_content')
    def start_javascript_content(self, jsContent):
        self.start_javascript(jsContent)

    def save_violations(self, frameworkName, violations, inHtmlFile, bookmarksByFramework, propertyName):

        for violation in violations:
            bookmarks = []
            for key, value in self.framework_versions[frameworkName].items():
                jsFiles = value[2]
                for jsFile in jsFiles.keys():
                    if not inHtmlFile and jsFile == self.currentFile.get_path():
                        bookmarks.append(key.create_bookmark(value[1]))
            if inHtmlFile:
                if frameworkName in bookmarksByFramework:
                    for textWithPos in bookmarksByFramework[frameworkName]:
                        bookmarks.append(textWithPos.create_bookmark(self.currentFile))
            self.currentSourceCode.save_violation(propertyName, violation.create_bookmark(self.currentFile), bookmarks)
        
    def start_javascript(self, jsContent, inHtmlFile = False):
        
        self.currentFile = jsContent.get_file()
        self.currentSourceCode = jsContent.kbObject
        parsingResults = self.ParsingResults()
        parsingResults.maxFrameworkVersion = self.maxFrameworkVersion
        cast.analysers.log.info('analyzing ' + self.currentFile.get_path())
        analyse(jsContent, self.currentFile, parsingResults)
        
        eventsByNameByType = {}
        
        for event in parsingResults.events:
            self.create_event(event, jsContent, self.guidsToNotDuplicate)
            if event.name in eventsByNameByType:
                d = eventsByNameByType[event.name]
            else:
                d = {}
                eventsByNameByType[event.name] = d 
            eventsByNameByType[event.name][event.eventType] = event

        parsingResults.violations.save(self.currentSourceCode)
            
        if parsingResults.containsJQuery:
            self.currentSourceCode.save_property('CAST_JQuery_Properties.containsJQueryCall', 1)
            
        if parsingResults.containsAjaxCall:
            self.currentSourceCode.save_property('CAST_JQuery_Properties.containsAjaxCall', 1)
        if parsingResults.containsJQueryDialog:
            self.currentSourceCode.save_property('CAST_JQuery_Properties.containsJQueryDialogCall', 1)
            
        for ajaxCallInLoop in parsingResults.ajaxCallsInLoop:
            self.currentSourceCode.save_violation('CAST_JQuery_Metric_UseOfDollarAjaxInLoop.numberOfDollarAjaxInLoop', ajaxCallInLoop.create_bookmark(self.currentFile))
           
        if inHtmlFile:
            bookmarksByFramework = self.end_html(jsContent.get_parent())
        else:
            bookmarksByFramework = {}
         
        if self.maxFrameworkVersion['jquery'] > 0 and self.maxFrameworkVersion['jquery'] < 3:
            self.save_violations('jquery', parsingResults.ajaxCallsWithoutDatatype, inHtmlFile, bookmarksByFramework, 'CAST_JQuery_Metric_UseOfDollarAjaxWithoutDataType.numberOfDollarAjaxWithouDataType')
            
        if self.maxFrameworkVersion['jquery-ui'] > 0 and self.maxFrameworkVersion['jquery-ui'] <= 1 and self.maxFrameworkSubVersion['jquery-ui'] < 12:
            self.save_violations('jquery-ui', parsingResults.dialogWithCloseText, inHtmlFile, bookmarksByFramework, 'CAST_JQuery_Metric_UseOfDialogWithCloseText.numberOfDialogWithCloseText')
         
        if self.maxFrameworkStrictVersion['jquery'] and self.maxFrameworkStrictVersion['jquery'] < StrictVersion('1.6.3'):
            self.save_violations('jquery', parsingResults.locationHash, inHtmlFile, bookmarksByFramework, 'CAST_JQuery_Metric_AvoidJQueryLocationHashBefore163.numberOfJQueryLocationHash')
         
        if self.maxFrameworkStrictVersion['jquery'] and self.maxFrameworkStrictVersion['jquery'] <= StrictVersion('1.4.2'):
            self.save_violations('jquery', parsingResults.appendOrAfter, inHtmlFile, bookmarksByFramework, 'CAST_JQuery_Metric_UseOfAppendOrAfter.numberOfAppendOrAfter')
         
        if self.maxFrameworkStrictVersion['jquery'] and self.maxFrameworkStrictVersion['jquery'] == JQueryStrictVersion('3.0.0-rc1'):
            self.save_violations('jquery', parsingResults.attr, inHtmlFile, bookmarksByFramework, 'CAST_JQuery_Metric_UseOfAttr_300rc1.numberOfAttr300rc1')
         
        if self.maxFrameworkStrictVersion['jquery'] and self.maxFrameworkStrictVersion['jquery'] <= StrictVersion('1.9.0'):
            self.save_violations('jquery', parsingResults.html, inHtmlFile, bookmarksByFramework, 'CAST_JQuery_Metric_UseOfHtmlFunction.numberOfHtmlCall')
         
        if self.maxFrameworkStrictVersion['jquery-ui'] and self.maxFrameworkStrictVersion['jquery-ui'] < StrictVersion('1.10.0'):
            self.save_violations('jquery-ui', parsingResults.dialog, inHtmlFile, bookmarksByFramework, 'CAST_JQuery_Metric_UseOfDialog.numberOfDialogCall')
            self.save_violations('jquery-ui', parsingResults.tooltip, inHtmlFile, bookmarksByFramework, 'CAST_JQuery_Metric_UseOfTooltip.numberOfTooltipCall')
        
        for ajax_call in parsingResults.ajax_calls:
            self.create_ajax_call(ajax_call)
            
        for callToEvent in parsingResults.calls_to_events_suspensions:
            
            if callToEvent.eventName in eventsByNameByType and callToEvent.eventType in eventsByNameByType[callToEvent.eventName]:
                event = eventsByNameByType[callToEvent.eventName][callToEvent.eventType]
                if callToEvent.caller:
                    caller = callToEvent.caller
                else:
                    caller = jsContent
                self.create_link('callLink', caller, event.kbObject, callToEvent.callPart.create_bookmark(self.currentFile))
            
        for link in parsingResults.links_suspensions:
            
            if link.caller and link.callee:
                if link.callee.get_kb_object():
                    self.create_link(link.type, link.caller, link.callee.kbObject, link.callee.create_bookmark(self.currentFile))
        
    @Event('com.castsoftware.html5', 'end_javascript_contents')
    def end_javascript_contents(self):

        for suspension in self.linkSuspensions:
            callee = suspension.callee.get_kb_object()
            if callee:
                self.create_link(suspension.type, suspension.caller, callee, suspension.bookmark)
        
        cast.analysers.log.info(str(self.nbSelectors) + ' JQuery selectors created.')
        cast.analysers.log.info(str(self.nbResourceServices) + ' JQuery resource services created.')
        
        for path, l in self.jqueryReferencesByFile.items():
            for ref in l:
                cast.analysers.log.info(ref + ' found in ' + path)
                
        for fmk in self.frameworks:
            s = ''
            already = []
            for v in self.framework_versions[fmk].values():
                if not v[0] in already:
                    s += (', ' if s else '') + v[0]
                    already.append(v[0])
            cast.analysers.log.info(fmk + ' versions: ' + s)
            cast.analysers.log.info('Max ' + fmk + ' version: ' + str(self.maxFrameworkVersion[fmk]))

    def create_event(self, event, jsContent, guids):
        
        path = self.currentFile.get_path()
        fullname = path + '/' + event.eventType + '/' + event.name
        displayfullname = path + '.' + event.eventType + '.' + event.name
        
        if not fullname in guids:
            guids[fullname] = 0
        else:
            cmpt = guids[fullname] + 1
            guids[fullname] = cmpt
            fullname += '_' + str(cmpt)
        
        event_object = cast.analysers.CustomObject()
        event.kbObject = event_object
        event_object.set_name(event.name + '/' + event.eventType)
        event_object.set_parent(self.currentSourceCode)
        event_object.set_type('CAST_JQuery_Selector')
        event_object.set_fullname(displayfullname)
        event_object.set_guid(fullname)
                 
        event_object.save()
        event_object.save_position(event.ast.create_bookmark(self.currentFile))
        event_object.save_property('CAST_JQuery_Selector.type', event.eventType)
        event_object.save_property('checksum.CodeOnlyChecksum', event.ast.get_code_only_crc())

        try:
            if event.eventHandler:
                if event.eventHandler.get_kb_object():
                    self.create_link('callLink', event_object, event.eventHandler.get_kb_object(), event.ast.create_bookmark(self.currentFile))
                else:
                    self.linkSuspensions.append(self.LinkSuspension('callLink', event_object, event.eventHandler, event.ast.create_bookmark(self.currentFile)))
        except:
            pass

        for htmlContent in jsContent.get_html_calling_files():
            jsFile = htmlContent.has_js_file(self.currentFile.get_path())
            if jsFile:
                self.create_link('callLink', htmlContent.htmlSourceCode, event_object, jsFile.create_bookmark(htmlContent.file))
            else:
                self.create_link('callLink', htmlContent.htmlSourceCode, event_object, event.ast.create_bookmark(htmlContent.file))
                
        self.nbSelectors += 1
    
    def create_ajax_call(self, ajax_call):
        
        if not ajax_call.parent:
            return
        
        parentKbSymbol = ajax_call.parent.get_kb_symbol()
        if not parentKbSymbol:
            return
        
        if not parentKbSymbol.kbObject:
            return
        
        if ajax_call.uri == None:
            ajax_call.uri = ''
        
        metamodelType = None
        if ajax_call.type == 'GET':
            metamodelType = 'CAST_JQuery_GetResourceService'
        elif ajax_call.type == 'POST':
            metamodelType = 'CAST_JQuery_PostResourceService'
        elif ajax_call.type == 'PUT':
            metamodelType = 'CAST_JQuery_PutResourceService'
        elif ajax_call.type == 'DELETE':
            metamodelType = 'CAST_JQuery_DeleteResourceService'
            
        if not metamodelType:
            return
        
        name = get_short_uri(ajax_call.uri)
        if not name or name == '{}':
            return

        fullname = parentKbSymbol.get_kb_fullname() + '/' + metamodelType + '/' + name
        displayfullname = parentKbSymbol.get_display_fullname() + '.' + name

        resource_object = cast.analysers.CustomObject()
        resource_object.set_name(name)
        resource_object.set_parent(parentKbSymbol.kbObject)
        resource_object.set_type(metamodelType)
        if not fullname in self.guidsToNotDuplicate:
            self.guidsToNotDuplicate[fullname] = 0
        else:
            cmpt = self.guidsToNotDuplicate[fullname] + 1
            self.guidsToNotDuplicate[fullname] = cmpt
            fullname += '_' + str(cmpt)
        resource_object.set_fullname(displayfullname)
        resource_object.set_guid(fullname)
                 
        resource_object.save()
        resource_object.save_position(ajax_call.ast.create_bookmark(self.currentFile))
        resource_object.save_property('CAST_ResourceService.uri', ajax_call.uri)
        resource_object.save_property('checksum.CodeOnlyChecksum', ajax_call.ast.get_code_only_crc())
        
        if ajax_call.astCall:
            linkCaller = ajax_call.astCall.get_first_kb_parent()
            bm = ajax_call.astCall.create_bookmark(ajax_call.astCall.get_file())
        else:
            linkCaller = parentKbSymbol
            bm = ajax_call.ast.create_bookmark(self.currentFile)
        self.create_link('callLink', linkCaller, resource_object, bm)
        
        self.nbResourceServices += 1

    def create_link(self, linkType, caller, callee, bm = None):
     
        try:    
            clr = caller
            cle = callee
            try:
                if not isinstance(clr, cast.analysers.CustomObject):
                    if clr.is_js_content():
                        clr = clr.create_javascript_initialisation()
                        if not isinstance(clr, cast.analysers.CustomObject):    # if we are in html, not javascript_init
                            clr = clr.get_kb_object()
                    else:
                        clr = clr.get_kb_object()
            except:
                clr = clr.get_kb_object()
                     
            if bm:
                cast.analysers.create_link(linkType, clr, cle, bm)
            else:
                cast.analysers.create_link(linkType, clr, cle)
        except:
            try:
                cast.analysers.log.debug('Internal issue when creating link: ' + str(traceback.format_exc()))
                cast.analysers.log.debug('linkType = ' + str(linkType))
                cast.analysers.log.debug('caller = ' + str(clr))
                cast.analysers.log.debug('callee = ' + str(cle))
                cast.analysers.log.debug('bookmark = ' + str(bm))
            except:
                pass

    def file_contains_jquery(self, path):
        
        try:
            with open(path) as fp:
                line = fp.readline().strip()
                if 'jQuery JavaScript Library v' in line:
                    s = line[line.find('jQuery JavaScript Library v') + len('jQuery JavaScript Library v'):]
                    s = s.split()[0]
                    if s.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                        return s
                elif 'jQuery v' in line:
                    s = line[line.find('jQuery v') + len('jQuery v'):]
                    s = s.split()[0]
                    if s.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                        return s
                else:
                    line = fp.readline()
                    if 'jQuery JavaScript Library v' in line:
                        s = line[line.find('jQuery JavaScript Library v') + len('jQuery JavaScript Library v'):]
                        s = s.split()[0]
                        if s.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                            return s
                    elif 'jQuery v' in line:
                        s = line[line.find('jQuery v') + len('jQuery v'):]
                        s = s.split()[0]
                        if s.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                            return s
        except:
            pass
        return ''

    def file_contains_jquery_ui(self, path):
        
        try:
            with open(path) as fp:
                line = fp.readline().strip()
                if 'jQuery UI - v' in line:
                    s = line[line.find('jQuery UI - v') + len('jQuery UI - v'):]
                    s = s.split()[0]
                    if s.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                        return s
                else:
                    line = fp.readline()
                    if 'jQuery UI - v' in line:
                        s = line[line.find('jQuery UI - v') + len('jQuery UI - v'):]
                        s = s.split()[0]
                        if s.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
                            return s
        except:
            pass
        return ''
    
    def add_framework_version(self, fmk, basename, value, htmlContent, jsFiles, testBasename = True):
        
        try:
            if '.' in basename:
                if not self.maxFrameworkStrictVersion[fmk] or JQueryStrictVersion(basename) > self.maxFrameworkStrictVersion[fmk]:
                    self.maxFrameworkStrictVersion[fmk] = JQueryStrictVersion(basename)
        except:
                cast.analysers.log.info('could not decode version ' + str(basename) + ' for framework ' + str(fmk))
        if not testBasename or basename.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
            self.framework_versions[fmk][value] = (basename, htmlContent.get_file(), jsFiles)
            index = basename.find('.')
            if index >= 0:
                try:
                    v = int(basename[:index])
                    remain = basename[index + 1:]
                    if v > self.maxFrameworkVersion[fmk]:
                        self.maxFrameworkVersion[fmk] = v
                except:
                    pass
                index = remain.find('.')
                if index >= 0:
                    try:
                        v = int(remain[:index])
                        if v > self.maxFrameworkSubVersion[fmk]:
                            self.maxFrameworkSubVersion[fmk] = v
                        v = int(remain[index + 1:])
                        if v > self.maxFrameworkSubSubVersion[fmk]:
                            self.maxFrameworkSubSubVersion[fmk] = v
                    except:
                        pass
            return True
        return False
        
    def end_html(self, htmlContent):
        
        bookmarksByFramework = {}
        # find jquery framework or jquery-ui framework
        stringsToSearch = ['\\jquery.', '\\jquery-', '/jquery.', '/jquery-']
        jsFiles = htmlContent.get_js_files()
        for name, value in jsFiles.items():
            if any(s in name for s in stringsToSearch):
                path = htmlContent.get_path()
                if path in self.jqueryReferencesByFile:
                    l = self.jqueryReferencesByFile[path]
                else:
                    l = []
                    self.jqueryReferencesByFile[path] = l
                l.append(name)
                basename = os.path.basename(name)
                if basename.endswith('.js'):
                    basename = basename[:-3]
                if basename.endswith('min'):    # -min or .min
                    basename = basename[:-4]
                found = False
                # basename should be now jquery-1.9.1 or jquery.1.9.1 or jquery-ui
                if basename.startswith('jquery-ui'):
                    basename = basename[10:]
#                     bookmarksByFramework
                    found = self.add_framework_version('jquery-ui', basename, value, htmlContent, jsFiles)
                    if not found:
                        dirname = os.path.dirname(name)
                        basename = os.path.basename(dirname)
                        found = self.add_framework_version('jquery-ui', basename, value, htmlContent, jsFiles)
                        if not found:
                            v = self.file_contains_jquery_ui(name)
                            if v:
                                found = self.add_framework_version('jquery-ui', v, value, htmlContent, jsFiles, False)
                    if found:
                        if 'jquery-ui' in bookmarksByFramework:
                            l = bookmarksByFramework['jquery-ui']
                        else:
                            l = []
                            bookmarksByFramework['jquery-ui'] = l
                        l.append(value)
                elif basename.startswith('jquery'):
                    basename = basename[7:]
                    found = self.add_framework_version('jquery', basename, value, htmlContent, jsFiles)
                    if not found:
                        dirname = os.path.dirname(name)
                        basename = os.path.basename(dirname)
                        found = self.add_framework_version('jquery', basename, value, htmlContent, jsFiles)
                        if not found:
                            v = self.file_contains_jquery(name)
                            if v:
                                found = self.add_framework_version('jquery', v, value, htmlContent, jsFiles, False)
                    if found:
                            if 'jquery' in bookmarksByFramework:
                                l = bookmarksByFramework['jquery']
                            else:
                                l = []
                                bookmarksByFramework['jquery'] = l
                            l.append(value)
                            
        return bookmarksByFramework
                