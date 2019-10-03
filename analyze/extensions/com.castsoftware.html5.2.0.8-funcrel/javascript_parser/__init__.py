from pygments.filter import Filter
from pygments.token import is_token_subtype, String, Name, Text, Keyword, Punctuation, Operator, Literal, Error, Comment
from javascript_parser.javascript_lexer import JavascriptLexer
from javascript_parser.light_parser import Parser, Statement, BlockStatement, Token, Seq, TokenIterator, Lookahead, Any, Optional, Or, Term, Node, Not
from javascript_parser.symbols import Identifier, BracketedIdentifier, Function, AstString, ObjectValue, GlobalFunction, GlobalVariable, HtmlContent, AstOperator, OrExpression, Violations, AstToken, FunctionCall, Module
from javascript_parser.diags_parser import process_diags
from cast.application import open_source_file # @UnresolvedImport
from cast.analysers import Bookmark
import cast.analysers.ua
from inspect import isclass
from javascript_parser.javascript_interpreter import JavascriptInterpreter
from javascript_parser.flow_preprocessor import preprocess
import os
import json
import traceback
from collections import OrderedDict

LAST_TOKEN_PARSED_TO_NONE = None

class PositionFilter(Filter):
    """
    Filter that add position to tokens.
    """
    def __init__(self, emptyLines):
        
        self.column = 1 
        self.line = 1
        self.emptyLines = emptyLines
        
    def filter(self, lexer, stream):
        
        nbRet = 0
        isComment = False
        
        for token in stream:
        
            if not isComment and nbRet > 1:
                try:
                    self.emptyLines[self.line - (nbRet - 1)] = nbRet-1
                except:
                    pass
    
            isComment = isinstance(token, Token) and is_token_subtype(token.type, Comment)
            
            end_line, end_column, nbRet = self.get_end_position(token.get_text(), isComment)
            
            new_token = token
                
            new_token.begin_line = self.line
            new_token.begin_column = self.column
            new_token.end_line = end_line
            new_token.end_column = end_column
            
            self.line = end_line
            self.column = end_column
            
            yield new_token
    
    def get_end_position(self, text, isComment):
        
        end_line = self.line
        end_column = self.column
        
        nbRet = 0
        
        for c in text:
            
            if c == '\n':
                end_line += 1
                end_column = 1
                nbRet += 1
            else:
                end_column += 1
                        
        return end_line, end_column, nbRet

class CurlyBracketedBlock(BlockStatement):
    
    begin = '{'
    end   = '}'

    def get_body_comments(self):
        """Get the body comments"""
        result = []
        body = False
        body_index = self.header_comments_length+self.header_length
         
        for token in self.children[body_index:]:
            if type(token) is Token:
                if token.is_comment() and body:
                    result.append(token)
                if not token.is_whitespace() and not token.is_comment():
                    body = True
            if isinstance(token, MethodBlock):
                pass
            elif isinstance(token, Node):
                result += token.get_body_comments()
        return result

class ParenthesedBlock(BlockStatement):
    
    begin = '('
    end   = ')'
    
    def is_parenthesed_block(self):
        return True
    
class BracketedBlock(BlockStatement):
    
    begin = '['
    end   = ']'

class FunctionBlock(Term):
      
    match = Or(Seq(Optional('export'), Optional('default'), Optional('async'), 'function', Optional('*'), Any(), ParenthesedBlock, CurlyBracketedBlock), Seq(Optional('export'), Optional('default'), Optional('async'), 'function', ParenthesedBlock, CurlyBracketedBlock))

class ArrowFunctionBlock(Term):
      
    match = Or(Seq(Optional('async'), ParenthesedBlock, '=>', CurlyBracketedBlock), Seq(Any(), '=>', CurlyBracketedBlock))

class NewFunctionBlock(Term):   # new Function(param1, param2, ..., code);
      
    match = Seq('new', 'function', ParenthesedBlock, Optional(CurlyBracketedBlock))

class MethodBlock(Term):
      
    match = Or(Seq(Or(Name, 'delete'), ParenthesedBlock, CurlyBracketedBlock), Seq(Or('get', 'set', 'static'), Or(Name, 'delete'), ParenthesedBlock, CurlyBracketedBlock))
        
def get_comments_whole_line_count(tok, comments = None):
        nb = 0
        lastNotNullTokenLine = -1
        for token in tok.children:
            if is_token_subtype(token.type, Comment):
                if token.begin_line > lastNotNullTokenLine:
                    if comments != None:
                        comments.append(token)
                    if is_token_subtype(token.type, Comment.Single):
                        nb += 1
                    else:
                        nb += ( token.text.count('\n') + 1 )
            elif isinstance(token, Token):
                txt = token.text.strip(' \n\t')
                if txt:
                    lastNotNullTokenLine = token.end_line
            else:
                nb += get_comments_whole_line_count(token, comments)
        return nb

class FileBlock(BlockStatement):
     
    def get_header_comments(self):
        
        comments = []
        for token in self.children:
            if is_token_subtype(token.type, Comment):
                comments.append(token)
            else:
                break
        return comments
     
    def get_body_comments(self):
        
        comments = []
        inHeader = True
        for token in self.children:
            if inHeader and is_token_subtype(token.type, Comment):
                continue
            inHeader = False
            if is_token_subtype(token.type, Comment):
                comments.append(token)
        return comments
    
    def get_comments_in_node_children(self, node, comments):

        try:
            for token in node.children:
                if isinstance(token, FunctionBlock):
                    self.get_comments_in_node_children(token.children[-1], comments)
                elif is_token_subtype(token.type, Comment):
                    comments.append(token)
                else:
                    self.get_comments_in_node_children(token, comments)
        except:
            pass
        
    def get_body_comments_line_count(self, includingFunctionHeaders = False):

        comments = []
        
        inHeader = True
        for token in self.children:
            if inHeader and is_token_subtype(token.type, Comment):
                continue
            inHeader = False
            if includingFunctionHeaders and isinstance(token, FunctionBlock):
                headerComments = token.get_header_comments()
                if headerComments:
                    comments.extend(headerComments)
                bodyComments = token.get_body_comments()
                if bodyComments:
                    comments.extend(bodyComments)
            elif is_token_subtype(token.type, Comment):
                comments.append(token)
            else:
                self.get_comments_in_node_children(token, comments)

        s = ''
        for comment in comments:
            s += comment.text
            if s.endswith('*/'):
                s += '\n'

        ret = s.count('\n')
        return ret
        
    def get_comments_whole_line_count(self, comments = None):
        return get_comments_whole_line_count(self, comments)
    
class ClassBlock(Term):
     
    match = Or(Seq(Optional('export'),Optional('default'),'class', Any(), 'extends', Any(), Optional(Seq('.', Any(), Optional(Seq('.', Any())))), Optional(ParenthesedBlock), CurlyBracketedBlock), Seq(Optional('export'),Optional('default'),'class', Any(), Optional(ParenthesedBlock), CurlyBracketedBlock))

    def get_body_comments(self):
        """Get the body comments"""
        result = []
        body = False
        body_index = self.header_comments_length+self.header_length
         
        for token in self.children[body_index:]:
            if type(token) is Token:
                if token.is_comment() and body:
                    result.append(token)
                if not token.is_whitespace() and not token.is_comment():
                    body = True
            if isinstance(token, MethodBlock):
                pass
            elif isinstance(token, Node):
                result += token.get_body_comments()
        return result

class NewStatement(Statement):
    
    begin = 'new'
    end   = ')'
            
    def create_bookmark(self, _file):
        
        t1 = self.tokens[0]
        t2 = self.tokens[-1]
        
        return Bookmark(_file, t1.get_begin_line(), t1.get_begin_column(), t2.get_end_line(), t2.get_end_column())

class ObjectTypes:
    
    def __init__(self, sourceCodeType = 'CAST_HTML5_JavaScript_SourceCode', jsxSourceCodeType = 'CAST_HTML5_JSX_SourceCode', functionType = 'CAST_HTML5_JavaScript_Function', classType = 'CAST_HTML5_JavaScript_Class', methodType = 'CAST_HTML5_JavaScript_Method', constructorType = 'CAST_HTML5_JavaScript_Constructor', htmlFragmentType = 'CAST_HTML5_HTML_Fragment'):
        self.sourceCodeType = sourceCodeType
        self.jsxSourceCodeType = jsxSourceCodeType
        self.functionType = functionType
        self.classType = classType
        self.methodType = methodType
        self.constructorType = constructorType
        self.webSocketType = 'CAST_HTML5_WebSocketService'
        self.getXMLHttpRequestType = 'CAST_HTML5_GetXMLHttpRequestService'
        self.postXMLHttpRequestType = 'CAST_HTML5_PostXMLHttpRequestService'
        self.updateXMLHttpRequestType = 'CAST_HTML5_UpdateXMLHttpRequestService'
        self.deleteXMLHttpRequestType = 'CAST_HTML5_DeleteXMLHttpRequestService'
        self.getHttpRequestType = 'CAST_HTML5_GetHttpRequestService'
        self.postHttpRequestType = 'CAST_HTML5_PostHttpRequestService'
        self.putHttpRequestType = 'CAST_HTML5_PutHttpRequestService'
        self.deleteHttpRequestType = 'CAST_HTML5_DeleteHttpRequestService'
        self.getEventSourceType = 'CAST_HTML5_GetEventSourceService'
        self.htmlFragmentType = htmlFragmentType

class AnalyzerConfiguration:

    def __init__(self, objectTypes):
        
        self.objectTypes = objectTypes
        self.functionCallThroughParametersIdentifiers = []    
        self.functionCallWithAreLoops = []
        self.violations = Violations()
  
        jsonPath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.json'))
        self.functionCallThroughParametersIdentifiers = []
        self.config = json.loads(open_source_file(jsonPath).read())
        for functionCallThroughParameters in self.config['functionCallsThroughParameters']:
            if 'identifierFullname' in functionCallThroughParameters:
                self.functionCallThroughParametersIdentifiers.append(functionCallThroughParameters['identifierFullname'])
            else:
                self.functionCallThroughParametersIdentifiers.append(functionCallThroughParameters['identifierName'])
            if 'isLoop' in functionCallThroughParameters and functionCallThroughParameters['isLoop'] == 'true' :
                if 'identifierFullname' in functionCallThroughParameters:
                    self.functionCallWithAreLoops.append(functionCallThroughParameters['identifierFullname'])
                else:
                    self.functionCallWithAreLoops.append(functionCallThroughParameters['identifierName'])
    
    def clean(self):
        
        self.violations = Violations()

def parse(text, emptyLines, lexer = None):

    if not type(text) is str:
        text = text.read()
        
    if lexer:
        parser = Parser(lexer, [ParenthesedBlock, CurlyBracketedBlock, BracketedBlock], [FunctionBlock, NewFunctionBlock, ClassBlock, MethodBlock])
    else:
        parser = Parser(JavascriptLexer, [ParenthesedBlock, CurlyBracketedBlock, BracketedBlock], [FunctionBlock, NewFunctionBlock, ClassBlock, MethodBlock])

    parser.lexer.add_filter(PositionFilter(emptyLines))

    return parser.parse(text)

def process(interpreter, text, lexer, firstRow, firstCol, bFullAnalysis = True):
    
    statements = []
    jsContent = interpreter.start_js_content(interpreter.parent, text, firstRow, firstCol, interpreter.jsContent)
    jsContent.objectDatabaseProperties.checksum = 0
    emptyLines = OrderedDict()
    interpreter.emptyLines = emptyLines
    for statement in parse(text, emptyLines, lexer):
        statements.append(statement)

    if not bFullAnalysis:
        firstRealToken = 0
        lastRealToken = 0
        for token in statements:
            if isinstance(token, Token) and is_token_subtype(token.type, Text) and not token.get_text().strip():
                firstRealToken += 1
            else:
                break
        for token in reversed(statements):
            if isinstance(token, Token) and is_token_subtype(token.type, Text) and not token.get_text().strip():
                lastRealToken += 1
            else:
                break
        
        jsContentAst = FileBlock()
        try:
            if lastRealToken == 0:
                interpreter.set_jscontent_ast(statements[firstRealToken:], jsContentAst)
            else:
                interpreter.set_jscontent_ast(statements[firstRealToken:-lastRealToken], jsContentAst)
            if not bFullAnalysis:
                jsContent.add_bookmark(Bookmark(interpreter.file, jsContent.get_begin_line(), jsContent.get_begin_column(), jsContent.get_end_line(), jsContent.get_end_column()))
        except:
            interpreter.set_jscontent_ast([], jsContentAst)

    if not bFullAnalysis:
        moduleStatements, bracketedBlockTokens, funcParamsTokens, moduleLastLine, isSapDefine = get_module_statements(statements, interpreter)
        if moduleStatements:
            jsContent.module = Module()
            jsContent.module.lastLine = moduleLastLine
            jsContent.module.isSapModule = isSapDefine
            paramRefs = []
            for value in bracketedBlockTokens:
                try:
                    if isinstance(value, Token) and value.get_text() != ',':
                        paramRefs.append(value.get_text()[1:-1])
                except:
                    pass
            params = []
            for value in funcParamsTokens:
                try:
                    if isinstance(value, Token) and value.get_text() != ',':
                        params.append(value.get_text())
                except:
                    pass
            if len(paramRefs) >= len(params):
                if len(paramRefs) > len(params):
                    cast.analysers.log.info('Parameters number mismatch in module define([...], function(...) {...})')
                cmpt = 0
                for param in params:
                    interpreter.add_module_parameter(param, paramRefs[cmpt])
                    cmpt += 1
            else:
                cast.analysers.log.info('Parameters number mismatch in module define([...], function(...) {...})')

            parse_statements(interpreter, moduleStatements, interpreter.file, bFullAnalysis)
        else:
            parse_statements(interpreter, statements, interpreter.file, bFullAnalysis)
    else:
        parse_statements(interpreter, statements, interpreter.file, bFullAnalysis)
    
    interpreter.end_js_content()
    
    return jsContent

def get_module_statements(statements, interpreter):
    tokens = Lookahead(TokenIterator(statements))
    token = get_next_token(tokens)
    isDefine = False
    isSapDefine = False
    children = None
    moduleLastLine = -1
    otherStatements= []
    while token:
        if not isDefine:
            if isinstance(token, Identifier) and token.get_name() == 'define':
                isDefine = True
                if token.get_fullname() == 'sap.ui.define':
                    isSapDefine = True
                token = get_next_token(tokens)
                continue
            break
        if isinstance(token, ParenthesedBlock):
            children = list(token.get_children())[1:-1]
            try:
                if isinstance(children[-1], FunctionBlock) and isinstance(children[-3], BracketedBlock):
                    isDefine = True
                else:
                    isDefine = False
                token = get_next_token(tokens)
                continue
            except:
                isDefine = False
                break
        else:
            if children == None:
                isDefine = False
                break
            else:
                if moduleLastLine == -1:
                    moduleLastLine = token.get_begin_line() - 1
                otherStatements.append(token)
        token = get_next_token(tokens)
        
    if not isDefine:
        return None, None, None, 0, False
    bracketedBlockTokens = list(list(children[-3].get_body()))[1:-1]
    funcParamsTokens = list(list(children[-1].get_body())[1].get_children())[1:-1]
    ret = list(list(children[-1].get_body())[-1].get_children())[1:-1]
    ret.extend(otherStatements)
    return ret, bracketedBlockTokens, funcParamsTokens, moduleLastLine, isSapDefine

def analyse_preprocess(interpreter, text, lexer, firstRow = 1, firstCol = 1):
    flowPresent = True if '/* @flow */' in text else False
    if flowPresent:
        text = preprocess(text)
    return process(interpreter, text, lexer, firstRow, firstCol, False)

