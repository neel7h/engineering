Create Proc SET_1020000  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Artifact*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026);
End
go
Create Proc SET_HTML5_Function_1020001  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Function*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183);
End
go
Create Proc SET_HTML5_Source_Code  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Source_Code*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE = 1020006;
End
go
Create Proc SET_HTML5_CSS_Source_Code  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_CSS_Source_Code*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020123,1020127);
End
go
Create Proc SET_HTML5_Func_WebSocket  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Func_WebSocket*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183)
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020001 and i.InfSubTyp = 0 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function.containsWebSocket
End
go
Create Proc SET_HTML5_Func_XMLHttpReq  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Func_XMLHttpReq*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183)
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020001 and i.InfSubTyp = 1 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function.containsXMLHttpRequest
End
go
Create Proc SET_HTML5_SrcCode_Http_Ref  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_SrcCode_Http_Ref*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE = 1020006	-- CAST_HTML5_SourceCode
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020001 and i.InfSubTyp = 2 and i.InfVal = 1);  --CAST_HTML5_SourceCode.containsHttpReference
  
End
go
Create Proc DIAG_SCOPE_HTML5TECCPLEX001 (
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
	    SC.TECHNO_TYPE					= 1020000
		AND T1.APPLICATION_ID			= SC.MODULE_ID
		AND T1.OBJECT_TYPE 				IN (1020007, 1020180, 1020183)
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
Create Proc DIAG_HTML5_ARTIFACTS_TOTAL (
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
	And MO.TECHNO_TYPE		= 1020000  -- Technology HTML5
	And MO.MODULE_ID		= SC.OBJECT_ID
	And T1.APPLICATION_ID		= SC.OBJECT_ID
	And T1.PROPERTIES	= 0 -- Application's Object	
	And T1.OBJECT_TYPE		in (1020007, 1020180, 1020183) -- Javascript function
Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID

return @ERRORCODE
End
go
Create Proc DIAG_HTML5_FILES_CTOR_TOTAL (
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
	And MO.TECHNO_TYPE		= 1020000  -- Technologic HTML5
	And MO.MODULE_ID		= SC.OBJECT_ID
	And T1.APPLICATION_ID		= SC.OBJECT_ID
	And T1.PROPERTIES	= 0 -- Application's Object	
	And T1.OBJECT_TYPE		= 1020026 -- Javascript source code
	Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID

return @ERRORCODE

End
go
Create Proc DIAG_SCOPE_HTML5DOC002 (
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
Create Proc SET_HTML5_Class_1020001  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Class*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE = 1020179;
End
go
Create Proc DIAG_MANY_HTML5PARAMS (
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
	    SC.TECHNO_TYPE					= 1020000
		AND T1.APPLICATION_ID			= SC.MODULE_ID
		AND T1.OBJECT_TYPE 				IN (1020007, 1020180, 1020183)
		AND T1.PROPERTIES		= 0
		And	T1.OBJECT_ID				= T3.IdObj
		AND T3.InfTyp					= 1020051
		And T3.InfSubTyp				= 23
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
Create Proc DIAG_HTML5_FUNC_METH_TOTAL (
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
	And MO.TECHNO_TYPE		= 1020000  -- Technologic HTML5
	And MO.MODULE_ID		= SC.OBJECT_ID
	And T1.APPLICATION_ID		= SC.OBJECT_ID
	And T1.PROPERTIES	= 0 -- Application's Object	
	And T1.OBJECT_TYPE		in (1020007, 1020180, 1020183) -- Javascript function, methods and constructors
	Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID

return @ERRORCODE

End
go

Create Proc DIA_MANY_UNDOCFUNCTION_HTML5 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_CHILD_ID INT
)
As
declare @L_PARAM_NUM    int
Begin
/*<<NAME>>DIA_MANY_UNDOCFUNCTION<</NAME>>*/
/*<<COMMENT>> Template name   = DSSGENERIC. <</COMMENT>>*/
/*<<COMMENT>> Diagnostic name = Avoid undocumented functions. <</COMMENT>>*/
/*<<COMMENT>> Definition      = functions should be documented. This reports shows all the undocumented.. <</COMMENT>>*/
/*<<COMMENT>> Action          = Find all undocumented functions. <</COMMENT>>*/
/*<<COMMENT>> Value           = 1. <</COMMENT>>*/
 	Select @L_PARAM_NUM = 0
     
	
	Insert Into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	Select 
		 T1.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, T1.APPLICATION_ID, @I_SNAPSHOT_ID, 1, Null, 0, 0
	From 
		DSSAPP_ARTIFACTS T1 left outer join DSS_OBJECT_EXCEPTIONS E on (E.OBJECT_ID = T1.OBJECT_ID and E.METRIC_ID = @I_METRIC_ID)  
	
    Where E.OBJECT_ID is null
    
and T1.TECHNO_TYPE  
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = @I_METRIC_ID 
						) 
and T1.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 10052	) -- APM Inventory Functions
and T1.CODE_LINES > 0 
and T1.COMMENT_LINES = 0
and Not Exists
	(
		Select 1 from ObjInf T3 where T1.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --Anonymous
	)

    
	
	 
	
END
go
Create Proc DIT_MANY_FUNCTIONS_HTML5 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_VALUE_INDEX INT
)
As
Begin
/*<<NAME>>DIT_MANY_FUNCTIONS <</NAME>>*/
/*<<COMMENT>> Template name   = TOTALARTIFACTS. <</COMMENT>>*/
/*<<COMMENT>> Definition      = Count of Inventory Functions. <</COMMENT>>*/
    Insert Into DSS_METRIC_RESULTS
        (METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    Select 
        Count(T1.OBJECT_ID), 0, SC.OBJECT_PARENT_ID, @I_METRIC_ID, @I_METRIC_VALUE_INDEX, @I_SNAPSHOT_ID 
    From 
        DSSAPP_ARTIFACTS T1 left outer join DSS_OBJECT_EXCEPTIONS E on (E.OBJECT_ID = T1.OBJECT_ID and E.METRIC_ID = @I_METRIC_ID),
        DSS_METRIC_SCOPES SC 
    Where                    
        E.OBJECT_ID                 is null
        And SC.SNAPSHOT_ID          = @I_SNAPSHOT_ID
        And SC.METRIC_PARENT_ID     = @I_METRIC_PARENT_ID
        And SC.METRIC_ID            = @I_METRIC_ID
        And SC.COMPUTE_VALUE        = 0
        And T1.TECHNO_TYPE            
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = @I_METRIC_ID 
						) 
        And T1.APPLICATION_ID       = SC.OBJECT_ID
		
     and T1.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 10052	) -- APM Inventory Functions
	and Not Exists
	(
		Select 1 from ObjInf T3 where T1.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --Anonymous
	)

    Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID
End
go
Create Proc DIT_MANY_ALLFUNCTIONS_HTML5 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_VALUE_INDEX INT
)
As
Begin
/*<<NAME>>DIT_MANY_ALLFUNCTIONS <</NAME>>*/
/*<<COMMENT>> Template name   = TOTALARTIFACTS. <</COMMENT>>*/
/*<<COMMENT>> Definition      = Count of Inventory Functions and SQL functions. <</COMMENT>>*/
    Insert Into DSS_METRIC_RESULTS
        (METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    Select 
        Count(T1.OBJECT_ID), 0, SC.OBJECT_PARENT_ID, @I_METRIC_ID, @I_METRIC_VALUE_INDEX, @I_SNAPSHOT_ID 
    From 
        DSSAPP_ARTIFACTS T1 left outer join DSS_OBJECT_EXCEPTIONS E on (E.OBJECT_ID = T1.OBJECT_ID and E.METRIC_ID = @I_METRIC_ID),
        DSS_METRIC_SCOPES SC 
    Where                    
        E.OBJECT_ID                 is null
        And SC.SNAPSHOT_ID          = @I_SNAPSHOT_ID
        And SC.METRIC_PARENT_ID     = @I_METRIC_PARENT_ID
        And SC.METRIC_ID            = @I_METRIC_ID
        And SC.COMPUTE_VALUE        = 0
        And T1.TECHNO_TYPE            
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = @I_METRIC_ID 
						) 
        And T1.APPLICATION_ID       = SC.OBJECT_ID
		
     and T1.OBJECT_TYPE = 1020007 -- CAST_HTML5_JavaScript_Function

    Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID
