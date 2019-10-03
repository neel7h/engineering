create or replace function  SET_1020000  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026);	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor or HTML5_Javascript_SourceCode
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_HTML5_Function_1020001  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Function*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183);	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_HTML5_Source_Code  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Source_Code*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE = 1020006;	-- CAST_HTML5_SourceCode
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_HTML5_CSS_Source_Code  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_CSS_Source_Code*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020123,1020127);	-- CAST_HTML5_CSS_SourceCode,CAST_HTML5_CSS_SourceCode_Fragment
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_HTML5_Func_WebSocket  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Func_WebSocket*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183)	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020001 and i.InfSubTyp = 0 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function.containsWebSocket
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_HTML5_Func_XMLHttpReq  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Func_XMLHttpReq*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183)	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020001 and i.InfSubTyp = 1 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function.containsXMLHttpRequest
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_HTML5_SrcCode_Http_Ref  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_SrcCode_Http_Ref*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE = 1020006	-- CAST_HTML5_SourceCode
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020001 and i.InfSubTyp = 2 and i.InfVal = 1);  --CAST_HTML5_SourceCode.containsHttpReference
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

CREATE OR REPLACE FUNCTION DIAG_SCOPE_HTML5TECCPLEX001 (
	I_SNAPSHOT_ID INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,			-- the metric id
	I_METRIC_CHILD_ID INT
)
returns int
as
$body$
declare
PARAM_INT INT := 0;
begin
--<<NAME>>DIAG_SCOPE_HTML5TECCPLEX001<</NAME>>
--<<COMMENT>> Template name   = DSSAPPARTIFACTS. <</COMMENT>>
--<<COMMENT>> Diagnostic name = Avoid <Artifacts> with High Cyclomatic Complexity (CC > 20). <</COMMENT>>
--<<COMMENT>> Definition      = Avoid <Artifacts> with High Cyclomatic Complexity (CC > 20). <</COMMENT>>
--<<COMMENT>> Action          = Lists all <Artifacts> with High Cyclomatic Complexity. <</COMMENT>>
--<<COMMENT>> Value           = Cyclomatic Complexity. <</COMMENT>>
	
	SELECT PARAM_NUM_VALUE INTO PARAM_INT
	--INTO PARAM_INT
    FROM
     	DSS_METRIC_PARAM_VALUES MTP
    WHERE
        MTP.METRIC_ID	= I_METRIC_CHILD_ID
        AND PARAM_INDEX	= 1;


	INSERT INTO DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	SELECT 
		DISTINCT T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, SC.MODULE_ID, I_SNAPSHOT_ID, T3.InfVal, 0, 0
	FROM 
    	CTT_OBJECT_APPLICATIONS T1, DSSAPP_MODULES SC, ObjInf T3
    WHERE                    
	    SC.TECHNO_TYPE					= 1020000   			-- Technologic HTML5 object
		AND T1.APPLICATION_ID			= SC.MODULE_ID
		AND T1.OBJECT_TYPE 				IN (1020007, 1020180, 1020183) 	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor
		AND T1.PROPERTIES	= 0 -- Application's Object

		--AND Bitand(T1.PROPERTIES, 1)	= 0 -- Application's Object
				
		-- Look for the artifact that have a CC higher than parameter
		And	T1.OBJECT_ID				= T3.IdObj
		AND T3.InfTyp					= 9
		And T3.InfSubTyp				= 1 --Cyclomatic Complexity
		And T3.InfVal					> PARAM_INT
		
		-- Deal with the Exceptions in the metrics tree
		AND NOT EXISTS
		(
			SELECT 1
			FROM
				DSS_OBJECT_EXCEPTIONS E
			WHERE
				E.METRIC_ID		= I_METRIC_ID
				AND E.OBJECT_ID	= T1.OBJECT_ID
		)
		      			
 
;
return 0;
End;
$body$
language 'plpgsql'
/

/******************************************************************************/
/** FUNCTION DIAG_HTML5_ARTIFACTS_TOTAL         * Total artifacts of HTML5/Javascript  */
/******************************************************************************/

CREATE OR REPLACE FUNCTION DIAG_HTML5_ARTIFACTS_TOTAL (
	I_SNAPSHOT_ID INT,	-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,	-- the metric id
	I_METRIC_VALUE_INDEX INT
)
RETURNS INTEGER
As $BODY$
	DECLARE ERRORCODE INTEGER;
