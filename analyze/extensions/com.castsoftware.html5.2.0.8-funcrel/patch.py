import cast.application


def patch8013(application, ua_project_id, ua_techno_id):
    """
    Patch for SCRAIP-8013.
    do not try that at home...
    """
    dialect = application.get_knowledge_base().engine.dialect.name
    """
    'oracle'
    'mssql'
    'postgresql'
    """

    if dialect != 'oracle':
                   
        application.sql_tool("""
        insert into ObjPro
        select IdObj, IdPro, 0 from (
        select IdObj, dep.IdPro from ObjPro p, (select IdProMain, IdPro from ProDep where IdPro in (select IdKey from Keys where ObjTyp = """ + str(ua_project_id) + """)) dep
                           where p.IdPro = IdProMain and p.IdObj != IdProMain and IdObj in (select IdKey from Keys where ObjTyp in (select IdTyp from TypCat where IdCatParent = """ + str(ua_techno_id) + """))
        except
        select IdObj, IdPro from ObjPro where IdPro in (select IdPro from ProDep where IdPro in (select IdKey from Keys where ObjTyp = """ + str(ua_project_id) + """))) temp
        ;
        """)
    else: # 'oracle'
        application.sql_tool("""
        insert into ObjPro
        ( select IdObj, IdPro, 0 from (
        select IdObj, dep.IdPro from ObjPro p, (select IdProMain, IdPro from ProDep where IdPro in (select IdKey from Keys where ObjTyp = """ + str(ua_project_id) + """)) dep
                           where p.IdPro = IdProMain and p.IdObj != IdProMain and IdObj in (select IdKey from Keys where ObjTyp in (select IdTyp from TypCat where IdCatParent = """ + str(ua_techno_id) + """))
        minus
        select IdObj, IdPro from ObjPro where IdPro in (select IdPro from ProDep where IdPro in (select IdKey from Keys where ObjTyp = """ + str(ua_project_id) + """))) temp
        );
        """)       

class PatchingExtension(cast.application.ApplicationLevelExtension):
    def end_application(self, application):
        patch8013(application, 1020005, 1020004)
