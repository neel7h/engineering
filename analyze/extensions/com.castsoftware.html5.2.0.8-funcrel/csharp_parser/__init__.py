from pygments.lexer import RegexLexer, using
from pygments.filter import Filter
from pygments.token import is_token_subtype, String, Name, Text, Keyword, Punctuation, Operator, Literal, Error, Comment
# from pygments.lexers.dotnet import CSharpLexer
from javascript_parser.light_parser import Parser, Statement, BlockStatement, Token, Seq, TokenIterator, Lookahead, Any, Optional, Or, Term, Node
from javascript_parser.symbols import Identifier, BracketedIdentifier, Function, AstString, ObjectValue, GlobalFunction, GlobalVariable, HtmlContent, AstOperator, OrExpression, Violations, AstToken
from javascript_parser.diags_parser import process_diags
from cast.analysers import Bookmark
import cast.analysers.ua
from inspect import isclass
from csharp_parser.csharp_interpreter import CSharpInterpreter
import os
import json
import traceback
from collections import OrderedDict
import re

from pygments.lexer import DelegatingLexer, bygroups, include, this
from pygments.token import Number, Other
from pygments.util import get_choice_opt
from pygments import unistring as uni

from pygments.lexers.web import XmlLexer

class CSharpLexer(RegexLexer):
    """
    For `C# <http://msdn2.microsoft.com/en-us/vcsharp/default.aspx>`_
    source code.

    Additional options accepted:

    `unicodelevel`
      Determines which Unicode characters this lexer allows for identifiers.
      The possible values are:

      * ``none`` -- only the ASCII letters and numbers are allowed. This
        is the fastest selection.
      * ``basic`` -- all Unicode characters from the specification except
        category ``Lo`` are allowed.
      * ``full`` -- all Unicode characters as specified in the C# specs
        are allowed.  Note that this means a considerable slowdown since the
        ``Lo`` category has more than 40,000 characters in it!

      The default value is ``basic``.

      *New in Pygments 0.8.*
    """

    name = 'C#'
    aliases = ['csharp', 'c#']
    filenames = ['*.cs']
    mimetypes = ['text/x-csharp'] # inferred

    flags = re.MULTILINE | re.DOTALL | re.UNICODE

    # for the range of allowed unicode characters in identifiers,
    # see http://www.ecma-international.org/publications/files/ECMA-ST/Ecma-334.pdf

    levels = {
        'none': '@?[_a-zA-Z][a-zA-Z0-9_]*',
        'basic': ('@?[_' + uni.Lu + uni.Ll + uni.Lt + uni.Lm + uni.Nl + ']' +
                  '[' + uni.Lu + uni.Ll + uni.Lt + uni.Lm + uni.Nl +
                  uni.Nd + uni.Pc + uni.Cf + uni.Mn + uni.Mc + ']*'),
        'full': ('@?(?:_|[^' +
                 uni.allexcept('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl') + '])'
                 + '[^' + uni.allexcept('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nl',
                                        'Nd', 'Pc', 'Cf', 'Mn', 'Mc') + ']*'),
    }

    tokens = {}
    token_variants = True

    for levelname, cs_ident in list(levels.items()):
        tokens[levelname] = {
            'root': [
                # method names
                (r'^([ \t]*(?:' + cs_ident + r'(?:\[\])?\s+)+?)' # return type
                 r'(' + cs_ident + ')'                           # method name
                 r'(\s*)(\()',                               # signature start
                 bygroups(using(this), Name.Function, Text, Punctuation)),
#                 (r'^\s*\[.*?\]', Name.Attribute),
                (r'[^\S\n]+', Text),
                (r'\\\n', Text), # line continuation
                (r'//.*?\n', Comment.Single),
                (r'/[*].*?[*]/', Comment.Multiline),
                (r'\n', Text),
                (r'[~!%^&*()+=|\[\]:;,.<>/?-]', Punctuation),
                (r'[{}]', Punctuation),
                (r'@"(""|[^"])*"', String),
                (r'"(\\\\|\\"|[^"\n])*["\n]', String),
                (r"'\\.'|'[^\\]'", String.Char),
                (r"[0-9](\.[0-9]*)?([eE][+-][0-9]+)?"
                 r"[flFLdD]?|0[xX][0-9a-fA-F]+[Ll]?", Number),
                (r'#[ \t]*(if|endif|else|elif|define|undef|'
                 r'line|error|warning|region|endregion|pragma)\b.*?\n',
                 Comment.Preproc),
                (r'\b(extern)(\s+)(alias)\b', bygroups(Keyword, Text,
                 Keyword)),
                (r'(abstract|as|async|await|base|break|case|catch|'
                 r'checked|const|continue|default|delegate|'
                 r'do|else|enum|event|explicit|extern|false|finally|'
                 r'fixed|for|foreach|goto|if|implicit|in|interface|'
                 r'internal|is|lock|new|null|operator|'
                 r'out|override|params|private|protected|public|readonly|'
                 r'ref|return|sealed|sizeof|stackalloc|static|'
                 r'switch|this|throw|true|try|typeof|'
                 r'unchecked|unsafe|virtual|void|while|'
                 r'get|set|new|partial|yield|add|remove|value|alias|ascending|'
                 r'descending|from|group|into|orderby|select|where|'
                 r'join|equals)\b', Keyword),
                (r'(global)(::)', bygroups(Keyword, Punctuation)),
                (r'(bool|byte|char|decimal|double|dynamic|float|int|long|object|'
                 r'sbyte|short|string|uint|ulong|ushort|var)\b\??', Keyword.Type),
                (r'(class|struct)(\s+)', bygroups(Keyword, Text), 'class'),
                (r'(namespace|using)(\s+)', bygroups(Keyword, Text), 'namespace'),
                (cs_ident, Name),
            ],
            'class': [
                (cs_ident, Name.Class, '#pop')
            ],
            'namespace': [
                (r'(?=\()', Text, '#pop'), # using (resource)
                ('(' + cs_ident + r'|\.)+', Name.Namespace, '#pop')
            ]
        }

    def __init__(self, **options):
        level = get_choice_opt(options, 'unicodelevel', list(self.tokens.keys()), 'basic')
        if level not in self._all_tokens:
            # compile the regexes now
            self._tokens = self.__class__.process_tokendef(level)
        else:
            self._tokens = self._all_tokens[level]

        RegexLexer.__init__(self, **options)

