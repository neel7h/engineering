import cast.application
import logging

class ExtensionApplication(cast.application.ApplicationLevelExtension):

    def end_application(self, application):
        logging.debug("running code at the end of an application to remove enlighten visibility for ua project associated with SQL analysis")
        application.sql_tool("""
        delete from TypCat where IdTyp = 1101005 and IdCatParent in (5020, 5023, 5024)
        """)