Create Proc DIAG_SCOPE_PYTHONTECCPLEX001 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_CHILD_ID INT
)
As
Begin
DECLARE @PARAM_INT INT
 
	SELECT @PARAM_INT=PARAM_NUM_VALUE
    FROM
     	DSS_METRIC_PARAM_VALUES MTP
    WHERE
        MTP.METRIC_ID	= @I_METRIC_CHILD_ID
        AND PARAM_INDEX	= 1
        
	INSERT INTO DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	SELECT 
		DISTINCT T1.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, SC.MODULE_ID, @I_SNAPSHOT_ID, T3.InfVal, 0, 0
	FROM 
    	CTT_OBJECT_APPLICATIONS T1, DSSAPP_MODULES SC, ObjInf T3
    WHERE                    
	    SC.TECHNO_TYPE					= 1021000
		AND T1.APPLICATION_ID			= SC.MODULE_ID
		AND T1.OBJECT_TYPE 				IN (1021008)
		AND T1.PROPERTIES		= 0
		And	T1.OBJECT_ID				= T3.IdObj
		AND T3.InfTyp					= 9
		And T3.InfSubTyp				= 1
		And T3.InfVal					> @PARAM_INT
		
		AND NOT EXISTS
		(
			SELECT 1
			FROM
				DSS_OBJECT_EXCEPTIONS E
			WHERE
				E.METRIC_ID		= @I_METRIC_ID
				AND E.OBJECT_ID	= T1.OBJECT_ID
		)
End
go
Create Proc DIAG_PYTHON_ARTIFACTS_TOTAL (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_VALUE_INDEX INT
)
As
Begin
DECLARE @ERRORCODE INT
 
 	SELECT @ERRORCODE = 0
 	
    Insert Into DSS_METRIC_RESULTS (METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    Select
		Count(T1.OBJECT_ID)
		, 0, SC.OBJECT_PARENT_ID, @I_METRIC_ID, @I_METRIC_VALUE_INDEX, @I_SNAPSHOT_ID
    From
    	DSS_METRIC_SCOPES SC, DSSAPP_MODULES MO, CTT_OBJECT_APPLICATIONS T1
    Where
	SC.SNAPSHOT_ID		= @I_SNAPSHOT_ID
	And SC.METRIC_PARENT_ID	= @I_METRIC_PARENT_ID
	And SC.METRIC_ID		= @I_METRIC_ID
	And SC.COMPUTE_VALUE		= 0
	And MO.TECHNO_TYPE		= 1021000  -- Technology Python
	And MO.MODULE_ID		= SC.OBJECT_ID
	And T1.APPLICATION_ID		= SC.OBJECT_ID
	And T1.PROPERTIES	= 0 -- Application's Object	
	And T1.OBJECT_TYPE		in (1021008) -- Python method
Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID

return @ERRORCODE
End
go
Create Proc DIAG_PYTHON_FILES_CTOR_TOTAL (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_VALUE_INDEX INT
)
As
Begin
DECLARE @ERRORCODE INT
 
 	SELECT @ERRORCODE = 0
 	
    Insert Into DSS_METRIC_RESULTS (METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    Select
		Count(T1.OBJECT_ID)
		, 0, SC.OBJECT_PARENT_ID, @I_METRIC_ID, @I_METRIC_VALUE_INDEX, @I_SNAPSHOT_ID
    From
    	DSS_METRIC_SCOPES SC, DSSAPP_MODULES MO, CTT_OBJECT_APPLICATIONS T1
    Where
	SC.SNAPSHOT_ID		= @I_SNAPSHOT_ID
	And SC.METRIC_PARENT_ID	= @I_METRIC_PARENT_ID
	And SC.METRIC_ID		= @I_METRIC_ID
	And SC.COMPUTE_VALUE		= 0
	And MO.TECHNO_TYPE		= 1021000  -- Technologic Python
	And MO.MODULE_ID		= SC.OBJECT_ID
	And T1.APPLICATION_ID		= SC.OBJECT_ID
	And T1.PROPERTIES	= 0 -- Application's Object	
	And T1.OBJECT_TYPE		= 1021006 -- Python source code
	Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID

return @ERRORCODE

End
go
Create Proc DIAG_SCOPE_PYTHONDOC002 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_CHILD_ID INT
)
As
Begin
DECLARE @ERRORCODE INT
DECLARE @PARAM_INT INT
 
 	SELECT @ERRORCODE = 0
 	
    Select @PARAM_INT = PARAM_NUM_VALUE
    From
     	DSS_METRIC_PARAM_VALUES MTP
    Where
        MTP.METRIC_ID	= @I_METRIC_CHILD_ID
        And PARAM_INDEX	= 1;

	Insert Into DSS_METRIC_SCOPES
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	Select
		T1.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, SC.MODULE_ID, @I_SNAPSHOT_ID,  ( CONVERT(FLOAT,IsNull(T2.METRIC_VALUE,0)) + CONVERT(FLOAT,IsNull(T3.METRIC_VALUE,0))) / (Case IsNull(T4.METRIC_VALUE,0) When 0 Then 1 Else T4.METRIC_VALUE END), 0, 0
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
				E.METRIC_ID		= @I_METRIC_ID
				And E.OBJECT_ID	= T1.OBJECT_ID
		)
        And T2.OBJECT_ID 				= T1.OBJECT_ID
        And T2.METRIC_TYPE 				= 'Number of heading comment lines'
        And T3.OBJECT_ID 				= T1.OBJECT_ID
        And T3.METRIC_TYPE 				= 'Number of inner comment lines'
        And T4.OBJECT_ID 				= T1.OBJECT_ID
        And T4.METRIC_TYPE 				= 'Number of code lines'
        And T4.METRIC_VALUE				> 0
        And (100*( CONVERT(FLOAT,IsNull(T2.METRIC_VALUE,0)) + CONVERT(FLOAT,IsNull(T3.METRIC_VALUE,0))) / (Case IsNull(T4.METRIC_VALUE,0) When 0 Then 1 Else T4.METRIC_VALUE END) )< @PARAM_INT

