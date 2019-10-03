from cast.analysers import log
from python_parser import is_expression_statement, is_assignement, is_function, is_parenthesis, is_method,\
    is_constant, Array
import symbols
import traceback
import re


class EvaluationContext:
    """
    Contains data used during evaluation
    self.caller is the ast at the origin of evaluation
    self.callee is the ast pointed by self.caller after resolution
    self.values is a list containing the possible values of self.caller after evaluation
    """
    def __init__(self, caller, callee):
        self.caller = caller
        self.callee = callee
        self.values = []
        
    def get_values(self):
        return self.values

# count of method call walk during the current evaluation
total_method_walked = 0

# threshold
max_method_walked = 100
max_method_call_depth = 10


class Value:
    """
    Represent a calculated value, plus the statements that created the value  
    """
    def __init__(self, value, ast_node=None):
        
        self.value = value
        self.ast_nodes = []
        if ast_node:
            self.ast_nodes.append(ast_node)
    
    @staticmethod
    def concat(value1, value2, ast_node):
        """
        Concatenation of values.
        """
        result = Value(value1.value + value2.value)
        result.ast_nodes = value1.ast_nodes + [ast_node] + value2.ast_nodes
        return result
        
    @staticmethod
    def concat_join(value1, constant, value2, ast_node):
        """
        Concatenation of values with a constant in between (for os.path.join)
        """
        result = Value(value1.value + constant + value2.value)
        result.ast_nodes = value1.ast_nodes + [ast_node] + value2.ast_nodes
        return result
    
    def __eq__(self, value):
        
        return self.value == value.value
    
    def __ne__(self, value):
        
        return self.value != value.value
    
    
    def __repr__(self):
        
        return self.value


