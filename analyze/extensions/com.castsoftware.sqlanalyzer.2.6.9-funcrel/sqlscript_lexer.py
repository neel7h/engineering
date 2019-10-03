'''
Created on 1 dec. 2014

@author: MRO
'''
from re import IGNORECASE
from pygments.lexer import RegexLexer, inherit
from pygments.token import Punctuation, \
     Text, Comment, Operator, Keyword, Name, String, Number, Generic

EndIf = Keyword.EndIf
EndLoop = Keyword.EndLoop
EndRepeat = Keyword.EndRepeat
EndWhile = Keyword.EndWhile
EndCase = Keyword.EndCase
EndCatch = Keyword.EndCatch
BeginTransaction = Keyword.BeginTransaction

class BaseSqlLexer(RegexLexer):
    """
    Lexer for Structured Query Language. Currently, this lexer does
    not recognize any special syntax except ANSI SQL.
    """

    name = 'SQL'
    aliases = ['sql']
    filenames = ['*.sql']
    mimetypes = ['text/x-sql']

    flags = IGNORECASE
    tokens = {
        'root': [
            (r'\nCOPY[\s\S]*\n\\\.', Generic),  # ignore embedded data within COPY and \. blocks
            (r'\s+', Text),
            (r'REM\n', Comment.Single),# REM[ARK] Begins a comment in a script. SQL*Plus does not interpret the comment as a command. It should be followed by a new line
            (r'REM .*?\n', Comment.Single),# or by a whitespace and some text
            (r'--.*?\n', Comment.Single),
            (r'#\n', Comment.Single),
            (r'# .*?\n', Comment.Single),
            (r'/\*', Comment.Multiline, 'multiline-comments'),
            (r'END\s+IF\s*;', Keyword.EndIf),
            (r'END\s+LOOP\s*;', Keyword.EndLoop),
            (r'END\s+REPEAT\s*;', Keyword.EndRepeat),
            (r'END\s+WHILE\s*;', Keyword.EndWhile),
            (r'END\s+WHILE\s*', Keyword.EndWhile),
            (r'END\s+CASE\s*', Keyword.EndCase),
            (r'END\s+CASE\s*;', Keyword.EndCase),
            (r'END\s+(CASE)+', Keyword.EndCase),
            (r'END\s+(CATCH)+', Keyword.EndCatch),
            (r'BEGIN\s+TRAN\s+', Keyword.BeginTransaction),
            (r'BEGIN\s+TRANSACTION\s+', Keyword.BeginTransaction),
            (r'BEGIN\s+TRANSACTION;', Keyword.BeginTransaction),
            (r"`(``|[^`])*`", String.Symbol),

            (r'(ABORT|ABSOLUTE|ADA|AFTER|AGGREGATE|%TYPE|'
             r'ALIAS|ALL|ALTER|ANALYZE|AND|ANY|ARE|AS|'
             r'ASC|ASENSITIVE|ASSERTION|ASYMMETRIC|AT|ATOMIC|'
             r'BACKWARD|BEFORE|BEGIN|BITVAR|'
             r'BIT_LENGTH|BOTH|BREADTH|BY|CACHE|CALLED|CARDINALITY|'
             r'CASCADED|CASE|CATALOG|CATALOG_NAME|CHAIN|'
             r'CHARACTERISTICS|CHARACTER_LENGTH|CHARACTER_SET_CATALOG|'
             r'CHARACTER_SET_NAME|CHARACTER_SET_SCHEMA|CHAR_LENGTH|CHECK|'
             r'CHECKED|CHECKPOINT|CLASS_ORIGIN|CLOB|CLUSTER|'
             r'COBOL|COLLATE|COLLATION|COLLATION_CATALOG|'#COALESCE
             r'COLLATION_NAME|COLLATION_SCHEMA|COLUMN|COLUMN_NAME|'
             r'COMMAND_FUNCTION|COMMAND_FUNCTION_CODE|COMMIT|'
             r'COMMITTED|COMPLETION|CONDITION_NUMBER|CONNECT|CONNECTION|'
             r'CONNECTION_NAME|CONSTRAINT|CONSTRAINTS|CONSTRAINT_CATALOG|'
             r'CONSTRAINT_NAME|CONSTRAINT_SCHEMA|CONSTRUCTOR|'
             r'CONTINUE|CONVERSION|CORRESPONTING|'
             r'CREATEDB|CROSS|CUBE|CURRENT|CURRENT_DATE|'
             r'CURRENT_PATH|CURRENT_ROLE|CURRENT_TIME|CURRENT_TIMESTAMP|'
             r'CURRENT_USER|CURSOR|CURSOR_NAME|CYCLE|DATABASE|'
             r'DATETIME_INTERVAL_CODE|DATETIME_INTERVAL_PRECISION|DAY|'
             r'DEALLOCATE|DECLARE|DEFAULT|DEFAULTS|DEFERRABLE|DEFERRED|'
             r'DEFINER|DELIMITERS|DEREF|DESC|'
             r'DESCRIBE|DESCRIPTOR|DESTROY|DESTRUCTOR|DETERMINISTIC|'
             r'DICTIONARY|DISCONNECT|DISTINCT|'
             r'DROP|DYNAMIC|DYNAMIC_FUNCTION|DYNAMIC_FUNCTION_CODE|'
             r'EACH|ELSE|ENCODING|ENCRYPTED|END|END-EXEC|EQUALS|ESCAPE|EVERY|'
             r'EXCEPT|EXCEPTION|EXCLUDING|EXCLUSIVE|'
             r'EXISTS|EXPLAIN|EXTERNAL|FALSE|FETCH|FOR|'
             r'FORCE|FOREIGN|FORTRAN|FOUND|FREE|FROM|FULL|'
             r'GENERAL|GENERATED|GOTO|GRANT|GRANTED|'
             r'GROUP|HANDLER|HAVING|HIERARCHY|IDENTITY|IF|'
             r'IGNORE|ILIKE|IMMUTABLE|IMPLEMENTATION|IMPLICIT|IN|'
             r'INCLUDING|INCREMENT|INDEX|INDICATOR|INFIX|INHERITS|'
             r'INITIALLY|INNER|INOUT|INPUT|INSENSITIVE|INSERT|INSTANTIABLE|'
             r'INSTEAD|INTERSECT|INTO|INVOKER|IS|ISOLATION|JOIN|'
             r'KEY|KEY_MEMBER|KEY_TYPE|LANCOMPILER|LARGE|LAST|'
             r'LATERAL|LEADING|LEFT|LESS|LIKE|'
             r'LOCAL|LOCALTIME|LOCALTIMESTAMP|LOCK|'
             r'MAXVALUE|MESSAGE_LENGTH|MESSAGE_OCTET_LENGTH|'
             r'MESSAGE_TEXT|MINUTE|MINVALUE|MODE|MODIFIES|'
             r'MODIFY|MONTH|MORE|MUMPS|NATIONAL|NATURAL|'
             r'NCLOB|NEXT|NO|NOCREATEDB|NOCREATEUSER|NONE|NOTHING|'
             r'NOTNULL|NULLABLE|NULLIF|OCTET_LENGTH|OF|OFF|'
             r'OFFSET|OIDS|OLD|ON|ONLY|OPERATOR|OPTION|OPTIONS|'
             r'OR|ORDINALITY|OUTER|OVERLAPS|OVERLAY|OVERRIDING|'
             r'PAD|PARAMETER_MODE|PARAMATER_NAME|'
             r'PARAMATER_ORDINAL_POSITION|PARAMETER_SPECIFIC_CATALOG|'
             r'PARAMETER_SPECIFIC_NAME|PARAMATER_SPECIFIC_SCHEMA|PARTIAL|'
             r'PASCAL|PENDANT|PLACING|PLI|POSITION|POSTFIX|PREFIX|'
             r'PREORDER|PRESERVE|PRIOR|PROCEDURAL|'
             r'PROCEDURE|READS|RECHECK|RECURSIVE|REF|REFERENCES|'
             r'REFERENCING|REINDEX|RELATIVE|RENAME|REPEATABLE|REPLACE|'
             r'RESTRICT|RETURN|RETURNED_LENGTH|'
             r'RETURNED_OCTET_LENGTH|RETURNED_SQLSTATE|RETURNS|REVOKE|RIGHT|'
             r'ROLLUP|ROUTINE|ROUTINE_CATALOG|ROUTINE_NAME|'
             r'ROUTINE_SCHEMA|ROW|ROWS|ROW_COUNT|RULE|SCHEMA|'
             r'SCHEMA_NAME|SCOPE|SCROLL|SECOND|SELECT|SELF|'
             r'SENSITIVE|SERIALIZABLE|SESSION|SESSION_USER|SET|'
             r'SETOF|SETS|SHARE|SIMILAR|SIMPLE|SIZE|SOME|SPACE|'
             r'SPECIFIC|SPECIFICTYPE|SPECIFIC_NAME|SQLCODE|SQLERROR|'
             r'SQLEXCEPTION|SQLSTATE|SQLWARNINIG|STABLE|START|'
             r'STATIC|STATISTICS|STDIN|STDOUT|STORAGE|STRICT|STRUCTURE|STYPE|'
             r'SUBCLASS_ORIGIN|SUBLIST|SYMMETRIC|SYSID|SYSTEM|'
             r'SYSTEM_USER|TABLE_NAME|'
             r'THAN|THEN|TIMEZONE_HOUR|TIMEZONE_MINUTE|TO|TOAST|'
             r'TRAILING|TRANSACTIONS_COMMITTED|'
             r'TRANSACTIONS_ROLLED_BACK|TRANSATION_ACTIVE|'
             r'TRANSFORMS|TRANSLATION|TREAT|TRIGGER|TRIGGER_CATALOG|'
             r'TRIGGER_NAME|TRIGGER_SCHEMA|TRUE|TRUSTED|'
             r'UNCOMMITTED|UNDER|UNENCRYPTED|UNION|UNIQUE|UNKNOWN|UNLISTEN|'
             r'UNNAMED|UNNEST|UNTIL|UPDATE|USAGE|USER|'
             r'USER_DEFINED_TYPE_CATALOG|USER_DEFINED_TYPE_NAME|'
             r'USER_DEFINED_TYPE_SCHEMA|USING|VACUUM|VALID|VALIDATOR|VALUES|'
             r'VERBOSE|VIEW|VOLATILE|WHEN|WHENEVER|WHERE|WHILE|'
             r'WITH|WITHOUT|WORK|YEAR|ZONE)\b', Keyword),
            (r'(ARRAY|BIGINT|BINARY|BIT|BLOB|BOOLEAN|CHAR|CHARACTER|DATE|'
             r'DEC|DECIMAL|FLOAT|INT|INTEGER|INTERVAL|NUMBER|NUMERIC|REAL|'
             r'NCHAR|NVARCHAR|NVARCHAR2|VARBINARY|VARCHAR2|'
             r'SERIAL|SMALLINT|VARCHAR|VARYING|INT8|SERIAL8)\b',
             Name.Builtin),
            (r'[0-9]+', Number.Integer),
            (r'[\w@#$_][\w0-9@#$_]*', Name),
            (r'[;:()\[\],\.]', Punctuation),
            (r'[+*/<>=~!@#%^&|`?-]|(BETWEEN|NOT|IN|EXISTS|LIKE|!=|<>|!>|<!|^=)\b', Operator),# |(BETWEEN|NOT IN|NOT LIKE|EXISTS|IN|LIKE|!=|<>|!>|<!)\b', Operator),# 
        ],
        'multiline-comments': [
            (r'\*/', Comment.Multiline, '#pop'),
            (r'[^/\*]+', Comment.Multiline),
            (r'[/*]', Comment.Multiline)
        ]
    }


class SqlLexer(BaseSqlLexer):
    """
    Lexer for Structured Query Language. 
    
    Accept ansi sql strings only.
    """
    tokens = {
        'root': [
            inherit,
            (r"'(''|[^'])*'", String.Single),
            (r'"(""|[^"])*"', String.Symbol),
        ]
    }

class MSSqlLexer(BaseSqlLexer):
    """
    Lexer for Structured Query Language. 
    
    Accept ansi sql strings only.
    """
    tokens = {
        'root': [
            inherit, 
            (r"'(-)*'", String.Single),
            (r'"', String.Single),
            (r"'""'", String.Single),
            (r'"(""|[^"])*"', String.Symbol),
            (r"[\[](''|""|[^[])*[\]]", String.Symbol)
        ]
    }

class MySqlLexer(BaseSqlLexer):
    """
    Lexer for Structured Query Language.  
    Accepts C-like strings. 
    For example MariaDB/MySQL
    """
    tokens = {
        'root': [
            inherit,
            (r"'(''|\\'|[^'])*'", String.Single),
            (r'"(""|\\"|[^"])*"', String.Symbol),
        ]
    }
