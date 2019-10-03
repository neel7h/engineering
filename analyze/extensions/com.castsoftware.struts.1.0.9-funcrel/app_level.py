'''
Created on 23 feb. 2018

@author: IBO
'''
import cast_upgrade_1_5_11 # @UnusedImport
from cast.application import ApplicationLevelExtension
import logging

    
def updateKnowledgeBase(application, _id, req):
    application.update_cast_knowledge_base(_id, req)
    pass

def remove_jee_struts_objects(application):

    req = """insert into CI_NO_OBJECTS (OBJECT_ID, ERROR_ID)
select IdKey, 0 from Keys 
  where 
     ObjTyp in (367, 958) -- JSP_ACTION_MAPPING (Struts Action Mapping), JSP_FORWARD (Struts Forward)"""
    try:
        logging.info('removing Struts Action Mapping: ' + req)
        updateKnowledgeBase(application, 'html5_remove_skipped_files', req)
    except:
        logging.warning('STRUTS-001 Error removing Struts Action Mapping: ' + req)
        
class ExtensionApplication(ApplicationLevelExtension):
    
    def end_application(self, application):

#         remove_jee_struts_objects(application)
        pass
        