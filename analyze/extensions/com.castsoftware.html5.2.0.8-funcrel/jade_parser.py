import re

from pygments.lexers.web import ExtendedRegexLexer, _indentation, bygroups, using, ScalaLexer, include, _starts_block
# from pygments.token import Text, Comment, String, Error, is_token_subtype, Punctuation, Keyword, Name
from pygments.token import *
from cast.analysers import Bookmark
from html_interpreter import HtmlInterpreter
from javascript_parser.symbols import ObjectDatabaseProperties
from javascript_parser.light_parser import Filter, Parser, BlockStatement, IncreaseIndent, DecreaseIndent, Token, Term, Optional, Seq, Or
import cast.analysers.ua
import traceback
import math

# Used to preprocess script sections where script code must be preceded with | character:
# script
#    | line1
#    | line2
def preprocess_text(text):

    if not 'script' in text:
        return text
    
    scriptStarted = False
    _indent = 0
    newText = ''
    firstIndentInScript = -1
    for line in text.splitlines():
        
        if scriptStarted:
            trimedLine = line.strip()
            index = line.find(trimedLine)
            if firstIndentInScript == -1:
                firstIndentInScript = index
            if index <= _indent:
                scriptStarted = False
                firstIndentInScript = -1
                if not trimedLine.startswith('script'):
                    newText += (line + '\n')
                    continue
            else:
                if not trimedLine.startswith('|'):
                    newLine = ' '*firstIndentInScript + '|' + ' '*(index - firstIndentInScript) + trimedLine
                    newText += (newLine + '\n')
                    continue
        
        trimedLine = line.strip()
        if trimedLine.startswith(('script.', 'script(')):
            _indent = line.find(trimedLine)
            scriptStarted = True
        
        newText += (line + '\n')
        
    return newText[:-1]

