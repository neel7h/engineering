from cast.analysers import external_link, log, CustomObject, Bookmark, File, create_link
from symbols import LinkSuspension, DatabaseConnection
from sql_parser import extract_tables
from nodejs_interpreter_framework import Context, NodeJSInterpreterFramework
           
class ExecuteContext(Context):
         
    def __init__(self, parentContext):
        Context.__init__(self, parentContext)
        self.returnVariable = None
        self.connection = None
         
    def is_execute(self):
        return True

class NodeJSInterpreterSQLDatabase(NodeJSInterpreterFramework):

    def __init__(self, file, config, parsingResults, callerInterpreter):

        NodeJSInterpreterFramework.__init__(self, file, config, parsingResults, callerInterpreter)
        self.dbConnectionVariablesByIdentifier = {}
        self.unknownDbConnection = DatabaseConnection(None, None, None)
        self.db_connector = None
        self.parsingResults.dbConnections.append(self.unknownDbConnection)
        
    def add_require(self, assignment):
        
        firstCallPart = assignment.get_right_operand().functionCallParts[0]
        if firstCallPart.parameters and len(firstCallPart.parameters) == 1 and firstCallPart.parameters[0].is_string():
            name = firstCallPart.parameters[0].get_name()
            if name in ['oracledb', 'node-sqlserver', 'mssql', 'pg', 'my_connection']:
                self.db_connector = name
        
    def start_function_call(self, fcall):

        callParts = fcall.get_function_call_parts()
        firstCallPart = True

        for callPart in callParts:
            
            firstCallPartIdentifierCall = callPart.identifier_call
    
            if firstCallPartIdentifierCall.get_prefix_internal() or not firstCallPart:
    
                callName = firstCallPartIdentifierCall.get_name()
                
                if callName == 'open':
                    if self.db_connector:
                        self.manage_getConnection(callPart, fcall.parent)
                    
                # getConnection for oracledb
                # open or query for node-sqlserver
                # Connection for mssql
                # Client for pg
                elif self.db_connector and callName in ['getConnection', 'Connection', 'Client']:
                    self.manage_getConnection(callPart, fcall.parent)
    
                elif callName == 'query':
                    if self.db_connector:
                        if self.db_connector == 'node-sqlserver':  # deprecated https://www.npmjs.com/package/node-sqlserver
                            self.manage_getConnection(callPart, fcall.parent)
                            if len(callPart.parameters) >= 2:
                                self.manage_query(callPart, callPart.parameters[1])
                        elif self.db_connector in ['mssql', 'pg']:
                            if callPart.parameters:
                                self.manage_query(callPart, callPart.parameters[0])
                        elif self.db_connector == 'my_connection':
                            if callPart.parameters:
                                self.manage_query(callPart, callPart.parameters[0])
    
                elif self.db_connector and callName == 'queryRaw': # node-sqlserver
                    self.manage_queryRaw(callPart, callPart.parameters[0])
                        
                elif self.db_connector and callName == 'execute': # oracledb
                    self.manage_execute(callPart, callPart.parameters[0])

            else:
                pass
            
            firstCallPart = False
        
    def end_function_call(self):
            
        if self.get_current_context():
            if self.get_current_context().is_execute():
                self.end_execute()

    def manage_getConnection(self, firstCallPart, fcallParent):

        firstCallPartIdentifierCall = firstCallPart.identifier_call

        requireDeclaration = self.get_require_declaration(firstCallPartIdentifierCall)
        if requireDeclaration:

            if requireDeclaration.reference == 'oracledb':
                       
                if self.get_current_context():         
                    connection = DatabaseConnection(firstCallPart.parameters[0].get_name(), firstCallPart, self.get_current_context().get_current_function())
                else:
                    connection = DatabaseConnection(firstCallPart.parameters[0].get_name(), firstCallPart, None)
                self.parsingResults.dbConnections.append(connection)
                self.check_violation_dataservice_loop(firstCallPart)

                parentAssignment = fcallParent
                if parentAssignment.is_assignment():
                    leftOperand = parentAssignment.get_left_operand()
                    if leftOperand.get_resolutions():
                        self.dbConnectionVariablesByIdentifier[leftOperand.resolutions[0].callee] = connection
                elif parentAssignment.is_object_value():
                    pass

            elif requireDeclaration.reference == 'node-sqlserver':

                if self.get_current_context():         
                    connection = DatabaseConnection(firstCallPart.parameters[0].get_name(), firstCallPart, self.get_current_context().get_current_function())
                else:
                    connection = DatabaseConnection(firstCallPart.parameters[0].get_name(), firstCallPart, None)
                self.parsingResults.dbConnections.append(connection)
                parentAssignment = fcallParent

                self.check_violation_dataservice_loop(firstCallPart)

                if parentAssignment.is_assignment():
                    leftOperand = parentAssignment.get_left_operand()
                    if leftOperand.get_resolutions():
                        self.dbConnectionVariablesByIdentifier[leftOperand.resolutions[0].callee] = connection
                elif parentAssignment.is_object_value():
                    pass

    def manage_query(self, firstCallPart, queryParameter):
        self.manage_execute_query(firstCallPart, queryParameter)

    def manage_queryRaw(self, firstCallPart, queryParameter):
        self.manage_execute_query(firstCallPart, queryParameter)

    def manage_execute(self, firstCallPart, queryParameter):
        self.manage_execute_query(firstCallPart, queryParameter)

    def manage_execute_query(self, firstCallPart, queryParameter):

        firstCallPartIdentifierCall = firstCallPart.identifier_call
        self.check_violation_dataservice_loop(firstCallPart)
        
        executeContext = self.start_execute()
        if firstCallPartIdentifierCall.get_resolutions():
            queryStrings = []
            for resolution in firstCallPartIdentifierCall.get_resolutions():
                if resolution.callee in self.dbConnectionVariablesByIdentifier:
                    currentConnection = self.dbConnectionVariablesByIdentifier[resolution.callee]

                    # ex: connection.execute("select ...", function(err, result) {});
                    firstParam = queryParameter
                    queryString = firstParam.evaluate()
                    if not queryString in queryStrings:
                        queryStrings.append(queryString)
                        if queryString:
                            executeContext.connection = currentConnection
                            # envoi de la requete aux liens externes
                            self.find_external_links_from_queries(queryString, firstCallPart, currentConnection)
                else:
                    firstParam = queryParameter
                    queryString = firstParam.evaluate()
                    if not queryString in queryStrings:
                        queryStrings.append(queryString)
                        if queryString:
                            executeContext.connection = self.unknownDbConnection
                            # envoi de la requete aux liens externes
                            self.find_external_links_from_queries(queryString, firstCallPart, self.unknownDbConnection)
        else:
            firstParam = queryParameter
            queryString = firstParam.evaluate()
            if queryString:
                executeContext.connection = self.unknownDbConnection
                # envoi de la requete aux liens externes
                self.find_external_links_from_queries(queryString, firstCallPart, self.unknownDbConnection)
    
    def start_execute(self):
        self.push_context(ExecuteContext(self.get_current_context()))
        return self.get_current_context()
 
    def end_execute(self):
        self.pop_context()

    def find_external_links_from_queries(self, queries, ast, currentConnection):
        
        for query in queries:
            self.find_external_links_from_query(query, ast, currentConnection)

    def create_query_name_object(self, query, parent, position):

        name = parent.get_name() + '_' + 'SQLquery'

        query_object = CustomObject()

        query_object.set_name(name)

        query_object.set_type('CAST_SQL_NamedQuery')

        query_object.set_parent(parent.get_kb_object())

        name_file = position.get_file().get_path().split('\\')[-1]
        full_name = name + '_' + name_file + '_' + str(position.get_begin_line()) + '_' + str(position.get_begin_column()) + '_' + str(position.get_end_line()) + '_' + str(position.get_end_column())
        guid = query + '_' + str(position)

        query_object.set_guid(guid)
        query_object.set_fullname(full_name)
        query_object.save()

        query_object.save_position(position)

        query_object.save_property("CAST_SQL_MetricableQuery.sqlQuery", query)

        create_link('callLink', parent.get_kb_object(), query_object, position)

        return query_object

    def find_external_links_from_query(self, query, ast, currentConnection):
        
        func = None

        try:
            func = getattr(external_link, 'analyse_embedded')
        except AttributeError:
            pass

        if func:
            embeddedResults = func(query)
        else:
            embeddedResults = None

        position = Bookmark(self.file, ast.get_begin_line(), ast.get_begin_column(), ast.get_end_line(), ast.get_end_column())

        function_parent = self.get_current_context().get_current_function()
        
        if not function_parent:
            function_parent = ast
            while function_parent.parent and not isinstance(function_parent.parent, File):
                function_parent = function_parent.parent

        query_obj = self.create_query_name_object(query, function_parent, position)

        if not embeddedResults or not func:

            tables = extract_tables(query)
            for table in tables:
                tableName = table['name']
                tableOperation = table['operation']
                linkType = None
                if tableOperation == 'SELECT':
                    linkType = 'useSelectLink'
                elif tableOperation == 'DELETE':
                    linkType = 'useDeleteLink'
                else:
                    linkType = 'useLink'
                  
                tablesAreResolved = False
                tbls = None
                if not func:
                    try:
                        tbls = external_link.find_objects(tableName, 'Database Table')
                        if not tbls:
                            tbls = external_link.find_objects(tableName, 'Database View')
                        if tbls:
                            tablesAreResolved = True
                    except:
                        pass

                if tbls:
                    for tbl in tbls:
                        if tablesAreResolved:
                            currentConnection.linkSuspensions.append(LinkSuspension(linkType, query_obj, tbl, ast))
                        else:
                            currentConnection.linkSuspensions.append(LinkSuspension(linkType, query_obj, tableName, ast))
                else:
                    currentConnection.linkSuspensions.append(LinkSuspension(linkType, query_obj, tableName, ast))

        elif embeddedResults:
        
            for embeddedResult in embeddedResults:
                for linkType in embeddedResult.types:
                    currentConnection.linkSuspensions.append(LinkSuspension(linkType, query_obj, embeddedResult.callee, ast))
