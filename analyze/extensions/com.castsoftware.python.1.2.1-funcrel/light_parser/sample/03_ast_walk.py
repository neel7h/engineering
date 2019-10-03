'''
Demonstrate a simple AST walk

'''
from pygments.lexers.sql import SqlLexer
from light_parser import Parser, BlockStatement, Statement

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
""")

def walk(node):
    print(node)
    for sub_node in node.get_sub_nodes():
        walk(sub_node)

for node in nodes:
    walk(node)