'''
Split a text into Parenthesis then split element inside parenthesis through ','

The splitting can be applied on already split streams, i.e., a stream of Token and Node.

'''
from pygments.lexers.sql import SqlLexer
from light_parser import Statement, BlockStatement, Lookahead, Not, Or, StatementFilter, create_lexer


class Element(Statement):
    
    begin = Not('(')
    end   = Or(',', ')')

    def on_end(self):
        """Called after end parsing"""
        # the last child which is ',' or ')'
        self.children.pop()

            
class Parenthesis(BlockStatement):
    
    begin ='('
    end   = ')'
    
    def on_end(self):
        """
        Called after end of matching a parenthesis pair.
        
        We directly apply the split through ',' and replace the children
        """
        element_splitter = StatementFilter([Element])
        
        # also remove the first child which is '('  
        self.children = list(element_splitter.process(self.get_children()))[1:]
    


text = """
a ( b (1), c, d(a, z))
"""

text = """
( b  x, c x, d x)
"""


# get the token stream
stream = Lookahead(create_lexer(SqlLexer).get_tokens(text))

# group this stream by parenthesis
parenthesis_splitter = StatementFilter([Parenthesis])
stream = parenthesis_splitter.process(stream)

for x in stream:
    x.print_tree()
