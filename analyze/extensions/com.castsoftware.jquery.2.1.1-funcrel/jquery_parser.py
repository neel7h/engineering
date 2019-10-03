import os
import traceback


import cast.analysers.ua
from collections import OrderedDict
from cast.analysers import create_link
from jquery_interpreter import JQueryInterpreter

g_events = ['click', 'dblclick', 'mouseenter', 'mouseleave', 'mousedown', 'mouseup', 'hover', 'keypress', 'keydown', 'keyup', 'submit', 'change', 'focus', 'blur', 'load', 'resize', 'scroll', 'unload']

def analyse(jsContent, file = None, parsingResults = None):

    interpreter = JQueryInterpreter(file, parsingResults, jsContent)
    parse_statements(interpreter, jsContent, file)

def parse_statements(interpreter, jsContent, file = None):

    for statement in jsContent.get_statements():
        try:
            parse_element(interpreter, jsContent, statement, file)
        except Exception as e:
            cast.analysers.log.debug('Internal issue : ' + str(e))
            cast.analysers.log.debug(traceback.format_exc())

def is_function(statement):
    try:
        return statement.is_function()
    except:
        return False

def is_assignment(statement):
    try:
        return statement.is_assignment()
    except:
        return False

def is_var_declaration(statement):
    try:
        return statement.is_var_declaration()
    except:
        return False

def is_function_call_part(statement):
    try:
        return statement.is_function_call_part()
    except:
        return False

def is_function_call(statement):
    try:
        return statement.is_function_call()
    except:
        return False

def is_identifier(statement):
    try:
        return statement.is_identifier()
    except:
        return False
    
def parse_element(interpreter, jsContent, statement, file = None):

    isAjaxCall = False
    isSelectorCall = False
    
    if not statement:
        return

    if is_loop(statement):
        interpreter.start_loop()
        
    if is_function(statement):
        interpreter.start_function(statement)
        
    elif is_assignment(statement) and not is_var_declaration(statement):
        interpreter.start_assignment(statement.get_left_operand(), statement.get_right_operand())

    elif is_function_call_part(statement):
        
#       Call is $.ajax() or something.prototype.ajax()
        if is_ajax_call(statement):
            callName = statement.identifier_call.get_name()
            if callName in ['syncGet', 'syncGetJSON', 'syncGetText']:
                callName = 'get'
            elif callName == 'syncPost':
                callName = 'post'
            if callName in ['get', 'post']:
                parse_dollar_get_post_call(interpreter, statement, callName)
            elif statement.identifier_call.get_name() in ['getJSON', 'getScript']:
                parse_dollar_getJSON_getScript_call(interpreter, statement, statement.identifier_call.get_name())
            else:
                parse_ajax_call(interpreter, statement)
        elif statement.get_name() == 'then':
            params = statement.get_parameters()
            if len(params) >= 2 and params[0] and params[1]:
                interpreter.add_ajax_success_callback(params[0])
                interpreter.add_ajax_error_callback(params[1])
        elif statement.get_name() == 'done':
            params = statement.get_parameters()
            if len(params) >= 1 and params[0]:
                interpreter.add_ajax_success_callback(params[0], statement.identifier_call)
        elif statement.get_name() == 'fail':
            params = statement.get_parameters()
            if len(params) >= 1 and params[0]:
                interpreter.add_ajax_error_callback(params[0], statement.identifier_call)
        elif statement.get_name() == 'always':
            params = statement.get_parameters()
            if len(params) >= 1 and params[0]:
                interpreter.add_ajax_always_callback(params[0], statement.identifier_call)
#       Call is $()
        elif statement.get_name() == '$':
            if statement.get_parameters():
                param = statement.get_parameters()[0]
                if param.is_string():
                    interpreter.add_dollar_call(param.get_text(), statement)
        elif statement.get_name() == 'bind':
            parse_bind(interpreter, statement)
        elif statement.get_name() == 'delegate':
            parse_delegate(interpreter, statement)
        elif statement.get_name() == 'on':
            parse_on(interpreter, statement)
        elif statement.get_name() == 'dialog':
            parse_dialog(interpreter, statement)
        elif statement.get_name() in g_events:
            parse_event(interpreter, statement.get_name(), statement)
        elif statement.get_name() == 'jQuery':
            interpreter.start_jquery_function_call_part(statement)