End
go
Create Proc DIA_MANY_UNREFFUNCTION_HTML5 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_CHILD_ID INT
)
As
Begin
/*<<NAME>>DIA_OTHER_UNREFFUNCTION<</NAME>>*/
/*<<COMMENT>> Template name   = DSSGENERIC. <</COMMENT>>*/
/*<<COMMENT>> Diagnostic name = Avoid unreferenced functions. <</COMMENT>>*/
/*<<COMMENT>> Definition      = Unreferenced functions make the code less readable and maintainable. <</COMMENT>>*/
/*<<COMMENT>> Action          = Avoid unreferenced functions. <</COMMENT>>*/
/*<<COMMENT>> Value           = 1. <</COMMENT>>*/

    


 truncate table  WK_DIA_OBJECT 
   
  insert into WK_DIA_OBJECT 
    ( OBJECT_ID ) 
     select distinct T2.CALLED_ID
       from DIAG_CTV_LINKS_SIMPLE T2, CTV_OBJECTS CF
      where T2.CALLER_ID = CF.OBJECT_ID 
        and CF.OBJECT_TYPE != 512
    
  
  Insert Into DSS_METRIC_SCOPES 
    (OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
  Select 
     da.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, da.APPLICATION_ID, @I_SNAPSHOT_ID, 0, Null, 0, 0
  From 
    DSSAPP_ARTIFACTS da left outer join DSS_OBJECT_EXCEPTIONS E on (E.OBJECT_ID = da.OBJECT_ID and E.METRIC_ID = @I_METRIC_ID)  
  
    Where E.OBJECT_ID is null
    
and da.TECHNO_TYPE  
           in ( select MTP.OBJECT_TYPE_ID
              from DSS_METRIC_PARAM_TYPES MTP
             where MTP.METRIC_ID = @I_METRIC_ID 
            ) 
and da.OBJECT_TYPE = 1020007 -- CAST_HTML5_JavaScript_Function
	and Exists
	(
		Select 1 from ObjInf T3 where da.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 28 --unreferencedFunctionEnabled
	)
	and not Exists
	(
		Select 1 from Acc where IdCle = da.OBJECT_ID
	)
and da.OBJECT_ID not in ( select w.OBJECT_ID from WK_DIA_OBJECT w ) 

    
  
  
truncate table  WK_DIA_OBJECT 

  
END
GO
Create Proc DIA_MANY_LOWDOCFUNCTION_HTML5 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_CHILD_ID INT
)
As
       
