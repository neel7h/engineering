'''
Created on 17 oct. 2014

@author: MRO
'''
from sqlscript_lexer import SqlLexer, MySqlLexer, MSSqlLexer
from light_parser import Parser, BlockStatement, Statement, Seq, Optional, Or, Not, Token,\
    Term, Any, Node, NotFollowedBy
from symbols import Table, Column, ForeignKey, Index, Unknown, Function, Procedure, View, Trigger, Package, Type, \
    UniqueConstraint, FulltextConstraint, Schema, Event, Synonym, TableSynonym, ViewSynonym, FunctionSynonym, ProcedureSynonym, \
    PackageSynonym, TypeSynonym, Method
from parser_common import parse_identifier
from select_parser import SelectResult, parse_select, analyse_select, ExecuteImmediate, ExecuteDynamicCursor, \
    ExecuteDynamicString0, ExecuteDynamicString2, ExecuteDynamicString3, ExecuteDynamicString4, \
    ExecuteDynamicString5, ExecuteDynamicString6, Insert, FunctionCall
from pygments.token import Operator, String, Name, Punctuation, Keyword, Error
from cast.analysers import log, Bookmark
from variant import Variant
from traceback import format_exc
from sqlparse.sql import Parenthesis
from logger import warning
from light_parser import Lookahead, create_lexer
from sqlparse.tokens import Text
from sap_sqlscript_symbols import SAPMethodProcedure, SAPMethodFunction

def create_symbols_sap(text, database, variant=Variant.sapsqlscript, raise_error=True):
    for statement in parse(text, variant, False): 
        if statement and type(statement) != Token:
            temp = create_symbol(statement, database, raise_error)
            if temp:
                yield temp

def create_symbols(text, database, raise_error=True, variant=Variant.ansisql, sqlserver_with_go=False):
    """
    Register (and unregister) the symbols in the database    
    """
    has_ddl = False
    has_dml = False
    select_detected = False
    insert_detected = False
    only_alter = False
    has_execute = False
    mixed_accepted = True if variant not in (Variant.sapsqlscript, Variant.sqlserver) else False
    try:
        for statement in parse(text, variant, sqlserver_with_go):
            """
            When DML and DDL statements
                are mixed in the same file 
            """
            if mixed_accepted and not has_dml and \
               ( 
                   (statement.type == Keyword and \
                    statement in ('SELECT', 'UPDATE', 'DELETE', 'INSERT')
                    ) or \
                   statement == 'TRUNCATE'\
                   ):
                has_dml = True 
                if statement == 'SELECT':
                    select_detected = True 
                elif statement == 'INSERT':
                    insert_detected = True 
            elif has_dml and insert_detected and statement == 'VALUES':
                """
                Insert into ... values ... are generated only to initialize tables
                    the file should not be considered mixed
                """
                has_dml = False
                insert_detected = False
            elif has_dml and select_detected and statement in ('PG_CATALOG', 'SYSTYPES', 'SYSOBJECTS'):
                """
                SELECT pg_catalog.setval ... are generated only to initialize sequences
                    the file should not be considered mixed
                
                The same for the following SQL SERVER statement with ; as separator, detected as AnsiSQL:
                IF NOT EXISTS(SELECT name FROM systypes WHERE name = N'id')
                    exec sp_addtype N'id', 'varchar(11)', 'NOT NULL'
                    ;
                """
                has_dml = False
                select_detected = False
            elif mixed_accepted and not has_execute and statement in ('EXEC', 'EXECUTE'):
                has_execute = True
            elif type(statement) != Token and not isinstance(statement, (GrantAllStatement, GrantStatement, CreateDatabaseLink, CreateSequence, CommentOn)):                 
                symbol = create_symbol(statement, database, raise_error) 
                if symbol and isinstance(statement, ExecuteDynamicStringBlock):
                    symbol.use_ast_for_dynamic_code(symbol.begin_line, symbol.begin_column, symbol.end_line, symbol.end_column)
                    has_ddl = True
                elif symbol:
                    try:
                        symbol.use_ast()
                    except TypeError:
                        pass
                    
                    if not isinstance(statement, (AlterStatement)):
                        has_ddl = True
    
                if isinstance(statement, CreateSynonym):
                    symbol = create_symbol_specific_synonym(statement, database, raise_error)
                    if symbol and isinstance(statement, CreateSynonym):
                        symbol.use_ast()
            elif isinstance(statement, (GrantAllStatement, GrantStatement, CreateDatabaseLink, CreateSequence, CommentOn)) and not has_ddl:
                has_ddl = True

            if isinstance(statement, (AlterStatement)) and not has_ddl:
                only_alter = True
        
        if only_alter and not has_ddl:
            has_ddl = True
            if has_execute and not has_dml:
                has_dml = True
        
    except:
        log.info('Issue with parse in create_symbols %s' % format_exc())

    return has_ddl, has_dml

def analyse_symbols(text, database, raise_error=True, variant=Variant.ansisql, sqlserver_with_go=False, impact_analysis=False):
    """
    Second pass : analyze the content and return the 'reanalyzed' symbols.
    Returns list of views and procedures
    """
    for statement in parse(text, variant, sqlserver_with_go):
        if type(statement) != Token and not isinstance(statement, (BeginPostgresqlStatement, CreateTableStatement, CreateDatabaseLink, \
                                                                    CreateSequence, GrantAllStatement, GrantStatement, DropTableStatement, \
                                                                    RenameTableStatement, Case, CommentOn, AlterStatement)):
            try:
                yield from analyse_symbol(statement, database, raise_error, None, variant, impact_analysis)  
            except (GeneratorExit, TypeError):
                pass

def get_longest_lenght_line(tokens):
    lenght = 0
    for token in tokens:
        if isinstance(token, Node):
            deep_token = token.get_children()
            lenght = max(get_longest_lenght_line(deep_token), lenght)
        else:
            try:
                lenght = max(token.end_column, lenght)
            except:
                break
            
    return(lenght)
            
def parse(text, variant=Variant.ansisql, sqlserver_with_go=False):
    """
    Parse the text and return high level AST nodes  
    """
    
    # set current schema
    schema_changes = [SearchPath, AlterSessionSetCurrentSchema, SetCurrentSchema]
    if variant != Variant.sqlserver:
        schema_changes.append(UseDatabase)

    # Case should be kept close to Block statement because it could end with a simple END, like blocks
    if variant == Variant.sqlserver and sqlserver_with_go:
        parser = Parser(MSSqlLexer,
                        schema_changes,
                        [GoSeparator, RevokeStatement, GrantStatement, CreateBlockTableStatement],
                        [ExecuteDynamicStringBlock],# first step grouping
                        [CreateSynonym, MSProcedureStatement, MSFunctionStatement, MSCreateTriggerStatement],
                        [Block, Case],
                        [CreateTableStatement, MSCreateViewStatement],
                        [CreateIndexStatement, 
                         GrantAllStatement, CreateSequence,
                         AlterStatement, DropTableStatement, RenameTableStatement]
                        )
    elif variant == Variant.postgresql:
        parser = Parser(SqlLexer,
                        schema_changes,
                        [GrantStatement, RevokeStatement, BeginPostgresqlStatement],
                        [Block, PostgresqlBlock, Case],# first step grouping
                        [CommentOn, GrantAllStatement, CreateSequence, 
                         CreateTableStatement, AlterStatement, CreateIndexStatement,
                         ProcedureStatement, FunctionStatement, PGCreateTriggerStatement, PGCreateRuleStatement,
                         CreateViewStatement, 
                         DropTableStatement, RenameTableStatement] # statements
                        )
    elif variant == Variant.mysql:
        parser = Parser(MySqlLexer,
                        schema_changes,
                        [GrantStatement, RevokeStatement],
                        [Block, Case],# first step grouping
                        [CommentOn, CreateTableStatement, CreateIndexStatement, 
                         ProcedureStatement, FunctionStatement, CreateTriggerStatement, EventStatement, 
                         CreateViewStatement, CreateSequence,
                         AlterStatement, DropTableStatement, RenameTableStatement,
                         TypeHeader], # statements
                        {PackageBody:[FunctionBodyStatement,ProcedureBodyStatement]}
                        ) 
    elif variant == Variant.oracle:
        parser = Parser(SqlLexer,
                        schema_changes,
                        [GrantStatement, RevokeStatement],
                        [Block, Case],# first step grouping
                        [PackageHeader],
                        [CommentOn, Define, GrantAllStatement, CreateSequence, CreateTableStatement, CreateIndexStatement, \
                         ProcedureStatement, FunctionStatement, CreateTriggerStatement, EventStatement, 
                         CreateViewStatement, PackageBody, TypeBody,
                         AlterStatement, DropTableStatement, RenameTableStatement,
                         CreateSynonym, CreateDatabaseLink, TypeHeader], # statements
                        {TypeBody:[MethodBodyStatement], PackageBody:[FunctionBodyStatement,ProcedureBodyStatement]}
                        )
    elif variant == Variant.db2:
        parser = Parser(SqlLexer, 
                        schema_changes,
                        [GrantStatement, RevokeStatement],
                        [Block, Case],# first step grouping
                        [CommentOn, GrantAllStatement, CreateSequence, CreateTableStatement, CreateIndexStatement,
                         ProcedureStatement, FunctionStatement, DB2CreateTriggerStatement, CreateTriggerStatement,
                         CreateViewStatement, 
                         AlterStatement, DropTableStatement, RenameTableStatement,
                         CreateSynonym, CreateDatabaseLink,
                         DB2CreateUserStatement, DB2CreateWrapperStatement, DB2CreateServerStatement] # statements
                        ) 
    elif variant == Variant.sapsqlscript:
        parser = Parser(SqlLexer, 
                        [Block],
                        [SAPSqlScriptProcedureStatement, SAPSqlScriptFunctionStatement] # statements
                        )        
    else:
        parser = Parser(SqlLexer, 
                        schema_changes,
                        [GrantStatement, RevokeStatement, CreateBlockTableStatement],
                        [Block, PostgresqlBlock, Case],# first step grouping
                        [PackageHeader],
                        [CommentOn, Define, GrantAllStatement, CreateSequence, CreateTableStatement, CreateIndexStatement, \
                         ProcedureStatement, FunctionStatement, CreateTriggerStatement, EventStatement, \
                         TeradataProcedureStatement,
                         CreateViewStatement, ReplaceViewStatement, PackageBody, TypeBody,
                         AlterStatement, DropTableStatement, RenameTableStatement,
                         CreateSynonym, CreateDatabaseLink, TypeHeader], # statements
                        {TypeBody:[MethodBodyStatement], PackageBody:[FunctionBodyStatement,ProcedureBodyStatement]}
                        )   
    
    return parser.parse(text)


###############
## First step
###############
 
class Parenthesis (BlockStatement):  
    begin = Seq('(', Any(), NotFollowedBy(','))
    end = ')'
            
class Block(BlockStatement):
    """
    Classical block
    
    end loop etc.. are hanlded by lexer 
    """
    
    begin = 'BEGIN'
    end   = 'END'

class BeginPostgresqlStatement(Term):
    match = Seq('BEGIN', ';')
    
class GoSeparator (Term):
    # Microsoft GO separator
    match = 'GO'
    
class PostgresqlBlock(BlockStatement):
    """
    Block for postgresl
    
    Those are the pattern seen in examples and exports
        AS $$
        ...
        $$;
    
        AS $$
        ...
        $$ LANGUAGE ....
    
    $$ ... $$ clashes with some mysql patterns 
    
    """
     
    begin = Seq('AS', '$','$')
    end   = Seq('$','$', Or(';', 'LANGUAGE'))

class Define(Statement):
    stopped_by_other_statement = True
    begin = Seq('DEFINE', Any(), '=', Any())
    end   = ';'

    def __init__(self):
        Statement.__init__(self)
 
# Case should be kept because it is the only statement with a possible END at the end, like the classical Blocks
class Case(BlockStatement):
     
    begin = Seq('CASE', NotFollowedBy(Or('OR', Seq('N', '('))))
    end   = Or('END CASE', 
               'END CASE ',
               'END CASE;', 
               'END')
    
class ExecuteDynamicStringBlock(Term):
    match = Seq(Optional('BEGIN'), Or('EXECUTE', 'EXEC', 'CALL'), Optional('dbo'),Optional('.'), Or('sp_executesql', 'execute_prepared_stmt'), Optional('@statement'), Optional('='), Optional('N'), Or("'", '"', String))

    # create procedure functions in dynamic ms sql strings
    def on_end(self):
        try:
            ProcedureLikeStatement.on_end(self)
        except:
            print('issue with ProcedureLikeStatement in ExecuteDynamicStringBlock')
            pass
    
class PackageHeader(Statement):
    
    begin = Seq('CREATE',
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('EDITIONABLE', 'NONEDITIONABLE')),
                'PACKAGE', 
                Not('BODY')
                )
    end   =  Or('END', Seq(Token('\n', Text), Token('/', Operator)), 'WRAPPED')

class PackageBody(Statement):
    
    begin = Seq('CREATE', 
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('EDITIONABLE', 'NONEDITIONABLE')),
                'PACKAGE', 
                'BODY')
    end   = Or('END', Seq(Token('\n', Text), Token('/', Operator)))
    
    stopped_by_other_statement = True

    def __init__(self):
        BlockStatement.__init__(self)
        self.name = None

    def on_end(self):
        tokens = self.get_children() 
        tokens.move_to('BODY')
        self.name = parse_identifier(tokens, force_parse=True)
        self.name.types = [Package]

class TypeLikeStatement(Statement):
    
    def __init__(self):
        BlockStatement.__init__(self)
        self.name = None
        self.superTypeName = None
        self.object_type_name = None
        self.useTypeName = None
               
class TypeBody(TypeLikeStatement):
    
    begin = Seq('CREATE', 
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('EDITIONABLE', 'NONEDITIONABLE')),
                'TYPE', 
                'BODY')
    end   = Or('END', Seq(Token('\n', Text), Token('/', Operator)))
    
    stopped_by_other_statement = True

    def __init__(self):
        BlockStatement.__init__(self)
        self.name = None

    def on_end(self):
        tokens = self.get_children() 
        tokens.move_to('BODY')
        self.name = parse_identifier(tokens, force_parse=True)
        self.name.types = [Type] 
               
class TypeHeader(TypeLikeStatement):
    
    begin = Seq('CREATE', 
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('EDITIONABLE', 'NONEDITIONABLE')), 
                'TYPE', 
                NotFollowedBy('BODY'))
    end   =  Or(';', Token('/', Operator), Seq(Optional('NOT'), 'FINAL'), ')')
    
    stopped_by_other_statement = True

    def __init__(self):
        TypeLikeStatement.__init__(self)
        
    def on_end(self):
        tokens = self.get_children() 
        tokens.move_to('TYPE')
        self.name = parse_identifier(tokens, force_parse=True)
        self.name.types = [Type] 
        self.object_type_name = self.name.get_name()

        tokens.move_to(['UNDER', 'OBJECT', 'TABLE'])
        try:
            from builtins import str
            if tokens.look_next().text == '(':
                # same name as the object name
                self.superTypeName  = self.object_type_name   
            elif tokens.look_next().text.upper() == 'OF':
                next(tokens)
                self.useTypeName  = tokens.look_next()     
            elif type(tokens.look_next().text) == str:
                self.superTypeName  = tokens.look_next().text
        except:
            print('issue with on_end in TypeHeader statement')
            pass
    
###############
## Second step
###############
class AlterSessionSetCurrentSchema(Term):
###############
#
# ALTER SESSION SET CURRENT_SCHEMA = <schema name>
# 
###############
    match = Seq('ALTER', 'SESSION', 'SET', 'CURRENT_SCHEMA', '=',  Or(String, Name))


class SetCurrentSchema(Term):
###############
# 
#         .-CURRENT-.          .-=-.                        
# >>-SET--+---------+--SCHEMA--+---+--+-schema-name-----+--------><
#                                     +-USER------------+   
#                                     +-SESSION_USER----+   
#                                     +-SYSTEM_USER-----+   
#                                     +-CURRENT_USER----+   
#                                     +-host-variable---+   
#                                     '-string-constant-'  
###############
    match = Seq('SET', Optional('CURRENT'), 'SCHEMA', Optional('='),  Or(String, Name))

    
class UseDatabase(Term):
###############
# USE
# { database_name }
# 
# [;]
###############
    match = Seq('USE', Optional('['), Or(String, Name), Optional(']'))


class SearchPath(Statement):
###############
# SET [ SESSION | LOCAL ] configuration_parameter { TO | = } { value | 'value' | DEFAULT }
###############

    begin = Seq('SET', Optional(Or('SESSION','LOCAL')), 'search_path', Or('TO', '='))
    end   = ';'
    
    stopped_by_other_statement = True


class GrantAllStatement(Statement):
    
    begin = Seq('GRANT', Or(Name, 'CONNECT', 'DROP', 'SELECT', 'UNLIMITED', 'ALTER', 'EXECUTE', 'READ', 'ADMINISTER', 
                            'BACKUP', 'GRANT', 'BECOME', 'AUDIT', 'INSERT', 'UPDATE', 'DELETE', 'GLOBAL', 'ANALYZE', 'EXECUTE_CATALOG_ROLE', 
                            'SELECT_CATALOG_ROLE', 'IMP_FULL_DATABASE', 'EXP_FULL_DATABASE', 'RESOURCE', 'RESUMABLE', 'PROXY', 'ALL', 'EVENT', 
                            'FILE', 'INDEX', 'LOCK', 'PROCESS', 'REFERENCES', 'RELOAD', 'REPLICATION', 'SHOW', 'SHUTDOWN', 'SUPER', 'TRIGGER',
                            'USAGE', 'CONTROL', 'ACCESSCTRL', 'BINDADD', 'CREATETAB', 'CREATE_EXTERNAL_ROUTINE', 'CREATE_NOT_FENCED_ROUTINE', 
                            'CREATE_SECURE_OBJECT', 'DATAACCESS', 'DBADM', 'EXPLAIN', 'IMPLICIT_SCHEMA', 'LOAD', 'QUIESCE_CONNECT', 'SECADM',
                            'SQLADM', 'WLMADM', 'BIND', 'ALTERIN', 'CREATEIN', 'DROPIN', 'USAGE', 'PASSTHRU', 'USE', 'TRUNCATE', 'TEMPORARY',
                            'TEMP'))
    # / is more like a statement separator
    end   = Or(GoSeparator, ';', Seq(Token('\n', Text), Token('/', Operator)))

    stopped_by_other_statement = True

