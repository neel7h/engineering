begin
execute immediate 'drop function DSS_DIAG_SCOPE_GENERIC_NUM2';
exception 
when others then null;
end;
/

begin
execute immediate 'drop function DSS_DIAG_TOTAL_GENERIC2';
exception 
when others then null;
end;
/

begin
execute immediate 'drop function DSS_DIAG_SCOPE_PARAM_NUM';
exception 
when others then null;
end;
/

begin
execute immediate 'drop function DSS_TRIGGER_ADDON_DIAG';
exception 
when others then null;
end;
/

begin
execute immediate 'drop function DSS_DIAG_TOTAL_PARAM';
exception 
when others then null;
end;
/

begin
execute immediate 'drop function DSS_TRIGGER_ADDON_TOTAL';
exception 
when others then null;
end;
/

CREATE OR REPLACE FUNCTION DSS_MOVE_QUALITY_RULES_RESULTS (I_SNAPSHOT_ID INT, I_METRIC_PARENT_ID INT, I_METRIC_ID INT, I_METRIC_CHILD_ID INT) 
RETURN INT
IS
BEGIN
    -- DSS_METRIC_PARAM_VALUES with PARAM_INDEX = -5 and OBJECT_TYPE_ID = 0, specifies a source ID as METRIC_ID-1 and a target metric ID as PARAM_NUM_VALUE+1

    -- MOVE VIOLATIONS
    UPDATE DSS_METRIC_RESULTS R 
    SET METRIC_ID = 
            (select CAST(P5.PARAM_NUM_VALUE AS INT) + 1 
             from DSS_METRIC_PARAM_VALUES P5 
             WHERE R.METRIC_ID = P5.METRIC_ID 
             AND P5.OBJECT_TYPE_ID = 0 
             AND P5.PARAM_INDEX = -5 
             AND R.SNAPSHOT_ID = I_SNAPSHOT_ID)
    WHERE
	    EXISTS (
              SELECT 1 FROM DSS_METRIC_PARAM_VALUES P5 
              WHERE R.METRIC_ID = P5.METRIC_ID 
              AND P5.OBJECT_TYPE_ID = 0 
              AND P5.PARAM_INDEX = -5 
              AND R.SNAPSHOT_ID = I_SNAPSHOT_ID)
      AND NOT EXISTS (
              SELECT 1 FROM DSS_OBJECT_EXCEPTIONS E, DSS_METRIC_PARAM_VALUES P5 
              WHERE R.METRIC_ID = P5.METRIC_ID 
              AND E.METRIC_ID = CAST(P5.PARAM_NUM_VALUE AS INT)+1 
              AND P5.OBJECT_TYPE_ID = 0 
              AND P5.PARAM_INDEX = -5 
              AND R.SNAPSHOT_ID = I_SNAPSHOT_ID
              AND E.OBJECT_ID  = R.OBJECT_ID); -- EXCLUSION OF OBJECTS (SEE DASHBOARDS)      

    -- MOVE COUNTERS: TOTALCHECKS, FAILEDCHECKS, ETC.
    UPDATE DSS_METRIC_RESULTS R
    SET METRIC_ID = (
              select CAST(P5.PARAM_NUM_VALUE AS INT) 
              FROM DSS_METRIC_PARAM_VALUES P5 
              WHERE R.METRIC_ID = P5.METRIC_ID - 1 AND P5.OBJECT_TYPE_ID = 0 AND P5.PARAM_INDEX = -5 AND R.SNAPSHOT_ID = I_SNAPSHOT_ID)
	  WHERE 
       EXISTS (
            SELECT 1 FROM DSS_METRIC_PARAM_VALUES P5 
            WHERE R.METRIC_ID = P5.METRIC_ID - 1 
            AND P5.OBJECT_TYPE_ID = 0 
            AND P5.PARAM_INDEX = -5 
            AND R.SNAPSHOT_ID = I_SNAPSHOT_ID);

   RETURN 0;
END DSS_MOVE_QUALITY_RULES_RESULTS;
/

CREATE OR REPLACE FUNCTION DSS_NOP (
    I_SNAPSHOT_ID INT,
    I_METRIC_PARENT_ID INT,
    I_METRIC_ID INT,
    I_METRIC_VALUE_INDEX INT
)
RETURN INT
IS
BEGIN
    RETURN 0;
END DSS_NOP;
/