def analyse_fullprocess(interpreter, text, lexer, firstRow = 1, firstCol = 1):
    flowPresent = True if '/* @flow */' in text else False
    if flowPresent:
        text = preprocess(text)
    jsContent = process(interpreter, text, lexer, firstRow, firstCol, True)
    return jsContent

def analyse_process_diags(jsContent, globalClassesByName, firstRow = 1, firstCol = 1):
    process_diags(jsContent, jsContent.file, jsContent.config.violations, globalClassesByName, firstRow, firstCol)

def analyse(text, file, config, lexer, firstRow = 1, firstCol = 1, jsContentsByFilename = {}, globalVariablesByName = {}, globalFunctionsByName = {}, globalClassesByName = {}, jsContent = None, htmlContentsByJS = {}, resolve = True):
    interpreter = JavascriptInterpreter(file, config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, jsContent, False, htmlContentsByJS, None, resolve)
    jsContent = analyse_preprocess(interpreter, text, lexer, firstRow, firstCol);
    interpreter = JavascriptInterpreter(file, jsContent.config, jsContentsByFilename, globalVariablesByName, globalFunctionsByName, globalClassesByName, jsContent, True, htmlContentsByJS, None, resolve)
    return analyse_fullprocess(interpreter, text, lexer, firstRow, firstCol);

def parse_import_statement(interpreter, phrase, bFullParsing):
    
    if not bFullParsing:
        return
    
    tokens = Lookahead(TokenIterator(phrase))
    
    get_next_token(tokens)
    token = tokens.look_next()
    isType = False
    if isinstance(token, Token) and token.text == 'type':
        get_next_token(tokens)
        token = tokens.look_next()
        isType = True
    stmt = interpreter.start_import_statement(token, isType)
    
    if isinstance(token, CurlyBracketedBlock):
        token = get_next_token(tokens)
        children = token.get_children()
        get_next_token(children)
        token = get_next_token(children)
        while token:
            try:
                nextToken = children.look_next()
            except:
                break
            _as = None
            if isinstance(nextToken, Token) and nextToken.text == 'as':
                get_next_token(children)
                _as = get_next_token(children)
            if isinstance(token, Token) and token.text in [',', '}']:
                token = get_next_token(children)
                continue
            else:
                stmt.add_what(token, _as)
                token = get_next_token(children)
    else:
        token = parse_next_token(interpreter, tokens, bFullParsing)
        nextToken = tokens.look_next()
        _as = None
        if isinstance(nextToken, Token) and nextToken.text == 'as':
            get_next_token(tokens)
            _as = get_next_token(tokens)
        stmt.add_what(token, _as)
        
    token = get_next_token(tokens)
    
    try:
        while token and (not isinstance(token, Token) or token.text != 'from'):
            token = get_next_token(tokens)
    except:
        pass
    token = parse_next_token(interpreter, tokens, bFullParsing)
    stmt.set_from(token)
    
    interpreter.end_import_statement()

def parse_any_statement(interpreter, tokens, bFullParsing, leftOperandAssignment = None):
    
    next2Tokens = look_next_tokens(tokens, 2)
    isReturnOv = False
    if len(next2Tokens) == 2 and next2Tokens[0].get_text() == 'return' and isinstance(next2Tokens[1], CurlyBracketedBlock):
        isReturnOv = True
    token = get_next_token(tokens)
    if token.get_text():
        firstTokenName = token.get_text().upper()
    else:
        firstTokenName = None
    # in case of var v = (function() { return { f : function() {} };}(); 
    # light parsing must be done to keep functions for global resolution
    if bFullParsing or isReturnOv:
        stmt = interpreter.start_any_statement(token, isReturnOv, bFullParsing)
        tok = token
        while tok:
            result = parse_token(interpreter, tok, tokens, leftOperandAssignment, bFullParsing, None, Identifier(None, firstTokenName))
            if result:
                stmt.add_element(result)
            tok = get_next_token(tokens)
        interpreter.end_any_statement()

def build_expression(interpreter, tokenList, anyExpr = False, bFullParsing = True):

    l = len(tokenList)
    if l == 0:
        return None
    if l == 1:
        if (isinstance(tokenList[0], Token) and is_token_subtype(tokenList[0].type, String)):
            expr = AstString(tokenList[0], None, tokenList[0].get_text())
            interpreter.add_string(expr)
        else:
            expr = interpreter.add_simple_expression(tokenList[0])
        return expr
    if l == 2:
        try:
            if isinstance(tokenList[0].tokens[0], ParenthesedBlock) and isinstance(tokenList[1].tokens[0], ParenthesedBlock):
                lst = [ tokenList[0].tokens[0], tokenList[1].tokens[0] ]
                tokens = Lookahead(TokenIterator(lst))
                expr = parse_js_function_call(interpreter, tokens, bFullParsing, True)
                return expr
        except:
            pass

    if anyExpr:
        expression = interpreter.start_any_expression(None)
        for token in tokenList:
            interpreter.add_any_expression_item(token)
        interpreter.end_any_expression()
        return expression

    firstOperator = None
    secondOperator = None
    for token in tokenList:
        if firstOperator and secondOperator:
            break
        isOperator = False
        try:
            isOperator = token.is_operator()
        except:
            isOperator = False
        if isOperator:
            if not firstOperator:
                firstOperator = token
            else:
                secondOperator = token
                
    tokensBeforeOperator = []
    tokensAfterOperator = []
    tokensAfterNextOperator = []
    operatorToken = None
    
    if firstOperator and (firstOperator.get_text() == '?' or (firstOperator.get_text().startswith(('!', '=')) and not firstOperator.get_text() == '=>' and secondOperator and secondOperator.get_text() == '?')) :
        nextOperatorToken = None
        for token in tokenList:
            isOperator = False
            try:
                isOperator = token.is_operator()
            except:
                isOperator = False
                
            if isOperator:
                if not operatorToken:
                    if token.get_text() == '?':
                        operatorToken = token
                    else:
                        tokensBeforeOperator.append(token)
                else:
                    if not nextOperatorToken:
                        if token.get_text() == ':':
                            nextOperatorToken = token
                        else:
                            tokensAfterOperator.append(token)
                    else:
                        tokensAfterNextOperator.append(token)
            else: # not operator
                if not operatorToken:
                    tokensBeforeOperator.append(token)
                else:
                    if not nextOperatorToken:
                        tokensAfterOperator.append(token)
                    else:
                        tokensAfterNextOperator.append(token)

    else:    # not ternary    
        for token in tokenList:
            isOperator = False
            try:
                isOperator = token.is_operator()
            except:
                isOperator = False
                
            if token and not isOperator:
                if not operatorToken:
                    tokensBeforeOperator.append(token)
                else:
                    tokensAfterOperator.append(token)
            elif not operatorToken:
                operatorToken = token
            else:
                tokensAfterOperator.append(token)
    
    if operatorToken:
        operatorText = operatorToken.get_text()
        if tokensBeforeOperator:
            if operatorText in ['+', '+=']:
                expression = None
                if operatorText == '+':
                    expression = interpreter.start_addition(tokenList, False, bFullParsing)
                if bFullParsing:
                    interpreter.start_left_operand()
                    build_expression(interpreter, tokensBeforeOperator)
                    interpreter.end_left_operand()
                    interpreter.start_right_operand()
                    build_expression(interpreter, tokensAfterOperator)
                    interpreter.end_right_operand()
                if operatorText == '+':
                    interpreter.end_addition()
                return expression
            elif operatorText == '||':
                expression = interpreter.start_or(tokenList)
                interpreter.start_left_operand()
                build_expression(interpreter, tokensBeforeOperator)
                interpreter.end_left_operand()
                interpreter.start_right_operand()
                build_expression(interpreter, tokensAfterOperator)
                interpreter.end_right_operand()
                interpreter.end_or()
                return expression
            elif operatorText == 'in':
                expression = interpreter.start_in(tokenList)
                interpreter.start_left_operand()
                build_expression(interpreter, tokensBeforeOperator)
                interpreter.end_left_operand()
                interpreter.start_right_operand()
                build_expression(interpreter, tokensAfterOperator)
                interpreter.end_right_operand()
                interpreter.end_in()
                return expression
            elif operatorText == '?':
                expression = interpreter.start_if_ternary_expression(tokenList)
                interpreter.start_if_operand()
                build_expression(interpreter, tokensBeforeOperator)
                interpreter.end_if_operand()
                interpreter.start_then_operand()
                build_expression(interpreter, tokensAfterOperator)
                interpreter.end_then_operand()
                interpreter.start_else_operand()
                build_expression(interpreter, tokensAfterNextOperator)
                interpreter.end_else_operand()
                interpreter.end_if_ternary_expression()
                return expression
            elif operatorText == '=>':
                function = parse_arrow_function(interpreter, None, tokenList, False, None, bFullParsing, None)
                return function
            else:
                expression = interpreter.start_binary_expression(operatorToken, tokenList)
                interpreter.start_left_operand()
                build_expression(interpreter, tokensBeforeOperator)
                interpreter.end_left_operand()
                interpreter.start_right_operand()
                build_expression(interpreter, tokensAfterOperator)
                interpreter.end_right_operand()
                interpreter.end_binary_expression()
                return expression
        else:
            if operatorText == '!':
                expression = interpreter.start_not_expression(tokenList)
                build_expression(interpreter, tokensAfterOperator)
                interpreter.end_not_expression()
            else:
                expression = interpreter.start_unary_expression(tokenList)
                build_expression(interpreter, tokensAfterOperator)
                interpreter.end_unary_expression()
            return expression
    else:
        expression = interpreter.start_any_expression(None)
        for tok in tokenList:
            interpreter.add_any_expression_item(tok)
        interpreter.end_any_expression()
        return expression

def finish_bracketed_identifier(interpreter, token, bFullParsing):

    try:
        if bFullParsing and token.is_bracketed_identifier() and token.get_bracketed_expression():
            children = token.bracketedExpression.get_children()
            next(children)
            expr = parse_expression(interpreter, children, bFullParsing)
            expr.parent = token
            token.bracketedExpression = expr
            b = token.evaluate_identifier()
            if not b:
                interpreter.bracketedIdentifiersToEvaluate.append(token)
    except:
        pass
    
def parse_any_expression(interpreter, tokens, leftOperandAssignment, bFullParsing, lightObject, functionNameIdentifier = None):
    
    token = get_next_token(tokens)
    finish_bracketed_identifier(interpreter, token, bFullParsing)

    tokenList = []
    
    tok = token
    isFuncCall = False
    while tok:
        result = parse_token(interpreter, tok, tokens, leftOperandAssignment, bFullParsing, lightObject, functionNameIdentifier)
        if result:
            try:
                if result.is_function_call() and functionNameIdentifier and functionNameIdentifier.get_fullname() == 'module.exports' and 'module.exports' in interpreter.jsContent.moduleExports:
                    if not isinstance(token, Token) or token.text != 'new':
                        oldResult = result
                        result = interpreter.jsContent.moduleExports['module.exports']
                        result.copy_from(oldResult)
            except:
                pass
            if not isFuncCall or not isinstance(tok, ParenthesedBlock):
                tokenList.append(result)
            if result.is_function_call():
                isFuncCall = True
            else:
                isFuncCall = False
        tok = get_next_token(tokens)
        if tok:
            finish_bracketed_identifier(interpreter, tok, bFullParsing)
    
    expr = interpreter.start_any_expression(token)
    build_expression(interpreter, tokenList)
    interpreter.end_any_expression()
    
    return expr

def token_is_arrow(token):
    
    try:
        if isinstance(token, Token) and is_token_subtype(token.type, Operator) and token.get_text() == '=>':
            return True
        else:
            return False
    except:
        return False
    