#       Call is $.something() or $() or something.prototype.ajax()
        try:
            if statement.prefix_starts_with('$') or statement.get_name() == '$' or statement.get_name() == '$$' or (statement.get_name() == 'ajax' and statement.get_prefix().endswith('prototype')):
                interpreter.is_jquery(True)
        except:
            pass
        
    elif is_function_call(statement):
        interpreter.start_function_call(statement)
        fcall = statement
        callParts = fcall.get_function_call_parts()
        callName = None
        firstCallPart = callParts[0]
        lastCallPart = callParts[-1]
                    
#       Call is $.ajax() or something.prototype.ajax()
        if is_ajax_call(firstCallPart):
            isAjaxCall = True
            interpreter.start_ajax_call(statement)

#       Call is $().ready(handler);
        elif is_ready_call(callParts[0], lastCallPart):
            parse_ready_call(interpreter, jsContent, lastCallPart, file)

#       Call is $().DataTable(...);
        elif is_DataTable_call(callParts[0], lastCallPart):
            parse_DataTable_call(interpreter, jsContent, lastCallPart, file)
        
#       element.bind('click', function () {}); or element.on('click', function () {}); or $('a#progressanchor').click()...
        elif may_be_jquery_bind(statement) or may_be_jquery_on(statement) or may_be_jquery_event(statement) or may_be_jquery_dialog(statement) or may_be_jquery_delegate(statement):
            isSelectorCall = True
            interpreter.start_selector()
            firstCallPart = statement.get_function_call_parts()[0]
            callName = firstCallPart.get_name()
            # $('xxx').on('click', function () {})
            if callName == '$':
                callParams = firstCallPart.get_parameters()
                if callParams:
                    param = callParams[0]
                    if param.is_string():
                        interpreter.set_selector_name(param.get_text())
                    elif param.is_identifier() and param.get_name() == 'document':
                        interpreter.set_selector_name(param.get_name())

    elif is_identifier(statement):
        interpreter.add_identifier(statement)

    for child in statement.get_children():
        try:
            parse_element(interpreter, jsContent, child, file)
        except Exception as e:
            cast.analysers.log.debug('Internal issue : ' + str(e))
            cast.analysers.log.debug(traceback.format_exc())

    if is_loop(statement):
        interpreter.end_loop()

    if is_assignment(statement) and not is_var_declaration(statement):
        interpreter.end_assignment()
    elif is_function(statement):
        interpreter.end_function()
    if isAjaxCall:
        interpreter.end_ajax_call()
    elif isSelectorCall:
        interpreter.end_selector()
    elif is_function_call_part(statement) and statement.get_name() == 'jQuery':
        interpreter.end_jquery_function_call_part(statement)

    if is_function_call(statement):
        interpreter.end_function_call()

def is_loop(statement):
    
    try:
        if statement.is_loop():    
            return True
        return False
    except:
        return False

#       Call is $.ajax() or something.prototype.ajax()
def is_ajax_call(callPart):
    
    callIdent = callPart.identifier_call
    try:
        if callIdent.get_name() in ['ajax', 'get', 'post', 'getJSON', 'getScript', 'sjax', 'syncGet', 'syncPost', 'syncGetJSON', 'syncGetText'] and callIdent.get_prefix_internal() and (callIdent.prefix == '$' or callIdent.prefix.startswith('jQuery') or callIdent.prefix.endswith('prototype')):
            return True
    except:
        return False
    return False

#       Call is $().ready(handler);
def is_ready_call(firstCallPart, lastCallPart):
    
    if firstCallPart == lastCallPart:
        return False
    
    callIdent = lastCallPart.identifier_call
    if callIdent.get_name() != 'ready':
        return False
    
    callIdent = firstCallPart.identifier_call
    if callIdent.get_name() == '$':
        if lastCallPart.parameters and len(lastCallPart.parameters) == 1:
            return True

    return False