class JadeLexer(ExtendedRegexLexer):
    """
    For Jade markup.
    Jade is a variant of Scaml, see:
    http://scalate.fusesource.org/documentation/scaml-reference.html
 
    *New in Pygments 1.4.*
    """
 
    name = 'Jade'
    aliases = ['jade', 'JADE']
    filenames = ['*.jade']
    mimetypes = ['text/x-jade']
 
    flags = re.IGNORECASE
    _dot = r'.'
 
    tokens = {
        'root': [
            (r'[ \t]*\n', Text),
            (r'[ \t]*', _indentation),
        ],
 
        'css': [
            (r'\.[a-z0-9_:-]+', Name.Class, 'tag'),
            (r'\#[a-z0-9_:-]+', Name.Function, 'tag'),
        ],
 
        'eval-or-plain': [
            (r'[&!]?==', Punctuation, 'plain'),
            (r'([&!]?[=~])(' + _dot + r'*\n)',
             bygroups(Punctuation, using(ScalaLexer)),  'root'),
            (r'', Text, 'plain'),
        ],
 
        'content': [
            include('css'),
            (r'!!!' + _dot + r'*\n', Name.Namespace, '#pop'),
            (r'(/)(\[' + _dot + '*?\])(' + _dot + r'*\n)',
             bygroups(Comment, Comment.Special, Comment),
             '#pop'),
            (r'/' + _dot + r'*\n', _starts_block(Comment, 'html-comment-block'),
             '#pop'),
            (r'-#' + _dot + r'*\n', _starts_block(Comment.Preproc,
                                                 'scaml-comment-block'), '#pop'),
            (r'(-@\s*)(import)?(' + _dot + r'*\n)',
             bygroups(Punctuation, Keyword, using(ScalaLexer)),
             '#pop'),
            (r'(-)(' + _dot + r'*\n)',
             bygroups(Punctuation, using(ScalaLexer)),
             '#pop'),
#             (r':' + _dot + r'*\n', _starts_block(Name.Decorator, 'filter-block'),
            (r':' + _dot + r'[^\n]*', _starts_block(Name.Decorator, 'filter-block'),
             '#pop'),
            (r'[a-z0-9_:-]+', Name.Tag, 'tag'),
            (r'\|', Text, 'eval-or-plain'),
            ('<!--', Comment, 'comment1'),
        ],
        'comment1': [
            ('[^-]+', Comment),
            ('-->', Comment, '#pop'),
            ('-', Comment),
        ],
 
        'tag': [
            include('css'),
            (r'\{(,\n|' + _dot + ')*?\}', using(ScalaLexer)),
            (r'\[' + _dot + '*?\]', using(ScalaLexer)),
            (r'\(', Text, 'html-attributes'),
            (r'/[ \t]*\n', Punctuation, '#pop:2'),
            (r'[<>]{1,2}(?=[ \t=])', Punctuation),
            include('eval-or-plain'),
        ],
 
        'plain': [
            (r'([^#\n]|#[^{\n]|(\\\\)*\\#\{)+', Text),
            (r'(#\{)(' + _dot + '*?)(\})',
             bygroups(String.Interpol, using(ScalaLexer), String.Interpol)),
            (r'\n', Text, 'root'),
        ],
 
        'html-attributes': [
            (r'\s+', Text),
            (r'[a-z0-9_:-]+[ \t]*=', Name.Attribute, 'html-attribute-value'),
            (r'[a-z0-9_:-]+', Name.Attribute),
            (r'\)', Text, '#pop'),
        ],
 
        'html-attribute-value': [
            (r'[ \t]+', Text),
            (r'[a-z0-9_]+', Name.Variable, '#pop'),
            (r'@[a-z0-9_]+', Name.Variable.Instance, '#pop'),
            (r'\$[a-z0-9_]+', Name.Variable.Global, '#pop'),
            (r"'(\\\\|\\'|[^'\n])*'", String, '#pop'),
            (r'"(\\\\|\\"|[^"\n])*"', String, '#pop'),
        ],
 
        'html-comment-block': [
            (_dot + '+', Comment),
            (r'\n', Text, 'root'),
        ],
 
        'scaml-comment-block': [
            (_dot + '+', Comment.Preproc),
            (r'\n', Text, 'root'),
        ],
 
        'filter-block': [
            (r'([^#\n]|#[^{\n]|(\\\\)*\\#\{)+', Name.Decorator),
            (r'(#\{)(' + _dot + '*?)(\})',
             bygroups(String.Interpol, using(ScalaLexer), String.Interpol)),
            (r'\n', Text, 'root'),
        ],
    }

class IndentJadeFilter(Filter):
    """
    Filter that add indentation tokens in the stream.
    
    This filter will insert in the stream special tokens IncreaseIndent, DecreaseIndent 
    """
    def __init__(self):
        
        # current column line
        self.current_column = 1
        self.new_line = False
        # we can deduce the indentation used
        self.deduced_indentation = 0

    def filter(self, lexer, stream):
    
        for token in stream:

            if token.is_whitespace():
                
                if '\n' in token.text:
                    # we have changed line
                    self.new_line = True
            
            else:
                
                if self.new_line:
                    
                    # waiting for a new line
                    self.new_line = False
                    
                    # this is a new line and this is the current indentation column given by the first text
                    column = token.begin_column
                    
                    if column > self.current_column: # indentation level has increased
                        
                        # calibrate the 'size of indentation':
                        if not self.deduced_indentation:
                            self.deduced_indentation = column - 1
                        
                        if not is_token_subtype(Comment, token.type) and not is_token_subtype(Literal.String, token.type):
                            nbIndent = math.floor((column-self.current_column)/self.deduced_indentation)
                            for _ in range(nbIndent):
                                yield Token(type=IncreaseIndent)
