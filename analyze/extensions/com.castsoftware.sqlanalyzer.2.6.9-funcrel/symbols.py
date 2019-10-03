'''
Created on 18 oct. 2014

@author: MRO
'''
from cast.analysers import Bookmark, CustomObject, create_link, log
from collections import defaultdict
from lxml import etree
from traceback import format_exc
from variant import Variant
from light_parser import Node
from binascii import crc32
from sqlscript_lexer import Comment
from logger import warning

class ResolutionScope:
    """
    Symbol Scope
    
    Stores and resolve symbols.
    """
    def __init__(self, parent=None):
        
        self.name = None
        self.parent_scope = parent
        self.symbols = defaultdict(list)
        self.sub_scopes = set()
        
        # references to be resolved latter
        self.references = []

    def add_element(self, name, symbol):
        """
        Register a symbol but do not do additional parent scoping
        assume case insensitivity
        """
        if name:
            self.symbols[name.lower()].append(symbol)
        
        

    # bug seen on DB2, McKinsey sources
    # GUID duplicate found : SQLScriptTableColumn  'SQLScriptTableColumn?McKinseyDuplicateGUID_60525.STREAM.CHANGELOG1.ID' UNIVERSAL_CACHE : DUPLICATE OBJECTS NAME IN SOURCE: Source File not found    
    # we should have unique GUIDs for columns on the same schema
    # so, added upper_case for than, because we should not change the case in the GUID of the columns
    def add_symbol(self, name, symbol, make_unique=True, upper_case=True):
        """
        Register a symbol and calculate a unique local name for it
        assume case insensitivity
        """
        duplicate_count = None 

        if name:
            
            duplicate_count = len(self.find_symbols(name, [type(symbol)]))
            
            self.symbols[name.lower()].append(symbol)
            
        # sub scope chaining
        if isinstance(symbol, ResolutionScope):
            
            self.sub_scopes.add(symbol)
            symbol.parent_scope = self
            symbol.name = name
        
        if make_unique:
            unique_name = name.upper() if upper_case else name
            
            if duplicate_count:
                unique_name = '%s<%s>' % (unique_name, duplicate_count)
            
            symbol.unique_name = unique_name
            
            return unique_name
            
    def find_symbol(self, name, types=[]):
        """
        Search for a symbol
        assume case insensitivity
        """
        if not name:
            return None
        
        symbols = self.find_symbols(name, types)

        if symbols:
            return symbols[0]
        else:
            return None
    
    def find_symbols(self, name, types=[], parameters=None, defaults=None):
        """
        Search for a symbol
        assume case insensitivity
        """
        if not name:
            return None
        if name.lower() in self.symbols:
            symbols = self.symbols[name.lower()]
            if types:
                # the case of overloading 
#                 log.info('parameters %s, defaults %s ' % (parameters, defaults))
                if defaults:
                    return [symbol for symbol in symbols if isinstance(symbol, tuple(types)) and getattr(symbol, 'count_parameters') == parameters and getattr(symbol, 'default_parameters') == defaults]
                elif parameters and not defaults:
                    return [symbol for symbol in symbols if isinstance(symbol, tuple(types)) and getattr(symbol, 'count_parameters') == parameters]
                else:
                    return [symbol for symbol in symbols if isinstance(symbol, tuple(types))]
            else:
                return symbols
        else:
            return []
    
    def add_reference(self, reference):
        """Add a reference to be resolved"""
        self.references.append(reference)
        
        def get_current_file(scope):
            if scope.parent_scope:
                return get_current_file(scope.parent_scope)
            return  scope.current_file
        try:
            reference.file = get_current_file(self)
        except AttributeError:
            pass

    def resolve(self):
        pass
    
    # added parameters for the overloading
    def resolve_reference(self, reference, unique=False, parameters=None, defaults=None):
        """
        resolve a quoted identifier in the context of this scope
        """
        result = []
        
        parent = reference.get_parent_identifier()
        if parent:
            # we have a a.b identifier, start by resolving a
            
            scope = self.resolve_reference(parent, True, parameters, defaults)
        
            if scope and isinstance(scope, ResolutionScope):
                # then find b in that a
                result = scope.find_symbols(reference.get_name(), reference.get_types(), parameters, defaults)
            else:
                return []

        else:
            # we have a simple 'a' identifier
            # search locally
            # strip whitespaces from the end for the cases when in the sql file we have "A " and A which are the same in DB2
            if Variant.db2 and reference.get_name():
                result = self.find_symbols(reference.get_name().rstrip(' '), reference.get_types(), parameters, defaults)
            else:
                result = self.find_symbols(reference.get_name(), reference.get_types(), parameters, defaults)
            if not result and self.parent_scope:
                # search in parent scopes 
                result = self.parent_scope.resolve_reference(reference, False, parameters, defaults)
        
        # filter locally inside the same 'file' if applicable
        if result and len(result) > 1:
            potentials = []
            for symbol in result:
                if not hasattr(symbol, 'file') or not symbol.file or not hasattr(reference, 'file') or not reference.file or symbol.file == reference.file:
                    potentials.append(symbol)
            result = potentials
        
        if unique and result:
            return result[0]
                
        return result
        
    def resolve_references(self, references, parameters=None, defaults=None):
        """
        Resolve all given references
        """
        for reference in references:
            reference.reference = self.resolve_reference(reference, False, parameters=None, defaults=None)

        # clean
        references = []

    def resolve_pending_references(self):
        """
        Resolve all pending references
        """
        self.resolve_references(self.references)
        
        for scope in self.sub_scopes:
            scope.resolve_pending_references()

        for symbols_list in self.symbols.values():
            
            for symbol in symbols_list:
                
                # additional resolution
                symbol.resolve()

    def save_symbol_links(self):
        
        # recurse
        for scope in self.sub_scopes:
            scope.save_symbol_links()

        # save links for all symbols
        for symbols_list in self.symbols.values():
            
            for symbol in symbols_list:
                # links
                try:
                    symbol.save_links()
                except:
                    warning('SQL-003', 'Issue during link saving %s' % format_exc())



class Unknown:
    """
    Unknown statement.
    """
    def __init__(self):
        self.text = None
        self.name = None
        self.fullname = None

    def save(self, parent):
        return
    
    def use_ast(self):
        return  # necessary for create_symbols

    def __repr__(self):
        return 'UnknownStatement'


