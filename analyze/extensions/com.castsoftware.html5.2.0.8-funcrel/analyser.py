import cast.analysers.ua
import cast.analysers
from javascript_parser import ObjectTypes, analyse, analyse_fullprocess, analyse_process_diags, analyse_preprocess, Function, HtmlContent, AnalyzerConfiguration
from javascript_parser.javascript_interpreter import JavascriptInterpreter
from javascript_parser.javascript_lexer import JSXLexer
from javascript_parser.symbols import html5_open_source_file, set_nodejs_config, CssContent, Resolution, Violations, JSPFile, ASPFile, get_uri_evaluation, get_uri_ov_evaluation, JsContent
from sql_parser import extract_tables
from js_file_filters import JSFileFilter, CssFileFilter, HtmlFileFilter, FileFilter
from collections import OrderedDict
import html_parser
import jade_parser
import css_parser
import traceback
import os
import re
import json
import razor_parser
from distutils.version import StrictVersion

def get_short_uri(uri):
    shortUri = uri
    if '?' in uri:
        shortUri = uri[:uri.find('?')]
    if shortUri.endswith('/'):
        shortUri = shortUri[:-1]
    if shortUri:
        return shortUri
    else:
        return '{}'

def compute_crc(ast):
    try:
        crc = ast.get_code_only_crc()
    except:
        try:
            crc = ast.tokens[0].get_code_only_crc()
        except:
            try:
                crc = ast.token.get_code_only_crc()
            except:
                crc = 0
    return crc
    
def memory():
#     try:
#         import platform
#         if platform.architecture()[0] == '32bit':
#             import psutil32 as psutil
#         else:
#             import psutil64 as psutil
#         process = psutil.Process(os.getpid())
#         cast.analysers.log.info("Max memory used is " + str(process.memory_info().rss / 1000000))
#         print(process.memory_info().rss)
#     except:
#         pass
    pass
   
# split a file name and returns a list containing directories and the basename.
# Example: if filename = C:\dir1\dir2\myfile.js,
# it returns ['dir1', 'dir2'] and 'myfile.js'
def splitFileDirectory(filename):
        
    folders = []
    path = filename
    while 1:
        path, folder = os.path.split(path)

        if folder != "":
            folders.append(folder)
        else:
            if path != "":
                folders.append(path)

            break

    folders.reverse()
    return [ folders[1:-1], folders[-1] ]

def preprocess_html_fragment(text):
    
    newtext = text
    index = -1
    while '@Url.Content("' in newtext:
        index = newtext.find('@Url.Content("', index+1)
#         if index > 0 and newtext[index-1] in ["'", '"']:
#             newtext = newtext[:index] + '              ' + newtext[index+13:]
#             continue
        if index < 0:
            break
        indexLast0 = newtext.find('"', index + 14)
        indexLast = newtext.find('")', index)
        if indexLast < 0 or ( indexLast0 > 0 and indexLast0 < indexLast ):
            continue
        if newtext[index-1] == '"':
            newtext = newtext[:index] + '              ' + newtext[index+14:indexLast] + '"  ' + newtext[indexLast+3:]
        elif newtext[index-1] == "'":
            newtext = newtext[:index] + '              ' + newtext[index+14:indexLast] + "'  " + newtext[indexLast+3:]
        else:
            newtext = newtext[:index] + '              ' + newtext[index+14:indexLast] + '"  ' + newtext[indexLast+3:]
    return newtext

def preprocess_html_fragment_old(text):
    
    newtext = text
    index = -1
    while '@Url.Content("' in newtext:
        index = newtext.find('@Url.Content("', index+1)
        if index < 0:
            break
        indexLast = newtext.find('")', index)
        if indexLast < 0:
            continue
            
        newtext = newtext[:index] + '              ' + newtext[index+14:indexLast+1] + '  ' + newtext[indexLast+3:]
    return newtext

def detect_language(text):
    if not text:
        return None
    firstChar = text[0]
    if firstChar == '<':
        res = re.search('<.[a-zA-Z_0-9:]*:.[a-zA-Z_0-9:]*>', text)
        if res:
            return 'jsp'
        res = re.search('<.[a-zA-Z_0-9:]*>', text)
        if res:
            return 'html'
    res = re.search('function.*\(', text)
    if res:
        return 'js'
    res = re.search('var .*=', text)
    if res:
        return 'js'
    if 'require(' in text:
        return 'js'
    if 'module.exports' in text:
        return 'js'
    if "'use strict'" in text:
        return 'js'
    if "exports." in text:
        return 'js'
    return None
    
class JavaScriptAnalyzer():
    
    # Stores a directory structure. A directory is composed of files and subdirectories.
    # Example: C:\dir1\dir2\file1.js
    #          C:\dir1\dir3\file2.js
    # 3 directories: dir1, dir2 and dir3
    # dir1 contains 2 subdirectories dir2 and dir3
    # dir2 contains 1 file file1.js and dir3 contains another file
    class Directory:
        def __init__(self, jsAnalyzer, name, parent = None, root = None):
            self.nbHtml = 0
            self.nbCss = 0
            self.nbJs = 0
            self.nbJsx = 0
            self.nbJsp = 0
            self.nbAsp = 0
            self.subDirectories = OrderedDict()
            self.files = OrderedDict()  # value = detectedLanguage
            self.name = name
            self.parent = parent
            self.root = root
            
            dirPath = self.get_path()
            if os.path.exists(os.path.join(dirPath, 'WEB-INF')) and not dirPath in jsAnalyzer.webappsFolders:
                cast.analysers.log.info('Web application found : ' + dirPath)
                jsAnalyzer.webappsFolders.append(dirPath)
            elif name == 'public' and not dirPath in jsAnalyzer.publicFolders:
                cast.analysers.log.info('public directory found : ' + dirPath)
                jsAnalyzer.publicFolders.append(dirPath)
            
        def get_path(self):
            if self.parent:
                return os.path.join(self.parent.get_path(), self.name)
            else:
                return os.path.join(self.root, self.name)

        def get_next_web_root_dir(self):
            
            while len(self.subDirectories) == 1 and not self.files:
                for _, d in self.subDirectories.items():
                    if len(d.subDirectories) > 1:
                        return self
                    return d.get_next_web_root_dir()
            return self
        
        def get_js_files(self, results):
            for _, sub in self.subDirectories.items():
                sub.get_js_files(results)
            for f, detectedLanguage in self.files.items():
                path = f.get_path()
                if path.endswith('.js') or detectedLanguage == 'js':
                    results.append(f)
        
        def get_jsx_files(self, results):
            for _, sub in self.subDirectories.items():
                sub.get_jsx_files(results)
            for f in self.files.keys():
                path = f.get_path()
                if path.endswith('.jsx'):
                    results.append(f)        
        
        def get_jsp_files(self, results):
            for _, sub in self.subDirectories.items():
                sub.get_jsp_files(results)
            for f, detectedLanguage in self.files.items():
                path = f.get_path()
                if path.endswith(('.jsp', 'jsf', 'jsff', 'jspx')) or detectedLanguage == 'jsp':
                    basename = os.path.basename(f.get_path())
                    if not basename in results:
                        results[basename] = []
                    results[basename].append(JSPFile(f))
        
        def get_asp_files(self, results):
            for _, sub in self.subDirectories.items():
                sub.get_asp_files(results)
            for f in self.files.keys():
                path = f.get_path()
                if path.endswith(('.asp', '.aspx', '.cshtml', '.cshtml.html', '.htc')):
                    basename = os.path.basename(f.get_path())
                    if not basename in results:
                        results[basename] = []
                    results[basename].append(ASPFile(f))

        def get_html_files(self, results):
            for _, sub in self.subDirectories.items():
                sub.get_html_files(results)
            for f, detectedLanguage in self.files.items():
                path = f.get_path()
                if ( path.endswith('.html') and not '.cshtml' in path) or path.endswith(('.htm', '.xhtml', '.jade')) or detectedLanguage == 'html':
                    results[f.get_path()] = f

        def get_css_files(self, results):
            for _, sub in self.subDirectories.items():
                sub.get_css_files(results)
            for f in self.files.keys():
                path = f.get_path()
                if path.endswith('.css'):
                    results[path] = f
        
        def addSubDirectory(self, jsAnalyzer, dirNameList, f, detectedLanguage = ''):
            
            filename = f.get_path()
            if filename.endswith('.js') or detectedLanguage == 'js':
                self.nbJs += 1
            elif filename.endswith('.jsx'):
                self.nbJsx += 1
            elif ( filename.endswith('.html') and not '.cshtml' in filename) or filename.endswith(('.htm', '.xhtml', 'jade')) or detectedLanguage == 'html':
                self.nbHtml += 1
            elif filename.endswith('.css'):
                self.nbCss += 1
            elif filename.endswith(('.jsp', 'jsf', 'jsff', 'jspx')) or detectedLanguage == 'jsp':
                self.nbJsp += 1
            elif filename.endswith(('.asp', '.aspx', '.htc', '.cshtml', '.cshtml.html')):
                self.nbAsp += 1
            
            if not dirNameList:
                self.files[f] = detectedLanguage
                return
            
            if not dirNameList[0] in self.subDirectories:
                d = JavaScriptAnalyzer.Directory(jsAnalyzer, dirNameList[0], self)
                self.subDirectories[dirNameList[0]] = d
            else:
                d = self.subDirectories[dirNameList[0]]
            d.addSubDirectory(jsAnalyzer, dirNameList[1:], f, detectedLanguage)
        
        def print(self, indent = 0):
            cast.analysers.log.info(' '.rjust(indent) + self.name + ': ' + str(self.nbJs) + ' js files, ' + str(self.nbJsx) + ' jsx files, ' + str(self.nbHtml) + ' html files, ' + str(self.nbJsp) + ' jsp files, ' + str(self.nbAsp) + ' asp/aspx/htc/cshtml files')
            for f in self.files:
                cast.analysers.log.info(' '.rjust(indent + 2) + f.get_path())
            for _, child in self.subDirectories.items():
                child.print(indent + 2)
        
        def get_files(self):
            #return (child for child in self.children if isinstance(child, Node))
            return self.files
           
    class WebXmlFile:
        
        def __init__(self, filename):
            
            import xml.etree.ElementTree as ET
            
            self.strutsConfigFilenames = []
            self.strutsSubappFilenames = {}
            
            try:
                tree = ET.parse(filename)
                root = tree.getroot()
                
                for init_param in root.iterfind('servlet/init-param'):
                    paramName = None
                    paramValue = None
                    for child_of_init_param in init_param:
                        if child_of_init_param.tag == 'param-name':
                            paramName = child_of_init_param.text
                        elif child_of_init_param.tag == 'param-value':
                            paramValue = child_of_init_param.text
                    #        <init-param>
                    #           <param-name>config</param-name>
                    #           <param-value>/WEB-INF/struts-config.xml</param-value>
                    #        </init-param>
                    if paramName == 'config':
                        if paramValue.startswith('/'):
                            parentDir = os.path.dirname(os.path.dirname(filename))
                            strutsFile = os.path.join(parentDir, paramValue[1:])
                        else:
                            parentDir = os.path.dirname(filename)
                            strutsFile = os.path.join(parentDir, paramValue)
                        if os.path.isfile(strutsFile):
                            self.strutsConfigFilenames.append(strutsFile)
                    #         <init-param>
                    #             <param-name>config/dashboard</param-name>
                    #             <param-value>/WEB-INF/struts-dashboard.xml</param-value>
                    #         </init-param>
                    elif paramName.startswith('config/'):
                        if paramValue.startswith('/'):
                            parentDir = os.path.dirname(os.path.dirname(filename))
                            strutsFile = os.path.join(parentDir, paramValue[1:])
                        else:
                            parentDir = os.path.dirname(filename)
                            strutsFile = os.path.join(parentDir, paramValue)
                        if os.path.isfile(strutsFile):
                            appName = paramName[7:]
                            if not appName in self.strutsSubappFilenames: 
                                self.strutsSubappFilenames[appName] = strutsFile
            except:
                cast.analysers.log.warning('Internal issue when parsing file: ' + str(filename))
                cast.analysers.log.debug(str(traceback.format_exc()))

        def is_subapp(self, name):
            
            if name in self.strutsSubappFilenames:
                return True
            return False
             
    # Saves the file f in self.directories structure
    def addFileDirectoryToDirectories(self, f, detectedLanguage = ''):
        
        folders, filen = splitFileDirectory(f.get_path())
        
        if folders[0] in self.directories:
            d = self.directories[folders[0]]
        else:
            fpath = f.get_path()
            index = fpath.find(folders[0])
            d = self.Directory(self, folders[0], None, fpath[0:index])
            self.directories[folders[0]] = d

        d.addSubDirectory(self, folders[1:], f, detectedLanguage)
    
    """
    var gvar = function() {}   --> 1 function gvar
    var gvar = expression      --> 1 variable gvar
    var gvar = {
        var1 : expression,
        f1 : function() {}
    }                          --> 2 variables gvar and gvar.var1, 1 function gvar.f1
    """

    """
    Parse .js files and create functions.
    """
    def __init__(self, extension, config = None, configJSInHtml = None, configCSSInHtml = None):
        
        self.directories = OrderedDict()
        
        self.supportedExtensions = '*.js;*.ts;*.jsx;*.tsx;*.html;*.htm;*.xhtml;*.jsp;*.jsf;*.jsff;*.jspx;*.xml;*.json;*.css;*.asp;*.aspx;*.htc;*.cshtml;*.jade;*.yml'
        self.supportedExtensions += ';'
        self.extension = extension
        self.jsFiles = []
        self.jsxFiles = []
        self.jspFiles = OrderedDict()       # key=file basename/value=list of JSPFile
        self.aspFiles = OrderedDict()       # key=file basename/value=list of ASPFile
        self.htmlFiles = OrderedDict()      # key=file path/value=list of HTML file
        self.cssFiles = OrderedDict()       # key=file path/value=css file
        self.globalVariablesByName = OrderedDict()   # key=name/value=list because may be 2 variables with same name 
        self.globalFunctionsByName = OrderedDict()   # key=name/value=list because may be 2 functions with same name
        self.globalClassesByName = OrderedDict()   # key=name/value=list because may be 2 classes with same name
        self.jsContentsByFilename = OrderedDict()        # key=filename/value=jsContent
        self.jsFilesByBasename = OrderedDict()    # key=file basename/value=list of files
        self.jsxFilesByBasename = OrderedDict()    # key=file basename/value=list of files
        self.htmlContentsByFile = OrderedDict()      # key=file/value=htmlContent
        self.htmlContentsByJS = OrderedDict()        # key=js filename/value=htmlContent list of html files including jsfile
        self.htmlContentsByName = OrderedDict()        # key=html basename/value=htmlContent list of html files
        self.jsFileFilter = JSFileFilter()
        self.cssFileFilter = CssFileFilter()
        self.htmlFileFilter = HtmlFileFilter()
        self.jsonFileFilter = FileFilter()
        self.xmlFileFilter = FileFilter()
        self.xmlHttpRequestGuids = OrderedDict()
        self.webappsFolders = []    # list of folders containing subfolder WEB-INF/web.xml
        self.publicFolders = []    # list of folders named public
        self.nbRazorServices = 0
        self.nbStrutsActions = 0
        self.nbAppletReferences = 0
        self.nbBeanMethodReferences = 0
        self.webXmlFiles = {} # WebXmlFile objects by filename
        self.taglibsByJspFullpath = {}

        if config:
            self.config = config
        else:
            self.config = AnalyzerConfiguration(ObjectTypes())

        if configJSInHtml:
            self.configJSInHtml = configJSInHtml
        else:
            self.configJSInHtml = AnalyzerConfiguration(ObjectTypes('CAST_HTML5_JavaScript_SourceCode_Fragment'))

        if configCSSInHtml:
            self.configCSSInHtml = configCSSInHtml
        else:
            self.configCSSInHtml = AnalyzerConfiguration(ObjectTypes('CAST_HTML5_CSS_SourceCode_Fragment'))

