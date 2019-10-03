CREATE OR REPLACE FUNCTION DIA_SCOPE_JVOBJECTS (
I_METRIC_ID INT
  
)
returns int as
$body$
declare
	ERRORCODE	INT := 0;
Begin
--<<NAME>>DIA_SCOPE_JVOBJECTS<</NAME>>
--<<COMMENT>> Template name   = EXECSUBGEN. <</COMMENT>>
--<<COMMENT>> Diagnostic name = %METRIC_NAME%. <</COMMENT>>
--<<COMMENT>> Definition      = Generate the scope of all java ( %_ALL_JAVA_OBJECTS_% ) + Jsp Pages containing Java Code . <</COMMENT>>
--<<COMMENT>> Action          = . <</COMMENT>>
--<<COMMENT>> Value           = . <</COMMENT>>

	
  
	

		select DIA_REG_WORKTABLE ('DIA_SCOPE_JVOBJECTS', 'DIA_SC_JVOBJECTS') into ERRORCODE ;
		if ( ERRORCODE	!= 0 ) then return 0; end if;
       
		
/*
====================================================
All Java artifacts, which are also Java ALL 
====================================================
101  Java Constructor 
991  Generic Java Constructor 
978  Java Instantiated Constructor  
102  Java Method 
988  Generic Java Method 
977  Java Instantiated Method 
104  Java Interface 
990  Generic Java Interface 
976  Java Instantiated Interface 
105  Java Initializer 
142034 Java Lambda Expression
====================================================
      All Java Objects which are not artifacts
====================================================
100  Java Class 
989  Generic Java Class 
   this will be integrated later : 975  Java Instantiated Class     
900  Java Enum 
*/
insert into DIA_SC_JVOBJECTS
      ( APPLICATION_ID, OBJECT_ID , IS_JAVALL, IS_JAVART) 
select T1.APPLICATION_ID , T1.OBJECT_ID, 1, CASE WHEN T1.OBJECT_TYPE in ( 100,989,900)   THEN 0 ELSE 1 END
  from CTT_OBJECT_APPLICATIONS T1 
                          join DSSAPP_MODULES SC on SC.MODULE_ID = T1.APPLICATION_ID
                          join CDT_OBJECTS TN on T1.OBJECT_ID = TN.OBJECT_ID
where SC.TECHNO_TYPE  = 140029 /* JEE Module */
  and  ( T1.OBJECT_TYPE in ( 100,989,900, 101,991,978,102,988,977, 104,990,105,142034) 
         or 
	    ( T1.OBJECT_TYPE = 103 and  TN.OBJECT_NAME != 'serialVersionUID') -- see if 103  should be here or down there JAVALL
	   )
  and T1.PROPERTIES = 0
 ;
   
/*
976  Java Instantiated Interface 
only those from the application
*/
insert into DIA_SC_JVOBJECTS
      ( APPLICATION_ID, OBJECT_ID , IS_JAVALL, IS_JAVART) 
select distinct T1.APPLICATION_ID , T1.OBJECT_ID, 1, 1   
  from CTT_OBJECT_APPLICATIONS T1 
                        join DSSAPP_MODULES SC on SC.MODULE_ID = T1.APPLICATION_ID
where SC.TECHNO_TYPE  = 140029 /* JEE Module */
  and T1.OBJECT_TYPE  = 976  --   Java Instantiated Interface 
  and T1.PROPERTIES = 0  
   /* where its parents is class or interface internal to the application scope*/
  and exists ( select 1 
                 from CTT_OBJECT_PARENTS P 
                                    join CTT_OBJECT_APPLICATIONS PA on PA.OBJECT_ID = P.PARENT_ID   
				                                                    and PA.PROPERTIES  = 0  
                 where P.PARENT_TYPE in (989,990) /*  Generic Java Class ,  Generic Java Interface */
                   and PA.APPLICATION_ID = T1.APPLICATION_ID
				           and P.OBJECT_ID = T1.OBJECT_ID 
			  )
 ;
 
/* all other artifacts */
insert into DIA_SC_JVOBJECTS
      ( APPLICATION_ID, OBJECT_ID , IS_JAVALL, IS_JAVART) 
select T1.APPLICATION_ID , T1.OBJECT_ID, 1, 1
  from DSSAPP_ARTIFACTS T1 
                   join ObjInf o on  o.IdObj = T1.OBJECT_ID
where T1.TECHNO_TYPE  = 140029 /* JEE Module */
  and o.InfTyp = 11002 and o.InfSubTyp = 67   -- CONTAINS JAVA CODE
  and not exists ( select 1 
                     from DIA_SC_JVOBJECTS jv 
					where jv.OBJECT_ID = T1.OBJECT_ID 
					  and jv.APPLICATION_ID = T1.APPLICATION_ID)
 ;
 


	  
   Return ERRORCODE;
END;
$body$
language plpgsql
/

CREATE OR REPLACE FUNCTION DIAG_SCOPE_JAVABEST023 (
	I_SNAPSHOT_ID INT,		-- the metric snapshot id
	I_METRIC_PARENT_ID INT,	-- the metric parent id
	I_METRIC_ID INT,			-- the metric id
	I_METRIC_CHILD_ID INT
)
returns int as
$body$
declare
	ERRORCODE	INT := 0;
Begin
--<<NAME>>DIAG_SCOPE_JAVABEST023<</NAME>>
--<<COMMENT>> Template name   = AVOIDUSINGOBJNAME. <</COMMENT>>

    
 ERRORCODE :=   DIA_SCOPE_JVOBJECTS  (I_METRIC_ID) ;

	
	insert into DSS_METRIC_SCOPES 
		(OBJECT_ID, METRIC_PARENT_ID, METRIC_ID, OBJECT_PARENT_ID, SNAPSHOT_ID, METRIC_NUM_VALUE, METRIC_CHAR_VALUE, METRIC_OBJECT_ID, COMPUTE_VALUE)
	select distinct T1.OBJECT_ID, I_METRIC_ID, I_METRIC_CHILD_ID, T1.APPLICATION_ID, I_SNAPSHOT_ID, 0, Null, 0, 0
	  from DIA_SC_JVOBJECTS T1  
		             join DIAG_CTV_LINKS_SIMPLE LI on LI.CALLER_ID = T1.OBJECT_ID
					 join CDT_OBJECTS T2 on T2.OBJECT_ID = LI.CALLED_ID 
					  
	where not exists ( select 1 
			             from DSS_OBJECT_EXCEPTIONS E
			            where E.METRIC_ID		= I_METRIC_ID 
				          and E.OBJECT_ID	= T1.OBJECT_ID
		              )
	 and T2.OBJECT_FULLNAME = 'java.io.File'
	 
and T1.IS_JAVALL = 1

	 
	;
	
	  
	 
Return ERRORCODE;
END;
$body$
language plpgsql
/
