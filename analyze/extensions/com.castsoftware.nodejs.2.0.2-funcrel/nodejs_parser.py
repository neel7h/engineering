import traceback
from cast.analysers import create_link, log, CustomObject, ExternalObject
from nodejs_interpreter import NodeJSInterpreter

def analyse(jsContent, config, analysisContext, parsingResults, file = None, versions = None):

    interpreter = NodeJSInterpreter(file, config, analysisContext, parsingResults, versions)
    interpreter.start_source_code(jsContent)
    parse_statements(interpreter, jsContent, file)
    interpreter.finalize()

def parse_statements(interpreter, jsContent, file = None):

    for statement in jsContent.get_statements():
        try:
            parse_statement(interpreter, jsContent, statement, file)
        except:
            try:
                log.warning('NODEJS-001 Internal issue in ' + str(file.get_path()))
            except:
                pass
            log.debug('Internal issue ' + str(traceback.format_exc()))
            pass

def is_assignment(token):
    try:
        return token.is_assignment()
    except:
        return False
    
def is_loop(statement):
    
    try:
        if statement.is_loop():    
            return True
        return False
    except:
        return False

def parse_statement(interpreter, jsContent, statement, file = None):

    if not statement:
        return
    
    try:
        if not statement.is_ast_token():
            return
    except:
        return
    
    if statement.is_function():
        interpreter.start_function(statement)
    
    elif statement.is_class():
        interpreter.start_class(statement)
        
    elif statement.is_var_declaration():
        for element in statement.elements:
            if is_assignment(element):
                leftOperandName = None
                try:
                    leftOperandName = element.get_left_operand().name
                except:
                    pass
                if leftOperandName:
                    interpreter.add_global_variable_declaration(element.get_left_operand().name, element)
                    rightOperand = element.get_right_operand()
                    if rightOperand.is_function_call() and rightOperand.is_require():
                        interpreter.add_require(element)
        
    elif statement.is_function_call():
        fcall = statement
        interpreter.start_function_call(fcall)

    elif statement.is_assignment():
        interpreter.start_assignment(statement)
        
    elif statement.is_addition_expression():
        interpreter.start_addition_expression(statement)
        
    elif is_loop(statement):
        interpreter.start_loop()

    for child in statement.get_children():
        try:
            parse_statement(interpreter, jsContent, child, file)
        except:
            try:
                log.warning('NODEJS-001 Internal issue in ' + str(file.get_path()))
            except:
                pass
            log.debug('Internal issue ' + str(traceback.format_exc()))
            pass

    if statement.is_function():
        interpreter.end_function()
    elif statement.is_class():
        interpreter.end_class()
    elif statement.is_function_call():
        interpreter.end_function_call()
    elif is_loop(statement):
        interpreter.end_loop()


def create_link_nodeJS(linkType, caller, callee, bm=None):

    try:
        clr = caller
        cle = callee
        try:
            if not isinstance(clr, CustomObject):
                if clr.is_js_content():
                    clr = clr.create_javascript_initialisation()
                else:
                    clr = clr.get_kb_object()
        except:
            clr = clr.get_kb_object()
        try:
            if not isinstance(cle, CustomObject) and not isinstance(cle, ExternalObject):
                if cle.is_js_content():
                    cle = clr.create_javascript_initialisation()
                else:
                    cle = clr.get_kb_object()
        except:
            if hasattr(cle, 'get_kb_object'):
                cle = cle.get_kb_object()

        if bm:
            create_link(linkType, clr, cle, bm)
        else:
            create_link(linkType, clr, cle)
    except:
        try:
            log.debug('Internal issue when creating link: ' + str(traceback.format_exc()))
            log.debug('linkType = ' + str(linkType))
            log.debug('caller = ' + str(clr))
            log.debug('callee = ' + str(cle))
            log.debug('bookmark = ' + str(bm))
        except:
            pass
    