Begin
/*<<NAME>>DIA_MANY_LOWDOCFUNCTION<</NAME>>*/
/*<<COMMENT>> Template name   = UNDOCUMENTEDRATIOARTIFACT. <</COMMENT>>*/
/*<<COMMENT>> Diagnostic name = Avoid functions with low comment / code ratio. <</COMMENT>>*/
/*<<COMMENT>> Definition      = functions should be documented. This reports shows all the  functions with less than 5% comment/code ratio.. <</COMMENT>>*/
/*<<COMMENT>> Action          = Find all functions  that have a very low Comment/Code ratio. <</COMMENT>>*/
/*<<COMMENT>> Value           = Comment ratio. <</COMMENT>>*/
   
    


 truncate table  TMP_DIA_PAR
 
 insert into TMP_DIA_PAR
      ( TECHNO_TYPE, PARAM_NUM_VALUE )
 select  MTP.OBJECT_TYPE_ID ,max(PARAM_NUM_VALUE)
   from DSSAPP_METRIC_PARAM_VALUES MTP  
  where MTP.METRIC_ID   = @I_METRIC_CHILD_ID
    and MTP.PARAM_INDEX = 1
group by MTP.OBJECT_TYPE_ID 		





	
    insert into DSS_METRIC_SCOPES 
           (OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
    select T1.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, T1.APPLICATION_ID, @I_SNAPSHOT_ID, 
	       ( CONVERT(FLOAT, T1.COMMENT_LINES ) / T1.CODE_LINES ) , 0, 0
      from   DSSAPP_ARTIFACTS T1 left outer join DSS_OBJECT_EXCEPTIONS E on (E.OBJECT_ID = T1.OBJECT_ID and E.METRIC_ID = @I_METRIC_ID)
     where E.OBJECT_ID                 is null
       and T1.TECHNO_TYPE           
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = @I_METRIC_ID 
						)       
       and T1.CODE_LINES        > 0
	   
     and T1.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 10052	) -- APM Inventory Functions
	and Not Exists
	(
		Select 1 from ObjInf T3 where T1.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --Anonymous
	)

       and 100* ( CONVERT(FLOAT, T1.COMMENT_LINES ) / T1.CODE_LINES ) < 
                           (  select PARAM_NUM_VALUE
                             from TMP_DIA_PAR MTP  
							where MTP.TECHNO_TYPE  = T1.TECHNO_TYPE
                         )
 