BEGIN 

 ERRORCODE:=0; 
--<<NAME>>DIAG_HTML5_ARTIFACTS_TOTAL<</NAME>>
--<<COMMENT>> Template name   = TOTAL. <</COMMENT>>
--<<COMMENT>> Template use    = Counts object of a given type and application type<</COMMENT>>
--<<COMMENT>> Definition      = For maintenability, files must not contains more than N lines of code details (default is 300) details. <</COMMENT>>
    Insert Into DSS_METRIC_RESULTS (METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    Select
		Count(T1.OBJECT_ID)
		, 0, SC.OBJECT_PARENT_ID, I_METRIC_ID, I_METRIC_VALUE_INDEX, I_SNAPSHOT_ID
    From
    	DSS_METRIC_SCOPES SC, DSSAPP_MODULES MO, CTT_OBJECT_APPLICATIONS T1
    Where
	SC.SNAPSHOT_ID		= I_SNAPSHOT_ID
	And SC.METRIC_PARENT_ID	= I_METRIC_PARENT_ID
	And SC.METRIC_ID		= I_METRIC_ID
	And SC.COMPUTE_VALUE		= 0
	And MO.TECHNO_TYPE		= 1020000  -- Technology HTML5
	And MO.MODULE_ID		= SC.OBJECT_ID
	And T1.APPLICATION_ID		= SC.OBJECT_ID
	And T1.PROPERTIES	= 0 -- Application's Object	
	And T1.OBJECT_TYPE		in (1020007, 1020180, 1020183)	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor
Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID	;
Return ERRORCODE;
end; 
 $BODY$
LANGUAGE 'plpgsql';
/

/******************************************************************************/
/** FUNCTION DIAG_HTML5_FILES_CTOR_TOTAL         * Object from Data Dictionary  */
/******************************************************************************/

CREATE OR REPLACE FUNCTION DIAG_HTML5_FILES_CTOR_TOTAL (
	I_SNAPSHOT_ID INT,	-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,	-- the metric id
	I_METRIC_VALUE_INDEX INT
)
RETURNS INTEGER
As $BODY$
	DECLARE ERRORCODE INTEGER;
BEGIN 

 ERRORCODE:=0; 
--<<NAME>>DIAG_HTML5_FILES_CTOR_TOTAL<</NAME>>
--<<COMMENT>> Template name   = TOTAL. <</COMMENT>>
--<<COMMENT>> Template use    = Counts object of a given type and application type<</COMMENT>>
--<<COMMENT>> Definition      = For maintenability, files must not contains more than N lines of code details (default is 300) details. <</COMMENT>>
    Insert Into DSS_METRIC_RESULTS (METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    Select
		Count(T1.OBJECT_ID)
		, 0, SC.OBJECT_PARENT_ID, I_METRIC_ID, I_METRIC_VALUE_INDEX, I_SNAPSHOT_ID
    From
    	DSS_METRIC_SCOPES SC, DSSAPP_MODULES MO, CTT_OBJECT_APPLICATIONS T1
    Where
	SC.SNAPSHOT_ID		= I_SNAPSHOT_ID
	And SC.METRIC_PARENT_ID	= I_METRIC_PARENT_ID
	And SC.METRIC_ID		= I_METRIC_ID
	And SC.COMPUTE_VALUE		= 0
	And MO.TECHNO_TYPE		= 1020000  -- Technologic HTML5
	And MO.MODULE_ID		= SC.OBJECT_ID
	And T1.APPLICATION_ID		= SC.OBJECT_ID
	And T1.PROPERTIES	= 0 -- Application's Object	
	And T1.OBJECT_TYPE		= 1020026 -- Javascript source code
Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID	;
Return ERRORCODE;
end; 
 $BODY$
LANGUAGE 'plpgsql';
/
/******************************************************************************/
/** FUNCTION DIAG_SCOPE_HTML5DOC002              * Object from Data Dictionary  */
/******************************************************************************/

CREATE OR REPLACE FUNCTION DIAG_SCOPE_HTML5DOC002 (
	I_SNAPSHOT_ID INT,	-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,	-- the metric id
	I_METRIC_CHILD_ID INT
)
RETURNS INTEGER
As $BODY$
	DECLARE ERRORCODE INTEGER;
	PARAM_INT	INT := 0;
BEGIN 

 ERRORCODE:=0; 
--<<NAME>>DIAG_SCOPE_HTML5DOC002<</NAME>>
--<<COMMENT>> Template name   = GENERIC. <</COMMENT>>
--<<COMMENT>> Template use    = Generic case<</COMMENT>>
--<<COMMENT>> Diagnostic name = HTML5:Avoid programs with low comment / code ratio details. <</COMMENT>>
--<<COMMENT>> Definition      = HTML5 programs should be documented. This reports shows all the HTML5 programs with less than 5% comment/code ratio details. <</COMMENT>>
    Select PARAM_NUM_VALUE
	Into PARAM_INT
    From
     	DSS_METRIC_PARAM_VALUES MTP
    Where
        MTP.METRIC_ID	= I_METRIC_CHILD_ID
        And PARAM_INDEX	= 1;

	Insert Into DSS_METRIC_SCOPES
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	Select
		T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, SC.MODULE_ID, I_SNAPSHOT_ID,  ( (T2.METRIC_VALUE + T3.METRIC_VALUE) / (CASE WHEN  coalesce(T4.METRIC_VALUE,0) = 0 THEN  1 ELSE T4.METRIC_VALUE END) ), 0, 0
    From
    	DIAG_OBJECT_METRICS T2, DIAG_OBJECT_METRICS T3, DIAG_OBJECT_METRICS T4, CTT_OBJECT_APPLICATIONS T1, DSSAPP_MODULES SC
	Where
		SC.TECHNO_TYPE					= 1020000  -- Technologic HTML5
		And T1.APPLICATION_ID			= SC.MODULE_ID
	And T1.OBJECT_TYPE = 1020026 -- Javascript source code
	And T1.PROPERTIES	= 0
		And Not Exists
		(
			Select 1
			From
				DSS_OBJECT_EXCEPTIONS E
			Where
				E.METRIC_ID		= I_METRIC_ID
				And E.OBJECT_ID	= T1.OBJECT_ID
		)
		/*And Exists
		(
			Select 1
			From
				CDT_OBJECTS TN
			Where
				TN.OBJECT_ID		= T1.OBJECT_ID
				And Upper(TN.OBJECT_NAME) Like '%C'
		)*/
        And T2.OBJECT_ID 				= T1.OBJECT_ID
        And T2.METRIC_TYPE 				= 'Number of heading comment lines'
        And T3.OBJECT_ID 				= T1.OBJECT_ID
        And T3.METRIC_TYPE 				= 'Number of inner comment lines'
        And T4.OBJECT_ID 				= T1.OBJECT_ID
        And T4.METRIC_TYPE 				= 'Number of code lines'
        And T4.METRIC_VALUE				> 0
        And (100::INT8*(T2.METRIC_VALUE + T3.METRIC_VALUE) / (CASE WHEN  coalesce(T4.METRIC_VALUE,0) = 0 THEN  1 ELSE T4.METRIC_VALUE END) )< (PARAM_INT)
 	;
Return ERRORCODE;
end; 
 $BODY$
LANGUAGE 'plpgsql';
/

create or replace function  SET_HTML5_Class_1020001  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Class*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE = 1020179;	-- HTML5_Javascript_Class
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

CREATE OR REPLACE FUNCTION DIAG_MANY_HTML5PARAMS (
	I_SNAPSHOT_ID INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,			-- the metric id
	I_METRIC_CHILD_ID INT
)
returns int
as
$body$
declare
PARAM_INT INT := 0;
begin
--<<NAME>>DIAG_MANY_HTML5PARAMS<</NAME>>
--<<COMMENT>> Template name   = DSSAPPARTIFACTS. <</COMMENT>>
--<<COMMENT>> Diagnostic name = Avoid Artifacts with too many parameters (Javascript). <</COMMENT>>
--<<COMMENT>> Definition      = Avoid Artifacts with too many parameters (Javascript). <</COMMENT>>
--<<COMMENT>> Action          = Lists all <Artifacts> with High Number of parameters. <</COMMENT>>
--<<COMMENT>> Value           = NA <</COMMENT>>
	
	SELECT PARAM_NUM_VALUE INTO PARAM_INT
	--INTO PARAM_INT
    FROM
     	DSS_METRIC_PARAM_VALUES MTP
    WHERE
        MTP.METRIC_ID	= I_METRIC_CHILD_ID
        AND PARAM_INDEX	= 1;


	INSERT INTO DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	SELECT 
		DISTINCT T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, SC.MODULE_ID, I_SNAPSHOT_ID, T3.InfVal, 0, 0
	FROM 
    	CTT_OBJECT_APPLICATIONS T1, DSSAPP_MODULES SC, ObjInf T3
    WHERE                    
	    SC.TECHNO_TYPE					= 1020000   			-- Technologic HTML5 object
		AND T1.APPLICATION_ID			= SC.MODULE_ID
		AND T1.OBJECT_TYPE 				IN (1020007, 1020180, 1020183) 	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor
		AND T1.PROPERTIES	= 0 -- Application's Object

		--AND Bitand(T1.PROPERTIES, 1)	= 0 -- Application's Object
				
		-- Look for the artifact that have a CC higher than parameter
		And	T1.OBJECT_ID				= T3.IdObj
		AND T3.InfTyp					= 1020051
		And T3.InfSubTyp				= 23 --Number of parameters
		And T3.InfVal					> PARAM_INT
		
		-- Deal with the Exceptions in the metrics tree
		AND NOT EXISTS
		(
			SELECT 1
			FROM
				DSS_OBJECT_EXCEPTIONS E
			WHERE
				E.METRIC_ID		= I_METRIC_ID
				AND E.OBJECT_ID	= T1.OBJECT_ID
		)
		      			
 
;
return 0;
End;
$body$
language 'plpgsql'
/

/******************************************************************************/
/** FUNCTION DIAG_HTML5_FUNC_METH_TOTAL         * Object from Data Dictionary  */
/******************************************************************************/

CREATE OR REPLACE FUNCTION DIAG_HTML5_FUNC_METH_TOTAL (
	I_SNAPSHOT_ID INT,	-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,	-- the metric id
	I_METRIC_VALUE_INDEX INT
)
RETURNS INTEGER
As $BODY$
	DECLARE ERRORCODE INTEGER;
BEGIN 

 ERRORCODE:=0; 
--<<NAME>>DIAG_HTML5_FUNC_METH_TOTAL<</NAME>>
--<<COMMENT>> Template name   = TOTAL. <</COMMENT>>
--<<COMMENT>> Template use    = Counts object of a given type and application type<</COMMENT>>
--<<COMMENT>> Definition      = For maintenability, files must not contains more than N lines of code details (default is 300) details. <</COMMENT>>
    Insert Into DSS_METRIC_RESULTS (METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    Select
		Count(T1.OBJECT_ID)
		, 0, SC.OBJECT_PARENT_ID, I_METRIC_ID, I_METRIC_VALUE_INDEX, I_SNAPSHOT_ID
    From
    	DSS_METRIC_SCOPES SC, DSSAPP_MODULES MO, CTT_OBJECT_APPLICATIONS T1
    Where
	SC.SNAPSHOT_ID		= I_SNAPSHOT_ID
	And SC.METRIC_PARENT_ID	= I_METRIC_PARENT_ID
	And SC.METRIC_ID		= I_METRIC_ID
	And SC.COMPUTE_VALUE		= 0
	And MO.TECHNO_TYPE		= 1020000  -- Technologic HTML5
	And MO.MODULE_ID		= SC.OBJECT_ID
	And T1.APPLICATION_ID		= SC.OBJECT_ID
	And T1.PROPERTIES	= 0 -- Application's Object	
	And T1.OBJECT_TYPE		in (1020007, 1020180, 1020183) -- Javascript function, methods and constructors
Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID	;
Return ERRORCODE;
end; 
 $BODY$
LANGUAGE 'plpgsql';
/

CREATE OR REPLACE FUNCTION DIA_MANY_UNDOCFUNCTION_HTML5 (
	I_SNAPSHOT_ID INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,			-- the metric id
	I_METRIC_CHILD_ID INT
)
returns int as
$body$
declare
	ERRORCODE	INT := 0;
	L_PARAM_NUM	INT := 0;
Begin
--<<NAME>>DIA_MANY_UNDOCFUNCTION<</NAME>>
--<<COMMENT>> Template name   = DSSGENERIC. <</COMMENT>>
--<<COMMENT>> Diagnostic name = Avoid undocumented functions. <</COMMENT>>
--<<COMMENT>> Definition      = functions should be documented. This reports shows all the undocumented.. <</COMMENT>>
--<<COMMENT>> Action          = Find all undocumented functions. <</COMMENT>>
--<<COMMENT>> Value           = . <</COMMENT>>
   
	
     
	
	insert into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	Select 
		 T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, T1.APPLICATION_ID, I_SNAPSHOT_ID, 1, Null, 0, 0
	From 
		DSSAPP_ARTIFACTS T1
	Where 
		 Not Exists 
		(
			Select 1 
			From 
				DSS_OBJECT_EXCEPTIONS E
			Where 
				E.METRIC_ID		= I_METRIC_ID 
				And E.OBJECT_ID	= T1.OBJECT_ID
		)
		
and T1.TECHNO_TYPE  
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = I_METRIC_ID 
						) 
and T1.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 10052	) -- APM Inventory Functions
and T1.CODE_LINES > 0 
and T1.COMMENT_LINES = 0

and Not Exists
	(
		Select 1 from ObjInf T3 where T1.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --Anonymous
	)
	;
	
	  
	 
Return ERRORCODE;
END;
$body$
language plpgsql
/

CREATE OR REPLACE FUNCTION DIT_MANY_FUNCTIONS_HTML5 (
	I_SNAPSHOT_ID          INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID     INT,	    -- the metric parent id
	I_METRIC_ID            INT,		-- the metric id
	I_METRIC_VALUE_INDEX   INT
)
returns int
as
$body$
declare
	ERRORCODE	int;
Begin
--<<NAME>>DIT_MANY_FUNCTIONS<</NAME>>*/
--<<COMMENT>> Template name   = TOTALARTIFACTS. <</COMMENT>>
--<<COMMENT>> Definition      = Count of Inventory Functions. <</COMMENT>>

    ERRORCODE  := 0;
    
    Insert Into DSS_METRIC_RESULTS
		(METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    select 
		Count(T1.OBJECT_ID), 0, SC.OBJECT_PARENT_ID, I_METRIC_ID, I_METRIC_VALUE_INDEX, I_SNAPSHOT_ID 
    from 
    	DSSAPP_ARTIFACTS T1, DSS_METRIC_SCOPES SC
    where                    
	    SC.SNAPSHOT_ID             	= I_SNAPSHOT_ID
	    and SC.METRIC_PARENT_ID    	= I_METRIC_PARENT_ID
	    and SC.METRIC_ID           	= I_METRIC_ID
 		and SC.COMPUTE_VALUE		= 0
		and T1.TECHNO_TYPE			 
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = I_METRIC_ID 
						) 
		and T1.APPLICATION_ID		= SC.OBJECT_ID
		and Not Exists 
		(
			select 1 
			from 
				DSS_OBJECT_EXCEPTIONS E
			where 
				E.METRIC_ID		= I_METRIC_ID 
				and E.OBJECT_ID	= T1.OBJECT_ID 
		)
		
     and T1.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 10052	) -- APM Inventory Functions
	and Not Exists
	(
		Select 1 from ObjInf T3 where T1.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --Anonymous
	)

    Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID
	; 
