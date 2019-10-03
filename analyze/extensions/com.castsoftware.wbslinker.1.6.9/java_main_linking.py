"""
Linking to java main method
"""
import cast_upgrade_1_5_25 # @UnusedImport
from cast.application import ApplicationLevelExtension, create_link
import logging



class CallToJava:
    
    def __init__(self, class_full_name, call_object):

        self.class_full_name = class_full_name
        self.call_object = call_object


class JavaMain:
    
    def __init__(self, method_full_name, method_object):

        self.method_full_name = method_full_name
        self.method_object = method_object


class ExtensionApplication(ApplicationLevelExtension):

    def end_application(self, application):

        logging.info('Linking calls to java programs')

        # 1. loading
        calls = [CallToJava(e.get_property('CAST_CallToJavaProgram.javaClassFullName'), e) for e in application.objects().has_type('CAST_CallToJavaProgram').load_property('CAST_CallToJavaProgram.javaClassFullName')]

        if not calls:
            logging.info('No call to java programs : nothing to do')
            return
        
        # load the main Java methods       
        mains = {m.get_fullname():JavaMain(m.get_fullname(), m) for m in application.search_objects(name='main', category='JV_METHOD')}

        if not mains:
            logging.info('No main java methods : nothing to do')
            return
        
        for call in calls:
            
            try:
                logging.debug('searching ' + call.class_full_name + '.main')
                main = mains[call.class_full_name + '.main']
                logging.debug('creating link between ' + str(call.call_object) + ' and ' + str(main.method_object))
                create_link('callLink', call.call_object, main.method_object)                    
            except KeyError:
                pass            
