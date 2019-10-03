'''
Created on 28 nov. 2015

@author: MRO
'''
from pygments.token import Name, String, Keyword
from light_parser import Token

def extract_identifiers(node):
    """
    Extract all identifiers from a light_parser.Node. 
    """
    result = []
    
    tokens = node.get_children()
    try:
        while True:
            token = tokens.look_next()
            
            if not token:
                break
            
            if token.text in ( '[', '"', '`' ) or token.type == Name:
                result.append(parse_identifier(tokens))
            else:
                next(tokens)
    except StopIteration:
        pass
    return result


def parse_identifier(tokens, force_parse=False, accept_keywords=False):
    """
    Parse an identifier
    
    force_parse : when we have found nothing, accept it anyway
    accept_keywords : if we accept keywords
    
    x . b
    x
    `x`
    [x]
    "x"."b"
    #x
    
    returns Identifier
    """
    def not_an_usual_string_cases (tokens, prev_end_column):
        for token in tokens.get_children():
            try:
                blanks = ' ' * (token.begin_column - t.end_column) 
                t.text = "".join([t.text, blanks])
                t.text = "".join([t.text, token.text])
                t.end_column = token.end_column
            except AttributeError:
                if token.get_children() and not token.type:
                    prev_end_column = t.end_column
                    t.text, t.end_column = not_an_usual_string_cases (token, prev_end_column)             
       
        return t.text, t.end_column
                            
    result = []
    
    name_token_types = [Name]
    
    if accept_keywords:
        name_token_types.append(Keyword)

    try:
        while True:

            token = tokens.look_next()
            
            is_name = False
            
            if token.type in name_token_types:
                # take it as is
                token = next(tokens)
                is_name = True
                    
                result.append(token)
            
            elif token.type == String.Symbol:
                # create a fake token with skipped quotes
                token = next(tokens)
                t = Token(token.text[1:-1], Name)
                t.begin_line = token.begin_line
                t.begin_column = token.begin_column
                t.end_line = token.end_line
                t.end_column = token.end_column
                result.append(t)
                
            elif token in ['[', '`', '"']:
                if token == '`' : expected_delimiter = '`'
                if token == '"' : expected_delimiter = '"'
                if token == '[' : expected_delimiter = ']'
                token = next(tokens)
                
                t = Token('', Name)
                t.begin_line = token.begin_line
                t.begin_column = token.begin_column+1
                t.end_line = token.end_line
                t.end_column = token.end_column
                
                # eat up to the next ']' or '`'
                token = next(tokens)
                while token != expected_delimiter: 
                    try:
                        blanks = ' ' * (token.begin_column - t.end_column) 
                        t.text = "".join([t.text, blanks])
                        t.text = "".join([t.text, token.text])
                        t.end_column = token.end_column
                    except (AttributeError, TypeError):
                        if token.get_children() and not token.type:
                            prev_end_column = t.end_column
                            t.text, t.end_column = not_an_usual_string_cases (token, prev_end_column)

                    token = next(tokens)
                    
                result.append(t)
            lastCol = token.end_column
            token = tokens.look_next()           
            if is_name and token.type == Name and token.begin_column == 1 and token.text and not token.text[0] == '@' and lastCol==73:
                # Identifier splitted on 2 lines
                # happens on db2 zOS where lines are generally splitted the Mainframe way
                # e.g.
                #       CONSTRAINT VA_VIEW_ID PRIMARY KEY (VA_VIEW_ID,VA_AT_ID,VA_BO_NUMBE
                # R))                
                
                # we could be a little more strict and check that 
                # we have increased line (but begin_column == 1 seems sufficient)
                # previous end_column is 72
                
                # eat it
                token = next(tokens)
                # corrects name and position
                result[-1].text = "".join([result[-1].text, token.text])
                result[-1].end_line = token.end_line
                result[-1].end_column = token.end_column
                
                # look next 
                token = tokens.look_next()
                
            if not token == '.':
                break
            # eat the dot
            token = next(tokens)
            
    except (StopIteration, AttributeError):
        pass
    
    if not result and force_parse:
        # probably a keyword : take it anyway
        result.append(next(tokens))
    
    return Identifier(result)




class Identifier:
    """
    An identifier
    
    a.b.c
    """
    def __init__(self, tokens):
        self.tokens = tokens
        self.name = None
        self.parent_name = None
        if tokens:
            self.name = tokens[-1].text
            self.parent_name = ''
            for token in tokens[:-1]:
                if self.parent_name:
                    self.parent_name = "".join([self.parent_name, '.'])
                self.parent_name = "".join([self.parent_name, token.text])
        
        # resolved references
        self.reference = None

        # possible types of the identifier
        self.types = []
        
        # file containing the identifier
        self.file = None
    
    def is_empty(self):
        """
        True if is empty...
        """
        return not self.tokens
    
    def get_name(self):
        """
        In case of a.b returns b
        """
        return self.name

    def get_parent_name(self):
        """
        In case of a.b returns a
        """
        return self.parent_name

    def get_parent_identifier(self):
        """
        In case of a.b.c returns a.b as identifier
        """
        tokens = self.tokens[:-1]
        if tokens:
            return Identifier(tokens)
        else:
            return None
        

    def get_fullname(self, default_schema=None):
        
        parent_name = default_schema
        if self.parent_name:
            if self.parent_name.find('.dbo.') > 0:
                parent_name = 'dbo'
            elif self.parent_name.find('.DBO.') > 0:
                parent_name = 'DBO'
            else:
                parent_name = self.parent_name
        
            return '%s.%s' %(parent_name, self.name)
        
        return self.name
    
    def get_referenced(self):
        
        return self.reference
    
    def get_unique_reference(self):
        
        try:
            if self.reference and len(self.reference) == 1:
                return self.reference[0]
        except TypeError:
            pass
        
        return None
    
    def get_types(self):
        return self.types
    
    def __repr__(self):
        return 'Identifier(%s)' % str(self.tokens)