End
go
Create Proc DIA_MANY_TECCPLEX005_HTML5 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_CHILD_ID INT
)
As
declare @L_PARAM_NUM    int
Begin
/*<<NAME>>DIA_MANY_TECCPLEX005<</NAME>>*/
/*<<COMMENT>> Template name   = DSSGENERIC. <</COMMENT>>*/
/*<<COMMENT>> Diagnostic name = Avoid <Artifacts> with long lines. <</COMMENT>>*/
/*<<COMMENT>> Definition      = Avoid <Artifacts> with long lines. <</COMMENT>>*/
/*<<COMMENT>> Action          = Lists all <Artifacts> with long lines. <</COMMENT>>*/
/*<<COMMENT>> Value           = 1. <</COMMENT>>*/
 	Select @L_PARAM_NUM = 0
    


 truncate table  TMP_DIA_PAR
 
 insert into TMP_DIA_PAR
      ( TECHNO_TYPE, PARAM_NUM_VALUE )
 select  MTP.OBJECT_TYPE_ID ,max(PARAM_NUM_VALUE)
   from DSSAPP_METRIC_PARAM_VALUES MTP  
  where MTP.METRIC_ID   = @I_METRIC_CHILD_ID
    and MTP.PARAM_INDEX = 1
group by MTP.OBJECT_TYPE_ID 		





	
	Insert Into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	Select 
		 T1.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, T1.APPLICATION_ID, @I_SNAPSHOT_ID, T1.LONG_LINES, Null, 0, 0
	From 
		DSSAPP_ARTIFACTS T1  left outer join DSS_OBJECT_EXCEPTIONS E on (E.OBJECT_ID = T1.OBJECT_ID and E.METRIC_ID = @I_METRIC_ID)  
	
    Where E.OBJECT_ID is null
    
    and T1.TECHNO_TYPE  
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = @I_METRIC_ID 
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
    
	
	 
	
END
GO
Create Proc DIA_MANY_TECCPLEX003_HTML5 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_CHILD_ID INT
)
As
declare @L_PARAM_NUM    int
Begin
/*<<NAME>>DIA_MANY_TECCPLEX003<</NAME>>*/
/*<<COMMENT>> Template name   = DSSGENERIC. <</COMMENT>>*/
/*<<COMMENT>> Diagnostic name = Avoid <Artifacts> with High Depth of Code (DoC > 5). <</COMMENT>>*/
/*<<COMMENT>> Definition      = Avoid <Artifacts> with High Depth of Code (DoC > 5). <</COMMENT>>*/
/*<<COMMENT>> Action          = Lists all <Artifacts> with High Depth of Code. <</COMMENT>>*/
/*<<COMMENT>> Value           = 1. <</COMMENT>>*/
 	Select @L_PARAM_NUM = 0
    


 truncate table  TMP_DIA_PAR
 
 insert into TMP_DIA_PAR
      ( TECHNO_TYPE, PARAM_NUM_VALUE )
 select  MTP.OBJECT_TYPE_ID ,max(PARAM_NUM_VALUE)
   from DSSAPP_METRIC_PARAM_VALUES MTP  
  where MTP.METRIC_ID   = @I_METRIC_CHILD_ID
    and MTP.PARAM_INDEX = 1
