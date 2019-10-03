create or replace function  SET_JavaMethod  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE   INT := 0;
begin
/* Set name SET_JavaMethod */
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
    where o.TECHNO_TYPE 	 = 140029 
    and o.OBJECT_TYPE In (select IdTyp from TypCat where IdCatParent  = 10008); -- APM Java Methods
  
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/