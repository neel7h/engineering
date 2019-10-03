
def normalize_path(operationPath):

    service_names = operationPath.split('/')
    service_name = None
    if service_names:
        service_name = ''
        for part in service_names:
            if part: 
                if part.startswith('{'):
                    service_name += '{}/'
                else:
                    service_name += ( part + '/' )
    return service_name
