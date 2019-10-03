import cast_upgrade_1_5_22 # @UnusedImport
from cast.application import  ApplicationLevelExtension
from logging import debug, info
from traceback import format_exc
from logger import warning
from cast.application import create_link

class SynonymLinksProperties(ApplicationLevelExtension):
    
    def end_application(self, application):
        
        info("Start pushing links from synonyms to aliased objects")
        list_of_callee_types = ['SQLScriptTable', 'SQLScriptView', 'SQLScriptMethod','SQLScriptType', 'SQLScriptProcedure', 'SQLScriptFunction']
        list_of_synonyms_temporary_types = ['SQLScriptTypeSynonym', 'SQLScriptProcedureSynonym', 
                                            'SQLScriptFunctionSynonym', 'SQLScriptViewSynonym', 'SQLScriptTableSynonym']
        
        temporary_links = application.links().has_callee(application.objects().has_type(list_of_callee_types))\
                                                         .has_caller(application.objects().has_type(list_of_synonyms_temporary_types)).count()
        if temporary_links == 0:
            debug("    There is no link between aliased objects and temporary objects")
        else:
            client = None
            bookmark = None
            aliased = None
            alias = None
            list_links_type = None
            
            list_of_aliases = []
            list_of_aliased_links = []
            list_of_aliased_links_t = []
            list_of_aliased_links_o = []
            list_of_o_callee_types = ['SQLScriptView', 'SQLScriptType', 'SQLScriptProcedure', 'SQLScriptFunction']
            list_of_link_types = ('useSelect', 'useDelete', 'useUpdate', 'useInsert', 'call', 'useSelectLink', 'useDeleteLink', 'useUpdateLink', 
                                  'useInsertLink', 'callLink')
            list_of_excluded_types = list_of_synonyms_temporary_types + \
									['SQLScriptSynonym', 'SQLScriptUniqueConstraint', 'SQLScriptForeignKey',
									'SQLScriptIndex', 'SQLScriptTableColumn', 'SQLScriptExternalProgram',
                                    'SQLScriptPackage', 'SQLScriptPackageSynonym']

            list_of_excluded_types_t = ['SQLScriptTable'] + list_of_excluded_types
            
            # retrieve the list of links for objects that could have aliases
            for link in application.links().load_positions()\
                .has_callee(application.objects().has_type('SQLScriptTable'))\
                .has_caller(application.objects().not_has_type(list_of_excluded_types_t)):

                list_links_type, aliased, client, bookmark = link.get_type_names(), link.get_callee(), link.get_caller(), link.get_positions()
                if not bookmark:
                    continue

                list_of_aliased_links_temp = [(link_type, client, aliased, bookmark[0]) for link_type in list_links_type if link_type in list_of_link_types]
                list_of_aliased_links_t += list_of_aliased_links_temp
                
            for link in application.links().load_positions()\
                .has_callee(application.objects().has_type(list_of_o_callee_types))\
                .has_caller(application.objects().not_has_type(list_of_excluded_types)):

                list_links_type, aliased, client, bookmark = link.get_type_names(), link.get_callee(), link.get_caller(), link.get_positions()

                if not bookmark:
                    continue
                list_of_aliased_links_temp = [(link_type, client, aliased, bookmark[0]) for link_type in list_links_type if link_type in list_of_link_types]
                list_of_aliased_links_o += list_of_aliased_links_temp
                           
            list_of_aliased_links = list_of_aliased_links_t + list_of_aliased_links_o

            # retrieve alias and objects aliased list
            list_of_aliases = [(link.get_callee(), link.get_caller()) for link in application.links()\
                               .has_callee(application.objects().has_type(list_of_callee_types))\
                               .has_caller(application.objects().has_type(list_of_synonyms_temporary_types))]

            def check_final_object (alias):
                for aliased in list_of_aliases:
                    if str(aliased[1]) == str(alias):
                        return aliased[0]
                return None
    
            def check_exists_link (link_type, client, aliased, bookmark):
                existing_link = False
                for list_of_links in list_of_aliased_links:
                    if str(link_type) == str(list_of_links[0]) and str(client) == str(list_of_links[1]) \
                     and str(aliased) == str(list_of_links[2]) and str(bookmark) == str(list_of_links[3]):
                        existing_link = True
                        break
                
                return existing_link
            
            # retrieve the list between aliases and client objects
            # from the list of client objects explude temporary objects and table subobjects, like FK, PK, etc
            for link in application.links().load_positions()\
						.has_callee(application.objects().has_type(list_of_synonyms_temporary_types))\
						.has_caller(application.objects().not_has_type(list_of_excluded_types)):
                list_links_type = link.get_type_names()
                client = link.get_caller()
                alias = link.get_callee()
                bookmark = link.get_positions()
                
                if not bookmark:
                    continue
                
                # retrieve the aliased object
                aliased = check_final_object(alias)
                if not aliased:
                    continue
                
                for link_type in list_links_type:
                    if link_type in list_of_link_types: 
                        links_exists = check_exists_link (link_type, client.fullname, aliased.fullname, bookmark[0])           
                        if not links_exists:
                            saved_link_type = link_type if link_type[-4:].lower() == 'link' else '%sLink' % link_type  
                            try:
#                                 print('    Add ', saved_link_type, ' between ', client.fullname,' and ',  aliased.fullname, ', bookmark=(', bookmark[0], ')')
                                debug("    Add %s between %s and %s, bookmark=(%s)" % (saved_link_type, client.fullname, aliased.fullname, bookmark[0]))

                                create_link(saved_link_type, client, aliased, bookmark[0])
                            except:
                                warning('SQL-013','Links could not be moved from synonyms to aliased objects because of %s ' % format_exc())
                            
        info("End pushing links from synonyms to aliased objects")

        info("Start removing temporary objects")
            
        req = """insert into CI_NO_OBJECTS (OBJECT_ID, ERROR_ID)
select IdKey, 0 from Keys 
  where 
     ObjTyp in ( 1101042, 1101043, 1101044, 1101045, 1101046, 1101050) -- specific synonyms
"""
        try:
            application.update_cast_knowledge_base('SQL-007', req)
        except:
            warning('SQL-007','Temporary objects cannot be removed, because of %s ' % format_exc())
    
        info("End removing temporary objects")