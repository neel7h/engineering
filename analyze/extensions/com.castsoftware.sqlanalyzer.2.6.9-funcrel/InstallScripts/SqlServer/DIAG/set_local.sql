create procedure SET_SQLScript_1101000  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101000

Procedures, functions, triggers, views and events
*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1101009, 1101012, 1101013, 1101014, 1101024); 
end
go


create procedure SET_SQLScript_1101001  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101001

Procedures, function, trigger, view when there are XXL information

Proc, function, trigger, view and events
that have a parent schema or grand parent schema (case of proc in a package) with property 1101000, 2

Schema stores the xxl treshold in property 1101000, 2 (only when XXL info is set)

*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
    from DSSAPP_MODULES sc, CTT_OBJECT_APPLICATIONS o 
    where o.APPLICATION_ID  = sc.MODULE_ID
	and o.PROPERTIES = 0 -- Application's Object
    and (o.OBJECT_TYPE in (1101009, 1101012, 1101013, 1101014, 1101024) 
   and o.OBJECT_ID in (
          -- objects with direct parent having property ...
          select pa.OBJECT_ID from CTT_OBJECT_PARENTS pa join ObjInf inf on pa.PARENT_ID = inf.IdObj where inf.InfTyp = 1101000 and inf.InfSubTyp = 2
		  union
		  -- objects with grand parent having property ...
		  select pa2.OBJECT_ID from CTT_OBJECT_PARENTS pa2 
		             where pa2.PARENT_ID in 
		             (select pa.OBJECT_ID from CTT_OBJECT_PARENTS pa join ObjInf inf on pa.PARENT_ID = inf.IdObj where inf.InfTyp = 1101000 and inf.InfSubTyp = 2))
		     )
     	or (
     		exists(select 1 from ObjInf inf where inf.InfTyp = 1101000 and inf.InfSubTyp = 21 and inf.IdObj = o.OBJECT_ID) -- client code
     		and exists(select 1 from Acc a, Keys k , ObjInf inf where a.IdCle = k.IdKey and k.IdKey = inf.IdObj and inf.InfTyp = 1101000 and inf.InfSubTyp = 2) -- with links through SQL analyzer XXL objects 
     	);


end
go
create procedure SET_SQLScript_1101013  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101013

Procedures, functions, triggers and events
*/
  
  insert into SET_Contents (SetId, ObjectId)
  Select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_ARTIFACTS o where o.OBJECT_TYPE in (1101009, 1101012, 1101014, 1101024); 
end
go
create procedure SET_SQLScript_1101014  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101014

Only tables

*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_MODULES sc, CTT_OBJECT_APPLICATIONS o 
  where o.APPLICATION_ID  = sc.MODULE_ID
	and o.PROPERTIES = 0 -- Application's Object 
  	and o.OBJECT_TYPE = 1101006; 
end
go
create procedure SET_SQLScript_1101002  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101002

Procedures, functions, triggers, views and events and client objects with SQL code
*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_MODULES sc, CTT_OBJECT_APPLICATIONS o 
  where o.APPLICATION_ID  = sc.MODULE_ID
	and o.PROPERTIES = 0 -- Application's Object
  	and (o.OBJECT_TYPE in (1101009, 1101012, 1101013, 1101014, 1101024)
  or exists(select 1 from ObjInf where InfTyp = 1101000 and InfSubTyp = 21 and IdObj = o.OBJECT_ID)
  ); -- Client objects scanned by us 
  
end
go
create procedure SET_SQLScript_1101003  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101003

Procedures, functions, triggers and events and client objects with SQL code
*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_MODULES sc, CTT_OBJECT_APPLICATIONS o 
  where o.APPLICATION_ID  = sc.MODULE_ID
	and o.PROPERTIES = 0 -- Application's Object
  	and (o.OBJECT_TYPE in (1101009, 1101012, 1101014, 1101024)
  or exists(select 1 from ObjInf where InfTyp = 1101000 and InfSubTyp = 21 and IdObj = o.OBJECT_ID)
  ); -- Client objects scanned by us 
  
end
go
create procedure SET_SQLScript_1101036  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101036

Only client objects with SQL code
*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_MODULES sc, CTT_OBJECT_APPLICATIONS o 
  where o.APPLICATION_ID  = sc.MODULE_ID
	and o.PROPERTIES = 0 -- Application's Object
  	and exists(select 1 from ObjInf where InfTyp = 1101000 and InfSubTyp = 21 and IdObj = o.OBJECT_ID); -- Client objects scanned by us 
  
end
go
create procedure SET_SQLScript_1101044  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101044

Only views

*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_MODULES sc, CTT_OBJECT_APPLICATIONS o 
  where o.APPLICATION_ID  = sc.MODULE_ID
	and o.PROPERTIES = 0 -- Application's Object 
  	and o.OBJECT_TYPE = 1101013; 
end
go
create procedure SET_SQLScript_1101046  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101046

Only packages

*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_MODULES sc, CTT_OBJECT_APPLICATIONS o 
  where o.APPLICATION_ID  = sc.MODULE_ID
	and o.PROPERTIES = 0 -- Application's Object 
  	and o.OBJECT_TYPE = 1101015; 
end
go
create procedure SET_SQLScript_1101048  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101048

Only package functions

*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_MODULES sc, CTT_OBJECT_APPLICATIONS o 
  where o.APPLICATION_ID  = sc.MODULE_ID
	and o.PROPERTIES = 0 -- Application's Object 
  	and o.OBJECT_TYPE = 1101012
    and exists (select 1 
             from DIAG_OBJECT_PARENTS p
            where p.OBJECT_ID = o.OBJECT_ID
              and p.PARENT_TYPE = 1101015
				); 
end
go
create procedure SET_SQLScript_1101050  (@I_SET_ID int)
as
begin
/* 
Set name SET_SQLScript_1101050

Only package procedures

*/
  
  insert into SET_Contents (SetId, ObjectId)
  select distinct @I_SET_ID, o.OBJECT_ID
  from DSSAPP_MODULES sc, CTT_OBJECT_APPLICATIONS o 
  where o.APPLICATION_ID  = sc.MODULE_ID
	and o.PROPERTIES = 0 -- Application's Object 
  	and o.OBJECT_TYPE = 1101009
    and exists (select 1 
             from DIAG_OBJECT_PARENTS p
            where p.OBJECT_ID = o.OBJECT_ID
              and p.PARENT_TYPE = 1101015
				); 
end
go