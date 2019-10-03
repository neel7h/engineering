import cast_upgrade_1_6_1  # @UnusedImport
from cast.application import ApplicationLevelExtension, create_link, LinkType # @UnresolvedImport
from collections import defaultdict
import logging


class JavaDevirtualisation(ApplicationLevelExtension):
    """
    Any link :
        spring mvc operation --> java abstract method
    will be devirtualised using CHA.
    """
    @staticmethod
    def one_step(application, links_by_callee, result):
        """
        take a map callee -> links 
        and return a map callee -> links for the next step
        fill result with the links to create
        
        """
        called = links_by_callee.keys()
        
        overrides = defaultdict(list)
        
        # search for the overriden for called methods
        for link in application.links().has_callee(called).has_type([LinkType.inheritOverride, LinkType.inheritImplement]):
            
            overrides[link.get_callee()].append(link.get_caller())
    
            
        links_to_create = []
        
        # we need also to find the next level overrides
        next_step_link_by_callee = defaultdict(list)
        
        for base_method, derived_methods in overrides.items():
            calling_links = links_by_callee[base_method]
            
            links_to_create.append((calling_links,derived_methods))
            
            for method in derived_methods:
                next_step_link_by_callee[method] = calling_links
        
    #    print('links to create')
        for calling_links, derived_methods in links_to_create:
            for link in calling_links:
                for derived_method in derived_methods:
    #                print (' ', link.caller, ' -->', derived_method)
                    
                    result.add((link.get_caller(), derived_method))
                    
        return next_step_link_by_callee
    
    @staticmethod
    def calculate_links(application):
    
        # map abstract method --> links to that method
        abstract = defaultdict(list)
         
        # list the links from operations to java abstract methods
        java_abstract = application.objects().is_executable().has_type('Java').is_abstract()
        operations = application.objects().has_type(['CAST_SpringMVC_GetOperation',
                                                     'CAST_SpringMVC_PostOperation',
                                                     'CAST_SpringMVC_PutOperation',
                                                     'CAST_SpringMVC_DeleteOperation',
                                                     'CAST_SpringMVC_AnyOperation'])
        
        result = set()
        if java_abstract.count() == 0 or operations.count() == 0:
            return result

        for link in application.links().has_caller(operations).has_callee(java_abstract):
            abstract[link.get_callee()].append(link)
        
        links_by_callee = abstract
         
        links_by_callee = JavaDevirtualisation.one_step(application, links_by_callee, result)
        
        # saturate result
        count = 0
        while count != len(result):
            count = len(result)
            links_by_callee = JavaDevirtualisation.one_step(application, links_by_callee, result)
        
        return result
        
    
    def end_application(self, application):
        
        logging.info('Devirtualization of Spring MVC links')
        result = self.calculate_links(application)
        
        for r in result:
            create_link('callLink', r[0], r[1])

        logging.info('Created %s links' % len(result))
