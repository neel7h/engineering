from pygments.filter import Filter
# from pygments.token import is_token_subtype, String, Name, Text, Keyword, Punctuation, Operator, Literal, Error, Comment
from pygments.lexers.dotnet import CSharpLexer
from pygments.token import is_token_subtype, Punctuation, String, Name
from javascript_parser.light_parser import Parser, Statement, BlockStatement, Token, Seq, TokenIterator, Lookahead, Any, Optional, Or, Term
from cast.analysers import Bookmark
import cast.analysers.ua
import os
from collections import OrderedDict

class ControllerMethodCall:
    
    def __init__(self, methodName, controllerName, ast, httpType = None, hasParameter = False):
        
        self.controllerName = controllerName
        self.methodName = methodName
        self.httpType = httpType
        self.ast = ast
        self.hasParameter = hasParameter

class ViewCall:
    
    def __init__(self, viewName, ast):

        if viewName.endswith('.cshtml'):
            self.viewPath = viewName
            self.viewName = None
        else:
            self.viewPath = None
            self.viewName = viewName
        self.ast = ast

class AnalysisResults:
    
    def __init__(self):
        
        self.controllerMethodCalls = []
        self.viewCalls = []
        
class CurlyBracketedBlock(BlockStatement):
    
    begin = Or('{', Seq('@', '{'))
    end   = '}'

class ParenthesedBlock(BlockStatement):
    
    begin = '('
    end   = ')'
    
class BracketedBlock(BlockStatement):
    
    begin = '['
    end   = ']'

class RazorTerm(Term):    

    def create_bookmark(self, file):
        return Bookmark(file, self.get_begin_line(), self.get_begin_column(), self.get_end_line(), self.get_end_column())

class RazorBlockStatement(BlockStatement):    

    def create_bookmark(self, file):
        return Bookmark(file, self.get_begin_line(), self.get_begin_column(), self.get_end_line(), self.get_end_column())

class UrlAction(RazorTerm):
    
    match = Seq(Or('@Url', 'Url'), '.', 'Action', ParenthesedBlock)

class UrlRouteUrl(RazorTerm):
    
    match = Seq(Or('@Url', 'Url'), '.', 'RouteUrl', ParenthesedBlock)
    
class AjaxActionLink(RazorTerm):
    
    match = Seq(Or('@Ajax', 'Ajax'), '.', 'ActionLink', ParenthesedBlock)
    
class HtmlActionUrl(RazorTerm):
    
    match = Seq(Or('@Html', 'Html'), '.', 'ActionUrl', ParenthesedBlock)
    
class HtmlActionLink(RazorTerm):
    
    match = Seq(Or('@Html', 'Html'), '.', 'ActionLink', ParenthesedBlock)
    
class HtmlAction(RazorTerm):
    
    match = Seq(Or('@Html', 'Html'), '.', 'Action', ParenthesedBlock)
    
class NameDotAction(RazorTerm):
    
    match = Seq(Name, '.', 'Action', ParenthesedBlock)
    
class HtmlRenderAction(RazorTerm):
    
    match = Seq(Or('@Html', 'Html'), '.', 'RenderAction', ParenthesedBlock)
    
class HtmlActionLinkWithAccess(RazorTerm):
    
    match = Seq(Or('@Html', 'Html'), '.', 'ActionLinkWithAccess', ParenthesedBlock)
    
class HtmlBeginForm(RazorTerm):
    
    match = Seq(Or('@Html', 'Html'), '.', 'BeginForm', ParenthesedBlock)
    
class AjaxBeginForm(RazorTerm):
    
    match = Seq(Or('@Ajax', 'Ajax'), '.', 'BeginForm', ParenthesedBlock)
    
class HtmlPartial(RazorTerm):
    
    match = Seq(Or('@Html', 'Html'), '.', 'Partial', ParenthesedBlock)
    
class HtmlRenderPartial(RazorTerm):
    
    match = Seq(Or('@Html', 'Html'), '.', 'RenderPartial', ParenthesedBlock)
    
class RenderPage(RazorTerm):
    
    match = Seq(Or('@RenderPage', 'RenderPage'), ParenthesedBlock)
    
class AtBlock(RazorTerm):
    
    match = Seq('@', ParenthesedBlock)
    
class ForEach(RazorBlockStatement):
    
    begin = '@foreach'
    end   = CurlyBracketedBlock
    
class AnonymousNew(RazorTerm):
    
    match = Seq('new', CurlyBracketedBlock)

def parse(text):

    if not type(text) is str:
        text = text.read()
        