Return ERRORCODE;
end;
$body$
language 'plpgsql'
/

CREATE OR REPLACE FUNCTION DIT_MANY_ALLFUNCTIONS_HTML5 (
	I_SNAPSHOT_ID          INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID     INT,	    -- the metric parent id
	I_METRIC_ID            INT,		-- the metric id
	I_METRIC_VALUE_INDEX   INT
)
returns int
as
$body$
declare
	ERRORCODE	int;
Begin
--<<NAME>>DIT_MANY_ALLFUNCTIONS<</NAME>>*/
--<<COMMENT>> Template name   = TOTALARTIFACTS. <</COMMENT>>
--<<COMMENT>> Definition      = Count of Inventory Functions and SQL functions. <</COMMENT>>

    ERRORCODE  := 0;
    
    Insert Into DSS_METRIC_RESULTS
		(METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    select 
		Count(T1.OBJECT_ID), 0, SC.OBJECT_PARENT_ID, I_METRIC_ID, I_METRIC_VALUE_INDEX, I_SNAPSHOT_ID 
    from 
    	DSSAPP_ARTIFACTS T1, DSS_METRIC_SCOPES SC
    where                    
	    SC.SNAPSHOT_ID             	= I_SNAPSHOT_ID
	    and SC.METRIC_PARENT_ID    	= I_METRIC_PARENT_ID
	    and SC.METRIC_ID           	= I_METRIC_ID
 		and SC.COMPUTE_VALUE		= 0
		and T1.TECHNO_TYPE			 
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = I_METRIC_ID 
						) 
		and T1.APPLICATION_ID		= SC.OBJECT_ID
		and Not Exists 
		(
			select 1 
			from 
				DSS_OBJECT_EXCEPTIONS E
			where 
				E.METRIC_ID		= I_METRIC_ID 
				and E.OBJECT_ID	= T1.OBJECT_ID 
		)
		
     and T1.OBJECT_TYPE = 1020007 -- CAST_HTML5_JavaScript_Function

    Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID
	; 
