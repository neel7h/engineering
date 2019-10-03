from cast.analysers import log, CustomObject, create_link


class Seneca:

    def __init__(self):
        self.seneca_require = False
        self.seneca_use_in_file = {}
        self.act_call = []
        self.add_call = []
        self.receiver_names = []

    def set_infos(self, parsingResult, jsContent):

        if parsingResult.seneca_require:
            self.seneca_require = True
            
        if parsingResult.seneca_uses:
            self.seneca_use_in_file[jsContent] = parsingResult.seneca_uses
        
        self.act_call.extend(parsingResult.act_call)
        self.add_call.extend(parsingResult.add_call)

    def __create_object(self, name, meta_type, kb_parent, position):
        if not name:
            return None

        kbObject = CustomObject()
        kbObject.set_name(name)
        kbObject.set_parent(kb_parent)
        kbObject.set_type(meta_type)
        kbObject.set_guid(name + ': ' + str(position))
        kbObject.save()
        kbObject.save_position(position)

        if meta_type == 'CAST_NodeJS_Seneca_Add':
            kbObject.save_property('CAST_MQE_QueueReceive.queueName', name)
            kbObject.save_property('CAST_MQE_QueueReceive.messengingSystem', 'Seneca')

        elif meta_type == 'CAST_NodeJS_Seneca_Act':
            kbObject.save_property('CAST_MQE_QueueCall.queueName', name)
            kbObject.save_property('CAST_MQE_QueueCall.messengingSystem', 'Seneca')

        if not meta_type == 'CAST_NodeJS_Seneca_Add':
            log.info('Create Act Seneca: ' + name)
        else:
            log.info('Create Add Seneca: ' + name)

        return kbObject

    def add_process(self, add):
        try:

            params = add.get_parameters()
            if not params:
                return

            if not hasattr(params[0], 'get_text'):
                return

            parent = add

            while not parent.is_function() and not parent.is_js_content():
                parent = parent.parent

            position = add.create_bookmark(add.get_file())
            
            # Compute handler
            handler = None
            if params[1].is_function():
                handler = params[1]

            else:
                res = params[1].get_resolutions()
                handler = res[0].callee

            # compute msg
            msg = ''
            if hasattr(params[0], 'get_items'):
                '''
                seneca.add({role:plugin, end:'offer'}, callback)
                '''
                role = params[0].get_item('role')

                if not role:
                    return

                for _key in params[0].items.keys():
                    value = params[0].items[_key]

                    res = value.get_text()
                    if value.is_identifier():
                        res = value.evaluate()[0]

                    msg = msg + _key.get_text() + ':' + res + ','

                msg = msg[0:len(msg) - 1]

            elif 'role' in params[0].get_text():
                '''
                seneca.add('role:name,info:hello', callback)
                '''
                msg = params[0].get_text()

            if msg and msg not in self.receiver_names:
                self.receiver_names.append(msg)
                receiver = self.__create_object(msg, 'CAST_NodeJS_Seneca_Add', parent.kbObject, position)

                if handler and handler.is_function():
                    create_link('callLink', receiver, handler.kbObject)
                    log.info('create link ' + msg + ' add() and ' + str(handler))
                else:
                    log.warning('Can not resolve handler of add: ' + msg)

        except:
            log.warning('Seneca.add() could not be analysed')

    def search_receiver_name_from_pin(self, pin, map_pin):
        for receiver_name in self.receiver_names:
            text = pin.replace("'", "")
            text_list = text.split(',')
            role = text_list[0]
            
            name_cmd = text_list[1]
            if '*' in text_list[1]:
                name_cmd = text_list[1].replace('*', map_pin)
            
            if role in receiver_name and name_cmd in receiver_name:
                return receiver_name

        return None

    def create_ws_method(self, ws_method, url, kb_parent, position):
        type_method = {'GET': 'CAST_NodeJS_GetOperation', 'POST': 'CAST_NodeJS_PostOperation', 
                       'PUT': 'CAST_NodeJS_PutOperation', 'DELETE': 'CAST_NodeJS_DeleteOperation'}

        def uri_normalization(uri):
            if uri == '/':
                return uri

            uris = uri.split('/')
            uri = ''
            if uris:
                uri = ''
                for part in uris:
                    if part:
                        if part.startswith(':') or part.startswith('{'):
                            uri += '{' + part.replace(part[0], '') + '}/'
                        else:
                            uri += (part + '/')

            return uri

        try:
            url = uri_normalization(url)

            if not url:
                return None

            fullname = position.get_file().get_path() + '\\' + ws_method + '\\' + url
            operation_object = CustomObject()
            operation_object.set_name(url)
            operation_object.set_type(type_method[ws_method])
            operation_object.set_parent(kb_parent)
            operation_object.set_guid(fullname)
            operation_object.set_fullname(fullname)
            operation_object.save()

            log.info('Create ws method from seneca :' + str(fullname))
            return operation_object

        except:
            log.warning('Ws from seneca microservice')
            return None

    def compute_seneca_web(self, ord_value, kb_parent, position):

        """
        use:{
              prefix:'/product',
              pin:'role:api,product:*',
              startware: verify_token,
              map:{
              ...
            }
        }
        """
        if not hasattr(ord_value, 'get_items'):
            return

        use = ord_value.get_item('use')

        if not hasattr(use, 'get_items'):
            return

        prefix = use.get_item('prefix')

        if not prefix or not hasattr(prefix, 'get_text'):
            return

        pos_ws = use.create_bookmark(use.get_file())

        postfix = use.get_item('postfix')

        url_post = ''
        if postfix:
            url_post = postfix.get_tex()

        base_url = prefix.get_text()
        
        maps = use.get_item('map')

        # from pin find out call method
        pin = use.get_item('pin')

        def resolve_pin(my_pin):

            if my_pin.is_identifier():
                try:
                    res = my_pin.get_resolutions()[0].calee
                    return resolve_pin(res)

                except:
                    pass

            elif hasattr(my_pin, 'get_items'):
                result = ''
                for key in my_pin.items.keys():
                    value = my_pin.items[key]
                    res = value.get_text()
                    if value.is_identifier():
                        res = value.evaluate()[0]
                    result = result + key.get_text() + ':' + res + ','

                result = result[0:len(result) - 1]
                result = result.replace('use.pin.', '')
                return result

            elif hasattr(my_pin, 'get_text'):
                return my_pin.get_text()

            return ''

        pin_text = resolve_pin(pin)

        if not hasattr(maps, 'items'):
            return

        sender = self.__create_object('role:web', 'CAST_NodeJS_Seneca_Act', kb_parent, position)

        if not sender:
            return

        for _map in maps.items.keys():
            try:
                '''https://github.com/senecajs/seneca-web/blob/master/docs/providing-routes.md'''
                if not hasattr(_map, 'get_name'):
                    continue

                value_map = maps.items[_map]

                if hasattr(value_map, 'get_text') and value_map.get_text() == 'true':
                    """ SET DIRECT hello MAP is TRUE: 
                      map:{
                        hello:true
                      }
                    """
                    url = base_url + _map.get_name() + url_post
                    name = self.search_receiver_name_from_pin(pin_text, _map.get_name())

                    operation = self.create_ws_method('GET', url, sender, pos_ws)

                    sender_handler = self.__create_object(name, 'CAST_NodeJS_Seneca_Act', sender, position)

                    create_link('callLink', operation, sender_handler, position)

                elif hasattr(value_map, 'items'):
                    """
                    map:{
                        star: { 
                          alias:'/:id/star' 
                        },
                        handle_star:{
                          PUT:true,
                          DELETE:true,
                          alias:'/:id/star'
                        }
                      }
                    """

                    alias = value_map.get_item('alias')
                    redirect = value_map.get_item('redirect')
                    auth = value_map.get_item('auth')
                    secure = value_map.get_item('secure')
                    name = value_map.get_item('name')
                    suffix = value_map.get_item('suffix')

                    if not suffix:
                        suffix = ''

                    if name:
                        url = base_url + name.get_name() + url_post + suffix

                    else:
                        url = base_url + _map.get_name() + url_post + suffix

                    if redirect:
                        pass  # TODO

                    elif auth:
                        pass  # TODO

                    elif secure:
                        pass  # TODO

                    if alias:
                        # ignore prefix, name and postfix
                        url = alias.get_name()

                    name = self.search_receiver_name_from_pin(pin_text, _map.get_name())

                    opr_methods = ['GET', 'POST', 'PUT', 'DELETE']

                    sender_handler = self.__create_object(name, 'CAST_NodeJS_Seneca_Act', sender, position)

                    for opr_method in opr_methods:
                        try:
                            opr = value_map.get_item(opr_method)
                            
                            if (opr and opr.get_name() == 'false') or not opr:
                                continue
                            
                            operation = self.create_ws_method(opr_method, url, sender, pos_ws)
                            if not operation:
                                return

                            create_link('callLink', operation, sender_handler, position)
                            log.info('link between webservice and ' + name + ' sender')
                            
                        except:
                            log.warning('webservice method seneca')
                            continue
                        
            except:
                continue

    def act_process(self, act):
        try:
            position = act.create_bookmark(act.get_file())

            parent = act
            while not parent.is_function() and not parent.is_js_content():
                parent = parent.parent
                
            params = act.get_parameters()
            msg = ''

            if hasattr(params[0], 'get_items'):
                '''{role:'web', use:{...}'''
                role = params[0].get_item('role')

                if not role:
                    return

                if role.get_text() == 'web':
                    self.compute_seneca_web(params[0], parent.kbObject, position)
                    return

                else:
                    for _key in params[0].items.keys():
                        msg = msg + _key.get_text() + ':' + params[0].items[_key].get_text() + ','

                    msg = msg[0:len(msg) - 1]

            elif params[0].get_text() == 'role:web':
                '''"role:'web', {use:{...}}}"'''
                self.compute_seneca_web(params[1], parent.kbObject, position)
                return

            else:
                msg = params[0].get_text()

            if not msg:
                return

            name = self.search_receiver_name_from_pin(msg, '')

            if not name:
                return

            self.__create_object(name, 'CAST_NodeJS_Seneca_Act', parent.kbObject, position)

        except:
            log.warning('Seneca.act() could not be analysed')

    def compute(self):
        try:

            for adds in self.add_call:
                for add in adds:
                    log.debug('----------' + str(add))
                    self.add_process(add)

            for key in self.seneca_use_in_file.keys():
                value = self.seneca_use_in_file[key]
                for callparts in value:
                    for callpart in callparts:
                        if callpart.get_name() == 'use':
                            '''
                            seneca.use(Web, config)
                            '''
                            params = callpart.get_parameters()
                            try:
                                if len(params) == 2 and params[0].get_text() == 'Web':
                                    
                                    parent = callpart
                                    while not parent.is_function() and not parent.is_js_content():
                                        parent = parent.parent

                                    config = params[1]
                                    if config.is_identifier():
                                        res = config.get_resolutions()[0]
                                        self.compute_seneca_web(res.callee, parent.kbObject)

                                    else:
                                        self.compute_seneca_web(config, parent.kbObject)
                            except:
                                log.warning('seneca web config is not correct')
                        
                        elif callpart.get_name() == 'act':
                            self.act_process(callpart)
                        
                        elif callpart.get_name() == 'ready':
                            pass

            for acts in self.act_call:
                for act in acts:
                    log.debug('----------' + str(act))
                    self.act_process(act)

        except:
            log.warning('seneca compute')
