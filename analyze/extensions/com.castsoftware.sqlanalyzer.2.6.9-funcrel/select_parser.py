'''
Created on 26 nov. 2015

General idea is the following :

- first step is to group (...)  so that we have 
SELECT ... FROM ... WHERE 
and the sub select (and sub where)  are inside Parenthesis 
- next we split in the 3 parts SELECT, FROM and WHERE
- then we split again inside SELECT and FROM through the ','

Needs :

- links to tables in the from 
- links to functions in the where
- column list in the select

Grammar from http://www.contrib.andrew.cmu.edu/~shadow/sql/sql1992.txt

<query specification> ::= SELECT [ <set quantifier> ] <select list> <table expression>
<from clause> ::= FROM <table reference> [ { <comma> <table reference> }... ]
<table reference> ::=
    <table name> [ [ AS ] <correlation name> [ <left paren> <derived column list> <right paren> ] ]
|   <derived table> [ AS ] <correlation name> [ <left paren> <derived column list> <right paren> ]
|   <joined table>
<derived table> ::= <table subquery>
<table subquery> ::= <subquery>
<subquery> ::= <left paren> <query expression> <right paren>
<derived column list> ::= <column name list>
<column name list> ::= <column name> [ { <comma> <column name> }... ]

 <joined table> ::=
       <cross join>
     | <qualified join>
     | <left paren> <joined table> <right paren>

<cross join> ::= <table reference> CROSS JOIN <table reference>

<qualified join> ::= <table reference> [ NATURAL ] [ <join type> ] JOIN <table reference> [ <join specification> ]

<join specification> ::=
       <join condition>
     | <named columns join>

<join condition> ::= ON <search condition>

<named columns join> ::= USING <left paren> <join column list> <right paren>

<join type> ::=
       INNER
     | <outer join type> [ OUTER ]
     | UNION

<outer join type> ::=
       LEFT
     | RIGHT
     | FULL

<join column list> ::= <column name list>


         <predicate> ::=
                <comparison predicate>
              | <between predicate>
              | <in predicate>
              | <like predicate>
              | <null predicate>
              | <quantified comparison predicate>
              | <exists predicate>
              | <unique predicate>
              | <match predicate>
              | <overlaps predicate>

<exists predicate> ::= EXISTS <table subquery>
<unique predicate> ::= UNIQUE <table subquery>
<match predicate> ::= <row value constructor> MATCH [ UNIQUE ] [ PARTIAL | FULL ] <table subquery>
<overlaps predicate> ::= <row value constructor 1> OVERLAPS <row value constructor 2>



Resolution principles 

- for 
  Select <...> From Table1 Alias1, Table2 Alias2 where <...>
  
  we associate a scope S1 
  - containing  Alias1, and Alias2
  - with parent a scope union of Table1 and Table2 (which are also scopes containing their columns)
  
  select list part and where parts are resolved inside S1 


@author: MRO
'''
from collections import defaultdict
from sqlscript_lexer import SqlLexer, EndIf, EndCase,  EndCatch, \
            EndWhile, EndLoop, EndRepeat, String, Number
from light_parser import Statement, BlockStatement, Lookahead, Any, \
            Parser, Seq, Optional, Or, Term, Walker, NotFollowedBy,\
            Not, Token, Node
from parser_common import extract_identifiers, parse_identifier, Identifier
from pygments.token import Name, Operator, Punctuation, Keyword, Error
from symbols import ResolutionScope, Synonym, Table, View
  
class SelectResult:
    """
    Store result of analysis of select
    """    
    def __init__(self):
        
        self.tables = []
        self.columns = []
        self.write_columns = []
        self.functions = []
        self.procedures = []
        self.selects = []
        self.controls = []
        self.dexecutes = []
        self.gotos = []
        self.methods = []
        
        self.insert_references = []
        self.update_references = []
        self.delete_references = []
        
        self.select_dynamic_references = ([])
        self.insert_dynamic_references = ([])
        self.update_dynamic_references = ([])
        self.delete_dynamic_references = ([])
        
        self.select_parameters_references = ([])
        
    def __repr__(self):
        
        return 'Tables=' + str(self.tables) + '\n' + 'Columns=' + str(self.columns) + '\n' +\
               'Updated Columns=' + str(self.write_columns) + '\n' +\
               'Methods =' + str(self.methods) + '\n' +\
               'Functions=' + str(self.functions) + '\n' + 'Procedures=' + str(self.procedures) + '\n' +\
               'insert_references=' + str(self.insert_references)  + '\n' +\
               'update_references=' + str(self.update_references)  + '\n' +\
               'delete_references=' + str(self.delete_references)  + '\n' +\
               'selects=' + str(self.selects)+ '\n' +\
               'gotos=' + str(self.gotos)+ '\n' +\
               'dexecutes=' + str(self.dexecutes)+ '\n' +\
               'controls=' + str(self.controls)


def analyse_select(stream, result, scope=None, client=None):
    """
    Analyse a select AST and feed a SelectResult
    
    scope contains the tables and so on... 
    """
    elements = list(stream)

    walker = Walker()
    walker.register_interpreter(IdentifierExtractor(result))
    walker.register_interpreter(Resolver(scope))
    
    # first pass
    walker.walk(elements)
    
    # quality rules
    walker = Walker()
    walker.register_interpreter(CartesianProduct())
    walker.register_interpreter(NoIndexCanSupport())
    walker.register_interpreter(NestedSubQueries())
    walker.register_interpreter(NonSARG())
    walker.register_interpreter(NaturalJoin())
    walker.register_interpreter(OrderByColumnNumber())
    walker.register_interpreter(NonAnsiJoin())
    walker.register_interpreter(FunctionCallOnIndex())
    walker.register_interpreter(HasGroupByClause())
    walker.register_interpreter(UnionInsteadUnionAll())
    walker.register_interpreter(HasNotInExists())
    walker.register_interpreter(MissingParenthesisInsertClause())
    walker.register_interpreter(CountTables())
    walker.register_interpreter(ControlFlowDetect())
    walker.register_interpreter(HasIndependentExistsClause())
    walker.register_interpreter(HasDistinctModifier())
    
    if client :
        walker.register_interpreter(NonAnsiOperators()) 
        
    walker.register_interpreter(OrOnTheSameIdentifier())  
    walker.register_interpreter(EmptyCatchBlock())      
    
    walker.walk(elements)
    


class IdentifierExtractor:

    """
    Interpret selects to get the identifiers.
    """
    class Context:
        
        def __init__(self):
            self.is_select = False
            self.is_delete = False
            self.select_into = False
            self.table_alias = None
    
    def __init__(self, result):
        self.result = result
        self.context = []

    def method_s_tokens (self, a, dot, b): 
        import pygments
        new_tokens = []
        
        new_tokens.append(Token(a.text, pygments.token.Token.Name))
        new_tokens.append(Token(dot.text, pygments.token.Token.Punctuation))       
        new_tokens.append(Token(b.text, pygments.token.Token.Name))
        
        return  (Lookahead(new_tokens)) 
    
    def start_Column(self, element):
        # extract column names	 
        try:
            previous_select = self.context[-1].is_select
        except:
            previous_select = None

        try:
            previous_table_alias = self.context[-1].table_alias
        except:
            previous_table_alias = None

        try:
            previous_select_into = self.context[-1].select_into
        except:
            previous_select_into = None

        if self.context and previous_select:
            try:
                column = element.get_column()
                table_alias = element.get_table_alias()
                                       
                if column and column == '*':
                    self.result.columns.append([column, table_alias])
                elif column and (isinstance(column, Token) or not column.is_empty()):
                    if not table_alias and previous_select and previous_table_alias:
                        self.result.columns.append([column, previous_table_alias])
                    elif not table_alias and previous_select and not previous_table_alias:
                        try:
                            details = element.get_children()
                            detail = details.look_next()
                            if detail == column:
                                next(details)
                                if details.look_next() == '.':
                                    next(details)
                                    table_alias = column
                                    column = details.look_next()
                                    self.result.columns.append([column, table_alias])
                                else:
                                    self.result.columns.append([column, None])
                            else:
                                self.result.columns.append([column, None])
                        except:
                            self.result.columns.append([column, None])
                    else: 
                        self.result.columns.append([column, table_alias])
                    # only a.b notations, that could be programs calls
                    if not table_alias and not isinstance(column, Token) and column.tokens[:-1]:
                        self.result.methods.append([column, column.tokens[-1:][0].begin_line, column.tokens[-1:][0].begin_column, column.tokens[-1:][0].end_line, column.tokens[-1:][0].end_column]) 
                

                tokens = element.get_children()		
                try:
                    function = parse_identifier(tokens)
                    if previous_select_into and not function.is_empty():
                        self.result.functions.append(function)
                except TypeError:
                    pass
            except StopIteration:
                pass

    def start_TableReference(self, element):
        # extract table names
        if self.context and self.context[-1].is_select:
            table = element.get_table()
            alias = element.get_alias()
            if table and not table.is_empty():
                self.result.tables.append([table, alias])
        
    def start_Join(self, element):
        if self.context and self.context[-1].is_select:
            tokens = element.get_children()
            tokens.move_to('JOIN')
            table = parse_identifier(tokens)
            alias = element.get_alias()
            if table and not table.is_empty():
                self.result.tables.append([table, alias])

        # add each column in the list of selected columns        
        for column in element.columns:
            self.result.columns.append(column)
            
    def start_FunctionCall(self, element):
        functions = extract_identifiers(element)
        # add the number of parameters for overloading
        try:
            for function in functions:
                function.parameters = getattr(element, 'parameters')

                a = None
                dot = None
                b = None

                for one_by_one in getattr(element, 'list_of_parameters'):
                    
                    if one_by_one.type == Name and not b and not a and not dot:
                        a = one_by_one
                    elif one_by_one.type == Name and not b and a:
                        b = one_by_one
                    elif one_by_one.text and one_by_one.text == '.' and one_by_one.type == Punctuation and a and not b:
                        dot = one_by_one
                     
                    if a and b and dot:  
                        tokens = self.method_s_tokens (a, dot, b)
                        identifier = parse_identifier((tokens), force_parse=True)
                        
                        begin_line = b.begin_line
                        begin_column = b.begin_column
                        end_line =  b.end_line
                        end_column =  b.end_column
                        
                        # only a.b notations, that could be programs calls
                        self.result.methods.append([identifier, begin_line, begin_column, end_line, end_column])
                        
                        a = None
                        dot = None
                        b = None
                        
                    elif (one_by_one.type == Punctuation and one_by_one.text and one_by_one == ',') or one_by_one.type == Operator:
                        a = None
                        dot = None
                        b = None
                        
        except AttributeError:
            pass
        
        self.result.functions += functions
        
    def start_Select(self, element):
        
        self.result.selects.append(element)
        
        context = IdentifierExtractor.Context()
        context.is_select = True
        context.table_alias = None
        context.select_into = False
        self.context.append(context)
        
        try:
            second_node = list(element.get_sub_nodes())[1]
            if isinstance(second_node, Into):
                context.select_into = True 
        except IndexError:
            pass
        try:
            if len(element.get_table_references()) == 1 and element.get_table_references()[0].get_table():
                context.table_alias = element.get_table_references()[0].get_table().get_name()        
        except IndexError:
            pass
        
        for column in element.get_columns():
            if isinstance(column, Column): 
                continue
            
            if isinstance(column, list):
                self.result.columns.append([column[0], column[1]])
            else:
                self.result.columns.append(column)
        
    def end_Select(self, element):
        
        self.context.pop()      

    def end_Insert(self, element):
        
        self.result.selects.append(element)

    def start_InsertClause(self, element):               
        stream = element.get_children()
        next(stream) # insert
        token = stream.look_next()
        if token == 'INTO':
            next(stream)
        
        # grab table identifier and push for resolution
        identifier = parse_identifier(stream)
        self.result.insert_references.append([identifier, None])
    
        if token == 'INTO':
            try:
                token = stream.look_next()
            except StopIteration:
                pass
            if isinstance(token, Parenthesis):
                list_of_columns = token.get_children()
                for column in list_of_columns:
                    if type(column) == BooleanTerm:
                        new_list_of_columns = column.get_children()
                        for new_column in new_list_of_columns:
                            if new_column in ('(', ',', ')', '[', ']'):
                                continue
                            if [new_column, identifier] not in self.result.write_columns:
                                self.result.write_columns.append([new_column, identifier])

                    elif column in ('(', ',', ')', '[', ']'):
                        continue
                    try:
                        if [column.get_tokens().look_next(), identifier] not in self.result.write_columns:
                            self.result.write_columns.append([column.get_tokens().look_next(), identifier])
                    except StopIteration:
                        pass
            else:   
                # the case when all columns should be linked
                self.result.write_columns.append([None, identifier])
        else:   
                try:
                    token = stream.look_next()
                except StopIteration:
                    pass
    
                if isinstance(token, Parenthesis):
                    list_of_columns = token.get_children()
                    for column in list_of_columns:
                        if type(column) == BooleanTerm:
                            new_list_of_columns = column.get_children()
                            for new_column in new_list_of_columns:
                                if new_column in ('(', ',', ')', '[', ']'):
                                    continue
                                if [new_column, identifier] not in self.result.write_columns:
                                    self.result.write_columns.append([new_column, identifier])
    
                        elif column in ('(', ',', ')', '[', ']'):
                            continue
                        try:
                            if [column.get_tokens().look_next(), identifier] not in self.result.write_columns:
                                self.result.write_columns.append([column.get_tokens().look_next(), identifier])
                        except StopIteration:
                            pass
                else:        
                    # the case when all columns should be linked, into is missing
                    self.result.write_columns.append([None, identifier])

    def start_Delete(self, element):

        self.result.selects.append(element)
        deleted = element.get_deleted_tables()
        if deleted:
            self.result.delete_references.append([deleted, None])
        
        for table_reference in element.get_table_references():
            table = table_reference.get_table()
            alias = table_reference.get_alias()
            if table and not table.is_empty():
                self.result.tables.append([table, alias])

            # join also register table references 
            for join in table_reference.get_joins():
                table = join.get_table()
                alias = table_reference.get_alias()
                if table and not table.is_empty():
                    self.result.tables.append([table, alias])
        
        # add each column in the list of selected columns        
        for column in element.columns:
            self.result.columns.append(column)


    def start_Update(self, element):

        self.result.selects.append(element)

        context = IdentifierExtractor.Context()
        context.is_select = True
        context.table_alias = None
        self.context.append(context)

        # add each column in the list of selected columns        
        for column in element.columns:
            self.result.columns.append(column)
            
        # add each column in the list of written columns        
        for column in element.write_columns:
            self.result.write_columns.append(column)
                        
    def end_Update(self, element):
        
        self.context.pop()

    def start_Merge(self, element):
        self.result.selects.append(element)

        for table_reference in element.get_inserted_table_references():
            table = table_reference.get_table()
            alias = table_reference.get_alias()
            if table and not table.is_empty():
                self.result.insert_references.append([table, alias])

        for table_reference in element.get_updated_table_references():
            table = table_reference.get_table()
            alias = table_reference.get_alias()
            if table and not table.is_empty():
                self.result.update_references.append([table, alias])

        for table_reference in element.get_table_references():
            table = table_reference.get_table()
            alias = table_reference.get_alias()
            if table and not table.is_empty():
                self.result.tables.append([table, alias])

        for table_reference in element.get_deleted_tables():
            table = table_reference.get_table()
            alias = table_reference.get_alias()
            if table and not table.is_empty():
                self.result.delete_references.append([table, alias])

        # add each column in the list of selected columns        
        for column in element.columns:
            self.result.columns.append(column)
                        
        # add each column in the list of written columns        
        for column in element.write_columns:
            self.result.write_columns.append(column)
                                   
        context = IdentifierExtractor.Context()
        context.is_select = True
        context.table_alias = None
        self.context.append(context)
                
    def end_Merge(self, element):
        self.result.selects.append(element)        
        self.context.pop()

    def end_GoTo(self, element):
        self.result.gotos.append(element)

    def end_ExecuteImmediate(self, element):
        self.result.dexecutes.append(element)

    def end_ExecuteDynamicCursor(self, element):
        self.result.dexecutes.append(element)

    def end_ExecuteDynamicString0(self, element):
        self.result.dexecutes.append(element)
        
    def end_ExecuteDynamicString1(self, element):
        self.result.dexecutes.append(element)

    def end_ExecuteDynamicString2(self, element):
        self.result.dexecutes.append(element)

    def end_ExecuteDynamicString3(self, element):
        self.result.dexecutes.append(element)

    def end_ExecuteDynamicString4(self, element):
        self.result.dexecutes.append(element)
        
    def end_ExecuteDynamicString5(self, element):
        self.result.dexecutes.append(element)

    def end_ExecuteDynamicString6(self, element):
        self.result.dexecutes.append(element)

    def end_While(self, element):
        self.result.controls.append(element)   

    def end_Loop(self, element):
        self.result.controls.append(element)  
        
    def end_Try(self, element):
        self.result.controls.append(element)  

    def end_Catch(self, element):
        self.result.controls.append(element)  

    def end_HandlerFor(self, element):
        self.result.controls.append(element) 

    def end_ExceptionWhenThen(self, element):
        self.result.controls.append(element)
            
    def end_OnException(self, element):
        self.result.controls.append(element) 
        
    def end_Case(self, element):
        self.result.controls.append(element)   

    def end_If(self, element):
        self.result.controls.append(element) 

    def end_Else(self, element):
        self.result.controls.append(element) 
 
    def end_Elseif(self, element):
        self.result.controls.append(element) 
                                               
    def start_UpdateClause(self, clause):
        
        stream = clause.get_children()
        next(stream)
        
        # grab table identifier and push for resolution
        identifier = parse_identifier(stream)            
        if identifier.get_name():
            self.result.update_references.append([identifier, None])
        
    def start_ExecuteClause(self, element):

        # look for ... 
        stream = element.get_children()
        
        try:
            next(stream)
            token = stream.look_next()
            if token.text and token.text.startswith('@'):
                next(stream) # @Name
                next(stream) # =
            
            identifier = parse_identifier(stream)            
            self.result.functions.append(identifier)
        except StopIteration:
            pass
    

