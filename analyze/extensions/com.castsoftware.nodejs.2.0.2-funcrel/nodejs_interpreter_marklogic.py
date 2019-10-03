from symbols import MarklogicDatabase
from nodejs_interpreter_framework import Context, NodeJSInterpreterFramework
   
class MarklogicContext(Context):
         
    def __init__(self, parentContext, functionName, marklogicDatabase, ast):
        Context.__init__(self, parentContext, ast)
        self.functionName = functionName
        self.marklogicDatabase = marklogicDatabase
        self.collections = []
         
    def is_marklogic(self):
        return True
         
    def get_marklogic_context(self):
        return self
    
    def add_collection(self, name, ast):
        self.collections.append(name)
        self.marklogicDatabase.add_collection(name, ast)
        
class NodeJSInterpreterMarklogic(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)
        self.marklogicDatabases = {}

    def manage_createDatabaseClient(self, firstCallPart):

        firstCallPartIdentifierCall = firstCallPart.identifier_call
        
        requireDeclaration = self.get_require_declaration(firstCallPartIdentifierCall)
        if requireDeclaration:

            if requireDeclaration.reference == 'marklogic' or requireDeclaration.variable.get_name() == 'marklogic':
                                
                database = MarklogicDatabase(firstCallPart.parameters[0], firstCallPart, self.get_current_context().get_current_function())
                self.parsingResults.marklogicDatabases.append(database)
                try:
                    self.marklogicDatabases[firstCallPart.get_parent().get_parent().get_left_operand()] = database
                except:
                    pass
        
    def start_function_call(self, fcall):

        callParts = fcall.get_function_call_parts()
        firstCallPart = True

        for callPart in callParts:
            
            firstCallPartIdentifierCall = callPart.identifier_call
    
            if firstCallPartIdentifierCall.get_prefix_internal() or not firstCallPart:
    
                callName = firstCallPartIdentifierCall.get_name()
                
                if callName == 'remove':
                    self.start_marklogic_documents_call(callName, callPart)
    
                elif callName == 'createDatabaseClient':
                    self.manage_createDatabaseClient(callPart)
    
                elif callName == 'query':
                    self.start_marklogic_documents_call(callName, callPart)
                
                elif callName in ['write', 'patch', 'read', 'removeAll']:
                    self.start_marklogic_documents_call(callName, callPart)
                
                elif callName == 'collection':
                    if self.get_current_context():
                        marklogicContext = self.get_current_context().get_marklogic_context()
                        if marklogicContext:
                            try:
                                marklogicContext.add_collection(callPart.parameters[0], callPart.parameters[0])
                            except:
                                pass
                        
            else:
                pass
            
            firstCallPart = False
        
    def end_function_call(self):

        if self.get_current_context() and self.get_current_context().is_marklogic():
                self.end_marklogic_documents_call()
        
    def start_marklogic_documents_call(self, callName, callPart):

        try:
            if callPart.identifier_call.resolutions:
                for resolution in callPart.identifier_call.resolutions:
                    if resolution.callee in self.marklogicDatabases:
                        marklogicDatabase = self.marklogicDatabases[resolution.callee]
                        self.push_context(MarklogicContext(self.get_current_context(), callName, marklogicDatabase, callPart))
                        self.check_violation_dataservice_loop(callPart)
        except:
            pass
        
    def end_marklogic_documents_call(self):
        
        current_context = self.get_current_context()
        marklogicDatabase = current_context.marklogicDatabase
        linkType = 'useLink'
        if current_context.functionName in ['query', 'read']:
            linkType = 'useSelectLink'
        elif current_context.functionName == 'write':
            linkType = 'useInsertLink'
        elif current_context.functionName == 'patch':
            linkType = 'useUpdateLink'
        elif current_context.functionName in ['remove', 'removeAll']:
            linkType = 'useDeleteLink'
        
        caller = self.get_current_caller()

        if current_context.collections:
            for collection in current_context.collections:
                marklogicDatabase.add_link_to_collection(linkType, caller, collection, current_context.ast)
        else:
            marklogicDatabase.add_link_to_collection(linkType, caller, None, current_context.ast)
            
        self.pop_context()
