create or replace function  SET_JavaMethodsAndLambdas  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_JavaMethodsAndLambdas <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Java Methods, Generic Methods and Lambdas. <</COMMENT>>*/   
 
  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, a.OBJECT_ID
    from DSSAPP_ARTIFACTS a 
    
 where a.TECHNO_TYPE  = 140029   -- Technologic JEE 
 and a.OBJECT_TYPE in (102, 988, 142034) --Method, generic method & lambdas
    ;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