class GrantStatement(Statement):
    
    begin = Seq('GRANT', 'CREATE')
    # / is more like a statement separator
    end   = Or(';', GoSeparator, Seq(Token('\n', Text), Token('/', Operator)))

    stopped_by_other_statement = True

class RevokeStatement(Statement):
    
    begin = Seq('REVOKE', 'CREATE')
    # / is more like a statement separator
    end   = Or(';', GoSeparator, Seq(Token('\n', Text), Token('/', Operator)))

    stopped_by_other_statement = True

class CommentOn(Statement):
    
    begin = Seq('COMMENT', 'ON')
    end   = Or(';', GoSeparator, Seq(Token('\n', Text), Token('/', Operator)), '%')
    
    stopped_by_other_statement = True
    
class CreateSequence(Statement):
    
    begin = Seq(Or('CREATE', 'ALTER', 'DROP'), 
                Optional(Seq('OR', 'REPLACE')), 
                Optional('TEMPORARY'), 
                'SEQUENCE')
    end   = Or(';', GoSeparator, Seq(Token('\n', Text), Token('/', Operator)), '%')

    stopped_by_other_statement = True

class CreateDatabaseLink(Statement):
    
    begin = Seq('CREATE', 
                Optional('SHARED'), 
                Optional('PUBLIC'), 
                'DATABASE',
                'LINK')
    end   = Or(';', GoSeparator, Seq(Token('\n', Text), Token('/', Operator)))

    stopped_by_other_statement = True
           
# the case of synonyms , aliases and nicknames
class CreateSynonym(Statement):
    
    begin = Seq('CREATE', 
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('EDITIONABLE', 'NONEDITIONABLE')),
                Optional(Or('PRIVATE', 'PUBLIC')), 
                Or('SYNONYM', 'ALIAS', 'NICKNAME'),
                Optional(Seq('IF', 'NOT', 'EXISTS')),
                )

    # / is more like a statement separator
    end   = Or(GoSeparator, ';', Seq(Token('\n', Text), Token('/', Operator)))
    
    stopped_by_other_statement = True

    def __init__(self):
        Statement.__init__(self)
        self.name = None
        self.object = None
        self.kind_of_synonym = None
                
# the case of SQL Server extraction with default options will export tables in begin end blocks
class CreateBlockTableStatement(Statement):
    
    begin = Seq('BEGIN', 'CREATE', 'TABLE',
                 Or(Any(),
                    Seq(Any(), Token('.', Punctuation), Any()),
                    Seq(Any(), Token('.', Punctuation), Any()), Token('.', Punctuation), Any()
                         ), 
                 NotFollowedBy('AS')
                )
    end   = Seq('END', 'GO')
    
    stopped_by_other_statement = True
    def __init__(self):
        Statement.__init__(self)
        self.hasPrimaryKey = 0
        
class CreateTableStatement(Statement):
    
    begin = Seq(Or('CREATE', 'DECLARE'), 
                Optional(Or('SET', 'MULTISET')),  
                Optional(Or('GLOBAL', 'LOCAL')), 
                Optional(Or('TEMPORARY', 'TEMP')), 
                'TABLE', 
                Optional('IF'), 
                Optional('NOT'), 
                Optional('EXISTS'), 
                Or(Seq(Any(), Token('.', Punctuation), Any()), Token('.', Punctuation), Any(),
                   Seq(Any(), Token('.', Punctuation), Any()),
                   Any()), 
                NotFollowedBy('AS')
                )
    # / is more like a statement separator
    end   = Or(GoSeparator, ';', Seq(Token('\n', Text), Token('/', Operator)))
    
    stopped_by_other_statement = True
    def __init__(self):
        Statement.__init__(self)
        self.hasPrimaryKey = 0
    
class GroupViewStatement(Statement):
    def __init__(self):
        Statement.__init__(self)
        self.name = None
        self.columns = []
        self.query = None
        self.longest_lenght_line = 0

    def get_query(self):
        """
        Get the query of the view
        """
        return self.query
    
    def on_end(self):
        
        tokens = self.get_children() 
        lines = self.get_tokens()
        self.longest_lenght_line = get_longest_lenght_line(lines)
        
        tokens.move_to('VIEW')
        
        """
        Search for view name
        """
        self.name = parse_identifier(tokens, force_parse=True)
        
        match = tokens.move_to(['(', 'AS'])
        
        try:
            if match.text == '(':
             
                """
                Search for columns
                """
                while True:
                     
                    column_name = parse_identifier(tokens).get_name()
                     
                    if column_name:
                        
                        self.columns.append(column_name)
                     
                    token = tokens.move_to([',', ')', '('])
                    if token == '(':
                        token = tokens.move_to(')')
                        token = tokens.move_to([',', ')'])
                     
                    if token and token == ')':
                        break
                token = tokens.move_to('AS')
        except AttributeError:
            pass                 

        # store the query...
        try:
            token = next(tokens) 
        except StopIteration:
            pass
        
        self.query = []
        try:
            while True:
                self.query.append(token)
                token = next(tokens) 
        except (StopIteration, UnboundLocalError):
            pass     
           
class CreateViewStatement(GroupViewStatement):
    stopped_by_other_statement = True
    
    begin = Seq('CREATE', 
                Optional('MATERIALIZED'), 
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('TEMP','TEMPORARY')), 
                Optional('NOFORCE'), Optional('FORCE'), # Oracle
                Optional(Or('EDITIONING', Seq('EDITIONABLE', Optional('EDITIONING')), 'NONEDITIONABLE')), # Oracle
                Optional(Seq('ALGORITHM','=', Or('UNDEFINED', 'MERGE', 'TEMPTABLE'))), # for mariaDB
                Optional(Seq('DEFINER','=', 'CURRENT_USER')), # for mariaDB
                Optional(Seq('DEFINER','=', Any(),'@', Any())), # for mariaDB
                Optional(Seq('SQL','SECURITY', Or('DEFINER', 'INVOKER'))), # for mariaDB
                Optional('RECURSIVE'), # for Teradata
                'VIEW',
                NotFollowedBy('LOG'))

    # / is more like a statement separator
    end   = Or(';', 'GO', Seq(Token('\n', Text), Token('/', Operator)))
    
# Teradata statement
class ReplaceViewStatement(GroupViewStatement):
    stopped_by_other_statement = True
    
    begin = Seq('REPLACE', # REPLACE VIEW
                Optional('RECURSIVE'), # for Teradata
                'VIEW')

    end   = ';'
    
class MSCreateViewStatement(GroupViewStatement):
    stopped_by_other_statement = True
    begin = Seq('CREATE', 
                Optional('MATERIALIZED'), 
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('TEMP','TEMPORARY')),
                'VIEW')
    end = GoSeparator

class CreateIndexStatement(Statement):
    
    begin = Seq('CREATE', 
                Optional('TYPE'),
                Optional(Or('1', '2')),
                Optional(Or('UNIQUE', 'BITMAP', 'FULLTEXT', 'SPATIAL', 'HASH')), 
                Optional(Or('NONCLUSTERED', 'CLUSTERED')), 
                'INDEX')

    # / is more like a statement separator
    end   = Or(';', GoSeparator, Seq(Token('\n', Text), Token('/', Operator)))
    
    stopped_by_other_statement = True

class AlterStatement(Statement):
    """Parse alter"""
    begin = Seq('ALTER', Or('TABLE', 'FUNCTION', 'VIEW', 'PROCEDURE', 'EVENT', 'INDEX', 'TRIGGER'))
    # / is more like a statement separator
    end   = Or(';', GoSeparator, Token('/', Operator), Seq(Token('\n', Text), Token('/', Operator)))
    
    stopped_by_other_statement = True

class DropTableStatement(Statement):
    """Parse drop table"""
    begin = Seq('DROP', Optional('TEMPORARY'), 'TABLE')
    # / is more like a statement separator
    end   = Or(';', GoSeparator, Seq(Token('\n', Text), Token('/', Operator)))
    
    stopped_by_other_statement = True
    
class RenameTableStatement(Statement):
    "Parse rename table"
    begin = Seq('RENAME', 'TABLE')
    # / is more like a statement separator
    end   = Or(';', GoSeparator, Seq(Token('\n', Text), Token('/', Operator)))
    
    stopped_by_other_statement = True   # xxx need verification

class GroupTriggerStatement(Statement):
    
    def __init__(self):
        Statement.__init__(self)
        self.events = None
        self.table = None
                       
    def on_end(self):
        self.name.types = [Trigger]
        
        table_name = None
        tokens = self.get_children()
        # search the commands : INSERT/UPDATE/DELETE
        command = tokens.move_to(['INSERT', 'UPDATE', 'DELETE', 'TRUNCATE', 'ON'])
        
        if command and command.text.upper() == 'ON':
            table_name = parse_identifier(tokens)
            
            # on is before the command
            command = tokens.move_to(['INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'])
        
        if command:
            # a trigger can be applied for several commands : 
            # AFTER INSERT OR DELETE OR UPDATE 
            commands = [command]
            
            # here command is in ['INSERT', 'UPDATE', 'DELETE']
            while (tokens.look_next().text.upper() == 'OR' or tokens.look_next() == ','):

                next(tokens)
                commands.append(next(tokens))
        
            self.events = commands
        
        if not table_name:
            # search the table ON table_name
            tokens.move_to('ON')
            table_name = parse_identifier(tokens)
        
        self.table = table_name
        self.content = tokens
        
class ProcedureLikeStatement(Statement):
    
    def __init__(self):
        Statement.__init__(self)
        self.name = None
        self.content = None
        self.count_parameters = 0
        self.count_quoted = 0
        self.longest_lenght_line = 0
        self.default_parameters = 0
        self.external_name = None
        self.external_position = None
        self.language = None
       
    def on_end(self):
        def countParemetersInParenthesis (self):  
            count_parameters = 0
            for t in self.get_children():
                if isinstance(t, Parenthesis):
                    continue
                if count_parameters == 0:
                    count_parameters += 1
                    continue
                if count_parameters >= 1 and t ==',':
                    count_parameters += 1
                    continue
            return(count_parameters)
                                    
        tokens = self.get_children()
        try:
            lines = self.get_tokens()
        except:
            lines = None
        if lines:
            self.longest_lenght_line = get_longest_lenght_line(lines)
        
        tokens.move_to(['PROCEDURE', 'SAP_SQLSCRIPT', 'SAP_SQLSCRIPT_FUNCTION', 'PROC', 'FUNCTION', 'TRIGGER', 'EVENT'])
        self.name = parse_identifier(tokens) 
        self.content = tokens
        parameters = self.get_children() 
        alltokens = self.get_children()
                             
        # count parameters, only for procedure and functions
        try:
            opp = False
            clp = False
            head = False
            for t in parameters:
#                 print('t in parameters : ', t)
                # count default parameters
                if t in ('DEFAULT', '='):
                    self.default_parameters += 1

                if isinstance(t, (Block, PostgresqlBlock)) or t in ('declare', 'as', 'is', 'event', 'trigger', 'return', 'returns', 'with', '$'):
                    if t == 'AS':
                        try:
                            t = parameters.look_next()
                        except StopIteration:
                            break
                        if t.type == Keyword or isinstance(t, (Block, PostgresqlBlock)):
#                             print('    break : t is Keyword : ', t)
                            break
                        # if is not a datatype
                        elif not ('int' in str(t).lower() or 'char' in str(t).lower() or 'date' in str(t).lower() or \
                                  'time' in str(t).lower() or 'numeric' in str(t).lower() or 'bit' in str(t).lower() or\
                                  'float' in str(t).lower()):
#                             print('    break : t is not a datatype : ', t)
                            break
                    elif 'with' not in str(t).lower():
#                         print('    break : else : ', t)
                        break
                if isinstance(t, Parenthesis):
                    head = False
                    self.count_parameters += countParemetersInParenthesis (t)
#                     print('    break : t is Parenthesis : ', t)
                    break
                if t in ('create','procedure', 'proc', 'function', 'definer', 'root') :
                    head = True
                    # reset counter and parenthesis
                    opp = False
                    self.count_parameters = 0
                    self.default_parameters = 0
                    continue

                if (t == '(' or str(t).find('@') > 0) and not opp:
                    if str(t).find('@') >= 0 and len(str(t)) == 1 and not head:
                        parameters.move_to(['PROCEDURE', 'PROC', 'FUNCTION', 'TRIGGER', 'EVENT'])
                    elif str(t).find('@') >= 0 and len(str(t)) > 1:
                        head = True
                        opp = True
                        self.count_parameters += 1
                        continue
                    else:
                        opp = True
                        head = True
                        continue 
                    
                if t == '(' and opp:
                    parameters.move_to(')')
                    continue
                elif not opp and not head:
#                     print('    break : not opp and not head : ', t)
                    break
                if t == ')' and opp:
                    clp = True
#                     print('    break : t is ) and opp : ', t)
                    break 
                if self.count_parameters == 0 and not clp and opp:
                    self.count_parameters += 1
                    continue
                if self.count_parameters >= 1 and not clp and opp and t ==',':
                    self.count_parameters += 1
                    continue
        except:
            log.info('Internal issue when counting parameters, because of %s ' % format_exc())
            pass

        try:
            # variable name
            prevIsString = False
            # previous token
            prevToken = None
            i = 0
            # count distinct
            quotedList=[i, '']
            # check if is in the list
            # only the first element after the variable name
            iSymbol = 0
            cursorDetected = False
            for t in alltokens:
                if t in ('AS', 'IS', 'BEGIN'):
                # this is the case of EXTERNAL PROGRAMS called in ORACLE
                    try:
                        t = alltokens.look_next()
                    except StopIteration:
                        break
                    if t == 'LANGUAGE':
                        next(alltokens)
                        t = alltokens.look_next()
                        self.language = t.text 
                        next(alltokens)
                        
                        try:
                            t = alltokens.look_next()
                        except StopIteration:
                            break
                        if t == 'NAME':
                            next(alltokens)
                            try:
                                t = alltokens.look_next()
                            except StopIteration:
                                break

                            if t.type == String.Single:
                                self.external_name = t.text[1:-1]
                            else:
                                self.external_name = t.text
                            self.external_position = '%s %s %s %s' % (t.begin_line, t.begin_column, t.end_line, t.end_column)
 
                    break
                
                if t == 'EXTERNAL' and not self.external_name and not self.external_position:
                    next(alltokens)
                    try:
                        t = alltokens.look_next()
                    except StopIteration:
                        break

                    if t.type == String.Single:
                        self.external_name = t.text[1:-1]
                    else:
                        self.external_name = t.text

                    if self.external_name and self.external_name.lower() in ('contains', 'return', 'reads'):
                        self.external_name = None

                    try:
                        if self.external_name:
                            self.external_position = '%s %s %s %s' % (t.begin_line, t.begin_column, t.end_line, t.end_column)
                    except AttributeError:     
                        pass
                    
                if t == 'LANGUAGE':
                    try:
                        t = alltokens.look_next()
                    except StopIteration:
                        break
                    self.language = t.text       
                            
                #db2 case SPECIFIC "NAME_OF_THE_PROCEDURE"
                if t.text and t.text == 'SPECIFIC':
                    next(alltokens)
                    try:
                        t = alltokens.look_next()
                    except StopIteration:
                        break
#                 print('all tokens : ', t, 'prevIsString is string', prevIsString)
                i += 1
                try:
                    if t.text.upper() == 'CURSOR':
                        cursorDetected = True
                        continue
                except AttributeError:
                    pass
                if cursorDetected and t == ';':
                    cursorDetected = False
                    continue
                if  cursorDetected and t != ';':
                    continue
                if t.type == String.Symbol:
                    prevToken = t
                    prevIsString = True 
                    iSymbol = i
                if t.type in (Name, Name.Builtin) and prevIsString and prevToken and iSymbol + 1 == i and t not in ('columns', '@', 'wrapped') and t.text not in ('FUNCTION', 'PRINT', 'EVENT', 'NEW', 'OLD', 'ORDER'):
                    try:
                        _ = quotedList.index(prevToken)
                    except:
                        self.count_quoted += 1
                        quotedList.insert(i, prevToken)
                        prevIsString = False
                        prevToken = None
                        iSymbol = 0
                elif prevIsString and prevToken and iSymbol + 1 == i and t.text in ('FUNCTION', 'PRINT', 'EVENT', 'NEW', 'OLD'):
                    prevIsString = False
                    prevToken = None
        except:
            log.info('Internal issue when counting quoted identifiers, because of %s ' % format_exc())
            pass 
        
        quotedList = None
        
class ProcedureBodyStatement(ProcedureLikeStatement):
    begin = 'PROCEDURE'
    end   = Or(Block, PostgresqlBlock)

    # procedures do not contain procedure
    # it does not contain substatement except inside block 
    stopped_by_other_statement = True

    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        self.name.types = [Procedure]
# Seq(Or('MEMBER', 'STATIC', Seq('MAP', 'MEMBER'), Seq('ORDER', 'MEMBER')), 'PROCEDURE')
# OO for object types
class MethodBodyStatement(ProcedureLikeStatement):
    begin = Seq(Or('CONSTRUCTOR', 'MEMBER', 'STATIC', Seq('OVERRIDING', 'MEMBER'), Seq('MAP', 'MEMBER'), Seq('ORDER', 'MEMBER')), Or('FUNCTION', 'PROCEDURE'))
    end   = Or(Block, PostgresqlBlock)

    stopped_by_other_statement = True

    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        self.name.types = [Method]
   
class FunctionBodyStatement(ProcedureLikeStatement):
    begin = 'FUNCTION'
    end   = Or(Block, PostgresqlBlock)

    # procedures do not contain procedure
    # it does not contain substatement except inside block 
    stopped_by_other_statement = True

    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        self.name.types = [Function]

class EventStatement(ProcedureLikeStatement):# for mariaDB
    
    begin = Seq('CREATE', 
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Seq('DEFINER','=', 'CURRENT_USER')), # for mariaDB
                Optional(Seq('DEFINER','=', String.Symbol,'@', String.Symbol)), 
                'EVENT')
    end   = Or(Block, PostgresqlBlock)

    # events do not contain event
    # it does not contain substatement except inside block 
    stopped_by_other_statement = True

    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        self.name.types = [Event]
 
class GroupProcedureStatement(ProcedureLikeStatement):
    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        self.name.types = [Procedure]
                          
