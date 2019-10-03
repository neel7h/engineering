import re

def normalize_path(operationPath):

    service_names = operationPath.split('/')
    service_name = None
    if service_names:
        service_name = ''
        for part in service_names:
            if part: 
                if part.startswith('{'):
                    service_name += '{}/'

                # !!! experimental
                elif part.startswith('*'):
                    if not service_name:
                        # /*/path1 --> path1/
                        continue
                    if part.startswith('*?'):
                        # path1/*?method=delete --> path1/{}?method=delete
                        tmp = re.sub('\*', '{}', part)
                        service_name += tmp + '/'
                    else:
                        service_name += '{}/'

                else:
                    service_name += ( part + '/' )
    return service_name