Return ERRORCODE;
end;
$body$
language 'plpgsql'
/
CREATE OR REPLACE FUNCTION DIA_MANY_UNREFFUNCTION_HTML5 (
  I_SNAPSHOT_ID INT,    -- the metric snapshot id
  I_METRIC_PARENT_ID INT, -- the metric parent id
  I_METRIC_ID INT,      -- the metric id
  I_METRIC_CHILD_ID INT
)
returns int as
$body$
declare
  ERRORCODE INT := 0;
Begin
--<<NAME>>DIA_OTHER_UNREFFUNCTION<</NAME>>
--<<COMMENT>> Template name   = DSSGENERIC. <</COMMENT>>
--<<COMMENT>> Diagnostic name = Avoid unreferenced functions. <</COMMENT>>
--<<COMMENT>> Definition      = Unreferenced functions make the code less readable and maintainable. <</COMMENT>>
--<<COMMENT>> Action          = Avoid unreferenced functions. <</COMMENT>>
--<<COMMENT>> Value           = . <</COMMENT>>
   
  insert into DSS_METRIC_SCOPES 
    (OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
  Select 
     da.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, da.APPLICATION_ID, I_SNAPSHOT_ID, 0, Null, 0, 0
  From 
    DSSAPP_ARTIFACTS da 
  Where 
     Not Exists 
    (
      Select 1 
      From 
        DSS_OBJECT_EXCEPTIONS E
      Where 
        E.METRIC_ID   = I_METRIC_ID 
        And E.OBJECT_ID = da.OBJECT_ID
    )
    
and da.TECHNO_TYPE  
           in ( select MTP.OBJECT_TYPE_ID
              from DSS_METRIC_PARAM_TYPES MTP
             where MTP.METRIC_ID = I_METRIC_ID 
            ) 
and da.OBJECT_TYPE  = 1020007  -- CAST_HTML5_JavaScript_Function
	and Exists
	(
		Select 1 from ObjInf T3 where da.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 28 --unreferencedFunctionEnabled
	)
	and not Exists
	(
		Select 1 from Acc where IdCle = da.OBJECT_ID
	)
  ;
   
Return ERRORCODE;
END;
$body$
language plpgsql
/
CREATE OR REPLACE FUNCTION DIA_MANY_LOWDOCFUNCTION_HTML5 (
	I_SNAPSHOT_ID INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,			-- the metric id
	I_METRIC_CHILD_ID INT
)
returns INT
as
$body$
declare
	   ERRORCODE	INT:=0;
 
Begin
 
ERRORCODE:=0;
--<<NAME>>DIA_MANY_LOWDOCFUNCTION<</NAME>>*/
--<<COMMENT>> Template name   = UNDOCUMENTEDRATIOARTIFACT. <</COMMENT>>
--<<COMMENT>> Diagnostic name = Avoid functions with low comment / code ratio. <</COMMENT>>
--<<COMMENT>> Definition      = functions should be documented. This reports shows all the  functions with less than 5% comment/code ratio.. <</COMMENT>>
--<<COMMENT>> Action          = Find all functions  that have a very low Comment/Code ratio. <</COMMENT>>
--<<COMMENT>> Value           = Comment ratio. <</COMMENT>>
	
    


 truncate table  TMP_DIA_PAR;
 
 insert into TMP_DIA_PAR
      ( TECHNO_TYPE, PARAM_NUM_VALUE )
 select  MTP.OBJECT_TYPE_ID ,max(PARAM_NUM_VALUE)
   from DSSAPP_METRIC_PARAM_VALUES MTP  
  where MTP.METRIC_ID   = I_METRIC_CHILD_ID
    and MTP.PARAM_INDEX = 1
group by MTP.OBJECT_TYPE_ID 		
;




	
 	insert into DSS_METRIC_SCOPES 
		   (OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	select T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, T1.APPLICATION_ID, I_SNAPSHOT_ID, 
	       ( ( cast ( T1.COMMENT_LINES as FLOAT ) ) / T1.CODE_LINES ), 0, 0
      from   DSSAPP_ARTIFACTS T1
	 where T1.TECHNO_TYPE		 
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = I_METRIC_ID 
						) 
	   and not exists (	select 1 
			              from DSS_OBJECT_EXCEPTIONS E
			             where E.METRIC_ID		= I_METRIC_ID 
				           and E.OBJECT_ID	= T1.OBJECT_ID 
		              )
       and T1.CODE_LINES        > 0
	   
     and T1.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 10052	) -- APM Inventory Functions
	and Not Exists
	(
		Select 1 from ObjInf T3 where T1.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --Anonymous
	)

	   and 100 * ( cast ( T1.COMMENT_LINES as FLOAT )     / T1.CODE_LINES ) < 
                           (  select PARAM_NUM_VALUE
                             from TMP_DIA_PAR MTP  
							where MTP.TECHNO_TYPE  = T1.TECHNO_TYPE
                         )
 
 	  ;    
	  
