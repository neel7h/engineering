'''
Created on 18 oct. 2014

@author: MRO
'''
from symbols import Database, Schema, Table, View, Procedure, Function
from cast.analysers import CustomObject, create_link, log

class SAPDatabase(Database):
    
    def __init__(self):
        Database.__init__(self)
        self.current_parent = None

    def register_symbol(self, symbol):
        """
        Register an object into a database/schema based on fullname
        
        return the schema in which object was added
        """
        schema_name = self.get_schema_name()
        if symbol.name == symbol.fullname or not symbol.fullname:
            
            symbol.fullname = "%s.%s" % (schema_name, symbol.name)
            
        # create schema if needed
        schema = self.find_symbol(schema_name, [Schema])
        if not schema:
            
            schema = Schema()
            schema.name = schema_name
            schema.fullname = schema_name
            
            self.add_symbol(schema_name, schema)
            
            # in case of xxl save the used threshold on schema
            if self.tablesize:
                schema.xxl_size = self.xxl_treshold
                schema.xxs_size = self.xxs_threshold
                           
        # finally add it to the correct schema
        schema.add_symbol(symbol.name, symbol)
        symbol.parent = schema
        symbol.file = self.current_file
        
        if isinstance(symbol, Table):
            schema.list_of_tables.append(symbol)

        # update gdprIndicator to make sure you can check it at the column level
        # the case SchemaName.TableName
        if isinstance(symbol, Table) and self.gdprIndicator and (symbol.fullname.lower() in self.tablesWithGdprIndicator \
                                                                 or '%s.*' % (schema.name) in  self.tablesWithGdprIndicator):
            symbol.gdprIndicator.update(self.gdprIndicator)
        # the case *.TableName and *.*
        elif isinstance(symbol, Table) and self.gdprIndicator \
            and ('%s.%s' %('*', symbol.name.lower()) in self.tablesWithGdprIndicator \
                 or '*.*' in self.tablesWithGdprIndicator):
            symbol.gdprIndicator.update(self.gdprIndicator)  
        # the case when TableName is specified or the wildcard * is replacing TableName
        elif isinstance(symbol, Table) and self.gdprIndicator \
            and (symbol.name.lower() in self.tablesWithGdprIndicator \
                 or '*' in self.tablesWithGdprIndicator):
            symbol.gdprIndicator.update(self.gdprIndicator)
        # gdpr is activated but not for this one
        elif len(self.tablesWithGdprIndicator)> 0:
            # The column is not concerned by the GDPR legislation
            # Put the default value for gdpr Indicator : Not concerned
            symbol.gdprIndicator = 'Not concerned'
                        
        if isinstance(symbol, (Table, View)):
            try:
                if self.tablesize[symbol.fullname.lower()] >= self.xxl_treshold:
                    symbol.is_xxl = True
                    symbol.xxl_size = self.tablesize[symbol.fullname.lower()]
                    log.info('Table %s is considered as XXL' %symbol.fullname)
            except:
                try:
                    if symbol.xxl_size >= self.xxl_treshold:
                        symbol.is_xxl = True
                        log.info('Table %s is considered as XXL' %symbol.fullname)
                except (TypeError, KeyError):
                    pass
            
            try:
                if self.tablesize[symbol.fullname.lower()] <= self.xxs_threshold:
                    symbol.is_xxs = True
                    symbol.xxs_size = self.tablesize[symbol.fullname.lower()]
                    log.info('Table %s is considered as XXS' % symbol.fullname)
            except:
                try:
                    if symbol.xxs_size <= self.xxs_threshold:
                        symbol.is_xxs = True
    #                   print('Table ', symbol.fullname , ' is considered as XXS, xxs_threshold is ', self.xxs_threshold)
                        log.info('Table %s is considered as XXS' % symbol.fullname)
                except (TypeError, KeyError):
                    pass

        return schema

class SAPTable(Table):
    
    def __init__(self):
        Table.__init__(self)

    def save(self, file):
        return

class SAPView(View):
    
    def __init__(self):
        View.__init__(self)

    def save(self, root):
        return

class SAPMethodFunction(Function):
    type_name = 'CAST_SAP_MethodSQLScriptFunction'
    
    def set_parent(self, parent):
        self.parent = parent
        
    def save(self, root=None):    
        """Save the object"""
        if not self.name or self.kb_symbol:
            # primary key added in alter statement
            if self.kb_symbol and self.primaryKey:
                self.kb_symbol.save_property('SQLScript_HasPrimaryKey.hasPrimaryKey', self.primaryKey)
            return
        
        result = CustomObject()
        result.set_type(self.type_name)
        result.set_name(self.name)
        
        result.set_parent(self.parent.kb_symbol)
        self.unique_fullname = self.parent.kb_symbol.get_fullname() + '/SQLSCRIPT'

        result.set_fullname(self.unique_fullname)
        result.set_guid(self.unique_fullname)
        result.save()
        
        bm = self.parent.kb_symbol.get_positions()[-1]
        
        create_link('callLink', self.parent.kb_symbol, result, bm)

        self.kb_symbol = result

        result.save_position(bm)
        
