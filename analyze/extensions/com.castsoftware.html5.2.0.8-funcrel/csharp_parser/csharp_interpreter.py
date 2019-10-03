from csharp_parser.symbols import CSharpClass, CSharpMethod, StatementsBlock, AnyStatement, AnyExpression, ParenthesedList, EqualityExpression, AssignmentExpression, NewAnonymousExpression

class Context:
    def __init__(self, obj, parent):
        self.currentObject = obj
        self.parent = parent
    def add_method(self, meth):
        pass
    def add_attribute(self, attr, ast):
        pass
    def add_statement(self, statement):
        pass
    def add_element(self, element):
        pass
    def is_class(self, className):
        if self.parent:
            return self.parent.is_class(className)
        return False
    
class ClassContext(Context):
    def __init__(self, cl, parent):
        Context.__init__(self, cl, parent)
        self.currentObject = cl
    def add_attribute(self, attr, ast):
        self.currentObject.add_attribute(attr, ast)
    def add_method(self, meth):
        self.currentObject.add_method(meth)
    def add_statement(self, statement):
        self.currentObject.add_statement(statement)
    def is_class(self, className):
        if self.currentObject.get_name() == className:
            return True
        return False
    
class MethodContext(Context):
    def __init__(self, meth, parent):
        Context.__init__(self, meth, parent)
        self.currentObject = meth
    def add_attribute(self, attr, ast):
        self.currentObject.add_attribute(attr, ast)
    def add_statement(self, statement):
        self.currentObject.add_statement(statement)
    
class BlockContext(Context):
    def __init__(self, block, parent):
        Context.__init__(self, block, parent)
    def add_statement(self, statement):
        self.currentObject.add_statement(statement)
    
class ParenthesedListContext(Context):
    def __init__(self, lst, parent):
        Context.__init__(self, lst, parent)
    def add_element(self, element):
        self.currentObject.add_element(element)
    
class ExpressionContext(Context):
    def __init__(self, lst, parent):
        Context.__init__(self, lst, parent)
    def add_element(self, element):
        self.currentObject.add_element(element)
    
class BinaryExpressionContext(Context):
    def __init__(self, lst, parent):
        Context.__init__(self, lst, parent)
    def set_left_operand(self, element):
        self.currentObject.set_left_operand(element)
    def set_right_operand(self, element):
        self.currentObject.set_right_operand(element)
    
class CSharpInterpreter:
    
    def __init__(self, file = None):
        self.file = file
        self.contexts = []
        self.currentContext = None

    def push_context(self, context):
        self.contexts.append(context)
        self.currentContext = context

    def pop_context(self):
        if self.contexts:
            self.contexts.pop()
        if self.contexts:
            self.currentContext = self.contexts[-1]
        else:
            self.currentContext = None
    
    def start_class(self, name, ast):
        cl = CSharpClass(name, self.currentContext.currentObject if self.currentContext else None, ast, self.file)
        self.push_context(ClassContext(cl, self.currentContext))
        return cl
      
    def end_class(self):
        self.pop_context()
    
    def start_method(self, name, returnType, accessibility, ast):
        isConstructor = self.currentContext.is_class(name)
        meth = CSharpMethod(name, returnType, accessibility, self.currentContext.currentObject, ast, self.file, isConstructor)
        self.currentContext.add_method(meth)
        self.push_context(MethodContext(meth, self.currentContext))
        return meth
      
    def add_attribute(self, attribute, ast):
        self.currentContext.add_attribute(attribute, ast)
        
    def end_method(self):
        self.pop_context()
    
    def start_block(self, ast):
        block = StatementsBlock(self.currentContext.currentObject if self.currentContext else None, ast)
        self.push_context(BlockContext(block, self.currentContext))
        return block
        
    def end_block(self):
        self.pop_context()
    
    def start_parenthesed_list(self, ast):
        lst = ParenthesedList(self.currentContext.currentObject if self.currentContext else None, ast)
        self.push_context(ParenthesedListContext(lst, self.currentContext))
        return lst
        
    def end_parenthesed_list(self):
        self.pop_context()
    
    def start_expression(self, ast):
        expr = AnyExpression(self.currentContext.currentObject if self.currentContext else None, ast)
        self.push_context(ExpressionContext(expr, self.currentContext))
        return expr
        
    def end_expression(self):
        self.pop_context()
        
    def add_element(self, element):
        if self.currentContext:
            self.currentContext.add_element(element)
        
    def add_any_statement(self, tokens):
        statement = AnyStatement(self.currentContext.currentObject if self.currentContext else None, tokens)
        if self.currentContext:
            self.currentContext.add_statement(statement)
        
    def add_any_expression(self, tokens):
        expr = AnyExpression(self.currentContext.currentObject if self.currentContext else None, tokens)
#         if self.currentContext:
#             self.currentContext.add_statement(statement)
    
    def set_left_operand(self, ast):
        self.currentContext.set_left_operand(ast)
    
    def set_right_operand(self, ast):
        self.currentContext.set_right_operand(ast)
        
    def start_equality_expression(self, ast):
        expr = EqualityExpression(self.currentContext.currentObject if self.currentContext else None, ast)
        self.push_context(BinaryExpressionContext(expr, self.currentContext))
        return expr
    
    def end_equality_expression(self):
        self.pop_context()
    
    def start_assignment_expression(self, ast):
        expr = AssignmentExpression(self.currentContext.currentObject if self.currentContext else None, ast)
        self.push_context(BinaryExpressionContext(expr, self.currentContext))
        return expr
    
    def end_assignment_expression(self):
        self.pop_context()
    
    def start_new_anonymous_expression(self, ast):
        expr = NewAnonymousExpression(self.currentContext.currentObject if self.currentContext else None, ast)
        self.push_context(ParenthesedListContext(expr, self.currentContext))
        return expr
    
    def end_new_anonymous_expression(self):
        self.pop_context()