Return ERRORCODE;
End;
$body$
language 'plpgsql'
/
CREATE OR REPLACE FUNCTION DIA_MANY_TECCPLEX005_HTML5 (
	I_SNAPSHOT_ID INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,			-- the metric id
	I_METRIC_CHILD_ID INT
)
returns int as
$body$
declare
	ERRORCODE	INT := 0;
	L_PARAM_NUM	INT := 0;
Begin
--<<NAME>>DIA_MANY_TECCPLEX005<</NAME>>
--<<COMMENT>> Template name   = DSSGENERIC. <</COMMENT>>
--<<COMMENT>> Diagnostic name = Avoid <Artifacts> with long lines. <</COMMENT>>
--<<COMMENT>> Definition      = Avoid <Artifacts> with long lines. <</COMMENT>>
--<<COMMENT>> Action          = Lists all <Artifacts> with long lines. <</COMMENT>>
--<<COMMENT>> Value           = Number of long lines ( the max length is a param). <</COMMENT>>
   
	
    


 truncate table  TMP_DIA_PAR;
 
 insert into TMP_DIA_PAR
      ( TECHNO_TYPE, PARAM_NUM_VALUE )
 select  MTP.OBJECT_TYPE_ID ,max(PARAM_NUM_VALUE)
   from DSSAPP_METRIC_PARAM_VALUES MTP  
  where MTP.METRIC_ID   = I_METRIC_CHILD_ID
    and MTP.PARAM_INDEX = 1
