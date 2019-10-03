'''
A non validating Java parser



'''
import pickle
import os
from .light_parser import Lookahead, Parser, BlockStatement, Statement, Term, Seq, Optional, Node, Token # @UnresolvedImport
from .lexer import JavaLexer
from pygments.token import Keyword
from java_parser.lexer import CommentEndOfLine
from collections import defaultdict

def parse(text, discoverer=None):
    """
    Parse a java code and return a CompilationUnit.
    
    :rtype: CompilationUnit
    """    
    parser = Parser(JavaLexer,
                    [Package, Import, Parenthesis, Bracket, CurlyBracket],
                    )
    
    stream = Lookahead(WhitespaceSkipper(parser.parse(text)))
    
    return JavaParser(discoverer).parse(stream)
    


class WhitespaceSkipper:
    """
    Skip whitespaces.
    """
    def __init__(self, tokens):
        self.tokens = iter(tokens)

    def __iter__(self):
        return self

    def __next__(self):
        token = None
        while not token:
            token = next(self.tokens)
            
            if not type(token) is Token:
                break
            
            if token.is_whitespace():
                token = None
        
        return token
    
    def __repr__(self):
        return str(self.tokens)


class JavaParser:
    
    def __init__(self, discoverer):
        
        self.result = CompilationUnit(discoverer)
        
    def parse(self, stream):
#         print()
        modifiers = None
        elements_before = []
        new_children = []
        scope = CompilationUnit(None)
        
        try:
            while True:
                token = next(stream)
#                 print(token)

                # store some elements still unassigned
                if token.is_comment():
                    elements_before.append(token)
                elif is_modifier(token):
                    modifiers = self.parse_modifiers(token, stream)
                    elements_before.append(modifiers)
                    
                elif isinstance(token, CurlyBracket):
                    # initialiser
                    if modifiers:
                        
                        # leave comments
                        
                        init = StaticInitializer(scope)
                        init.children += elements_before
                        elements_before = []
                        init.children.append(token)
                        new_children.append(init)
                    else:
                        # class init
                        new_children.append(token)
                        
                else:
                    # method/constructor/variable eat till ; or {}
                    local_children = []

                    seen_assignement = False
                    seen_parenthesis = False
                    seen_comma = False
                    length = 0
                    
                    while token != ';' and (not isinstance(token, CurlyBracket) or seen_assignement):
                        if token == '=':
                            seen_assignement = True
                            
                        if isinstance(token,Parenthesis) and not seen_assignement:
                            seen_parenthesis = True
                            self.parse_formal_parameters(token)
                            length = len(local_children)
                            
                        local_children.append(token)
                        
                        if token == '=':
                            token = next(stream)
                            while token.is_whitespace() or token.is_comment():
                                local_children.append(token)
                                token = next(stream)
                            local_children.append(self.parse_expression(token, stream, scope))
                        
                        token = next(stream)
#                         print(token, scope.is_enum())
#                         if scope.is_enum() and token in [',', ';', '}'] and not seen_semi_colon:
#                             seen_comma = True
#                             break
                    
                    if token == ';':
                        seen_semi_colon = True
                        
                    if isinstance(token, CurlyBracket):
                        # procedure like
                        self.parse_simple_statements(token)
                    
                    # keep the last one
                    local_children.append(token)
                    
                    # one can write 
                    # void f(...) {...};
#                     print('next', stream.look_next())
                    try:
                        if stream.look_next() == ';':
                            token = next(stream)
                            local_children.append(token)
                            seen_semi_colon = True
                    except StopIteration:
                        pass
                    
                    # @todo simplify
                    stream.start_lookahead()
                    try:
                        
                        look_next = next(stream)
                        while look_next.is_whitespace():
                            look_next = next(stream)
                        
                        # comment at the end of line are treated separatly
                        if look_next.type == CommentEndOfLine:
                            local_children += stream.stop_lookahead_and_consume()
                        else:
                            stream.stop_lookahead()
                    except:
                        stream.stop_lookahead()
                    
                    
                    # switch on type
                    element = None
                    
                    if seen_comma:
                        element = EnumValue(scope)
                    elif not seen_parenthesis:
                        element = VariableDeclaration(scope)                        
                    elif length == 1:
                        # constructor
                        element = Constructor(scope)
                    else:
                        element = Method(scope)
                        
                    # put what we have eaten
                    element.children += elements_before
                    
                    element.children += local_children

                    element.on_end()
                    
                    # re-init 
                    elements_before = []
                    modifiers = None
                    
                    new_children.append(element)

