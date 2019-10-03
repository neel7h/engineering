import cast_upgrade_1_6_1 # @UnusedImport
from cast.application import ApplicationLevelExtension
from cast.application import select
from cast.application.internal.reflect import reflect_table
from sqlalchemy import bindparam, and_
from collections import defaultdict 
import logging
import traceback


def get_cpp_guid_level(application):
    """
    Get the C++ guid level for an application
    """
    
    kb = application.get_knowledge_base()
    
    objinf = reflect_table('ObjInf', kb.metadata, kb.engine)
    query = select([objinf.c.infval]).where(objinf.c.idobj == application.id).where(objinf.c.inftyp == 13080).where(objinf.c.infsubtyp == 0)
    
    for line in kb._execute_sqlalchemyquery(query):
        return line[0]

    # default 
    return 0

def set_cpp_guid_level(application, level):
    """
    Update the C++ guid level for an application
    """
    kb = application.get_knowledge_base()
    
    objinf = reflect_table('ObjInf', kb.metadata, kb.engine)
    
    query = select([objinf.c.infval]).where(objinf.c.idobj == application.id).where(objinf.c.inftyp == 13080).where(objinf.c.infsubtyp == 0)
    
    for _ in kb._execute_sqlalchemyquery(query):
        
        # exists so update
        ins = objinf.update().where(objinf.c.idobj == application.id).where(objinf.c.inftyp == 13080).where(objinf.c.infsubtyp == 0).values(infval=level)
        kb.engine.execute(ins)
        return
    
    # insert
    ins =objinf.insert().values(idobj = application.id,
                                inftyp = 13080,
                                infsubtyp = 0,
                                blkno=0,
                                infval=level)
    kb.engine.execute(ins)


def calculate_new_guid(fullname, old_guid, export_name):
    """
    Given a method fullname, calculate the new guid
    """
    
    if not fullname:
        return old_guid
    
    elements = fullname.split('.[')
    
    if len(elements) <= 1:
        return old_guid # I do not know
    
    
    path = ''
    
    if '"' in old_guid:
        old_guid_elements = old_guid.split('"')
        if len(old_guid_elements) <= 1:
            return old_guid # I do not know
        
        # first one is path : take from old_guid
        
        path = old_guid_elements[1].replace('..', '.')
    else:
        
        try:
            path = fullname.split('[')[1].split(']')[0].upper()
        except:
            pass # sic
        
    new_elements = ['[' + path + ']']
    new_elements += elements[1:] # rest is left as is
    
    guid = '.['.join(new_elements) 
    
    if export_name and export_name.endswith('const'):
        guid += 'const'

    return guid




class Migration(ApplicationLevelExtension):
    """
    migration of guids : render them local
    """
    def start_application(self, application):
        
        level = get_cpp_guid_level(application)
        if level == 0:
            self.migrate_from_level_0(application)
        elif level == 1:
            self.migrate_from_level_1(application)
        else:
            logging.info("No need to migrate guids")

    def migrate_from_level_0(self, application):
        
        kb = application.get_knowledge_base()
        
        new_guids = []
        duplicate = defaultdict(int)
        
        logging.info("calculating new guids...")
        
        objects = reflect_table('Objects', kb.metadata, kb.engine)
        ObjFulNam = kb.ObjFulNam
        ObjDsc = reflect_table('ObjDsc', kb.metadata, kb.engine)
        
        j = objects.join(ObjFulNam, 
                         objects.c.idkey == ObjFulNam.c.idobj, 
                         True).join(ObjDsc, 
                                    and_(ObjDsc.c.idobj == objects.c.idkey, ObjDsc.c.inftyp == 46000, ObjDsc.c.infsubtyp == 24),
                                    True)
                         
        query = select([objects.c.idkey,
                        ObjFulNam.c.fullname,
                        objects.c.idnam,
                        ObjDsc.c.infval
                        ]).select_from(j)
                         
        query = query.where(objects.c.idkey.in_(application.objects().has_type(['C/C++']).has_type(['APM Inventory Methods', 'APM Inventory Functions'])._get_object_query()))
        
        for line in kb._execute_sqlalchemyquery(query):

            try:
                
                # under 256 chars...
                guid = calculate_new_guid(line[1], line[2], line[3])
        
                if guid in duplicate:
                    
                    # we have found a duplicate : too bad
                    count = duplicate[guid] + 1
                    guid += str(count)
                    duplicate[guid] += 1
#                     logging.info('found duplicate %s', guid)
                else:
                    duplicate[guid] = 0
                
                new_guids.append({'_idkey':line[0], 'idnam':guid, 'idshortnam':guid})
        
            except:
                # sic...
                logging.warning('issue : ' + traceback.format_exc())

        if new_guids:
            logging.info("Updating new guids...")
            
            ins = objects.update().where(objects.c.idkey == bindparam('_idkey')).values({'idnam': bindparam('idnam'), 'idshortnam': bindparam('idshortnam')})
            kb.engine.execute(ins, new_guids)
        
        # set new level
        set_cpp_guid_level(application, 2)
        
        logging.info("Migration done")
    
    
    
    def migrate_from_level_1(self, application):
        
        """
        Here we can have created dups...
        """
        # nothing to do...
        
        # set new level
        set_cpp_guid_level(application, 2)