class Resolver:
    """
    We resolve the diverse part of a Select.
    
    For the where clause : 
    
    for each boolean term : 
    - <...> = <...> 
      - we want to know which table reference is used (diag cartesian product)
      - so we define a scope using the from clause
        - with aliases pointing to the table reference
        - with column names of the table pointing to the table reference
      - we resolve each part of the boolean terms to those table references and set the field 'table_reference'   
    
    @todo:
    - recurse on select (inside select, from, and where differently)
    - views 
    - mark unresolved to avoid scanning the select latter
      
    """
    def __init__(self, parent_scope=None):
        
        self.parent_scope = parent_scope
    
    def start_Select(self, select):   
        
        self.resolve_select_like(select)
    
    def start_Delete(self, delete):
        
        self.resolve_select_like(delete)

    def start_Update(self, update):

        self.resolve_select_like(update)

    def start_Merge(self, merge):

        self.resolve_select_like(merge)
           
    def resolve_select_like(self, select):

        # scope for table references resolution
        # 2 scopes : 
        # first for resolving A in A.b : we put table alias, and table name (alias usage is optional)
        # second for resolving columns b in b : we put all columns of all tables.
        table_reference_scope = (ResolutionScope(), ResolutionScope())
        
        # same for column resolution
        column_scope = (ResolutionScope(), ResolutionScope())
        
        for reference in select.get_table_references() + select.get_additional_table_references():
            
            self.add_symbols_for_table_reference(reference, table_reference_scope, self.parent_scope)
            self.add_symbols_for_column(reference, column_scope, self.parent_scope)
            
            # join also register table references 
            for join in reference.get_joins():
                self.add_symbols_for_table_reference(join, table_reference_scope, self.parent_scope)
                self.add_symbols_for_column(join, column_scope, self.parent_scope)
                
                on = join.get_on()
                if on:
                    for boolean_term in on.get_boolean_terms():
                        
                        for identifier in boolean_term.get_all_identifiers():

                            self.resolve_term(identifier, table_reference_scope)
                            self.resolve_term_as_column(identifier, column_scope)
        
        # resolve where clauses
        try:
            for boolean_term in select.get_where().get_boolean_terms():
                
                for identifier in boolean_term.get_all_identifiers():
                
                    self.resolve_term(identifier, table_reference_scope)
                    self.resolve_term_as_column(identifier, column_scope)

        except AttributeError:
            pass

        
    @staticmethod
    def add_symbols_for_table_reference(reference, table_reference_scope, parent_scope):
        """
        declare the tables reference symbols for an element
        """
        tr_scope = table_reference_scope[0]
        col_scope = table_reference_scope[1]
        
        table_identifier = reference.get_table()
        # columns names are also registered as aliases for the table reference 
        if table_identifier and parent_scope:
            table_identifier.types = [Table, View, Synonym]
            table = parent_scope.resolve_reference(table_identifier, unique=True)
            while type(table) == Synonym:
                table = table.object
                table_identifier.object = table
            if table:
                # table reference is resolved, let's enjoy
                table_identifier.reference = [table]
                if hasattr(table, 'symbols'):
                    for column_name in table.symbols:
                        col_scope.add_element(column_name, reference)

        
        name = reference.get_alias()
        if name:
            # table reference has alias so this is the 'name' 
            tr_scope.add_element(name, reference)

        elif table_identifier:
            # table reference has no alias so table name is the 'name' 
            tr_scope.add_element(table_identifier.get_name(), reference)
            
    @staticmethod
    def resolve_term(term, table_reference_scope):
        """
        resolve a left or right part of a boolean term
        """
        if term:
            tr_scope = table_reference_scope[0]
            col_scope = table_reference_scope[1]
            
            # here we can have several cases :
            if term.is_empty():
                # Identifier([]) 
                # --> not an id in fact, resolved no need for resolution
                setattr(term, 'table_reference', None)
                setattr(term, 'table_reference_is_resolved', True)
                
            elif term.get_parent_name():
                # Identifier([Token(Token.Name,'alias',1,28,1,30), Token(Token.Name,'id',1,28,1,30)]) 
                # --> alias.id, we try to resolve alias alone (no need for id...)
                resolution = tr_scope.find_symbol(term.get_parent_name())
                setattr(term, 'table_reference', resolution)
                setattr(term, 'table_reference_is_resolved', True if resolution else False)
            else:
                # Identifier([Token(Token.Name,'id',1,28,1,30)])
                # --> id, a column, we try to resolve id  
                resolution = col_scope.resolve_reference(term, unique=True)
                setattr(term, 'table_reference', resolution)
                setattr(term, 'table_reference_is_resolved', True if resolution else False)

    @staticmethod
    def add_symbols_for_column(reference, column_scope, parent_scope):
        """
        declare the column symbols for an element
        """
        tr_scope = column_scope[0]
        col_scope = column_scope[1]
        
        table_identifier = reference.get_table()
        
        if table_identifier and table_identifier.reference:

            table = table_identifier.reference[0]
            # register all columns as mapped to themselves
            if hasattr(table, 'symbols'):
                for column_name in table.symbols:
                    col_scope.add_element(column_name, table.symbols[column_name][0])

            name = reference.get_alias()
            if name:
                # alias is mapped to table
                tr_scope.add_element(name, table)
            else:
                # if no alias table name is an alias for itself
                tr_scope.add_element(table_identifier.get_name(), table)
                
    @staticmethod
    def resolve_term_as_column(term, column_scope):
        """
        Resolve a left or right part of a boolean term to a column
        """
        if not term:
            return

        tr_scope = column_scope[0]
        col_scope = column_scope[1]

        # here we can have several cases :
        if term.is_empty():
            # Identifier([]) 
            # --> not an id in fact, resolved no need for resolution
            setattr(term, 'column', None)
            setattr(term, 'column_is_resolved', True)
            
        elif term.get_parent_name():
            resolution = None
            
            table = tr_scope.find_symbol(term.get_parent_name())
            if table and hasattr(table, 'find_symbol'):
                resolution = table.find_symbol(term.get_name())
            setattr(term, 'column', resolution)
            setattr(term, 'column_is_resolved', True if resolution else False)
            
        else:
            
            resolution = col_scope.resolve_reference(term, unique=True)
            setattr(term, 'column', resolution)
            setattr(term, 'column_is_resolved', True if resolution else False)


class DiagCommon:
    
    def get_elements(self, select):
        """
        returns all the table references, the joins and the boolean terms of a select like
        """
        table_references = []
        joins = []
        boolean_terms = []
        
        
        # postgresql consider that :
        # tables_references = update table reference + from tables references
        # sqlsever consider only from table reference
        # this approximation will introduce false negative on postgresql

        from_table_references = select.get_table_references()
        
        if not from_table_references:
            # easy case : nothing in from
            from_table_references = select.get_additional_table_references()
        
        
        resolved_table_references = set()
        
        for reference in from_table_references:
            table_references.append(reference)

            # join also register table references 
            for join in reference.get_joins():
                
                joins.append(join)
                table_references.append(join)
                
                on = join.get_on()
                if on:
                    boolean_terms += on.get_boolean_terms()
                    
        
        where = select.get_where()
        if where:
            boolean_terms += where.get_boolean_terms()
        
        
        # heuristic...
        for bt in boolean_terms:
            
            identifier = bt.get_left_identifier()
            if identifier and hasattr(identifier, 'table_reference') and identifier.table_reference:
                # resolved table reference must reside in result
                resolved_table_references.add(identifier.table_reference)
            identifier = bt.get_right_identifier()
            if identifier and hasattr(identifier, 'table_reference') and identifier.table_reference:
                # resolved table reference must reside in result
                resolved_table_references.add(identifier.table_reference)
        
        for tr in resolved_table_references:
            if not tr in table_references:
                table_references.append(tr)
        
        return table_references, joins, boolean_terms

class EmptyCatchBlock():
    """
    1101040 : Avoid empty catch blocks 
    """ 
    def end_Catch(self, control):
        for t in control.get_sub_nodes():
            if isinstance(t, BlockStatement):
                return
        self.finalise_statement(control)

                                     
    def finalise_statement(self, control):
        catch_detected = False
        has_empty_catch = False

        for node in control.get_children():        
            if node == 'CATCH' and not catch_detected:
                catch_detected = True
                has_empty_catch = True
            elif node.type !=  EndCatch and catch_detected:
                has_empty_catch = False
                break
        setattr(control, 'has_empty_catch', has_empty_catch)
    

                        
class OrOnTheSameIdentifier(DiagCommon):
    """
    Detect at least 2 or on the same identifier
    """ 
    def end_Select(self, select):
        self.finalise_statement(select)

    def end_Update(self, update):
        self.finalise_statement(update)
                               
    def end_Delete(self, delete):
        self.finalise_statement(delete)

    def end_Merge(self, merge):
        self.finalise_statement(merge)
                             
    def finalise_statement(self, select):
        has_or_on_the_same_identifier = False
        all_identifiers = set()
        prev_or_detected = None
        group_detected = None
        _, _, boolean_terms = self.get_elements(select)
        
        for boolean_term in boolean_terms:
            group_detected  = boolean_term.begin_of_a_group_text
            or_detected = boolean_term.or_detected
            if group_detected and not or_detected:
                prev_or_detected = or_detected
                continue

            left = boolean_term.left_text
            right = boolean_term.right_text
            
            if left and right:
                prev_or_detected = or_detected
                continue
                
            if boolean_term.operator == '=':
                if left and left not in all_identifiers:
                    all_identifiers.add(left)
                elif prev_or_detected and left in all_identifiers:
                    has_or_on_the_same_identifier = True
                    break
                elif right and right not in all_identifiers:
                    all_identifiers.add(right)
                elif prev_or_detected and right in all_identifiers:
                    has_or_on_the_same_identifier = True
                    break
                prev_or_detected = or_detected
       
        setattr(select, 'has_or_on_the_same_identifier', has_or_on_the_same_identifier)   
        
class NonAnsiOperators(DiagCommon):
    """
    Detect NON ANSI OPERATOS like !=, !> and !< in Statements
    """ 
    def end_Select(self, select):
        self.finalise_statement(select)

    def end_Update(self, update):
        self.finalise_statement(update)
                               
    def end_Delete(self, delete):
        self.finalise_statement(delete)

    def end_Merge(self, merge):
        self.finalise_statement(merge)
                             
    def finalise_statement(self, select):
        has_non_ansi_operator = False
        _, _, boolean_terms = self.get_elements(select)
        
        for boolean_term in boolean_terms:  
            if boolean_term.get_operator() in ('!=', '!>', '!<'):
                has_non_ansi_operator = True
                break                      
        
        setattr(select, 'has_non_ansi_operator', has_non_ansi_operator)      
                            
class HasDistinctModifier():
    """
    Detect Distinct modifiers : "DISTINCT", "DISTINCTROW" and "UNIQUE"
    """                
    def end_Select(self, select):
        distinctModifiers = select.get_distinct()
        self.finalise_statement(select, distinctModifiers)

    def end_Update(self, update):
        distinctModifiers = update.distinct
        self.finalise_statement(update, distinctModifiers)

    def end_Delete(self, delete):
        distinctModifiers = delete.distinct
        self.finalise_statement(delete, distinctModifiers)

    def end_Insert(self, insert):
        distinctModifiers = insert.distinct
        self.finalise_statement(insert, distinctModifiers)

    def end_Merge(self, merge):
        distinctModifiers = merge.distinct
        self.finalise_statement(merge, distinctModifiers)
                                             
    def finalise_statement(self, select, distinctModifiers):
        if distinctModifiers: 
            setattr(select, 'has_distinct', True)
        else: 
            setattr(select, 'has_distinct', False)
        
class ControlFlowDetect():     
    def end_Case(self, control):
        self.finalise_statement(control)

    def end_If(self, control):
        self.finalise_statement(control)

    def end_Else(self, control):
        self.finalise_statement(control)
 
    def end_Elseif(self, control):
        self.finalise_statement(control)

    def end_While(self, control):
        loop_detected = False
        tokens = control.get_children()
        for t in tokens:
            if isinstance(t, Loop):
                loop_detected = True
        if not loop_detected:
            self.finalise_statement(control)

    
    def end_Loop(self, control):
        self.finalise_statement(control)
        
    def end_Try(self, control):
        self.finalise_statement(control)

    def end_Catch(self, control):
        self.finalise_statement(control)
    
    def finalise_statement(self, control):
        list_of_if_statements = set()
        # to be reviewed
        def cf_deep (nodes, deep_of_cf):
            deep_of_cf = deep_of_cf
            max_deep_of_cf = 0
            nodes_again = None
            for n in nodes:
                if n.get_children() :
                    nodes_again = n.get_children()
                if isinstance(n, While):
                    loop_detected = False
                    for t in nodes_again:
                        if isinstance(t, Loop):
                            loop_detected = True
                            break
                        
                    if loop_detected:
                        deep_of_cf = 1
                        deep_of_cf += cf_deep (t.get_children(), deep_of_cf)
                    else:
                        deep_of_cf = 1
                        deep_of_cf += cf_deep (n.get_children(), deep_of_cf)
                elif isinstance(n, Case) or isinstance(n, If) or isinstance(n, Loop) or isinstance(n, Try) or isinstance(n, Catch):
                    if isinstance(n, If):
                        # the case of  MS SQL when we don't have a real block statement
                        tokens = n.get_children()
                        token = tokens.look_next()
                        if token.begin_column not in list_of_if_statements:
                            list_of_if_statements.add(token.begin_column)
                        else:
                            break
                    deep_of_cf = 1
                    deep_of_cf += cf_deep (nodes_again, deep_of_cf)
                elif isinstance(n, Else) or isinstance(n, Elseif):
                    deep_of_cf = 0
                    deep_of_cf += cf_deep (nodes_again, deep_of_cf)               
                elif isinstance(nodes_again, BlockStatement):
                    deep_of_cf = 0
                    deep_of_cf += cf_deep (nodes_again, deep_of_cf)
                elif n.text and ('END ' in n.text.upper() or 'RETURN' in n.text.upper()) or isinstance(n, EndIfWithSpace):
                    max_deep_of_cf = max(deep_of_cf, max_deep_of_cf)
                    deep_of_cf = 0
                    break

                max_deep_of_cf = max(deep_of_cf, max_deep_of_cf)   
            
            return max_deep_of_cf

        deep_of_cf = 1 
        details = control.get_children()
        max_of_deep_of_code = deep_of_cf
        nodes = None
        for n in details:
            if n.get_children(): 
                nodes = n.get_children()
            else:
                nodes = None
            if isinstance(n, While):
                loop_detected = False
                for t in nodes:
                    if isinstance(t, Loop):
                        loop_detected = True
                        break
                    
                if loop_detected:
                    deep_of_cf = 1
                    deep_of_cf += cf_deep (t.get_children(), deep_of_cf)
                else:
                    deep_of_cf = 1
                    deep_of_cf += cf_deep (n.get_children(), deep_of_cf)
            elif isinstance(n, Case) or isinstance(n, If) or isinstance(n, Loop) or isinstance(n, Try) or isinstance(n, Catch):
                deep_of_cf = 1
                deep_of_cf += cf_deep (nodes, deep_of_cf)
            elif isinstance(n, Else) or isinstance(n, Elseif):
                deep_of_cf = 0
                deep_of_cf += cf_deep (nodes, deep_of_cf)
            elif n.text and ('END ' in n.text.upper() or 'RETURN' in n.text.upper()) or isinstance(n, EndIfWithSpace):
                max_of_deep_of_code = max(max_of_deep_of_code, deep_of_cf)
                deep_of_cf = 0
                continue  
            elif isinstance(nodes, BlockStatement):
                deep_of_cf = 0
                deep_of_cf += cf_deep (nodes, deep_of_cf)    

            max_of_deep_of_code = max(max_of_deep_of_code, deep_of_cf)
            deep_of_cf = 0

        setattr(control, 'maxControlStatementsNestedLevels', max_of_deep_of_code)
        max_of_deep_of_code = None
        del list_of_if_statements
        
