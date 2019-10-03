CREATE OR REPLACE FUNCTION install_migration_of_extensions  ()
RETURNS integer AS
$body$
DECLARE
  L_EXE_AMT_P_EXTMIGRGUID varchar(2000);
  L_EXE_LIST_OF_MIGRATIONS varchar(2000);
  L_EXE_AMT_P_EXTMIGRGUID_GETMIGRLEVELS varchar(2000);
  L_EXE_AMT_P_EXTMIGRGUID_RUNMIGR text;
  L_EXE_CACHE_PROCESSID varchar(2000);
BEGIN
  if not exists (
              select 1
              from pg_tables 
              where schemaname = current_schema() 
              and lower(trim(tablename)) = 'ext_listofmigrationfunctions'
            ) then
     L_EXE_LIST_OF_MIGRATIONS := 'create table if not exists EXT_ListOfMigrationFunctions (ExtensionName varchar(255) not null,'|| e'\n' ||
	'FunctionToBeExecuted varchar(255) not null,'|| e'\n' ||
	'CONSTRAINT PK_MIGR_ExtensionName PRIMARY KEY (ExtensionName, FunctionToBeExecuted));';
     EXECUTE L_EXE_LIST_OF_MIGRATIONS;

     L_EXE_AMT_P_EXTMIGRGUID := 'CREATE OR REPLACE FUNCTION AMT_P_EXTMIGRGUID('|| e'\n' ||
		'  IN I_IDSESSION INT'|| e'\n' ||
		')'|| e'\n' ||
		' RETURNS int AS'|| e'\n' ||
		' $' || 'body' || '$ '|| e'\n' ||
		'DECLARE'|| e'\n' ||
		'L_ErrorCode int;'|| e'\n' ||
		'L_EXE RECORD;'|| e'\n' ||
		'BEGIN'|| e'\n' ||
		'  L_ErrorCode := 0;'|| e'\n' ||
		''|| e'\n' ||
		'/* call migration procedures, one by one'|| e'\n' ||
		'*/'|| e'\n' ||
		''|| e'\n' ||
		'perform cast_log(''start AMT_P_EXTMIGRGUID'');'|| e'\n' ||
		''|| e'\n' ||
		'--#@__KB_TIME__1__KB_TIME__@#    '|| e'\n' ||
		'For L_EXE in'|| e'\n' ||
		'	SELECT FunctionToBeExecuted'|| e'\n' ||
		'	from EXT_ListOfMigrationFunctions'|| e'\n' ||
		'	order by ExtensionName'|| e'\n' ||
		'	Loop'|| e'\n' ||
		'		Begin'|| e'\n' ||
		'			EXECUTE FORMAT (''select '' || L_EXE.FunctionToBeExecuted || ''(''||cast(I_IDSESSION as varchar)||'')'' || e''\n'', current_schema());'|| e'\n' ||
		'			Exception'|| e'\n' ||
		'				When Others Then'|| e'\n' ||
		'					perform cast_log(''end AMT_P_EXTMIGRGUID : '' || L_EXE.FunctionToBeExecuted || '' with errors'');'|| e'\n' ||
		'		End;'|| e'\n' ||
		'End Loop;'|| e'\n' ||
		'		'|| e'\n' ||
		'perform cast_log(''end   AMT_P_EXTMIGRGUID'');'|| e'\n' ||
		'--#@__KB_TIME__1__KB_TIME__@#  '|| e'\n' ||  
		'' || e'\n' ||
		'  return L_ERRORCODE; '|| e'\n' ||
		'END;'|| e'\n' ||
		' $' || 'body' || '$ '|| e'\n' ||
		'LANGUAGE ''plpgsql''';
	EXECUTE L_EXE_AMT_P_EXTMIGRGUID;
		
     L_EXE_AMT_P_EXTMIGRGUID_GETMIGRLEVELS := 'CREATE OR REPLACE FUNCTION AMT_P_EXTMIGRGUID_GETMIGRLEVELS(I_IDSESSION integer, I_EXTENSION_ID varchar(50), I_INF_TYPE integer, I_INF_SUB_TYPE integer)'|| e'\n' ||
		'  RETURNS TABLE (migration_levels int) AS'|| e'\n' ||
		' $' || 'func' || '$ '|| e'\n' ||
		'BEGIN'|| e'\n' ||
		''|| e'\n' ||
		'   RETURN QUERY EXECUTE '' '|| e'\n' ||					
		'	select distinct coalesce((select distinct oi.InfVal from ObjInf oi where oi.IdObj =  k.IdKey and oi.InfTyp = $3 and oi.InfSubTyp = $4), 0) as migration_levels'|| e'\n' ||
		'	from Objects k, (select op.IdObj, op.IdPro '|| e'\n' ||
		'					from ObjPro op, ANAATTR atr, AnaPro ap'|| e'\n' ||
		'					where atr.SESSION_ID = $1'|| e'\n' ||
		'					and atr.ATTRNAM = ''''IDUSRPRO'''' '|| e'\n' ||
		'					and atr.SESSION_ID = ap.IdJob'|| e'\n' ||
		'					and op.IdPro = ap.IdPro'|| e'\n' ||
		'					and op.IdPro in (select IdKey from Keys where ObjTyp in (141813, 141887)'|| e'\n' ||
		'									)'|| e'\n' ||
		'					) p'|| e'\n' ||
		'	 where k.IdKey = p.IdObj'|| e'\n' ||
		'	  and exists(select 1 from ObjDsc where IdObj = p.IdPro and InfSubTyp=5 and InfVal = $2)'' '|| e'\n' ||
		'   USING  I_IDSESSION, I_EXTENSION_ID, I_INF_TYPE, I_INF_SUB_TYPE;'|| e'\n' ||
		''|| e'\n' ||
		'END;'|| e'\n' ||
				' $' || 'func' || '$ '|| e'\n' ||
		'LANGUAGE ''plpgsql''';

     
     EXECUTE L_EXE_AMT_P_EXTMIGRGUID_GETMIGRLEVELS;


     L_EXE_AMT_P_EXTMIGRGUID_RUNMIGR := 'CREATE OR REPLACE FUNCTION AMT_P_EXTMIGRGUID_RUNMIGR'|| e'\n' ||
		'('|| e'\n' ||
		'  IN I_IDSESSION INT,'|| e'\n' ||
		'  IN I_PROPERTY_ID INT'|| e'\n' ||
		')'|| e'\n' ||
		' RETURNS int AS'|| e'\n' ||
		' $' || 'body' || '$ '|| e'\n' ||
		'DECLARE'|| e'\n' ||
		'  L_ErrorCode int;'|| e'\n' ||
		'  L_CharBlock int:=0;  '|| e'\n' ||
		'  L_RowCount int; '|| e'\n' ||
		'  L_Extension_Id varchar(50);'|| e'\n' ||
		'  L_Extension_Version int;'|| e'\n' ||
		'  L_Extension_Build varchar(50);'|| e'\n' ||
		'BEGIN'|| e'\n' ||
		'  L_ErrorCode := 0;'|| e'\n' ||
		'  L_RowCount  := 0;'|| e'\n' ||
		'  '|| e'\n' ||
		'  perform cast_log(''Start AMT_P_EXTMIGRGUID_RUNMIGR'');'|| e'\n' ||
		'--#@__KB_TIME__1__KB_TIME__@#  '|| e'\n' ||
		''|| e'\n' ||
		'  select droptemporarytable(''TMP_PrevVersionGuid'') into L_ErrorCode;  '|| e'\n' ||
		'  create temporary table TMP_PrevVersionGuid '|| e'\n' ||
		'  ('|| e'\n' ||
		'    OBJECT_ID int not null,'|| e'\n' ||
		'    NAME_ID varchar(1015) not null,'|| e'\n' ||
		'    SHORT_NAME_ID varchar(600) null,'|| e'\n' ||
		'    NEW_NAME_ID varchar(1015) not null,'|| e'\n' ||
		'    NEW_SHORT_NAME_ID varchar(600) null,'|| e'\n' ||
		'    PROPERTY_TYPE_ID int not null, '|| e'\n' ||
		'    MATCHING_ID int null'|| e'\n' ||
		'  );'|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		'                '|| e'\n' ||
		'  /* insert first part of GUID (long&short) exists  */ '|| e'\n' ||
		'  perform cast_log(''AMT_P_EXTMIGRGUID_RUNMIGR : start inserting GUIDs if exists''); '|| e'\n' ||
		'  insert into TMP_PrevVersionGuid (OBJECT_ID, NAME_ID, SHORT_NAME_ID, NEW_NAME_ID, NEW_SHORT_NAME_ID, PROPERTY_TYPE_ID, MATCHING_ID)'|| e'\n' ||
		'  select io.OBJECT_ID, ipn.PROPERTY_CHAR,  null, io.NAME_ID, io.SHORT_NAME_ID, I_PROPERTY_ID, NULL'|| e'\n' ||
		'    from (select ipn.OBJECT_ID, ipn.PROPERTY_CHAR, ipn.PROPERTY_TYPE_ID '|| e'\n' ||
		'            from IN_CHAR_PROPERTIES ipn'|| e'\n' ||
		'           where ipn.SESSION_ID = I_IDSESSION '|| e'\n' ||
		'			 and ipn.CHAR_BLOCK = L_CharBlock'|| e'\n' ||
		'			 and ipn.PROPERTY_TYPE_ID = I_PROPERTY_ID) ipn  '|| e'\n' ||
		'    join (select io.OBJECT_ID, NAME_ID, SHORT_NAME_ID'|| e'\n' ||
		'            from IN_OBJECTS io '|| e'\n' ||
		'           where io.SESSION_ID = I_IDSESSION) io'|| e'\n' ||
		'      on ipn.OBJECT_ID = io.OBJECT_ID'|| e'\n' ||
		'    ;   '|| e'\n' ||
		'    get diagnostics L_RowCount := ROW_COUNT;'|| e'\n' ||
		'    if ( L_RowCount = 0 ) then'|| e'\n' ||
		'		--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		'		perform cast_log(''End AMT_P_EXTMIGRGUID_RUNMIGR there is no GUID to be migrated'');'|| e'\n' ||
		'		select droptemporarytable(''TMP_PrevVersionGuid'') into L_ErrorCode;  '|| e'\n' ||
		'        return 0;'|| e'\n' ||
		'    end if;'|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		'     '|| e'\n' ||
		'  create index TMP_PrevVersionGuid_idx on TMP_PrevVersionGuid(OBJECT_ID);'|| e'\n' ||
		'  create index TMP_PrevVersionGuid_idx2 on TMP_PrevVersionGuid(MATCHING_ID);'|| e'\n' ||
		''|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		'  L_RowCount :=1 ;'|| e'\n' ||
		'  L_CharBlock := L_CharBlock + 1;'|| e'\n' ||
		'  '|| e'\n' ||
		'  while (L_RowCount != 0) loop'|| e'\n' ||
		'    update TMP_PrevVersionGuid '|| e'\n' ||
		'       set NAME_ID = NAME_ID || ipn.PROPERTY_CHAR'|| e'\n' ||
		'      from (select ipn.OBJECT_ID, ipn.PROPERTY_TYPE_ID, ipn.PROPERTY_CHAR  '|| e'\n' ||
		'              from IN_CHAR_PROPERTIES ipn '|| e'\n' ||
		'             where ipn.SESSION_ID = I_IDSESSION'|| e'\n' ||
		'               and ipn.CHAR_BLOCK = L_CharBlock'|| e'\n' ||
		'            ) ipn '|| e'\n' ||
		'     where ipn.OBJECT_ID = TMP_PrevVersionGuid.OBJECT_ID'|| e'\n' ||
		'       and ipn.PROPERTY_TYPE_ID = TMP_PrevVersionGuid.PROPERTY_TYPE_ID;'|| e'\n' ||
		'       '|| e'\n' ||
		'    get diagnostics L_RowCount := ROW_COUNT;'|| e'\n' ||
		'    L_CharBlock := L_CharBlock + 1;        '|| e'\n' || 
		'  end loop;'|| e'\n' ||
		'  '|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		'  update TMP_PrevVersionGuid'|| e'\n' ||
		'    set SHORT_NAME_ID = case when length(NAME_ID) <= 600 then NAME_ID'|| e'\n' ||
		'                             when length(NAME_ID) <= 1000 then right(NAME_ID, 600)'|| e'\n' ||
		'                             else null'|| e'\n' ||
		'                        end'|| e'\n' ||
		'  ;'|| e'\n' ||
		''|| e'\n' ||
		'  L_RowCount:= 1;'|| e'\n' ||
		'  '|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@#   '|| e'\n' ||
		'    perform cast_log(''AMT_P_EXTMIGRGUID_RUNMIGR : start matching GUIDs''); '|| e'\n' ||
		'    update TMP_PrevVersionGuid'|| e'\n' ||
		'       set MATCHING_ID = o.IdKey'|| e'\n' ||
		'      from Objects o '|| e'\n' ||
		'     where TMP_PrevVersionGuid.MATCHING_ID is null'|| e'\n' ||
		'       and TMP_PrevVersionGuid.SHORT_NAME_ID is not null'|| e'\n' ||
		'       and o.IdNam = TMP_PrevVersionGuid.NAME_ID'|| e'\n' ||
		'       and o.IdShortNam = TMP_PrevVersionGuid.SHORT_NAME_ID'|| e'\n' ||
		'    ;'|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		''|| e'\n' ||
		'    update TMP_PrevVersionGuid'|| e'\n' ||
		'       set MATCHING_ID = o.IdKey'|| e'\n' ||
		'      from Objects o '|| e'\n' ||
		'     where TMP_PrevVersionGuid.MATCHING_ID is null'|| e'\n' ||
		'       and TMP_PrevVersionGuid.SHORT_NAME_ID is null'|| e'\n' ||
		'       and o.IdNam = TMP_PrevVersionGuid.NAME_ID'|| e'\n' ||
		'    ;'|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		'  perform cast_log(''AMT_P_EXTMIGRGUID_RUNMIGR : update Objects'');  '|| e'\n' ||
		'  '|| e'\n' ||
		'  update Objects '|| e'\n' ||
		'     set IdNam = t.NEW_NAME_ID,'|| e'\n' ||
		'         IdShortNam = t.NEW_SHORT_NAME_ID'|| e'\n' ||
		'    from TMP_PrevVersionGuid t'|| e'\n' ||
		'   where t.MATCHING_ID = Objects.IdKey'|| e'\n' ||
		'     and t.MATCHING_ID is not null;'|| e'\n' ||
		'  '|| e'\n' ||
		'  get diagnostics L_RowCount := ROW_COUNT;'|| e'\n' ||
		''|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		'  perform UpdateStats (''Objects'', L_RowCount);'|| e'\n' ||
		''|| e'\n' ||
		'   '|| e'\n' ||
		'  /* cleanup properties used for migration */'|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		'  perform cast_log(''AMT_P_EXTMIGRGUID_RUNMIGR : cleanup properties used for migration''); '|| e'\n' ||
		'  create index idx_inchprotyp on IN_CHAR_PROPERTIES (PROPERTY_TYPE_ID);'|| e'\n' ||
		'  delete from IN_CHAR_PROPERTIES '|| e'\n' ||
		'   where IN_CHAR_PROPERTIES.PROPERTY_TYPE_ID = I_PROPERTY_ID;'|| e'\n' ||
		'   '|| e'\n' ||
		'  get diagnostics L_RowCount := ROW_COUNT;'|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@# '|| e'\n' ||
		''|| e'\n' ||
		'  drop index idx_inchprotyp ;'|| e'\n' ||
		'  perform UpdateStats (''IN_CHAR_PROPERTIES'', L_RowCount);'|| e'\n' ||
		''|| e'\n' ||
		'--#@__KB_TIME__2__KB_TIME__@#  '|| e'\n' ||
		'  select droptemporarytable(''TMP_PrevVersionGuid'') into L_ErrorCode;   '|| e'\n' ||
		''|| e'\n' ||
		'  perform cast_log(''End AMT_P_EXTMIGRGUID_RUNMIGR'');'|| e'\n' ||
		'--#@__KB_TIME__1__KB_TIME__@#  '|| e'\n' ||
		'  return L_ErrorCode;'|| e'\n' ||
		'  '|| e'\n' ||
		'END;'|| e'\n' ||
		' $' || 'body' || '$ '|| e'\n' ||
		'LANGUAGE ''plpgsql'' ';
     EXECUTE L_EXE_AMT_P_EXTMIGRGUID_RUNMIGR;
	 
     L_EXE_CACHE_PROCESSID := 'CREATE OR REPLACE FUNCTION CACHE_PROCESSID (I_IDSESSION INT4, I_IDUSRPRO  INT4) RETURNS int AS '|| e'\n' ||
		' $' || 'body' || '$ '|| e'\n' ||
		 'DECLARE '|| e'\n' ||
		 '  L_ERRORCODE int; ' || e'\n' ||
		 ' BEGIN ' || e'\n' ||
		 '  L_ERRORCODE := 0; ' || e'\n' ||
		 ' ' || e'\n' ||
		 '--#@__KB_TIME__1__KB_TIME__@#    ' || e'\n' ||
		 ' ' || e'\n' ||
		 '  perform cast_log (''START CACHE_PROCESSID ''||cast(I_IDSESSION as varchar)||''''||cast(I_IDUSRPRO as varchar) ); '|| e'\n' ||
		 '  '|| e'\n' ||
		 '	perform cast_log(''START AMT_P_INIT''|| cast(I_IDSESSION as varchar)) ; '|| e'\n' ||
		 '  select AMT_P_INIT (I_IDSESSION, I_IDUSRPRO) into L_ERRORCODE; '|| e'\n' ||
		 '  '|| e'\n' ||
		 '	perform cast_log(''END AMT_P_INIT''|| cast(I_IDSESSION as varchar)); '|| e'\n' ||
		 ' --#@__KB_TIME__2__KB_TIME__@#   '|| e'\n' ||
		 ' '|| e'\n' ||
		 '  '|| e'\n' ||
		 '  /* Process migration of GUID before all */ '|| e'\n' ||
		 '	perform cast_log(''START AMT_P_MIGRGUID''|| cast(I_IDSESSION as varchar)) ; '|| e'\n' ||
		 '  '|| e'\n' ||
		 '  select AMT_P_MIGRGUID(I_IDSESSION) into L_ERRORCODE; '|| e'\n' ||
		 '  '|| e'\n' ||
		 '	perform cast_log(''END AMT_P_MIGRGUID''|| cast(I_IDSESSION as varchar)) ; '|| e'\n' ||
		 ' '|| e'\n' ||
		 '	Begin'|| e'\n' ||
		 '		perform cast_log(''START AMT_P_EXTMIGRGUID''|| cast(I_IDSESSION as varchar)) ; '|| e'\n' ||
		 ''|| e'\n' ||
		 '		select AMT_P_EXTMIGRGUID(I_IDSESSION) into L_ERRORCODE; '|| e'\n' ||
		 ''|| e'\n' ||
		 '		perform cast_log(''END AMT_P_EXTMIGRGUID''|| cast(I_IDSESSION as varchar)) ; '|| e'\n' ||
		 '	Exception'|| e'\n' ||
		 '		When Others Then'|| e'\n' ||
		 '			perform cast_log(''END AMT_P_EXTMIGRGUID With errors''|| cast(I_IDSESSION as varchar)) ; '|| e'\n' ||
		 '	End;'|| e'\n' ||
		 '		perform cast_log(''END AMT_P_EXTMIGRGUID''|| cast(I_IDSESSION as varchar)) ; '|| e'\n' ||
		 ' --#@__KB_TIME__2__KB_TIME__@#   '|| e'\n' ||
		 ' '|| e'\n' ||
		 '	perform cast_log(''START AMT_P_SPLIT_IN''|| cast(I_IDSESSION as varchar)) ; '|| e'\n' ||
		 '  select AMT_P_SPLIT_IN (I_IDSESSION) into L_ERRORCODE; '|| e'\n' ||
		 ' '|| e'\n' ||
		 '	perform cast_log(''END AMT_P_SPLIT_IN''|| cast(I_IDSESSION as varchar)) ;  '|| e'\n' ||
		 ' --#@__KB_TIME__2__KB_TIME__@#  ' || e'\n' ||
		 ' '|| e'\n' ||
		 '	perform cast_log(''START AMT_P_BUILD''|| cast(I_IDSESSION as varchar)) ; '|| e'\n' ||
		 '  select AMT_P_BUILD (I_IDSESSION) into L_ERRORCODE; '|| e'\n' ||
		 ' '|| e'\n' ||
		 '	perform cast_log(''END AMT_P_BUILD''|| cast(I_IDSESSION as varchar)) ;  '|| e'\n' ||
		 ' --#@__KB_TIME__1__KB_TIME__@# '|| e'\n' ||
		 '   perform cast_log (''END CACHE_PROCESSID ''||cast(I_IDSESSION as varchar)||'' ''||cast(I_IDUSRPRO as varchar) ); '
		 ' '|| e'\n' ||
		 '  return L_ERRORCODE; '|| e'\n' ||
		 ' '|| e'\n' ||
		 ' END; '|| e'\n' ||
		 ' $' || 'body' || '$ '|| e'\n' ||
		 ' LANGUAGE ''plpgsql'' ';
     EXECUTE L_EXE_CACHE_PROCESSID;
  end if;

return 0;
END;
$body$
LANGUAGE 'plpgsql'
/
select install_migration_of_extensions  ()
/
