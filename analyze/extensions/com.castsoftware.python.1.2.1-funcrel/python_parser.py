from python_lexer import PythonLexer
from pygments.token import Token, is_token_subtype, Name, Comment, Punctuation, Operator, Literal, Keyword, String
from light_parser import Parser, BlockStatement, Statement, IncreaseIndent, DecreaseIndent, \
                         Seq, Optional, Or, Filter, Token as lightToken, Node, TokenIterator, Term
import math

'''
See grammar at : 
- https://docs.python.org/3/reference/grammar.html

'''


def light_parse(text):
    """
    Light parsing of a python file.
    """
    if not type(text) is str:
        text = text.read()
    
    parser = Parser(PythonLexer,
                    [Parenthesis, SquareBracketedBlock, BracketedBlock, IndentBlock],
                    [Decorators],
                    [ClassBlock, ClassOneLine, FunctionBlock, FunctionOneLine, Import]
                    )
    
    use_indentation(parser)
    return parser.parse(text)


def parse(text):
    """
    Full parsing of a python file.
    """
    if not type(text) is str:
        text = text.read()
    
    parser = Parser(PythonLexer, 
                    [Parenthesis, SquareBracketedBlock, BracketedBlock, IndentBlock],
                    [Decorators],
                    [ClassBlock, ClassOneLine, FunctionBlock, FunctionOneLine, Import],
                    # structure
                    [IfThenElseBlock, IfThenElseOneLine, ForBlock, ForOneLine, WhileBlock, WhileOneLine, 
                     TryBlock, TryOneLine, ExceptBlock, ExceptOneLine, WithBlock, WithOneLine, 
                     FinallyBlock, FinallyOneLine],
                    # statements
                    [If, Return, Pass, EllipsisObject, Delete, Break, Continue,
                     Raise, Global,
                     NonLocal, Assert, Print, Exec, Yield, YieldFrom, Await, ExpressionStatement
                    ]
                    )

    use_indentation(parser)
    
    return (handle_expression(token) for token in parser.parse(text))
    




LineFeed = Token.LineFeed
StartLine = Token.StartLine
DocString = String.Doc


def is_parenthesis(self):
    try:
        return self.is_parenthesis()
    except:
        return False
    

def is_assignement(self):
    try:
        return self.is_assignement()
    except:
        return False

def is_expression_statement(self):
    try:
        return self.is_expression_statement()
    except:
        return False

def is_function(self):
    try:
        return self.is_function()
    except:
        return False

def is_class(self):
    try:
        return self.is_class()
    except:
        return False

def is_method(node):
    """
    True when node is a function being a method (i.e., a function inside a class)
    """
    def get_ancestor(n):
        
        if is_class(n) or is_function(n):
            return n
        
        parent = None
        try:
            parent = getattr(n, 'parent')
        except:
            pass
        
        if not parent:
            return None
        
        return get_ancestor(parent)
        
    if not is_function(node):
        return False
    
    parent = None
    try:
        parent = getattr(node, 'parent')
    except:
        pass
    
    if not parent:
        return False
    
    ancestor = get_ancestor(parent)
    
    if is_class(ancestor):
        return True
    else:
        return False
    
    

def is_dot_access(self):
    try:
        return self.is_dot_access()
    except:
        return False

def is_identifier(self):
    try:
        return self.is_identifier()
    except:
        return False

def is_constant(self):
    try:
        return self.is_constant()
    except:
        return False

def is_import(self):
    try:
        return self.is_import()
    except:
        return False

def is_if_then_else(self):
    try:
        return self.is_if_then_else()
    except:
        return False

def is_binary_operation(self):
    try:
        return self.is_binary_operation()
    except:
        return False

def is_method_call(self):
    try:
        return self.is_method_call()
    except:
        return False
    
def is_expression_list(self):
    try:
        return self.is_expression_list()
    except AttributeError:
        return False
    
def is_addition(self):
    try:
        return self.is_addition()
    except AttributeError:
        return False

def is_interpolation(self):
    try:
        return self.is_interpolation()
    except AttributeError:
        return False

def is_for(self):
    try:
        return self.is_for()
    except AttributeError:
        return False

def is_while(self):
    try:
        return self.is_while()
    except AttributeError:
        return False




class IndentBlock(BlockStatement):
    begin = IncreaseIndent
    end = DecreaseIndent

    def get_statements(self):
        """
        Get the statements
        """
        return list(self.get_sub_nodes())
        
        
class WithResolution:
    """
    For something resolvable
    """
    def __init__(self):
        
        # resolution made
        self._resolutions = []

    def get_resolutions(self):
        """
        The possible elements it resolve to.
        """
        resolutions = list(set(self._resolutions))
        
        def filter_super(resolutions):
            """Remove recursivity in __init__ methods. 
            
            It is very unlikely that an __init__ call is called recursively within
            its definition. Removing spurious resolution to self.__init__ when 
            initializing external class (with super, or direct call) avoids 
            registering incorrect recursive callLinks.
            
            @todo: move this code to resolution.py 
            @todo: support to Python's "method resolution order" 
            """
            if is_method_call(self):
                method = self.get_method()
                if is_dot_access(method):
                    identifier = method.get_identifier()
                    if identifier.text == "__init__":
                        parent = self
                        try:
                            while not is_function(parent):
                                parent = parent.parent
                            func = parent
                        except:
                            return resolutions
                        
                        # remove recursive calls to self.__init__
                        if func.get_name() == "__init__":
                            parent = self
                            try:
                                while not is_class(parent):
                                    parent = parent.parent
                                cls = parent
                            except:
                                return resolutions
                            
                            cls_name = cls.get_name()
                            
                            # we compare the endings because the leading part will depend on
                            # the type of file (module or script)
                            # "." -> is there any problem using it when imported modules?
                            resolutions = [element for element in resolutions 
                                                   if not element.get_qualified_name().endswith("."+cls_name+".__init__")]
                            
                            # resolve super
                            expression = method.get_expression()
                            if is_method_call(expression):
                                super_ =  expression.get_method()
                                if super_.get_name() == "super":
                                    # keep inherited classes with __init__ method
                                    # here we should add the method resolution order restriction
                                    inheritance = cls.get_inheritance()
                                    names_inheritance = [ref.get_name() for ref in inheritance]
                                    endings =  tuple(name+".__init__" for name in names_inheritance)
                                    resolutions = [element for element in resolutions 
                                                           if element.get_qualified_name().endswith(endings)]
            
            return resolutions
        
        try:
            resolutions = filter_super(resolutions)
        except:
            pass
        
        return resolutions


class Parenthesis(BlockStatement, WithResolution):
    
    def __init__(self):
        BlockStatement.__init__(self)
        WithResolution.__init__(self)
    
    begin = lightToken('(', Punctuation)
    end = lightToken(')', Punctuation)


    def is_parenthesis(self):
        return True
    