group by MTP.OBJECT_TYPE_ID 		
;




	
	insert into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	Select 
		 T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, T1.APPLICATION_ID, I_SNAPSHOT_ID, T1.LONG_LINES, Null, 0, 0
	From 
		DSSAPP_ARTIFACTS T1   
	Where 
		 Not Exists 
		(
			Select 1 
			From 
				DSS_OBJECT_EXCEPTIONS E
			Where 
				E.METRIC_ID		= I_METRIC_ID 
				And E.OBJECT_ID	= T1.OBJECT_ID
		)
		
    and T1.TECHNO_TYPE  
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = I_METRIC_ID 
						) 
     and T1.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 10052	) -- APM Inventory Functions
	and Not Exists
	(
		Select 1 from ObjInf T3 where T1.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --Anonymous
	)
 	and T1.LONG_LINES > (  select PARAM_NUM_VALUE
                             from TMP_DIA_PAR MTP  
	                        where MTP.TECHNO_TYPE  =  T1.TECHNO_TYPE
                         ) 
		
	;
	
	  
	 
Return ERRORCODE;
END;
$body$
language plpgsql
/
CREATE OR REPLACE FUNCTION DIA_MANY_TECCPLEX003_HTML5 (
	I_SNAPSHOT_ID INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,			-- the metric id
	I_METRIC_CHILD_ID INT
)
returns int as
$body$
declare
	ERRORCODE	INT := 0;
	L_PARAM_NUM	INT := 0;
