'''
Created on 5 janv. 2015

@author: MRO
'''
import cast_upgrade_1_5_25 # @UnusedImport
from cast.application import ApplicationLevelExtension, Bookmark, create_link, Object
import logging
import traceback
import json
from cast.application import select
from sqlalchemy import func, or_
    
def updateKnowledgeBase(application, id, req):
    application.update_cast_knowledge_base(id, req)
    pass



def html5_has_been_launched(application):

    for _ in application.search_objects(category='CAST_HTML5_JavaScript_SourceCode'):
        # at least one object
        return True
    return False

def remove_skipped_files(application, languageDetectedByExtension):
    remove_files_with_no_children(application, languageDetectedByExtension)
    
"""
(1000001, 1020005, 141813) are UA project type, HTML5 project type and CAST_PluginProject project type
"""
def remove_files_with_no_children(application, languageDetectedByExtension):

    extensions = [ '.js', '.ts', '.jsx', '.tsx', '.html', '.htm', '.xhtml', '.jsp', '.jsf', '.jsff', '.jspx', '.xml', '.json', '.css', '.asp', '.aspx', '.htc', '.cshtml', '.jade', '.yml' ]
    if languageDetectedByExtension:
        for _ext in languageDetectedByExtension.keys():
            extensions.append(_ext)
    logging.info('extensions ' + str(extensions))
    
    keyNameLikeStr = ''
    for extension in extensions:
        if keyNameLikeStr:
            keyNameLikeStr += ' or '
        keyNameLikeStr += "KeyNam like '%" + extension + "'"
    logging.info('keyNameLikeStr ' + str(keyNameLikeStr)) 

    req = """insert into CI_NO_OBJECTS (OBJECT_ID, ERROR_ID)
        select k.IdKey, 0 from Keys k
        where ObjTyp = 1000007
        and ( """ + keyNameLikeStr + \
        """ )
        and IdKey not in ( select IdParent from KeyPar )
        and IdKey in
            (select IdObj from ObjPro where IdPro in 
                (select k2.IdKey from Keys k2 where k2.ObjTyp in (1020005) )
        )
        and not IdKey in
            (select IdObj from ObjInf where InfTyp = 1020000 and InfSubTyp = 5 
        )
        and k.IdKey not in 
            (select IdObj from ObjPro where IdPro in 
                (select k2.IdKey from Keys k2 where k2.ObjTyp not in (1000001, 1020005) )
        )"""

    updateRequestIdentifier = 'html5_remove_files_with_no_children'
        
    try:
        logging.info('removing objects without children ' + req)
        updateKnowledgeBase(application, updateRequestIdentifier, req)
    except:
        logging.warning('HTML5-009 Error removing files without children: ' + req)

# Some xml files have not the HTML5 project, but only the UA one (those where UA writes "file skipped" in the log file
# we must remove these objects but only if they are not part of another project

    """
    2 examples:
    1 - web1.xml file belonging to 2 HTML5 AU
    2 - web2.xml file belonging to 1 HTML5 AU and 1 other non HTML5 AU over UA
    (1000001, 1020005, 141813) are UA project type, HTML5 project type and CAST_PluginProject project type
    
    keys
    -----
    id_web1            type_uafile
    id_web2            type_uafile
    
    id_proj1_html5    1020005
    id_proj1_ua        1000001
    id_proj1_plugin    141813

    id_proj2_html5    1020005
    id_proj2_ua        1000001
    id_proj2_plugin    141813

    id_proj3_other    type_other_project
    id_proj3_ua        1000001
    id_proj3_plugin    141813

    objpro
    ------
    id_web1            id_proj1_ua
    id_web1            id_proj2_ua

    id_web2            id_proj1_ua
    id_web2            id_proj3_ua

    anapro (we can find here correspondance between UA project and html5 project)
    ------
    id_job1       id_proj1_html5 
    id_job1       id_proj1_ua 
    id_job1       id_proj1_plugin 

    id_job2       id_proj2_html5 
    id_job2       id_proj2_ua 
    id_job2       id_proj2_plugin 

    id_job3       id_proj3_other 
    id_job3       id_proj3_ua 
    id_job3       id_proj3_plugin 
    """
    
    req = """insert into CI_NO_OBJECTS (OBJECT_ID, ERROR_ID)
        select k.IdKey, 0 from Keys k
        where ObjTyp = 1000007
        and ( KeyNam like '%.html' or KeyNam like '%.css' or KeyNam like '%.js' or KeyNam like '%.jsx' or KeyNam like '%.ts' or KeyNam like '%.tsx' or KeyNam like '%.xml' or KeyNam like '%.json' or KeyNam like '%.jade' or KeyNam like '%.yml')
        and IdKey not in ( select IdParent from KeyPar )
        and not IdKey in
            (select IdObj from ObjInf where InfTyp = 1020000 and InfSubTyp = 5 
        )
        and not exists (
                    select 1 from AnaPro a1
                    where 
                        a1.IdJob in (
                            select a2.IdJob from Anapro a2
                            where a2.IdPro in ( select o1.IdPro from Objpro o1 where o1.IdObj = k.IdKey)
                                 
                        )
                        and a1.IdPro not in (select k2.IdKey from Keys k2 where k2.IdKey = a1.IdPro and k2.ObjTyp in (1020005, 1000001, 141813))
        )"""

    try:
        logging.info('removing objects without children (second step) ' + req)
        updateKnowledgeBase(application, updateRequestIdentifier + '_2', req)
    except:
        logging.warning('HTML5-009 Error removing files without children second step: ' + req)