def evaluate(node, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    """
    Evaluates the value of current ast as a string. 
    
    :rtype: list of str
    """
    
    value_for_unknown = None
    if charForUnknown:
        value_for_unknown = Value(charForUnknown)
    
    values = evaluate_with_trace(node, evaluationContext, originalCaller, objectsPassed, value_for_unknown, method_call_depth)
    
    return [value.value for value in values]


def evaluate_with_trace(node, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    """
    Evaluates the value of current ast as a string. 
    
    :param charForUnknown: Value
    
    :rtype: list of Value
    
    Evaluation is done using:
       - assignments
       - additions
       - function calls
       - method parameters
       - if statements
    evaluationContext is internal
    originalCaller is the ast token from which the evaluation was started
    objectsPassed is internal and used to avoid infinite loops
    charForUnknown is a string which will replace the unresolved parts of the string
    method_call_depth is the current depth of method call stack 
    """
    
    if isinstance(charForUnknown, str):
        charForUnknown = Value(charForUnknown)
    
    # to check for cyclic call (and potentially depth search)
    if not objectsPassed:
        objectsPassed = []
        
        # new query : reset the count 
        global total_method_walked
        total_method_walked = 0
        
    if node in objectsPassed:
#         log.debug('Object already passed in evaluation, heap size = ' + str(len(objectsPassed)))
#         log.debug('total_method_walked ' + str(total_method_walked))
#         log.debug('method_call_depth ' + str(method_call_depth))
#         for line in traceback.format_stack():
#             log.debug(line.strip())
        
        return []
    objectsPassed.append(node)
    
    # This pattern of code is a fake override
    # we associate a function for each interesting ast node types
    
    methods = {'Constant':evaluate_string,
               'MethodCall':evaluate_method_call,
               'ExpressionStatement':evaluate_expression_statement,
               'Assignement':evaluate_assignement,
               'Identifier':evaluate_identifier,
               'AdditionExpression':evaluate_addition,
               'If':evaluate_if,
               'list':evaluate_statement_list,
               'IfTernaryExpression':evaluate_ternary,
               'DotAccess':evaluate_identifier, # for self.m
               'BinaryOperation':evaluate_binary_operation,
               'Parenthesis':evaluate_parenthesis,
               'StringInterpolation': evaluate_string_interpolation,
               'ArrayAccess': evaluate_array,
               }
    
    try:
        method = methods[type(node).__name__]
        return method(node, evaluationContext, originalCaller, objectsPassed, charForUnknown, method_call_depth)
    except:
#         print(traceback.format_exc())
        pass
    
    return []

# @todo : split evaluate_string evaluate_number 
def evaluate_string(constant, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    
    value = constant.get_value()
    
    if constant.is_constant_string():
        
        #@todo: extract variables and evaluate them
        if constant.is_fstring():
            
            # remove leading modificator
            value = re.sub(r'[bf]*([\"\'])', "\g<1>", value)
            
            # substitute variable by {}
            value = re.sub("{.*?}", "{}", value)
            
        if len(value) >= 2 and value[0] in ["'", '"']:
            if not value[0] == value[1]:
                return [Value(value[1:-1], constant)]  #   " text "
            else:
                return [Value(value[3:-3], constant)]  # """ text """
    else:
        return [Value(str(value), constant)]

def evaluate_statement_list(statements, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    """
    @type statements: list
    """
    for statement in statements:
        newObjectsPassed = list(objectsPassed)
        evaluate_with_trace(statement, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
    
    return evaluationContext.values


def evaluate_method_call(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    
    method = self.get_method()
    name = method.get_name()
    
    if name == 'join':
        # str.join
        try:
            expression = method.get_expression()
            
            if is_constant(expression):
                
                parameters = self.get_parameters()
                if len(parameters)==1 and isinstance(parameters[0], Array):
                    
                    array = parameters[0]
                    array_list = array.get_values()
                    value = expression.get_string_value()
                    
                    value_list= []
                    for element in array_list:
                        val = evaluate_with_trace(element, None, originalCaller, objectsPassed, charForUnknown, method_call_depth)                                                
                        if val:
                            value_list.append(val[0].value)  # @todo: support multiple values
                        
                    if value_list:
                        value = Value(value.join(value_list))
                        value.ast_nodes.append(self)
                        return [value]
        except:
            pass
        
        # if url = os.path.join(base_url, 'somestring', mode) for example, we append the 2 first parameters evaluations
        try:
            
            result_values = []
            
            for parameter in self.get_parameters():
                callees = parameter.get_resolutions()
                if evaluationContext and evaluationContext.callee in callees:
                    # the one calculated...
                    values = evaluationContext.values
                else:
                    newObjectsPassed = list(objectsPassed)
                    values = evaluate_with_trace(parameter, None, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
                    
                if values:
                    
                    if result_values:
                        new_values = []
                        
                        for value_left in result_values:
                            for value_right in values:
                                new_values.append(Value.concat_join(value_left, '/' , value_right, self))
                        
                        result_values = new_values
                    else:
                        result_values = values
                    
            return result_values
        except:
            return []
        

    elif name == 'Request':  # urllib.request.Request('http://www.voidspace.org.uk')
        url = self.get_argument(0, 'url')
        if url:
            newObjectsPassed = list(objectsPassed)
            return evaluate_with_trace(url, charForUnknown=charForUnknown, objectsPassed=newObjectsPassed, method_call_depth=method_call_depth)
        
    elif name == 'format':

        constant = method.children[0]
        
        try:
            if constant.is_constant_string():
                
                literal = constant.get_string_value()
                
                result_parameters = []
                parameters = self.get_parameters()
                for index, param in enumerate(parameters):
                    newObjectsPassed = list(objectsPassed)
                    
                    if not charForUnknown:
                        charForUnknown = "{}"
                    values = evaluate_with_trace(param, charForUnknown=charForUnknown, objectsPassed=newObjectsPassed, method_call_depth=method_call_depth)
                    for value in values:
                        val = value.value

                        # sanitize the string (TODO: it should be fixed in its root)                        
                        if len(val)>2 and charForUnknown == val.strip("'"):
                            val = charForUnknown
                        
                        literal = re.sub(r'\{\}', val, literal)
                        regexp =  r'\{'+str(index)+'\}'
                        literal = re.sub(regexp, val, literal)
                        temp = Value(literal)
                        temp.ast_nodes = value.ast_nodes
                        temp.ast_nodes.append(self)
                        temp.ast_nodes.append(constant)
                        result_parameters.append(temp)
                
                return result_parameters
        except:
            return []
            
    return []



# @done
def evaluate_expression_statement(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    
    return evaluate_with_trace(self.get_expression(), evaluationContext, originalCaller, objectsPassed, charForUnknown, method_call_depth)

# @done
def evaluate_assignement(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    """
    Evaluates an identifier when in an assignment
    """
    try:
        leftOperand = self.get_left_expression()
        if leftOperand != evaluationContext.callee:
            if not leftOperand.get_resolutions():
                return []
        if leftOperand != evaluationContext.callee:
            
            leftCallees = leftOperand.get_resolutions()
            if not evaluationContext.callee in leftCallees:
                return []
        
        
        vals = evaluate_with_trace(self.get_right_expression(), evaluationContext, originalCaller, objectsPassed, charForUnknown, method_call_depth)

        if vals:
            
            # special case of += 
            if self.get_operator() == '+=':
                
                values = []
                for value in evaluationContext.values:
                    for additional_value in vals:
                        values.append(Value.concat(value, additional_value, self))
                vals = values

            evaluationContext.values = vals
            return vals
        return []
    except:
        return []


    
    
def is_in_method(node):    
    """
    True when node is a parameter of a method
    """
    statement = node.get_enclosing_statement()
    
    return is_method(statement)
    
    

def is_in_assignement(node):
    """
    True when node is part of an assignement
    """
    statement = node.get_enclosing_statement()
    
    if not is_expression_statement(statement):
        return False
    
    return is_assignement(statement.get_expression())

def is_formal_parameter(node):
    """
    True when node is a parameter of a function/method
    """
    statement = node.get_enclosing_statement()
    
    if not is_function(statement):
        return False
    
    """
    @type statement:  python_parser.Function
    """
    
    is_formal_identifier = node in statement.get_parameters()
    is_formal_assignment = node in [param.get_left_expression() for param in statement.get_parameters() if is_assignement(param)]
    
    return is_formal_identifier or is_formal_assignment
        
def get_parameter_index(node):
    
    statement = node.get_enclosing_statement()
    
    if not is_function(statement):
        return False

    for index, param in enumerate(statement.get_parameters()):
        if is_assignement(param):
            param = param.get_left_expression()
        if param == node:
            return index

def get_function(node):
    """
    return the function of module containing the node
    """
    if is_function(node) or isinstance(node, symbols.Module):
        return node
    
    if node.parent:
        return get_function(node.parent)

def contains(node1, node2):
    """
    True if node2 is a sub node of node1
    """
    if node2 == node1:
        return True
    
    for sub_node in node1.get_sub_nodes():
        
        if contains(sub_node, node2):
            return True
    
    return False
    



def evaluate_identifier(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    """
    Evaluates the possible values for the identifier
    """
    global total_method_walked
    global max_method_walked
    global max_method_call_depth
    
    try:
        if not originalCaller:
            originalCaller = self
            
        # If the identifier is not part of an assignment or if it has not be resolved to a definition,
        # it can not be evaluated.
        
        if not self.get_resolutions() and not is_in_assignement(self):
            if charForUnknown:
                return [ charForUnknown ]
            else:
                return None
        
        if evaluationContext:
            caller = evaluationContext.caller
        else:
            caller = self

        # if context callee is not the same as self.resolutions.callee, we reevaluate current identifier from scratch.
        # This is the case for example with "a = b + c" when we want to evaluate a, which require the evaluation of b and c
        # which have not the same callee as a.
        
        callees = self.get_resolutions()
        if evaluationContext and self.get_resolutions() and not evaluationContext.callee in callees:
            evaluationContext = None
            caller = self
            
        returnValues = []
        
        if not evaluationContext:
            # determine the callee
            callees = caller.get_resolutions()
            if not callees:
                callees = [ caller ]
            
            for callee in callees:

                # if callee is a member take the ast instead
                try:
                    callee = callee.get_ast()
                except:
                    pass

                # If callee is a function parameter, we get all the calls to the function to try to evaluate
                # the identifier
                vals = []
                if is_formal_parameter(callee):  # postional/keyword parameter of a method
                
                # @todo: refactor to avoid code repetition
                
                    # Search an assigned value within the function until we reach the current statement where
                    # the identifier of interest is enclosed. At this point, if we have found a value we stop searching.
                    # Example: 
                    #
                    #   def function(a):
                    #        a = 1
                    #        toto(a)
                    #
                    #   val = 3 
                    #   function(val)
                    # 
                    # When finding "a=1", then we stop searching for "a" in function calls.
                    #    
                    callerContainer = caller.get_enclosing_statement().get_container_block()
                    currentStatement = self.get_enclosing_statement()
                    evaluationContext = EvaluationContext(caller, callee)
                    
                    statement_value = False 

                    for statement in callerContainer.get_statements():
                        newObjectsPassed = list(objectsPassed)
                        val = evaluate_with_trace(statement, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
                        if val:
                            statement_value = True
                        
                        if statement == currentStatement:
                            break
                    
                    if (evaluationContext.values):
                        
                        for val in evaluationContext.values:
                                returnValues.append(val)
                    
                    if statement_value:
                        continue
                    
                    if is_assignement(callee.parent):
                        newObjectsPassed = list(objectsPassed)
                        evaluate_with_trace(callee.parent, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
                    
                    if (evaluationContext.values):
                        statement_value = True
                        for val in evaluationContext.values:
                                returnValues.append(val) 
                    
                    paramNumber = get_parameter_index(callee)
                    
                    # if callee is a parameter of a method (not a function) then param are different
                    # shift parameter order
                    if is_in_method(callee):
                        paramNumber = paramNumber - 1
                    
                    all_callers = callee.get_enclosing_statement().get_calling_asts()
                    
                    for method_call in all_callers:
                        """
                        @type method_call: python_parser.MethodCall
                        """
                        
                        # apply threshold
                        if total_method_walked > max_method_walked:
                            break
                        
                        if method_call_depth > max_method_call_depth:
                            break
                        
                        
                        try:
                            if len(method_call.get_parameters()) > paramNumber:
                                paramValue = method_call.get_parameters()[paramNumber]
                                newObjectsPassed = list(objectsPassed)
                                paramVals = evaluate_with_trace(paramValue, None, originalCaller, newObjectsPassed, charForUnknown, method_call_depth + 1)
                                
                                # increase...
                                total_method_walked += 1
                                
                                if paramVals:
                                    returnValues = []  # overrides values obtained by default parameters
                                    for paramVal in paramVals:
                                        if not paramVal in vals:
                                            vals.append(paramVal)
                        except:
                            pass
                    if vals:
                        for val in vals:
                            if not val in returnValues:
                                returnValues.append(val)
                    continue

                if not callee.parent or not is_in_assignement(callee):
                    continue
                evaluationContext = EvaluationContext(caller, callee)
                
                callerContainer = None
                
                
                calleeAssignment = callee.get_enclosing_statement().get_expression()
                # @todo : what about that ?
#                 if calleeAssignment.is_dereferencement_expression():
#                     calleeAssignment = calleeAssignment.parent
                
                
                callerContainer = caller.get_enclosing_statement().get_container_block() # should return function instead of block...
                currentStatement = self.get_enclosing_statement()
                
                if caller == callee:
                    newObjectsPassed = list(objectsPassed)
                    vals = evaluate_with_trace(currentStatement, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
                    if evaluationContext:
                        # check
                        if (evaluationContext.values):
                            for val in evaluationContext.values:
                                if not val in returnValues:
                                    returnValues.append(val)
                        continue
                    else:
                        if vals:
                            for val in vals:
                                if not val in returnValues:
                                    returnValues.append(val)
                        continue
                    
                # Ex of a block containing following statements: 
                #   statement1 
                #   var a = 1; 
                #   other statements; 
                #   f(a); 
                #   other statements; 
                # If we want to evaluate a on line 4, we get the calleeContainer which is all the block, 
                # we go to each statement from the first one, we do nothing until a declaration (line 2),
                # and we evaluate a on each statement after declaration and until line 4.
                # we do not enter in function declarations.
                
                # Other example: 
                #   var a = 1; 
                #   other statements; 
                #   function f() { 
                #      g(a); 
                #   } 
                # If we want to evaluate a on line 4, we get the calleeContainer which is all the JSContent block, 
                # we get the callerContainer which is all the function block.
                # As both containers are different, we evaluate the declaration of a (line 1), then we go to each statement of the function,
                # and we evaluate a on each statement until line 4.
                
                calleeFunctionContainer = get_function(calleeAssignment)
                callerFunctionContainer = get_function(caller)

                if calleeFunctionContainer != callerFunctionContainer:
                    # we evaluate declaration
                    newObjectsPassed = list(objectsPassed)
                    try:
                        vals = evaluate_with_trace(calleeAssignment.get_right_expression(), None, None, newObjectsPassed, charForUnknown, method_call_depth)
                    except:
                        # @todo : not sure of translation...
                        vals = evaluate_with_trace(calleeAssignment.get_left_expression(), None, None, newObjectsPassed, charForUnknown, method_call_depth)
                    evaluationContext.values = vals
                    afterDeclaration = True
                else:
                    afterDeclaration = False
                    
                for statement in callerContainer.get_statements():
                    if not afterDeclaration and statement != calleeAssignment and not contains(statement, calleeAssignment):
                        continue
                    else:
                        newObjectsPassed = list(objectsPassed)
                        evaluate_with_trace(statement, evaluationContext, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
                        afterDeclaration = True
                            
                        if statement == currentStatement:
                            break
                if (evaluationContext.values):
                    for val in evaluationContext.values:
                        if val not in returnValues:
                            returnValues.append(val)
                continue
            
            if charForUnknown and not returnValues:
                returnValues.append(charForUnknown)
            return returnValues
        
        else:
            
            statement = self.get_statement_container()
            newObjectsPassed = list(objectsPassed)
            return evaluate_with_trace(statement, evaluationContext, None, newObjectsPassed, charForUnknown, method_call_depth)
    except:
        if charForUnknown:
            return [charForUnknown]
        return [] 

def evaluate_ternary(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    """
    Evaluates an identifier defined in the context parameter when we go through an If ternary expression
    Ex: a = 'a'
        f(a + 'b' if ... else a + 'c');
    On last line, expression can be evaluated to 'ab' or 'ac'
    """
    try:
        
        newObjectsPassed = list(objectsPassed)
        values = evaluate_with_trace(self.get_first_value(), evaluationContext, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)

        newObjectsPassed = list(objectsPassed)
        values += evaluate_with_trace(self.get_second_value(), evaluationContext, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
            
        return values
    except:
        return []

# @done
def evaluate_addition(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    """
    Evaluates an identifier defined in a context parameter when in addition
    """
    try:

        leftEvaluationValues = []
        rightEvaluationValues = []
        if self.get_left_expression():
            if evaluationContext:
                # if left operand has the same definition of callee in context
                
                leftCallees = self.get_left_expression().get_resolutions()
                if self.get_left_expression().get_resolutions() and evaluationContext.callee in leftCallees:
                    
                    leftEvaluationValues = evaluationContext.values
                # if left operand has not the same definition of callee in context
                else:
                    newObjectsPassed = list(objectsPassed)
                    leftEvaluationValues = evaluate_with_trace(self.get_left_expression(), None, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
            else:
                newObjectsPassed = list(objectsPassed)
                leftEvaluationValues = evaluate_with_trace(self.get_left_expression(), None, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
        if self.get_right_expression():
            # if right operand has the same definition of callee in context
            rightCallees = self.get_right_expression().get_resolutions()
            if evaluationContext and self.get_right_expression().get_resolutions() and evaluationContext.callee in rightCallees:
                rightEvaluationValues = evaluationContext.values
            else:
                newObjectsPassed = list(objectsPassed)
                rightEvaluationValues = evaluate_with_trace(self.get_right_expression(), evaluationContext, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
                
        # we compute the addition and put the result in values
        values = []
        
        
        if leftEvaluationValues:
            if rightEvaluationValues:
                for i in range(len(leftEvaluationValues)):
                    for j in range(len(rightEvaluationValues)):
                        values.append(Value.concat(leftEvaluationValues[i], rightEvaluationValues[j], self))
            else:
                values = leftEvaluationValues
        else:
            if rightEvaluationValues:
                values = rightEvaluationValues
            
        return values
    except:
        return []

def evaluate_binary_operation(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    
    if self.get_operator() != '%':
        return []
    
    # case for %
    left_values = evaluate_with_trace(self.get_left_expression(), evaluationContext, originalCaller, objectsPassed, charForUnknown, method_call_depth)
    
    right_expression = self.get_right_expression()
    right_values = []
    
    if is_parenthesis(right_expression):
        
        for expression in right_expression.get_sub_nodes():
            
            right_values.append(evaluate_with_trace(expression, evaluationContext, originalCaller, objectsPassed, charForUnknown, method_call_depth))
            
    else:
        
        right_values.append(evaluate_with_trace(right_expression, evaluationContext, originalCaller, objectsPassed, charForUnknown, method_call_depth))

    # replace all %s ...
    values = []
    
    for left_value in left_values:
        left_value.ast_nodes.append(self)
        local_values = [left_value]
        
        for right_value in right_values:
            after_replace = []
            for value in local_values:
                
                for _unit_right_value in right_value:
                    
                    # only replace first occurence :)
                    replaced_text = value.value.replace('%s', _unit_right_value.value, 1)
                    
                    replaced_value = Value(replaced_text)
                    replaced_value.ast_nodes = value.ast_nodes + _unit_right_value.ast_nodes
                    after_replace.append(replaced_value)
                    
            if after_replace:
                local_values = after_replace
        
        values.extend(local_values)
    
    return values
    
    
def evaluate_string_interpolation(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    return evaluate_binary_operation(self, evaluationContext, originalCaller, objectsPassed, charForUnknown, method_call_depth)
    
def evaluate_if(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    """
    Evaluates an identifier defined in the context parameter when we go through an If statement
    Ex: var a = 'a';
        if ()
            a += 'b';
        else
            a += 'c';
        f(a);
    On last line, a can be evaluated to 'ab' or 'ac'
    """
    try:
        # we save evaluationContext values in initial value ('a' in our example):
        initialValues = evaluationContext.values
        vals = []
        # do we have an else
        has_else = False 
        
        for block in self.get_cases():
            newObjectsPassed = list(objectsPassed)
            evaluationContext.values = initialValues
            vals += evaluate_with_trace(block.get_statements(), evaluationContext, originalCaller, newObjectsPassed, charForUnknown, method_call_depth)
            if block.is_else():
                has_else = True 
        
        if not has_else:
            vals += initialValues
            
        evaluationContext.values = vals
        return vals
    except:
        return []

def evaluate_parenthesis(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    
    subnodes = list(self.get_sub_nodes())
    
    try:
        signature = self.children[-2]
        if signature == ',':
            return []
    except:
        pass
    
    if len(subnodes) == 1:
        subnode = subnodes[0]
        vals = evaluate_with_trace(subnode)
    
    return vals

def evaluate_array(self, evaluationContext = None, originalCaller = None, objectsPassed = None, charForUnknown = None, method_call_depth = 0):
    
    if charForUnknown:
        return [charForUnknown]

    return []