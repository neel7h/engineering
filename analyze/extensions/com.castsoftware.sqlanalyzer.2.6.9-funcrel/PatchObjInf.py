import cast.application
import logging
from distutils.version import StrictVersion

class ExtensionApplication(cast.application.ApplicationLevelExtension):

    def end_application(self, application):
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
            logging.debug("Move SQL_CodeLinesCount to CodeLinesCount (CAST version is %s)." % castVersion)
            try:
                application.sql_tool("""
                update ObjInf
                set InfVal = (select oioi.InfVal
                                from ObjInf oioi
                                where ObjInf.IdObj = oioi.IdObj
                                and ObjInf.InfTyp = 1 and ObjInf.InfSubTyp = 0
                                and oioi.InfTyp = 1101000 and oioi.InfSubTyp = 6
                                )
                where exists(select 1 
                                from ObjInf oioi
                                where ObjInf.IdObj = oioi.IdObj
                                and ObjInf.InfTyp = 1 and ObjInf.InfSubTyp = 0
                                and oioi.InfTyp = 1101000 and oioi.InfSubTyp = 6
                )
                """)
            except AttributeError:
                logging.debug("There is no analysis result, so the SQL_CodeLinesCount value cannot be moved to CodeLinesCount.")
                pass