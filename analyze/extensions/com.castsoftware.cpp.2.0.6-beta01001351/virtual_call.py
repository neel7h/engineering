'''
Created on 26 janv. 2016

Create virtual calls

@author: MRO
'''
import cast_upgrade_1_6_1 # @UnusedImport
from cast.application import ApplicationLevelExtension, create_link, LinkType # @UnresolvedImport
import logging
from collections import defaultdict


class CreateVirtualCall(ApplicationLevelExtension):
    """
    Create virtual calls for C++
    """
    
    @staticmethod
    def one_step(application, links_by_callee, result):
        """
        take a map callee -> links 
        and return a map callee -> links for the next step
        fill result with the links to create
        
        """
        called = links_by_callee.keys()
        
        logging.info('len of called %s', str(len(called)))
        
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
         
        # list the calls to abstract methods
        cpp_abstract = application.objects().has_type('CAST_C_KB_Symbol').is_virtual()
        
        for link in application.links().has_callee(cpp_abstract).has_type(LinkType.call):
            # @type link:cast.application.EnlightenLink
            
            project = link.get_project()
            # do not take into account the links we already created by this extension
            # so that we recreate it
            # also handle case where there is lot of virtual links
            # @todo : will still not hanlde tons of links
            if project.get_type() == 'CAST_ApplicationPluginProject' and project.get_name().endswith('/com.castsoftware.cpp'):
                continue
            
            abstract[link.get_callee()].append(link)
        
        links_by_callee = abstract
         
        result = set()
        
        links_by_callee = CreateVirtualCall.one_step(application, links_by_callee, result)
        
        # saturate result
        count = 0
        while count != len(result):
            count = len(result)
            links_by_callee = CreateVirtualCall.one_step(application, links_by_callee, result)
        
        return result
        
    
    def end_application(self, application):

        logging.info('Creating "virtual call" links')
        
        result = self.calculate_links(application)
        
        for r in result:
            create_link('callLink', r[0], r[1])

        logging.info('Created %s "virtual call" links' % len(result))

        
