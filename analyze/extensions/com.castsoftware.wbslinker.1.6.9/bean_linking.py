'''
Specialised linking for beans.
'''
import cast_upgrade_1_5_25 # @UnusedImport
from cast.application import ApplicationLevelExtension, create_link
import logging, re
from collections import defaultdict


class ELExpression:
    
    def __init__(self, expression, o=None):

        self.expression = expression
        self.object = o



class BeanMethod:
    
    def __init__(self, bean_name, fullname, o=None):

        self.bean_name = bean_name
        self.fullname = fullname
        self.object = o


class Bean:
    
    def __init__(self, bean_object, class_object):

        self.bean = bean_object
        self._class = class_object
        

def get_bean_accesses(expression):
    """
    extract the xxx.xxx.xxx sub expressions
    """
    result = []
    for match in re.findall(r'[a-zA-Z0-9_]+\.[a-zA-Z0-9_]+', expression):
        result.append(match)
    
    return result


def link(expressions, bean_methods):

    result = []
    bean_methods_per_bean_name = defaultdict(list)

    for bean_method in bean_methods:
#         logging.info('bean method(bean_name=%s, method=%s)', bean_method.bean_name, bean_method.object.get_fullname())
        bean_methods_per_bean_name[bean_method.bean_name].append(bean_method)
        
    for expression in expressions:
        
        # normalise
        for access in get_bean_accesses(expression.expression):
            
            names = access.split('.') 
            bean_name = names[0]
            try:
                member_name = names[1].capitalize()
                
#                 logging.info(member_name)
                
                for method in bean_methods_per_bean_name[bean_name]:
                    method_name = method.fullname.split('.')[-1] 
#                     logging.info('**' + method_name + '**')
                    # method_name can be :
                    # xxx and be linked to getXxx method
                    # xxx and be linked to isXxx method (case of boolean)
                    # xxx and be linked to xxx method
                    # see : https://docs.oracle.com/javaee/7/tutorial/jsf-el003.htm#BNAHU
                    if method_name in ['get' + member_name, 'is' + member_name, names[1]]:
#                         logging.info('********** linking')
                        result.append((expression, method))  
            except KeyError:
#                 logging.debug('No bean named %s', bean_name)
                pass
    return result



class ExtensionApplication(ApplicationLevelExtension):

    def end_application(self, application):

        logging.info('Linking EL expressions')

        # 1. loading
        expressions = [ELExpression(e.get_property('CAST_EL_Expression.expression'), e) for e in application.objects().has_type('CAST_EL_Expression').load_property('CAST_EL_Expression.expression')]

        if not expressions:
            logging.info('No EL expressions : nothing to do')
            return
        
        # maybe some more ???        
        beans = {}
        
        for l in application.links().has_callee(application.objects().is_class().has_type('Java')).has_caller(application.objects().has_type(['CAST_Web_AllBeans', 'CAST_Spring_AllBeans'])):
            beans[l.get_callee().get_fullname()] = Bean(l.get_caller(), l.get_callee())
#             logging.info('bean %s, %s', l.get_caller().get_name(), l.get_callee().get_fullname())
        
        if not beans:
            logging.info('No beans : nothing to do')
            return # nothing to do
        
        bean_methods = []
        for method in application.objects().has_type('Java').is_executable():
            
            
            class_fullname = '.'.join(method.get_fullname().split('.')[:-1])
#             logging.info('method %s', method.get_fullname())
#             logging.info('class_fullname %s', class_fullname)
            try:
                bean = beans[class_fullname]
                
                bean_name = bean.bean.get_name()
                
                bean_methods.append(BeanMethod(bean_name, method.get_fullname(), method))
                
            except KeyError:
                pass
                    
        # 2. linking
        links = link(expressions, bean_methods)
        
        # create links
        for call, service in links:
            
            create_link('callLink', call.object, service.object)
        
        