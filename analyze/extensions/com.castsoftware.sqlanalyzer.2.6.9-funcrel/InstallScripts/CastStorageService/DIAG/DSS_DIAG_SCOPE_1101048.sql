create or replace function DSS_DIAG_SCOPE_1101048 (
	I_SNAPSHOT_ID       int,
	I_METRIC_PARENT_ID  int,
	I_METRIC_ID         int,
	I_METRIC_CHILD_ID   int,
	I_SCOPE_ID          int,
	I_PROPERTY_ID       int
)
returns int
as
$body$
begin

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
		And T1.OBJECT_TYPE	= 1101012
		And not exists ( select 1 
                      from DSS_METRIC_PARAM_VALUES PA 
					 where PA.METRIC_ID		= I_METRIC_CHILD_ID
                      
		And INSTR (TN.OBJECT_NAME, PA.PARAM_CHAR_VALUE) = 1
		And SC.TECHNO_TYPE = PA.OBJECT_TYPE_ID     
                   );

	return 0;
end;
$body$
language 'plpgsql'
/