def remove_UA_grep_links(application):
    
    req_source_files = """insert into CI_NO_LINKS(CALLER_ID, CALLED_ID, ERROR_ID)
        select IdClr, IdCle, 0 from Acc
        where IdClr in (
                select distinct k.IdKey
                from Keys k join ObjPro op on op.IdObj = k.IdKey
                join Keys kp on op.IdPro = kp.IdKey and kp.ObjTyp in (1020005, 1000001) -- UA and HTML5 projects
                where k.ObjTyp = 1000007 -- UA file (sourceFile)
                -- the object is only in 2 projects : 1 UA and 1 HTML5
                and 2 = (select count(distinct op2.IdPro) 
                from ObjPro op2
                where op2.IdObj = k.IdKey
                )
                )
        or IdCle in (
                select distinct k.IdKey
                from Keys k join ObjPro op on op.IdObj = k.IdKey
                join Keys kp on op.IdPro = kp.IdKey and kp.ObjTyp in (1020005, 1000001) -- UA and HTML5 projects
                where k.ObjTyp = 1000007 -- UA file (sourceFile)
                -- the object is only in 2 projects : 1 UA and 1 HTML5
                and 2 = (select count(distinct op2.IdPro) 
                from ObjPro op2
                where op2.IdObj = k.IdKey
                )
                )"""
    try:
        logging.info('removing links generated by UA grep for HTML5 source files ' + req_source_files)
        updateKnowledgeBase(application, "html5_remove_sourceFile_links", req_source_files)
    except:
        logging.warning('HTML5-007 Error removing UA grep links ' + req_source_files)

def report_metric_properties(fromObject, toObject, totalCodeLines):

    if totalCodeLines:
        try:
            codeLines = fromObject.get_property('CAST_HTML5_JavaScript_SourceCode_metrics.totalCodeLinesCount')
        except:
            codeLines = None
    else:
        codeLines = fromObject.get_property('metric.CodeLinesCount')
    if codeLines != None:
        toObject.save_property('metric.CodeLinesCount', codeLines)
            
    codeLines = fromObject.get_property('metric.LeadingCommentLinesCount')
    if codeLines != None:
        toObject.save_property('metric.LeadingCommentLinesCount', codeLines)
            
    codeLines = fromObject.get_property('metric.BodyCommentLinesCount')
    if codeLines != None:
        toObject.save_property('metric.BodyCommentLinesCount', codeLines)
            
# comments are not reported anymore because this step is stuck when too big comments are present
#     comment = fromObject.get_property('comment.commentBeforeObject')
#     if comment:
#         toObject.save_property('comment.commentBeforeObject', comment)
#             
#     comment = fromObject.get_property('comment.sourceCodeComment')
#     if comment:
#         toObject.save_property('comment.sourceCodeComment', comment)
    
