from symbols import ExternalLibrary
from nodejs_diags_interpreter import NodeJSDiagsInterpreter
from nodejs_interpreter_framework import Context
from nodejs_interpreter_couchdb import NodeJSInterpreterCouchDB
from nodejs_interpreter_marklogic import NodeJSInterpreterMarklogic
from nodejs_interpreter_mongodb import NodeJSInterpreterMongoDB
from nodejs_interpreter_sqldb import NodeJSInterpreterSQLDatabase
from nodejs_interpreter_loopback import NodeJSInterpreterLoopback
from nodejs_interpreter_hapi import NodeJSInterpreterHapi
from nodejs_interpreter_sails import NodeJSInterpreterSails
from nodejs_interpreter_express import NodeJSInterpreterExpress
from nodejs_interpreter_koa import NodeJSInterpreterKoa
from nodejs_interpreter_knex import NodeJSInterpreterKnex
from nodejs_interpreter_message_queues import NodeJSInterpreterMQTT
from nodejs_interpreter_seneca import NodeJSInterpreterSeneca

from cast.analysers import log

import os

class FunctionContext(Context):
        
    def __init__(self, func, parentContext):
        Context.__init__(self, parentContext)
        self.function = func
        
    def get_function(self):
        return self.function
        
    def get_kb_function(self):
        if self.function.parent.is_js_function_call():
            return None
        else:
            return self.function
    
    def get_current_function(self):
        return self.get_function()
        
class ClassContext(Context):
        
    def __init__(self, cl, parentContext):
        Context.__init__(self, parentContext)
        self.cl = cl
        
    def get_class(self):
        return self.cl
    
    def get_current_class(self):
        return self.get_class()
        