Begin
--<<NAME>>DIA_MANY_TECCPLEX003<</NAME>>
--<<COMMENT>> Template name   = DSSGENERIC. <</COMMENT>>
--<<COMMENT>> Diagnostic name = Avoid <Artifacts> with High Depth of Code (DoC > 5). <</COMMENT>>
--<<COMMENT>> Definition      = Avoid <Artifacts> with High Depth of Code (DoC > 5). <</COMMENT>>
--<<COMMENT>> Action          = Lists all <Artifacts> with High Depth of Code. <</COMMENT>>
--<<COMMENT>> Value           = Depth of Code. <</COMMENT>>
   
	
    


 truncate table  TMP_DIA_PAR;
 
 insert into TMP_DIA_PAR
      ( TECHNO_TYPE, PARAM_NUM_VALUE )
 select  MTP.OBJECT_TYPE_ID ,max(PARAM_NUM_VALUE)
   from DSSAPP_METRIC_PARAM_VALUES MTP  
  where MTP.METRIC_ID   = I_METRIC_CHILD_ID
    and MTP.PARAM_INDEX = 1
group by MTP.OBJECT_TYPE_ID 		
;




	
	insert into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	Select 
		 T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, T1.APPLICATION_ID, I_SNAPSHOT_ID, T1.CODE_DEPTH, Null, 0, 0
	From 
		DSSAPP_ARTIFACTS T1   
	Where 
		 Not Exists 
		(
			Select 1 
			From 
				DSS_OBJECT_EXCEPTIONS E
			Where 
				E.METRIC_ID		= I_METRIC_ID 
				And E.OBJECT_ID	= T1.OBJECT_ID
		)
		
    and T1.TECHNO_TYPE  
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = I_METRIC_ID 
						) 
     and T1.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 10052	) -- APM Inventory Functions
	and Not Exists
	(
		Select 1 from ObjInf T3 where T1.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --Anonymous
	)
 	and T1.CODE_DEPTH > (  select PARAM_NUM_VALUE
                            from TMP_DIA_PAR MTP  
	                       where MTP.TECHNO_TYPE  = T1.TECHNO_TYPE
                         )

		
	;
	
	  
	 
