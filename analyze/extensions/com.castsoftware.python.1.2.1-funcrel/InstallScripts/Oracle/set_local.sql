
CREATE OR REPLACE FUNCTION DIAG_SCOPE_PYTHONTECCPLEX001 (
	I_SNAPSHOT_ID IN INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID IN INT,	-- the metric parent id
	I_METRIC_ID IN INT,			-- the metric id
	I_METRIC_CHILD_ID IN INT
)
Return INT
Is
	PARAM_INT	INT := 0;
Begin
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
	    SC.TECHNO_TYPE					= 1021000   			-- Technologic Python object
		AND T1.APPLICATION_ID			= SC.MODULE_ID
		AND T1.OBJECT_TYPE 				IN (1021008) 	-- CAST_Python_Method
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
End DIAG_SCOPE_PYTHONTECCPLEX001;
/

CREATE OR REPLACE FUNCTION DIAG_PYTHON_ARTIFACTS_TOTAL (
	I_SNAPSHOT_ID INT,	-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,	-- the metric id
	I_METRIC_VALUE_INDEX INT
)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
--<<NAME>>DIAG_PYTHON_ARTIFACTS_TOTAL<</NAME>>
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
	And MO.TECHNO_TYPE		= 1021000  -- Technology Python
	And MO.MODULE_ID		= SC.OBJECT_ID
	And T1.APPLICATION_ID		= SC.OBJECT_ID
	And T1.PROPERTIES	= 0 -- Application's Object	
	And T1.OBJECT_TYPE		in (1021008) -- Python method
Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID	;
Return ERRORCODE;
End DIAG_PYTHON_ARTIFACTS_TOTAL;
/

/******************************************************************************/
/** FUNCTION DIAG_PYTHON_FILES_CTOR_TOTAL         * Object from Data Dictionary  */
/******************************************************************************/

CREATE OR REPLACE FUNCTION DIAG_PYTHON_FILES_CTOR_TOTAL (
	I_SNAPSHOT_ID INT,	-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,	-- the metric id
	I_METRIC_VALUE_INDEX INT
)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
--<<NAME>>DIAG_PYTHON_FILES_CTOR_TOTAL<</NAME>>
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
	And T1.OBJECT_TYPE		= 1021006 -- Python source code
Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID	;
Return ERRORCODE;
End DIAG_PYTHON_FILES_CTOR_TOTAL;
/

/******************************************************************************/
/** FUNCTION DIAG_SCOPE_PYTHONDOC002         * Object from Data Dictionary  */
/******************************************************************************/

CREATE OR REPLACE FUNCTION DIAG_SCOPE_PYTHONDOC002 (
	I_SNAPSHOT_ID INT,	-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,	-- the metric id
	I_METRIC_CHILD_ID INT
)
Return INT
Is
	ERRORCODE	INT := 0;
	PARAM_INT	INT := 0;
Begin
--<<NAME>>DIAG_SCOPE_PYTHONDOC002<</NAME>>
--<<COMMENT>> Template name   = GENERIC. <</COMMENT>>
--<<COMMENT>> Template use    = Generic case<</COMMENT>>
--<<COMMENT>> Diagnostic name = Python:Avoid programs with low comment / code ratio details. <</COMMENT>>
--<<COMMENT>> Definition      = Python programs should be documented. This reports shows all the Python programs with less than 5% comment/code ratio details. <</COMMENT>>
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
		T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, SC.MODULE_ID, I_SNAPSHOT_ID,  ( (T2.METRIC_VALUE + T3.METRIC_VALUE) / (Decode(Nvl(T4.METRIC_VALUE,0),0,1,T4.METRIC_VALUE) ) ), 0, 0
    From
    	DIAG_OBJECT_METRICS T2, DIAG_OBJECT_METRICS T3, DIAG_OBJECT_METRICS T4, CTT_OBJECT_APPLICATIONS T1, DSSAPP_MODULES SC
	Where
		SC.TECHNO_TYPE					= 1021000  -- Technologic Python
		And T1.APPLICATION_ID			= SC.MODULE_ID
	And T1.OBJECT_TYPE = 1021006 -- Python source code
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
        And T2.OBJECT_ID 				= T1.OBJECT_ID
        And T2.METRIC_TYPE 				= 'Number of heading comment lines'
        And T3.OBJECT_ID 				= T1.OBJECT_ID
        And T3.METRIC_TYPE 				= 'Number of inner comment lines'
        And T4.OBJECT_ID 				= T1.OBJECT_ID
        And T4.METRIC_TYPE 				= 'Number of code lines'
        And T4.METRIC_VALUE				> 0
        And (100* (T2.METRIC_VALUE + T3.METRIC_VALUE) / (Decode(Nvl(T4.METRIC_VALUE,0),0,1,T4.METRIC_VALUE) ) )< (PARAM_INT)
 	;
