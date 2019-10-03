import cast.analysers
from symbols import Event, ResourceService, LinkToEventSuspension, LinkSuspension
from jquery_diags_interpreter import JQueryDiagsInterpreter
from collections import OrderedDict
import traceback

class AjaxCall:
    def __init__(self, ajaxCall, service, hasSuccessCallback = False, hasFailureCallback = False, hasAlwaysCallback = False):
        self.has_success_callback = hasSuccessCallback
        self.has_failure_callback = hasFailureCallback
        self.has_always_callback = hasAlwaysCallback
        self.ajaxCall = ajaxCall
        self.service = service

def evaluate_url(urlItem, astCalls):
    try:
        return urlItem.get_uri_evaluation(urlItem, '{}', astCalls)
    except:
        cast.analysers.log.debug(str(traceback.format_exc()))

class Context:
    def __init__(self, previousContext, statement = None):
        self.previous_context = previousContext
        self.statement = statement
    def is_function_context(self):
        return False
    def is_assignment_context(self):
        return False
    def is_ajax_context(self):
        return False
    def is_selector_context(self):
        return False
    def is_function_call_context(self):
        return False
    def get_current_function(self):
        if self.previous_context:
            return self.previous_context.get_current_function()
        return self.statement
    def get_last_function_context(self):
        if self.previous_context:
            return self.previous_context.get_last_function_context()
        else:
            return None
    def get_ajax_assignment(self, identifier):
        if self.previous_context:
            return self.previous_context.get_ajax_assignment(identifier)
        return None
    
    def get_left_operand_resolutions(self):
        return None
    
class FunctionContext(Context):
    def __init__(self, previousContext, function, is_jquery_init = False):
        Context.__init__(self, previousContext, function)
        self.current_function = function
        self.ajaxAssignments = {}
        self.ajax_calls = []
        self.is_jquery_init = is_jquery_init    # True for jQuery(function ($) {});
    def is_function_context(self):
        return True
    def get_current_function(self):
        return self.current_function
    def get_last_function_context(self):
        return self
    def get_ajax_assignment(self, identifier):
        if identifier in self.ajaxAssignments:
            return self.ajaxAssignments[identifier]
        if self.previous_context:
            return self.previous_context.get_ajax_assignment(identifier)
        return None
    
class FunctionCallContext(Context):
    def __init__(self, previousContext, statement = None):
        Context.__init__(self, previousContext, statement)
        self.services = None

    def is_function_call_context(self):
        return True

    def is_ajax_context(self):
        if self.services:
            return True
        return False
    
class AssignmentContext(Context):
    def __init__(self, previousContext, statement, leftOperand, rightOperand):
        Context.__init__(self, previousContext, statement)
        self.left_operand = leftOperand
        self.right_operand = rightOperand

    def is_assignment_context(self):
        return True

    # In case of following example:
    # dm.doc.last.filter_doc = $('#doc_last_used .filterdoc');
    #
    # it returns the resolution of left operand to var identifier
    def get_left_operand_resolutions(self):
        
        try:
            if self.left_operand.get_resolutions():
                return self.left_operand.get_resolutions()
            else:
                return [ self.left_operand ]
        except:
            return None
        
class SelectorContext(Context):
    def __init__(self, previousContext, statement = None):
        Context.__init__(self, previousContext, statement)
        self.selector_name = None

    def is_selector_context(self):
        return True