#                 print('next loop')
        except StopIteration:
            pass
            
        scope.elements = new_children
        return new_children

    def parse_annotation(self, token, stream, scope):
        """
        Parse an annotation
        """
        result = Annotation()
        result.children = [token]
        
        parenthesis = stream.look_next()
        
        if isinstance(parenthesis, Parenthesis):
            next(stream)
            result.children.append(parenthesis)
            self.recurse_on_annotation(parenthesis, scope)
            
            # parse annotation values
            elements = parenthesis.get_children()
            next(elements) # (
            try:
                
                first = True
                while True:
                    name_or_value = next(elements)
                    
                    next_is_equal = False
                    try:
                        next_is_equal = elements.look_next() == '='
                    except StopIteration:
                        pass
                    
                    if next_is_equal:
                        # named parameter
                        element_name = name_or_value.text
                        next(elements) # '='
                        value = next(elements)
                        
                        result.named_parameter_expressions[element_name] = self.parse_constant(value, elements, scope)
                    elif name_or_value not in [')', ',']:
                        # positional parameter
                        constant = self.parse_constant(name_or_value, elements, scope)
                        if first:
                            result.named_parameter_expressions['value'] = constant
                            
                
            except StopIteration:
                pass
            
            
            
        result.on_end()
        return result
    
    def recurse_on_annotation(self, parenthesis, scope):
        """
        Parse annotation inside annotations.
        """
        
        stream = Lookahead(WhitespaceSkipper(parenthesis.children))
        token = next(stream)
        
        new_children = []
        
        try:
            
            while True:
                
                if is_annotation(token):
                    new_children.append(self.parse_annotation(token, stream, scope))
                else:
                    new_children.append(token)
                    if isinstance(token, Node):
                        self.recurse_on_annotation(token, scope)
                
                token = next(stream)
            
        except StopIteration:
            pass        
        
        parenthesis.children = new_children
        
        
    def parse_modifiers(self, token, stream):
        """
        Parse a modifer list
        """
        result = Modifiers()
        result.children = [token]
        
        modifier = stream.look_next()
        
        while is_modifier(modifier):
            next(stream)
            result.children.append(modifier)
            modifier = stream.look_next()
            
        return result
    
    def parse_simple_statements(self, curly_bracket):
        
        stream = Lookahead(curly_bracket.children)
        new_children= [next(stream)] # skip {
        
        catches = []
        
        try:
            while True:
                
                token = next(stream)
                if token.text == 'catch':
                    # catch (...) {...}
                    catch = Catch()
                    catch.children.append(token)
                    catch.children.append(next(stream))
                    catch.children.append(next(stream))
                    
                    catches.append(catch)
                elif token.text == 'finally':
                    # finally  {...}
                    catch = Finally()
                    catch.children.append(token)
                    catch.children.append(next(stream))
                    
                    catches.append(catch)
                else:
                    # something else than a catch series... 
                    if catches:
                        c = Catches()
                        c.children = catches
                        
                        new_children.append(c)
                    else:
                        new_children.append(token)
                if is_name(token):
                    
                    n = stream.look_next()
                    if n == ';':
                        # name ;
                        statement = ExpressionStatement()
                        statement.children.append(token)
                        statement.children.append(next(stream))
                        new_children.append(statement)
                    elif isinstance(n, Parenthesis):
                        # name (...) ;
                        statement = ExpressionStatement()
                        statement.children.append(token)
                        statement.children.append(next(stream))
                        statement.children.append(next(stream))
                        new_children.append(statement)
                        
                    
                    
                
        except StopIteration:
            pass
        
        
        curly_bracket.children = new_children
    
    def parse_expression(self, token, stream, scope):
        """
        @todo
        """
        if token.text and token.text[0] in ['"', "'"]:
            return self.parse_simple_constant(token, scope)
        
        return token
    
    def parse_constant(self, token, stream, scope):
        
        result = self.parse_simple_constant(token, scope)
        
        token = stream.look_next()
        while token in ['+', '-', '*', '/']:
            operator = next(stream)
            token = next(stream)
            right = self.parse_simple_constant(token, scope)
            result = BinaryExpression(result, operator, right)
            token = stream.look_next()

        return result
    
    def parse_simple_constant(self, token, scope):
        """
        :rtype: Expression
        """
        if isinstance(token, CurlyBracket):
            # a set of value
            result = []
            sub_values = token.get_children()
            next(sub_values) # {
            try:
                while True:
                    sub_value = next(sub_values)
                    result.append(self.parse_constant(sub_value, sub_values, scope))
                    next(sub_values) # ,
            except StopIteration:
                pass
            return List(result)
        elif isinstance(token, Parenthesis):
            sub_values = token.get_children()
            next(sub_values) # (
            try:
                sub_value = next(sub_values)
                return self.parse_constant(sub_value, sub_values, scope)
            except StopIteration:
                pass
            
        elif isinstance(token, Annotation):
            return token
        else:
            
            # try to convert value...
            if token.text and token.text[0] in ['"', "'"]:
                return ConstantString(token.text[1:-1])
            else:
                try:
                    int(token.text)
                    return ConstantInteger(token)
                except:
                    try:
                        float(token.text)
                        return ConstantInteger(token)
                    except:
                        pass
            # defaulting
            return Identifier(token, scope)

    
    
    def parse_formal_parameters(self, parenthesis):
        
        children = parenthesis.get_children()
        
        new_children = [next(children)] # openning parenthesis
        
        try:
            
            while True:
                elements = []
                token = next(children)
                
                if token == 'final':
                    elements.append(token)
                    token = next(children)
                
                while is_annotation(token):
                    elements.append(self.parse_annotation(token, children, self.result)) # not sure here
                    token = next(children)
                
                elements.append(self.parse_type(token, children))
                elements.append(next(children))
                
                parameter = FormalParameter()
                parameter.children = elements
                
                new_children.append(parameter)
                new_children.append(next(children)) # comma
            
        except StopIteration:
            pass
        
        parenthesis.children = new_children
        
        
        
    
    def parse_type(self, token, stream):
        
        result = self.parse_non_array_type(token, stream)
        
        try:
            current = stream.look_next()
            while isinstance(current, Bracket):
                current = next(stream)
                temp = ArrayType()
                temp.children.append(result)
                temp.children.append(current)
                
                result = temp
                
                current = stream.look_next()
        except StopIteration:
            pass
        
        return result
        
    
    
    def parse_generic_parameter(self, token, stream):
        """
        token == '<'
        """
        # ?|<type> [extends <type> & <type> ...]
        # empty
        
        result = GenericParameter()
        result.children.append(token)
        
        try:
            while True:
                
                current_token = next(stream)
                if current_token == '>':
                    result.children.append(current_token)
                    return result
                elif current_token not in ['?', ',', '&', 'extends', 'super']:
                    result.children.append(self.parse_type(current_token, stream))
                else:
                    result.children.append(current_token)
        
        except StopIteration:
            pass
        
        return result
    
    def parse_non_array_type(self, token, stream):
        """
        Type without []
        """
        if token.text in ['void', 'byte' , 'short', 'int', 'long', 'float', 'double', 'boolean', 'char']:
            return SimpleType(token)

        next_token = stream.look_next()
        if next_token != '<':
            
            return SimpleType(token)
        
        
        result = GenericType()
        result.children.append(token)
    
        token = next(stream)
        result.children.append(self.parse_generic_parameter(token, stream))
        
        return result
     
    

