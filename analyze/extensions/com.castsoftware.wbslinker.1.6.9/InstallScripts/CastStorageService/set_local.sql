create or replace function  SET_RESOURCES  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_WbsLinker_Resources*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 141964 ); -- CAST_ResourceService

Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