class CountTables():
    """
    Avoid Artifacts with queries on more than 4 Tables
    """              
    count_tables = 0

    def end_Select(self, select):
        self.finalise_statement(select)
                       
    def finalise_statement(self, select):  
        self.count_tables = 0
        def get_ref (nodes):
            try:
                join_detected = False
                parenthesis_with_join = False
                tokens = nodes.get_children()
                for t in tokens:
                    if parenthesis_with_join and join_detected and t.type == Name:
                        join_detected = False
                        parenthesis_with_join = False
                    elif isinstance(t, TableReference):
                        get_table_reference(t)
                    elif isinstance(t, Select):
                        get_ref(t)
                    elif isinstance(t, Where) or isinstance(t, BooleanTerm) or isinstance(t, Having):
                        get_ref(t)  
                    elif isinstance(t, From): 
                        get_from(t)
                    elif isinstance(t, Join):
                        get_join (t)
                    elif (t.type in ( Name, String.Symbol)) and join_detected:
                        if self.count_tables  == 0:
                            self.count_tables += 2
                            t = tokens.move_to('ON')
                            next(tokens)
                            t = tokens.look_next()
                        else :
                            self.count_tables += 1 
                        join_detected = False
                    elif t.type == Keyword and t == 'JOIN' and not join_detected:
                        join_detected = True
                    elif isinstance(t, Parenthesis):
                        if join_detected : parenthesis_with_join = True
                        get_parenthesis(t)
            except StopIteration:
                pass
             
            return
            
        def get_join (nodes):
            try:
                prev = False
                using_case = False
                tokens = nodes.get_children()
                for t in tokens:
                    if isinstance(t, FunctionCall) and get_function_name(t) == 'OPENXML':
                        self.count_tables += 1 
                        t = tokens.move_to('AS')
                        next(tokens)
                        t = tokens.look_next()
                        continue
                    elif t == 'USING':
                        using_case = True
                        continue
                    elif isinstance(t, TableReference):
                        get_table_reference(t)
                    elif (isinstance(t, Parenthesis) or isinstance(t, BooleanTerm)) and not using_case:
                        get_join (t)
                    elif isinstance(t, Parenthesis) and using_case:
                        using_case = False
                    elif (t.type in ( Name, String.Symbol)) and not prev:
                        self.count_tables += 1 
                        prev = True
                    elif (t.type in ( Name, String.Symbol) and prev):
                        prev = True
                    elif (prev and t == ','):
                        prev = False
                    elif (prev and t == '.'):
                        prev = True
                       
            except:
                print('issue with get_join in CountTables')
                pass
             
            return

        def get_from (nodes):
            try:
                for t in nodes.get_children():
                    if isinstance(t, TableReference): 
                        get_table_reference(t)
                    elif isinstance(t, Join):
                        get_join (t)
                    elif isinstance(t, Parenthesis): 
                        get_parenthesis(t)
            except:
                print('issue with get_from in CountTables')
                pass
             
            return

        def get_function_name (nodes):
            for t in nodes.get_children():
                if t.type == Name:
                    return(t.text)
             
            return
        
        def get_table_reference (nodes):
            try:
                prev = False
                for t in nodes.get_children():
                    if isinstance(t, Parenthesis): 
                        get_parenthesis(t)
                        prev = True
                    elif (t.type in ( Name, String.Symbol) and prev):
                        prev = True
                    elif (prev and t == ','):
                        prev = False
                    elif (prev and t == '.'):
                        prev = True
                    elif t.type in ( Name, String.Symbol) and not prev:
                        self.count_tables += 1
                        prev = True
                    elif isinstance(t, Join):
                        get_join (t)

            except:
                print('issue with get_table_reference in CountTables')
                pass
             
            return

        def get_parenthesis (nodes):
            try:
                for t in nodes.get_children():
                    if isinstance(t, Select): 
                        get_ref(t)
                    if isinstance(t, Parenthesis): 
                        get_parenthesis(t)
                    elif isinstance(t, TableReference): 
                        get_table_reference(t)
                    elif  isinstance(t, BooleanTerm):
                        get_ref(t)
            except:
                print('issue with get_parenthesis in CountTables')
                pass
             
            return
                                                          
        try:
            for t in select.get_tokens():
                if isinstance(t, TableReference): 
                    get_table_reference(t)
                elif isinstance(t, Where) or isinstance(t, Having):
                    get_ref(t)
                elif isinstance(t, From):
                    get_from(t)
                elif isinstance(t, Join):                  
                    get_join (t)
        except:
            print('issue with get_parenthesis in CountTables')
            pass

        setattr(select, 'number_of_tables', self.count_tables)

class HasIndependentExistsClause(DiagCommon):
    """
    Detect Independent Exists clause
    """                 
    def end_Select(self, select):
        """
        fix the case when select are commented
        """
        begin_line = None
        begin_column = None
        for t in select.get_children():
            if isinstance(t, SelectList):
                try:
                    if select.get_begin_line() != t.get_children().move_to('SELECT').get_begin_line() or \
                        select.get_begin_column() != t.get_children().move_to('SELECT').get_begin_column():
                        begin_line =  t.get_children().move_to('SELECT').get_begin_line()
                        begin_column = t.get_children().move_to('SELECT').get_begin_column()
                except AttributeError:
                    pass
                break
        if begin_line and begin_column:
            self.finalise_statement(select, begin_line, begin_column)
        else:
            self.finalise_statement(select, None, None)
                                    
    def end_Delete(self, delete):
        self.finalise_statement(delete, None, None)

    def end_Update(self, update):
        self.finalise_statement(update, None, None)

    def end_Merge(self, merge):
        self.finalise_statement(merge, None, None)
        
    def finalise_statement(self, select, begin_line, begin_column):
        self.has_independent_exists = False
        isSubquery = False
        table_references, _ , boolean_terms = self.get_elements(select)
        self.parent_tables = set()
        self.child_tables = set()
        unresolved_references_tables = set()
        self.detected_as_parent = False
        self.detected_as_child = False
        self.parent_child_are_linked = False
        term_operator = None
        
        def deep_of_the_bool (nodes, detected_as_child, detected_as_parent):
            for node in nodes:
                if self.parent_child_are_linked:
                    break
                if node.get_children():
                    self.parent_child_are_linked, self.has_independent_exists, self.detected_as_child, self.detected_as_parent = deep_of_the_bool (node.get_children(), self.detected_as_child, self.detected_as_parent)
                    if (self.detected_as_child and self.detected_as_parent):
                        self.parent_child_are_linked = True
                        self.has_independent_exists = False
                        break
                else:
                    if node.type == Name and node.text in self.parent_tables:
                        self.detected_as_parent = True
                    elif node.type == Name and node.text in self.child_tables:
                        self.detected_as_child = True

                    if (self.detected_as_child and self.detected_as_parent):
                        self.parent_child_are_linked = True
                        self.has_independent_exists = False
                        break
                    
            return (self.parent_child_are_linked, self.has_independent_exists, self.detected_as_child, self.detected_as_parent)
        
                    
        def Subquery(self):
            isSubquery = False
            r = None
            for r in self.get_children():
                if isinstance(r, Parenthesis) or isinstance(r, BooleanTerm):
                    isSubquery, r = Subquery(r)
                if isinstance(r, Select): 
                    isSubquery = True
                    break

            return isSubquery, r


        if isinstance(select, Update):
            if len(select.updated_tables) > 0:
                self.parent_tables.add(select.updated_tables[0].name)
            
        for table_reference in table_references:
            for tr in table_reference.get_children():
                
                if tr.type in ( Name, String.Symbol):
                    self.parent_tables.add(tr.text.replace('`', ''))
        for term in boolean_terms:
            for r in term.get_children():
                if isinstance(r, Parenthesis):
                    isSubquery, sub_query = Subquery(r)
                    if not isSubquery and not term.get_operator() in( 'not exists', 'exists'):
                        break
                    if isSubquery and term.get_operator() in( 'not exists', 'exists'):
                        term_operator = term.get_operator()
                        sub_table_references, _, sub_boolean_terms = self.get_elements(sub_query)
                        if len(sub_boolean_terms) == 0:
                            self.has_independent_exists = True 
                            break                                    
                        for sub_table_reference in sub_table_references:
                            for subtableref in sub_table_reference.get_children():
                                if subtableref.type in ( Name, String.Symbol):
                                    self.child_tables.add(subtableref.text.replace('`', ''))
                        for sub_term in sub_boolean_terms:
                            detected_as_parent = False
                            detected_as_child = False
                            sub_left = sub_term.get_left_identifier()
                            sub_right = sub_term.get_right_identifier()
                            if self.parent_child_are_linked :
                                break
                            elif sub_term.get_operator() in ('in','not in', 'exists', 'not exists'):
                                for i in (0, len(sub_boolean_terms)-1):
                                    if self.parent_child_are_linked:
                                        break
                                    name_detected = False
                                    isbools = sub_boolean_terms[i].get_children()
                                    name_detected = False
                                    for isbool in isbools:
                                        if self.parent_child_are_linked:
                                            break
                                        if isbool.type in ( Name, String.Symbol) and not name_detected and isbool.text.lower() not in ('is', 'not', 'null'):
                                            name_detected = True
                                            unresolved_references_tables.add(isbool.text.replace('`', ''))
                                            if not detected_as_parent and isbool.text.replace('`', '') in self.parent_tables:
                                                detected_as_parent = True
                                                try:
                                                    unresolved_references_tables.remove(isbool.text.replace('`', ''))
                                                except:pass
                                            if isbool.text.replace('`', '') in self.child_tables:
                                                detected_as_child = True
                                                try:
                                                    unresolved_references_tables.remove(isbool.text.replace('`', ''))
                                                except:
                                                    print('issue with remove unresolved_references_tables in HasIndependentExistsClause')
                                                    pass
                                        elif isbool.type in ( Name, String.Symbol) and name_detected:
                                            name_detected = False
                                        if (detected_as_child and detected_as_parent):
                                            self.parent_child_are_linked = True
                                            self.has_independent_exists = False
                                            break
                                        else:
                                            self.has_independent_exists = True 
                                            self.parent_child_are_linked = False
                            elif (not sub_left or not sub_right) and len(sub_boolean_terms)-1 == 0:
                                name_detected = False
                                for isbool in sub_boolean_terms[0].get_children():
                                    if self.parent_child_are_linked:
                                        break
                                    if isbool.type in ( Name, String.Symbol) and not name_detected and isbool.text.lower() not in ('is', 'not', 'null'):
                                        name_detected = True
                                        unresolved_references_tables.add(isbool.text.replace('`', ''))
                                        if not detected_as_parent and isbool.text.replace('`', '') in self.parent_tables:
                                            detected_as_parent = True
                                            try:
                                                unresolved_references_tables.remove(isbool.text.replace('`', ''))
                                            except:
                                                print('issue with remove unresolved_references_tables in HasIndependentExistsClause')
                                                pass
                                        if isbool.text.replace('`', '') in self.child_tables:
                                            detected_as_child = True
                                            try:
                                                unresolved_references_tables.remove(isbool.text.replace('`', ''))
                                            except:
                                                print('issue with remove unresolved_references_tables in HasIndependentExistsClause')
                                                pass
                                    elif isbool.type in ( Name, String.Symbol) and name_detected:
                                        name_detected = False
                                    if (detected_as_child and detected_as_parent):
                                        self.parent_child_are_linked = True
                                        self.has_independent_exists = False
                                        break
                                    else:
                                        self.has_independent_exists = True 
                                        self.parent_child_are_linked = False
                            elif (sub_left and not sub_left.table_reference_is_resolved ) or (sub_right and not sub_right.table_reference_is_resolved):
                                if (sub_left and not sub_left.column_is_resolved) and (sub_right and not sub_right.column_is_resolved):
                                    detected_as_child = True
                                    detected_as_parent = True
                                    self.parent_child_are_linked = True
                                    self.has_independent_exists = False
                                    break
                                elif sub_term.get_children():
                                    name_detected = False
                                    count_detected_names = 0
                                    for sub_term_expression in sub_term.get_children():
                                        if sub_term_expression.type in ( Name, String.Symbol) and not name_detected and sub_term_expression.text.lower() not in ('is', 'not', 'null'):
                                            name_detected = True
                                            count_detected_names += 1
                                            unresolved_references_tables.add(sub_term_expression.text.replace('`', ''))
                                            if sub_term_expression.text.replace('`', '') in self.parent_tables:
                                                detected_as_parent = True
                                                try:
                                                    unresolved_references_tables.remove(sub_term_expression.text.replace('`', ''))
                                                except:
                                                    print('issue with remove unresolved_references_tables in HasIndependentExistsClause')
                                                    pass
                                                if (detected_as_child and detected_as_parent):
                                                    self.parent_child_are_linked = True
                                                    self.has_independent_exists = False
                                                    break
                                            if sub_term_expression.text.replace('`', '') in self.child_tables:
                                                detected_as_child = True
                                                try:
                                                    unresolved_references_tables.remove(sub_term_expression.text.replace('`', ''))
                                                except:
                                                    print('issue with remove unresolved_references_tables in HasIndependentExistsClause')
                                                    pass
                                                if (detected_as_child and detected_as_parent):
                                                    self.parent_child_are_linked = True
                                                    self.has_independent_exists = False
                                                    break
                                        elif sub_term_expression.type in ( Name, String.Symbol) and name_detected:
                                            name_detected = False
                                            count_detected_names += 1
                                    if (detected_as_child and count_detected_names >= 3 and not detected_as_parent) or (not detected_as_child and not detected_as_parent and count_detected_names == 2):
                                        # limitation, we have a second name but is not in the list of parents, it could be a cursor name 
                                        # case of a.b = c.d where only a side is fully resolved
                                        detected_as_parent = True
                                        self.has_independent_exists = False
                                        break
                                
                                if (detected_as_child and detected_as_parent):
                                    self.parent_child_are_linked = True
                                    self.has_independent_exists = False
                                    break
                                for i in (0, len(sub_boolean_terms)-1):
                                    if self.parent_child_are_linked:
                                        break
                                    name_detected = False
                                    isbools = sub_boolean_terms[i].get_children()
                                    
                                    if (sub_left and sub_left.table_reference_is_resolved and sub_left.column_is_resolved) and sub_left.get_name():
                                        detected_as_child = True                                       
                                        isbools.move_to(Operator)
                                    if (sub_right and sub_right.table_reference_is_resolved and sub_right.column_is_resolved) and sub_right.get_name():
                                        detected_as_child = True
                                    for isbool in isbools:
                                        if (sub_right and sub_right.table_reference_is_resolved and sub_right.column_is_resolved) and isbool.type == Operator:
                                            break
                                        if isbool.type in ( Name, String.Symbol) and not name_detected and isbool.text.lower() not in ('is', 'not', 'null'):
                                            name_detected = True
                                            unresolved_references_tables.add(isbool.text.replace('`', ''))
                                            if isbool.text.replace('`', '') in self.parent_tables:
                                                detected_as_parent = True
                                                try:
                                                    unresolved_references_tables.remove(isbool.text.replace('`', ''))
                                                except:
                                                    print('issue with remove unresolved_references_tables in HasIndependentExistsClause')
                                                    pass
                                                if (detected_as_child and detected_as_parent):
                                                    self.parent_child_are_linked = True
                                                    self.has_independent_exists = False
                                                    break
                                            if isbool.text.replace('`', '') in self.child_tables:
                                                detected_as_child = True
                                                try:
                                                    unresolved_references_tables.remove(isbool.text.replace('`', ''))
                                                except:
                                                    print('issue with remove unresolved_references_tables in HasIndependentExistsClause')
                                                    pass
                                                if (detected_as_child and detected_as_parent):
                                                    self.parent_child_are_linked = True
                                                    self.has_independent_exists = False
                                                    break
                                        elif isbool.type in ( Name, String.Symbol) and name_detected:
                                            name_detected = False
                                    if (detected_as_child and detected_as_parent):
                                        self.parent_child_are_linked = True
                                        self.has_independent_exists = False
                                        break
                                    elif not self.parent_child_are_linked and not self.has_independent_exists:
                                        self.has_independent_exists = True 
                            else:
                                if (sub_left and not sub_left.get_name()) or (sub_right and not sub_right.get_name()):
                                    for i in (0, len(sub_boolean_terms)-1):
                                        if self.parent_child_are_linked:
                                            break
                                        isbools = sub_boolean_terms[i].get_children() 
                                        for isbool in isbools:
                                            if isbool.type in ( Name, String.Symbol) and isbool.text.replace('`', '') in self.parent_tables:
                                                self.detected_as_parent = True
                                            elif isbool.type in ( Name, String.Symbol) and isbool.text.replace('`', '') in self.child_tables:
                                                self.detected_as_child = True
                                            elif isbool.get_children():
                                                self.parent_child_are_linked, self.has_independent_exists, self.detected_as_child, self.detected_as_parent = deep_of_the_bool(isbool.get_children(), self.detected_as_child, self.detected_as_parent)
                                            
                                            if detected_as_child and detected_as_parent:
                                                self.parent_child_are_linked = True
                                                self.has_independent_exists = False
                                                break
                                                
                                                
                                    if self.parent_child_are_linked:
                                        break                 
                                    else:
                                        self.has_independent_exists = True
        
        if isSubquery and term_operator in( 'not exists', 'exists'): 
            setattr(select, 'has_independent_exists', self.has_independent_exists)
            setattr(select, 'new_begin_line', begin_line)
            setattr(select, 'new_begin_column', begin_column)
        else:
            setattr(select, 'has_independent_exists', False)