#     parser = Parser(CSharpLexer, [ForEach, HtmlActionLink, HtmlAction, HtmlRenderAction, UrlAction, UrlRouteUrl, AjaxActionLink, HtmlActionLinkWithAccess, HtmlBeginForm, AjaxBeginForm, HtmlPartial, HtmlRenderPartial, RenderPage, AtBlock, HtmlActionUrl, AnonymousNew, ParenthesedBlock, CurlyBracketedBlock, BracketedBlock])
    parser = Parser(CSharpLexer, [ParenthesedBlock, CurlyBracketedBlock, BracketedBlock], [ForEach, HtmlActionLink, HtmlAction, HtmlRenderAction, UrlAction, UrlRouteUrl, AjaxActionLink, HtmlActionLinkWithAccess, HtmlBeginForm, AjaxBeginForm, HtmlPartial, HtmlRenderPartial, RenderPage, AtBlock, HtmlActionUrl, NameDotAction, AnonymousNew])

    return parser.parse(text)    

# in order to parse razor in HTML like that:
# <a href="@Url.Action("EditWeekdayColor", new { id = item.HolidayType })" class="popupLink ico">
# <table data-ajax-handler="@Url.Action("MissionItemsAjaxHandler")?missionId=@Model.MissionId">
# we replace by a blank the " before @Url. and the " after )"
def preprocess_text(text):
    
    newtext = text
    index = -1
    while '"@Url.' in newtext:
        index = newtext.find('"@Url.Action(', index+1)
        if index < 0:
            index = newtext.find('"@Url.RouteUrl(', index+1)
        if index < 0:
            break
        indexLast = newtext.find(')', index)
        if indexLast < 0:
            continue
        if newtext[indexLast+1] != '"':
            indexLast = newtext.find('"', indexLast+1)
        if indexLast < 0:
            continue
        newtext = newtext[:index] + ' ' + newtext[index+1:indexLast + 1] + ' ' + newtext[indexLast+2:]
    
    index = -1
    while '"@(Url.' in newtext:
        index = newtext.find('"@(Url.RouteUrl(', index+1)
        if index < 0:
            break
        indexLast = newtext.find('))', index)
        if indexLast < 0:
            continue
        if newtext[indexLast+1] != '"':
            indexLast = newtext.find('"', indexLast+1)
        if indexLast < 0:
            continue
        newtext = newtext[:index] + ' ' + newtext[index+1:indexLast] + ' ' + newtext[indexLast+2:]
    return newtext

def analyse(text):

    results = AnalysisResults()
    newtext = preprocess_text(text)
    for statement in parse(newtext):
        parse_statement(statement, results)
    return results

def parse_statement(statement, results, inAtBlock = False):

    parseChildren = True
    if isinstance(statement, HtmlBeginForm):
        result = parse_html_beginForm(statement)
        if result:
            results.controllerMethodCalls.append(result)
    elif isinstance(statement, AjaxBeginForm):
        result = parse_ajax_beginForm(statement)
        if result:
            results.controllerMethodCalls.append(result)
    elif isinstance(statement, UrlAction):
        result = parse_url_action(statement)
        if result:
            results.controllerMethodCalls.append(result)
    elif isinstance(statement, UrlRouteUrl):
        result = parse_url_routeUrl(statement)
        if result:
            results.controllerMethodCalls.append(result)
    elif isinstance(statement, HtmlActionLinkWithAccess):
        result = parse_html_actionLinkWithAccess(statement)
        if result:
            results.controllerMethodCalls.append(result)
    elif isinstance(statement, HtmlActionLink):
        result = parse_html_actionLink(statement)
        if result:
            results.controllerMethodCalls.append(result)
    elif isinstance(statement, HtmlAction):
        result = parse_html_action(statement)
        if result:
            results.controllerMethodCalls.append(result)
    elif inAtBlock and isinstance(statement, NameDotAction):
        result = parse_html_action(statement, True)
        if result:
            results.controllerMethodCalls.append(result)
    elif isinstance(statement, HtmlRenderAction):
        result = parse_html_render_action(statement)
        if result:
            results.controllerMethodCalls.append(result)
    elif isinstance(statement, AjaxActionLink):
        result = parse_ajax_actionLink(statement)
        if result:
            results.controllerMethodCalls.append(result)
    elif isinstance(statement, HtmlPartial):
        result = parse_html_partial(statement)
        if result:
            results.viewCalls.append(result)
    elif isinstance(statement, HtmlRenderPartial):
        result = parse_html_partial(statement)
        if result:
            results.viewCalls.append(result)
    elif isinstance(statement, RenderPage):
        result = parse_render_page(statement)
        if result:
            results.viewCalls.append(result)
    elif isinstance(statement, AtBlock):
        result = parse_at_block(statement, results)
        parseChildren = False
    
    if parseChildren:
        for child in statement.get_children():
            parse_statement(child, results, inAtBlock)

def get_text(token):
    try:
        return token.text
    except:
        return ''
    