# classical opening

class Parenthesis(BlockStatement):

    begin = '('
    end   = ')'
    
    
class Bracket(BlockStatement):

    begin = '['
    end   = ']'
    
    
class CurlyBracket(BlockStatement):

    begin = '{'
    end   = '}'



class Scope:
    
    def __init__(self, parent=None):
        self.parent = parent


    def resolve_qname(self, qualified_name):
        """
        Resolve a qualified name
        """
        names = qualified_name.split('.')
        
        current_scope = self
        
        for name in names:
            
            if isinstance(current_scope, Scope):
                current_scope = current_scope.resolve_name(name)
                if not current_scope:
                    return None
            else:
                return None
        
        return current_scope

    def resolve_name(self, name):
        """
        Try to resolve an unqualified name in the current scope.
        """
        
        local = self.local_resolve_name(name)
        if local:
            return local
        
        if self.parent:
            return self.parent.resolve_name(name)
        
        
    def local_resolve_name(self, name):
        
        pass


class CompilationUnit(Scope):
    """
    Root of AST.
    """
    def __init__(self, discoverer):
        
        Scope.__init__(self)
        # a file discoverer, optional
        self.discoverer = discoverer
        self.package = None
        self.imports = []
        self.type_declaration = None
        self.elements = []
        
        self.elements_by_fullname = defaultdict(list)

    def get_type_declaration(self):
        """
        Access to the class/enum/interface/... defined in this compilation unit.
        
        :rtype: Class
        """
        return self.type_declaration
    
    def get_possible_qualified_names(self, name):
        """
        Given a name, returns the list of possible qualified names.
        
        Using package and imports, one can determine the list of possible qualified names of a Java name.
        
        This information is generally enough for most usages.
        
        Examples :
        
            import java.util.RequestMapping;
            @RequestMapping // possible qualified names are java.util.RequestMapping
            public class MyClass {}
            
            ...
            
            package mypackage;
            @RequestMapping // possible qualified names are mypackage.RequestMapping
            public class MyClass {}
            
            ...
            
            package mypackage;
            import java.util.*;
            @RequestMapping // possible qualified names are mypackage.RequestMapping and java.util.RequestMapping
            public class MyClass {}
            
                 
        """
        # @todo can be a relative name for a an inner class...
        if '.' in name:
            return [name] # already qualified
        
        result = []
        
        for _import in self.imports:
            qname = _import.get_name().split('.')
            if len(qname) == 1:
                continue
            imported = qname[-1]
            if imported == name:
                return ['.'.join(qname)] # unique solution
            
            # import *
            if imported == '':
                qname[-1] = name
                # one of the possible solutions
                result.append('.'.join(qname))
        
        # package + name is also a solution
        if self.package:
            result.append(self.package.get_name() + '.' + name)
        else:
            result.append(name)
            
        return result
    
    def local_resolve_name(self, name):
        
        # is it the local class ?
        if self.type_declaration and name == self.type_declaration.name:
            return self.type_declaration
         
        # is it something imported ?
#         for fullname in self.get_possible_qualified_names(name):
#             
#             pathes = [path for path in self.discoverer.get_pathes(fullname) if os.path.exists(path)]
#             
#             # else ambiguous...
#             if len(pathes) == 1:
#                 
#                 with open_source_file(pathes[0]) as f:
#                     
#                     compilation_unit = parse(f.read(), self.discoverer)
#                     return compilation_unit.local_resolve_name(name)
    
    
    def _calculate_elements_by_fullname(self):
    
        if not self.elements_by_fullname:
            
            for element in self.elements:
                
                if isinstance(element, VariableDeclaration):
                    self.elements_by_fullname[element.name.text].append(element)
    
    def get_element(self, fullname):
        """
        Search a class, method, field etc... by its fullname
        """
        self._calculate_elements_by_fullname()
        
        try:
            return self.elements_by_fullname[fullname]
        except:
            pass
                
    def save(self, path):
        """
        Passivation to disk
        """
        with open(path, "wb") as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)
            
            
    @staticmethod
    def load(path):
        """
        Depassivation from disk
        """
        with open(path, "rb") as f:
            return pickle.load(f)
    
    

class Package(Statement):

    begin = 'package'
    end   = ';'
    
    def __init__(self):
        Statement.__init__(self)
        self.name = None
    
    def get_name(self):
        """
        Get package name.
        
        :rtype: str
        """
        return self.name.text;
    
    def on_end(self):

        tokens = self.get_children()
        next(tokens)
        token = next(tokens)
        self.name = token
        

