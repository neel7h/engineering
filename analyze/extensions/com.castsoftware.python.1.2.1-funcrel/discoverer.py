import os
from collections import defaultdict


class Discoverer:
    """
    Discover the structure of a python source folder

    Take the list of all python path
    
    Then, it is able to discover include pathes and the import name for each file
    """
    def __init__(self):
        
        self.pathes = []
        self.normalised_pathes = []
        self.imports = defaultdict(list)
        self.calculated = False 
        
    def add_path(self, path):
        
        self.normalised_pathes.append(os.path.abspath(path))
        self.pathes.append(path)

    def calculate(self):
        """
        Calculate every thing
        """
        if self.calculated:
            return
        
        for path in self.pathes:
            
            _import = self.get_import_name(path)
            self.imports[_import].append(path)
        
        self.calculated = True
    
    def get_paths_from_import(self, import_name):
        """
        from an import, returns the possible files 
        """
        self.calculate()
        return self.imports[import_name]
        
    def get_import_name(self, path):
        """
        Returns the import associated with the file path.
        """
        path = os.path.abspath(path)
        
        folder_path, filename = os.path.split(path)
        
        base_name = ''
        
        while self.is_package(folder_path):
            
            folder_path, dirname = os.path.split(folder_path)
            
            if base_name:
                base_name = dirname + '.' + base_name
            else:
                base_name = dirname
        
        if filename == '__init__.py':
            return base_name
        else:
            filename, _ = os.path.splitext(filename)
            if base_name:
                return base_name + '.' + filename
            else:
                return filename
            
        
    def is_package(self, folder_path):
        """
        True when folder_path is a package
        """
        init = os.path.join(folder_path, '__init__.py')
        return init in self.normalised_pathes