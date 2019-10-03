from cast.analysers import log, external_link, CustomObject, Bookmark, create_link


class Knexsupport:
    
    def __init__(self):
        self.is_knex = False
        self.is_bookshelf = False
        self.model_infos = []
        self.sql_techno = 'postgresql'  # by default
        self.models = {}
        self.knex_config = None

    def update_config(self, config):
        
        if not config:
            return

        try:
            if hasattr(config, 'get_items'):
                client = config.get_item('client')
                
                if not client:
                    client = config.get_item('moduule.exports.client')

                if client and hasattr(client, 'get_values'):
                    self.sql_techno = client.get_values()

            elif hasattr(config, 'get_resolutions'):
                id_config = config.get_resolutions()[0]
                self.update_config(id_config.callee)

        except:
            pass

    def set_infos(self, parsingResult):
        if parsingResult.knex_require:
            self.is_knex = parsingResult.knex_require

            if not self.knex_config:
                self.knex_config = parsingResult.knex_config
            
        if parsingResult.bookshelf_require:
            self.is_bookshelf = parsingResult.bookshelf_require

        self.model_infos.extend(parsingResult.model_knex_infos)

    def create_model(self, name, jsContent, type_metalmodel):

        if name in self.models.keys():
            return self.models[name]

        try:
            kbModel = CustomObject()
            kbModel.set_name(name)
            kbModel.set_type(type_metalmodel)
            kbModel.set_parent(jsContent.get_kb_object())
            fullname = jsContent.get_file().get_path() + '/' + name + '/' + type_metalmodel
            kbModel.set_guid(fullname)
            kbModel.set_fullname(fullname)
            kbModel.save()
            kbModel.save_position(Bookmark(jsContent.get_file(), 1, 1, -1, -1))

            name_file = jsContent.get_file().get_path().split('\\')[-1]

            log.info('Model object has been found :' + name_file + ' with type: ' + type_metalmodel)
            self.models[name] = kbModel
            return kbModel

        except:
            pass

    def resolve_table(self, callPart, kb_info, name_method):
        
        ord_dict = callPart.get_parameters()[0]

        if not hasattr(ord_dict, 'get_items_dictionary'):
            return

        item_dict = ord_dict.get_items_dictionary()

        for key, value in item_dict.items():
            if hasattr(key, 'get_text') and 'tableName' == key.get_text() and\
               hasattr(value, 'get_text'):
                parent_part = kb_info

                while not parent_part.is_js_content() and not parent_part.is_function():
                    parent_part = parent_part.parent
                
                js_content = parent_part

                while not js_content.is_js_content():
                    js_content = js_content.parent

                if name_method in ['destroy', 'del']:
                    link_type = 'useDeleteLink'

                elif name_method in ['update', 'save', 'fetch']:
                    link_type = 'useUpdateLink'

                elif name_method in ['insert']:
                    link_type = 'useInsertLink'

                elif name_method in ['select']:
                    link_type = 'useSelectLink'

                else:
                    link_type = 'useLink'
                
                model_objects = []
                true_table = external_link.find_objects(value.get_text(), 'Database Table')
                
                if not true_table:
                    model_objects = external_link.find_objects(value.get_text(), 'Database View')

                if model_objects:
                    log.info('found table from sql: ' + value.get_text())
                    
                else:
                    elm = self.create_model(value.get_text(), js_content, 'CAST_NodeJS_Unknown_Database_Table')
                    model_objects.append(elm)

                for model_object in model_objects:
                    create_link(link_type, parent_part.get_kb_object(), model_object)
                    log.debug('create ' + link_type + ' link between ' + parent_part.get_name() + ' function and ' + value.get_text() + ' table')

    def compute(self):

        if not self.is_knex or not self.is_bookshelf:
            return

        self.update_config(self.knex_config)

        for callParts in self.model_infos:
            try:

                callpart = callParts[0]
                identifier = callpart.identifier_call
    
                resolution = identifier.get_resolutions()[0]
                callee = resolution.callee
    
                if not callee.is_function_call():
                    continue
    
                callpart_table = callee.get_function_call_parts()[0]
    
                id_table = callpart_table.identifier_call
    
                if '.Model.extend' not in id_table.get_fullname():
                    continue
                
                name_method = ''
    
                if len(callParts) == 1 and identifier.get_prefix():
                    name_method = identifier.get_prefix()
                
                elif len(callParts) >= 2:
                    name_method = callParts[-1].get_text()
    
                    if name_method in ['then', 'where'] :
                        name_method = callParts[-2].get_text()
    
                if name_method:
                    self.resolve_table(callpart_table, callpart, name_method)

            except:
                continue
             
