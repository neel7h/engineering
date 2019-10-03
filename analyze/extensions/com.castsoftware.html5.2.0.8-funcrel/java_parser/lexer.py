'''
Created on 14 oct. 2016

@author: MRO
'''
from .light_parser.splitter import Splitter # @UnresolvedImport
from .light_parser import Token # @UnresolvedImport
from pygments.token import Generic, Comment, String, Keyword, Name

CommentEndOfLine = Comment.EndOfLine # @UndefinedVariable


class JavaLexer:
    """
    A very basic lexer 
    """
    
    def __init__(self, stripnl=False):
        pass
    
    def add_filter(self, _):
        pass
        
    def get_tokens(self, text, unfiltered=False):
        """
        To keep compliant with pygment 
        
        But still returns positionned tokens
        """
        
        # text can be a file...
        if isinstance(text, str):
            text = text.splitlines()
        
        # see : https://docs.oracle.com/javase/specs/jls/se8/html/jls-3.html#jls-3.11
        # but we do not take all 
        # for example we skip '@', '.', 
        s = Splitter(['(', ')', '{', '}', '[', ']', 
                      ';', ',', '...',
                      
                      '=', '<', '>',  '!', '~', '?',  ':', '->', 
                      '==',  '<=', '>=', '!=', '||', '&&', '++', '--',
                      '+', '-', '*', '/', '&', '|', '^', '%', '<<',
                      '+=', '-=', '*=', '/=', '&=', '|=', '^=', '%=', '<<=', '>>=', '>>>=',
                      '/*', '*/', '//',  
                      '"', '\\', "'"])
        split = s.split
        
        # state 
        mono_line_comment = False
        multi_line_comment = False
        current_comment = None 
        multi_line_comment_begin_line = None
        multi_line_comment_begin_column = None
        
        is_string = False
        current_string = None
        current_separator = None
        previous_is_backslash = False
        
        current_line_number = 0
        
        for line in text:
            
            current_line_number += 1
            
            begin_column = 0
            end_column = 0
            
            # true when we have seen something non blank and non comment on the line
            seen_something = False
            
            for token in split(line):
                
                begin_column = end_column + 1
                end_column = begin_column + len(token) - 1
                
                mono_line_comment_begin_column = None
                string_begin_column = None
                
                if mono_line_comment:
                    current_comment += token
                elif multi_line_comment:
                    current_comment += token
                    if token == '*/':
                        result = Token(current_comment, Comment)
                        result.begin_line = multi_line_comment_begin_line
                        result.end_line = current_line_number
                        result.begin_column = multi_line_comment_begin_column
                        result.end_column = end_column
                        
                        yield result
                        multi_line_comment = False
                elif is_string:
                    current_string += token
                    if token == current_separator and not previous_is_backslash:
                        result = Token(current_string, String)
                        result.begin_line = current_line_number
                        result.end_line = current_line_number
                        result.begin_column = string_begin_column
                        result.end_column = end_column
                        
                        yield result
                        
                        is_string = False
                    
                    
                elif token == '//':
                    mono_line_comment = True
                    mono_line_comment_begin_column = begin_column
                    current_comment = '//'
                elif token == '/*':
                    multi_line_comment = True
                    multi_line_comment_begin_line = current_line_number
                    multi_line_comment_begin_column = begin_column
                    current_comment = '/*'
                elif token == '"' or token == "'":
                    is_string = True
                    current_string = token
                    current_separator = token
                    seen_something = True
                else:
                    """
                    Warning : here we have a tight coupling with parser rules
                    Some Java keywords are not listed here as purpose
                    For example : do not list 'enum' as keyword due to the 1.5 breaking
                    """
                    _type = Generic
                    if token in  ['assert', 'break', 'case', 'catch',  
                                  'continue', 'default', 'do', 'else', 'extends', 'finally',
                                  'for', 'if', 'implements', 'instanceof',  
                                  'new', 'null', 'return', 'super', 
                                  'switch', 'this', 'throw', 'throws','try', 'while' ]:
                        _type = Keyword
                    
                    if token and token[0] == '$':
                        _type = Name.Variable
                    
                    if not seen_something:
                        seen_something = not token.isspace()
                    
                    result = Token(token, _type)
                    result.begin_line = current_line_number
                    result.end_line = current_line_number
                    result.begin_column = begin_column
                    result.end_column = end_column
                    yield result
                
                current_is_backslash = token == '\\'
                
                if previous_is_backslash and current_is_backslash:
                    # for \\ case (escaping of escape)
                    previous_is_backslash = False
                else:
                    previous_is_backslash = current_is_backslash
                
                
            if mono_line_comment:
                result = Token(current_comment, Comment if not seen_something else CommentEndOfLine)
                result.begin_line = current_line_number
                result.end_line = current_line_number
                result.begin_column = mono_line_comment_begin_column
                result.end_column = end_column
                yield result
                mono_line_comment = False
            if multi_line_comment:
                current_comment += '\n'
                