Return ERRORCODE;
End DIAG_SCOPE_PYTHONDOC002;
/

CREATE OR REPLACE FUNCTION  SET_Python_1021000(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_Artifact*/
 
  insert into SET_Contents (SetId, ObjectId)
  Select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006);  
     commit;
    
    return ERRORCODE;

End; 
/


CREATE OR REPLACE FUNCTION  SET_Python_1021001(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_httplib  : python object calling httplib */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 1 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfHttplibwebService  
     commit;
    
    return ERRORCODE;

End; 
/

CREATE OR REPLACE FUNCTION  SET_Python_1021002(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_requests  : python object calling requests */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 3 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfRequestsWebService  
     commit;
    
    return ERRORCODE;

End; 
/

CREATE OR REPLACE FUNCTION  SET_Python_1021003(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_aiohttp  : python object calling aiohttp */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 5 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfAiohttpWebService  
     commit;
    
    return ERRORCODE;

End; 
/

CREATE OR REPLACE FUNCTION  SET_Python_1021004(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_urllib  : python object calling urllib */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 7 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfUrllibWebService  
     commit;
    
    return ERRORCODE;

End; 
/

CREATE OR REPLACE FUNCTION  SET_Python_1021005(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_urllib2  : python object calling urllib2 */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 9 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfUrllib2WebService  
     commit;
    
    return ERRORCODE;

End; 
/

CREATE OR REPLACE FUNCTION  SET_Python_1021006(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_httplib2  : python object calling httplib2 */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 11 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfHttplib2WebService  
     commit;
    
    return ERRORCODE;

End; 
/

CREATE OR REPLACE FUNCTION  SET_Python_1021007(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_artifacts_using_yield*/
 
  insert into SET_Contents (SetId, ObjectId)
  Select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008);  -- CAST_Python_Method
     commit;
    
    return ERRORCODE;

End; 
/

CREATE OR REPLACE FUNCTION  SET_Python_1021008(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_hashlib_MD5 */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009);    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
     commit;
    
    return ERRORCODE;

End; 
/

CREATE OR REPLACE FUNCTION  SET_Python_1021009(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_empty_except */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009);    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
     commit;
    
    return ERRORCODE;

End;
/

CREATE OR REPLACE FUNCTION  SET_Python_1021010(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* CRAPPED, TO BE REMOVED */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021006, 1021007, 1021008, 1021009);    -- CAST_Python_SourceCode, CAST_Python_Class,  CAST_Python_Method, or CAST_Python_Script
     commit;
    
    return ERRORCODE;

End;
/

CREATE OR REPLACE FUNCTION  SET_Python_1021011(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_classes */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from CTT_OBJECT_APPLICATIONS o where o.OBJECT_TYPE in (1021007);    --  CAST_Python_Class
     commit;
    
    return ERRORCODE;

End;
/

CREATE OR REPLACE FUNCTION  SET_Python_1021012(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
/* Set name SET_Python_classes */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from CTT_OBJECT_APPLICATIONS o where o.OBJECT_TYPE in (1021006);    --  CAST_Python_SourceCode
     commit;
    
    return ERRORCODE;

End;
/

CREATE OR REPLACE FUNCTION  SET_Python_1021013(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
Begin
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021006, 1021007, 1021008)  -- CAST_Python_SourceCode, CAST_Python_Class, CAST_Python_Method
  and exists(select 1 from ObjInf i
    where i.IdObj = o.OBJECT_ID
      and i.InfTyp = 1021000
      and i.InfSubTyp = 40
      and i.InfVal = 1);  -- CAST_Python_Metric.has_docstring
  
  commit;
  
  return ERRORCODE;

End;
/
