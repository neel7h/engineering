CREATE OR REPLACE FUNCTION  SET_AJAX_1020300(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set JS source code artifacts containing jQuery code*/
 
  insert into SET_Contents (SetId, ObjectId)
  Select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
  where o.OBJECT_TYPE in (1020026, 1020030)     -- CAST_HTML5_JavaScript_SourceCode, CAST_HTML5_JavaScript_SourceCode_Fragment
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020300 and i.InfSubTyp = 1 and i.InfVal = 1);
	 commit;
	
	return ERRORCODE;

End  SET_AJAX_1020300; 
/
CREATE OR REPLACE FUNCTION  SET_JQUERY_1020301(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set JS source code artifacts containing jQuery code*/
 
  insert into SET_Contents (SetId, ObjectId)
  Select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
  where o.OBJECT_TYPE in (1020026, 1020030)     -- CAST_HTML5_JavaScript_SourceCode, CAST_HTML5_JavaScript_SourceCode_Fragment
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020300 and i.InfSubTyp = 3 and i.InfVal = 1);
	 commit;
	
	return ERRORCODE;

End  SET_JQUERY_1020301; 
/
CREATE OR REPLACE FUNCTION  SET_DIALOG_1020302(I_SET_ID int)
Return INT
Is
	ERRORCODE	INT := 0;
Begin
/* Set JS source code artifacts containing dialog code*/
 
  insert into SET_Contents (SetId, ObjectId)
  Select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o 
  where o.OBJECT_TYPE in (1020026, 1020030)     -- CAST_HTML5_JavaScript_SourceCode, CAST_HTML5_JavaScript_SourceCode_Fragment
  and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1020300 and i.InfSubTyp = 16 and i.InfVal = 1);
	 commit;
	
	return ERRORCODE;

End  SET_DIALOG_1020302; 
/
