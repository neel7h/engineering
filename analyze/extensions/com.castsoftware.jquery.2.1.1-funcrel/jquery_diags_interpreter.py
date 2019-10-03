
def get_assignment_right_operand(resolution):
    try:
        parentCallee = resolution.callee.parent
        if not parentCallee.is_assignment():
            return None
        rightOperand = parentCallee.get_right_operand()
        return rightOperand
    except:
        return None
    
### see if, in statement v.f(); v is resolved as a $ call (ex: var v = $('');)
def is_variable_pointing_to_dollar_call(callPart):
    
    if get_dollar_call_resolution(callPart):
        return True
    return False

def get_dollar_call_resolution(callPart):
    
    v = callPart.identifier_call
    if not v.get_resolutions():
        if v.get_name() == '$':
            return callPart
        
        return None
    
    for resolution in v.get_resolutions():
        rightOperand = get_assignment_right_operand(resolution)
        if rightOperand and rightOperand.is_function_call() and rightOperand.get_function_call_parts()[0].get_name() == '$':
            return rightOperand.get_function_call_parts()[0]
        
    return None

class JQueryDiagsInterpreter:
            
    def __init__(self, violations, file, jqueryInterpreter):

        self.file = file
        self.violations = violations
        self.jqueryInterpreter = jqueryInterpreter
        self.parsingResults = jqueryInterpreter.parsingResults
        self.jqueryMaxFrameworkVersion = jqueryInterpreter.parsingResults.maxFrameworkVersion['jquery']

    def get_current_context(self):
        return self.jqueryInterpreter.current_context
    
    def end_function(self):
        
        services = []
        currentContext = self.get_current_context()
        for _, ajaxCall in currentContext.ajaxAssignments.items():
            if ajaxCall.has_success_callback and ajaxCall.has_failure_callback:
                services.append(ajaxCall.service)
            else:
                if not ajaxCall.service in currentContext.ajax_calls:
                    services.append(ajaxCall.service)
                    if self.jqueryMaxFrameworkVersion > 0:
                        if self.jqueryMaxFrameworkVersion < 3:
                            self.violations.add_ajax_without_callbacks_violation(ajaxCall.ajaxCall.create_bookmark(self.file))
                        else:
                            self.violations.add_ajax_without_callbacks_jquery3_violation(ajaxCall.ajaxCall.create_bookmark(self.file))
        
        for service in currentContext.ajax_calls:
            if service in services:
                continue
            if service.ast.get_name() in ['sjax', 'syncGet', 'syncPost', 'syncGetJSON', 'syncGetText']:
                continue
            if ( not service.successCallbackPresent or not service.errorCallbackPresent ) and not service.completeCallbackPresent:
                if self.jqueryMaxFrameworkVersion > 0:
                    if self.jqueryMaxFrameworkVersion < 3:
                        self.violations.add_ajax_without_callbacks_violation(service.ast.create_bookmark(self.file))
                    else:
                        self.violations.add_ajax_without_callbacks_jquery3_violation(service.ast.create_bookmark(self.file))
                else:   # no jquery version detected
                    self.violations.add_ajax_without_callbacks_violation(service.ast.create_bookmark(self.file))
            
    def start_function_call(self, fcall):
        
        firstCallpart = fcall.get_function_call_parts()[0]
        prefix = firstCallpart.identifier_call.get_prefix()
        
        isVarPointingToDollarCall = False
        dollarCallPart = None
        
        if prefix:
            dollarCallPart = get_dollar_call_resolution(firstCallpart)
            if dollarCallPart:
                isVarPointingToDollarCall = True
        else:
            if firstCallpart.get_name() == '$':
                isVarPointingToDollarCall = True
                dollarCallPart = firstCallpart
            else:
                return
        
        nbCallParts = len(fcall.get_function_call_parts())
        lastCallPart = fcall.get_function_call_parts()[-1]
        lastCallPartPrefix = lastCallPart.identifier_call.get_prefix()
        
        if nbCallParts >= 2 or prefix:   # $(some_string).something()
            if isVarPointingToDollarCall and not prefix:    # call to $('...').something(...)
                try:
                    if nbCallParts >= 2:
                        firstCallPartParameter = firstCallpart.get_parameters()[0]
                        if not firstCallPartParameter.get_text().startswith('#'):
                            self.violations.add_use_of_uncached_object_violation(fcall.create_bookmark(self.file))
                except:
                    pass
            if isVarPointingToDollarCall and lastCallPart.get_name() == 'css':    # call to $('...').css(...)
                try:
                    if nbCallParts >= 2:
                        firstCallPartParameter = firstCallpart.get_parameters()[0]
                        if not firstCallPartParameter.get_text().startswith('#'):
                            self.violations.add_use_of_css_violation(fcall.create_bookmark(self.file))
                    else:
                        prefixResols = firstCallpart.identifier_call.get_resolutions()
                        if prefixResols:
                            for prefixResol in prefixResols:
                                rightOperand = get_assignment_right_operand(prefixResol)
                                if rightOperand and rightOperand.is_function_call():
                                    fcallPart = rightOperand.get_function_call_parts()[0]
                                    if fcallPart.get_name() == '$':
                                        params = fcallPart.get_parameters()
                                        if params and not params[0].get_text().startswith('#'):
                                            self.violations.add_use_of_css_violation(lastCallPart.create_bookmark(self.file))
                                            break
                                    return True
                except:
                    pass
            if firstCallpart.get_fullname() == '$.cookie':
                self.violations.add_use_of_jquery_cookie_violation(fcall.create_bookmark(self.file))

        if isVarPointingToDollarCall and lastCallPart.get_name() in [ 'andSelf', 'die', 'live', 'load', 'size', 'toggle', 'unload', 'selector', 'context' ]:
            self.violations.add_use_of_deprecated_methods_violation(fcall.create_bookmark(self.file), lastCallPart.get_name())
        elif lastCallPartPrefix and lastCallPart.get_name() == 'sub' and prefix in [ 'jQuery', '$' ]:
            self.violations.add_use_of_deprecated_methods_violation(fcall.create_bookmark(self.file), lastCallPart.get_name())
        elif lastCallPart.get_name() == 'error' and prefix == '$':  # $.ajax(...).error(...)
            self.violations.add_use_of_deprecated_methods_violation(lastCallPart.create_bookmark(self.file), lastCallPart.get_name())
        elif isVarPointingToDollarCall and lastCallPart.get_name() in [ 'after', 'append' ]:
            self.parsingResults.appendOrAfter.append(lastCallPart)
        elif isVarPointingToDollarCall and lastCallPart.get_name() == 'attr':
            self.parsingResults.attr.append(lastCallPart)
        elif isVarPointingToDollarCall and lastCallPart.get_name() == 'dialog':
            self.parsingResults.dialog.append(lastCallPart)
        elif isVarPointingToDollarCall and lastCallPart.get_name() == 'tooltip':
            self.parsingResults.tooltip.append(lastCallPart)
        elif isVarPointingToDollarCall and lastCallPart.get_name() == 'html':
            # violation must be triggered only if parameter contains html tags
            if dollarCallPart:
                params = dollarCallPart.get_parameters()
                if params:
                    param = params[0]
                    try:
                        evs = param.evaluate()
                        for ev in evs:
                            if '<' in ev: 
                                self.parsingResults.html.append(lastCallPart)
                    except:
                        pass
        elif isVarPointingToDollarCall and nbCallParts == 1 and len(firstCallpart.get_parameters()) >= 1:
            firstCallPartParameter = firstCallpart.get_parameters()[0]
            if firstCallPartParameter.is_identifier() and firstCallPartParameter.get_fullname() == 'location.hash':
                self.parsingResults.locationHash.append(fcall)
            
    def add_event_selector(self, handler):

        if handler.is_function():
            self.violations.add_use_of_anonymous_function_for_event_violation(handler.create_bookmark(self.file))
            
    def add_dollar_call(self, text, ast):
        if text.startswith('div.'):
            self.violations.add_element_type_usage_violation(ast.create_bookmark(self.file)) 
        elif text.startswith('#'):  # $("#products div.id")
            v = text.split(' ')
            if len(v) > 1:
                if v[1].startswith('div.'):
                    self.violations.add_id_child_nested_selector_without_find_violation(ast.create_bookmark(self.file)) 
        if ':' in text:
            stringsToCheck = (':checkbox', ':file', ':image', ':password', ':radio', ':reset', ':text')
            if any(ext in text for ext in stringsToCheck):
                self.violations.add_use_type_to_select_elements_by_type_violation(ast.create_bookmark(self.file)) 
        if '> *' in text or text.startswith(':') or text.startswith('*:'):
            # $( ".buttons > *" ) or $( ":radio" ) or $( "*:radio" )
            self.violations.add_use_of_universal_selector_violation(ast.create_bookmark(self.file))
        
    def add_identifier(self, identifier):
        
        if not identifier.get_prefix_internal():
            return
        
        if identifier.get_name() in [ 'context', 'selector' ] and identifier.prefix.startswith('$'):
            self.violations.add_use_of_deprecated_methods_violation(identifier.create_bookmark(self.file), identifier.get_name())
        elif identifier.get_name() in [ 'boxModel', 'browser', 'support' ] and identifier.prefix in [ 'jQuery', '$' ]:
            self.violations.add_use_of_deprecated_methods_violation(identifier.create_bookmark(self.file), identifier.get_name())
        
    def add_dialog_call(self, callPart):
                            
        params = callPart.get_parameters()
        if len(params) >= 1:
            param = params[0]
            if param.is_object_value():
                self.parsingResults.containsJQueryDialog = True
                closeText = param.get_item('closeText')
                if closeText:
                    self.parsingResults.dialogWithCloseText.append(closeText)
        