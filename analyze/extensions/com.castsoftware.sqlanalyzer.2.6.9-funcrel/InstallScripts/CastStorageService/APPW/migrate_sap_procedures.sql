-- upgrade ObjTyp 142309 becomes 1020299
update Objects set ObjTyp = 1020299 where ObjTyp = 142309
/
update Keys set ObjTyp = 1020299 where ObjTyp = 142309
/