#       Call is $().DataTable(...);
def is_DataTable_call(firstCallPart, lastCallPart):
    
    if firstCallPart == lastCallPart:
        return False
    
    callIdent = lastCallPart.identifier_call
    if callIdent.get_name() != 'DataTable':
        return False
    
    callIdent = firstCallPart.identifier_call
    if callIdent.get_name() == '$':
        if lastCallPart.parameters and len(lastCallPart.parameters) == 1:
            return True

    return False

#       Call is $.ajax().done(successHandler);
def is_done_call(firstCallPart):
    
    callIdent = firstCallPart.identifier_call
    if callIdent.get_name() == 'done':
        return True
    return False

#       Call is $.ajax().fail(successHandler);
def is_fail_call(firstCallPart):
    
    callIdent = firstCallPart.identifier_call
    if callIdent.get_name() == 'fail':
        return True
    return False

# element.bind('click', function () {});
def may_be_jquery_bind(fcall):
    
    for callPart in fcall.get_function_call_parts():

        if callPart.get_name() != 'bind':
            continue
        
        params = callPart.get_parameters()
        if not params or len(params) <= 1 or (not params[-1].is_function() and not params[-1].is_identifier()):
            continue
    
        firstParam = params[0]
        if not firstParam.is_string():
            continue
        
        return True

# element.delegate('td', 'click', function () {});
def may_be_jquery_delegate(fcall):
    
    for callPart in fcall.get_function_call_parts():

        if callPart.get_name() == 'require':
            return False

        if callPart.get_name() != 'delegate':
            continue
        
        params = callPart.get_parameters()
        if not params or len(params) <= 2 or (not params[-1].is_function() and not params[-1].is_identifier()):
            continue
    
        typeParam = params[1]
        if not typeParam.is_string():
            continue
        
        return True

# element.on('click', function () {});
def may_be_jquery_on(fcall):
    
    for callPart in fcall.get_function_call_parts():

        if callPart.get_name() == 'require':
            return False

        if callPart.get_name() != 'on':
            continue
        
        params = callPart.get_parameters()
        if not params or len(params) <= 1:
            continue
        
        handler = params[-1]
        
        if not params[-1].is_function():
            if not params[-1].is_function_call():
                continue
            else:
                callPartIdent = params[-1].get_function_call_parts()[0].identifier_call
                if not callPartIdent.get_resolutions():
                    continue
                handler = callPartIdent.resolutions[0].callee
                if not handler.is_function():
                    continue
    
        firstParam = params[0]
        if not firstParam.is_string():
            continue
        
        return True
    return False

# element.dialog({});
def may_be_jquery_dialog(fcall):
    
    for callPart in fcall.get_function_call_parts():

        if callPart.get_name() == 'require':
            return False

        if callPart.get_name() != 'dialog':
            continue
        
        params = callPart.get_parameters()
        if not params:
            continue
        ov = params[0]
        if not ov.is_object_value():
            continue
        
        buttons = ov.get_item('buttons')
        if not buttons or not buttons.is_list():
            continue
    
        return True

# $('a#progressanchor').click(), $('a#progressanchor').dblclick() ... See g_events for complete list
def may_be_jquery_event(fcall):

    for callPart in fcall.get_function_call_parts():

        if callPart.get_name() == 'require':
            return False
        
        if callPart.get_name() not in g_events:
            continue
        
        return True

# Parses $('a#progressanchor').click()
def parse_event(interpreter, eventType, callPart):
    
    parse_selector_prefix(interpreter, callPart)
    
    handler = None
    params = callPart.get_parameters()
    if not params:  # this is a call to an event (ex: $('#loginForm').submit();)
        interpreter.add_event_call(eventType, callPart)
    elif params[0].is_function():
        handler = params[0]
        interpreter.add_event_selector(eventType, handler, callPart)