class SquareBracketedBlock(BlockStatement):
    begin = lightToken('[', Punctuation)
    end = lightToken(']', Punctuation)


class BracketedBlock(BlockStatement):
    begin = lightToken('{', Punctuation)
    end = lightToken('}', Punctuation)


def is_begin_line_ending_with_semicolon(token, stream):
    """
    Matches StartLine when 
        
        StartLine ... ':' LineFeed

    Used to recognise the 
        if ...: 
    all on one line with nothing after the :
    """
    if token.type != StartLine:
        return False
    
    if hasattr(token, 'is_begin_line_ending_with_semicolon'):
        return getattr(token, 'is_begin_line_ending_with_semicolon')
    
    index_of_stream = stream.tokens.index
    
    try:
        previous = token
        while token.type != LineFeed:
            if token.type != StartLine:
                previous = token
            token = next(stream)
        
        stream.tokens.index = index_of_stream # do not consume
        if previous == ':':
            setattr(token, 'is_begin_line_ending_with_semicolon', True)
            return True
        else:
            setattr(token, 'is_begin_line_ending_with_semicolon', False)
            return False
    except:
        stream.tokens.index = index_of_stream # do not consume
        setattr(token, 'is_begin_line_ending_with_semicolon', False)
        return False
    

def is_begin_line_not_ending_with_semicolon(token, stream):
    """
    matches StartLine when 
        
        StartLine ... Not(':') LineFeed

    Used to recognise the 
        if ...: print(a); print(b); 
    all on one line
    """
    if token.type != StartLine:
        return False
    
    if hasattr(token, 'is_begin_line_ending_with_semicolon'):
        return not getattr(token, 'is_begin_line_ending_with_semicolon')
    
    index_of_stream = stream.tokens.index
    
    try:
        previous = token
        while token.type != LineFeed:
            if token.type != StartLine:
                previous = token
            token = next(stream)
        
        stream.tokens.index = index_of_stream # do not consume
        if previous == ':':
            setattr(token, 'is_begin_line_ending_with_semicolon', True)
            return False
        else:
            setattr(token, 'is_begin_line_ending_with_semicolon', False)
            return True
    except:
        stream.tokens.index = index_of_stream # do not consume
        setattr(token, 'is_begin_line_ending_with_semicolon', False)
        return True # end of file ?


class Decorators(Statement):
    """
    A suite of decorators.
    We use this for matching the block of decorators.
    """
    begin = Seq(StartLine, Name.Decorator)
    
    end = Seq(StartLine, 
              Or(lightToken('class', Keyword),
                 Seq(Optional('async'), lightToken('def', Keyword))))
    
    consume_end = False 


class Decorator(Node):
    
    def __init__(self):
        Node.__init__(self)

    def get_parameters(self):
        """
        :return: list of expressions
        """
        for parenthesis in self.get_sub_nodes(Parenthesis):
            
            return list(parenthesis.get_sub_nodes())
        
        return []
        
        
class WithDocString:
    
    def get_docstring(self, unstripped=False):
        """
        Return python docstring of element
        """
        for node in self.get_sub_nodes(IndentBlock):
            
            children = node.get_children()
            
            token = next(children)
            while token.type in [IncreaseIndent, StartLine, LineFeed]:
                token = next(children)
            
            if is_token_subtype(token.type, Literal.String.Doc): # @UndefinedVariable
                
                text = token.text
                triple_quotes = ('"""', "'''")
                single_quotes = ('"', "'")
                
                if text.startswith(triple_quotes):
                    text = text[3:-3]
                elif text.startswith(single_quotes):
                    text = text[1:-1]
                
                if unstripped:
                    return (text, token)
                else:
                    return text.strip()
            
        return ""

    def get_header_comments(self):
        """
        @override because we have strange tokens...
        """
        children = iter(self.children)
        result = []
        token = next(children) 
        while is_token_subtype(token.type, Comment):
            result.append(token)
            token = next(children)
        
        return result
    
    def get_body_comments(self):
        """
        @override because we have strange organisation...
        """
        def get_comments(node):
            
            result = []
            for token in node.children:
                
                if is_token_subtype(token.type, Comment):
                    result.append(token)
                
                if isinstance(token, Node):
                    result += get_comments(token)
                
            return result
        
        return get_comments(self)

    def get_decorators(self):
        """
        Access to decorators of object.
        
        @rtype: list of Decorator
        """
        for decorators in self.get_sub_nodes(Decorators):
            
            return list(decorators.get_sub_nodes())
        
        return []


class PythonStatement():

    def get_container_block(self):
        """
        Access to block, if, for etc... that contains that statement
        
        @return: None for top level statements
        """
        return self.parent


class Class(PythonStatement, WithDocString):
    def __init__(self):
        super().__init__()
        self.__name = None
        self.__inheritance = []
        
    def is_class(self):
        return True

    def get_name(self):
        """
        Access to class name
        """
        return self.__name
    
    def get_inheritance(self):
        """
        Access to inheritance
        """
        return self.__inheritance

    def on_end(self):
        """
        Parse some basic info on class : name, inheritance
        """
        children = self.get_children()
        token = next(children)
        if token.type == LineFeed:
            token = next(children)
        if isinstance(token, Decorators):
            token = next(children)
        token = children.move_to('class')
        name = next(children)
        self.__name = name.text
        p = next(children)
        if isinstance(p, Parenthesis):
            # parse inheritance list
            inheritance = p.get_children()
            try:
                next(inheritance) # '('
                
                tokens = []
                name = ''
                
                while True:
                    token = next(inheritance)
                    
                    if token.type in [Name, Operator, Name.Exception]:
                        tokens.append(token)
                        name += token.text
                    else:
                        if tokens:
                            self.__inheritance.append(Reference(name, tokens))
                            # reset
                            tokens = []
                            name = ''
            except:
                pass

class ClassOneLine(Class, Statement):
    def __init__(self):
        super().__init__()
    
    begin = Seq(Optional(Decorators),
                is_begin_line_not_ending_with_semicolon,
                lightToken('class', Keyword),
                Name,
                Optional(Parenthesis))
    
    end = LineFeed

class ClassBlock(Class, BlockStatement):
    """
    Classes
    
    @todo class block and class one line
    """
    begin = Seq(Optional(Decorators),
                is_begin_line_ending_with_semicolon,
                lightToken('class', Keyword),
                Name,
                Optional(Parenthesis))
    
    end   = IndentBlock
    
    def __init__(self):
        super().__init__()