class Object:
    
    def __init__(self):
        self.kb_symbol = None
        self.ast = None
        self.name = None
        self.fullname = None
        self.file = None
        self.parent = None
        self.inherit_references = []
        self.use_references = []

        # a 'local unique name' calculated when having two objects with same name and parent
        # see ResolutionScope.add_symbol
        self.unique_name = None
        self.unique_fullname = None
        
        self.begin_line = None
                
        # dependent on ast
        self.begin_line = None
        self.header_comments = None
        self.body_comments = None
        self.header_comments_line_count = 0
        self.body_comments_line_count = 0
        self.number_of_lines = 0            
        self.checksum = None      

        self.primaryKey = None
        self.count_parameters = None
        self.default_parameters = None
        self.count_quoted = None
        
        self.external_name = None
        self.external_position = None
        self.language = None
        
                
        # bookmark
        self.bookmark = None

    def resolve(self):
        if self.ast:
            try:
                if not self.count_parameters and self.ast.count_parameters :
                    self.count_parameters = self.ast.count_parameters
            except AttributeError:
                pass
            
            try:
                if not self.default_parameters and self.ast.default_parameters:
                    self.default_parameters = self.ast.default_parameters
            except AttributeError:
                pass
        pass

    def is_function(self):
        return False

    def get_header_comments(self):
        if self.ast:
            header_comments = self.ast.get_header_comments()
            return ''.join(comment.text for comment in header_comments)
        
    def get_body_comments(self):
        if self.ast:
            body_comments = self.ast.get_body_comments()
            return ''.join(comment.text for comment in body_comments)

    def get_header_comments_line_count(self):
        result = 0
        prev_line = 0
        if self.ast:
            for comment in self.ast.get_header_comments():
                result += comment.text.count('\n')

        if result == 0 and self.ast:
            for comment in self.ast.get_header_comments():
                if comment.get_begin_line() == comment.get_end_line() and prev_line != comment.get_begin_line():
                    prev_line = comment.get_begin_line()
                    result += 1

        return result

    def get_header_lines_count(self):
        result = 0
        prev_line = 0
        last_comment_line = 0
        startto = 0
        if self.ast:
            for comment in self.ast.get_header_comments():
                result += comment.text.count('\n')
                if comment.type == Comment.Single:
                    last_comment_line = comment.get_begin_line()
                else:
                    last_comment_line = comment.get_end_line()
                    

            def get_begin_line_object(nodes):
                start_to = 0
                lines = nodes.get_children()
                line = lines.look_next()
                if line == 'CREATE':
                    start_to = line.get_begin_line()
                    try:
                        lines.move_to('PACKAGE')
                        line = lines.look_next()
                        # except package and type bodies
                        if line == 'BODY':
                            start_to = 0
                    except:
                        try:
                            lines.move_to('PACKAGE')
                            line = lines.look_next()
                            # except package and type bodies
                            if line == 'BODY':
                                start_to = 0
                        except StopIteration:
                            pass

                    return (start_to)
        
        if result == 0 and self.ast:
            for comment in self.ast.get_header_comments():
                if comment.get_begin_line() == comment.get_end_line() and prev_line != comment.get_begin_line():
                    prev_line = comment.get_begin_line()
                    result += 1
                if comment.type == Comment.Single:
                    last_comment_line = comment.get_begin_line()
                else:
                    last_comment_line = comment.get_end_line()

        if self.ast and result > 0:
            startto = get_begin_line_object(self.ast)
            if not startto: 
                return result
            if startto > 0 and startto > last_comment_line + 1 :
                result += (startto - last_comment_line) - 1

        return result
                    
    def get_body_comments_line_count(self):
        result = 0
        prev_line = 0
        if self.ast:
            for comment in self.ast.get_body_comments():
                result += comment.text.count('\n')
                
        if result == 0 and self.ast:
            for comment in self.ast.get_body_comments():
                if comment.get_begin_line() == comment.get_end_line() and prev_line != comment.get_begin_line():
                    prev_line = comment.get_begin_line()
                    result += 1
                
        return result

    def get_number_of_lines(self):
        result = 0
        commented_lines_list = set()
        list_of_lines = set()
        if self.ast:
                
            def append_list_of_lines(nodes): 
                for i in nodes.get_children():
                    if isinstance(i, Node):
                        append_list_of_lines(i)
                    else:
                        list_of_lines.add(i.get_begin_line())        
                return
        
            result = self.ast.get_line_count()
            result -=  self.get_header_lines_count()

            def commented_lines(nodes):
                for i in nodes.get_body_comments():
                    commented_lines_list.add(i.get_begin_line())
                    if isinstance(i, Node):
                        commented_lines(i)

                return
            
            def count_body_comments_full_line_count ():  
                count_body_comments = 0
                prev_line = 0
                prev_column = 0
                calc = 0
                calc_line = 0
                prev_comment_star = False
                for comment in self.ast.get_body_comments():
                    if comment.type == Comment.Multiline and prev_line != comment.get_begin_line():
                        prev_line = 0 
                        prev_column = 0
                    if (comment.get_begin_column() > 1 and comment.type == Comment.Single) or (comment.type == Comment.Multiline and comment in ( '*/', '/*')):
                        if comment.type == Comment.Single and comment.get_begin_line() == prev_line and comment.get_begin_column() == prev_column:
                            continue
                        #cbc = self.check_behind_comment(self.ast, comment.get_begin_line())
                        if comment.get_begin_line() not in list_of_lines and comment.type == Comment.Single:  
                            count_body_comments += 1
                        elif comment.get_begin_line() not in list_of_lines and comment.type == Comment.Multiline and comment == '*/' and (prev_comment_star or comment.get_begin_line() == prev_line):
                            count_body_comments += 1
                            prev_comment_star = False
                        else:
                            if comment.type == Comment.Multiline:
                                prev_line = comment.get_begin_line() 
                                prev_column = comment.get_end_column()
                            continue
                    elif comment.type == Comment.Multiline and (comment.get_end_line() - comment.get_begin_line()) + 1 > comment.text.count('\n') and comment.get_end_line() != comment.get_begin_line():
                        if comment.get_end_line() == comment.get_begin_line() + 1:
                            calc = 1
                        elif calc > 0 and calc_line == comment.get_begin_line(): 
                            count_body_comments += ((comment.get_end_line() - comment.get_begin_line()) - 1)
                            calc = 0
                            calc_line = 0
                        else:
                            calc = (comment.get_end_line() - comment.get_begin_line()) + 1
                            calc_line = comment.get_end_line()
                        count_body_comments += calc
                    else:
                        if comment.text.count('\n') > 0:
                            count_body_comments += comment.text.count('\n')
                
                    if comment == '*':
                        prev_comment_star = True
                    if comment.type == Comment.Multiline:
                        prev_line = comment.get_begin_line() 
                        prev_column = comment.get_end_column()
                            
                if count_body_comments == 0:
                    prev_line = 0
                    for comment in self.ast.get_body_comments():
                        if comment.type == Comment.Multiline and comment.get_begin_line() == comment.get_end_line() and prev_line != comment.get_begin_line():
                            prev_line = comment.get_begin_line()
                            count_body_comments += 1
                        elif comment.type == Comment.Single and comment.get_begin_line() not in list_of_lines:                          
                            count_body_comments += 1
                      
                return count_body_comments

            def count_empty_line(node):
                def check_for_comment(comment_line):
                    return 1  if comment_line in commented_lines_list else 0

                def count_details (nodes, begin_line, end_line):
                    t = 0
                    for line in range(begin_line , end_line):
                        cfc = check_for_comment(line)
                        if line not in list_of_lines and cfc == 0:
                            t += 1
                        elif cfc > 0 and t > 0:
                            t -= cfc
                    return t
                        
                result = 0 
                
                for token in node.children:
                    if isinstance(token, Node):
                        result += count_empty_line(token)
                    
                    elif token.is_whitespace():
                        t = 0
                        number_of_lf = 0
                        t = count_details(self.ast, token.get_begin_line(), token.get_end_line())
                        if t == 0:
                            number_of_lf = token.text.count('\n')
                        elif t > 0:
                            result += t
                        elif number_of_lf > 1:
                            result += (number_of_lf - 1)
                        elif number_of_lf == 1 and token.get_begin_column() == 1 and token.get_end_line() == token.get_begin_line() + 1:
                            result += 1
                    elif token.type != Comment.Multiline:
                        
                        number_of_additional_lf = token.text.count('\n\n')
                        if number_of_additional_lf > 1:
                            result += (number_of_additional_lf - 1)
        
                return result

            commented_lines(self.ast)
            append_list_of_lines(self.ast)  
            result -= count_body_comments_full_line_count()
            result -= count_empty_line(self.ast)

        return result
    
    def get_code_only_checksum(self):
        """
        Default behaviour, overridable.
        """
        if self.ast:
            return self.ast.get_code_only_crc()
            
    def save_links(self):
        if len(self.inherit_references) > 0:
            # add inheritLink for the case of : create type TOTO under TATA
            for term in self.inherit_references:
                calee = term[0]
                create_link('inheritLink', self.kb_symbol, calee.kb_symbol, term[1])

        if len(self.use_references) > 0:
            # add inheritLink for the case of : create type TOTO under TATA
            for term in self.use_references:
                calee = term[0]
                create_link('useLink', self.kb_symbol, calee.kb_symbol, term[1])
            
    def save_violations(self):
        pass
        
    def use_ast(self):
        """
        Use the ast to get 
        - checksum
        - comments
        - line of code
        - position
    - ...
        """
 
        if self.file:
            self.bookmark = self.create_bookmark(self.file)
         
        if not self.ast:
            return
        
        try:
            if self.parent.ast:
                self.parent.use_ast()
        except:
            # issues with ipss_dump
            return
                  
           
        self.begin_line = self.ast.get_begin_line()
                
        self.header_comments = self.get_header_comments()
        self.body_comments = self.get_body_comments()
        self.header_comments_line_count = self.get_header_comments_line_count()
        self.body_comments_line_count = self.get_body_comments_line_count()
        
        self.number_of_lines = self.get_number_of_lines()
           
        if self.type_name in ('SQLScriptTableSynonym', 'SQLScriptSynonym', 'SQLScriptViewSynonym', 'SQLScriptFunctionSynonym', 'SQLScriptProcedureSynonym', 'SQLScriptPackageSynonym', 'SQLScriptTypeSynonym'): 
            self.checksum = 0
        else:self.checksum = self.get_code_only_checksum() 

        # language
        try:
            if hasattr(self.ast, 'language'):
                if self.ast.language: 
                    self.language = self.ast.language
        except:
            log.info('Internal issue when registering SQLScriptExternalProgram.language, because of %s' % format_exc())
            pass

        # external program name
        try:
            if hasattr(self.ast, 'external_name'):
                if self.ast.external_name: 
                    self.external_name = self.ast.external_name
        except:
            log.info('Internal issue when registering SQLScriptExternalProgram.external_name, because of %s' % format_exc())
            pass
        
        try:
            if hasattr(self.ast, 'external_position'):
                if self.ast.external_position: 
                    self.external_position = self.ast.external_position
        except:
            log.info('Internal issue when registering SQLScriptExternalProgram.external_position, because of %s' % format_exc())
            pass
                        
        try:
            if hasattr(self.ast, 'longest_lenght_line'):
                if self.ast.longest_lenght_line:
                    self.longest_lenght_line = self.ast.longest_lenght_line        
        except:
            log.info('Internal issue when registering SQLScript_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine, because of %s' % format_exc())
            pass
        
        try:
            # primary key added in create table statement
            if hasattr(self.ast, 'primaryKey'):
                if self.ast.primaryKey: 
                    self.primaryKey = self.ast.primaryKey
                    # this part might be deprecated !!
        except:
            log.info('Internal issue when registering SQLScript_HasPrimaryKey.hasPrimaryKey, because of %s' % format_exc())
            pass
        
        try:
            if hasattr(self.ast, 'count_parameters'):
                if self.ast.count_parameters:
                    self.count_parameters = self.ast.count_parameters
        except:
            log.info('Internal issue when registering SQLScript_Metric_CountParameters.countParameters, because of %s' % format_exc())
            pass

        try:
            if hasattr(self.ast, 'parameters'):
                if self.ast.parameters:
                    self.parameters = self.ast.parameters
        except:
            log.info('Internal issue when registering parameters, because of %s' % format_exc())
            pass

        try:
            if hasattr(self.ast, 'default_parameters'):
                if self.ast.default_parameters:
                    self.default_parameters = self.ast.default_parameters
        except:
            log.info('Internal issue when registering default_parameters, because of %s' % format_exc())
            pass
                        
        try:
            if hasattr(self.ast, 'count_quoted'):
                if self.ast.count_quoted: 
                    self.count_quoted = self.ast.count_quoted
        except:
            log.info('Internal issue when registering SQLScript_Metric_CountQuotedIdentifiers.numberOfQuotedIdentifiers, because of %s' % format_exc())
            pass
                
        self.ast = None

    def use_ast_for_dynamic_code(self, begin_line, begin_column, end_line, end_column):
        """
        Use the ast to get 
        - checksum
        - comments
        - line of code
        - position
    - ...
        """
 
        if self.file:
            self.bookmark = Bookmark(self.file, begin_line, begin_column, end_line, end_column)
         
        if not self.ast:
            return
        
        try:
            if self.parent.ast:
                self.parent.use_ast()
        except:
            # issues with ipss_dump
            return
                  
           
        self.begin_line = begin_line          
        self.header_comments = self.get_header_comments()
        self.body_comments = self.get_body_comments()
        self.header_comments_line_count = self.get_header_comments_line_count()
        self.body_comments_line_count = self.get_body_comments_line_count()
        
        self.number_of_lines = self.get_number_of_lines()
        
        self.checksum = self.get_code_only_checksum()    

        try:
            if hasattr(self.ast, 'language'):
                if self.ast.language: 
                    self.language = self.ast.language
        except:
            log.info('Internal issue when registering SQLScriptExternalProgram.language, because of %s' % format_exc())
            pass

        try:
            if hasattr(self.ast, 'external_name'):
                if self.ast.external_name: 
                    self.external_name = self.ast.external_name
        except:
            log.info('Internal issue when registering SQLScriptExternalProgram.external_name, because of %s' % format_exc())
            pass

        try:
            if hasattr(self.ast, 'external_position'):
                if self.ast.external_position: 
                    self.external_position = self.ast.external_position
        except:
            log.info('Internal issue when registering SQLScriptExternalProgram.external_position, because of %s' % format_exc())
            pass
        
        try:
            if hasattr(self.ast, 'longest_lenght_line'):
                if self.ast.longest_lenght_line: 
                    self.longest_lenght_line = self.ast.longest_lenght_line        
        except:
            log.info('Internal issue when registering SQLScript_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine, because of %s' % format_exc())
            pass
                
        try:
            # primary key added in create table statement
            if hasattr(self.ast, 'primaryKey'):
                if self.ast.primaryKey: 
                    self.primaryKey = self.ast.primaryKey
                    # this part might be deprecated !!
        except:
            log.info('Internal issue when registering SQLScript_HasPrimaryKey.hasPrimaryKey, because of %s' % format_exc())
            pass
        
        try:
            if hasattr(self.ast, 'count_parameters'):
                if self.ast.count_parameters:
                    self.count_parameters = self.ast.count_parameters
        except:
            log.info('Internal issue when registering SQLScript_Metric_CountParameters.countParameters, because of %s' % format_exc())
            pass

        try:
            if hasattr(self.ast, 'default_parameters'):
                if self.ast.default_parameters:
                    self.default_parameters = self.ast.default_parameters
        except:
            log.info('Internal issue when registering default_parameters, because of %s' % format_exc())
            pass

        try:
            if hasattr(self.ast, 'parameters'):
                if self.ast.parameters:
                    self.parameters = self.ast.parameters
        except:
            log.info('Internal issue when registering parameters, because of %s' % format_exc())
            pass
                        
        try:
            if hasattr(self.ast, 'count_quoted'):
                if self.ast.count_quoted: 
                    self.count_quoted = self.ast.count_quoted
        except:
            log.info('Internal issue when registering SQLScript_Metric_CountQuotedIdentifiers.numberOfQuotedIdentifiers, because of %s' % format_exc())
            pass
                
        self.ast = None         
            
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
        if self.fullname and isinstance(self, Schema):
            result.set_fullname(self.fullname)
        
        if self.parent:
            # save parent if needed
            if not self.parent.kb_symbol:
                self.parent.save(root)
            result.set_parent(self.parent.kb_symbol)
            
            self.unique_fullname = self.parent.unique_fullname
            
        else:                  
            result.set_parent(root)
            self.unique_fullname = root.get_project().get_name()

        if not self.unique_name:
            self.unique_name = self.name
        
        self.unique_fullname = "%s.%s" % (self.unique_fullname, self.unique_name)
        
        # bug seen on DB2, McKinsey sources
        # GUID duplicate found : SQLScriptTableColumn  'SQLScriptTableColumn?McKinseyDuplicateGUID_60525.STREAM.CHANGELOG1.ID' UNIVERSAL_CACHE : DUPLICATE OBJECTS NAME IN SOURCE: Source File not found    
        # we should have unique GUIDs for columns on the same schema
        if isinstance(self, Column):
            self.unique_fullname = self.parent.parent.add_symbol(self.unique_fullname, self, make_unique=True, upper_case=False)
        
        guid = "%s?%s" % (self.type_name, self.unique_fullname)
        
        result.set_guid(guid)
        result.save()

        self.kb_symbol = result

        if not self.parent:
            create_link('parentLink', self.kb_symbol, root.get_project())
            
        if self.file:
            result.save_position(self.bookmark)
        
        if self.header_comments:
            result.save_property('comment.commentBeforeObject', self.header_comments)
  
        if self.body_comments:            
            result.save_property('comment.sourceCodeComment', self.body_comments)      
             
        result.save_property('metric.LeadingCommentLinesCount', self.header_comments_line_count)
        result.save_property('metric.BodyCommentLinesCount', self.body_comments_line_count)        
        result.save_property('metric.CodeLinesCount', self.number_of_lines)         

        if self.type_name in ('SQLScriptTableSynonym', 'SQLScriptSynonym', 'SQLScriptViewSynonym', 'SQLScriptFunctionSynonym', 'SQLScriptProcedureSynonym', 'SQLScriptPackageSynonym', 'SQLScriptTypeSynonym'):
            result.save_property('checksum.CodeOnlyChecksum', self.checksum)
        elif self.checksum:   
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
            
