import re

from pygments.lexer import RegexLexer, using
from pygments.lexers.web import CssLexer
from pygments.token import Text, Comment, Name, String, Error, is_token_subtype
from cast.analysers import Bookmark
from javascript_parser.light_parser import create_lexer
from html_interpreter import HtmlInterpreter
from javascript_parser.symbols import ObjectDatabaseProperties
import cast.analysers.ua
import traceback

class HtmlLexer(RegexLexer):
    """
    For HTML 4 and XHTML 1 markup. Nested JavaScript and CSS is highlighted
    by the appropriate lexer.
    """

    name = 'HTML'
    aliases = ['html']
    filenames = ['*.html', '*.htm', '*.xhtml', '*.xslt']
    mimetypes = ['text/html', 'application/xhtml+xml']

    flags = re.IGNORECASE | re.DOTALL
    tokens = {
        'root': [
            ('[^<&]+', Text),
            (r'&\S*?;', Name.Entity),
            (r'\<\!\[CDATA\[.*?\]\]\>', Comment.Preproc),
            ('<!--', Comment, 'comment1'),
            ('<%--', Comment, 'comment2'),
            (r'<\?.*?\?>', Comment.Preproc),
            ('<![^>]*>', Comment.Preproc),
            (r'<\s*script\s+(?=type="text/ng-template")', Name.Tag, 'tag'),
            (r'<\s*script\s+(?=type="text/x-handlebars-template")', Name.Tag, 'tag'),
            (r'<\s*script\s+(?=id=")', Name.Tag, 'tag'),
            (r'<\s*script\s+(?=src=")', Name.Tag, 'tag'),
            (r'<\s*script\s+(?=type="text/javascript")', Name.Tag, ('script-content', 'tag')),
            (r'<\s*script\s*(?=>)', Name.Tag, ('script-content', 'tag')),
            (r'<\s*script\s*', Name.Tag, ('script-content', 'tag')),
            (r'<%=', Name.Builtin, ('template-content')),
            (r'<%@\s*[a-zA-Z0-9:-]+\s*', Name.Tag, 'tag'),
            (r'<%', Name.Builtin, ('template-content')),
            (r'<\s*style\s*', Name.Tag, ('style-content', 'tag')),
            (r'<\s*[a-zA-Z0-9:-]+', Name.Tag, 'tag'),
            (r'<\s*/\s*[a-zA-Z0-9:]+\s*>', Name.Tag),
#             (r'@', Text, ('script-content')),
        ],
        'comment1': [
            ('[^-]+', Comment),
            ('-->', Comment, '#pop'),
            ('-', Comment),
        ],
        'comment2': [
            ('[^-]+', Comment),
            ('--%>', Comment, '#pop'),
            ('-', Comment),
        ],
        'tag': [
            (r'\s+', Text),
            (r'[*#a-zA-Z0-9_:-]+\s*=\s*', Name.Attribute, 'attr'),
            (r'\([^)]*\)\s*=\s*', Name.Attribute, 'attr'),
            (r'[*#a-zA-Z0-9_:-]+', Name.Attribute),
            (r'/?\s*>', Name.Tag, '#pop'),
            (r'%>', Name.Tag, '#pop'),
        ],
        'script-content': [
            (r'<\s*/\s*script\s*>', Name.Tag, '#pop'),
            (r'.+?(?=<\s*/\s*script\s*>)', Text),
        ],
        'template-content': [
            (r'.+?(?=%>)', Text, '#pop'),
            (r'/?\s*%>', Name.Builtin, '#pop'),
        ],
        'style-content': [
            (r'<\s*/\s*style\s*>', Name.Tag, '#pop'),
            (r'.+?(?=<\s*/\s*style\s*>)', using(CssLexer)),
        ],
#         'attr': [
#             ('"<.*?>"', String, '#pop'),
#             ("'<.*?>'", String, '#pop'),
#             ('"@Url.[^\r\n\)]*\)"', String, '#pop'),
#             ("'@Url.[^\r\n\)]*\)'", String, '#pop'),
#             ('"[^\"]*"', String, '#pop'),
#             ("'[^\']*'", String, '#pop'),
#             ('"[^\"].*?"(?=[\s>]+)', String, '#pop'),
#             (r'[^\s>]+', String, '#pop'),
#         ],
        'attr': [
            ('"<.*?>[^"<]*"', String, '#pop'),
            ("'<.*?>[^'<]*'", String, '#pop'),
            ('"<.*?>[^"<]*<.*?>[^"]*"', String, '#pop'),
            ("'<.*?>[^'<]*<.*?>[^']*'", String, '#pop'),
            ('"@Url.[^\r\n\)]*\)"', String, '#pop'),
            ("'@Url.[^\r\n\)]*\)'", String, '#pop'),
            ('"[^\"]*"', String, '#pop'),
            ("'[^\']*'", String, '#pop'),
            ('"[^\"].*?"(?=[\s>]+)', String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
        'attr-crochets': [
            ('"<.*?>"', String, '#pop'),
            ("'<.*?>'", String, '#pop'),
            ('"@Url.[^\r\n\)]*\)"', String, '#pop'),
            ("'@Url.[^\r\n\)]*\)'", String, '#pop'),
            ('"[^\"]*"', String, '#pop'),
            ("'[^\']*'", String, '#pop'),
            ('"[^\"].*?"(?=[\s>]+)', String, '#pop'),
            (r'[^\s>]+', String, '#pop'),
        ],
    }
    
def preanalyse_jsp(analyser, text, taglibs):

    if not type(text) is str:
        text = text.read()

    myLexer = create_lexer(HtmlLexer)
    tokens = myLexer.get_tokens(text)
        
    inTaglib = False
    inPrefix = False
    inUri = False
    prefix = None
    uri = None
    
    for token in tokens:

        if is_token_subtype(token.type, Name.Tag):
            
            if token.text.startswith('<%@') and 'taglib' in token.text:
                inTaglib = True
            elif inTaglib and token.text[0:2] == '%>':
                if prefix and uri:
                    taglibs[prefix] = uri
                inTaglib = False
                inPrefix = False
                prefix = None
                uri = None
                inUri = False

        elif inTaglib and is_token_subtype(token.type, Name.Attribute):
            
            txt = token.text.strip()
            if txt.endswith('='):
                attribute = txt[0:-1].strip()
            else:
                attribute = token.text
            if attribute == 'prefix':
                inPrefix = True
            elif attribute == 'uri':
                inUri = True
            
        elif inTaglib and is_token_subtype(token.type, String):

            if attribute:
                value = token.text.strip('"\'')
                if inPrefix:
                    prefix = value
                    inPrefix = False
                elif inUri:
                    uri = value
                    inUri = False
    
def analyse(analyser, text, htmlContent = None, violations = None, htmlInterpreter = None):

    if not type(text) is str:
        text = text.read()

    myLexer = create_lexer(HtmlLexer)
    tokens = myLexer.get_tokens(text)
        
    if htmlInterpreter:
        interpreter = htmlInterpreter
    else:
        interpreter = HtmlInterpreter(analyser, htmlContent, violations)
    
    attribute = None
    attributeToken = None
    firstToken = None
    lastToken = None
    crc = 0
    lastTag = None
    templatingCommentLevel = 0
    nbCodeLines = 0
    nbComments = 0
    currentCodeLine = -1
    
    for token in tokens:

        if not token._is_whitespace:
            if token._is_comment:
                if token.text.strip() not in ['<!--', '-->']:
                    comment = token.text.strip('\n')
                    while '\n\n' in comment:
                        comment = comment.replace('\n\n', '\n')
                    nbComments += (1 + comment.count('\n'))
                currentCodeLine = token.begin_line
            else:
                if token.begin_line > currentCodeLine:
                    nbCodeLines += 1
                    currentCodeLine = token.begin_line
            
        if templatingCommentLevel > 0:
            if is_token_subtype(token.type, Text) and '--}}' in token.text and not '{{!--' in token.text:
                templatingCommentLevel -= 1
            continue
        
#         crc = token._get_code_only_crc(crc)
        if not firstToken:
            firstToken = token
        else:
            crc = lastToken._get_code_only_crc(crc)
        lastToken = token

        if is_token_subtype(token.type, Name.Tag):
            
            if attribute:
                interpreter.add_attribute_value(attribute, attributeToken, None, token)
                
            attribute = None

            if token.text[0:2] == '</':
                interpreter.end_text()
                interpreter.end_tag(token.text[2:-1].strip(), token)
#             elif token.text[0:2] == '<%':
#                 interpreter.start_builtin(token.text.strip(), token)
            elif token.text[0] == '<':
                lastTag = token.text[1:].strip()
                interpreter.start_tag(lastTag, token)
            elif token.text[0] == '/':
                interpreter.end_tag(None)
            elif token.text == '%>':
                interpreter.end_builtin(token.text.strip())
            elif token.text[0] == '>':
                # with input tag, final / is not mandatory
                # <input onfocus=write(1) autofocus>
#                 if lastTag in ['input', 'br', 'META']:
#                     interpreter.end_tag(lastTag)
#                 else:
                interpreter.start_text()

        elif not interpreter.in_javascript_code and is_token_subtype(token.type, Name.Builtin):
            
            if token.text[0:] == '<%=':
                interpreter.start_builtin_equal(token.text.strip(), token)
            elif token.text[0:] == '<%':
                interpreter.start_builtin(token.text.strip(), token)
            elif token.text[0:2] == '%>':
                interpreter.end_text()
                interpreter.end_builtin(token.text.strip())
                                
        elif is_token_subtype(token.type, Name.Attribute):
            
            txt = token.text.strip()
            if txt.endswith('='):
                attribute = txt[0:-1].strip()
            else:
                attribute = token.text
                interpreter.add_attribute_value(attribute, attributeToken, None, token)
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
                
            if token.begin_line < token.end_line:
                currentCodeLine = token.end_line
                nbCodeLines += (token.end_line - token.begin_line)            
                
        elif is_token_subtype(token.type, Text) or is_token_subtype(token.type, Error):

            if is_token_subtype(token.type, Text):
                if '{{!--' in token.text and not '--}}' in token.text:
                    templatingCommentLevel += 1
            
            if templatingCommentLevel == 0:
                attribute = None
                if token.text.startswith('%>') and not interpreter.in_javascript_code:
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
                    nbCodeLines += nb            
        else:
            attribute = None
            if not is_token_subtype(token.type, Comment):
                interpreter.add_text(token.text, token)
            
    crc = lastToken.get_code_only_crc(crc)

    objectDatabaseProperties = ObjectDatabaseProperties()
    objectDatabaseProperties.checksum = crc
    objectDatabaseProperties.codeLinesCount = nbCodeLines
    objectDatabaseProperties.bodyCommentLinesCount = nbComments
    
    if firstToken:
        objectDatabaseProperties.bookmarks.append(Bookmark(htmlContent.file, firstToken.get_begin_line(), firstToken.get_begin_column(), lastToken.get_end_line(), lastToken.get_end_column()))
        
    interpreter.finish()
    return objectDatabaseProperties