class Function(PythonStatement, WithDocString):

    def is_function(self):
        return True

    def get_name(self):
        """
        Access to function name
        """
        children = self.get_children()
        while True:
            try:
                token = next(children)
            except StopIteration:
                return None
                
            if token.text:
                if token == 'def':
                    break
        
        name = next(children)
        return name.text

    def get_members(self):
        """
        When __init__ list the member names.
        all x if there exists "self.x"
        """
        
        def extract_member(children):
            """
            Assume children is just after a 'self'
            """
            token = next(children) 
            if not token.text or token != '.':
                return
            name = next(children)
            token = next(children)
            if not isinstance(token, Parenthesis) and token != '.':
                return name
        
        result = []
        
        for block in self.get_sub_nodes(IndentBlock):
            children = block.get_children()
            try:
                children.move_to('self')
                while True:
                    name = extract_member(children)
                    if not name:
                        continue
                    # warning! case-insensitivity when
                    # comparing tokens directly like : "name in result"
                    if not name.text in [name.text for name in result]:
                        result.append(name)
                    children.move_to('self')
            except:
                pass
        
        return result

    def get_statements(self):
        """
        Access to statements list of the function
        """
        for block in self.get_sub_nodes(IndentBlock):
            return list(block.get_sub_nodes())
        else:
            return list(self.get_sub_nodes(PythonSimpleStatement))
    
    def get_parameters(self):
        """
        Access to parameters of the function.
        """
        
        def extract_identifiers(node):
            result = []
            
            for param in node.get_sub_nodes():
            
                if isinstance(param, Identifier):
                    
                    result.append(param)

                elif isinstance(param, Assignement):
                    
                    # @type param: Assignement
                    
                    exp = param.get_left_expression()
                    if isinstance(exp, Identifier):
                        result.append(param)
                    elif isinstance(exp, Parenthesis):
                        result += extract_identifiers(exp)
                        
                elif isinstance(param, Parenthesis):
                    
                    result += extract_identifiers(param)
            
            return result
                
        
        result = []

        try:
            parenthesis = list(self.get_sub_nodes(Parenthesis))[0]
            
            result = extract_identifiers(parenthesis)

        except:
            pass
        
        return result
    
    def add_caller(self, caller):
        
        if not hasattr(self, '_callers'):
            setattr(self, '_callers', [])
        
        if not caller in self._callers:
            self._callers.append(caller)
    
    def remove_caller(self, caller):

        if hasattr(self, '_callers'):
        
            self._callers.remove(caller)
    
    def get_calling_asts(self):
        """
        Access to other asts calling that function.
        Feed during resolution.
        """
        if not hasattr(self, '_callers'):
            setattr(self, '_callers', [])
        return self._callers
        

class FunctionOneLine(Function, Statement):

    begin = Seq(Optional(Decorators), 
                is_begin_line_not_ending_with_semicolon, 
                Optional('async'), 
                lightToken('def', Keyword), 
                Name, 
                Parenthesis)
    end = LineFeed


class FunctionBlock(Function, BlockStatement):
    """
    Methods

    """
    begin = Seq(Optional(Decorators), 
                is_begin_line_ending_with_semicolon, 
                Optional('async'), 
                lightToken('def', Keyword), 
                Name, Parenthesis)
    end   = IndentBlock


    

class PythonSimpleStatement(PythonStatement):
    
    end = Or(';', LineFeed)


class WithExpression:
    
    def get_expression(self, strip_parentheses=True):

        try:
            expression = next(self.get_sub_nodes((Expression, Parenthesis)))
            
            if strip_parentheses:
                while is_parenthesis(expression):
                    expression = next(expression.get_sub_nodes((Expression, Parenthesis)))
            
            return expression
        
        except StopIteration:
            pass
    
    
class Return(Statement, PythonSimpleStatement, WithExpression):
    
    begin = lightToken('return', Keyword)


class YieldFrom(Statement, PythonSimpleStatement, WithExpression):
    
    begin = lightToken('yield from', Keyword)


class Yield(Statement, PythonSimpleStatement, WithExpression):
    
    begin = lightToken('yield', Keyword)

class Await(Statement, PythonSimpleStatement, WithExpression):
    
    begin = lightToken('await', Keyword)

class Pass(Statement, PythonSimpleStatement):
    
    begin = lightToken('pass', Keyword)


class EllipsisObject(Statement, PythonSimpleStatement):
    """
    Note: 'Ellipsis' name is already taken by bultin library
    """
    
    begin = lightToken('...', Keyword)


class Delete(Statement, PythonSimpleStatement, WithExpression):
    
    begin = lightToken('del', Keyword)


class Break(Statement, PythonSimpleStatement):
    
    begin = lightToken('break', Keyword)


class Continue(Statement, PythonSimpleStatement):
    
    begin = lightToken('continue', Keyword)


class Raise(Statement, PythonSimpleStatement, WithExpression):
    
    begin = lightToken('raise', Keyword)


        

class Reference(WithResolution):
    """
    A reference to something.
    """
    def __init__(self, name, tokens):
        WithResolution.__init__(self)
        self.__name = name
        self._alias = None
        self.__begin_line = tokens[0].get_begin_line()
        self.__begin_column = tokens[0].get_begin_column()
        self.__end_line = tokens[-1].get_end_line()
        self.__end_column = tokens[-1].get_end_column()
        
    def get_begin_line(self):
        return self.__begin_line    
        
    def get_begin_column(self):
        return self.__begin_column    

    def get_end_line(self):
        return self.__end_line    
        
    def get_end_column(self):
        return self.__end_column    

        
    def get_name(self):
        """
        Access to name
        """
        return self.__name
    
    def get_alias(self):
        return self._alias
    

class Import(Statement, PythonSimpleStatement):
    
    begin = Or(lightToken('import', Keyword), lightToken('from', Keyword))

    def __init__(self):
        Statement.__init__(self)
        PythonSimpleStatement.__init__(self)
        self._module_references = []
        self._alias = None
        # in case of from ... import <...>
        self._method_or_class_references = []

    def is_import(self):
        return True

    def get_module_references(self):
        """
        Access to the imported module
        
        For 
        - import a.b
          - returns a.b
         
        """
        return self._module_references
    
    def get_imported_elements(self):
        """
        from ... import <imported elements>
        """
        return self._method_or_class_references

    def on_end(self):
        """
        Deep parsing.
        """
        children = self.get_children()
        from_or_import = next(children) # from or import        

        token = next(children)
        reference = Reference(token.text, [token])
        self._module_references.append(reference)

        if from_or_import == 'import':
            
            try:

                as_or_comma = next(children)
                if as_or_comma == 'as':
                    reference._alias = next(children).text
                    next(children)
                
                while True:
                    token = next(children)
                    if token == 'as':
                        reference._alias = next(children).text
                    elif token == ',':
                        continue
                    elif token != ')':
                        reference = Reference(token.text, [token])
                        self._module_references.append(reference)
                
            except:
                pass                        
            
        else:

            try:
            
                as_or_import = next(children)
                if as_or_import == 'as':
                    reference._alias = next(children).text
                else:
                    # from ... import
                    
                    parenthesis = children.look_next()
                    if isinstance(parenthesis, Parenthesis):
                        children = parenthesis.get_children()
                        next(children)
                    
                    while True:
                        token = next(children)
                        if token == 'as':
                            reference._alias = next(children).text
                        elif token == ',':
                            continue
                        elif token != ')':
                            reference = Reference(token.text, [token])
                            self._method_or_class_references.append(reference)
            except:
                pass                        


