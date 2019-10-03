'''
Demonstrate simple AST patterns.

'''
from pygments.lexers.sql import SqlLexer
from javascript_parser.light_parser import Parser, BlockStatement, Statement

class Create(Statement):
    
    begin = 'CREATE'
    end   = ';'

class Block(BlockStatement):
  
    begin = 'BEGIN'
    end   = 'END'

parser = Parser(SqlLexer, [Create, Block])

nodes = parser.parse("""
begin
  create table foo;
  select * from toto;
end;
select * from titi;
""")

for node in nodes:
    node.print_tree()
