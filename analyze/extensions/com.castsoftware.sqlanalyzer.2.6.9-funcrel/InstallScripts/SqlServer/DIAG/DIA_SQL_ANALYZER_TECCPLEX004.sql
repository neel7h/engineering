if exists(select name from sysobjects where name='DIA_SQL_ANALYZER_TECCPLEX004' and type='P')
	drop proc DIA_SQL_ANALYZER_TECCPLEX004
go
create proc DIA_SQL_ANALYZER_TECCPLEX004 (
	@I_SNAPSHOT_ID         int,
	@I_METRIC_PARENT_ID    int,
	@I_METRIC_ID           int,
	@I_METRIC_CHILD_ID     int,
	@I_SCOPE_ID            int,
	@I_PROPERTY_ID         int
	
) with recompile
as
begin

	declare	@L_ErrorCode int,
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

	 truncate table  TMP_DIA_PAR
 
	 insert into TMP_DIA_PAR
		  ( TECHNO_TYPE, PARAM_NUM_VALUE )
	 select  MTP.OBJECT_TYPE_ID ,max(PARAM_NUM_VALUE)
	   from DSSAPP_METRIC_PARAM_VALUES MTP  
	  where MTP.METRIC_ID   = @I_METRIC_CHILD_ID
		and MTP.PARAM_INDEX = 1
	group by MTP.OBJECT_TYPE_ID 

    insert into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE, POSITION_ID)
	select 
		T1.OBJECT_ID, @I_METRIC_ID, @I_METRIC_CHILD_ID, T1.APPLICATION_ID, @I_SNAPSHOT_ID, OI.InfVal, 0, 0, isnull(DP.MetricPositionId, 0)
	from 
		DSS_METRIC_SCOPES SC 
		join DSSAPP_ARTIFACTS T1 on ( T1.APPLICATION_ID = SC.OBJECT_ID )
		join SET_Contents C on ( C.ObjectId = T1.OBJECT_ID and C.SetId = @I_SCOPE_ID )
		join ObjInf OI on ( OI.IdObj = T1.OBJECT_ID and OI.InfTyp = @L_INFTYP and OI.InfSubTyp = @L_INFSUBTYP )
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
 	and OI.InfVal > (  select PARAM_NUM_VALUE
                             from TMP_DIA_PAR MTP  
	                        where MTP.TECHNO_TYPE  = T1.TECHNO_TYPE
                         )
	and T1.OBJECT_TYPE not in (select  TC.IdTyp from TypCat TC where TC.IdCatParent = 6101)  -- Except Views
   	
	select @L_ErrorCode = @@error
	if @L_ErrorCode != 0
		goto GTRAN

GTRAN:
	return @L_ErrorCode

end
go