class ProcedureStatement(ProcedureLikeStatement):
    begin = Seq('CREATE', 
                Optional(Seq('DEFINER','=', 'CURRENT_USER')), # for mariaDB
                Optional(Seq('DEFINER','=', String.Symbol,'@', String.Symbol)), # for mariaDB
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('EDITIONABLE', 'NONEDITIONABLE')),
                Or('PROCEDURE', 'PROC'))
    end   = Or(Block, PostgresqlBlock, 'WRAPPED', Seq('END', 'PROCEDURE', ';'))
    
    # procedures do not contain procedure
    # it does not contain substatement except inside block 
    stopped_by_other_statement = True

    def on_end(self):
        GroupProcedureStatement.on_end(self)

class SAPSqlScriptProcedureStatement(ProcedureLikeStatement):
    begin = 'SAP_SQLSCRIPT'
    end   = Seq('END', 'SAP_SQLSCRIPT', ';')
    
    # procedures do not contain procedure
    # it does not contain substatement except inside block 
    stopped_by_other_statement = True

    def on_end(self):
        GroupProcedureStatement.on_end(self)
        self.name.types = [Procedure]

class TeradataProcedureStatement(ProcedureLikeStatement):
    begin = Seq('REPLACE', 
                Or('PROCEDURE', 'PROC'))
    end   =  Block
    
    # procedures do not contain procedure
    # it does not contain substatement except inside block 
    stopped_by_other_statement = True

    def on_end(self):
        GroupProcedureStatement.on_end(self)
        
class SAPSqlScriptFunctionStatement(ProcedureLikeStatement):
    begin = 'SAP_SQLSCRIPT_FUNCTION'
    end   = Seq('END', 'SAP_SQLSCRIPT_FUNCTION', ';')
    
    # procedures do not contain procedure
    # it does not contain substatement except inside block 
    stopped_by_other_statement = True

    def on_end(self):
        GroupProcedureStatement.on_end(self)
        self.name.types = [Function]

class MSProcedureStatement(ProcedureLikeStatement):
    stopped_by_other_statement = True
    begin = Seq(Or('CREATE', 'ALTER'),
                Or('PROCEDURE', 'PROC'))
    end = GoSeparator  
     
    def on_end(self):
        GroupProcedureStatement.on_end(self)

class GroupFunctionStatement(ProcedureLikeStatement):
    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        self.name.types = [Function]
                
class FunctionStatement(ProcedureLikeStatement):
    begin = Seq('CREATE', 
                Optional(Seq('DEFINER','=', 'CURRENT_USER')), # for mariaDB
                Optional(Seq('DEFINER','=', String.Symbol,'@', String.Symbol)), # for mariaDB
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('EDITIONABLE', 'NONEDITIONABLE')),
                'FUNCTION')
    end   = Or(Block, PostgresqlBlock, 'WRAPPED')

    # procedures do not contain procedure
    # it does not contain substatement except inside block 
    stopped_by_other_statement = True

    def on_end(self):
        GroupFunctionStatement.on_end(self)
        
class MSFunctionStatement(ProcedureLikeStatement):
    stopped_by_other_statement = True
    begin = Seq(Or('CREATE', 'ALTER'),
                'FUNCTION')
    end = GoSeparator

    def on_end(self):
        GroupFunctionStatement.on_end(self)
 
class PGCreateTriggerStatement(ProcedureLikeStatement):
    
    begin = Seq('CREATE', Optional(Seq('OR', 'REPLACE')), Optional('EVENT'), 'TRIGGER')
    end   = Or(Block, PostgresqlBlock, ';' ) 

    def __init__(self):
        ProcedureLikeStatement.__init__(self)
        GroupTriggerStatement.__init__(self)

    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        GroupTriggerStatement.on_end(self)
        
    stopped_by_other_statement = True 

class PGCreateRuleStatement(ProcedureLikeStatement):
    
    begin = Seq('CREATE', Optional(Seq('OR', 'REPLACE')), 'RULE')
    end   = Or(Block, PostgresqlBlock, ';' ) 

    def __init__(self):
        ProcedureLikeStatement.__init__(self)
        GroupTriggerStatement.__init__(self)

    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        GroupTriggerStatement.on_end(self)
        
    stopped_by_other_statement = True 
                  
class CreateTriggerStatement(ProcedureLikeStatement):
    
    begin = Seq('CREATE', 
                Optional(Seq('OR', 'REPLACE')), 
                Optional(Or('EDITIONABLE', 'NONEDITIONABLE')),
                'TRIGGER')
    end   = Or(Block, PostgresqlBlock, 'SET' ) # SET is for the case of MariaDB triggers without BEGIN END

    def __init__(self):
        ProcedureLikeStatement.__init__(self)
        GroupTriggerStatement.__init__(self)

    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        GroupTriggerStatement.on_end(self)
        
    stopped_by_other_statement = True                

class DB2CreateTriggerStatement(ProcedureLikeStatement):
    
    begin = Seq('CREATE', 
                'TRIGGER')
    end   = Or(';', Seq('END', '%'), Block)

    def __init__(self):
        ProcedureLikeStatement.__init__(self)
        GroupTriggerStatement.__init__(self)

    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        GroupTriggerStatement.on_end(self)
        
    stopped_by_other_statement = True  
    
class MSCreateTriggerStatement(ProcedureLikeStatement):
    
    begin = Seq(Or('CREATE', 'ALTER'), 'TRIGGER')
    end = GoSeparator
    stopped_by_other_statement = True

    def __init__(self):
        ProcedureLikeStatement.__init__(self)
        GroupTriggerStatement.__init__(self)

    def on_end(self):
        ProcedureLikeStatement.on_end(self)
        GroupTriggerStatement.on_end(self)

class DB2CreateWrapperStatement(Statement):
     
    begin = Seq('CREATE', 'WRAPPER')
    end   = Or(';', Seq(Optional('END'), '%'), Block)
        
    stopped_by_other_statement = True  

class DB2CreateServerStatement(Statement):
     
    begin = Seq('CREATE', 'SERVER')
    end   = Or(';', Seq(Optional('END'), '%'), Block)
        
    stopped_by_other_statement = True  

class DB2CreateUserStatement(Statement):
     
    begin = Seq('CREATE', 'USER')
    end   = Or(';', Seq(Optional('END'), '%'), Block)
        
    stopped_by_other_statement = True 
                        
def create_symbol_specific_synonym(statement, symbols, raise_error=True):

    actions =  {CreateSynonym:create_specific_synonym
               }
    try:
        return actions[type(statement)](statement, symbols)
    except KeyError:
        pass
    except:
        warning('SQL-002', 'Parsing issue between line %s and line %s : %s' % (statement.get_begin_line(), statement.get_end_line(), format_exc()))
        if raise_error:
            raise
                                          
def create_symbol(statement, symbols, raise_error=True):

    actions = {SearchPath:handle_set_current_path,
               UseDatabase:handle_set_current_database,
               AlterSessionSetCurrentSchema:handle_set_current_schema,
               SetCurrentSchema:handle_set_current_schema,
               Define:create_define,
               CreateIndexStatement:create_index,
               CreateTableStatement:create_table,
               CreateBlockTableStatement:create_table,
               ReplaceViewStatement:replace_view,
               MSCreateViewStatement:create_view,
               CreateViewStatement:create_view,
               AlterStatement:parse_alter,
               DropTableStatement:parse_drop_table,
               RenameTableStatement:parse_rename_table,
               MSProcedureStatement:create_procedure,
               TeradataProcedureStatement:create_procedure,
               MSFunctionStatement:create_function,
               MSCreateTriggerStatement:create_trigger,
               ProcedureStatement:create_procedure,
               FunctionStatement:create_function,
               CreateTriggerStatement:create_trigger,
               DB2CreateTriggerStatement:create_trigger,
               PGCreateTriggerStatement:create_trigger,
               EventStatement:create_event,
               PackageBody:create_package_body,
               TypeBody:create_type_body,
               ExecuteDynamicStringBlock:create_dynamic_ms_sql_objects,
               CreateSynonym:create_synonym,
               TypeHeader:create_type_header,
               SAPSqlScriptProcedureStatement:create_sap_sqlscript_procedure,
               SAPSqlScriptFunctionStatement:create_sap_sqlscript_function
               }
    try:
        return actions[type(statement)](statement, symbols)
    except KeyError:
        pass
    except:
        warning('SQL-002', 'Parsing issue between line %s and line %s : %s' % (statement.get_begin_line(), statement.get_end_line(), format_exc()))
        if raise_error:
            raise
            
def analyse_symbol(statement, symbols, raise_error=True, variables_list=None, variant=None, impact_analysis = False):
    
    actions = {SearchPath:handle_set_current_path,
               UseDatabase:handle_set_current_database,
               AlterSessionSetCurrentSchema:handle_set_current_schema,
               SetCurrentSchema:handle_set_current_schema,
               TypeHeader:analyse_type_header,
               MSCreateViewStatement:analyse_view,
               MSProcedureStatement:analyse_procedure,
               MSFunctionStatement:analyse_procedure,
               MSCreateTriggerStatement:analyse_procedure,
               ReplaceViewStatement:analyse_view,
               CreateViewStatement:analyse_view,
               ProcedureStatement:analyse_procedure,
               TeradataProcedureStatement:analyse_procedure,
               SAPSqlScriptProcedureStatement:analyse_procedure,
               SAPSqlScriptFunctionStatement:analyse_procedure,
               FunctionStatement:analyse_procedure,
               CreateTriggerStatement:analyse_procedure,
               DB2CreateTriggerStatement:analyse_procedure,
               PGCreateTriggerStatement:analyse_procedure,
               EventStatement:analyse_procedure,
               PackageBody:analyse_package_body,
               ProcedureBodyStatement:analyse_procedure,
               FunctionBodyStatement:analyse_procedure,
               TypeBody:analyse_type_body,
               MethodBodyStatement:analyse_procedure,
               ExecuteDynamicStringBlock:analyze_dynamic_ms_sql_objects}

    try:
        return actions[type(statement)](statement, symbols, variables_list, variant, impact_analysis)
    except KeyError:
        pass
    except:
        warning('SQL-004', 'Analysis issue between line %s and %s %s' % (statement.get_begin_line(), statement.get_end_line(), format_exc()))
        if raise_error:
            raise

def handle_set_current_path(statement, symbols, variables_list=None, variant=None, impact_analysis = False):
    tokens = statement.get_children()
    tokens.move_to(['to', '='])
    
    identifier = parse_identifier(tokens, force_parse=True)
    symbols.declared_schema_name = identifier.get_name()

def handle_set_current_database(statement, symbols, variables_list=None, variant=None, impact_analysis = False):
    tokens = statement.get_children()
    tokens.move_to('USE')
  
    identifier = parse_identifier(tokens, force_parse=True)   
    symbols.declared_schema_name = identifier.get_name()

def handle_set_current_schema(statement, symbols, variables_list=None, variant=None, impact_analysis = False):
    tokens = statement.get_children()
    tokens.move_to(['CURRENT_SCHEMA', 'SCHEMA'])
    token = tokens.look_next()
    if token in ['to', '=']:
        tokens.move_to(['to', '='])
        
    identifier = parse_identifier(tokens, force_parse=True)
    symbols.declared_schema_name = identifier.get_name().rstrip()

def define_values(statement):
    tokens = statement.get_children()
    next(tokens)
    token = tokens.look_next()
    if token == 'GLOBAL':
        return
    variable_name = token.text
    tokens.move_to('=')
    token = tokens.look_next()
    variable_value = token.text.replace('"', '').replace("'", "")
    return [variable_name, variable_value]
    
def create_define(statement, symbols, variables_list=None, variant=None):
    symbols.variables.append(define_values(statement))  

def replace_variables (statement, symbols):
    import pygments
    new_tokens = []
    variable_next = False
    variable_replaced = False
    for child in statement.get_tokens():
        if child.text == '&':
            variable_next = True
        elif variable_next and child.type == Name:
            for variable in symbols.variables:
                if variable[0] == child.text:
                    new_tokens.append(Token(variable[1], pygments.token.Token.Name))
                    variable_next = False
                    variable_replaced = True
                    break
        elif variable_replaced and child.text == '.':
            variable_replaced = False
            continue
        elif not variable_next and not variable_replaced:
            new_tokens.append(child)

    return (Lookahead(new_tokens))

