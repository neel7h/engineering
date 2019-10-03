from cast import Event
from cast.analysers import log, ua, CustomObject, create_link, Bookmark
from normalize import normalize_path


class Context:
    
    def __init__(self, tag):

        self.tag = tag
        # th:action
        self.action = None
        # method="post"
        self.method = None
        self.href = None
        
class ThymeLeaf(ua.Extension):
    """
    Handle thymeleaf html parsing...
    See http://www.thymeleaf.org/index.html
    """
    def __init__(self):
        self.context_stack = []
        self.thymeleaf_namespace = 'th' # some default...
        self.html_source_code = None # the object that will be the parent
        
        self.current_guids = {}
        
        self.current_file = None
        
    def get_current_context(self):
        return self.context_stack[-1]
    
    
    @Event('com.castsoftware.html5', 'start_html_source_code')
    def start_html_source_code(self, html_source_code):
        # @type html_source_code: cast.analysers.CustomObject
        self.html_source_code = html_source_code 
        self.current_file = html_source_code.parent
        
    @Event('com.castsoftware.html5', 'start_html_tag')
    def start_html_tag(self, tag):
        self.context_stack.append(Context(tag))

    @Event('com.castsoftware.html5', 'start_html_attribute_value')
    def start_html_attribute_value(self, attribute_value):
        
        name = attribute_value.get_attribute()
        value =  attribute_value.get_value()
        
        # value.get_token() gives position
        
        # get presence of thymeleaf and get the namespace
        if self.get_current_context().tag.get_text() == 'html' and name.get_text().startswith('xmlns:') and value.get_text() == 'http://www.thymeleaf.org':
            
            # the namespace for thymeleaf
            self.thymeleaf_namespace = name.get_text()[6:]
        
        # store the th:action
        if name.get_text() == self.thymeleaf_namespace + ':action':
            self.get_current_context().action = value
        
        # store the method=
        if name.get_text() == 'method':
            self.get_current_context().method = value
        
        # store the th:href
        if name.get_text() == self.thymeleaf_namespace + ':href':
            self.get_current_context().href = value

    
    @Event('com.castsoftware.html5', 'end_html_tag')
    def end_html_tag(self, tag):
        
        # html may be badly formed
        if not self.context_stack:
            return
        
        value = None
        method = 'get' # default ?
        
        if self.get_current_context().tag.get_text() == 'form':
            value = self.get_current_context().action
            if self.get_current_context().method and self.get_current_context().method.get_text():
                method = self.get_current_context().method.get_text().lower()
            
        if self.get_current_context().href:
            value = self.get_current_context().href
        
        self.context_stack.pop()

        
        if not value:
            return
        
        if not value.get_text().startswith('@{'):
            return
        
        # create a service call

        url = value.get_text().strip()[2:-1]
        
        # select the type
        types = {'get':'CAST_Thymeleaf_GetResourceService',
                 'put':'CAST_Thymeleaf_PutResourceService',
                 'post':'CAST_Thymeleaf_PostResourceService',
                 'delete':'CAST_Thymeleaf_DeleteResourceService',
                 }        
        
        type_name = 'CAST_Thymeleaf_PostResourceService' # default        

        try:
            type_name = types[method]
        except KeyError:
            pass
        
        url = normalize_path(url)

        log.debug('Creating call : %s, %s' % (type_name, url))
        
        service_call = CustomObject()
        service_call.set_parent(self.html_source_code)
        service_call.set_type(type_name)
        service_call.set_name(url)
        # @todo guid
        # service_call.set_guid(url)
        service_call.save()
        
        # position 
        token = value.get_token()
        
        bookmark = Bookmark(self.current_file, token.begin_line, token.begin_column, token.end_line, token.end_column)
        service_call.save_position(bookmark)
        # uri
        service_call.save_property('CAST_ResourceService.uri', url)
        
        create_link('callLink', self.html_source_code, service_call, bookmark)

        