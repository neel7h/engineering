'''
Created on 26 nov. 2014

@author: iboillon
'''
import os
import cast.analysers.ua
from cast.analysers import Object, File, Bookmark, create_link
from collections import OrderedDict
from pygments.token import is_token_subtype, Name
from javascript_parser.light_parser import Token

class Position:
    def __init__(self, begin_line, begin_col, end_line, end_col):
        self.begin_line = begin_line
        self.begin_col = begin_col
        self.end_line = end_line
        self.end_col = end_col

class CSharpObject:
    
    def __init__(self, name, file):
        self.name = name
        self.kbObject = None
        self.file = file
        
    def set_kb_object(self, kbObject):
        self.kbObject = kbObject
        
    def get_kb_object(self, recursiveInParents = False):
        return self.kbObject
        
    def get_name(self):
        return self.name
    
    def get_file(self):
        return self.file

class Ast:
    
    def __init__(self, parent, ast):
        self.ast = ast
        self.parent = parent

    def get_controller_name(self):
        if self.parent:
            return self.parent.get_controller_name()
        return ''

    def is_any_statement(self):
        return False
    
    def is_parenthesed_list(self):
        return False

    def is_new_anonymous(self):
        return False
    
    def get_children(self):
        return []

    def find_method_calls(self, shortName):
        res = []
        for child in self.get_children():
            l = child.find_method_calls(shortName)
            if l:
                res.extend(l)
        return res
    
    def create_bookmark(self, file):
        if self.ast is list:
            return Bookmark(file, self.ast[0].get_begin_line(), self.ast[0].get_begin_column(), self.ast[-1].get_end_line(), self.ast[-1].get_end_line())
        else:
            return Bookmark(file, self.ast.get_begin_line(), self.ast.get_begin_column(), self.ast.get_end_line(), self.ast.get_end_line())
    
class StatementsList(Ast):        
    
    def __init__(self, parent, ast):
        Ast.__init__(self, parent, ast)
        self.statements = []
    
    def get_children(self):
        return self.statements
    
    def add_statement(self, statement):
        self.statements.append(statement)
        
    def get_statements(self):
        return self.statements

class StatementsBlock(StatementsList):        
    
    def __init__(self, parent, ast):
        StatementsList.__init__(self, parent, ast)
        self.ast = ast

class ParenthesedList(Ast):        
    
    def __init__(self, parent, ast):
        Ast.__init__(self, parent, ast)
        self.elements = []
    
    def is_parenthesed_list(self):
        return True
    
    def get_children(self):
        return self.elements
        
    def get_elements(self):
        return self.elements
        
    def add_element(self, element):
        self.elements.append(element)

