'''
Created on 26 mai 2016

@author: MRO
'''
import os
import xml.etree.ElementTree as ET
from variant import Variant

def find_vendor(node):

    if node.tag == 'UAXOption' and node.attrib['name'] in ['RDBMS.Name']:
        yield node

    else:
        
        for n in node:
            
            for vendor in find_vendor(n):
                yield vendor
                               
def find_schemas(node):

    if node.tag == 'UAXFile' and node.attrib['type'] in ['CAST_ASETSQL_Schema',
                                                         'CAST_DB2ZOS_Schema',
                                                         'CAST_MSTSQL_Schema',
                                                         'CAST_Oracle_Schema']:
        yield node

    else:
        
        for n in node:
            
            for schema in find_schemas(n):
                yield schema


def load_uaxdirectory(path):
    """
    Basic loading of schema names associated with src files
    """
    result = Result()
    result.variant = None
    result.sqlserver_with_go = None

    try:

        tree = ET.parse(path)
        root = tree.getroot()
        
        for vendor in find_vendor(root):
            if vendor.attrib['value'].count('Sybase') > 0\
                or vendor.attrib['value'].count('ASE')> 0 \
                or vendor.attrib['value'].count('MS') > 0\
                or vendor.attrib['value'].count('Microsoft')  > 0:
                result.variant = Variant.sqlserver
                result.sqlserver_with_go = True
            elif vendor.attrib['value'].count('Oracle') > 0:
                result.variant = Variant.oracle
            break
                
        for schema in find_schemas(root): 
        
            schema_name = schema.attrib['name']
        
            # sub nodes
            for f in schema:
                
                path = f.attrib['path']
                path = path.replace('.uax', '.src')
                
                result.map[path] = schema_name
                
                _type = f.attrib['type']
                if _type in ['CAST_ASETSQL_RelationalTable',
                             'CAST_MSTSQL_View',
                             'CAST_Oracle_RelationalTable',
                             'CAST_Oracle_View',
                             'CAST_ASETSQL_RelationalTable',
                             'CAST_ASETSQL_View'
                             ]:
                    result.table_or_views.add(path)
                
                
    except:
        print('issue when load_uaxdirectory')
        pass
    
    return result



class Result:
    
    def __init__(self):
        
        self.map = {}
        self.table_or_views = set()
        
    def get_schema_name(self, path):
        """
        Provide the schema name given a .src file path
        """
        try:        
            return self.map[os.path.basename(path)]
        except:
            try:
                return self.map['%s/%s' % (os.path.basename(os.path.dirname(path)), os.path.basename(path))]
            except:
                print('issue when get_schema_name')
                pass
    
    def is_table_or_view(self, path):
        """
        True when the given a .src file path represent a table or a view
        """
        if os.path.basename(path) in self.table_or_views:
            return True
        elif ('%s/%s' % (os.path.basename(os.path.dirname(path)), os.path.basename(path))) in self.table_or_views:
            return True
        
        return False
    