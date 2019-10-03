import unittest
from migrate_guid import calculate_new_guid 


class Test(unittest.TestCase):

    
    def test_case_01(self):
        
        fullname = '[S:\\CAIP\\SRC\\XMLMng32\\htmlutils.h].[CHTMLProp].[FirstSave(void*)]'
        old_guid = 'C_Cl.CHTMLProp.C_Met.FirstSave(-1601902600):c.C_Fi."S:\\CAIP\\SRC\\XMLMNG32\\HTMLUTILS..H"'
        export_name = 'CHTMLProp::FirstSave(void*)'
        
        self.assertEqual("[S:\\CAIP\\SRC\\XMLMNG32\\HTMLUTILS.H].[CHTMLProp].[FirstSave(void*)]", 
                         calculate_new_guid(fullname, old_guid, export_name))
        
    def test_case_02(self):
        
        fullname = '[S:\\CAIP\\SRC\\XMLMng32\\htmlutils.h].[CHTMLProp].[FirstSave(void*)]'
        old_guid = 'C_Cl.CHTMLProp.C_Met.FirstSave(-1601902600):c.C_Fi."S:\\CAIP\\SRC\\XMLMNG32\\HTMLUTILS..H"'
        export_name = 'CHTMLProp::FirstSave(void*)const'
        
        self.assertEqual("[S:\\CAIP\\SRC\\XMLMNG32\\HTMLUTILS.H].[CHTMLProp].[FirstSave(void*)]const", 
                         calculate_new_guid(fullname, old_guid, export_name))
        
    def test_case_03(self):
        
        fullname = '[S:\\CAIP\\SRC\\XMLMng32\\htmlutils.h].[CHTMLProp].[FirstSave(void*)]'
        old_guid = 'C_Cl.CHTMLProp.C_Met.FirstSave(-1601902600):<int:>'
        export_name = 'CHTMLProp::FirstSave(void*)const'
        
        self.assertEqual("[S:\\CAIP\\SRC\\XMLMNG32\\HTMLUTILS.H].[CHTMLProp].[FirstSave(void*)]const", 
                         calculate_new_guid(fullname, old_guid, export_name))

    def test_case_04(self):
        
        fullname = None
        old_guid = 'C_Cl.CHTMLProp.C_Met.FirstSave(-1601902600):<int:>'
        export_name = 'CHTMLProp::FirstSave(void*)const'
        
        self.assertEqual(old_guid, 
                         calculate_new_guid(fullname, old_guid, export_name))

if __name__ == "__main__":
    unittest.main()
