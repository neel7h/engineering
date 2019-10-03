import cast_upgrade_1_5_22 # @UnusedImport

from cast.application import  ApplicationLevelExtension, Bookmark
import logging
from cast.application import create_link

class LinkProceduresWithExternalProgram(ApplicationLevelExtension):

    def end_application(self, application):
        logging.info("Start adding links between stored procedures, functions  and external programs for application %s" % application.name)
        
        def look_for_cobol_saved_program (external_name):
            for client in application.objects().has_type('CAST_COBOL_SavedProgram'):
                if client.name.lower() == external_name.lower():
                    return(client)
            for client in application.objects().has_type('CAST_COBOL_NestedProgram'):
                if client.name.lower() == external_name.lower():
                    return(client)
                                
            return None

        def look_for_java_saved_program (external_name):
            for client in application.objects().has_type('JV_METHOD'):
                if client.name.lower() in external_name.lower():
                    return(client)
                                
            return None

        def look_for_c_cpp_saved_program (external_name):
            for client in application.objects().has_type('C_FUNCTION'):
                if client.name.lower() in external_name.lower():
                    return(client)
                                
            return None
                
        application.declare_property_ownership('SQLScriptExternalProgram.external_position',['SQLScriptProcedure', 'SQLScriptFunction'])
                
                       
        count_links = 0
        
        for client in application.objects().load_property('SQLScriptExternalProgram.external_name').load_property('SQLScriptExternalProgram.language').load_property('SQLScriptExternalProgram.external_position').has_type('SQLScriptExternalProgram').load_positions():
            external_name = client.get_property('SQLScriptExternalProgram.external_name') 
            language = client.get_property('SQLScriptExternalProgram.language') 
            external_position = client.get_property('SQLScriptExternalProgram.external_position') 
            called = None
            if language and language.lower() =='cobol':
                called = look_for_cobol_saved_program (external_name)
            elif language and language.lower() == 'java':
                called = look_for_java_saved_program (external_name)
            elif language and language.lower() == 'c':
                called = look_for_c_cpp_saved_program (external_name)   
                         
            if called:
                data = external_position.split()
                begin_line = int(data[0])
                begin_column = int(data[1])
                end_line = int(data[2])
                end_column = int(data[3])
                try:
                    first_bookmark = client.get_positions()[0]
                    bookmark = Bookmark(first_bookmark.file, begin_line, begin_column, end_line, end_column)
                except:
                    bookmark = Bookmark(client, begin_line, begin_column, end_line, end_column)
                create_link('callLink', client, called, bookmark) 
                count_links += 1
                    
        logging.info("End adding links (%s) between stored procedures, functions and external programs for application %s" % (count_links, application.name))
                    
