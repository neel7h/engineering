from cast.application import ApplicationLevelExtension
import logging
from distutils.version import StrictVersion


class LineOfCodeExtension(ApplicationLevelExtension):
    
    def end_application(self, application):
        """
        LOC is counting of objects inheriting from APM Sources
        But SQLScriptProcedure, ... inherit from them indirectly
        """
        logging.info("Start fixing LOC for sqltablesize and uaxdirectory files")
        
        application.sql_tool("delete from TypCat where IdCatParent = 10048 and IdTyp >= 1101000 and IdTyp <= 1101999")
        
                # put 8.0.0 as default CAST version
        castVersion = '8.0.0'
        try:
            castVersion = str(application.get_knowledge_base().get_caip_version())
        except AttributeError: 
            logging.debug("Cannot detect CAST version, so we will consider it is 8.0.0.")
            pass
        # Return type:   distutils.version.StrictVersion
        if (castVersion < StrictVersion('8.2.11') and castVersion >= StrictVersion('8.3.0')) \
            or StrictVersion(castVersion) < '8.3.4': 
            logging.debug("sqltablesize and uaxdirectory CodeLinesCount metric should be set to 0 (CAST version is %s)." % castVersion)
            try:
                        
                # sqltablesize,  uaxdirectory and gdpr files must be counted to zero 
                application.sql_tool("""
        update ObjInf set InfVal = 0 where 
        IdObj in (select IdKey from Keys 
                  where ObjTyp = 1000007 and (LOWER(KeyNam) like '%.sqltablesize' or LOWER(KeyNam) like '%.uaxdirectory' or LOWER(KeyNam) like '%.gdpr'))
        and InfTyp = 1 and InfSubTyp=0        
                """)
            except AttributeError:
                logging.debug("There is no analysis result, so sqltablesize and uaxdirectory CodeLinesCount cannot be set to 0.")
                pass  
                  
        logging.info("End fixing LOC for sqltablesize and uaxdirectory files")
