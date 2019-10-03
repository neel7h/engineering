from symbols import LinkSuspension, MongooseConnection, MongooseModel
from nodejs_interpreter_framework import Context, NodeJSInterpreterFramework
from cast.analysers import log

class FindOneContext(Context):
        
    def __init__(self, parentContext):
        Context.__init__(self, parentContext)
        self.returnVariable = None
        self.model = None
        
    def is_findOne(self):
        return True
        
    def is_findOne_return_variable(self, identifierName):
        if identifierName == self.returnVariable.get_name():
            return self
        else:
            return Context.is_findOne_return_variable(self, identifierName)
        
class OpenConnectionContext(Context):
        
    def __init__(self, parentContext, dbParameter, connection):
        Context.__init__(self, parentContext)
        self.connection = connection
        self.dbParameter = dbParameter
        
    def is_open_connection(self):
        return True

    def get_openConnection_context(self):
        return self
           
class NodeJSInterpreterMongoDB(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)
        self.mongooseModelVariablesByIdentifier = {}
        self.mongooseModelByCallPart = {}
        self.mongooseConnectionVariablesByIdentifier = {}
#         var Server = require('mongodb').Server
        self.mongoDBServerVariable = None
#         var Db = require('mongodb').Db
        self.mongoDBDbVariable = None
#         var mongo = require("mongo-client")
        self.mongoClientVariable = None
#         var insert = require("mongo-client/insert")
#         var findOne = require("mongo-client/findOne")
#         var close = require("mongo-client/close")
        self.mongoClientOperationVariables = {} # key = variable, value = operation Type as string

    def add_require(self, assignment):

#         Register these 2 variables in self.mongoDBDbVariable and self.mongoDBServerVariable
#         var Db = require('mongodb').Db
#         var Server = require('mongodb').Server
        firstCallPart = assignment.get_right_operand().functionCallParts[0]
        if firstCallPart.parameters and len(firstCallPart.parameters) == 1 and firstCallPart.parameters[0].is_string():
            name = firstCallPart.parameters[0].get_name()
            if len(assignment.get_right_operand().functionCallParts) == 2:
                secondCallPart = assignment.get_right_operand().functionCallParts[1]
                name2 = secondCallPart.get_name()
                if name == 'mongodb':
                    if name2 == 'Db':
                        self.mongoDBDbVariable = assignment.get_left_operand()
                    elif name2 == 'Server':
                        self.mongoDBServerVariable = assignment.get_left_operand()
            else:
                if name == 'mongo-client':
                    self.mongoClientVariable = assignment.get_left_operand()
                elif name.startswith('mongo-client/'):
                    self.mongoClientOperationVariables[assignment.get_left_operand()] = name[13:]
        
    def add_model_variable(self, identifier, model, callPart):
             
        if identifier:   
            if identifier in self.mongooseModelVariablesByIdentifier:
                l = self.mongooseModelVariablesByIdentifier[identifier]
            else:
                l = []
                self.mongooseModelVariablesByIdentifier[identifier] = l
            l.append(model)
        self.mongooseModelByCallPart[callPart] = model
        
    def get_model_variables(self, identifier):

        if identifier in self.mongooseModelVariablesByIdentifier:
            return self.mongooseModelVariablesByIdentifier[identifier]

        else:
            # if not currentModel, create a special model for unknown models because in other files and store suspensions
            # specialModel.linkSuspensions.append(LinkSuspension(linkType, self.get_current_caller(), resolution.callee, callPart))
            # see integration test test_integration_mongoose
            model = MongooseModel(None, None, None, None, None, None, identifier)
            self.parsingResults.mongooseModels.append(model)
            return [ model ]

    def start_assignment(self, assign):
        
        if not self.mongoDBDbVariable and not self.mongoDBServerVariable and not self.mongoClientVariable and not self.mongooseConnectionVariablesByIdentifier:
            return
        