class HasNotInExists(DiagCommon):
    """
    Detect Not In and Not Exists operators 
    """                 
    def end_Select(self, select):
        self.finalise_statement(select)
                                    
    def end_Delete(self, delete):
        self.finalise_statement(delete)

    def end_Update(self, update):
        self.finalise_statement(update)

    def end_Merge(self, merge):
        self.finalise_statement(merge)
        
    def finalise_statement(self, select):
        def Subquery(self):
            isSubquery = False
            for r in self.get_children():
                if isinstance(r, Parenthesis) or isinstance(r, BooleanTerm):
                    isSubquery = Subquery(r)
                if isinstance(r, Select): 
                    isSubquery = True
                    break
                
            return isSubquery
                
        has_NotInNotExists=False
        isSubquery = False
        _, _, boolean_terms = self.get_elements(select)
        if not boolean_terms:
            setattr(select, 'has_NotInNotExists', has_NotInNotExists)
            return
        for term in boolean_terms:
            for r in term.get_children():
                if isinstance(r, Parenthesis):
                    isSubquery = Subquery(r)
                    if isSubquery:break    
            if term.get_operator() in( 'not exists', 'not in') and isSubquery :
                has_NotInNotExists=True 

        setattr(select, 'has_NotInNotExists', has_NotInNotExists)
        
class UnionInsteadUnionAll():
    """
    Detect Union operator
    """ 
    numberOfUnion = 0   
    numberOfUnionAll = 0                    
    def end_Select(self, select):
        self.finalise_statement(select)

    def end_Update(self, update):
        self.finalise_statement(update)

    def end_Delete(self, delete):
        self.finalise_statement(delete)

    def end_Merge(self, merge):
        self.finalise_statement(merge)
                                     
    def finalise_statement(self, select):
        tokens = select.get_tokens()
        token = tokens.look_next()
        unionList = set()
        unionAllList = set()
        def tdeep (self): 
            for tdetails in self.get_children():               
                if isinstance(tdetails, Union): 
                    if not '%s.%s' % (tdetails.get_begin_line(), tdetails.get_begin_column()) not in unionList:
                        self.numberOfUnion += 1
                        unionList.add('%s.%s' % (tdetails.get_begin_line(), tdetails.get_begin_column()))
                elif isinstance(tdetails, UnionAll):
                    if not '%s.%s' % (tdetails.get_begin_line(), tdetails.get_begin_column()) not in unionAllList:
                        self.numberOfUnionAll += 1
                        unionAllList.add('%s.%s' % (tdetails.get_begin_line(), tdetails.get_begin_column()))
                elif tdetails.get_children():tdeep(tdetails) 
                
        for token in tokens:  
            if isinstance(token, Union):
                if '%s.%s' % (token.get_begin_line() , token.get_begin_column()) not in unionList:
                    self.numberOfUnion += 1
                    unionList.add('%s.%s' % (token.get_begin_line() , token.get_begin_column()))
            elif isinstance(token, UnionAll):
                if '%s.%s' % (token.get_begin_line(), token.get_begin_column()) not in unionAllList:
                    self.numberOfUnionAll += 1
                    unionAllList.add('%s.%s' % (token.get_begin_line(), token.get_begin_column()))
            elif token.get_children():tdeep(token)

        setattr(select, 'numberOfUnion', self.numberOfUnion)
        setattr(select, 'numberOfUnionAndUnionAll', self.numberOfUnion + self.numberOfUnionAll)


class MissingParenthesisInsertClause():
    """
    Detect when the parenthesis enclosing column names is missing in an insert clause.
    
    Non compliant example: 
        INSERT into Table1 values (1,2,3); 
    
    Compliant example:
        INSERT into Table1 (col1,col2,col3) values (1,2,3);
    """                                      
                  
    def end_Insert(self, insert):
        # Note: in a insert-into-select structure, the select part is not captured by the parser,
        #       use a try/except to avoid StopIteration errors.
        def found_punctuation(ins_nodes):            
            try:
                node = ins_nodes.look_next()
                if node.type == Punctuation:                                        
                    return True
            except StopIteration:
                pass                  
            return False 
                    
        children = insert.get_children()
        insert_clause = next(children)                          
        insert_nodes = insert_clause.get_children()
        missing = True   
                                                                     
        # treat missing into token
        next(insert_nodes)
        node = insert_nodes.look_next()
        # case of MERGE statement
        if isinstance(node, Parenthesis):
            missing = False
            setattr(insert, 'missingParenthesis', missing) 
            return

        if node == "into":
            next(insert_nodes)
                          
        node = next(insert_nodes)
        try: 
            assert(node.type == Name)         
        except AssertionError:
            pass  
        
        if node =='[':
            insert_nodes.move_to(']')
            try:
                node = insert_nodes.look_next()
            except StopIteration:
                pass
                                          
        # case: scheme1.table1
        while found_punctuation(insert_nodes):
            next(insert_nodes)
            node = next(insert_nodes)
            try:
                assert(node.type == Name)
            except AssertionError:
                if isinstance(node, Parenthesis) or isinstance(node, FunctionCall):
                    missing = False
                    setattr(insert, 'missingParenthesis', missing) 
                    return
                pass
            
        if node =='[':
            insert_nodes.move_to(']')
            try:
                node = insert_nodes.look_next()
            except StopIteration:
                pass    
        # look for Parenthesis
        try:
            node = next(insert_nodes)
            #FunctionCall is the case of alias followed by parenthesis and list of the columns
            if isinstance(node, Parenthesis) or isinstance(node, FunctionCall):
                missing = False
                setattr(insert, 'missingParenthesis', missing) 
                return
        except StopIteration:
            pass
        
        setattr(insert, 'missingParenthesis', missing)        
          
class HasGroupByClause():
    """
    Detect Group By Clause
    """                
    def end_Select(self, select):
        self.finalise_statement(select)

    def end_Update(self, update):
        self.finalise_statement(update)

    def end_Delete(self, delete):
        self.finalise_statement(delete)

    def end_Merge(self, merge):
        self.finalise_statement(merge)
                                     
    def finalise_statement(self, select):
        groupBy = select.get_groupBy()
        if groupBy: setattr(select, 'hasGroupByClause', True)
        else: setattr(select, 'hasGroupByClause', False)  
        
class OrderByColumnNumber():
    """
    Detect Order by column numbers
    """                
    def end_Select(self, select):
        self.finalise_statement(select)

    def end_Update(self, update):
        self.finalise_statement(update)

    def end_Delete(self, delete):
        self.finalise_statement(delete)

    def end_Merge(self, merge):
        self.finalise_statement(merge)
                                     
    def finalise_statement(self, select):
        orderBy = select.get_orderBy()
        has_numbers = False

        if orderBy:
            children = orderBy.get_children()
            token = children.move_to('BY')
            try:
                token = next(children)  
                nc = None
                case = None
                then = None
                elsecase = None
                prevToken = None
                
                # the case of
                # ORDER BY SUM(CASE WHEN (PaidDate IS NULL OR PaidDate>@obs_date) THEN 0 ELSE 1 END) ASC
                try:
                    if isinstance(token, FunctionCall):
                        children = token.get_children()
                        token = next(children)
                        if token == 'sum':
                            token = children.look_next()
                            if isinstance(token, Parenthesis):
                                children = token.get_children()
                                next(children)
                                token = children.look_next()
                                if isinstance(token, BooleanTerm):
                                    children = token.get_children()
                                    token = next(children)
                except:
                    pass
                
                while token:
                    if token.type == None:
                        cnone = token.children
                        for cn in cnone:
                            if cn == 'CASE':case = 1
                            if cn == 'THEN':then = 1
                            if cn == 'ELSE' or isinstance(cn, Else):
                                elsecase = 1
                                if isinstance(cn, Else):
                                    cnvalue = cn.get_children()
                                    cn_int = cnvalue.move_to('ELSE')
                                    cn_int = next(cnvalue)
                                    cn.type = cn_int.type
                            if then == 1 and case == 1 and cn.type == Number.Integer:
                                has_numbers = True
                                break
                            if elsecase == 1 and case == 1 and cn.type == Number.Integer:
                                has_numbers = True
                                break                            
                    if prevToken:
                        # if calculations , like col1 * 2, or limit X like order by col limit 1, or offset X,than go to the next one
                        if (prevToken.type==Operator or prevToken in ['limit', 'offset', 'for', 'option']) and token.type == Number.Integer:
                            token = next(children)
                            continue 
                    if token.type == Number.Integer:
                        try:
                            nc = next(children)
                            if nc:
                                if nc.type == Punctuation or nc in ['limit', 'offset', 'for', 'option']:
                                    has_numbers = True
                                    break
                                elif nc in ['asc', 'desc', 'collate', 'end']:
                                    has_numbers = True
                                    break
                                else:
                                    has_numbers = False
                                    break
                            else:
                                has_numbers = True
                                break
                        except:
                            if nc:break
                            has_numbers = True
                            break
                    prevToken = token
                    token = next(children)
            except StopIteration:
                pass
        else:
            setattr(select, 'has_numbers', False)
           
        setattr(select, 'has_numbers', has_numbers)      

class NonAnsiJoin(DiagCommon):
    """
    Detect NON ANSI JOINs 
    """ 
    def end_Select(self, select):
        self.finalise_statement(select)

    def end_Update(self, update):
        self.finalise_statement(update)
                               
    def end_Delete(self, delete):
        self.finalise_statement(delete)

    def end_Merge(self, merge):
        self.finalise_statement(merge)
                              
    def finalise_statement(self, select):
        table_references, joins, _ = self.get_elements(select)
        
        if len(table_references) > 1 and len(joins) == len(table_references) - 1:has_nonAnsiJoin = False
        elif len(table_references) <= 1:has_nonAnsiJoin = False
        else:has_nonAnsiJoin = True

        setattr(select, 'has_nonAnsiJoin', has_nonAnsiJoin)
        
class NaturalJoin(DiagCommon):
    """
    Detect NATURAL JOIN Syntax in Statements
    """ 
    def end_Select(self, select):
        self.finalise_statement(select)

    def end_Update(self, update):
        self.finalise_statement(update)
                               
    def end_Delete(self, delete):
        self.finalise_statement(delete)

    def end_Merge(self, merge):
        self.finalise_statement(merge)
                             
    def finalise_statement(self, select):
        has_naturalJoin = False
        _, joins, _ = self.get_elements(select)
       
        for join in joins:  
            if join.is_natural():
                has_naturalJoin = True
                break

        if has_naturalJoin:setattr(select, 'has_naturalJoin', True)
        else:setattr(select, 'has_naturalJoin', False)
        
class NonSARG(DiagCommon):
    """
    Detect NONSarg statements
    """                 
    def end_Select(self, select):
        self.finalise_statement(select)
                                    
    def end_Delete(self, delete):
        self.finalise_statement(delete)

    def end_Update(self, update):
        self.finalise_statement(update)

    def end_Merge(self, merge):
        self.finalise_statement(merge)
        
    def finalise_statement(self, select):
        def get_text(tokens):
            return ''.join(token.text for token in tokens if token not in ['and', 'or', 'between', 'all', 'any', 'not', 'in', 'exists', 'like', '~~', '!~~','!~~*', 'is null', 'unique'])

        try:
            sarg=False
            # flag a nonSARGable predicate/expression
            notsomething = False 
            # count boolean terms
            countTerms = 0
            # count nonSARGable predicates/expressions
            countnotsomething = 0
            haveParenthesis = False 
            # you have a between which means you have more than 1 expression, for the last check before saving
            prevBetween = False
            _, _, boolean_terms = self.get_elements(select)
            # same as for prevBetween, for boolean expressions
            prevWasBetween = False
            if boolean_terms:
                for term in boolean_terms:
                    # leftfunctioncall and rightfunctioncall counts functions calls in each side of operators
                    # you could have more than 1
                    leftfunctioncall = 0
                    rightfunctioncall = 0
                    if term.get_operator() == 'BETWEEN': 
                        prevWasBetween = True
                        countTerms += 1
                    elif prevWasBetween:
                        # skip 1 of them, do nothing if the previous operator was between
                        continue
                    else:countTerms += 1
                    haveParenthesis = False
                    countnotsomething_by_level = 0
                    if term.get_operator() in ['<>', '!=', '!>','!<', 'not' , 'not exists', 'not in', 'not like']:
                        sarg=False
                        notsomething = True 
                        countnotsomething_by_level += 1  
                    l=0
                    for tleft in term.left:
                        l +=1 
                        if isinstance(tleft, Select): 
                            countTerms -= 1 
                            break
                        if tleft == 'is' and len(term.left) > l:
                            if term.left[l] in ['null', 'not']:
                                sarg=False
                                notsomething = True 
                                countnotsomething_by_level += 1 
                                break
                        if tleft in ['right', 'left'] and len(term.left) > l:
                            if isinstance(term.left[l], Parenthesis):
                                leftfunctioncall += 1
                                sarg=False
                                notsomething = True 
                                break
                        if isinstance(tleft, FunctionCall):
                            for tcol in tleft.get_children():
                                for tccol in tcol.get_children():
                                    for tdetail in tccol.get_children():
                                        if tdetail.type == Name: 
                                            leftfunctioncall += 1
                                            sarg=False
                                            notsomething = True 
                                            break
                        else: notsomething = False  
                        if tleft.type == Operator and not prevWasBetween:
                            sarg=False
                            notsomething = True 
                            countnotsomething_by_level += 1 
                            break 
                    r = 0
                    for tright in term.right:
                        r +=1 
                        
                        if tright in ['loop', 'while', 'perform', 'if', 'else'] or isinstance(tright, Else): 
                            sarg=False
                            notsomething = False
                            break
                        if isinstance(tright, Parenthesis):
                            haveParenthesis = True
                            break
                        if isinstance(tright, FunctionCall):
                            rightfunctioncall += 1
                            sarg=False
                            notsomething = True
                            break
                        if tright.type == Operator:
                            if len(term.right)>r and tright.text  == '/':
                                if term.right[r] == '/' :
                                    break
                            elif len(term.right)>r and term.right[r-1] != '@' :# exclude operators at the end of a right expression that are more separators than operators
                                sarg=False
                                notsomething = True 
                                countnotsomething_by_level += 1 
                                break 
                        else: notsomething = False   
                    # you if have the same number of function calls in each side that count what you have in one side
                    # else count the side with the bigger number of function calls               
                    if rightfunctioncall == leftfunctioncall:                   
                        countnotsomething_by_level += leftfunctioncall
                    elif rightfunctioncall > leftfunctioncall:
                        countnotsomething_by_level += rightfunctioncall
                    else:countnotsomething_by_level += leftfunctioncall
                    if countnotsomething_by_level > 0 : countnotsomething +=1
