"""
A java file discoverer.

"""
import os
from collections import defaultdict
from pathlib import PureWindowsPath


class Discoverer:
    """
    Discoverer for java file pathes.
    """
    def __init__(self):
        
        self.files = defaultdict(set)

    def register_file(self, path):
        """
        Register a java file path.
        """
        _, _file = os.path.split(path)
        name, ext = os.path.splitext(_file)
        
        if ext != '.java':
            # not interested
            return
        
        self.files[name].add(path)
        
    def get_pathes(self, class_fullname):
        """
        Find the file given the class fullname.
        There may exist several solutions.
        
        :param class_fullname: str, for example 'com.p1.Class'
        :rtype: list of str
        """
        if not class_fullname:
            return []
        
        elements = class_fullname.split('.')
        
        class_name = elements[-1]
        
        result = []
        
        package_parts = elements[:-1]
        lenght_package = len(package_parts)
        
        # check all path having the correct class name
        for candidate in self.files[class_name]:
            
            candidate_parts = list(PureWindowsPath(candidate).parts[:-1])
            length_candidate = len(candidate_parts)
            
            # compare length of packages
            if lenght_package > length_candidate:
                continue
            
            candidate_parts = candidate_parts[length_candidate-lenght_package:]
            
            if package_parts == candidate_parts:
                result.append(candidate)
            
        return result