def create_table(statement, symbols):
    """
    Parse a create table statement
    
    CREATE [TEMPORARY] TABLE [IF NOT EXISTS] <...> (colum1 , ... ,)
    
    Primary key, unique and constraints:

    postgresql : https://www.postgresql.org/docs/9.4/static/indexes-unique.html
    
        PostgreSQL automatically creates a unique index when a unique constraint or primary key is defined for a table. The index covers the columns that make up the primary key or unique constraint (a multicolumn index, if appropriate), and is the mechanism that enforces the constraint.
    
    sqlserver : http://stackoverflow.com/questions/3296230/unique-constraint-vs-unique-index
    
    mysql : http://stackoverflow.com/questions/9764120/does-a-unique-constraint-automatically-create-an-index-on-the-fields
    
    
    
    
    in colunm : 
    
    [UNIQUE [KEY] | [PRIMARY] KEY]    MySQL
    
    constraints :
    
    [CONSTRAINT [symbol]] PRIMARY KEY [index_type] (index_col_name,...)
    {INDEX|KEY} [index_name] [index_type] (index_col_name,...)
    [CONSTRAINT [symbol]] UNIQUE [INDEX|KEY]
    {FULLTEXT|SPATIAL} [INDEX|KEY] [index_name] (index_col_name,...)
    [CONSTRAINT [symbol]] FOREIGN KEY
    
    
    
    
    
    """
    def get_tokens(node):
        
        result = []
        for child in node.get_children():
            if isinstance(child, Node):
                result += get_tokens(child)
            else:
                result.append(child)
                
        return result
        
    
    def parse_type(tokens):
        """
        Parse a type declaration and returns it as a list of tokens
        
        Example : 
        
        CHAR(32) --> ['CHAR', '(', 32, ')']
        """
        result = []
        token = None
        try:
            token = tokens.look_next()
        except StopIteration:
            pass
        if isinstance(token, Token):
            token = next(tokens)
            # the case of SQL Server, when brackets are used
            if token == '[': #
                token = tokens.look_next()
                next(tokens)
                next_token = tokens.look_next()
                if next_token == ']': 
                    next(tokens)
                    next_token_2 = tokens.look_next()
                    # the case of A.B
                    if next_token_2 == '.': 
                        next(tokens)
                        next_token_3 = tokens.look_next()
                        if next_token_3 == '[': 
                            next(tokens)
                            next_token_4 = tokens.look_next()
                            
                            result.append(token)
                            result.append(next_token_2)
                            result.append(next_token_4)
                            return result
                        elif isinstance(next_token_3, Parenthesis):
                            result.append(token)
                            result += get_tokens(next_token_3)
                            return(result)
                        else:
                            result.append(token)
                            return result
                    elif isinstance(next_token_2, Parenthesis):
                        result.append(token)
                        result += get_tokens(next_token_2)
                        return(result)
                    else:
                        result.append(token)
                        return result
                else:
                    result.append(token)
                    return result
            
            # the case of SQL Server when column is declared AS ... something ....
            if token == 'AS': 
                token = next(tokens)
                if isinstance(token, Parenthesis):
                    result += get_tokens(token)
                    return result
            

            result.append(token)
        
        try:
            #Ã‚Â lookahead
            if isinstance(token, Parenthesis):
                result += get_tokens(token)
            else:
                token = next(tokens)
                if isinstance(token, Parenthesis):
                    result += get_tokens(token)
                    return result
        except StopIteration:
            pass
        return result
          
    result = Table()
    result.ast = statement 
    tokens = statement.get_children()   
    tokens.move_to('TABLE')
    
    while tokens.look_next() in ['IF', 'NOT', 'EXISTS']:
        tokens.__next__()
    

    """
    Search for table name
    """
    identifier = parse_identifier(tokens, force_parse=True, accept_keywords=True)
    if  identifier.get_name() == '&':
        tokens = replace_variables (statement, symbols)
        tokens.move_to('TABLE')
    
        while tokens.look_next() in ['IF', 'NOT', 'EXISTS']:
            tokens.__next__()
        identifier = parse_identifier(tokens, force_parse=True, accept_keywords=True)
        
    result.name = identifier.get_name()
    result.fullname = identifier.get_fullname(symbols.get_schema_name())
    result.ast.primaryKey = 0
    class Parenthesis(BlockStatement):
        begin = '('
        end = ')'

    
    class ColumnClause(Statement):
        begin = Any()
        end = ','
    
    
    class NotNull(Term):
        match = Seq('NOT', 'NULL')

    class NoPrimaryKey(Term):
        match = Seq('NO', 'PRIMARY', 'INDEX')
        
    class PrimaryKey(Term):
        match = Seq(Optional('PRIMARY'), Or('KEY', 'INDEX'))
    
    class UniqueKey(Term):
        match = Seq('UNIQUE', Optional(Or('KEY', 'INDEX')))

    class UniqueIndex(Term):
        match = 'INDEX'

    class FulltextIndex(Term):
        match = Seq('FULLTEXT', Optional('KEY'))

    class OnDelete(Term):
        match = Seq('ON', 'DELETE')  
    class OnDeleteCascade(Term):
        match = Seq('ON', 'DELETE', 'CASCADE')      
    class OnDeleteRestrict(Term):
        match = Seq('ON', 'DELETE',  'RESTRICT')       
    class OnDeleteSetNull(Term):
        match = Seq('ON', 'DELETE',  'SET', 'NULL') 
    class OnDeleteSetDefault(Term):
        match = Seq('ON', 'DELETE', 'SET', 'DEFAULT') 
    class OnDeleteNoAction(Term):
        match = Seq('ON', 'DELETE', 'NO', 'ACTION') 

    class OnUpdate(Term):
        match = Seq('ON', 'UPDATE')                            
    class OnUpdateCascade(Term):
        match = Seq('ON', 'UPDATE', 'CASCADE')      
    class OnUpdateRestrict(Term):
        match = Seq('ON', 'UPDATE', 'RESTRICT') 
    class OnUpdateSetNull(Term):
        match = Seq('ON', 'UPDATE', 'SET', 'NULL') 
    class OnUpdateSetDefault(Term):
        match = Seq('ON', 'UPDATE' , 'SET', 'DEFAULT') 
    class OnUpdateNoAction(Term):
        match = Seq('ON', 'UPDATE', 'NO', 'ACTION') 
                           
    class ForeignKeyTerm(Term):
        match = Seq('FOREIGN', 'KEY')
                
    class ReferencedColumn(Term):
        match = Seq('REFERENCES')
    parser = Parser(SqlLexer, [Parenthesis], 
                    [NotNull, ReferencedColumn, NoPrimaryKey, PrimaryKey, UniqueKey, 
                     OnDeleteCascade, OnDeleteRestrict, OnDeleteSetNull, OnDeleteSetDefault, OnDeleteNoAction,
                     OnUpdateCascade, OnUpdateRestrict, OnUpdateSetNull, OnUpdateSetDefault, OnUpdateNoAction,
                     ForeignKeyTerm, FulltextIndex, UniqueIndex],
                    [OnDelete, OnUpdate],
                    {Parenthesis:[ColumnClause]}
                    )

    list_of_tokens = list(statement.get_children())
    
    
    if 'AS' in list_of_tokens and 'SELECT' in list_of_tokens and 'FROM' in list_of_tokens:
        as_detected = False
        parenthesis_detected = False
        comma_detected = False
        for t in list_of_tokens:
            if parenthesis_detected and comma_detected: 
                # we could save CTAS as table
                break
            if t == ',' and not as_detected and parenthesis_detected:
                comma_detected = True
            if t == '(' and not as_detected:
                parenthesis_detected = True
            if as_detected and t.text.lower() == 'select':
                return Unknown
            if t.text.lower() == 'as':
                as_detected = True
    
    parenthesis = None
    PrimaryKey_Nodes = None
    FK_Syntax = 0

    for node in parser.parse_stream(tokens):
        if isinstance(node, Parenthesis) and not parenthesis:
            # columns
            parenthesis = node
        elif isinstance(node, PrimaryKey) and not PrimaryKey_Nodes:
            PrimaryKey_Nodes = node
        elif PrimaryKey_Nodes and not node == ';':
            PrimaryKey_Nodes = node

    schema = symbols.register_symbol(result)
        
    if parenthesis:
        column_order = 0     
        for column_clause in parenthesis.get_sub_nodes():
            local_tokens = column_clause.get_children()
            identifier = parse_identifier(local_tokens)
            column_name = identifier.get_name() if identifier else None
            parsed_type = parse_type(local_tokens)
            
            column = None
            
            # FK Referential Integrity Actions
            on_delete_cascade = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnDeleteCascade)]
            on_delete_restrict = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnDeleteRestrict)]
            on_delete_setnull = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnDeleteSetNull)]
            on_delete_setdefault = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnDeleteSetDefault)]
            on_delete_noaction = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnDeleteNoAction)]
            on_delete = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnDelete)]

            on_update_cascade = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnUpdateCascade)]
            on_update_restrict = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnUpdateRestrict)]
            on_update_setnull = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnUpdateSetNull)]
            on_update_setdefault = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnUpdateSetDefault)]
            on_update_noaction = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnUpdateNoAction)]
            on_update = [node for node in column_clause.get_sub_nodes() if isinstance(node, OnUpdate)]
                
            if column_name and parsed_type:
                column = Column()
                column.table = result
                
                column.name = column_name

                column.type = ''.join(token.text for token in parsed_type)
                column_order += 1
                column.order = column_order
                result.register_column(column)
            
                has_index = False
            
                for sub_node in column_clause.get_children():

                    if isinstance(sub_node, NotNull):
                        
                        column.nullable = False
                    
                    # column constraints 
                    elif isinstance(sub_node, PrimaryKey):
                        
                        pk = UniqueConstraint()
                        pk.name = 'PK_%s' % result.name
                        pk.fullname = '%s.%s' % (result.fullname, pk.name)
                        pk.columns = [column]
                        pk.ast = sub_node
                        result.ast.primaryKey = 1
                        result.register_constraint(pk)
                        
                    elif not has_index and isinstance(sub_node, FulltextIndex):
                        
                        has_index = True
                        # full text index for mariadb
                        pk = FulltextConstraint()
                        pk.name = 'Fulltext_%s' % column.name
                        pk.fullname = '%s.%s' % (result.fullname, pk.name)
                        pk.columns = [column]
                        pk.ast = sub_node
                        result.register_constraint(pk)
                                            
                    elif not has_index and (isinstance(sub_node, UniqueKey) or isinstance(sub_node, UniqueIndex)):
                        
                        has_index = True
                        # unique constraint
                        pk = UniqueConstraint()
                        pk.name = 'UQ_%s' % column.name
                        pk.fullname = '%s.%s' % (result.fullname, pk.name)
                        pk.columns = [column]
                        pk.ast = sub_node
                        result.register_constraint(pk)
            
                    elif FK_Syntax == 0 and isinstance(sub_node, ReferencedColumn): 
                        # foreign key
                        fk = ForeignKey()
                        fk.name = 'FK_%s' % column.name                     
                        fk.fullname = '%s.%s' % (result.fullname, fk.name)
                        fk.columns = [column]
                        fk.ast = sub_node
                                                
                        fk.first_table = result

                        tokens = column_clause.get_children()
                        token = tokens.look_next()
                        while True:
                            token = next(tokens)
                            if isinstance(token, ReferencedColumn):
                                break
                        
                        table2_reference = parse_identifier(tokens)
                        table2_reference.types = [Table]
                        
                        schema.add_reference(table2_reference)
                        fk.second_table_identifier = table2_reference                                     
                        fk.first_table_columns = fk.columns
                        fk.second_table_columns = fk.columns
                            
                        token = get_tokens(next(tokens))
                        if token == '(':
                            fk.second_table_columns = parse_identifier(tokens)  
                        
                        fk.on_delete_cascade = True if on_delete_cascade else False
                        fk.on_delete = True if on_delete or on_delete_cascade or\
                             on_delete_noaction or on_delete_restrict or on_delete_setdefault or on_delete_setnull else False
                        fk.on_delete_restrict = True if on_delete_restrict else False
                        fk.on_delete_setdefault = True if on_delete_setdefault else False
                        fk.on_delete_setnull = True if on_delete_setnull else False
                        fk.on_delete_noaction = True if on_delete_noaction else False
                        
                        fk.on_update_cascade = True if on_update_cascade else False
                        fk.on_update = True if on_update or on_update_cascade or\
                             on_update_noaction or on_update_restrict or on_update_setdefault or on_update_setnull else False
                        fk.on_update_restrict = True if on_update_restrict else False
                        fk.on_update_setdefault = True if on_update_setdefault else False
                        fk.on_update_setnull = True if on_update_setnull else False
                        fk.on_update_noaction = True if on_update_noaction else False
                        
                        result.register_foreign_key(fk)
            else:
                # table constraint
#                 print('table constraint')
#                 column_clause.print_tree()
                primary_keys = [node for node in column_clause.get_sub_nodes() if isinstance(node, PrimaryKey) or isinstance(node, UniqueKey) or isinstance(node, UniqueIndex) or isinstance(node, FulltextIndex)]
                parenthesis = [node for node in column_clause.get_sub_nodes() if isinstance(node, Parenthesis)]
                foreign_key = [node for node in column_clause.get_sub_nodes() if isinstance(node, ForeignKeyTerm)]
                                
                primaryKey = 0
                if primary_keys and parenthesis:
                    
                    columns = []
                    for column in parenthesis[0].get_sub_nodes():
                        
                        try:
                            column_name = parse_identifier(column.get_children()).get_name()
                            columns.append(result.find_column(column_name))
                        except:
                            print('issue with parsing columns in create_table')
                            pass
                    
                    # 
                    constraint_name = None

                    tokens = column_clause.get_children()
                    token = tokens.look_next()
                    if token == 'CONSTRAINT':
                        next(tokens)
                    
                    if token == '[':
                        next(tokens)
                    
                    constraint_identifier = parse_identifier(tokens)
                    if not constraint_identifier.is_empty():
                        constraint_name = constraint_identifier.get_name()
                    
                    while True:
                        try:
                            token = next(tokens)
                        except:
                            break
                        if isinstance(token, PrimaryKey) or isinstance(token, UniqueKey) or isinstance(token, UniqueIndex) or isinstance(token, FulltextIndex):
                            if isinstance(token, PrimaryKey):result.ast.primaryKey = 1
                            break
                    
                    # token contains the ... 
                    try:
                        primary = token.get_children()
                    except:
                        break
                    if not constraint_name:
                        if next(primary) == 'PRIMARY':
                            # pk 
                            constraint_name = 'PK_%s' % result.name
                            result.ast.primaryKey = 1
                        else:
                            # named constraint
                            identifier = parse_identifier(tokens)
                            if not identifier.is_empty(): 
                                constraint_name = identifier.get_name()
                            else:
                                # auto generated
                                if isinstance(token, FulltextIndex):
                                    constraint_name = 'Fulltext_%s' % result.name
                                else:
                                    constraint_name = 'UQ_%s' % result.name

                    if isinstance(token, FulltextIndex):
                        pk = FulltextConstraint()
                    else:                                          
                        pk = UniqueConstraint()
                    result.primaryKey = primaryKey
                    pk.name = constraint_name
                    pk.fullname = '%s.%s' % (result.fullname, pk.name)
                    pk.columns = columns
                    pk.ast = column_clause
                    result.register_constraint(pk)

                if foreign_key and len(parenthesis) >= 2:
                    FK_Syntax = FK_Syntax + 1                    
#                     column_clause.print_tree()              
                    tokens = column_clause.get_children()
                    token = tokens.look_next()
                    if token == 'CONSTRAINT':
                        next(tokens)

                    name_identifier = parse_identifier(tokens)
                    
                    fk = ForeignKey()
                    fk.first_table = result
                    fk.ast = column_clause

                    fk.name = name_identifier.get_name()
                    if fk.name == None:
                        fk.name = 'FK_%s' % result.name
                    
                    fk.fullname = '%s.%s' % (result.fullname, fk.name)
                    
                    tokens = column_clause.get_children()
                    token = tokens.look_next()
                    while True:
                        token = next(tokens)
                        if isinstance(token, ReferencedColumn):
                            break
                        
                    table2_reference = parse_identifier(tokens)
                    table2_reference.types = [Table]
                    schema.add_reference(table2_reference)
                    fk.second_table_identifier = table2_reference
                    
                    def extract_column_names(parenthesis_node):
                        
                        result = []
                        for s in parenthesis_node.get_sub_nodes():
                            result.append(parse_identifier(s.get_children()).get_name())
                        return result
                        
                    fk.first_table_columns = extract_column_names(parenthesis[0])
                    fk.second_table_columns = extract_column_names(parenthesis[1])
                    
                    fk.on_delete_cascade = True if on_delete_cascade else False
                    fk.on_delete = True if on_delete or on_delete_cascade or\
                         on_delete_noaction or on_delete_restrict or on_delete_setdefault or on_delete_setnull else False
                    fk.on_delete_restrict = True if on_delete_restrict else False
                    fk.on_delete_setdefault = True if on_delete_setdefault else False
                    fk.on_delete_setnull = True if on_delete_setnull else False
                    fk.on_delete_noaction = True if on_delete_noaction else False
                    
                    fk.on_update_cascade = True if on_update_cascade else False
                    fk.on_update = True if on_update or on_update_cascade or\
                         on_update_noaction or on_update_restrict or on_update_setdefault or on_update_setnull else False
                    fk.on_update_restrict = True if on_update_restrict else False
                    fk.on_update_setdefault = True if on_update_setdefault else False
                    fk.on_update_setnull = True if on_update_setnull else False
                    fk.on_update_noaction = True if on_update_noaction else False
                    
                    result.register_foreign_key(fk)

    # the case of Teradata when indexes are declared after parenthesis and before ; 
    if PrimaryKey_Nodes:
        columns = []
        constraint_name = 'PK_%s' % result.name
        for column_clause in PrimaryKey_Nodes.get_sub_nodes():
            local_tokens = column_clause.get_children()
            identifier = parse_identifier(local_tokens)
            column_name = identifier.get_name() if identifier else None
            columns.append(result.find_column(column_name))
            
        result.ast.primaryKey = 1
        pk = UniqueConstraint()
        result.primaryKey = 1
        pk.name = constraint_name
        pk.fullname = '%s.%s' % (result.fullname, pk.name)
        pk.columns = columns
        pk.ast = column_clause
        result.register_constraint(pk)
            
    return result

def create_dynamic_symbols(text, database, raise_error=True, variant=Variant.ansisql, begin_line=0, end_line=0, begin_column=0, end_column=0):
    """
    Register dynamic symbols in the database    
    """
    for statement in parse(text, variant, None): 
        if statement: 
            symbol = create_symbol(statement, database, raise_error)    
            if symbol and not isinstance(symbol, Unknown): 
                symbol.begin_line = begin_line
                symbol.end_line = end_line   
                symbol.begin_column = begin_column      
                symbol.end_column = end_column   
                self = symbol      
                symbol.use_ast_for_dynamic_code(begin_line, begin_column, end_line, end_column)
    return statement

def create_dynamic_ms_sql_objects(statement, symbols):  
    tokens = statement.get_children() 
    for t in tokens:
        if t.type ==  String.Single:
            text = t.text[1: len(t.text) -2]
            text = text.replace("''", "'")       
            dynamic_object = create_dynamic_symbols(text, symbols, False, 'sqlserver', t.begin_line, t.end_line, t.begin_column, t.end_column) 
            if isinstance(dynamic_object, GroupViewStatement):
                return(GroupViewStatement.on_end(dynamic_object))
            elif isinstance(dynamic_object, GroupFunctionStatement):
                return(create_function(statement, symbols))
            elif isinstance(dynamic_object, GroupProcedureStatement):
                return(create_procedure(statement, symbols))

def replace_view(statement, symbols):
    """
    Parse a replace view statement
    
    REPLACE ... VIEW <...> [(col1, ..., )] ... AS <query expression>   
    
    """

    try:
        statement.name.types = [View]
        try:
            view, _ = find_symbol(statement, symbols)
        except:
            view = None
            pass
        if not view:
            result = View()
            result.ast = statement
            result.name = statement.name.get_name()
            result.fullname = statement.name.get_fullname(symbols.get_schema_name())
    
            column_order = 0
            for column_name in statement.columns:
                column = Column()
                result.columns.append(column)
                column.table = result
                column.name = column_name
                column_order += 1
                column.order = column_order
                    
            
            result.query = statement.query
            
            _ = symbols.register_symbol(result)
            
            return result
        else:
            return
    except:  
        result = View()
        result.ast = statement
        result.name = statement.name.get_name()
        result.fullname = statement.name.get_fullname(symbols.get_schema_name())

        column_order = 0
        for column_name in statement.columns:
            column = Column()
            result.columns.append(column)
            column.table = result
            column.name = column_name
            column_order += 1
            column.order = column_order
                
        
        result.query = statement.query
        
        _ = symbols.register_symbol(result)
        
        return result

def create_view(statement, symbols):
    """
    Parse a create view statement
    
    CREATE ... VIEW <...> [(col1, ..., )] ... AS <query expression>   
    
    """
    result = View()
    result.ast = statement
    result.name = statement.name.get_name()
    result.fullname = statement.name.get_fullname(symbols.get_schema_name())

    column_order = 0
    for column_name in statement.columns:
        column = Column()
        result.columns.append(column)
        column.table = result
        column.name = column_name
        column_order += 1
        column.order = column_order
            
    
    result.query = statement.query
    
    _ = symbols.register_symbol(result)
    
    return result


def create_index(statement, symbols):
    """
    Parse a create table statement
    
    CREATE [UNIQUE] ... INDEX <index_name> ON <table_name> (colum1 , ... ,)
    
    Teradata : 
        CREATE [UNIQUE] ... INDEX <index_name> (colum1 , ... ,) ON <table_name> 
    """
    tokens = statement.get_children() 
    tokens.move_to('INDEX')
    
    token = tokens.look_next()

    # [CONCURRENTLY]
    if token == 'CONCURRENTLY':
        next(tokens)
    
    # [IF NOT EXISTS]
    elif token == 'IF':
        next(tokens)
        token = tokens.look_next()
        if token == 'NOT':
            next(tokens)
            token = tokens.look_next()
            if token == 'EXISTS':
                next(tokens)
        
        
    dbo_detected = False
    token = tokens.look_next()
    if token.text.lower() == 'dbo':
        next(tokens)
        dbo_detected = True
    identifier = parse_identifier(tokens)
    _ = tokens.move_to('ON')
    
    
    table_name = parse_identifier(tokens, force_parse=False, accept_keywords=True)
    table_name.types = [Table, View]
    
    scope = symbols
    if not table_name.get_parent_name():
        if dbo_detected:
            scope = symbols.find_symbol(['dbo', 'DBO'], [Schema])
        else:
            scope = symbols.find_symbol(symbols.get_schema_name(), [Schema])
    
    table = None
    
    if scope:
        table = scope.resolve_reference(table_name, unique=True)
            
    columns_name = pase_column_list(tokens)
    
    # the case of Teradata when I missed columns names
    # CREATE [UNIQUE] ... INDEX <index_name> (colum1 , ... ,) ON <table_name> 
    if not columns_name:
        tokens_columns = statement.get_children() 
        columns_name = pase_column_list(tokens_columns)
    
    result = Index()
    result.ast = statement
    result.name = identifier.get_name() if identifier.get_name() else 'IDX_%s' % table_name.get_name()
    result.table = table
    result.columns = columns_name
    if table and table.already_has_constraint(result):
        return

    if identifier.get_fullname(symbols.get_schema_name()) and table and symbols.get_schema_name() == 'DEFAULT' and ('DEFAULT.' in identifier.get_fullname(symbols.get_schema_name()) or identifier.get_fullname(symbols.get_schema_name()) == result.name) and table.parent.name != 'DEFAULT':
        result.fullname = '%s.%s' % (table.parent.name, result.name)
    else:
        result.fullname = identifier.get_fullname(symbols.get_schema_name())

    if table:
        table.indexes.append(result)
    try:
        _ = symbols.register_symbol(result)
    except:
        # issue with ipss_dump
        print('issue with register_symbol in create_index')
        pass
    
    return result