class Global(Statement, PythonSimpleStatement):
    
    begin = lightToken('global', Keyword)


class NonLocal(Statement, PythonSimpleStatement):
    
    begin = 'nonlocal'


class Assert(Statement, PythonSimpleStatement, WithExpression):
    
    begin = lightToken('assert', Keyword)


class Print(Statement, PythonSimpleStatement, WithExpression):
    
    begin = lightToken('print', Keyword)

class Exec (Statement, PythonSimpleStatement, WithExpression):
    
    begin = lightToken('exec', Keyword)

def is_start_line_followed_by_name(token, stream):
    
    if token.type != StartLine:
        return False
    
    index_of_stream = stream.tokens.index
    next_token = next(stream)
    stream.tokens.index = index_of_stream # do not consume
    
    return (is_token_subtype(next_token.type, Name) and not is_token_subtype(next_token.type, Name.Decorator)) or isinstance(next_token, Parenthesis)
    

def is_if(token, stream):
    """
    recognise and consume contiguous if elif ... else blocks 
    """
    def get_first_sub_token(node):
        
        if isinstance(node, IfThenElse):
           
            children = node.get_children()
            next(children)
            return next(children) 


    first = get_first_sub_token(token)
    if first != 'if':
        return False

    
    index_of_stream = stream.tokens.index
    node = next(stream)
    
    try:
        first = get_first_sub_token(node)
        while first in ['elif', 'else']:
            index_of_stream = stream.tokens.index
            node = next(stream)
            first = get_first_sub_token(node)
        
        stream.tokens.index = index_of_stream # do not consume last unmatching one
    except StopIteration:
        pass
    
    return True


class ExpressionStatement(Statement, PythonSimpleStatement):
    
    begin = is_start_line_followed_by_name
    
    def get_expression(self):
        
        for node in self.get_sub_nodes():
            return node

    def is_expression_statement(self):
        return True


class If(Term, PythonStatement):
    """
    Sequence of IfThenElse
    """
    match = is_if
    
    def get_cases(self):
        """
        Access to each sub case.
        
        @rtype: list of IfThenElse
        """
        return list(self.get_sub_nodes())
        
        

class PythonBlockStatement(BlockStatement):

    def get_statements(self):
        
        for block in self.get_sub_nodes(IndentBlock):
            return list(block.get_sub_nodes())


class IfThenElse(WithExpression):
    """
    Common class to if then else
    """
    def __init__(self):
        self.condition = None
        
    def is_else(self):
        
        children = self.get_children()
        next(children)
        return next(children) == 'else' 
    
    def is_if_then_else(self):
        return True
    

class IfThenElseBlock(PythonBlockStatement, IfThenElse):
    """
    Classical block
    """
    def __init__(self):
        BlockStatement.__init__(self)
        IfThenElse.__init__(self)
    
    begin = Seq(is_begin_line_ending_with_semicolon, Or(lightToken('if', Keyword), 
                                                        lightToken('else', Keyword), 
                                                        lightToken('elif', Keyword)))
    end = IndentBlock


class IfThenElseOneLine(Statement, IfThenElse):
    """
    an if can be on one line : 
    if .... : statement1; ... statementn;
    """
    def __init__(self):
        Statement.__init__(self)
        IfThenElse.__init__(self)
        
    begin = Seq(is_begin_line_not_ending_with_semicolon, Or(lightToken('if', Keyword), 
                                                            lightToken('else', Keyword), 
                                                            lightToken('elif', Keyword)))
    end = LineFeed


    def get_statements(self):
        
        return list(self.get_sub_nodes(PythonSimpleStatement))


class For(PythonStatement, WithExpression):
    
    def get_identifiers(self):
        """
        Identifiers used for iteration 
        """
        
        def get_identifiers(node):
            
            if is_identifier(node):
                return [node]
            
            if is_parenthesis(node):
            
                result = []
                for sub_node in node.get_sub_nodes():
                    result += get_identifiers(sub_node)
                
                return result
            
            if is_binary_operation(node):
                return get_identifiers(node.get_left_expression())
            
            return []
        
        exp = self.get_expression()
        if isinstance(exp, BinaryOperation):
            
            left = exp.get_left_expression()
            return get_identifiers(left)
        
        if is_expression_list(exp):
            # handle "except Exception as err:"
            result = []
            for node in exp.get_sub_nodes():
                result += get_identifiers(node)
        
            return result
    
        return []

    def is_for(self):
        return True

class ForBlock(PythonBlockStatement, For):
    
    begin = Seq(is_begin_line_ending_with_semicolon, Optional('async'), lightToken('for', Keyword))
    end = IndentBlock


class ForOneLine(Statement, For):
    
    begin = Seq(is_begin_line_not_ending_with_semicolon, Optional('async'), lightToken('for', Keyword))
    end = LineFeed


class While(PythonStatement, WithExpression):
    
    def is_while(self):
        return True
    

class WhileBlock(PythonBlockStatement, While):
    
    begin = Seq(is_begin_line_ending_with_semicolon, lightToken('while', Keyword))
    end = IndentBlock


class WhileOneLine(Statement, While):
    
    begin = Seq(is_begin_line_not_ending_with_semicolon, lightToken('while', Keyword))
    end = LineFeed

    
class TryBlock(PythonBlockStatement, PythonStatement):
    
    begin = Seq(is_begin_line_ending_with_semicolon, lightToken('try', Keyword))
    end = IndentBlock


class TryOneLine(Statement, PythonStatement):
    
    begin = Seq(is_begin_line_not_ending_with_semicolon, lightToken('try', Keyword))
    end = LineFeed

    def get_statements(self):
        
        return list(self.get_sub_nodes(PythonSimpleStatement))


class ExceptBlock(PythonBlockStatement, PythonStatement, WithExpression):
    
    begin = Seq(is_begin_line_ending_with_semicolon, lightToken('except', Keyword))
    end = IndentBlock

# @todo: add & test get_identifier and get_expression like With

class ExceptOneLine(Statement, PythonStatement):
    
    begin = Seq(is_begin_line_not_ending_with_semicolon, lightToken('except', Keyword))
    end = LineFeed

    
