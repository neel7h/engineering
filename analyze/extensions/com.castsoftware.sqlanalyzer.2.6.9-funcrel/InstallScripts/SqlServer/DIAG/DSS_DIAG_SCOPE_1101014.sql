create proc DSS_DIAG_SCOPE_1101014 (
	@I_SNAPSHOT_ID         int,
	@I_METRIC_PARENT_ID    int,
	@I_METRIC_ID           int,
	@I_METRIC_CHILD_ID     int,
	@I_SCOPE_ID            int,
	@I_PROPERTY_ID         int
	
) with recompile
as
begin

	declare	@ErrorCode int,
	        @L_INFTYP int,
	        @L_INFSUBTYP int
	         
    select @L_INFTYP = IntVal
    from PropAttr
    where IdProp = @I_PROPERTY_ID
    and AttrNam = 'INF_TYPE'
    
    select @L_INFSUBTYP = IntVal
    from PropAttr
    where IdProp = @I_PROPERTY_ID
    and AttrNam = 'INF_SUB_TYPE'

    insert into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE, POSITION_ID)
	select 
		T1.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, T1.APPLICATION_ID, @I_SNAPSHOT_ID, 1, 0, 0, isnull(DP.MetricPositionId, 0)
	from 
		DSS_METRIC_SCOPES SC 
		join CTT_OBJECT_APPLICATIONS T1 on ( T1.APPLICATION_ID = SC.OBJECT_ID and T1.PROPERTIES = 0 )
		join SET_Contents C on ( C.ObjectId = T1.OBJECT_ID and C.SetId = @I_SCOPE_ID )
		left outer join ObjInf OI on ( OI.IdObj = T1.OBJECT_ID and OI.InfTyp = @L_INFTYP and OI.InfSubTyp = @L_INFSUBTYP )
		left outer join ( select distinct ObjectId , MetricPositionId from DSS_Positions  where PropertyId = @I_PROPERTY_ID  ) DP on  DP.ObjectId = T1.OBJECT_ID 
	where 
		SC.SNAPSHOT_ID			= @I_SNAPSHOT_ID
		and SC.METRIC_PARENT_ID	= @I_METRIC_PARENT_ID
		and SC.METRIC_ID		= @I_METRIC_ID
		and not exists 
		(
			select 1 
			from 
				DSS_OBJECT_EXCEPTIONS E
			where 
				E.METRIC_ID		= @I_METRIC_ID 
				and E.OBJECT_ID	= T1.OBJECT_ID 
		)
		-- equivalent of a not exists which is nonSARG operator 
		and OI.IdObj is NULL
   	
	select @ErrorCode = @@error
	if @ErrorCode != 0
		goto GTRAN

GTRAN:
	return @ErrorCode

end
go