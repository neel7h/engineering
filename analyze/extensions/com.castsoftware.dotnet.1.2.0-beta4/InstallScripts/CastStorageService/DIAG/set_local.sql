create or replace function  SET_DotNet_PInvoke_Method (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_DotNet_PInvoke_Method <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Dotnet Methods that use Platform Invoke Services. <</COMMENT>>*/

  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, a.OBJECT_ID
    from DSSAPP_ARTIFACTS a  
join ObjInf o on o.IdObj = a.OBJECT_ID   
    
and a.TECHNO_TYPE 	in (138383, 138385) -- DotNet C# and VB
and o.InfTyp = 1027000 and o.InfSubTyp = 2 and o.InfVal = 1;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_DotNet_OverlappedIO_Method (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_DotNet_OverlappedIO_Method <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Dotnet Methods that use Overlapped IO. <</COMMENT>>*/

  insert into SET_Contents 
        (SetId, ObjectId)
  select distinct I_SET_ID, a.OBJECT_ID
    from DSSAPP_ARTIFACTS a  
join ObjInf o on o.IdObj = a.OBJECT_ID   
    
and a.TECHNO_TYPE 	in (138383) -- DotNet C#
and o.InfTyp = 1027000 and o.InfSubTyp = 3 and o.InfVal = 1;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/


create or replace function  SET_DotNet_UsesSystemXml (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_DotNet_UsesSystemXml <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Dotnet Methods and classes that use System.Xml Namespace. <</COMMENT>>*/

  insert into SET_Contents (SetId, ObjectId)
	select distinct I_SET_ID, a.OBJECT_ID from (
		select OBJECT_ID, TECHNO_TYPE from DSSAPP_ARTIFACTS
		union 
		select  OBJECT_ID, TECHNO_TYPE from DSSAPP_CLASSES) a  
	join ObjInf o on o.IdObj = a.OBJECT_ID   
	and a.TECHNO_TYPE 	in (138383, 138385) -- DotNet C# and VB
	and o.InfTyp = 1027000 and o.InfSubTyp = 5 and o.InfVal = 1; -- CAST_DotNet_Method_Uses_SystemXml.isUsingSystemXml
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_DotNet_Impersonate_Method (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_DotNet_Impersonate_Method <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Dotnet Methods that use Impersonation. <</COMMENT>>*/

  insert into SET_Contents (SetId, ObjectId)
	select distinct I_SET_ID, a.OBJECT_ID
	from DSSAPP_ARTIFACTS a  
	join ObjInf o on o.IdObj = a.OBJECT_ID
		and a.TECHNO_TYPE 	in (138383, 138385) -- DotNet C#, VB
		and o.InfTyp = 1027000 and o.InfSubTyp = 7 and o.InfVal = 1;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_DotNet_Encryption_Method (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_DotNet_Encryption_Method <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Dotnet Methods that use CryptoEncryption. <</COMMENT>>*/

  insert into SET_Contents (SetId, ObjectId)
	select distinct I_SET_ID, a.OBJECT_ID
	from DSSAPP_ARTIFACTS a  
	join ObjInf o on o.IdObj = a.OBJECT_ID
		and a.TECHNO_TYPE 	in (138383, 138385) -- DotNet C#, VB
		and o.InfTyp = 1027000 and o.InfSubTyp = 9 and o.InfVal = 1;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_DotNet_HttpSessionAttr (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_DotNet_HttpSessionAttr <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Dotnet Methods that set attributes on HttpSessionState. <</COMMENT>>*/

  insert into SET_Contents (SetId, ObjectId)
	select distinct I_SET_ID, a.OBJECT_ID
	from DSSAPP_ARTIFACTS a  
	join ObjInf o on o.IdObj = a.OBJECT_ID
		and a.TECHNO_TYPE 	in (138383, 138385) -- DotNet C#, VB
		and o.InfTyp = 1027000 and o.InfSubTyp = 11 and o.InfVal = 1;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/

create or replace function  SET_DotNet_UtilityClass (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/*<<NAME>>SET_DotNet_UtilityClass <</NAME>>*/
/*<<COMMENT>> Template name   = OBJSET. <</COMMENT>>*/
/*<<COMMENT>> Definition      =  Scope of Dotnet Non-Static Classes that only have static members. <</COMMENT>>*/

  insert into SET_Contents (SetId, ObjectId)
	select distinct I_SET_ID, a.OBJECT_ID
	from DSSAPP_CLASSES a  
	join ObjInf o on o.IdObj = a.OBJECT_ID
		and a.TECHNO_TYPE 	in (138383, 138385) -- DotNet C#, VB
		and o.InfTyp = 1027001 and o.InfSubTyp = 1 and o.InfVal = 1;
	
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
