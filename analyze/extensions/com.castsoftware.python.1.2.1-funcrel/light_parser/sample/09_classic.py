'''
Created on 26 nov. 2015

General idea is the following :

- first step of parsing is to match and group {...}, (...), [...] which is almost correct for all languaqes  
- 


@author: MRO
'''
from pygments.lexers.sql import SqlLexer
from light_parser import Parser, Node, BlockStatement, Lookahead, StatementFilter,create_lexer


#
# Basic and common blocks 

class Parenthesis(BlockStatement):
    
    begin ='('
    end   = ')'

class CurlyBracket(BlockStatement):
    
    begin ='{'
    end   = '}'
    

class SquareBracket(BlockStatement):
    
    begin ='['
    end   = ']'


def first_step_parse(lexer):
    
    return Parser(lexer, [Parenthesis, CurlyBracket,SquareBracket])


parser = first_step_parse(SqlLexer)


text = """
{
  a := b ;
  
  if (x)
    pass; 

}

BEGIN
  create TABLE toto () ;
  select * from toto;
END;
"""

# for node in parser.parse(text):
#     node.print_tree()


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
    if isinstance(stream, Node):
        stream = stream.get_inner_body()
    
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
    

text = """(a int,b varchar,c,d)"""

class Element(Node):
    pass

# for node in parser.parse(text):
#     if isinstance(node, Parenthesis): 
#         print('splitting')
#         for element in split(node, ',', Element):
#             element.print_tree()


text = "SELECT k.idkey AS idobj, k.keynam AS objnam, k.objtyp, p.idpro, p.prop AS externobj FROM keys k, objpro p WHERE (((k.idkey = p.idobj) AND (k.objtyp = 274)) AND (((((((((((k.keynam)::text ~~ '%.jsp'::text) OR ((k.keynam)::text ~~ '%.js'::text)) OR ((k.keynam)::text ~~ '%.aspx'::text)) OR ((k.keynam)::text ~~ '%.asmx'::text)) OR ((k.keynam)::text ~~ '%.ascx'::text)) OR ((k.keynam)::text ~~ '%.asax'::text)) OR ((k.keynam)::text ~~ '%.asp'::text)) OR ((k.keynam)::text ~~ '%.htc'::text)) OR ((k.keynam)::text ~~ '%.htm'::text)) OR ((k.keynam)::text ~~ '%.html'::text)));"


class SubStatement(Node):
    pass


def split_sub_statement(stream, node_types):
    """
    take a stream of tokens/nodes and split it according to separators constructing elements
    
    stream = SELECT ... FROM ... WHERE ... 
    
    node_types a list of classes inheriting from SubStatement
    
    typically used after Parenthesis splitting
    
    """
    
    if isinstance(stream, Node):
        stream = stream.get_inner_body()
    
    current_node = None
    
    try:
        while True:
            
            token = next(stream)
            #print('current token ', token)
            
            matched = False
            
            for node_type in node_types:
                match = Node.match_begin(node_type, token, stream)
                if match:
                    
                    matched = True
                    previous_node = current_node
                    
                    # build current node
                    current_node = node_type()
                    current_node.children += match
                    
                    if previous_node:
                        yield previous_node
    
                    # stop looking for a match                
                    break
            
            # non matching token 
            if not matched:
                
                if current_node:
                    current_node.children.append(token)
                else:
                    yield token
    except:
        pass

    if current_node:        
        yield current_node
    

    
class Select(SubStatement):
    begin='SELECT'

class From(SubStatement):
    begin='FROM'

class Where(SubStatement):
    begin='WHERE'


# for element in split_sub_statement(parser.parse(text), [Select, From, Where]):
#     element.print_tree()

    

def parse_select(text):
    """
    parse a select ... eventually complex
    
    Sub select are necessarily inside a parenthesis block
    
    """
    
    lexer = create_lexer(SqlLexer)
    
    class Select(SubStatement):
        begin='SELECT'
    
    class From(SubStatement):
        begin='FROM'
    
    class Where(SubStatement):
        begin='WHERE'

    def split_select(stream):
        
        return (element for element in split_sub_statement(stream, [Select, From, Where]))
    
    
    class Parenthesis(BlockStatement):
        begin ='('
        end   = ')'
        
        def on_end(self):
            
            # recurse
            self.children = list(split_select(Lookahead(self.children)))
    
    
    parenthesis = StatementFilter([Parenthesis, CurlyBracket,SquareBracket])
    
    stream = Lookahead(lexer.get_tokens(text))
    
    # first apply ()
    stream = Lookahead(parenthesis.process(stream))
    
    # then split in select from where for first one
    stream = split_select(stream)
    
    return stream
    
text = """

SELECT (SELECT a FROM T1) as X FROM (SELECT * FROM T2) WHERE c1 in (SELECT c FROM T3)

"""

        
for element in parse_select(text):
    element.print_tree()
