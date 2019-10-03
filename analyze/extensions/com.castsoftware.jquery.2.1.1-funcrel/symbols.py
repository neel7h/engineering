'''
Created on 26 nov. 2014

@author: iboillon
'''
from cast.analysers import Bookmark
from collections import OrderedDict
import os

class LinkToEventSuspension:
    
    def __init__(self, linkType, eventName, eventType, caller, callPart):
        self.eventType = eventType
        self.eventName = eventName 
        self.callPart = callPart
        self.linkType = linkType
        self.caller = caller

class LinkSuspension:
    
    def __init__(self, linkType, caller, callee):
        self.type = linkType
        self.caller = caller
        self.callee = callee
        
class AstToken:

    def __init__(self, name, token):
        
        self.name = name
        self.token = token
        
    def get_code_only_crc(self):

        if self.token:        
            return self.token.get_code_only_crc()
        else:
            return 0
    
class Object:
    
    def __init__(self, name):
        self.kb_symbol = None
        self.ast = None
        self.name = name
        self.fullname = None

    def get_kb_object(self):
        return self.kb_symbol

    def get_code_only_crc(self):

        if self.ast:        
            return self.ast.get_code_only_crc()
        else:
            return 0

    def _get_code_only_crc(self):

        if self.ast:        
            return self.ast._get_code_only_crc()
        else:
            return 0
        
class Event(Object):
    """
    An event.
    """
    def __init__(self, name, handler, eventType, ast):
        Object.__init__(self, name)
        self.eventType = eventType
        self.eventHandler = handler
        self.ast = ast
        self.kbObject = None
    
    def __repr__(self):
        
        result = "jquery.event(" + self.name + ',' + self.eventType + ")"
        return result

class ResourceService:

    def __init__(self, name, type, uri, ast, parent):
        
        if name:
            self.name = name
        else:
            self.name = 'GET'
        self.ast = ast
        self.uri = uri
        if uri:
            uris = uri.split('/')
            self.uri = None
            if uris:
                self.uri = ''
                for part in uris:
                    if part:
                        if part.startswith('http:'):
                            self.uri += 'http://'
                        elif part.startswith(':'):
                            self.uri += '{}/'
                        else:
                            self.uri += ( part + '/' )
        self.type = type    # GET/PUT/POST
        self.parent = parent
        self.kbObject = None
        self.successCallbackPresent = False
        self.errorCallbackPresent = False
        self.alwaysCallbackPresent = False
        self.completeCallbackPresent = False
        self.astCall = None
        
    def get_kb_object(self):
        return self.kbObject

class SymbolLink:
    
    def __init__(self, type = None, caller = None, callee = None, bookmark = None):
        
        self.type = type
        self.caller = caller
        self.callee = callee
        self.bookmark = bookmark

class Violation:
    
    def __init__(self, metamodelProperty, bookmark, metamodelPropertyValue = None, propertyValue = None):
        self.metamodelProperty = metamodelProperty
        self.bookmark = bookmark
        self.metamodelPropertyValue = metamodelPropertyValue
        self.propertyValue = propertyValue
        
class Violations:
    
    def __init__(self):
        
        self.dollarDocumentAst = None
        self.dollarWindowAst = None

        self.violations = []

    def add_violation(self, metamodelProperty, bookmark, metamodelPropertyValue = None, propertyValue = None):
        self.violations.append(Violation(metamodelProperty, bookmark, metamodelPropertyValue, propertyValue))
        
    def add_element_type_usage_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_UseOfElementType.numberOfElementType', bookmark)
        
    def add_id_child_nested_selector_without_find_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_UnuseOfFindForIdChildNestedSelector.numberOfIdChildNestedSelectorWithoutFind', bookmark)
        
    def add_ajax_without_callbacks_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_UseOfDollarAjaxWithoutCallbacks.numberOfDollarAjaxWithoutCallbacks', bookmark)
        
    def add_ajax_without_callbacks_jquery3_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_UseOfDollarAjaxWithoutCallbacksJQuery3.numberOfDollarAjaxWithoutCallbacksJQuery3', bookmark)
        
    def add_use_of_uncached_object_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_UseOfUncachedObject.numberOfUncachedObject', bookmark)
        
    def add_use_type_to_select_elements_by_type_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_UseTypeToSelectElementsByType.numberOfSelectElementsByTypeWithoutType', bookmark)
        
    def add_use_of_anonymous_function_for_event_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_UseOfAnonymousFunctionsForEvents.numberOfAnonymousFunctionsForEvents', bookmark)
        
    def add_use_of_css_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_UseOfCss.numberOfCss', bookmark)
        
    def add_use_of_universal_selector_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_AvoidUniversalSelectors.numberOfUniversalSelectors', bookmark)
        
    def add_use_of_deprecated_methods_violation(self, bookmark, methodName):
        self.add_violation('CAST_JQuery_Metric_AvoidJQueryDeprecatedMethods.numberOfJQueryDeprecatedMethods', bookmark, 'CAST_JQuery_Metric_AvoidJQueryDeprecatedMethods.methodName', methodName)
        
    def add_use_of_jquery_cookie_violation(self, bookmark):
        self.add_violation('CAST_JQuery_Metric_AvoidJQueryCookie.numberOfJQueryCookie', bookmark)
        
    def save(self, kb_symbol):
        
        propValues = {}
        for violation in self.violations:
            kb_symbol.save_violation(violation.metamodelProperty, violation.bookmark)
            if violation.propertyValue:
                if not violation.metamodelPropertyValue in propValues:
                    l = []
                    propValues[violation.metamodelPropertyValue] = l
                else:
                    l = propValues[violation.metamodelPropertyValue]
                if not violation.propertyValue in l:
                    l.append(violation.propertyValue)
        for key, values in propValues.items():
            s = None
            for value in values:
                if s:
                    s += ( ',' + value )
                else:
                    s = value
            if propValues:
                kb_symbol.save_property(key, s)