def create_specific_synonym(statement, symbols):
    """
    Parse a create specific synonym statement
    
    CREATE ... SYNONYM <synonym_name> ON <object_name>
    """
    tokens = statement.get_children() 
    tokens.move_to(['SYNONYM', 'ALIAS', 'NICKNAME'])
            
    token = tokens.look_next()
   
    # [IF NOT EXISTS]
    if token == 'IF':
        next(tokens)
        token = tokens.look_next()
        if token == 'NOT':
            next(tokens)
            token = tokens.look_next()
            if token == 'EXISTS':
                next(tokens)

    identifier = parse_identifier(tokens, force_parse=True, accept_keywords=True)
    
    _ = tokens.move_to(['ON', 'FOR'])  
    
    token = tokens.look_next()
    if token in ['TABLE', 'MODULE']:
        next(tokens)
    elif token == 'SEQUENCE': return

    object_name = parse_identifier(tokens, force_parse=True, accept_keywords=True)
    object_name.types = [Table, View, Procedure, Function, Synonym, Package, Type]

    scope = symbols
    if not object_name.get_parent_name():
        scope = symbols.find_symbol(symbols.get_schema_name(), [Schema])

    aliased_object = None
    if scope:
        aliased_object = scope.resolve_reference(object_name, unique=True)
        
    if type(aliased_object) == Table :result = TableSynonym()
    elif type(aliased_object) == View : result = ViewSynonym()
    elif type(aliased_object) == Procedure : result = ProcedureSynonym()
    elif type(aliased_object) == Function : result = FunctionSynonym()
    elif type(aliased_object) == Package : result = PackageSynonym()
    elif type(aliased_object) == Type : result = TypeSynonym()
    elif type(aliased_object) == Synonym : 
        aliased_object = scope.resolve_reference(object_name, False)
        if aliased_object[0].name == identifier.get_name() and len(aliased_object)==1:
            return
        else:
            aliased_object = aliased_object[0]
            while type(aliased_object) == Synonym:
                aliased_object = aliased_object.get_relyonLink()     
            if type(aliased_object) == Table : result = TableSynonym()
            elif type(aliased_object) == View : result = ViewSynonym()
            elif type(aliased_object) == Procedure : result = ProcedureSynonym()
            elif type(aliased_object) == Function : result = FunctionSynonym()
            elif type(aliased_object) == Package : result = PackageSynonym()
            elif type(aliased_object) == Type : result = TypeSynonym()
            else : result = TableSynonym() 
    else : result = TableSynonym() 

    result.ast = statement
    result.name = identifier.get_name()
    result.fullname = identifier.get_fullname(symbols.get_schema_name())
    result.object = aliased_object
    
    try:
        _ = symbols.register_symbol(result)
    except:
        print('issue with register_symbol in create_specific_synonym')
        pass
    
    return result

def create_synonym(statement, symbols):
    """
    Parse a create synonym statement
    
    CREATE ... SYNONYM <synonym_name> ON <object_name>
    """
    tokens = statement.get_children() 
    tokens.move_to(['CREATE', 'OR', 'REPLACE'])
    token = tokens.look_next()
    if token == 'OR':
        next(tokens)
        token = tokens.look_next()
        if token == 'REPLACE':
            next(tokens)
            token = tokens.look_next()

    kind_of_synonym = 'PUBLIC' if token == 'PUBLIC' else 'PRIVATE'

    tokens.move_to(['SYNONYM', 'ALIAS', 'NICKNAME'])
            
    token = tokens.look_next()
   
    # [IF NOT EXISTS]
    if token == 'IF':
        next(tokens)
        token = tokens.look_next()
        if token == 'NOT':
            next(tokens)
            token = tokens.look_next()
            if token == 'EXISTS':
                next(tokens)
        
        
    
    identifier = parse_identifier(tokens, force_parse=True, accept_keywords=True)
    
    _ = tokens.move_to(['ON', 'FOR'])  
    
    token = tokens.look_next()
    if token in ['TABLE', 'MODULE']:
        next(tokens)
    elif token == 'SEQUENCE': return
            
    object_name = parse_identifier(tokens)
    object_name.types = [View, Procedure, Function, Synonym, Package, Type, Table]
    
    scope = symbols
    if not object_name.get_parent_name():
        scope = symbols.find_symbol(symbols.get_schema_name(), [Schema])

    result = Synonym()
    result.ast = statement
    
    aliased_object = None
    result.objects = []
    if scope:
        aliased_object = scope.resolve_reference(object_name, unique=True)
        result.object = aliased_object
        result.objects.append(aliased_object)
        if aliased_object : 
            aliased_object.synonyms.append(result)
        while type(aliased_object) == Synonym:
            aliased_object = aliased_object.get_relyonLink()        
            result.objects.append(aliased_object)
            
    result.name = identifier.get_name()
    result.fullname = identifier.get_fullname(symbols.get_schema_name())
    result.kind_of_synonym = kind_of_synonym
    
    try:
        _ = symbols.register_symbol(result)
    except (AttributeError, KeyError):
        pass

    return result

def pase_column_list(tokens):
    result = []
    token = tokens.move_to('(')
    while token:
        column_name = parse_identifier(tokens).get_name()
        result.append(column_name)
        token = tokens.move_to([',', ')'])
        if token and token == ')':
            break
    return result

def parse_alter(statement, symbols):
    """
    Parse an ALTER ... statement.
    """
    tokens = statement.get_children()
    assert(next(tokens) == 'ALTER')
    altered = next(tokens)
    
    if altered == 'TABLE':
        return parse_alter_table(statement, symbols)
    
    return Unknown()

def parse_alter_table(statement, symbols):
    """
    Parse an 
    
    ALTER TABLE [ONLY] <table1_name> ADD CONSTRAINT <constraint_name> FOREIGN KEY (...) REFERENCES <table2_name>

    ALTER TABLE <table1_name> ADD CONSTRAINT <constraint_name> FOREIGN KEY (...) REFERENCES <table2_name>
    
    ALTER TABLE RENAME <table_name1> [TO|AS] <table_name2>
    
    """   
    existing_indexes = statement.get_children() 
    tokens = statement.get_children() 
    
    assert(next(tokens) == 'ALTER')
    assert(next(tokens) == 'TABLE')
    
    token = tokens.look_next()
    if token == 'ONLY':
        next(tokens)
    # ALTER TABLE ... CHECK/NOCHECK CONSTRAINT ...
    elif token in ['CHECK', 'NOCHECK']:
        return
                   
    # PostgreSQL
    token = tokens.look_next()
    if token == 'IF':     
        assert(next(tokens) == 'IF')
        assert(next(tokens) == 'EXISTS')
    
    table1_reference = parse_identifier(tokens)
    if  token == '&' :
        tokens = replace_variables (statement, symbols)

        assert(next(tokens) == 'ALTER')
        assert(next(tokens) == 'TABLE')
                      
        token = tokens.look_next()
        if token == 'ONLY':
            next(tokens)
        # ALTER TABLE ... CHECK/NOCHECK CONSTRAINT ...
        elif token in ['CHECK', 'NOCHECK']:
            return
                       
        # Postgre
        token = tokens.look_next()
        if token == 'IF':     
            assert(next(tokens) == 'IF')
            assert(next(tokens) == 'EXISTS')
        
        table1_reference = parse_identifier(tokens)       
    table1_reference.types = [Table]
    
    token = next(tokens)
    if token == 'FOREIGN':
        
        constraint_name = None
        token = tokens.look_next()
        if token == 'KEY':
            token = next(tokens)
            token = tokens.look_next()
        constraint_name = parse_identifier(tokens)

        return create_foreign_key(statement, tokens, table1_reference, constraint_name, symbols)
    
    if token == 'RENAME':
        
        # renames table1 to table2
        
        table = Table()
        table.name = table1_reference.get_name()
        table.fullname = table1_reference.get_fullname(symbols.get_schema_name())
        schema_name = table1_reference.get_parent_name()  # if 'a.b' gives 'a'
        
        if not schema_name:
            schema_name = symbols.get_schema_name()
        
        # if missing, add schema name to fullname (eg "DEFAULT")
        if table.name == table.fullname:
            table.fullname = "%s.%s" % (schema_name, table.name)
        table.file = symbols.current_file
        
        token = tokens.look_next()
        if token in ['TO','AS']:
            next(tokens)
            
        table2_reference = parse_identifier(tokens)   # force_parse=True ?
        
        token = tokens.look_next()
        if token == 'TO':
            log.debug("Column renaming detected in table {}".format(table.name))
            return
        
        new_name = table2_reference.get_name()
        new_schema = table2_reference.get_parent_name()  # if 'a.b' gives 'a'
        
        if not new_schema:
            new_schema = symbols.get_schema_name()

        if schema_name != new_schema:
            log.debug("Unsupported syntax ALTER TABLE RENAME TO between different schemes/databases")
            return

        symbols.rename_symbol(table,new_name)        
        return 
    
    # some tokens should be ignored because what they do are not important for analysis
    if token in ['PCTFREE', 'APPEND', 'ALTER', 'MODIFY', 'OWNER', 'DISABLE', 'CLUSTER']:
        return
    
    if token == 'WITH':
        token = tokens.look_next()
        if token in ['CHECK', 'NOCHECK']:
            next(tokens)
            token = tokens.look_next()
            if token == 'CHECK':
                return
            elif token != 'ADD':
                log.debug('Unsupported syntax ALTER TABLE ... %s ... has been detected at the line %s.' % (token.text, statement.get_begin_line()))
                return
            next(tokens)
    elif token.text in ('CHECK'):
        return
    elif not token in ('ADD' , 'CONSTRAINT'):
        log.debug('Unsupported syntax ALTER TABLE ... %s ... has been detected at the line %s.' % (token.text, statement.get_begin_line()))
        return
    
    constraint_name = None
    primaryKey = 0
    addColumn = 0

    if token == 'CONSTRAINT': 
        constraint_name = parse_identifier(tokens)
    else:
        token = tokens.look_next()
       
    if token.text == 'DEFAULT':
        log.debug('Unsupported syntax ALTER TABLE ... ADD DEFAULT ... has been detected at the line %s.' % (statement.get_begin_line()))
        return

    if token in [ '(', 'ADD']:
        next(tokens)
        token = tokens.look_next() 
        
    if token == 'CONSTRAINT' and not constraint_name:                                                                                                                                    
        next(tokens)
    
        # constraint name
        constraint_name = parse_identifier(tokens)

    try:
        token = next(tokens)  #Ã‚Â FOREIGN or PRIMARY or UNIQUE
    except StopIteration:
        pass
       
    if token == '(':
        token = next(tokens)  
  
    if token == 'FOREIGN':
        return create_foreign_key(statement, tokens, table1_reference, constraint_name, symbols) 

    """
    PRIMARY KEY (...)
    UNIQUE [INDEX|KEY] [index_name] (...)
    INDEX|KEY [index_name] (...)
    
    """

    # column order is unknown so start from 0
    column_order = 0   
    existing_index = None 
    maybe_primaryKey = 0
    if token == 'PRIMARY':
        token = next(tokens)  #Ã‚Â KEY
        if token != 'KEY':
            return
        else:
            primaryKey = 1
        column_names = pase_column_list(tokens)
        result = UniqueConstraint()
        if not column_names:
            existing_index = existing_indexes.move_to('USING')
            if existing_index:
                existing_index = None 
                existing_index = existing_indexes.move_to('INDEX')
                if existing_index:
                    primaryKey = 1
        else:
            # alter without USING but with a list of columns
            maybe_primaryKey = 1
    elif token == 'UNIQUE':
        token = tokens.look_next()
        if token in ['INDEX', 'KEY']:
            token = tokens.look_next()
            
        index_identifier = parse_identifier(tokens)
        if not constraint_name or constraint_name.is_empty():
            constraint_name = index_identifier
        column_names = pase_column_list(tokens)
        result = UniqueConstraint()
    elif token in ['INDEX', 'KEY']:
        index_identifier = parse_identifier(tokens)
        if not constraint_name or constraint_name.is_empty():
            constraint_name = index_identifier
        column_names = pase_column_list(tokens)
        result = UniqueConstraint()
    elif token == 'COLUMN':
        addColumn = 1
        result = Column()
        column_name = parse_identifier(tokens).get_name()
        token = tokens.look_next()
        result.type = ''.join(token.text)
        column_order -= 1
        result.order = column_order
        column_names = []
        column_names.append(column_name)
        result.name = column_name
        if not column_name :
            return
    elif token in ['CHECK', 'DEFAULT', 'PERIOD', 'PARTITION', 'ORGANIZE', 'VERSIONING', 'MATERIALIZED', 'CLONE', 'RESTRICT']:
        return
    else:
        scope = symbols
        if not table1_reference.get_parent_name():
            scope = symbols.find_symbol(symbols.get_schema_name(), [Schema])

        if not scope:
            return

        table = scope.resolve_reference(table1_reference, unique=True)
    
        if not table:
            return
        result = Column()               
        result.ast = statement
        if token.text == 'ADD':
            token = tokens.look_next()
            if token.text == 'FOREIGN':
                next(tokens)
                token = tokens.look_next()
                # yet another FK
                if token.text == 'KEY':
                    return create_foreign_key(statement, tokens, table1_reference, constraint_name, symbols)

        column_name_t = token
        column_name = parse_identifier(tokens).get_name()
        if not column_name:
            try:
                column_name = column_name_t.text
            except StopIteration:
                pass
        try:
            token = tokens.look_next()
        except StopIteration:
            pass
        
        while token in ['[', '(', ')', ']']:
            next(tokens)
            token = tokens.look_next()
            
        # Unnamed Foreigner Key
        result.type = ''.join(token.text)
        column_order -= 1
        result.order = column_order
        column_names = []
        column_names.append(column_name)
        result.name = column_name
        result.fullname = '%s.%s' % (table.fullname, result.name)
        table.register_column(result)
        
        token = tokens.move_to([','])
        while token in [',', '[']:
            token = tokens.look_next()
            if token in (',', '['):
                next(tokens)
                token = tokens.look_next()
            column_name_t = token
            result = Column()
            column_name = parse_identifier(tokens).get_name()
            if not column_name:
                column_name = column_name_t.text
            token = tokens.look_next()
            while token in ['[', '(', ']', ')']:
                next(tokens)
                token = tokens.look_next()
            result.type = ''.join(token.text)
            column_order -= 1
            result.order = column_order
            column_names = []
            column_names.append(column_name)
            result.name = column_name
            try:
                table.register_column(result)
            except:
                log.debug('Cannot register column %s' % format_exc())
                
            token = tokens.move_to([','])

        return result
  
    #column_names = pase_column_list(tokens)
    scope = symbols
    if not table1_reference.get_parent_name():
        scope = symbols.find_symbol(symbols.get_schema_name(), [Schema])
    
    resolve_in_the_same_file = symbols.current_file
    
    table = None
    if scope:
        for t in scope.resolve_reference(table1_reference, unique=False):
            if t.file == resolve_in_the_same_file:
                table = t
    
    if not table:
        try: 
            table = scope.resolve_reference(table1_reference, unique=True)
        except:
            # unresolved... live with it
            return
                        
    if not table:
        # unresolved... live with it
        return
           
    result.ast = statement
    if constraint_name and not constraint_name.is_empty():
        result.name = constraint_name.get_name()
    elif addColumn == 0:
        result.name = 'UQ_%s' % table1_reference.get_name()
        
    result.fullname = '%s.%s' % (table.fullname, result.name)
        
    if table.already_has_constraint(result) and table.get_indexes() and (existing_index or maybe_primaryKey):
        # if maybe_primaryKey is valued, maybe the index is a primary key
        for t in table.get_indexes():
            if constraint_name and t.name.lower() == constraint_name.get_name().lower():
                result = UniqueConstraint()
                result.name = t.name
                result.ast = statement
                result.table = table
                table.primaryKey = True
                table.register_constraint(result)
    
                columns = []
                # columns
                for column_name in t.columns:
                    columns.append(table.find_column(column_name))
                result.columns = columns
                # In the case of : ALTER TABLE ADD PRIMARY KEY USING INDEX index_name
                # we should unregister the index 
                # because when this command is executed, the index is "owned" by the constraint
                try:
                    symbols.unregister_symbol(t)
                except StopIteration:
                    pass

                return result

    if table.already_has_constraint(result) and addColumn == 0:
        return
    
    if (not table.primaryKey or primaryKey == 1)  and addColumn == 0:
        table.primaryKey = primaryKey
        try:
            table.ast.primaryKey = primaryKey
        except AttributeError:
            pass
    
    if addColumn == 0:
        table.register_constraint(result)

    columns = []
    # columns
    for column_name in column_names:
        if addColumn == 0:
            columns.append(table.find_column(column_name))
        elif addColumn == 1:
            columns.append(table.register_column(result))
    result.columns = columns
    
    return result

def parse_rename_table(statement, symbols):
    """
    Parse RENAME TABLE statement. 
    
    MySQL:
        RENAME TABLE tbl_name TO new_tbl_name [, tbl_name2 TO new_tbl_name2] ...
    """
    tokens = statement.get_children() 
    
    tokens.move_to('TABLE')
        
    table = Table()
    
    while True:

        try:
            token = tokens.look_next()                                                                                                                            
        except StopIteration:        
            return Unknown()
        
        if token == ";":                            
            return Unknown()
        elif token == ",":                
            next(tokens)            
        
        # ... fill table ...      
        identifier = parse_identifier(tokens, force_parse=True)
        table.name = identifier.get_name()
        table.fullname = identifier.get_fullname(symbols.get_schema_name())
        schema_name = identifier.get_parent_name()  # if 'a.b' gives 'a'
        
        if not schema_name:
            schema_name = symbols.get_schema_name()
        
        # if missing, add schema name (eg "DEFAULT")
        if table.name == table.fullname:
            table.fullname = "%s.%s" % (schema_name, table.name)
        table.file = symbols.current_file

        if table:
            tokens.move_to('TO')
            try:
                tokens.look_next()
            except StopIteration:
                break
        
        identifier = parse_identifier(tokens, force_parse=True)
        new_name = identifier.get_name()
        new_schema = identifier.get_parent_name()  # if 'a.b' gives 'a'
        
        
        if not new_schema:
            new_schema = symbols.get_schema_name()                    
        
        if schema_name != new_schema:
            warning('SQL-005', 'Non supported RENAME TABLE between different schemes/databases')
            return
                                     
        if new_name:             
            symbols.rename_symbol(table,new_name)
            continue
                  
