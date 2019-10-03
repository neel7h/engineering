create or replace function  SECQR_JavaMethod_1039000  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE   INT := 0;
begin
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (101,102,988,991,142034,274,281); --Java Method, JSP File
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SECQR_JavaClass_1039001  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE   INT := 0;
begin
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (900, 989, 990, 100, 104); --Java Class, Interface, Generic Class
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SECQR_ClassMethod_1039002  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE   INT := 0;
begin
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
    where o.TECHNO_TYPE      = 140029
    and o.OBJECT_TYPE In (select IdTyp from TypCat where IdCatParent  in (10024, 10008));  --Java Class and Java Methods
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SECQR_ServletMethod_1039003  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE   INT := 0;
begin
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (102)
    and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1039007 and i.InfSubTyp = 3);  -- Java Servelt Methods
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SECQR_ServletMethod_1039004  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE   INT := 0;
begin
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
    where o.TECHNO_TYPE      = 140029
    and o.OBJECT_TYPE in (102)
    and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1039015 and i.InfSubTyp = 7);  -- Java Servelt Methods
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  JEE_SEC_AtCodeAnno_1039005  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE   INT := 0;
begin
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
    where o.TECHNO_TYPE      = 140029
    and o.OBJECT_TYPE In (select IdTyp from TypCat where IdCatParent  in (10024, 10008))
    and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1039047 and i.InfSubTyp = 15);  -- @code annotation
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  JEE_SEC_AtCodeAnno_1039006  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE   INT := 0;
begin
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
    where o.TECHNO_TYPE      = 140029
    and o.OBJECT_TYPE in (102)
    and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1039051 and i.InfSubTyp = 16);  -- @Method override annotation
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/