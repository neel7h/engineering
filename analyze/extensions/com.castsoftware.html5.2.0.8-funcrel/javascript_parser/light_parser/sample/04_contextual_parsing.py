'''
Demonstrate the contextual parsing of statements.

A BlockStatement can contain other Statement or BlockStatement declaration. 
They will be matched uniquely when inside the block.
 
'''
from pygments.lexers.sql import SqlLexer
from javascript_parser.light_parser import Parser, BlockStatement, Statement


class Block(BlockStatement):
  
    begin = 'BEGIN'
    end   = 'END'

    class Create(Statement):
        
        begin = 'CREATE'
        end   = ';'

parser = Parser(SqlLexer, [Block])

# as we can see : the create outside the begin/end are not matched 
nodes = parser.parse("""
create table foo;
begin
  create table foo;
  select * from toto;
end;
create table foo;
""")

for node in nodes:
    node.print_tree()
