create or replace function SET_SS_1040000(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
begin


  insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (98); --Java Project
     commit;
    
    return ERRORCODE;

End  SET_SS_1040000;
/

create or replace function SET_SS_1040001(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
begin


 insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (900, 989, 990, 100, 104); --Java Class, Interface, Generic Class
     commit;
    
    return ERRORCODE;

End  SET_SS_1040001;
/

create or replace function SET_SS_1040002(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
begin


 insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (281, 98)  --Java Project and JSP Project
    and exists(select 1 from ObjInf i
        where i.IdObj = o.OBJECT_ID and i.InfTyp = 1040017 and i.InfSubTyp = 16 and i.InfVal = 1);

     commit;
    
    return ERRORCODE;

End  SET_SS_1040002;
/


create or replace function SET_SS_1040003(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
begin


 insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (142302);  --XML File
  

     commit;
    
    return ERRORCODE;

End  SET_SS_1040003;
/

create or replace function SET_SS_1040004(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
begin


 insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (101, 102, 988, 991); --Java Method
     commit;
    
    return ERRORCODE;

End  SET_SS_1040004;
/


create or replace function SET_SS_1040005(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
begin


 insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (365); --Properties File
     commit;
    
    return ERRORCODE;

End  SET_SS_1040005;
/


create or replace function SET_SS_1040006(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
begin
 

insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (142302, 101, 102, 988, 991);  --XML File and Java Methods
     commit;
    
    return ERRORCODE;

End  SET_SS_1040006;
/

create or replace function SET_SS_1040007(I_SET_ID int)
Return INT
Is
    ERRORCODE   INT := 0;
begin


insert into SET_Contents (SetId, ObjectId)
  select distinct I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o
    where o.TECHNO_TYPE      = 140029 
    and o.OBJECT_TYPE in (900, 989, 990, 100, 104, 101, 102, 988, 991);  --Java Class and Java Methods
     commit;
    
    return ERRORCODE;

End  SET_SS_1040007;
/


