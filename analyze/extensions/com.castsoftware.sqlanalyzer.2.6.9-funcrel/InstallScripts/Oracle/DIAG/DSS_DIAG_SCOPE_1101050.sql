CREATE OR REPLACE FUNCTION DSS_DIAG_SCOPE_1101050  (
	I_SNAPSHOT_ID       in int,
	I_METRIC_PARENT_ID  in int,
	I_METRIC_ID         in int,
	I_METRIC_CHILD_ID   in int,
	I_SCOPE_ID          in int,
	I_PROPERTY_ID       in int
)
Return INT
Is
	ERRORCODE	INT := 0;
Begin

    insert into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE, POSITION_ID)
	select 
		T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, SC.MODULE_ID, I_SNAPSHOT_ID, 1, Null, 0, 0
	from 
		DSSAPP_MODULES SC 
		join CTT_OBJECT_APPLICATIONS T1 on ( T1.APPLICATION_ID = SC.MODULE_ID and T1.PROPERTIES = 0 )
		join CDT_OBJECTS TN 			on ( T1.OBJECT_ID	= TN.OBJECT_ID)
		join SET_Contents C				on ( C.ObjectId = T1.OBJECT_ID and C.SetId = I_SCOPE_ID )
	where 
		not exists 
		(
			select 1 
			from 
				DSS_OBJECT_EXCEPTIONS E
			where 
				E.METRIC_ID		= I_METRIC_ID 
				and E.OBJECT_ID	= T1.OBJECT_ID 
		)
		And T1.OBJECT_TYPE	= 1101009
	    And not exists ( select 1 
	                      from DSS_METRIC_PARAM_VALUES PA 
						 where PA.METRIC_ID		= I_METRIC_CHILD_ID
	                      
	    And INSTR (TN.OBJECT_NAME, PA.PARAM_CHAR_VALUE) = 1
	    And SC.TECHNO_TYPE = PA.OBJECT_TYPE_ID     
	                   );

Return ERRORCODE;

End DSS_DIAG_SCOPE_1101050;
/