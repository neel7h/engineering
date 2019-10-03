'''
Demonstrate the 'begin is end'.

Often, a language has weak statement ending. In that case, the beginning of a statement 
is the end of the previous.

Here a statement class can use : 

    stopped_by_other_statement = True

Matching the beginning of another statement will also acts as a ending for statement.
'''
from pygments.lexers.sql import SqlLexer
from light_parser import Parser, Statement


class Insert(Statement):
    stopped_by_other_statement = True
    begin = 'INSERT'
    end   = ';'
    

class Update(Statement):
    stopped_by_other_statement = True
    begin = 'UPDATE'
    end   = ';'

    
class Delete(Statement):
    stopped_by_other_statement = True
    begin = 'DELETE'
    end   = ';'


    
parser = Parser(SqlLexer, [Insert, Update, Delete])

# as we can see : end are not matched but matching the begin of an other statement stops the current statement  
nodes = parser.parse("""
insert into A
insert into B
delete from A
""")

for node in nodes:
    node.print_tree()
