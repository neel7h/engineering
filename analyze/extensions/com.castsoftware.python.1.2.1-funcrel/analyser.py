import cast.analysers.ua
import os
import traceback
from py_file_filters import FileFilter
from chardet.universaldetector import UniversalDetector
from symbols import Library, Module
from resolution import resolve
import http_parametrisation
import quality_rules
import web_frameworks
import database_frameworks
import msgq_activemq
import msgq_rabbitmq
import msgq_ibmmq


class PythonAnalyzer(cast.analysers.ua.Extension):
    """
    Analyzer in charge of python files *.py
    """

    def __init__(self):
        # self.active = True if the analyzer is active in CAST-MS
        self.active = True
        self.extensions = ['.py']
        
        # list of top hierarchy AST corresponding to python files
        
        self.library = Library()

        self.fileFilter = FileFilter()
        
    def start_analysis(self):
        # resistant (for unit tests)
        try:
            options = cast.analysers.get_ua_options()  # @UndefinedVariable dynamically added
            if not 'Python' in options:
                # Python language not selected : inactive
                self.active = False
            else:
                self.active = True
                self.extensions = options['Python'].extensions
        except:
            pass
    
    def start_file(self, file):
        if not self.active:
            return
        
        path = file.get_path().lower()
        _, ext = os.path.splitext(path)
 
        if not ext in self.extensions:
            return
        
        if self.fileFilter.matches(file.get_path()):
            return
        
        module = Module(file.get_path(), _file=file) 
        self.library.add_module(module)

    def end_analysis(self):

        if not self.active:
            return

        self.library.discover()
        self.library.save_std_library()
        
        # Light parsing consists to parse only classes and methods, i.e.
        # global objects which can be called from outside the file where
        # they are defined
        for module in self.library.get_modules():
            cast.analysers.log.info('Light parsing of file ' + module.get_path())
        
            try:
                module.light_parse()
                module.save()
            except Exception:
                cast.analysers.log.warning('An error occurred on file ' + module.get_path())
                cast.analysers.log.warning(traceback.format_exc())
            
            # @todo clean ast as not needed
        
        # resolution of imports and inheritance
        self.library.resolve_globals()
        
        # Full parsing consists to parse all ast.
        # During this step, AST can be resolved because
        # light parsing has been done and global objects
        # and methods already exist.
        for module in self.library.get_modules():
            cast.analysers.log.info('Full parsing of file ' + module.get_path())
            
            try:                
                module.fully_parse()
                resolve(module, self.library)
                                
                http_parametrisation.analyse(module)
                cast.analysers.log.debug('quality rule analysis')
                quality_rules.analyse(module)
                web_frameworks.analyse(module)
                database_frameworks.analyse(module)
                msgq_rabbitmq.analyse(module)
                msgq_activemq.analyse(module)
                msgq_ibmmq.analyse(module)
                
                cast.analysers.log.debug('violation saving')
                module.save_violations(module.get_file())
                module.save_main()

                cast.analysers.log.debug('link saving')
                module.save_links()
                
            except Exception:
                cast.analysers.log.warning('An error occurred on file ' + module.get_path())
                cast.analysers.log.warning(traceback.format_exc())

        # Specific PYTHON-129 DIAG-3797 :
        quality_rules.save_violation_candidates(self.library)

        for module in self.library.get_modules():
            if module.get_resource_services():
                cast.analysers.log.debug('service saving for %s' % module.get_path())
                module.save_services()
            
            if module.get_server_operations():
                cast.analysers.log.debug('server operation saving for %s' % module.get_path())
                module.save_operations()
                
            if module.get_db_queries():
                cast.analysers.log.debug('database query saving for %s' % module.get_path())
                module.save_db_queries()

        cast.analysers.log.info(str(self.library.nbRequestsServices) + ' requests services created.')
        cast.analysers.log.info(str(self.library.nbHttplibServices) + ' httplib or http services created.')
        cast.analysers.log.info(str(self.library.nbHttplib2Services) + ' httplib2 services created.')
        cast.analysers.log.info(str(self.library.nAiohttpServices) + ' aiohttp services created.')
        cast.analysers.log.info(str(self.library.nUrllibServices) + ' urllib services created.')
        cast.analysers.log.info(str(self.library.nUrllib2Services) + ' urllib2 services created.')
        
        cast.analysers.log.info(str(self.library.nbFlaskServerOperations) + ' flask operations created.')
        cast.analysers.log.info(str(self.library.nbAiohttpServerOperations) + ' aiohttp operations created.')
        
        cast.analysers.log.info(str(self.library.nbSqlQueries) + ' SQL queries created.')
        cast.analysers.log.info(str(self.library.nbActiveMQ_queue_objects) + ' ActiveMQ Queue objects created. ')
        cast.analysers.log.info(str(self.library.nbRabbitMQ_queue_objects) + ' RabbitMQ Queue objects created.')
        cast.analysers.log.info(str(self.library.nbIBMMQ_queue_objects) + ' IBM MQ Queue objects created.')
