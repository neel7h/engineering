.. light_parser documentation master file, created by
   sphinx-quickstart on Wed Nov 12 23:55:17 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. toctree::
   :maxdepth: 2


Introduction
============

Getting Started
---------------

The :mod:`light_parser` module provides simple functions to build a language parser.
This section shows some simple usage examples of these functions.

Let's get started with splitting a string containing one or more SQL
statements into a basic AST containing create statements and begin...end blocks:

.. code-block:: python

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
  end;
  """)
  
  for node in nodes:
      node.print_tree()


This prints :

.. code-block:: python

  Block
    Token(Token.Keyword,'begin',1,1,1,5)
    Token(Token.Text,'\n  ',1,6,2,2)
    Create
      Token(Token.Keyword,'create',2,3,2,8)
      Token(Token.Text,' ',2,9,2,9)
      Token(Token.Keyword,'table',2,10,2,14)
      Token(Token.Text,' ',2,15,2,15)
      Token(Token.Name,'foo',2,16,2,18)
      Token(Token.Punctuation,';',2,19,2,19)
    Token(Token.Punctuation,';',2,19,2,19)
    Token(Token.Text,'\n  ',2,20,3,2)
    Token(Token.Keyword,'select',3,3,3,8)
    Token(Token.Text,' ',3,9,3,9)
    Token(Token.Operator,'*',3,10,3,10)
    Token(Token.Text,' ',3,11,3,11)
    Token(Token.Keyword,'from',3,12,3,15)
    Token(Token.Text,' ',3,16,3,16)
    Token(Token.Name,'toto',3,17,3,20)
    Token(Token.Punctuation,';',3,21,3,21)
    Token(Token.Text,'\n',3,22,4,0)
    Token(Token.Keyword,'end',4,1,4,3)
  

:class:`light_parser.BlockStatement` represent block statement found in programming languages. 
They have a recursive structure. The beginning and end of a block are is given by a pattern.
:class:`light_parser.Statement` represent basic non recursive statements.

:class:`light_parser.Parser` will parse the text and try to recognize any statement present using the 'begin' and 'end'. 
It will then : 
* create an object of this statement class
* 'move' the recognized tokens as children as children of this statement
* and continue recursively
Unrecognized tokens are left as is in the token stream. In the example above, we were not interested into SELECT statement, so it is left as raw tokens.  

Each created node will have the recognized tokens as children. Blocks will also have blocks and statements as child.

One step further
----------------

Now we have a basic 'hight level' AST structure. 

The key idea is to progressively transform a stream of tokens into an AST. 




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