class Import(Statement):

    begin = 'import'
    end   = ';'

    def get_name(self):
        """
        Get imported name.

        :rtype: str
        """
        return self.name.text;
    
    def on_end(self):

        tokens = self.get_children()
        next(tokens)
        token = next(tokens)
        self.name = token

def is_annotation(token):
    
    return token.text and token.text[0] == '@' and not token.text == '@interface'

def is_modifier(token):
    
    return token.text in ['public', 'private', 'protected', 
                          'abtsract', 'static', 'final', 'strictfp',
                          'native', 'synchronized', 'transient']

def is_class(token):
    
    return token.text in ['class', 'interface', 'enum', '@interface']    


def parse_constant(value):
    """
    value is a constant element
    
    :rtype: python type with correct elements (for example list of string/int, ...)
    """
    if isinstance(value, CurlyBracket):
        # a set of value
        result = []
        sub_values = value.get_children()
        next(sub_values) # {
        try:
            while True:
                
                sub_value = next(sub_values)
                result.append(parse_constant(sub_value))
                next(sub_values) # ,
        except StopIteration:
            pass
    
        return result
    elif isinstance(value, Annotation):
        return value
    else:
        
        # try to convert value...
        if value.text and value.text[0] in ['"', "'"]:
            return value.text[1:-1]
        else:
            try:
                return int(value.text)
            except:
                try:
                    return float(value.text)
                except:
                    pass
        return value.text


class Annotation(Term):
    """
    An annotation
    """

    def __init__(self):
        Term.__init__(self)
        self.name = None
        self.named_parameters = {}
        self.named_parameter_expressions = {}
        self.named_parameters_calculated = False
    
    def get_type_name(self):
        """
        Get the name of the annotation class.

        :rtype: str
        """
        return self.name
        
    def get_named_parameters(self):
        """
        Get the annotation named parameters.
        
        :rtype: map str -> something (int, str)
        """
        if not self.named_parameters_calculated:
            
            self.named_parameters = {}
            for key in self.named_parameter_expressions:
                
                self.named_parameters[key] = self.named_parameter_expressions[key].evaluate_as_constant()
            
            self.named_parameters_calculated = True
            
        return self.named_parameters

    def evaluate_as_constant(self):
        """
        Evaluate an expression as a constant.
        """
        return self

    def to_text(self):
        return str(self)

    def on_end(self):

        tokens = self.get_children()
        name = next(tokens)
        self.name = name.text[1:]
        
        try:
            parenthesis = next(tokens)
            elements = parenthesis.get_children()
            next(elements) # (
            try:
                
                first = True
                while True:
                    name_or_value = next(elements)
                    
                    next_is_equal = False
                    try:
                        next_is_equal = elements.look_next() == '='
                    except StopIteration:
                        pass
                    
                    if next_is_equal:
                        # named parameter
                        element_name = name_or_value.text
                        next(elements) # '='
                        value = next(elements)
                        
                        self.named_parameters[element_name] = parse_constant(value)
                    elif name_or_value not in [')', ',']:
                        # positional parameter
                        constant = parse_constant(name_or_value)
                        if first:
                            self.named_parameters['value'] = constant
                            
                
            except StopIteration:
                pass
            
            
        except StopIteration:
            pass
        

def match_annotation_list(_token, stream):
    
    token = _token
    
    index_of_stream = stream.tokens.index
    
    seen = False
    # accepts list of annotations
    while isinstance(token, Annotation):
        # this index is correct
        index_of_stream = stream.tokens.index
        token = next(stream)
        seen = True
    
    # whatever reason we reput as the last one correct
    stream.tokens.index = index_of_stream
    
    return seen


def match_modifier_list(_token, stream):

    token = _token

    index_of_stream = stream.tokens.index
    
    seen = False
    
    # then things like public, etc...
    while token.text in ['public', 'private', 'protected', 
                         'abtsract', 'static', 'final', 'strictfp',
                         'native', 'synchronized', 'transient']:
        # this index is correct
        index_of_stream = stream.tokens.index
        token = next(stream)
        seen = True
    
    # whatever reason we reput as the last one correct
    stream.tokens.index = index_of_stream
    
    return seen




class Modifiers(Term):
    
    match = match_modifier_list


def is_name(token):
    
    return not is_keyword(token) and token.text and token.text[0].isalpha()


class JavaStructureElement:
    
    def get_header_comments(self):
        
        tokens = iter(self.children)
        
        result = []
        token = None
        try:
            while token not in ['class', 'interface', 'enum', '@interface']:
                token = next(tokens)
                if token.is_comment():
                    result.append(token)
        except StopIteration:
            pass
        
        return result


