import cast.application


class PatchingExtension(cast.application.ApplicationLevelExtension):
    
    def end_application(self, application):
        """
        Apply the modification
        """
        dialect = application.get_knowledge_base().engine.dialect.name
        """
        'oracle'
        'mssql'
        'postgresql'
        """
        query = ""
        
        
        if dialect == 'postgresql':
            query = """
update ProDep pd1 
set IdProMain = pd2.IdProMain 
from ProDep pd2 
where pd1.IdPro in (select IdKey from Keys where ObjTyp = 141813) and 
      pd1.IdProMain in (select IdKey from Keys where ObjTyp in (select IdTyp from TypCat where IdCatParent = 1000011 and IdTyp != 1000001)) and
      pd1.IdProMain = pd2.IdPro and 
      pd2.IdProMain in (select IdKey from Keys where ObjTyp = 1000001);
      """        
        elif dialect == 'mssql':
            query = """
update ProDep
set IdProMain = pd2.IdProMain 
from ProDep, ProDep pd2
where ProDep.IdPro in (select IdKey from Keys where ObjTyp = 141813) and 
      ProDep.IdProMain in (select IdKey from Keys where ObjTyp in (select IdTyp from TypCat where IdCatParent = 1000011 and IdTyp != 1000001)) and
      ProDep.IdProMain = pd2.IdPro and 
      pd2.IdProMain in (select IdKey from Keys where ObjTyp = 1000001);
      """   
        else: # oracle
            query = """     
update ProDep pd1 
set IdProMain = (select pd2.IdProMain from ProDep pd2 where pd1.IdProMain = pd2.IdPro and pd2.IdProMain in (select IdKey from Keys where ObjTyp = 1000001))
where pd1.IdPro in (select IdKey from Keys where ObjTyp = 141813) and 
      pd1.IdProMain in (select IdKey from Keys where ObjTyp in (select IdTyp from TypCat where IdCatParent = 1000011 and IdTyp != 1000001));
            
            """
        application.sql_tool(query)