Return ERRORCODE;
END;
$body$
language plpgsql
/
CREATE OR REPLACE FUNCTION DIA_MANY_FUNC_IN_HTML_HTML5 (
  I_SNAPSHOT_ID INT,    -- the metric snapshot id
  I_METRIC_PARENT_ID INT, -- the metric parent id
  I_METRIC_ID INT,      -- the metric id
  I_METRIC_CHILD_ID INT
)
returns int as
$body$
declare
  ERRORCODE INT := 0;
Begin
--<<NAME>>DIA_MANY_FUNC_IN_HTML_HTML5<</NAME>>
   

  insert into DSS_METRIC_SCOPES 
    (OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
  Select 
     da.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, da.APPLICATION_ID, I_SNAPSHOT_ID, 0, Null, 0, 0
  From 
    DSSAPP_ARTIFACTS da
    	join DIAG_OBJECT_PARENTS pa on da.OBJECT_ID = pa.OBJECT_ID
  Where 
     Not Exists 
    (
      Select 1 
      From 
        DSS_OBJECT_EXCEPTIONS E
      Where 
        E.METRIC_ID   = I_METRIC_ID 
        And E.OBJECT_ID = da.OBJECT_ID
    )
    
and da.TECHNO_TYPE  
           in ( select MTP.OBJECT_TYPE_ID
              from DSS_METRIC_PARAM_TYPES MTP
             where MTP.METRIC_ID = I_METRIC_ID 
            ) 
and da.OBJECT_TYPE in ( 1020007 )  -- CAST_HTML5_JavaScript_Function
	and Not Exists
	(
		Select 1 from ObjInf T3 where da.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --anonymous
	)
and pa.PARENT_TYPE in ( 1020030 ) -- CAST_HTML5_JavaScript_SourceCode_Fragment
  ;
   
Return ERRORCODE;
END;
$body$
language plpgsql
/

create or replace function  SET_HTML5_Func_Cookie  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Func_Cookie*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor, HTML5_Javascript_SourceCode
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020052 and i.InfSubTyp = 30 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsCookieCall
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_HTML5_Func_SetTimeout  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Func_SetTimeout*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor, HTML5_Javascript_SourceCode
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020052 and i.InfSubTyp = 32 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsSetTimeout
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_HTML5_Document_Cookie  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Document_Cookie*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor, HTML5_Javascript_SourceCode
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020052 and i.InfSubTyp = 34 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsCookieCall
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_HTML5_JSONParseStringify  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_HTML5_Javascript_Function_with_JSONParseStringify*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)	-- HTML5_Javascript_Function, HTML5_Javascript_Method, HTML5_Javascript_Constructor, HTML5_Javascript_SourceCode
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020101 and i.InfSubTyp = 5 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsJSONParseOrStringify
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
