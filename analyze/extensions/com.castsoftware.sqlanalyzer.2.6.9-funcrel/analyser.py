'''
Created on 18 oct. 2014

@author: MRO
'''
import traceback
import os
import cast.analysers.ua
from cast.analysers import log, CustomObject
from sqlscript_parser import create_symbols, analyse_symbols
from dml_analyser import analyse_dml
from symbols import Database, Function, Schema, Procedure,\
             Method, Trigger, Event, Synonym, View, ForeignKey, Table,\
             Index, Type, Package, Constraint, FulltextConstraint, \
             UniqueConstraint
from parse_uaxdirectory import load_uaxdirectory
from variant import detect_variant, Variant
from logger import warning
from distutils.version import StrictVersion


class SQLScript(cast.analysers.ua.Extension):
    """
    Parse .sql files and create tables, views ...
    """

    def __init__(self):
        
        self.active = True
        
        # default value : to be kept synchro with metamodel
        self.extensions = ['.sql', '.src', '.uaxdirectory', '.sqltablesize', '.gdpr']
        
        # will contain schemas and symbols
        self.database = Database()
        
        self.files = []
        self.uax_directory = None
        self.detected_encodings = {}
        # option that should be kept at TRUE if we want ACCEES LINKS 
        self.impact_analysis = False
        
        # UA should skip the processing of the files, feature introduced in CAIP 8.2.11
        self.castVersion = None
        self.isUADeactivated = False
            
    def start_analysis(self):
        try:
            self.castVersion = cast.analysers.get_cast_version()
            if (self.castVersion >= StrictVersion('8.2.11') and self.castVersion < StrictVersion('8.3.0')) \
                or self.castVersion >= StrictVersion('8.3.4'):
                self.isUADeactivated = True
                log.debug('Number of code lines will be calculated by the extension.')
        except:
            log.debug('Number of code lines cannot be calculated by the extension.')

        try:
            from cast.analysers import get_extensions # @UnresolvedImport
            list_of_extensions = get_extensions()
            for extension in list_of_extensions:
                if extension[0].lower() == 'com.castsoftware.datacolumnaccess':
                    self.impact_analysis = True
                    log.info("Data Column Access is activated")
                    break

        except ImportError:
            # the case of Unit Tests
            log.debug("get_extensions cannot be imported so Impact Analysis will be activated")
            self.impact_analysis = True
                          
        try:
            options = cast.analysers.get_ua_options() #@UndefinedVariable

            # language name : to be kept synchro with metamodel
            language_name = 'SQLScript'
            
            if not language_name in options:
                # SQL Analyzer language not selected : inactive
                self.active = False
            else:
                # options :
                for extension in options[language_name].extensions:
                    self.extensions.append(extension.lower())
        except AttributeError:
            pass        
        
    
    def start_file(self, file):
        def set_loc_0 (file):
            if self.isUADeactivated:
                # should not be counted to LOC, see fix_apm_sources
                file.save_property('metric.CodeLinesCount', 0)
                file.save_property('metric.LeadingCommentLinesCount', 0)
                file.save_property('metric.BodyCommentLinesCount', 0)
            
        if not self.active:
            return
        
        path = file.get_path()
        
        _, extension = os.path.splitext(path.lower())
        
        if not extension in self.extensions:
            return
        
        
        if path.lower().endswith('.sqltablesize'):
            set_loc_0(file)
            log.info("Using table size file %s for XXL rules" % path)
            self.database.load_tablesize(path)
            return

        elif path.lower().endswith('.gdpr') and self.impact_analysis:
            set_loc_0(file)                
            log.info("Using GDPR indicator configuration file %s for table columns" % path)
            self.database.load_gdpr(path)
            return
        
        elif path.lower().endswith('.gdpr') and not self.impact_analysis:
            # skip-it
            return
                            
        elif path.lower().endswith('.uaxdirectory'):
            set_loc_0(file)
            self.uax_directory = path
        
        else:
            # source code
            self.files.append((file,path))
            
    def end_analysis(self):
        from pympler import asizeof
        from hurry.filesize import size
        
        if not self.active:
            return
        
        schema_names = None
        
        if self.uax_directory:
            
            schema_names = load_uaxdirectory(self.uax_directory)
        
            # re-order files so that tables and view are first
            table_files = []
            other_files = []
            
            for file, path in self.files:
                if schema_names.variant:
                    setattr(file, 'variant', schema_names.variant)
                if schema_names.sqlserver_with_go:
                    setattr(file, 'sqlserver_with_go', schema_names.sqlserver_with_go)
                if schema_names.is_table_or_view(path):
                    table_files.append((file,path))
                else:
                    other_files.append((file,path))
                    
            self.files = table_files + other_files
            
            # detach memory
            del table_files
            del other_files
            del self.uax_directory
        
        # first pass on files
        for file, path in self.files:
            
            if path.lower().endswith('.src') and schema_names:
                # src files generally contains non 'qualified' names
                # so we get the schema name from uaxdirectory
                default_schema_name = schema_names.get_schema_name(path)
                if default_schema_name:
                    self.database.current_schema_name = default_schema_name
                else:
                    warning('SQL-001', 'No schema found for file %s' % path)
                    
            self.first_pass(file, path)
            
            self.print_table_stats(file)
        
        try:
            log.debug("Max memory used is {}" .format( size(asizeof.asizeof(self))))
        except:
            print('issue with memory used calculation')
            pass
        
        self.database.save()
        
        log.debug("Start resolving pending references")
        # resolve all refs for index and so on ...
        self.database.resolve_pending_references()
        log.debug("End resolving pending references")

        log.debug("Start saving symbol links")
        # create links
        self.database.save_symbol_links()
        log.debug("End saving symbol links")
        
        # second pass, mainly for procs and views
        # @todo : do not second pass when file do not contain view, proc, nor triggers 
        
        for file, path in self.files:

            if path.lower().endswith('.src') and schema_names:
                # src files generally contains non 'qualified' names
                # so we get the schema n,ame from uaxdirectory
                default_schema_name = schema_names.get_schema_name(path)
                if default_schema_name:
                    
                    self.database.current_schema_name = default_schema_name
      
            self.second_pass(path, file)

        self.print_stats()

        # detach memory
        del self.files
        del self.database
        del self.detected_encodings
        
        try:
            log.debug("Max memory used is {}" .format( size(asizeof.asizeof(self))))
        except:
            print('issue with memory used calculation')
            pass
    
    def first_pass(self, file, path):
        """
        First pass on file, create symbols and save them
        put them in self.database object for latter analysis
        """
            
        def code_lines_count_file(path, file, variant):
            count_mini = 0
            skip = False
            prevLineIsAComment = False   
            with open_source_file(path, self) as f:
                for line in f:      
                    line = line.strip()
                    if line:
                        if prevLineIsAComment and '*/' not in line:
                            continue
                
                        if prevLineIsAComment and (not line.startswith('*/') and '*/' in line):
                            prevLineIsAComment = False
                            skip = False
                            if line.endswith('*/'): 
                                continue
                                                
                        if line.startswith('#') or line.startswith('--') or line.startswith('REM ') or (line.startswith('/*') and line.endswith('*/')):
                            continue
                
                        # start of the multi line comment
                        if line.startswith('/*') and not line.endswith('*/') and variant != Variant.mysql:
                            prevLineIsAComment = True
                            skip = True
                            continue
                        
                        # start of the multi line comment
                        if line.startswith('/*') and not line.startswith('/*!') and not line.endswith('*/') and variant == Variant.mysql:
                            prevLineIsAComment = True
                            skip = True
                            continue
                
                        # end of the multi line comment
                        if (line.endswith('*/') or line.startswith('*/')) and not line.startswith('/*') and prevLineIsAComment:
                            prevLineIsAComment = False
                            skip = True
                         
                        if line.startswith('"""') and prevLineIsAComment:
                            continue
                                                         
                        if line.startswith('"""') and not prevLineIsAComment and skip:
                            skip = False
                            
                        # start of the multi line comment
                        if not line.startswith('/*') and '/*' in line and not line.endswith('*/') and '*/' not in line:
                            prevLineIsAComment = True
                            skip = False
                                               
                        if not skip:
                            count_mini += 1
                        else:
                            if not prevLineIsAComment: skip = False
                            else : skip = True

            if self.isUADeactivated:
                try:
                    file.save_property('metric.CodeLinesCount', count_mini)
                    # with UA, all those are 0, so I keep them as before
                    file.save_property('metric.LeadingCommentLinesCount', 0)
                    file.save_property('metric.BodyCommentLinesCount', 0)
                except:
                    log.debug('Cannot update the Number of code lines, because of %s' % traceback.format_exc())
            else:
                file.save_property('sourceFile.SQL_CodeLinesCount', count_mini) 

        log.info('Start creating symbols for file %s' % str(path))
        
        self.database.declared_schema_name = None
        
        has_ddl = False
        has_dml = False
        
        already_detected_variant = None
        already_detected_sqlserver_with_go = None
            
        self.database.current_file = file
        
        # in first pass detect sql variant of file
        # for Transact-SQL we detect if GO is used because it signals the end of a batch of Transact-SQL statements
        try:
            already_detected_variant = getattr(file, 'variant') 
            already_detected_sqlserver_with_go = getattr(file, 'sqlserver_with_go') 
        except AttributeError:
            pass
            
        variant, sqlserver_with_go = detect_variant(path, self)

        # store it for future use
        if not already_detected_variant:
            setattr(file, 'variant', variant)
            sql_vendor = str(variant).replace('Variant.', '').capitalize()
        else:
            sql_vendor = str(already_detected_variant).replace('Variant.', '').capitalize()
            
        if not already_detected_sqlserver_with_go:
            setattr(file, 'sqlserver_with_go', sqlserver_with_go)
        
        file.save_property('sourceFile.SQL_Vendor', sql_vendor)
    
        log.info("This file is analyzed against %s variant" % sql_vendor)   
        with open_source_file(path, self)  as f:             
            try:
                has_ddl, has_dml = create_symbols(f, self.database, False, variant, sqlserver_with_go)  
            except:
                warning('SQL-002', 'Parsing issue on file %s, because of ' % (path, traceback.format_exc()))
                return
    
            if not already_detected_variant:
                log.debug('File {} is considered as {}' .format (str(path), ('DDL' if has_ddl else 'DML')))
            else:
                log.debug('File {} is considered as DDL' .format (str(path)))
                has_ddl = True
            
            if (has_ddl and has_dml) or not has_ddl:
                # re-read
                f.seek(0)
                
                result = CustomObject()
                result.set_type('SQLScriptDML')
                result.set_name(file.get_name())
                result.set_parent(file)
                result.save()
                size = sum(1 for _ in f)
                f.seek(0)
                bookmark = cast.analysers.Bookmark(file,1,1,size,-1)
                result.save_position(bookmark)
                setattr(file, 'DML', True)
                setattr(file, 'result', result)
        
        code_lines_count_file(path, file, variant)
        log.info('End creating symbols for file %s' % str(path))    
                
    def second_pass(self, path, file):
        log.info("Start creating links for file %s" % path)
        self.database.declared_schema_name = None
        
        variant = getattr(file, 'variant') 
        sqlserver_with_go = getattr(file, 'sqlserver_with_go')
                
        with open_source_file(path, self) as f:            
            for symbol in analyse_symbols(f, self.database, False, variant, sqlserver_with_go, self.impact_analysis):
            # save links on the fly on reanalyzed symbols to save memory 
                symbol.save_links()
                
                # When the option is activated, save the links through the columns
                if self.impact_analysis:
                    try:
                        symbol.save_column_links()
                    except AttributeError:
                        pass
                    
                symbol.save_violations()

            try:
                if getattr(file, 'DML'):
                    # analyse it as dml
                    file_object = getattr(file, 'result')
                    analyse_dml(f, file_object, file, self.database)                
            except AttributeError:
                # expected for DDL files
                pass
            except Exception as exception:
                # unexpected exception
                log.info('File %s cannot be analyzed (%s)' % (file.get_name(), exception))
                
        log.info("End creating links for file %s" % path)

    def print_stats(self):
        number_of_schemas, number_of_functions, number_of_procedures = 0, 0, 0
        number_of_triggers,number_of_events, number_of_synonyms, number_of_views = 0, 0, 0, 0
        number_of_foreigner_keys, number_of_indexes, number_of_types, number_of_packages = 0, 0, 0, 0
        number_of_constraints, number_of_full_text_constraints, number_of_unique_constraints, number_of_tables = 0, 0, 0, 0
        element = None
        
        like_unique_constraints, like_constraints, like_full_text_constraints, \
            like_indexes, like_foreigner_keys = 0, 0, 0, 0, 0
        
        def like_a_table(element):
            like_a_table_element = None
            unique_constraints, constraints, full_text_constraints, indexes, foreigner_keys = 0, 0, 0, 0, 0
            for _, item in element.symbols.items():
                like_a_table_element = item[0]
                if not like_a_table_element:
                    continue
                if type(like_a_table_element) == UniqueConstraint:
                    unique_constraints += 1 
                elif type(like_a_table_element) == Constraint:
                    constraints += 1 
                elif type(like_a_table_element) == FulltextConstraint:
                    full_text_constraints += 1 
                elif type(like_a_table_element) == Index:
                    indexes += 1    
                elif type(like_a_table_element) == ForeignKey:
                    foreigner_keys += 1 
            
            return (unique_constraints, constraints, full_text_constraints, indexes, foreigner_keys)
        
        for _, schema in self.database.symbols.items():
            schema = schema[0]

            if type(schema) == Schema:
                number_of_schemas += 1
                for _, item in schema.symbols.items():
                    try:
                        element = item[0]
                    except IndexError:
                        element = None
                    if not element:
                        continue
                    
                    if type(element) == Function:
                        number_of_functions += 1
                    elif type(element) == Procedure:
                        number_of_procedures += 1
                    elif type(element) == Method:
                        number_of_procedures += 1
                    elif type(element) == Trigger:
                        number_of_triggers += 1 
                    elif type(element) == Event:
                        number_of_events += 1  
                    elif type(element) == Synonym:
                        number_of_synonyms += 1 
                    elif type(element) == View:
                        number_of_views += 1 
                        like_unique_constraints, like_constraints, like_full_text_constraints, \
                            like_indexes, like_foreigner_keys = like_a_table(element)
                        number_of_unique_constraints += like_unique_constraints
                        number_of_constraints += like_constraints
                        number_of_full_text_constraints += like_full_text_constraints
                        number_of_indexes += like_indexes
                        number_of_foreigner_keys += like_foreigner_keys
                    elif type(element) == ForeignKey:
                        number_of_foreigner_keys += 1 
                    elif type(element) == Index:
                        number_of_indexes += 1 
                    elif type(element) == Type:
                        number_of_types += 1 
                    elif type(element) == Package:
                        number_of_packages += 1 
                    elif type(element) == Constraint:
                        number_of_constraints += 1 
                    elif type(element) == FulltextConstraint:
                        number_of_full_text_constraints += 1 
                    elif type(element) == UniqueConstraint:
                        number_of_unique_constraints += 1 
                    elif type(element) == Table:
                        number_of_tables += 1 
                        like_unique_constraints, like_constraints, like_full_text_constraints, \
                            like_indexes, like_foreigner_keys = like_a_table(element)
                        number_of_unique_constraints += like_unique_constraints
                        number_of_constraints += like_constraints
                        number_of_full_text_constraints += like_full_text_constraints
                        number_of_indexes += like_indexes
                        number_of_foreigner_keys += like_foreigner_keys
                                                             
        suffix_message = '(s) created.'

        if number_of_schemas > 0:
            log.info('%s Schema%s' % (number_of_schemas, suffix_message))
            if number_of_packages > 0:
                log.info('%s Package%s' % (number_of_packages, suffix_message))
            if number_of_types > 0:
                log.info('%s Object Type%s' % (number_of_types, suffix_message))
            if number_of_functions > 0 :
                log.info('%s Function%s' % (number_of_functions, suffix_message))
            if number_of_procedures > 0:
                log.info('%s Procedure%s' % (number_of_procedures, suffix_message))
            if number_of_tables > 0:
                log.info('%s Table%s' % (number_of_tables, suffix_message))
            if number_of_events > 0:
                log.info('%s Event%s' % (number_of_events, suffix_message))
            if number_of_triggers > 0:
                log.info('%s Trigger%s' % (number_of_triggers, suffix_message))
            if number_of_foreigner_keys > 0:
                log.info('%s Foreigner Key%s' % (number_of_foreigner_keys, suffix_message))
            if number_of_unique_constraints > 0:
                log.info('%s Unique Constraint%s' % (number_of_unique_constraints, suffix_message))
            if number_of_constraints > 0:
                log.info('%s Constraint%s' % (number_of_constraints, suffix_message))
            if number_of_indexes > 0:
                log.info('%s Index(es) created.' % number_of_indexes)
            if number_of_full_text_constraints > 0:
                log.info('%s Full Text Constraint%s' % (number_of_full_text_constraints, suffix_message))
            if number_of_views > 0:
                log.info('%s View%s' % (number_of_views, suffix_message))
            if number_of_synonyms > 0:
                log.info('%s Synonym%s' % (number_of_synonyms, suffix_message))
        
    def print_table_stats(self,file):
        n_drop = 0
        n_rename = 0
        for _, schema in self.database.symbols.items():
            schema = schema[0]
            n_drop += schema.count_dropped_tables
            n_rename += schema.count_renamed_tables
        
        # necessary to keep count within the scope of a file 
            schema.count_dropped_tables = 0
            schema.count_renamed_tables = 0
        
        if n_drop == 1:                
            log.info("{} table has been dropped in file {}".format(n_drop,file.get_name()))
        elif n_drop > 1:
            log.info("{} tables have been dropped in file {}".format(n_drop,file.get_name()))
        
        if n_rename == 1:
            log.info("{} table has been renamed in file {}".format(n_rename,file.get_name()))
        elif n_rename > 1:
            log.info("{} tables have been renamed in file {}".format(n_rename,file.get_name()))   

        
                             
def open_source_file(path, cache=None):
    """
    Uses chardet to autodetect encoding and open the file in the correct encoding.
    """
    from chardet.universaldetector import UniversalDetector
    
    # use cache first
    if cache and path in cache.detected_encodings:
        return open(path, 'r', encoding=cache.detected_encodings[path], errors='replace')
    
    detector = UniversalDetector()
    
    from itertools import islice
    with open(path, 'rb') as f:
        first_one_hundred_lines = islice(f, 100)
        for line in first_one_hundred_lines:
            detector.feed(line)
            if detector.done: 
                break
    detector.close()

    encoding = detector.result['encoding']
   
    # caching
    if cache:  
        cache.detected_encodings[path] = encoding

    log.debug('File %s has %s as detected encoding' % (path, encoding))

    return open(path, 'r', encoding=encoding, errors='replace')