# a = b;
# var a = b;
def parse_assignment(interpreter, identifier, tokens, isVar, bFullParsing, exported = False):
    
    assignment = None
    assignmentRightOperand = None
    b = False
    fcall = None
    isFuncCall = False
    isObjectDestructuration = False
    try:
        isFuncCall = identifier.is_func_call()
    except:
        pass
    if isinstance(identifier, CurlyBracketedBlock):
        isObjectDestructuration = True
    if bFullParsing:
        if isFuncCall:
            token = tokens.look_next()
            fcall = parse_function_call(interpreter, identifier, token, tokens, bFullParsing, False)
            assignment = interpreter.start_assignment(isVar, fcall, exported)
        else:
            assignment = interpreter.start_assignment(isVar, identifier, exported)
    else:
        b = interpreter.start_assignment(isVar, identifier, exported)
    
    if True:
        leftOperand = None
        if bFullParsing:
            leftOperand = assignment.leftOperand
            assignmentRightOperand = assignment.rightOperand
        isModuleExports = False
        if not leftOperand:
            if isFuncCall:
                leftOperand = fcall
            elif isObjectDestructuration:
                leftOperand = parse_object_destructuration(interpreter, identifier, tokens, bFullParsing, None)
            else:
                leftOperand = identifier
                try:
                    if leftOperand.get_fullname().startswith('module.exports'):
                        isModuleExports = True
                except:
                    pass
            if bFullParsing:
                interpreter.set_left_operand(leftOperand)
                if not fcall:
                    gvars = None
                    try:
                        gvars = interpreter.get_global_variables(identifier.get_fullname())
                    except:
                        pass
                    if not gvars:
                        if not isObjectDestructuration:
                            interpreter.add_identifier(identifier, False)
                    else:
                        interpreter.add_identifier(gvars[0].identifier, False)
            elif b and not fcall:
                interpreter.add_global(leftOperand, isVar)
        else:
            try:
                if leftOperand.is_bracketed_identifier():
                    finish_bracketed_identifier(interpreter, leftOperand, True)
            except:
                pass

            interpreter.update_left_operand()
            if bFullParsing and not fcall:
                interpreter.add_identifier(leftOperand, False)
            
        if not fcall:
            token = get_next_token(tokens)
        finish_bracketed_identifier(interpreter, token, bFullParsing)
        nextTokens = look_next_tokens(tokens, 4)
        # case of a = module.exports = ...
        try:
            if len(nextTokens) == 4 and nextTokens[-1].text == '=' and nextTokens[0].text + nextTokens[1].text + nextTokens[2].text == 'module.exports':
                isModuleExports = True
                token = get_next_token(tokens)
                token = get_next_token(tokens)
                nextTokens = look_next_tokens(tokens, 3)
        except:
            pass
        nextToken = nextTokens[0]
        if isinstance(nextToken, FunctionBlock):
            funcDirectlyCalled = False
            if len(nextTokens) >= 2 and isinstance(nextTokens[1], ParenthesedBlock):
                funcDirectlyCalled = True
            rightOperand = parse_function(interpreter, leftOperand, nextToken, False, None, bFullParsing, assignmentRightOperand, funcDirectlyCalled)
            if bFullParsing:
                interpreter.set_right_operand(rightOperand)
        elif isinstance(nextToken, NewFunctionBlock):
            funcDirectlyCalled = False
            rightOperand = parse_function(interpreter, leftOperand, nextToken, False, None, bFullParsing, assignmentRightOperand, funcDirectlyCalled)
            if bFullParsing:
                rightOperand.set_function_constructor()
                interpreter.set_right_operand(rightOperand)
        elif (len(nextTokens) >= 2 and token_is_arrow(nextTokens[1])) or (((isinstance(nextTokens[0], Token) and nextTokens[0].text == 'async') or (isinstance(nextTokens[0], Identifier) and nextTokens[0].get_name() == 'async')) and len(nextTokens) >= 3 and token_is_arrow(nextTokens[2])):
            funcDirectlyCalled = False
            rightOperand = parse_arrow_function(interpreter, leftOperand, list(tokens), False, leftOperand, bFullParsing, assignmentRightOperand)
            if bFullParsing:
                interpreter.set_right_operand(rightOperand)
        elif isinstance(nextToken, CurlyBracketedBlock):
            token = get_next_token(tokens)
            expr = parse_object_value(interpreter, token, tokens, leftOperand, None, bFullParsing, assignmentRightOperand)
            rightOperand = expr
            if bFullParsing:
                interpreter.set_right_operand(rightOperand)
            elif isModuleExports:
                if not leftOperand.get_fullname() in interpreter.jsContent.moduleExports:
                    interpreter.jsContent.moduleExports[leftOperand.get_fullname()] = expr
                for key, value in expr.get_items_dictionary().items():
                    try:
                        if value.is_identifier():
                            f = interpreter.jsContent.get_global_function(value.get_name(), False, False)
                            if not f:
                                f = interpreter.jsContent.get_global_variable(value.get_name(), False)
                        elif value.is_function():
                            f = value
                        else:
                            f = value
                    except:
                        f = None
                    if f:
                        interpreter.jsContent.moduleExports[leftOperand.get_fullname() + '.' + key.get_name()] = f
            elif not expr.get_items():
                # self = {}
                interpreter.add_namespace_prefix(leftOperand.get_name())
        elif isinstance(nextToken, ParenthesedBlock) and len(nextTokens) >= 2 and isinstance(nextTokens[1], ParenthesedBlock):
            try:
                expr = parse_js_function_call(interpreter, tokens, bFullParsing, True, leftOperand)
                rightOperand = expr
                if bFullParsing:
                    interpreter.set_right_operand(rightOperand)
            except:
                pass
        elif isModuleExports and not bFullParsing:
            if isinstance(nextTokens[0], Token) and is_token_subtype(nextTokens[0].type, Name):
                l = list(tokens)
                if isinstance(l[-1], ParenthesedBlock) or (len(l) >= 2 and isinstance(l[-2], ParenthesedBlock)):
                    fcall = FunctionCall(None, None, None)
                    interpreter.jsContent.moduleExports[leftOperand.get_fullname()] = fcall
                else:
                    tokenName = nextTokens[0].text
                    f = interpreter.jsContent.get_global_function(tokenName, False, False)
                    if f:
                        interpreter.jsContent.moduleExports[leftOperand.get_fullname()] = f
                        interpreter.jsContent.moduleExports[leftOperand.get_fullname() + '.' + tokenName] = f
                    else:
                        v = interpreter.jsContent.get_global_variable(tokenName, False)
                        if v:
                            interpreter.jsContent.moduleExports[leftOperand.get_fullname()] = v
            elif isinstance(nextTokens[0], Token) and nextTokens[0].text == 'new' and isinstance(nextTokens[1], Token) and is_token_subtype(nextTokens[1].type, Name):
                tokenName = nextTokens[1].text
                cl = interpreter.jsContent.get_global_class(tokenName)
                if cl:
                    interpreter.jsContent.moduleExports[leftOperand.get_fullname()] = cl
                else:
                    f = interpreter.jsContent.get_global_function(tokenName, False, False)
                    if f:
                        interpreter.jsContent.moduleExports[leftOperand.get_fullname()] = f
                    else:
                        v = interpreter.jsContent.get_global_variable(tokenName, False)
                        if v:
                            interpreter.jsContent.moduleExports[leftOperand.get_fullname()] = v
        elif bFullParsing:
            expr = parse_any_expression(interpreter, tokens, leftOperand, bFullParsing, assignmentRightOperand, identifier)
            if expr and len(expr.elements) == 1:
                rightOperand = expr.elements[0]
                rightOperand.parent = assignment
            else:
                rightOperand = expr
            if bFullParsing:
                interpreter.set_right_operand(rightOperand)
    
    get_next_token(tokens)
        
    interpreter.end_assignment()
    return assignment
    
def tokenize_assignments(tokens):
    
    # we transform 
    # var a = b = c;
    # into
    # var b = c, a = b;
    result = [] # list of assignments
    
    currentAssignment = []
    assignmentsSinceLastComma = []
    assignmentsSinceLastComma.append(currentAssignment)
    
    token = get_next_token(tokens)
    firstEqualFound = False
    
    while token:
        
        if token.get_text() == ',':
            if len(assignmentsSinceLastComma) > 1:
                assignmentsSinceLastComma.reverse()
            result.extend(assignmentsSinceLastComma)
            assignmentsSinceLastComma = []
            firstEqualFound = False
            token = get_next_token(tokens)
            currentAssignment = []
            currentAssignment.append(token)
            assignmentsSinceLastComma.append(currentAssignment)
        elif firstEqualFound and token.get_text() == '=':
            currentAssignment = []
            currentAssignment.append(assignmentsSinceLastComma[-1][-1])
            currentAssignment.append(token)
            token = get_next_token(tokens)
            currentAssignment.append(token)
#             result.append(currentAssignment)
            assignmentsSinceLastComma.append(currentAssignment)
        else:
            if token.get_text() == '=':
                firstEqualFound = True
            currentAssignment.append(token)
        if (isinstance(token, Identifier) or isinstance(token, BracketedIdentifier)) and token.is_func_call():
            token = get_next_token(tokens, True)
        else:
            token = get_next_token(tokens, False, token)
    
    if len(assignmentsSinceLastComma) > 1:
        assignmentsSinceLastComma.reverse()
    result.extend(assignmentsSinceLastComma)
        
    return result
    
def parse_var_declaration(interpreter, varToken, toks, bFullParsing, isLet = False, isConst = False):

    if bFullParsing:
        interpreter.start_var_declaration(varToken, isLet, isConst)
    
    assignmentsTokens = tokenize_assignments(toks)
    
    for assignmentTokens in assignmentsTokens:  
            
        tokens = Lookahead(TokenIterator(assignmentTokens))
    
        identifier = get_next_token(tokens)
    
        if identifier:
            
            finish_bracketed_identifier(interpreter, identifier, bFullParsing)

            try:
                token = tokens.look_next()
            except StopIteration:
                if bFullParsing:
                    interpreter.start_var_declaration_element()
                    interpreter.add_var_declaration_element(identifier)
                    interpreter.end_var_declaration_element()
                continue
            if token.get_text() == ';':
                if bFullParsing:
                    interpreter.start_var_declaration_element()
                    interpreter.add_var_declaration_element(identifier)
                    interpreter.set_var_declaration(identifier)
                    interpreter.end_var_declaration_element()
                continue
            elif token.get_text() == '=':
                if bFullParsing:
                    interpreter.start_var_declaration_element()
                assignment = parse_assignment(interpreter, identifier, tokens, True, bFullParsing)
                if bFullParsing:
                    interpreter.add_var_declaration_element(assignment)
                    interpreter.end_var_declaration_element()
        
    if bFullParsing:
        interpreter.end_var_declaration()            

def look_tokens_until_statement_end(tokens):
    
    result = []
    tokens.start_lookahead()
    try:
        token = next(tokens)
        while (token.get_text() != ';'):
            result.append(token)
            token = next(tokens)
        if token.get_text() == ';':
            result.append(token)
        return result
    except StopIteration:
        return result
    finally:
        tokens.stop_lookahead()

# get tokens until ;
# At the end, we are on ;
def get_tokens_until_statement_end(interpreter, tokens):
    
    result = []
    tagLevel = 0    # do not catch ; is we are in jsx part as in <h4>Drag &amp; drop your sequence file here</h4>
    try:
        token = tokens.look_next()
        if isinstance(token, Token) and token.get_text() == 'if':
            return get_tokens_until_if_statement_end(tokens)
        elif isinstance(token, MethodBlock):
            token = next(tokens)
            tok = tokens.look_next()
            if isinstance(tok, Token) and tok.get_text() == ';':
                next(tokens)
            return [ token ]
        
        token = next(tokens)
        # we skip such code <script type="text/javascript"> present in .js in PHP projects
        if token.get_text() == '<':
            while token.get_text() != '>':
                token = next(tokens)
            token = next(tokens)
            
        while (token.get_text() != ';' or tagLevel > 0):
            if token.get_text() == '=':
                tokenList = look_next_tokens(tokens, 2)
                if not tokenList:
                    token = next(tokens)
                    continue
                token1 = tokenList[0]
                token2 = None
                if len(tokenList) == 2:
                    token2 = tokenList[1]
                if isinstance(token1, Token) and isinstance(token2, Token) and is_token_subtype(token2.type, Name.Tag):
                    if token1.text != '<':
                        result.append(token)
                        token = next(tokens)
                else:
                    result.append(token)
                    token = next(tokens)
                if isinstance(token, FunctionBlock):
                    result.append(token) # if ; missing at end of a = function() {}
                    token = tokens.look_next()
                    if isinstance(token, ParenthesedBlock):
                        result.append(token)
                        get_next_token(tokens)
                        token = tokens.look_next()
                    if token.get_text() == ',':
                        result.append(token)
                        get_next_token(tokens)
                        oldToken = token
                        token = get_next_token(tokens)
                    elif token.get_text() != ';':
                        result.append(Token(';', Punctuation))
                        break;
                elif isinstance(token, NewFunctionBlock):
                    result.append(token) # if ; missing at end of a = new function() {}
                    token = tokens.look_next()
                    if isinstance(token, ParenthesedBlock):
                        result.append(token)
                        get_next_token(tokens)
                        token = tokens.look_next()
                    if token.get_text() == ',':
                        result.append(token)
                        get_next_token(tokens)
                        oldToken = token
                        token = get_next_token(tokens)
                    elif token.get_text() != ';':
                        result.append(Token(';', Punctuation))
                        break;
                else:
                    result.append(token)
                    tokenLine = token.get_end_line()
                    oldToken = token
                    tokenList = look_next_tokens(tokens, 2)
                    if not tokenList:
                        break
                    token = tokenList[0]
                    token2 = None
                    if len(tokenList) == 2:
                        token2 = tokenList[1]
                    if isinstance(token, Token) and isinstance(token2, Token) and is_token_subtype(token2.type, Name.Tag):
                        if token.text == '<':
                            tagLevel += 1
                        elif token.text == '/':
                            if tagLevel > 0:
                                tagLevel -= 1
                    elif tagLevel > 0 and isinstance(token, Token) and token.text == '/' and isinstance(token2, Token) and token2.text == '>':
                        if tagLevel > 0:
                            tagLevel -= 1
                    newLine = token.get_begin_line()
                    if tagLevel == 0 and newLine and newLine > tokenLine:
                        if isinstance(token, Token) and is_token_subtype(token.type, Keyword):
                            result.append(Token(';', Punctuation))
                            break
                        elif isinstance(token, Token) and isinstance(oldToken, Token) and is_token_subtype(token.type, Name) and (is_token_subtype(oldToken.type, Keyword.Constant) or is_token_subtype(oldToken.type, Literal)):
                            result.append(Token(';', Punctuation))
                            break
                        elif isinstance(token, Token) and isinstance(oldToken, Token) and is_token_subtype(token.type, Name) and (is_token_subtype(oldToken.type, Name) or oldToken.text == 'this'):
                            result.append(Token(';', Punctuation))
                            break
                        elif (isinstance(token, FunctionBlock) or isinstance(token, ClassBlock)) and isinstance(oldToken, Token) and ( oldToken.text not in ['=', ':']):
                            result.append(Token(';', Punctuation))
                            break
                        elif isinstance(oldToken, BlockStatement):
                            result.append(Token(';', Punctuation))
                            break
                    token = next(tokens)
            else:
                result.append(token)
                tokenLine = token.get_end_line()
                oldToken = token

                tokenList = look_next_tokens(tokens, 2)
                if not tokenList:
                    break
                token = tokenList[0]
                token2 = None
                if len(tokenList) == 2:
                    token2 = tokenList[1]
                if isinstance(token, Token) and isinstance(token2, Token) and is_token_subtype(token2.type, Name.Tag):
                    if token.text == '<':
                        tagLevel += 1
                    elif token.text == '/':
                        if tagLevel > 0:
                            tagLevel -= 1
                elif tagLevel > 0 and isinstance(token, Token) and token.text == '/' and isinstance(token2, Token) and token2.text == '>':
                    if tagLevel > 0:
                        tagLevel -= 1
                
                newLine = token.get_begin_line()
                if not newLine: # ; which have been artificially added
                    newLine = tokenLine
                if tagLevel == 0 and newLine > tokenLine:
                    if isinstance(token, Token) and is_token_subtype(token.type, Keyword):
                        result.append(Token(';', Punctuation))
                        break
                    elif isinstance(oldToken, BlockStatement) and ((isinstance(token, Token) and is_token_subtype(token.type, Name)) or isinstance(token, FunctionBlock) or isinstance(token, NewFunctionBlock)):
                        if not interpreter.is_class_context():
                            result.append(Token(';', Punctuation))
                        break
                    elif isinstance(token, Token) and is_token_subtype(token.type, Name) and isinstance(oldToken, Token) and (is_token_subtype(oldToken.type, Literal) or is_token_subtype(oldToken.type, Keyword.Constant) or is_token_subtype(oldToken.type, Name)):
                        result.append(Token(';', Punctuation))
                        break
                    elif isinstance(token, FunctionBlock) or isinstance(token, NewFunctionBlock):
                        result.append(Token(';', Punctuation))
                        break
                    elif isinstance(token, MethodBlock):
                        result.append(Token(';', Punctuation))
                        break
                    elif isinstance(token, ClassBlock):
                        result.append(Token(';', Punctuation))
                        break
                token = next(tokens)
            if interpreter.is_class_context() and token.get_text() == '}':
                break
                    
        if token.get_text() == ';':
            result.append(token)
        return result
    except StopIteration:
        return result
    
# get tokens until end of statement if ... else ....
# At the end, we are on ; or end of block }
def get_tokens_until_if_statement_end(tokens):
    
#     tant qu'il n'y a pas de ';', on est dans le meme if
#     s'il y a un ';', et ensuite un else, on est dans le meme if
        
    result = []
    try:
        tokenList = look_next_tokens(tokens, 2)
        if not tokenList or len(tokenList) < 2:
            return []
        
        token = tokenList[0]
        token2 = tokenList[1]

        if not ( isinstance(token, Token) and token.get_text() == 'if'):
            return []
        
        while (token.get_text() != ';' or token2.get_text() != 'else'):
            token = next(tokens)
            result.append(token)
                    
        if token.get_text() == ';':
            result.append(token)
        return result
    except StopIteration:
        return result

def look_tokens_until_curlyBracketedBlock(tokens):
    
    result = []
    tokens.start_lookahead()
    try:
        token = next(tokens)
        while not isinstance(token, CurlyBracketedBlock):
            result.append(token)
            token = next(tokens)
        result.append(token)
        return result
    except StopIteration:
        return result
    finally:
        tokens.stop_lookahead()