#                     print(countTerms, countnotsomething_by_level, countnotsomething)
                    if notsomething or haveParenthesis:
                        continue   
                    try:    
                        notequal = 0
                        for o in term.get_operator():
                            if o =='@':
                                notequal = 1
                        # the case of mariadb and delimiter
                        if get_text(term.right[-3:]) == "//DELIMITER":
                            term_right = get_text(term.right[0:-3])
                        elif get_text(term.right[-1:]) == "/":
                            term_right = get_text(term.right[0:-1])
                        else : term_right = get_text(term.right)
                        if get_text(term.left) == term_right and notequal == 0:
                            sarg=False
                            notsomething = True 
                            if countnotsomething_by_level == 0:
                                countnotsomething += 1
                            continue 
                    except TypeError:
                        pass
                    if term.get_operator() in ['in', 'exists', 'like']:
                        for r in term.right:
                            if r.text:
                                if r.text.find('%') == 1:
                                    self.sarg=False
                                    notsomething = True
                                    if countnotsomething_by_level == 0:
                                        countnotsomething += 1
                                else: notsomething = False 
                if countTerms == 0 and countnotsomething > countTerms: countnotsomething = countTerms
#                 print(sarg, countTerms, len(boolean_terms), len(term.left), len(term.right), term.get_operator(), countnotsomething)
                prevBetween = False
                booleantermslength = 0
                for t in boolean_terms:
                    booleantermslength +=1
                    operators = t.get_operator()
                    if len(boolean_terms) > 1 and operators == 'BETWEEN':
                        prevBetween = True
                    if prevBetween and operators != 'BETWEEN' : 
                        continue
                    if operators and countTerms > countnotsomething or countTerms == 0 and countnotsomething == 0: 
                        sarg=True
                    else:pass

            else:sarg=True
    
            if not sarg:setattr(select, 'has_nonSARG', True)
            else: setattr(select, 'has_nonSARG', False)
        except:
            print('issue in NonSARG')
            pass
        
class NestedSubQueries():
    """
    Count Number Of Nested SubQueries
    """
    maxDepth = 0    
                
    def end_Select(self, select):
        self.finalise_statement(select)
                                    
    def end_Delete(self, delete):
        self.maxDepth = 0
        self.finalise_statement(delete)

    def end_Update(self, update):
        self.maxDepth = 0
        self.finalise_statement(update)

    def end_Merge(self, merge):
        self.maxDepth = 0
        self.finalise_statement(merge)
                                              
    def finalise_statement(self, select):
        tokens = select.get_tokens()
        token = tokens.look_next()
        for token in tokens:
            realTokens = token.get_children()
            for realToken in realTokens:
                nextlevels = realToken.get_children()
                nl= 0
                resultSetDetectedNl = 0
                resultSetDetected = False
                for nextlevel in nextlevels:
                    nl += 1
                    if isinstance(nextlevel, Union) or isinstance(nextlevel, Except) or isinstance(nextlevel, UnionAll):
                        resultSetDetected = True
                        resultSetDetectedNl = nl
                    if isinstance(nextlevel, Parenthesis):# == '(' and nextlevels.next() == 'SELECT': # this is a query
                        queries = nextlevel.get_children()
                        for query in queries:
                            if isinstance(query, Select):
                                if resultSetDetected and nl == resultSetDetectedNl+1: 
                                    resultSetDetected = False
                                    resultSetDetectedNl = 0
                                else:
                                    self.maxDepth += 1
                            if isinstance(query, BooleanTerm):
                                subqueries = query.get_children()
                                for subquery in subqueries:
                                    if isinstance(subquery, Select):
                                        self.maxDepth += 1

        if self.maxDepth > 0:
            setattr(select, 'has_maxDepth', True)
            setattr(select, 'maxDepth', self.maxDepth)
        else:
            setattr(select, 'has_maxDepth', False)
   
class CartesianProduct(DiagCommon):
    """
    Interprets select for the rule avoid cartesian product
    """
    
    class Context:
        """
        Context that store some information 
        """
        def __init__(self, select):
            self.select = select
            self.in_where = False
            self.has_function_call = False
            self.has_operation = False
    
    def __init__(self):
        
        self.context_stack = []

    def start_Where(self, _):
        
        if self.context_stack:
            self.context_stack[-1].in_where = True

    def end_Where(self, _):
        if self.context_stack:
            self.context_stack[-1].in_where = False

    def start_On(self, _):
        if self.context_stack:
            self.context_stack[-1].in_where = True

    def end_On(self, _):
        if self.context_stack:
            self.context_stack[-1].in_where = False
    
    def start_FunctionCall(self, _):
        # limitation : if we have FunctionCall in the where clauses part (even in join on ...)
        # then we cannot conclude yet if we have a violation or not
        if self.context_stack and self.context_stack[-1].in_where:
            self.context_stack[-1].has_function_call = True
    
    def start_BooleanTerm(self, term):
        
        if self.context_stack and self.context_stack[-1].in_where:
            children = term.get_children()
            # current limitations : when operators or exists ... cannot conclude
            #
            token = children.move_to(['+', '-', '*', '/', 'EXISTS'])
            if token:
#                 print('limitation due to', token)
                self.context_stack[-1].has_operation = True

    def start_Select(self, select):
        
        self.context_stack.append(CartesianProduct.Context(select))

    def end_Select(self, select):
    
        self.finalise_statement(select)

    def start_Delete(self, select):

        self.context_stack.append(CartesianProduct.Context(select))

    def end_Delete(self, delete):
    
        self.finalise_statement(delete)

    def start_Update(self, select):

        self.context_stack.append(CartesianProduct.Context(select))

    def end_Update(self, update):
    
        self.finalise_statement(update)

    def start_Merge(self, merge):

        self.context_stack.append(CartesianProduct.Context(merge))

    def end_Merge(self, merge):
    
        self.finalise_statement(merge)
           
    def finalise_statement(self, select):

#         print("===========")
#         select.print_tree()

        class Group:
            
            def __init__(self):
                
                self.table_references = []
            
            def contains(self, table_reference):
                
                return table_reference in self.table_references
                
            @staticmethod
            def create(table_reference):
                result = Group()
                result.table_references = [table_reference]
                return result

            @staticmethod
            def merge(group1, group2):
                result = Group()
                result.table_references = group1.table_references + group2.table_references
                return result
                
                
        class Groups:
            
            def __init__(self, table_references):
                self.groups = []
                for table_reference in table_references:
                    self.groups.append(Group.create(table_reference))

            def connect(self, tr1, tr2):

                # find groups
                # remove them
                def find_group(table_reference):
                    result = None
                    for group in self.groups:
                        if group.contains(table_reference):
                            result = group
                            break
                    return result
                    
                group1 = find_group(tr1)
                group2 = find_group(tr2)
                
                if group1 and group2 and group1 != group2:
                    self.groups.remove(group1)
                    self.groups.remove(group2)
                    # replace by merged
                    self.groups.append(Group.merge(group1, group2))


        table_references, joins, boolean_terms = self.get_elements(select)

        groups = Groups(table_references)
        
        has_unresolved = False
        
        for boolean_term in boolean_terms:
            
            left = boolean_term.get_left_identifier()
            right = boolean_term.get_right_identifier()
            if left and right:
                if not hasattr(left, 'table_reference_is_resolved') \
                    or not hasattr(right, 'table_reference_is_resolved')\
                    or (hasattr(left, 'table_reference_is_resolved') and right.name =='null'):
                    #case when I have is null or is not null in the right side or one of left/side are not resolved
                    pass
                 
                if left.table_reference_is_resolved and right.table_reference_is_resolved:
                    groups.connect(left.table_reference, right.table_reference)
                else:
                    # unresolved ...
                    has_unresolved = True

        for join in joins:
            
            if join.is_natural() or join.get_using_columns():
                groups.connect(join, join.get_joined())

        setattr(select, 'has_cartesian_product', len(groups.groups) > 1)
        setattr(select, 'has_cartesian_product_limitation', False)
        
        if self.context_stack[-1].has_function_call or self.context_stack[-1].has_operation or has_unresolved:
            setattr(select, 'has_cartesian_product', None)
            # for future usage (statistics and so on)
            setattr(select, 'has_cartesian_product_limitation', True)
        
        # xxl 
        has_xxl = False
        for table_reference in table_references:
            try:
                table = table_reference.get_table().get_unique_reference()
                if table.is_xxl:
                    has_xxl = True
            except AttributeError:
                pass
        
        setattr(select, 'has_cartesian_product_xxl', has_xxl and select.has_cartesian_product)
        
        self.context_stack.pop()


class NoIndexCanSupport(DiagCommon):
    """
    For each table reference of the select we gather the 
    columns used in boolean terms
    
    then we can determine if there exists an applicable index for the table 
    """
    def end_Select(self, select):
    
        self.finalise_statement(select)

    def end_Delete(self, delete):
    
        self.finalise_statement(delete)

    def end_Update(self, update):
    
        self.finalise_statement(update)

    def end_Merge(self, merge):
    
        self.finalise_statement(merge)
            
    def finalise_statement(self, select):
        
        table_references, _, boolean_terms = self.get_elements(select)
        
        # true when we are in a situation where we cannot conclude 
        limitation = False
        
        # @todo : any unresolve in columns usage mean that we will have false positives...
        
        # columns used per table reference
        columns_per_table_reference = defaultdict(list)
        for boolean_term in boolean_terms:
            if boolean_term.get_operator() in ('exists', 'not exists'):
                limitation = True
            
#             print(boolean_term)
            left = boolean_term.get_left_identifier()
            if left and left.table_reference_is_resolved and left.table_reference and left.column_is_resolved:
                columns_per_table_reference[left.table_reference].append(left.column)
                        
            right = boolean_term.get_right_identifier()
            if right and right.table_reference_is_resolved and right.table_reference and right.column_is_resolved:
                columns_per_table_reference[right.table_reference].append(right.column)

        # now
        # for all table reference of the query : do we have an applicable index ?
        # incorrect : for example, if we have 2 tables, we only need one table index ?? 
        
        violation = False
        xxl_violation = False
        
        additional_bookmarks = []
        additional_bookmarks_xxl = []
        
        # empty where : no violation
        if boolean_terms and not limitation:
            
            for table_reference in table_references:
                
                table_identifier = table_reference.get_table()
                try:
                    if table_identifier and table_identifier.reference:
                        list_of_columns = columns_per_table_reference[table_reference]
                        table = table_identifier.reference[0]
                        applicable_indexes = []
                        for index in table.indexes:
                            applicable = True
                            if index.columns[0] not in list_of_columns:
                                applicable = False
                            
                            if applicable:
                                applicable_indexes.append(index)
                        
                        if not applicable_indexes and not table.is_xxs:
                            # if the view is indexed but the columns are not specified or indexed columns are not in the where clause
                            if isinstance(table, View): 
                                violation = False
                            else: violation = True
                            
                            if violation:
                                # add additional bookmarks on table + indexes
                                if table.bookmark:
                                    additional_bookmarks.append(table.bookmark)
                                for index in table.indexes:
                                    if index.bookmark:
                                        additional_bookmarks.append(index.bookmark)
                                
                                # xxl case :
                                if table.is_xxl:
                                    xxl_violation = True
                                    if table.bookmark:
                                        additional_bookmarks_xxl.append(table.bookmark)
                                    for index in table.indexes:
                                        if index.bookmark:
                                            additional_bookmarks_xxl.append(index.bookmark)
                except:
                    print('issue in no_index_can_support')
                    pass
        setattr(select, 'no_index_can_support', violation)
        setattr(select, 'no_index_can_support_bookmarks', additional_bookmarks)
        setattr(select, 'no_index_can_support_xxl', xxl_violation)
        setattr(select, 'no_index_can_support_xxl_bookmarks', additional_bookmarks_xxl)

                
class FunctionCallOnIndex(DiagCommon):
    """
 
    """
    def end_Select(self, select):
    
        self.finalise_statement(select)

    def end_Delete(self, delete):
    
        self.finalise_statement(delete)

    def end_Update(self, update):
    
        self.finalise_statement(update)

    def end_Merge(self, merge):
    
        self.finalise_statement(merge)
            
    def finalise_statement(self, select):
        
        _, _, _ = self.get_elements(select)
        
#         for boolean_term in boolean_terms:
#             
#             print(boolean_term.get_all_identifiers())
            

  

def parse_select(stream):
    """
    Parse a DML statement
        Statements and sub-statements could be grouped by  parenthesis blocks
        Control flow statements are also parsed, like If, Loop, etc
        Dynamic statements are parsed too
        The more complex is the SELECT statement
    """
    parser = Parser(SqlLexer, 
                    # Oracle external non ansi outer join 
                    [ExternalNonAnsiJoin, CURRENT_Exceptions, NoCount, NoLock, Distinct], 
                    # recurse
                    [Parenthesis], 
                    [Union, UnionAll, SetCurrent, Except, HandlerFor, \
                      ExecuteImmediate, ExecuteDynamicString0, \
                      ExecuteDynamicString2, ExecuteDynamicString3, \
                      ExecuteDynamicString4, ExecuteDynamicString5, \
                      ExecuteDynamicString6, 
                      ROLLBACK, RELEASE, SAVEPOINT],
                    [Return], 
                    [ExceptionWhenThen, CreateFunctionProcedure, RenameObjects],
                    [Elseif, Loop, EndIfWithSpace, InsertClause, UpdateClause,\
                      DeleteClause, ExecuteClause, SelectList, Values, From, \
                      Where, GroupBy, OrderBy, Having, Window, PartitionBy, \
                      Into, Cursor, Ctas], # split in 3 SELECT ... FROM ... WHERE
                    [ExecuteDynamicCursor, Case, Try, Catch, While, \
                     ExecuteDynamicString1, FunctionCall, Declare, 
                     OnException],
                    [If, Else],
                    {From:[Using]},
                    {From:[TableReference], Using:[TableReference], SelectList:[Column]}, # split for ','
                    {TableReference:[Join]}, # handle joins in from 
                    {Join:[On]},
                    [Merge, GoTo, Insert, Update, Delete, Execute, Select], # final : group select/from/where into one node
                    {Where:[BooleanTerm], On:[BooleanTerm], Parenthesis:[BooleanTerm]}
                    )
    
    return parser.parse_stream(stream)


class WithBooleanTerms:
    
    def get_boolean_terms(self):
        """
        Return a list of BooleanTerm in the element.
        """
        # direct result
        result = []

        # indirect one
        for node in self.get_sub_nodes():
            if isinstance(node, BooleanTerm) and not ('CURRENT' in list(node.get_children()) and 'OF' in list(node.get_children())):
                result.append(node)
            try:
                result += node.get_boolean_terms()
            except AttributeError:
                pass

        return result


class Parenthesis(BlockStatement, WithBooleanTerms):
    begin ='('
    end   = ')'

class ExternalNonAnsiJoin(Term):
    match =Seq('(', '+' ,')')

"""
DB2
CURRENT DATE / TIME / TIMESTAMP should not be identified as function call
"""
class CURRENT_Exceptions(Term):
    match = Seq('CURRENT', Or('DATE', 'TIME', 'TIMESTAMP'))

""" 
DB2
ROLLBACK should not be identified as function call
"""
class ROLLBACK(Statement):
    begin = 'ROLLBACK'
    end = ';'
"""
DB2
SAVEPOINT should not be identified as function call
"""
class SAVEPOINT(Statement):
    begin = 'SAVEPOINT'
    end = ';'

""" 
DB2
RELEASE should not be identified as function call
"""
class RELEASE(Statement):
    begin = 'RELEASE'
    end = ';'

""" 
DB2, MS SQL
DECLARE should not be identified as function call
"""
class Declare(Term):
    stopped_by_other_statement = True
    match = Seq('DECLARE', Any(), Name)

""" 
Added from mixed DDL and DML files,
    the CREATE FUNCTION / PROCEDURE () ...
    should not be identified as call FUNCTION / PROCEDURE
"""
class CreateFunctionProcedure(Term):
    match = Seq('CREATE', Or('FUNCTION', 'PROCEDURE'), \
                Or(Name, 'LEFT', 'RIGHT', 'SELF'), \
                Optional(Seq('.', Name)), \
                Parenthesis)

""" 
The same for Rename .... ;
"""
class RenameObjects(Statement):
    begin = 'RENAME'
    end = Or(';', '/')
                          
class FunctionCall(Term):
    """
    exact match is f(...)
    """
    match = Seq(Or(Name, 'LEFT', 'RIGHT', 'SELF'), Optional(Seq('.', Name)), Or(Parenthesis, ';'))

    def on_end(self):
        # for overloading, count the number of parameters
        tokens = self.get_children()
        parameters = None
        count_parameters = 0
        for token in tokens:
            if token == 'TABLE':
                inside_token = tokens.look_next()
                for t in inside_token.get_children():
                    if isinstance(t, Parenthesis):
                        parameters = t
                        break
                break
            elif isinstance(token, Parenthesis):
                
                parameters = token
                break
           
        if parameters:
            something_in = False
            all_of_parameters = parameters.get_children()
            for parameter in parameters.get_children():
                # if we have something in except parenthesis, should add 1
                if parameter not in ('(', ')') and not(parameter.type == Punctuation and parameter == ','):
                    something_in = True
                elif parameter.type == Punctuation and parameter == ',':
                    count_parameters += 1

                
            if count_parameters > 0 or (something_in and count_parameters == 0):
                count_parameters += 1
        
            setattr(self, 'parameters', count_parameters)  
            setattr(self, 'list_of_parameters', all_of_parameters)     
    
