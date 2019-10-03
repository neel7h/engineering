CREATE OR REPLACE FUNCTION DIAG_SCOPE_NETNAM011 (
	I_SNAPSHOT_ID INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,			-- the metric id
	I_METRIC_CHILD_ID INT
)
returns int as
$body$
declare
	ERRORCODE	INT := 0;
Begin
--<<NAME>>DIAG_SCOPE_NETNAM011<</NAME>>*/
--<<COMMENT>> Template name   = NAMINGGENERICWITHOUTOBJTYPE. <</COMMENT>>
--<<COMMENT>> Diagnostic name = .Net: Avoid using Keywords as Names. <</COMMENT>>
--<<COMMENT>> Definition      = Keywords should not be used as names. <</COMMENT>>
--<<COMMENT>> Action          = List all non system objects with one of the following names 'ADDHANDLER'.... <</COMMENT>>
--<<COMMENT>> Value           = 1. <</COMMENT>>
--138383 = C#
--138385 = VB.NET
--check for C#
	Insert Into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	select 
		T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, SC.MODULE_ID, I_SNAPSHOT_ID, 1, 0, 0
	from 
    	CDT_OBJECTS TN, CTT_OBJECT_APPLICATIONS T1, DSSAPP_MODULES SC
    where                    
	    SC.TECHNO_TYPE				= 138383  
		and T1.APPLICATION_ID		= SC.MODULE_ID

		and T1.PROPERTIES = 0 -- Application's Object
        and T1.OBJECT_ID 			= TN.OBJECT_ID
		and Not Exists 
		(
			select 1 
			from 
				DSS_OBJECT_EXCEPTIONS E
			where 
				E.METRIC_ID		= I_METRIC_ID 
				and E.OBJECT_ID	= T1.OBJECT_ID 
		)
		And TN.OBJECT_LANGUAGE_NAME = 'C#'
		and T1.OBJECT_TYPE			In       (Select IdTyp From TypCat Where IdCatParent  = 138102) /*CAST_DotNet_DotNet*/
        and T1.OBJECT_TYPE not in (137069, 137070)  /*'C# Property Set', 'C# Property Get'*/

And (TN.OBJECT_MANGLING || TN.OBJECT_TYPE_STR) != 'FINALIZE ()DESTRUCTOR'

And (TN.OBJECT_NAME) IN ('abstract',
'as',
'base',
'bool',
'break',
'byte',
'case',
'catch',	
'char',
'checked',
'class',
'const',	
'continue',
'decimal',
'default',
'delegate',	
'do',
'double',
'else',
'enum',	
'event',
'explicit',
'extern',
'false',	
'finally',
'fixed',
'float',
'for',
'foreach',
'goto',
'if',
'implicit',
'in',
'int',
'interface',
'internal',
'is',
'lock',
'long',
'namespace',
'new',
'null',
'object',
'operator',
'out',
'override',
'params',
'private',
'protected',
'public',
'readonly',
'ref',
'return',
'sbyte',
'sealed',
'short',	
'sizeof',
'stackalloc',
'static',
'string',	
'struct',
'switch',
'this',
'throw',	
'true',
'try',
'typeof',
'uint',
'ulong',
'unchecked',
'unsafe',
'ushort',
'using',
'static',
'virtual',
'void',
'volatile',
'while',
'add',
'alias',
'ascending',
'async',
'await',
'by',
'descending',
'dynamic',
'equals',
'from',
'get',
'global',
'group',
'into',
'join',
'let',
'nameof',
'on',
'orderby',
'partial',
'remove',
'select',
'set',
'value',
'var',
'when',
'where',
'yield'

); 
--End C# check

--VB.NET check
Insert Into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	select 
		T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, SC.MODULE_ID, I_SNAPSHOT_ID, 1, 0, 0
	from 
    	CDT_OBJECTS TN, CTT_OBJECT_APPLICATIONS T1, DSSAPP_MODULES SC
    where                    
	    SC.TECHNO_TYPE				= 138385  
		and T1.APPLICATION_ID		= SC.MODULE_ID

		and T1.PROPERTIES = 0 -- Application's Object
        and T1.OBJECT_ID 			= TN.OBJECT_ID
		and Not Exists 
		(
			select 1 
			from 
				DSS_OBJECT_EXCEPTIONS E
			where 
				E.METRIC_ID		= I_METRIC_ID 
				and E.OBJECT_ID	= T1.OBJECT_ID 
		)
		And TN.OBJECT_LANGUAGE_NAME = 'VB.NET'

And Upper(TN.OBJECT_MANGLING || TN.OBJECT_TYPE_STR) != 'FINALIZE ()DESTRUCTOR'