#                         nbIndent = math.floor((column-self.current_column)/self.deduced_indentation)
#                         for _ in range(nbIndent):
#                             yield Token(type=IncreaseIndent)

                    elif column < self.current_column and not is_token_subtype(Comment, token.type) and not is_token_subtype(Literal.String, token.type): # decrease of indentation
                        
                        # we can 'close' several blocks at one time : we use deduced_indentation to know how many 
                        # decrease we should get 
                        while column < self.current_column:
                        
                            yield Token(type=DecreaseIndent)
                            self.current_column -= self.deduced_indentation
                    
                    # the current 'indent'
                    if not is_token_subtype(Comment, token.type) and not is_token_subtype(Literal.String, token.type):
                        self.current_column = column
#                     self.current_column = column
                        
                    if is_token_subtype(Comment, token.type):  
                        self.new_line = True
                        
            # still give the current token...
            yield token 

class IndentationBlock(BlockStatement):
    
    begin = IncreaseIndent
    end   = DecreaseIndent

class ParenthesedBlock(BlockStatement):
    
    begin = '('
    end   = ')'
    
class ScriptBlock(Term):
      
    match = Seq(Or('script', ':javascript'), Optional(ParenthesedBlock), Optional('.'), IndentationBlock)

def analyse(analyser, text, htmlContent = None, violations = None, htmlInterpreter = None):

    if not type(text) is str:
        text = text.read()

#     myLexer = create_lexer(JadeLexer)
    parser = Parser(JadeLexer, [ IndentationBlock, ParenthesedBlock ], [ ScriptBlock ])
    parser.lexer.add_filter(IndentJadeFilter())

    res = parser.parse(preprocess_text(text))
        
    if htmlInterpreter:
        interpreter = htmlInterpreter
    else:
        interpreter = HtmlInterpreter(analyser, htmlContent, violations)
        
    bc = BlockContext(0, None, None)
    parse_block(list(res), htmlContent, violations, interpreter, bc)
            
    crc = bc.lastToken.get_code_only_crc(bc.crc)

    objectDatabaseProperties = ObjectDatabaseProperties()
    objectDatabaseProperties.checksum = crc
    objectDatabaseProperties.codeLinesCount = bc.nbCodeLines
    objectDatabaseProperties.bodyCommentLinesCount = bc.nbComments
    
    if bc.firstToken:
        objectDatabaseProperties.bookmarks.append(Bookmark(htmlContent.file, bc.firstToken.get_begin_line(), bc.firstToken.get_begin_column(), bc.lastToken.get_end_line(), bc.lastToken.get_end_column()))
        
    interpreter.finish()
    return objectDatabaseProperties

def get_next_token(tokens, keepBlanks = False):
     
    try:
        token = next(tokens)
        if not keepBlanks:
            while isinstance(token, Token) and is_token_subtype(token.type, Text) and (not token.text or token.text == '\n'):
                token = next(tokens)
        return token
    except StopIteration:
        return None

class BlockContext:
    def __init__(self, crc, firstToken, lastToken, currentCodeLine = -1):
        self.crc = crc
        self.firstToken = firstToken
        self.lastToken = lastToken
        self.nbCodeLines = 0
        self.nbComments = 0
        self.currentCodeLine = currentCodeLine

def parse_attributes(tokens, htmlContent, violations, interpreter, context):
    
    attribute = None
    attributeToken = None
    token = get_next_token(tokens)
    
    while token:
        
        if is_token_subtype(token.type, Name.Attribute):
            
            txt = token.text.strip()
            if txt.endswith('='):
                attribute = txt[0:-1].strip()
            else:
                attribute = token.text
                interpreter.add_attribute_value(attribute, token, None, token)
            attributeToken = token
            
        elif is_token_subtype(token.type, String):

            if attribute:
                startsWithUrl = False
                if token.text.startswith('"@Url.') or token.text.startswith("'@Url."):
                    startsWithUrl = True
                    beg = token.text.find('(')
                    end = token.text.find(')', beg)
                    if beg >= 0 and end > 0:
                        value = token.text[beg + 1: end]
                else:
                    value = token.text
                if value[0] in ['"', "'"]:
                    value = value[1:-1]
                if startsWithUrl and value.startswith('~/'):
                    value = value[2:]
                beg = value.find('<%')
                if beg >= 0:
                    end = value.find('%>', beg)
                    if end >= 0:
                        value = value[:beg] + value[end+2:]
                    else:
                        value = value[:beg]
                interpreter.add_attribute_value(attribute, attributeToken, value, token)
                    
                attribute = None
                attributeToken = None
                
            if token.begin_line < token.end_line:
                currentCodeLine = token.end_line
                context.nbCodeLines += (token.end_line - token.begin_line)
        token = get_next_token(tokens)            
        
