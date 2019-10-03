from symbols import CouchDBDatabase, CouchDBCall
from nodejs_interpreter_framework import NodeJSInterpreterFramework

class NodeJSInterpreterCouchDB(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)
        self.couchDBInstances = []
        self.couchDBDatabasesByVariable = {}
        self.couchDBDatabasesByDocVariable = {}
        self.couchDBBinds = {}
        self.couchDB = False
    
    def manage_createDatabase(self, callName, firstCallPart):

        callees = self.callerInterpreter.get_resolution_callees(firstCallPart.identifier_call)
        for callee in callees:
            if callee in self.couchDBInstances:
                try:
                    database = CouchDBDatabase(firstCallPart.get_parameters()[0], firstCallPart, self.get_current_context().get_current_function())
                    self.parsingResults.couchdbDatabases.append(database)
                    if firstCallPart.parent and firstCallPart.parent.parent and firstCallPart.parent.parent.is_assignment():
                        self.couchDBDatabasesByVariable[firstCallPart.parent.parent.get_left_operand()] = database 
                except:
                    pass
                break
        
    def manage_couchdb_call(self, callName, callPart):

        callees = self.callerInterpreter.get_resolution_callees(callPart.identifier_call)
        for callee in callees:
            if callee in self.couchDBInstances:
                try:
                    linkType = 'useLink'
                    if callName == 'get':
                        linkType = 'useSelectLink'
                    elif callName == 'insert':
                        linkType = 'useInsertLink'
                    elif callName == 'update':
                        linkType = 'useUpdateLink'
                    elif callName == 'del':
                        linkType = 'useDeleteLink'
                    self.parsingResults.couchdbCalls.append(CouchDBCall(callPart.get_parameters()[0], linkType, self.get_current_caller(), callPart))
                    self.check_violation_dataservice_loop(callPart)
                except:
                    pass
                break

            elif callee in self.couchDBDatabasesByVariable:
                try:
                    db = self.couchDBDatabasesByVariable[callee]
                    linkType = 'useLink'
                    if callName == 'insert':
                        linkType = 'useInsertLink'
                    db.add_link_to_database(linkType, self.get_current_caller(), callPart)
                    self.check_violation_dataservice_loop(callPart)
                except:
                    pass
                break

    def manage_attach(self, callPart, callParts):

        if len(callParts) < 2:
            return
        lastCallPart = callParts[-1]
        if not lastCallPart.identifier_call.get_name() == 'create':
            return
        
        callees = self.callerInterpreter.get_resolution_callees(callPart.identifier_call)
        for callee in callees:
            if callee in self.couchDBDatabasesByDocVariable:
                db = self.couchDBDatabasesByDocVariable[callee]
                db.add_link_to_database('useInsertLink', self.get_current_caller(), lastCallPart)
                self.check_violation_dataservice_loop(callPart)

    def manage_open(self, callPart):

        callees = self.callerInterpreter.get_resolution_callees(callPart.identifier_call)
        for callee in callees:
            if callee in self.couchDBDatabasesByDocVariable:
                db = self.couchDBDatabasesByDocVariable[callee]
                db.add_link_to_database('useSelectLink', self.get_current_caller(), callPart)
                self.check_violation_dataservice_loop(callPart)

    def manage_save(self, firstCallPart):

        callees = self.callerInterpreter.get_resolution_callees(firstCallPart.identifier_call)
        for callee in callees:
            if callee in self.couchDBDatabasesByDocVariable:
                db = self.couchDBDatabasesByDocVariable[callee]
                db.add_link_to_database('useUpdateLink', self.get_current_caller(), firstCallPart)
                self.check_violation_dataservice_loop(firstCallPart)

    def add_require(self, assignment):
        firstCallPart = assignment.get_right_operand().functionCallParts[0]
        if firstCallPart.parameters and len(firstCallPart.parameters) == 1 and firstCallPart.parameters[0].is_string():
            name = firstCallPart.parameters[0].get_name()
            if name == 'couch-db':
                self.couchDB = True
        
    def start_assignment(self, assign):
        rightOper = assign.get_right_operand()
        if rightOper.is_identifier() and rightOper.get_fullname() in self.couchDBBinds:
            self.couchDBDatabasesByVariable[assign.get_left_operand()] = self.couchDBBinds[rightOper.get_fullname()] 
        
    def start_function_call(self, fcall):

        if fcall.parent and fcall.parent.is_assignment():
            if fcall.parent.get_right_operand().is_new_expression():
                newFCall = fcall.parent.get_right_operand().elements[1]
                requireDeclaration = self.get_require_declaration(newFCall.get_function_call_parts()[0].identifier_call)
                if requireDeclaration:
                    if requireDeclaration.reference == 'node-couchdb':
                        self.couchDBInstances.append(fcall.parent.get_left_operand())
                    elif requireDeclaration.reference == 'couch-db':
                        self.couchDBInstances.append(fcall.parent.get_left_operand())
            else:
                identCall = fcall.get_function_call_parts()[0].identifier_call
                callees = self.callerInterpreter.get_resolution_callees(identCall)
                for callee in callees:
                    requireDeclaration = self.get_require_declaration(callee)
                    if requireDeclaration and requireDeclaration.reference == 'couch-db':
                        self.couchDBInstances.append(fcall.parent.get_left_operand())
                    elif identCall.get_name() == 'doc' and callee in self.couchDBDatabasesByVariable:
                        self.couchDBDatabasesByDocVariable[fcall.parent.get_left_operand()] = self.couchDBDatabasesByVariable[callee]
        
        callParts = fcall.get_function_call_parts()
        firstCallPart = True

        for callPart in callParts:
            
            firstCallPartIdentifierCall = callPart.identifier_call
    
            if firstCallPartIdentifierCall.get_prefix_internal() or not firstCallPart:
    
                callName = firstCallPartIdentifierCall.get_name()
                
                if callName in ['get', 'insert', 'update', 'del']:
                    self.manage_couchdb_call(callName, callPart)
    
                elif callName == 'attach':
                    self.manage_attach(callPart, callParts)
    
                elif callName == 'bind':
                    if self.couchDB:
                        callees = self.callerInterpreter.get_resolution_callees(callPart.identifier_call)
                        for callee in callees:
                            if callee in self.couchDBInstances:
                                try:
                                    param = callPart.get_parameters()[0]
                                    database = CouchDBDatabase(param, callPart, self.get_current_context().get_current_function())
                                    self.couchDBBinds[callPart.identifier_call.get_prefix() + '.' + param.get_name()] = database
                                    self.parsingResults.couchdbDatabases.append(database)

                                except:
                                    pass

                elif callName == 'open':
                    self.manage_open(callPart)
    
                elif callName == 'save':
                    self.manage_save(callPart)
    
                elif callName in ['createDatabase', 'database']:
                    self.manage_createDatabase(callName, callPart)

            else:
                pass
            
            firstCallPart = False
