Create Proc SET_1020700  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_Artifact*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE in (1020007, 1020180, 1020183)	-- CAST_HTML5_JavaScript_Function, CAST_HTML5_JavaScript_Method, CAST_HTML5_JavaScript_Constructor
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020050 and InfSubTyp = 0)
End
go
Create Proc SET_NODEJS_EXPRESS_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_Artifact*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 4)
End
go
Create Proc SET_NODEJS_HTTP_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_Artifact*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 10)
End
go
Create Proc SET_NODEJS_HTTPSERVER_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_Artifact*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 14)
End
go
Create Proc SET_NODEJS_MARKED_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_Artifact*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 4)
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 16)
End
go
Create Proc SET_NODEJS_EXPRESS_SESSION  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_Artifact using express-session*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 18)
End
go
Create Proc SET_NODEJS_FS_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_Artifact using fs*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 21)
End
go
Create Proc SET_NODEJS_CREATE_HASH_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_Artifact using fs*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 26)
End
go
Create Proc SET_NODEJS_SOURCE_CODE  (@I_SET_ID int)
As
Begin
/* Set name SET_NODEJS_SOURCE_CODE*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020050 and InfSubTyp = 0)
End
go
Create Proc SET_NODEJS_NODE_CURL_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_SourceCode using node-curl*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 31)
End
go
Create Proc SET_NODEJS_TLS_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_SourceCode using tls*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 34)
End
go
Create Proc SET_NODEJS_HTTP2_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_SourceCode using http2*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020051 and InfSubTyp = 37)
End
go
Create Proc SET_NODEJS_LOOP_DATASERVICE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_DataService using Loop*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE in (1020007, 1020180, 1020183, 1020026)	-- CAST_HTML5_JavaScript_SourceCode, CAST_HTML5_JavaScript_Function, CAST_HTML5_JavaScript_Method, CAST_HTML5_JavaScript_Constructor
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020101 and InfSubTyp = 2)
End
go
Create Proc SET_NODEJS_PATH_SOURCE  (@I_SET_ID int)
As
Begin
/* Set name SET_NodeJS_SourceCode using path*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE = 1020026	-- CAST_HTML5_JavaScript_SourceCode
     and exists( select IdObj from ObjInf where IdObj = o.OBJECT_ID
        and InfTyp = 1020101 and InfSubTyp = 8)
End
go