from javascript_parser.javascript_diags_interpreter import JavascriptDiagsInterpreter

# Parsing of AST to create diags. It is launched file by file after full parsing.

def process_diags(jsContent, file, violations, globalClassesByName, firstRow, firstCol):
    
    interpreter = JavascriptDiagsInterpreter(file, violations, globalClassesByName)
    interpreter.start_js_content(jsContent)
    for statement in jsContent.get_statements():
        parse_ast(interpreter, statement)
    interpreter.end_js_content()
    
def parse_ast(interpreter, ast):
    
    if not ast:
        return
    
    try:
        if ast.is_function():
            interpreter.start_function(ast)
        elif ast.is_loop():
            interpreter.start_loop(ast)
            if ast.is_for_block():
                parse_for_loop(interpreter, ast)
                interpreter.end_loop()
                return
        elif ast.is_function_call():
            interpreter.start_function_call(ast)
        elif ast.is_function_call_part():
            interpreter.start_function_call_part(ast.identifier_call, ast)
        elif ast.is_identifier():
            interpreter.start_identifier(ast)
        elif ast.is_class():
            interpreter.start_class(ast)
        elif ast.is_try_catch_block():
            interpreter.start_try_catch_block(ast)
        elif ast.is_string():
            interpreter.start_string(ast)
        elif ast.is_assignment():
            interpreter.start_assignment(ast)
        elif ast.is_binary_expression():
            interpreter.start_binary_expression(ast)
        elif ast.is_object_value():
            interpreter.start_object_value(ast)
            
        for child in ast.get_children():
            parse_ast(interpreter, child)
    
        if ast.is_function():
            interpreter.end_function()
        elif ast.is_loop():
            interpreter.end_loop()
        elif ast.is_function_call_part():
            interpreter.end_function_call_part()
        elif ast.is_new_expression():
            interpreter.end_any_expression(ast)
        elif ast.is_break_statement():
            interpreter.end_any_statement(ast)
        elif ast.is_return_statement():
            interpreter.end_any_statement(ast)
        elif ast.is_delete_statement():
            interpreter.end_delete_statement(ast)
        elif ast.is_switch_block():
            interpreter.end_switch_block(ast)
        elif ast.is_class():
            interpreter.end_class()
        elif ast.is_try_catch_block():
            interpreter.end_try_catch_block()

    except Exception as e:
        pass
    
def parse_for_loop(interpreter, ast):

    for startExpression in ast.startExpressions:
        parse_ast(interpreter, startExpression)
    interpreter.start_termination_expression()
    parse_ast(interpreter, ast.terminationExpression)
    interpreter.end_termination_expression()
    parse_ast(interpreter, ast.forwardExpression)
    parse_ast(interpreter, ast.block)
