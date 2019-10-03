import logging
import cast.application
from sqlalchemy import select



def create_missing_project_links(application):
    """
    Repair some missing information for dotnet.
    """
    kb = application.kb

    # some categories
    technical = kb.metamodel.get_category(name='CAST_TechnicalProject')
    vb = kb.metamodel.get_category(name='CAST_DotNet_VB')
    cs = kb.metamodel.get_category(name='CAST_DotNet_CSharp')
    
    # 1. get technological projects
    techno_projects = []
    vb_projects = []    
    cs_projects = []    
    
    for p in application.projects:
        
        if p.type.inherit_from(technical):
            techno_projects.append(p.id)
        if p.type.inherit_from(vb):
            vb_projects.append(p.id)
        if p.type.inherit_from(cs):
            cs_projects.append(p.id)


    # 2. get the plugin types for dotnet
    plugin_types = []
    
    dotnet = kb.metamodel.get_category(name='CAST_DotNet_DotNet')
    
    for t in kb.metamodel.get_category(name='CAST_PluginObject').get_sub_types():
        if t.inherit_from(dotnet):
            plugin_types.append(t.id)
    
    if not plugin_types:
        return
    
    # 3. get parentships for those objects
#     query = """
#     select IdKey, IdParent from KeyPar where IdKey in (select IdKey from Keys where ObjTyp in (%s))
#     """ % ', '.join(map(repr, plugin_types))
    
    query = select([kb.KeyPar.c.idkey, 
                    kb.KeyPar.c.idparent]).where(kb.KeyPar.c.idkey.in_(select([kb.Keys.c.idkey]).where(kb.Keys.c.objtyp.in_(plugin_types))))
    
    
    parentship = {}
    for line in kb.engine.execute(query):
        o = line[0]
        parent = line[1]
        parentship[o] = parent
    
        
    # search the objects without parent : 
    # here it can be the xaml file
    roots = []
    for parent in set(parentship.values()):
        
        if parent not in parentship:
            roots.append(parent)

    # search internal/external
    internal = {}
    
#     query = """
#     select IdObj, Prop from ObjPro where IdObj in (select IdKey from Keys where ObjTyp in (%s))
#     """ % ', '.join(map(repr, plugin_types))
    
    query = select([kb.ObjPro.c.idobj, 
                    kb.ObjPro.c.prop]).where(kb.ObjPro.c.idobj.in_(select([kb.Keys.c.idkey]).where(kb.Keys.c.objtyp.in_(plugin_types))))
    
    for line in kb.engine.execute(query):
        o = line[0]
        prop = line[1]
        internal[o] = prop
    
    if not roots or not techno_projects:
        return
    
    # search technological projects for those roots
#     query = """
#     select IdObj, IdPro from ObjPro where IdObj in (%s) and IdPro in (%s)
#     """ % (', '.join(map(repr, roots)), ', '.join(map(repr, techno_projects)))
    
    query = select([kb.ObjPro.c.idobj, 
                    kb.ObjPro.c.idpro]).where(kb.ObjPro.c.idobj.in_(roots)).where(kb.ObjPro.c.idpro.in_(techno_projects))
    
    project_of_root = {}
    for line in kb.engine.execute(query):
        
        o = line[0]
        project = line[1]
    
        project_of_root[o] = project
    
    projects = cs_projects + vb_projects
    if not projects:
        return
    
    # search technological project associated with csproj
    # we search in ProDep for c# project -- C# technology project 
    # and same for vb 
    query = """
    select IdPro, IdProMain from ProDep where IdPro in (%s) and IdProMain in (%s)
    """ % (', '.join(map(repr, techno_projects)), ', '.join(map(repr, projects)))
    
    cursor = kb.create_cursor()
    cursor.execute(query)

    for line in cursor:
        
        techno_project = line[0]
        project = line[1]
        
        # and 
        if techno_project in vb_projects and project in vb_projects:
            project_of_root[project] = techno_project
        
        if techno_project in cs_projects and project in cs_projects:
            project_of_root[project] = techno_project
    
    
    def get_tech_project(o):
        
        if o in parentship:
            return get_tech_project(parentship[o])
        else:
            try:
                return project_of_root[o]
            except:
                
                logging.debug('missing tech project for : %s', str(o))
                

    # get the already present links 
    already_present = []

#     query = """
#     select IdObj, IdPro from ObjPro where IdObj in (select IdKey from Keys where ObjTyp in (%s)) and IdPro in (%s)
#     """ % (', '.join(map(repr, plugin_types)), ', '.join(map(repr, techno_projects)))
    
    query = select([kb.ObjPro.c.idobj, 
                    kb.ObjPro.c.idpro]).where(kb.ObjPro.c.idobj.in_(select([kb.Keys.c.idkey])
                                                                    .where(kb.Keys.c.objtyp.in_(plugin_types)))).where(kb.ObjPro.c.idpro.in_(techno_projects))
    
    for line in kb.engine.execute(query):
        o = line[0]
        project = line[1]
        already_present.append((o, project))


    # prepare insertion to perform in project    
    in_objpro = []
    
    for o in parentship:
        
        tech_project = get_tech_project(o)
        
        # internal == 0 means internal
        if o and tech_project and internal[o] == 0 and not (o, tech_project) in already_present: 
            in_objpro.append([o, tech_project, internal[o]])
            
        
    # insert...
    ins = kb.ObjPro.insert()
    cursor = kb.create_cursor()
    raw_connection = kb.raw_connection
    
    try:  
        cursor.executemany(str(ins.compile()), in_objpro)
        raw_connection.commit()
    except:
        raw_connection.rollback()


class PatchingExtension(cast.application.ApplicationLevelExtension):
    
    def end_application(self, application):
        """
        Apply the modification
        """
        create_missing_project_links(application)
