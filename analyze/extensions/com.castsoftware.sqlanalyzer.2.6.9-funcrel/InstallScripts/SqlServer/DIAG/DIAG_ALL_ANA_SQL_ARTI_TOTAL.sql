Alter Proc DIAG_ALL_ANA_SQL_ARTI_TOTAL (
    @I_SNAPSHOT_ID INT,     -- the metric snapshot id
    @I_METRIC_PARENT_ID INT,    -- the metric parent id
    @I_METRIC_ID INT,           -- the metric id
    @I_METRIC_VALUE_INDEX INT
)
As
Begin
/*<<NAME>>DIAG_ALL_ANA_SQL_ARTI_TOTAL <</NAME>>*/
/*<<COMMENT>> Template name   = DSSTOTAL. <</COMMENT>>*/
/*<<COMMENT>> Definition      = Couts all client server Artifacts using tables.. <</COMMENT>>*/
    
	 
	
    insert into DSS_METRIC_RESULTS
        (METRIC_NUM_VALUE, METRIC_OBJECT_ID, OBJECT_ID, METRIC_ID, METRIC_VALUE_INDEX, SNAPSHOT_ID)
    select count(distinct T1.OBJECT_ID), 0, SC.OBJECT_PARENT_ID, @I_METRIC_ID, @I_METRIC_VALUE_INDEX, @I_SNAPSHOT_ID 
      from DSSAPP_SQL_ARTIFACTS T1 left outer join DSS_OBJECT_EXCEPTIONS E on (E.OBJECT_ID = T1.OBJECT_ID and E.METRIC_ID = @I_METRIC_ID),
           DSS_METRIC_SCOPES SC  
     where E.OBJECT_ID                 is null
       and SC.SNAPSHOT_ID          = @I_SNAPSHOT_ID
       and SC.METRIC_PARENT_ID     = @I_METRIC_PARENT_ID
       and SC.METRIC_ID            = @I_METRIC_ID
       and SC.COMPUTE_VALUE        = 0
       and SC.OBJECT_ID            = T1.APPLICATION_ID
        
       
and T1.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 10062 ) -- APM Client-Server Artifacts
and ( T1.OBJECT_TYPE = 545     -- No C/S links on Cobol Programs
      or 
      exists ( select 1
                  from DIAG_CTV_LINKS_SIMPLE IL, CTV_OBJECTS TV
                 where TV.OBJECT_TYPE    in ( select TC.IdTyp from TypCat TC where TC.IdCatParent      = 6100  ) -- database table
                   and IL.CALLER_ID     = T1.OBJECT_ID
                   and IL.CALLED_ID     = TV.OBJECT_ID
              )
    )
and T1.OBJECT_TYPE not in ( select IdTyp from TypCat where IdCatParent = 1101004 ) -- SQLScript objects
    group by SC.OBJECT_PARENT_ID, SC.OBJECT_ID
		
	 
End
go