# prefix is variable in variable.on('click', function () {}), see if variable is resolved as $('xxx')
def parse_selector_prefix(interpreter, callpart):
    
    # var $todoApp = $('#todoapp');
    # var $main = $todoApp.find('#main');
    # var $todoList = $main.find('#todo-list');
    # var list = $todoList;
    # list.on('click', '.destroy', destroy.bind(this));
#     doit renvoyer: #todoapp.#main.#todo-list
#     Idem pour:
    # $todoApp : null,
    # f : function() {
    #     $todoApp = $('#todoapp');
    #     $main = $todoApp.find('#main');
    #     $todoList = $main.find('#todo-list');
    #     list = $todoList;
    #     list.on('click', '.destroy', destroy.bind(this));
    #    }
#     list.on pointe sur "list =", $todoList pointe sur "$todoList ="...
#     On stocke le last assignment par leftOperand resolution
    
    firstAssignment = interpreter.get_first_assignment(callpart.identifier_call)
    paramName = None
    if firstAssignment:
        oldAssignment = firstAssignment
        firstAssignments = []
        while firstAssignment and not firstAssignment.is_function_call():
            if firstAssignment in firstAssignments:
                break
            firstAssignments.append(firstAssignment)
            firstAssignment = interpreter.get_first_assignment(firstAssignment)
            if firstAssignment == oldAssignment:
                break
            oldAssignment = firstAssignment
        if firstAssignment:
            if firstAssignment.is_function_call():
                firstCallPart = firstAssignment.get_function_call_parts()[0]
                if firstCallPart.get_name() == 'require':
                    return
#                 if firstCallPart.get_name() == '$':
                if firstCallPart.get_parameters() and firstCallPart.get_parameters()[0].is_string():
                    if firstCallPart.get_parameters():
                        param = firstCallPart.get_parameters()[0]
                        paramText = param.get_text()
                        if paramName:
                            paramName = paramText + '.' + paramName
                        else:
                            paramName = paramText
                else:
                    lastCallPart = firstAssignment.get_function_call_parts()[-1]
                    name = lastCallPart.get_name()
                    if name == 'find':
                        params = lastCallPart.get_parameters()
                        if params:
                            param = params[0]
                            if param.is_string():
                                if paramName:
                                    paramName = param.get_text() + '.' + paramName
                                else:
                                    paramName = param.get_text()
  
            firstAssignment = interpreter.get_first_assignment(firstAssignment)
      
        if paramName:
            interpreter.set_selector_name(paramName)
    
    if not paramName:
        
        topResolutions = []
        callpart.get_top_resolutions(topResolutions)
        if topResolutions and topResolutions[0].is_function_call():
            bFirst = True
            paramName = None
            for topResolution in topResolutions:
                if bFirst:
                    bFirst = False
                    firstCallPart = topResolution.get_function_call_parts()[0]
                    callParams = firstCallPart.get_parameters()
                    if callParams:
                        param = callParams[0]
                        if param.is_string():
                            paramName = param.get_text()
                elif topResolution.is_function_call():
                    lastCallPart = topResolution.get_function_call_parts()[-1]
                    name = lastCallPart.get_name()
                    if name == 'find':
                        params = lastCallPart.get_parameters()
                        if params:
                            param = params[0]
                            if paramName and param.is_string() and param.get_text():
                                paramName += ( '.' + param.get_text())
            if paramName:
                interpreter.set_selector_name(paramName)
    
# Parses element.bind('click', function () {});
def parse_bind(interpreter, callPart):

    params = callPart.get_parameters()
    if not params or len(params) <= 1 or (not params[-1].is_function() and not params[-1].is_identifier()):
        return
    
    firstParam = params[0]
    if not firstParam.is_string():
        return
    
    parse_selector_prefix(interpreter, callPart)
    
    firstParamText = firstParam.get_text()
    handler = params[-1]
    
    if firstParamText:
        index = firstParamText.rfind('.')
        if index >= 0:
            firstParamText = firstParamText[index + 1:]
            interpreter.add_bind_selector(firstParamText, handler, callPart)
        else:
            interpreter.add_bind_selector(firstParamText, handler, callPart)
    