class With(PythonStatement, WithExpression):
    """
    Common class for with statement
    """
    
    def get_identifier(self):
        """
        Access to variable, i.e., 'v' in 'with ... as v'
        """
        sub_nodes = self.get_sub_nodes(Expression)
        try:
            next(sub_nodes)
            return next(sub_nodes) 
        except:
            # no variable in the with
            pass
        
class WithBlock(PythonBlockStatement, With):
    """
    with statement 
      with ... as ...:
         ...
         ...
    """
    begin = Seq(is_begin_line_ending_with_semicolon, Optional('async'), lightToken('with', Keyword))
    end = IndentBlock


class WithOneLine(Statement, With):
    """
    with statement 
      with ... as ...: ...; ...;
    """
    
    begin = Seq(is_begin_line_not_ending_with_semicolon, Optional('async'), lightToken('with', Keyword))
    end = LineFeed

    def get_statements(self):
        
        return list(self.get_sub_nodes(PythonSimpleStatement))

    
class FinallyBlock(PythonBlockStatement, PythonStatement):
    
    begin = Seq(is_begin_line_ending_with_semicolon, lightToken('finally', Keyword))
    end = IndentBlock


class FinallyOneLine(Statement, PythonStatement):
    
    begin = Seq(is_begin_line_not_ending_with_semicolon, lightToken('finally', Keyword))
    end = LineFeed

    
def use_indentation(parser):
    """
    Indentation increase/decrease tokens are inserted in the token flux.
    So that they can be used as begin/end.
        
    Those tokens are : light_parser.IncreaseIndent ; light_parser.DecreaseIndent
                
    """
    parser.lexer.add_filter(IndentPythonFilter())


class BadIndentation(Exception):
    """
    Custom exception for bad indentation. 
    """
    pass


class IndentPythonFilter(Filter):
    """
    Filter that add indentation tokens in the stream.
    
    This filter will insert in the stream special tokens 
    - IncreaseIndent, 
    - DecreaseIndent
    - StartLine
    - LineFeed 
    
    """
    def __init__(self):
        
        # current column line
        self.current_column = 1
        self.new_line = False
        # we can deduce the indentation used
        self.deduced_indentation = []

    def filter(self, lexer, stream):
        
        def create_fake_token(_type, token):
            _t = lightToken(type=_type)
            _t._is_whitespace = False
            _t.begin_line = token.begin_line
            _t.end_line = token.end_line
            return _t
            
        
        parenthesedLevel = 0
        lastToken = None
        previous_non_whitespace_token = None
        
        for token in stream:
            
            if not lastToken:
                # first line
                yield create_fake_token(StartLine, token)
            
            yieldToken = True
            if token.is_whitespace():
                
                if '\n' in token.text and not parenthesedLevel: 
                    # we have changed line
                    self.new_line = True
                    previous_non_whitespace_token = None
                    yield create_fake_token(LineFeed, token)
                    
            elif token.text.endswith('\\\n'):
                
#                 print('yieldToken')
                yieldToken = True
            
            else:
                
                if parenthesedLevel == 0 and previous_non_whitespace_token and previous_non_whitespace_token.text in [':', ';']:
                    # for one line block statements StartLine is in fact a "start statement"
                    yield create_fake_token(StartLine, token)
                
                
                if self.new_line:
                    
                    # this is a new line and this is the current indentation column given by the first text
                    column = token.begin_column
                    
                    if column > self.current_column: # indentation level has increased
                        
                        if parenthesedLevel == 0:
                            if not is_token_subtype(token.type, Comment) and not (is_token_subtype(token.type, Literal.String) and lastToken and is_token_subtype(lastToken.type, Literal.String)):
                                # calibrate the 'size of indentation':
                                if not self.deduced_indentation and parenthesedLevel == 0:
                                    deduced_indentation = column - 1
                                else:
                                    deduced_indentation = column - self.current_column
                                self.deduced_indentation.append(deduced_indentation)
                        
                                nbIndent = math.floor((column-self.current_column)/deduced_indentation)
                                for _ in range(nbIndent):
                                    yield lightToken(type=IncreaseIndent)
                                    yield create_fake_token(StartLine, token)

                    elif column < self.current_column and not is_token_subtype(token.type, Comment) and not (is_token_subtype(token.type, Literal.String) and lastToken and is_token_subtype(lastToken.type, Literal.String)): # decrease of indentation
                        
                        # we can 'close' several blocks at one time : we use deduced_indentation to know how many 
                        # decrease we should get
                        if parenthesedLevel == 0:
                            while column < self.current_column:
                                yield lightToken(type=DecreaseIndent)
                                if not self.deduced_indentation:
                                    pass
                                
#                                 if not self.deduced_indentation:
#                                     print(lastToken)
#                                     print(parenthesedLevel)
#                                     print(self.current_column)
#                                     print(token)

                                error = False
                                try:
                                    self.current_column -= self.deduced_indentation[-1]
                                except IndexError:
                                    # source code with incorrect mixed indentation
                                    error = True
                                
                                if error:
                                    raise BadIndentation()
                                
                                self.deduced_indentation.pop()
                            
                        yield create_fake_token(StartLine, token)
                        
                    elif column == self.current_column and not is_token_subtype(token.type, Comment) and not (is_token_subtype(token.type, Literal.String) and lastToken and is_token_subtype(lastToken.type, Literal.String)): 
                        # new line in same indent
                        yield create_fake_token(StartLine, token)
                        
                    
                    # the current 'indent'
                    if not is_token_subtype(token.type, Comment) and not (is_token_subtype(token.type, Literal.String) and lastToken and is_token_subtype(lastToken.type, Literal.String)):
                        if parenthesedLevel == 0:
                            self.current_column = column
#                             print('setting self.current_column ', self.current_column, token)
                
                if '\n' in token.text and token.type == Comment and not parenthesedLevel: 
                    # we have changed line
                    if token.type != Comment or previous_non_whitespace_token:
                        yield create_fake_token(LineFeed, token)
                    self.new_line = True
                    previous_non_whitespace_token = None
                else:
                    # waiting for a new line
                    previous_non_whitespace_token = token
                    self.new_line = False
                    
            # still give the current token...
            if yieldToken:
                yield token 

            if is_token_subtype(Punctuation, token.type):
                if token.text in ['(', '[', '{']:
                    parenthesedLevel += 1
                elif token.text in [')', ']', '}']:
                    parenthesedLevel -= 1

            lastToken = token



"""
Parsing Expressions by Recursive Descent
@see : https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm

Basically we have : 
- one main function (handle_expression)

We call parse_expression on the body of a statement above, and, then replace the body with the expression found.  

Then several functions, for parsing it self (one per 'level of precedence')
- parse_expression (main entry point)
- parse_expression_level2
- parse_simple_term
 

@todos :

*name in parenthesis f(*values)

tests, tests, tests

"""