# Parses a list of statements
def parse_statements(interpreter, statements, file, bFullAnalysis, leftOperandAssignment = None):

    if isinstance(statements, list):
        tokens = Lookahead(TokenIterator(statements))
    else:
        tokens = statements
    
    # we look at the first token of statements list
    try:
        token = tokens.look_next()
    except StopIteration:
        token = None
    
    # Skip curly brackets if block
    if token and isinstance(token, Token) and token.get_text() == '{':
        token = get_next_token(tokens)

    try:
        token = tokens.look_next()
        if isinstance(token, Token) and is_token_subtype(token.type, Keyword) and token.text == 'static':
            next(tokens)
    except:
        pass
    
    # we look at the 2 first tokens of statements list
    tokenList = look_next_tokens(tokens, 3)
    l = len(tokenList)
    if l < 1:
        return
    nextToken = tokenList[0]
    if l == 1:
        nextToken2 = None
    else:
        nextToken2 = tokenList[1]

    while nextToken:
           
        # Skip last curly brackets if block 
        if nextToken.get_text() == '}':
            break;
        try:
            token = tokens.look_next()
            if isinstance(token, Token) and is_token_subtype(token.type, Keyword) and token.text == 'static':
                next(tokens)
        except:
            pass

        if nextToken.get_text() == 'if':

            if isinstance(nextToken2, ParenthesedBlock):
                parse_if_statement(interpreter, tokens, token, bFullAnalysis)
                    
            else:
                phrase = get_tokens_until_statement_end(interpreter, tokens)
                if not phrase:
                    pass
                parse_statement(interpreter, phrase, file, bFullAnalysis)
                # we are at the end of current statement
        
        else:
                
            if isinstance(nextToken, FunctionBlock) or isinstance(nextToken, NewFunctionBlock):
                token = get_next_token(tokens)
                #we are on function block
                parse_function(interpreter, None, token, True, None, bFullAnalysis, None)

            elif isinstance(nextToken, ClassBlock):
                token = get_next_token(tokens)
                #we are on class block
                parse_class(interpreter, None, token, True, None, bFullAnalysis, None)

            elif nextToken.get_text() == 'switch':
                if isinstance(nextToken2, ParenthesedBlock):
                    token = get_next_token(tokens)
                    # we are on switch
                    parse_switch_block(interpreter, token, tokens, bFullAnalysis)
                else:
                    phrase = get_tokens_until_statement_end(interpreter, tokens)
                    parse_statement(interpreter, phrase, file, bFullAnalysis)
                    # we are at the end of current statement
        
            elif nextToken.get_text() == 'for':
                if isinstance(nextToken2, ParenthesedBlock):
                    token = get_next_token(tokens)
                    # we are on for
                    parse_for_block(interpreter, token, tokens, bFullAnalysis)
                elif nextToken2.get_text() == 'each':
                    token = get_next_token(tokens)
                    # we are on for
                    parse_for_each_block(interpreter, token, tokens, bFullAnalysis)
                else:
                    phrase = get_tokens_until_statement_end(interpreter, tokens)
                    parse_statement(interpreter, phrase, file, bFullAnalysis)
                    # we are at the end of current statement
        
            elif nextToken.get_text() == 'do':
                if isinstance(nextToken2, CurlyBracketedBlock):
                    token = get_next_token(tokens)
                    # we are on do
                    parse_do_block(interpreter, token, tokens, bFullAnalysis)
                else:
                    phrase = get_tokens_until_statement_end(interpreter, tokens)
                    parse_statement(interpreter, phrase, file, bFullAnalysis)
                    # we are at the end of current statement
        
            elif nextToken.get_text() == 'while':
                if isinstance(nextToken2, ParenthesedBlock):
                    token = get_next_token(tokens)
                    # we are on while
                    parse_while_block(interpreter, token, tokens, bFullAnalysis)
                else:
                    phrase = get_tokens_until_statement_end(interpreter, tokens)
                    parse_statement(interpreter, phrase, file, bFullAnalysis)
                    # we are at the end of current statement
        
            elif nextToken.get_text() == 'try':
                if isinstance(nextToken2, CurlyBracketedBlock):
                    token = get_next_token(tokens)
                    # we are on try
                    parse_try_catch_block(interpreter, token, tokens, bFullAnalysis)
                else:
                    phrase = get_tokens_until_statement_end(interpreter, tokens)
                    parse_statement(interpreter, phrase, file, bFullAnalysis)
                    # we are at the end of current statement

            elif nextToken.get_text() == 'import':
                phrase = get_tokens_until_statement_end(interpreter, tokens)
                if not phrase:
                    nextToken = None
                    break
                parse_import_statement(interpreter, phrase, bFullAnalysis)
                
            elif isinstance(nextToken, CurlyBracketedBlock):
                parse_block_scope(interpreter, nextToken, bFullAnalysis)
                next(tokens)

            else:
                
                phrase = get_tokens_until_statement_end(interpreter, tokens)
                if not phrase:
                    nextToken = None
                    break
                parse_statement(interpreter, phrase, file, bFullAnalysis, leftOperandAssignment)
                # we are at the end of current statement
            
        tokenList = look_next_tokens(tokens, 3)
        l = len(tokenList)
        if l < 1:
            break
        nextToken = tokenList[0]
        if l == 1:
            nextToken2 = None
        else:
            nextToken2 = tokenList[1]

def is_assignment(tokenList):
    for token in tokenList:
        if isinstance(token, Token) and is_token_subtype(token.type, Operator) and token.get_text() == '=':
            return True
    return False
    
# parse one statement      
def parse_statement(interpreter, statements, file, bFullParsing, leftOperandAssignment = None):
    
    try:
        tokens = Lookahead(TokenIterator(statements))
        identifier = get_next_identifier(None, tokens)
        if bFullParsing:
            finish_bracketed_identifier(interpreter, identifier, True)
        
        if identifier:
    
            interpreter.start_identifier(identifier)
            
            if isinstance(identifier.get_prefix_internal(), ParenthesedBlock):
                expr = parse_parenthesed_expression(interpreter, identifier.get_prefix_internal(), bFullParsing)
                identifier.set_prefix_internal(expr)
    
            interpreter.end_identifier()
            
            if identifier.is_func_call():
                # beware to async (v) => v + 1 which is not a function call
                isAssignment = False
                if identifier.get_name() == 'async':
                    try:
                        nextTokens = look_next_tokens(tokens, 2)
                        if token_is_arrow(nextTokens[1]):
                            isAssignment = True
                    except:
                        pass
                if not is_assignment(statements) and not isAssignment:
                    token = tokens.look_next()
                    if bFullParsing:
                        parse_function_call(interpreter, identifier, token, tokens, bFullParsing, True)
                    elif identifier.get_name() == 'define':
                        parse_define(interpreter, identifier, token, tokens, bFullParsing, True)
                else:
                    if identifier.is_func_call() and not bFullParsing:
                        return None
                    parse_assignment(interpreter, identifier, tokens, False, bFullParsing)
            else:
                try:
                    nextToken = tokens.look_next()
                except:
                    nextToken = None
                if nextToken and nextToken.get_text() == '=':
                    parse_assignment(interpreter, identifier, tokens, False, bFullParsing)
                    try:
                        nextToken2 = tokens.look_next()
                        while nextToken2 and isinstance(nextToken2, Token) and is_token_subtype(nextToken2.type, Punctuation) and nextToken2.text == ',':
                            tok1 = next(tokens)
                            tok2 = next(tokens)
                            tok3 = tokens.look_next()
                            if tok3 and isinstance(tok3, Token) and is_token_subtype(tok3.type, Operator) and tok3.text == '=':
                                parse_assignment(interpreter, identifier, tokens, False, bFullParsing)
                                nextToken2 = tokens.look_next()
                            else:
                                if tok3:
                                    line = 0
                                    try:
                                        line = tok3.begin_line
                                    except:
                                        try:
                                            line = tok2.begin_line
                                        except:
                                            line = tok1.begin_line
                                    cast.analysers.log.info('Perhaps an incorrect syntax has been found near line ' + str(line))
                                break
                    except:
                        pass
                elif isinstance(nextToken, Token) and is_token_subtype(nextToken.type, Operator):
                    if nextToken.get_text() == '+=':
                        parse_short_addition_statement(interpreter, Lookahead(TokenIterator(statements)), bFullParsing)
                    else:
                        parse_any_statement(interpreter, Lookahead(TokenIterator(statements)), bFullParsing)
                else:
                    parse_any_statement(interpreter, Lookahead(TokenIterator(statements)), bFullParsing)
                
        else:
            tokenList = look_next_tokens(tokens, 3)
            if not tokenList:
                pass
            token = tokenList[0]
            if token.get_text() in ['var', 'let', 'const']:
                get_next_token(tokens)
                parse_var_declaration(interpreter, token, tokens, bFullParsing, token.get_text() == 'let', token.get_text() == 'const')
            elif token.get_text() == 'export' and tokenList[1].get_text() == 'const':
                get_next_token(tokens)
                get_next_token(tokens)
                parse_var_declaration(interpreter, token, tokens, bFullParsing, False, True)
            elif token.get_text() == 'export' and len(tokenList) >= 3 and tokenList[2].get_text() == '=':
                get_next_token(tokens)
                identifier = get_next_identifier(None, tokens)
                parse_assignment(interpreter, identifier, tokens, False, bFullParsing, True)
            elif isinstance(token, ParenthesedBlock):
                phrase = look_tokens_until_statement_end(tokens)
                if len(phrase) >= 2 and isinstance(phrase[-2], ParenthesedBlock):
                    parentheseChildren = token.get_children()
                    get_next_token(parentheseChildren)
                    childToken = get_next_token(parentheseChildren)
                    if isinstance(childToken, FunctionBlock):
                        parse_js_function_call(interpreter, tokens, bFullParsing)
                    elif phrase[1].get_text() == '.':
                        expr = parse_parenthesed_expression(interpreter, token, bFullParsing)
                        parse_function_call(interpreter, expr, None, tokens, bFullParsing)
                    else:
                        parse_any_statement(interpreter, tokens, bFullParsing)
            elif isinstance(token, MethodBlock) and interpreter.is_class_context():
                parse_method(interpreter, token, bFullParsing)
            elif not (isinstance(token, Token) and is_token_subtype(token.type, Error)) and token.get_text() != ';' and token.get_text() not in ['var', 'let', 'const']:
                try:
                    parse_any_statement(interpreter, tokens, bFullParsing, leftOperandAssignment)
                except StopIteration:
                    pass
    except Exception as e:
        if not interpreter.resolvingHtmlValues:
            cast.analysers.log.warning('HTML5-005 Internal issue in parsing one statement')
        cast.analysers.log.debug(str(traceback.format_exc()))
    
def get_block(interpreter, tokens):
    """
    Gets a block.
    
    if () {
       statements
    }
    Here the block is all which is between {}

    if () statement;
    Here the block the only statement in If block.
    """
    tokenList = look_next_tokens(tokens, 2)
    nextToken = tokenList[0]
    if len(tokenList) >= 2:
        nextToken2 = tokenList[1]
    else:
        nextToken2 = None
    if isinstance(nextToken, CurlyBracketedBlock):
        block = get_next_token(tokens)
    else: # case if (... ) ... ;
        block = []
        elseFound = False
        # if statements can be imbricated and blocks without {}
        if isinstance(nextToken, Token) and (nextToken.get_text() == 'if' and nextToken2.get_text() != 'else'):
            while nextToken and isinstance(nextToken, Token) and (nextToken.get_text() == 'if' and nextToken2.get_text() != 'else'):
                if  nextToken.get_text() == 'else' and nextToken2.get_text() != 'if':
                    elseFound = True
                bl = get_tokens_until_statement_end(interpreter, tokens)
                block.extend(bl)
                if elseFound:
                    break
                try:
                    tokenList = look_next_tokens(tokens, 2)
                    if tokenList:
                        nextToken = tokenList[0]
                        if len(tokenList) >= 2:
                            nextToken2 = tokenList[1]
                        else:
                            nextToken2 = None
                    else:
                        nextToken = None
                        nextToken2 = None
                except StopIteration:
                    nextToken = None
                    nextToken2 = None
        else:
            block = get_tokens_until_statement_end(interpreter, tokens)
    return block

def parse_if_else_block(interpreter, tokens, token, bFullAnalysis):   

    ifBlock = None
    token = tokens.look_next()

    if isinstance(token, CurlyBracketedBlock):
        ifBlock = get_block(interpreter, tokens)
    else:
        if isinstance(token, Token) and token.get_text() == 'if':
            interpreter.start_ast_block(token)
            parse_if_statement(interpreter, tokens, token, bFullAnalysis)
            interpreter.end_ast_block()
        elif bFullAnalysis:
            pass # on va jusqu'au ; ou else if ou else
            ifBlock = []
            next(tokens)
            ifBlock.append(token)
            try:
                oldToken = token
                token = tokens.look_next()
                while not isinstance(token, Token) or (token.get_text() != 'else' and token.get_text() != ';'):
                    if isinstance(token, Token) and isinstance(oldToken, Token) and is_token_subtype(oldToken.type, Keyword.Constant) and is_token_subtype(token.type, Name):
                        break
                    next(tokens)
                    ifBlock.append(token)
                    oldToken = token
                    token = tokens.look_next()
            except StopIteration:
                pass
            
            if isinstance(token, Token) and token.get_text() == ';':
                ifBlock.append(token)
                try:
                    token = get_next_token(tokens)
                except StopIteration:
                    pass

    if bFullAnalysis and ifBlock:
        parse_statements_block(interpreter, ifBlock, tokens)
        
    return ifBlock
         
def parse_if_statement(interpreter, tokens, token, bFullAnalysis):
    
    ifStatement = None
    
    if bFullAnalysis:
        ifStatement = interpreter.start_if_statement(token)   # token is if keyword

    if bFullAnalysis:
        interpreter.start_if_block(token)   # token is if keyword
    get_next_token(tokens)
    parenthesedExpr = get_next_token(tokens)
    if bFullAnalysis:
        parse_parenthesed_expression(interpreter, parenthesedExpr, bFullAnalysis)
        parse_if_else_block(interpreter, tokens, token, bFullAnalysis)
    if bFullAnalysis:
        interpreter.end_if_block()
    
    try:
        while True:    
    
            token = tokens.look_next()
            if isinstance(token, Token) and token.get_text() == 'else':
                token = get_next_token(tokens)
                token = tokens.look_next()
                if isinstance(token, Token) and token.get_text() == 'if':
                    token = get_next_token(tokens)
                    token = tokens.look_next()
                    if bFullAnalysis:
                        interpreter.start_elseif_block(token)
                    parenthesedExpr = get_next_token(tokens)
                    if bFullAnalysis:
                        parse_parenthesed_expression(interpreter, parenthesedExpr, bFullAnalysis)
                    parse_if_else_block(interpreter, tokens, token, bFullAnalysis)
                    if bFullAnalysis:
                        interpreter.end_elseif_block()
                else:
                    if bFullAnalysis:
                        interpreter.start_else_block(token)
                    parse_if_else_block(interpreter, tokens, token, bFullAnalysis)
                    if bFullAnalysis:
                        interpreter.end_else_block()
                    break
            else:
                if not bFullAnalysis and not isinstance(token, CurlyBracketedBlock):
                    try:
                        token = tokens.look_next()
                        while not isinstance(token, Token) or (token.get_text() != 'else' and token.get_text() != ';'):
                            next(tokens)
                            token = tokens.look_next()
                    except StopIteration:
                        pass
                    
                    if isinstance(token, Token) and token.get_text() == ';':
                        next(tokens)
                break
        
    except StopIteration:
        pass
        
    if bFullAnalysis:
        interpreter.end_if_statement()
        
    return ifStatement
        
def parse_if_block(interpreter, token, tokens, bFullAnalysis):
    
    ifBlock = None
    interpreter.start_if_statement(token)   # token is if keyword
    if bFullAnalysis:
        ifBlock = interpreter.start_if_block(token)   # token is if keyword
    parenthesedExpr = get_next_token(tokens)
    if bFullAnalysis:
        parse_parenthesed_expression(interpreter, parenthesedExpr, bFullAnalysis)
    block = get_block(interpreter, tokens)

    if bFullAnalysis:
        parse_statements_block(interpreter, block, tokens)
        interpreter.end_if_block()
    return ifBlock
    
