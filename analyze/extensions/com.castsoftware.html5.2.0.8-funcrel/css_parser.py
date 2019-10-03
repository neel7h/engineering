from pygments.lexers.web import CssLexer
from pygments.token import Name, String, is_token_subtype
from javascript_parser.light_parser import create_lexer
from javascript_parser.symbols import ObjectDatabaseProperties
from cast.analysers import Bookmark
# from css_interpreter import CssInterpreter

def analyse(analyser, text, cssContent, violations = None, begin_line = 1, begin_column = 1, current_crc = 0):

    nbCodeLines = 0
    nbComments = 0
    currentCodeLine = -1

    if not type(text) is str:
        text = text.read()

    myLexer = create_lexer(CssLexer)
    tokens = myLexer.get_tokens(text)
            
    firstToken = None
    lastTokenBeforeLast = None
    lastToken = None
    crc = current_crc
    file = cssContent.get_file()
    
    for token in tokens:

        if not token._is_whitespace:
            if token._is_comment:
                comment = token.text.replace('/*', '')
                comment = comment.replace('*/', '')
                comment = comment.strip('\n')
                while '\n\n' in comment:
                    comment = comment.replace('\n\n', '\n')
                nbComments += (1 + comment.count('\n'))
                currentCodeLine = token.begin_line
            else:
                if token.begin_line > currentCodeLine:
                    nbCodeLines += 1
                    currentCodeLine = token.begin_line

        if not firstToken:
            firstToken = token
        else:
            crc = lastToken._get_code_only_crc(crc)
        lastTokenBeforeLast = lastToken
        lastToken = token
        
        if violations:
            if is_token_subtype(token.type, String):
                if ('javascript:' in token.text and len(token.text) > len('"javascript:"')) or 'expression(' in token.text:
                    bm = Bookmark(file, token.get_begin_line(), token.get_begin_column(), token.get_end_line(), token.get_end_column())
                    violations.add_javascriptOrExpressionInCss_violation(cssContent, bm)
            elif is_token_subtype(token.type, Name):
                if token.text == 'expression':
                    bm = Bookmark(file, token.get_begin_line(), token.get_begin_column(), token.get_end_line(), token.get_end_column())
                    violations.add_javascriptOrExpressionInCss_violation(cssContent, bm)
            
    crc = lastToken.get_code_only_crc(crc)

    objectDatabaseProperties = ObjectDatabaseProperties()
    objectDatabaseProperties.checksum = crc
    objectDatabaseProperties.codeLinesCount = nbCodeLines
    objectDatabaseProperties.bodyCommentLinesCount = nbComments
    
    if firstToken and lastTokenBeforeLast:
        lineStart = firstToken.get_begin_line()
        lineEnd = lastTokenBeforeLast.get_end_line()
        if lineStart == lineEnd:
            objectDatabaseProperties.bookmarks.append(Bookmark(file, lineStart + begin_line-1, firstToken.get_begin_column() + begin_column - 1, lineEnd + begin_line-1, lastTokenBeforeLast.get_end_column() + begin_column - 1))
        else:
            objectDatabaseProperties.bookmarks.append(Bookmark(file, lineStart + begin_line-1, firstToken.get_begin_column() + begin_column - 1, lineEnd + begin_line-1, lastTokenBeforeLast.get_end_column()))
        
    return objectDatabaseProperties