def report_codeLines_and_comments(application, languageDetectedByExtension):

    logging.info('Reporting properties from HTML5 objects to UA files objects')

    jsAndjspExtensions = ('.js', '.jsp', '.jsf', '.jsff', '.jspx', '.aspx', )
    jsExtensions = ('.js', )
    if languageDetectedByExtension:
        for _ext, language in languageDetectedByExtension.items():
            if language == 'jsp':
                jsAndjspExtensions = jsAndjspExtensions + (_ext, )
            elif language == 'js':
                jsExtensions = jsExtensions + (_ext, )
                jsAndjspExtensions = jsAndjspExtensions + (_ext, )
    logging.info('jsExtensions ' + str(jsExtensions))
    logging.info('jsAndjspExtensions ' + str(jsAndjspExtensions))
        
    logging.info('Retrieving .js sourceFile objects ...')
    cmpt = 1
    cmptJs = 0
    
    uaJSSourceFiles = {}
    for o in application.search_objects(category='sourceFile'):
        fn = o.get_fullname()
        if fn.endswith(jsExtensions):
            uaJSSourceFiles[fn] = o
            cmptJs += 1
        cmpt += 1

    logging.info('sourceFile objects successfully retrieved')
    
    application.declare_property_ownership('metric.CodeLinesCount',['sourceFile'])
    application.declare_property_ownership('metric.LeadingCommentLinesCount',['sourceFile'])
    application.declare_property_ownership('metric.BodyCommentLinesCount',['sourceFile'])
# comments are not reported anymore because this step is stuck when too big comments are present
#     application.declare_property_ownership('comment.commentBeforeObject',['sourceFile'])
#     application.declare_property_ownership('comment.sourceCodeComment',['sourceFile'])
    
#     properties = ['CAST_HTML5_JavaScript_SourceCode_metrics.totalCodeLinesCount', 'metric.CodeLinesCount', 'metric.LeadingCommentLinesCount', 'metric.BodyCommentLinesCount', 'comment.commentBeforeObject', 'comment.sourceCodeComment']
    properties = ['CAST_HTML5_JavaScript_SourceCode_metrics.totalCodeLinesCount', 'metric.CodeLinesCount', 'metric.LeadingCommentLinesCount', 'metric.BodyCommentLinesCount']
     
    logging.info('Retrieving CAST_HTML5_JavaScript_SourceCode objects ...')
    cmpt = 1

    for o in application.objects().has_type('CAST_HTML5_JavaScript_SourceCode').load_property(properties):
        fn = o.get_fullname()
        if not fn in uaJSSourceFiles:
            logging.debug('UA file not found fullname=' + fn)
            cmpt += 1
            continue
        parent = uaJSSourceFiles[fn]
        
        try:
            report_metric_properties(o, parent, True)
        except:
            logging.warning('HTML5-008 Update failed when reporting metric properties ' + fn)
        cmpt += 1

    logging.info('CAST_HTML5_JavaScript_SourceCode objects successfully retrieved')

#     properties2 = ['metric.CodeLinesCount', 'metric.LeadingCommentLinesCount', 'metric.BodyCommentLinesCount', 'comment.commentBeforeObject', 'comment.sourceCodeComment']
    properties2 = ['metric.CodeLinesCount', 'metric.LeadingCommentLinesCount', 'metric.BodyCommentLinesCount']
    # update properties on other UA files with the initial one (because declare_property_ownership provokes a reset to 0)
     
    logging.info('Retrieving internal sourceFile objects ...')
    cmpt = 1

    for o in application.objects().has_type('sourceFile').is_internal().load_property(properties2):
        fn = o.get_fullname()
        if fn.endswith(jsAndjspExtensions) or fn.endswith('.yml'):   # for yml files we do now want codeslines present.
            cmpt += 1
            continue
        try:
            report_metric_properties(o, o, False)
        except:
            logging.warning('HTML5-008 Update failed when reporting metric properties ' + fn)
        cmpt += 1

    logging.info('Internal sourceFile successfully retrieved')

def save_violation(o, propertyName, bm):
    if not bm.file:
        logging.warning('save_violation could not be done for ' + propertyName + ' (undefined file bookmark)')
        return
    o.save_violation(propertyName, bm)
   
def report_multi_technos_diags(application, languageDetectedByExtension):

    logging.info('Reporting properties concerning multi techno diags')
