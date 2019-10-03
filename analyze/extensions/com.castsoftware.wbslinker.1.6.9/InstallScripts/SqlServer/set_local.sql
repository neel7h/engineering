Create Proc SET_RESOURCES  (@I_SET_ID int)
As
Begin
/* Set name SET_WbsLinker_Resources*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
  where o.OBJECT_TYPE in ( select IdTyp from TypCat where IdCatParent = 141964 )	-- CAST_ResourceService

End
go
