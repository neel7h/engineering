def parse_log(path):
    """
    Parse a castlog file and return a the list of activated extensions
    """
    result = []
    
    with open(path, 'r') as f:
        
        for line in f:
            
            if 'Registering extension ' in line:
                splitted_line = line[line.find('Registering extension '):].strip().split('\x07')[0].split()
                result.append((splitted_line[2], splitted_line[3][:-1]))
            if 'About to run' in line:
                break # no need to continue
    
    return result


def get_log_path(params):
    
    
    for param in params:
        if param.startswith('-LOG('):
            result = param[6:param.rfind(',')-1]
            return result
    
    # probably a componentised analyser
    for param in params:
        
        if '.xml' in param:
            
            import xml.etree.ElementTree as ET
            
            tree = ET.parse(param)
            root = tree.getroot()
            
            for node in root.findall(".//logFile"):
                
                return node.text

    
import cast.analysers #@UnusedImport
import sys
import platform

if platform.architecture()[0] == '32bit':
    import psutil32 as psutil #@UnresolvedImport #@UnusedImport
else:
    import psutil64 as psutil #@UnresolvedImport @ImportRedefinition

import os

def get_extensions():

    
    pid = os.getpid()
    p = psutil.Process(pid)
    params = p.cmdline()
    path = get_log_path(params)
    
    if path:
        return parse_log(path)
    else:
        result = []
        if 'analyzer.exe' in params[0]:
            for param in params:
                if param.startswith('--plugin-path='):
                    result.append((os.path.basename(param[14:]),''))
        
        return result
    

cast_module = sys.modules["cast.analysers"]
if not hasattr(cast_module, 'get_extensions'):
    setattr(cast_module, 'get_extensions', get_extensions)


def get_log_folder():
    
    pid = os.getpid()
    p = psutil.Process(pid)
    params = p.cmdline()
    path = get_log_path(params)
    
    if path:
        return os.path.dirname(path)
    

if not hasattr(cast_module, 'get_log_folder'):
    setattr(cast_module, 'get_log_folder', get_log_folder)

