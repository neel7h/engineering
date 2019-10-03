'''
Created on 26 nov. 2015

General idea is the following :


- first step is to group (...)  so that we have 
SELECT ... FROM ... WHERE 
and the sub select (and sub where)  are inside Parenthesis 

- then we split again SELECT and FROM with ','
- we re apply every thin inside Parenthesis (for recursion)  

Needs :

- links to tables in the from 
- links to functions in the where
- column list in the select


@author: MRO
'''
from pygments.lexers.sql import SqlLexer
from light_parser import Node, Statement, BlockStatement, Lookahead, StatementFilter, create_lexer



def parse_select(stream):
    """
    parse a select ... eventually complex
    
    Sub select are necessarily inside a parenthesis block
    
    """
    # first apply ()
    stream = group(stream, [Parenthesis])
    
    # then split in select from where for first one
    stream = group_select(stream)
    
    return stream


def analyse(stream):

    for element in stream:
        
        element.print_tree()
        
        if isinstance(element, TableReference):
            analyse_table_reference(element)
            

def analyse_table_reference(reference):
    
    pass
        
        
        

def split(stream, separator, element):
    """
    take a stream of tokens/nodes and split it according to tokens
    
    stream = a , c , e , f 
    separator = ','
    element = class E(Node): ...
    
    will return a stream 

    E 
      a 
    E 
      c
    E
      e
    E
      f
    
    typically used in conjunction with Parenthesis
    
    """
    
    current = None
    try:
        
        while True:
            if not current:
                current = element()
            
            token = stream.__next__()
#             print('scanning ', token)
            if token.text == separator:
                # finished element 
                temp = current
                # reset current for next one
                current = None
#                 print('returning ', temp)
                yield temp
            else:
                # part of current element
                current.children.append(token)

    except:
        yield current


def group(stream, statements):
    """
    Apply statements grouping on a stream
    """
    f = StatementFilter(statements)
    return Lookahead(f.process(stream))


class Column(Node):
    pass
    

class Select(Statement):
    stopped_by_other_statement = True
    begin='SELECT'
    end = None
    
    def on_end(self):
        
        self.children = split(Lookahead(self.children), ',',  Column)
        

class TableReference(Node):
    pass

class From(Statement):
    stopped_by_other_statement = True
    begin='FROM'
    end = None

    def on_end(self):
        
        self.children = split(Lookahead(self.children), ',',  TableReference)

class Where(Statement):
    stopped_by_other_statement = True
    begin='WHERE'
    end = None

def group_select(stream):
    """
    Take a stream SELECT ... FROM ... WHERE and group it against those 3 sub groups
    """
    return group(stream, [Select, From, Where])

class Parenthesis(BlockStatement):
    begin ='('
    end   = ')'
    
    def on_end(self):
        
        # recurse 
        self.children = list(group_select(Lookahead(self.children)))



if __name__ == "__main__":
        
    text = """
    
    SELECT (SELECT a FROM T1) as X FROM (SELECT * FROM T2, T3) WHERE c1 in (SELECT c FROM T3) Union SELECT a FROM T1
    
    """
    
    lexer = create_lexer(SqlLexer)
    stream = Lookahead(lexer.get_tokens(text))
    
    analyse(parse_select(stream))

    

    
        
    
    