#         self.jspConfig = AnalyzerConfiguration(ObjectTypes('CAST_HTML5_JSP_SourceCode'))
        
        self.webSockets = [] # must be kept because url needs evaluation and evaluation can be done only when all ast has been read
        self.openCalls = []
        self.XMLHttpRequests = []
        self.httpRequests = []
        self.eventSourceRequests = []
        self.executeSqls = []
#         self.f = open('f:\\temp\\entry.pickle', 'wb')
        self.razorRootDirectories = []
        self.globalClassesBroadcasted = False
        self.castVersion = None
        self.isUADeactivated = False
        self.configJsonFilesByRootDir = {}
        self.configJsonObjectByRootDir = {}
        # key = extension without ., value = dict 'jsp' --> nr of files, 'html' --> nr of files ...
        self.detectedLanguagesByUnknownExtension = {}   # key = myext, value = {} where key = language, value = list of files
        
    def get_cast_version(self):
        
        if not self.castVersion:
            self.castVersion = cast.analysers.get_cast_version()
            if (self.castVersion >= StrictVersion('8.2.11') and self.castVersion < StrictVersion('8.3.0')) or self.castVersion >= StrictVersion('8.3.4'):
                self.isUADeactivated = True
            
        return self.castVersion

    def broadcast(self, msg, obj = None):
            self.extension.broadcast(msg, obj)

    def broadcast_no_param(self, msg):
            self.extension.broadcast(msg)

    def create_link(self, linkType, caller, callee, bm = None):
     
        try:    
            clr = caller
            cle = callee
            if not clr:
                if bm:
                    cast.analysers.log.debug('Empty caller when creating link: ' + str(str(bm)))
                return
            if not isinstance(clr, cast.analysers.CustomObject):
                if isinstance(clr, JsContent):
                    clr = clr.create_javascript_initialisation()
                else:
                    clr = clr.get_kb_object()
            else:
                if clr.typename == 'CAST_HTML5_JavaScript_SourceCode':
                    filename = clr.parent.get_path()
                    if filename.endswith('.js') or filename.endswith('.jsx'):
                        clr = self.jsContentsByFilename[filename]
                        try:
                            clr = clr.ast
                        except:
                            pass
                        if isinstance(clr, JsContent):
                            clr = clr.create_javascript_initialisation()
                        else:
                            clr = clr.get_kb_object()
                     
            if not isinstance(cle, cast.analysers.CustomObject):
                cle = cle.get_kb_object()
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

    def clean_jsContent(self, jsContent):
        self.jsContentsByFilename[jsContent.file.get_path()] = jsContent.get_kb_object()
        jsContent.convert_ast_list_to_position()
    
    def is_file_to_be_skipped(self, filename, detectedLanguage = '', unsupportedExtension = False):
        
        basename = os.path.basename(filename)

        if not basename.endswith(('.js', '.jsx')) and not detectedLanguage == 'js':
            if unsupportedExtension:
                self.jsFileFilter.last_matches_result = 'bad extension'
                return True
                
        if basename.endswith(('.min.js', 'Spec.js')):
            self.jsFileFilter.last_matches_result = 'minified or test file'
            return True

        if basename.endswith('.js'):
            dirname = os.path.dirname(filename)
            if os.path.exists(os.path.join(dirname, basename[:-2] + 'ts')):
                # a .ts file exists with the same name at the same place
                self.jsFileFilter.last_matches_result = 'generated from .ts file'
                return True
        
        return self.jsFileFilter.matches(filename)
    
    def is_css_file_to_be_skipped(self, filename):
        
        basename = os.path.basename(filename)

        if not basename.endswith('.css'):
            self.cssFileFilter.last_matches_result = 'bad extension'
            return True
                
        if basename.endswith('.min.css'):
            self.cssFileFilter.last_matches_result = 'minified file'
            return True
        
        return self.cssFileFilter.matches(filename)
    
    def is_json_file_to_be_skipped(self, filename):
        
        basename = os.path.basename(filename)

        if not basename.endswith('.json'):
            self.jsonFileFilter.last_matches_result = 'bad extension'
            return True
        
        return self.jsonFileFilter.matches(filename)
    
    def is_xml_file_to_be_skipped(self, filename):
        
        basename = os.path.basename(filename)

        if not basename.endswith('.xml'):
            self.xmlFileFilter.last_matches_result = 'bad extension'
            return True
        
        return self.xmlFileFilter.matches(filename)

    def _start_file(self, file, detectedLanguage, unsupportedExtension):

        skipped = False
        filepath = file.get_path()
            
        if (filepath.endswith('.html') and not '.cshtml' in filepath) or filepath.endswith(('.htm', '.xhtml', '.jade')) or detectedLanguage == 'html':
             
            if not self.htmlFileFilter.matches(filepath):
                self.addFileDirectoryToDirectories(file, detectedLanguage)
            else:
                skipped = True
                cast.analysers.log.info('File ' + filepath + ' has been skipped (' + self.htmlFileFilter.get_last_result() + ')')
              
        elif filepath.endswith('.css'):
             
            if not self.cssFileFilter.matches(filepath):
                if not self.is_css_file_to_be_skipped(filepath):
                    self.addFileDirectoryToDirectories(file)
                else:
                    skipped = True
                    cast.analysers.log.info('File ' + filepath + ' has been skipped (' + self.cssFileFilter.get_last_result() + ')')
            else:
                skipped = True
                cast.analysers.log.info('File ' + filepath + ' has been skipped (' + self.cssFileFilter.get_last_result() + ')')
 
        elif filepath.endswith(('.jsp', '.jsf', '.jspx', '.jsff')) or detectedLanguage == 'jsp':
            self.addFileDirectoryToDirectories(file, detectedLanguage)
            self.preanalyze_jsp_file(file)
             
        elif filepath.endswith('.asp'):
            self.addFileDirectoryToDirectories(file)
         
        elif filepath.endswith('.aspx'):
            self.addFileDirectoryToDirectories(file)
         
        elif filepath.endswith(('.cshtml', '.cshtml.html')):
            if not self.htmlFileFilter.matches(filepath):
                parentDir = os.path.dirname(os.path.dirname(filepath))
                if not parentDir in self.razorRootDirectories and os.path.exists(os.path.join(parentDir, 'Controllers')) and os.path.exists(os.path.join(parentDir, 'Views')):
                    self.razorRootDirectories.append(parentDir)
                self.addFileDirectoryToDirectories(file)
            else:
                skipped = True
                cast.analysers.log.info('File ' + filepath + ' has been skipped (' + self.htmlFileFilter.get_last_result() + ')')
         
        elif filepath.endswith('.htc'):
            self.addFileDirectoryToDirectories(file)
         
        elif filepath.endswith('.xml'):
             
            if not self.is_xml_file_to_be_skipped(filepath):
                self.broadcast('start_xml_content', file)
                if filepath.endswith('WEB-INF\\web.xml'):
                    webappDir = os.path.dirname(file.get_path()[:-8])
                    if not webappDir in self.webappsFolders: 
                        cast.analysers.log.info('Webapp found : ' + webappDir)
                        self.webappsFolders.append(webappDir)
                self.broadcast('end_xml_content', file)    
            else:
                skipped = True
                cast.analysers.log.info('File ' + filepath + ' has been skipped (' + self.xmlFileFilter.get_last_result() + ')')
         
        elif filepath.endswith('.json'):
             
            if not self.is_json_file_to_be_skipped(filepath):
                fileBasename = os.path.basename(filepath)
                dirname = os.path.normpath(os.path.dirname(filepath))
                if os.path.basename(dirname) == 'config':
                    dirname = os.path.normpath(os.path.dirname(os.path.dirname(filepath)))
                    if dirname in self.configJsonFilesByRootDir:
                        _map = self.configJsonFilesByRootDir[dirname]
                    else:
                        _map = {}
                        self.configJsonFilesByRootDir[dirname] = _map
                    _map[fileBasename] = file
                self.broadcast('start_json_content', file)    
                self.broadcast('end_json_content', file)    
            else:
                skipped = True
                cast.analysers.log.info('File ' + filepath + ' has been skipped (' + self.jsonFileFilter.get_last_result() + ')')

        elif detectedLanguage in ['js', ''] and not self.is_file_to_be_skipped(filepath, detectedLanguage, unsupportedExtension):
            
            self.addFileDirectoryToDirectories(file, detectedLanguage)
            
        else:
            skipped = True
            cast.analysers.log.info('File ' + file.get_path() + ' has been skipped (' + self.jsFileFilter.get_last_result() + ')')
            
        if not skipped:
            self.broadcast('start_file_from_html5', file)
        return True
    
    def start_file(self, file):
           
        cast.analysers.log.debug('start_file ' + file.get_path())
        detectedLanguage = ''  
        filepath = file.get_path()
        basename = os.path.basename(filepath)
        unsupportedExtension = False
        if '.' in basename:
            extension = basename[basename.rfind('.'):].lower()
            if not '*' + extension + ';' in self.supportedExtensions:
                unsupportedExtension = True
                try:
                    if extension in self.detectedLanguagesByUnknownExtension:
                        detectedLanguages = self.detectedLanguagesByUnknownExtension[extension]
                    else:
                        detectedLanguages = {}
                        self.detectedLanguagesByUnknownExtension[extension] = detectedLanguages
                    text = html5_open_source_file(filepath)
                    if text:
                        detectedLanguage = detect_language(text)
                        if detectedLanguage:
                            if not detectedLanguage in detectedLanguages:
                                detectedLanguages[detectedLanguage] = []
                            detectedLanguages[detectedLanguage].append(file)
                            cast.analysers.log.info('File ' + filepath + " has been detected as '" + detectedLanguage + "' type.")
                        else:
                            cast.analysers.log.info('File ' + filepath + ' type has not been detected.')
                except:
                    pass
                return
         
        self._start_file(file, detectedLanguage, unsupportedExtension)        
        
    def preprocess_file(self, file, fileType, suspensionLinks = None):
        
        if ( file.get_path()[-5:] == '.html' and not '.cshtml' in file.get_path() ) or file.get_path().endswith(('.htm', '.xhtml', '.jade')) or fileType == 'html':
            self.analyze_html_file(file, suspensionLinks)

        elif file.get_path().endswith('.css') or fileType == 'css':
            cssContent = self.analyze_css_file(file)
            if cssContent:
                self.cssFiles[file.get_path()] = cssContent

        elif file.get_path().endswith(('.jsp', '.jsf', '.jspx', '.jsff')) or fileType == 'jsp':
            
            try:
                return self.analyze_jsp_file(file, suspensionLinks)
            except Exception as e:
                cast.analysers.log.warning('HTML5-001 Internal issue analyzing jsp file: ' + file.get_path() + ' could not be parsed.')
                cast.analysers.log.debug(str(traceback.format_exc()))
                return None

        elif file.get_path().endswith(('.asp', '.aspx', '.htc', '.cshtml', '.cshtml.html')) or fileType == 'asp':
            
            try:
                path = file.get_path()
                extension = path[path.rfind('.') + 1 :]
                return self.analyze_jsp_file(file, suspensionLinks, extension)
            except Exception as e:
                cast.analysers.log.warning('HTML5-002 Internal issue analyzing asp/aspx/htc/cshtml file: ' + file.get_path() + ' could not be parsed.')
                cast.analysers.log.debug(str(traceback.format_exc()))
                return None
            
        else:
            
            cast.analysers.log.info('Light parsing of file ' + file.get_path())

            try:
                text = html5_open_source_file(file.get_path())