class CSharpClass(StatementsList, CSharpObject):
    
    def __init__(self, name, parent, ast, file):
        StatementsList.__init__(self, parent, ast)
        CSharpObject.__init__(self, name, file)
        self.inheritedTypes = []
        self.inheritedClasses = []
        self.childrenClasses = []
        self.methods = []
        self.inheritedMethods = []
        self.attributes = []
        self.routes = []
    
    def get_controller_name(self):
        ctrlName = self.get_name()
        if ctrlName.endswith('Controller'):
            ctrlName = ctrlName[:-10]
        return ctrlName
    
    def add_attribute(self, text, ast):
        txt = text.get_text()
        self.attributes.append(txt)
        if 'Route(' in txt:
            index1 = txt.find('Route(')
            index1 = txt.find('"', index1)
            if index1 > 0:
                index2 = txt.find('"', index1 + 1)
                if index2 > 0:
                    route = txt[index1 + 1: index2]
                    if route:
                        if not route.endswith('/'):
                            route += '/'
                        if route.startswith('/'):
                            route = route[1:]
                        while '{id' in route:
                            index10 = route.find('{id')
                            index11 = route.find('}', index10)
                            route = route.replace(route[index10:index11+1], '{}')
                        self.routes.append(route)
        
    def get_attributes(self):
        attrs = []
        for attr in self.attributes:
            attrs.append(attr.text.strip())
        return attrs
    
    def get_routes(self):
        if self.routes:
            return self.routes
        for inheritedClasses in self.inheritedClasses:
            try:
                if inheritedClasses.routes:
                    return inheritedClasses.routes
            except:
                pass
        return []
    
    def resolve_inheritance(self, classesByKbObject):
        
        for inheritedType in self.inheritedTypes:
            if not inheritedType:
                continue
            if inheritedType.get_fullname() in classesByKbObject:
                cl = classesByKbObject[inheritedType.get_fullname()]
                if cl.get_name() in self.inheritedClasses:
                    self.inheritedClasses.remove(cl.get_name()) 
                self.inheritedClasses.append(cl)
                cl.childrenClasses.append(self)
                if cl.methods:
                    self.inheritedMethods.extend(cl.methods)
    
    def add_inherited_type(self, typ):
        self.inheritedTypes.append(typ)
        
    def add_inheritance(self, name):
        self.inheritedClasses.append(name)
        
    def add_child_class(self, cl):
        self.childrenClasses.append(cl)
        
    def get_children_classes(self):
        return self.childrenClasses
        
    def get_inheritances(self):
        return self.inheritedClasses
    
    def add_method(self, method):
        self.methods.append(method)
        self.add_statement(method)
        
    def get_methods(self, name = None):
        if name:
            methods = []
            for method in self.methods:
                if method.name == name:
                    methods.append(method)
            return methods
        else:
            return self.methods
        
    def get_inherited_methods(self):
        return self.inheritedMethods
        
    def get_method(self, name):
        for method in self.methods:
            if method.name == name:
                return method
        return None
    
    def __repr__(self):
        s = str('class ' + self.name + '(' + str(self.kbObject) + ')')
        for meth in self.methods:
            s += ('\n' + meth.__repr__())
        return s

class Route:
    def __init__(self, route, _type = 'ANY'):
        self.route = route
        self.type = _type
                
class CSharpMethod(StatementsList, CSharpObject):
    
    def __init__(self, name, returnType, accessibility, parent, ast, file, isConstructor = False):
        StatementsList.__init__(self, parent, ast)
        CSharpObject.__init__(self, name, file)
        self.attributes = []
        self.returnType = returnType
        self.accessibility = accessibility  # private/public/protected
        self.isConstructor = isConstructor
        self.routes = []    # for attributes of type [Route("Home/Index")], an element of the list will be "Home/Index"
        
    def get_routes(self):
        return self.routes
    
    def add_attribute(self, text, ast):
        txt = text.get_text()
        self.attributes.append(txt)
        
        if 'Route(' in txt:
            index1 = txt.find('Route(')
            index1 = txt.find('"', index1)
            if index1 > 0:
                index2 = txt.find('"', index1 + 1)
                if index2 > 0:
                    route = txt[index1 + 1: index2]
                    if route:
                        if not route.endswith('/'):
                            route += '/'
                        if route.startswith('/'):
                            route = route[1:]
                        while '{id' in route:
                            index10 = route.find('{id')
                            index11 = route.find('}', index10)
                            route = route.replace(route[index10:index11+1], '{}')
                        route = route.replace('[controller]', self.get_controller_name())
                        route = route.replace('[action]', self.get_name())
                        self.routes.append(Route(route))
        elif 'HttpGet(' in txt or 'HttpPost(' in txt or 'HttpPut(' in txt or 'HttpDelete(' in txt:
            index1 = txt.find('Http')
            indexType = index1 + 4
            indexTypeEnd = txt.find('(', indexType)
            index1 = txt.find('"', index1)
            if index1 > 0:
                index2 = txt.find('"', index1 + 1)
                if index2 > 0:
                    route = txt[index1 + 1: index2]
                    if route:
                        if not route.endswith('/'):
                            route += '/'
                        if route.startswith('/'):
                            route = route[1:]
                        while '{id' in route:
                            index10 = route.find('{id')
                            index11 = route.find('}', index10)
                            route = route.replace(route[index10:index11+1], '{}')
                        route = route.replace('[controller]', self.get_controller_name())
                        route = route.replace('[action]', self.get_name())
                        self.routes.append(Route(route, txt[indexType:indexTypeEnd].strip().upper()))
        elif 'HttpGet' in txt or 'HttpPost' in txt or 'HttpPut' in txt or 'HttpDelete' in txt:
            index1 = txt.find('Http')
            indexType = index1 + 4
            routeType = txt[indexType:indexType+3]
            if routeType == 'Pos':
                routeType = 'POST'
            if routeType == 'Del':
                routeType = 'DELETE'
            self.routes.append(Route('', routeType.upper()))
        
    def get_attributes(self):
        attrs = []
        for attr in self.attributes:
            attrs.append(attr.strip())
        return attrs
    
    def get_return_type(self):
        return self.returnType
    
    def get_accessibility(self):
        return self.accessibility
    
    def attribute_contains(self, text):
        for attribute in self.attributes:
            if text in attribute:
                return True
        return False
    
    def get_attribute(self, text):
        for attribute in self.attributes:
            if text in attribute:
                return attribute.strip()
        return None
    
    def __repr__(self):
        s = str('   method ' + self.name + '(' + str(self.kbObject) + ')')
        if self.attributes:
            s += ' ['
        for attr in self.attributes:
            s += ( attr + ' ' )
        if self.attributes:
            s += ']'
        return s
       