class MyLookAhead():
    """
    A look ahead for expression parsing...
    @see https://www.engr.mun.ca/~theo/Misc/exp_parsing.htm#RDP
    
    """
    def __init__(self, tokens):
        
        self.tokens = [token for token in tokens if token.type not in [StartLine, LineFeed] and token.text != '\\\n']
        
    def look_next(self):
        
        if self.tokens:
            return self.tokens[0]
        
        return None

    def consume(self):
        
        if self.tokens:
            return self.tokens.pop(0)
        
        return None



def handle_expression(token):
    """
    """
    if isinstance(token, Node):
        # recurse first but do not recurse in (), [], {}
        for node in token.get_sub_nodes():
            # parentship
            setattr(node, 'parent', token)
            handle_expression(node)

    if isinstance(token, Decorators):
        
        begin, body, _ = token._split_block()
        
        token.begin_length = 1
        
        # remove whitespaces and comments
        body = MyLookAhead(list(TokenIterator(body)))
        new_body = []

        lenght_begin = len(begin)
        sub_token = begin[lenght_begin -1]  # @hack: skips StartLine & top-adjacent comments
        
        try:
            while sub_token and is_token_subtype(sub_token.type, Name.Decorator):
                
                decorator = Decorator()
                setattr(decorator, 'parent', token)
                decorator.children = [sub_token]
                
                new_body.append(decorator)
                
                sub_token = body.consume()
                
                if isinstance(sub_token, Parenthesis):
                    
                    parse_parameters(sub_token)
                    decorator.children.append(sub_token)
                    sub_token = body.consume()

        except StopIteration:
            pass
    
        token._replace_body(new_body + body.tokens)
        
        
    # here order matters with the lines before: do the recursion first 
    # then we can change the tree...
    classes = (IfThenElse, While, For, ExpressionStatement, With, WithExpression)
    if isinstance(token, classes):
        
        _, body, _ = token._split_block()
        
        # remove whitespaces and comments
        body = MyLookAhead(list(TokenIterator(body)))

        condition = parse_expression(body)
        if condition: # the 'else:' parsing...
            
            # ??? how does it works ?
            token.condition = condition
            _as = body.look_next()
            
            if isinstance(token, With) and _as == 'as':
                # scan the identifier ...
                _as = body.consume()
                
                identifier = parse_expression(body)
                setattr(identifier, 'parent', token)
                new_body = [condition, _as, identifier] + body.tokens
            else:
                new_body = [condition] + body.tokens
    
            token._replace_body(new_body)
            setattr(condition, 'parent', token)
            
            
        
    elif isinstance(token, Function):
        
        parenthesis = next(token.get_sub_nodes(Parenthesis))
        parse_parameters(parenthesis)
    
    return token


class Expression(Node, WithResolution):
    
    def __init__(self):
        Node.__init__(self)
        WithResolution.__init__(self)

    def get_enclosing_statement(self):
        """
        Return the enclosing statement
        """
        def get_first_parent(node):
            
            if isinstance(node, PythonStatement):
                return node
            
            if hasattr(node, 'parent'):
                return get_first_parent(node.parent)
        
        return get_first_parent(self)


class Identifier(Expression):
    """
    An identifier, e.g. :
    - a
    - f
    
    No dots here, see DotAccess
    """
    
    def get_name(self):
        
        return self.children[0].text

    def is_identifier(self):
        return True
     
class Constant(Expression):
    
    string_marks = ("'", '"', "r'", 'r"', "f'", 'f"', "b'", 'b"', "rb'", 'rb"', "br'", 'br"', "rf'", 'rf"', "fr'", 'fr"')

    def get_value(self):
        
        return ''.join(child.text for child in self.children)

    def is_constant(self):
        return True
    
    def is_constant_string(self):
        val = self.get_value()
        
        start_condition = val.lower().startswith(self.string_marks)
        
        quotes = ("'", '"')
        end_condition =  val.endswith(quotes)
        
        if start_condition and end_condition:
            return True
                
        return False
    
    def is_fstring(self):
        token = next(self.get_children())
        return True if token in [ "f'", 'f"', "rf'", 'rf"', "fr'", 'fr"'] else False
    
    def get_string_value(self):

        val = self.get_value()
        if self.is_constant_string():

            index = 0
            single_modificators = ('r', 'b', 'f')
            if val.lower().startswith(single_modificators):
                index = 1
                double_modificators = ('rb', 'br', 'rf', 'fr')
                if val.lower().startswith(double_modificators):
                    index = 2
            
            string_marks = ('"""', "'''") + ("r'''", 'r"""', "b'''", 'b"""', "f'''", 'f"""') + ("rb'''", 'br"""', "rf'''", 'fr"""')
            if val.lower().startswith(string_marks):
                return val[3+index:-3]
            
            return val[1+index:-1]
        return None


class DotAccess(Expression):
    """
    exp1 . name
    """
    def get_expression(self):
        
        return self.children[0]
    
    def get_identifier(self):
        """
        """
        return self.children[-1]
    
    def get_name(self):

        return self.children[-1].text
    
    def is_dot_access(self):
        return True

class ArrayAccess(Expression):
    """
    exp [...]
    """
    def get_array_expression(self):
        
        return self.children[0]
    
    def get_indice(self):

        return next(self.children[-1].get_sub_nodes())
    

class MethodCall(Expression):
    """
    exp (...)
    """
    def get_method(self):
        
        return self.children[0]
    
    def get_parameters(self):

        return list(self.children[-1].get_sub_nodes())

    def is_method_call(self):
        return True
    
    def get_argument(self, position, keyword):
        """
        Returns positional/keyword argument
        
        If found a match with positional argument, the keyword
        argument is neglected.
        
        Limitations 
            Optional keyword arguments with no defined position
            can be retrieved by keyword. However combinations
            with optional (non-keyword) arguments are not tested.
        
        """
        parameters = self.get_parameters()
        
        if position is not None:
            if position < len(parameters):
                
                argument = parameters[position]
                
                # positional argument
                if not is_assignement(argument):
                    return argument
        
        # keyword argument
        for assig in parameters:
            if not is_assignement(assig):
                continue
            kw = assig.get_left_expression()
            kw = kw.get_name()
            if kw == keyword:
                return assig.get_right_expression()


class Array(Expression):
    """
    An array expression :
    
    [..., ..., ...]
    """
    def get_values(self):
        
        for node in self.get_sub_nodes():
            return list(node.get_sub_nodes())


class ComprehensionLoop(Expression):
    """
    [ ... for ... in ... ...]
    ( ... for ... in ... ...)
    """
    
    def get_expression(self):
        """
        return first expression
        """
        first_node = next(self.get_sub_nodes())
        return next(first_node.get_sub_nodes())
    
    def get_comprehension_for(self):
        """
        Get the for part
        """
        first_node = next(self.get_sub_nodes())
        return next(first_node.get_sub_nodes(ComprehensionFor))


