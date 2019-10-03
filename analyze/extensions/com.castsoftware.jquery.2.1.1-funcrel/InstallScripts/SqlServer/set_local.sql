Create Proc SET_AJAX_1020300  (@I_SET_ID int)
As
Begin
/* Set name SET_JQuery_Artifact*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
  where o.OBJECT_TYPE in (1020026, 1020030)     -- CAST_HTML5_JavaScript_SourceCode, CAST_HTML5_JavaScript_SourceCode_Fragment
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020300 and i.InfSubTyp = 1 and i.InfVal = 1);
End
go
Create Proc SET_JQUERY_1020301  (@I_SET_ID int)
As
Begin
/* Set JS source code artifacts containing jQuery code */
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
  where o.OBJECT_TYPE in (1020026, 1020030)     -- CAST_HTML5_JavaScript_SourceCode, CAST_HTML5_JavaScript_SourceCode_Fragment
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020300 and i.InfSubTyp = 3 and i.InfVal = 1);
End
go
Create Proc SET_DIALOG_1020302  (@I_SET_ID int)
As
Begin
/* Set name SET_JQuery_Artifact using dialog*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
  where o.OBJECT_TYPE in (1020026, 1020030)     -- CAST_HTML5_JavaScript_SourceCode, CAST_HTML5_JavaScript_SourceCode_Fragment
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020300 and i.InfSubTyp = 16 and i.InfVal = 1);
End
go
