create procedure SET_NoSQLJava_1101915  (@I_SET_ID int)
as
begin
/* 
Set name SET_NoSQLJava_Connection

*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1101901, 1101905)
  
end
go
