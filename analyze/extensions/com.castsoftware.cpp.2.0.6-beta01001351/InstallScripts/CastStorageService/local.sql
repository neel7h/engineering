
create or replace function  SET_1065000  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE   INT := 0;
begin
/* Set name SET_Cpp_Enum */

  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from CTT_OBJECT_APPLICATIONS o where o.OBJECT_TYPE in (594);    -- C_ENUM
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/