#                 f = open(file.get_path(), 'r', encoding="utf8")
#                 try:
#                     text = f.read()
#                 except UnicodeDecodeError:
#                     f.close()
#                     f = open(file.get_path(), 'r')
#                     text = f.read()
                 
                basename = os.path.basename(file.get_path())
                
                if file.get_path().endswith('.jsx'):
                    filesByBasename = self.jsxFilesByBasename
                    lexer = JSXLexer
                else:
                    filesByBasename = self.jsFilesByBasename
                    if 'React' in text:
                        lexer = JSXLexer
                    else:
                        lexer = None
                
                if not basename in filesByBasename:
                    List = []
                    filesByBasename[basename] = List
                else:
                    List = filesByBasename[basename]
                List.append(file)
                
                interpreter = JavascriptInterpreter(file, self.config, self.jsContentsByFilename, self.globalVariablesByName, self.globalFunctionsByName, self.globalClassesByName, None, False, self.htmlContentsByJS)
                jsContent = analyse_preprocess(interpreter, text, lexer, 1, 1);
    
                self.globalClassesByName
    
                self.jsContentsByFilename[file.get_path()] = jsContent
    
                jsContent.create_cast_objects(file)
                
            except:
                cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))
                cast.analysers.log.warning('Problem when light parsing ' + file.get_path())

    def process_razor_file(self, aspFile):

        cast.analysers.log.info('Processing razor file ' + aspFile.file.get_path())
        try:
            text = html5_open_source_file(aspFile.file.get_path(), False)
        except:
            cast.analysers.log.warning('HTML5-003 Problem when opening ' + aspFile.file.get_path())
            return
                
        results = razor_parser.analyse(text)
        
        defaultControllerName = os.path.basename(os.path.dirname(aspFile.file.get_path()))
        
        guids = {}
        
        for result in results.controllerMethodCalls:
            if not result.controllerName:
                result.controllerName = defaultControllerName
            if result.controllerName.startswith('{{'):
                continue
                
            sourceCode_object = cast.analysers.CustomObject()
            objectName = result.controllerName + '/' + result.methodName
            if result.hasParameter:
                objectName += '/{}'
            sourceCode_object.set_name(objectName)
            objectType = None
            if result.httpType:
                if result.httpType.lower() == 'get':
                    objectType = 'CAST_HTML5_Razor_GetService'
                else:
                    objectType = 'CAST_HTML5_Razor_PostService'
            else:
                objectType = 'CAST_HTML5_Razor_PostService'
            sourceCode_object.set_type(objectType)
                
            sourceCode_object.set_parent(aspFile.sourceCode)
            fullname = aspFile.file.get_path() + '/' + objectType + '/' + objectName
            if fullname in guids:
                nr = guids[fullname]
                guids[fullname] = nr + 1
                fullname += ('_' + str(nr + 1))
            else:
                guids[fullname] = 1
            sourceCode_object.set_guid(fullname)
            sourceCode_object.set_fullname(fullname)
            sourceCode_object.save()
            sourceCode_object.save_property('CAST_ResourceService.uri', objectName + '/')
            self.nbRazorServices += 1

            try:
                sourceCode_object.save_position(result.ast.create_bookmark(aspFile.file))
            except Exception as e:
                pass
            self.create_link('callLink', aspFile.sourceCode, sourceCode_object, result.ast.create_bookmark(aspFile.file))
           
    def analyze_html_file(self, file, suspensionLinks):
        
        cast.analysers.log.info('Starting file ' + file.get_path())
        isJade = False
        if file.get_path().lower().endswith('jade'):
            isJade = True
            
        try:
            text = html5_open_source_file(file.get_path(), False)
        except:
            cast.analysers.log.warning('HTML5-003 Problem when opening ' + file.get_path())
            return
                
        if not self.config.objectTypes.sourceCodeType:
            sourceCode_object = file
        else:
            sourceCode_object = cast.analysers.CustomObject()
            sourceCode_object.set_name(os.path.basename(file.get_path()))
            if isJade:
                sourceCode_object.set_type('CAST_HTML5_Jade_SourceCode')
            else:
                sourceCode_object.set_type('CAST_HTML5_SourceCode')
            
            sourceCode_object.set_parent(file)
            if isJade:
                fullname = file.get_path() + '/CAST_HTML5_Jade_SourceCode'
            else:
                fullname = file.get_path() + '/CAST_HTML5_SourceCode'
            sourceCode_object.set_guid(fullname)
            sourceCode_object.set_fullname(file.get_path())
            sourceCode_object.save()

        self.broadcast('start_html_content', file)    
        self.broadcast('start_html_source_code', sourceCode_object)
        htmlContent = HtmlContent(file, sourceCode_object)
        self.htmlContentsByFile[file] = htmlContent
        htmlBasename = os.path.basename(file.get_path())
        if not htmlBasename in self.htmlContentsByName:
            l = []
            self.htmlContentsByName[htmlBasename] = l
        else:
            l = self.htmlContentsByName[htmlBasename]
        l.append(htmlContent)
        violations = Violations()
        if isJade:
            objectDatabaseProperties = jade_parser.analyse(self, text, htmlContent, violations)
        else:
            objectDatabaseProperties = html_parser.analyse(self, text, htmlContent, violations)
        
        if sourceCode_object != file:
            sourceCode_object.save_property('metric.CodeLinesCount', objectDatabaseProperties.codeLinesCount)
            if objectDatabaseProperties.headerCommentLinesCount > 0:
                sourceCode_object.save_property('metric.LeadingCommentLinesCount', objectDatabaseProperties.headerCommentLinesCount)
            if objectDatabaseProperties.bodyCommentLinesCount > 0:
                sourceCode_object.save_property('metric.BodyCommentLinesCount', objectDatabaseProperties.bodyCommentLinesCount)
        if self.isUADeactivated:
            file.save_property('metric.CodeLinesCount', objectDatabaseProperties.codeLinesCount)
            if objectDatabaseProperties.headerCommentLinesCount > 0:
                file.save_property('metric.LeadingCommentLinesCount', objectDatabaseProperties.headerCommentLinesCount)
            if objectDatabaseProperties.bodyCommentLinesCount > 0:
                file.save_property('metric.BodyCommentLinesCount', objectDatabaseProperties.bodyCommentLinesCount)
        
        self.create_struts_actions(htmlContent, fullname, file.get_path(), sourceCode_object, file)
        
        self.create_services(htmlContent, file)
        violations.save()
        
        if self.config.objectTypes.sourceCodeType:
            sourceCode_object.save_property('checksum.CodeOnlyChecksum', objectDatabaseProperties.checksum)
            if objectDatabaseProperties.bookmarks:
                sourceCode_object.save_position(objectDatabaseProperties.bookmarks[0])
            
        for jsFileName, _ in htmlContent.get_js_files().items():
            if jsFileName in self.htmlContentsByJS:
                l = self.htmlContentsByJS[jsFileName]
            else:
                l = []
                self.htmlContentsByJS[jsFileName] = l
            l.append(htmlContent)
           
        globalVariablesByName = self.globalVariablesByName
        globalFunctionsByName = self.globalFunctionsByName
        globalClassesByName = self.globalClassesByName
        jsContentsByFilename = self.jsContentsByFilename

        htmlBasename = os.path.basename(file.get_path())
        index = htmlBasename.rfind('.')
        htmlBasename = htmlBasename[:index]
        config = self.configJSInHtml
        jsContents = []
        for fragment in htmlContent.get_javascript_fragments():
            interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, None, False, None)
            interpreter.jsContent = analyse_preprocess(interpreter, fragment.get_text(), None, fragment.get_begin_line(), fragment.get_begin_column())
            jsContents.append(interpreter.jsContent)

        cmpt = 0
        lastJsContent = None
        for fragment in htmlContent.get_javascript_fragments():
            jsContent = jsContents[cmpt]
            self.jsContentsByFilename[file.get_path()] = jsContent
            self.jsContentsByFilename[file.get_path()].add_html_calling_file(htmlContent)
