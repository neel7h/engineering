class File:

    def __init__(self, path):
        self.path = path
        
    def get_path(self):
        return self.path
    
class Resolution:
    
    def __init__(self, callee, linkType):
        self.callee = callee
        self.linkType = linkType

class Node:
    
    def __init__(self, name = None, children = None, parent = None):
        self.name = name
        self.statements = []
        self.parent = parent
        if children:
            self.children = children
        else:
            self.children = []
        self.resolutions = []   # list of objects pointed by identifier 

    def is_resolved(self):
        return (len(self.resolutions) > 0)

    def add_resolution(self, callee, linkType):
        self.resolutions.append(Resolution(callee, linkType))
        
    def create_bookmark(self, file):
        return None
    
    def add_child(self, child):
        self.children.append(child)
        child.parent = self
        
    def add_statement(self, statement):
        self.statements.append(statement)
        self.children.append(statement)
        statement.parent = self
        
    def get_fullname(self):
        return self.name
    
    def get_parent(self):
        return self.parent

    def get_first_kb_parent(self):
                    
        return self.parent
    
    def get_name(self):
        return self.name
    
    def get_statements(self):
        return self.statements
    
    def get_children(self):
        return self.children
    
    def is_string(self):
        return False
    
    def is_function_call(self):
        return False
    
    def is_function_call_part(self):
        return False
    
    def is_list(self):
        return False
    
    def is_function(self):
        return False
    
    def is_identifier(self):
        return False
    
    def is_assignment(self):
        return False
    
    def is_define(self):
        return False
    
    def is_require(self):
        return False
    
    def is_object_value(self):
        return False

    def get_top_resolutions(self, topResolutions):
        pass

class AstString(Node):

    def __init__(self, text):
        Node.__init__(self, text)

    def is_string(self):
        return True

    def get_text(self):
        return self.name
        
class Identifier(Node):
    
    def __init__(self, name, prefix = None):
        Node.__init__(self, name)
        self.prefix = prefix
        
    def get_name(self):
#         if self.prefix:
#             return self.prefix + '.' + self.name
#         else:
        return self.name

    def get_fullname(self):
        if self.prefix:
            return self.prefix + '.' + self.name
        else:
            return self.name
           
    def get_prefix(self):
        return self.prefix
    
    def is_identifier(self):
        return True
            
    def get_top_resolutions(self, topResolutions):

        for resolution in self.resolutions:
            callee = resolution.callee
            if callee.parent and callee.parent.is_assignment():
                rightOperand = callee.parent.rightOperand
                if not rightOperand.get_top_resolutions(topResolutions):
                    topResolutions.append(rightOperand)
        
class FunctionCallPart(Node):
    
    def __init__(self, identName, params):
        Node.__init__(self, identName.get_name())
        self.identifier_call = identName
        if params:
            self.params = params
        else:
            self.params = []
        identName.parent = self
        for param in params:
            param.parent = self
            
    def get_identifier(self):
        return self.identifier_call
            
    def get_name(self):
        return self.name

    def get_fullname(self):
        if self.identifier_call.prefix:
            return self.identifier_call.prefix + '.' + self.identifier_call.name
        else:
            return self.identifier_call.name
    
    def get_parameters(self):
        return self.params

    def get_first_kb_parent(self):
                    
        return self
    
    def is_function_call_part(self):
        return True

    def get_children(self):
        return [ param for param in self.params ]

    def get_top_resolutions(self, topResolutions):

        self.identifier_call.get_top_resolutions(topResolutions)
        
class FunctionCall(Node):
    
    def __init__(self, identName = None, params = None, identName2 = None, params2 = None, identName3 = None, params3 = None):
        Node.__init__(self, identName.name)
        self.parts = []
        if identName:
            self.parts.append(FunctionCallPart(identName, params))
        if identName2:
            self.parts.append(FunctionCallPart(identName2, params2))
        if identName3:
            self.parts.append(FunctionCallPart(identName3, params3))
        for part in self.parts:
            part.parent = self
    
    def get_children(self):
        return [ part for part in self.parts ]
    
    def is_function_call(self):
        return True
    
    def get_function_call_parts(self):
        return self.parts

    def get_top_resolutions(self, topResolutions):

        self.functionCallParts[-1].get_top_resolutions(topResolutions)
        