class ParenthesedBlock(BlockStatement):
    begin = '('
    end   = ')'
    
    def get_text(self):
        text = ''
        for child in self.get_children():
            txt = child.get_text()
            if txt:
                text += txt
        return text

class CurlyBracketedBlock(BlockStatement):
    begin = '{'
    end   = '}'
    
    def get_text(self):
        text = ''
        for child in self.get_children():
            txt = child.get_text()
            if txt:
                text += txt
        return text

class BracketedBlock(BlockStatement):
    begin = '['
    end   = ']'
    
    def get_text(self):
        text = ''
        for child in self.get_children():
            txt = child.get_text()
            if txt:
                text += txt
        return text
    
class NamespaceBlock(BlockStatement):
    header = 'namespace'
    begin = Any()
    end = CurlyBracketedBlock
    
class ClassBlock(BlockStatement):
    header = Seq(Or('public', 'protected', 'private'), Optional(Or('static', 'abstract')), 'class')
    begin = Any()
    end = CurlyBracketedBlock
    
class MemberBlock(BlockStatement):
    header = Seq(Or('public', 'protected', 'private'), Optional('async'), Optional(Or('static', 'override')), Any())
    begin = Any()
    end = Or(CurlyBracketedBlock, ';')
    
class NewAnonymous(Term):
    match = Seq('new', CurlyBracketedBlock)
    
def parse(text):

    if not type(text) is str:
        text = text.read()
        
    parser = Parser(CSharpLexer, [ParenthesedBlock, CurlyBracketedBlock, BracketedBlock], [NamespaceBlock, ClassBlock, MemberBlock, NewAnonymous])
    return parser.parse(text)    

