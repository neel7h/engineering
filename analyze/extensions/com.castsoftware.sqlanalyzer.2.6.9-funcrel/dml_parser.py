'''
Parsing switched to DDL common part on 2 feb. 2019
Kept only for Define and Spool cases

@author: DOP
'''
from select_parser import FunctionCall
from sqlscript_parser import parse, Define
from light_parser import Statement, Token, Seq, Parser,\
    Optional, Or, Any
from sqlscript_parser import define_values
from sqlscript_lexer import SqlLexer
from sqlparse.sql import Parenthesis
from cast.analysers import log
from pygments.token import Error, String
import pygments

def Convert_SpoolDefine(f):
    """
    Only Define and Spool should be parsed
    
    Define example:
    define SCH_HAB = 'HAB_TESTU';

    -- GATA CQPRD00286750 -- Transaction en ligne - Versement
    
    CREATE TABLE &SCH_HAB..ESPSOC_TYPE_DEMANDE
    (ID_TYPE_DEMANDE NUMBER(11) NOT NULL,
    LIBELLE VARCHAR2(255) NOT NULL,
    CATEGORIE VARCHAR2(100) NOT NULL);
    
    
    Spool example :
    set echo on
set timing on
set term off
spool /home/rs554c/samc2t/poststeps/countnotmatching.out


tart of Count ***********************"
select /*+ PARALLEL(acct,6) */ market, count(1) acct from  acct  group by market having market in ('001','006','007','010','014','022','024');

select /*+ PARALLEL(acct_address,6) */ market, count(1) acct_address from  acct_address group by market having market in ('001','006','007','010','014','022','024');

    """
    variables = []
                    
    class DML_Insert(Statement):
        stopped_by_other_statement = True
        begin = Seq(Optional(Error), 'INSERT')
        end   = Optional(';')
            
    class DML_Select(Statement):
        stopped_by_other_statement = True
        begin = Seq(Optional(Or(Error, Seq('"', '\n'))), Optional(Any()),  'SELECT')
        end   = Optional(';')

    class DML_Update(Statement):
        stopped_by_other_statement = True
        begin = Seq(Optional(Error), 'UPDATE')
        end   = Optional(';')

    class DML_Delete(Statement):
        stopped_by_other_statement = True
        begin = Seq(Optional(Error), 'DELETE')
        end   = Optional(';')

    class DML_Merge(Statement):
        stopped_by_other_statement = True
        begin = Seq(Optional(Error), 'MERGE')
        end   = Optional(';')
                    
    class DML_Define(Statement):
        stopped_by_other_statement = True
        begin = 'DEFINE'
        end   = ';'
                          
    parser = Parser(SqlLexer, 
                [Parenthesis], 
                [Define],
                [DML_Insert],
                [DML_Select, DML_Update, DML_Delete, DML_Merge, FunctionCall]
                )
    replaced_stream = []
    new_children = []
    variable_has_been_replaced = None
    
    sliced_text = [node for node in parse(f)]
    sliced_text_lower = str(sliced_text).lower()
    
    spool_detected = "'spool'" in sliced_text_lower
    define_detected = "'define'" in sliced_text_lower

    try:
        f.seek(0)
        initial_stream = parse(f)
    except Exception as initial_stream_cannot_be_generated:
        print('Initial stream cannot be generated (' , initial_stream_cannot_be_generated , ').' )
        log.warning('Initial stream cannot be generated (%s).' % initial_stream_cannot_be_generated)
            
    if define_detected:
        f.seek(0)
        tokens = parse(f)
        for node in parser.parse_stream(tokens):
            if isinstance(node, Define):
                replaced_stream.append(node)
                variables.append(define_values(node))
            elif isinstance(node, (DML_Select, DML_Update, DML_Delete, DML_Merge, DML_Insert, FunctionCall)):
                if '&' in node.get_children():
                    variable_next = False
                    variable_replaced = False
                    for child in node.get_children():
                        if child.text == '&':
                            variable_next = True
                        elif variable_next:
                            for variable in variables:
                                if variable[0] == child.text:
                                    new_children.append(Token(variable[1], pygments.token.Token.Name))
                                    replaced_stream.append(Token(variable[1], pygments.token.Token.Name))
                                    variable_has_been_replaced = True
                                    variable_next = False
                                    variable_replaced = True
                        elif variable_replaced and child.text == '.':
                            variable_replaced = False
                            continue
                        elif not variable_next and not variable_replaced:
                            new_children.append(child)
                            replaced_stream.append(child)
                 
                    if new_children:
                        tokens = new_children
                        replaced_stream.append(node)
                elif isinstance(node, (DML_Select, DML_Update, DML_Delete, DML_Merge, DML_Insert)):
                    variable_has_been_replaced = True
                    for child in node.get_children():
                        replaced_stream.append(child)
            elif variable_has_been_replaced and node.type != Error :
                variable_has_been_replaced = True
                replaced_stream.append(node)

    if spool_detected:
        variable_has_been_replaced = True
        f.seek(0)
        tokens = parse(f)
        sliced_text = [node for node in tokens]
        for node in sliced_text:
            if node.type == String.Symbol:
                try:
                    detected_string_symbol = parse(node.text[1:-2])
                    sliced_string_symbol = [node for node in detected_string_symbol]
                except Exception as string_symbol_cannot_be_resolved:
                    print('String detected in spool cannot be resolved (', string_symbol_cannot_be_resolved, ').')
                    log.debug('String detected in spool cannot be resolved (%s).' % string_symbol_cannot_be_resolved)
                
                begin_line = node.begin_line
                
                for detail_string in sliced_string_symbol:
                    if detail_string == '\n' and begin_line == node.begin_line:
                        continue
                    else:
                        try:
                            detail = Token()
                            detail = detail_string
                            detail.begin_line = begin_line + detail_string.begin_line - 1
                            detail.end_line = begin_line + detail_string.end_line - 1
                            detail.begin_column = detail_string.begin_column
                            detail.end_column = detail_string.end_column
                            replaced_stream.append(detail)
                        except Exception as token_cannot_be_added:
                            print('Token cannot be added (', token_cannot_be_added, ').')
                            log.debug('Token cannot be added (%s).' % token_cannot_be_added)
            else:
                replaced_stream.append(node)
        
    return variable_has_been_replaced, replaced_stream, initial_stream