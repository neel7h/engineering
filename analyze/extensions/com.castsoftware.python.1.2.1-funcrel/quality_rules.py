"""
Define, register, and analyse generic Python quality rules
"""
from light_parser import Walker
from python_parser import Return, Yield, YieldFrom, Node, FunctionBlock, ClassBlock,\
    is_identifier, is_dot_access, is_method_call, is_class, IndentBlock, is_parenthesis,\
    is_expression_list, is_function, WithBlock, is_assignement,\
    FinallyBlock, ForBlock, is_interpolation, is_addition, is_constant,\
    is_binary_operation, BinaryOperation, is_method, Parenthesis, MethodCall, \
    UnaryNot, IfTernaryExpression, Identifier, Global

from symbols import Class
from database_frameworks import SelectQueryInterpreter

from cast.analysers import log
import re
import traceback

interpreters = []

def analyse(module):
    """
    Analyse an AST 
    """
    walker = Walker(interpreters, module)
    walker.walk(module.get_ast())

    for interpreter in walker.interpreters:
        interpreter.on_end()
            

def register_class(target_class):
    interpreters.append(target_class)

class AutoRegister(type):
    """Metaclass allowing automatic registration
    of classes that inherit from QualityRule.
    
    @todo: add parameter to easily switch off quality rules. Example:
    
        >>> class Q1(QualityRule):               # active by default
        >>>     pass
        
        >>> class Q2(QualityRule, active=False)  # switched off
        >>>     pass
    """

    def __new__(meta, name, bases, class_dict):
        cls = type.__new__(meta, name, bases, class_dict)
        if bases[0].__name__ == 'QualityRule':
            register_class(cls)
        return cls


class QualityRule(object, metaclass=AutoRegister):
    def __init__(self, module):
        self.__module = module
        self.__symbol_stack = [module]

    def push_symbol(self, symbol):

        return self.__symbol_stack.append(symbol)

    def pop_symbol(self):

        self.__symbol_stack.pop()

    def get_current_symbol(self):
        return self.__symbol_stack[-1]

    def get_current_class(self):

        symbol = self.get_current_symbol()

        while symbol and not isinstance(symbol, Class):
            symbol = symbol.get_parent_symbol()

        return symbol

    def get_module(self):
        return self.__module

    def start_ClassBlock(self, _ast_class):
        self.start_Class(_ast_class)

    def start_ClassOneLine(self, _ast_class):
        self.start_Class(_ast_class)

    def start_Class(self, _ast_class):
        """
        Resolve class inheritances
        """
        _class = self.get_current_symbol().get_class(_ast_class.get_name(), _ast_class.get_begin_line())
        if not _class:

            log.warning("no class found for %s under %s" % (str(_ast_class.get_name()), str(self.get_current_symbol())))

        self.push_symbol(_class)

    def end_ClassOneLine(self, _ast_class):
        self.end_Class(_ast_class)

    def end_ClassBlock(self, _ast_class):
        self.end_Class(_ast_class)

    def end_Class(self, _ast_class):
        self.pop_symbol()

    def start_FunctionBlock(self, ast_function):
        self.start_Function(ast_function)

    def start_FunctionOneLine(self, ast_function):
        self.start_Function(ast_function)

    def start_Function(self, ast_function):
        name = ast_function.get_name()
        function = self.get_current_symbol().get_function(name, ast_function.get_begin_line())
        self.push_symbol(function)

    def end_FunctionBlock(self, ast_function):
        self.end_Function(ast_function)

    def end_FunctionOneLine(self, ast_function):
        self.end_Function(ast_function)

    def end_Function(self, ast_function):
        self.pop_symbol()

    def on_end(self):
        pass

class Md5Hashes(QualityRule):
    """
    md5 hashes can be used in different contexts:
        - checking data integrity
        - indexing
        - encripting data
        
    Only last case should raise a violation, for security reasons.
    Since it is hard (not to say impossible) to interpret the
    use case at hand, we will rely on semantics and simple 
    heuristics to guess the intention.
    
    Limitations
    -----------
    Only few cases of calling md5 and sha1 is considered, without
    resolution of instances. (TODO)
    """

    def start_MethodCall(self, method_call):
        """
        search for hashlib.md5(), hashlib.new() constructor patterns (Python > 2.5)
        and md5.new(), md5.md5() (deprecated)
        """

        # @todo: consider the possibility to add violations when defining
        #    static variables inside class definitions. Then modifications
        #    inside metamodel, for example to Python_Class add (maybe new) category inheritance.
        #    Class scopes should be added as well in files inside InstallScripts folder.
        #
        if is_class(self.get_current_symbol()):
            return

        try:
            parent = method_call.parent
        except:
            return  # skip issues with 'builtin' module

        if is_dot_access(parent):
            return

        method = method_call.get_method()
        argument = None
        if is_dot_access(method):

            name = method.get_name()

            # skip md5 object's methods
            while name in ['update', 'digest', 'hexdigest', 'copy']:
                expr = method.get_expression()

                if is_method_call(expr):
                    method_call = expr
                    method = expr.get_method()

                    if is_dot_access(method):
                        name = method.get_name()
                        continue
                return
            
            match_constructor = False

            # hashlib.new('md5') / hashlib.md5([arg])
            if name in ['md5', 'sha1']:
                argument = method_call.get_argument(0, None)
                if is_identifier(method.get_expression()):
                    match_constructor = True

            if match_constructor and is_identifier(method.get_expression()):
                    identifier_name = method.get_expression().get_name()
                    if identifier_name == 'hashlib':
                        # to avoid false positives, (since 
                        # md5 might be used for data integrity check) 
                        # we will try to guess whether the
                        # parameter is related to a password or not
                        if argument:
                            if is_method_call(argument):
                                # example:  identifier.encode()
                                method = argument.get_method()
                                if is_dot_access(method):
                                    identifier = method.get_expression()
                                    argument = identifier
                                    
                            if not is_identifier(argument):
                                return
                            
                            if argument.get_name() in AvoidHardcodedPasswords.pss:
                                self.get_current_symbol().add_violation('CAST_Python_Rule.useOfMd5Hashes', method_call)
                                return


class YieldAndReturnWithValueInFunction(QualityRule):

    def start_Function(self, ast_function):

        has_yield = False
        has_return_with_value = False
        for node in self.search_ReturnYield(ast_function):

            if isinstance(node, (Yield, YieldFrom)):
                has_yield = True
                continue

            if isinstance(node, Return):
                try:
                    expression = node.get_expression()
                    if expression:
                        if expression.get_string_value == 'None':
                            continue
                        has_return_with_value = True
                    continue
                except:
                    pass

        name = ast_function.get_name()
        function = self.get_current_symbol().get_function(name, ast_function.get_begin_line())

        if not function:
            log.warning("no function found for %s under %s" % (str(name), str(self.get_current_symbol())))

        self.push_symbol(function)

        if has_yield and has_return_with_value:
            function.add_violation('CAST_Python_Rule.returnWithValueInsideGenerator', ast_function)



    def search_ReturnYield(self, node):
        all_nodes = []
        sub_nodes = node.get_sub_nodes()

        for sub_node in sub_nodes:

            if isinstance(sub_node, (FunctionBlock, ClassBlock)):
                continue

            if isinstance(sub_node, (Return, Yield, YieldFrom)):
                all_nodes.append(sub_node)
                continue

            all_nodes.extend(self.search_ReturnYield(sub_node))

        return all_nodes


