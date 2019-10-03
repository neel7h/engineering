'''
Block can have header, we try to match :  

header 
... 
begin 
... 
end

It is handy for classical function/classes declarations

'''
from pygments.lexers.sql import SqlLexer
from javascript_parser.light_parser import Parser, BlockStatement, Statement, Seq, Optional, Or


def parse(text):
    """
    Parse the text and return high level AST nodes  
    """
    parser = Parser(SqlLexer, [Procedure])
    return parser.parse(text)    


class Procedure(BlockStatement):
    header = Seq('CREATE', Optional(Seq('OR', 'REPLACE')), Or('FUNCTION', 'PROCEDURE'))
    begin  = 'BEGIN'
    end    = 'END'

    class Create(Statement):
        
        begin = 'CREATE'
        end   = ';'
    
    class Select(Statement):
        
        begin = 'SELECT'
        end   = ';'

text = """

CREATE FUNCTION foo(param1 integer) RETURNS integer
AS
BEGIN
  create TABLE toto () ;
  select * from toto;
END;
"""

for node in parse(text):
    node.print_tree()