def parse_elseif_block(interpreter, token, tokens, bFullAnalysis):
    
    ifBlock = None
    if bFullAnalysis:
        ifBlock = interpreter.start_elseif_block(token)
    get_next_token(tokens)
    parenthesedExpr = get_next_token(tokens)
    if bFullAnalysis:
        parse_parenthesed_expression(interpreter, parenthesedExpr, bFullAnalysis)
    block = get_block(interpreter, tokens)
    if bFullAnalysis:
        parse_statements_block(interpreter, block, tokens)
        interpreter.end_elseif_block()
    return ifBlock
    
def parse_else_block(interpreter, token, tokens, bFullAnalysis):
    
    ifBlock = None
    if bFullAnalysis:
        ifBlock = interpreter.start_else_block(token)
    nextToken = tokens.look_next()
    if isinstance(nextToken, CurlyBracketedBlock):
        block = get_next_token(tokens)
    else: # cast if (... ) ... ;
        block = get_tokens_until_statement_end(interpreter, tokens)
    if bFullAnalysis:
        parse_statements_block(interpreter, block, tokens)
        interpreter.end_else_block()
    return ifBlock
    
def parse_do_block(interpreter, token, tokens, bFullAnalysis):
    
    stmtBlock = None
    if bFullAnalysis:
        stmtBlock = interpreter.start_do_block(token)
    block = get_next_token(tokens)
    if bFullAnalysis:
        parse_statements_block(interpreter, block, tokens)
    get_next_token(tokens)
    parenthesedExpr = get_next_token(tokens)
    if bFullAnalysis:
        parse_parenthesed_expression(interpreter, parenthesedExpr, bFullAnalysis)
    get_next_token(tokens) # ;
    if bFullAnalysis:
        interpreter.end_do_block()
    return stmtBlock
    
def parse_while_block(interpreter, token, tokens, bFullAnalysis):
    
    stmtBlock = None
    if bFullAnalysis:
        stmtBlock = interpreter.start_while_block(token)
    parenthesedExpr = get_next_token(tokens)
    if bFullAnalysis:
        parse_parenthesed_expression(interpreter, parenthesedExpr, bFullAnalysis)
    block = get_block(interpreter, tokens)
    if bFullAnalysis:
        parse_statements_block(interpreter, block, tokens)
    if bFullAnalysis:
        interpreter.end_while_block()
    return stmtBlock
    
def parse_for_block(interpreter, token, tokens, bFullAnalysis):
    
    global LAST_TOKEN_PARSED_TO_NONE
    stmtBlock = None
    if bFullAnalysis:
        stmtBlock = interpreter.start_for_block(token)
    parenthesedExpr = get_next_token(tokens)
    if bFullAnalysis:
        stmtBlock.add_token(parenthesedExpr)
    if bFullAnalysis:
        exprTokens = parenthesedExpr.get_children()
        get_next_token(exprTokens)
        interpreter.start_start_expression()
        expr = parse_expression(interpreter, exprTokens, True)
        lastToken = LAST_TOKEN_PARSED_TO_NONE
        interpreter.add_start_expression(expr)
        while lastToken and isinstance(lastToken, Token) and lastToken.text == ',':
            expr = parse_expression(interpreter, exprTokens, True)
            lastToken = LAST_TOKEN_PARSED_TO_NONE
            interpreter.add_start_expression(expr)
        interpreter.end_start_expression()
        interpreter.start_termination_expression()
        expr = parse_expression(interpreter, exprTokens, True)
        interpreter.set_termination_expression(expr)
        interpreter.end_termination_expression()
        interpreter.start_forward_expression()
        expr = parse_expression(interpreter, exprTokens, True)
        interpreter.set_forward_expression(expr)
        interpreter.end_forward_expression()
        
    block = get_block(interpreter, tokens)
    if bFullAnalysis:
        stmtBlock.add_token(block)
    if bFullAnalysis:
        parse_statements_block(interpreter, block, tokens)
    if bFullAnalysis:
        interpreter.end_for_block()
    return stmtBlock
    
def parse_for_each_block(interpreter, token, tokens, bFullAnalysis):
    
    stmtBlock = None
    if bFullAnalysis:
        stmtBlock = interpreter.start_for_each_block(token)
    get_next_token(tokens)
    parenthesedExpr = get_next_token(tokens)
    if bFullAnalysis:
        parse_parenthesed_expression(interpreter, parenthesedExpr, bFullAnalysis, True)
    block = get_block(interpreter, tokens)
    if bFullAnalysis:
        parse_statements_block(interpreter, block, tokens)
    if bFullAnalysis:
        interpreter.end_for_each_block()
    return stmtBlock
    
def parse_switch_block(interpreter, token, tokens, bFullAnalysis):
    
    stmtBlock = None
    if bFullAnalysis:
        stmtBlock = interpreter.start_switch_block(token)
    parenthesedExpr = get_next_token(tokens)
    if bFullAnalysis:
        parse_parenthesed_expression(interpreter, parenthesedExpr, bFullAnalysis)
    block = get_block(interpreter, tokens)
    if bFullAnalysis:
        stmtBlock.add_token(block)
        parse_switch_cases(interpreter, block, tokens)
        interpreter.end_switch_block()
    return stmtBlock

def parse_switch_cases(interpreter, token, tokens):
    
    children = token.get_children()
    
    get_next_token(children)
    token = next(children)
    inCase = False
    inDefault = False
    caseBlock = None
    defaultBlock = None
    tokenList = []
    while token:
        if (isinstance(token, Token) and is_token_subtype(token.type, Punctuation) and token.get_text() == '}'):
            try:
                token = next(children)
            except StopIteration:
                token = None
            continue
        elif (isinstance(token, Token) and is_token_subtype(token.type, Keyword) and token.get_text() == 'case'):
            inCase = True
            if caseBlock:
                if tokenList:
                    parse_statements_block(interpreter, tokenList, tokenList)
                interpreter.end_switch_case_block()
                tokenList = []               
            elif defaultBlock:
                if tokenList:
                    parse_statements_block(interpreter, tokenList, tokenList)
                interpreter.end_switch_default_block()
                tokenList = []               
            caseBlock = None
            defaultBlock = None
        elif (isinstance(token, Token) and is_token_subtype(token.type, Keyword) and token.get_text() == 'default'):
            inDefault = True
            if caseBlock:
                if tokenList:
                    parse_statements_block(interpreter, tokenList, tokenList)
                interpreter.end_switch_case_block()
                tokenList = []               
            caseBlock = None
        elif (inCase or inDefault) and (isinstance(token, Token) and is_token_subtype(token.type, Operator) and token.get_text() == ':'):
            if inCase:
                caseBlock = interpreter.start_switch_case_block(tokenList)
                if tokenList:
                    toks = Lookahead(TokenIterator(tokenList))
                    expr = parse_expression(interpreter, toks, True)
                    interpreter.set_expression(expr)
                tokenList = []
                inCase = False
            else:
                defaultBlock = interpreter.start_switch_default_block(tokenList)
            inDefault = False
        else:
            tokenList.append(token)
        try:
            token = next(children)
        except StopIteration:
            token = None

    if caseBlock: 
        if tokenList:        
            parse_statements_block(interpreter, tokenList, tokenList)
        interpreter.end_switch_case_block()
        
    elif defaultBlock:
        if tokenList:
            parse_statements_block(interpreter, tokenList, tokenList)
        interpreter.end_switch_default_block()
        
#     # we look at the first token of statements list
#     try:
#         token = tokens.look_next()
#     except StopIteration:
#         token = None
#     
#     # Skip curly brackets if block
#     if token and isinstance(token, Token) and token.get_text() == '{':
#         token = get_next_token(tokens)
# 
#     # we look at the 2 first tokens of statements list
#     tokenList = look_next_tokens(tokens, 3)
# 
#     # Skip curly brackets if block
#     if token and isinstance(token, Token) and token.get_text() == '{':
#         token = get_next_token(tokens)
# 
#     interpreter.start_ast_block(token)
#     parse_statements(interpreter, token.get_children(), None, True)
#     interpreter.end_ast_block()
    
def parse_try_catch_block(interpreter, token, tokens, bFullAnalysis):
    
    stmtBlock = None
    if bFullAnalysis:
        stmtBlock = interpreter.start_try_catch_block(token)
    block = get_block(interpreter, tokens)
    if bFullAnalysis:
        parse_statements_block(interpreter, block, tokens)
    tok = tokens.look_next()
    while tok and tok.get_text() == 'catch':
        get_next_token(tokens) # catch
        parenthesedExpr = get_next_token(tokens)
        block = get_block(interpreter, tokens)
        if bFullAnalysis:
            bl = interpreter.start_catch_block(tok)
            bl.add_token(block)
        if bFullAnalysis:
            parse_parenthesed_expression(interpreter, parenthesedExpr, bFullAnalysis)
        if bFullAnalysis:
            parse_statements_block(interpreter, block, tokens)
            interpreter.end_catch_block()
        tok = None
        try:
            tok = tokens.look_next()
        except:
            pass
    if tok and tok.get_text() == 'finally':
        get_next_token(tokens) # catch
        block = get_block(interpreter, tokens)
        if bFullAnalysis:
            bl = interpreter.start_finally_block(tok)
            bl.add_token(block)
        if bFullAnalysis:
            parse_statements_block(interpreter, block, tokens)
            interpreter.end_finally_block()
        tok = None
        try:
            tok = tokens.look_next()
        except:
            pass
    if bFullAnalysis:
        interpreter.end_try_catch_block()
    return stmtBlock
    
def parse_block_scope(interpreter, token, bFullAnalysis):
    
    if not bFullAnalysis:
        return
    
    interpreter.start_ast_block(token)
    parse_statements(interpreter, token.get_children(), None, True)
    interpreter.end_ast_block()

def parse_short_addition_statement(interpreter, tokens, bFullParsing):
    """
    A short addition statement is a += b.
    """
    listTokens = []
    if not bFullParsing:
        expr = None
    else:
        expr = interpreter.start_addition(listTokens, True, bFullParsing)
        expr = parse_expression(interpreter, tokens, bFullParsing)
        interpreter.end_addition()
    return expr

def parse_expression(interpreter, tokens, bFullParsing, setExpr = True, leftOperandAssignment = None):
    
    listTokens = []
    value = parse_next_token(interpreter, tokens, bFullParsing, leftOperandAssignment)
    isArrowFunction = False
    while value:
        listTokens.append(value)
        try:
            if value and value.is_function_call():
                try:
                    tok = tokens.look_next()
                    if isinstance(tok, ParenthesedBlock):
                        get_next_token(tokens)
                        tok = parse_next_token(interpreter, tokens, bFullParsing)
                except:
                    tok = None
                if tok and tok.get_text() != '?':
#                     value = get_next_token(tokens)
                    value = parse_next_token(interpreter, tokens, bFullParsing)
                    listTokens.append(value)
        except:
            pass
        if isinstance(value, AstOperator) and value.get_name() == '=>':
            isArrowFunction = True
            
        if isArrowFunction:
            value = get_next_token(tokens)
        else:
            value = parse_next_token(interpreter, tokens, bFullParsing)
    expr = build_expression(interpreter, listTokens, False, bFullParsing)
    if not bFullParsing and setExpr:
        interpreter.set_expression(expr)
    return expr

def parse_parenthesed_expression(interpreter, token, bFullParsing, anyExpr = False):
    
    tokens = token.get_children()
    get_next_token(tokens)
    listTokens = []
    value = parse_next_token(interpreter, tokens, bFullParsing)
    while value:
        listTokens.append(value)
        value = parse_next_token(interpreter, tokens, bFullParsing)
    expr = build_expression(interpreter, listTokens, anyExpr)
    interpreter.set_expression(expr)
    return expr
    
def parse_statements_block(interpreter, token, tokens):
    
    if isinstance(token, CurlyBracketedBlock):
        interpreter.start_ast_block(token)
        parse_statements(interpreter, token.get_children(), None, True)
        interpreter.end_ast_block()
    else:
        interpreter.start_ast_block(token)
        if not isinstance(token, Token) or token.get_text() != ';':
            parse_statements(interpreter, token, None, True)
        interpreter.end_ast_block()
    
def parse_object_value(interpreter, token, tokens, leftOperandAssignment, prefix, bFullParsing, lightObject):

    ovName = None
    try:
        ovName = leftOperandAssignment.get_fullname()
    except:
        ovName = prefix
    objectValue = interpreter.start_object_value(ovName, token, lightObject)
    nameParameters = []
    tokenParameters = []
    tokenValues = []
    parse_object(token, nameParameters, tokenParameters, tokenValues)
    cmpt = 0
    maxLen = len(tokenValues)
    bEmpty = True
    if objectValue.itemsList:
        bEmpty = False
        
    lightParams = {}
    if lightObject:
        for key, value in lightObject.items.items():
            lightParams[key.get_name()] = key
            
    for paramName in nameParameters:

        if cmpt >= maxLen:
            break
        value = tokenValues[cmpt]
        if not value:
            try:
                value = tokenParameters[cmpt]
            except:
                value = None
        
        if paramName.is_identifier():
            if not isinstance(value, FunctionBlock) and not isinstance(value, NewFunctionBlock) and not isinstance(value, MethodBlock):
                fullname = paramName.get_name()
                if prefix:
                    fullname = prefix + '.' + paramName.get_name()
#                 elif ovName:
#                     fullname = ovName + '.' + paramName.get_name()
                if not bFullParsing:
                    interpreter.add_global(paramName, True)
                    if prefix:
                        interpreter.add_global(paramName, True, prefix)
                    elif ovName:
                        interpreter.add_global(paramName, True, ovName)
                    interpreter.jsContent.add_global_variable(fullname, paramName)
                    if fullname.startswith('exports.') or fullname.startswith('module.exports.'):
                        func = interpreter.currentContext.get_function(paramName.get_name())
                        if func:
                            if fullname.startswith('exports.'):
                                interpreter.add_global(func, True, fullname[8:-len(paramName.get_name())-1], None, True)
                                interpreter.jsContent.add_global_function(fullname[8:], func)
                            else:
                                interpreter.add_global(func, True, fullname[15:-len(paramName.get_name())-1], None, True)
                                interpreter.jsContent.add_global_function(fullname[15:], func)
                else:
                    if interpreter.contextStack[-1].wasPreprocessed:
                        ident = interpreter.jsContent.get_global_variable(fullname)
                        if ident:
                            paramName = ident
                
            paramName.parent = objectValue
            if paramName.get_name() in lightParams:
                paramName = lightParams[paramName.get_name()]
        
        if value and type(value) is list:
            if ((isinstance(value[0], Identifier) and not isinstance(value[1], ParenthesedBlock)) or isinstance(value[0], BracketedIdentifier)) and value[0].is_identifier() and isinstance(value[1], ParenthesedBlock):
                if bFullParsing:
                    valueTokens = Lookahead(TokenIterator(value))
                    fcall = parse_function_call(interpreter, value[0], value[1], valueTokens, bFullParsing)
                    objectValue.add_item(paramName, fcall)
                else:
                    objectValue.add_item(paramName, None)
            else:
