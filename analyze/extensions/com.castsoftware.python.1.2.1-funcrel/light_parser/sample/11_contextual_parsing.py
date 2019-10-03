'''
Demonstrate the contextual parsing of statements this type with sub parsers.





@author: MRO
'''
from pygments.lexers.compiled import ObjectiveCLexer
from pygments.token import Keyword, Name
from light_parser import Token, Or, Parser, Any, Statement, BlockStatement, Node, Seq, Optional


def any_but_whitespace(token):
    """
    Generic token matcher
    """
    return not token.is_whitespace() and not isinstance(token, Node)

class GenericStatement(Statement):
    
    begin = any_but_whitespace # usage of generic token matcher
    end   = ';'

class VariableDeclaration(Statement):
    
    begin = Seq(Optional('const'), Or(Name, Keyword.Type), Optional('*'), Name) 
    end = ';'


class Block(BlockStatement):
  
    begin = '{'
    end   = '}'

class InstanceMethod(Statement):
    
    begin = Token('-', Keyword)
    end   = Or(Block, ';')



parser = Parser(ObjectiveCLexer, [Block], # first pass group blocks
                                 [InstanceMethod], # second pass recognize methods 
                                 {Block:[VariableDeclaration]}) # third pass : inside blocks recognize variable delcarations

nodes = parser.parse("""

- (void)f:
{
  {
    int a = b;
  
  }
  c = d;
}

""")

for node in nodes:
    node.print_tree()
