"""
This code patches some cast.analysers.jee.Extension bugs and limitations.

Usage:

in your cast.analysers.jee.Extension

class JEE(cast.analysers.jee.Extension):
    
    def __init__(self):
        self.java_parser = None
    
    @cast.Event('com.castsoftware.internal.platform', 'jee.java_parser')
    def get_java_parser(self, java_parser):
        self.java_parser = java_parser
        
        
    # ... use 
    def start_type(self, _type):
        annotations = self.java_parser.get_annotations(_type)


java parser has the following api :

class JavaParser:
    
    def get_annotations(self, o):
        '''
        Scan object for annotations
        
        :param o: the cast.analyzer.Object to scan for annotations
        :rtype: list of tuple (fullname, named_parameters, positional_parameters) 
        
        '''


"""
from functools import lru_cache
import cast.analysers.jee
import cast_upgrade_1_5_18 # @UnusedImport
from cast.application import open_source_file # @UnresolvedImport
from java_parser.parser import parse as parse_java
from cast.analysers import log
from java_parser.discoverer import Discoverer
import traceback


class JavaParser:
    """
    A python Java parser.
    """
    
    def __init__(self, file_pathes):
        
        self.discoverer = Discoverer()
        for path in file_pathes:
            self.discoverer.register_file(path)
        
    @lru_cache()
    def parse(self, path):
        """
        Parse a java code and return an ast.
        
        :param path: str
        :rtype : java_parser.parser.CompilationUnit
        """
        try:
            with open_source_file(path) as f:
                return parse_java(f, self.discoverer)
        except:
            return None
        
    def get_object_ast(self, o):
        """
        Get the AST node of an object
        
        :param o: cast.analayzers.Object
        """
        
        def search(node, line):
            
            if node.get_begin_line() == line:
                return node
            
            for sub_node in node.get_sub_nodes():
                
                temp = search(sub_node, line)
                if temp:
                    return temp
        
        compilation_unit = self.parse(o.get_position().get_file().get_path())
        
        begin = o.get_position().get_begin_line()
        
        try:
            for ast in compilation_unit.get_type_declarations():
                temp = search(ast, begin)
                if temp:
                    return temp
        except:
#             log.debug('for object' + str(o) + '  ' + traceback.format_exc())
            return None


class JEE(cast.analysers.jee.Extension):
    """
    Corrects some issues from cast.analysers.jee.Extension
    """
    
    def start_analysis(self, options):
        
        self.broadcast('jee.java_parser', JavaParser(options.get_source_files()))