#             interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, jsContent, True, None, self.htmlContentsByName)
            interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, jsContent, True, self.htmlContentsByJS, self.htmlContentsByName)
            text = preprocess_html_fragment(fragment.get_text())
            analyse_fullprocess(interpreter, text, None, fragment.get_begin_line(), fragment.get_begin_column() + 1)
            if cmpt == 0:
                jsContent.create_cast_objects(file, sourceCode_object, htmlBasename)
                self.create_link('callLink', sourceCode_object, jsContent.kbObject, objectDatabaseProperties.bookmarks[0])
            else:
                jsContent.create_cast_objects(file, sourceCode_object, htmlBasename, lastJsContent.kbObject)
            jsContent.update_globals_with_cast_objects(globalVariablesByName, globalFunctionsByName)
            jsContent.create_cast_links(file, suspensionLinks)
            self.broadcast('start_html_javascript_content', jsContent)
            lastJsContent = jsContent
            self.clean_jsContent(jsContent)
            cmpt += 1

        self.resolve_html_values(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, suspensionLinks, sourceCode_object, file)
        self.analyze_html_css_fragments(file, htmlContent)
                        
        self.broadcast('end_html_source_code', sourceCode_object)    
        self.broadcast('end_html_content', htmlContent)
           
    def analyze_html_css_fragments(self, file, htmlContent):

        if not htmlContent.get_css_fragments():
            return

        sourceCode_object = cast.analysers.CustomObject()
        sourceCode_object.set_name(os.path.basename(file.get_path())[:-5]) # we remove .html from the name
        sourceCode_object.set_type('CAST_HTML5_CSS_SourceCode_Fragment')
                
        sourceCode_object.set_parent(htmlContent.htmlSourceCode)
        fullname = file.get_path() + '/CAST_HTML5_CSS_SourceCode_Fragment'
        sourceCode_object.set_guid(fullname)
        sourceCode_object.set_fullname(file.get_path())
        sourceCode_object.save()
        
        checksum = 0
        
        for fragment in htmlContent.get_css_fragments():

            cssContent = CssContent(file, sourceCode_object)
            violations = Violations()
            objectDatabaseProperties = css_parser.analyse(self, fragment.get_text(), cssContent, violations, fragment.get_begin_line(), fragment.get_begin_column(), checksum)
            checksum = objectDatabaseProperties.checksum
            if objectDatabaseProperties.bookmarks:
                sourceCode_object.save_position(objectDatabaseProperties.bookmarks[0])

        sourceCode_object.save_property('checksum.CodeOnlyChecksum', checksum)
        
    def analyze_css_file(self, file):
        
        cast.analysers.log.info('Starting file ' + file.get_path())
        try:
            text = html5_open_source_file(file.get_path(), False)
        except:
            cast.analysers.log.warning('HTML5-003 Problem when opening ' + file.get_path())
            return None
        
        if not self.config.objectTypes.sourceCodeType:
            sourceCode_object = file
        else:
            sourceCode_object = cast.analysers.CustomObject()
            sourceCode_object.set_name(os.path.basename(file.get_path()))
            sourceCode_object.set_type('CAST_HTML5_CSS_SourceCode')
            
            sourceCode_object.set_parent(file)
            fullname = file.get_path() + '/CAST_HTML5_CSS_SourceCode'
            sourceCode_object.set_guid(fullname)
            sourceCode_object.set_fullname(file.get_path())
            sourceCode_object.save()
                
        self.broadcast('start_css_content', file)    
        self.broadcast('start_css_source_code', sourceCode_object)
        cssContent = CssContent(file, sourceCode_object)
        violations = Violations()
        try:
            objectDatabaseProperties = css_parser.analyse(self, text, cssContent, violations)
            violations.save()
            
            if self.config.objectTypes.sourceCodeType:
                sourceCode_object.save_property('checksum.CodeOnlyChecksum', objectDatabaseProperties.checksum)
                if objectDatabaseProperties.bookmarks:
                    sourceCode_object.save_position(objectDatabaseProperties.bookmarks[0])
        
            if sourceCode_object != file:
                sourceCode_object.save_property('metric.CodeLinesCount', objectDatabaseProperties.codeLinesCount)
                if objectDatabaseProperties.headerCommentLinesCount > 0:
                    sourceCode_object.save_property('metric.LeadingCommentLinesCount', objectDatabaseProperties.headerCommentLinesCount)
                if objectDatabaseProperties.bodyCommentLinesCount > 0:
                    sourceCode_object.save_property('metric.BodyCommentLinesCount', objectDatabaseProperties.bodyCommentLinesCount)
            if self.isUADeactivated:
                file.save_property('metric.CodeLinesCount', objectDatabaseProperties.codeLinesCount)
                if objectDatabaseProperties.headerCommentLinesCount > 0:
                    file.save_property('metric.LeadingCommentLinesCount', objectDatabaseProperties.headerCommentLinesCount)
                if objectDatabaseProperties.bodyCommentLinesCount > 0:
                    file.save_property('metric.BodyCommentLinesCount', objectDatabaseProperties.bodyCommentLinesCount)
        except:
            cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))
        self.broadcast('end_css_source_code', sourceCode_object)    
        self.broadcast('end_css_content', file)
        return cssContent
            
    def preprocess_javascript_razor(self, text):
        
        end = 0
        while '"@Url.Content("' in text:
            begin = text.find('"@Url.Content(', end)
            end = text.find(')"')
            if end:
                text = text[:begin] + '              ' + text[begin+14:end] + '  ' + text[end+2:]
        return text
     
    # prepa to struts modules STRUTS-18
    # we search for a prefix to the service:
    # if <jsp_file_dir>/../WEB-INF/struts-<jsp_file_dir>.xml exists, take <jsp_file_dir> as prefix
    def get_url_prefix(self, fileDirPath):

        prefix = ''
        if True:
            parentDirBaseName = os.path.basename(fileDirPath)
            webXml = os.path.join(os.path.join(os.path.dirname(fileDirPath), 'WEB-INF'), 'web.xml')
            webXmlFile = None
            if os.path.isfile(webXml):
                if webXml in self.webXmlFiles:
                    webXmlFile = self.webXmlFiles[webXml]
                else:
                    webXmlFile = self.WebXmlFile(webXml)
                    self.webXmlFiles[webXml] = webXmlFile
                    
            if webXmlFile and webXmlFile.is_subapp(parentDirBaseName):
                prefix = '/' + parentDirBaseName
        return prefix
                   
    def create_struts_actions(self, htmlContent, fullname, displayName, sourceCode_object, file):

#         prefix = self.get_url_prefix(os.path.dirname(htmlContent.file.get_path()))
        
        strutsActions = htmlContent.get_struts_actions()
        guids = {}
        for strutsAction in strutsActions:
            actionText = strutsAction.get_action_value()
            if not actionText:
                # this happen when code as been put blank because contains only <% ... %>
                actionText = strutsAction.action.token.text
                actionText = actionText.strip('"\' \r\n\t')
            if not actionText:
                cast.analysers.log.debug('Struts action without uri')
                continue
            if actionText == '#' or actionText.startswith(('{{', 'javascript:')):
                continue
            
#             if any(actionText.endswith(x) for x in ['.html/', '.html', '.htm/', '.htm', '.jsp/', '.jsp', '.asp/', '.asp', '.aspx/', '.aspx', '.cshtml/', '.cshtml', '.htc/', '.htc', '.css/', '.css', '.ico/', '.ico', '.png/', '.png', '.doc/', '.doc', '.pdf/', '.pdf', '.xml/', '.xml', '.jpg/', '.jpg', '.gif/', '.gif']) or any((x in actionText) for x in ['.html#', '.htm#', '.jsp#', '.asp#', '.aspx#', '.cshtml#', '.htc#']):
            extensions = ['.html/', '.html', '.htm/', '.htm', '.jsp/', '.jsp', '.asp/', '.asp', '.aspx/', '.aspx', '.cshtml/', '.cshtml', '.htc/', '.htc', '.css/', '.css', '.ico/', '.ico', '.png/', '.png', '.doc/', '.doc', '.pdf/', '.pdf', '.xml/', '.xml', '.jpg/', '.jpg', '.gif/', '.gif', '.html#', '.htm#', '.jsp#', '.asp#', '.aspx#', '.cshtml#', '.htc#']
            if any(x in actionText for x in extensions):
                res = None
                for x in extensions:
                    if x in actionText:
                        try:
                            mainActionText = actionText[:actionText.find(x) + len(x)]
                            res = self.create_HttpRequestLinkToFile(mainActionText, file, sourceCode_object, strutsAction.action.create_bookmark(file))
                        except:
                            res = None
                            cast.analysers.log.debug('Internal issue in create_HttpRequestLinkToFile')
                            cast.analysers.log.debug(str(traceback.format_exc()))
                        break
                if res and not '?' in actionText:
                    continue
                    
            index = actionText.find('.action')
            if index >= 0:
                if not actionText.endswith('.action') and not actionText.endswith('.action/') and not '.action?' in actionText:
                    actionText = actionText.replace('.action', '')
            index = actionText.find('.do')
            if index >= 0:
                if not actionText.endswith('.do') and not actionText.endswith('.do/') and not '.do?' in actionText:
                    actionText = actionText.replace('.do', '')

# prepa to struts modules STRUTS-18
            actionText, _ = self.compute_url_prefix(os.path.dirname(htmlContent.file.get_path()), actionText)
#             if prefix:
#                 if actionText.startswith('/'):
#                     actionText = prefix + actionText
#                 else:
#                     actionText = prefix + '/' + actionText
            strutsAction_object = cast.analysers.CustomObject()
            cast.analysers.log.debug('Creating Struts action ' + str(actionText))
            # for name, keep only the first parameter after ? (in order to be not too long)
            _name = actionText
            if '?' in _name:
                indexInterr = _name.find('?')
                indexAnd = _name.find('&', indexInterr)
                if indexAnd > 0:
                    _name = _name[:indexAnd]
                if _name.startswith('/'):
                    _name = _name[1:]
                if not _name:
                    _name = '{}'
            strutsAction_object.set_name(_name)
            smallType = 'post'
            _type = 'CAST_HTML5_PostHttpRequestService'
            if strutsAction._type == 'GET':
                _type = 'CAST_HTML5_GetHttpRequestService'
                smallType = 'get'
            strutsAction_object.set_type(_type)
             
            strutsAction_object.set_parent(sourceCode_object)
            actionFullname = fullname + '/' + _type + '/' + actionText
            actionDisplayName = displayName + '.' + smallType + '.' + actionText
            if actionFullname in guids:
                cmpt = guids[actionFullname]
                guids[actionFullname] = cmpt + 1
                actionFullname += ('_' + str(cmpt))
            else:
                guids[actionFullname] = 2
            strutsAction_object.set_guid(actionFullname)
            strutsAction_object.set_fullname(actionDisplayName)
            strutsAction_object.save()
            self.nbStrutsActions += 1
            if strutsAction.value:
                position = strutsAction.value.create_bookmark(file)
            else:
                position = strutsAction.action.create_bookmark(file)
            strutsAction_object.save_position(position)
            strutsAction_object.save_property('CAST_ResourceService.uri', actionText)
            self.create_link('callLink', sourceCode_object, strutsAction_object, position)
                   
    def create_applet_references(self, htmlContent, fullname, displayName, sourceCode_object, file):
        
        guids = {}
        for appletReference in htmlContent.appletReferences:
            appletReference_object = cast.analysers.CustomObject()
            cast.analysers.log.debug('Creating Applet reference ' + str(appletReference.className))
            appletReference_object.set_name(appletReference.className)
            appletReference_object.set_type('CAST_HTML5_AppletClassReference')
            appletReference_object.set_parent(sourceCode_object)
            appletRefFullname = fullname + '/CAST_HTML5_AppletClassReference/' + appletReference.className
            appletRefdisplayName = displayName + '.' + appletReference.className
            if appletRefFullname in guids:
                cmpt = guids[appletRefFullname]
                guids[appletRefFullname] = cmpt + 1
                appletRefFullname += ('_' + str(cmpt))
            else:
                guids[appletRefFullname] = 2
            appletReference_object.set_guid(appletRefFullname)
            appletReference_object.set_fullname(appletRefdisplayName)
            appletReference_object.save()
            self.nbAppletReferences += 1
            position = appletReference.ast.create_bookmark(file)
            appletReference_object.save_position(position)
            self.create_link('callLink', sourceCode_object, appletReference_object, position)
                   
