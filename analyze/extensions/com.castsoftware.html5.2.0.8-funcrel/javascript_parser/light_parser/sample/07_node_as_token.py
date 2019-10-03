'''
replacement for on end mecanism
'''
from pygments.lexers.sql import SqlLexer
from javascript_parser.light_parser import Parser, BlockStatement, Not, Statement



class Parenthesis(BlockStatement):
    
    begin = '('
    end   = ')'

    class Element(Statement):
        
        begin = Not('(')
        end   = ','


text = """
a ( b (1), c, d(a, z))
"""


parser = Parser(SqlLexer, [Parenthesis])
 
for node in parser.parse(text):
    node.print_tree()