class EmptyCatchAllExceptionClause(QualityRule):
    """
    Two conditions must be fulfilled to register a violation

    (i) a catch-all as first exception. There are essentially four different cases
        to be handled when parsing the except header:
        
        (1) except:
        (2) except Exception:
        (3) except (Exception, ..):
        (4) except Exception, err:   # Python 2
       
       
    (ii) Single 'empty' statement in the exception handler. Two different
        conventions are considered only:
         
        (1) null operation "pass"
        (2) Elipsis "..." object
        
        
    Limitations
    -----------
    
    - 'Empty' statements might be missed if other trivial (non conventional) expression statements
    are used like using an integer:

            try:
                try_statement()
            except:
                1

    - Violations raised within unit test functions might be considered as false positives. @todo?: skip test files
    
    - We might consider skipping violations when found at module level (these are used to allow running the code
      whatever happens)
      
    - Edge case: When multiple exception clauses in a try statement, violations are applied independently
      to each clause. Probably we should avoid violation if there is previous detailed handling of cases. 
      This requires nesting exception blocks into try blocks when parsing them.
    """

    def is_catch_all_exception(self, token):
        """
        Return True if identifier is a high order Exception
        """
        if is_identifier(token):
            if token.get_name() in ['Exception', 'BaseException']:
                return True

        return False

    def start_ExceptOneLine(self, ast_except):

        self.start_ExceptBlock(ast_except)

    def start_ExceptBlock(self, ast_except):

        tokens = ast_except.get_children()

        tokens.move_to('except')    # move to first except clause
        next(tokens)                # consume 'except'

        token = next(tokens)

        if token.text == ':':
            pass

        elif self.is_catch_all_exception(token):
            pass

        # handle: "except Except, err"
        elif is_expression_list(token):
            sub_tokens = token.get_children()
            token = next(sub_tokens)

            if is_identifier(token) and not self.is_catch_all_exception(token):
                return

        elif is_parenthesis(token):
            sub_tokens = token.get_children()
            next(sub_tokens)
            token = next(sub_tokens)  # consume "("

            while not self.is_catch_all_exception(token):
                try:
                    next(sub_tokens)
                    token = next(sub_tokens)  # consume ","
                except StopIteration:
                    return

        # all the rest assumed to be lower level Exceptions
        # and thus not a catch-all
        else:
            return


        try:
            while token.text != ':':
                token = next(tokens)
        except StopIteration:
            return

        blocks = list(ast_except.get_sub_nodes(IndentBlock))

        if blocks:
            block = blocks[0]
            try:
                statements = block.get_statements()
            except AttributeError:
                return
            else:
                # we assume that the many statements in except clause
                # are not "empty" ones
                if len(statements) > 1:
                    return

                # the analyser does not consider standalone expressions
                # as statements
                if statements:
                    statement = statements[0]
                else:
                    statement = None
        # handle one-line except clause
        else:
            statement = list(ast_except.get_sub_nodes())[0]


        try:
            type_ = statement.get_type()
        except AttributeError:
            # ex. literal strings
            type_ = None

        if type_  in ['Pass', 'EllipsisObject', None]:
            self.get_current_symbol().add_violation('CAST_Python_Rule.emptyCatchAllExceptionClause', ast_except)


class AvoidWildCardImport(QualityRule):

    def start_Import(self, ast_import_data):
        """
        > This functions searches for the import statements in the code.
        > Raises or adds and violation if wildcard character * is used 
        while importing from a module.
            > e.g. from math import *
            
        Multiple imports from a single module in same row will not be treated
        as a violation
        e.g. from math import ceil, pow    is correct
        """
        # Boolean Variable to determine if the violation has to be raised or not
        has_violation = False
        tokens = ast_import_data.get_children()
        original_tokens = ast_import_data.get_children()

        # Boolean variable for checking the presence of "from" word
        from_statement = False

        for token in tokens :
            if token.text == "from":
                from_statement = True
                #print ("--> token from ", token.text, tokens)
                break

        # If "from" exists then  check for:
        # If there are multiple imports from the same module in same row then no violation
        # If wildcard character "*" is used for importing then violation needs to be raised
        if from_statement :
            if self.check_from_statement_multiple_import(tokens) == True:
                has_violation = False
            has_violation = self.check_wildcard_import(original_tokens)

        # Check if violation needs to be raised
        if has_violation:
            self.get_current_symbol().add_violation('CAST_Python_Rule.avoidWildCardImport', ast_import_data)

    def check_wildcard_import(self, tokens):
        """
        This function returns True if the wildcard * is used for import in from statement
        e.g. from numpy import *
        """
        has_wildcard_import = False
        tokens.move_to('import')
        try:
            token = next(tokens)
            if token.text == "*":
                has_wildcard_import = True

            return has_wildcard_import
        except:
            pass

    def check_from_statement_multiple_import (self, tokens):
        """
        This function checks if the "from" statement has multiple imports.
        If yes, then its not a violation
        e.g. from math import sqrt, pow should be treated correct and hence no violation
        """
        has_from_multiple_imports = False
        for token in tokens :
            if token.text == ",":
                has_from_multiple_imports = True
                break
        return has_from_multiple_imports


class CallAncestorWhenOverridingInit(QualityRule):
    """
    Identifies a violation in the __init__ method of a
    subclass when NO call to the its ancestor's corresponding
    __init__ method is found. Two different approaches exist
    to call the ancenstor's __init__ method:
    
        class A:
            def __init__(self):
                self.x = 3
                self.y = 14
        
        class B1(A):  #1
            def __init__(self):
                A.__init__(self)
                
        
        class B2(A):  #2
            def __init__(self):
                super().__init__()
                
                
    Rationale behind this violation:
    
      (i) Whether it was forgotten or deliverately omitted, if the class is open for development, then
    it might introduce unexpected errors when the ancestor is further extended.

      (ii) Additionally, if there was no need to initialize the ancestor, it might indicate that 
    inheritance is not the most appropriate approach to organize this particular piece of code.


    Limitations & restrictions
    --------------------------
    - Only inherited classes that are resolvable are considered. Thus external modules are skipped, 
    including those built-in : type, Exception, ...

    - The rule is only applied to non-initialized __init__ methods that are NON-trivial, ie, with
      member initialization:
    
        def __init__(self):
            pass  # trivial / empty

    - supported classes referred as A.B, but not A.B.C or deeper
    - builtin classes like 'type' or 'Exception' are not considered for the rule (as desired following first point)         
    """

    def has_init(self, reference):
        """Returns True only if ancestor has a non-trivial __init__ method,
        and if the ancestor itself is uniquely resolved.
        """

        resolutions = reference.get_resolutions()

        # non-ambiguously resolved
        if not len(resolutions) == 1:
            return False

        class_ = resolutions[0]

        # non-trivial __init__
        if not class_.get_members():
            return False

        for statement in class_.get_statements():
            if not is_function(statement):
                continue
            function = statement
            name_function = function.get_name()
            if name_function == '__init__':
                    return True

        return False

    def start_Function(self, ast_function):

        symbol = self.get_current_symbol()
        name_function = ast_function.get_name()
        function = symbol.get_function(name_function, ast_function.get_begin_line())
        self.push_symbol(function)

        # only methods of a class
        if not is_class(symbol):
            return

        inheritance = symbol.get_inheritance()

        ancestors = set([reference.get_name() for reference in inheritance
                                              if self.has_init(reference)])

        if name_function == '__init__':
            call_init_ancestors = set()
            call_super = False
            for statement in ast_function.get_statements():
                try:
                    expr = statement.get_expression()
                    call = expr.get_method()
                    if is_dot_access(call):
                        if call.get_name() == '__init__':
                            ancestor = call.get_expression()
                            name_ancestor = None

                            if is_dot_access(ancestor):
                                identifier = ancestor.get_expression()
                                tok = ancestor.get_identifier()
                                name_ancestor = identifier.get_name() + "." + tok.text
                            elif is_method_call(ancestor):
                                ancestor = ancestor.get_method()

                            if not name_ancestor:
                                name_ancestor = ancestor.get_name()

                            if name_ancestor == 'super':
                                call_super = True
                                break

                            call_init_ancestors.add(name_ancestor)
                except:
                    continue

            # ">=" takes into account special cases when, eg,
            # 'Exception', 'ValueError', 'type' classes are initialized,
            # however these are not resolved by get_inheritance() used
            # above (these are parsed as Token.builtins.type, Token.Name.Exception)
            # so the set of call_init_ancestors turns out to be larger
            # than ancestors itself
            cond1 = call_init_ancestors >= ancestors

            if not (cond1 or call_super):
                function.add_violation('CAST_Python_Rule.InitializeAncestorWhenOverriding', function)


