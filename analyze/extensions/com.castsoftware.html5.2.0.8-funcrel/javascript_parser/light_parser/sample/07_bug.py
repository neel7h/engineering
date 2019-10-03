'''
Created on 5 mars 2015

@author: MRO
'''
from pygments.lexers.sql import SqlLexer
from javascript_parser.light_parser import Parser, BlockStatement, Statement, Seq, Optional, Or


def parse(text):
    """
    Parse the text and return high level AST nodes  
    """
    parser = Parser(SqlLexer, [FunctionBlock])
    return parser.parse(text)    

class FunctionBlock(BlockStatement):
    
    header = 'function'
    begin = '{'
    end   = '}'


text = """
function TodoCtrl($scope, $routeParams, $filter, store) {  }
"""

for node in parse(text):
    node.print_tree()