def parse_drop_table(statement, symbols):
    """
    Parse a DROP TABLE statement.
    
    The effect of CASCADE and RESTRICT 
    as well as HIERARCHY is not addressed
    """          
  
    result = Table()        
    
    tokens = statement.get_children() 
    
    tokens.move_to('TABLE')
    
    # applies to db2
    if tokens.look_next() == 'HIERARCHY':
        next(tokens)        
    
    while tokens.look_next() in ['IF', 'EXISTS']:
        next(tokens)
    
    token = tokens.look_next()

    # run over comments (MariaDB)
    if token == '\\':
        next(tokens)
        while True:
            token = next(tokens)
            if token == '\\':                 
                break        
    
    while True:
        try:
            # look ahead
            token = tokens.look_next()
        except StopIteration:
            return Unknown()                            
        else:
            if token in ['CASCADE','RESTRICT',';']:                
                return Unknown()                        
                                                                                
            identifier = parse_identifier(tokens, force_parse=True)
            result.name = identifier.get_name()
            result.fullname = identifier.get_fullname(symbols.get_schema_name())
            
            # hack to retrieve fullname when DEFAULT scheme name            
            if result.name == result.fullname:
                schema_name = symbols.get_schema_name()
                try:
                    result.fullname = "%s.%s" % (schema_name, result.name)
                except:
                    # Unknown table name
                    return Unknown()
            
            result.file = symbols.current_file            
                         
            symbols.unregister_symbol(result)        
    
    return Unknown()
    
        
def create_foreign_key(statement, tokens, table1_reference, identifier, symbols):        
    """
    
    identifier may be null for example in db2
    
    ALTER TABLE ... ADD FOREIGN KEY <identifier> (...) REFERENCES ...    
    """    
    token = next(tokens)  #Ã‚Â KEY
    if token.text == '(':
        columns_name1 = pase_column_list(tokens)
    elif token != 'KEY':
        return
    else:
        token = tokens.look_next()
        if (not identifier or not identifier.get_name()) and token != '(':
            # db2
            identifier = parse_identifier(tokens)
#             print('identifier : ', identifier)
        
        columns_name1 = pase_column_list(tokens)
    tokens.move_to('REFERENCES')
    
    table2_reference = parse_identifier(tokens)
    table2_reference.types = [Table]

    columns_name2 = None

    all_tokens = tokens

    try:
        token = all_tokens.look_next()
    except StopIteration:
        pass
    
    skip_here = False
    new_identifier = identifier

    if token == 'CONSTRAINT':
        try:
            token = next(all_tokens)
        except StopIteration:
            pass
        new_identifier = parse_identifier(all_tokens)
        columns_name2 = pase_column_list(tokens) 
    elif token in [';', ')']:
        skip_here = True
        columns_name2 = columns_name1 
    else:
        columns_name2 = pase_column_list(tokens) 
        try:
            token = next(all_tokens)
        except StopIteration:
            pass

    if token == 'CONSTRAINT' and not new_identifier.get_name():
        try:
            token = next(tokens)
        except StopIteration:
            pass
        new_identifier = parse_identifier(tokens)
                
    if not columns_name2:
        # the second column list is optional 
        columns_name2 = columns_name1 

    try:   
        if not skip_here :
            token_all = next(all_tokens)
            if token_all == 'CONSTRAINT':
                try:
                    token_all = next(all_tokens)
                except StopIteration:
                    pass
                new_identifier = parse_identifier(all_tokens)
    except StopIteration: 
        pass
    
    result = ForeignKey()
                
    # store references to be resolved latter
    result.first_table_identifier = table1_reference
    result.first_table_columns = columns_name1
    
    result.second_table_identifier = table2_reference
    result.second_table_columns = columns_name2
    
    result.ast = statement
    if not identifier or skip_here or new_identifier.get_name():
        if new_identifier:
            result.name = new_identifier.get_name()
        else :
            # anonymous
            result.name = 'FK_%s_%s'  % (table1_reference.get_name(), table2_reference.get_name())
    else:
        result.name = identifier.get_name()
    
    if not result.name: result.name = 'FK_%s_%s' % (table1_reference.get_name(), table2_reference.get_name())

    parent_name = symbols.get_schema_name()
    if table1_reference.get_parent_name():
        parent_name = table1_reference.get_parent_name()
        

    result.fullname = "%s.%s" % (parent_name, result.name)

    # detect referDelete / referUpdate links
    on_delete = 0
    on_update = 0
    
    try:
        my_tokens = statement.get_tokens()
        my_tokens.move_to('REFERENCES')
        my_list = list(map(lambda x:x.text.lower(), list(my_tokens)))

        on_delete_update_cascade = list(filter(lambda x:x in ('update', 'delete', 'cascade'), my_list))        
        on_delete_update_restrict = list(filter(lambda x:x in ('update', 'delete', 'restrict'), my_list))

        on_delete_update_noaction = list(filter(lambda x:x in ('update', 'delete', 'no', 'action'), my_list))        
        on_delete_update_setnull = list(filter(lambda x:x in ('update', 'delete', 'null'), my_list))
        on_delete_update_setdefault = list(filter(lambda x:x in ('update', 'delete', 'default'), my_list))
                
        on_delete = len(list(filter(lambda x:x in ('on', 'delete'), my_list)))
        on_update = len(list(filter(lambda x:x in ('on', 'update'), my_list)))
        
    except AttributeError:
        pass

    if on_delete >=2:
        result.on_delete = True
        if on_delete_update_setdefault == ['update', 'default', 'delete', 'default'] \
            or on_delete_update_setdefault == ['delete', 'default', 'update', 'default']:
            result.on_delete_setdefault = True
            result.on_update_setdefault = True
        if on_delete_update_setnull == ['update', 'null', 'delete', 'null'] \
            or on_delete_update_setnull == ['delete', 'null', 'update', 'null']:
            result.on_delete_setnull = True
            result.on_update_setnull = True
        if on_delete_update_noaction == ['update', 'no', 'action', 'delete', 'no', 'action'] \
            or on_delete_update_noaction == ['delete', 'no', 'action', 'update', 'no', 'action']:
            result.on_delete_noaction = True
            result.on_update_noaction = True
        if on_delete_update_cascade == ['update', 'cascade', 'delete', 'cascade'] \
            or on_delete_update_cascade == ['delete', 'cascade', 'update', 'cascade']:
            result.on_delete_cascade = True
            result.on_update_cascade = True
        if on_delete_update_restrict == ['update', 'restrict', 'delete', 'restrict'] \
            or on_delete_update_restrict == ['delete', 'restrict', 'update', 'restrict']:
            result.on_delete_restrict = True
            result.on_update_restrict = True
            
        if on_delete_update_setdefault == ['delete', 'default'] \
            or on_delete_update_setdefault == ['update', 'delete', 'default'] \
            or on_delete_update_setdefault == ['delete', 'default', 'update']:
            result.on_delete_setdefault = True
        if on_delete_update_setnull == ['delete', 'null'] \
            or on_delete_update_setnull == ['update', 'delete', 'null'] \
            or on_delete_update_setnull == ['delete', 'null', 'update']:
            result.on_delete_setnull = True
        if on_delete_update_noaction == ['delete', 'no', 'action'] \
            or on_delete_update_noaction == ['update', 'delete', 'no', 'action'] \
            or on_delete_update_noaction == ['delete', 'action', 'no', 'update']:
            result.on_delete_noaction = True                        
        if on_delete_update_cascade == ['delete', 'cascade'] \
            or on_delete_update_cascade == ['update', 'delete', 'cascade'] \
            or on_delete_update_cascade == ['delete', 'cascade', 'update']:
            result.on_delete_cascade = True
        if on_delete_update_restrict == ['delete', 'restrict'] \
            or on_delete_update_restrict == ['delete', 'restrict', 'update'] \
            or on_delete_update_restrict == ['update', 'delete', 'restrict']:
            result.on_delete_restrict = True
                        
    if on_update >=2:
        result.on_update = True
        if on_delete_update_setdefault == ['update', 'default'] \
            or on_delete_update_setdefault == ['delete', 'update', 'default'] \
            or on_delete_update_setdefault == ['update', 'default', 'delete']:
            result.on_update_setdefault = True
        if on_delete_update_setnull == ['update', 'null'] \
            or on_delete_update_setnull == ['delete', 'update', 'null'] \
            or on_delete_update_setnull == ['update', 'null', 'delete']:
            result.on_update_setnull = True
        if on_delete_update_noaction == ['update', 'no', 'action'] \
            or on_delete_update_noaction == ['delete', 'update', 'no', 'action'] \
            or on_delete_update_noaction == ['update', 'action', 'no', 'delete']:
            result.on_update_noaction = True
        if on_delete_update_cascade == ['update', 'cascade'] \
            or on_delete_update_cascade == ['delete', 'update', 'cascade'] \
            or on_delete_update_cascade == ['update', 'cascade', 'delete']:
            result.on_update_cascade = True
        if on_delete_update_restrict == ['update', 'restrict'] \
            or on_delete_update_restrict == ['delete', 'update', 'restrict'] \
            or on_delete_update_restrict == ['update', 'restrict', 'delete']:
            result.on_update_restrict = True
              
    schema = symbols.register_symbol(result)
    
    schema.add_reference(table1_reference)
    schema.add_reference(table2_reference)
    
    return result
        
        

def create_package_body(statement, symbols):
    result = Package()
    result.ast = statement    
    result.name = statement.name.get_name()
    result.fullname = statement.name.get_fullname(symbols.get_schema_name())
    symbols.register_symbol(result)
    
    # add each procedure and function to the package which is a scope too
    for sub_statement in statement.get_sub_nodes():        
        if isinstance(sub_statement, Parenthesis):
            continue
            
        if isinstance(sub_statement, ProcedureBodyStatement):
            create_procedure(sub_statement, result)        
    
        elif isinstance(sub_statement, FunctionBodyStatement):
            create_function(sub_statement, result)        
    
    return result

def create_type_body(statement, symbols):

    result = Type()
    result.ast = statement    
    result.name = statement.name.get_name()
    result.fullname = statement.name.get_fullname(symbols.get_schema_name())
    symbols.register_symbol(result)
    
    # add each procedure and function to the type which is a scope too
    for sub_statement in statement.get_sub_nodes():
        
        if isinstance(sub_statement, MethodBodyStatement):
            create_method(sub_statement, result)            

    return result

def create_type_header(statement, symbols):
    if statement.useTypeName:
        result = create_type_body(statement, symbols) 
        return result
    
def create_method(statement, symbols):
    statement.type = Method
    
    return create_procedure_or_function(statement, symbols, Method)

def create_procedure(statement, symbols):
    statement.type = Procedure
    
    return create_procedure_or_function(statement, symbols, Procedure)

def create_sap_sqlscript_procedure(statement, symbols):
    statement.type = SAPMethodProcedure
    return create_procedure_or_function(statement, symbols, SAPMethodProcedure)

def create_sap_sqlscript_function(statement, symbols):
    statement.type = SAPMethodFunction
    return create_procedure_or_function(statement, symbols, SAPMethodFunction)

def create_function(statement, symbols):
    statement.type = Function
    return create_procedure_or_function(statement, symbols, Function)

def create_trigger(statement, symbols):

    return create_procedure_or_function(statement, symbols, Trigger)

def create_event(statement, symbols):

    return create_procedure_or_function(statement, symbols, Event)

def create_procedure_or_function(statement, symbols, symbol_type):
    """
    Parse a CREATE PROCEDURE ... statement.
    """
    result = symbol_type()

    try:
        identifier = statement.name
    except:
        log.debug('Name is missing for the statement %s' % statement)
        
    result.name = identifier.get_name()
    if not result.name:
        lookForName = statement.get_children()
        chekForName = next(lookForName)
        if chekForName in('FUNCTION', 'PROCEDURE', 'SAP_SQLSCRIPT', 'SAP_SQLSCRIPT_FUNCTION', 'TRIGGER', 'EVENT'):chekForName = next(lookForName)
        if chekForName.text.lower() in ('int', 'exists'):
            result.name = chekForName.text
    
    result.fullname = identifier.get_fullname(symbols.get_schema_name())
    if not result.fullname: result.fullname = result.name 
    
    if not result.name:
        return
    
    table_name = None
    
    if symbol_type == Trigger:
        
        identifier.types = [Trigger]
        
        # weirdly in sql server export, triggers come in double so search it first    
        if symbols.resolve_reference(identifier):
            return 
    
        # special for triggers
        result.events = statement.events
        result.table = statement.table
        table_name = statement.table

    # common part    
    schema = symbols.register_symbol(result)
    if isinstance(statement, SAPSqlScriptProcedureStatement) or isinstance(statement, SAPSqlScriptFunctionStatement):
        schema.kb_symbol = symbols.current_parent
    
    if table_name:
        schema.add_reference(table_name)

    result.ast = statement
    
    return result


##############################################
# Second pass on View, Proc, Function, Trigger
##############################################


def find_symbol(statement, symbols):
    """
    Find a symbol created in first pass. 
    """
    identifier = statement.name
    parent = identifier.get_parent_identifier()
    result = None
    schema = None
    if parent:
        schema = symbols.resolve_reference(parent, unique=True)
        result = symbols.resolve_reference(identifier)
    elif type(symbols) == Package:
        result = symbols.resolve_reference(identifier)
        schema = symbols
    elif type(symbols) == Type:
        result = symbols.resolve_reference(identifier)
        schema = symbols
    else:
        schema = symbols.find_symbol(symbols.get_schema_name())
        result = schema.resolve_reference(identifier)
        # the case of DB2 when schema is DEFAULT and not the one detected by us
        # the result is detected to by an empty list so we try to resolve it in the DEFAULT schema
        if isinstance(result, list) and len(result) == 0:
            schema = symbols.find_symbol('DEFAULT', [Schema])
            result = schema.resolve_reference(identifier)

    if result and len(result) == 1:
        result = result[0]
        # special case for sql server that dumps twice the same trigger
        if type(result) == Trigger and result.begin_line and result.begin_line != statement.get_begin_line():
            result = None
    elif result:
        
        # distinguish by begin line
        final = None
        for candidate in result:
            if candidate.begin_line == statement.get_begin_line():
                final = candidate
        
        result = final
        
    return result, schema

def analyze_dynamic_ms_sql_objects( statement, symbols, variables_list=None, variant=None, impact_analysis=False):
    tokens = statement.get_children() 
    for t in tokens:
        if t.type in (String.Single, Error):
            text = t.text.replace("'", "")
            statement.begin_line = t.begin_line
            statement.end_line = t.end_line
            break

    if text:
        for statement in parse(text, 'sqlserver', None): 
            if isinstance(statement, MSProcedureStatement) or isinstance(statement, MSFunctionStatement) or isinstance(statement, ProcedureStatement) or isinstance(statement, FunctionStatement):
                return (analyse_procedure(statement, symbols, variables_list, variant, impact_analysis))
            elif isinstance(statement, CreateViewStatement) or isinstance(statement, MSCreateViewStatement): 
                return (analyse_view(statement, symbols, variables_list, variant, impact_analysis))  
    
def analyse_view(statement, symbols, variables_list=None, variant=None, impact_analysis = False):
    """
    Second pass on views.
    """
    statement.name.types = [View]
    try:
        view, schema = find_symbol(statement, symbols)
    except AttributeError:
        schemas = symbols.find_symbols(symbols.declared_schema_name, [Schema])
        
        identifier = statement.name
        for schema in schemas:
            view = schema.find_symbol(identifier.get_name(), [View])
            if view:
                break
    
    if not view or isinstance(view, list): 
        return

    tokens = statement.get_children()
    tokens.move_to(['AS', 'IS'])
     
    select_result = SelectResult()
    analyse_select(parse_select(tokens), select_result, schema)
    try:
        if select_result.selects:
            view.selects = select_result.selects  
            view.controls = select_result.controls
    except:
        # issue with ipss_dump
        warning('SQL-006', 'Symbol %s cannot be analyzed.' % select_result)

    if impact_analysis:
        for selected_column in select_result.columns:
            try: 
                column = selected_column[0]
                table_column_alias = selected_column[1]
            except:
                try:
                    if len(selected_column) == 2:
                        column = selected_column[1]
                        table_column_alias = selected_column[0]
                except:
                    column = selected_column
                    table_column_alias = None
            
            if not isinstance(column, Token) and not table_column_alias:
                try:
                    column = selected_column[0].tokens[1]
                    table_column_alias = selected_column[0].get_parent_name()
                except IndexError:
                    pass
                
            select_star = False
            try:
                if column.text == '*':
                    select_star = True
                    column_file = symbols.current_file
                    bookmark = Bookmark(column_file, column.get_begin_line(), column.get_begin_column(), column.get_end_line(), column.get_end_column())
            except AttributeError:
                pass
            column.reference = None
            column.types = [Column]
            
            for selected_table in select_result.tables:
                table = selected_table[0]
                table_alias = selected_table[1]
    
                # when table and column are aliased and aliases doesn't match
                # skip it
                if table_column_alias:
                    table_column_alias = table_column_alias.text.lower() if isinstance(table_column_alias, Token) else table_column_alias.lower()
                
                if table_alias:
                    table_alias = table_alias.lower()
                    
                if table_alias and table_column_alias and table_alias != table_column_alias and table_column_alias != table.name.lower():
                    continue
                
                if table_column_alias and not table_alias and table_column_alias != table.name.lower():
                    continue
                
                # fix issue seen on Omega sources, whith table accessed as a.b.c
                # but saved in DEFAULT schema
                if table_column_alias in (table_alias, table.name.lower()):
                    table.types = [Table, View]
                    table.reference = schema.resolve_reference(table)
                    
                    if not table.reference:
                        table.reference = schema.find_symbols(table.name, table.types, None, None)
                                    
                detected_table = table.reference[0] if table.reference and isinstance(table.reference, list) else table.reference
                if select_star and table.reference:
                    
                    for star_column in detected_table.columns:
                        star_column.types = [Column]
                        star_column.reference = detected_table.find_column(star_column.name)
                        view.select_star_columns.append([star_column, bookmark])
                    continue
                elif not select_star and (table_column_alias and \
                                          (table_column_alias == table.name.lower() or \
                                           table_column_alias == table_alias.lower())) and \
                                           table.reference:
                    try:
                        column.reference = detected_table.find_column(column.get_name())
                        if not column.reference:
                            column.reference = detected_table.find_column_insensitive(column.get_name())
                    except AttributeError:
                        column.reference = detected_table.find_column_insensitive(column.text.lower())

                elif not select_star and not table_column_alias and table.reference and not table_alias:
                    try:
                        column.reference = detected_table.find_column(column.get_name())
                        if not column.reference:
                            column.reference = detected_table.find_column_insensitive(column.get_name())
                    except AttributeError:
                        column.reference = detected_table.find_column_insensitive(column.text.lower())

                if column.reference and not select_star:
                    break
    
            if not column.reference and not select_star:
                for table in schema.list_of_tables:
                    try:
                        column.reference = table.find_column(column.get_name())
                        if not column.reference:
                            column.reference = table.find_column_insensitive(column.get_name())
                    except AttributeError:
                        column.reference = table.find_column_insensitive(column.text.lower())
                    
                    if column.reference:
                        break
                    
            if column.reference and not select_star:
                try:
                    all_columns = column.tokens
                    c_ref = column.reference
                    column.types = [Column]
                    column = all_columns[1]
                    column.reference = c_ref
                    view.select_columns.append(column)
                except:
                    view.select_columns.append(column)
           
    for selected_table in select_result.tables:
        table = selected_table[0]
        table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
        table.reference = schema.resolve_reference(table)
        
        # fix issue seen on Omega sources, whith table accessed as a.b.c
        # but saved in DEFAULT schema
        if not table.reference:
            table.reference = schema.find_symbols(table.name, table.types, None, None)
                
        view.select_references.append(table)

    
    for proc in select_result.functions:
        proc.types = [Function, Procedure, Method, FunctionSynonym, ProcedureSynonym, Synonym]
        # search always in the right scope : schema and not symbols
        proc.reference = schema.resolve_reference(proc)
        if not proc.reference:
            # the case when a column has a method as type
            proc.types = [Method]
            tokens_list = proc.tokens
            method_name = proc.name
            full_name = proc.get_fullname()
            if full_name:
                proc.types = [Column]
                proc.name = full_name[0:full_name.find('.')]
                for table in schema.list_of_tables:
                    proc.reference = table.find_column(proc.name)
                    if proc.reference:
                        object_type_name = proc.reference.type
                        if object_type_name:
                            for object_type in schema.object_types:
                                if object_type.name == object_type_name:
                                    proc.types = [Method]
                                    proc.reference = object_type.find_methods(method_name)
                                    for token in tokens_list:
                                        if token.text == method_name:
                                            view.select_references.append(proc)
        else:
            proc.reference = schema.resolve_reference(proc)
            view.select_references.append(proc)

    for method in select_result.methods:
        proc = method[0]
        begin_line_method = method[1]
        begin_column_method = method[2]
        end_line_method = method[3]
        end_column_method = method[4]
        proc.types = [Method, Synonym, FunctionSynonym, ProcedureSynonym]
        proc.reference = schema.resolve_reference(proc)
        if proc.reference:
            t = [proc, begin_line_method, end_line_method, begin_column_method, end_column_method]
            view.select_dynamic_references.append(t)
                   
    return [view]
    
