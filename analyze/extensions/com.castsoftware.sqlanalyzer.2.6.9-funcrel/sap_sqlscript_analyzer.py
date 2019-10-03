import cast.analysers.abap
from cast.analysers import create_link, Bookmark, log
from cast.application import open_source_file
from symbols import Table, View
from sap_sqlscript_symbols import SAPDatabase, SAPTable, SAPView
from sqlscript_parser import create_symbols_sap, analyse_symbols
from variant import Variant
from collections import OrderedDict
import traceback
import os
from lxml import etree

class ABAP(cast.analysers.abap.Extension):
    """
    Parse ...
    """
    def __init__(self):
        self.objectsToSave = []
        self.sapTables = OrderedDict()  # key = table name, value = obj
#         self.sapUnresolvedTables = OrderedDict()  # key = table name, value = obj
        self.sapPackages = OrderedDict()  # key = package name, value = obj
        self.lastSapTablesFile = None
        self.firstUnsavedTableSaved = False
        self.sapProject = None
        self.sapUresolvedFolder = None
        self.guids = {}
        self.databaseProcedureMethods = []
        self.guids = {}
        self.unresTables = {}
        self.sapPackagesHierarchy = {}
        
    def start_analysis(self, execution_unit):
        log.debug('start_analysis')
        self.nbTables = 0
        self.nbUnresTables = 0
        self.nbLinks = 0
        log.debug(str(execution_unit.get_source_files()))
        log.debug(str(execution_unit.get_source_projects()))
        
    def start_database_procedure(self, o):
        log.info('registering database procedure ' + str(o.get_fullname()))
        o.isProcedure = True
        self.databaseProcedureMethods.append(o)
        
    def start_database_function(self, o):
        log.info('registering database function ' + str(o.get_fullname()))
        o.isProcedure = False
        self.databaseProcedureMethods.append(o)
        
    def start_sap_unresolved_folder(self, o):
        log.debug('start SAP unresolved folder ' + o.get_name())
        self.sapUresolvedFolder = o
        
    def start_sap_unresolved_table(self, o):
        log.debug('start unresolved table ' + o.get_name())
        o.file = self.lastSapTablesFile
        o.saved = True
        tbl = SAPTable()
        tbl.is_sap = True
        tbl.name = o.get_name()
        tbl.fullname = o.get_fullname()
        tbl.kb_symbol = o
        self.sapTables[o.get_name()] = tbl
        
    def create_package(self, o):
        log.debug('create package ' + o.get_name())
        self.sapPackages[o.get_name()] = o
        
    def start_sap_table(self, o):
        log.debug('start SAP table ' + o.get_name())
        o.file = self.lastSapTablesFile
        o.saved = False
        tbl = SAPTable()
        tbl.is_sap = True
        tbl.name = o.get_name()
        tbl.fullname = o.get_fullname()
        tbl.kb_symbol = o
        self.sapTables[o.get_name()] = tbl
        
    def start_sap_view(self, o):
        log.debug('start SAP view ' + o.get_name())
        o.file = self.lastSapTablesFile
        o.saved = False
        tbl = SAPView()
        tbl.is_sap = True
        tbl.name = o.get_name()
        tbl.fullname = o.get_fullname()
        tbl.kb_symbol = o
        self.sapTables[o.get_name()] = tbl
        
    def complete_table_or_view(self, o):
        log.debug('complete table or view ' + o.get_name())
        if o.get_name() in self.sapTables:
            tbl = self.sapTables[o.get_name()]
            tbl.kb_symbol.saved = True
        
    def createObject(self, operationName, parentObject, file, pos):
        
        operation_object = cast.analysers.CustomObject()
        operation_object.set_type('CAST_ABAP_Newobject')
        operation_object.set_name(operationName)
        operation_object.set_parent(parentObject)
        try:
            operationFullname = parentObject.get_fullname() + '/newObject'
        except:
            try:
                operationFullname = parentObject.get_name() + '/newObject'
            except:
                operationFullname = parentObject.fullname + '/newObject'
        if not operationFullname in self.guids:
            self.guids[operationFullname] = 0
        else:
            nr = self.guids[operationFullname] + 1
            self.guids[operationFullname] = nr
            operationFullname = operationFullname + '_' + str(nr)
                
        operation_object.set_fullname(operationFullname)
        operation_object.set_guid(operationFullname)
        self.objectsToSave.append(operation_object)
        operation_object.save()
        if file:
            operation_object.save_position(pos)
        return operation_object

    def start_sap_project(self, p):
        log.debug('start_sap_project')
        self.sapProject = p

    def end_full_parsing(self):
        log.debug('end_full_parsing')
        for databaseProcedureMethod in self.databaseProcedureMethods:
            try:
                pos = databaseProcedureMethod.get_positions()[-1]
                log.info('Parsing ' + pos.get_file().get_path())
                txt = open_source_file(pos.get_file().get_path(), pos)
                self.analyze_sql_script(txt, databaseProcedureMethod, pos.get_file(), pos.get_begin_line(), databaseProcedureMethod.isProcedure)
            except:
                log.info('Internal issue occured, some sql links could be missing (' + pos.get_file().get_path() + ').')
                log.debug('%s' % traceback.format_exc())
        log.info(str(self.nbTables) + ' tables created')
        log.info(str(self.nbUnresTables) + ' unresolved tables created')
        log.info(str(self.nbLinks) + ' links created')

    def analyze_sql_script(self, txt, databaseProcedureMethod, file, beginLine, procedure = True):
        if procedure:
            kw = 'SAP_SQLSCRIPT'
        else:
            kw = 'SAP_SQLSCRIPT_FUNCTION'
        index = txt.find('.')
        nbLines = txt[:index].count('\n')
        index2 = txt.rfind('ENDMETHOD')
        sourceCode = '\n' * ( beginLine + nbLines - 3 ) + kw + ' ' + databaseProcedureMethod.get_name() + ' as\n'
        sourceCode += 'Begin\n'
        sourceCode += txt[index + 1 : index2]
        sourceCode += ( 'end ' + kw + ';' )
        sourceCode = sourceCode.replace("\n*", "\n--")
        log.debug(sourceCode)
        database = SAPDatabase()
        database.current_file = file
        database.current_parent = databaseProcedureMethod
        database.declared_schema_name = 'SAP_SCHEMA'
        
        result = list(create_symbols_sap(text=sourceCode, database=database))
        
        for tbl in self.sapTables.values():
            database.register_symbol(tbl)
        
        database.resolve_pending_references()
        list(analyse_symbols(sourceCode, database, variant=Variant.sapsqlscript))

        referencesByLinkType = {}
        referencesByLinkType['useSelectLink'] = result[0].select_references
        self.nbLinks += len(result[0].select_references)
        referencesByLinkType['useInsertLink'] = result[0].insert_references
        self.nbLinks += len(result[0].insert_references)
        referencesByLinkType['useDeleteLink'] = result[0].delete_references
        self.nbLinks += len(result[0].delete_references)
        referencesByLinkType['useUpdateLink'] = result[0].update_references
        self.nbLinks += len(result[0].update_references)
        
        for selectRefs in referencesByLinkType.values():
            for selectRef in selectRefs:
                refs = selectRef.reference
                if not refs:
                    continue
                for ref in refs:
                    if not ref.kb_symbol.saved:
                        newTbl = self.create_table(ref.kb_symbol, isinstance(ref, SAPView))
                        newTbl.saved = True
                        ref.kb_symbol = newTbl

        database.save()
        database.save_symbol_links()

        for linkType, selectRefs in referencesByLinkType.items():
            for selectRef in selectRefs:
                refs = selectRef.reference
                if not refs:
                    types = selectRef.types
                    if Table in types or View in types:
                        token = selectRef.tokens[0]
                        self.createLinkToUnresolvedTable(selectRef, linkType, result[0].kb_symbol, Bookmark(file, token.get_begin_line(), token.get_begin_column(), token.get_end_line(), token.get_end_column()))
        
        return result

    def create_table(self, tbl, view = False):
        
        pos = tbl.get_position()

        if not self.sapPackagesHierarchy:
            self.get_packages_hierarchy(os.path.dirname(pos.get_file().get_path()))

        newTbl = cast.analysers.CustomObject()
        if view:
            newTbl.set_type('SAPView')
        else:
            newTbl.set_type('SAPTable')
        newTbl.set_name(tbl.get_name())
        packageName = self.find_package_name(tbl.get_name(), pos.get_file().get_path(), view)
        package = self.create_sap_package(packageName)
        newTbl.set_parent(package)
        if view:
            fullname = 'SAP_VIEW/' + tbl.get_name()
        else:
            fullname = 'SAP_TABLE/' + tbl.get_name()
        if not fullname in self.guids:
            self.guids[fullname] = 0
        else:
            nr = self.guids[fullname] + 1
            self.guids[fullname] = nr
            fullname = fullname + '_' + str(nr)
        log.debug('createObject ' + fullname)
                
        newTbl.set_fullname(fullname)
        newTbl.set_guid(fullname)
        newTbl.save()
        self.nbTables += 1;
        newTbl.save_position(pos)
        return newTbl

    def get_packages_hierarchy(self, dirname):
        
        def get_packages(topNode, parents = []):

            package_name = topNode.get('name')
            log.debug('get_packages ' + package_name)
            if parents:
                log.debug('self.sapPackagesHierarchy ' + str(parents))
                self.sapPackagesHierarchy[package_name] = parents
                
            for node in topNode.findall("PACKAGE"):
                newparents = []
                if parents:
                    newparents.extend(parents)
                newparents.append(package_name)
                get_packages(node, newparents)
            log.debug('end get_packages ')
            
        log.debug('get_packages_hierarchy ')
        files = os.listdir(dirname)
        for _file in files:
            basename = os.path.basename(_file)
            if basename.endswith('.sap.xml') and basename.startswith('SAP_TABLES_PACKAGES_'):
                path = os.path.join(os.path.abspath(dirname), basename)
                try:
                    tree = etree.parse(path)
                        
                    for node0 in tree.xpath("/PACKAGES"):
                        for node1 in node0.findall("PACKAGE"):
                            get_packages(node1)
                except:
                    log.info('Packages file is malformed: ' + _file)
                    log.debug('Packages file is malformed %s ' % traceback.format_exc())
    
    def get_unresolved_table(self, tableName):
        
        tableNameUpper = tableName.upper()
        
        if tableNameUpper in self.unresTables:
            return self.unresTables[tableNameUpper]
        
        if tableNameUpper in self.sapTables:
            return self.sapTables[tableNameUpper].kb_symbol
        
        newTbl = cast.analysers.CustomObject()
        newTbl.set_type('CAST_ABAP_SAPUnresolvedTable')
        newTbl.set_name(tableNameUpper)
        if not self.sapUresolvedFolder:
            self.sapUresolvedFolder = self.create_sap_unresolved_folder()
            if not self.sapUresolvedFolder:
                return None
            
        newTbl.set_parent(self.sapUresolvedFolder)
        fullname = 'unresolvedObjects/SAP_TABLE/' + tableNameUpper
        if not fullname in self.guids:
            self.guids[fullname] = 0
        else:
            nr = self.guids[fullname] + 1
            self.guids[fullname] = nr
            fullname = fullname + '_' + str(nr)
        log.debug('create unresolved table ' + fullname)
                
        newTbl.set_fullname(fullname)
        newTbl.set_guid(fullname)
        newTbl.save()
        self.nbUnresTables += 1;
        self.unresTables[tableNameUpper] = newTbl
        return newTbl
    
    def createLinkToUnresolvedTable(self, ref, linkType, caller, bm):
        
        unresTable = self.get_unresolved_table(ref.name)
        if not unresTable:
            return
        create_link(linkType, caller, unresTable, bm)

    def create_sap_unresolved_folder(self):

        if not self.sapProject:
            return None
        
        folder = cast.analysers.CustomObject()
        folder.set_type('SAPUnresolvedFolder')
        folder.set_name('unresolvedFolder')
        folder.set_parent(self.sapProject)
        fullname = self.sapProject.get_name()+"/unresolvedFolder"
        log.debug('createObject ' + fullname)
                
        folder.set_fullname(fullname)
        folder.set_guid(fullname)
        folder.save()
        return folder
        
    def create_sap_package(self, name, parentPackages = None):
        
        log.info('create sap package ' + name + str(parentPackages))

        if name in self.sapPackages:
            return self.sapPackages[name]
        
        if name in self.sapPackagesHierarchy:
            parent_name = self.sapPackagesHierarchy[name][-1]
            if len(self.sapPackagesHierarchy[name]) >= 2:
                parentPackage = self.create_sap_package(parent_name, self.sapPackagesHierarchy[name][:-2])
            else:
                parentPackage = self.create_sap_package(parent_name)
        else:
            parentPackage = self.sapProject
        
        package = cast.analysers.CustomObject()
        package.set_type('CAST_ABAP_Package')
        package.set_name(name)
        package.set_parent(parentPackage)
        fullname = 'SAP_PACKAGE/' + name.upper()
        log.debug('createObject ' + fullname)
                
        package.set_fullname(fullname)
        package.set_guid(fullname)
        package.save()
        self.sapPackages[name] = package
        
        return package
    
    def find_package_name(self, tableName, filepath, view = False):
        txt = open_source_file(filepath)
        if view:
            index = txt.find('<VIEW Name="' + tableName + '"')
        else:
            index = txt.find('<TABLE Name="' + tableName + '"')
        if index < 0:
            return None
        index = txt.rfind('<PACKAGE Name="', 0, index)
        if index < 0:
            return None
        index2 = txt.find('"', index + 15)
        if index2 < 0:
            return None
        packageName = txt[index + 15 : index2]
        log.debug('packageName ' + packageName)
        return packageName
        
def open_source_file(path, pos = None):
    """
    Equivalent of python open(path) that autotdetects encoding. 
    
    :rtype: file 
    """
    from chardet.universaldetector import UniversalDetector
    
    detector = UniversalDetector()
    with open(path, 'rb') as f:
        count = 0
        for line in f:
            detector.feed(line)
            count += 1
            if detector.done or count > 100: 
                break
    detector.close()

    encoding = detector.result['encoding']
   
    result = open(path, 'r', encoding=encoding, errors='replace').read()
    
    line = 1
    if pos:
        fromLine = pos.get_begin_line()
        fromCol = pos.get_begin_column()
        toLine = pos.get_end_line()
        toCol = pos.get_end_column()
        _from = -1
        while line < fromLine:
            _from = result.find('\n', _from + 1)
            line += 1
        if _from >= 0:
            _from += fromCol
        _to = _from
        while line < toLine:
            _to = result.find('\n', _to + 1)
            line += 1
        if _to >= 0:
            _to += toCol
    else:
        _from = 0
        _to = -1
        
    return result[_from:_to]
