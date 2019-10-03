create or replace function SET_NoSQLJava_1101915  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* 
Set name SET_NoSQLJava_Collection

*/
 
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1101901, 1101905); 
  
return ERRORCODE;
end;
$body$
LANGUAGE plpgsql
/

create or replace function SET_NoSQLJava_1101916  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* 
Set name SET_NoSQLJava_Connection

*/
 
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1101900); 
  
return ERRORCODE;
end;
$body$
LANGUAGE plpgsql
/