class JQueryInterpreter:
            
    def __init__(self, file, parsingResults, jsContent):

        self.file = file
        self.current_filename = None
        if file:
            self.current_filename = file.get_path()
        self.events = parsingResults.events
        self.ajax_calls = parsingResults.ajax_calls
        self.current_event = None
        self.current_context = None
        self.stack_contexts = []
        self.calls_to_events_suspensions = parsingResults.calls_to_events_suspensions
        self.links_suspensions = parsingResults.links_suspensions
        self.parsingResults = parsingResults
        self.loopDepth = 0
        self.violations = parsingResults.violations
        self.parsingResults.containsJQuery = False
        self.push_context(Context(None, jsContent))
        self.jquery_init_call_depth = 0 # incremented/decremented with jQuery(function ($) {}) calls start/end;
        self.diagsInterpreter = JQueryDiagsInterpreter(self.violations, file, self)
        self.lastAssignmentsByLeftOperandResolution = {}

    def push_context(self, context):
        self.stack_contexts.append(context)
        self.current_context = context

    def pop_context(self):
        if not self.stack_contexts:
            self.current_context = None
            return
        
        self.stack_contexts.pop()
        if self.stack_contexts:
            self.current_context = self.stack_contexts[-1]
        else:
            self.current_context = None

    def get_current_function(self):
        if not self.current_context:
            return None
        return self.current_context.get_current_function()

    def get_current_function_context(self):
        if not self.current_context:
            return None
        return self.current_context.get_last_function_context()
        
    def start_function(self, function):
        self.push_context(FunctionContext(self.current_context, function))

    def end_function(self):
        
        self.diagsInterpreter.end_function()
        self.pop_context()
        
    def start_function_call(self, fcall):
        
        self.push_context(FunctionCallContext(self.current_context, fcall))
        self.diagsInterpreter.start_function_call(fcall)
        
    def end_function_call(self):
        fcall = self.current_context.statement
        fcallparts = fcall.get_function_call_parts()
        # $("#ExcludedReportsForm").attr("action", "generateReport.do");
        # We suppose the type is POST
        # the type should be found in html file:
        # ex: <Form action="#" type="POST" id="ExcludedReportsForm" >
        # but we do not resolve for the moment ids between html files and js files
        if len(fcallparts) >= 2:
            lastCallPart = fcallparts[-1]
            if lastCallPart.identifier_call.get_name() == 'attr':
                params = lastCallPart.get_parameters()
                try:
                    if len(params) >= 2 and params[0].is_string() and params[0].get_name() == 'action':
                        uri = params[1]
                        astCallsInitial = []
                        try:
                            values = evaluate_url(uri, astCallsInitial)
                        except:
                            values = []
                        if not values:
                            self.ajax_calls.append(ResourceService('POST', 'POST', None, uri, self.get_current_function()))
                        else:
                            urls = []
                            j = 0
                            for value in values:
                                if not value in urls:
                                    v = value.replace('!', '/')
                                    service = ResourceService('POST', 'POST', v, uri, self.get_current_function())
                                    self.ajax_calls.append(service)
                                    urls.append(value)
                                    service.astCall = astCallsInitial[j]
                                j += 1
                except:
                    pass 
        self.pop_context()

    def start_loop(self):
        self.loopDepth += 1

    def end_loop(self):
        self.loopDepth -= 1
        
# Parses $('a#progressanchor').click()
    def add_event_selector(self, eventType, handler, ast):
        
        if not self.current_context.is_selector_context():
            return
        if not self.current_context.selector_name:
            return
        
        self.diagsInterpreter.add_event_selector(handler)

        if handler.is_function():
            self.current_event = Event(self.current_context.selector_name, handler, eventType, ast)
        elif handler.is_identifier():
            if handler.get_resolutions():
                self.current_event = Event(self.current_context.selector_name, handler.resolutions[0].callee, eventType, ast)
            else:
                self.current_event = Event(self.current_context.selector_name, handler, eventType, ast)
        elif handler.is_function_call():
            callPartIdent = handler.get_function_call_parts()[0].identifier_call
            if callPartIdent.get_resolutions():
                handler = callPartIdent.resolutions[0].callee
                self.current_event = Event(self.current_context.selector_name, handler, eventType, ast)
            else:
                return
        else:
            self.current_event = Event(self.current_context.selector_name, handler, eventType, ast)
            
        self.events.append(self.current_event)
        self.current_event = None
    
# Parses element.bind('click', function () {});
    def add_bind_selector(self, eventType, handler, ast):
        self.add_event_selector(eventType, handler, ast)
    
# Parses element.delegate('td', 'click', function () {});
    def add_delegate_selector(self, eventType, handler, ast):
        self.add_event_selector(eventType, handler, ast)
    