def parse_block(tokenList, htmlContent, violations, interpreter, context):

    attribute = None
    attributeToken = None
    templatingCommentLevel = 0
    currentCodeLine = context.currentCodeLine
    lastTag = None
    
    i = -1
    for token in tokenList:
        
        i += 1
        if isinstance(token, Token) and (is_token_subtype(token.type, DecreaseIndent) or is_token_subtype(token.type, IncreaseIndent)):
            continue
        if isinstance(token, IndentationBlock):
            bc = BlockContext(context.crc, context.firstToken, context.lastToken, currentCodeLine)
            parse_block(token.children, htmlContent, violations, interpreter, bc)
            context.crc = bc.crc
            if bc.lastToken:
                context.lastToken = bc.lastToken
            context.nbCodeLines += bc.nbCodeLines
            context.nbComments += bc.nbComments
            currentCodeLine = bc.currentCodeLine
            continue
        elif isinstance(token, ScriptBlock):
            if lastTag:
                interpreter.end_tag(lastTag)
                lastTag = None
            parse_script_block(token.get_children(), htmlContent, violations, interpreter, context)
            continue
        elif isinstance(token, ParenthesedBlock):
            parse_attributes(token.get_children(), htmlContent, violations, interpreter, context)
            continue
        if not token._is_whitespace:
            if token._is_comment:
                if token.text.strip() not in ['<!--', '-->']:
                    comment = token.text.strip('\n')
                    while '\n\n' in comment:
                        comment = comment.replace('\n\n', '\n')
                    context.nbComments += (1 + comment.count('\n'))
                currentCodeLine = token.begin_line
            else:
                if token.begin_line > currentCodeLine:
                    context.nbCodeLines += 1
                    currentCodeLine = token.begin_line
            
        if templatingCommentLevel > 0:
            if is_token_subtype(token.type, Text) and '--}}' in token.text and not '{{!--' in token.text:
                templatingCommentLevel -= 1
            continue
        
        if not context.firstToken:
            context.firstToken = token
        else:
            context.crc = context.lastToken._get_code_only_crc(context.crc)
        context.lastToken = token

        if is_token_subtype(token.type, Name.Tag):
            
            if attribute:
                interpreter.add_attribute_value(attribute, attributeToken, None, token)
                
            attribute = None
            if lastTag:
                interpreter.end_tag(lastTag)
            lastTag = token.text
            interpreter.start_tag(token.text, token)

#             if token.text[0:2] == '</':
#                 interpreter.end_text()
#                 interpreter.end_tag(token.text[2:-1].strip())
#             elif token.text[0] == '<':
#                 lastTag = token.text[1:].strip()
#                 interpreter.start_tag(lastTag, token)
#             elif token.text[0] == '/':
#                 interpreter.end_tag(None)
#             elif token.text == '%>':
#                 interpreter.end_builtin(token.text.strip())
#             elif token.text[0] == '>':
#                 # with input tag, final / is not mandatory
#                 # <input onfocus=write(1) autofocus>
#                 if lastTag in ['input', 'br', 'META']:
#                     interpreter.end_tag(lastTag)
#                 else:
#                     interpreter.start_text()
        elif is_token_subtype(token.type, Name.Function):
            
            if attribute:
                interpreter.add_attribute_value(attribute, attributeToken, None, token)
                
            attribute = None
            
            previousTokenIsTag = False
            if token.text.startswith('#'):
                try:
                    if is_token_subtype(tokenList[i - 1].type, Name.Tag):
                        previousTokenIsTag = True
                except:
                    pass
            if not previousTokenIsTag:
                if lastTag:
                    interpreter.end_tag(lastTag)
                lastTag = 'div'
                interpreter.start_tag('div', token)
            interpreter.add_attribute_value('id', token, token.text[1:], token)

        elif is_token_subtype(token.type, Name.Class):
            if not lastTag:
                lastTag = 'div'
                interpreter.start_tag('div', token)
            interpreter.add_attribute_value('class', token, token.text[1:], token)

        elif is_token_subtype(token.type, Name.Builtin):
            