class Class(JavaStructureElement, BlockStatement, Scope):
    """
    Class, interface, enum, annotation.
    
    [AnnotationList] [Modifiers] class|interface|enum|@intereface <name> ... CurlyBracket
    """
    
    def __init__(self, parent):
        BlockStatement.__init__(self)
        Scope.__init__(self, parent)
        self.name = None
        self.annotations = []
        self.modifiers = []
        self.extends = []

    def get_name(self):
        """
        Access to class name

        :rtype: str
        """
        return self.name.text
    
    def get_annotations(self):
        """
        Access to class annotations
        
        :rtype: list of Annotation
        """
        return self.annotations
    
    def get_modifiers(self):
        """
        Access to class modifiers
        """
        return self.modifiers
    
    def get_extends(self):
        """
        Inherited class or None
        
        @todo implement
        :rtype: Class or NoneType
        """
        return self.extends
    
    def get_methods(self):
        """
        Access to class methods

        :rtype: list of Method
        """
        # not in on_end, because would not work
        for block in self.get_sub_nodes(CurlyBracket):
            
            return list(block.get_sub_nodes(Method))
            
    def get_constructors(self):
        """
        Access to class constructors
        
        :rtype: list of Constructor
        """
        # not in on_end, because would not work
        for block in self.get_sub_nodes(CurlyBracket):
            
            return list(block.get_sub_nodes(Constructor))

    def get_fields(self):
        """
        Access to class fields

        :rtype: list of VariableDeclaration
        """
        # not in on_end, because would not work
        for block in self.get_sub_nodes(CurlyBracket):
            return list(block.get_sub_nodes(VariableDeclaration))

    def get_enum_values(self):
        """
        In case of enum access to constants.
        """
        for block in self.get_sub_nodes(CurlyBracket):
            return list(block.get_sub_nodes(EnumValue))

    def get_instance_initializers(self):
        """
        :rtype: list of CurlyBracket
        """
        for block in self.get_sub_nodes(CurlyBracket):
            return list(block.get_sub_nodes(CurlyBracket))

    def get_static_initializers(self):
        """
        :rtype: list of StaticInitializer
        """
        for block in self.get_sub_nodes(CurlyBracket):
            return list(block.get_sub_nodes(StaticInitializer))
    
    def get_type_declarations(self):
        """
        Inner class declarations.
        
        :rtype: list of Class
        """
        for block in self.get_sub_nodes(CurlyBracket):
            return list(block.get_sub_nodes(Class))
    
    def is_enum(self):
        """
        True if class is an enum
        """
        tokens = self.get_children()
        kind = tokens.move_to(['class', 'interface', 'enum', '@interface'])
        return kind == 'enum'
    
    def local_resolve_name(self, name):
        
        for child in self.get_methods():
            if child.name == name:
                return child
        
        for child in self.get_constructors():
            if child.name == name:
                return child

        for child in self.get_fields():
            if child.name == name:
                return child

        for child in self.get_type_declarations():
            if child.name == name:
                return child
        
        pass
    
    def on_end(self):
        
        self.annotations = list(self.get_sub_nodes(Annotation))
        
        for modifiers in self.get_sub_nodes(Modifiers):
            self.modifiers = list(modifiers.get_children())

        tokens = self.get_children()
        tokens.move_to(['class', 'interface', 'enum', '@interface'])
           
        
        self.name = next(tokens)
def is_keyword(token):
    
    return token.type == Keyword


def is_type(token, stream):
    
    if not is_non_array_type(token, stream):
        return False
    
    index_of_stream = stream.tokens.index
    
    try:
        token = next(stream)
        
        while isinstance(token,Bracket):
            index_of_stream = stream.tokens.index
            token = next(stream)
        
    except StopIteration:
        pass
    stream.tokens.index = index_of_stream
    return True

def is_generic_type_parameter(token, stream):
    
    # ?|<type> [extends <type> & <type> ...]
#         print("is_generic_type_parameter", stream.tokens.index, stream.tokens)
    
    if token != '?' and not is_type(token, stream):
        return False
    
    index_of_stream = stream.tokens.index
    token = next(stream)
    if token.text != 'extends':
        stream.tokens.index = index_of_stream
        return True
    
    token = next(stream)
    if not is_type(token, stream):
        stream.tokens.index = index_of_stream
        return False
    
    index_of_stream = stream.tokens.index
    token = next(stream)
    while token == '&':
        token = next(stream)
        is_type(token, stream)
        
        index_of_stream = stream.tokens.index
        token = next(stream)

    stream.tokens.index = index_of_stream
    return True
    
def is_non_array_type(token, stream):
    """
    Type without []
    """
    if token.text in ['void', 'byte' , 'short', 'int', 'long', 'float', 'double', 'boolean', 'char']:
        return True
    
    if not is_name(token):
        return False
    
    # for rollbacking
    index_of_stream = stream.tokens.index
    
    try:
        token = next(stream)
        if token != '<':
            stream.tokens.index = index_of_stream
            return True
    
        # here we have matched 
        # name <  
    
    
        index_of_stream = stream.tokens.index
        token = next(stream)
        while is_generic_type_parameter(token, stream):
            token = next(stream)
            if token == '>':
                break
            if token == ',':
                token = next(stream)
            else:
                # something bad happenned
                stream.tokens.index = index_of_stream
                return False

    except StopIteration:
        pass
        
    # and again with commas till > 
    return True
    

def is_throws(token, stream):
    
    if token.text != 'throws':
        return False
    
    # eats type, type, ...
    # fragile...
    token = next(stream)
    while is_type(token, stream):
        index_of_stream = stream.tokens.index
        
        token = next(stream)
        if token != ',':
            stream.tokens.index = index_of_stream
            return True
        else:
            token = next(stream)
    

class Throws(Term):
    
    match = is_throws


class MethodLike(Scope):
    
    def __init__(self, parent):
        Scope.__init__(self, parent)
        self.__parsed = False
    
    def get_statements(self):
        """
        Access to method statements
        """
        for block in self.get_sub_nodes(CurlyBracket):
            
            # on demand statement parsing
            if not self.__parsed:
                parser = Parser(JavaLexer,
                                [Assert, Break, Continue, Return, Throw, Switch, DoWhile, Try],
                    )
                
                # need one loop to force the parsing
                for _ in recursive_statement_pass(parser.parse_stream([block])):
                    pass
                
                self.__parsed = True
                
            return list(block.get_sub_nodes(JavaStatement))
    
    def get_parameters(self):
        """
        Access to method parameters
        
        :rtype: list FormalParameter
        """
        for parenthesis in self.get_sub_nodes(Parenthesis):
        
            return list(parenthesis.get_sub_nodes(FormalParameter))
            