class AvoidReturnInFinally(QualityRule):
    """
    This quality rule is used to raise a violation if Return or Break or Continue statement 
    is found in finally block.
    > Break statement in finally block swallows exception
    > A finally clause is always executed before leaving the try statement,
     whether an exception has occurred or not. If the exception is not handled, it will be raised 
     after the finally block. Presence of return will never allow this exception to be raised.
    """

    def start_FinallyBlock(self, ast_finally_data):
        """
        This function is responsible for raising a violation if break, continue or return is found in 
        finally block
        > It is executed whenever a finally block is present in the code
        > ASt of the finally block is send as an argument to the method find_keyword to search for the 
          desired keywords. This search is done recursively. Presence of keyword appends True to the list,
          absence indicates False. 
        > At the end of the search, this list is checked for the presence of any True element and violation
          is raised accordingly
        """
        self.keywords_found = []
        violations_found = self.find_keyword(ast_finally_data)

        if any(violations_found):
            self.get_current_symbol().add_violation('CAST_Python_Rule.avoidReturnInFinally', ast_finally_data)

    def find_keyword(self, ast_root_data):
        """
        This  function scans the ast for the keywords
        > Follows the recursive approach on all the children nodes
        > Search continues till we reach the end or the keyword has been found
        """
        keyword_found = False
        try :
            tokens_text = [token.get_type() for token in ast_root_data.get_children()]
        except:
            return []
        else :
            if 'Return' in tokens_text or 'Break' in tokens_text or 'Continue' in tokens_text:
                keyword_found = True
                self.keywords_found.append(keyword_found)
                return self.keywords_found
            else :
                for child in ast_root_data.get_children():
                    self.find_keyword(child)
                keyword_found = False
                self.keywords_found.append(keyword_found)
                return self.keywords_found


class AlwaysCloseFileResources(QualityRule):
    """
    The advantage of using a *with* statement is that it is guaranteed 
    to close the file no matter how the nested block exits.
    
    Special use cases NOT to be considered as violation:
    
        - Assignements of file-like objects to instance members as well as
        instance member initializations:
        
            >>> class A:
            >>>     def __init__(self):
            >>>         self.f = open("file.txt", "w")
          
        - Returning a file-like object:
            
            >>> f = open("file.txt", "w")
            >>> return f
    """

    def start_MethodCall(self, ast_method_call):
        method = ast_method_call.get_method()

        # skips expressions like a.b()
        if is_dot_access(method):
            return
        if is_identifier(method):
            method_name = method.get_name()
            if method_name == 'open':
                try:
                    # raise violation when open().read, open().write, ...
                    # except open().close()
                    grand_parent = method.parent.parent
                    if is_dot_access(grand_parent):
                        identifier = grand_parent.get_identifier()

                        txt = identifier.text
                        if txt == 'close':
                            return

                        self.get_current_symbol().add_violation('CAST_Python_Rule.AlwaysCloseFileResources', ast_method_call)
                        return

                    enclosing = method.get_enclosing_statement()

                    if self.open_in_FOR_expression_list(enclosing):
                        self.get_current_symbol().add_violation('CAST_Python_Rule.AlwaysCloseFileResources', ast_method_call)
                        return

                    if self.use_WITH_statement(enclosing):
                        return

                    if self.returned_file_object(enclosing):
                        return

                    if self.close_inside_finally(enclosing):
                        return

                    assignment = enclosing.get_expression()
                    if not is_assignement(assignment):
                        return

                    # skip file-like object assignment to an instance member
                    left = assignment.get_left_expression()
                    if is_dot_access(left):
                        return
                except:
                    return

                self.get_current_symbol().add_violation('CAST_Python_Rule.AlwaysCloseFileResources', ast_method_call)

    def open_in_FOR_expression_list(self, enclosing):
        return True if isinstance(enclosing, ForBlock) else False

    def use_WITH_statement(self, enclosing):
        return True if isinstance(enclosing, WithBlock) else False

    def close_inside_finally(self, enclosing):
        assignment = enclosing.get_expression()
        if not is_assignement(assignment):
            return False
        file_identifier = assignment.get_left_expression()
        name_file = file_identifier.get_name()
        try:
            block = enclosing.get_container_block()
            try:
                block = block.parent
            except AttributeError:  # note: modules do not have parent
                pass
        except AttributeError:
            return False
        begin_line = enclosing.get_begin_line()
        for statement in block.get_statements():
            if statement.get_begin_line() < begin_line:
                continue
            if isinstance(statement, FinallyBlock):
                for sub_statement in statement.get_statements():
                    method_call = sub_statement.get_expression()
                    if is_method_call(method_call):
                        method = method_call.get_method()
                        token = method.get_identifier()
                        identifier = method.get_expression()
                        if identifier.get_name() == name_file and token.text == 'close' :
                            return True
        return False

    def returned_file_object(self, enclosing):
        """Returns True if the file object is returned in a function. 
        Two use cases are checked:
        
        (i)
            >>> return open("file.txt", 'w')
        
        (ii)
            >>> f = open("file.txt", 'w')
            >>> return f
        """

        # (i)
        if isinstance(enclosing, Return):
            return True

        # (ii)
        assignment = enclosing.get_expression()
        if not is_assignement(assignment):
            return False
        file_identifier = assignment.get_left_expression()
        try:
            block = enclosing.get_container_block()
            block = block.parent
        except AttributeError:
            return False

        if is_function(block):
            for statement in block.get_statements():
                if not isinstance(statement, Return):
                    continue
                if isinstance(statement, Return):

                    expression = statement.get_expression()
                    if not expression:
                        # Return statement without expression
                        continue
                    resolutions = expression.get_resolutions()

                    if file_identifier in resolutions:
                        return True
        return False