class Return(Statement):
    stopped_by_other_statement = True
    begin = Seq('RETURN', NotFollowedBy(Or('FOR', ('TO'))))
    end = Optional(';')

class NoCount(Term):
    match = Seq('SET', 'NOCOUNT')
           
class NoLock(Term):
    match = Seq('(', 'NOLOCK', ')')
           
class Distinct(Term):
    match = Or('DISTINCT', 'DISTINCTROW', 'UNIQUE')
 
class GoTo(Term):
    match = 'GOTO'

    def on_end(self):
        setattr(self, 'count_goTo', 1)

class SetCurrent(Term):
    match = Seq('SET', 'CURRENT', Or('SCHEMA', 'PATH'))
      
class Union(Term):
    match = Seq('UNION', NotFollowedBy('ALL'))

class UnionAll(Term):
    match = Seq('UNION', 'ALL')
    
class Except(Term):
    match = Or('EXCEPT', 'MINUS', 'INTERSECT')

class Values(Term):
    match = Seq('VALUES', Parenthesis)
            
class Clause(Statement):
    """
    Clauses of SQL statements.
    """
    stopped_by_other_statement = True
    consume_end = False
    end   = Or(';', 'GO', Union, UnionAll, Except, SetCurrent)
    
    
class InsertClause(Clause):
    begin = Seq(Optional('FOR'), 
                Or(
                    Seq('INSERT', 'INTO', Any(), '.', Any(), '.', Any(), Parenthesis),
                    Seq(Or('INSERT', Seq('REPLACE', NotFollowedBy(Or(Parenthesis, 'DEFINER', 'FORCE', 'PROCEDURE', 'FUNCTION', 'TRIGGER', 'VIEW')))), Optional('INTO'),  Any(), '.',  Any()),
                   Seq(Or('INSERT', Seq('REPLACE', NotFollowedBy(Or(Parenthesis, 'DEFINER', 'FORCE', 'PROCEDURE', 'FUNCTION', 'TRIGGER', 'VIEW')))), Optional('INTO'),  Any()),
                   Seq('INTO', Any(), Parenthesis),
                   Seq('INSERT', Parenthesis),
                   Seq('INSERT', 'INTO', Any(), Any(), Parenthesis),
               ), NotFollowedBy(';'))


class UpdateClause(Clause):
    begin = Seq(Optional('FOR'), 'UPDATE', NotFollowedBy(';'))


class DeleteClause(Clause):
    begin = Or(Seq(Optional('FOR'), Or('DELETE', 'TRUNCATE'), NotFollowedBy('ON')), \
               Seq(Optional('FOR'), Or('DELETE', 'TRUNCATE'), NotFollowedBy(';')))


class ExecuteClause(Clause):
    """
    SQL Server 
    EXEC | EXECUTE  [ @return_status = ] function         
    """
    begin = Or('EXEC', 'EXECUTE', 'CALL')



class SelectList(Clause):
    begin = Seq(Optional('FOR'), 'SELECT')


class From(Clause):
    begin = 'FROM'

class GroupBy(Clause):
    begin = Seq('GROUP', 'BY')


class OrderBy(Clause):
    begin = Seq('ORDER', 'BY')


class Using(Clause):
    begin = Seq('USING', NotFollowedBy(Parenthesis))


class Having(Clause):
    begin = 'HAVING'


class Window(Clause):
    begin = 'WINDOW'


class PartitionBy(Clause):
    begin = Seq('PARTITION', 'BY')


# class For(Clause):
#     begin = 'FOR'

class Into(Clause):
    begin = 'INTO'

def look_for_joined_column(self, nodes):
    for sub_node in nodes.get_sub_nodes():
        if sub_node.get_sub_nodes():
            for look_for_join in sub_node.get_sub_nodes():
                if isinstance(look_for_join, Join):
                    for joined_column in look_for_join.get_columns():
                        self.columns.append(joined_column)
    return 

def look_for_filtered_columns(self, nodes):
    all_columns = set()

    try:
        alias = None
        for column in nodes:
            if isinstance(column, (FunctionCall, Parenthesis)): 
                tokens = column.get_children()
                if isinstance(column, FunctionCall):
                    next (tokens) 
                look_for_filtered_columns(self, tokens)
            # the case of merge
            elif column.type in (Name, Keyword) and column.text.lower() in ('when', 'then', 'else', 'matched'):
                break
            elif column.type in (Operator, Number, String) or (column.type in (Name, Keyword) and column.text.lower() in ('in', 'between', 'or', 'and', 'not', 'null')):
                if column.type == Operator and column == '=' and alias:
                    t = (alias.text, alias.begin_line, alias.begin_column, alias.end_line, alias.end_column)
                    if t not in all_columns:
                        all_columns.add(t)
                        self.columns.append([alias, None])
                alias = None
                token = None
                continue
            if column.type in (Name, Keyword):
                if not alias:
                    alias = column
                token = nodes.look_next()
                # TableName/Alias.ColumnName
                if token.type == Punctuation and token != ')':
                    next(nodes)
                    token = nodes.look_next()
                    if token.type in (Name, Keyword):
                        t = (token.text, token.begin_line, token.begin_column, token.end_line, token.end_column)
                        if t not in all_columns:
                            all_columns.add(t)
                            self.columns.append([token, alias])
                            alias = None
                            token = None
                # only ColumnName
                else:
                    t = (column.text, column.begin_line, column.begin_column, column.end_line, column.end_column)
                    if t not in all_columns:
                        all_columns.add(t)
                        self.columns.append(column)
                        
    except StopIteration:
        pass
    
    del all_columns
    return

def look_for_ordered_grouped_columns(self, nodes):
    all_columns = set()
    try:
        alias = None
        for column in nodes:
            if isinstance(column, (FunctionCall, Parenthesis)): 
                tokens = column.get_children()
                if isinstance(column, FunctionCall):
                    next (tokens) 
                look_for_ordered_grouped_columns(self, tokens)
            # the case of merge
            elif column.type in (Name, Keyword) and column.text.lower() in ('when', 'then', 'else', 'matched'):
                break
            elif (column.type == Punctuation and column.text == ',') or \
                column.type in (Operator, Number, String) or (column.type in (Name, Keyword) and column.text.lower() in ('in', 'between', 'or', 'and', 'not', 'null')):
                alias = None
                token = None
                continue
            elif column.type == Name.Builtin:
                try:
                    token = nodes.look_next()
                except:
                    token = None
                if token and token.type not in (Punctuation, Keyword):
                    alias = column
                    t = None
                    try:
                        t = (token.text, token.begin_line, token.begin_column, token.end_line, token.end_column)
                    except AttributeError:
                        pass
                    if t and t not in all_columns:
                        all_columns.add(t)
                        self.columns.append([token, alias])
                        alias = None
                        token = None
                elif token and token.type in (Punctuation, Keyword):
                    t = (column.text, column.begin_line, column.begin_column, column.end_line, column.end_column)
                    if t not in all_columns:
                        all_columns.add(t)
                        self.columns.append(column)                  
                
            if column.type in (Name, Keyword):
                if not alias:
                    alias = column
                token = nodes.look_next()
                # TableName/Alias.ColumnName
                if token.type == Punctuation and token.text == '.':
                    next(nodes)
                    token = nodes.look_next()
                    if token.type in (Name, Keyword):
                        t = (token.text, token.begin_line, token.begin_column, token.end_line, token.end_column)
                        if t not in all_columns:
                            all_columns.add(t)
                            self.columns.append([token, alias])
                            alias = None
                            token = None
                # only ColumnName
                else:
                    t = (column.text, column.begin_line, column.begin_column, column.end_line, column.end_column)
                    if t not in all_columns:
                        all_columns.add(t)
                        self.columns.append(column)
                    
    except StopIteration:
        pass
    
    del all_columns
    return
      
def parse_column_reference(children):

    # handle #, ##, @ table for sqlserver 
    additional_text = ""
    table_alias = None
    token = children.look_next()
    if token in ['@', '#']:
        additional_text = token.text
        next(children)
    token = children.look_next()
    first_token = token

    # select all columns
    if first_token == '*':
        return first_token, None, table_alias
    
    if first_token == '#':
        additional_text += first_token.text
        next(children)
    
    
    identifier = parse_identifier(children, accept_keywords=True)
    if identifier.tokens:
        if len(identifier.tokens) == 2:
            table_alias = identifier.tokens[0].text
        else:
            table_alias = None
            
        alias = None

        identifier.tokens[0].text = additional_text + identifier.tokens[0].text
        column = Identifier(identifier.tokens)
        try:
            token = children.look_next()
            if token == 'AS':
                token = next(children)
            elif len(identifier.tokens) != 2 and token == '*':
                table_alias = first_token
                column = token
                next(children)
                token = children.look_next()
                if token == 'AS':
                    token = next(children)
                elif token != ',':
                    # the case of calculations
                    column = table_alias
                    table_alias = None
                
            local_alias = parse_identifier(children, accept_keywords=True)
            if local_alias.tokens:
                alias = local_alias.get_name() 
            
        except StopIteration:
            pass
        
        return column, alias, table_alias
    
    return None, None, None

class ColumnReferenceLike:
    
    def parse_column(self, children):
        
        self.column, self.alias, self.table_alias = parse_column_reference(children)
        

class Column(Statement, ColumnReferenceLike):
    begin = Any()
    end   = ','

    def __init__(self):
        Statement.__init__(self)
        self.column = None
        self.alias = None
        self.table_alias = None
        self.subquery = None

    def get_table_alias(self):
        """
        In case of alias return the table alias
        """
        return self.table_alias
    
    def get_alias(self):
        """
        In case of alias return the alias Identifier.
        """
        return self.alias

    def get_column(self):
        """
        In case of column return the column Identifier.
        """
        return self.column
       
    def get_subquery(self):
        """
        In case of subquery return the column identifier.
        """
        return self.subquery
    
    def on_end(self):
        """
        - get column expression : a subquery or a table
        - scan alias
        """
        children = self.get_children()
        
        token = children.look_next()
        if isinstance(token, Parenthesis):
            self.subquery = next(children)
            
            # @todo pull up again this...
            try:
                token = children.look_next()
                if token == 'AS':
                    token = next(children)
                
                token = children.look_next()
                if token == '[':
                    next(children)
                    token = children.look_next()
                alias = parse_identifier(children, accept_keywords=True)
    
                if alias.tokens:
                    self.alias = alias.get_fullname() 
                
            except StopIteration:
                pass

        elif isinstance(token, Distinct):
            next(children)
            token = children.look_next()

            self.column = parse_identifier(children, accept_keywords=True)
            alias = parse_identifier(children, accept_keywords=True)

            if not self.column.get_name() and alias:
                self.column = alias
                alias = None
        else:
            try:
                self.parse_column(children)
            except TypeError:
                # the case of calculations
                pass
                    
def parse_table_reference(children):

    # handle #, ##, @ table for sqlserver 
    additional_text = ""
    token = children.look_next()
    if token in ['@', '#']:
        additional_text = token.text
        next(children)
    token = children.look_next()

    if token == '#':
        additional_text = "".join([additional_text, token.text])
        next(children)
    
    identifier = parse_identifier(children, accept_keywords=True)
    if identifier.tokens:

        alias = None

        identifier.tokens[0].text = '%s%s' % (additional_text, identifier.tokens[0].text)
        table = Identifier(identifier.tokens)
#         print('table is ', table)
        try:
            token = children.look_next()
            if token == 'AS':
                token = next(children)
            
            if not token in ['ON', 'JOIN', 'INNER', 'NATURAL', 'LEFT', 'RIGHT', 'OUTER', 'SET']:
                local_alias = parse_identifier(children, accept_keywords=True)
        
                if local_alias.tokens:
                    alias = local_alias.get_name() 
            
        except StopIteration:
            pass
        
        return table, alias
    
    return None, None



class TableReferenceLike:
    
    def parse_table(self, children):
        
        self.table, self.alias = parse_table_reference(children)
        

class TableReference(Statement,TableReferenceLike):
    begin = Any()
    end   = ','
    
    def __init__(self):
        Statement.__init__(self)
        self.table = None
        self.alias = None
        self.subquery = None
        self.synonym = None
        
    def get_alias(self):
        """
        In case of alias return the alias Identifier.
        """
        return self.alias

    def get_table(self):
        """
        In case of table return the table identifier.
        """
        return self.table

    def get_synonym(self):
        """
        In case of synonym return the table identifier.
        """
#        print('get synonym : ', self)
        return self.table
       
    def get_subquery(self):
        """
        In case of subquery return the table identifier.
        """
        return self.subquery
    
    def get_joins(self):
        """
        Get the list of joins of that table reference
        """
        result = []
        current_joined = self
        for node in self.get_sub_nodes():
            if isinstance(node, Join):
                node.joined = current_joined
                result.append(node)
                current_joined = node
        return result
    
    
    def on_end(self):
        """
        - get table expression : a subquery or a table
        - scan alias
        """
        children = self.get_children()
        
        token = children.look_next()
#         print('token is ', token)
        if isinstance(token, Parenthesis):
            self.subquery = next(children)
            
            # @todo pull up again this...
            try:
                token = children.look_next()
                if token == 'AS':
                    token = next(children)
                
                token = children.look_next()
                if not token in ['JOIN', 'INNER', 'NATURAL', 'LEFT', 'RIGHT', 'OUTER']:
                
                    alias = parse_identifier(children, accept_keywords=True)
        
                    if alias.tokens:
                        self.alias = alias.get_fullname() 
                
            except StopIteration:
                pass

        else:
            self.parse_table(children)

        
def get_sub_nodes(nodes, t):
    
    result = []
    
    for node in nodes:
        if isinstance(node, t):
            result.append(node)
        if isinstance(node, Parenthesis):
            result += get_sub_nodes(node.get_sub_nodes(), t)
    
    return result
    

def get_direct_sub_nodes(node, t):
    
    result = []
    
    for child in node.get_sub_nodes():
        if isinstance(child, t):
            result.append(child)
    
    return result


class On(Statement, WithBooleanTerms):
    """
    ON ... inside a join
    """
    begin = 'ON'
    end = None
        
    
class Join(Statement, TableReferenceLike):
    
    # or statement and stopped_by_other_statement
    stopped_by_other_statement = True
    begin = Seq(Optional('NATURAL'),
                Or(Seq(Optional('INNER'), 'JOIN') , 
                   Seq(Or('LEFT', 'RIGHT', 'FULL'), Optional('OUTER'), 'JOIN'), 
                   Seq('CROSS', 'JOIN')))
    end = None
    

    def __init__(self):
        Statement.__init__(self)
        self.table = None
        self.alias = None
        self.subquery = None
        self.using_columns = []
        self.columns = []
        self.natural = False
        self.joined = None
        
    def calculate_joined_columns (self, nodes):
        nodes.move_to('ON')
        table_column_alias = None
        for token in nodes:
            if token.type in (Name, Keyword):
                if token.type in (Operator) and table_column_alias:
                    t = [table_column_alias, None]
                    self.columns.append(t)
                    table_column_alias = None
                elif token.type not in (Operator, Punctuation) and not table_column_alias:   
                    table_column_alias = token
                else:
                    t = [token, table_column_alias]
                    self.columns.append(t)
                    table_column_alias = None
                                        
    def get_joined(self):
        """
        The other table reference or join we are joining
        """
        return self.joined
        
    def get_alias(self):
        """
        In case of alias return the alias Identifier.
        """
        return self.alias

    def get_table(self):
        """
        In case of table return the table identifier.
        """
        return self.table
    
    def get_subquery(self):
        """
        In case of subquery return the query.
        """
        return self.subquery

    def get_using_columns(self):
        """
        In case of join ... using (column1, ...) return the list of column names
        """
        return self.using_columns
    
    def get_columns(self):
        """
        Get the list of joined coluns
        """
        return self.columns
          
    def is_natural(self):
        """
        True when natural join
        """
        return self.natural

    def get_on(self):
        """
        In case of join ... on <...> return the on part
        """
        for node in self.get_sub_nodes():
            if isinstance(node, On):
                return node
        return None

    def on_end(self):
        """
        - get table expression : a subquery or a table
        - scan alias
        """
        children = self.get_children()
        joined_columns = self.get_children()
        
        token = children.look_next()
        if token == 'NATURAL':
            self.natural = True
            
        children.move_to('join')
        
        token = children.look_next()
        if isinstance(token, Parenthesis):
            joined_columns = None
            self.subquery = next(children)
        else:
            self.parse_table(children)
        
        # @todo : adapt        
        token = children.move_to('USING')
        if token == 'USING':
            joined_columns = None
            parenthesis = next(children)
            
            table_column_alias = None
            for column in parenthesis.get_children():
                if column.type in (Name):
                    # keep unchanged
                    self.using_columns.append(column.text)

                if column.type in (Name, Keyword):
                    if not table_column_alias:   
                        table_column_alias = column
                    else:
                        t = [column, table_column_alias]
                        self.columns.append(t)
                        table_column_alias = None
                elif column.type in (Operator, Punctuation, String, Number):
                    if  (column.type == Operator and column == ',') or (column.type == Punctuation and column in (')', '(')):
                        if table_column_alias:
                            t = [table_column_alias, None]
                            self.columns.append(t)
                            table_column_alias = None    

        if joined_columns:
            joined_columns.move_to('join')
            self.calculate_joined_columns (joined_columns)
        