class EnumValue(JavaStructureElement, Term):
    
    def __init__(self, parent):
        Term.__init__(self)
        self.name = None
        self.annotations = []
        
    def get_name(self):
        """
        Access to name.

        :rtype: str
        """
        return self.name.text
    
    def on_end(self):
        
        self.annotations = list(self.get_sub_nodes(Annotation))

        tokens = self.get_children()
        token = next(tokens)

        while isinstance(token, Annotation):
            token = next(tokens)
        
        # here we assume that name is a single token
        self.name = token
        

class Method(JavaStructureElement, Term, MethodLike):
    """
    [AnnotationList] [Modifiers] [AnnotationList] <type> <identifier> Parenthesis [throws <type>, ...] CurlyBracket|;
    """
    
    def __init__(self, parent):
        Term.__init__(self)
        MethodLike.__init__(self, parent)
        
        self.name = None
        self.annotations = []
        self.modifiers = []
        self.type = []
        
    def get_name(self):
        """
        Access to name.

        :rtype: str
        """
        return self.name.text
        
    def get_annotations(self):
        """
        Access to class annotations
        """
        return self.annotations
    
    def get_modifiers(self):
        """
        Access to class modifiers
        """
        return self.modifiers
    
    def on_end(self):
        
        self.annotations = list(self.get_sub_nodes(Annotation))

        tokens = self.get_children()
        token = next(tokens)
        
        while isinstance(token, Annotation):
            token = next(tokens)
            
        if isinstance(token, Modifiers):
            self.modifiers += list(token.get_children())
            token = next(tokens)
        
        # here we are on type...
        while not isinstance(token, Parenthesis):
            self.type.append(token)
            token = next(tokens)
        
        # here we assume that name is a single token
        self.name = self.type[-1]
        self.type = self.type[:-1]
        
        # here token is parenthesis and contains parameters... 


class Constructor(JavaStructureElement, Term, MethodLike):
    """
    [AnnotationList] [Modifiers] <identifier> Parenthesis [throws <type>, ...] CurlyBracket
    """
    
    def __init__(self, parent):
        Term.__init__(self)
        MethodLike.__init__(self, parent)
        
        self.name = None
        self.annotations = []
        self.modifiers = []
        
    def get_name(self):
        """
        Access to name.
        :rtype: str
        """
        return self.name.text
        
    def get_annotations(self):
        """
        Access to class annotations
        """
        return self.annotations
    
    def get_modifiers(self):
        """
        Access to class modifiers
        """
        return self.modifiers
    
    def on_end(self):
        
        tokens = self.get_children()
        token = next(tokens)
        
        self.annotations = list(self.get_sub_nodes(Annotation))
        
        while isinstance(token, Annotation):
            token = next(tokens)
        
        if isinstance(token, Modifiers):
            self.modifiers += list(token.get_children())
            token = next(tokens)
        
        self.name = token
        
        # here token is parenthesis and contains parameters... 


class StaticInitializer(Term, MethodLike):
    
    match = Seq('static', CurlyBracket)

    def __init__(self, parent):
        Term.__init__(self)
        MethodLike.__init__(self, parent)


class VariableDeclaration(JavaStructureElement, Statement, Scope):
    """
    Member variable also...
    
    [AnnotationList] [Modifiers] <type> <identifier> [= ...] ;
    """

    def __init__(self, parent):
        Statement.__init__(self)
        Scope.__init__(self, parent)
        self.name = None
        self.annotations = []
        self.modifiers = []
        self.type = []
        self.initialisation = None
        
    def get_name(self):
        """
        Access to name.
        :rtype: str
        """
        return self.name.text
        
    def get_annotations(self):
        """
        Access to class annotations
        """
        return self.annotations
    
    def get_modifiers(self):
        """
        Access to class modifiers
        """
        return self.modifiers
    
    def get_initialisation(self):
        """
        :rtype: Expression
        """
        return self.initialisation
        
        
    def on_end(self):
        
        self.annotations = list(self.get_sub_nodes(Annotation))

        tokens = self.get_children()
        token = next(tokens)

        while isinstance(token, Annotation):
            token = next(tokens)

        if isinstance(token, Modifiers):
            self.modifiers += list(token.get_children())
            token = next(tokens)
        
        # here we are on type...
        while not token in ['=', ';']:
            self.type.append(token)
            token = next(tokens)
        
        # here we assume that name is a single token
        self.name = self.type[-1]
        self.type = self.type[:-1]
        
        if token != '=':
            return
        
        self.initialisation = next(tokens)
        

### For statements
"""


Todo:

    synchronized ParExpression Block


Hope useless ??:
    Identifier : Statement
    ;

Partially :
##  StatementExpression ;

    method ... ;

Done:
**  Block
**  do Statement while ParExpression ;
**  assert Expression [: Expression] ;
**  switch ParExpression { SwitchBlockStatementGroups } 
**  break [Identifier] ;
**  continue [Identifier] ;
**  return [Expression] ;
**  throw Expression ;
**  if ParExpression Statement [else Statement] 
**  for ( ForControl ) Statement
**  while ParExpression Statement
**  try Block (Catches | [Catches] Finally)
**  try ResourceSpecification Block [Catches] [Finally]

"""
"""
Expressions:

Todo:
  new <expression> ;
  
  
  
  
"""


