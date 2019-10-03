'''
Created on 19 avr. 2016

A Term is a node with an exact match

@author: MRO
'''
from pygments.lexers.agile import PythonLexer
from pygments.token import Name

from light_parser import Parser, Term, BlockStatement, Seq, Optional, IncreaseIndent, DecreaseIndent



class Parenthesis(BlockStatement):
    begin = IncreaseIndent
    end = DecreaseIndent

parser = Parser(PythonLexer, [Parenthesis])
parser.use_indentation()

text = """
class Toto:

    def __init__(self):
        pass
"""

for n in parser.parse(text):
    n.print_tree()

