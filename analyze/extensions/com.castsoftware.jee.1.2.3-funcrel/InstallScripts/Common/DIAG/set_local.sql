create or replace function  SET_JavaMethodsAndGenerics  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_JavaMethodsAndGenerics <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Java Methods and Generic Methods. <</COMMENT>>*/   
 
  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, a.OBJECT_ID
    from DSSAPP_ARTIFACTS a 
    
 where a.TECHNO_TYPE  = 140029   -- Technologic JEE 
 and a.OBJECT_TYPE in (102, 988) --Method, generic method
    ;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_JavaCtor  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_JavaCtor <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Java Contructors. <</COMMENT>>*/

   
 
  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, f.OBJECT_ID
    from CTT_OBJECT_APPLICATIONS f
                         join DSSAPP_MODULES m on m.MODULE_ID = f.APPLICATION_ID 
  
    
 where m.TECHNO_TYPE  = 140029   -- Technologic JEE 
 and f.OBJECT_TYPE in ( 101, 991) -- Java Constructor, Generic Java Constructor

    ;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_JavaArtifactMutation  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_JavaArtifactMutation <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Java Artifacts that has incompatible mutation . <</COMMENT>>*/   
 
  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, a.OBJECT_ID
    from DSSAPP_ARTIFACTS a 
    where a.TECHNO_TYPE = 140029 -- Technologic JEE
    and a.OBJECT_TYPE in (101,102,105,988,991,137127,142034,274) -- Constructor, method, JV_INIT, generic method, generic Constructor, annotation method, lambda, web file(CAST_Web_TranferedJavaProperties)
    ;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_JavaArtifactOpenDatabase  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_JavaArtifactOpenDatabase <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Java Methods that open a database resource . <</COMMENT>>*/   
 
  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, a.OBJECT_ID
    from DSSAPP_ARTIFACTS a
    where a.TECHNO_TYPE = 140029 -- Technologic JEE
      and a.OBJECT_TYPE in (101,102,105,988,991,137127,142034) -- Constructor, method, JV_INIT, generic method, generic Constructor, annotation method, lambda
    ;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_JavaArtifactInvalidAccess  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_JavaArtifactInvalidAccess <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Java Methods that access a closed resource . <</COMMENT>>*/   
 
  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, a.OBJECT_ID
    from DSSAPP_ARTIFACTS a
    where a.TECHNO_TYPE = 140029 -- Technologic JEE
      and a.OBJECT_TYPE in (101,102,105,988,991,137127,142034) -- Constructor, method, JV_INIT, generic method, generic Constructor, annotation method, lambda
    ;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_JavaClass  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_JavaClass <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Java Class, Java Instanciated Class and Generic Java Class. <</COMMENT>>*/
   
 
  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, a.OBJECT_ID
   from CTT_OBJECT_APPLICATIONS a
      join DSSAPP_MODULES m
         on (m.module_id = a.application_id 
            and m.techno_type = 140029 -- Technologic JEE
				)
      where a.properties = 0
         and a.OBJECT_TYPE in(100, 975, 989) -- Java Class, Java Instanciated Class and Generic Java Class using the Bean
         
    ;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_JavaMethodsAndConstructor (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_JavaMethodsAndConstructor <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Java Methods and Java Constructor. <</COMMENT>>*/   
 
  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, a.OBJECT_ID
    from DSSAPP_ARTIFACTS a 
    
 where a.TECHNO_TYPE  = 140029   -- Technologic JEE 
 and a.OBJECT_TYPE in (101, 102, 988, 991) -- Constructor, Method, Generic Method, Generic ctor
    ;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function SET_PersistentEntityTypes (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_PersistentEntityTypes<</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of JPA and Hibernate entity and properties. <</COMMENT>>*/   
 
  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, c.OBJECT_ID
    from CTT_OBJECT_APPLICATIONS c
    where c.OBJECT_TYPE in ( Select IdTyp from TypCat where IdCatParent in ( 136996, 136995, 140210, 140211) ) -- hibernate/jpa peristent entities

    ;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