#             if token.text[0:] == '<%=':
#                 interpreter.start_builtin_equal(token.text.strip(), token)
#             elif token.text[0:] == '<%':
#                 interpreter.start_builtin(token.text.strip(), token)
#             elif token.text[0:2] == '%>':
#                 interpreter.end_text()
#                 interpreter.end_builtin(token.text.strip())
            pass
                                
#         elif is_token_subtype(token.type, Name.Attribute):
#             
#             txt = token.text.strip()
#             if txt.endswith('='):
#                 attribute = txt[0:-1].strip()
#             else:
#                 attribute = token.text
#                 interpreter.add_attribute_value(attribute, attributeToken, None, token)
#             attributeToken = token
#             
#         elif is_token_subtype(token.type, String):
# 
#             if attribute:
#                 startsWithUrl = False
#                 if token.text.startswith('"@Url.') or token.text.startswith("'@Url."):
#                     startsWithUrl = True
#                     beg = token.text.find('(')
#                     end = token.text.find(')', beg)
#                     if beg >= 0 and end > 0:
#                         value = token.text[beg + 1: end]
#                 else:
#                     value = token.text
#                 if value[0] in ['"', "'"]:
#                     value = value[1:-1]
#                 if startsWithUrl and value.startswith('~/'):
#                     value = value[2:]
#                 beg = value.find('<%')
#                 if beg >= 0:
#                     end = value.find('%>', beg)
#                     if end >= 0:
#                         value = value[:beg] + value[end+2:]
#                     else:
#                         value = value[:beg]
#                 interpreter.add_attribute_value(attribute, attributeToken, value, token)
#                     
#                 attribute = None
                
            if token.begin_line < token.end_line:
                currentCodeLine = token.end_line
                context.nbCodeLines += (token.end_line - token.begin_line)            
                
        elif is_token_subtype(token.type, Text) or is_token_subtype(token.type, Error):

            if is_token_subtype(token.type, Text):
                if '{{!--' in token.text and not '--}}' in token.text:
                    templatingCommentLevel += 1
            
            if templatingCommentLevel == 0:
                attribute = None
                if token.text.startswith('%>'):
                    interpreter.end_text()
                else:
                    interpreter.add_text(token.text, token)
            if not token._is_whitespace and not token._is_comment:
                txt = token.text
                severalLines = False
                if '\n' in txt:
                    severalLines = True
                txt = txt.replace('\t', '')
                txt = txt.replace(' ', '')
                while '\n\n' in txt:
                    txt = txt.replace('\n\n', '\n')
                if severalLines:
                    nb = txt.count('\n')
                    currentCodeLine = token.end_line
                    context.nbCodeLines += nb            
        else:
            attribute = None
            if not is_token_subtype(token.type, Comment):
                interpreter.add_text(token.text, token)
        
    if lastTag:
        interpreter.end_tag(lastTag)
        