class Where(Clause, WithBooleanTerms):
    begin = 'WHERE'

class Insert(Statement):
    
    stopped_by_other_statement = True
    begin = InsertClause
    end = ';'

    def __init__(self):
        Statement.__init__(self)
        self.has_nonAnsiJoin = None
        self.has_naturalJoin = None
        self.hasGroupByClause = None
        self.has_numbers = None
        self.has_nonSARG = None
        self.has_maxDepth = None
        self.numberOfUnion = None
        self.numberOfUnionAndUnionAll = None
        self.has_NotInNotExists = None
        self.no_index_can_support = None
        self.has_cartesian_product = None
        self.no_index_can_support_xxl = None
        self.has_cartesian_product_xxl = None 
        self.number_of_tables = None                       
        self.has_independent_exists = None
        self.distinct = None
        self.has_non_ansi_operator = None
        self.has_or_on_the_same_identifier = None
                
class Update(Statement):
    
    stopped_by_other_statement = True
    begin = UpdateClause
    end = ';'
    
    def __init__(self):
        Statement.__init__(self)
        self.updated_tables = []
        self.table_references = []
        self.columns = []
        self.write_columns = []
        self.fromClause = None
        self.where = None
        self.update_table_references = []
        self.orderBy = None
        self.groupBy = None
        self.missingParenthesis = None
        self.number_of_tables = None      
        self.has_independent_exists = None  
        self.distinct = None
        self.has_non_ansi_operator = None
        self.has_or_on_the_same_identifier = None
        
    def get_updated_tables(self):
        """
        Updated tables identifiers
        """
        return self.updated_tables

    def get_updated_table_references(self):
        """
        Updated tables references (with alias)
        """
        return self.update_table_references
    
    def get_additional_table_references(self):
        
        return self.update_table_references
    
    def get_table_references(self):
        """
        Return the table references. 
        
        :rtype: list of TableReference
        """
        return self.table_references
    
    def get_where(self):
        """
        Return the where part. 
        
        :rtype: Where
        """
        return self.where

    def get_from(self):
        """
        Return the from part. 
        
        :rtype: From
        """
        return self.fromClause
       
    def get_orderBy(self):
        """
        Return the order by part. 
        
        :rtype: order by
        """
        return self.orderBy

    def get_groupBy(self):
        """
        Return the group by part. 
        
        :rtype: group by
        """
        return self.groupBy    
                    
    def on_end(self):
        """
        Parsing of update
        
        UPDATE [ONLY]          table_reference SET ...
               [LOW_PRIORITY]
               [IGNORE]
        
        """
        for node in self.get_sub_nodes():

            if isinstance(node, UpdateClause):
                try:
                    self.updated_tables = extract_identifiers(node)
                except TypeError:
                    break
                
                tokens = node.get_children()
                next(tokens) # UPDATE
                
                token = tokens.look_next()
                
                if token in ['ONLY', 'LOW_PRIORITY', 'IGNORE']:
                    next(tokens)
                
                table, alias = parse_table_reference(tokens)
                
                tr = TableReference()
                tr.table = table
                tr.alias = alias
                
                self.update_table_references.append(tr)
                tokens.move_to('set')
                table_column_alias = None
                equal_detected = None
                
                try:
                    token = tokens.look_next()
                    if isinstance(token, Parenthesis):
                        tokens = token.get_children()
                except StopIteration:
                    pass
                
                for token in tokens:
                    if token.type in (Name, Keyword):
                        if not table_column_alias:   
                            table_column_alias = token
                        else:
                            t = [token, table]
                            if not equal_detected :
                                self.write_columns.append(t)
                            else:
                                t = [token, table_column_alias]
                                self.columns.append(t)
                                equal_detected = None
                            table_column_alias = None
                            
                    # set (col1, col2, ....
                    elif token.type == Punctuation and token in( ',', ')') and table_column_alias and not equal_detected:
                        
                        t = [table_column_alias, table]
                        self.write_columns.append(t)
                        table_column_alias = None

                    elif token.type == Punctuation and token == ',' and table_column_alias and equal_detected:
                        
                        t = [table_column_alias, table]
                        self.columns.append(t)
                        table_column_alias = None
                        equal_detected = None
                                                    
                    elif token.type in (Operator, String, Number):
                        if  token.type == Operator and token == '=':
                            equal_detected = True
                            
                            if table_column_alias and table:
                                t = [table_column_alias, table]
                                self.write_columns.append(t)
                            table_column_alias = None
                        continue
                
            elif isinstance(node, From):
                self.fromClause = node
                self.table_references = list(node.get_sub_nodes())
                look_for_joined_column (self, node) 
                
            elif isinstance(node, Where):
                self.where = node
                nodes = node.get_tokens()
                # skip the where keyword
                next(nodes)
                look_for_filtered_columns(self, nodes)
                
            elif isinstance(node, OrderBy):
                self.orderBy = node
                nodes = node.get_tokens()
                # skip the order and by keywords
                next(nodes)
                next(nodes)
                look_for_ordered_grouped_columns(self, nodes)  
                  
            elif isinstance(node, GroupBy):
                self.groupBy = node   
                nodes = node.get_tokens()
                # skip the group and by keywords
                next(nodes)
                next(nodes)
                look_for_ordered_grouped_columns(self, nodes)
                                                           
class Delete(Statement):
    
    stopped_by_other_statement = True
    begin = DeleteClause
    end = ';'
    
    def __init__(self):
        Statement.__init__(self)
        
        self.deleted_tables = []
        self.deleted_table_references = []
        
        self.columns = []
        # the from content
        self.fromClause = None
        self.table_references = []
        # the where
        self.where = None
        self.orderBy = None
        self.groupBy = None
        self.missingParenthesis = None
        self.number_of_tables = None      
        self.has_independent_exists = None
        self.distinct = None
        self.has_non_ansi_operator = None
        self.has_or_on_the_same_identifier = None
                    
    def get_deleted_tables(self):
        """
        Deleted tables identifiers
        """
        return self.deleted_tables

    def get_orderBy(self):
        """
        Return the order by part. 
        
        :rtype: order by
        """
        return self.orderBy
    
    def get_groupBy(self):
        """
        Return the group by part. 
        
        :rtype: group by
        """
        return self.groupBy 
           
    def get_additional_table_references(self):
        
        return self.deleted_table_references
    
    def get_table_references(self):
        """
        Return the table references. 
        
        :rtype: list of TableReference
        """
        return self.table_references
    
    def get_where(self):
        """
        Return the where part. 
        
        :rtype: Where
        """
        return self.where

    def get_from(self):
        """
        Return the from part. 
        
        :rtype: From
        """
        return self.fromClause
                   
    def on_end(self):
        """
        Parsing of delete
        """
        number_of_from = 0 

        for n in self.get_sub_nodes():
            
            if isinstance(n, DeleteClause):
                # delete clause may contain identifiers
                
                tokens = n.get_children()
                
                token = next(tokens) # delete
                if token == 'TRUNCATE':
                    token = tokens.look_next()
                    if token == 'TABLE':
                        next(tokens)
                        
                    token = tokens.look_next()
                    if token == 'ONLY':
                        next(tokens)
                
                while True:
                    try:
                        table, alias = parse_table_reference(tokens)
                        
                        tr = TableReference()
                        tr.table = table
                        tr.alias = alias
                        
                        self.deleted_table_references.append(tr)
                        if table:
                            self.deleted_tables.append(table)
                        
                        tokens.move_to(',')
                    except StopIteration:
                        break
                
            elif isinstance(n, From):
                self.fromClause = n
                number_of_from += 1
                
                table_references = get_direct_sub_nodes(n, TableReference)
                look_for_joined_column (self, n) 
                
                if number_of_from == 1:
                    if self.deleted_tables:
                        # DELETE T1 FROM T2
                        self.table_references = table_references
                    else:
                        # DELETE FROM T1
                        self.deleted_tables = [t.get_table() for t in table_references if t.get_table()]
                        self.deleted_table_references = table_references
                        
                elif number_of_from == 2:
                    # DELETE FROM T1 FROM T2
                    self.table_references = table_references
                        
                # search for using
                if table_references:
                    
                    usings = get_direct_sub_nodes(table_references[0], Using)
                    if usings:
                        
                        self.table_references = get_direct_sub_nodes(usings[0], TableReference)
                    
            elif isinstance(n, Where):
                self.where = n
                nodes = n.get_tokens()
                # skip the where keyword
                next(nodes)
                look_for_filtered_columns(self, nodes)
                
            elif isinstance(n, OrderBy):
                self.orderBy = n
                nodes = n.get_tokens()
                # skip the order and by keywords
                next(nodes)
                next(nodes)
                look_for_ordered_grouped_columns(self, nodes)
                
            elif isinstance(n, GroupBy):
                self.groupBy = n
                nodes = n.get_tokens()
                # skip the group and by keywords
                next(nodes)
                next(nodes)
                look_for_ordered_grouped_columns(self, nodes)


class Merge(Statement):
    
    begin = 'MERGE'
    end = ';' 
    
    def __init__(self):
        Statement.__init__(self)
        self.updated_tables = []
        self.inserted_tables = []
        self.deleted_tables = []
        self.table_references = []
        self.columns = []
        self.write_columns = []
        
        self.fromClause = None
        self.where = None
        self.update_table_references = []
        self.insert_table_references = []
        self.orderBy = None
        self.groupBy = None
        self.missingParenthesis = None
        self.has_nonAnsiJoin = None
        self.has_naturalJoin = None
        self.hasGroupByClause = None
        self.has_numbers = None
        self.has_nonSARG = None
        self.has_maxDepth = None
        self.numberOfUnion = None
        self.numberOfUnionAndUnionAll = None
        self.has_NotInNotExists = None
        self.no_index_can_support = None
        self.has_cartesian_product = None
        self.no_index_can_support_xxl = None
        self.has_cartesian_product_xxl = None    
        self.number_of_tables = None      
        self.has_independent_exists = None  
        self.distinct = None
        self.has_non_ansi_operator = None
        self.has_or_on_the_same_identifier = None
         
    def get_updated_tables(self):
        """
        Merged tables identifiers
        """
        return self.updated_tables
    def get_inserted_tables(self):
        """
        Merged tables identifiers
        """
        return self.inserted_tables
    def get_deleted_tables(self):
        """
        Merged tables identifiers
        """
        return self.deleted_tables
    def get_updated_table_references(self):
        """
        Merged tables references (with alias)
        """
        return self.update_table_references
    def get_inserted_table_references(self):
        """
        Merged tables references (with alias)
        """
        return self.insert_table_references   
     
    def get_additional_table_references(self):
        
        return self.update_table_references
    
    def get_table_references(self):
        """
        Return the table references. 
        
        :rtype: list of TableReference
        """
        return self.table_references
    
    def get_where(self):
        """
        Return the where part. 
        
        :rtype: Where
        """
        return self.where

    def get_from(self):
        """
        Return the from part. 
        
        :rtype: From
        """
        return self.fromClause
       
    def get_orderBy(self):
        """
        Return the order by part. 
        
        :rtype: order by
        """
        return self.orderBy

    def get_groupBy(self):
        """
        Return the group by part. 
        
        :rtype: group by
        """
        return self.groupBy    
                    
    def on_end(self):
        number_of_from = 0
        tokens = self.get_children()
 
        next(tokens)
        token = tokens.look_next()
        if isinstance(token, Into):
            tokens = token.get_children()
            next(tokens)
            token = tokens.look_next()
            
        table, alias = parse_table_reference(tokens)
        tr = TableReference()
        tr.table = table
        tr.alias = alias
        self.table_references.append(tr)

        for node in self.get_sub_nodes():                              
            if isinstance(node, UpdateClause):               
                self.update_table_references.append(tr)
                
                tokens = node.get_children()
                tokens.move_to('set')
                table_column_alias = None
                equal_detected = None
                
                try:
                    token = tokens.look_next()
                    if isinstance(token, Parenthesis):
                        tokens = token.get_children()
                except StopIteration:
                    pass
                    
                for token in tokens:
                    if token.type in (Name, Keyword):
                        # the merge case when ...
                        if token.text.lower() == 'when':
                            break
                        if not table_column_alias:   
                            table_column_alias = token
                        else:
                            t = [token, table]
                            if not equal_detected :
                                self.write_columns.append(t)
                            else:
                                t = [token, table_column_alias]
                                self.columns.append(t)
                                equal_detected = None
                            table_column_alias = None
                    elif token.type in (Operator, String, Number):
                        if  token.type == Operator and token == '=':
                            equal_detected = True
                            
                            if table_column_alias:
                                t = [table_column_alias, table]
                                self.write_columns.append(t)
                                table_column_alias = None
                    
            elif isinstance(node, InsertClause):          
                self.insert_table_references.append(tr)     
                tokens = node.get_children()
                next(tokens)
                token = tokens.look_next()
                if isinstance(token, Parenthesis):
                    list_of_columns = token.get_children()
                    table_column_alias = None
                    for column in list_of_columns:
                        if column.type in (Name, Keyword):
                            # the merge case when ...
                            if column.text.lower() == 'when':
                                break
                            if not table_column_alias:   
                                table_column_alias = column
                            else:
                                t = [column, table]
                                self.write_columns.append(t)
                                table_column_alias = None
                        elif column.type in (Punctuation, Operator, String, Number):
                            if  column.type in (Punctuation, Operator) and column in ( ',', ')'):
                                if table_column_alias:
                                    t = [table_column_alias, table]
                                    self.write_columns.append(t)
                                    table_column_alias = None
                
            elif isinstance(node, DeleteClause):   
                self.deleted_tables.append(tr)
            elif isinstance(node, Parenthesis):    
                children = self.get_children()                              
                self.subquery = next(children)
            
            elif isinstance(node, Where):
                self.where = node
                nodes = node.get_tokens()
                # skip the where keyword
                next(nodes)
                look_for_filtered_columns(self, nodes)
                
            elif isinstance(node, OrderBy):
                self.orderBy = node
                nodes = node.get_tokens()
                # skip the order and by keywords
                next(nodes)
                next(nodes)
                look_for_ordered_grouped_columns(self, nodes)
                
            elif isinstance(node, GroupBy):
                self.groupBy = node
                nodes = node.get_tokens()
                # skip the group and by keywords
                next(nodes)
                next(nodes)
                look_for_ordered_grouped_columns(self, nodes)
                
            elif isinstance(node, From) or isinstance(node, Using):
                number_of_from += 1
                self.fromClause = node
                self.table_references = list(node.get_sub_nodes())
                                                      
class Execute(Statement):
    
    stopped_by_other_statement = True
    begin = ExecuteClause
    end = ';'

class Else(BlockStatement):
    begin = 'ELSE'
    end = Or(EndIf, Seq('END', Optional('IF')), 'ELSIF', 'ELSEIF', Return, 'IF') 
    
    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None
        
class Elseif(BlockStatement):
    begin = Seq(Or('ELSIF', 'ELSEIF'), Optional(Parenthesis))
    end = Or(Else, EndIf,Seq('END', Optional('IF')), Return, 'IF') 

    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None

class EndIfWithSpace(Term):
    match = Seq('END', 'IF', Optional(';'))
                  
class Case(BlockStatement):
    begin = 'CASE'    
    end = Or(EndCase, 'END')

    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None                  
    