#         if self.header_comments:
#             result.save_property('comment.commentBeforeObject', self.header_comments)
#   
#         if self.body_comments:            
#             result.save_property('comment.sourceCodeComment', self.body_comments)                         
         
#         result.save_property('metric.LeadingCommentLinesCount', self.header_comments_line_count)
#         result.save_property('metric.BodyCommentLinesCount', self.body_comments_line_count)        
#         result.save_property('metric.CodeLinesCount', self.number_of_lines)         

#         if self.type_name in ('SQLScriptTableSynonym', 'SQLScriptSynonym', 'SQLScriptViewSynonym', 'SQLScriptFunctionSynonym', 'SQLScriptProcedureSynonym', 'SQLScriptPackageSynonym', 'SQLScriptTypeSynonym'):
#             result.save_property('checksum.CodeOnlyChecksum', self.checksum)
        if self.checksum:   
            result.save_property('checksum.CodeOnlyChecksum', self.checksum)
                   
        if hasattr(self, 'xxl_size') and self.xxl_size:
#            print('self.xxl_size is :', self.xxl_size)
            try:
                result.save_property('SQLScript_WithNumberOfRows.numberOfRows', self.xxl_size)
            except:
                # SQLSCRIPT-213 : OverflowError: Python int too large to convert to C long
                if self.xxl_size >= 4294967295:
                    result.save_property('SQLScript_WithNumberOfRows.numberOfRows', 2147483647)

        if hasattr(self, 'xxs_size') and self.xxs_size:
#            print('self.xxs_size is :', self.xxs_size)
            result.save_property('SQLScript_WithNumberOfRows.numberOfRowsXXS', self.xxs_size)
            
    def __repr__(self):
        return 'SAP method Function ' + self.name 

class SAPMethodProcedure(Procedure):
    type_name = 'CAST_SAP_MethodSQLScriptProcedure'
    
    def set_parent(self, parent):
        self.parent = parent
        
    def save(self, root=None):    
        """Save the object"""
        if not self.name or self.kb_symbol:
            # primary key added in alter statement
            if self.kb_symbol and self.primaryKey:
                self.kb_symbol.save_property('SQLScript_HasPrimaryKey.hasPrimaryKey', self.primaryKey)
            return
        
        result = CustomObject()
        result.set_type(self.type_name)
        result.set_name(self.name)
        
        result.set_parent(self.parent.kb_symbol)
        self.unique_fullname = self.parent.kb_symbol.get_fullname() + '/SQLSCRIPT'

        result.set_fullname(self.unique_fullname)
        result.set_guid(self.unique_fullname)
        result.save()
        
        bm = self.parent.kb_symbol.get_positions()[-1]
        
        create_link('callLink', self.parent.kb_symbol, result, bm)

        self.kb_symbol = result

        result.save_position(bm)
        
#         if self.header_comments:
#             result.save_property('comment.commentBeforeObject', self.header_comments)
#   
#         if self.body_comments:            
#             result.save_property('comment.sourceCodeComment', self.body_comments)                         
         
#         result.save_property('metric.LeadingCommentLinesCount', self.header_comments_line_count)
#         result.save_property('metric.BodyCommentLinesCount', self.body_comments_line_count)        
#         result.save_property('metric.CodeLinesCount', self.number_of_lines)         

#         if self.type_name in ('SQLScriptTableSynonym', 'SQLScriptSynonym', 'SQLScriptViewSynonym', 'SQLScriptFunctionSynonym', 'SQLScriptProcedureSynonym', 'SQLScriptPackageSynonym', 'SQLScriptTypeSynonym'):
#             result.save_property('checksum.CodeOnlyChecksum', self.checksum)
        if self.checksum:   
            result.save_property('checksum.CodeOnlyChecksum', self.checksum)
                   
        if hasattr(self, 'xxl_size') and self.xxl_size:
#            print('self.xxl_size is :', self.xxl_size)
            try:
                result.save_property('SQLScript_WithNumberOfRows.numberOfRows', self.xxl_size)
            except:
                # SQLSCRIPT-213 : OverflowError: Python int too large to convert to C long
                if self.xxl_size >= 4294967295:
                    result.save_property('SQLScript_WithNumberOfRows.numberOfRows', 2147483647)

        if hasattr(self, 'xxs_size') and self.xxs_size:
#            print('self.xxs_size is :', self.xxs_size)
            result.save_property('SQLScript_WithNumberOfRows.numberOfRowsXXS', self.xxs_size)
            
    def __repr__(self):
        return 'SAP method Procedure ' + self.name 