return @ERRORCODE

End
go


Create Proc SET_Python_1021000  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_Artifact*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006);
End
go



Create Proc SET_Python_1021001  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_httplib  : python object calling httplib */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 1 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfHttplibwebService  
End
go

Create Proc SET_Python_1021002  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_requests  : python object calling requests */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 3 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfRequestsWebService  
End
go

Create Proc SET_Python_1021003  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_aiohttp  : python object calling aiohttp */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 5 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfAiohttpWebService  
End
go

Create Proc SET_Python_1021004  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_urllib  : python object calling urllib */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 7 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfUrllibWebService  
End
go

Create Proc SET_Python_1021005  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_urllib2  : python object calling urllib2 */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 9 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfUrllib2WebService  
End
go

Create Proc SET_Python_1021006  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_httplib2  : python object calling httplib2 */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009)    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1021000 and i.InfSubTyp = 11 and i.InfVal = 1);  --CAST_Pyhton_Rule.useOfHttplib2WebService  
End
go

Create Proc SET_Python_1021007  (@I_SET_ID int)
As
Begin
/* SET_Python_artifacts_using_yield*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008);  -- CAST_Python_Method
End
go

Create Proc SET_Python_1021008  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_hashlib_MD5 */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009);    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script  
End
go

Create Proc SET_Python_1021009  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_empty_except */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021008, 1021006, 1021009);    -- CAST_Python_Method, CAST_Python_SourceCode or CAST_Python_Script  
End
go

Create Proc SET_Python_1021010  (@I_SET_ID int)
As
Begin
/* CRAPPED, TO BE REMOVED */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1021006, 1021007, 1021008, 1021009);    -- CAST_Python_SourceCode, CAST_Python_Class,  CAST_Python_Method, or CAST_Python_Script
End
go

Create Proc SET_Python_1021011  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_classes */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from CTT_OBJECT_APPLICATIONS o where o.OBJECT_TYPE in (1021007);    --  CAST_Python_Class
End
go

Create Proc SET_Python_1021012  (@I_SET_ID int)
As
Begin
/* Set name SET_Python_classes */

  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from CTT_OBJECT_APPLICATIONS o where o.OBJECT_TYPE in (1021006);    --  CAST_Python_SourceCode
End
go

Create Proc SET_Python_1021013  (@I_SET_ID int)
As
Begin
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
  where o.OBJECT_TYPE in (1021006, 1021007, 1021008)  -- CAST_Python_SourceCode, CAST_Python_Class, CAST_Python_Method
  and exists(select 1 from ObjInf i
    where i.IdObj = o.OBJECT_ID
      and i.InfTyp = 1021000
      and i.InfSubTyp = 40
      and i.InfVal = 1);  -- CAST_Python_Metric.has_docstring
End
go