#                 expr = build_expression(interpreter, value)
                if len(value) >= 3 and token_is_arrow(value[1]):
                    if bEmpty:
                        lightFunc = None
                    else:
                        lightFunc = objectValue.itemsList[cmpt]
                    if prefix:
                        ident = Identifier(None, paramName.get_name())
                        ident.set_prefix(prefix)
                        value = parse_arrow_function(interpreter, ident, value, False, leftOperandAssignment, bFullParsing, lightFunc)
                    else:
                        value = parse_arrow_function(interpreter, paramName, value, False, leftOperandAssignment, bFullParsing, lightFunc)
                    if not lightFunc:
                        objectValue.add_item(paramName, value)
                else:
                    valueTokens = Lookahead(TokenIterator(value))
                    expr = parse_expression(interpreter, valueTokens, bFullParsing, False)
                    objectValue.add_item(paramName, expr)
                
            cmpt += 1
            continue
        
        if isinstance(value, FunctionBlock) or isinstance(value, NewFunctionBlock) or isinstance(value, MethodBlock):
            if bEmpty:
                lightFunc = None
            else:
                lightFunc = objectValue.itemsList[cmpt]
            token = value
            if prefix:
                ident = Identifier(None, paramName.get_name())
                ident.set_prefix(prefix)
                value = parse_function(interpreter, ident, value, False, leftOperandAssignment, bFullParsing, lightFunc)
            else:
                value = parse_function(interpreter, paramName, value, False, leftOperandAssignment, bFullParsing, lightFunc)
            if isinstance(token, NewFunctionBlock):
                value.set_function_constructor()
                
            if not lightFunc:
                objectValue.add_item(paramName, value)

        elif isinstance(value, CurlyBracketedBlock):
            if paramName.is_identifier():
                interpreter.add_object_value_variable(paramName)
            pref = None
            if leftOperandAssignment:
                pref = leftOperandAssignment.get_fullname() + '.' + paramName.get_name()
            elif prefix:
                pref = prefix + '.' + paramName.get_name()
            else:
                pref = paramName.get_name()
#             lightOV = objectValue.get_item(paramName.get_name())
            if bEmpty:
                lightOV = None
            else: 
                lightOV = objectValue.itemsList[cmpt]
            value = parse_object_value(interpreter, value, tokens, None, pref, bFullParsing, lightOV)
            if not lightOV:
                objectValue.add_item(paramName, value)
                
        elif not type(value) is list:
            if paramName.is_identifier():
                interpreter.add_object_value_variable(paramName)
            if not isinstance(value, Identifier) and not isinstance(value, BracketedIdentifier):
                if bEmpty:
                    lightList = None
                else: 
                    lightList = objectValue.itemsList[cmpt]
                if value:
                    value = parse_token(interpreter, value, None, None, bFullParsing, lightList, paramName)
            if isinstance(objectValue, ObjectValue):
                if not lightObject:
                    objectValue.add_item(paramName, value)
            else:
                cast.analysers.log.debug('Object with several same names : ' + paramName.get_name())
        cmpt += 1
    interpreter.end_object_value()
    return objectValue
    
def parse_object_destructuration(interpreter, token, tokens, bFullParsing, lightObject):

    objectValue = interpreter.start_object_destructuration(token, lightObject)
    nameParameters = []
    tokenParameters = []
    tokenValues = []
    parse_object(token, nameParameters, tokenParameters, tokenValues)
    cmpt = 0
    maxLen = len(tokenValues)
    bEmpty = True
    if objectValue.itemsList:
        bEmpty = False
        
    lightParams = {}
    if lightObject:
        for key, value in lightObject.items.items():
            lightParams[key.get_name()] = key
            
    for paramName in nameParameters:

        if cmpt >= maxLen:
            break
        value = tokenValues[cmpt]
        
        if paramName.is_identifier():
            if not isinstance(value, FunctionBlock) and not isinstance(value, NewFunctionBlock):
                fullname = paramName.get_name()
                if not bFullParsing:
                    interpreter.add_global(paramName, True)
                    interpreter.jsContent.add_global_variable(fullname, paramName)
#                     if fullname.startswith('exports.') or fullname.startswith('module.exports.'):
#                         func = interpreter.currentContext.get_function(paramName.get_name())
#                         if func:
#                             if fullname.startswith('exports.'):
#                                 interpreter.add_global(func, True, fullname[8:-len(paramName.get_name())-1], None, True)
#                                 interpreter.jsContent.add_global_function(fullname[8:], func)
#                             else:
#                                 interpreter.add_global(func, True, fullname[15:-len(paramName.get_name())-1], None, True)
#                                 interpreter.jsContent.add_global_function(fullname[15:], func)
                else:
                    if interpreter.contextStack[-1].wasPreprocessed:
                        ident = interpreter.jsContent.get_global_variable(fullname)
                        if ident:
                            paramName = ident
                
            paramName.parent = objectValue
            if paramName.get_name() in lightParams:
                paramName = lightParams[paramName.get_name()]
        
        if value and type(value) is list:
            if ((isinstance(value[0], Identifier) and not isinstance(value[1], ParenthesedBlock)) or isinstance(value[0], BracketedIdentifier)) and value[0].is_identifier() and isinstance(value[1], ParenthesedBlock):
                if bFullParsing:
                    valueTokens = Lookahead(TokenIterator(value))
                    fcall = parse_function_call(interpreter, value[0], value[1], valueTokens, bFullParsing)
                    objectValue.add_item(paramName, fcall)
                else:
                    objectValue.add_item(paramName, None)
            else:
                if len(value) >= 3 and token_is_arrow(value[1]):
                    if bEmpty:
                        lightFunc = None
                    else:
                        lightFunc = objectValue.itemsList[cmpt]
                    value = parse_arrow_function(interpreter, paramName, value, False, None, bFullParsing, lightFunc)
                    if not lightFunc:
                        objectValue.add_item(paramName, value)
                else:
                    valueTokens = Lookahead(TokenIterator(value))
                    expr = parse_expression(interpreter, valueTokens, bFullParsing, False)
                    objectValue.add_item(paramName, expr)
                
            cmpt += 1
            continue
        
        if isinstance(value, FunctionBlock) or isinstance(value, NewFunctionBlock):
            if bEmpty:
                lightFunc = None
            else:
                lightFunc = objectValue.itemsList[cmpt]
            token = value
            value = parse_function(interpreter, paramName, value, False, None, bFullParsing, lightFunc)
            if isinstance(token, NewFunctionBlock):
                value.set_function_constructor()
                
            if not lightFunc:
                objectValue.add_item(paramName, value)

        elif isinstance(value, CurlyBracketedBlock):
            if paramName.is_identifier():
                interpreter.add_object_value_variable(paramName)
            pref = None
            pref = paramName.get_name()
            if bEmpty:
                lightOV = None
            else: 
                lightOV = objectValue.itemsList[cmpt]
            value = parse_object_value(interpreter, value, tokens, None, pref, bFullParsing, lightOV)
            if not lightOV:
                objectValue.add_item(paramName, value)
                
        elif not type(value) is list:
            if paramName.is_identifier():
                interpreter.add_object_value_variable(paramName)
            if not isinstance(value, Identifier) and not isinstance(value, BracketedIdentifier):
                if bEmpty:
                    lightList = None
                else: 
                    lightList = objectValue.itemsList[cmpt]
                if value:
                    value = parse_token(interpreter, value, None, None, bFullParsing, lightList, paramName)
            if isinstance(objectValue, ObjectValue):
                if not lightObject:
                    objectValue.add_item(paramName, value)
            else:
                cast.analysers.log.debug('Object with several same names : ' + paramName.get_name())
        cmpt += 1
    interpreter.end_object_destructuration()
    return objectValue

def parse_bracketed_block(interpreter, token, tokens = None, bFullParsing = True, lightObject = None, functionNameIdentifier = None):

    block = interpreter.start_bracketed_block(token, lightObject)
    if bFullParsing:
        cmpt = 1
        tokensList = parse_list(token)
        for value in tokensList:

            if value and type(value) is list:
                if (isinstance(value[0], Identifier) or isinstance(value[0], BracketedIdentifier)) and value[0].is_identifier() and isinstance(value[1], ParenthesedBlock):
                    valueTokens = Lookahead(TokenIterator(value))
                    fcall = parse_function_call(interpreter, value[0], value[1], valueTokens, bFullParsing)
                    interpreter.add_list_value(fcall)
                elif isinstance(value[0], Token) and value[0].text == 'new':
                    try:
                        valueTokens = Lookahead(TokenIterator(value))
                        expr = parse_any_expression(interpreter, valueTokens, None, bFullParsing, None)
                        if expr and len(expr.elements) == 1:
                            elt = expr.elements[0]
                            interpreter.add_list_value(elt)
                            elt.parent = block
                        else:
                            interpreter.add_list_value(None)
                    except:
                        cast.analysers.log.debug(str(traceback.format_exc()))
                        interpreter.add_list_value(None)
                else:
                    interpreter.add_list_value(None)
                cmpt += 1
                continue
            
            if isinstance(value, FunctionBlock) or isinstance(value, NewFunctionBlock):
                if functionNameIdentifier:
                    fname = Identifier(None, functionNameIdentifier.get_name() + '_' + str(cmpt))
                else:
                    fname = None 
                token = value
                value = parse_function(interpreter, fname, value, False, None, True, None)
                if isinstance(token, NewFunctionBlock):
                    value.set_function_constructor()
                    
                interpreter.add_list_value(value)
            elif not type(value) is list:
                value = parse_token(interpreter, value, tokens, None, True, None)
                interpreter.add_list_value(value)
            cmpt += 1
    interpreter.end_bracketed_block()
    return block

def parse_function(interpreter, functionNameIdentifier, token, function_is_statement, leftOperandAssignment, bFullParsing, lightFunc, funcDirectlyCalled = False):
        
    fname = None
    exportDefault = False
    export = False
    children = token.get_children()
    tok = get_next_token(children)
    try:
        if tok.text == 'export':
            export = True
            tok = get_next_token(children)
        if tok.text == 'default':
            exportDefault = True
            tok = get_next_token(children)
        if tok.text == 'new':
            tok = get_next_token(children)
    except:
        pass
    if functionNameIdentifier and not export:
        fname = functionNameIdentifier.get_name()
    else:
        tok = children.look_next()
        if isinstance(tok, Token) and is_token_subtype(tok.type, Name):
            tok = get_next_token(children)
            fname = tok.name
    function = None
    if leftOperandAssignment:
        function = interpreter.start_function(fname, leftOperandAssignment.get_fullname(), token, function_is_statement, lightFunc, funcDirectlyCalled, False, exportDefault)
    else:
        function = interpreter.start_function(fname, (functionNameIdentifier.get_prefix_internal() if functionNameIdentifier and functionNameIdentifier.is_identifier() else None), token, function_is_statement, lightFunc, funcDirectlyCalled, False, exportDefault)
    
    if bFullParsing:
        parenthesedBlock = get_next_token(children)
        while not isinstance(parenthesedBlock, ParenthesedBlock):
            parenthesedBlock = get_next_token(children)
        parenthesedParameters = parenthesedBlock.get_children()
        tok = get_next_token(parenthesedParameters)
        while tok and tok.get_text() != '(':
            tok = get_next_token(parenthesedParameters)
        interpreter.start_function_parameters()
        tok = parse_next_token(interpreter, parenthesedParameters, bFullParsing)
        commaEncontered = True
        while tok:
            if tok.get_text() == ')':
                break
            if commaEncontered:
                interpreter.add_parameter(None, tok)
                commaEncontered = False
            tok = parenthesedParameters.look_next()
            if tok.get_text() == ',':
                commaEncontered = True
                next(parenthesedParameters)
            tok = parse_next_token(interpreter, parenthesedParameters, bFullParsing)
        interpreter.end_function_parameters()
    else:
        get_next_token(children)
    
    bracketedBlock = get_next_token(children)
    if bracketedBlock:
        parse_statements(interpreter, bracketedBlock.get_children(), None, bFullParsing, leftOperandAssignment)

    interpreter.end_function()
    return function
    
def parse_arrow_function(interpreter, functionNameIdentifier, tokenList, function_is_statement, leftOperandAssignment, bFullParsing, lightFunc):
        
    function = None
    fname = None
    if functionNameIdentifier:
        fname = functionNameIdentifier.get_name()

    parametersPositionInTokenList = 0
    lastToken = tokenList[-1]
    try:
        if isinstance(lastToken, Token) and is_token_subtype(lastToken.type, Punctuation) and lastToken.get_text() == ';':
            ast = tokenList[:-1]
        else:
            ast = tokenList
    except:
        ast = tokenList
    firstToken = tokenList[0]
    try:
        if (isinstance(firstToken, Token) and firstToken.text == 'async' ) or ( firstToken.is_identifier() and firstToken.get_fullname() == 'async'):
            parametersPositionInTokenList = 1
            ast = ast[1:]
    except:
        pass
    if leftOperandAssignment and leftOperandAssignment.get_name() != fname:
        function = interpreter.start_arrow_function(fname, leftOperandAssignment.get_fullname(), ast, function_is_statement, lightFunc)
    else:
        function = interpreter.start_arrow_function(fname, None, ast, function_is_statement, lightFunc)
    
    if bFullParsing:
        headers = tokenList[parametersPositionInTokenList]
        interpreter.start_function_parameters()
        parenthesedBlock = None
        if isinstance(headers, ParenthesedBlock):
            parenthesedBlock = headers
        elif isinstance(headers, AstToken) and isinstance(headers.tokens[0], ParenthesedBlock):
            parenthesedBlock = headers.tokens[0]
        if parenthesedBlock:
            headers = parenthesedBlock.get_children()
            tok = get_next_token(headers)
            while tok and tok.get_text() != '(':
                tok = get_next_token(headers)
            tok = parse_next_token(interpreter, headers, bFullParsing)
            commaEncontered = True
            while tok:
                if tok.get_text() == ')':
                    break
                if commaEncontered:
                    interpreter.add_parameter(None, tok)
                    commaEncontered = False
                tok = headers.look_next()
                if tok.get_text() == ',':
                    commaEncontered = True
                    next(headers)
                tok = parse_next_token(interpreter, headers, bFullParsing)
        else:
            interpreter.add_parameter(None, headers)
        interpreter.end_function_parameters()
    
#     parse_statements(interpreter, tokenList[2:], None, bFullParsing, leftOperandAssignment)
    exprTokens = ast[2:]
    if len(exprTokens) >= 1 and isinstance(exprTokens[0], CurlyBracketedBlock):  # v => {...}
        ltokens = list(exprTokens[0].get_children())
        tokens = Lookahead(TokenIterator(ltokens[1:-1]))
        parse_statements(interpreter, tokens, None, bFullParsing, leftOperandAssignment)
    elif len(exprTokens) >= 1 and isinstance(exprTokens[0], ParenthesedBlock) and not (len(exprTokens) >= 2 and isinstance(exprTokens[1], Token) and token_is_arrow(exprTokens[1])):  # v => (...) but not v => (param1,param2) =>
        ltokens = list(exprTokens[0].get_children())
        tokens = Lookahead(TokenIterator(ltokens[1:-1]))
#         parse_statements(interpreter, tokens, None, bFullParsing, leftOperandAssignment)
        if bFullParsing or isinstance(ltokens[1], CurlyBracketedBlock): 
            expr = parse_expression(interpreter, tokens, bFullParsing, True, leftOperandAssignment)
            try:
                if expr.is_function_call():
                    function.add_statement(expr)
            except:
                cast.analysers.log.debug(str(traceback.format_exc()))
        pass
    elif bFullParsing:
        if len(exprTokens) == 1 and isinstance(exprTokens[0], AstToken) and isinstance(exprTokens[0].tokens[0], ParenthesedBlock):  # v => (...)
            ltokens = list(exprTokens[0].tokens[0].get_children())
            tokens = Lookahead(TokenIterator(ltokens[1:-1]))
        else:
            tokens = Lookahead(TokenIterator(exprTokens))
        expr = parse_expression(interpreter, tokens, bFullParsing)
        function.add_statement(expr)

    interpreter.end_function()
    return function