# Kept for testing drop/rename table        
#         if hasattr(self, 'count_dropped_tables'):
#             result.save_property('SQLScript_Metric_Dropped_Objects.count_dropped_tables', self.count_dropped_tables)
# 
#         if hasattr(self, 'count_renamed_tables'):
#             result.save_property('SQLScript_Metric_Renamed_Objects.count_renamed_tables', self.count_renamed_tables)
        try:
            if self.external_name:
                result.save_property('SQLScriptExternalProgram.external_name', self.external_name)
        except (RuntimeError, AttributeError):
            pass

        try:
            if self.external_position:
                result.save_property('SQLScriptExternalProgram.external_position', self.external_position)
        except (RuntimeError, AttributeError):
            pass
                        
        try:
            if self.language:
                result.save_property('SQLScriptExternalProgram.language', self.language)
        except (RuntimeError, AttributeError):
            pass
                    
        try:
            if self.longest_lenght_line:
                result.save_property('SQLScript_Metric_lengthOfTheLongestLine.lengthOfTheLongestLine', self.longest_lenght_line)
        except (RuntimeError, AttributeError):
            pass
        
        if self.primaryKey:
            result.save_property('SQLScript_HasPrimaryKey.hasPrimaryKey', self.primaryKey)
            

               
        if self.count_parameters:
            result.save_property('SQLScript_Metric_CountParameters.countParameters', self.count_parameters)


        if self.count_quoted:
            result.save_property('SQLScript_Metric_CountQuotedIdentifiers.numberOfQuotedIdentifiers', self.count_quoted)               

        return result

    def create_bookmark(self, _file):
        if self.ast:
            return Bookmark(_file, self.ast.get_begin_line(), self.ast.get_begin_column(), self.ast.get_end_line(), self.ast.get_end_column())
        else:
            return Bookmark(_file,1,1,-1,-1)

    def get_bookmark_dynamic_code(self, identifier, begin_line, begin_column=None, end_line=None, end_column=None):
        if not begin_column and not end_column:
            begin = identifier.tokens[0]
            end = identifier.tokens[-1]
            new_begin_line = begin.get_begin_line() + begin_line -1 
            new_end_line =  end.get_end_line() + begin_line -1
            return Bookmark(self.file, new_begin_line, begin.get_begin_column(), new_end_line, end.get_end_column())
        else:
            return Bookmark(self.file, begin_line, begin_column, end_line, end_column)
                
    def get_bookmark(self, identifier):
        begin = identifier.tokens[0]
        end = identifier.tokens[-1]
        return Bookmark(self.file, begin.get_begin_line(), begin.get_begin_column(), end.get_end_line(), end.get_end_column())

    def get_token_bookmark(self, identifier):
        return Bookmark(self.file, identifier.get_begin_line(), identifier.get_begin_column(), identifier.get_end_line(), identifier.get_end_column())
    
class WithObjectReferences(Object):
    """
    USed for object having references to table, etc...
    """

    def __init__(self):
        Object.__init__(self)
        self.write_columns = []
        self.select_columns = []
        self.select_star_columns = []
        self.write_star_columns = []
        self.select_references = []
        self.insert_references = []
        self.update_references = []
        self.delete_references = []
        self.select_dynamic_references = ([])
        self.insert_dynamic_references = ([])
        self.update_dynamic_references = ([])
        self.delete_dynamic_references = ([])
        self.select_parameters_references = ([])
        self.begin_line = 0
        self.end_line = 0
        self.selects = []
        self.controls = []
        self.dexecutes = []
        self.gotos = []
        

    def save_column_links(self):
        if not self.kb_symbol:
            return
        
        def create_columns_links(references, link_type):
            for identifier in references:
                try:
                    if not identifier.tokens:
                        continue
                    bookmark = self.get_bookmark(identifier)
                except AttributeError:
                    bookmark = self.get_token_bookmark(identifier)

                if identifier.reference:
                    callee = identifier.reference
                    try:
                        create_link(link_type, self.kb_symbol, callee.kb_symbol, bookmark)
                    except:
                        log.debug('Internal issue with create columns link, because of %s' % format_exc())

        def create_star_columns_links(references, link_type):
            for identifier in references:
                bookmark = identifier[1]
                if identifier[0].reference:
                    callee = identifier[0].reference
                    try:
                        create_link(link_type, self.kb_symbol, callee.kb_symbol, bookmark)
                    except:
                        log.debug('Internal issue with create all columns link, because of %s' % format_exc())

        try:
            create_columns_links(self.write_columns, 'accessWriteLink')
        except:
            log.info('Internal issue with accessWriteLink %s, because of %s' % (self.write_columns,  format_exc()))

                                                         
        try:
            create_columns_links(self.select_columns, 'accessReadLink')
        except:
            log.info('Internal issue with accessReadLink %s, because of %s' % (self.select_columns,  format_exc()))

        try:
            create_star_columns_links(self.write_star_columns, 'accessWriteLink')
        except:
            log.info('Internal issue with accessWriteLink all %s, because of %s' % (self.write_star_columns,  format_exc()))


        try:
            create_star_columns_links(self.select_star_columns, 'accessReadLink')
        except:
            log.info('Internal issue with accessReadLink all %s, because of %s' % (self.select_star_columns,  format_exc()))

        # detach memory
        self.write_columns = []
        self.select_columns = []
        self.select_star_columns = []  
        self.write_star_columns = []         
                             
    def save_links(self):
        if not self.kb_symbol:
            return
        
        def create_links(references, link_type):
            for identifier in references:
                if not identifier.tokens:
                    continue
                if self.begin_line > 0 and self.end_line > 0:
                    bookmark =  self.get_bookmark_dynamic_code(identifier, self.begin_line)
                else:  bookmark = self.get_bookmark(identifier)
                
                if identifier.reference:
                    callee = identifier.reference
                    if isinstance(identifier.reference, Method):
                        try:
                            create_link('callLink', self.kb_symbol, callee.kb_symbol, bookmark)
                        except:
                            log.info('Internal issue with create link, because of %s' % format_exc())
                    else:
                        try:
                            for callee in identifier.reference:
                                created_link_type = link_type
            
                                # override to call for functions                    
                                if callee.is_function() or isinstance(callee, Type):
                                    created_link_type = 'callLink'
                            
                                try:
                                    create_link(created_link_type, self.kb_symbol, callee.kb_symbol, bookmark)
                                except:
                                    log.info('Internal issue with create link, because of %s' % format_exc())
                    
                                # handle implicit trigger calls
                                if hasattr(callee,'triggers'): 
                                
                                    if link_type == 'useInsertLink':
                                        for trigger in callee.triggers['INSERT']:
                                            create_link('callLink', self.kb_symbol, trigger.kb_symbol, bookmark)
                                
                                    if link_type == 'useUpdateLink':
                                        for trigger in callee.triggers['UPDATE']:
                                            create_link('callLink', self.kb_symbol, trigger.kb_symbol, bookmark)
            
                                    if link_type == 'useDeleteLink':
                                        for trigger in callee.triggers['DELETE']:
                                            create_link('callLink', self.kb_symbol, trigger.kb_symbol, bookmark)
                        except TypeError:
                            try:
                                create_link(link_type, self.kb_symbol, callee.kb_symbol, bookmark)
                            except:
                                log.info('Internal issue with create link, because of %s' % format_exc())

        def create_dynamic_links(references, link_type):
            for identifiers in references:
                identifier = identifiers[0]
                begin_line = identifiers[1]
                end_line = identifiers[2]
                begin_column = identifiers[3]
                end_column = identifiers[4]
                if not identifier.tokens:
                    continue

                if begin_column > 0 and end_column > 0:
                    bookmark =  self.get_bookmark_dynamic_code(identifier, begin_line, begin_column, end_line, end_column)
                else:  bookmark = self.get_bookmark(identifier)
                
                if identifier.reference:
                    if isinstance(identifier.reference, Method):
                        callee = identifier.reference
                        try:
                            create_link('callLink', self.kb_symbol, callee.kb_symbol, bookmark)
                        except:
                            log.info('Internal issue with create link, because of %s' % format_exc())
                    else:
                        for callee in identifier.reference:
#                             log.info('link_type %s , bookmark is : %s, callee.kb_symbol %s' % (link_type, bookmark, callee.name))                            
                            created_link_type = link_type
        
                            # override to call for functions                    
                            if callee.is_function():
                                created_link_type = 'callLink'
                        
                            try:
                                create_link(created_link_type, self.kb_symbol, callee.kb_symbol, bookmark)
                            except:
                                log.info('Internal issue with create link, because of %s' % format_exc())
                
                            # handle implicit trigger calls
                            if hasattr(callee,'triggers'): 
                            
                                if link_type == 'useInsertLink':
                                    for trigger in callee.triggers['INSERT']:
                                        create_link('callLink', self.kb_symbol, trigger.kb_symbol, bookmark)
                            
                                if link_type == 'useUpdateLink':
                                    for trigger in callee.triggers['UPDATE']:
                                        create_link('callLink', self.kb_symbol, trigger.kb_symbol, bookmark)
        
                                if link_type == 'useDeleteLink':
                                    for trigger in callee.triggers['DELETE']:
                                        create_link('callLink', self.kb_symbol, trigger.kb_symbol, bookmark)

        def create_parameters_links(references, link_type):
            for identifier in references:
                if not identifier[0].tokens:
                    continue
                if self.begin_line > 0 and self.end_line > 0:
                    bookmark =  self.get_bookmark_dynamic_code(identifier[0], self.begin_line)
                else:  bookmark = self.get_bookmark(identifier[0])
                
                # identifier.reference
                if identifier[2]:
                    if isinstance(identifier[0].reference, Method):
                        callee = identifier[2]
                        cnt_default = (0 if getattr(callee, 'default_parameters') is None else getattr(callee, 'default_parameters'))
                        cnt_parameters = (0 if getattr(callee, 'count_parameters') is None else getattr(callee, 'count_parameters'))
                        called_parameters = cnt_parameters - cnt_default
                        if identifier[1] >= called_parameters and identifier[1] <= cnt_parameters:
                            try:
                                create_link('callLink', self.kb_symbol, callee.kb_symbol, bookmark)
                            except:
                                log.info('Internal issue with create link, because of %s' % format_exc())
                    else:
                        for callee in identifier[2]:
                            cnt_default = (0 if getattr(callee, 'default_parameters') is None else getattr(callee, 'default_parameters'))
                            cnt_parameters = (0 if getattr(callee, 'count_parameters') is None else getattr(callee, 'count_parameters'))
                            called_parameters = cnt_parameters - cnt_default