class ComprehensionFor(Node, For):
    """
    The sub part of a comprehension loop
    """
    pass


class Map(Expression):
    """
    An map expression :
    
    {...:..., ...:..., ...:...]
    """
    def get_values(self):
        
        return list(next(self.get_sub_nodes()).get_sub_nodes())
        


class Lambda(Expression):
    pass


class LambdaParameters(Expression):
    pass


class Unary(Expression):
    """
    Unary expression
    """
    pass


class UnaryNot(Unary):
    """
    not expression
    """
    pass



class BinaryOperation(Expression):
    """
    A binary operation: 
    
    left_expression op right_expression
    
    Assignemnts are here too.
    """
    
    def get_left_expression(self):
        
        return self.children[0]
    
    def get_right_expression(self):

        return self.children[-1]

    def is_binary_operation(self):
        return True

    def get_operator(self):
        
        children = self.get_children()
        next(children)
        return next(children)
    
    def is_assignement(self):
        return False
    

class Assignement(BinaryOperation):
    """
    An Assignement
    """
    # augmented assignment
    augassign = ['=', '+=', '-=', '*=', '/=', '@=', '%=', '&=', '|=', '^=', '<<=', '>>=', '**=', '//=']
    
    def get_operator(self):
        
        children = self.get_children()
        next(children)
        return next(children)
    
    def is_assignement(self):
        return True
    

class AdditionExpression(BinaryOperation):
    """
    exp + exp
    """
    def is_addition(self):
        return True

class StringInterpolation(BinaryOperation):
    """
    exp % exp  [it over-captures modulo-operator expressions]
    
    Accurate identification of a % b would require type inference
    of the variables.
    """
    def is_interpolation(self):
        return True

class IfTernaryExpression(Expression):
    
    def get_first_value(self):
        return self.children[0]
    
    def get_second_value(self):
        return self.children[-1]


class ExpressionList(Expression):
    
    def is_expression_list(self):
        return True


def parse_expression(tokens):
    """
    Given a MyLookAhead of tokens (without whitespaces) and nodes, parse an expression
    
    :param tokens: MyLookAhead, a list of tokens
    :param continue_operator: True try to match operator after, False do not  
    
    :returns: Expression
    tokens have been eaten of consumed tokens
    
    """
    result = parse_expression_level3(tokens)
    
    if not result:
        return
     
    token = tokens.look_next()
    expression_list = None
    
    while token == ',':
        token = tokens.consume()
        
        if not expression_list:
            expression_list = ExpressionList()
            expression_list.children.append(result)
            result = expression_list
            
        expression_list.children.append(token)
        
        local_exp = parse_expression_level3(tokens)
        if local_exp:
            expression_list.children.append(local_exp)
        else:
            break
        
        token = tokens.look_next()
    
    token = tokens.look_next()
    if token in Assignement.augassign:
        token = tokens.consume()

        op = Assignement()
        setattr(result, 'parent', op)
        op.children = [result] + [token]
        
        right_expression = parse_expression_level3(tokens)
        
        if right_expression:
            setattr(right_expression, 'parent', op)
            op.children += [right_expression]
        
        op.children += tokens.tokens
        
        result = op
        
    
    return result
    

def parse_expression_level3(tokens):

    current_exp = parse_expression_level2(tokens)
    
    if not current_exp:
        return
    
    token = tokens.look_next()
    if token == 'if':
        
        result = IfTernaryExpression()
        token = tokens.consume()
        setattr(current_exp, 'parent', result)
        result.children = [current_exp, token]
        
        exp = parse_expression_level2(tokens)
        result.children.append(exp)
        e = tokens.look_next()
        if not e == 'else':
            print('warning')
            return exp
        e = tokens.consume()
        result.children.append(e)
        exp = parse_expression_level2(tokens)
        result.children.append(exp)
        
        return result
    
    return current_exp
        

def parse_expression_level2(tokens, continue_operator=True):
    """
    Same as parse_expression for another level of priority
    """
    token = tokens.look_next()
    
    current_exp = None
    
    if token and token.text == 'lambda':
        token = tokens.consume()
        
        l = Lambda()
        l.children.append(token)

        params = LambdaParameters()
        l.children.append(params)
        
        while token != ':':
            
            token = tokens.consume()
            params.children.append(token)
        
        token = tokens.look_next()
        if token.type == StartLine:
            token = tokens.consume() # a fake startLine inserted here
        
        exp = parse_expression_level2(tokens)
        l.children.append(exp)
        current_exp = l
        
    elif token and is_token_subtype(token.type, Keyword):
        keywords = {'yield': Yield, 'yield from': YieldFrom, 'await': Await}

        try:
            result = keywords[token.text]()
        except KeyError:
            return
            
        token = tokens.consume()
           
        result.children.append(token)
        exp = parse_expression_level2(tokens)
        result.children.append(exp)
         
        current_exp = result
    
    
    elif token and token.text == 'not':
        token = tokens.consume()

        result = UnaryNot()
        result.children.append(token)
        
        exp = parse_expression_level2(tokens)
        result.children.append(exp)
        
        current_exp = result

    elif token == '-':
        token = tokens.consume()

        result = Unary()
        result.children.append(token)
        
        exp = parse_expression_level2(tokens)
        result.children.append(exp)
        
        current_exp = result
    
    else:
        
        term = parse_simple_term(tokens)
        if term: 
            current_exp = term
    
    
    if not current_exp:
        return

    
    if not continue_operator:
        return current_exp
    
    # search for bin operators
    token = tokens.look_next()
        
    while token and is_token_subtype(token.type, Operator) and token not in Assignement.augassign:
        # binary op
        token = tokens.consume()
        
        operators = [token]
        
        if token in ['<', '>', 'not']:
            
            _next = tokens.look_next()
            if _next in ['=', 'in']:
                operators.append(tokens.consume())
        
        exp = parse_expression_level2(tokens, False)
        if exp:
            if operators == ['=']:
                op = Assignement()
            elif operators == ['+']:
                op = AdditionExpression()
            elif operators == ['%']:
                op = StringInterpolation()
            else:
                op = BinaryOperation()
            
            setattr(current_exp, 'parent', op)
            setattr(exp, 'parent', op)
            op.children = [current_exp] + operators + [exp]
            
            current_exp = op
        else:
            break
        token = tokens.look_next()
    
    return current_exp

    