# Html.BeginForm("Setting", "Peopulse", FormMethod.Post, new { autocomplete = "off", id = "form-peopulseFtpSettings", @class = "block" })
# -First parameter is the controller method name,
# -Second parameter is the controller name,
# -Third or fourth parameter is the http call type (Get, Post).
def parse_html_beginForm(statement):
    
    paramNo = 0
    methodName = None
    controllerName = None
    httpType = None
    httpTypeIsThirdParameter = False
    firstNew = True
    isParameter = False
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, Punctuation) and token.text == '(':
            paramNo = 1
        elif is_token_subtype(token.type, Punctuation) and token.text == ',':
            paramNo += 1
        elif is_token_subtype(token.type, String):
            s = token.text[1:-1]
            if paramNo == 1:
                methodName = s
            elif paramNo == 2:
                controllerName = s
        elif paramNo == 3 and is_token_subtype(token.type, Name):
            httpType = token.text
            httpTypeIsThirdParameter = True
        elif not httpTypeIsThirdParameter and paramNo == 4 and is_token_subtype(token.type, Name):
            httpType = token.text
        elif firstNew and isinstance(token, AnonymousNew):
            # parameters if new contains <something>id = ...
            firstNew = False
            if not isParameter:
                isParameter = block_contains_id(token)
            
    if methodName:
        return ControllerMethodCall(methodName, controllerName, statement, httpType, isParameter)
    return None

def get_parameter(paramName, bracketedBlock):

    lastParamName = None
    for token in bracketedBlock.get_children():
        if is_token_subtype(token.type, Name):
            lastParamName = token.text
        elif is_token_subtype(token.type, String) and lastParamName == paramName:
            return token.text[1:-1]
    return None

def parse_ajax_beginForm(statement):
    
    paramNo = 0
    methodName = None
    controllerName = None
    httpType = None
    firstNew = True
    isParameter = False
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, Punctuation) and token.text == '(':
            paramNo = 1
        elif is_token_subtype(token.type, Punctuation) and token.text == ',':
            paramNo += 1
        elif is_token_subtype(token.type, String):
            s = token.text[1:-1]
            if paramNo == 1:
                methodName = s
            elif paramNo == 2:
                controllerName = s
        elif paramNo == 4 and isinstance(token, CurlyBracketedBlock):
            httpType = get_parameter('HttpMethod', token)
        elif firstNew and isinstance(token, AnonymousNew):
            # parameters if new contains <something>id = ...
            firstNew = False
            if not isParameter:
                isParameter = block_contains_id(token)
            
    if methodName:
        return ControllerMethodCall(methodName, controllerName, statement, httpType, isParameter)
    return None

def parse_url_action(statement):
    
    paramNo = 0
    methodName = None
    controllerName = None
    httpType = 'get'
    firstNew = True
    isParameter = False
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, Punctuation) and token.text == '(':
            paramNo = 1
        elif is_token_subtype(token.type, Punctuation) and token.text == ',':
            paramNo += 1
        elif is_token_subtype(token.type, String):
            s = token.text[1:-1]
            if paramNo == 1:
                methodName = s
            elif paramNo == 2:
                controllerName = s
        elif firstNew and isinstance(token, AnonymousNew):
            # parameters if new contains <something>id = ...
            firstNew = False
            if not isParameter:
                isParameter = block_contains_id(token)
            
    if methodName:
        return ControllerMethodCall(methodName, controllerName, statement, httpType, isParameter)
    return None

def parse_url_routeUrl(statement):
    
    paramNo = 0
    methodName = None
    controllerName = None
    httpType = 'get'
    firstNew = True
    isParameter = False
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, Punctuation) and token.text == '(':
            paramNo = 1
        elif is_token_subtype(token.type, Punctuation) and token.text == ',':
            paramNo += 1
        elif firstNew and isinstance(token, AnonymousNew):
            # parameters if new contains <something>id = ...
            firstNew = False
            controllerToken = get_value_in_new(token, 'controller')
            actionToken = get_value_in_new(token, 'action')
            if not isParameter:
                isParameter = block_contains_id(token)
            if controllerToken:
                controllerName = controllerToken.text[1:-1]
            if actionToken:
                methodName = actionToken.text[1:-1]
            
    if methodName:
        return ControllerMethodCall(methodName, controllerName, statement, httpType, isParameter)
    return None

def parse_html_actionLinkWithAccess(statement):
    
    paramNo = 0
    methodName = None
    controllerName = None
    httpType = 'get'
    firstNew = True
    isParameter = False
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, Punctuation) and token.text == '(':
            paramNo = 1
        elif is_token_subtype(token.type, Punctuation) and token.text == ',':
            paramNo += 1
        elif is_token_subtype(token.type, String):
            s = token.text[1:-1]
            if paramNo == 2:
                methodName = s
            elif paramNo == 3:
                controllerName = s
        elif firstNew and isinstance(token, AnonymousNew):
            # parameters if new contains <something>id = ...
            firstNew = False
            if not isParameter:
                isParameter = block_contains_id(token)
            
    if methodName:
        return ControllerMethodCall(methodName, controllerName, statement, httpType, isParameter)
    return None

