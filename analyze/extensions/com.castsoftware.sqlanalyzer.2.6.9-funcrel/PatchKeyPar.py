import cast.application
import logging

class ExtensionApplication(cast.application.ApplicationLevelExtension):

    def end_application(self, application):
        logging.debug("running code at the end of an application to fix duplicated node schema")
        application.sql_tool("""
        delete from KeyPar
        where exists (select 1 from Keys, Typ where ObjTyp = IdTyp and TypNam = 'SQLScriptSchema' and Keys.IdKey = KeyPar.IdKey)
             and exists(select 1 from Keys, Typ where ObjTyp = IdTyp and TypNam = 'sourceFile' and Keys.IdKey = KeyPar.IdParent)
        """)