# Deactivated because done on JEE side
#     def create_bean_method_references(self, htmlContent, fullname, sourceCode_object, file):
#         
#         guids = {}
#         for beanMethod in htmlContent.beanMethodReferences:
#             name = beanMethod.methodName[2:-1]
#             beanMethodReference_object = cast.analysers.CustomObject()
#             cast.analysers.log.debug('Creating bean method reference ' + str(beanMethod.methodName))
#             beanMethodReference_object.set_name(name)
#             beanMethodReference_object.set_type('CAST_HTML5_BeanMethodReference')
#             beanMethodReference_object.set_parent(sourceCode_object)
#             beanMethodRefFullname = fullname + '/CAST_HTML5_BeanMethodReference/' + name
#             if beanMethodRefFullname in guids:
#                 cmpt = guids[beanMethodRefFullname]
#                 guids[beanMethodRefFullname] = cmpt + 1
#                 beanMethodRefFullname += ('_' + str(cmpt))
#             else:
#                 guids[beanMethodRefFullname] = 2
#             beanMethodReference_object.set_guid(beanMethodRefFullname)
#             beanMethodReference_object.set_fullname(beanMethodRefFullname)
#             beanMethodReference_object.save()
#             self.nbBeanMethodReferences += 1
#             position = beanMethod.ast.create_bookmark(file)
#             beanMethodReference_object.save_position(position)
#             beanMethodReference_object.save_property('CAST_EL_Expression.expression', beanMethod.methodName)
#             self.create_link('callLink', sourceCode_object, beanMethodReference_object, position)
        
    def preanalyze_jsp_file(self, file):
    
        cast.analysers.log.info('Preanalyze file ' + file.get_path())
        try:    
            text = html5_open_source_file(file.get_path(), False)
        except:
            cast.analysers.log.warning('Problem when processing ' + file.get_path())
            cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))
            return
        taglibs = {}
        html_parser.preanalyse_jsp(self, text, taglibs)
        if taglibs:
            self.taglibsByJspFullpath[file.get_path()] = taglibs
        
    def analyze_jsp_file(self, file, suspensionLinks, extension = None):
    
        cast.analysers.log.info('Starting file ' + file.get_path())

        html5ContentType = 'CAST_HTML5_JSP_Content'
        startContentBroadcastMsg = 'start_jsp_content'
        startSourceCodeBroadcastMsg = 'start_jsp_source_code'
        endContentBroadcastMsg = 'end_jsp_content'
        endSourceCodeBroadcastMsg = 'end_jsp_source_code'
        startJavascriptContentBroadcastMsg = 'start_jsp_javascript_content'
        if extension:
            extensionLower = extension.lower()
            if extensionLower == 'asp':
                html5ContentType = 'CAST_HTML5_ASP_Content'
                startContentBroadcastMsg = 'start_asp_content'
                startSourceCodeBroadcastMsg = 'start_asp_source_code'
                endContentBroadcastMsg = 'end_asp_content'
                endSourceCodeBroadcastMsg = 'end_asp_source_code'
                startJavascriptContentBroadcastMsg = 'start_asp_javascript_content'
            elif extensionLower == 'aspx':
                html5ContentType = 'CAST_HTML5_ASPX_Content'
                startContentBroadcastMsg = 'start_aspx_content'
                startSourceCodeBroadcastMsg = 'start_aspx_source_code'
                endContentBroadcastMsg = 'end_aspx_content'
                endSourceCodeBroadcastMsg = 'end_aspx_source_code'
                startJavascriptContentBroadcastMsg = 'start_aspx_javascript_content'
            elif extensionLower in ['cshtml', 'html']:
                html5ContentType = 'CAST_HTML5_CSHTML_Content'
                startContentBroadcastMsg = 'start_cshtml_content'
                startSourceCodeBroadcastMsg = 'start_cshtml_source_code'
                endContentBroadcastMsg = 'end_cshtml_content'
                endSourceCodeBroadcastMsg = 'end_cshtml_source_code'
                startJavascriptContentBroadcastMsg = 'start_cshtml_javascript_content'
            elif extensionLower == 'htc':
                html5ContentType = 'CAST_HTML5_HTC_Content'
                startContentBroadcastMsg = 'start_htc_content'
                startSourceCodeBroadcastMsg = 'start_htc_source_code'
                endContentBroadcastMsg = 'end_htc_content'
                endSourceCodeBroadcastMsg = 'end_htc_source_code'
                startJavascriptContentBroadcastMsg = 'start_htc_javascript_content'
        
        if not self.config.objectTypes.sourceCodeType:
            sourceCode_object = file
        else:
            sourceCode_object = cast.analysers.CustomObject()
            sourceCode_object.set_name(os.path.basename(file.get_path()))
            sourceCode_object.set_type(html5ContentType)
            fullname = file.get_path() + '/' + html5ContentType
            displayName = file.get_path()
            sourceCode_object.set_parent(file)
            sourceCode_object.set_guid(fullname)
            sourceCode_object.set_fullname(displayName)
            sourceCode_object.save()
            
        try:    
            text = html5_open_source_file(file.get_path(), False)
        except:
            cast.analysers.log.warning('Problem when processing ' + file.get_path())
            cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))
            return
        
        self.broadcast(startContentBroadcastMsg, file)    
        self.broadcast(startSourceCodeBroadcastMsg, sourceCode_object)
        
        htmlContent = HtmlContent(file, sourceCode_object)
        self.htmlContentsByFile[file] = htmlContent
        htmlBasename = os.path.basename(file.get_path())
        if not htmlBasename in self.htmlContentsByName:
            l = []
            self.htmlContentsByName[htmlBasename] = l
        else:
            l = self.htmlContentsByName[htmlBasename]
        l.append(htmlContent)
        violations = Violations()
        objectDatabaseProperties = html_parser.analyse(self, text, htmlContent, violations)
        
        if sourceCode_object != file:
            sourceCode_object.save_property('metric.CodeLinesCount', objectDatabaseProperties.codeLinesCount)
            if objectDatabaseProperties.headerCommentLinesCount > 0:
                sourceCode_object.save_property('metric.LeadingCommentLinesCount', objectDatabaseProperties.headerCommentLinesCount)
            if objectDatabaseProperties.bodyCommentLinesCount > 0:
                sourceCode_object.save_property('metric.BodyCommentLinesCount', objectDatabaseProperties.bodyCommentLinesCount)
        
        if self.isUADeactivated:
            file.save_property('metric.CodeLinesCount', objectDatabaseProperties.codeLinesCount)
            if objectDatabaseProperties.headerCommentLinesCount > 0:
                file.save_property('metric.LeadingCommentLinesCount', objectDatabaseProperties.headerCommentLinesCount)
            if objectDatabaseProperties.bodyCommentLinesCount > 0:
                file.save_property('metric.BodyCommentLinesCount', objectDatabaseProperties.bodyCommentLinesCount)

        self.create_services(htmlContent, file)
        violations.save()
        
        if self.config.objectTypes.sourceCodeType:
            sourceCode_object.save_property('checksum.CodeOnlyChecksum', objectDatabaseProperties.checksum)
            if objectDatabaseProperties.bookmarks:
                sourceCode_object.save_position(objectDatabaseProperties.bookmarks[0])
            
        for jsFileName, _ in htmlContent.get_js_files().items():
            if jsFileName in self.htmlContentsByJS:
                l = self.htmlContentsByJS[jsFileName]
            else:
                l = []
                self.htmlContentsByJS[jsFileName] = l
            l.append(htmlContent)
            
        self.create_struts_actions(htmlContent, fullname, displayName, sourceCode_object, file)
        self.create_applet_references(htmlContent, fullname, displayName, sourceCode_object, file)
# Deactivated because done on JEE side
#         self.create_bean_method_references(htmlContent, fullname, sourceCode_object, file)
             
        globalVariablesByName = self.globalVariablesByName
        globalFunctionsByName = self.globalFunctionsByName
        globalClassesByName = self.globalClassesByName
        jsContentsByFilename = self.jsContentsByFilename

        htmlBasename = os.path.basename(file.get_path())
        dotIndex = htmlBasename.rfind('.')
        if dotIndex:
            htmlBasename = htmlBasename[:dotIndex]
        config = self.configJSInHtml
        jsContents = []
        for fragment in htmlContent.get_javascript_fragments():
            interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, None, False, None)
            text = preprocess_html_fragment(fragment.get_text())
            interpreter.jsContent = analyse_preprocess(interpreter, text, None, fragment.get_begin_line(), fragment.get_begin_column())
            jsContents.append(interpreter.jsContent)

        cast.analysers.log.info('Full parsing of file ' + file.get_path())
        cmpt = 0
        lastJsContent = None
        for fragment in htmlContent.get_javascript_fragments():
            jsContent = jsContents[cmpt]
            self.jsContentsByFilename[file.get_path()] = jsContent
            self.jsContentsByFilename[file.get_path()].add_html_calling_file(htmlContent)
#             interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, jsContent, True, None, self.htmlContentsByName)
            interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, jsContent, True, self.htmlContentsByJS, self.htmlContentsByName)
            text = preprocess_html_fragment(fragment.get_text())
            if '.cshtml' in file.get_path():
                text = self.preprocess_javascript_razor(text)
            analyse_fullprocess(interpreter, text, None, fragment.get_begin_line(), fragment.get_begin_column() + 1)
            if cmpt == 0:
                jsContent.create_cast_objects(file, sourceCode_object, htmlBasename)
                self.create_link('callLink', sourceCode_object, jsContent.kbObject, objectDatabaseProperties.bookmarks[0])
            else:
                jsContent.create_cast_objects(file, sourceCode_object, htmlBasename, lastJsContent.kbObject)
            self.create_services(jsContent, file)
            jsContent.update_globals_with_cast_objects(globalVariablesByName, globalFunctionsByName)
            jsContent.create_cast_links(file, suspensionLinks)

            self.broadcast(startJavascriptContentBroadcastMsg, jsContent)

            lastJsContent = jsContent
            self.clean_jsContent(jsContent)
            cmpt += 1

        self.resolve_html_values(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, suspensionLinks, sourceCode_object, file)

#         for fragment in htmlContent.get_javascript_values():
#             try:
#                 interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, None, False, None)
#                 jsContent = analyse_preprocess(interpreter, fragment.get_text(), fragment.get_begin_line(), fragment.get_begin_column())
#                 interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, jsContent, True, None, self.htmlContentsByName)
#                 analyse_fullprocess(interpreter, fragment.get_text(), fragment.get_begin_line(), fragment.get_begin_column())
#                 lBefore = len(suspensionLinks)
#                 jsContent.create_cast_links(file, suspensionLinks)
#                 lAfter = len(suspensionLinks)
#                 if lAfter > lBefore:
#                     for suspensionLink in suspensionLinks[lBefore:]:
#                         suspensionLink.callerKbObject = sourceCode_object
#                 self.clean_jsContent(jsContent)
#             except:
#                 pass
            
        self.analyze_html_css_fragments(file, htmlContent)
            
        self.broadcast(endSourceCodeBroadcastMsg, sourceCode_object)    
        self.broadcast(endContentBroadcastMsg, htmlContent)
        
        return sourceCode_object

    def resolve_html_values(self, htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, suspensionLinks, sourceCode_object, file):

        for fragment in htmlContent.get_javascript_values():
            try:
                interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, None, False, None)
                interpreter.resolvingHtmlValues = True
                jsContent = analyse_preprocess(interpreter, fragment.get_text(), None, fragment.get_begin_line(), fragment.get_begin_column())
                interpreter = JavascriptInterpreter(htmlContent, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, jsContent, True, None, self.htmlContentsByName)
                jsContent.set_kb_symbol(htmlContent.htmlSourceCode)
                interpreter.resolvingHtmlValues = True
                analyse_fullprocess(interpreter, fragment.get_text(), None, fragment.get_begin_line(), fragment.get_begin_column() + 1)
                lBefore = len(suspensionLinks)
                jsContent.create_cast_links(file, suspensionLinks)
                lAfter = len(suspensionLinks)
                if lAfter > lBefore:
                    for suspensionLink in suspensionLinks[lBefore:]:
                        suspensionLink.callerKbObject = sourceCode_object
                self.clean_jsContent(jsContent)
            except:
                pass
        
    def initialize_analysis_root(self, rootDir):

