If Exists(Select name From sysobjects Where name='DSS_DIAG_SCOPE_GENERIC_NUM2' And type='P')
    Drop Proc DSS_DIAG_SCOPE_GENERIC_NUM2
go

If Exists(Select name From sysobjects Where name='DSS_DIAG_TOTAL_GENERIC2' And type='P')
    Drop Proc DSS_DIAG_TOTAL_GENERIC2
go

If Exists(Select name From sysobjects Where name='DSS_DIAG_SCOPE_PARAM_NUM' And type='P')
    Drop Proc DSS_DIAG_SCOPE_PARAM_NUM
go

If Exists(Select name From sysobjects Where name='DSS_TRIGGER_ADDON_DIAG' And type='P')
    Drop Proc DSS_TRIGGER_ADDON_DIAG
go

If Exists(Select name From sysobjects Where name='DSS_DIAG_TOTAL_PARAM' And type='P')
    Drop Proc DSS_DIAG_TOTAL_PARAM
go

If Exists(Select name From sysobjects Where name='DSS_TRIGGER_ADDON_TOTAL' And type='P')
    Drop Proc DSS_TRIGGER_ADDON_TOTAL
go

If Exists(Select name From sysobjects Where name='DSS_MOVE_QUALITY_RULES_RESULTS' And type='P')
    Drop Proc DSS_MOVE_QUALITY_RULES_RESULTS
go
create procedure DSS_MOVE_QUALITY_RULES_RESULTS (
    @I_SNAPSHOT_ID INT, 
    @I_METRIC_PARENT_ID INT,  
    @I_METRIC_ID INT, 
    @I_METRIC_CHILD_ID INT) 
AS
BEGIN
    -- DSS_METRIC_PARAM_VALUES with PARAM_INDEX = -5 and OBJECT_TYPE_ID = 0, specifies a source ID as METRIC_ID-1 and a target metric ID as PARAM_NUM_VALUE+1

    -- MOVE VIOLATIONS
    UPDATE DSS_METRIC_RESULTS
    SET METRIC_ID = convert(int, P5.PARAM_NUM_VALUE) + 1
    FROM 
        DSS_METRIC_PARAM_VALUES P5
    WHERE 
            P5.OBJECT_TYPE_ID = 0 
        AND P5.PARAM_INDEX = -5
 		AND DSS_METRIC_RESULTS.SNAPSHOT_ID = @I_SNAPSHOT_ID
		AND DSS_METRIC_RESULTS.METRIC_ID = P5.METRIC_ID
        AND NOT EXISTS (SELECT 1 FROM DSS_OBJECT_EXCEPTIONS E WHERE E.METRIC_ID = convert(int, P5.PARAM_NUM_VALUE)+1 AND E.OBJECT_ID  = DSS_METRIC_RESULTS.OBJECT_ID) -- EXCLUSION OF OBJECTS (SEE DASHBOARDS)      

    -- MOVE COUNTERS: TOTALCHECKS, FAILEDCHECKS, ETC.
    UPDATE DSS_METRIC_RESULTS 
    SET METRIC_ID = convert(int, P5.PARAM_NUM_VALUE) 
    FROM 
        DSS_METRIC_PARAM_VALUES P5
    WHERE 
            P5.OBJECT_TYPE_ID = 0 
        AND P5.PARAM_INDEX = -5
 		AND DSS_METRIC_RESULTS.SNAPSHOT_ID = @I_SNAPSHOT_ID
		AND DSS_METRIC_RESULTS.METRIC_ID	= P5.METRIC_ID - 1

   RETURN 0
END 	
go


IF EXISTS(SELECT NAME FROM sysobjects WHERE NAME='DSS_NOP' AND TYPE='P')
    DROP PROC DSS_NOP
GO
CREATE PROCEDURE DSS_NOP (
    @I_SNAPSHOT_ID INT,
    @I_METRIC_PARENT_ID INT,
    @I_METRIC_ID INT,
    @I_METRIC_VALUE_INDEX INT
)
AS
BEGIN
    RETURN 0
END
go