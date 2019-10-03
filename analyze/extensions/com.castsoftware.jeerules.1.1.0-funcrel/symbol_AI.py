'''
Created on Sep 3, 2018

@author: MRE
'''
from cast.analysers import log, Method
import types
import string
import itertools
from cast.application import open_source_file
import re
from email.policy import default
from builtins import len
from numpy.core.defchararray import lstrip
    
class read_file(object):
    listoffile = []
    m_dict = {}
    import_stat = {}
    
    def __init__(self, file):
        self.file = file
        self.__dict = {}
        self.fldvalue = {}
        self.keyvalue = {}
        self.isxmlparserimported = False
        self.isservletpckimported = False
        self.actual_class_name = ''
        

    def get_importstatement(self):
        with open_source_file(self.file) as impfile:
            if self.file[-5:] == '.java':
                import_files = [(line) for index, line in enumerate(impfile) if re.search(r'import (static )*([^;])*', line)]   
            elif self.file[-4:] == '.jsp':
                import_files = [(line) for index, line in enumerate(impfile) if re.search(r'<%@ page import', line)]
                         
            return import_files
 
    def get_indexedLines(self):
        with open_source_file(self.file) as textfile:
            field_data = [(index,line) for index, line in enumerate(textfile) if not re.search(r'import (static )*([^;])*', line)]
        
            return field_data
        
    def generate_fieldinfo(self, classname, fieldname, force = False):
        try:                
            method_name = ''
            block_comment_started = False

            is_methodstarted = False
            if self.file in self.listoffile and not force:
                return
            
            tempkeyvalue = {}
            
            if not force:
                self.listoffile.append(self.file)

            import_statement = self.get_importstatement()
            fldinfo = self.get_indexedLines()
            del_dic= False
            getmethod_param = ''
            type_value = None
            gen_field = False

            for lineno,value in fldinfo:
                lineno = lineno + 1

                line_length = len(str(value).strip())
                if line_length < 1:
                    continue
                
                if self.file[-4:] == '.jsp' and '<%@' in value:
                    continue
                
                if self.file[-4:] == '.jsp' and '<%' in value:
                    gen_field = True
                elif self.file[-4:] == '.jsp' and '%>' in value:
                    gen_field = False
                
                if not gen_field and self.file[-4:] == '.jsp':
                    continue
                
                if self.file[-4:] == '.jsp' and '<%@' in value and '%>' in value:
                    gen_field = False


                if '//' in value:
                    commented_line = str(value).strip().find('//')
                    if commented_line == 0:
                        # line is commented, skip it !
                        continue
                    else:
                        index = value.find('//');
                        value = value[0:index]
                if '/*' in value:
                    block_comment_started = True
                if '*/' in value:
                    block_comment_started = False
                    continue
                    
                if block_comment_started:
                    continue    
                    
                full_line = value;
                if del_dic is True:
                    tempkeyvalue = {}
                    del_dic = False

                field_info_list = value.split('=')
                if len(field_info_list) == 1 :  
                    
                    t = re.search(r"(public|protected|private|static|\s) +[\w\<\>\[\]]+\s+(\w+) *\([^\)]*\) *(\{?|[^;])", value)
                    
                    if t is None:
                        if 'class' in value:
                            clname = value[value.find('class')+5:-1]
                            clname = clname.strip()
                            if '{' in clname:
                                clname = clname[0:clname.find('{')]
                                clname = clname.strip()
                                
                            if ' ' in clname:
                                clname = clname[0:clname.find(' ')]
                                clname = clname.strip()

                            self.actual_class_name = clname
                            classname = clname
                        elif 'namespace' in value:
                            continue
                        else:
                            tempkeyvalue[lineno] = field_info_list[0].strip()
                        continue
                                  
                    if is_methodstarted is True:
                        self.keyvalue = self.keyvalue.copy()
                        tempkeyvalue['fparam'] = getmethod_param
                        z = {method_name[0].strip():tempkeyvalue}
                        self.keyvalue.update(z)
                        del_dic = True



                    is_methodstarted = True
                    getmethod_name = field_info_list[0]
                    getmethod_param = getmethod_name[getmethod_name.rindex('(', 0, -1)+1:-1] 
                    getmethod_name = getmethod_name[0:getmethod_name.rindex('(', 0, -1)+1]
                    method_name = [getmethod_name[getmethod_name.rindex(' ', 0, -1):-1], lineno,line_length,1]
                    
                    index = getmethod_param.rindex(')')
                    getmethod_param = getmethod_param[0:index]

                    continue

                key_item = field_info_list[0].strip().split(' ')
                field_info_list.pop(0)
                field_info_list[0] = field_info_list[0].rstrip().rstrip(';')
                field_info_list.extend((lineno,line_length,1,key_item[0], key_item[-1]))
                
                if is_methodstarted is not True:
                    if len(key_item) > 1 :
                        self.keyvalue[key_item[-1]] = field_info_list
                        self.keyvalue[lineno] = field_info_list
                    else:
                        self.keyvalue[key_item[0]] = field_info_list
                        self.keyvalue[lineno] = field_info_list
                else:
                    if len(key_item) > 1 :
                        tempkeyvalue[key_item[-1]] = field_info_list
                        tempkeyvalue[lineno] = field_info_list
                    else:
                        tempkeyvalue[key_item[0]] = field_info_list
                        tempkeyvalue[lineno] = field_info_list

            if is_methodstarted is True:
                tempkeyvalue['fparam'] = getmethod_param
                self.keyvalue[method_name[0].strip()] = tempkeyvalue 
                self.keyvalue[method_name[1]] = tempkeyvalue 
                         
                
            self.m_dict = {classname:self.keyvalue}
            
            self.import_stat = import_statement

        except:
            pass
        
    def get_keyvalue(self, d, args, default=None):
        try:            
            if not args:
                return d
            
            key, arg   = args[0], args[1:]

            return self.get_keyvalue(d.get(key, default), arg, default=None)
        except KeyError:
            return None
        except AttributeError:
            return None
        except TypeError:
            return None


    def get_global_field_info(self, m_dict, class_name, fld_name):
        t = [class_name, fld_name]
        return self.get_keyvalue(m_dict,t) 
    
    def get_local_methode_info(self, m_dict, class_name, method_name, fld_name):
        t = [class_name,method_name,fld_name]
        fld_value = self.get_keyvalue(m_dict,t)
        return  fld_value 

    def get_fullcls_info(self, m_dict, fld):
        t = [fld]
        return self.get_keyvalue(m_dict,t)
    
    def getKeyValuByValue(self, m_dict,value_to_find):
        kayValue = {key:m_dict[key] for(key,value) in m_dict.items() if str(value).find(value_to_find) != -1}
        if any(kayValue):
            return kayValue
        else:
            return None