def parse_class(interpreter, classNameIdentifier, token, class_is_statement, leftOperandAssignment, bFullParsing, lightClass):
        
    className = None
    exportDefault = False
    if classNameIdentifier:
        className = classNameIdentifier.get_name()
    else:
        children = token.get_children()
        tok = get_next_token(children)
        try:
            if tok.text == 'export':
                tok = get_next_token(children)
            if tok.text == 'default':
                exportDefault = True
                tok = get_next_token(children)
        except:
            pass
        tok = children.look_next()
        if isinstance(tok, Token) and is_token_subtype(tok.type, Name):
            tok = get_next_token(children)
            className = tok.name
    cl = None
    if leftOperandAssignment:
        cl = interpreter.start_class(className, leftOperandAssignment.get_fullname(), token, class_is_statement, lightClass, exportDefault)
    else:
        cl = interpreter.start_class(className, (classNameIdentifier.get_prefix_internal() if classNameIdentifier else None), token, class_is_statement, lightClass, exportDefault)
    
    headers = token.get_body()
    tok = get_next_token(headers)
    while tok and tok.get_text() != 'extends':
        tok = get_next_token(headers)
    if tok:
        tok = get_next_token(headers)
        try:
            interpreter.set_class_inheritance(tok)
        except:
            pass
        
    body = list(token.get_body())[-1]
    parse_statements(interpreter, body.get_children(), None, bFullParsing, leftOperandAssignment)

    interpreter.end_class()
    return cl

def parse_method(interpreter, token, bFullParsing):
        
    tokenName = None
    parenthesedBlock = None
    body = None
    static = False
    for tok in token.get_children():
        if isinstance(tok, ParenthesedBlock):
            methodname = tokenName.text
            method = interpreter.start_method(methodname, token, static)
            parenthesedBlock = tok
        elif isinstance(tok, CurlyBracketedBlock):
            body = tok
        else:
            tokenName = tok
            if tok.text == 'static':
                static = True
    
    if bFullParsing:
        parametersToken = parenthesedBlock.get_children()
        tok = get_next_token(parametersToken)
        while tok and tok.get_text() != '(':
            tok = get_next_token(parametersToken)
        interpreter.start_function_parameters()
        tok = parse_next_token(interpreter, parametersToken, bFullParsing)
        commaEncontered = True
        while tok:
            if tok.get_text() == ')':
                break
            if commaEncontered:
                interpreter.add_parameter(None, tok)
                commaEncontered = False
            tok = parametersToken.look_next()
            if tok.get_text() == ',':
                commaEncontered = True
                next(parametersToken)
            tok = parse_next_token(interpreter, parametersToken, bFullParsing)
        interpreter.end_function_parameters()
    
        parse_statements(interpreter, body.get_children(), None, bFullParsing)

    interpreter.end_method()
    return method

def parse_token(interpreter, token, tokens, leftOperandAssignment, bFullParsing, lightObject, functionNameIdentifier = None):
    
    global LAST_TOKEN_PARSED_TO_NONE
    LAST_TOKEN_PARSED_TO_NONE = None
    if isinstance(token, Identifier) or isinstance(token, BracketedIdentifier) or (isinstance(token, Token) and is_token_subtype(token.type, Name)):
        if tokens:
            if isinstance(token, Identifier) or isinstance(token, BracketedIdentifier):
                identifier = token
            else:
                identifier = get_identifier(None, token, tokens)

            try:
                nextToken = tokens.look_next()
            except StopIteration:
                return identifier
            if isinstance(nextToken, ParenthesedBlock) or ( isinstance(nextToken, Token) and nextToken.get_text().startswith('`') ):
                fcall = parse_function_call(interpreter, identifier, nextToken, tokens, bFullParsing, False)
#                 get_next_token(tokens)
                return fcall
            else:
                if isinstance(token, Identifier) or isinstance(token, BracketedIdentifier):
                    if interpreter:
                        interpreter.add_identifier(token)
                    return token
                else:
                    ident = get_identifier(None, token, tokens)
                    if interpreter:
                        interpreter.add_identifier(ident)
                    return ident
    elif (isinstance(token, Token) and is_token_subtype(token.type, String)):
        if token.get_text()[:1] in ["'", '"', '`']:
            s = AstString(token, None, token.get_text()[1:-1])
        else:
            s = AstString(token, None, token.get_text())
        interpreter.add_string(s)
        return s
    elif isinstance(token, FunctionBlock) or isinstance(token, NewFunctionBlock):
        function = parse_function(interpreter, functionNameIdentifier, token, False, None, bFullParsing, lightObject)
        if isinstance(token, NewFunctionBlock):
            function.set_function_constructor()
        return function
    elif isinstance(token, CurlyBracketedBlock):
        block = parse_object_value(interpreter, token, tokens, leftOperandAssignment, None, bFullParsing, lightObject)
        return block
    elif isinstance(token, BracketedBlock):
        block = parse_bracketed_block(interpreter, token, tokens, bFullParsing, lightObject, functionNameIdentifier)
        return block
    elif (isinstance(token, Token) and is_token_subtype(token.type, Operator)):
        return parse_operator_token(interpreter, token, tokens)
    elif (isinstance(token, Token) and is_token_subtype(token.type, Keyword) and token.get_text() == 'in'):
        return parse_operator_token(interpreter, token, tokens)
    elif isinstance(token, Token) and is_token_subtype(token.type, Punctuation) and token.text == '<':
        return parse_jsx_token(interpreter, token, tokens)
    elif isinstance(token, ParenthesedBlock) and len(list(token.get_children())) >= 2 and isinstance(list(token.get_children())[1], Token) and is_token_subtype(list(token.get_children())[1].type, Punctuation) and list(token.get_children())[1].text == '<':
        return parse_jsx_token(interpreter, list(token.get_children())[1], Lookahead(TokenIterator(list(token.get_children())[2:-1])))
#     elif isinstance(token, ParenthesedBlock):
#         childrenList = list(token.get_children())
#         if len(childrenList) >= 2:
#             secondElement = childrenList[1]
#             if isinstance(secondElement, Token) and is_token_subtype(secondElement.type, Punctuation) and secondElement.text == '<':
#                 return parse_jsx_token(interpreter, secondElement, Lookahead(TokenIterator(childrenList[2:-1])))
    elif not isinstance(token, Token) or not is_token_subtype(token.type, Punctuation):
        return parse_unknown_token(interpreter, token, tokens)
    LAST_TOKEN_PARSED_TO_NONE = token
    return None

def parse_unknown_token(interpreter, token, tokens):
        
        astToken = interpreter.start_unknown_token(token)
        interpreter.end_unknown_token(token)
        return astToken

def parse_jsx_token(interpreter, token, tokens, astExprParent = None):
        
    try:
        nextToken = tokens.look_next()
        if not isinstance(nextToken, Token) or not is_token_subtype(nextToken.type, Name.Tag):
            return None
        astExpr = interpreter.start_jsx_expression(token)
        token = next(tokens)  # we are on first tag
        astExpr.add_token(token)
        astExpr.set_tag(token)
        attributeName = None
        
        while True:
            try:
                next2 = look_next_tokens(tokens, 2)
                if len(next2) < 2:
                    if len(next2) == 1:
                        astExpr.add_token(next2[0])
                    interpreter.end_jsx_expression()
                    return astExpr
                
                if isinstance(next2[0], Token) and is_token_subtype(next2[0].type, Punctuation) and next2[0].text == '/' and isinstance(next2[1], Token) and is_token_subtype(next2[1].type, Punctuation) and next2[1].text == '>':
                    token = next(tokens)  # we are on /
                    astExpr.add_token(token)
                    token = next(tokens)  # we are on >
                    astExpr.add_token(token)
                    interpreter.end_jsx_expression()
                    return astExpr
                    
                elif isinstance(next2[0], Token) and is_token_subtype(next2[0].type, Punctuation) and next2[0].text == '<' and isinstance(next2[1], Token) and is_token_subtype(next2[1].type, Name.Tag):
                    token = next(tokens)  # we are on <
                    expr = parse_jsx_token(interpreter, token, tokens, astExpr)
                    astExpr.subExpressions.append(expr)
#                     astExpr.add_token(token)
#                     token = next(tokens)  # we are on tag
#                     astExpr.add_token(token)
                    
                elif isinstance(next2[0], Token) and is_token_subtype(next2[0].type, Punctuation) and next2[0].text == '/' and isinstance(next2[1], Token) and is_token_subtype(next2[1].type, Name.Tag):
                    token = next(tokens)  # we are on /
                    astExpr.add_token(token)
                    token = next(tokens)  # we are on tag
                    astExpr.add_token(token)
                    token = next(tokens)  # we are on >
                    astExpr.add_token(token)
                    interpreter.end_jsx_expression()
                    return astExpr
                    
                elif isinstance(next2[0], Token) and is_token_subtype(next2[0].type, Name.Attribute) and isinstance(next2[1], Token) and next2[1].text == '=':
                    token = next(tokens)  # we are on attribute name
                    attributeName = token.text
                    astExpr.add_token(token)
                    token = next(tokens)  # we are on =
                    astExpr.add_token(token)
                    
                elif isinstance(next2[0], CurlyBracketedBlock):
                    token = next(tokens)
                    astExpr.add_token(token)
                    expr = parse_expression(interpreter, Lookahead(TokenIterator(list(next2[0].get_children())[1:-1])), True)
                    if expr:
                        astExpr.subExpressions.append(expr)
                    pass
                
                else:
                    token = next(tokens)
                    if attributeName:
                        attributeValueTokens = [ token ]
                        token = tokens.look_next()
                        while is_token_subtype(token.type, String):
                            attributeValueTokens.append(token)
                            token = next(tokens)
                            token = tokens.look_next()
                        htmlTextWithPos = astExpr.add_attribute_value(attributeName, attributeValueTokens)
                        text = htmlTextWithPos.text.strip()
                        if text.startswith('{'):
                            interpreter.add_unresolved_identifier(htmlTextWithPos, None)
                        attributeName = None
                    astExpr.add_token(token)
                    
            except StopIteration:
                break
        
        interpreter.end_jsx_expression()
        return astExpr
        
    except StopIteration:
        return None

def parse_operator_token(interpreter, token, tokens):
        
    astToken = interpreter.start_operator_token(token)
    interpreter.end_operator_token(token)
    return astToken
    
def parse_function_call(interpreter, identifier, parenthesedBlock, tokens, bFullParsing, isStatement = True):
    
    if not bFullParsing:
        return None
    
    functionCall = interpreter.start_function_call(identifier, parenthesedBlock, isStatement)
    if identifier.is_await() and functionCall:
        functionCall.set_is_await(True)
    
    toks = []
    for tok in identifier.tokens:
        toks.append(tok)
    
    parenthesedBlocks = []
    while parenthesedBlock and (isinstance(parenthesedBlock, ParenthesedBlock) or (isinstance(parenthesedBlock, Token) and is_token_subtype(parenthesedBlock.type, String))):
        parenthesedBlocks.append(parenthesedBlock)
        toks.append(parenthesedBlock)
        next(tokens)
        try:
            parenthesedBlock = tokens.look_next()
        except:
            parenthesedBlock = None
        
    ident = identifier
    
    while toks:
        if not isinstance(ident, Token) and not isinstance(ident, MethodBlock):
            parse_function_call_part(interpreter, ident, parenthesedBlocks, tokens, toks)
    
        token = parenthesedBlock
        if token and token.get_text() == '.':
            next(tokens)
            ident = get_next_token(tokens)
        else:
            break
        toks = []
        try:
            for tok in ident.tokens:
                toks.append(tok)
        except:
            # ident id not an identifier
            toks.append(ident)
        try:
            parenthesedBlock = tokens.look_next()
        except:
            parenthesedBlock = None
        
        parenthesedBlocks = []
        while parenthesedBlock and (isinstance(parenthesedBlock, ParenthesedBlock) or (isinstance(parenthesedBlock, Token) and is_token_subtype(parenthesedBlock.type, String))):
            parenthesedBlocks.append(parenthesedBlock)
            toks.append(parenthesedBlock)
            next(tokens)
            try:
                parenthesedBlock = tokens.look_next()
            except:
                parenthesedBlock = None
    
    interpreter.end_function_call()
    if not parenthesedBlocks:
        try:
            next(tokens)
        except:
            pass
    
    return functionCall
    
def parse_define(interpreter, identifier, parenthesedBlock, tokens, bFullParsing, isStatement = True):
    
#     if not bFullParsing:
#         return None
    
#     define = interpreter.start_define(identifier)
    """
    parenthesedBlock should be ([ ... ], function () {}) or ('...', [ ... ], function () {}) 
    """
    tokens = parenthesedBlock.get_children()
    token = get_next_token(tokens)
    bracketedFound = False
    while token:
        if isinstance(token, BracketedBlock):
            bracketedFound = True
        elif isinstance(token, FunctionBlock):
            if not bracketedFound:
                break
            break
        token = get_next_token(tokens)
    pass
    
def parse_function_call_part(interpreter, identifier, parenthesedBlocks, tokens, toks):

    interpreter.start_function_call_part(identifier, toks)
    if parenthesedBlocks:
        parse_parameters(interpreter, parenthesedBlocks[0], identifier)
    
    if len(parenthesedBlocks) > 1:
        rang = 0
        for block in parenthesedBlocks[1:]:   # f()()
            parse_parameters(interpreter, block, None, rang)
            rang += 1
    
    interpreter.end_function_call_part()

#  (function() {
#  }).call(this);
# or
#  (function() {
#  })(this);
# or
#  var v = (function() {
#  })();
def parse_js_function_call(interpreter, tokens, bFullParsing, bExpression = False, leftOperandAssignment = None):
    
    firstToken = get_next_token(tokens)  # ParenthesedBlock
    try:
        token = next(tokens)
    except StopIteration:
        pass
    if isinstance(token, ParenthesedBlock):
        callToken = None
        parenthesedBlock = token
    else:
        callToken = None
        parenthesedBlock = None
        try:
            callToken = next(tokens)
            parenthesedBlock = next(tokens)
        except StopIteration:
            pass

    if not bFullParsing and interpreter.jsContent.is_module():
        get_next_token(tokens)
        return None

    functionCall = None
    if True:
        if bFullParsing:
            functionCall = interpreter.start_js_function_call(None, token, callToken, parenthesedBlock, bExpression)
        for child in firstToken.get_children():
            if isinstance(child, FunctionBlock):
                func = parse_function(interpreter, None, child, False, leftOperandAssignment, bFullParsing, None, True)
                if bFullParsing:
                    functionCall.function = func
                break
        if bFullParsing:
            parse_parameters(interpreter, parenthesedBlock)
        if bFullParsing:
            interpreter.end_js_function_call()
    return functionCall