class AvoidEmptyFinallyBlock(QualityRule):
    """
    A finally clause is always executed before leaving the try statement,
    whether an exception has occurred or not. If the exception is not handled, 
    it will be raised after the finally block. In a try and except finally 
    statement, finally blocks should contain code  to handle the thrown exception or 
    release the resources etc, should not be left empty.
    
    This quality rule will raise a violation if finally block is empty.
    """

    def start_FinallyBlock(self, ast_finally_data):
        """
        This function raises violation if finally block is empty
        > Every time finally block is encountered, this function gets executed
        > Indent token is identified
        > List is created for the type of sub nodes in indent token
        > If "Pass" is found in the list and the list consists of only one node
          then violation is raised. 
        > Length of the list should be one because if the pass statement is preceded 
          by some code e.g. print , then violation must not be raised. In such a 
          case, list will consist of other nodes also e.g. Print.
          
          try:
              x = 5/0
          except ZerDivisionError as e:
              print("Division by 0 not possible)
          finally:
              pass   ----------------> Error , should  contain some code
              
          try:
              x = 5/0
          except ZerDivisionError as e:
              print("Division by 0 not possible)
          finally:
              print ("Division", x)
              pass   # ----------------> Acceptable (Length of list of indent sub nodes > 1)
        """
        violation_found = False

        indent_token = list(ast_finally_data.get_children())[-1]

        indent_token_sub_nodes = [token.get_type() for token in indent_token.get_sub_nodes()]

        if ('Pass' in indent_token_sub_nodes or 'EllipsisObject' in indent_token_sub_nodes) and len(indent_token_sub_nodes) == 1:
            pass_sub_node = indent_token.get_sub_nodes('Pass')
            violation_found = True

        if violation_found:
            self.get_current_symbol().add_violation('CAST_Python_Rule.avoidEmptyFinallyBlock', ast_finally_data)