def analyse_procedure(statement, symbols, parent_variables_list=None, variant=None, impact_analysis = False):   
    begin_line = 0
    end_line = 0
    begin_column = 0

    list_of_statements = set()

    def analyse_inner_block (tokens, statement, begin_line, end_line, begin_column):       
        for token in tokens.get_children():
            if isinstance(token, (ExecuteImmediate, ExecuteDynamicCursor, ExecuteDynamicString0, ExecuteDynamicString2, \
                          ExecuteDynamicString3,  ExecuteDynamicString4, ExecuteDynamicString5,  ExecuteDynamicString6)):
                if isinstance(token, ExecuteDynamicCursor):
                    all_tokens = token.get_children()
                    all_tokens.move_to('FOR')
                    tok = all_tokens.look_next()
                    if tok.type == String.Single:
                        if begin_line == 0:
                            begin_line = tok.get_begin_line()
                            begin_column = tok.get_begin_column()
                            end_line = tok.get_end_line()
                        statement = " ".join([statement, tok.text.replace("'", "").replace('"', '').replace('|','')]) 
            elif isinstance(token, BlockStatement):
                statement , _, _, _ = analyse_inner_block(token, statement, begin_line, end_line, begin_column)
            elif token.type == String.Single and \
                    ('SELECT' in token.text.upper() or \
                     'UPDATE' in token.text.upper() or \
                     'INSERT' in token.text.upper() or \
                     'DELETE' in token.text.upper() or \
                     'TRUNCATE' in token.text.upper() or \
                     'EXEC' in token.text.upper() or \
                     'MERGE' in token.text.upper()):
                if statement:
                    t = (statement, begin_line, end_line, begin_column)
                    if t not in list_of_statements:
                        list_of_statements.add(t)

                    statement = ''
                    begin_line = 0
                    end_line = 0
                    begin_column = 0
                    
                begin_line = token.get_begin_line()
                begin_column = token.get_begin_column()
                end_line = token.get_end_line()

                statement = " ".join([statement, token.text.replace("'", "").replace('"', '').replace('|','')])

            elif begin_line > 0 and token.type == String.Single and statement and not \
                     'SELECT' in token.text.upper() and not \
                     'UPDATE' in token.text.upper() and not \
                     'INSERT' in token.text.upper() and not \
                     'DELETE' in token.text.upper() and not \
                     'TRUNCATE' in token.text.upper() and not \
                     'EXEC' in token.text.upper() and not \
                     'MERGE' in token.text.upper():
                statement = " ".join([statement, token.text.replace("'", "").replace('"', '').replace('|','')])

        if statement and begin_line >= 0 and \
            ('SELECT' in statement.upper() or \
             'UPDATE' in statement.upper() or \
             'INSERT' in statement.upper() or \
             'DELETE' in statement.upper() or \
             'TRUNCATE' in statement.upper() or \
             'EXEC' in statement.upper() or \
             'MERGE' in statement.upper()):

            t = (statement, begin_line, end_line, begin_column)
            if t not in list_of_statements:
                list_of_statements.add(t)
                statement = ''
                begin_line = 0
                end_line = 0
                begin_column = 0
                                                                       
        return (statement, begin_line, end_line, begin_column)


    def analyse_block (tokens, statement, begin_line, end_line, begin_column):
        var_name = None
        var_value = None
        
        for token in tokens.get_children():
            if isinstance(token, (ExecuteImmediate, ExecuteDynamicCursor, ExecuteDynamicString0, ExecuteDynamicString2, \
                                  ExecuteDynamicString3, ExecuteDynamicString4, ExecuteDynamicString5, ExecuteDynamicString6)):
                if isinstance(token, ExecuteDynamicCursor):
                    all_tokens = token.get_children()
                    all_tokens.move_to('FOR')
                    tok = all_tokens.look_next()
                    if tok.type == String.Single:
                        if begin_line == 0:
                            begin_line = tok.get_begin_line()
                            begin_column = tok.get_begin_column()
                            end_line = tok.get_end_line()
                        statement = " ".join([statement, tok.text.replace("'", "").replace('"', '').replace('|','')])

            elif token.type == String.Single and \
                ('SELECT' in token.text.upper() or \
                 'UPDATE' in token.text.upper() or \
                 'INSERT' in token.text.upper() or \
                 'DELETE' in token.text.upper() or \
                 'TRUNCATE' in token.text.upper() or \
                 'EXEC' in token.text.upper() or \
                 'MERGE' in token.text.upper()):
                if statement:
                    t = (statement, begin_line, end_line, begin_column)
                    if t not in list_of_statements:
                        list_of_statements.add(t)
                    statement = ''
                    begin_line = 0
                    end_line = 0
                    begin_column = 0
                    
                begin_line = token.get_begin_line()
                begin_column = token.get_begin_column()
                end_line = token.get_end_line()

                statement = " ".join([statement, token.text.replace("'", "").replace('"', '').replace('|','')])
            elif begin_line > 0 and token.type == String.Single and statement and not \
                     'SELECT' in token.text.upper() and not \
                     'UPDATE' in token.text.upper() and not \
                     'INSERT' in token.text.upper() and not \
                     'DELETE' in token.text.upper() and not \
                     'TRUNCATE' in token.text.upper() and not \
                     'EXEC' in token.text.upper() and not \
                     'MERGE' in token.text.upper():
                statement = " ".join([statement, token.text.replace("'", "").replace('"', '').replace('|','')])
            elif isinstance(token, BlockStatement):
                statement, _, _, _ = analyse_inner_block(token, statement, begin_line, end_line, begin_column)
            elif (token.type == Name or isinstance(token, FunctionCall)) and var_name:
                var_value = token.children[0].text if isinstance(token, FunctionCall) else token.text
                if var_name != var_value:
                    t = (var_name, var_value)
                    variables_list.add(t)
                var_name = None
                var_value = None
            elif token.type == Name and not var_name:
                var_name = token.text
        
        if statement and begin_line >= 0 and \
            ('SELECT' in statement.upper() or \
             'UPDATE' in statement.upper() or \
             'INSERT' in statement.upper() or \
             'DELETE' in statement.upper() or \
             'TRUNCATE' in statement.upper() or \
             'EXEC' in statement.upper() or \
             'MERGE' in statement.upper()):

            t = (statement, begin_line, end_line, begin_column)
            if t not in list_of_statements:
                list_of_statements.add(t)
                statement = ''
                begin_line = 0
                end_line = 0
                begin_column = 0
               
        return (statement, begin_line, end_line, begin_column)
            
    result, schema = find_symbol(statement, symbols)

    if result:
        reparse_procedure(result, schema, statement, variant, symbols, impact_analysis)
       
        if not result.dexecutes:
            return [result]
        
        # the case of dynamic SQL
        tokens = statement.get_children()
        tokens.move_to(['AS', 'IS'])
        
        variables_list = set()
        var_name = None
        var_value = None
        # only variable
        for token in tokens:
            if type(token) in (Block, PostgresqlBlock):
                break 
            elif token.type == Name and token != 'ROWTYPE':
                if not var_name:
                    var_name = token.text
                else:
                    var_value = token.text
                    t = (var_name, var_value)
                    variables_list.add(t)
                    var_name = None
                    var_value = None
        
        if parent_variables_list:
            variables_list = variables_list.union(parent_variables_list)
        
        if result.dexecutes:    
            def match_variable(table):      
                for variable in variables_list:
                    if table == variable[0]:
                        return variable[1]
                    
                return None
                        
            def detect_variable (variables_list, table):
                variable_name = set()
                for variable in variables_list:
                    if table == variable[0]:
                        variable_name.add(variable[1])
                if len(variable_name) >= 1:
                    for table in variable_name:
                        if match_variable(table):
                            return match_variable(table)
                    else:
                        if len(variable_name) == 1:
                            return variable_name.pop()
                        
                return None                            
                
    
            begin_line = 0
            for token in statement.get_children():
                if type(token) in (Block, PostgresqlBlock):
                    _, _, _, _ = analyse_block(token, '', begin_line, end_line, begin_column)

                    if len(list_of_statements) > 0:
                        lexer = create_lexer(SqlLexer)
                        
                        for little_statement in list_of_statements:
                            select_result = SelectResult()
                            begin_line = little_statement[1]
                            end_line = little_statement[2]
                            begin_column = little_statement[3]
                            upper_statement = little_statement[0].upper()
                            if 'INSERT' in upper_statement and \
                                not 'VALUES' in upper_statement and \
                                not 'SELECT' in upper_statement:
                                transformed_statement = little_statement[0] + ' select 1'
                                stream = Lookahead(lexer.get_tokens(transformed_statement))
                            else:
                                stream = Lookahead(lexer.get_tokens(little_statement[0]))
                            analyse_select(parse_select(stream), select_result, symbols)
                            for method  in select_result.methods:
                                proc = method[0]
                                begin_line_method = method[1]
                                begin_column_method = method[2]
                                end_line_method = method[3]
                                end_column_method = method[4]
                                proc.types = [Method, Synonym, FunctionSynonym, ProcedureSynonym]
                                proc.reference = schema.resolve_reference(proc)
                                if proc.reference:
                                    t = [proc, begin_line_method, end_line_method, begin_column_method, end_column_method]
                                    result.select_dynamic_references.append(t)
                        
                            # when tables are not resolved check them in variables 
                            for selected_table in select_result.tables:
                                table = selected_table[0]
                                table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
                                table.reference = schema.resolve_reference(table)

                                if not table.reference:
                                    new_table = detect_variable (variables_list, table.name)
                                    
                                    if new_table:
                                        new_statement = little_statement[0].replace(table.name, new_table)
                                        stream = Lookahead(lexer.get_tokens(new_statement))
                                        analyse_select(parse_select(stream), select_result, symbols)
                                        break
                                    else:
                                        new_table = detect_variable (variables_list, table.parent_name)
                                        if new_table:
                                            new_statement = little_statement[0].replace('{}.{}'.format(table.parent_name,table.name), new_table)
                                            stream = Lookahead(lexer.get_tokens(new_statement))
                                            analyse_select(parse_select(stream), select_result, symbols)
                                            break
                                        
                            # less than 1 because of the 1st quote
                            begin_column -= 1
                            common_reparse_procedure(result, schema, select_result, begin_line, end_line, begin_column)
                            begin_line = 0
                            end_line = 0
                            begin_column = 0
                    list_of_statements = set()
                        
        #  detach memory     
        variables_list = set()
        return [result]

def common_reparse_procedure(result, schema, select_result, initial_begin_line, initial_end_line, initial_begin_column):
    
    for selected_table in select_result.tables:
        table = selected_table[0]
        table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
        table.reference = schema.resolve_reference(table)

        try:
            begin_column = initial_begin_column + table.tokens[len(table.tokens)-1].begin_column
            end_column = initial_begin_column + table.tokens[len(table.tokens)-1].end_column
        except IndexError:
            begin_column = 0
            end_column = 0
        t = [table, initial_begin_line, initial_end_line, begin_column, end_column]
        result.select_dynamic_references.append(t)

    for inserted_table in select_result.insert_references:
        table = inserted_table[0]
        table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
        table.reference = schema.resolve_reference(table)
            
        try:
            begin_column = initial_begin_column + table.tokens[len(table.tokens)-1].begin_column
            end_column = initial_begin_column + table.tokens[len(table.tokens)-1].end_column
        except IndexError:
            begin_column = 0
            end_column = 0
        t = [table, initial_begin_line, initial_end_line, begin_column, end_column]
        result.insert_dynamic_references.append(t)
        
    for deleted_table in select_result.delete_references:
        # the case when is a list vs identifier
        try:
            table = deleted_table[0][0]
        except:
            table = deleted_table[0]
        table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
        table.reference = schema.resolve_reference(table)

        try:
            begin_column = initial_begin_column + table.tokens[len(table.tokens)-1].begin_column
            end_column = initial_begin_column + table.tokens[len(table.tokens)-1].end_column
        except IndexError:
            begin_column = 0
            end_column = 0
        t = [table, initial_begin_line, initial_end_line, begin_column, end_column]
        result.delete_dynamic_references.append(t)

    for updated_table in select_result.update_references:
        table = updated_table[0]
        table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
        table.reference = schema.resolve_reference(table)
        try:
            begin_column = initial_begin_column + table.tokens[len(table.tokens)-1].begin_column
            end_column = initial_begin_column + table.tokens[len(table.tokens)-1].end_column
        except IndexError:
            begin_column = 0
            end_column = 0
        t = [table, initial_begin_line, initial_end_line, begin_column, end_column]
        result.update_dynamic_references.append(t)

    for proc in select_result.functions:
        proc.types = [Function, Procedure, Method, Synonym, FunctionSynonym, ProcedureSynonym]
        proc.reference = schema.resolve_reference(proc)
        # the case of object types
        if not proc.reference and isinstance(schema, Schema):
            # the case when a column has a method as type
            tokens_list = proc.tokens
            method_name = proc.name
            full_name = proc.get_fullname()
            if full_name:
                dot_position = full_name.find('.')
                if dot_position > 0:
                    proc.types = [Column]
                    column_name = full_name[0:full_name.find('.')]
                    for table in schema.list_of_tables:
                        proc.reference = table.find_column_insensitive(column_name)
                        if proc.reference:
                            object_type_name = proc.reference.type
                            if object_type_name:
                                for object_type in schema.object_types:
                                    if object_type.name == object_type_name:
                                        proc.types = [Method]
                                        proc.reference = object_type.find_methods(method_name)
                                        for token in tokens_list:
                                            if token.text == method_name:
                                                try:
                                                    begin_column = initial_begin_column + token.begin_column
                                                    end_column = initial_begin_column + token.end_column
                                                except IndexError:
                                                    begin_column = 0
                                                    end_column = 0
                                                t = [proc, initial_begin_line, initial_end_line, begin_column, end_column]
                                                result.select_dynamic_references.append(t)
                                
                    else:
                        proc.types = [Function, Procedure, Method, Synonym, FunctionSynonym, ProcedureSynonym]
                        try:
                            begin_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].begin_column
                            end_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].end_column
                        except IndexError:
                            begin_column = 0
                            end_column = 0
                        t = [proc, initial_begin_line, initial_end_line, begin_column, end_column]
                        result.select_dynamic_references.append(t)
                        
                else:
                    proc.types = [Function, Procedure, Method, Synonym, FunctionSynonym, ProcedureSynonym]
                    try:
                        begin_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].begin_column
                        end_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].end_column
                    except IndexError:
                        begin_column = 0
                        end_column = 0
                    t = [proc, initial_begin_line, initial_end_line, begin_column, end_column]
                    result.select_dynamic_references.append(t)
        elif not proc.reference and isinstance(schema, Type):
            
            if schema.find_methods(proc.get_name()):
                proc.types = [Method]
                proc.reference = schema.find_methods(proc.get_name())
            elif schema.find_inherited_methods(proc.get_name()):
                proc.types = [Method]
                proc.reference = schema.find_inherited_methods(proc.get_name())

            if proc.reference:
                try:
                    begin_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].begin_column
                    end_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].end_column
                except IndexError:
                    begin_column = 0
                    end_column = 0
                t = [proc, initial_begin_line, initial_end_line, begin_column, end_column]
                result.select_dynamic_references.append(t)

        elif not proc.reference and not isinstance(schema, Type) and not isinstance(schema, Schema):
            schema_ = schema.parent_scope
            for object_type in schema_.object_types:
                if object_type.name == proc.name:
                    proc.types = [Method]
                    proc.reference = object_type.find_methods(proc.name)
                    try:
                        begin_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].begin_column
                        end_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].end_column
                    except IndexError:
                        begin_column = 0
                        end_column = 0
                    t = [proc, initial_begin_line, initial_end_line, begin_column, end_column]
                    result.select_dynamic_references.append(t)
        else:
            try:
                begin_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].begin_column
                end_column = initial_begin_column + proc.tokens[len(proc.tokens)-1].end_column
            except IndexError:
                begin_column = 0
                end_column = 0
            t = [proc, initial_begin_line, initial_end_line, begin_column, end_column]
            result.select_dynamic_references.append(t)
                
