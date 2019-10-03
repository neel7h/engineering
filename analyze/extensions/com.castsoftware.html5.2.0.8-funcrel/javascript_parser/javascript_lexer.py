# -*- coding: utf-8 -*-
"""
    pygments.lexers.web
    ~~~~~~~~~~~~~~~~~~~

    Lexers for web-related languages and markup.

    :copyright: Copyright 2006-2013 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re

from pygments.lexer import RegexLexer, bygroups, include
from pygments.token import Text, Comment, Operator, Keyword, Name, String, \
     Number, Punctuation

class JavascriptLexer(RegexLexer):
    """
    For JavaScript source code.
    """

    name = 'JavaScript'
    aliases = ['js', 'javascript']
    filenames = ['*.js', ]
    mimetypes = ['application/javascript', 'application/x-javascript',
                 'text/x-javascript', 'text/javascript', ]

    flags = re.DOTALL
    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'<!--', Comment),
            (r'//.*?\n(?!")', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            (r'', Text, '#pop')
        ],
        'badregex': [
            (r'\n', Text, '#pop')
        ],
        'root': [
            (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r'\+\+|--|=>|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|[-<>+*%&\|\^/])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(for|in|while|do|break|return|continue|switch|case|default|if|else|'
             r'throw|try|catch|finally|new|delete|typeof|instanceof|void|each|'
             r'this)\b', Keyword, 'slashstartsregex'),
            (r'(var|const|let|with|function|class)\b', Keyword.Declaration, 'slashstartsregex'),
            (r'(abstract|boolean|byte|char|const|debugger|double|enum|export|'
             r'extends|final|float|goto|implements|import|int|interface|long|native|'
             r'package|private|protected|public|short|static|super|synchronized|throws|'
             r'transient|volatile|as|from)\b', Keyword.Reserved),
            (r'(true|false|null|NaN|Infinity|undefined)\b', Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|netscape|'
             r'Number|Object|Packages|RegExp|String|sun|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'Error|eval|isFinite|isNaN|parseFloat|parseInt|document|this|'
             r'window)\b', Name.Builtin),
            (r'[$a-zA-Z_][$a-zA-Z0-9_]*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
            (r"'(\\\\|\\'|[^'])*'", String.Single),
            (r"`(\\\\|\\`|[^`])*`", String.Single),
        ]
    }


class JSXLexer(JavascriptLexer):
    """
    For JSX source code.
    """

    name = 'JSX'
    aliases = ['jsx', 'react']
    filenames = ['*.jsx', ]
    mimetypes = ['text/jsx', 'text/typescript-jsx', ]

    flags = re.MULTILINE | re.DOTALL | re.UNICODE

    tokens = {
        'commentsandwhitespace': [
            (r'\s+', Text),
            (r'<!--', Comment),
            (r'//.*?\n(?!")', Comment.Single),
            (r'/\*.*?\*/', Comment.Multiline)
        ],
        'slashstartsregex': [
            include('commentsandwhitespace'),
            (r'/(\\.|[^[/\\\n]|\[(\\.|[^\]\\\n])*])+/'
             r'([gim]+\b|\B)', String.Regex, '#pop'),
            (r'(?=/)', Text, ('#pop', 'badregex')),
            (r'', Text, '#pop')
        ],
        'badregex': [
            (r'\n', Text, '#pop')
        ],
        'root': [
            (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r'\+\+|--|=>|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|[-<>+*%&\|\^/])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(for|in|while|do|break|return|continue|switch|case|default|if|else|'
             r'throw|try|catch|finally|new|delete|typeof|instanceof|void|'
             r'this)\b', Keyword, 'slashstartsregex'),
            (r'(var|const|let|with|function|class)\b', Keyword.Declaration, 'slashstartsregex'),
            (r'(abstract|boolean|byte|char|const|debugger|double|enum|export|'
             r'extends|final|float|goto|implements|import|int|interface|long|native|'
             r'package|private|protected|public|short|static|super|synchronized|throws|'
             r'transient|volatile|as|from)\b', Keyword.Reserved),
            (r'(true|false|null|NaN|Infinity|undefined)\b', Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|netscape|'
             r'Number|Object|Packages|RegExp|String|sun|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'Error|eval|isFinite|isNaN|parseFloat|parseInt|document|this|'
             r'window)\b', Name.Builtin),
            (r'[$a-zA-Z_][$a-zA-Z0-9_]*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
            (r"'(\\\\|\\'|[^'])*'", String.Single),
            (r"`(\\\\|\\`|[^`])*`", String.Single),
        ],
        'root_embedded': [
            (r'}', Punctuation, '#pop'),
            (r'{', Punctuation, '#push'),
            (r'(<)([\.\w_\-]+)(?=[ \t\r\n>/])',
             bygroups(Punctuation, Name.Tag), 'tag'),
            (r'^(?=\s|/|<!--)', Text, 'slashstartsregex'),
            include('commentsandwhitespace'),
            (r'\+\+|--|=>|~|&&|\?|:|\|\||\\(?=\n)|'
             r'(<<|>>>?|==?|!=?|[-<>+*%&\|\^/])=?', Operator, 'slashstartsregex'),
            (r'[{(\[;,]', Punctuation, 'slashstartsregex'),
            (r'[})\].]', Punctuation),
            (r'(for|in|while|do|break|return|continue|switch|case|default|if|else|'
             r'throw|try|catch|finally|new|delete|typeof|instanceof|void|'
             r'this)\b', Keyword, 'slashstartsregex'),
            (r'(var|const|let|with|function|class)\b', Keyword.Declaration, 'slashstartsregex'),
            (r'(abstract|boolean|byte|char|const|debugger|double|enum|export|'
             r'extends|final|float|goto|implements|import|int|interface|long|native|'
             r'package|private|protected|public|short|static|super|synchronized|throws|'
             r'transient|volatile)\b', Keyword.Reserved),
            (r'(true|false|null|NaN|Infinity|undefined)\b', Keyword.Constant),
            (r'(Array|Boolean|Date|Error|Function|Math|netscape|'
             r'Number|Object|Packages|RegExp|String|sun|decodeURI|'
             r'decodeURIComponent|encodeURI|encodeURIComponent|'
             r'Error|eval|isFinite|isNaN|parseFloat|parseInt|document|this|'
             r'window)\b', Name.Builtin),
            (r'[$a-zA-Z_][$a-zA-Z0-9_]*', Name.Other),
            (r'[0-9][0-9]*\.[0-9]+([eE][0-9]+)?[fd]?', Number.Float),
            (r'0x[0-9a-fA-F]+', Number.Hex),
            (r'[0-9]+', Number.Integer),
            (r'"(\\\\|\\"|[^"])*"', String.Double),
            (r"'(\\\\|\\'|[^'])*'", String.Single),
            (r"`(\\\\|\\`|[^`])*`", String.Single),
        ]
    }
# \s equivalent to [^ \t\r\n]

#     tokens.update({
#        'jsx': [
#             (r'(<)([\w_\-]+)([ \t\r\n])',
#              bygroups(Punctuation, Name.Tag, Text), 'tag'),
#             (r'(<)([\w_\-]+)(>)',
#              bygroups(Punctuation, Name.Tag, Punctuation), 'tag2'),
#             (r'(<)(/)(\s*)([\w_\-]+)(\s*)(>)',
#              bygroups(Punctuation, Punctuation, Text, Name.Tag, Text,
#                       Punctuation)),
#         ],
#         'tag': [
#             (r'\s+', Text),
#             (r'([\w]+\s*)(=)(\s*{)', bygroups(Name.Attribute, Operator, String),
#              'attr'),
#             (r'([\w]+\s*)(=)(\s*)', bygroups(Name.Attribute, Operator, Text),
#              'attr'),
#             (r'[{}]+', Punctuation),
#             (r'[\w\.]+', Name.Attribute),
#             (r'(/?)(\s*)(>)', bygroups(Punctuation, Text, Punctuation), '#pop'),
#         ],
#         'tag2': [
#             (r'[^<]*', Text, '#pop'),
#         ],
#         'attr': [
# #             ('\s+', Text),
#             ('".*?"', String, '#pop'),
#             ("'.*?'", String, '#pop'),
#             ('{`.*?`}', String, '#pop'),
# #             ('{.*?}', String, '#pop'),
#             
#             ('{', String, '#push'),
#             ('}', String, '#pop'),
#             ('[^{}]*', String),
#                  
# #             ("'.*?'", String, '#pop'),
#             (r'[^\s>]+', String, '#pop'),
#         ],
#         })
    tokens.update({
       'jsx': [
            (r'(<)([\.\w_\-]+)(?=[ \t\r\n>/])',
             bygroups(Punctuation, Name.Tag), 'tag'),
        ],
        'tag': [
            (r'>', Punctuation, 'jsx_text'),
            (r'(<)(/)(\s*)([\.\w_\-]+)(\s*)(?=>)',
             bygroups(Punctuation, Punctuation, Text, Name.Tag, Text), '#pop'),
            (r'([ \r\t\n]*)(/)(\s*)(>)',
             bygroups(Text, Punctuation, Text, Punctuation), '#pop'),
            (r'([\w-]+)(\s*)(=)(\s*{)', bygroups(Name.Attribute, Text, Operator, String),
             'attr2'),
            (r'([\w-]+)(\s*)(=)(\s*)', bygroups(Name.Attribute, Text, Operator, Text),
             'attr'),
            (r'[\w-]+', Name.Attribute),
            (r'{[^}]*}', Name.Attribute),
            (r'[ \r\n\t]+', Text),
            (r'[^<]+', String),
            (r'(<)([\.\w_\-]+)',
             bygroups(Punctuation, Name.Tag), '#push'),
        ],
        'attr': [
            ('".*?"', String, '#pop'),
            ("'.*?'", String, '#pop'),
                 
            (r'[^\s>]+', String, '#pop'),
        ],
        'attr2': [
            ('{', String, '#push'),
            ('}', String, '#pop'),
            ('[^{}]*', String),
                 
            (r'[^\s>]+', String, '#pop'),
        ],
        'jsx_text': [
            (r'(<)([\.\w_\-]+)(?=[ \t\r\n>/])',
             bygroups(Punctuation, Name.Tag), 'tag'),
            (r'[ \r\n\t]+', String),
            (r'{', Punctuation, 'root_embedded'),
            (r'[^<]+', String),
            (r'[.]*(?=<)', Text, '#pop'),
        ],
        })
    tokens['root'].insert(0, include('jsx'))
    
# class JSXLexer(JavascriptLexer):
#     
#     JavascriptLexer.tokens.update({
#         'jsx': [
#             (r'(<)([\w_\-]+)',
#              bygroups(Punctuation, Name.Tag), 'tag'),
#             (r'(<)(/)(\s*)([\w_\-]+)(\s*)(>)',
#              bygroups(Punctuation, Punctuation, Text, Name.Tag, Text,
#                       Punctuation)),
#         ],
#         'tag': [
#             (r'\s+', Text),
#             (r'([\w]+\s*)(=)(\s*)', bygroups(Name.Attribute, Operator, Text),
#              'attr'),
#             (r'[{}]+', Punctuation),
#             (r'[\w\.]+', Name.Attribute),
#             (r'(/?)(\s*)(>)', bygroups(Punctuation, Text, Punctuation), '#pop'),
#         ],
#         'attr': [
#             ('\s+', Text),
#             ('".*?"', String, '#pop'),
#             ("'.*?'", String, '#pop'),
#             (r'[^\s>]+', String, '#pop'),
#         ],
#     })
#     JavascriptLexer.tokens['root'].insert(0, include('jsx'))