group by MTP.OBJECT_TYPE_ID 		





	
	Insert Into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	Select 
		 T1.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, T1.APPLICATION_ID, @I_SNAPSHOT_ID, T1.CODE_DEPTH, Null, 0, 0
	From 
		DSSAPP_ARTIFACTS T1  left outer join DSS_OBJECT_EXCEPTIONS E on (E.OBJECT_ID = T1.OBJECT_ID and E.METRIC_ID = @I_METRIC_ID)  
	
    Where E.OBJECT_ID is null
    
    and T1.TECHNO_TYPE  
				   in ( select MTP.OBJECT_TYPE_ID
						  from DSS_METRIC_PARAM_TYPES MTP
						 where MTP.METRIC_ID = @I_METRIC_ID 
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

    
	
	 
	
END
GO

Create Proc DIA_MANY_FUNC_IN_HTML_HTML5 (
    @I_SNAPSHOT_ID INT,         -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_CHILD_ID INT
)
As
Begin
/*<<NAME>>DIA_MANY_FUNC_IN_HTML_HTML5<</NAME>>*/
/*<<COMMENT>> Template name   = DSSGENERIC. <</COMMENT>>*/
/*<<COMMENT>> Diagnostic name = Avoid unreferenced functions. <</COMMENT>>*/
/*<<COMMENT>> Definition      = Unreferenced functions make the code less readable and maintainable. <</COMMENT>>*/
/*<<COMMENT>> Action          = Avoid unreferenced functions. <</COMMENT>>*/
/*<<COMMENT>> Value           = 1. <</COMMENT>>*/

    


 truncate table  WK_DIA_OBJECT 
   
  insert into WK_DIA_OBJECT 
    ( OBJECT_ID ) 
     select distinct T2.CALLED_ID
       from DIAG_CTV_LINKS_SIMPLE T2, CTV_OBJECTS CF
      where T2.CALLER_ID = CF.OBJECT_ID 
        and CF.OBJECT_TYPE != 512
    
  
  Insert Into DSS_METRIC_SCOPES 
    (OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
  Select 
     da.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, da.APPLICATION_ID, @I_SNAPSHOT_ID, 0, Null, 0, 0
  From 
    DSSAPP_ARTIFACTS da left outer join DSS_OBJECT_EXCEPTIONS E on (E.OBJECT_ID = da.OBJECT_ID and E.METRIC_ID = @I_METRIC_ID)  
      	join DIAG_OBJECT_PARENTS pa on da.OBJECT_ID = pa.OBJECT_ID
  
    Where E.OBJECT_ID is null
    
and da.TECHNO_TYPE  
           in ( select MTP.OBJECT_TYPE_ID
              from DSS_METRIC_PARAM_TYPES MTP
             where MTP.METRIC_ID = @I_METRIC_ID 
            ) 
and da.OBJECT_TYPE in ( 1020007 ) -- CAST_HTML5_JavaScript_Function
	and Not Exists
	(
		Select 1 from ObjInf T3 where da.OBJECT_ID = T3.IdObj and T3.InfTyp	= 1020052 and T3.InfSubTyp = 27 --anonymous
	)
and da.OBJECT_ID not in ( select w.OBJECT_ID from WK_DIA_OBJECT w ) 
and pa.PARENT_TYPE in ( 1020030 ) -- CAST_HTML5_JavaScript_SourceCode_Fragment

    
  
  
truncate table  WK_DIA_OBJECT 

  
END
GO
Create Proc SET_HTML5_Func_Cookie  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Func_Cookie*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020052 and i.InfSubTyp = 30 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsCookieCall
End
go
Create Proc SET_HTML5_Func_SetTimeout  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Func_SetTimeout*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020052 and i.InfSubTyp = 32 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsSetTimeout
End
go
Create Proc SET_HTML5_Document_Cookie  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Document_Cookie*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020052 and i.InfSubTyp = 34 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsCookieCall
End
go
Create Proc SET_HTML5_JSONParseStringify  (@I_SET_ID int)
As
Begin
/* Set name SET_HTML5_Javascript_Function_with_JSONParseStringify*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020101 and i.InfSubTyp = 5 and i.InfVal = 1);  --CAST_HTML5_JavaScript_Function_SourceCode_Properties.containsJSONParseOrStringify
End
go
