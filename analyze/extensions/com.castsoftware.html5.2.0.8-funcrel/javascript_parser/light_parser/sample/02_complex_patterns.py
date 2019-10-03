'''
Demonstrate complex begin/end AST patterns.

Seq matches a sequence of tokens or other matches
Or matches something or something 
'''
from pygments.lexers.sql import SqlLexer
from javascript_parser.light_parser import Parser, BlockStatement, Statement, Seq, Optional, Or

def parse(text):
    """
    Parse the text and return high level AST nodes  
    """
    parser = Parser(SqlLexer, [CreateStatement, Block])
    return parser.parse(text)    
    

class Block(BlockStatement):
    """
    BEGIN ... END
    """
    begin = 'BEGIN'
    end   = 'END'


class CreateStatement(Statement):
    """
    CREATE { TABLE          } ... ;
           { [UNIQUE] INDEX }
           
    will recognise : 
    - CREATE TABLE ... ;
    - CREATE INDEX ... ;
    - CREATE UNIQUE INDEX ... ;
    """
    begin = Seq('CREATE', Or('TABLE', 
                             Seq(Optional('UNIQUE'), 'INDEX')))
    end = ';'


text = """
BEGIN
  create TABLE toto () ;
  select * from toto;
END;
"""

for node in parse(text):
    node.print_tree()