And Upper(TN.OBJECT_NAME) IN ('ADDHANDLER',
'ADDRESSOF',
'ALIAS',
'AND',
'ALSO',
'AS',
'BOOLEAN',
'BYREF',
'BYTE',
'BYVAL',
'CALL',
'CASE',
'CATCH',
'CBOOL',
'CBYTE',
'CCHAR',
'CDATE',
'CDBL',
'CDEC',
'CHAR',
'CINT',
'CLASS',
'CONSTRAINT',
'CLASS',
'STATEMENT',
'CLNG',
'COBJ',
'CONST',
'CONTINUE',
'CSBYTE',
'CSHORT',
'CSNG',
'CSTR',
'CTYPE',
'CUINT',
'CULNG',
'CUSHORT',
'DATE',
'DECIMAL',
'DECLARE',
'DEFAULT',
'DELEGATE',
'DIM',
'DIRECTCAST',
'DO',
'DOUBLE',
'EACH',
'ELSE',
'ELSEIF',
'END',
'ENDIF',
'ENUM',
'ERASE',
'ERROR',
'EVENT',
'EXIT',
'FALSE',
'FINALLY',
'FOR',
'EACH',
'NEXT',
'FRIEND'
'FUNCTION',
'GET',
'GETTYPE',
'GETXMLNAMESPACE',
'GLOBAL',
'GOSUB',
'GOTO',
'HANDLES',
'IF',
'IF()',
'IMPLEMENTS',
'STATEMENT',
'IMPORTS',
'INHERITS',
'INTEGER',
'INTERFACE',
'IS',
'ISNOT',
'LET',
'LIB',
'LIKE',
'LONG',
'LOOP',
'ME',
'MOD',
'MODULE',
'STATEMENT',
'MUSTINHERIT',
'MUSTOVERRIDE',
'MYBASE',
'MYCLASS',
'NAMESPACE',
'NARROWING',
'NEW CONSTRAINT',
'NEW OPERATOR',
'NEXT',
'NOT',
'NOTHING',
'NOTINHERITABLE',
'NOTOVERRIDABLE',
'OBJECT',
'OPTION',
'OPTIONAL',
'OR',
'ORELSE',
'OUT', 
'OVERLOADS',
'OVERRIDABLE',
'OVERRIDES',
'PARAMARRAY',
'PARTIAL',
'PRIVATE',
'PROPERTY',
'PROTECTED',
'PUBLIC',
'RAISEEVENT',
'READONLY',
'REDIM',
'REM',
'REMOVEHANDLER',
'RESUME',
'RETURN',
'SBYTE',
'SELECT',
'SET',
'SHADOWS',
'SHARED',
'SHORT',
'SINGLE',
'STATIC',
'STEP',
'STOP',
'STRING',
'STRUCTURE',
'CONSTRAINT',
'STRUCTURE',
'STATEMENT',
'SUB',
'SYNCLOCK',
'THEN',
'THROW',
'TO',
'TRUE',
'TRY',
'TRYCAST',
'TYPEOF',
'UINTEGER',
'ULONG',
'USHORT',
'USING',
'VARIANT',
'WEND',
'WHEN',
'WHILE',
'WIDENING',
'WITH',
'WITHEVENTS',
'WRITEONLY',
'XOR',
'#CONST',
'#ELSE',
'#ELSEIF',
'#END',
'#IF',
'AGGREGATE',
'ANSI',
'ASSEMBLY',
'ASYNC',
'AUTO',
'AWAIT',
'BINARY',
'COMPARE'
'CUSTOM',
'DISTINCT',
'EQUALS',
'EXPLICIT',
'FROM',
'BY',
'GROUP',
'JOININTO',
'ISFALSE',
'ISTRUE',
'ITERATOR',
'JOIN',
'KEY',
'MID',
'OFF',
'ORDER',
'PRESERVE',
'SKIP',
'WHILE',
'STRICT',
'TAKE',
'WHILE',
'TEXT',
'UNICODE',
'UNTIL',
'WHERE',
'YIELD',
'#EXTERNALSOURCE',
'#REGION'); 

--END VB.NET Check
Return ERRORCODE;
END;

$body$
language plpgsql
/
CREATE OR REPLACE FUNCTION DIAG_DOTNET_ANA_OBJECTS_TOTAL_NO_PROPERTIES (
	I_SNAPSHOT_ID          INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID     INT,	-- the metric parent id
	I_METRIC_ID            INT,			-- the metric id
	I_METRIC_VALUE_INDEX   INT
)
returns int
as
$body$
declare
	ERRORCODE	int;
Begin
    ERRORCODE  := 0;
--<<NAME>>DIAG_DOTNET_ANA_OBJECTS_TOTAL_NO_PROPERTIES<</NAME>>*/
--<<COMMENT>> Template name   = TOTAL. <</COMMENT>>
--<<COMMENT>> Definition      = Count of .Net objects. other than C# Property Get and Set <</COMMENT>>

    Insert Into DSS_METRIC_RESULTS
		(METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    select 
		Count(T1.OBJECT_ID), 0, SC.OBJECT_PARENT_ID, I_METRIC_ID, I_METRIC_VALUE_INDEX, I_SNAPSHOT_ID 
    from 
    	CTT_OBJECT_APPLICATIONS T1, DSSAPP_MODULES MO, DSS_METRIC_SCOPES SC
    where                    
	    SC.SNAPSHOT_ID             	= I_SNAPSHOT_ID
	    and SC.METRIC_PARENT_ID    	= I_METRIC_PARENT_ID
	    and SC.METRIC_ID           	= I_METRIC_ID
 		and SC.COMPUTE_VALUE		= 0
		and MO.TECHNO_TYPE			in (138383,138385,141901)  
		and MO.MODULE_ID			= SC.OBJECT_ID
  		and T1.APPLICATION_ID      	= SC.OBJECT_ID
		and T1.OBJECT_TYPE			In       (Select IdTyp From TypCat Where IdCatParent  = 138102) /*'CAST_DotNet_DotNet'*/
		and T1.OBJECT_TYPE not in (137069, 137070)  /*'C# Property Set', 'C# Property Get'*/
		and T1.PROPERTIES = 0 -- Application's Object
        and T1.OBJECT_TYPE not in (137069, 137070)  /*'C# Property Set', 'C# Property Get'*/
		
		and Not Exists 
		(
			select 1 
			from 
				DSS_OBJECT_EXCEPTIONS E
			where 
				E.METRIC_ID		= I_METRIC_ID 
				and E.OBJECT_ID	= T1.OBJECT_ID 
		)
    Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID
	; 
Return ERRORCODE;
End;
$body$
language 'plpgsql'