class NodeJSInterpreter:
        
    class Require:
        
        def __init__(self, var, ref):
            self.variable = var
            self.reference = ref

    def __init__(self, file, config, analysisContext, parsingResults, versions):

        self.file = file
        self.config = config
        self.analysisContext = analysisContext
        self.jsContent = analysisContext.jsContent
        self.parsingResults = parsingResults
        self.stack_contexts = []
        self.push_context(Context(None))
        self.require_declarations = {}
        self.global_var_declarations = {}
        self.diagsInterpreter = NodeJSDiagsInterpreter(self.parsingResults.violations, self.file, self)
        self.onHandlersSuspensions = {}
        self.jsContent = None
        self.loopDepth = 0
        self.functionListFullNames = []
        self.functionCreatingClassListFullNames = []
        self.externalLibFunctionCalls = []
        self.externalLibMethodCalls = []
        self.interpreters = []
        self.versions = versions
        self.interpreters.append(NodeJSInterpreterCouchDB(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterMarklogic(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterMongoDB(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterSQLDatabase(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterLoopback(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterHapi(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterSails(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterExpress(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterKoa(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterKnex(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterMQTT(file, config, parsingResults, self))
        self.interpreters.append(NodeJSInterpreterSeneca(file, config, parsingResults, self))

    def get_resolution_callees(self, ident):
        res = []
        try:
            if ident.resolutions:
                for resol in ident.resolutions:
                    res.append(resol.callee)
        except:
            pass
        return res
    
    def start_source_code(self, jsContent):
        self.jsContent = jsContent
        self.diagsInterpreter.start_source_code(jsContent)
        
    def get_require_declaration(self, firstCallPartIdentifierCall):
            
        requireDeclaration = None
        try:
            if not firstCallPartIdentifierCall.get_prefix_internal() in self.require_declarations:
                        
                variableAssignment = self.get_global_variable(firstCallPartIdentifierCall.get_prefix_internal())
                if variableAssignment:
                    rightOperand = variableAssignment.get_right_operand()
                    if rightOperand.is_function_call():
                        callIdentName = rightOperand.functionCallParts[0].identifier_call.name
                        if callIdentName in self.require_declarations:
                            requireDeclaration = self.require_declarations[callIdentName]
            else:
                requireDeclaration = self.require_declarations[firstCallPartIdentifierCall.get_prefix_internal()]
                
            if not firstCallPartIdentifierCall.get_prefix_internal() and not requireDeclaration:
                if firstCallPartIdentifierCall.get_name() in self.require_declarations:
                    requireDeclaration = self.require_declarations[firstCallPartIdentifierCall.get_name()]
        except:
            pass
        return requireDeclaration
            
    def get_current_caller(self):
        caller = self.current_context.get_current_function()
        if not caller:
            caller = self.jsContent
        return caller

    def push_context(self, context):            
        self.current_context = context
        self.stack_contexts.append(self.current_context)

    def pop_context(self):            
        if not self.stack_contexts:
            pass
        self.stack_contexts.pop()
        if self.stack_contexts:
            self.current_context = self.stack_contexts[-1]
        else:
            self.current_context = None

    def start_function(self, function):
        path_file = os.path.abspath(function.get_file().get_path())
        if '\\api\\controllers' in path_file:
            self.parsingResults.action_sails.append(function)

        if not self.require_declarations and not self.parsingResults.is_node_project:
            return

        if self.current_context and self.current_context.is_findOne():
            if len(function.parameters) >= 2 and function.parameters[1].is_identifier():
                self.current_context.returnVariable = function.parameters[1]
            else:
                self.current_context.returnVariable = None
        self.push_context(FunctionContext(function, self.current_context))
        self.diagsInterpreter.start_function(function, self.current_context)

    def end_function(self):
        if not self.require_declarations and not self.parsingResults.is_node_project:
            return

        self.diagsInterpreter.end_function()

        if self.stack_contexts:
            self.stack_contexts.pop()
            
        if self.stack_contexts:
            self.current_context = self.stack_contexts[-1]
        else:
            self.current_context = None

    def start_class(self, cl):

        if not self.require_declarations and not self.parsingResults.is_node_project:
            return
        
        self.push_context(ClassContext(cl, self.current_context))

    def end_class(self):

        if not self.require_declarations and not self.parsingResults.is_node_project:
            return

        if self.stack_contexts:
            self.stack_contexts.pop()
            
        if self.stack_contexts:
            self.current_context = self.stack_contexts[-1]
        else:
            self.current_context = None
        
    def add_require(self, assignment):
        
        for interpreter in self.interpreters:
            interpreter.add_require(assignment)

        leftOperand = assignment.get_left_operand()
        firstCallPart = assignment.get_right_operand().functionCallParts[0]
        if firstCallPart.parameters and len(firstCallPart.parameters) == 1 and firstCallPart.parameters[0].is_string():
            name = firstCallPart.parameters[0].get_name()
            callParts = assignment.get_right_operand().functionCallParts
            app_express = name == 'express'and len(callParts) > 1 and callParts[1].get_name() not in ['json', 'static', 'Router', 'urlencoded']
            bSimple = len(callParts) == 1 or app_express
            self.diagsInterpreter.start_require(name, bSimple)
            self.require_declarations[leftOperand.get_name()] = self.Require(leftOperand, name)
            self.parsingResults.requires.append(name)
            if any( s in name for s in ['.', '/'] ):
                return
            
            if not name in self.parsingResults.externalLibraries:
                self.parsingResults.externalLibraries[name] = firstCallPart.parameters[0]
            if name in ExternalLibrary.functionListByLibName:
                varName = leftOperand.get_name()
                for funcName in ExternalLibrary.functionListByLibName[name]:
                    self.functionListFullNames.append(varName + '.' + funcName)
            if name in ExternalLibrary.functionCreatingClassListByLibName:
                varName = leftOperand.get_name()
                for funcName in ExternalLibrary.functionCreatingClassListByLibName[name]:
                    self.functionCreatingClassListFullNames.append(varName + '.' + funcName)
            
    def add_global_variable_declaration(self, varName, assignment):
        self.global_var_declarations[varName] = assignment
    
    def get_global_variable(self, varName):
        if varName in self.global_var_declarations:
            return self.global_var_declarations[varName]
        return None
    
    def get_current_kb_function(self):
        
        if not self.stack_contexts:
            return None
        return self.stack_contexts[-1].get_kb_function()
    
    def get_current_function(self):
        
        if not self.stack_contexts:
            return None
        return self.stack_contexts[-1].get_function()
        
    def start_assignment(self, assign):
        for interpreter in self.interpreters:
            interpreter.start_assignment(assign)
        self.diagsInterpreter.start_assignment(assign)
        
    def start_function_call(self, fcall):
    
        if not self.require_declarations and not self.parsingResults.is_node_project:
            return

        for interpreter in self.interpreters:
            interpreter.start_function_call(fcall)

        self.diagsInterpreter.start_function_call(fcall)      
        
    def start_addition_expression(self, expression):
        self.diagsInterpreter.start_addition_expression(expression)      

    def finalize(self):

        self.diagsInterpreter.finalize()
        for onHandler, currentFunctions in self.onHandlersSuspensions.items():
            for currentFunction in currentFunctions:
                for httpReq in self.parsingResults.httpRequests:
                    if currentFunction and httpReq.handler in [ currentFunction, currentFunction.get_kb_symbol() ]:
                        httpReq.onFunctions.append(onHandler)
                        break
                            
        for linkSusp in self.externalLibFunctionCalls:
            requireDeclaration = self.get_require_declaration(linkSusp.callPart.get_identifier())
            if requireDeclaration:
                if requireDeclaration.reference in self.parsingResults.externalLibrariesFunctionCalls:
                    l = self.parsingResults.externalLibrariesFunctionCalls[requireDeclaration.reference]
                else:
                    l = []
                    self.parsingResults.externalLibrariesFunctionCalls[requireDeclaration.reference] = l
                l.append(linkSusp)
                
        for linkSusp in self.externalLibMethodCalls:
            createClassCallPartIdent = linkSusp.infos['createClass']
            requireDeclaration = self.get_require_declaration(createClassCallPartIdent)
            if requireDeclaration:
                if requireDeclaration.reference in self.parsingResults.externalLibrariesMethodCalls:
                    l = self.parsingResults.externalLibrariesMethodCalls[requireDeclaration.reference]
                else:
                    l = []
                    self.parsingResults.externalLibrariesMethodCalls[requireDeclaration.reference] = l
                l.append(linkSusp)

        if not self.parsingResults.isApplication:
            self.parsingResults.isApplication = self.diagsInterpreter.is_application()
        
    def end_function_call(self):
            
        if not self.require_declarations:
            return

        for interpreter in self.interpreters:
            interpreter.end_function_call()
    
    def start_loop(self):
        self.loopDepth += 1

    def end_loop(self):
        self.loopDepth -= 1