# Parses element.on('click', function () {});
    def add_on_selector(self, eventType, handler, ast):
        self.add_event_selector(eventType, handler, ast)
    
# Parses element.dialog({...});
    def add_dialog_selector(self, eventType, handler, ast):
        self.add_event_selector(eventType, handler, ast)

#   Process $(some_text)
    def add_dollar_call(self, text, ast):
        resolutions = self.current_context.get_left_operand_resolutions()
        self.diagsInterpreter.add_dollar_call(text, ast)
    
    def is_jquery(self, isJQuery):
        self.parsingResults.containsJQuery = isJQuery
        
    def start_ajax_call(self, ast):
        
        if self.parsingResults:
            self.parsingResults.containsAjaxCall = True
        if self.loopDepth > 0:
            self.parsingResults.ajaxCallsInLoop.append(ast)
            
    def end_ajax_call(self):
        pass

    def add_link_suspension(self, typ, func):
        if self.get_current_function():
            self.links_suspensions.append(LinkSuspension(typ, self.get_current_function(), func))
        
# Parses $.ajax() or something.prototype.ajax()
    def add_ajax_call(self, name, type, urlItem, successFunction, errorFunction, completeFunction, ast, createLinksToCallbacks = True, datatypeExists = True):
        
        if self.ajax_calls == None:
            return None
        
        if type not in ['GET', 'PUT', 'POST', 'DELETE']:
            return None
        
        if not datatypeExists:
            self.parsingResults.ajaxCallsWithoutDatatype.append(ast)
            
        services = []
        astCalls = []
        if not urlItem:
            services.append(ResourceService(name, type, '', ast, self.get_current_function()))
            astCalls.append(None)
        else:
            astCallsInitial = []
            values = evaluate_url(urlItem, astCallsInitial)
            if not values:
                services.append(ResourceService(name, type, None, ast, self.get_current_function()))
                astCalls.append(None)
            else:
                urls = []
                j = 0
                for value in values:
                    if not value in urls:
                        services.append(ResourceService(name, type, value, ast, self.get_current_function()))
                        urls.append(value)
                        astCalls.append(astCallsInitial[j])
                    j += 1

        functionContext = self.get_current_function_context()
        firstTime = True
        i = 0
        for service in services:
            service.astCall = astCalls[i]
            self.ajax_calls.append(service)
            if functionContext:
                functionContext.ajax_calls.append(service)

            if successFunction:
                service.successCallbackPresent = True
                if firstTime and createLinksToCallbacks:
                    self.links_suspensions.append(LinkSuspension('callLink', self.get_current_function(), successFunction))
    
            if errorFunction:
                service.errorCallbackPresent = True
                if firstTime and createLinksToCallbacks:
                    self.links_suspensions.append(LinkSuspension('callLink', self.get_current_function(), errorFunction))
    
            if completeFunction:
                service.completeCallbackPresent = True
                if firstTime and createLinksToCallbacks:
                    self.links_suspensions.append(LinkSuspension('callLink', self.get_current_function(), completeFunction))
            
            firstTime = False
            
            if (successFunction and not errorFunction) or (not successFunction and errorFunction):
                pass
            elif not successFunction:
                # if we are in FunctionCallContext which is in AssignmentContext
                if self.current_context.previous_context and self.current_context.previous_context.is_assignment_context():
                    assignmentContext = self.current_context.previous_context
                    if functionContext:
                        functionContext.ajaxAssignments[assignmentContext.left_operand] = AjaxCall(assignmentContext.right_operand, service)
            i += 1
        self.current_context.services = services
        return services
    
    def add_ajax_success_callback(self, successFunction, identifier_call = None):
        if self.current_context.is_ajax_context():
            for service in self.current_context.services:
                service.successCallbackPresent = True
        elif identifier_call:
            for resolution in identifier_call.get_resolutions():
                ajaxAssignment = self.current_context.get_ajax_assignment(resolution.callee)
                if ajaxAssignment:
                    ajaxAssignment.has_success_callback = True
    
    def add_ajax_error_callback(self, errorFunction, identifier_call = None):
        if self.current_context.is_ajax_context():
            for service in self.current_context.services:
                service.errorCallbackPresent = True
