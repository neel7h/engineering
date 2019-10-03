CREATE OR REPLACE FUNCTION  SET_1020700(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE in (1020007, 1020180, 1020183)	-- CAST_HTML5_JavaScript_Function, CAST_HTML5_JavaScript_Method, CAST_HTML5_JavaScript_Constructor
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020050 and InfSubtyp = 0);
	 commit;
	
	return ERRORCODE;

End  SET_1020700; 
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_EXPRESS_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 4);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_EXPRESS_SOURCE; 
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_HTTP_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 10);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_HTTP_SOURCE; 
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_HTTPSERVER_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 14);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_HTTPSERVER_SOURCE; 
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_MARKED_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 4)
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 16);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_MARKED_SOURCE; 
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_EXPRESS_SESSION(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact using express-session*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 18);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_EXPRESS_SESSION; 
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_FS_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact using fs*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 21);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_FS_SOURCE;
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_CREATE_HASH_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact using fs*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 26);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_CREATE_HASH_SOURCE;
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_SOURCE_CODE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NODEJS_SOURCE_CODE*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020050 and InfSubtyp = 0);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_SOURCE_CODE; 
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_NODE_CURL_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact using fs*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 31);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_NODE_CURL_SOURCE;
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_TLS_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact using tls*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 34);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_TLS_SOURCE;
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_HTTP2_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact using http2*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubtyp = 37);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_HTTP2_SOURCE;
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_LOOP_DATASERVICE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_DataService using Loop*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)	-- CAST_HTML5_JavaScript_SourceCode, CAST_HTML5_JavaScript_Function, CAST_HTML5_JavaScript_Method, CAST_HTML5_JavaScript_Constructor
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020101 and InfSubtyp = 2);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_LOOP_DATASERVICE;
/
/
CREATE OR REPLACE FUNCTION  SET_NODEJS_PATH_SOURCE(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set name SET_NodeJS_Artifact using path*/
  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020101 and InfSubtyp = 8);
	 commit;
	
	return ERRORCODE;

End  SET_NODEJS_PATH_SOURCE;
/