class JavaStatement():
    pass


class JavaSimpleStatement(JavaStatement, Statement):
    pass


class JavaBlockStatement(JavaStatement, BlockStatement):
    pass


class Assert(JavaSimpleStatement):

    begin = 'assert'
    end   = ';'


class Break(JavaSimpleStatement):

    begin = 'break'
    end   = ';'


class Continue(JavaSimpleStatement):

    begin = 'continue'
    end   = ';'


class Return(JavaSimpleStatement):

    begin = 'return'
    end   = ';'


class Throw(JavaSimpleStatement):

    begin = 'throw'
    end   = ';'


class Catch(Term):
    
    match = Seq('catch', Parenthesis, CurlyBracket)



def is_catches(token, stream):
    """
    catches ... and finally
    """
    if isinstance(token, Finally):
        return False
    
    if not isinstance(token, Catch):
        return False
    
    # eats Catch Catch
    index_of_stream = stream.tokens.index

    try:
        token = next(stream)

        while isinstance(token, Catch) or isinstance(token, Finally):
            index_of_stream = stream.tokens.index
            token = next(stream)
            
    except:
        pass
    
    stream.tokens.index = index_of_stream
    return True
    

class Catches(Term):
    
    match = is_catches


class Finally(Term):

    match = Seq('finally', CurlyBracket)


class Try(JavaStatement, Term):
    
    match = Seq('try', Optional(Parenthesis), CurlyBracket, Optional(Catches))
    
    def get_catches(self):
        """
        Access to catches blocks
        """
        for node in self.get_sub_nodes(Catches):
            return node.get_sub_nodes(Catch)

    
    def get_finally(self):
        """
        Access to finally block if exist
        """
        for node in self.get_sub_nodes(Catches):
            for f in node.get_sub_nodes(Finally):
                return f
    
    

class Switch(JavaSimpleStatement):

    begin = 'switch'
    end   = CurlyBracket


class ExpressionStatement(JavaStatement, Term):

    match = Seq(is_name, Optional(Parenthesis), ';')


class DoWhile(JavaBlockStatement):
    
    begin = 'do' 
    end   = Seq('while', Parenthesis, ';')

    def get_statemens(self):
        # @todo
        pass
    

class If(JavaBlockStatement):
    
    
    def get_condition(self):
        """
        The condition of the if
        """
        return list(self.get_sub_nodes())[0]
        
    def get_then(self):
        """
        The then part
        """
        return list(self.get_sub_nodes())[1]
    
    def get_else(self):
        """
        The else part
        """
        try:
            return list(self.get_sub_nodes())[2]
        except:
            pass


class For(JavaBlockStatement):

    def get_for_control(self):
        """
        The control of the for
        
        for (....)
            ------
        """
        return list(self.get_sub_nodes())[0]
    
    def get_statement(self):
        """
        Access to the statement looped.
        """
        return list(self.get_sub_nodes())[1]
        


class While(JavaBlockStatement):

    def get_condition(self):
        """
        The condition of the while
        """
        return list(self.get_sub_nodes())[0]

    def get_statement(self):
        """
        Access to the statement looped.
        """
        return list(self.get_sub_nodes())[1]

    
def recursive_statement_pass(stream):
    """
    Special treatment for if/for/while
    """
    
    for node in stream:
        handle_node(node)
        yield node


def handle_node(node):
    
    # recurse
    if isinstance(node, Node):
        for sub in node.get_sub_nodes():
            handle_node(sub)
    
    if isinstance(node, CurlyBracket):
        handle_block(node)
    

def handle_block(node):
    """
    Here we get the CurlyBracket nodes
    """
#     print('handling block...')
    
    # re-manipulate node.children to create sub nodes for if/else, for () statement, while () statement,
    stream = SimpleStream(node.children)

    new_children = []
    
    try:
        while True:
            new_children.append(consume(stream))
            
    except StopIteration:
        pass
    
    
    node.children = new_children
    
#     print()
#     for child in new_children:
#         print(' ', child)


class SimpleStream:
    
    def __init__(self, elements):
        
        self.elements = elements
        self.index = 0
        
    def __iter__(self):
        return self

    def __next__(self):
        
        try:
            index = self.index
            self.index += 1
            return self.elements[index]
        except:
            raise StopIteration
    
    def look_next(self):
        
        return self.look(1)
    
    def look(self, delta):
        """
        Look future...
        """
        try:
            return self.elements[self.index+delta]
        except:
            return None
    
    def peek_next(self):
        """
        Look for the next significative token
        """
        delta = 1
        peek = None
        while True:
            
            peek = self.look(delta)
            delta += 1
            
            if not peek:
                break
            if not (peek.is_whitespace() or peek.is_comment()):
                break
        
        return peek
    


def eat_statement(stream, l):

    # eat up to a node
    # recursive, but will not work for 1; ...
    while True: 
        then = consume(stream)
        l.append(then)
        if isinstance(then, Node):
            break



def consume(stream):
    """
    Main parsing for if, for, while
    """
    token = next(stream)
    if token.text == 'if':
        
        result = If()
        result.children.append(token)
        
        # eat up to parenthesis
        while True: 
            token = next(stream)
            result.children.append(token)
            if isinstance(token, Parenthesis):
                break
        
#         print(result.children)
        eat_statement(stream, result.children)
#         print(result.children)

        # have we a else ?
        peek = stream.peek_next()