#             self.links_suspensions.append(LinkSuspension('callLink', self.get_current_function(), errorFunction))
        elif identifier_call:
            for resolution in identifier_call.get_resolutions():
                ajaxAssignment = self.current_context.get_ajax_assignment(resolution.callee)
                if ajaxAssignment:
                    ajaxAssignment.has_failure_callback = True
    
    def add_ajax_always_callback(self, errorFunction, identifier_call = None):
        if self.current_context.is_ajax_context():
            for service in self.current_context.services:
                service.alwaysCallbackPresent = True
#             self.links_suspensions.append(LinkSuspension('callLink', self.get_current_function(), errorFunction))
        elif identifier_call:
            for resolution in identifier_call.get_resolutions():
                ajaxAssignment = self.current_context.get_ajax_assignment(resolution.callee)
                if ajaxAssignment:
                    ajaxAssignment.has_always_callback = True
    
# Parses $('a#progressanchor').click()
    def add_event_call(self, eventType, callPart):
        
        if not self.current_context.is_selector_context():
            return
        
        self.calls_to_events_suspensions.append(LinkToEventSuspension('callLink', self.current_context.selector_name, eventType, self.get_current_function(), callPart))
        
    def start_assignment(self, leftOperand, rightOperand):
        self.push_context(AssignmentContext(self.current_context, None, leftOperand, rightOperand))
        try:
            if leftOperand.get_resolutions():
                self.lastAssignmentsByLeftOperandResolution[leftOperand.resolutions[0].callee] = rightOperand
            else:
                self.lastAssignmentsByLeftOperandResolution[leftOperand] = rightOperand
        except:
            pass
        
    def get_first_assignment(self, identifier):
        
        if identifier.get_resolutions():
            resol = identifier.resolutions[0].callee
        else:
            resol = identifier
            
        if resol in self.lastAssignmentsByLeftOperandResolution:
            return self.lastAssignmentsByLeftOperandResolution[resol]
        return None
        
    def end_assignment(self):
        self.pop_context()
        
    def start_selector(self):
        self.push_context(SelectorContext(self.current_context))
        
    def end_selector(self):
        self.pop_context()
        
    def set_selector_name(self, name):
        if not self.current_context.is_selector_context():
            return
        
        self.current_context.selector_name = name
        
# Entering/Quitting jQuery(function ($) {
#                   });
    def start_jquery_function_call_part(self, fcallpart):
        params = fcallpart.get_parameters()
        try:
            if params and params[0].is_function():
                func = params[0]
                pars = func.get_parameters()
                if pars and pars[0].is_identifier() and pars[0].get_name() == '$': 
                    self.jquery_init_call_depth += 1
                    if self.jquery_init_call_depth == 1:
                        self.start_selector()
                        self.set_selector_name('init')
                        self.add_event_selector('init', params[0], params[0])
        except:
            pass
        
    def end_jquery_function_call_part(self, fcallpart):
        params = fcallpart.get_parameters()
        try:
            if params and params[0].is_function():
                func = params[0]
                pars = func.get_parameters()
                if pars and pars[0].is_identifier() and pars[0].get_name() == '$':
                    if self.jquery_init_call_depth == 1:
                        self.end_selector() 
                    self.jquery_init_call_depth -= 1
        except:
            pass
# Entering/Quitting $(document).ready(...);
    def start_jquery_document_ready_call(self, fcallpart):
        self.start_selector()
        self.set_selector_name('ready')
        self.add_event_selector('ready', fcallpart.get_parameters()[0], fcallpart.get_parameters()[0])
    
    def end_jquery_document_ready_call(self):
        self.end_selector() 
    
    def add_identifier(self, identifier):
        self.diagsInterpreter.add_identifier(identifier) 
        
    def add_dialog_call(self, callPart):
        self.diagsInterpreter.add_dialog_call(callPart)
    