def parse_script_block(tokens, htmlContent, violations, interpreter, context):

    attribute = None
    attributeToken = None
    templatingCommentLevel = 0
    currentCodeLine = context.currentCodeLine
    lastTag = None
    
    token = get_next_token(tokens)
    
    while token:

        if isinstance(token, IndentationBlock):
            parse_script_code(token.get_children(), htmlContent, violations, interpreter, context)
            token = get_next_token(tokens)
            continue
        elif isinstance(token, ParenthesedBlock):
            parse_attributes(token.get_children(), htmlContent, violations, interpreter, context)
            token = get_next_token(tokens)
            continue
        if not token._is_whitespace:
            if token._is_comment:
                if token.text.strip() not in ['<!--', '-->']:
                    comment = token.text.strip('\n')
                    while '\n\n' in comment:
                        comment = comment.replace('\n\n', '\n')
                    context.nbComments += (1 + comment.count('\n'))
                currentCodeLine = token.begin_line
            else:
                if token.begin_line > currentCodeLine:
                    context.nbCodeLines += 1
                    currentCodeLine = token.begin_line
            
        if templatingCommentLevel > 0:
            if is_token_subtype(token.type, Text) and '--}}' in token.text and not '{{!--' in token.text:
                templatingCommentLevel -= 1
            continue
        
        if not context.firstToken:
            context.firstToken = token
        else:
            context.crc = context.lastToken._get_code_only_crc(context.crc)
        context.lastToken = token

        if is_token_subtype(token.type, Name.Tag):
            
            if attribute:
                interpreter.add_attribute_value(attribute, attributeToken, None, token)
                
            attribute = None
            if lastTag:
                interpreter.end_tag(lastTag)
            lastTag = token.text
            interpreter.start_tag(token.text, token)
                
            if token.begin_line < token.end_line:
                currentCodeLine = token.end_line
                context.nbCodeLines += (token.end_line - token.begin_line)            

        if is_token_subtype(token.type, Name.Decorator):
            
            if attribute:
                interpreter.add_attribute_value(attribute, attributeToken, None, token)
                
            attribute = None
            if lastTag:
                interpreter.end_tag(lastTag)
            lastTag = token.text
            interpreter.start_tag('script', token)
            interpreter.add_attribute_value('language', token, 'JavaScript', token)
                
            if token.begin_line < token.end_line:
                currentCodeLine = token.end_line
                context.nbCodeLines += (token.end_line - token.begin_line)            
                
        elif is_token_subtype(token.type, Text) or is_token_subtype(token.type, Error):

            if is_token_subtype(token.type, Text):
                if '{{!--' in token.text and not '--}}' in token.text:
                    templatingCommentLevel += 1
            
            if templatingCommentLevel == 0:
                attribute = None
                if token.text.startswith('%>'):
                    interpreter.end_text()
                else:
                    interpreter.add_text(token.text, token)
            if not token._is_whitespace and not token._is_comment:
                txt = token.text
                severalLines = False
                if '\n' in txt:
                    severalLines = True
                txt = txt.replace('\t', '')
                txt = txt.replace(' ', '')
                while '\n\n' in txt:
                    txt = txt.replace('\n\n', '\n')
                if severalLines:
                    nb = txt.count('\n')
                    currentCodeLine = token.end_line
                    context.nbCodeLines += nb            
        else:
            attribute = None
            if not is_token_subtype(token.type, Comment):
                interpreter.add_text(token.text, token)
        
        token = get_next_token(tokens)
        
    if lastTag:
        interpreter.end_tag(lastTag)

def parse_script_code(tokens, htmlContent, violations, interpreter, context):

    currentCodeLine = context.currentCodeLine
    
    token = get_next_token(tokens, True)
    lastLine = 0
    interpreter.start_text()
#     begin_line, end_line
    while token:
        try:
            if token.text == '|':
                if lastLine > 0:
                    text = '\n'*(token.begin_line-lastLine)
                    text += ' '*(token.begin_column-1)
                else:
                    text = ' '*(token.begin_column-1)
                lastLine = token.end_line
            elif token.text.startswith('|'):
                if lastLine > 0:
                    text = '\n'*(token.begin_line-lastLine)
                    text += ' '*(token.begin_column-1)
                else:
                    text = ' '*(token.begin_column-1)
                lastLine = token.end_line
                text += token.text[1:]
            else:
                text = token.text
            if text:
                interpreter.add_text(text, token)
        except:
            pass
        token = get_next_token(tokens, True)

    interpreter.end_text()