#         for _, jsContent in self.htmlContentsByFile.items():
#             jsContent.empty()

        self.jsFiles = []
        self.jsxFiles = []
        rootDir.get_js_files(self.jsFiles)
        rootDir.get_jsx_files(self.jsxFiles)
        self.htmlFiles = OrderedDict()
        self.cssFiles = OrderedDict()
        rootDir.get_html_files(self.htmlFiles)
        rootDir.get_css_files(self.cssFiles)
        self.jspFiles = OrderedDict()
        rootDir.get_jsp_files(self.jspFiles)
        self.aspFiles = OrderedDict()
        rootDir.get_asp_files(self.aspFiles)
        self.globalVariablesByName = OrderedDict()   # key=name/value=list because may be 2 variables with same name 
        self.globalFunctionsByName = OrderedDict()   # key=name/value=list because may be 2 functions with same name
        self.jsContentsByFilename = OrderedDict()        # key=filename/value=jsContent
        self.jsFilesByBasename = OrderedDict()    # key=file basename/value=list of files
        self.jsxFilesByBasename = OrderedDict()    # key=file basename/value=list of files
        self.htmlContentsByFile = OrderedDict()      # key=file/value=htmlContent
        self.htmlContentsByJS = OrderedDict()        # key=js filename/value=htmlContent list of html files including jsfile
        self.htmlContentsByName = OrderedDict()        # key=html basename/value=htmlContent list of html files

        self.webSockets = [] # must be kept because url needs evaluation and evaluation can be done only when all ast has been read
        self.openCalls = []
        self.XMLHttpRequests = []
        self.httpRequests = []
        self.eventSourceRequests = []
        self.executeSqls = []
        self.globalClassesBroadcasted = False
        
    def analyze_root(self, rootDir):

        cast.analysers.log.info('Start analyzing root ' + rootDir.name)
        self.initialize_analysis_root(rootDir)

        for jsFile in self.jsFiles:
            self.preprocess_file(jsFile, 'js')

        for jsxFile in self.jsxFiles:
            self.preprocess_file(jsxFile, 'jsx')
                         
        suspensionLinks = []
         
        for _, htmlFile in self.htmlFiles.items():
            self.preprocess_file(htmlFile, 'html', suspensionLinks)
        for _, cssFile in self.cssFiles.items():
            self.preprocess_file(cssFile, 'css', suspensionLinks)
        for _, jspFiles in self.jspFiles.items():
            for jspFile in jspFiles:
                jspFile.sourceCode = self.preprocess_file(jspFile.file, 'jsp', suspensionLinks)
        for _, aspFiles in self.aspFiles.items():
            for aspFile in aspFiles:
                aspFile.sourceCode = self.preprocess_file(aspFile.file, 'asp', suspensionLinks)
                if aspFile.file.get_path().lower().endswith(('.cshtml', '.cshtml.html')):
                    try:
                        self.process_razor_file(aspFile)
                    except:
                        pass
        self.resolve_html_links()
 
 
        self.jsp_global_resolution()
         
        for _, htmlContent in self.htmlContentsByFile.items():
            htmlContent.resolve_absolute_js_files(self.jsFilesByBasename)
            for filename, jsFile in htmlContent.get_js_files().items():
                if filename in self.jsContentsByFilename:
                    try:
                        self.jsContentsByFilename[filename].add_html_calling_file(htmlContent)
                    except:
                        # In jsp cases, self.jsContentsByFilename[filename] contains CustomObjects
                        cast.analysers.log.debug('Internal issue when add_html_calling_file on ' + str(filename))
#                         cast.analysers.log.debug(traceback.format_exc())
 
        self.inheritance_resolution()
        
        if not self.globalClassesBroadcasted:
            self.broadcast('global_functions', self.globalFunctionsByName)
            self.broadcast('global_variables', self.globalVariablesByName)
            self.broadcast('global_classes', self.globalClassesByName)
            self.globalClassesBroadcasted = True
 
        for file in self.jsFiles:
             
            cast.analysers.log.info('Full parsing of file ' + file.get_path())

            try:
                text = html5_open_source_file(file.get_path())
            except:
                cast.analysers.log.warning('Problem when full parsing ' + file.get_path())
                cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))
                continue
                  
            if file.get_path() in self.jsContentsByFilename:
              
                self.config.clean()
                interpreter = JavascriptInterpreter(file, self.config, self.jsContentsByFilename, self.globalVariablesByName, self.globalFunctionsByName, self.globalClassesByName, self.jsContentsByFilename[file.get_path()], True, self.htmlContentsByJS, self.htmlContentsByName)
 
                try:
                    if 'React' in text:
                        lexer = JSXLexer
                    else:
                        lexer = None
                    jsContent = analyse_fullprocess(interpreter, text, lexer, 1, 1)
                    jsContent.create_cast_objects(file)
                    self.create_services(jsContent, file)
                    jsContent.update_globals_with_cast_objects(self.globalVariablesByName, self.globalFunctionsByName)
                    analyse_process_diags(jsContent, self.globalClassesByName, 1, 1)
                    jsContent.create_cast_links(file, suspensionLinks)
                    self.config.violations.save()
                     
                    for htmlContent in jsContent.get_html_calling_files():
                        textWithPos =  htmlContent.has_js_file(jsContent.file.get_path())
                        if textWithPos:
                            self.create_link('includeLink', htmlContent.htmlSourceCode, jsContent.get_kb_object(), textWithPos.create_bookmark(htmlContent.file))
                        else:
                            self.create_link('includeLink', htmlContent.htmlSourceCode, jsContent.get_kb_object())
     
                    self.broadcast('start_javascript_content', jsContent)
                    self.clean_jsContent(jsContent)
                    self.jsContentsByFilename[file.get_path()] = jsContent
                    memory()
                except Exception as e:
                    cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))
 
        for file in self.jsxFiles:
             
            cast.analysers.log.info('Full parsing of file ' + file.get_path())
            try:
                text = html5_open_source_file(file.get_path())
            except:
                cast.analysers.log.warning('Problem when full parsing ' + file.get_path())
                cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))
                continue
                  
            if file.get_path() in self.jsContentsByFilename:
              
                self.config.clean()
                interpreter = JavascriptInterpreter(file, self.config, self.jsContentsByFilename, self.globalVariablesByName, self.globalFunctionsByName, self.globalClassesByName, self.jsContentsByFilename[file.get_path()], True, self.htmlContentsByJS, self.htmlContentsByName)
 
                try:
                    jsContent = analyse_fullprocess(interpreter, text, JSXLexer, 1, 1)
                    jsContent.create_cast_objects(file)
                    self.create_services(jsContent, file)
                    jsContent.update_globals_with_cast_objects(self.globalVariablesByName, self.globalFunctionsByName)
                    analyse_process_diags(jsContent, self.globalClassesByName, 1, 1)
                    jsContent.create_cast_links(file, suspensionLinks)
                    self.config.violations.save()
                     
                    for htmlContent in jsContent.get_html_calling_files():
                        self.create_link('includeLink', htmlContent.htmlSourceCode, jsContent.get_kb_object())
     
                    self.broadcast('start_javascript_content', jsContent)
                    self.clean_jsContent(jsContent)
                    self.jsContentsByFilename[file.get_path()] = jsContent
                    memory()
                except Exception as e:
                    cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))

        for suspensionLink in suspensionLinks:
            if suspensionLink.callee:
                try:
                    calleeKbObject = suspensionLink.callee.get_kb_object()
                except:
                    calleeKbObject = suspensionLink.callee
                if calleeKbObject:
                    self.create_link(suspensionLink.type, suspensionLink.callerKbObject, calleeKbObject, suspensionLink.bookmark)

    def inheritance_resolution(self):
        for _, classes in self.globalClassesByName.items():
            for cl in classes:
                if not cl.inheritanceIdentifier:
                    continue
                if cl.inheritanceIdentifier.get_resolutions():
                    continue
                if not cl.inheritanceIdentifier.get_name() in self.globalClassesByName:
                    continue
                foundClasses = self.globalClassesByName[cl.inheritanceIdentifier.get_name()]
                for foundCl in foundClasses:
                    if foundCl.get_kb_symbol().get_fullname() == cl.inheritanceIdentifier.get_fullname():
                        cl.inheritanceIdentifier.add_resolution(foundCl.get_kb_symbol(), 'inheritLink')
                 
    def resolve_html_links(self):
        
        for _, l in self.htmlContentsByName.items():
            for htmlContent in l:
                for htcRef in htmlContent.get_htc_references():
                    filepath = htcRef.text
                    basename = os.path.basename(filepath)
                    if basename in self.htmlContentsByName:
                        l = self.htmlContentsByName[basename]
                        for calleeContent in l:
                            if calleeContent.file.get_path() == filepath:
                                self.create_link('useLink', htmlContent.htmlSourceCode, calleeContent.htmlSourceCode, htcRef.create_bookmark(htmlContent.file))
                                break
    
#     Creates services contained in jsContent: XMLHTTPService, WebSocket
    def create_services(self, jsContent, file):

        cast.analysers.log.debug('Creating services')
        if type(jsContent) is JsContent:
            for openCall in jsContent.openCalls:
                openCall.kbParent = jsContent.get_kb_object()
                self.openCalls.append(openCall)
            for httpReq in jsContent.xmlHttpRequests:
                self.XMLHttpRequests.append(httpReq)
            for httpReq in jsContent.httpRequests:
                self.httpRequests.append(httpReq)
            for httpReq in jsContent.eventSourceRequests:
                self.eventSourceRequests.append(httpReq)
            for executeSql in jsContent.executeSqls:
                self.executeSqls.append(executeSql)
            for webSocket in jsContent.webSockets:
                webSocket.kbParent = jsContent.get_kb_object()
                self.webSockets.append(webSocket)
        else:
            for httpReq in jsContent.httpRequests:
                self.httpRequests.append(httpReq)