def process(interpreter, text):
    
    classes = []
    classAttributes = []
    for statement in parse(text):
        if isinstance(statement, ClassBlock):
            cl = parse_class(interpreter, statement, classAttributes)
            if cl:
                classes.append(cl)
            classAttributes.clear()
        elif isinstance(statement, NamespaceBlock):
            cls = parse_namespace(interpreter, statement)
            if cls:
                classes.extend(cls)
        elif is_token_attribute(statement):
            classAttributes.append(statement)
        else:
            classAttributes.clear()
    return classes

def process_statements(interpreter, tokens):
    
    anyStatementTokens = []
    classAttributes = []
    for token in tokens:
        if isinstance(token, ClassBlock):
            parse_class(interpreter, token, classAttributes)
            classAttributes.clear()
        elif isinstance(token, Token) and token.text == ';':
            if anyStatementTokens:
                parse_any_statement(interpreter, anyStatementTokens)
            anyStatementTokens = []
        elif is_token_attribute(token):
            classAttributes.append(token)
        else:
            classAttributes.clear()
            if isinstance(token, CurlyBracketedBlock):
                block = process_statements_block(interpreter, token)
                anyStatementTokens.append(block)
            elif not isinstance(token, Token) or not token.text == '{':
                anyStatementTokens.append(token)

def process_statements_block(interpreter, astBlock):
    
    interpreter.start_block(astBlock)
    process_statements(interpreter, astBlock.get_children())
    interpreter.end_block()

def parse_any_statement(interpreter, tokens):
    astTokens = []
    for token in tokens:
        if isinstance(token, ParenthesedBlock):
            lst = parse_parenthesed_list(interpreter, token)
            astTokens.append(lst)
        else:
            astTokens.append(token)
    interpreter.add_any_statement(astTokens)

def parse_parenthesed_list(interpreter, parenthesedToken):
    lst = interpreter.start_parenthesed_list(parenthesedToken)
    firstToken = True   # firstToken is (
    expressionTokens = []
    for token in parenthesedToken.get_children():
        if firstToken:
            firstToken = False
            continue
        if isinstance(token, Token) and token.text in [',', ')']:
            expr = parse_expression(interpreter, expressionTokens)
            interpreter.add_element(expr)
            expressionTokens = []
        else:
            expressionTokens.append(token)
    interpreter.end_parenthesed_list()
    return lst

def parse_new_anonymous_expression(interpreter, newToken):
    lst = interpreter.start_new_anonymous_expression(newToken)
    firstToken = True   # firstToken is (
    expressionTokens = []
    parenthesedList = list(newToken.get_children())[-1]
    for token in parenthesedList.get_children():
        if firstToken:
            firstToken = False
            continue
        if isinstance(token, Token) and token.text in [',', ')']:
            expr = parse_expression(interpreter, expressionTokens)
            interpreter.add_element(expr)
            expressionTokens = []
        else:
            expressionTokens.append(token)
    interpreter.end_new_anonymous_expression()
    return lst

def parse_expression(interpreter, tokens):

    if len(tokens) == 0:
        return None
    
    if len(tokens) == 1:
        if isinstance(tokens[0], NewAnonymous):
            expr = parse_new_anonymous_expression(interpreter, tokens[0])
            return expr
        else:
            return tokens[0]
    
    if tokens[1].text == ':':
        expr = interpreter.start_assignment_expression(tokens)
        interpreter.set_left_operand(tokens[0])
        expr2 = parse_expression(interpreter, tokens[2:])
        interpreter.set_right_operand(expr2)
        interpreter.end_assignment_expression()
    elif tokens[1].text == '=':
        expr = interpreter.start_equality_expression(tokens)
        interpreter.set_left_operand(tokens[0])
        expr2 = parse_expression(interpreter, tokens[2:])
        interpreter.set_right_operand(expr2)
        interpreter.end_equality_expression()
    else:
        expr = interpreter.start_expression(tokens)
        for token in tokens:
            if isinstance(token, ParenthesedBlock):
                lst = parse_parenthesed_list(interpreter, token)
                interpreter.add_element(lst)
            else:
                interpreter.add_element(token)
        interpreter.end_expression()
    return expr