class Assignment(Node):
    
    def __init__(self, leftOperand, rightOperand):
        Node.__init__(self, None, [leftOperand, rightOperand])
        self.leftOperand = leftOperand
        self.rightOperand = rightOperand
        leftOperand.parent = self
        rightOperand.parent = self
    
    def is_assignment(self):
        return True
    
    def get_left_operand(self):
        return self.leftOperand
    
    def get_right_operand(self):
        return self.rightOperand
    
class List(Node):
    
    def __init__(self, values = None):
        Node.__init__(self, None, values)
        if values:
            self.values = values
        else:
            self.values = []
        for value in self.values:
            value.parent = self
        
    def get_values(self):
        return self.values
    
    def is_list(self):
        return True
    
class Function(Node):
    
    def __init__(self, nameIdent, params = None, file = None ):
        Node.__init__(self, nameIdent.name)
        if params:
            self.params = params
            for param in params:
                self.add_child(param)
        else:
            self.params = []
        self.resolved_parameters = []
        for param in self.params:
            param.parent = self
        nameIdent.parent = self
        self.file = file
        self.prefix = nameIdent.prefix
    
    def get_parameters(self):
        return self.params
    
    def get_file(self):
        return self.file

    def is_function(self):
        return True
    
    def get_prefix(self):
        return self.prefix
    
    def get_fullname(self):
        if self.prefix:
            return self.prefix + '.' + self.name
        else:
            return self.name

class ObjectValue(Node):
    
    def __init__(self, items):
        Node.__init__(self, None)
        if items:
            self.items = items
            for _, value in items.items():
                self.add_child(value)
        else:
            self.items = {}
        for _, item in self.items.items():
            item.parent = self
    
    def is_object_value(self):
        return True
    
    def get_item(self, name):
        
        for n, item in self.items.items():
            if isinstance(n, Identifier):
                if n.get_name() == name:
                    return item
            elif n == name:
                return item
        return None

    def get_items(self):
        
        return [ item for _, item in self.items.items() ]

class AnyStatement(Node):
    
    def __init__(self, elements):
        Node.__init__(self, None)
        if elements:
            self.elements = elements
            for element in elements:
                self.add_child(element)
        else:
            self.elements = []
        for element in self.elements:
            element.parent = self

class Define(Node):
    """
    A define statement. define([...], function(..) {});
    """
    def __init__(self, parameters, function):
        
        Node.__init__(self, None)
        self.function = function
        self.parameters = parameters
        
    def get_function(self):
        
        return self.function
        
    def get_parameters(self):
        
        return self.parameters


class Require(Node):
    """
    A define statement. define([...], function(..) {});
    """
    def __init__(self, parameters, function):
        
        Node.__init__(self, None)
        self.function = function
        self.parameters = parameters
        
    def get_function(self):
        
        return self.function
        
    def get_parameters(self):
        
        return self.parameters
    
class HtmlTextWithPosition:

    def __init__(self, text = None, token = None):
        
        self.text = text
        self.token = token
        
    def get_text(self):
        return self.text
        
    def get_token(self):
        return self.token
    
    def __repr__(self):
        return self.text

class AttributeValueWithPosition:

    def __init__(self, attributeName, attributeToken, valueName, valueToken):
        
        self.attribute = HtmlTextWithPosition(attributeName, attributeToken)
        self.value = HtmlTextWithPosition(valueName, valueToken)
        
    def get_attribute(self):
        return self.attribute
        
    def get_value(self):
        return self.value
    
    def __repr__(self):
        return self.attribute.__repr__() + ', ' + self.value.__repr__()
