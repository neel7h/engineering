create or replace function  SET_1020700  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE in (1020007, 1020180, 1020183)	-- CAST_HTML5_JavaScript_Function, CAST_HTML5_JavaScript_Method, CAST_HTML5_JavaScript_Constructor
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020050 and infsubtyp = 0);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_EXPRESS_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 4);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_HTTP_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 10);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_HTTPSERVER_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 14);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_MARKED_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 4)
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 16);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_EXPRESS_SESSION  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_Artifact using express-session*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 18);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_FS_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_Artifact using fs*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 21);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_CREATE_HASH_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_Artifact using fs*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 26);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_SOURCE_CODE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NODEJS_SOURCE_CODE*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020050 and infsubtyp = 0);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_NODE_CURL_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_SourceCode using node-curl*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 31);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_TLS_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_SourceCode using tls*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 34);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_HTTP2_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_SourceCode using http2*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020051 and infsubtyp = 37);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_LOOP_DATASERVICE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_DataService using Loop*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020101 and infsubtyp = 2);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/
create or replace function  SET_NODEJS_PATH_SOURCE  (I_SET_ID int)
returns int
as
$body$
declare
ERRORCODE	INT := 0;
begin
/* Set name SET_NodeJS_SourceCode using path*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select idobj from ObjInf where idobj = o.object_id
        and inftyp = 1020101 and infsubtyp = 8);
Return ERRORCODE;
END;
$body$
LANGUAGE plpgsql
/