def parse_simple_term(tokens):
    """
    Given a list of tokens and nodes, parse an expression
    
    returns 
      Term if found tokens is removed from the element
      None if not found, tokens is unchanged
    
    """
    current_term = None
    
    token = tokens.look_next()
    if not token:
        return
    
    token_type = type(token)
    
    if token_type == Parenthesis:
        token = tokens.consume()
        # recurse inside
        
        if not is_comprehension_for(token):
            parse_parameters(token)
            current_term = token
            
        else:
            
            term =  ComprehensionLoop()
            parse_comprehension_loop(token)
            term.children = [token]
            current_term = term
            
        
    # name like
    elif is_token_subtype(token.type, Name):
        token = tokens.consume()
        term = Identifier()
        term.children = [token]
        current_term = term

    # constants
    elif is_token_subtype(token.type, Literal):
        term = Constant()
        token = tokens.consume()
        term.children = [token]
        try:
            token = tokens.look_next()
            while is_token_subtype(token.type, Literal):
                
                token = tokens.consume()
                term.children.append(token)
                token = tokens.look_next()
        except:
            pass
        current_term = term
    
    elif token_type == SquareBracketedBlock:
        # array
        token = tokens.consume()
        
        if not is_comprehension_for(token):
        
            # recurse inside
            parse_parameters(token)
    
            term = Array()
            term.children = [token]
            current_term = term

        else:
            
            term =  ComprehensionLoop()
            parse_comprehension_loop(token)
            term.children = [token]
            current_term = term
            
        
    elif token_type == BracketedBlock:
        # map
        token = tokens.consume()
        term = Map()
        term.children = [token]
        # recurse
        parse_map_parameters(token)
        current_term = term
    
    if not current_term:
        return None
    
    # search for 
    # .Name
    # ()
    # []
    # ...
    token = tokens.look_next()
    while token == '.' or type(token) == Parenthesis or type(token) == SquareBracketedBlock:

        token = tokens.consume()
        
        if token == '.':
            name = tokens.consume()
            term = DotAccess()
            term.children = [current_term, token, name]
            setattr(current_term, 'parent', term)
            current_term = term
        elif type(token) == Parenthesis:
            
            # recurse inside
            parse_parameters(token)
                        
            term = MethodCall()
            term.children = [current_term, token]
            setattr(current_term, 'parent', term)
            current_term = term
        else:
            # recurse inside
            parse_parameters(token)

            term = ArrayAccess()
            term.children = [current_term, token]
            setattr(current_term, 'parent', term)
            current_term = term
        
        token = tokens.look_next()
    
    return current_term

def is_comprehension_for(parenthesis):
    """
    True when parenthesis of [] is a comprehension for loop
    """
    for token in parenthesis.get_children():
        if token == 'for':
            return True
    
    return False
    
def parse_comprehension_loop(parenthesis):    

    # recurse in parenthesis
    _, tokens, _ = parenthesis._split_block()
    if tokens:
        # remove whitespaces and comments
        tokens = MyLookAhead(list(TokenIterator(tokens)))
        
        exp = parse_expression_level2(tokens)
        
        setattr(exp, 'parent', parenthesis)
        result = [exp]
        
        token = tokens.consume() # normally a for
        
        _for = ComprehensionFor()
        _for.children = [token]

        exp = parse_expression_level2(tokens)
        setattr(exp, 'parent', _for)
        
        expression_list = None
        
        token = tokens.look_next()
        while token == ',':
            
            
            if not expression_list:
                # expression list
                expression_list = ExpressionList()
                setattr(expression_list, 'parent', _for)
                _for.children.append(expression_list)
                
                expression_list.children = [exp]
                setattr(exp, 'parent', expression_list)
            
            
            token = tokens.consume()
            expression_list.children.append(token)

            expression = parse_expression_level2(tokens)
            expression_list.children.append(expression)
            
            token = tokens.look_next()
        
        if not expression_list:
            _for.children.append(exp)
        
        while token == 'if':
            
            token = tokens.consume()
            _for.children.append(token)
            
            expression = parse_expression_level2(tokens)
            _for.children.append(expression)
            token = tokens.look_next()
        
        setattr(_for, 'parent', parenthesis)
        result.append(_for)
        
        new_body = result + tokens.tokens
        
        parenthesis._replace_body(new_body)

def parse_parameters(parenthesis):
    """
    Parse parameters of call, bracket, etc...
    """
    # recurse in parenthesis
    _, tokens, _ = parenthesis._split_block()
    if tokens:
        # remove whitespaces and comments
        tokens = MyLookAhead(list(TokenIterator(tokens)))
        
        result = []
        
        exp = parse_expression_level3(tokens)
        token = tokens.look_next()
        if exp:
            
            if token == '=':
                op = Assignement()
                token = tokens.consume()
                value = parse_expression_level3(tokens)
                
                op.children = [exp, token, value]
                setattr(exp, 'parent', op)
                token = tokens.look_next()
                exp = op
            
            setattr(exp, 'parent', parenthesis)
            result.append(exp)
        
        token = tokens.look_next()
        
        try:
            while token == ',':
                
                token = tokens.consume()
                result.append(token)
                
                expression = parse_expression_level3(tokens)
                if expression:
                    token = tokens.look_next()
                    if token == '=':
                        op = Assignement()
                        token = tokens.consume()
                        value = parse_expression_level3(tokens)
                        
                        op.children = [expression, token, value]
                        setattr(expression, 'parent', op)
                        token = tokens.look_next()
                        
                        expression = op
                    
                    setattr(expression, 'parent', parenthesis)
                    result.append(expression)
                
                token = tokens.look_next()
        except:
            pass
        
        new_body = result + tokens.tokens
        
        parenthesis._replace_body(new_body)


class Value(Node):
    
    def get_key(self):
        children = self.get_children()
        key = next(children)
        return key
    
    def get_value(self):
        children = self.get_children()
        _ = next(children) # key
        try:
            _ = next(children) # :
        except StopIteration:
            # not dictionary but set
            return
        value = next(children)
        return value


def parse_map_parameters(_map):
    """
    Parse the inseid of a map or set
    """
    def parse_value(tokens):
        
        key = parse_expression_level3(tokens)
        if not key:
            return
        token = tokens.consume() # :
        value = parse_expression_level3(tokens)
        result = Value()
        setattr(key, 'parent', result)
        
        if value:
            setattr(value, 'parent', result)
            result.children = [key, token, value]
        else:
            result.children = [key]
        return result
        
    
    _, tokens, _ = _map._split_block()
    if tokens:
        # remove whitespaces and comments
        tokens = MyLookAhead(list(TokenIterator(tokens)))
        
        result = []
        result.append(parse_value(tokens))
        
        token = tokens.look_next()
        
        try:
            while token == ',':
                
                token = tokens.consume()
                result.append(token)
                
                value = parse_value(tokens)
                if value:
                    result.append(value)
                
                token = tokens.look_next()
                
        except:
            pass
        
        new_body = result + tokens.tokens
        
        _map._replace_body(new_body)
    
    