def reparse_procedure(procedure, symbols, statement, variant=None, context=None, impact_analysis = False):
    try:
        select_result = SelectResult()
        try:
            analyse_select(parse_select(statement.content), select_result, symbols)
        except:
            log.info('Reparsing error : %s.' % format_exc())
    except:
        return Unknown()

    if impact_analysis:   
        for selected_column in select_result.columns:
            try: 
                column = selected_column[0]
                table_column_alias = selected_column[1]
            except:
                try:
                    if len(selected_column) == 2:
                        column = selected_column[1]
                        table_column_alias = selected_column[0]
                except:
                    column = selected_column
                    table_column_alias = None
                    
            select_star = False
            try:
                if column.text == '*':
                    select_star = True
                    column_file = context.current_file
                    bookmark = Bookmark(column_file, column.get_begin_line(), column.get_begin_column(), column.get_end_line(), column.get_end_column())
            except AttributeError:
                pass
            column.reference = None
            column.types = [Column]
            
            column_begin_line, column_end_line = 0, 0
            if isinstance(column, Token):
                column_begin_line = column.get_begin_line()
                column_end_line = column.get_end_line()
            else:
                try:
                    column_begin_line = column.tokens[0].get_begin_line()
                    column_end_line = column.tokens[0].get_end_line()
                except AttributeError:
                    continue

            select_begin_line, select_begin_line = 0, 0
            
            for sel in select_result.selects: 
                if not isinstance(sel, Insert) and sel.get_begin_line() <= column_begin_line and \
                    column_end_line <= sel.get_end_line():
                    select_begin_line, select_end_line = sel.get_begin_line(), sel.get_end_line()
                    break
            
            detected_table = None
            
            for selected_table in select_result.tables + select_result.update_references + select_result.delete_references:
                table = selected_table[0]
                table_alias = selected_table[1]
                
                if isinstance(table, list):
                    table = table[0]

                # when table and column are aliased and aliases doesn't match
                # skip it
                if table_alias and table_column_alias and table_alias != table_column_alias and table_column_alias != table.name:
                    continue
                
                if table_column_alias and not table_alias and table_column_alias != table.name:
                    continue
    
                if isinstance(table, Token):
                    table_begin_line = table.get_begin_line()
                    table_end_line = table.get_end_line()
                else:
                    table_begin_line = table.tokens[0].get_begin_line()
                    table_end_line = table.tokens[0].get_end_line()
                
                # skip homonymous tables 
                if not (select_begin_line <= table_begin_line and \
                    table_end_line <= select_end_line):
                    continue     

                table.types = [Table, View]
                table.reference = symbols.resolve_reference(table)
                
                detected_table = table.reference[0] if table.reference and isinstance(table.reference, list) else table.reference
                
                if select_star and table.reference:
                    for star_column in detected_table.columns:
                        star_column.types = [Column]
                        star_column.reference = detected_table.find_column(star_column.name)
                        try:    
                            procedure.select_star_columns.append([star_column, bookmark])
                        except UnboundLocalError:
                            pass
                    continue                       
                elif not select_star and (table_column_alias and table_column_alias == table.name or table_column_alias == table_alias) and \
                             table.reference:
                    try:
                        column.reference = detected_table.find_column(column.get_name())
                        if not column.reference:
                            column.reference = detected_table.find_column_insensitive(column.get_name())
                    except AttributeError:
                        column.reference = detected_table.find_column_insensitive(column.text)
                elif not select_star and not table_column_alias and table.reference and not table_alias:
                    try:
                        column.reference = detected_table.find_column(column.get_name())
                        if not column.reference:
                            column.reference = detected_table.find_column_insensitive(column.get_name())
                    except AttributeError:
                        column.reference = detected_table.find_column_insensitive(column.text)
                
                if column.reference and not select_star:
                    break
            
            if not column.reference and not select_star:
                try:
                    for table in context.list_of_tables:
                        try:
                            column.reference = table.find_column(column.get_name())
                            if not column.reference:
                                column.reference = table.find_column_insensitive(column.get_name())
                        except AttributeError:
                            column.reference = table.find_column_insensitive(column.text)

                        if column.reference:
                            break
                except AttributeError:
                    pass
            
            if column.reference and not select_star:
                try:
                    all_columns = column.tokens
                    c_ref = column.reference
                    column.types = [Column]
                    column = all_columns[1]
                    column.reference = c_ref
                    procedure.select_columns.append(column)
                except:
                    procedure.select_columns.append(column)
    
        for write_column in select_result.write_columns:
            column = write_column[0]
            if column:
                column.reference = None
                column.types = [Column]
                column.name = column.text
                table = write_column[1]
                table.types = [Table, View]
                table.reference = symbols.resolve_reference(table)
                        
                detected_table = table.reference[0] if table.reference and isinstance(table.reference, list) else table.reference
                
                try:
                    if detected_table:
                        column.reference = detected_table.find_column_insensitive(column.text)
                    else:
                        column.reference = None
                except (IndexError, AttributeError):
                    pass
                
                if column.reference:
                    procedure.write_columns.append(column)
            else:
                table = write_column[1]
                table.types = [Table, View]
                table.reference = symbols.resolve_reference(table)
                
                detected_table = table.reference[0] if table.reference and isinstance(table.reference, list) else table.reference
                
                column_file = None
                try:
                    column_file = context.current_file
                except AttributeError:
                    try:
                        column_file = symbols.parent_scope.parent_scope.current_file
                    except AttributeError:
                        pass
                try:
                    bookmark = Bookmark(column_file, table.tokens[0].get_begin_line(), table.tokens[0].get_begin_column(), table.tokens[0].get_end_line(), table.tokens[0].get_end_column())
                except IndexError:
                    pass
                try:
                    if detected_table:
                        for star_column in detected_table.columns:
                            star_column.reference = None
                            star_column.types = [Column]
                            try:
                                star_column.reference = detected_table.find_column_insensitive(star_column.name)
                            except IndexError:
                                pass
                            if star_column.reference:
                                procedure.write_star_columns.append([star_column, bookmark])

                except (IndexError, TypeError):
                    pass

    for selected_table in select_result.tables:

        table = selected_table[0]
        table.types = [Table, View]
        table.reference = symbols.resolve_reference(table)
            
        if not table.reference:
            table.types = [TableSynonym, ViewSynonym, Synonym]
            table.reference = symbols.resolve_reference(table)

        # the case of ABAP
        if not table.reference:
            table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
        
        procedure.select_references.append(table)
     
    for proc in select_result.functions:
        proc.types = [Function, Procedure, Method]
        proc.reference = symbols.resolve_reference(proc)

        if not proc.reference:
            proc.types = [Synonym, FunctionSynonym, ProcedureSynonym]
            proc.reference = symbols.resolve_reference(proc)
            
        # the case of object types
        if not proc.reference and isinstance(symbols, Schema):
            # the case when a column has a method as type
            proc.types = [Function, Procedure, Method, Synonym, FunctionSynonym, ProcedureSynonym]
            tokens_list = proc.tokens
            method_name = proc.name
            full_name = proc.get_fullname()
            if full_name:
                dot_position = full_name.find('.')
                if dot_position > 0:
                    proc.types = [Column]
                    column_name = full_name[0:full_name.find('.')]
                    for table in symbols.list_of_tables:
                        proc.reference = table.find_column_insensitive(column_name)
                        if proc.reference:
                            object_type_name = proc.reference.type
                            if object_type_name:
                                for object_type in symbols.object_types:
                                    if object_type.name == object_type_name:
                                        proc.types = [Method]
                                        proc.reference = object_type.find_methods(method_name)
                                        for token in tokens_list:
                                            if token.text == method_name:
                                                procedure.select_references.append(proc)                                                
                    else:
                        proc.types = [Function, Procedure, Method, Synonym, FunctionSynonym, ProcedureSynonym]
                        procedure.select_references.append(proc)
        elif not proc.reference and isinstance(symbols, Type):
            
            if symbols.find_methods(proc.get_name()):
                proc.types = [Method]
                proc.reference = symbols.find_methods(proc.get_name())
            elif symbols.find_inherited_methods(proc.get_name()):
                proc.types = [Method]
                proc.reference = symbols.find_inherited_methods(proc.get_name())

            if proc.reference:
                procedure.select_references.append(proc)
            else:
                # the case of type which is table of another type
                proc.types = [Type]
                proc.reference = symbols.resolve_reference(proc)
                procedure.select_references.append(proc)

        elif not proc.reference and not isinstance(symbols, Type) and not isinstance(symbols, Schema):
            schema = symbols.parent_scope
            for object_type in schema.object_types:
                if object_type.name == proc.name:
                    proc.types = [Method]
                    proc.reference = object_type.find_methods(proc.name)
                    procedure.select_references.append(proc)
        else:
            # when the caller and callee are overloaded we should check at least the number of parameters 
            list_of_references = proc.reference
            proc.types = [Function, Procedure, Method, Synonym, FunctionSynonym, ProcedureSynonym]
            try:
                for proc_detail in list_of_references: 
                    try:
                        exception_on_called_parameters = False
                        cnt_called_parameters = getattr(proc, 'parameters')   
                    except:
                        exception_on_called_parameters = True
                        cnt_called_parameters = 0
    
                    cnt_default = (0 if getattr(proc_detail, 'default_parameters') is None else getattr(proc_detail, 'default_parameters'))
                    cnt_parameters = (0 if getattr(proc_detail, 'count_parameters') is None else getattr(proc_detail, 'count_parameters'))
                    # resolve according with number of parameters and how many are default
                    proc.reference = symbols.resolve_reference(proc, False, cnt_parameters, cnt_default)
                    # overloading the case of default parameters
                    # aliased objects are resolved in post application step so we should let all kind of Synonyms to be resolved as before
                    if variant!=Variant.informix and not isinstance(proc_detail, Synonym) and not isinstance(proc_detail, FunctionSynonym) and \
                        not isinstance(proc_detail, ProcedureSynonym) and not exception_on_called_parameters and cnt_default > 0 and \
                        (cnt_called_parameters >= cnt_parameters - cnt_default and cnt_called_parameters <= cnt_parameters):
                        t = [proc, cnt_called_parameters, proc.reference]
                        procedure.select_parameters_references.append(t)
                        continue                    
    #                 proc.reference = proc_detail
                    # overloading, the case of the same number of parameters
                    elif variant!=Variant.informix and not isinstance(proc_detail, Synonym) and not isinstance(proc_detail, FunctionSynonym) and \
                        not isinstance(proc_detail, ProcedureSynonym) and not exception_on_called_parameters and \
                        ((isinstance(procedure, Function) or isinstance(procedure, Procedure) or isinstance(procedure, Method) or isinstance(procedure, Trigger)) and \
                        proc.name.lower().strip() == procedure.name.lower().strip() and cnt_called_parameters == cnt_parameters):
                        t = [proc, cnt_called_parameters, proc.reference]
                        procedure.select_parameters_references.append(t)
    
                    # All except Informix : no overloading, let them pass as before
                    
                    # Informix
                    # When you invoke an SPL routine, you can specify all, some, or none of the defined arguments. 
                    # If you do not specify an argument, and if its corresponding parameter does not have a default value, the argument, 
                    # which is used as a variable within the SPL routine, is given a status of undefined.
                    elif variant==Variant.informix or isinstance(proc_detail, Synonym) or isinstance(proc_detail, FunctionSynonym) or \
                        isinstance(proc_detail, ProcedureSynonym) or exception_on_called_parameters or \
                        (proc.name != procedure.name and cnt_called_parameters == cnt_parameters):
                        proc.reference = symbols.resolve_reference(proc, False, cnt_parameters)
                        if isinstance(proc_detail, Synonym) and proc in procedure.select_references:
                            continue
                        procedure.select_references.append(proc)
            except TypeError:
                if proc.reference:
                    proc.types = [Function, Procedure, Method, Synonym, TableSynonym, ViewSynonym, FunctionSynonym, ProcedureSynonym]
                    proc.reference = symbols.resolve_reference(proc) 
                    if proc not in procedure.select_references:
                        procedure.select_references.append(proc) 
        
        if not proc.reference and symbols.parent_scope:
            parent_symbols = symbols.parent_scope
            for detail in parent_symbols.sub_scopes:
                proc.reference = detail.find_symbol(proc.get_name(), [TableSynonym, ViewSynonym, TypeSynonym, FunctionSynonym, ProcedureSynonym])
                if proc.reference:
                    proc.types = [TableSynonym, ViewSynonym, TypeSynonym, FunctionSynonym, ProcedureSynonym]
                    procedure.select_references.append(proc)
                    break
            else:
                proc.types = [Function, Procedure, Method, Synonym, FunctionSynonym, ProcedureSynonym]
                if not '@' in str(proc) and proc.get_name() and proc not in procedure.select_references:
                    procedure.select_references.append(proc)
                                                   
        elif not proc.reference and not symbols.parent_scope:
            proc.types = [Function, Procedure, Method, Synonym, FunctionSynonym, ProcedureSynonym]
            if not '@' in str(proc) and proc.get_name() and proc not in procedure.select_references:
                procedure.select_references.append(proc)
                                                   
    for method  in select_result.methods:
        proc = method[0]
        begin_line_method = method[1]
        begin_column_method = method[2]
        end_line_method = method[3]
        end_column_method = method[4]
        proc.types = [Method, Synonym, FunctionSynonym, ProcedureSynonym]
        proc.reference = symbols.resolve_reference(proc)
        if proc.reference:
            t = [proc, begin_line_method, end_line_method, begin_column_method, end_column_method]
            procedure.select_dynamic_references.append(t)
                                        
    for inserted_table in select_result.insert_references:
        
        table = inserted_table [0]
        table.types = [Table, View]
        table.reference = symbols.resolve_reference(table)
                  
        if not table.reference:
            table.types = [TableSynonym, ViewSynonym, Synonym]
            table.reference = symbols.resolve_reference(table)

        # the case of ABAP
        if not table.reference:
            table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]

        procedure.insert_references.append(table)
        
    for deleted_table in select_result.delete_references:
        # the case when is a list vs identifier
        try:
            table = deleted_table[0][0]
        except:
            table = deleted_table[0]
        table.types = [Table, View]
        table.reference = symbols.resolve_reference(table)
                    
        if not table.reference:
            table.types = [TableSynonym, ViewSynonym, Synonym]
            table.reference = symbols.resolve_reference(table)

        # the case of ABAP
        if not table.reference:
            table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]

        procedure.delete_references.append(table)

    for updated_table in select_result.update_references:
        table = updated_table[0]
        table.types = [Table, View]
        table.reference = symbols.resolve_reference(table)
            
        if not table.reference:
            table.types = [TableSynonym, ViewSynonym, Synonym]
            table.reference = symbols.resolve_reference(table)

        # the case of ABAP
        if not table.reference:
            table.types = [Table, View, TableSynonym, ViewSynonym, Synonym]
            
        procedure.update_references.append(table)
        
    procedure.selects = select_result.selects
    procedure.gotos = select_result.gotos
    procedure.dexecutes = select_result.dexecutes
    procedure.controls = select_result.controls

def catch_parent_variable_list (statement):
    tokens  = statement.get_children()
    tokens.move_to(['AS', 'IS'])
    
    variables_list = set()
    var_name = None
    var_value = None
    # only variable
    for token in tokens:
        if type(token) in (ProcedureBodyStatement, FunctionBodyStatement, MethodBodyStatement, Block, PostgresqlBlock):
            break 
        elif token == 'TYPE':
            tokens.move_to(';')
        elif token.type == Name and token != 'ROWTYPE':
            if not var_name:
                var_name = token.text
            else:
                var_value = token.text
                t = (var_name, var_value)
                variables_list.add(t)
                var_name = None
                var_value = None
    
    return variables_list

def analyse_package_body(statement, symbols, variables_list=None, variant=None, impact_analysis = False):
    result, _ = find_symbol(statement, symbols)
    
    parent_variables_list = catch_parent_variable_list(statement)
    body_elements = []
    for sub_statement in statement.get_sub_nodes() :
        temp = analyse_symbol(sub_statement, result, True, parent_variables_list, variant, impact_analysis) if isinstance(sub_statement, (FunctionBodyStatement, ProcedureBodyStatement)) else None
        if temp:
            body_elements += temp
    
    #detach memory
    # del parent_variables_list
    parent_variables_list = set()
  
    return body_elements

def analyse_type_body(statement, symbols, variables_list=None, variant=None, impact_analysis = False):
    result, _ = find_symbol(statement, symbols)

    parent_variables_list = catch_parent_variable_list(statement)       

    body_elements = []
    for sub_statement in statement.get_sub_nodes() :
        temp = analyse_symbol(sub_statement, result, True, parent_variables_list, variant, impact_analysis) if isinstance(sub_statement, MethodBodyStatement) else None
        if temp:
            body_elements += temp
        
    #detach memory
    # del parent_variables_list
    parent_variables_list = set()

    return body_elements

def analyse_type_header(statement, symbols, variables_list=None, variant=None, impact_analysis = False):
    try:
        type_object, schema = find_symbol(statement, symbols)
        if type_object and statement.superTypeName:
            if type_object.name == statement.object_type_name and not (statement.object_type_name == statement.superTypeName) and statement.object_type_name and statement.superTypeName:
                for object_type in schema.object_types:
                    if object_type.name == statement.superTypeName:
                        tokens = statement.get_tokens()
                        tokens.move_to(type_object.name)
                        super_position = tokens.look_next()
                        bookmark = Bookmark(type_object.file, super_position.begin_line, super_position.begin_column, super_position.end_line, super_position.end_column)
                        type_object.inherit_references.append([object_type, bookmark])
                        return [type_object]
        elif type_object and statement.useTypeName:
            useTypeName = statement.useTypeName.text.replace('"', '').replace("'", "") 
            for object_type in schema.object_types:
                if object_type.name == useTypeName:
                    tokens = statement.get_tokens()
                    tokens.move_to(statement.useTypeName)
                    use_position = tokens.look_next()
                    bookmark = Bookmark(type_object.file, use_position.begin_line, use_position.begin_column, use_position.end_line, use_position.end_column)
                    type_object.use_references.append([object_type, bookmark])
                    return [type_object]
    
    except:
        pass
