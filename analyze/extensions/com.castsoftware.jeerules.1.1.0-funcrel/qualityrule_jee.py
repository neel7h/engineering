'''
Created on Jun 6, 2018

@author: RSI
'''
import cast.analysers.jee
from cast.analysers import log, Bookmark, CustomObject
import traceback  
from functools import lru_cache
from _ast import Str
import collections
import symbol_AI as sAI
from builtins import str
import lxml.etree as ET
from numpy import equal
import re
import itertools
from _hashlib import new
from cast.application import open_source_file


class HandleJEESecurity_QualityRules(cast.analysers.jee.Extension):

    CONST_SESSION_CONFIG = 'session-config' 
    CONST_COOKIE_CONFIG = 'cookie-config'    
    
    def __init__(self):
        self.protocol_used = None
        self.referer_used = None
        self.java_parser = None
        self.symbol_ai = False
        self.addviolation = ([])
        self.symbol_obj = None
        self.m_dict = {}
        self.m_importdict = []
        self.m_suppored_imp = []
        self.listfile = []
        self.class_name = ''
        self.xml_session_config = {}
        self.secureviolation = {}
        self.httponlyviolation = {}
        self.xmlxpathfactory = []
        self.saxpfactory = []
        self.xmlreaderfactory = []
        self.createxmlstreamReader = []
        self.Optionallist = []
        self.bannedapi = []
        self.esapilibrary = []
        self.isjspfile = False
        self.jspfile = None
        self.objectsByFullname = {}
        """
        Handle secure random properties file values and resolver it
        """
        self.propertyfile = []
        self.prop_value = {}
        self.getprop_meth = []
        self.prop_violation = []
        
        """
        added the below dictionaries as part of JEEQRS - 44
        added by skh dated 21-Dec-2018.
        """
        self.methodinfile = {}
        self.inheritedclass = {}
        """
        added the below dictionary as part of JEEQRS - 67
        added by skh date 07-Mar-2019
        """
        self.implist = {'org.bouncycastle.crypto.digests':['SHA1Digest', 'MD2Digest', 'MD4Digest', 'RipeMD128Digest'], \
                        'org.bouncycastle.crypto.generators':[ 'PKCS5S2ParametersGenerator', 'OpenSSLPBEParametersGenerator']}
    
    def start_web_xml(self, file):
        if file.get_path()[-4:] == '.xml' :
            try:
                element_tree = ET.iterparse(file.get_path())
                
                for _, el in element_tree:
                    if '}' in el.tag:
                        el.tag = el.tag.split('}', 1)[1]
            except:
                pass 

            root_element = element_tree.root

            if root_element == None:
                return

            for childs in root_element.findall(self.CONST_SESSION_CONFIG): 
                for child in childs.findall(self.CONST_COOKIE_CONFIG):
                    for ch in child:
                        self.xml_session_config[ch.tag] = ch.text

    def start_web_file(self, file):
        fileUrl = file.get_path()
        if fileUrl[-4:] == '.jsp' and fileUrl not in self.listfile:
            obj = sAI.read_file(fileUrl)
            self.class_name = fileUrl[fileUrl.rindex('\\', 0, -1) + 1:-4]
            obj.generate_fieldinfo(self.class_name, file.get_name())
            self.m_dict = obj.m_dict;
            self.m_importdict = obj.import_stat
            self.symbol_obj = obj
            self.listfile.append(fileUrl)
            self.isjspfile = True
            self.jspfile = file
            
            if len(self.m_importdict) != -1:
                self.is_jeesecqrcope()
    
    def start_properties_file(self, file):
        if file not in self.propertyfile:
            self.propertyfile.append(file)
    
    # Handle .properties files
    def get_propertiesvalue(self,file_path,file):
        with open_source_file(file_path) as propfile:
            for index, line in enumerate(propfile):
                prop_info_list = line.split('=')
                if len(prop_info_list) == 2:
                    self.prop_value[prop_info_list[0]] = [prop_info_list[1].rstrip(),index+1,file]
        
    # receive a java parser from platform
    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def receive_java_parser(self, parser):
        self.java_parser = parser        
    
    def start_analysis(self, options):
        options.add_classpath('jars')
        log.info('jee extension loaded')
        
        # for  Avoid using Deprecated SSL protocoles to secure connection
        options.add_parameterization('javax.net.ssl.SSLContext.getInstance(java.lang.String)', [1], self.callback_SSLprotocol)
        options.add_parameterization('javax.net.ssl.SSLContext.getInstance(java.lang.String, java.lang.String)', [1], self.callback_SSLprotocol)
        options.add_parameterization('javax.net.ssl.SSLContext.getInstance(java.lang.String, java.security.Provider)', [1], self.callback_SSLprotocol)
        
        # Avoid using risky cryptographic hash
        options.add_parameterization('java.security.SecureRandom.getInstance(java.lang.String)', [1], self.secure_RandomGenerator)
        options.add_parameterization('java.security.MessageDigest.getInstance(java.lang.String)', [1], self.secure_RandomGenerator)
        options.add_parameterization('java.security.MessageDigest.getInstance(java.lang.String,java.lang.String)', [1], self.secure_RandomGenerator)

        options.add_parameterization('java.lang.ClassLoader.getResourceAsStream(java.lang.String)', [1], self.secure_RandomGenerator_getproperties)
        options.add_parameterization('java.util.Properties.getProperty(java.lang.String,java.lang.String)', [1], self.secure_RandomGenerator_properties)
        # Avoid using predictable "SecureRandom"
        options.add_parameterization('java.util.Random.Random(long)', [1], self.callback_secureRandom)
        options.add_parameterization('java.util.Random.setSeed(long)', [1], self.callback_secureRandom)
        options.add_parameterization('java.security.SecureRandom.setSeed(long)', [1], self.callback_secureRandom)
        options.add_parameterization('java.security.SecureRandom.SecureRandom(byte[])', [1], self.callback_secureRandom) 
        
        # Avoid using referer header field in HTTP request
        options.add_parameterization('javax.servlet.http.HttpServletRequest.getHeader(java.lang.String)', [1], self.callback_refererHeader)
        options.add_parameterization('javax.servlet.http.HttpServletResponse.getHeader(java.lang.String)', [1], self.callback_refererHeader)
        
        # avoidunvalidatedredirect
        options.add_parameterization('javax.servlet.http.HttpServletResponse.sendRedirect(java.lang.String)', [1], self.callback_sendRedirect)

        # avoid hardcodedsalt
        options.add_parameterization('org.owasp.esapi.Encryptor.hash(java.lang.String,java.lang.String)', [1], self.callback_hardcodedsalt)
        options.add_parameterization('org.owasp.esapi.Encryptor.hash(java.lang.String,java.lang.String,int)', [1], self.callback_hardcodedsalt)
        options.add_parameterization('javax.crypto.spec.PBEParameterSpec.PBEParameterSpec(byte[],int)', [1], self.callback_hardcodedsalt)
        
        # Avoid using "javax.crypto.NullCipher
        options.add_parameterization('javax.crypto.NullCipher.NullCipher', [1], self.crypto_NullCipher)
        options.add_parameterization('javax.crypto.Cipher.getInstance(java.lang.String)', [1], self.callback_secureCipher)
        
        # Avoid using Insecure PBE Iteration Count
        options.add_parameterization('javax.crypto.spec.PBEParameterSpec.PBEParameterSpec(byte[],int)', [1], self.callback_specPBEParameterSpec)
        options.add_parameterization('javax.crypto.spec.PBEParameterSpec.PBEParameterSpec(byte[],int,AlgorithmParameterSpec)', [1], self.callback_specPBEParameterSpec)
        
        # CWE-614 : Avoid using unsecured cookie
        options.add_parameterization('javax.servlet.http.Cookie.Cookie(java.lang.String,java.lang.String)', [1], self.callback_insecuredCookie) 
        options.add_parameterization('javax.servlet.http.Cookie.setSecure(boolean)', [1], self.callback_matchsecuredCookie)  
        
        # Avoid creating cookie without setting httpOnly option
        options.add_parameterization('javax.servlet.http.Cookie.setHttpOnly(boolean)', [1], self.callback_matchhttponlyCookie)
        
        # Avoid weak encryption providing not sufficient key size (JEE)
        options.add_parameterization('javax.crypto.KeyGenerator.init(int)', [1], self.callback_cryptoKeyGeneratorAES)
        options.add_parameterization('java.security.KeyPairGenerator.initialize(int)', [1], self.callback_cryptoKeyGeneratorRSA)
        
        # http://rulesmanager/#:a:1o9
        options.add_parameterization('java.io.File.createTempFile(java.lang.String,java.lang.String)', [1], self.callback_bannaedAPI) 
        options.add_parameterization('java.lang.Runtime.exec(java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('javax.servlet.http.HttpServletRequest.isUserInRole(java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('javax.servlet.ServletResponse.setContentType(java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('javax.servlet.http.HttpServletResponse.sendRedirect(java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('javax.servlet.http.HttpServletResponse.addHeader(java.lang.String,java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('javax.servlet.ServletContext.log(java.lang.String,java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('javax.servlet.ServletContext.log(java.lang.String,Throwable)', [1], self.callback_bannaedAPI)
        options.add_parameterization('java.net.URLEncoder.encode(java.lang.String,java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('java.net.URLEncoder.encode(java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('java.net.URLDecoder.decode(java.lang.String,java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('java.net.URLDecoder.decode(java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('javax.servlet.http.HttpServletResponse.encodeRedirectURL(java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('javax.servlet.http.HttpServletResponse.encodeURL(java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('java.sql.Statement.execute(java.lang.String)', [1], self.callback_bannaedAPI)
        options.add_parameterization('java.sql.Statement.execute(java.lang.String,java.lang.String[])', [1], self.callback_bannaedAPI)
        options.add_parameterization('java.sql.Statement.execute(java.lang.String,int)', [1], self.callback_bannaedAPI)
        options.add_parameterization('java.sql.Statement.execute(java.lang.String,int[])', [1], self.callback_bannaedAPI)
        
        options.add_parameterization('javax.servlet.ServletRequest.getRequestDispatcher(java.lang.String)', [1], self.callback_bannaedforwardAPI)
    
    def is_jeesecqrcope(self): 
        
        s_list = ['javax.xml.parsers.', 'javax.servlet.', 'org.owasp.', 'javax.crypto.', 'java.security.', 'java.net.', 'org.owasp.esapi.ESAPI']
        self.m_suppored_imp = [0, 0, 0, 0, 0, 0, 0, 0]
        
        for index, x in enumerate(s_list, start=0):
            for y in self.m_importdict:
                if str(x) in str(y):
                    self.m_suppored_imp[index] = 1 
                    break;             

    def clear_previous_value(self):
        self.xmlxpathfactory.clear()
        self.xmlreaderfactory.clear() 
        self.saxpfactory.clear() 
        self.createxmlstreamReader.clear()
        self.Optionallist.clear()
#         self.bannedapi.clear()
        
    def start_type(self, _type):
        self.qualified_identifier = ["org.apache.http.impl.client.DefaultHttpClient", "javax.xml.parsers.SAXParserFactory", "org.xml.sax.helpers.XMLReaderFactory", "org.w3c.dom.xpath.XPathExpression", "javax.xml.stream.XMLInputFactory", "java.util.Optional", "java.lang.", "java.io.", "java.util.Properties", "javax.servlet.http.HttpSession", "javax.servlet.http.HttpServletRequest"]
        """
        Added the below dictionary as part of JEEQRS -67
        """
        imprts = {}

        def get_all_tokens(ast, meth, dc):
            # Quality Rule - JEEQRS-42: Always use code annotation to wrap code statements
            if hasattr(ast, 'children'):
                # start Block
                for index, tok in enumerate(ast.children):
                    if imprts and hasattr(tok, 'text'):
                        for ref in imprts.keys():
                            for algo in self.implist[ref]:
                                if tok.text != None and tok.text.endswith(algo):
                                        if len(ast.children) > index + 1 and\
                                        hasattr(ast.children[index + 1], 'children') and\
                                        hasattr(ast.children[index + 1].children[0], 'text') and\
                                        ast.children[index + 1].children[0].text == '(' and\
                                        ast.children[index + 1].children[1].text == ')':
                                            log.debug(str(imprts))
                                            if resolve_match_imports(tok.text, imprts, self.implist):
                                                bookmark = Bookmark(_type.get_position().get_file(), tok.get_begin_line() , tok.get_begin_column(), tok.get_end_line(), tok.get_end_column())
                                                t = [meth, 'CAST_Java_Metric_Avoidusingriskycryptographichash.riskycryptographichash', bookmark]
                                                self.addviolation.append(t)
                                        
                # End Block
                    if hasattr(tok, 'children'):
                        if tok.is_comment():
                            dc = check_codeann(tok, meth, dc)
                    get_all_tokens(tok, meth, dc)
            elif hasattr(ast, 'text') and ast.text:
                if ast.is_comment():
                    dc = check_codeann(ast, meth, dc)

        def check_codeann(ast, meth, dcomm):
            # Quality Rule - JEEQRS-42: Always use code annotation to wrap code statements
            if dcomm.get(ast.get_begin_line(), 0) == 0:
                dcomm[ast.get_begin_line()] = ''
                line_no = ast.get_begin_line()
                criteria = re.compile(r"<code>.*</code>", re.DOTALL)
                for ind in criteria.finditer(ast.text):
                    line_start = line_no + ast.text[0:ind.start() - 1].count("\n")
                    line_end = line_start + ast.text[ind.start():ind.end()].count("\n")
                    t = [meth, 'CAST_Java_Metric_AvoidUsingCodeTagInComments.codeAnnotation', Bookmark(_type.get_position().get_file(), line_start, 1, line_end , -1)]
                    self.addviolation.append(t)
            return dcomm

        def check_dml(children, mem):
            for child in children.get_children():
                if hasattr(child, 'children') and child.get_children():
                    check_dml(child, mem)
                elif hasattr(child, 'text'):
                    if child.text.find("DefaultHttpClient") > -1:
                        t = [mem, 'CAST_Java_Metric_AvoidUsingDefaultHttpClientConstructor.defaultHttpConstructor', Bookmark(mem.get_position().get_file(), child.get_begin_line(), child.get_begin_column(), child.get_begin_line() , -1)]
                        self.addviolation.append(t)
                    if child.text.find("SAXParserFactory.newInstance") > -1:
                        self.saxpfactory.append([mem, child.get_begin_line(), child.get_begin_column(), child.get_begin_line()])
                    if child.text.find("XMLReaderFactory.createXMLReader") > -1:
                        t = [mem, child.get_begin_line(), child.get_begin_column(), child.get_begin_line()]
                        if t not in self.xmlreaderfactory:
                            self.xmlreaderfactory.append([mem, child.get_begin_line(), child.get_begin_column(), child.get_begin_line()])  #
                    if child.text.find(".evaluate") > -1 : 
                        t = [mem, child.get_begin_line(), child.get_begin_column(), child.get_begin_line()]
                        if t not in self.xmlxpathfactory:
                            self.xmlxpathfactory.append(t)
                    if child.text.find(".createXMLStreamReader") > -1 : 
                        t = [mem, child.get_begin_line(), child.get_begin_column(), child.get_begin_line()]
                        if t not in self.createxmlstreamReader:
                            self.createxmlstreamReader.append(t)
                    if child.text.find("Optional") > -1 : 
                        t = [mem, child.get_begin_line(), child.get_begin_column(), child.get_begin_line()]
                        if t not in self.Optionallist:
                            self.Optionallist.append(t) 
                    if self.m_suppored_imp[6] == 1 and (child.text.find("System.out.println") > -1 or child.text.find("Math.random") > -1 or child.text.find(".printStackTrace") > -1 or child.text.find("Properties") > -1 or child.text.find(".getId") > -1 or child.text.find(".getUserPrincipal") > -1 or child.text.find(".isSecure") > -1 or child.text.find(".invalidate") > -1): 
                        t = [mem, mem.get_position().get_file(), child.get_begin_line(), child.get_begin_column(), child.get_begin_line()]
                        if t not in self.bannedapi:
                            self.bannedapi.append(t)
                
        fileUrl = _type.get_position().get_file().get_path()

        if fileUrl[-5:] == '.java' and fileUrl not in self.listfile:
            obj = sAI.read_file(fileUrl)
            self.class_name = fileUrl[fileUrl.rindex('\\', 0, -1) + 1:-5]
            obj.generate_fieldinfo(self.class_name, _type.get_name())
            self.m_dict = obj.m_dict;
            self.m_importdict = obj.import_stat
            self.symbol_obj = obj
            self.listfile.append(fileUrl)
        
        self.clear_previous_value()
        if len(self.m_importdict) != -1:
            self.is_jeesecqrcope()
            
        all_tokens = self.java_parser.parse(_type.get_position().get_file().get_path())
        if all_tokens is not None:
            allImports = all_tokens.imports
            for imp in allImports:
                if 'org.owasp.esapi.ESAPI' == imp.get_name():
                    self.esapilibrary.append([imp.get_begin_line(), imp.get_begin_column()])
                """
                added the block as part of JEEQRS -67
                """
                # Start Block
                for implist in self.implist.keys():
                    if len(implist) > len(imp.get_name()):
                        if implist.startswith(imp.get_name()):
                            imprts[implist] = imp.get_name()
                    else:
                        if imp.get_name().startswith(implist):
                            imprts[implist] = imp.get_name()
                # End Block
                if imp.get_name() in self.qualified_identifier: 
                    allMethods = _type.get_children()
                    for meth in allMethods:
                        ast = self.java_parser.get_object_ast(meth)
                        if ast:
                            if ast.get_children():
                                for child in ast.get_children():
                                    if child and hasattr(child, 'children') and child.get_children():
                                        check_dml(child, meth) 
        
        ast_ = self.java_parser.get_object_ast(_type)
        dc = dict()
        if hasattr(ast_, 'children'):
            for tok in ast_.children:
                if tok.is_comment():
                    dc = check_codeann(tok, _type, dc)
        allMethods = _type.get_children()
        for meth in allMethods:
            ast_ = self.java_parser.get_object_ast(meth)
            '''
            Quality Rule JEEQRS - 44
            Add @Override on methods overriding or implementing a method
            in a super Type
            '''
            if meth.get_typename() == "JV_METHOD":
                self.methodinfile.setdefault(_type.get_fullname(), list())\
                .append(meth.get_name())
            if ast_ and hasattr(ast_, 'children') and hasattr(_type, 'get_inherited_types') and callable(getattr(_type, 'get_inherited_types'))and\
             _type.get_inherited_types() != [] and\
            _type.get_inherited_types()[0].get_name() not in ["Object", "Enum"] and\
            meth.get_typename() == "JV_METHOD" and\
            (meth.get_annotations() == [] or\
            meth.get_annotations()[0][0].get_name() != "Override"):
                self.inheritedclass.setdefault(_type.get_inherited_types()[0].get_fullname()\
                                               , list()).append\
                                               ([meth.get_name(), meth, _type.get_position().get_file(), \
                                                ast_.get_begin_line(), \
                                                ast_.get_begin_column(), ast_.get_begin_line()])
            if ast_:
                get_all_tokens(ast_, meth, dc)

    def start_member(self, member):

        if len(self.m_importdict) != -1:

            self.get_member_informations(member)
    
    def get_member_informations(self, member):
        """
        Scan member to get the annotations 
        """        
        if (member.get_typename() == 'JV_METHOD'):  
            check_catch = False  
            last_child = None
            thrw = False
            doget = []
            childrens = None
            
            self.java_parser.parse(member.get_position().get_file().get_path())
            ast = self.java_parser.get_object_ast(member)
            
            try: 
                childrens = ast.get_children()
            except:
                return
                
            if not isinstance(childrens, collections.Iterable):
                return
                
            for child in childrens:
                if str(child).find('.getRequestedSessionId') != -1:                
                    token_list = self.get_child_candidate_list('.getRequestedSessionId', child)
                    t = [member, 'CAST_Java_Metric_AvoidgetRequestedSessionId.getRequestedSessionId', Bookmark(member.get_position().get_file(), token_list[1] , token_list[2], token_list[1], token_list[4] + 1)]
                    self.addviolation.append(t)

                if str(child).find('doGet') != -1 or str(child).find('doPost') != -1 or str(child).find('doDelete') != -1 or str(child).find('doHead') != -1 or str(child).find('doPut') != -1 or str(child).find('doOptions') != -1:
                    doget = [child.get_begin_line(), child.get_begin_column(), child.get_end_line(), child.get_end_column()]
                    try:
                        chl = childrens.look_next()
                        if str(chl).find('HttpServletRequest') != -1 and str(chl).find('HttpServletResponse') != -1 :
                            thrw = True
                    except:
                        log.debug('No Next child')
                
                if check_catch is False and thrw and str(child).find('throws') != -1 :
                    check_catch = True
                if check_catch is not False and str(child).find('catch') != -1: 
                    check_catch = False
                
                last_child = child
            
            t = [last_child.get_end_line(), last_child.get_end_column()]        
            if check_catch is True and len(doget) > 0:
                t = [member, 'CAST_Java_Metric_AvoidthrownExceptionsinservletmethods.throwexception', Bookmark(member.get_position().get_file(), doget[0], doget[1] , t[0], doget[1] + 1)]
                self.addviolation.append(t)   

#            To Handle ValueKey type expression 
            try:

                if self.symbol_obj is not None and self.m_dict is not None:
                    mem_dic = self.symbol_obj.get_global_field_info(self.m_dict, self.symbol_obj.actual_class_name, member.get_name())
                    
                    if mem_dic is not None:
                        self.KeyValue_Interface(member, mem_dic)
                    elif self.isjspfile:
                        mem_dic = self.symbol_obj.get_fullcls_info(self.m_dict, str(self.class_name))
                        if mem_dic is not None:                            
                            self.KeyValue_Interface(self.jspfile, mem_dic)

            except:
                pass

    def create_customeobject(self, obj_name, obj_fullname, obj_type, obj_position, parent_obj, file):
        if obj_fullname in self.objectsByFullname:
            return self.objectsByFullname[obj_fullname]
        else:
            new_object = cast.analysers.CustomObject()
            new_object.set_type(obj_type)
            new_object.set_name(obj_name)
            new_object.set_fullname(obj_fullname)
            new_object.parent(parent_obj)
            new_object.set_guid(obj_fullname)
            try:
                new_object.Save()
                self.objectsByFullname[obj_fullname] = new_object
                
                if type(file) is not str:
                    new_object.savepoint(obj_position)
            except:
                log.warning('Internal issue saving new JEE object')
                log.debug(traceback.format_exc())
                return None
        return new_object
        
    def callback_SSLprotocol(self, values, caller, line, column):

        if values and values[1][0].strip() != '':
            bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1)
            self.protocol_used = values[1][0]
            if self.protocol_used is not None and self.protocol_used.strip() == 'SSL':  
                t = [caller, 'CAST_Java_Metric_AvoidusingDeprecatedSSLprotocols.SSLprotocols', bookmark]
                self.addviolation.append(t)
    
    def callback_secureRandom(self, values, caller, line, column):
        
        bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1)
        t = [caller, 'CAST_Java_Metric_AvoidusingpredictableSecureRandomSeeds.SecureRandom', bookmark]
        self.addviolation.append(t)
 
    def secure_RandomGenerator(self, values, caller, line, column):
        if values:  
            if values[1][0].strip() == 'MD5' or values[1][0].strip() == 'MD4'\
            or values[1][0].strip() == 'MD2' or values[1][0].strip() == 'SHA1':
                bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1)
                t = [caller, 'CAST_Java_Metric_Avoidusingriskycryptographichash.riskycryptographichash', bookmark]
                self.addviolation.append(t)
        else:
            fileUrl = caller.get_position().get_file().get_path() 
            if fileUrl[-5:] == '.java':
                obj = sAI.read_file(fileUrl)
                self.class_name = fileUrl[fileUrl.rindex('\\', 0, -1) + 1:-5]
                obj.generate_fieldinfo(self.class_name, caller.get_name(), True)
                if obj is not None and obj.m_dict is not None:
                    t = [caller]
                    fld_info = self.symbol_obj.get_local_methode_info(obj.m_dict, obj.actual_class_name, caller.get_name(), line)
                    if fld_info is not None:
                        value = fld_info[0]
                        param = value[value.rfind('(')+1:-1]
                        bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1)
                        t = [param, caller, 'CAST_Java_Metric_Avoidusingriskycryptographichash.riskycryptographichash', bookmark]
                        self.prop_violation.append(t)
            
    
    def secure_RandomGenerator_properties(self, values, caller, line, column):
        if values: 
            fileUrl = caller.get_position().get_file().get_path() 
            if fileUrl[-5:] == '.java':
                obj = sAI.read_file(fileUrl)
                self.class_name = fileUrl[fileUrl.rindex('\\', 0, -1) + 1:-5]
                obj.generate_fieldinfo(self.class_name, caller.get_name(), True)
                if obj is not None and obj.m_dict is not None:
                    t = [caller]
                    fld_info = self.symbol_obj.get_local_methode_info(obj.m_dict, obj.actual_class_name, caller.get_name(), line)
                    if fld_info is not None:
                        t.extend(fld_info)
                        self.getprop_meth.append(t)

    def secure_RandomGenerator_getproperties(self, values, caller, line, column):
        if values:
            for file in self.propertyfile:
                file_path = file.get_name()
                value = values[1][0]
                if value in file_path:
                    self.get_propertiesvalue(file_path, file)


    def callback_refererHeader(self, values, caller, line, column):
        if values:  
            if values[1][0].strip() != '':
                bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1) 
                self.referer_used = values[1][0]
                if self.referer_used is not None and self.referer_used.strip() == 'referer': 
                    t = [caller, 'CAST_Java_Metric_AvoidusingrefererheaderfieldinHTTPrequest.refererheader', bookmark]
                    self.addviolation.append(t)
    
    def callback_sendRedirect(self, values, caller, line, column):
        
        if not values:
            bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1) 
            t = [caller, 'CAST_Java_Metric_AvoidUnvalidatedRedirect.UnvalidatedRedirect', bookmark]
            self.addviolation.append(t) 

    def callback_secureCipher(self, values, caller, line, column): 
        if values:
            if values[1][0].find('CBC') > -1 or values[1][0].find('OFB') > -1 or values[1][0].find('CTR') > -1 or values[1][0].find('ECB') > -1:
                bookmark = Bookmark(caller.get_position().get_file(), line, column, line, -1)
                caller.save_violation('CAST_Java_Metric_AvoidUsingCipherWithNoHMAC.noHMACCipher', bookmark)
                t = [caller, 'CAST_Java_Metric_AvoidUsingCipherWithNoHMAC.noHMACCipher', bookmark]
                self.addviolation.append(t)    
            
    def callback_hardcodedsalt(self, values, caller, line, column):

        if values:
            bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1) 
            t = [caller, 'CAST_Java_Metric_Avoidusingcryptographyhashwithhardcodedsalt.hardcodedsalt', bookmark]
            self.addviolation.append(t) 
    
    def crypto_NullCipher(self, values, caller, line, column):
        bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1)
        t = [caller, 'CAST_Java_Metric_AvoidusingjavaxcryptoNullCipher.nullcipher', bookmark]
        self.addviolation.append(t)
  
    def callback_specPBEParameterSpec(self, values, caller, line, column): 
        
        if self.symbol_obj is not None and self.m_dict is not None:
            fld_info = self.symbol_obj.get_local_methode_info(self.m_dict, self.symbol_obj.actual_class_name, caller.get_name(), line)
                  
            if fld_info is not None:
                params = fld_info[0].strip()
                param = self.get_param(params, 1)
                value = 0
                if param.isdigit() :
                    value = param.strip()
                else:                    
                    value = self.symbol_obj.get_local_methode_info(self.m_dict, self.symbol_obj.actual_class_name, caller.get_name(), param.strip())

                value = int(value[0].strip())
                if value < 1000:
                    bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1) 
                    t = [caller, 'CAST_Java_Metric_AvoidusingInsecurePBEIterationCount.IterationCount', bookmark]
                    self.addviolation.append(t) 
    
    def callback_insecuredCookie(self, values, caller, line, column):
        
        if line <= 1:
            pass
        
        issecsetinweb = self.xml_session_config.get('secure')
        ishttponlyinweb = self.xml_session_config.get('http-only')
        
        if issecsetinweb and ishttponlyinweb :
            if issecsetinweb == 'true' and ishttponlyinweb == 'true':
                pass
            elif issecsetinweb == 'false' and ishttponlyinweb == 'true':
                    bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1)
                    t = [caller, 'CAST_Java_Metric_AvoidusingInSecuredCookie.InsecureSeed', bookmark]
                    self.secureviolation[line] = t
            elif issecsetinweb == 'true' and ishttponlyinweb == 'false':
                    bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1)
                    t = [caller, 'CAST_Java_Metric_AvoidCreatingCookieWithoutSettingHttpOnlyOption.HttpOnlyOption', bookmark]
                    self.httponlyviolation[line] = t
            else:
                    bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1)
                    t = [caller, 'CAST_Java_Metric_AvoidCreatingCookieWithoutSettingHttpOnlyOption.HttpOnlyOption', bookmark]
                    self.httponlyviolation[line] = t
                    t = [caller, 'CAST_Java_Metric_AvoidusingInSecuredCookie.InsecureSeed', bookmark]
                    self.secureviolation[line] = t  
                    
        if self.m_suppored_imp[6] == 1:
            self.check_bannedAPI(".addCookie(", ")", caller, line, column)

    def callback_matchsecuredCookie(self, values, caller, line, column):
        
        found = self.find_matching_key(caller, line)
        if found :
            self.secureviolation.pop(found[1])

    def callback_matchhttponlyCookie(self, values, caller, line, column):
        
        found = self.find_matching_key(caller, line)
        if found :
            self.httponlyviolation.pop(found[1])
            
    def callback_cryptoKeyGeneratorAES(self, values, caller, line, column):
        
        fld_info = self.find_matching_key(caller, line, True)
        if fld_info is not None:
            param = self.get_param(fld_info, 0)
            self.add_weekKeyViolation(caller, line, column, param, 256)
                
    def callback_cryptoKeyGeneratorRSA(self, values, caller, line, column):
        
        fld_info = self.find_matching_key(caller, line, True)
        if fld_info is not None:
            param = self.get_param(fld_info, 0)
            self.add_weekKeyViolation(caller, line, column, param, 4096)
    
    def KeyValue_Interface(self, member, mem_dic): 
        keyValue = None
        
        if self.m_suppored_imp[1] == 1 or self.m_suppored_imp[3] == 1: 
            keyValue = self.symbol_obj.getKeyValuByValue(mem_dic, "PBEKeySpec")
            
            if keyValue is not None:  
                self.check_cryptoKeyGeneratorPBKDF2(member, keyValue)
        
        if self.m_suppored_imp[0] == 1:
            keyValue = self.symbol_obj.getKeyValuByValue(mem_dic, ".newDocumentBuilder()")
            
            if keyValue is not None: 
                for key, values in keyValue.items():
                    if type(key) is str:
                        get_key = str(key) + '.parse('
                        keyValue = self.symbol_obj.getKeyValuByValue(mem_dic, get_key)
                        if keyValue is not None: 
                            self.check_restrictionofXML_XXE(member, keyValue, mem_dic, 'CAST_Java_Metric_AvoidDocumentBuilderwithoutrestrictionofXMLXXE.DocBuildXMLXXE')
                
        if self.saxpfactory:
            
            for item in self.saxpfactory:
                if member == item[0]:
                    keyValue = self.symbol_obj.getKeyValuByValue(mem_dic, "SAXParserFactory.newInstance()")
                    
                    if keyValue is not None:  
                        self.check_restrictionofXML_XXE(member, keyValue, mem_dic, 'CAST_Java_Metric_AvoidSAXParserFactorywithoutrestrictionofXXE.SAXParserFactoryXMLXXE')

        if self.xmlreaderfactory:
                    
            for idx, item in enumerate(self.xmlreaderfactory):
                remove = []
                if member == item[0]:
                    keyValue = self.symbol_obj.getKeyValuByValue(mem_dic, 'XMLReaderFactory.createXMLReader()')
                     
                    if keyValue is not None:  
                        self.check_restrictionofXML_XXE(member, keyValue, mem_dic, 'CAST_Java_Metric_AvoidXMLReaderwithoutrestrictionofXMLXXE.XMLReaderFactory')
                    remove.append(idx)
                    
            for k in remove: del self.xmlreaderfactory[k]
                        
        if self.xmlxpathfactory:
            
            remove = []
            for idx, item in enumerate(self.xmlxpathfactory):
                if member == item[0]:
                    keyValue = self.symbol_obj.getKeyValuByValue(mem_dic, str(item[1]))
                     
                    if keyValue is not None:  
                        self.checkrestrictesXpathXML_XXE(member, mem_dic, keyValue)
                    
                    remove.append(idx)
                    
            for k in remove: del self.xmlxpathfactory[k]
        
        if self.createxmlstreamReader:
            
            for idx, item in enumerate(self.createxmlstreamReader):
                remove = []
                if member == item[0]:
                    keyValue = self.symbol_obj.getKeyValuByValue(mem_dic, '.createXMLStreamReader(')
                     
                    if keyValue is not None:  
                        self.check_restrictionofXMLStreamReader_XXE(member, keyValue, mem_dic, 'CAST_Java_Metric_AvoidXMLStreamReaderwithoutrestrictionofXMLXXE.XMLStreamReader')
                    remove.append(idx)
                    
            for k in remove: del self.createxmlstreamReader[k]
            
        if self.Optionallist:
            
            for idx, item in enumerate(self.Optionallist):
                remove = []
                if member == item[0]:
                    keyValue = self.symbol_obj.getKeyValuByValue(mem_dic, str(item[1]))
                     
                    if keyValue is not None:  
                        del keyValue[item[1]]
                        self.check_Optionallist(member, keyValue, mem_dic, 'CAST_Java_Metric_AvoidInvokingOptionalGetWithoutInvokingOptionalIsPresent.UseOptionalIsPresent')
                    remove.append(idx)
                    
            for k in remove: del self.Optionallist[k]
            
        keyValue = self.symbol_obj.getKeyValuByValue(mem_dic, "[]") 
        keyValueWithclosebracket = self.symbol_obj.getKeyValuByValue(mem_dic, "[") 
        
        def Merge(dict1, dict2):
            dict2.update(dict1)
            return dict2
        
        finalKeyArray = Merge(keyValue, keyValueWithclosebracket)
        if keyValue is not None:
            self.ArrayDesignator(member, mem_dic, keyValue)
    
    def ArrayDesignator(self, mem, mem_dic, keyvalue):
        for k, v in keyvalue.items():
            lineno = v[1]
            if isinstance(k, str) and k.find('[]') > -1:
                t = [mem, 'CAST_Java_Metric_AlwaysPreferSetArrayDesignators.ArrayDesignator', Bookmark(mem.get_position().get_file(), lineno, lineno, lineno, -1)]
                self.addviolation.append(t)
                
        for k, v in keyvalue.items():
            if v is not None:
                val = v.replace(' ', '')
                result = val.rfind(';')
                value_check = val[result - 1]
                if value_check == ']':
                    t = [mem, 'CAST_Java_Metric_AlwaysPreferSetArrayDesignators.ArrayDesignator', Bookmark(mem.get_position().get_file(), k, k, k, -1)]
                    self.addviolation.append(t)
    
    def check_cryptoKeyGeneratorPBKDF2(self, member, keyValue):
    
        for key, values in keyValue.items():
            actual_value = str(values[0])
            lineno = int(values[1])
            start_col = int(values[3])
            if lineno == key and actual_value.find(',') != -1:
                val = actual_value[actual_value.rindex(',', 0, -1) + 1:-1]
                val = val[0:val.find('*')]

                self.add_weekKeyViolation(member, lineno, start_col, val.rstrip().lstrip(), 255);
    
    def check_restrictionofXML_XXE(self, member, keyValue, mem_dic, v_id):
        
        kv = self.symbol_obj.getKeyValuByValue(mem_dic, ".setFeature(")
        
        remove = []
        if kv is not None:
            for kvkey, kvvalues in kv.items():
                statement = str(kvvalues)
                if kvvalues.find('FEATURE_SECURE_PROCESSING') != -1 and kvvalues.find('true') != -1:
                    kv_obj_name = str(kvvalues[0:kvvalues.find('.')])
                    for key, values in keyValue.items():
                        statement = values[0]
                        key_obj_name = str(statement[0:statement.find('.')])
                        if kv_obj_name.strip() == key_obj_name.strip() :
                            remove.append(key)
        
        for k in remove: del keyValue[k]
        
        for key, values in keyValue.items():
            lineno = int(values[1])
            start_col = int(values[3])
            if lineno == key:
                if self.isjspfile:
                    bookmark = Bookmark(member, lineno, start_col, lineno, -1)
                else:
                    bookmark = Bookmark(member.get_position().get_file(), lineno, start_col, lineno, -1)
                t = [member, v_id, bookmark]
                self.addviolation.append(t) 
    
    def checkrestrictesXpathXML_XXE(self, member, mem_dic, keyValue):
        for kv, value in keyValue.items():
            if len(value) > 5 :
                lineno = int(value[3])
                start_col = int(value[5])
            else:
                lineno = int(value[1])
                start_col = int(value[3])
                
            if kv == lineno : 
                df_found = False
                str_val = str(value[0]).strip()
                str_val = str_val[str_val.find('evaluate(') + 9:str_val.find(',')]
                if str_val.find('.parse') != -1:
                    docfactory = str_val[str_val.find('(') + 1:str_val.find('.parse')]
                    df_found = True 
                elif str_val.find('"') > -1 or str_val.find(' ') > -1:
                    df_found = False
                else:
                    if self.symbol_obj is not None and self.m_dict is not None:
                        factoryobj = self.symbol_obj.get_local_methode_info(self.m_dict, self.symbol_obj.actual_class_name, member.get_name(), str_val)
                        if factoryobj is not None and factoryobj[0].find('.parse(') != -1:
                            builderstr = factoryobj[0]
                            docfactory = builderstr[0:str_val.find('.')].strip()
                            
                            df_found = True
                            
                if  df_found :
                    find_kv = str(docfactory + '.setFeature(')
                    actual_kv = self.symbol_obj.getKeyValuByValue(mem_dic, find_kv)
                    
                    if actual_kv is not None and actual_kv.find('FEATURE_SECURE_PROCESSING') != -1 and actual_kv.find('true') != -1:
                        continue

                if self.isjspfile:
                    bookmark = Bookmark(member, lineno, start_col, lineno, -1)
                else:
                    bookmark = Bookmark(member.get_position().get_file(), lineno, start_col, lineno, -1)
                    
                t = [member, 'CAST_Java_Metric_AvoidXMLXPathFactorywithoutrestrictionofXMLXXE.XMLXpathFactory', bookmark]
                self.addviolation.append(t)

    def check_restrictionofXMLStreamReader_XXE(self, member, keyValue, mem_dic, v_id):
        
        kv = self.symbol_obj.getKeyValuByValue(mem_dic, ".setProperty")
        
        remove = []
        if kv is not None:
            for kvkey, kvvalues in kv.items():
                statement = str(kvvalues)
                if kvvalues.find('XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES') != -1 and (kvvalues.find('false') != -1 or kvvalues.find('Boolean.FALSE') != -1):
                    kv_obj_name = str(kvvalues[0:kvvalues.find('.')])
                    for key, values in keyValue.items():
                        statement = values[0]
                        key_obj_name = str(statement[0:statement.find('.')])
                        if kv_obj_name.strip() == key_obj_name.strip() :
                            remove.append(key)
        
        for k in remove: del keyValue[k]
        
        for key, values in keyValue.items():
            lineno = int(values[1])
            start_col = int(values[3])
            if lineno == key:
                if self.isjspfile:
                    bookmark = Bookmark(member, lineno, start_col, lineno, -1)
                else:
                    bookmark = Bookmark(member.get_position().get_file(), lineno, start_col, lineno, -1)
                    
                t = [member, v_id, bookmark]
                self.addviolation.append(t) 

    def check_Optionallist(self, member, keyValue, mem_dic, v_id):
        for key, values in keyValue.items():        
            kvg = self.symbol_obj.getKeyValuByValue(mem_dic, key + str('.get'))
            kvip = self.symbol_obj.getKeyValuByValue(mem_dic, key + str('.isPresent()'))
            
            if kvg is not None and kvip is not None:
                continue;
            
            for key, values in kvg.items():
                lineno = int(values[1])
                start_col = int(values[3]) 
                if lineno == key:
                    bookmark = Bookmark(member.get_position().get_file(), lineno, start_col, lineno, -1)
                    t = [member, v_id, bookmark]
                    self.addviolation.append(t)
            
    def add_weekKeyViolation(self, caller, line, column, param, keylimit): 
        value = 0
        if param.isdigit() :
            value = param.strip()
        else:
            value = self.symbol_obj.get_local_methode_info(self.m_dict, self.symbol_obj.actual_class_name, caller.get_name(), param.strip())

        if value is None : 
            return
        
        if (type(value) == list):
            value = value[0]
            
        val = int(value.strip()) 
               
        if val < keylimit:
            bookmark = Bookmark(caller.get_position().get_file(), line , column, line, -1) 
            t = [caller, 'CAST_Java_Metric_AvoidWeakEncryptionProvidingnotSufficientKeySize.weekkeysize', bookmark]
            self.addviolation.append(t)           

    def get_param(self, params, pos):
        params = params[params.rindex('(') + 1:params.rindex(')')]
        param = params.split(',')[pos].strip()
        return param

    def find_matching_key(self, caller, line, split=False):
        
        if line > 0 and self.symbol_obj is not None and self.m_dict is not None:
            found = self.symbol_obj.get_local_methode_info(self.m_dict, self.symbol_obj.actual_class_name, caller.get_name(), line)
            
            if split :
                return found
            
            if found is not None:
                obj = found.split('.')
                
                return self.symbol_obj.get_local_methode_info(self.m_dict, self.symbol_obj.actual_class_name, caller.get_name(), obj[0])
        
    def get_child_candidate_list(self, values, child):
        for each_token in child.get_children():
            if str(each_token).find(values) != -1: 
                t = [each_token.text, each_token.get_begin_line(), each_token.get_begin_column() , each_token.get_end_line(), each_token.get_end_column() + 1]                   
                return t

    def callback_bannaedAPI(self, values, caller, line, column):
        if (values or line > 1) and len(self.m_suppored_imp) > 0 and  self.m_suppored_imp[6] == 1:
            t = [caller, caller.get_position().get_file(), line , column, line, -1]
            self.bannedapi.append(t)

    def callback_bannaedforwardAPI(self, values, caller, line, column):
        if values and len(self.m_suppored_imp) > 0 and self.m_suppored_imp[6] == 1:
            self.check_bannedAPI(".forward", "", caller, line, column)
                                
    def check_bannedAPI(self, val1, val2, caller, line, column):
        if self.symbol_obj is not None and self.m_dict is not None:
                fld_info = self.symbol_obj.get_global_field_info(self.m_dict, self.symbol_obj.actual_class_name, caller.get_name())                
                      
                if fld_info is not None:
                    kv = self.symbol_obj.getKeyValuByValue(fld_info, str(line))
                    if kv is not None:
                        for kvkey, kval in kv.items():
                            if kvkey == line:
                                continue
                            
                            to_be_find = ""
                            if val1 == ".forward":
                                to_be_find = str(kvkey) + ".forward"
                            elif val1 == ".addCookie(":
                                to_be_find = val1 + str(kvkey) + val2
                                
                            kvviolation = self.symbol_obj.getKeyValuByValue(fld_info, to_be_find)
                                
                            for kvkey, val in kvviolation.items():                                
                                t = [caller, caller.get_position().get_file(), kvkey , 1, kvkey, -1]
                                self.bannedapi.append(t)
            
    def end_analysis(self):

        def post_violation():
            for vitem in self.addviolation:
                try:
                    vitem[0].save_violation(vitem[1], vitem[2])
                except:
                    pass
                
        def addtoviolation():
            for k, v in self.secureviolation.items():
                self.addviolation.append(v)
            for k, v in self.httponlyviolation.items():
                self.addviolation.append(v)
                
        def createbannedapiviolation():
            sec_lineno = self.esapilibrary[0] 
            if type(sec_lineno) is list:
                sec_lineno = sec_lineno[0]
            for item in self.bannedapi: 
                line = int(item[2])
                col = int(item[3])               
                bookmark = Bookmark(item[1], line, col, line, -1)
                secbookmark = Bookmark(item[1], sec_lineno, 1, sec_lineno, -1) 
                item[0].save_violation('CAST_Java_Metric_AvoidusageofBannedAPIwhenusingESAPIlibrary.bannedAPI', bookmark, [secbookmark])

        def baseclassoverloadviolation():
            for key, values in self.inheritedclass.items():
                if self.methodinfile.get(key, 0) != 0:
                    temp = self.methodinfile[key]
                    for value in values:
                        if value[0] in temp:
                            self.addviolation.append([value[1], "CAST_Java_Metric_AddOverrideonMethodsImplementSuperType.AddOverride", Bookmark(value[2], value[3], value[4], value[3] , -1)])