#         var db = new Db('integration_tests',
#            new Server("127.0.0.1", 27017, { ...
        rightOper = assign.get_right_operand()
        if rightOper.is_new_expression():
            connection = None
            fcallpart = rightOper.elements[1].get_function_call_parts()[0]
            callees = self.callerInterpreter.get_resolution_callees(fcallpart.identifier_call)
            for callee in callees:
                if callee == self.mongoDBDbVariable:
                    connection = MongooseConnection(fcallpart.parameters[0], fcallpart, self.get_current_caller())
                    self.parsingResults.mongooseConnections.append(connection)
                    self.mongooseConnectionVariablesByIdentifier[assign.get_left_operand()] = connection
                    break
            try:
                param2 = fcallpart.parameters[1]
                if connection and param2.is_new_expression():
                    fcallpart = param2.elements[1].get_function_call_parts()[0]
                    callees = self.callerInterpreter.get_resolution_callees(fcallpart.identifier_call)
                    for callee in callees:
                        if callee == self.mongoDBServerVariable:
                            server = fcallpart.parameters[0].get_name()
                            port = fcallpart.parameters[1].get_name()
                            connection.name = 'mongodb://' + server + ':' + port
            except:
                pass

        elif rightOper.is_function_call():
            connection = None
            fcallpart = rightOper.get_function_call_parts()[0]
            callees = self.callerInterpreter.get_resolution_callees(fcallpart.identifier_call)
            for callee in callees:
                if callee == self.mongoClientVariable:
                    connection = MongooseConnection(fcallpart.parameters[0], fcallpart, self.get_current_caller())
                    self.parsingResults.mongooseConnections.append(connection)
                    self.mongooseConnectionVariablesByIdentifier[assign.get_left_operand()] = connection
                    break
                elif callee in self.mongooseConnectionVariablesByIdentifier:
                    self.create_model_on_connection(fcallpart, fcallpart.parent.parent, self.mongooseConnectionVariablesByIdentifier[callee].ast)
            
    def start_function_call(self, fcall):

        callParts = fcall.get_function_call_parts()
        firstCallPart = True

        for callPart in callParts:
            
            firstCallPartIdentifierCall = callPart.identifier_call
    
            if firstCallPartIdentifierCall.get_prefix_internal() or not firstCallPart:
    
                callName = firstCallPartIdentifierCall.get_name()
                
                if callName == 'connect':
                    self.manage_connect(callPart)
                
                elif callName == 'open':
                    self.manage_open(callPart)
                
                elif callName in ['model', 'collection']:
                    self.manage_model(callPart, fcall.parent)

                elif callName in ['findOne', 'findById']:
                    self.manage_findOne(callPart, firstCallPart)
                    
                elif callName in ['remove', 'findByIdAndRemove', 'findOneAndRemove']:
                    self.manage_find_or_remove(callPart, 'useDeleteLink', callParts[0])
    
                elif callName == 'find':
                    self.manage_find_or_remove(callPart, 'useSelectLink', callParts[0])
    
                elif callName == 'save':
                    self.manage_save(callPart, callParts[0])

                elif callName in ['insertMany', 'insert']:
                    self.manage_insert(callPart, callParts[0])

                elif callName in ['updateOne', 'findByIdAndUpdate', 'findOneAndUpdate']:
                    self.manage_update(callPart, callParts[0])

                elif callName == 'deleteOne':
                    self.manage_delete(callPart, callParts[0])
                        
            else:
                
                if not firstCallPartIdentifierCall.get_prefix_internal():

                    if self.mongoClientOperationVariables:

                        callees = self.callerInterpreter.get_resolution_callees(firstCallPartIdentifierCall)
                        for callee in callees:
                            if callee in self.mongoClientOperationVariables:
                                ttype = self.mongoClientOperationVariables[callee]
                                if ttype == 'insert':
                                    linkType = 'useInsertLink'
                                elif ttype in ['findOne', 'find']:
                                    linkType = 'useSelectLink'
                                elif ttype in ['update', 'findAndModify']:
                                    linkType = 'useUpdateLink'
                                elif ttype in ['remove', 'findAndRemove']:
                                    linkType = 'useDeleteLink'
                                else:
                                    linkType = None
                                if linkType:
                                    self.check_violation_dataservice_loop(callPart)
                                    collection = callPart.parameters[0]
                                    callees = self.callerInterpreter.get_resolution_callees(collection)
                                    for callee in callees:
                                        models = self.get_model_variables(callee)
                                        for currentModel in models:
                                            currentModel.linkSuspensions.append(LinkSuspension(linkType, self.get_current_caller(), currentModel, callPart))
            
            firstCallPart = False
        
    def end_function_call(self):
            
        if self.get_current_context():
            if self.get_current_context().is_findOne():
                self.end_findOne()
            elif self.get_current_context().is_open_connection():
                self.end_openConnection()
        
    def manage_connect(self, firstCallPart):
        try:
            firstCallPartIdentifierCall = firstCallPart.identifier_call
            
            requireDeclaration = self.get_require_declaration(firstCallPartIdentifierCall)
            if (requireDeclaration and requireDeclaration.reference in ['mongoose', 'mongodb']) or \
                (firstCallPartIdentifierCall.get_resolutions() and firstCallPartIdentifierCall.resolutions[0].callee.parent and \
                 firstCallPartIdentifierCall.resolutions[0].callee.parent.is_function() and \
                 firstCallPartIdentifierCall.resolutions[0].callee in firstCallPartIdentifierCall.resolutions[0].callee.parent.get_parameters() and \
                 firstCallPartIdentifierCall.get_prefix() and firstCallPartIdentifierCall.get_prefix() == 'mongoose'):
    
                connection = MongooseConnection(firstCallPart.parameters[0], firstCallPart, self.get_current_caller())
                self.parsingResults.mongooseConnections.append(connection)
                try:
                    self.start_openConnection(firstCallPart.parameters[1].parameters[1], connection)
                    self.check_violation_dataservice_loop(firstCallPart)
                except:
                    pass
        except:
            pass
        
    def manage_open(self, firstCallPart):

        callees = self.callerInterpreter.get_resolution_callees(firstCallPart.identifier_call)
        for callee in callees:
            if callee in self.mongooseConnectionVariablesByIdentifier:
                self.start_openConnection(firstCallPart.parameters[0].parameters[1], self.mongooseConnectionVariablesByIdentifier[callee])
                self.check_violation_dataservice_loop(firstCallPart)
                break
        
    def findMongoDBConnections(self, func):
        
        if self.get_current_context():
            dbConnectionContext = self.get_current_context().get_openConnection_context()
            if dbConnectionContext:
                return [ dbConnectionContext.connection.ast ]
