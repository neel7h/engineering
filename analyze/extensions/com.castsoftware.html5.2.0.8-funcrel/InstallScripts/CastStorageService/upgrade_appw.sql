-- upgrade to 1.9.2-funcrel (should be removed when all clients will be above 1.9.2-funcrel)
update Objects 
set IdNam = REPLACE(IdNam, SUBSTRING(IdNam, STRPOS(IdNam, 'CAST_HTML5_JavaScript_SourceCode_Fragment_'), STRPOS(SUBSTRING(IdNam, STRPOS(IdNam, 'CAST_HTML5_JavaScript_SourceCode_Fragment_')), '.')), 'CAST_HTML5_JavaScript_SourceCode_Fragment.'),
    IdShortNam = REPLACE(IdShortNam, SUBSTRING(IdShortNam, STRPOS(IdShortNam, 'CAST_HTML5_JavaScript_SourceCode_Fragment_'), STRPOS(SUBSTRING(IdShortNam, STRPOS(IdShortNam, 'CAST_HTML5_JavaScript_SourceCode_Fragment_')), '.')), 'CAST_HTML5_JavaScript_SourceCode_Fragment.')
where ObjTyp in ( select IdTyp from TypCat where IdCatParent = 1020004 )	-- HTML5
and IdNam like '%CAST\_HTML5\_JavaScript_SourceCode\_Fragment\_%'
and IdShortNam like '%CAST\_HTML5\_JavaScript_SourceCode\_Fragment\_%'
/