class ExceptionWhenThen(Statement):
    stopped_by_other_statement = True
    begin = Seq('EXCEPTION', 'WHEN')
    end = Or(Return, 'END', None)
    
    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None
        
    def on_end(self):
        def check_the_next_when_then (nodes):
            token = nodes.move_to('WHEN')
            if not token:
                return self.has_empty_catch
            
            token = nodes.move_to('THEN')
            try:
                token = nodes.look_next()
                if token not in( 'WHEN', 'NULL'):
                    self.has_empty_catch = False
                elif token == 'NULL':
                    try:
                        next(nodes)
                        next(nodes)
                        token = nodes.look_next()
                        if token:
                            self.has_empty_catch = False
                    except StopIteration:
                        self.has_empty_catch = True
                        return self.has_empty_catch
                else:
                    self.has_empty_catch = True
                    return self.has_empty_catch
                    
                self.has_empty_catch = check_the_next_when_then(nodes)
            except StopIteration:
                self.has_empty_catch = True
                return self.has_empty_catch
            
            return self.has_empty_catch
            
        self.has_empty_catch = False
        tokens = self.get_tokens()
        self.has_empty_catch = check_the_next_when_then(tokens)
                
        setattr(self, 'has_empty_catch', self.has_empty_catch)
            
class If(BlockStatement):
    begin = 'IF'
    end = Or(Elseif, Else, EndIf, EndIfWithSpace, Return)

    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None
                                
class Loop(BlockStatement):
    begin = Or('DO', 'LOOP', 'REPEAT')
    end = Or('END', EndWhile, EndRepeat, EndLoop)

    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None
           
class While(BlockStatement):
    begin = Or('WHILE')
    end = Or('END', EndWhile, EndLoop)

    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None
            
class Try(BlockStatement):
    begin = Seq(Not('END'), 'TRY')
    end = Seq('END', 'TRY')

    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None
            
class Catch(BlockStatement):
    begin = Seq(Not('END'), 'CATCH')
    end = EndCatch

    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None

class HandlerFor(Statement):
    begin = Seq('DECLARE', Or('CONTINUE', 'EXIT', 'UNDO'), 'HANDLER', 'FOR')
    end = Or(BlockStatement, ';')

    def __init__(self):
        Statement.__init__(self)   
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None
        
    def on_end(self):
        begin_detected = False
        self.has_empty_catch = False
        tokens = self.get_tokens()
        tokens.move_to('FOR')
        next(tokens)
        token = tokens.look_next()
        if not isinstance(token, BlockStatement):
            next(tokens)
            token = tokens.look_next()

        if isinstance(token, BlockStatement):            
            for node in token.get_children():   
                if node == 'BEGIN' and not begin_detected:
                    begin_detected = True
                    self.has_empty_catch = True
                elif node != 'END' and begin_detected:
                    self.has_empty_catch = False
                    break
                
        setattr(self, 'has_empty_catch', self.has_empty_catch)
    

class OnException(Statement):
    begin = Seq('ON', 'EXCEPTION')
    end = Seq('END', 'EXCEPTION')

    def __init__(self):
        Statement.__init__(self)  
        self.maxControlStatementsNestedLevels = None
        self.has_empty_catch = None
        
    def on_end(self):
        self.has_empty_catch = False
        tokens = self.get_tokens()
        tokens.move_to('EXCEPTION')
        next(tokens)
        token = tokens.look_next()
        if isinstance(token, Parenthesis):
            try:
                next(tokens)
                token = tokens.look_next()
            except:    
                self.has_empty_catch = True

        setattr(self, 'has_empty_catch', self.has_empty_catch)

# Oracle, DB2 : EXECUTE IMMEDIATE dynamic_string
# SQL Server EXEC(UTE) sp_executesql, EXEC(UTE)(dynamic_string)
# Sybase : EXEC(UTE) dynamic_string
# mySQL : EXECUTE dynamic_string, CALL execute_prepared_stmt (dynamic_string)
# mariaDB : EXEC SQL EXECUTE dynamic_string
# postreSQL : EXEC SQL EXECUTE IMMEDIATE dynamic_string, EXEC SQL FETCH cursor into ..., EXEC SQL EXECUTE dynamic_string into/using .. 
# db2 : EXECUTE dynamic_string
               
class ExecuteImmediate(Term):
    match = Seq('EXECUTE', 'IMMEDIATE')
    
    def on_end(self):
        setattr(self, 'count_dynamicSQL', 1)   

class ExecuteDynamicString0(Term):
    match = Seq(Or('EXECUTE', 'EXEC'), Or(Parenthesis, String))
    
    def on_end(self):
        setattr(self, 'count_dynamicSQL', 1)
            
class ExecuteDynamicString1(Term):
    match = Seq(Not(Or('PROCEDURE', 'END')), Or('EXECUTE', 'EXEC'), NotFollowedBy('ON'), Not(Or(Name, '[', 'AS', 'PROCEDURE', ';')))
    
    def on_end(self):
        setattr(self, 'count_dynamicSQL', 1)
        
class ExecuteDynamicString2(Term):
    match = Seq('EXEC', 'SQL', 'EXECUTE', Optional('IMMEDIATE'))
    
    def on_end(self):
        setattr(self, 'count_dynamicSQL', 1)
        
class ExecuteDynamicString3(Term):
    match = Seq('EXEC', 'SQL', 'FETCH')
    
    def on_end(self):
        setattr(self, 'count_dynamicSQL', 1)
        
class ExecuteDynamicString4(Term):
    match = Seq('EXECUTE', Or(Name, String), Optional('USING'), ';')
    
    def on_end(self):
        setattr(self, 'count_dynamicSQL', 1)
        
class ExecuteDynamicString5(Term):
    match = Seq(Optional('BEGIN'), Or('EXECUTE', 'EXEC', 'CALL'), Optional('dbo'),Optional('.'), Or('sp_executesql', 'execute_prepared_stmt'), Optional('@statement'), Optional('='), Optional('N'), Optional(String))
    
    def on_end(self):
        setattr(self, 'count_dynamicSQL', 1)
                
class ExecuteDynamicString6(Term):
    match= Seq('EXEC', 'SQL', Or('EXECUTE', 'INSERT', 'UPDATE', 'DELETE', 'SELECT'))
    
    def on_end(self):
        setattr(self, 'count_dynamicSQL', 1)

class ExecuteDynamicCursor(Statement):
    begin = Seq('OPEN', Any(), 'FOR', Or(Name, String, NotFollowedBy(Or(DeleteClause, InsertClause, UpdateClause, SelectList ))))
    end = ';'
    
    def on_end(self):
        setattr(self, 'count_dynamicSQL', 1)
               
class Cursor(Term):
    match = Seq('CURSOR', Or('IS', 'FOR'))

class Ctas(Term):
    match = Seq(Or('CREATE', 'DECLARE'), Optional(Or('LOCAL', 'GLOBAL')), Optional(Or('TEMPORARY', 'TEMP')), 'TABLE', 
                Or(Any(),
                    Seq(Any(), '.', Any()),
                    Seq(Any(), '.', Any()), '.', Any()
                         ), 
                'AS')
        
class Select(Statement):
    """ Finaly group select from where """
    stopped_by_other_statement = True
    begin = Or(Seq(Cursor, SelectList),
               Values,
               SelectList,
               Seq(Ctas, SelectList))
    # Error is the case of MSSQL
    end = Or(Union, UnionAll, SetCurrent, Except, Return, 'PRINT', Seq(';', NotFollowedBy(Error)))

    def __init__(self):
        Statement.__init__(self)

        self.columns = []
        # the from content
        self.fromClause = None
        self.table_references = []
        # the where
        self.where = None
        self.orderBy = None
        self.groupBy = None
        self.scope = None
        self.into = None
        self.isCursor = None
        self.isCtas = None
        self.missingParenthesis = None
        self.maxControlStatementsNestedLevels = None  
        self.distinct = None
        self.has_non_ansi_operator = None
        self.has_or_on_the_same_identifier = None
        self.has_empty_catch = None
        
    def get_columns(self):
        """
        Return the columns of the select. 
        
        :rtype: list of Columns
        """
        return self.columns
    
    def get_table_references(self):
        """
        Return the table references. 
        
        :rtype: list of TableReference
        """
        return self.table_references
    
    def get_additional_table_references(self):
        return []
    
    def get_where(self):
        """
        Return the where part. 
        
        :rtype: Where
        """
        return self.where

    def get_from(self):
        """
        Return the from part. 
        
        :rtype: From
        """
        return self.fromClause
    
        
    def get_orderBy(self):
        """
        Return the order by part. 
        
        :rtype: order by
        """
        return self.orderBy

    def get_groupBy(self):
        """
        Return the group by part. 
        
        :rtype: group by
        """
        return self.groupBy

    def get_into(self):
        """
        detect into 
        
        :rtype: into
        """
        return self.into

    def get_isCursor(self):
        """
        Detect the cursor
        
        :rtype: the SELECT is a Cursor
        """
        return self.isCursor

    def get_isCtas(self):
        """
        Detect the CTAS
        
        :rtype: the SELECT is a Create Tables As statement (CTAS)
        """
        return self.isCtas
                      
    def get_distinct(self):
        return self.distinct
                          
    def on_end(self):
        def look_for_distinct(nodes):    
            for t in nodes:
                if isinstance(t, Column):
                    for td in t.get_tokens():
                        if not isinstance(td, Distinct) and isinstance(td, Node):
                            td = look_for_distinct(td.get_children())
                        
                        if isinstance(td, Distinct):
                            return td
                elif not isinstance(t, Column) and isinstance(t, Node):
                    t = look_for_distinct(t.get_children())
                
                if isinstance(t, Distinct):
                    return t
        
            return

        for n in self.get_sub_nodes():
            if isinstance(n, SelectList):
                self.columns = list(n.get_sub_nodes())	 
                nodes = n.get_tokens()
                self.distinct = look_for_distinct(nodes)
            elif isinstance(n, From):
                self.fromClause = n
                self.table_references = list(n.get_sub_nodes())
                look_for_joined_column (self, n) 
                
            elif isinstance(n, Where):
                self.where = n
                nodes = n.get_tokens()
                # skip the where keyword
                next(nodes)
                look_for_filtered_columns(self, nodes)
                
            elif isinstance(n, OrderBy):
                self.orderBy = n
                nodes = n.get_tokens()
                # skip the order and by keywords
                next(nodes)
                next(nodes)
                look_for_ordered_grouped_columns(self, nodes)
                
            elif isinstance(n, GroupBy):
                self.groupBy = n
                nodes = n.get_tokens()
                # skip the group and by keywords
                next(nodes)
                next(nodes)
                look_for_ordered_grouped_columns(self, nodes)
                
            elif isinstance(n, Into):
                self.into = n
            elif isinstance(n, Cursor):
                self.isCursor = n
            elif isinstance(n, Ctas):
                self.isCtas = n
                                                                                               
class BooleanTerm(Statement, WithBooleanTerms):
    """
    An element in a condition. 
    
    for example : 
    - a.b = c.d
    - a.b+0 = c.d
    - a in (...)
    - a like '...'
    - ...
    """
    begin = Not(Select)
    end   = Or('AND', 'OR', 'BETWEEN')
        
    def __init__(self):
        Statement.__init__(self)
        self.operator = None
        self.left_operand = None
        self.right_operand = None
        self.operands = []
        self.or_detected = []
        self.left = []
        self.right = []
        self.right_text = ''
        self.left_text = ''
        self.begin_of_a_group_text = ''
        # identifiers inside function call
        self.function_call_identifiers= []
        
    def get_operator(self):
        """
        Returns : 
        - like, in, =, !=, ...  
        """
        if self.operator == 'not':
            children = self.get_children()
            children.move_to(self.operator)
            if next(children) == 'in': 
                self.operator = 'not in'
        return self.operator

    def get_left_identifier(self):
        """
        For a.c1 = b.c1 
        Returns a.c1 

        In other cases (function call, calculation) returns none

        @return:  Identifier
        """
        return self.left_operand

    def get_right_identifier(self):
        """
        For a.c1 = b.c1 
        Returns b.c1 
        
        In other cases returns none
        
        @return:  Identifier
        """
        return self.right_operand
       
    def get_all_identifiers(self):
        """
        In case of 
        - a.c1 = b.c1  : returns a.c1 , b.c1
        - f(a) ... : returns a, ...
        
        """
        result = []
        
        result.append(self.left_operand)
        result.append(self.right_operand)
        result += self.function_call_identifiers
        
        return result
        
    
    def on_end(self):
        
        tokens = self.get_children()
        try:
            # left part
            token = next(tokens)
            self.left = []
            prev_is_to_skip = False
            while not token in ['<', '>', '=', '!']:
                if token == ':':
                    prev_is_to_skip = True
                elif token.text in ['integer', 'text', 'INTEGER', 'TEXT'] and prev_is_to_skip:
                    prev_is_to_skip = False
                    break
                elif token in ['IS NULL', 'IS NOT NULL', 'BETWEEN', 'NOT EXISTS', 'NOT IN', 'NOT LIKE', '!=', '<>', '!>', '<!']:
                    self.operator = token.text             
                elif token in ['not']:
                    token2 = next(tokens)
                    if token2 == 'exists':
                        self.operator = '%s %s' % (token.text.lower(), token2.text.lower())
                        token = next(tokens)
                        break
                    self.operator = token.text
                    break
                elif token in ['LIKE', 'IN', 'EXISTS', 'BETWEEN']:
                    self.operator = token.text
                    break                   
                else:
                    self.left.append(token)
                    if isinstance(token, Parenthesis):
                        self.begin_of_a_group_text = "".join([self.begin_of_a_group_text, ':%s:%s' % (str(token.get_begin_line()), str(token.get_begin_column()))])
                    if token.text and token.type not in (String.Single, Number.Integer, Name.Builtin, Keyword, Error) and not isinstance(token, FunctionCall):
                        self.left_text = "".join([self.left_text, token.text.upper()])
                token = next(tokens)
            
            is_Parenthesis = None
            try:
                is_Parenthesis = isinstance(self.left[0], Parenthesis)
            except IndexError:
                pass
            if is_Parenthesis:
                result_indetifier = []
                for t in self.left[0].get_children():
                    if isinstance(t, BooleanTerm):
                        for tt in t.get_tokens():
                            if tt.type in [Name]:
                                result_indetifier.append(tt)
                        self.left_operand = Identifier(result_indetifier)
                        break
            elif self.left and not any(token in ['+', '-', '*', '/', 'EXISTS', 'BETWEEN'] for token in self.left):
                self.left_operand = parse_identifier(Lookahead(self.left), accept_keywords=True)
            
            # operator  
            if token.text:         
                self.operator = token.text.lower()
            token = tokens.look_next()
            if token.type == Operator:
                token = next(tokens)
                self.operator = "".join([self.operator, token.text])

            # right part
            #self.right = list(tokens)
            error_detected = False
            string_error_detected = False
            skip_next = None
            for t in tokens:
                # the case of CURRENT DATE
                if t.type == Name and t.text.lower() == 'date' and skip_next:
                    skip_next = None
                    continue
                                    
                if t.type == Keyword and t.text.lower() == 'current':
                    skip_next = True

                self.right.append(t)
                # MS SQL case when string are decoded as Error ... Error
                if error_detected and string_error_detected:
                    error_detected = False
                    string_error_detected = False
                    continue
                if error_detected:
                    string_error_detected = True
                    continue
                if t.type == Error and not error_detected:
                    error_detected = True
                    continue
                if t.text and t.text.upper() not in ('AND', 'OR') and t.type not in (String.Single, Number.Integer, Name.Builtin, Keyword) and not isinstance(token, FunctionCall):
                    self.right_text = "".join([self.right_text, t.text.upper()])
                elif (t.text and t.text.upper() == 'OR'):
                    self.or_detected.append(t)

            is_Parenthesis = None
            try:
                is_Parenthesis = isinstance(self.right[0], Parenthesis)
            except:
                print('issue with is_Parenthesis in BooleanTerm')
                pass
            if is_Parenthesis:
                result_indetifier = []
                for t in self.right[0].get_children():
                    if isinstance(t, BooleanTerm):
                        for tt in t.get_tokens():
                            if tt.type in [Name]:
                                result_indetifier.append(tt)
                        self.right_operand = Identifier(result_indetifier)
                        break           
            elif self.right and not any(token in ['+', '-', '*', '/', 'EXISTS'] for token in self.right):
                self.right_operand = parse_identifier(Lookahead(self.right), accept_keywords=True)
            
        except StopIteration:
            pass 
        
        for function_call in get_direct_sub_nodes(self, FunctionCall):
            for term in get_sub_nodes(function_call.get_children(), BooleanTerm):
                
                tokens = term.get_children()
                
                try:
                    while True:
                        
                        identifier = parse_identifier(tokens)

                        if not identifier.is_empty():
                            self.function_call_identifiers.append(identifier)
                        token = tokens.move_to(',')
                        if not token:
                            break
                except:
                    print('issue with function_call in BooleanTerm')
                    pass 