#         print(peek)
        if peek.text == 'else':
            
            # eat up to else
            while True:
                token = next(stream)
                result.children.append(token)
                if token.text == 'else':
                    break
            
            # eat the next statement
            eat_statement(stream, result.children)
        
        return result
    
    elif token.text == 'for':
        
        result = For()
        result.children.append(token)
        
        # eat up to parenthesis
        while True: 
            token = next(stream)
            result.children.append(token)
            if isinstance(token, Parenthesis):
                break
        
        eat_statement(stream, result.children)
        
        return result

    elif token.text == 'while':
        
        result = While()
        result.children.append(token)
        
        # eat up to parenthesis
        while True: 
            token = next(stream)
            result.children.append(token)
            if isinstance(token, Parenthesis):
                break
        
        eat_statement(stream, result.children)
        
        return result
    
    return token 


# ???
        
class Expression:
    pass

    def evaluate_as_constant(self):
        """
        Evaluate an expression as a constant.
        """
        return ""


class BinaryExpression(Expression):

    def __init__(self, left, operator, right):
        Expression.__init__(self)
        self.left = left
        self.operator = operator
        self.right = right

    def evaluate_as_constant(self):
        """
        Evaluate an expression as a constant.
        """
        
        # only + for the moment
        if self.operator == '+':
        
            left = self.left.evaluate_as_constant()
            right = self.right.evaluate_as_constant()
            
            return left + right
        else:
            return self.left.to_text() + self.operator.text + self.right.to_text()
    
    def to_text(self):
        return ""

    def __repr__(self):
        
        return "%s %s %s" % (self.left, self.operator.text, self.right)


class ConstantString(Expression):
    def __init__(self, token):
        self.value = token
    
    def __repr__(self):
        return "Constant(\"%s\")" % self.value

    def evaluate_as_constant(self):
        """
        Evaluate an expression as a constant.
        """
        return self.value
    
    def to_text(self):
        return self.value.text


class ConstantInteger(Expression):
    def __init__(self, token):
        self.value = token

    def __repr__(self):
        return "Constant(%s)" % self.value

    def evaluate_as_constant(self):
        """
        Evaluate an expression as a constant.
        """
        return int(self.value.text)

    def to_text(self):
        return str(self.value)
        

class ConstantFloat(Expression):
    def __init__(self, token):
        self.value = token

    def __repr__(self):
        return "Constant(%s)" % self.value

    def evaluate_as_constant(self):
        """
        Evaluate an expression as a constant.
        """
        return float(self.value)

    def to_text(self):
        return str(self.value)


class Identifier(Expression):
    def __init__(self, token, scope=None):
        self.identifier = token
        # we need a scope to resolve its value latter
        self.scope = scope

    def __repr__(self):
        return self.identifier.text

    def evaluate_as_constant(self):
        """
        Evaluate an expression as a constant.
        """
        try:
            if self.scope:
                # we can try to resolve it
                resolved_as = self.scope.resolve_qname(self.identifier.text)
                if resolved_as and isinstance(resolved_as, VariableDeclaration):
                    
                    init_expression = resolved_as.get_initialisation()
                    if init_expression:
                        
                        return init_expression.evaluate_as_constant()
        except:
            pass # shit may happen
        
        return self.identifier.text

    def to_text(self):
        return self.identifier.text


class List(Expression):
    def __init__(self, elements):
        self.elements = elements

    def __repr__(self):
        return "List(%s)" % self.elements

    def evaluate_as_constant(self):
        """
        Evaluate an expression as a constant.
        """
        return [element.evaluate_as_constant() for element in self.elements]

    def to_text(self):
        return "{" + ','.join([element.to_text() for element in self.elements])  + "}"



def get_all_tokens(node):
    
    result = []
    
    for t in node.children:
        if isinstance(t, Node):
            result += get_all_tokens(t)
        else:
            result.append(t)
        
    return result


class Type:
    
    
    def __repr__(self):      
        return ''.join(token.text for token in get_all_tokens(self))

    
    

class SimpleType(Type, Node):
    """
    predefined type of class
    """
    def __init__(self, token):
        Node.__init__(self)
        self.children = [token]

    def get_type_name(self):
        """
        Get the name of the type.
        :rtype: str
        """
        return self.children[0].text
        

class ArrayType(Type, Node):
    """
    ... []
    """
    
    def get_type(self):
        """
        Access to type on which we do an array
        """
        return next(self.get_sub_nodes())
    

class GenericType(Type, Node):
    """
    @todo : maybe we need a SimpleType here as first child ?
    ... < ... >
    """
    pass


class GenericParameter(Node):
    pass
        

class FormalParameter(Node):
    """
    A formal parameter of a method.
    """
    
    def get_name(self):
        """
        Parameter name
        
        :rtype: str
        """
        for child in self.get_children():
            if child == 'final':
                continue
            
            if isinstance(child, Annotation):
                continue
            
            if isinstance(child, Type):
                continue
            
            return child.text

    def get_type(self):
        """
        Parameter type
        
        :rtype: Type
        """
        for child in self.get_children():

            if isinstance(child, Type):
            
                return child


def open_source_file(path):
    """
    Equivalent of python open(path) that autotdetects encoding. 
    
    :rtype: file 
    """
    from chardet.universaldetector import UniversalDetector
    
    detector = UniversalDetector()
    with open(path, 'rb') as f:
        count = 0
        for line in f:
            detector.feed(line)
            count += 1
            if detector.done or count > 100: 
                break
    detector.close()

    encoding = detector.result['encoding']
   
    result = open(path, 'r', encoding=encoding, errors='replace')
    return result