class AnyStatement(Ast):
    
    def __init__(self, parent, tokens):
        Ast.__init__(self, parent, tokens)
        self.elements = tokens
    
    def get_children(self):
        return self.elements

    def is_any_statement(self):
        return True
    
    def get_elements(self):
        return self.elements
    
    def startswith_method_call(self):
        for element in self.elements:
            if isinstance(element, Token) and ((is_token_subtype(element.type, Name) or element.text == '.')):
                continue
            elif isinstance(element, ParenthesedList):
                return True
            else:
                return False
        return False
    
    def get_method_call_name(self):
        name = ''
        for element in self.elements:
            if isinstance(element, Token) and ((is_token_subtype(element.type, Name) or element.text == '.')):
                name += element.text
            else:
                break
        return name

    def find_method_calls(self, shortName):
        if self.startswith_method_call() and self.get_method_call_name().endswith(shortName):
            return [ self ]
        return []
    
    def __repr__(self):
        return str(self.elements)

class BinaryExpression(Ast):        
    
    def __init__(self, parent, tokens):
        Ast.__init__(self, parent, tokens)
        self.leftOperand = None
        self.rightOperand = None
        
    def get_right_operand(self):
        return self.rightOperand
        
    def get_left_operand(self):
        return self.leftOperand
        
    def set_right_operand(self, ast):
        self.rightOperand = ast
        
    def set_left_operand(self, ast):
        self.leftOperand = ast

# a = b
class EqualityExpression(BinaryExpression):        
    
    def __init__(self, parent, tokens):
        BinaryExpression.__init__(self, parent, tokens)
        
    def get_children(self):
        return [ self.leftOperand, self.rightOperand ]
# a : b
class AssignmentExpression(BinaryExpression):        
    
    def __init__(self, parent, tokens):
        BinaryExpression.__init__(self, parent, tokens)
        
    def get_children(self):
        return [ self.leftOperand, self.rightOperand ]

# new {Name = cust.Name, Address = cust.PrimaryAddress}
class NewAnonymousExpression(Ast):        
    
    def __init__(self, parent, tokens):
        Ast.__init__(self, parent, tokens)
        self.elements = []   # list of EqualityExpression
        
    def is_new_anonymous(self):
        return True
    
    def get_elements(self):
        return self.elements
    
    def add_element(self, element):
        self.elements.append(element)
    
    def get_children(self):
        return self.elements

class AnyExpression(Ast):
    
    def __init__(self, parent, tokens):
        Ast.__init__(self, parent, tokens)
        self.elements = []
    
    def get_children(self):
        return self.elements

    def get_elements(self):
        return self.elements

    def add_element(self, element):
        self.elements.append(element)
    
    def __repr__(self):
        return str(self.elements)