# if new { } contains <something>id = ...
def block_contains_id(token):
    
    isParameter = False
    for child in list(token.get_children())[-1].get_children():
        try:
            if child.text.lower().endswith('id'):
                isParameter = True
                break
        except:
            pass
    return isParameter

# if new { controller="myController" }
# returns myController if name = controller
def get_value_in_new(token, name):

    afterNameToken = -1    
    for child in list(token.get_children())[-1].get_children():
        try:
            if child.text.lower() == name:
                afterNameToken = 0
            else:
                if afterNameToken >= 0:
                    if afterNameToken == 1:
                        return child
                    afterNameToken += 1
        except:
            pass
    return None
    
def parse_html_actionLink(statement):
    
    paramNo = 0
    methodName = None
    controllerName = None
    httpType = 'get'
    isParameter = False
    firstNew = True
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, Punctuation) and token.text == '(':
            paramNo = 1
        elif is_token_subtype(token.type, Punctuation) and token.text == ',':
            paramNo += 1
        elif is_token_subtype(token.type, String):
            s = token.text[1:-1]
            if paramNo == 2:
                methodName = s
            elif paramNo == 3:
                controllerName = s
        elif firstNew and isinstance(token, AnonymousNew):
            # parameters if new contains <something>id = ...
            firstNew = False
            if not isParameter:
                isParameter = block_contains_id(token)
            
    if methodName:
        return ControllerMethodCall(methodName, controllerName, statement, httpType, isParameter)
    return None

def parse_html_action(statement, nameDotAction = False):
    
    paramNo = 0
    methodName = None
    controllerName = None
    httpType = 'get'
    firstNew = True
    isParameter = False
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, Punctuation) and token.text == '(':
            paramNo = 1
        elif is_token_subtype(token.type, Punctuation) and token.text == ',':
            paramNo += 1
        elif is_token_subtype(token.type, String):
            s = token.text[1:-1]
            if paramNo == 1:
                methodName = s
            elif paramNo == 2:
                controllerName = s
        elif firstNew and isinstance(token, AnonymousNew):
            # parameters if new contains <something>id = ...
            firstNew = False
            if not isParameter:
                isParameter = block_contains_id(token)
            
    if methodName:
        return ControllerMethodCall(methodName, controllerName, statement, httpType, isParameter)
    return None

def parse_html_render_action(statement):
    
    paramNo = 0
    methodName = None
    controllerName = None
    httpType = 'post'
    firstNew = True
    isParameter = False
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, Punctuation) and token.text == '(':
            paramNo = 1
        elif is_token_subtype(token.type, Punctuation) and token.text == ',':
            paramNo += 1
        elif is_token_subtype(token.type, String):
            s = token.text[1:-1]
            if paramNo == 1:
                methodName = s
            elif paramNo == 2:
                controllerName = s
        elif firstNew and isinstance(token, AnonymousNew):
            # parameters if new contains <something>id = ...
            firstNew = False
            if not isParameter:
                isParameter = block_contains_id(token)
            
    if methodName:
        return ControllerMethodCall(methodName, controllerName, statement, httpType, isParameter)
    return None

def parse_ajax_actionLink(statement):
    
    paramNo = 0
    methodName = None
    controllerName = None
    httpType = None
    firstNew = True
    isParameter = False
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, Punctuation) and token.text == '(':
            paramNo = 1
        elif is_token_subtype(token.type, Punctuation) and token.text == ',':
            paramNo += 1
        elif is_token_subtype(token.type, String):
            s = token.text[1:-1]
            if paramNo == 2:
                methodName = s
        elif paramNo == 5 and isinstance(token, CurlyBracketedBlock):
            httpType = get_parameter('HttpMethod', token)
        elif firstNew and isinstance(token, AnonymousNew):
            # parameters if new contains <something>id = ...
            firstNew = False
            if not isParameter:
                isParameter = block_contains_id(token)
            
    if methodName:
        return ControllerMethodCall(methodName, controllerName, statement, httpType, isParameter)
    return None

def parse_html_partial(statement):
    
    viewName = None
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, String):
            viewName = token.text[1:-1]
            break
             
    if viewName:
        return ViewCall(viewName, statement)
    return None

def parse_render_page(statement):
    
    viewName = None
    for token in list(statement.get_children())[-1].get_children():
        if is_token_subtype(token.type, String):
            viewName = token.text[1:-1]
            break
             
    if viewName:
        return ViewCall(viewName, statement)
    return None

def parse_at_block(statement, results):
    
    block = list(statement.get_children())[-1]
    for stmt in block.get_children():
        parse_statement(stmt, results, True)
