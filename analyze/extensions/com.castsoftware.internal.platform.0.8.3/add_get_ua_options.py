
import collections

Option = collections.namedtuple('Option', ['extensions'])


def parse_log(path):
    """
    Parse a castlog file and return a map of UA technology found with their extensions
    """
    result = {}
    
    with open(path, 'r') as f:
        
        current_extensions_list = None
        current_name = None
        is_universal = False
        first_universal = True
        for line in f:
            
            # activated UAs are listed that way :
            # Universal language
            # ...
            # Sources
            if first_universal and 'Universal language' in line:
                is_universal = True
                first_universal = False
            elif is_universal and 'Extensions used in jobSettings :' in line:
                current_extensions_list = line[line.find('*'):].strip().split('\x07')[0]
                current_extensions_list = current_extensions_list.split(';')
                current_extensions_list = [ext[1:] for ext in current_extensions_list]
                
            elif is_universal and 'Name :' in line:
                
                content = line[line.find('Name :'):]
                content = content[content.find(':')+2:].split('\x07')[0]
                current_name = content.strip()
                result[current_name] = Option(current_extensions_list)
            
            elif 'Sources' in line:
                is_universal = False
    
    return result


def get_log_path(params):
    
    for param in params:
        if param.startswith('-LOG('):
            result = param[6:param.rfind(',')-1]
            return result

import cast.analysers #@UnusedImport
import sys
import platform

if platform.architecture()[0] == '32bit':
    import psutil32 as psutil #@UnresolvedImport #@UnusedImport
else:
    import psutil64 as psutil #@UnresolvedImport @ImportRedefinition

import os

def get_ua_options():

    
    pid = os.getpid()
    p = psutil.Process(pid)
    params = p.cmdline()
    path = get_log_path(params)
    
    if path:
        return parse_log(path)
    else:
        
        if 'analyzer.exe' in params[0]:

            for param in params:
                if param.startswith('--language='):
                    result = {param[11:]:Option('')}
                    return result
        
        
    

cast_module = sys.modules["cast.analysers"]
if not hasattr(cast_module, 'get_ua_options'):
    setattr(cast_module, 'get_ua_options', get_ua_options)

