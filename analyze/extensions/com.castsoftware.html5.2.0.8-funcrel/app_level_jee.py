'''
Created on 5 janv. 2015

@author: MRO
'''
import cast_upgrade_1_5_25 # @UnusedImport
from cast.application import ApplicationLevelExtension, create_link
import logging
import json
import traceback

class JEEExtensionApplication(ApplicationLevelExtension):
    
    def match_jsp_files(self, application, languageDetectedByExtension):

        jspExtensions = ('.jsp', '.jsf', '.jsff', '.jspx', )
        if languageDetectedByExtension:
            for _ext, language in languageDetectedByExtension.items():
                if language == 'jsp':
                    jspExtensions = jspExtensions + (_ext, )
        logging.info('jspExtensions ' + str(jspExtensions))

        jspContents = {}
        for o in application.search_objects(category='CAST_HTML5_JSP_Content'):
            # remove /CAST_HTML5_JSP_Content from then end
#             jspContents[o.fullname[:-23].lower()] = o
            jspContents[o.fullname.lower()] = o
            logging.debug('Loading ' + o.fullname)
        if not jspContents:
            return

        for o in application.search_objects(category='CAST_Web_File'):
            fullname = o.fullname[1:-1].lower()
            if fullname.endswith(jspExtensions):
                if fullname in jspContents:
                    create_link('callLink', o, jspContents[fullname])
                else:
                    logging.warning('HTML5-009 File not matched ' + fullname)

        # Making UA jsp source files external
        s = ''
        for o in application.search_objects(category='sourceFile'):
            fullname = o.fullname.lower()
            if fullname.endswith(jspExtensions):
                if fullname in jspContents:
                    if s:
                        s += ','
                    s += str(o.id)
        
        if s:
            req = "update ObjPro set Prop = 1 where IdObj in ( " + s + " )"
            try:
                logging.info('updating ObjPro ' + req)
                application.sql_tool(req)
            except:
                logging.warning('HTML5-010 Error executing ' + req + ' on jsp files')

    def match_asp_files(self, application):

        jspContents = {}
        for o in application.search_objects(category='CAST_HTML5_ASP_Content'):
            # remove /CAST_HTML5_ASP_Content from then end
#             jspContents[o.fullname[:-23].lower()] = o
            jspContents[o.fullname.lower()] = o
            logging.debug('Loading ' + o.fullname)
        if not jspContents:
            return

        for o in application.search_objects(category='CAST_Web_File'):
            fullname = o.fullname[1:-1].lower()
            if fullname.endswith('.asp'):
                if fullname in jspContents:
                    create_link('callLink', o, jspContents[fullname])
                else:
                    logging.warning('HTML5-009 File not matched ' + fullname)

        # Making UA jsp source files external
        s = ''
        for o in application.search_objects(category='sourceFile'):
            fullname = o.fullname.lower()
            if fullname.endswith('.asp'):
                if fullname in jspContents:
                    if s:
                        s += ','
                    s += str(o.id)
        
        if s:
            req = "update ObjPro set Prop = 1 where IdObj in ( " + s + " )"
            try:
                logging.info('updating ObjPro ' + req)
                application.sql_tool(req)
            except:
                logging.warning('HTML5-011 Error executing ' + req + ' on asp files')
    
    def match_aspx_files(self, application):

        jspContents = {}
        for o in application.search_objects(category='CAST_HTML5_ASPX_Content'):
            # remove /CAST_HTML5_ASP_Content from then end
#             jspContents[o.fullname[:-24].lower()] = o
            jspContents[o.fullname.lower()] = o
            logging.info('debug ' + o.fullname)
        if not jspContents:
            return

        for o in application.search_objects(category='CAST_DotNet_AspxFile'):
            fullname = o.fullname.lower()
            if fullname.endswith('.aspx'):
                if fullname in jspContents:
                    create_link('callLink', o, jspContents[fullname])
                else:
                    logging.info('HTML5-009 File not matched ' + fullname)

        # Making UA jsp source files external
        s = ''
        for o in application.search_objects(category='sourceFile'):
            fullname = o.fullname.lower()
            if fullname.endswith('.aspx'):
                if fullname in jspContents:
                    if s:
                        s += ','
                    s += str(o.id)
        
        if s:
            req = "update ObjPro set Prop = 1 where IdObj in ( " + s + " )"
            try:
                logging.info('updating ObjPro ' + req)
                application.sql_tool(req)
            except:
                logging.warning('HTML5-012 Error executing ' + req + ' on aspx files.')
    
    def match_htc_files(self, application):

        jspContents = {}
        for o in application.search_objects(category='CAST_HTML5_HTC_Content'):
            # remove /CAST_HTML5_ASP_Content from then end
#             jspContents[o.fullname[:-23].lower()] = o
            jspContents[o.fullname.lower()] = o
            logging.debug('Loading ' + o.fullname)
        if not jspContents:
            return

        for o in application.search_objects(category='CAST_DotNet_HtcFile'):
            fullname = o.fullname.lower()
            if fullname.endswith('.htc'):
                if fullname in jspContents:
                    create_link('callLink', o, jspContents[fullname])
                else:
                    logging.info('HTML5-009 File not matched ' + fullname)

        # Making UA jsp source files external
        s = ''
        for o in application.search_objects(category='sourceFile'):
            fullname = o.fullname.lower()
            if fullname.endswith('.htc'):
                if fullname in jspContents:
                    if s:
                        s += ','
                    s += str(o.id)
        
        if s:
            req = "update ObjPro set Prop = 1 where IdObj in ( " + s + " )"
            try:
                logging.info('updating ObjPro ' + req)
                application.sql_tool(req)
            except:
                logging.warning('HTML5-013 Error executing ' + req + ' on htc files.')
    
    def match_applet_references(self, application):

        logging.info('Matching applet references...')
        
        applets = {}
        for o in application.objects().has_type('CAST_J2EE_HTML5_Applet'):
            applets[o.get_fullname()] = o
        
        for o in application.objects().has_type('CAST_HTML5_AppletClassReference').load_positions():
            className = o.get_name()
            if className in applets:
                pos = o.get_positions()
                if pos:
                    create_link('callLink', o, applets[className], pos[0])
                else:
                    create_link('callLink', o, applets[className])
            else:
                logging.info('applet ' + str(className) + ' not found.')
            
    def end_application(self, application):

        languageDetectedByExtension = {}
        try:
            f = self.get_intermediate_file("html5.txt")
            if not f or f.isstdin():
                logging.info('No user defined extensions detected')
            else:
                languageDetectedByExtensionStr = ''
                for line in f.readline():
                    languageDetectedByExtensionStr += line
                try:
                    languageDetectedByExtension = json.loads(languageDetectedByExtensionStr)
                except:
                    logging.warning('Problem when converting user defined extensions')
                logging.info('User defined extensions detected: ' + languageDetectedByExtensionStr)
            f.close()
        except:
            logging.warning('No user defined extensions detected (exception)')
            logging.warning(str(traceback.format_exc()))
        
        self.match_jsp_files(application, languageDetectedByExtension)
        self.match_asp_files(application)
        self.match_aspx_files(application)
        self.match_htc_files(application)
        self.match_applet_references(application)
            