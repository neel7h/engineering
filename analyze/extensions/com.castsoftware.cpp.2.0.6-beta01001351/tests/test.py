'''
Created on 26 janv. 2016

@author: MRO
'''
import unittest
import cast_upgrade_1_6_1 # @UnusedImport
from cast.application.test import TestKnowledgeBase # @UnresolvedImport
from cast.application import LinkType # @UnresolvedImport
from virtual_call import CreateVirtualCall


class Test(unittest.TestCase):

    
    def test_cpp_virtual_function(self):
        """
        basic test
        """
        test = TestKnowledgeBase()

        project = test.add_project('toto', 'C_CLASSPROJECT')
        
        # one abstract method with one override
        callee = project.add_object('abstract', 'A.abstract', 'C_METHOD', keyprop=1024)
        override = project.add_object('override', 'A.override', 'C_METHOD')
        project.add_link(LinkType.inheritOverride, override, callee)
        
        # abstract method is called 
        caller = project.add_object('caller', 'B.caller', 'C_METHOD')
        project.add_link(LinkType.call, caller, callee)
        
        extension = CreateVirtualCall()
        
        application = test.run(extension.end_application)
        
        result = list(application.links().has_caller([caller]).has_callee([override]))
        
        self.assertEqual(1, len(result))
       
    
    def test_cpp_two_overrides(self):
        """
        level 2 inheritance
        """
    
        test = TestKnowledgeBase()

        project = test.add_project('toto', 'C_CLASSPROJECT')
        
        # one abstract method with one override
        callee = project.add_object('abstract', 'A.abstract', 'C_METHOD', keyprop=1024)
        override1 = project.add_object('override1', 'A.override1', 'C_METHOD')
        project.add_link(LinkType.inheritOverride, override1, callee)

        override2 = project.add_object('override2', 'A.override2', 'C_METHOD')
        project.add_link(LinkType.inheritOverride, override2, override1)
        
        # abstract method is called 
        caller = project.add_object('caller', 'B.caller', 'C_METHOD')
        project.add_link(LinkType.call, caller, callee)
        
        extension = CreateVirtualCall()
        
        application = test.run(extension.end_application)
        
        result = list(application.links().has_caller([caller]).has_callee([override1]))
        self.assertEqual(1, len(result))

        result = list(application.links().has_caller([caller]).has_callee([override2]))
        self.assertEqual(1, len(result))

    def test_cpp_level_two_inheritance(self):
        """
        2 overrides
        """
    
        test = TestKnowledgeBase()

        project = test.add_project('toto', 'C_CLASSPROJECT')
        
        # one abstract method with one override
        callee = project.add_object('abstract', 'A.abstract', 'C_METHOD', keyprop=1024)
        override1 = project.add_object('override1', 'A.override1', 'C_METHOD')
        project.add_link(LinkType.inheritOverride, override1, callee)

        override2 = project.add_object('override2', 'A.override2', 'C_METHOD')
        project.add_link(LinkType.inheritOverride, override2, callee)
        
        # abstract method is called 
        caller = project.add_object('caller', 'B.caller', 'C_METHOD')
        project.add_link(LinkType.call, caller, callee)
        
        extension = CreateVirtualCall()
        
        application = test.run(extension.end_application)
        
        result = list(application.links().has_caller([caller]).has_callee([override1]))
        self.assertEqual(1, len(result))

        result = list(application.links().has_caller([caller]).has_callee([override2]))
        self.assertEqual(1, len(result))

    def test_cpp_virtual_by_inheritance_function(self):
        """
        basic test
        """
        test = TestKnowledgeBase()

        project = test.add_project('toto', 'C_CLASSPROJECT')
        
        # one abstract method with one override
        callee = project.add_object('abstract', 'A.abstract', 'C_METHOD', keyprop=8388608)
        override = project.add_object('override', 'A.override', 'C_METHOD')
        project.add_link(LinkType.inheritOverride, override, callee)
        
        # abstract method is called 
        caller = project.add_object('caller', 'B.caller', 'C_METHOD')
        project.add_link(LinkType.call, caller, callee)
        
        extension = CreateVirtualCall()
        
        application = test.run(extension.end_application)
        
        result = list(application.links().has_caller([caller]).has_callee([override]))
        
        self.assertEqual(1, len(result))

       
if __name__ == "__main__":
    unittest.main()