#     Creates services contained in jsContent: XMLHTTPService
    def create_XMLHttpRequest(self, openCall):

        try:
            nb = 0
            if not openCall.urlValues:
                try:
                    evals = openCall.url.evaluate(None, None, None, '{}')
                    if evals:
                        openCall.urlValues = []
                        for ev in evals:
                            end = 0
                            while '${' in ev:
                                begin = ev.find('${', end)
                                end = ev.find('}', begin)
                                if end > 0:
                                    ev = ev[:begin] + '{}' + ev[end+1:]
                                else:
                                    break
                            if ev.startswith('~/'):
                                openCall.urlValues.append(ev[2:])
                            else:
                                openCall.urlValues.append(ev)
                except:
                    cast.analysers.log.debug('Internal issue in create_XMLHttpRequest: ' + str(traceback.format_exc()))
            if not openCall.urlValues:
                return nb
     
            identifierCall = openCall.ast.identifier_call
            if not identifierCall.get_resolutions():
                return nb
                 
            if not openCall.urlValues:
                openCall.urlValues = []
                openCall.urlValues.append('')
                 
            for url in openCall.urlValues:
                if openCall.requestType == 'GET':
                    objectType = self.config.objectTypes.getXMLHttpRequestType
                elif openCall.requestType == 'POST':
                    objectType = self.config.objectTypes.postXMLHttpRequestType
                elif openCall.requestType == 'UPDATE':
                    objectType = self.config.objectTypes.updateXMLHttpRequestType
                elif openCall.requestType == 'DELETE':
                    objectType = self.config.objectTypes.deleteXMLHttpRequestType
                else:
                    objectType = None
                if not objectType:
                    continue
                for _ in identifierCall.get_resolutions():
                    obj = cast.analysers.CustomObject()
                    name = get_short_uri(url)
                    if not name or name == '{}':
                        continue
                    obj.set_name(name)
                    obj.set_type(objectType)
                    obj.set_parent(openCall.caller.get_kb_object())
                    fullname = openCall.caller.get_kb_symbol().get_kb_fullname() + '/' + objectType + '/' + name
                    displayname = openCall.caller.get_kb_symbol().get_display_fullname() + '.' + openCall.requestType.lower() + '.' + name
                    n = 0
                    if fullname in self.xmlHttpRequestGuids:
                        n = self.xmlHttpRequestGuids[fullname] + 1
                        finalFullname = fullname + '_' + str(n)
                    else:
                        finalFullname = fullname
                    self.xmlHttpRequestGuids[fullname] = n
                    obj.set_guid(finalFullname)
                    obj.set_fullname(displayname)
                    obj.save()
                    obj.save_property('CAST_ResourceService.uri', url)
                    crc = compute_crc(openCall.ast)
                    obj.save_property('checksum.CodeOnlyChecksum', crc)
                    obj.save_position(openCall.ast.create_bookmark(openCall.file))
         
                    self.create_link('callLink', openCall.caller.get_kb_object(), obj)
                    nb += 1
                         
                    break
            return nb
        except:
            cast.analysers.log.debug('Internal issue in create_XMLHttpRequest: ' + str(traceback.format_exc()))
            return nb
        
    def create_HttpRequestLinkToFile(self, url, file, caller, bm):
        
        filename = url
        if '.html#' in url:
            indexDiese = url.rfind('.html#') + 5
        elif '.html/' in url:
            indexDiese = url.rfind('.html/') + 5
        elif url.endswith('.html'):
            indexDiese = url.rfind('.html') + 5
        elif '.htm#' in url:
            indexDiese = url.rfind('.htm#') + 4
        elif '.htm/' in url:
            indexDiese = url.rfind('.htm/') + 4
        elif url.endswith('.htm'):
            indexDiese = url.rfind('.htm') + 4
        elif '.jsp#' in url:
            indexDiese = url.rfind('.jsp#') + 4
        elif '.jsp/' in url:
            indexDiese = url.rfind('.jsp/') + 4
        elif url.endswith('.jsp'):
            indexDiese = url.rfind('.jsp') + 4
        elif '.asp#' in url:
            indexDiese = url.rfind('.asp#') + 4
        elif '.asp/' in url:
            indexDiese = url.rfind('.asp/') + 4
        elif url.endswith('.asp'):
            indexDiese = url.rfind('.asp') + 4
        elif '.css#' in url:
            indexDiese = url.rfind('.css#') + 4
        elif '.css/' in url:
            indexDiese = url.rfind('.css/') + 4
        elif url.endswith('.css'):
            indexDiese = url.rfind('.css') + 4
        elif '.ico/' in url:
            indexDiese = url.rfind('.ico/') + 4
        elif url.endswith('.ico'):
            indexDiese = url.rfind('.ico') + 4
        else:
            indexDiese = 0
        if indexDiese > 0:
            filename = url[:indexDiese]
        filename = filename.lstrip('/')
        filename = os.path.normpath(filename)

        res = False
        httpReqDir = os.path.dirname(file.get_path())
        searchedFilepath = os.path.join(httpReqDir, filename)
        if isinstance(caller, cast.analysers.CustomObject):
            callerObject = caller
        else:
            callerObject = caller.get_kb_object()
        if os.path.exists(searchedFilepath):
            if searchedFilepath in self.htmlFiles:
                htmlContent = self.htmlContentsByFile[self.htmlFiles[searchedFilepath]]
                if htmlContent.htmlSourceCode:
                    self.create_link('callLink', callerObject, htmlContent.htmlSourceCode, bm)
                return True
            elif searchedFilepath in self.cssFiles:
                cssContent = self.cssFiles[searchedFilepath]
                if cssContent.cssSourceCode:
                    self.create_link('callLink', callerObject, cssContent.cssSourceCode, bm)
                return True
            basename = os.path.basename(searchedFilepath)
            if basename in self.jspFiles:
                for jspFile in self.jspFiles[basename]:
                    if jspFile.file.get_path() == searchedFilepath:
                        if jspFile.sourceCode:
                            self.create_link('callLink', callerObject, jspFile.sourceCode, bm)
                        res = True
                        break
            elif basename in self.aspFiles:
                for aspFile in self.aspFiles[basename]:
                    if aspFile.file.get_path() == searchedFilepath:
                        if aspFile.sourceCode:
                            self.create_link('callLink', callerObject, aspFile.sourceCode, bm)
                        res = True
                        break
            return True
        
        for wa in self.webappsFolders:
            if not file.get_path().startswith(wa):
                continue
            searchedFilepath = os.path.join(wa, filename)
            if not os.path.exists(searchedFilepath):
                break
                
            if searchedFilepath in self.htmlFiles:
                htmlContent = self.htmlContentsByFile[self.htmlFiles[searchedFilepath]]
                if htmlContent.htmlSourceCode:
                    self.create_link('callLink', callerObject, htmlContent.htmlSourceCode, bm)
                res = True
                break
            elif searchedFilepath in self.cssFiles:
                cssContent = self.cssFiles[searchedFilepath]
                if cssContent.cssSourceCode:
                    self.create_link('callLink', callerObject, cssContent.cssSourceCode, bm)
                res = True
                break
            
            basename = os.path.basename(searchedFilepath)
            if basename in self.jspFiles:
                for jspFile in self.jspFiles[basename]:
                    if jspFile.file.get_path() == searchedFilepath:
                        if jspFile.sourceCode:
                            self.create_link('callLink', callerObject, jspFile.sourceCode, bm)
                        res = True
                        break
            elif basename in self.aspFiles:
                for aspFile in self.aspFiles[basename]:
                    if aspFile.file.get_path() == searchedFilepath:
                        if aspFile.sourceCode:
                            self.create_link('callLink', callerObject, aspFile.sourceCode, bm)
                        res = True
                        break
            break
        if not res and './' in url:
            return True
        
        return res
       
    def compute_url_prefix(self, filepath, url):

        if url.startswith('http'):
            return url, url
        
        urlWithPrefix = url
        shortUrl = url
        dirname = filepath
        onePoint = False
        twoPoints = False
        if url.startswith('../'):
            onePoint = True
            dirname = os.path.dirname(dirname)
            if url.startswith('../../'):
                onePoint = False
                twoPoints = True
                dirname = os.path.dirname(dirname)
        prefix = self.get_url_prefix(dirname)
        if prefix:
            if shortUrl.startswith('/'):
                shortUrl = prefix + shortUrl
                urlWithPrefix = prefix + urlWithPrefix
            else:
                if onePoint:
                    shortUrl = prefix + '/' + shortUrl[3:]
                    urlWithPrefix = prefix + '/' + urlWithPrefix[3:]
                elif twoPoints:
                    shortUrl = prefix + '/' + shortUrl[6:]
                    urlWithPrefix = prefix + '/' + urlWithPrefix[6:]
                else:
                    shortUrl = prefix + '/' + shortUrl
                    urlWithPrefix = prefix + '/' + urlWithPrefix
        return urlWithPrefix, shortUrl

    def create_Request(self, httpReq, getType, postType = None, putType = None, deleteType = None):

        nb = 0
        astCallers = []
        fullname = ''
        
        try:
            if not httpReq.urlValues:
                try:
                    if httpReq.ovUrlName and not httpReq.url.is_string():
                        evals = get_uri_ov_evaluation([httpReq.ovUrlName, httpReq.ovTypeName], httpReq.url, '{}', astCallers)
                    else:
                        evals = get_uri_evaluation(httpReq.url, '{}', astCallers)
                    if evals:
                        httpReq.urlValues = []
                        httpReq.methodValues = []
                        cmpt = 0
                        for _evals in evals:
                            if httpReq.ovUrlName and not httpReq.url.is_string():
                                ev = _evals[httpReq.ovUrlName].value
                                evMethod = _evals[httpReq.ovTypeName].value.upper()
                            else:
                                ev = _evals
                                evMethod = httpReq.requestType.upper()
                            if not '@' in ev and not 'Url.' in ev:  # avoid services already created with razor
                                httpReq.urlValues.append(ev)
                                httpReq.methodValues.append(evMethod)
                                if httpReq.ovUrlName:
                                    node = _evals[httpReq.ovUrlName].ast_nodes[0]
                                    for astNode in _evals[httpReq.ovUrlName].ast_nodes:
                                        if astNode.is_function_call_part():
                                            node = astNode
                                            break
                                    astCallers.append(node);
                                else:
                                    astCallers.append(astCallers[cmpt])
                            cmpt += 1
                    else:
                        httpReq.urlValues = []
                        httpReq.methodValues = []
                        httpReq.urlValues.append('{}/')
                        httpReq.methodValues.append(httpReq.requestType.upper())
                except:
                    cast.analysers.log.debug(str(traceback.format_exc()))
                
            if not httpReq.urlValues:
                return nb
     
            if not httpReq.urlValues:
                httpReq.urlValues = []
                httpReq.urlValues.append('')
               
            i = 0  
            for url in httpReq.urlValues:
                # prepa to struts modules STRUTS-18
                urlWithPrefix, shortUrl = self.compute_url_prefix(os.path.dirname(httpReq.file.get_path()), url)
                
                if '?' in shortUrl:
                    shortUrl = shortUrl[:shortUrl.find('?')]
                    if shortUrl and not shortUrl.endswith('/'):
                        shortUrl += '/'
                if any(shortUrl.endswith(x) for x in ['.html/', '.html', '.htm/', '.htm', '.jsp/', '.jsp', '.asp/', '.asp', '.aspx/', '.aspx', '.cshtml/', '.cshtml', '.htc/', '.htc', '.css/', '.css', '.ico/', '.ico', '.png/', '.png', '.doc/', '.doc', '.pdf/', '.pdf', '.xml/', '.xml', '.jpg/', '.jpg', '.gif/', '.gif']) or any((x in url) for x in ['.html#', '.htm#', '.jsp#', '.asp#', '.aspx#', '.cshtml#', '.htc#']):
                    try:
                        res = self.create_HttpRequestLinkToFile(shortUrl, httpReq.file, httpReq.caller, httpReq.ast.create_bookmark(httpReq.file))
                    except:
                        cast.analysers.log.debug('Internal issue in HttpRequestLinkToFile')
                        cast.analysers.log.debug(str(traceback.format_exc()))
                    if res:
                        i += 1
                        continue
                if shortUrl.startswith('{{') or shortUrl.startswith('mailto:') or shortUrl.endswith('>/'):
                    i += 1
                    continue
                
                _method = httpReq.methodValues[i].lower()
                if httpReq.methodValues[i] in ['POST', 'document.forms.action']:
                    objectType = postType if postType else getType
                elif httpReq.methodValues[i] == 'PUT':
                    objectType = putType if putType else getType
                elif httpReq.methodValues[i] == 'DELETE':
                    objectType = deleteType if deleteType else getType
                else:
                    objectType = getType
    
                name = get_short_uri(shortUrl)
                if not name or name == '{}' or name.endswith('.css'):
                    i += 1
                    continue
                obj = cast.analysers.CustomObject()
                obj.set_name(name)
                obj.set_type(objectType)
                obj.set_parent(httpReq.caller.get_kb_object())
                try:
                    # httpReq.caller could be a function or an HTMLContent
                    fullname = httpReq.caller.get_kb_symbol().get_kb_fullname() + '/' + objectType + '/' + name
                    displayname = httpReq.caller.get_kb_symbol().get_display_fullname() + '.' + _method + '.' + name
                except:
                    fullname = httpReq.file.get_path() + '/' + objectType + '/' + name
                    displayname = httpReq.file.get_path() + '.' + _method + '.' + name
                n = 0
                if fullname in self.xmlHttpRequestGuids:
                    n = self.xmlHttpRequestGuids[fullname] + 1
                    finalFullname = fullname + '_' + str(n)
                else:
                    finalFullname = fullname
                self.xmlHttpRequestGuids[fullname] = n
                obj.set_guid(finalFullname)
                obj.set_fullname(displayname)
                obj.save()
                obj.save_property('CAST_ResourceService.uri', urlWithPrefix)
                crc = compute_crc(httpReq.ast)
                obj.save_property('checksum.CodeOnlyChecksum', crc)
                obj.save_position(httpReq.ast.create_bookmark(httpReq.file))
         
                linkCaller = httpReq.caller.get_kb_object()
                astCaller = None
                try:
                    astCaller = astCallers[i]
                except:
                    astCaller = None
                if astCallers and astCaller:
                    linkCaller = astCaller.get_first_kb_parent().get_kb_object()
                    bm = astCaller.create_bookmark(astCaller.get_file())
                else:
                    bm = httpReq.ast.create_bookmark(httpReq.file)
                self.create_link('callLink', linkCaller, obj, bm)
                
                for listener in httpReq.get_listeners():
                    parent = listener.parent.get_first_kb_parent()
                    self.create_link('callLink', parent, listener, listener.create_bookmark(httpReq.file))
                
                nb += 1
                i += 1
                         
#                 break
        except:
            cast.analysers.log.warning('HTML5-004 Internal issue creating Request (' + str(fullname) + ')')
            try:
                cast.analysers.log.debug(str(astCallers[i]))
            except:
                pass
            cast.analysers.log.debug('Internal issue: ' + str(traceback.format_exc()))
        return nb
                    
    def create_HttpRequest(self, httpReq):
        return self.create_Request(httpReq, self.config.objectTypes.getHttpRequestType, self.config.objectTypes.postHttpRequestType, self.config.objectTypes.putHttpRequestType, self.config.objectTypes.deleteHttpRequestType)
                    
    def create_EventSourceRequest(self, httpReq):
        return self.create_Request(httpReq, self.config.objectTypes.getEventSourceType)