#     jsExtensions = ('.js', '.jsx', )
#     if languageDetectedByExtension:
#         for _ext, language in languageDetectedByExtension.items():
#             if language == 'js':
#                 jsExtensions = jsExtensions + (_ext, )
#     logging.info('jsExtensions ' + str(jsExtensions))
# 
#     uaJSSourceFiles = {}
#     for o in application.search_objects(category='sourceFile'):
#         fn = o.get_fullname()
#         if fn.endswith(jsExtensions):
#             uaJSSourceFiles[fn] = o
    
    application.declare_property_ownership('CAST_MetricAssistant_Metric_NumberOfForLoops.numberOfForLoops',['CAST_HTML5_Metric_NumberOfForLoops'])
    
    for o in application.objects().has_type(['CAST_HTML5_JavaScript_SourceCode', 'CAST_HTML5_JavaScript_Function', 'CAST_HTML5_JavaScript_Method']).load_property(['CAST_HTML5_Metric_NumberOfForLoops.numberOfForLoops', 'CAST_HTML5_Metric_AvoidBreakInForLoop.numberOfBreakInForLoop']):
        try:
            numberOfForLoops = o.get_property('CAST_HTML5_Metric_NumberOfForLoops.numberOfForLoops')
            if numberOfForLoops > 0:
                o.save_property('CAST_MetricAssistant_Metric_NumberOfForLoops.numberOfForLoops', numberOfForLoops)
        except:
            pass

    application.declare_property_ownership('CAST_MetricAssistant_Metric_NumberOfBreaksInForLoops.numberOfBreaksInForLoops',['CAST_HTML5_Metric_AvoidBreakInForLoop'])

    for o in application.objects().has_type(['CAST_HTML5_JavaScript_SourceCode', 'CAST_HTML5_JavaScript_Function', 'CAST_HTML5_JavaScript_Method']).load_violations(['CAST_HTML5_Metric_AvoidBreakInForLoop.numberOfBreakInForLoop']):
        for violation in o.get_violations('CAST_HTML5_Metric_AvoidBreakInForLoop.numberOfBreakInForLoop'):
            save_violation(o, 'CAST_MetricAssistant_Metric_NumberOfBreaksInForLoops.numberOfBreaksInForLoops', violation[1])
    
    application.declare_property_ownership('CAST_MetricAssistant_Metric_NumberOfSwitchWithNoDefault.numberOfSwitchWithNoDefault',['CAST_HTML5_Metric_AvoidMissingDefaultInSwitch'])
    
    for o in application.objects().has_type(['CAST_HTML5_JavaScript_SourceCode', 'CAST_HTML5_JavaScript_Function', 'CAST_HTML5_JavaScript_Method']).load_violations(['CAST_HTML5_Metric_AvoidMissingDefaultInSwitch.numberOfSwitchNoDefault']):
        for violation in o.get_violations('CAST_HTML5_Metric_AvoidMissingDefaultInSwitch.numberOfSwitchNoDefault'):
            save_violation(o, 'CAST_MetricAssistant_Metric_NumberOfSwitchWithNoDefault.numberOfSwitchWithNoDefault', violation[1])
    