#                             log.info('called_parameters %s, identifier[1] %s, cnt_parameters %s' %(called_parameters, identifier[1], cnt_parameters))
                            if identifier[1] >= called_parameters and identifier[1] <= cnt_parameters :
                                # override to call for functions                    
                                if callee.is_function() or isinstance(callee, Type):
                                    created_link_type = 'callLink'
                            
                                try:
                                    create_link(created_link_type, self.kb_symbol, callee.kb_symbol, bookmark)
                                except:
                                    log.info('Internal issue with create link, because of %s' % format_exc())    
                                                      
                                                           
        try:
            create_links(self.select_references, 'useSelectLink')
        except:
            log.info('Internal issue with self.select_references %s, because of %s' % (self.select_references,  format_exc()))

        try:
            create_links(self.insert_references, 'useInsertLink')
        except:
            log.info('Internal issue with self.insert_references %s, because of %s' % (self.insert_references, format_exc()))

        try:
            create_links(self.update_references, 'useUpdateLink')
        except:
            log.info('Internal issue with self.update_references %s, because of %s' % (self.update_references, format_exc()))

        try:
            create_links(self.delete_references, 'useDeleteLink')
        except:
            log.info('Internal issue with self.delete_references %s, because of %s' % (self.delete_references, format_exc()))

        # dynamic links
        try:
            create_dynamic_links(self.select_dynamic_references, 'useSelectLink')
        except:
            log.info('Internal issue with self.select_dynamic_references %s, because of %s' % (self.select_dynamic_references,  format_exc()))

        try:
            create_dynamic_links(self.insert_dynamic_references, 'useInsertLink')
        except:
            log.info('Internal issue with self.insert_dynamic_references %s, because of %s' % (self.insert_dynamic_references, format_exc()))

        try:
            create_dynamic_links(self.update_dynamic_references, 'useUpdateLink')
        except:
            log.info('Internal issue with self.update_dynamic_references %s, because of %s' % (self.update_dynamic_references, format_exc()))

        try:
            create_dynamic_links(self.delete_dynamic_references, 'useDeleteLink')
        except:
            log.info('Internal issue with self.delete_dynamic_references %s, because of %s' % (self.delete_dynamic_references, format_exc()))

        # the case of overloading
        try:
            create_parameters_links(self.select_parameters_references, 'useSelectLink')
        except:
            log.info('Internal issue with self.select_references %s, because of %s' % (self.select_parameters_references,  format_exc()))

        # detach memory
        self.select_references = []
        self.insert_references = []
        self.update_references = []
        self.delete_references = []
        self.select_dynamic_references = ([])
        self.insert_dynamic_references = ([])
        self.update_dynamic_references = ([])
        self.delete_dynamic_references = ([])
        self.select_parameters_references = ([])
        
    def save_violations(self):
        """
        Save the violations coming from the SelectResult
        """
        max_depth = 0
        numberOfUnion = 0
        numberOfUnionAndUnionAll = 0
        number_of_tables = 0
        maxControlStatementsNestedLevels = 0   
        new_begin_line = None
        new_begin_column = None

        if len(self.gotos) > 0:
            self.kb_symbol.save_property('CAST_MetricAssistant_Metric_useOfGoto.numberOfGoto', len(self.gotos)) 
        for control in self.controls:
            try:
                if control.has_empty_catch:
                    
                    self.kb_symbol.save_violation('SQLScript_Metric_EmptyCatchBlock.has_empty_catch', 
                                                  Bookmark(self.file, control.get_begin_line(), control.get_begin_column(), control.get_end_line(), control.get_end_column()))
            except:
                print('there is no has_empty_catch')
                pass
            try:
                if control.maxControlStatementsNestedLevels:
                    maxControlStatementsNestedLevels = max(control.maxControlStatementsNestedLevels, maxControlStatementsNestedLevels)
            except: 
                print('there is no maxControlStatementsNestedLevels')
                pass

        for dexecute in self.dexecutes:
            try:
                if dexecute.count_dynamicSQL:
                    
                    self.kb_symbol.save_violation('SQLScript_Metric_DynamicSQL.count_dynamicSQL', 
                                                  Bookmark(self.file, dexecute.get_begin_line(), dexecute.get_begin_column(), dexecute.get_end_line(), dexecute.get_end_column()))
            except:
                print('there is no count_dynamicSQL')
                pass

            
        if maxControlStatementsNestedLevels > 0:
            self.kb_symbol.save_property('SQLScript_Metric_StatementsNestedLevels.maxControlStatementsNestedLevels', maxControlStatementsNestedLevels) 
                                   
        for select in self.selects:
            
            try:
                if select.has_or_on_the_same_identifier:
                    
                    self.kb_symbol.save_violation('SQLScript_Metric_OrClausesTestingEquality.has_or_on_the_same_identifier', 
                                                  Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except:
                print('there is no has_or_on_the_same_identifier')
                pass
            
            try:
                if select.has_non_ansi_operator:
                    
                    self.kb_symbol.save_violation('SQLScript_Metric_NonAnsiOperators.has_non_ansi_operator', 
                                                  Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except:
                print('there is no has_non_ansi_operator')
                pass
            
            try:
                if select.has_distinct:
                    
                    self.kb_symbol.save_violation('SQLScript_Metric_DistinctModifiers.has_distinct', 
                                                  Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except:
                print('there is no has_distinct')
                pass
            
            try:
                if select.has_independent_exists:
                    new_begin_line = select.new_begin_line
                    new_begin_column = select.new_begin_column
                    if new_begin_line and new_begin_column:
                        self.kb_symbol.save_violation('SQLScript_Metric_ExistsIndependentClauses.has_independent_exists', 
                                                      Bookmark(self.file, new_begin_line, new_begin_column, select.get_end_line(), select.get_end_column()))
                    else:
                        self.kb_symbol.save_violation('SQLScript_Metric_ExistsIndependentClauses.has_independent_exists', 
                                                  Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except:
                print('there is no has_independent_exists')
                pass
            
            try:
                if select.number_of_tables:
                    number_of_tables = max(select.number_of_tables, number_of_tables)
            except: 
                print('there is no number_of_tables')
                pass

            try:
                if select.has_NotInNotExists:
                    self.kb_symbol.save_violation('SQLScript_Metric_UseMinusExcept.has_NotInNotExists', 
                                              Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except: 
                print('there is no has_NotInNotExists')
                pass
    
            try:
                if select.missingParenthesis:
                    self.kb_symbol.save_violation('SQLScript_Metric_MissingParenthesisInsertClause.missingParenthesis', 
                                              Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except: 
                print('there is no missingParenthesis')
                pass
         
            try:
                if select.numberOfUnion:
                    numberOfUnion = max(select.numberOfUnion, numberOfUnion)
                if select.numberOfUnionAndUnionAll:
                    numberOfUnionAndUnionAll = max(select.numberOfUnionAndUnionAll, numberOfUnionAndUnionAll)
            except: 
                print('there is no numberOfUnion or numberOfUnionAndUnionAll')
                pass
                
            try:
                if select.hasGroupByClause:
                    self.kb_symbol.save_violation('SQLScript_Metric_HasGroupByClause.hasGroupByClause', 
                                              Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except: 
                print('there is no hasGroupByClause')
                pass
                
            try:
                if select.has_nonAnsiJoin:
                    self.kb_symbol.save_violation('SQLScript_Metric_HasNonAnsiJoin.hasNonAnsiJoin', 
                                              Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except: 
                print('there is no has_nonAnsiJoin')
                pass

            try:
                if select.has_numbers:
                    self.kb_symbol.save_violation('SQLScript_Metric_HasNumbersInOrderBy.hasNumbers', 
                                              Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except: 
                print('there is no has_numbers')
                pass
            
            try:
                if select.has_naturalJoin:
                    self.kb_symbol.save_violation('SQLScript_Metric_NaturalJoin.isNaturalJoin', 
                                              Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except: 
                print('there is no has_naturalJoin')
                pass
                
            try:
                if select.has_nonSARG:
                    self.kb_symbol.save_violation('SQLScript_Metric_NonSARGable.isNonSARGable', 
                                              Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except: 
                print('there is no has_nonSARG')
                pass
                
            try:
                if select.has_maxDepth:
                    max_depth = max(select.maxDepth, max_depth)
            except: 
                print('there is no has_maxDepth')
                pass
             
            try:                       
                if select.has_cartesian_product:
                   
                    self.kb_symbol.save_violation('SQLScript_Metric_UseOfCartesianProduct.number', 
                                                  Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except:
                print('there is no has_maxDepth')
                pass
            
            try:
                if select.has_cartesian_product_xxl:
                    
                    self.kb_symbol.save_violation('SQLScript_Metric_UseOfCartesianProductXXL.number', 
                                                  Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()))
            except:
                print('there is no has_cartesian_product_xxl')
                pass
            
            try:       
                if select.no_index_can_support:
                    
                    self.kb_symbol.save_violation('SQLScript_Metric_NoIndexCanSupport.number', 
                                                  Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()),
                                                  select.no_index_can_support_bookmarks)
            except: 
                print('there is no no_index_can_support')
                pass
            
            try:
                if select.no_index_can_support_xxl:
                    
                    self.kb_symbol.save_violation('SQLScript_Metric_NoIndexCanSupportXXL.number', 
                                                  Bookmark(self.file, select.get_begin_line(), select.get_begin_column(), select.get_end_line(), select.get_end_column()),
                                                  select.no_index_can_support_xxl_bookmarks)
            except:
                print ('there is no no_index_can_support_xxl')
                pass
            
        if number_of_tables > 0:
            self.kb_symbol.save_property('SQLScript_Metric_CountTables.number_of_tables', number_of_tables)
                                    
        if max_depth > 0:
            self.kb_symbol.save_property('CAST_SQL_Metric_MaxNestedSubqueriesDepth.maxDepth', max_depth) 

        if numberOfUnion > 0:
            self.kb_symbol.save_property('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnion', numberOfUnion) 
        if numberOfUnionAndUnionAll > 0:
            self.kb_symbol.save_property('SQLScript_Metric_UnionAllInsteadOfUnion.numberOfUnionAndUnionAll', numberOfUnionAndUnionAll) 

        self.selects = []
        self.controls = []
        self.dexecutes = []
        self.gotos = []
                        
class Database(ResolutionScope):
    """
    A container for schema, not saved
    """
    def __init__(self):
        ResolutionScope.__init__(self)
        
        # default schema name
        self.current_schema_name = "DEFAULT"
        # name of the current schema declared by code : USE , set search_path etc... 
        self.declared_schema_name = None
        self.current_file = None
        self.tablesize = {}
        self.xxl_treshold = 100000
        self.xxs_threshold = 10
        self.variables = []
        self.gdprIndicator = {}
        self.tablesWithGdprIndicator = set()
    
    def get_schema_name(self):
        """
        Return the name of the schema to use for non qualified elements. 
        """
        if self.declared_schema_name:
            return self.declared_schema_name
        
        return self.current_schema_name

    def get_variables_name(self):
        return self.variables
        
    def load_tablesize(self, path):
        """
        schema/table row > 100 000
        
        @todo:
        - not sure here is the good place?
        """
        from analyser import open_source_file
        log.info('Start Loading Table Size')
        with open_source_file(path) as f: 
            for line in f:
                line = line.rstrip() #removes trailing whitespace and '\n' chars
        
                if "=" not in line: continue #skips blanks and comments w/o =
                if line.startswith("#"): continue #skips comments which contain =
        
                k, v = line.split("=", 1)
                if k.lower() in ['xxl_treshold', 'xxl_threshold']:
                    self.xxl_treshold = int(v)
                    log.info('Setting XXL threshold to %s' % self.xxl_treshold)
                elif k.lower() in ['xxs_treshold', 'xxs_threshold']:
                    self.xxs_threshold = int(v)
                    log.info('Setting XXS threshold to %s' % self.xxs_threshold)
                elif v.isnumeric():
                    log.info('    Load table %s size %s' % (k, int(v)))
                    self.tablesize[k.lower()] = int(v)  

        if self.tablesize:
            return
                            
        try:
            tree = etree.parse(path)
            
            for node in tree.xpath("//schema"):
                schema_name = node.get('name')
                for table in node.xpath(".//table"):
                    table_name = table.get('name')
                    if table.get('rows'):
                        table_size = int(table.get('rows'))
                    else:
                        table_size = 0
                    log.info('    Load table %s size %s' % ('%s.%s' % (schema_name.lower(), table_name.lower()), table_size))
                    self.tablesize['%s.%s' % (schema_name.lower(),  table_name.lower())] = table_size
        except Exception as malformed_table_size:
            print('    Table size file is malformed ' , malformed_table_size)
            log.info('    Table size file is malformed %s' % malformed_table_size)
        except:
            log.info('    Table size file is malformed %s' % format_exc())
            print('    Table size file is malformed ' , format_exc())
            
        log.info('End Loading Table Size')

    def load_gdpr(self, path):
        """
        
        Schema1.Table1.Col1=GDPRHard
        Schema1.Table1.Col2=GDPRSoft
        Schema1.Table1.Col3=Security
        Schema1.Table1.Col4=NonGDPR
        Schema1.Table1.Col5=Unused
        
        @todo:
        - not sure here is the good place?
        """
        from analyser import open_source_file
        log.info('Start Loading Columns GDPR Indicators')
        with open_source_file(path) as f: 
            for line in f:
                line = line.rstrip() #removes trailing whitespace and '\n' chars
        
                if "=" not in line: continue #skips blanks and comments w/o =
                if line.startswith("#"): continue #skips comments which contain =

                k, v = line.split("=", 1) 
                if k and v:
                    log.info('    Load column %s GDPR indicator %s' % (k, v))
                    self.gdprIndicator[k.lower()] = v
                    
                    table_full_name, _ = line.rsplit(".", 1)
                    self.tablesWithGdprIndicator.add(table_full_name.lower()) if (table_full_name.lower() not in self.tablesWithGdprIndicator) else None

            return
            
        log.info('End Loading Columns GDPR Indicators')
        
                
    def register_symbol(self, symbol):
        """
        Register an object into a database/schema based on fullname
        
        return the schema in which object was added
        """
        schema_name = self.get_schema_name()
        # strip whitespaces from the end for the cases when in the sql file we have "A " and A which are the same in DB2
        if schema_name:
            schema_name = schema_name.rstrip(' ')
        
        if symbol.name == symbol.fullname or not symbol.fullname:
            symbol.fullname = "%s.%s" % (schema_name, symbol.name)
        
        elif symbol.fullname:
            schema_name = symbol.fullname[:len(symbol.fullname) - 1 - len(symbol.name)]
            # for sqlserver : change default schema name
            if schema_name == 'dbo':
                self.current_schema_name = 'dbo'  
            elif schema_name:
                # strip whitespaces from the end for the cases when in the sql file we have "A " and A which are the same in DB2
                schema_name = schema_name.rstrip(' ')
                self.current_schema_name = self.current_schema_name.rstrip(' ')            

        # A.B.C, should apply only on DB2 case
        if (not self.current_schema_name == 'dbo') and schema_name.count('.') == 1:
            _, schema_name = schema_name.split('.')

        schema = self.find_symbol(schema_name, [Schema])
                
        # create schema if needed
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
        symbol.parent_scope = schema
        
        if isinstance(symbol, Table):
            schema.list_of_tables.append(symbol)

        if isinstance(symbol, Type):
            schema.object_types.add(symbol)

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
                        
        if isinstance(symbol, (Table, View, Synonym, TableSynonym, ViewSynonym)):
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
    
    def unregister_symbol(self, symbol_to_drop):
        """
        Unregister an object from a database/schema based on fullname
        
        Presently we only allow dropping tables when defined in the 
        same file by comparing the 'file' attribute. This is in accord with commutability
    principle, i.e. our results should not depend on file loading order.
        """      
        
        for _, schema in self.symbols.items():
            schema = schema[0]            
            for _, symbol_list in schema.symbols.items(): 
                for symbol in symbol_list:             
                    if (symbol.fullname.lower() == symbol_to_drop.fullname.lower() 
                            and type(symbol) == type(symbol_to_drop)
                            and symbol.file == symbol_to_drop.file):                                                                    
                        schema.symbols[symbol_to_drop.name.lower()].remove(symbol)
                        if isinstance(symbol_to_drop,Table):                            
                            schema.count_dropped_tables += 1
                            log.debug("Dropped table : %s" % symbol_to_drop.name)
                                                                        
            # remove resulted empty list from dictionary                        
            if symbol_to_drop.name in schema.symbols:
                if len(schema.symbols[symbol_to_drop.name]) == 0:                    
                    del schema.symbols[symbol_to_drop.name]
                
    def rename_symbol(self, target, new_name):
        """
        Renames a symbol and the unique_name of affected symbols
        Only tested for tables.
        """
        if not isinstance(target,Table):
            log.debug("Object renaming only tested for Tables")
                
        for _, schema in self.symbols.items():
            schema = schema[0]                           
            symbols = schema.find_symbols(target.name, [type(target)])
            
            # for duplicated objects we remove 
            # latest added symbol            
            for symbol in reversed(symbols):                                           
                
                if not (symbol.fullname.lower() == target.fullname.lower() and symbol.file == target.file):                   
                    continue

                schema.symbols[symbol.name.lower()].remove(symbol)
                if len(schema.symbols[symbol.name]) == 0:                    
                    del schema.symbols[symbol.name]
                                      
                symbol.name = new_name
                symbol.fullname = "%s.%s" % (schema.name, new_name)
                
                self.register_symbol(symbol)
       
                if isinstance(symbol,Table):                                            
                    schema.count_renamed_tables += 1                                                                                       
                
                return

        if isinstance(target,Table):    
            log.debug("Unable to rename table : {} ".format(target.name))
            
        return 
     
    def save(self):                         
            for _, schema in sorted(self.symbols.items()):
                schema = schema[0]                     
                for _, symbol_list in sorted(schema.symbols.items()):                    
                    for symbol in symbol_list:
                        try:
                            file = symbol.file                            
                            symbol.save(file)                            
                        except:
                            if symbol.begin_line:
                                warning('SQL-003', 'At line %s, during saving %s' % (str(symbol.begin_line), symbol))
                            else:
                                warning('SQL-003', 'Saving %s' % str(symbol)) # xxx
                            warning('SQL-003', format_exc())
                                              

    def __repr__(self):
        """
        Print the structure
        """
        result = "Database\n" 
        for _, schema in self.symbols.items():
            
            result += "  " + schema[0].name + "\n"        
            
            for _, element in sorted(schema[0].symbols.items()):
                
                result += "    " + str(element[0]) + "\n"
            result +=  "   xxs_threshold: " + str(self.xxs_threshold)
            
            result +=  "   gdprIndicator: " + str(self.gdprIndicator)
        return result



class Schema(Object, ResolutionScope):
    """
    A Schema.
    """
    type_name = 'SQLScriptSchema'

    def __init__(self):
        Object.__init__(self)
        ResolutionScope.__init__(self)
        self.xxl_size = None
        self.xxs_size = None
        self.count_dropped_tables = 0
        self.count_renamed_tables = 0
        self.list_of_tables = []
        self.object_types = set()
        
    def __repr__(self):
        result = "Schema %s\n" %self.name
        for _, element in self.symbols.items():
            if type(element[0]) in [Table, View]:
                result += "    " + str(element[0]) + "    xxl_size:  " +str(element[0].xxl_size)+" , xxs_size:  " +str(element[0].xxs_size) + "\n"
            else:
                result += "    " + str(element[0]) + "\n"
        return result
        
class Package(Object, ResolutionScope):
    """
    A package.
    See http://docs.oracle.com/cd/B19306_01/server.102/b14200/statements_6006.htm
    """    
    type_name = 'SQLScriptPackage'

    def __init__(self):
        Object.__init__(self)
        ResolutionScope.__init__(self)
        self.current_schema_name = None
        self.synonyms = []
        
    def get_schema_name(self):
        return None
    
    def register_symbol(self, symbol):
        """
        Register an object.
        """
        symbol.fullname = "%s.%s" % (self.fullname, symbol.name)
        
        # add it 
        self.add_symbol(symbol.name, symbol)
        symbol.parent = self
        symbol.file = self.file
        
        return self
    
    def save(self, root):
        """
        Save the package and all procedure children
        """
        Object.save(self, root)
    
        # recurse on symbols
        for _, symbols in sorted(self.symbols.items()):
            for symbol in symbols:
                symbol.save(root)
                
    def use_ast(self):
        Object.use_ast(self)
        
        for _, symbols in self.symbols.items():
            for symbol in symbols:
                symbol.use_ast()       

    def __repr__(self):
        
        result = 'CREATE PACKAGE BODY ' + str(self.name) + ' IS '
        separator = '\n'
        for method in sorted(self.symbols.items()):

            result += separator + '        Method ' + str(method[0]) 
            
        return result
                
class Type(Object, ResolutionScope):
    """
    A type.
    https://docs.oracle.com/cd/B13789_01/appdev.101/b10807/10_objs.htm
    """    
    type_name = 'SQLScriptType'

    def __init__(self):
        Object.__init__(self)
        ResolutionScope.__init__(self)
        self.current_schema_name = None
        self.synonyms = []
        self.methods = []

    def find_methods(self, name):
        # @todo case insensitive ?
        for method in self.methods:
            if method.name == name:
                return method
            
    def find_inherited_methods(self, name):
        for object_type in self.inherit_references:
            for method in object_type[0].methods:
                if method.name == name:
                    return object_type[0].find_methods(method.name)

        for object_type in self.use_references:
            for method in object_type[0].methods:
                if method.name == name:
                    return object_type[0].find_methods(method.name)
                                    
        # recurse on super class for the case of self
        return None
       
    def get_schema_name(self):
        return None
    
    def register_symbol(self, symbol):
        """
        Register an object.
        """
        symbol.fullname = "%s.%s" % (self.fullname, symbol.name)
        
        # add it 
        self.add_symbol(symbol.name, symbol)
        symbol.parent = self
        symbol.file = self.file
        return self
    
    def save(self, root):
        """
        Save the type and all procedure children
        """
        Object.save(self, root)
    
        # recurse on symbols
        for _, symbols in sorted(self.symbols.items()):
            for symbol in symbols:
                self.methods.append(symbol)
                symbol.save(root)
                
    def use_ast(self):
        Object.use_ast(self)
        
        for _, symbols in self.symbols.items():
            for symbol in symbols:
                symbol.use_ast()    

    def __repr__(self):
        
        result = 'CREATE TYPE BODY ' + str(self.name) + ' IS '
        separator = '\n'
        for method in sorted(self.symbols.items()):

            result += separator + '        Method ' + str(method[0]) 
            
        return result
                                   
class Table(Object, ResolutionScope):
    """
    A table.
    """
    def __init__(self):
        Object.__init__(self)
        ResolutionScope.__init__(self)
        self.columns = []
        self.indexes = []
        self.constraints = []
        self.foreign_key_constraints = []
        self.kb_symbol = None
        self.is_xxl = False
        self.is_xxs = False
        self.xxl_size = None
        self.xxs_size = None
        # the map event -> triggers        
        self.triggers = defaultdict(list)
        self.hasPrimaryKey = False
        self.file = None
        self.synonyms = []
        self.gdprIndicator = {}
    
    type_name = 'SQLScriptTable'
    
    def register_column(self, column):
        self.columns.append(column)
        self.add_symbol(column.name, column, make_unique=False)

    def already_has_constraint(self, result):
        
        for index in self.indexes:
            if index.name == result.name:
                # already registered
                return True
        return False

    def register_constraint(self, constraint):
        """
        Add a PRIMARTY KEY or UNIQUE constraint or A FULLTEXT INDEX
        """
        self.add_symbol(constraint.name, constraint)
        self.indexes.append(constraint)
        self.constraints.append(constraint)
        constraint.table = self
        constraint.file = self.file
        constraint.parent = self
        # save the primaryKey attribute only if table has been registered
        if self.kb_symbol:
            if self.primaryKey:self.save(self)
        
    def register_foreign_key(self, constraint):
        """
        Add a FOREIGN KEY constraint to the table
        """
        self.add_symbol(constraint.name, constraint)
        self.foreign_key_constraints.append(constraint)
        constraint.first_table = self
        constraint.file = self.file
        constraint.parent = self
    
    def find_column(self, name):
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def find_column_insensitive(self, name):
        # the same as before but insensitive, added for AR links in CS side
        for col in self.columns:
            if col.name.lower() == name.lower():
                return col
        return None
    
    def get_indexes(self):
        """
        Returns the indexes of the table
        """
        return self.indexes

    def get_code_only_checksum(self):
        """
        Takes only 
        - table name
        - columns definitions :
          - name, type, null/not null
          
        """
        def crc(text, initial_crc = 0):
            return crc32(bytes(text.lower(), 'UTF-8'), initial_crc)  - 2**31
            
        initial_crc = crc(self.name)
        for c in self.columns:
            
            initial_crc = crc(c.name, initial_crc)
            initial_crc = crc(c.type, initial_crc)
        
        # 
        return initial_crc
        
    def save(self, file):
        result = Object.save(self, file)
        if not result:
            return
        
        for column in self.columns:
            column.parent = self
            column.save()
            
        for constraint in self.constraints:
            constraint.save(self.file)

        for constraint in self.foreign_key_constraints:
            constraint.save(self.file)
            
    def use_ast(self):
        Object.use_ast(self)
        
        for column in self.columns:
            column.parent = self
            column.use_ast()
            
        for constraint in self.constraints:
            constraint.use_ast()

        for constraint in self.foreign_key_constraints:
            constraint.use_ast()
        

    def __repr__(self):
        
        result = 'CREATE TABLE ' + str(self.name) + '('
        separator = ''
        for column in self.columns:
            
            result += separator + str(column) 
            separator = ','
        
        result += ('); Is XXL : ' + str(self.is_xxl) + ', Is XXS : ' + str(self.is_xxs) + '\n')
         
        for index in self.indexes:
            
            result += ('        ' + str(index) + '\n')

        return result
        
class View(WithObjectReferences, ResolutionScope):
    """
    A view.
    """
    def __init__(self):
        WithObjectReferences.__init__(self)
        ResolutionScope.__init__(self)
        self.columns = []
        self.query = None
        self.indexes = []
        # the map event -> triggers        
        self.triggers = defaultdict(list)
        self.is_xxl = False
        self.is_xxs = False
        self.xxl_size = None
        self.xxs_size = None    
        self.synonyms = []    
    type_name = 'SQLScriptView'

    def already_has_constraint(self, result):
        
        for index in self.indexes:
            if index.name == result.name:
                # already registered
                return True
        return False
        
    def find_column(self, name):
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def find_column_insensitive(self, name):
        # the same as before but insensitive, added for AR links in CS side
        for col in self.columns:
            if col.name.lower() == name.lower():
                return col
        return None
    
    def get_code_only_checksum(self):
        """
        Takes only 
        - view name
        - columns definitions :
          - name
        - select
        
        """
        def crc(text, initial_crc = 0):
            return crc32(bytes(text.lower(), 'UTF-8'), initial_crc)  - 2**31
        
        # name + columns
        initial_crc = crc(self.name)
        for c in self.columns:
            initial_crc = crc(c.name, initial_crc)
        
        # query...
        for token in self.query:
            initial_crc = token.get_code_only_crc(initial_crc)
        
        return initial_crc
    

    def save(self, root):
        result = Object.save(self, root)
        
        self.query = None
        
        if not result:
            return
        for column in self.columns:
            column.parent = self
            column.save()

    def __repr__(self):
        
        result = 'CREATE VIEW ' + str(self.name) + '('
        separator = ''
        for column in self.columns:
            
            result += separator + str(column) 
            separator = ','
            
        result += ')' + '\n'+ str(self.query) + '\n;' 
        return result

class Column(Object):
    """
    A column declaration.
    """
    def __init__(self):
        Object.__init__(self)
        self.type = None
        self.table = None
        self.nullable = True
        self.kb_symbol = None
        self.order = None
        self.gdprIndicator = {}
        
    def save(self):
        gdpr_is_activated = False

        try:
            if len(self.parent.gdprIndicator) > 0:
                gdpr_is_activated = True
                # The column is not concerned by the GDPR legislation
                # Default value for gdpr Indicator
                gdprIndicator_value = 'Not concerned'
        except AttributeError:
            pass

            
        result = Object.save(self)
        if not result:
            return
        if self.type:
            result.save_property('CAST_ANSISQL_Column.typeName', self.type)
            result.save_property('CAST_AST_ANSISQL_GenericDatatypeAttributes.typeName', self.type)
        if self.order:
            result.save_property('CAST_ANSISQL_ColumnOrder.order', self.order)
                    
        result.save_property('CAST_ANSISQL_Column.isNull', 1 if self.nullable else 0)

        # if GDPR has been activated than save it
        if gdpr_is_activated:
            try:
                # the case SchemaName.TableName.ColumnName
                if self.parent.gdprIndicator[result.fullname.lower()]:  
                    gdprIndicator_value = self.parent.gdprIndicator[result.fullname.lower()]
            except  (TypeError):    
                gdprIndicator_value = 'Not concerned'                                   
            except  (KeyError, AttributeError):
                try:
                    # the case *.TableName.ColumnName
                    if self.parent.gdprIndicator['%s.%s.%s' %('*', self.parent.name.lower(), result.name.lower())]:     
                        gdprIndicator_value = self.parent.gdprIndicator['%s.%s.%s' %('*', self.parent.name.lower(), result.name.lower())]      
                except  (KeyError, AttributeError):            
                    try:
                        # the case TableName.ColumnName
                        if self.parent.gdprIndicator['%s.%s' %(self.parent.name.lower(), result.name.lower())]:   
                            gdprIndicator_value = self.parent.gdprIndicator['%s.%s' %(self.parent.name.lower(), result.name.lower())]       
                    except  (KeyError, AttributeError):            
                        try:
                            # the case *.*.ColumnName
                            if self.parent.gdprIndicator['*.*.%s' %result.name.lower()]:   
                                gdprIndicator_value = self.parent.gdprIndicator['*.*.%s' % result.name.lower()]       
                        except  (KeyError, AttributeError):            
                            try:
                                # the case *.ColumnName
                                if self.parent.gdprIndicator['*.%s' %result.name.lower()]:           
                                    gdprIndicator_value = self.parent.gdprIndicator['*.%s' % result.name.lower()]
                            except  (KeyError, AttributeError):
                                # the case *.TableName.*
                                try:
                                    if self.parent.gdprIndicator['%s.%s.%s' %('*', self.parent.name.lower(), '*')]:       
                                        gdprIndicator_value = self.parent.gdprIndicator['%s.%s.%s' %('*', self.parent.name.lower(), '*')]   
                                except  (KeyError, AttributeError): 
                                    # the case TableName.*
                                    try:
                                        if self.parent.gdprIndicator['%s.%s' %(self.parent.name.lower(), '*')]:           
                                            gdprIndicator_value = self.parent.gdprIndicator['%s.%s' %(self.parent.name.lower(), '*')]
                                    except  (KeyError, AttributeError):      
                                        # the case SchemaName.*.ColumnName
                                        try:
                                            if self.parent.gdprIndicator['%s.%s.%s' %(self.parent.parent.name.lower(), '*', result.name.lower())]:           
                                                gdprIndicator_value = self.parent.gdprIndicator['%s.%s.%s' %(self.parent.parent.name.lower(), '*', result.name.lower())]  
                                        except  (KeyError, AttributeError): 
                                            # the case SchemaName.TableName.*
                                            try:
                                                if self.parent.gdprIndicator['%s.%s.%s' %(self.parent.parent.name.lower(), self.parent.name.lower(), '*')]:           
                                                    gdprIndicator_value = self.parent.gdprIndicator['%s.%s.%s' %(self.parent.parent.name.lower(), self.parent.name.lower(), '*')]  
                                            except  (KeyError, AttributeError): 
                                                # otherwise, do nothing   
                                                pass
                                        
            result.save_property('SQLScriptTableColumn.GDPR_indicator', gdprIndicator_value) 
        
    type_name = 'SQLScriptTableColumn'
        
    def __repr__(self):
        return str(self.name) + ' ' + str(self.type) + ' ' + str(self.gdprIndicator)


class ForeignKey(Object):
    """
    A foreign key
    """
    type_name = 'SQLScriptForeignKey'
    
    def __init__(self):
        Object.__init__(self)
        self.first_table = None
        self.first_table_identifier = None
        
        self.first_table_columns = []
        self.second_table = None
        self.second_table_identifier = None
        
        self.second_table_columns = []
        
        self.on_delete = False
        self.on_update = False

        self.on_delete_cascade = False
        self.on_update_cascade = False

        self.on_delete_restrict = False
        self.on_update_restrict = False

        self.on_delete_noaction = False
        self.on_update_noaction = False

        self.on_delete_setdefault = False
        self.on_update_setdefault = False

        self.on_delete_setnull = False
        self.on_update_setnull = False
                                                    
    def resolve(self):
        """
        After references have been resolved
        """
        if not self.first_table:
            self.first_table = self.first_table_identifier.get_unique_reference()   
  
        if not self.second_table:
            self.second_table = self.second_table_identifier.get_unique_reference()       

        columns1 = []
        if self.first_table:
            for column_name in self.first_table_columns:
                columns1.append(self.first_table.find_column(column_name))
        
        self.first_table_columns = columns1
        del columns1
        
        columns2 = []
        if self.second_table:
            for column_name in self.second_table_columns:
                columns2.append(self.second_table.find_column(column_name))

        self.second_table_columns = columns2
        del columns2

    def save_links(self):        
        if self.first_table_identifier:   
            try:                 
                create_link('relyonLink', self.kb_symbol, self.first_table.kb_symbol, self.get_bookmark(self.first_table_identifier))
            except AttributeError:
                pass
            
        if self.second_table:
            try:
                create_link('relyonLink', self.kb_symbol, self.second_table.kb_symbol, self.get_bookmark(self.second_table_identifier)) 
            except AttributeError:
                pass
            
        if self.first_table and self.second_table:
            create_link('referLink', self.first_table.kb_symbol, self.second_table.kb_symbol)
            
            if self.on_delete:
                referDelete = create_link('referDeleteLink', self.first_table.kb_symbol, self.second_table.kb_symbol)
                prop_delete = ""

                if self.on_delete_restrict:
                    prop_delete = 'Restrict for Delete'
                if self.on_delete_noaction:
                    prop_delete = 'No Action for Delete'           
                if self.on_delete_cascade:
                    prop_delete = 'Cascade for Delete'
                if self.on_delete_setnull:
                    prop_delete = 'Set Null for Delete' 
                if self.on_delete_setdefault:
                    prop_delete = 'Set Default for Delete'                
                if prop_delete:        
                    referDelete.save_property('SQLScript_ReferLinks_Details.details', prop_delete)

            if self.on_update:
                referUpdate = create_link('referUpdateLink', self.first_table.kb_symbol, self.second_table.kb_symbol)
                prop_update = ""
                if self.on_update_restrict:
                    prop_update = 'Restrict for Update'
                if self.on_update_noaction:
                    prop_update = 'No Action for Update' 
                if self.on_update_cascade:
                    prop_update = 'Cascade for Update'
                if self.on_update_setnull:
                    prop_update = 'Set Null for Update' 
                if self.on_update_setdefault:
                    prop_update = 'Set Default for Update'
                                                
                if prop_update:     
                    referUpdate.save_property('SQLScript_ReferLinks_Details.details', prop_update)
                                
        # resistant to non resolution
        length = min(len(self.first_table_columns), len(self.second_table_columns))
        
        for i in range(length):
            # resistance is my combat stance
            if self.first_table_columns[i] and self.second_table_columns[i]:
                create_link('referLink', self.first_table_columns[i].kb_symbol, self.second_table_columns[i].kb_symbol)          
                
        return

    def __repr__(self):
        """
ALTER TABLE editions ADD CONSTRAINT foreign_book FOREIGN KEY (book_id) REFERENCES books (id);
        """        
        return 'ALTER TABLE ' + str(self.first_table) \
               + ' ADD CONSTRAINT ' + str(self.name) \
               + ' FOREIGN KEY () REFERENCES ' + str(self.second_table) + ';'
        

class Constraint(Object):
    """
    Factorization of code
    """
    def __init__(self):
        Object.__init__(self)
        self.table = None
        self.columns = []
        self.synonyms = []

    def save(self, file):
        self.file = file
        result = Object.save(self, file)
        
        column_names = []
        # @todo : move to save links and add positions 
        for column in self.columns:
            if column:
                create_link('relyonLink', result, column.kb_symbol)
                column_names.append(column.name)
            else:
                # something bad happened on column resolution
                pass
                
        result.save_property('SQLScript_IndexProperties.columns', ';'.join(column_names))
        
        del column_names
        
        # @todo : bookmarks
        if self.table and self.table.kb_symbol:
            create_link('relyonLink', result, self.table.kb_symbol)

class UniqueConstraint(Constraint):
    """
    A foreign key
    """
    type_name = 'SQLScriptUniqueConstraint'
    
    def __init__(self):
        Constraint.__init__(self)

            
    def __repr__(self):
        return 'UNIQUE CONSTRAINT ' + str(self.table.fullname) \
               +  ' name ' + str(self.unique_name)


class FulltextConstraint(Constraint):
    """
    A full text key
    """
    type_name = 'SQLScriptIndex'
    
    def __init__(self):
        Constraint.__init__(self)

    def __repr__(self):
        return 'FULLTEXT ' + str(self.table.fullname) \
               +  ' name ' + str(self.unique_name)

               
class Index(Object):
    """
    An index from create index
    """
    def __init__(self):
        Object.__init__(self)
        self.name = None
        self.table = None
        self.columns = []
        self.synonyms = []

    type_name = 'SQLScriptIndex'

    def resolve(self):
        
        if not self.table:
            return
        
        columns = []
        for column_name in self.columns:
            columns.append(self.table.find_column(column_name))

        self.columns = columns
        del columns
        

    def save_links(self):
                
        # @todo : bookmarks
        if self.table and self.table.kb_symbol:
            create_link('relyonLink', self.kb_symbol, self.table.kb_symbol)
            
            column_names = []
            
            for column in self.columns:
                if column and column.kb_symbol:
                    create_link('relyonLink', self.kb_symbol, column.kb_symbol)
                    column_names.append(column.name)
                else:
                    # something bad happened on column resolution
                    pass
                    
            self.kb_symbol.save_property('SQLScript_IndexProperties.columns', ';'.join(column_names))
            del column_names
    
    def __repr__(self):
        result = 'CREATE INDEX ' + str(self.name) + '('
        separator = ''
        for column in self.columns:
            result += separator + str(column) 
            separator = ','
    
        return result + ');'   

class FunctionOrProcedure(WithObjectReferences):
    synonyms = []
    def is_function(self):
        return True


class Method(FunctionOrProcedure):
    type_name = 'SQLScriptMethod'

    def __repr__(self):
        return 'Method ' + self.name 
            
class Function(FunctionOrProcedure):
    type_name = 'SQLScriptFunction'

    def __repr__(self):
        return 'Function ' + self.name 


class Procedure(FunctionOrProcedure):
    type_name = 'SQLScriptProcedure'

    def __repr__(self):
        return 'Procedure ' + self.name 


class Trigger(FunctionOrProcedure):
    type_name = 'SQLScriptTrigger'

    def __init__(self):
        FunctionOrProcedure.__init__(self)
        self.table = None
        self.events = []

    def resolve(self):
        if not self.table:
            return

        self.table = self.table.get_unique_reference()
        
        if not self.table:
            return
        
        if not self.events:
            return
        
        for event in self.events:
            self.table.triggers[event.text.upper()].append(self)

    def save_links(self):
        FunctionOrProcedure.save_links(self)
        
        if self.table and self.events:
            for event in self.events:
                event_text = event.text.upper()
                
                if event_text == 'INSERT':
                    create_link('monitorInsertLink', self.kb_symbol, self.table.kb_symbol)
                if event_text == 'UPDATE':
                    create_link('monitorUpdateLink', self.kb_symbol, self.table.kb_symbol)
                if event_text == 'DELETE' or event_text == 'TRUNCATE':
                    create_link('monitorDeleteLink', self.kb_symbol, self.table.kb_symbol)
        
        self.table = None
        
    def is_function(self):
        return False

    def __repr__(self):
        return 'Trigger ' + self.name 
        
class Event(FunctionOrProcedure):
    type_name = 'SQLScriptEvent'

    def __repr__(self):
        return 'EVENT ' + self.name 

class Synonym(Object):
    """
    A synonym from create synonym /alias / nickname
    """
    def __init__(self):
        Object.__init__(self)
        self.name = None
        self.objects = []
        self.object = None
        self.kind_of_synonym = None
        self.synonyms = []
        self.list_of_alias_objects = None
        
    type_name = 'SQLScriptSynonym'

    def get_relyonLink(self):
        
        return self.object
                
    def resolve(self):
        
        if not self.object:
            return

    def save_links(self):
        self.kb_symbol.save_property('SQLScriptSynonym.kind_of_synonym', self.kind_of_synonym)
        for o in self.objects:
            try:
                create_link('relyonLink', self.kb_symbol, o.kb_symbol)
                o.kb_symbol.save_property('SQLScript_AliasedBy.list_of_alias_objects', str(self.fullname))
            except:
                print('cannot create relyonLink')
                pass
    
    def __repr__(self):
        result = 'CREATE SYNONYM ' + str(self.name) + ' ON ' + str(self.object)
    
        return result   
        
class TableSynonym(Synonym):
    """
    A synonym from create synonym /alias / nickname
    """
    def __init__(self):
        Object.__init__(self)
        self.name = None
        self.object = None
        self.synonyms = []
        self.is_xxl = False
        self.is_xxs = False
        self.xxl_size = None
        self.xxs_size = None
        
    type_name = 'SQLScriptTableSynonym'

    def resolve(self):
        
        if not self.object:
            return

    def save_links(self):
        if self.object and self.object.kb_symbol:
            create_link('relyonLink', self.kb_symbol, self.object.kb_symbol)
    
    def __repr__(self):
        result = 'CREATE SYNONYM on TABLE ' + str(self.name) + ' ON ' + str(self.object)
    
        return result  
        
class ViewSynonym(Object):
    """
    A synonym from create synonym /alias / nickname
    """
    def __init__(self):
        Object.__init__(self)
        self.name = None
        self.object = None
        self.synonyms = []
        self.is_xxl = False
        self.is_xxs = False
        self.xxl_size = None
        self.xxs_size = None
        
    type_name = 'SQLScriptViewSynonym'

    def resolve(self):
        
        if not self.object:
            return

    def save_links(self):
        if self.object and self.object.kb_symbol:
            create_link('relyonLink', self.kb_symbol, self.object.kb_symbol)
    
    def __repr__(self):
        result = 'CREATE SYNONYM on VIEW ' + str(self.name) + ' ON ' + str(self.object)
    
        return result  
        
class FunctionSynonym(Object):
    """
    A synonym from create synonym /alias / nickname
    """
    def __init__(self):
        Object.__init__(self)
        self.name = None
        self.object = None
        self.synonyms = []

    type_name = 'SQLScriptFunctionSynonym'

    def resolve(self):
        
        if not self.object:
            return

    def save_links(self):
        if self.object and self.object.kb_symbol:
            create_link('relyonLink', self.kb_symbol, self.object.kb_symbol)
    
    def __repr__(self):
        result = 'CREATE SYNONYM on FUNCTION ' + str(self.name) + ' ON ' + str(self.object)
    
        return result 
        
class ProcedureSynonym(Object):
    """
    A synonym from create synonym /alias / nickname
    """
    def __init__(self):
        Object.__init__(self)
        self.name = None
        self.object = None
        self.synonyms = []

    type_name = 'SQLScriptProcedureSynonym'

    def resolve(self):
        
        if not self.object:
            return

    def save_links(self):
        if self.object and self.object.kb_symbol:
            create_link('relyonLink', self.kb_symbol, self.object.kb_symbol)
    
    def __repr__(self):
        result = 'CREATE SYNONYM on PROCEDURE ' + str(self.name) + ' ON ' + str(self.object)
    
        return result 
        
class PackageSynonym(Object):
    """
    A synonym from create synonym /alias / nickname
    """
    def __init__(self):
        Object.__init__(self)
        self.name = None
        self.object = None
        self.synonyms = []

    type_name = 'SQLScriptPackageSynonym'

    def resolve(self):
        
        if not self.object:
            return

    def save_links(self):
        if self.object and self.object.kb_symbol:
            create_link('relyonLink', self.kb_symbol, self.object.kb_symbol)
    
    def __repr__(self):
        result = 'CREATE SYNONYM on PACKAGE ' + str(self.name) + ' ON ' + str(self.object)
    
        return result 
        
class TypeSynonym(Object):
    """
    A synonym from create synonym /alias / nickname
    """
    def __init__(self):
        Object.__init__(self)
        self.name = None
        self.object = None
        self.synonyms = []

    type_name = 'SQLScriptTypeSynonym'

    def resolve(self):
        
        if not self.object:
            return

    def save_links(self):
        if self.object and self.object.kb_symbol:
            create_link('relyonLink', self.kb_symbol, self.object.kb_symbol)
    
    def __repr__(self):
        result = 'CREATE SYNONYM on TYPE ' + str(self.name) + ' ON ' + str(self.object)
    
        return result 