#                 return [ dbConnectionContext.connection ]
            
        l = []
        try:
            for call in func.calls:
                parent = call.parent
                while parent:
                    if parent.is_function_call_part() and parent.identifier_call.get_name() == 'connect':
                        if not parent in l:
                            l.append(parent)
                        break
                    parent = parent.parent
        except:
            pass
        return l
    
    def create_model_on_connection(self, firstCallPart, fcallParent, fcallpartConnection):

        try:
            varIdentifier = fcallParent.get_left_operand()
        except:
            varIdentifier = None
            
        if self.get_current_context():
            model = MongooseModel(firstCallPart.parameters[0], fcallpartConnection, firstCallPart, self.get_current_caller(), varIdentifier, self.callerInterpreter.jsContent)
        else:
            model = MongooseModel(firstCallPart.parameters[0], fcallpartConnection, firstCallPart, None, varIdentifier, self.callerInterpreter.jsContent)
        parent = fcallParent
        if parent.is_assignment():
            leftOperand = parent.get_left_operand()
            if leftOperand.get_resolutions():
                try:
                    self.add_model_variable(leftOperand.resolutions[0].callee, model, firstCallPart)
                except:
                    pass
            else:
                try:
                    self.add_model_variable(leftOperand, model, firstCallPart)
                except:
                    pass
        elif parent.is_function():
            try:
                self.add_model_variable(parent.parameters[1], model, firstCallPart)
            except:
                pass
        try:
            if firstCallPart.parameters[1].is_function():
                self.add_model_variable(firstCallPart.parameters[1].parameters[1], model, firstCallPart)
        except:
            self.add_model_variable(None, model, firstCallPart)
        self.parsingResults.mongooseModels.append(model)
        
    def manage_model(self, firstCallPart, fcallParent):
        try:
            firstCallPartIdentifierCall = firstCallPart.identifier_call
    
            requireDeclaration = self.get_require_declaration(firstCallPartIdentifierCall)
            if (requireDeclaration and requireDeclaration.reference in ['mongoose', 'mongodb']) or self.require_contain('mongodb') or \
                (firstCallPartIdentifierCall.get_resolutions() and firstCallPartIdentifierCall.resolutions[0].callee.parent and \
                firstCallPartIdentifierCall.resolutions[0].callee.parent.is_function() and \
                 firstCallPartIdentifierCall.resolutions[0].callee in firstCallPartIdentifierCall.resolutions[0].callee.parent.get_parameters() and \
                 firstCallPartIdentifierCall.get_prefix() and firstCallPartIdentifierCall.get_prefix() == 'mongoose'):
                fcallpartConnections = None
    
                try:
                    if firstCallPartIdentifierCall.resolutions:
                        for resol in firstCallPartIdentifierCall.resolutions:
                            callee = resol.callee
                            if callee.parent and callee.parent.is_function() and callee in callee.parent.parameters:
                                fcallpartConnections = self.findMongoDBConnections(callee.parent)
                                if fcallpartConnections:
                                    break
                except:
                    pass
    
                if fcallpartConnections:
                    for fcallpartConnection in fcallpartConnections:
                    # self.create_model_on_connection(firstCallPart, fcallParent, fcallpartConnection.ast)
                        self.create_model_on_connection(firstCallPart, fcallParent, fcallpartConnection)
                else:
                    self.create_model_on_connection(firstCallPart, fcallParent, None)
        except:
            pass

    def manage_findOne(self, callPart, firstCallPart = None):

        firstCallPartIdentifierCall = callPart.identifier_call
        findOneContext = self.start_findOne()
        if firstCallPartIdentifierCall.get_resolutions():
            for resolution in firstCallPartIdentifierCall.get_resolutions():
                currentModels = self.get_model_variables(resolution.callee)
                linkType = 'useSelectLink'
                self.check_violation_dataservice_loop(callPart)
                for currentModel in currentModels:
                    currentModel.linkSuspensions.append(LinkSuspension(linkType, self.get_current_caller(), currentModel, callPart))
    
                    # get second parameter of last parameter function
                    # ex: userModel.findOne({'pseudo': pseudo}, function(err, user) {})
                    if callPart.parameters:
                        param = callPart.parameters[-1]
                        if param.is_function() and len(param.parameters) == 2:
                            param1 = param.parameters[1]
                            if param1.is_identifier():
                                findOneContext.model = currentModel
                                
        if not firstCallPart:
            firstCallPart = callPart.parent.get_function_call_parts()[0]
            firstCallPartIdentifierCall = firstCallPart.identifier_call
            try:
                if firstCallPartIdentifierCall.get_name() == 'collection' and firstCallPartIdentifierCall.prefix_ends_with('.db'):
                    paramName = firstCallPart.get_parameters()[0].get_name()
                    for model in self.parsingResults.mongooseModels:
                        if model.name.get_name() == paramName:
                            model.linkSuspensions.append(LinkSuspension('useSelectLink', self.get_current_caller(), model, callPart))
                            break
            except:
                pass

    def manage_find_or_remove(self, callPart, linkType, firstCallPart = None):

        found = self.manage_mongodb_operation(callPart, linkType, firstCallPart)
        if found:
            return

        firstCallPartIdentifierCall = callPart.identifier_call
        self.check_violation_dataservice_loop(firstCallPart)

        if firstCallPartIdentifierCall.get_resolutions():
            for resolution in firstCallPartIdentifierCall.get_resolutions():
                currentModels = self.get_model_variables(resolution.callee)
                for currentModel in currentModels:
                    currentModel.linkSuspensions.append(LinkSuspension(linkType, self.get_current_caller(), currentModel, callPart))
                    
    def manage_save(self, callPart, firstCallPart = None):

        firstCallPartIdentifierCall = callPart.identifier_call
        
        findOneContext = self.get_current_context().is_findOne_return_variable(firstCallPartIdentifierCall.get_prefix_internal())
        if findOneContext and findOneContext.model:
            findOneContext.model.linkSuspensions.append(LinkSuspension('useUpdateLink', self.get_current_caller(), findOneContext.model, callPart))
        else:
            for resolution in firstCallPartIdentifierCall.get_resolutions():
                callee = resolution.callee
                if callee.parent and callee.parent.is_assignment():
                    rightOperand = callee.parent.get_right_operand()
                    if rightOperand.is_new_expression():
                        fcall = rightOperand.elements[1]
                        if fcall.is_function_call():
                            modelVariable = fcall.functionCallParts[0].identifier_call
                            for resolModel in modelVariable.get_resolutions():
                                currentModels = self.get_model_variables(resolModel.callee)
                                for currentModel in currentModels:
                                    currentModel.linkSuspensions.append(LinkSuspension('useInsertLink', self.get_current_caller(), currentModel, callPart))

        self.check_violation_dataservice_loop(callPart)

    def manage_mongodb_operation(self, callPart, linkType, firstCallPart = None):

        found = False
        callPartIdentifierCall = callPart.identifier_call
        try:
            '''
            * identifier has always get_resolutions but resolutions hasn't.
            * Here when there no resolutions => pass except.
            '''
            for resol in callPartIdentifierCall.resolutions:
                callee = resol.callee
                models = self.get_model_variables(callee)
                for model in models:
                    model.linkSuspensions.append(LinkSuspension(linkType, self.get_current_caller(), model, callPart))
                    found = True
        except:
            # database.collection(mongoConfig.collection).insert(record, function(error) { ...
            if firstCallPart and firstCallPart != callPart:
                if firstCallPart in self.mongooseModelByCallPart:
                    model = self.mongooseModelByCallPart[firstCallPart]
                    model.linkSuspensions.append(LinkSuspension(linkType, self.get_current_caller(), model, callPart))
                    found = True
        return found

    def manage_insert(self, callPart, firstCallPart = None):
        self.check_violation_dataservice_loop(callPart)
        self.manage_mongodb_operation(callPart, 'useInsertLink', firstCallPart)

    def manage_update(self, callPart, firstCallPart = None):
        self.check_violation_dataservice_loop(callPart)
        self.manage_mongodb_operation(callPart, 'useUpdateLink', firstCallPart)

    def manage_delete(self, callPart, firstCallPart = None):
        self.check_violation_dataservice_loop(callPart)
        self.manage_mongodb_operation(callPart, 'useDeleteLink', firstCallPart)
    
    def start_findOne(self):
        self.push_context(FindOneContext(self.get_current_context()))
        return self.get_current_context()
    
    def end_findOne(self):
        self.pop_context()
    
    def start_openConnection(self, dbParameter, connection):
        self.push_context(OpenConnectionContext(self.get_current_context(), dbParameter, connection))
        return self.get_current_context()
    
    def end_openConnection(self):
        self.pop_context()
