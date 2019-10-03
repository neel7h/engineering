CREATE OR REPLACE FUNCTION DIAG_ARTIFAC_TOTAL (
	I_SNAPSHOT_ID INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,			-- the metric id
	I_METRIC_VALUE_INDEX INT
)
returns int as
$body$
declare
	ERRORCODE	int := 0;
Begin
--<<NAME>>DIAG_ARTIFAC_TOTAL<</NAME>>*/
--<<COMMENT>> Template name   = TOTALARTIFACTSALLTECHNO. <</COMMENT>>
--<<COMMENT>> Definition      = Count of Artifacts. <</COMMENT>>
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
		and T1.TECHNO_TYPE not in ( 1101000 ) -- SQLScript objects		
    Group By SC.OBJECT_PARENT_ID, SC.OBJECT_ID
	; 
Return ERRORCODE;
END;
$body$
language plpgsql
/