#     Creates services contained in jsContent: WebSocket
    def create_WebSocket(self, webSocket):
        
            nb = 0
            if not webSocket.urlValues:
                try:
                    evals = webSocket.param.evaluate(None, None, None, '{}')
                    if evals:
                        webSocket.urlValues = []
                        for ev in evals:
                            end = 0
                            while '${' in ev:
                                begin = ev.find('${', end)
                                end = ev.find('}', begin)
                                if end > 0:
                                    ev = ev[:begin] + '{}' + ev[end+1:]
                                else:
                                    break
                            if ev.startswith('~/'):
                                webSocket.urlValues.append(ev[2:])
                            else:
                                webSocket.urlValues.append(ev)
                except:
                    pass

            if not webSocket.urlValues:
                webSocket.urlValues = []
                webSocket.urlValues.append('')
            
            for url in webSocket.urlValues:
                
                uris = url.split('/')
                uri = None
                if uris:
                    uri = ''
                    for part in uris:
                        if part:
                            if part.endswith(':'):
                                uri += ( part + '//' )
                            else:
                                uri += ( part + '/' )
                    
                    name = get_short_uri(uri)
                    if not name or name == '{}':
                        continue
                    obj = cast.analysers.CustomObject()
                    obj.set_name(name)
                    obj.set_type(self.config.objectTypes.webSocketType)
                    obj.set_parent(webSocket.caller.get_kb_object())
                    fullname = webSocket.caller.get_kb_symbol().get_kb_fullname() + '/' + self.config.objectTypes.webSocketType + '/' + name
                    displayname = webSocket.caller.get_kb_symbol().get_display_fullname() + '.ws.' + name
                    n = 0
                    if fullname in self.xmlHttpRequestGuids:
                        n = self.xmlHttpRequestGuids[fullname] + 1
                        finalFullname = fullname + '_' + str(n)
                    else:
                        finalFullname = fullname
                    self.xmlHttpRequestGuids[fullname] = n
                    obj.set_guid(finalFullname)
                    obj.set_fullname(displayname)
                    obj.save()
                    obj.save_property('CAST_ResourceService.uri', uri)
                    crc = compute_crc(webSocket.ast)
                    obj.save_property('checksum.CodeOnlyChecksum', crc)
                    obj.save_position(webSocket.ast.create_bookmark(webSocket.file))
    
                    self.create_link('callLink', webSocket.caller.get_kb_object(), obj)
                    nb += 1
                    
                    break
                
            return nb

    def manage_unknown_extensions(self):
        
        if not self.detectedLanguagesByUnknownExtension:
            try:
                f = self.extension.get_intermediate_file("html5.txt")
                cast.analysers.log.info(str(f))
                languageDetectedByExtensionStr = json.dumps({})
                cast.analysers.log.info('writing ' + languageDetectedByExtensionStr)
                f.write(languageDetectedByExtensionStr)
            except:
                cast.analysers.log.warning('Problem when writing the intermediate file')
                cast.analysers.log.warning(traceback.format_exc())
            return

        languageDetectedByExtension = {}
        for extension, filesByLanguage in self.detectedLanguagesByUnknownExtension.items():
            languageDetected = 'None'
            maxNbFiles = 0
            # which language for this extension?
            for language, files in filesByLanguage.items():
                l = len(files)
                if l > maxNbFiles:
                    maxNbFiles = l
                    languageDetected = language
            languageDetectedByExtension[extension] = languageDetected
            if not languageDetected:
                cast.analysers.log.info('Files with extension ' + extension + ' have been detected with no known language.')
                continue
            cast.analysers.log.info('Files with extension ' + extension + ' have been detected as of language ' + languageDetected)
            for files in filesByLanguage.values():
                for file in files:
                    self._start_file(file, languageDetected, True)

        try:
            f = self.extension.get_intermediate_file("html5.txt")
            languageDetectedByExtensionStr = json.dumps(languageDetectedByExtension)
            cast.analysers.log.info('writing ' + languageDetectedByExtensionStr)
            f.write(languageDetectedByExtensionStr)
        except:
            cast.analysers.log.warning('Problem when writing the intermediate file')
            cast.analysers.log.warning(traceback.format_exc())
        
    def end_analysis(self):

        def merge_objects(element1, element2):
            c = {}
            for key1, value1 in element1.items():
                c[key1] = value1
                if key1 in element2:
                    value2 = element2[key1]
                    if type(value1) is dict and type(value2) is dict:
                        d = merge_objects(value1, value2)
                        c[key1] = d
            for key1, value1 in element2.items():
                if not key1 in element1:
                    c[key1] = value1
            return c        
        
        cast.analysers.log.debug('end_analysis')
        
        self.manage_unknown_extensions()
        
        for key, _map in self.configJsonFilesByRootDir.items():
            try:
                self.configJsonObjectByRootDir[key] = {}
                if 'default.json' in _map:
                    try:
                        self.configJsonObjectByRootDir[key] = json.loads(html5_open_source_file(_map['default.json'].get_path()))
                    except:
                        cast.analysers.log.debug(traceback.format_exc())

                for basename, _file in _map.items():
                    if basename == 'default.json':
                        continue
                    try:
                        jsonContent = json.loads(html5_open_source_file(_file.get_path()))
                        self.configJsonObjectByRootDir[key] = merge_objects(self.configJsonObjectByRootDir[key], jsonContent)
                    except:
                        cast.analysers.log.debug(traceback.format_exc())
            except:
                cast.analysers.log.debug(traceback.format_exc())
        set_nodejs_config(self.configJsonObjectByRootDir)
        
        rootDir = None
        if len(self.directories) == 1:
            for _, d in self.directories.items():
                rootDir = d.get_next_web_root_dir()
            
        dirs = []
        
        if rootDir:
            if not rootDir.files:
                for _, d in rootDir.subDirectories.items():
                    dirs.append(d)
            else:
                dirs.append(rootDir)
#         for _, dir in self.directories.items():
#             self.get_web_root_dirs(dir, dirs)

        cast.analysers.log.info('Root directories:')
        for sub in dirs:
            cast.analysers.log.info('  ' + sub.name + ': ' + str(sub.nbHtml) + ' html files, ' + str(sub.nbCss) + ' css files, ' + str(sub.nbJs) + ' js files,' + str(sub.nbJsp) + ' jsp files, ' + str(sub.nbAsp) + ' asp files')

        self.broadcast('start_configuration', self.config)    
                
        for sub in dirs:
            self.broadcast('start_analysis_root', sub.name)
            self.analyze_root(sub)
            self.broadcast('end_analysis_root', sub.name)
            
        self.broadcast_no_param('end_javascript_contents')
        
        nbHttpRequests = 0
        nbExecuteSqls = 0
        nbWebSockets = 0
        nbOpencalls = 0
        cast.analysers.log.debug('create_WebSocket')
        for webSocket in self.webSockets:
            nbWebSockets += self.create_WebSocket(webSocket)
        cast.analysers.log.debug('create_XMLHttpRequest')
        for openCall in self.openCalls:
            nbOpencalls += self.create_XMLHttpRequest(openCall)
        cast.analysers.log.debug('create_HttpRequest')
        for httpReq in self.httpRequests:
            nbHttpRequests += self.create_HttpRequest(httpReq)
        cast.analysers.log.debug('create_EventSourceRequest')
        for httpReq in self.eventSourceRequests:
            nbHttpRequests += self.create_EventSourceRequest(httpReq)
        cast.analysers.log.debug('find_external_links_from_queries')
        for executeSql in self.executeSqls:
            nbExecuteSqls += self.find_external_links_from_queries(executeSql)
         
        cast.analysers.log.info(str(nbWebSockets) + ' HTML5 Web sockets created')
        cast.analysers.log.info(str(nbOpencalls) + ' HTML5 XML HTTP requests created')
        cast.analysers.log.info(str(nbHttpRequests + self.nbStrutsActions) + ' HTML5 HTTP requests created')
        cast.analysers.log.info(str(self.nbRazorServices) + ' HTML5 Razor services created')
        cast.analysers.log.info(str(self.nbAppletReferences) + ' HTML5 applet references created')
        cast.analysers.log.info(str(self.nbBeanMethodReferences) + ' HTML5 bean method references created')
        cast.analysers.log.info('Ending javascript analysis')

    def jsp_global_resolution(self):
        
        for file, htmlContent in self.htmlContentsByFile.items():
            if not file.get_path().endswith(('.jsp', '.jsf', '.jsff', '.jspx')) and not file.get_path().endswith('.asp') and not file.get_path().endswith('.aspx') and not file.get_path().endswith('.htc'):
                continue
            for tile in htmlContent.strutsTiles:
                basename = os.path.basename(tile.text)
                if basename in self.jspFiles:
                    for jspFile in self.jspFiles[basename]:
                        if jspFile.file.get_path().replace('\\', '/').endswith(tile.text):
                            self.create_link('useLink', htmlContent.htmlSourceCode, jspFile.sourceCode, tile.create_bookmark(htmlContent.file))
                elif basename in self.aspFiles:
                    for aspFile in self.aspFiles[basename]:
                        if aspFile.file.get_path().replace('\\', '/').endswith(tile.text):
                            self.create_link('useLink', htmlContent.htmlSourceCode, aspFile.sourceCode, tile.create_bookmark(htmlContent.file))

    def find_external_links_from_queries(self, executeSql):
   
        cast.analysers.log.debug('find_external_links_from_queries')     
        queries = executeSql.query.evaluate()
        if not queries:
            return 0
        
        nb = 0
        for query in queries:
            nb += self.find_external_links_from_query(query, executeSql)
        return nb

    def find_external_links_from_query(self, query, executeSql):
        
        cast.analysers.log.debug('find_external_links_from_query ' + query)     
        func = None
        nb = 0
        
        try:
            func = getattr(cast.analysers.external_link, 'analyse_embedded')
        except AttributeError:
            pass

        if func:
            embeddedResults = func(query)
        else:
            embeddedResults = None
            
        if not embeddedResults or not func:

            tables = extract_tables(query)
            for table in tables:
                tableName = table['name']
                tableOperation = table['operation']
                linkType = None
                if tableOperation == 'SELECT':
                    linkType = 'useSelectLink'
                elif tableOperation == 'DELETE':
                    linkType = 'useDeleteLink'
                else:
                    linkType = 'useLink'
                  
                tablesAreResolved = False
                tbls = None
                if not func:
                    try:
                        tbls = cast.analysers.external_link.find_objects(tableName, 'Database Table')
                        if not tbls:
                            tbls = cast.analysers.external_link.find_objects(tableName, 'Database View')
                        if tbls:
                            tablesAreResolved = True
                    except:
                        pass

                if tbls:
                    for tbl in tbls:
                        if tablesAreResolved:
                            self.create_link(linkType, executeSql.caller, tbl, executeSql.ast.create_bookmark(executeSql.file))
                            nb += 1
                        else:
                            self.create_link(linkType, executeSql.caller, tableName, executeSql.ast.create_bookmark(executeSql.file))
                            nb += 1
                else:
                    self.create_link(linkType, executeSql.caller, tableName, executeSql.ast.create_bookmark(executeSql.file))
                    nb += 1

        elif embeddedResults:
        
            for embeddedResult in embeddedResults:
                for linkType in embeddedResult.types:
                    self.create_link(linkType, executeSql.caller.get_kb_object(), embeddedResult.callee, executeSql.ast.create_bookmark(executeSql.file))
                    nb += 1
#                     currentConnection.linkSuspensions.append(LinkSuspension(linkType, self.current_context.get_current_function(), embeddedResult.callee, ast))

        if nb > 0:
            cast.analysers.log.debug('links found')
                 
        return nb
    
class JavaScript(cast.analysers.ua.Extension):

    def __init__(self):
        self.analyzer = JavaScriptAnalyzer(self)
        self.active = True
        
    def start_analysis(self):
        
        self.analyzer.get_cast_version()
#         version = cast.analysers.get_cast_version()
        # resistant (for unit tests)
        try:
            options = cast.analysers.get_ua_options() #@UndefinedVariable dynamically added
            if not 'HTML5' in options:
                # SQLScript language not selected : inactive
                self.active = False
            else:
                # @todo use the options
                self.active = True
        except:
            pass        
    
    def start_file(self, file):

        if not self.active:
            return
        self.analyzer.start_file(file)

    def end_analysis(self):
        if not self.active:
            return
        self.analyzer.end_analysis()
