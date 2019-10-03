"""
Define, register, and analyse generic Python quality rules
"""

from light_parser import Walker
from cast.analysers import CustomObject, Bookmark, log, create_link, external_link
from python_parser import is_dot_access, is_class, is_binary_operation, Array, Parenthesis,\
    is_identifier
from evaluation import evaluate_with_trace

def analyse(module):
    """
    Analyse an AST 
    """
    walker = Walker()
    walker.register_interpreter(SelectQueryInterpreter(module))
    walker.walk(module.get_ast())
    
class SqlQuery:
    """
    Object
    """
    def __init__(self, sql, ast, parentFullname):
        self.sql = sql
        self.ast = ast
        self.caller = None
        self.parentFullname = parentFullname
        self.name = None
        self.initialize_name()
    
    def initialize_name(self):
        max_words = 4
        if self.sql.upper().startswith(('EXEC', 'EXECUTE')):
            # we don't show parameters in the name for procedure calls
            max_words = 2
        truncated_sql = self.sql
        
        splitted = self.sql.split()
        if len(splitted) > max_words:
            truncated_sql = " ".join(splitted[0:max_words])
            
        self.name = truncated_sql

    def save(self, module):
        """
        Save to KB.
        """
            
        fullname = self.parentFullname + '/' + self.name
        checksum = self.ast.get_code_only_crc()
        position = Bookmark(module.get_file(), 
                            self.ast.get_begin_line(), 
                            self.ast.get_begin_column(), 
                            self.ast.get_end_line(), 
                            self.ast.get_end_column())

        library = module.get_library()
        
        query_object = CustomObject()
        query_object.set_name(self.name)
        
        query_object.set_type('CAST_SQL_NamedQuery')
        
        query_object.set_parent(module.get_kb_object())
         
        guid = module.get_final_guid(fullname)
        
        query_object.set_guid(guid)
        query_object.set_fullname(fullname)
        query_object.save()
        
        query_object.save_property('checksum.CodeOnlyChecksum', checksum)
        query_object.save_position(position)
        
        query_object.save_property("CAST_SQL_MetricableQuery.sqlQuery", self.sql)
          
        log.debug("SQL statement : {}".format(self.sql))
        
        for embedded in external_link.analyse_embedded(self.sql):
            for _type in embedded.types:
                create_link(_type, query_object, embedded.callee)
        
        create_link('callLink', self.caller, query_object, position)
        
        library.nbSqlQueries += 1


class SelectQueryInterpreter:
    """
    Interprets database queries that follow the Python Database API Specification -- PEP 249
    
    It searches for 'execute' method calls in instance objects. These instances are not
    validated as Cursor objects (or as any other non-standard connection objects). To
    avoid false positives the first argument of the method-call is required 
    to be a string starting with a consistent SQL statement: for example 
    the 'SELECT' (case insensitive) word. Leading white spaces are skipped.
    
    We allow expressions where many method calls are concatenated after the execute call:
        
        result = connection.execute("select * from orders").fetchall()
    
    Parameters in parameterized sql calls are not resolved:   

        result = cursor.execute("SELECT 2 WHERE ?=?", [1, 1])

    will return as sql statement "SELECT 2 WHERE ?=?". Similar behavior is found with 'executemany' method.
                        
    Limitations    
        - Arbitrary joined method/instance names are allowed next to execute: coco.execute(sql).toto()
        - When providing sql scripts to executescript, the 'newline' characters are lost in the returning
          sql_query string. The reason for this has to be found in 'evaluate' -> 'evaluate_string' where 
          the 'get_value' method of class 'Constant' is called joining the tokens.
               
    """
    
    
    # non-used: 'ANALYZE', 'ATTACH', 'COMMIT','REINDEX', 'RELEASE', 
    #           'ROLLBACK', 'SAVEPOINT','VACUUM', 'DETACH', 'PRAGMA'
    sql_stmt_keywords = [
        # sqlite    
        'ALTER TABLE', 'BEGIN',  'CREATE', 'DELETE', 
        'DROP', 'INSERT', 'SELECT', 'UPDATE', 'WITH',
        # + mysql
        'RENAME TABLE', 'TRUNCATE TABLE', 'EXEC', 'EXECUTE',
    ]
    
    def __init__(self,module):
        self.__module = module
      
        self.__symbol_stack = [module]
        
    
    def push_symbol(self, symbol):
        
        return self.__symbol_stack.append(symbol)
    
    def pop_symbol(self):
    
        self.__symbol_stack.pop()
    
    def get_current_symbol(self):
        
        return self.__symbol_stack[-1]
    
    def get_current_kb_symbol(self):
        
        return self.__symbol_stack[-1].get_kb_object()
    
    def start_ClassBlock(self, _ast_class):
        """
        Resolve class inheritances
        """
        _class = self.get_current_symbol().get_class(_ast_class.get_name(), _ast_class.get_begin_line())
        if not _class:
            
            log.warning("no class found for %s under %s" % (str(_ast_class.get_name()), str(self.get_current_symbol())))
        
        self.push_symbol(_class)
    
    def end_ClassBlock(self, _ast_class):
        self.pop_symbol()
    
    def start_FunctionBlock(self, ast_function):
        self.start_Function(ast_function)
    
    def start_FunctionOneLine(self, ast_function): 
        self.start_Function(ast_function)
    
    def start_Function(self,ast_function):
        name = ast_function.get_name()
        function = self.get_current_symbol().get_function(name, ast_function.get_begin_line())
        self.push_symbol(function)
    
    def end_FunctionBlock(self, ast_function):
        self.end_Function(ast_function)
            
    def end_FunctionOneLine(self, ast_function): 
        self.end_Function(ast_function)
                
    def end_Function(self, ast_function):
        self.pop_symbol()
        

    def extract_sql_parameters(self, method_call):
        
        try:
            parent = method_call.parent
        except:
            return  # skip issues with 'builtin' module
        
        method = method_call.get_method()
        
        if is_dot_access(method):
            
            name = method.get_name()
            
            #@todo: special parsing for executescript (comments, \n, ...)
            if not name in ['execute', 'executemany', 'executescript', 'prepare']:
                return
            
            parameters = method_call.get_parameters()
            
            if not parameters:
                return
            
            sql_param = method_call.get_argument(0, 'sql')
            evaluations = evaluate_with_trace(sql_param)
            
            if evaluations: #@todo: avoid NoneType returns in evaluations
                for value in evaluations:
                    sql = value.value.lstrip()  # remove leading spaces
                    value.value = sql
                    if any([sql.upper().startswith(kw) for kw in self.sql_stmt_keywords]):
                        yield value
        
        
    def start_MethodCall(self, method_call):
        """
        :type method_call: python_parser.MethodCall
        """
        if is_class(self.get_current_symbol()):
            return
        
        for sql_evaluation in self.extract_sql_parameters(method_call):
            sql = sql_evaluation.value
            
            module = self.__module
            
            query = SqlQuery(sql, method_call, self.__module.get_fullname())
            query.caller = self.get_current_kb_symbol()
            
            module.add_db_query(query)