def analyse(text, file):
    interpreter = CSharpInterpreter(file)
    classes = process(interpreter, text);
    return classes

def is_token_name(token):
    try:
        if is_token_subtype(token.type, Name):
            return True
    except:
        pass
    return False

# def is_token_function(token):
#     try:
#         if is_token_subtype(token.type, Name.Function):
#             return True
#     except:
#         pass
#     return False

def is_token_attribute(token):
    try:
        if isinstance(token, BracketedBlock):
            return True
#         if is_token_subtype(token.type, Name.Attribute):
#             return True
    except:
        pass
    return False

def is_token_keyword(token):
    try:
        if is_token_subtype(token.type, Keyword):
            return True
    except:
        pass
    return False

def get_token_text(token):
    try:
        return token.text
    except:
        ''
    
def parse_namespace(interpreter, namespaceBlock):

    classes = []
    for token in namespaceBlock.get_body():
        if isinstance(token, CurlyBracketedBlock):
            classes = parse_namespace_body(interpreter, token)
        elif isinstance(token, NamespaceBlock):
            cls = parse_namespace(interpreter, token)
            if cls:
                classes.extend(cls)
    return classes

def parse_namespace_body(interpreter, body):

    classes = []
    classAttributes = []
    for token in body.get_children():
        if isinstance(token, ClassBlock):
            cl = parse_class(interpreter, token, classAttributes)
            if cl:
                classes.append(cl)
            classAttributes.clear()
        elif is_token_attribute(token):
            classAttributes.append(token)
        else:
            classAttributes.clear()
    return classes
    
def parse_class(interpreter, classBlock, classAttributes):

    cl = None
    afterDbPoint = False
    for token in classBlock.get_body():
        if not cl:
            if is_token_name(token):
                cl = interpreter.start_class(token.text, classBlock)
                if cl:
                    for attribute in classAttributes:
                        interpreter.add_attribute(attribute, None)
        else:
            text = get_token_text(token)
            if afterDbPoint:
                if is_token_name(token):
                    cl.add_inheritance(token.text)
            else:
                if text == ':':
                    afterDbPoint = True
            if isinstance(token, CurlyBracketedBlock):
                parse_class_body(interpreter, token)
    if cl:
        interpreter.end_class()
    return cl
    
def parse_class_body(interpreter, tokenBlock):

    methodAttributes = []
    for token in tokenBlock.get_children():        
        if isinstance(token, MemberBlock):
            parse_member(interpreter, token, methodAttributes)
            methodAttributes.clear()
        elif is_token_attribute(token):
            methodAttributes.append(token)
        else:
            methodAttributes.clear()
    
def parse_member(interpreter, memberBlock, methodAttributes):

    method = None
    lastTokenBeforeFunction = None
    beforeLastTokenBeforeFunction = None
    accessibility = None
    beforeDbPoint = True
    for token in memberBlock.get_header():
        try:
            if not accessibility and token.text in ['public', 'protected', 'private']:
                accessibility = token.text
        except:
            pass
        if is_token_name(token):
            if lastTokenBeforeFunction:
                beforeLastTokenBeforeFunction = lastTokenBeforeFunction
            lastTokenBeforeFunction = token
            
    for token in memberBlock.get_body():
                
        if beforeDbPoint and isinstance(token, ParenthesedBlock):
            method = interpreter.start_method(lastTokenBeforeFunction.text, beforeLastTokenBeforeFunction.text if beforeLastTokenBeforeFunction else None, accessibility, memberBlock)
        elif isinstance(token, CurlyBracketedBlock):
            process_statements(interpreter, token.get_children())
        elif isinstance(token, Token):
            if token.text == '=':
                break
            elif beforeDbPoint and token.text == ':':
                beforeDbPoint = False
            
        if is_token_name(token):
            if lastTokenBeforeFunction:
                beforeLastTokenBeforeFunction = lastTokenBeforeFunction
            lastTokenBeforeFunction = token
    if method:
        for attribute in methodAttributes:
            interpreter.add_attribute(attribute, None)
        interpreter.end_method()
    return method
    