# Parses element.delegate('td', 'click', function () {});
def parse_delegate(interpreter, callPart):

    params = callPart.get_parameters()
    if not params or len(params) <= 2 or (not params[-1].is_function() and not params[-1].is_identifier()):
        return
    
    eventTypeParam = params[1]
    if not eventTypeParam.is_string():
        return
    
    parse_selector_prefix(interpreter, callPart)
    
    params = callPart.get_parameters()
    eventTypeParam = params[1]
    
    eventTypeParamText = eventTypeParam.get_text()
    handler = params[-1]
    
    if eventTypeParamText:
        index = eventTypeParamText.rfind('.')
        if index >= 0:
            eventTypeParamText = eventTypeParamText[index + 1:]
            interpreter.add_delegate_selector(eventTypeParamText, handler, callPart)
        else:
            interpreter.add_delegate_selector(eventTypeParamText, handler, callPart)

# Parses element.on('click', function () {});
def parse_on(interpreter, callPart):
    
    parse_selector_prefix(interpreter, callPart)

    params = callPart.get_parameters()
    handler = params[-1]
    firstParam = params[0]
    firstParamText = firstParam.get_text()
    if firstParamText:
        index = firstParamText.rfind('.')
        if index >= 0:
            firstParamText = firstParamText[index + 1:]
            interpreter.add_on_selector(firstParamText, handler, callPart)
        else:
            interpreter.add_on_selector(firstParamText, handler, callPart)

# Parses element.dialog({
#    buttons : [{
#      click : function() {}
#    }
#     ]});
def parse_dialog(interpreter, callPart):
    
    parse_selector_prefix(interpreter, callPart)
    
    params = callPart.get_parameters()
    if not params:
        return
    
    interpreter.add_dialog_call(callPart)

    ov = params[0]
    if not ov.is_object_value():
        return
    
    buttonsItems = ov.get_item('buttons')
    if not buttonsItems or not buttonsItems.is_list():
        return
    
    for buttonItem in buttonsItems.get_values():
        if not buttonItem.is_object_value():
            continue
        clickItemFunction = buttonItem.get_item('click')
        if not clickItemFunction:
            continue
        
        handler = clickItemFunction
                    
        if not handler:
            continue

        interpreter.add_dialog_selector('dialog.click', handler, ov)

def get_first_object_value_child(obj):
    if obj.is_object_value():
        return obj
    
    ov = None
    for c in obj.get_children():
        if c.is_object_value():
            ov = c
            break
        else:
            ov = get_first_object_value_child(c)
            if ov:
                break
    return ov
        
# Parses $.ajax() or something.prototype.ajax()
def parse_ajax_call(interpreter, callPart):
    
    lastParam = callPart.get_parameters()[-1]
    
    ov = get_first_object_value_child(lastParam)
    
    datatypeExists = True

    if ov:
    
        typeItem = ov.get_item('type')
        if not typeItem:
            typeItem = ov.get_item('method')
        if not typeItem or not typeItem.is_string():
            typeName = 'GET'
        else:
            typeName = typeItem.get_name().upper()
        
        urlItem = ov.get_item('url')
        if not urlItem and lastParam != callPart.get_parameters()[0]:
            urlItem = callPart.get_parameters()[0]
            typeName = 'POST'

        datatypeItem = ov.get_item('dataType')
        if not datatypeItem:
            datatypeExists = False
    
        successFunction = ov.get_item('success')
        if not successFunction:
            successFunction = ov.get_item('onSuccess')
        
        errorFunction = ov.get_item('error')
        if not errorFunction:
            errorFunction = ov.get_item('onError')
        if not errorFunction:
            errorFunction = ov.get_item('failure')
        if not errorFunction:
            errorFunction = ov.get_item('onFailure')

        completeFunction = ov.get_item('complete')
        if not completeFunction:
            completeFunction = ov.get_item('onComplete')
        
    else:
#         Global.prototype.ajax("POST", "modifyUser.html", param)

        firstParam = callPart.get_parameters()[0]
        if len(callPart.get_parameters()) < 2:
            return None
        if not firstParam.is_string():
            return None
        typeName = firstParam.get_text().upper()
        if not typeName in ['GET', 'PUT', 'POST']:
            return None
        urlItem = callPart.get_parameters()[1]
        successFunction = None
        errorFunction = None
        completeFunction = None
        
    services = interpreter.add_ajax_call(typeName, typeName, urlItem, successFunction, errorFunction, completeFunction, callPart, True, datatypeExists)
    return services
        
# Parses $.get() or $.post()
def parse_dollar_get_post_call(interpreter, callPart, fcallName):
    
    typeName = fcallName.upper()
    urlItem = callPart.get_parameters()[0]
    func = callPart.get_parameters()[-1]
    
    # Last param is False because if True, callLinks to callbacks will be duplicated beacause html extension
    # already creates these links because methodCall has get and post for names.
    services = interpreter.add_ajax_call(typeName, typeName, urlItem, func, None, None, callPart, False)
    return services
        
# Parses $.getJSON() or $.getScript()
def parse_dollar_getJSON_getScript_call(interpreter, callPart, fcallName):
    
    urlItem = callPart.get_parameters()[0]
    params = callPart.get_parameters()
    if len(params) >= 2:
        func = params[1]
        services = interpreter.add_ajax_call('GET', 'GET', urlItem, func, None, None, callPart, False)
        return services
    return []

# Parses $().ready(successHandler);
def parse_ready_call(interpreter, jsContent, callPart, file):
    
#     paramIdent = callPart.get_parameters()[0]
    
    interpreter.start_jquery_document_ready_call(callPart);
    
#     if paramIdent.resolutions:
#         resol = paramIdent.resolutions[0]
#         if resol.callee.is_function() and file:
#             for htmlContent in jsContent.get_html_calling_files():
#                 create_link('callLink', htmlContent.htmlSourceCode, resol.callee.kbSymbol.kbObject, htmlContent.has_js_file(file.get_path()).create_bookmark(htmlContent.file))

    interpreter.end_jquery_document_ready_call();

# Parses $().DataTable({
#         "ajax":
#         {
#             "url": getCompanies,
#             "data": function (d) {
#             },
#             "dataSrc": function (result) {
#             },
#             "error":   function(jqXHR, textStatus, errorThrown) { callback(); }
#         },
#        
#         "columnDefs":
#         [
#             {
#                 "targets": 7,
#                 "data": "",
#                 "render": function (data, type, full, meta) {
#                     return '<a href="' + getScoreDetails + full[0] + '">Get Score</a>';
#                 }
#             }
#         ],
#        "initComplete": function ()
#         {
#         }
#        });
def parse_DataTable_call(interpreter, jsContent, callPart, file):
    
    ov = callPart.get_parameters()[0]
    if not ov.is_object_value():
        return
    
    typeName = 'GET'
    urlItem = None
    errorFunc = None
    ovAjax = ov.get_item('ajax')
    if ovAjax and ovAjax.is_object_value():
        
        urlItem = ovAjax.get_item('url')
        dataFunc = ovAjax.get_item('data')
        if dataFunc and dataFunc.is_function():
            interpreter.add_link_suspension('callLink', dataFunc)
        dataSrcFunc = ovAjax.get_item('dataSrc')
        if dataSrcFunc and dataSrcFunc.is_function():
            interpreter.add_link_suspension('callLink', dataSrcFunc)
        errorFunc = ovAjax.get_item('error')

        lstColumnDefs = ov.get_item('columnDefs')
        if lstColumnDefs and lstColumnDefs.is_list():
            for elt in lstColumnDefs.get_values():
                if elt.is_object_value():
                    renderFunc = elt.get_item('render')
                    if renderFunc and renderFunc.is_function():
                        interpreter.add_link_suspension('callLink', renderFunc)

        initCompleteFunc = ov.get_item('initComplete')
        if initCompleteFunc and initCompleteFunc.is_function():
            interpreter.add_link_suspension('callLink', initCompleteFunc)
        
    if urlItem:
        interpreter.add_ajax_call(typeName, typeName, urlItem, None, errorFunc, None, callPart)