#       Check .properties files and add violation
        def check_random_properties():  
            for violation_item in self.prop_violation:
                val = violation_item[1]
                vVariable = violation_item[0]
                for prop_item in self.getprop_meth:
                    prop_val = prop_item[0]
                    variable = prop_item[6]
                    
                    if variable == vVariable and prop_val == val:
                        getprop = prop_item[1]
                        start_index = getprop.find("\"") + 1
                        getprop = getprop[start_index:getprop.rfind(',')] 
                        getprop = getprop.strip("\"") 
                        get_key = str(getprop)
                        prop_keyValue = self.prop_value.get(get_key)
                        prop_val = prop_keyValue[0]
                        if prop_val == 'MD5' or prop_val == 'SHA1':
                            sec_bookmark = Bookmark(prop_keyValue[2], prop_keyValue[1], 1, prop_keyValue[1], -1) 
                            val.save_violation(violation_item[2], violation_item[3],[sec_bookmark])
            
        
        baseclassoverloadviolation()
        if len(self.prop_value) > 0 and len(self.prop_violation) > 0 and len(self.getprop_meth) > 0:
            try:
                check_random_properties()
            except:
                log.info('Internal issue while posting check_random_properties %s' % traceback.format_exc())

        if  len(self.secureviolation) > 0 or len(self.httponlyviolation) > 0:
            try:
                addtoviolation()
            except:
                log.info('Internal issue while posting self.secureviolation %s' % traceback.format_exc())
        if  len(self.bannedapi) > 0 :
            try:
                createbannedapiviolation()
            except:
                log.info('Internal issue while posting bannedapi %s' % traceback.format_exc())

        if len(self.addviolation) > 0 :
            log.info('Start Adding Violation')
            try:
                post_violation()
            except:
                log.info('Internal issue while posting violation %s' % traceback.format_exc())
                
        self.secureviolation.clear()
        self.xml_session_config.clear()
        if self.m_dict:
            self.m_dict.clear()


def resolve_match_imports(toresolve, imprt, reslist):
    '''
    created as part of JEEQRS - 60. to resolve and match a class instantiation.
    inputs
    to resolve - Type String - input from source code to be resolved.
    imprt - Type dictionary - extracted from imports section.
    reslist - type list - contains list of all classes to be checked
    return Type True or False
    added by skh date 07-Mar-2019
    '''
    for ref, imp in imprt.items():
        if imp == toresolve:
            log.debug("imp==toresolve")
            return True
        else:
            if imp[-1] == '.':
                imp = imp[:-1]
            if len(toresolve.split('.')) == 1 and imp == ref:
                for lst in reslist[ref]:
                    if toresolve == lst:
                        log.debug("len_toresolve==1")
                        return True
            else:
                toresolve_ = '.'.join(e for e in toresolve.split('.')[:-1])
                if len(ref) >= len(toresolve_) and ref.endswith(toresolve_):
                    for lst in reslist[ref]:
                        if toresolve.split('.')[-1] == lst:
                            log.debug("toresolve subset of ref")
                            return True
    return False

        
if __name__ == '__main__':
    pass