def parse_parameters(interpreter, parenthesedBlock, functionNameIdentifier = None, rang = -1):
    
    parameters = []
    if not parenthesedBlock:
        return parameters
    
    parameters = []
    parameterTokenList = None
    
    if isinstance(parenthesedBlock, Token) and is_token_subtype(parenthesedBlock.type, String):
        parameterTokenList = [ parenthesedBlock ]
        parameters.append(parameterTokenList)
        interpreter.start_parameter()
        build_expression(interpreter, parameterTokenList)
        interpreter.end_parameter()
        return parameters
    
    tokens = parenthesedBlock.get_children()
    get_next_token(tokens)
    token = get_next_token(tokens)
    cmpt = 1
    isArrowFunction = False
    while token:
        parse_token_last_param = None
        if isinstance(token, Token) and is_token_subtype(token.type, Punctuation) and token.get_text() == ',':
            parameterTokenList = []
            parameters.append(parameterTokenList)
            isArrowFunction = False
            cmpt += 1
        else:
            if not parameters:
                parameterTokenList = []
                parameters.append(parameterTokenList)
            if isinstance(token, FunctionBlock) or isinstance(token, NewFunctionBlock):
                if functionNameIdentifier:
                    fname = functionNameIdentifier.get_name() + '_PARAM_' + str(cmpt)
                    if functionNameIdentifier.get_prefix():
                        fname = functionNameIdentifier.get_prefix() + '_' + fname
                    fname = Identifier(None, fname)
                    parse_token_last_param = fname
                else:
                    fname = None
            elif isinstance(token, BlockStatement):
                if functionNameIdentifier:
                    fname = functionNameIdentifier.get_name() + '_PARAM_' + str(cmpt)
                    if functionNameIdentifier.get_prefix():
                        fname = functionNameIdentifier.get_prefix() + '_' + fname
                    fname = Identifier(None, fname)
                    parse_token_last_param = fname
                else:
                    fname = None
            else:
                try:
                    if isinstance(token, Token) and is_token_subtype(token.type, Operator) and token.get_text() == '=>':
                        isArrowFunction = True
                except:
                    pass
            if isArrowFunction and isinstance(token, CurlyBracketedBlock):  # v => { ... }
                parameterTokenList.append(token)
            else:
                try:
                    if token.get_name() == 'async':
                        nextTokens = look_next_tokens(tokens, 2)
                        if nextTokens[1].text == '=>':
                            token = get_next_token(tokens)  # skip async token
                            isArrowFunction = True
                except:
                    pass
                parameterTokenList.append(parse_token(interpreter, token, tokens, None, True, None, parse_token_last_param))
        token = get_next_token(tokens)
    if parameterTokenList and parameterTokenList[-1] == None:
        parameterTokenList.pop()
        
    cmpt = 1
    for paramTokens in parameters:

        interpreter.start_parameter(rang)
        build_expression(interpreter, paramTokens)
        interpreter.end_parameter()
        cmpt += 1
    
    return parameters

def get_next_token(tokens, inFuncCall = False, precedingToken = None):
    try:
        token = get_next_identifier(None, tokens, inFuncCall, precedingToken)
        if not token:
            token = next(tokens)
        return token
    except StopIteration:
        return None
    except:
        return None

def parse_next_token(interpreter, tokens, bFullParsing, leftOperandAssignment = None):
    try:
        token = get_next_token(tokens)
        if not token:
            return None
        return parse_token(interpreter, token, tokens, leftOperandAssignment, bFullParsing, None)
    except StopIteration:
        return None

def get_blocks_with_type(tokens, ttype, result, recursive = False):
 
    try:
        token = next(tokens)
        
        while token:
            if type(token) is ttype:
                result.append(token)
            if recursive and isinstance(token,BlockStatement):
                children = token.get_children()
                get_blocks_with_type(children, ttype, result, recursive)
            token = next(tokens)

        return result
    
    except StopIteration:
        return result

def next_token_is_identifier(tokens):
    
    try:
        token = tokens.look_next()
        if not isinstance(token, Token):
            return False
        
        if isinstance(token, Token) and (is_token_subtype(token.type, Text) or is_token_subtype(token.type, String)):
            return True
        
        if (not (isinstance(token, Token) and is_token_subtype(token.type, Name)) and not (isinstance(token, Token) and (is_token_subtype(token.type, Keyword)) and (token.get_text() in ['this', 'super', 'delete', 'each']))):
            return False
        
        return True

    except StopIteration:
        return False

def token_is_identifier(token, token2 = None, inFuncCall = False, precedingToken = None):
    
    if isinstance(token, Token) and is_token_subtype(token.type, Name):
        return True
    
    if isinstance(token, Token) and is_token_subtype(token.type, Keyword) and isinstance(token2, ParenthesedBlock) and token.get_text() in ['delete', 'define', 'catch', 'each', 'finally']:
        return True

    if isinstance(token, Token) and is_token_subtype(token.type, Keyword) and token.get_text() in ['this', 'super']:
        return True
    
    if not inFuncCall and token2 and isinstance(token, ParenthesedBlock) and token2.get_text() == '.':
        children = token.get_children()
        get_next_token(children)
        firstChild = get_next_token(children)
        if isinstance(firstChild, FunctionBlock) or isinstance(firstChild, NewFunctionBlock) or (precedingToken and isinstance(precedingToken, ParenthesedBlock)):
            return False
        return True
    
    if not inFuncCall and token2 and isinstance(token, Token) and is_token_subtype(token.type, String) and token2.get_text() == '.':
        return True
    
    return False

def next_token_is_block(tokens):
    
    try:
        token = tokens.look_next()
        if isinstance(token, BlockStatement):
            return token
        
        return None

    except StopIteration:
        return None

# if next token is identifier, returns identifier and go to the last position of identifier
# if not, returns None and keeps its position  
def get_next_identifier(parent, tokens, inFuncCall = False, precedingToken = None):
    
    next4 = None
    bAwait = False
    try:
        next4 = look_next_tokens(tokens, 4)
        if isinstance(next4[0], Token) and (next4[0].text == 'await' or next4[0].text == 'async' and len(next4) >= 2 and isinstance(next4[1], MethodBlock)):
            next4.remove(next4[0])
            tok = next(tokens)
            bAwait = True
#         token = tokens.look_next()
        if len(next4) >= 2:
            if not token_is_identifier(next4[0], next4[1], inFuncCall, precedingToken):
                return None
        else:
            if not token_is_identifier(next4[0], None, inFuncCall):
                return None
    except:
        return None
    
    identifier = Identifier()
    if bAwait:
        identifier.tokens.append(tok)
    
    # case of 'mystring'.replace()
    if len(next4) == 4 and isinstance(next4[0], Token) and is_token_subtype(next4[0].type, String) and  next4[1].get_text() == '.' and isinstance(next4[2], Token) and is_token_subtype(next4[2].type, Name) and  isinstance(next4[3], ParenthesedBlock):
        identifier.set_is_func_call(True)

    tok = next(tokens) # we are on the token at the beginning of identifier
    
    try:
        
        identifier.parent = parent
        
        if isinstance(tok, Token) and (is_token_subtype(tok.type, Text) or is_token_subtype(tok.type, String)):
            nextTok = tokens.look_next()
            if nextTok.get_text() == '.':
                next(tokens)
                tok = next(tokens)
            identifier.set_name(tok.get_text(),tok.get_text()) 
            identifier.tokens.append(tok)
            identifier.is_text = True
            return identifier
                
        cmpt = 0
        
        while True:
                        
            identifier.tokens.append(tok)
#             fullname = identifier.get_fullname()
            fullname = identifier.get_fullname_internal()
            
            if fullname:
                if isinstance(fullname, ParenthesedBlock):
                    identifier.set_prefix_internal(fullname)
                else:
                    identifier.set_prefix(fullname)

            if not fullname:
                if isinstance(tok, ParenthesedBlock):
                    fullname = tok
                else:
                    fullname = tok.get_text()
            else:
                if isinstance(fullname, ParenthesedBlock):
                    fullname = ''
                else:
                    fullname += '.'
                fullname += tok.get_text()
            if tok.get_text() == 'prototype':
                identifier.set_prototype_true()
                
            identifier.set_name(tok.get_text(), fullname)
#             if identifier.is_bracketed_identifier():
#                 identifier.update_bracketed_name()
            
            ## look 2 next tokens if .name
            next2 = look_next_tokens(tokens, 2)
            if not next2 or len(next2) == 0:
                return identifier
            if len(next2) == 1:
                if type(next2[0]) is ParenthesedBlock:
                    identifier.set_is_func_call(True)
                return identifier
            if isinstance(next2[0], Token) and is_token_subtype(next2[0].type, String) and next2[0].get_text().startswith('`'):
                identifier.set_is_func_call(True)
                return identifier
            if not isinstance(next2[0], Token):
                if type(next2[0]) is ParenthesedBlock:
                    identifier.set_is_func_call(True)
                    if bAwait:
                        identifier.set_is_await(True)
                    return identifier
                elif type(next2[0]) is BracketedBlock:
                    tok = next(tokens)
                    next2 = look_next_tokens(tokens, 2)
                    identifier.tokens.append(tok)
                    identifier = BracketedIdentifier(identifier)
                    if isinstance(next2[0], ParenthesedBlock):
                        identifier.set_is_func_call(True)
                    identifier.bracketedExpression = tok
                else:
                    return identifier

            if isinstance(next2[0], Token) and next2[0].get_text() == '.':
                if not isinstance(next2[1], Token):
                    return identifier
                if not (isinstance(next2[1], Token) and is_token_subtype(next2[1].type, Name)) and not (isinstance(next2[1], Token) and is_token_subtype(next2[1].type, Keyword)):
                    return identifier
                tok = next(tokens)
            else:
                return identifier
            
            tok = next(tokens)
            cmpt += 1
        
        return identifier
    
    except StopIteration:
        return identifier
    
def get_identifier(parent, token, tokens):
    
    if not token_is_identifier(token):
        return None
    
    identifier = Identifier()
    tok = token
    
    try:
        
        identifier.parent = parent
        
        if isinstance(tok, Token) and (is_token_subtype(tok.type, Text) or is_token_subtype(tok.type, String)):
            identifier.set_name(tok.get_text(),tok.get_text()) 
            identifier.tokens.append(tok)
            identifier.is_text = True
            return identifier
                
        cmpt = 0
        
        while True:
                        
            identifier.tokens.append(tok)
            if cmpt == 1:
                identifier.set_prefix(identifier.get_name())

            fullname = identifier.get_fullname_internal()
            if not identifier.get_fullname_internal():
                fullname = tok.get_text()
            else:
                fullname += '.'
                fullname += tok.get_text()
            identifier.set_name(tok.get_text(), fullname)
            
            ## look 2 next tokens if .name
            next2 = look_next_tokens(tokens, 2)
            if not next2 or len(next2) == 0:
                return identifier
            if len(next2) == 1:
                if type(next2[0]) is ParenthesedBlock:
                    identifier.set_is_func_call(True)
                return identifier
            if not isinstance(next2[0], Token):
                if type(next2[0]) is ParenthesedBlock:
                    identifier.set_is_func_call(True)
                return identifier

            if isinstance(next2[0], Token) and next2[0].get_text() == '.':
                if not isinstance(next2[1], Token):
                    return identifier
                if not (isinstance(next2[1], Token) and is_token_subtype(next2[1].type, Name)):
                    return identifier
                tok = next(tokens)
            else:
                next(tokens)
                return identifier
            
            tok = next(tokens)
            cmpt += 1
        
        return identifier
    
    except StopIteration:
        return identifier
    
def look_next_tokens(tokens, nb):
    
    result = []
    tokens.start_lookahead()
    try:
        for _ in range(nb):
            result.append(next(tokens))
        return result
    except StopIteration:
        return result
    finally:
        tokens.stop_lookahead()

def create_token_from_list(tokens, res_tokens = None):

    if len(tokens) == 1:
        return tokens[0]
    
    if len(tokens) > 1:
        for token in tokens:
            try:
                if isinstance(token, Token) and is_token_subtype(token.type, String):
                    res_tokens.append(token)
                else:
                    if res_tokens != None:
                        res_tokens.append(token)
            except:
                pass
            
    return None

# parses a javascript object of this kind:
# {
#    'param1' : token1,
#    'param2' : token2
#    ...
# }
# and put it in 2 arrays: tokenParameters for parameters (array of tokens, 1 token for each param), 
#                         tokenValues for values (array of tokens or tokens lists, 1 token or a list of tokens for each value).
def parse_object(token, nameParameters, tokenParameters, tokenValues):
    
    if not isinstance(token, CurlyBracketedBlock):
        return 0
    
    tokens = token.get_children()
    beforeDbPoints = True
    get_next_token(tokens)  # we are on {
    tok = get_next_token(tokens)
    valueTokens = []
    paramNameFound = False
    while tok:
        if tok.get_text() == '}':
            break
        elif tok.get_text() == ',':
            res_tokens = []
            newtoken = create_token_from_list(valueTokens, res_tokens)
            if newtoken:
                tokenValues.append(newtoken)
            elif res_tokens:
                tokenValues.append(res_tokens)
            else:
                tokenValues.append(None)
            valueTokens.clear()
            beforeDbPoints = True
            paramNameFound = False
        elif tok.get_text() == ':':
            if not beforeDbPoints:
                valueTokens.append(tok)
            else:
                beforeDbPoints = False
                paramNameFound = False
        else:
            if beforeDbPoints:
                if not paramNameFound:
                    try:
                        try:
                            if tok.is_identifier():
                                astTok = tok.tokens[0]
                            else:
                                astTok = tok
                        except:
                            astTok = tok
#                         if tok.get_text()[0] == '"' or tok.get_text()[0] == "'":
#                             nameParameters.append(Identifier(None, tok.get_text()[1:-1], astTok))
#                         else:
#                             nameParameters.append(Identifier(None, tok.get_text(), astTok))
                        if isinstance(tok, MethodBlock):
                            children = list(tok.get_children())
                            cmpt = 0
                            while not isinstance(children[cmpt], ParenthesedBlock):
                                cmpt += 1
                            astTok = children[cmpt-1]
#                             if astTok.get_text() == '=':
#                                 astTok = children[cmpt-2]
                            nameParameters.append(Identifier(None, astTok.get_text(), astTok))
                        elif tok.get_text() and ( tok.get_text()[0] == '"' or tok.get_text()[0] == "'" ):
                            nameParameters.append(Identifier(None, tok.get_text()[1:-1], astTok))
                        else:
                            if tok.get_text():
                                nameParameters.append(Identifier(None, tok.get_text(), astTok))
                            else:
                                nameParameters.append(Identifier(None, 'UNKNOWN', astTok))
                        tokenParameters.append(tok)
                        paramNameFound = True
                    except:
                        cast.analysers.log.debug('Unsupported syntax')
                        nameParameters.append(Identifier(None, '', tok))
                        tokenParameters.append(token)
            else:
                valueTokens.append(tok)
        
        tok = get_next_token(tokens)
        
    res_tokens = []
    newtoken = create_token_from_list(valueTokens, res_tokens)
    if newtoken:
        tokenValues.append(newtoken)
    elif res_tokens:
        tokenValues.append(res_tokens)
    else:
        tokenValues.append(None)
    valueTokens.clear()

# parses a javascript list of this kind:
# [
#    token1,
#    token2
#    ...
# ]
# and put it in a list    
def parse_list(token):
    
    tokensList = []
    if not isinstance(token, BracketedBlock):
        return tokensList
    
    tokens = token.get_children()
    token = get_next_token(tokens)  # we are on [
    token = get_next_token(tokens)
    valueTokens = []
    while token:
        if token.get_text() == ']':
            break
        elif token.get_text() == ',':
            res_tokens = []
            newtoken = create_token_from_list(valueTokens, res_tokens)
            if newtoken:
                tokensList.append(newtoken)
            else:
                tokensList.append(res_tokens)
            valueTokens.clear()
        else:
            valueTokens.append(token)
        
        token = get_next_token(tokens)
       
    res_tokens = [] 
    newtoken = create_token_from_list(valueTokens, res_tokens)
    if newtoken:
        tokensList.append(newtoken)
    else:
        tokensList.append(res_tokens)
    valueTokens.clear()
    return tokensList