# Following properties can not be updated in analyzer himself because the DOTNET category property has not 'merge="sum"' property and the extension framework
# prevents updating this property.

    application.declare_property_ownership('CAST_DotNet_Metric_AvoidEmptyCatchBlocks.number',['CAST_HTML5_Metric_AvoidEmptyCatchBlocks'])
    
    for o in application.objects().has_type(['CAST_HTML5_JavaScript_SourceCode', 'CAST_HTML5_JavaScript_Function', 'CAST_HTML5_JavaScript_Method']).load_violations(['CAST_HTML5_Metric_AvoidEmptyCatchBlocks.numberOfEmptyCatchBlocks']):
        for violation in o.get_violations('CAST_HTML5_Metric_AvoidEmptyCatchBlocks.numberOfEmptyCatchBlocks'):
            save_violation(o, 'CAST_DotNet_Metric_AvoidEmptyCatchBlocks.number', violation[1])
    
    application.declare_property_ownership('CAST_DotNet_Metric_AvoidEmptyFinallyBlocks.number',['CAST_HTML5_Metric_AvoidEmptyFinallyBlocks'])
    
    for o in application.objects().has_type(['CAST_HTML5_JavaScript_SourceCode', 'CAST_HTML5_JavaScript_Function', 'CAST_HTML5_JavaScript_Method']).load_violations(['CAST_HTML5_Metric_AvoidEmptyFinallyBlocks.numberOfEmptyFinallyBlocks']):
        for violation in o.get_violations('CAST_HTML5_Metric_AvoidEmptyFinallyBlocks.numberOfEmptyFinallyBlocks'):
            save_violation(o, 'CAST_DotNet_Metric_AvoidEmptyFinallyBlocks.number', violation[1])


    
    application.declare_property_ownership('CAST_MetricAssistant_Metric_cyclomaticComplexity.cyclomatic',['CAST_HTML5_JavaScript_Metrics_Category_From_MA'])
    application.declare_property_ownership('CAST_MetricAssistant_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine',['CAST_HTML5_JavaScript_Metrics_Category_From_MA'])
    
    for o in application.objects().has_type(['CAST_HTML5_JavaScript_SourceCode', 'CAST_HTML5_JavaScript_Function', 'CAST_HTML5_JavaScript_Method', 'CAST_HTML5_JavaScript_SourceCode_Fragment']).load_property(['CAST_HTML5_JavaScript_Metrics_Category_From_MA.complexity', 'CAST_HTML5_JavaScript_Metrics_Category_From_MA.lengthOfTheLongestLine']):
        _prop = o.get_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.complexity')
        if _prop:
            o.save_property('CAST_MetricAssistant_Metric_cyclomaticComplexity.cyclomatic', _prop)
        _prop = o.get_property('CAST_HTML5_JavaScript_Metrics_Category_From_MA.lengthOfTheLongestLine')
        if _prop:
            o.save_property('CAST_MetricAssistant_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine', _prop)

    application.declare_property_ownership('CAST_MetricAssistant_Metric_cyclomaticComplexity.cyclomatic',['CAST_HTML5_SourceCode', 'CAST_HTML5_CSS_SourceCode_Fragment', 'CAST_HTML5_HTML_Fragment', 'CAST_HTML5_CSS_SourceCode', 'CAST_HTML5_Jade_SourceCode', 'CAST_HTML5_JSP_Content', 'CAST_HTML5_ASP_Content', 'CAST_HTML5_CSHTML_Content'])
    application.declare_property_ownership('CAST_MetricAssistant_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine',['CAST_HTML5_SourceCode', 'CAST_HTML5_CSS_SourceCode_Fragment', 'CAST_HTML5_HTML_Fragment', 'CAST_HTML5_CSS_SourceCode', 'CAST_HTML5_Jade_SourceCode', 'CAST_HTML5_JSP_Content', 'CAST_HTML5_ASP_Content', 'CAST_HTML5_CSHTML_Content'])
    
    for o in application.objects().has_type(['CAST_HTML5_SourceCode', 'CAST_HTML5_CSS_SourceCode_Fragment', 'CAST_HTML5_HTML_Fragment', 'CAST_HTML5_CSS_SourceCode', 'CAST_HTML5_Jade_SourceCode', 'CAST_HTML5_JSP_Content', 'CAST_HTML5_ASP_Content', 'CAST_HTML5_CSHTML_Content']):
        o.save_property('CAST_MetricAssistant_Metric_cyclomaticComplexity.cyclomatic', 1)
        o.save_property('CAST_MetricAssistant_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine', 1)
        
class ExtensionApplication(ApplicationLevelExtension):
    
    def end_application(self, application):

        languageDetectedByExtension = {}
        try:
            f = self.get_intermediate_file("html5.txt")
            if not f or f.isstdin():
                logging.info('No user defined extensions detected (f not found)')
            else:
                languageDetectedByExtensionStr = ''
                for line in f.readline():
                    languageDetectedByExtensionStr += line
                languageDetectedByExtensionStr = languageDetectedByExtensionStr.strip()
                if languageDetectedByExtensionStr:
                    try:
                        languageDetectedByExtension = json.loads(languageDetectedByExtensionStr)
                    except:
                        logging.warning('Problem when converting user defined extensions')
                        logging.warning(str(traceback.format_exc()))
                    logging.info('User defined extensions detected: ' + languageDetectedByExtensionStr)
            f.close()
        except:
            logging.warning('No user defined extensions detected (exception)')
            logging.warning(str(traceback.format_exc()))
        
        remove_skipped_files(application, languageDetectedByExtension)

        if not html5_has_been_launched(application):
            return
        
        remove_UA_grep_links(application)
        report_multi_technos_diags(application, languageDetectedByExtension)
        report_codeLines_and_comments(application, languageDetectedByExtension)
        