class AvoidHardcodedResources(QualityRule):
    """
    @todo: skip strings inside assertions (likely to be a test)
    """

    def start_Constant(self,  ast_constant):


        try:
            string = ast_constant.get_string_value()
        except:
            return

        if not string:
            return

        # check if inside string concatenation or interpolation
        # -> cases not covered: .format and f-strings
        try:
            parent = ast_constant.parent
        except AttributeError:
            pass
        else:
            if is_interpolation(parent) or is_addition(parent):
                return

        # skip configuration and test files
        file = self.get_module().get_file()
        if file:
            filename = file.get_name()
            filename = filename.split(".", 1)[0]  # remove ".py" extension

            excluded_cases = [filename.startswith("test_"),
                        filename.endswith("_test"),
                        "__init__" == filename,
                        "install" in filename,
                        "config"  in filename,
                        "setup"   in filename,
                        ]

            if any(excluded_cases):
                return

        # check if inside a test assert of the form
        #   >>>  self.assertXXXX(...)
        try:
            enclosing = ast_constant.get_enclosing_statement()
            call = enclosing.get_expression()
            method = call.get_method()
            identifier = method.get_identifier()
            if 'assert' in identifier.text:
                return
        except:
            pass

        try:
            ipv4 = AvoidHardcodedResources.match_ipv4(string)
            ipv6 = AvoidHardcodedResources.match_ipv6(string)
            url = AvoidHardcodedResources.match_url(string)
            path_w = AvoidHardcodedResources.match_absolute_path_windows(string)
            path_l = AvoidHardcodedResources.match_absolute_path_linux(string)
        except:
            return

        if any([ipv4, ipv6, url, path_w, path_l]):
            self.get_current_symbol().add_violation('CAST_Python_Rule.AvoidHardcodedNetworkResourceNames', ast_constant)

    IP4Regexp = ('(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
                 '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
                 '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.'
                 '(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)')

    IP6Regexp = ('((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|'
                  '(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3})|:))|'
                  '(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3})|:))|'
                  '(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|'
                  '(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|'
                  '(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|'
                  '(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:))|'
                  '(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]d|1dd|[1-9]?d)(.(25[0-5]|2[0-4]d|1dd|[1-9]?d)){3}))|:)))'
                 '(%.+)?s*(\/([0-9]|[1-9][0-9]|1[0-1][0-9]|12[0-8]))?')

    @staticmethod
    def match_ipv4(text):
        res = re.search(AvoidHardcodedResources.IP4Regexp, text)
        if not res:
            return False
        start = res.start()
        if start > 0 and text[start - 1] != '/':
            return False
        end = res.end()
        l = len(text)
        if end == l or text[end] in ['/', ':']:
            return res
        return False

    @staticmethod
    def match_ipv6(text):
        res = re.search(AvoidHardcodedResources.IP6Regexp, text)
        if not res:
            return False
        if text.startswith(':'):
            return False
        start = res.start()
        if start > 0 and text[start - 1] != '/':
            return False
        end = res.end()
        l = len(text)
        if end == l and text.endswith('::'):
            return False
        if end == l or text[end] in ['/', ':']:
            return res
        return False

    @staticmethod
    def match_url(text):
        """
        resources:
           https://stackoverflow.com/questions/7857416/file-uri-scheme-and-relative-files
           
        note: "(?:...) means non-capturing group, where "..." denotes any other regular expression
        """
        regex = re.compile(
            # adapted from: https://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
            #     reporting django url validation regex from
            r'^((?:http|ftp)s?://)|(www\.)'
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        return True if regex.match(text) else False

    @staticmethod
    def match_absolute_path_windows(text):

        # the python's os.path module automatically handles forward slashes
        # to adapt to the underlaying platform
        regex = re.compile(
        r'(file:///)?[A-Z]:(\\|/)(.+)', re.IGNORECASE)

        return True if regex.match(text) else False

    @staticmethod
    def match_absolute_path_linux(text):

        # source:   http://www.thegeekstuff.com/2010/09/linux-file-system-structure
        #   we don't consider : "dev" (not regular file)
        high_level_dirs = ["bin", "sbin", "etc", "proc", "var", "tmp", "usr", "home", "boot", "lib", "opt", "mnt", "media", "src"]

        pattern_dirs = r"|".join(high_level_dirs)
        pattern = r'(file:///)?/(' + pattern_dirs + ')/.*'

        regex = re.compile(pattern, re.IGNORECASE)

        return True if regex.match(text) else False


class InconsistentInitializationWhenSubclassingException(QualityRule):
    """
    Python Cookbook, 3rd Ed. p. 579.   http://chimera.labs.oreilly.com/books/1230000000393/ch14.html

        ``If you are going to define a new exception that overrides the __init__() method
        of Exception, make sure you always call Exception.__init__() with all of the passed arguments.``
        
    https://stackoverflow.com/questions/1319615/proper-way-to-declare-custom-exceptions-in-modern-python
    
    Features & limitations:
    =======================
    
        - Most standard exceptions captured: "Exception" and those which name ends with "Error"
        
        - Compared number of arguments passed. *args and **kwargs ignored
        
        - Even if the subclass overrides "__init__", when no arguments are passed to "subclass.__init__", 
          the rule does not apply. Its innocuity has been checked for a particular use case using 
          the "pickle" module.
        
        - There might be an alternative way (little bit more verbose) to circumvent potential errors, 
          given by the answer of Martijn Pieters:
            https://stackoverflow.com/questions/16244923/how-to-make-a-custom-exception-class-with-multiple-init-args-pickleable
       
    """

    def start_ClassBlock(self, _ast_class):
        super().start_ClassBlock(_ast_class)

        _class = self.get_current_symbol()
        inheritances = _class.get_inheritance()

        if not inheritances:
            return

        name_ancestors = [reference.get_name() for reference in inheritances]

        cond1 = 'Exception' in name_ancestors
        cond2 = any(name.endswith("Error") for name in name_ancestors)
        if cond1 or cond2:
            init = _class.get_function('__init__')
            if init:
                ast_init = init.get_ast()
                try:
                    parameters_subclass = ast_init.get_parameters()
                    parameters_subclass = [identifier.get_name() for identifier in parameters_subclass]
                    # remove 'self'
                    parameters_subclass = parameters_subclass[1:]

                    # if no extra arguments passed to __init__,
                    # violation does not apply
                    if not parameters_subclass:
                        return

                    statements = init.get_statements()
                    for statement in statements:
                        expression = statement.get_expression()
                        if is_method_call(expression):
                            method = expression.get_method()
                            parameters = expression.get_parameters()
                            parameters = [identifier.get_name() for identifier in parameters]

                            if is_dot_access(method):
                                identifier = method.get_identifier()
                                if is_identifier(identifier):
                                    name_identifier = identifier.get_name()
                                else:
                                    # likely to be a Token
                                    name_identifier = identifier.text

                                if name_identifier == "__init__":
                                    expression = method.get_expression()
                                    if is_identifier(expression):
                                        name = expression.get_name()
                                    elif is_method_call(expression):
                                        method = expression.get_method()
                                        name = method.get_name()
                                    else:
                                        # unexpected scenario
                                        return

                                    # check if direct call or through super
                                    if name == 'super' or [name] == name_ancestors:
                                        if len(parameters) == len(parameters_subclass):
                                            # no violation
                                            return

                    cls = self.get_current_symbol()
                    init_symbol = cls.get_function('__init__')
                    init_symbol.add_violation('CAST_Python_Rule.InconsistentInitializationWhenSubclassingException', ast_init)

                except:
                    pass


class AvoidUsingEval(QualityRule):
    """
    Aim of this quality rule is to raise a violation if 
    the sample code consists of eval statement
    Using eval is a bad practice as :
        > It makes code very insecure
        > Readability of the code reduces
        > Complexity increases
        
    eval() should be avoided and discouraged. 
    Following code will result in violation
        >>> import os
        >>> new_folder_creation = r'os.mkdir("C:\\New_Folder_1")'
        >>> eval(new_folder_creation)
    """
    def start_MethodCall(self, ast_method_call):
        """
        This function is called for every method call in the code :
        
        > Initialise a boolean variable violation_found with False
        > Check for all the sub nodes in the AST of the method call
        > Iterate through all the subnodes
        > If the node is an identifier and its name is eval then make
          violation_found as True and break from the for loop
        > Raise violation as per the boolean value of violation_found
        """
        violation_found = False

        try :
            sub_nodes = ast_method_call.get_sub_nodes()
        except :
            pass
        else :
            for node in sub_nodes:
                if is_identifier(node) and node.get_name() == "eval":
                    violation_found = True
                    break

        if violation_found :
            self.get_current_symbol().add_violation('CAST_Python_Rule.avoidUsingEval', ast_method_call)


class AvoidUsingExec(QualityRule):
    """
    Aim of this quality rule is to raise a violation if 
    the sample code consists of exec statement or function
    Using exec is a bad practice as :
        > It makes code very insecure
        > Readability of the code reduces
        > Complexity increases
        
    exec should be avoided and discouraged. 
    exec is a statement in Python 2.x
    exec is a builtin function call in Python 3.x
    
    Following code will result in violation
        >>> import os
        >>> new_folder_creation = r'os.mkdir("C:\\New_Folder_1")'
        >>> exec(new_folder_creation)        # Python 3 Violation
        
        
        >>> stat = 'print "Hello World!"'
        >>> exec stat                        # Python 2 Violation
    """

    def start_Exec(self, ast_exec):
        """
        This function is called every time exec statement or
        function is called in the input code :
         
        Entry to this function itself confirms the presence of 
        exec, to raise  violation. Check is made just to be on the 
        safer side.
        
        > Initialise a boolean variable violation_found with False
        > If the type of ast data is Exec, then make
          violation_found as True 
        > Raise violation as per the boolean value of violation_found
        """
        violation_found = False

        if ast_exec.get_type() == "Exec":
            violation_found = True

        if violation_found :
            self.get_current_symbol().add_violation('CAST_Python_Rule.avoidUsingExec', ast_exec)

class AvoidClassAttributesOnlyDifferingByCaps(QualityRule):
    """
    Note: In Python everything contained inside an object is an attribute,
          including plain data and function
    
    @todo: refine the violation bookmark to the violation pairs, ...
    @todo: consider generalizing to full hierarchy
    @todo: study more use-cases: static methods, sub-classes, etc ...
    """
    def start_ClassBlock(self, _ast_class):
        super().start_ClassBlock(_ast_class)

        cls = self.get_current_symbol()
        methods = [method_name.lower() for method_name in cls.get_functions().keys()]
        members = [member_name.lower() for member_name in cls.get_members().keys()]

        attributes = methods + members

        if len(attributes) != len(set(attributes)):

            cls.add_violation('CAST_Python_ClassRule.AttributesOnlyDifferingByCaps', _ast_class)


class AvoidHardcodedPasswords(QualityRule):
    """ Raise a violation when assigning a variable to hardcoded password
    
    @todo: assignment with instance members self.pssw = "ccc12837"    
    @todo: credentials['password'] = "1234abc"
    @todo: string interpolation such as: "..., password={}".format("xzik2123")
    @todo: analyse interfaces from main frameworks that handle passwords: databases (sqlite), web (django) 
    """
    # exactly matches variable name
    pss = [  # english
            'password', 'passcode', 'rootpassword', 'countersign', 'watchword', 'magic_word', 'passphrase',
            'parole', 'pass', 'pass_phrase', 'passwd', 'passwrd', 'psswrd', 'pword',
            'pss', 'psw', 'pwd',  # these can raise false positives because of similarity to file extensions
            # spanish
            'contraseña', 'contrasena', 'clave_secreta', 'palabra_accesso', 'clave_seguridad', 'clavecom',
            # chinese
            'mima', 'mìmǎ',
            # french
            'mot_de_passe'  # 'mdp'
           ]  # -> not very evident ..


    pss_ends = pss  # ["_"+w for w in pss]

    pss_begins = [w + "_" for w in pss]

    pss_inside = []

    no_pss_inside = []  # ["file", 'prompt', 'uri']


    def analyse_constant(self, constant, _ast):
        value = constant.get_value()
        if not value:
            return

        # skip chain interpolations using "%" (potential false negatives)
        if "%" in value:
            return

        if "=" in value:
            values = re.split("([;|,|-|=])", value)
            for i, value in enumerate(values):
                if value == "=":
                    # take closest string to "="
                    var = values[i - 1].lower()

                    # extract last word from nested quotes " ' ' "
                    try:
                        var = var.strip().split()[-1]
                    except IndexError:
                        continue

                    try:
                        pss = values[i + 1]
                        pss = pss.strip()
                        if not pss or pss.isspace():
                            continue

                        # heuristic to identify string interpolation by ".format"
                        if pss.startswith("{") or pss.endswith("}"):
                            continue
                    except IndexError:
                        continue

                    if self.check_password_hardcoding_and_save(var, _ast):
                        # single violation in a string is enough
                        return

    def start_Value(self, ast):
        """handles dictionaries"""

        key = ast.get_key()
        try:
            key = key.get_string_value()
        except AttributeError:
            return

        if not key:
            return

        value = ast.get_value()
        if not self.is_string_literal(value):
            return

        self.check_password_hardcoding_and_save(key, ast)

    def start_BinaryOperation(self, _ast_binary):
        operator = _ast_binary.get_operator()
        if operator not in ["==", "!="]:
            return

        left = _ast_binary.get_left_expression()

        # workaround to extract left identifier within
        # nested binary operations
        # (see tests for hardcoded passwords)
        if is_binary_operation(left):
            sub_right = left.get_right_expression()
            left = sub_right

        if not is_identifier(left):
            return

        right = _ast_binary.get_right_expression()
        if not self.is_string_literal(right):
            return

        self.check_password_hardcoding_and_save(left, _ast_binary)

    def start_Assignement(self, _ast_assig):

        operator = _ast_assig.get_operator()
        if operator not in ["="]:
            return

        right = _ast_assig.get_right_expression()
        if not self.is_string_literal(right):
            return

        left = _ast_assig.get_left_expression()

        if not is_identifier(left) and not is_dot_access(left):
            return

        if is_dot_access(left):
            left = left.get_identifier()

        # this checks for signatures in the variable name in the left
        if self.check_password_hardcoding_and_save(left, _ast_assig):
            return

        # we perform additional check in the right hand side
        self.analyse_constant(right, _ast_assig)

    def start_MethodCall(self, _ast_call):
        """ Targets method calls that likely serve to set a password, like in 
        Diango library 
            >>> set_password(raw_password)    # https://docs.djangoproject.com/en/1.11/ref/contrib/auth/
        """
        # avoid false positives:
        #    >>> data['confirm'] = getpass.getpass(' Confirm: ')
        #    >>> fp.write('password=None\n')
        #
        # @todo: probably we should find better heuristics
        #
        words_to_skip = ("get", "write", "open", "read")


        method = _ast_call.get_method()
        try:
            identifier = method.get_identifier()
        except AttributeError:
            return

        name_method = identifier.text
        if name_method.startswith(words_to_skip):
            return

        string_list = _ast_call.get_parameters()

        for string in string_list:
            # skip keyword arguments, already captured by
            # "start_Assignement"
            if is_assignement(string):
                return

            if self.is_string_literal(string):
                if self.check_password_hardcoding_and_save(identifier, _ast_call):
                    return

    def is_string_literal(self, string):
        """Returns True if string is a non-empty
        string literal (not numbers)
"""

        if not is_constant(string):
            return False

        value = string.get_string_value()
        if not value:
            return False

        match_whitespace = re.search("\s", value)
        if match_whitespace:
            return False

        return True

    def check_password_hardcoding_and_save(self, var, _ast):
        # accepts identifier or token
        if not isinstance(var, str):
            if is_identifier(var):
                identifier = var
                var = identifier.get_name().lower()
            else:
                try:
                    token = var
                    var = token.text.lower()
                except AttributeError:
                    return False

        cond1 = var in AvoidHardcodedPasswords.pss
        cond2 = any(string in var for string in AvoidHardcodedPasswords.pss_inside)
        cond3 = any(var.endswith(string) for string in AvoidHardcodedPasswords.pss_ends)
        cond4 = any(var.startswith(string) for string in AvoidHardcodedPasswords.pss_begins)
        cond5 = not any(string in var for string in AvoidHardcodedPasswords.no_pss_inside)

        if cond5 and any([cond1, cond2, cond3, cond4]):
            symbol = self.get_current_symbol()
            symbol.add_violation('CAST_Python_Rule.AvoidHardcodedPasswords', _ast)
            return True

        return False

class PreventSQLInjections(QualityRule):

    def __init__(self, module):
        super().__init__(module)
        self.sql_stmt_keywords = SelectQueryInterpreter.sql_stmt_keywords

    def start_MethodCall(self, ast):

        found_violation = False
        for sql_evaluations in SelectQueryInterpreter.extract_sql_parameters(self, ast):

            trace = sql_evaluations.ast_nodes
            for traced_node in trace:

                # using "%" formatting
                if is_interpolation(traced_node):
                    found_violation = True
                    break

                # using "str.format"
                if is_method_call(traced_node):
                    method = traced_node.get_method()

                    if method.get_identifier() in ["format", "join"]:
                        found_violation = True
                        break

                # @todo: f-strings
                if is_constant(traced_node) and traced_node.is_fstring():
                    found_violation = True
                    break


        if found_violation:
            symbol = self.get_current_symbol()
            symbol.add_violation('CAST_Python_Rule.SqlQueryStringConcatenation', ast)

class AvoidNotIs(QualityRule):
    """ Raise a violation when 'not...is' is used """

    def __init__(self, module):
        super().__init__(module)
        self.unarynot = None
        self.name = 'CAST_Python_Rule.AvoidNotIs'

    def start_UnaryNot(self, unarynot):
        self.unarynot = unarynot

        for node in unarynot.get_sub_nodes():

            try:
                operator = node.get_operator()
            except AttributeError:
                continue

            if operator == 'is':
                self.resolve_violations(node)

    def resolve_violations(self, root):
        """ 
        Find recursively a BinaryOperation of the form:
            
            BinaryOperation[
                Identifier[Token(Token.Name,'name',3,12,3,13)],
                Token(Token.Operator.Word,'is',3,14,3,16)
            ]
        """
        try:
            operator = root.get_operator()
        except AttributeError:
            return

        for node in root.get_sub_nodes():
            if is_identifier(node) and operator == 'is':
                if not node.get_name() == 'None':
                    self.get_current_symbol().add_violation(self.name, self.unarynot)
                    return
            else:
                self.resolve_violations(node)


class AvoidSuperfluousParenthesis(QualityRule):
    """
    Raise violation if superfluous parenthesis is used in
    if, while or for block
    """
    name = 'CAST_Python_Rule.AvoidSuperfluousParenthesis'
    node_kinds = (BinaryOperation, MethodCall, UnaryNot, IfTernaryExpression)

    def start_IfThenElseBlock(self, ast):
        self.analyse_parenthesisBlock(ast)

    def start_WhileBlock(self, ast):
        self.analyse_parenthesisBlock(ast)

    def start_ForBlock(self, ast):
        self.analyse_parenthesisBlock(ast)

    def analyse_parenthesisBlock(self, ast):
        expression = ast.get_expression(strip_parentheses=False)
        if is_parenthesis(expression):
            self.addViolation(expression)

        elif not isinstance(expression, MethodCall):
            try:
                parenthesis = next(expression.get_sub_nodes(Parenthesis))
                if len(parenthesis.children) == 3:
                    try:
                        if next(parenthesis.get_sub_nodes(self.node_kinds)):
                            pass
                    except:
                        self.addViolation(parenthesis)
            except:
                pass

    def addViolation(self, expression):

        begin_line = expression.get_begin_line()
        end_line = expression.get_end_line()
        begin_column = expression.get_begin_column()
        end_column = expression.get_end_column()
        ast = _AstPositions(begin_line, begin_column, end_line, end_column)
        if begin_line == end_line:
            self.get_current_symbol().add_violation(self.name, ast)


class _AstPositions:
        """
        Class that only implements the bookmarking interface for
        later violation markup
        """

        def __init__(self, begin_line, begin_column, end_line, end_column):
            self._begin_line = begin_line
            self._begin_column = begin_column
            self._end_line = end_line
            self._end_column = end_column

        def get_begin_line(self):
            return self._begin_line

        def get_end_line(self):
            return self._end_line

        def get_begin_column(self):
            return self._begin_column

        def get_end_column(self):
            return self._end_column

        def __str__(self):
            return "Bookmark({},{},{},{})".format(self._begin_line,
                                          self._begin_column,
                                          self._end_line,
                                          self._end_column)


class PEP8(QualityRule):

    """
    This class treats together a few PEP-8 
    quality rules that need line by line analysis 
    to reduce computational cost.
    """

    max_line_length = 99
    max_comment_length = 72
    rule_name1 = 'CAST_Python_PEP8Rule.AvoidLongLines'
    rule_name2 = 'CAST_Python_PEP8Rule.AvoidLongDocstringLines'
    rule_name3 = 'CAST_Python_PEP8Rule.MissingWhitespaceAfterComma'
    rule_name4 = 'CAST_Python_PEP8Rule.AvoidTrailingWhitespace'

    def __init__(self, module):
        super().__init__(module)
        self.bookmarked_lines = []
        self.string_bookmarks = []

    def start_Function(self, ast):
        super().start_Function(ast)
        if ast.get_docstring(unstripped=True):
            text, token = ast.get_docstring(unstripped=True)
            self._bookmark_lines(text, token.get_begin_line())

    def start_Class(self, ast):
        super().start_Class(ast)
        if ast.get_docstring(unstripped=True):
            text, token = ast.get_docstring(unstripped=True)
            self._bookmark_lines(text, token.get_begin_line())

    def start_Constant(self, ast):

        if not ast.is_constant_string():
            return

        self.register_string_bookmark(ast)

    def register_string_bookmark(self, ast):
        begin_line = ast.get_begin_line()
        begin_column = ast.get_begin_column()
        end_line = ast.get_end_line()
        end_column = ast.get_end_column()

        bookmark = _AstPositions(begin_line, begin_column, end_line, end_column)
        self.string_bookmarks.append(bookmark)
        
    def addViolation(self, lineno, length, rule_name, begin_col=1):
        ast = _AstPositions(lineno, begin_col, lineno, length + 1)
        self.get_module().add_violation(rule_name, ast)

    def analyse_length(self, lineno, line):
        """
        Analyse the nth (lineno) line of a code file:
            - Adds violation if length of code line exceeds 99 characters.
            - Adds violation if length of comments/docstring exceeds 72 characters.
        """

        length = len(line)

        if length > self.max_comment_length and line.lstrip().startswith('#'):
            self.addViolation(lineno, length, self.rule_name1, begin_col=73)

        elif lineno not in self.bookmarked_lines and length > self.max_line_length:
            self.addViolation(lineno, length, self.rule_name1, begin_col=100)

    def analyse_comma(self, lineno, line):

        # skip comments
        if line.lstrip().startswith('#'):
            return

        # skip function/class docstrings
        if lineno in self.bookmarked_lines:
            return

        length = len(line)
        
        inline_comment = False
        for i, char in enumerate(line):
            if i == length-1:
                return

            if char == "#":
                inline_comment = True
                # TODO: refactor into function loop running through bookmarks
                # if inside string or docstring -> continue
                for bookmark in self.string_bookmarks:
                    if (bookmark.get_begin_line() <= lineno <= bookmark.get_end_line()):
                        if lineno in [bookmark.get_begin_line(), bookmark.get_end_line()]:
                            if bookmark.get_begin_column() < i + 1 < bookmark.get_end_column():
                                inline_comment = False
                                break
                            else:
                                # inline comment
                                break
                        inline_comment = False
                        break

            if inline_comment:
                return

            if char == ',':
                # TODO: another PEP8 rule -> Extra space in tuple
                if line[i + 1] in (' ', ')', '}', ']'):
                    return

                for bookmark in self.string_bookmarks:
                    if (bookmark.get_begin_line() <= lineno <= bookmark.get_end_line()):
                        if lineno in [bookmark.get_begin_line(), bookmark.get_end_line()]:
                            if bookmark.get_begin_column() < i + 1 < bookmark.get_end_column():
                                return
                            else:
                                continue
                        return

                end_column = i + 2
                self.addViolation(lineno, end_column, self.rule_name3)

    def _analyse_lines(self, text, start_line):
        if isinstance(text, str):
            text = text.splitlines()

        for i, line in enumerate(text, start_line):
            line = line.rstrip('\n')
            if i not in self.bookmarked_lines:
                self.analyse_whitespace(i, line)
                self.analyse_length(i, line)
            self.analyse_comma(i, line)

    def register_module_level_strings(self):
        """
        Register module docstrings which are
        not captured by _getDocstring and dangling strings
        """
        module = self.get_module()
        ast_module = module.get_ast()
        for token in ast_module:
            typ = token.type
            if str(typ).startswith('Token.Literal.String'):
                triple_quotes = ('"""', "'''")
                if token.text.startswith(triple_quotes):
                    self._bookmark_lines(token.text, token.get_begin_line())
                self.register_string_bookmark(token)

    def _bookmark_lines(self, text, start_line):
        ast_fragments = []
        if isinstance(text, str):
            text = text.splitlines()

        for i, line in enumerate(text, start_line):
            line = line.rstrip('\n')
            length = len(line)
            self.bookmarked_lines.append(i)
            if length > self.max_comment_length:
                ast = _AstPositions(i, 73, i, length + 1)
                ast_fragments.append(ast)
        if ast_fragments:
            self.get_current_symbol().add_violation(self.rule_name2, *ast_fragments)

    def analyse_whitespace(self, lineno, line):
        """
        Raise a violation if trailing whitespace is present
        in code lines.
        """
        length1 = len(line)
        new_line = line.rstrip()
        length2 = len(new_line)
        comment_line = line.lstrip().startswith('#')
        if length2 not in (0, length1) and not comment_line:
            self.addViolation(lineno, length1, self.rule_name4)

    def on_end(self):
        self.register_module_level_strings()
        text = self.get_module().get_text()
        self._analyse_lines(text, start_line=1)


class PreventSensitiveDataInConfigFilesFromDisclosure(QualityRule):

    """ 
    Raise a violation when loading sensitive data using the OpenStack 
    framework without the protection flag. 
    """

    def __init__(self, module):
        super().__init__(module)
        self.name = 'CAST_Python_Rule.PreventDataDisclosureOStack'
        self.class_name = 'StrOpt'
        self.keyword_name = 'secret'
        self.keyword_value = 'True'
        # list of names tested
        self.filter_values = ['password', 'pass', 'pswd', 'user', 'username',
                              'credential', 'authentification', 'motdepasse',
                              'mot de passe', 'passwd', 'pswrd',
                              'p/w', 'login' , 'contraseña']

    def filter(self, value, filter_values):
        """ Return True if one of the name of filter_values is in value """
        for word in filter_values:
            if word in value.lower():
                return True

        return False

    def start_MethodCall(self, method_call):
        """
        Raise a violation if the constructor of the class StrOpt is used 
        for a password without the assignment "secret=True"
        """
        if is_class(self.get_current_symbol()):
            return

        try:
            parent = method_call.parent
        except:
            return  # skip issues with 'builtin' module

        if is_dot_access(parent):
            return


        method = method_call.get_method()
        try:
            method_name = method.get_name()
        except AttributeError:
            return
        match_constructor = False
        match_secret = True
        if self.class_name == method_name:
            match_constructor = True
            parameters = method_call.get_parameters()
            if (len(parameters) > 0
                    and parameters[0].is_constant_string()
                    and self.filter(parameters[0].get_value(),
                                    self.filter_values)):
                match_secret = False
                # keyword argument
                for assig in parameters:
                    if not is_assignement(assig):
                        continue
                    kw = assig.get_left_expression()
                    val = assig.get_right_expression()

                    if (self.keyword_name == kw.get_name()
                        and is_identifier(val)
                        and self.keyword_value == val.get_name()):
                        match_secret = True
                        break

            if match_constructor and not match_secret:
                self.get_current_symbol().add_violation(self.name, method_call)


class AvoidUnsecuredCookie(QualityRule):

    rule_name = 'CAST_Python_Rule.AvoidUnsecuredCookie'

    def __init__(self, module):
        super().__init__(module)
        self.module = module
        self.method_name = 'set_cookie'
        self.keyword_name = 'secure'
        self.keyword_value = 'True'
        self.global_environment_variable_name = 'CSRF_COOKIE_SECURE'
        self.cookie_secured = False
        self.violation_candidates = []

    def start_Assignement(self, assignment):
        """ 
        Verify if the environment variable CSRF_COOKIE_SECURE is set to "True"
        In that case the cookies are secured and there is not any possible 
        violations
        """
        left_expression = assignment.get_left_expression()
        right_expression = assignment.get_right_expression()
        if (is_identifier(left_expression)
                and self.global_environment_variable_name == left_expression.get_name()
                and is_identifier(right_expression)
                and self.keyword_value == right_expression.get_name()):
            self.cookie_secured = True
            self.violation_candidates.clear()

    def start_MethodCall(self, method_call):
        """
        Raise a violation if the method set_cookie of the class HttpResponse
        is used without the assignment "secure=True".
        In that case the cookie is unsecured.
        """
        # If the environment variable CSRF_COOKIE_SECURE is set to "True"
        if self.cookie_secured:
            return

        if is_method(self.get_current_symbol()):
            return

        try:
            parent = method_call.parent
        except:
            return  # skip issues with 'builtin' module

        if is_dot_access(parent):
            return

        method = method_call.get_method()
        if is_dot_access(method):
            try:
                method_name = method.get_name()
            except AttributeError:
                return

            match_method = False
            match_secure = False

            if self.method_name == method_name:
                match_method = True
                parameters = method_call.get_parameters()
                if not parameters:
                    return

                # keyword argument
                for assig in parameters:
                    if not is_assignement(assig):
                        continue
                    kw = assig.get_left_expression()
                    val = assig.get_right_expression()
                    if self.keyword_name == kw.get_name() and \
                            is_identifier(val) and \
                            self.keyword_value == val.get_name():
                        match_secure = True
                        break

            if match_method and not match_secure:
                self.violation_candidates.append((self.get_current_symbol(),
                                                  self.rule_name,
                                                  method_call))

    def on_end(self):
        """ Add remaining violation candidates as violations """

        library = self.get_module().get_library()
        if not self.cookie_secured:
            library.violation_candidates.extend(self.violation_candidates)

        else:
            library.adding_violation_candidates = False


def save_violation_candidates(library):
    log.debug('violation candidate saving')
    if library.adding_violation_candidates:
        for candidate in library.violation_candidates:
            candidate[0].add_violation(candidate[1], candidate[2])

        for module in library.get_modules():
            try:
                module.save_candidate_violations(AvoidUnsecuredCookie.rule_name, module.get_file())
            except Exception:
                log.warning('An error occurred on file ' + module.get_path())
                log.warning(traceback.format_exc())
    else:
        library.violation_candidates.clear()


class NamingConventions(QualityRule):
    """
    @todo: recognize camelCase or not
    """
    
    rule_name_for = dict()
    rule_name_for['class'] = 'CAST_Python_PEP8Rule.RespectClassNamingConventions'
    rule_name_for['function'] = 'CAST_Python_PEP8Rule.RespectFunctionNamingConventions'
    rule_name_for['variable'] = 'CAST_Python_PEP8Rule.RespectVariableNamingConventions'

    def start_Identifier(self, identifier):

        name = identifier.get_name()
        if name in ['l', 'O', 'I']:
            self.get_current_symbol().add_violation(self.rule_name_for['variable'], identifier)


    def start_Assignement(self, assig):
        left = assig.get_left_expression()

        # self.varCamelCase
        if is_dot_access(left):
            identifier = Identifier()
            identifier.children = [left.get_identifier()]
            left = identifier

        if is_identifier(left):
            name = left.get_name()

            # skip CONSTANTS and lower_cased variable names
            if name.isupper() or name.islower():
                return
            
            # first alpha character should be lowercase (no capitalized)
            try:
                non_pep8_name = name.lstrip('_')[0].isupper()
            except:
                non_pep8_name = False

            # heuristic to skip class objects @todo: resolution of variables
            if non_pep8_name:
                stripped = name.lstrip('_')  # allow 'private' marker
                if stripped.lower().endswith('class') and not '_' in stripped:
                    return

                right = assig.get_right_expression()
                if is_identifier(right):
                    rname = right.get_name()                
                    rname = rname.lstrip('_')
                    cond1 = '_' in rname
                    cond2 = rname[0].isupper()
                    cond3 = name.endswith(rname)

                    if not cond1 and cond2 and cond3:
                        return

            # we allow acronyms
            fragments = name.split('_')
            for fragment in fragments:
                if not fragment:
                    continue
                
                if not (fragment.isupper() or fragment.islower()):
                    non_pep8_name = True

            if non_pep8_name:
                self.get_current_symbol().add_violation(self.rule_name_for['variable'],
                                                        left)
            
    @staticmethod
    def is_bad_function(name):
        """
        return True if the first alphanumeric fragment
        of a name is capitalized
        """
        fragments = name.split('_')
        for fragment in fragments:
            if not fragment:
                continue
            return any(letter.isupper() for letter in fragment)

    @staticmethod
    def is_bad_class(name):
        # @toConsider: classes named with double underscore
        if '_' in name[1:]:
            return True

        first_letter = name[0]
        return first_letter.islower()

    def start_Function(self, ast):
        super().start_Function(ast)
        name = ast.get_name()
        if self.is_bad_function(name):
            token = next(token for token in ast.get_children()
                                if token.text == name)

            bookmark = _AstPositions(token.get_begin_line(),
                                token.get_begin_column(),
                                token.get_end_line(),
                                token.get_end_column())

            self.get_current_symbol().add_violation(self.rule_name_for['function'], bookmark)
            
    def start_Class(self, ast):
        super().start_Class(ast)
        name = ast.get_name()
        if self.is_bad_class(name):
            token = next(token for token in ast.get_children()
                                if token.text == name)

            # if __call__ defined, probably instance
            # to be used as a function
            class_object = self.get_current_symbol()

            for method_name in class_object.get_functions():
                if method_name == "__call__":
                    return

            inheritance = class_object.get_inheritance()
            for reference in inheritance:
                ancestors = reference.get_resolutions()
                for ancestor in ancestors:
                    for method_name in ancestor.get_functions():
                        if method_name == "__call__":
                            return

            bookmark = _AstPositions(token.get_begin_line(),
                                token.get_begin_column(),
                                token.get_end_line(),
                                token.get_end_column())

            self.get_current_symbol().add_violation(self.rule_name_for['class'], bookmark)

            
class AvoidUsingGlobalStatement(QualityRule):
    """
    Raise violation if a global statement is found.
    """
    rulename = 'CAST_Python_Rule.AvoidUsingGlobalStatement'

    def start_Global(self, ast_global):
        self.get_current_symbol().add_violation(self.rulename, ast_global)
    
class AvoidSuperClassKnowingSubClass(QualityRule):
    """
    Raise violation if a superclass knowing a subclass.
    """

    rulename = 'CAST_Python_ClassRule.AvoidSuperClassKnowingSubClass'

    def __init__(self, module):
        super().__init__(module)
        self._classname = None

    def _check_violation(self, _class):

        if not isinstance(_class, Class):
            return False

        inheritance_class = _class.get_inheritance()

        for _element in inheritance_class:
            if _element.get_name() == self._classname:
                return True
            else:
                resolutions = _element.get_resolutions()
                if len(resolutions) > 0:
                    current_class = resolutions[0]
                    res = self._check_violation(current_class)
                    if res:
                        return res
        return False

    def start_Identifier(self, identifier):

        resolutions = identifier.get_resolutions()
        for obj in resolutions:
            if self._check_violation(obj):
                self.get_current_class().add_violation(self.rulename, identifier)

    def start_Class(self, _ast_class):
        super().start_Class(_ast_class)
        self._classname = _ast_class.get_name()
