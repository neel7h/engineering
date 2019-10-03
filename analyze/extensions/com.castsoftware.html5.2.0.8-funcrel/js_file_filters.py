'''
Created on 26 nov. 2014

@author: iboillon
'''
import os
import json
import re
import cast.analysers
from cast.application import open_source_file # @UnresolvedImport
import traceback

class FileFilter:
    
    def __init__(self):
        
        jsonPath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'filters.json'))
        self.filters = json.loads(open_source_file(jsonPath).read())
        self.last_matches_result = None

    def get_last_result(self):
        return self.last_matches_result if self.last_matches_result else ''

    def matches(self, filename, css = False):
        
        self.last_matches_result = None
        fname = filename.replace(os.sep, '/')
        
        for _filter in [ _filter for _filter in self.filters if _filter['type'] == 'FilePath' ]:
            pattern = _filter['value'].upper()
            if css and pattern.endswith(".JS"):
                pattern = pattern[0:-3] + '.CSS'
            if self.match_string(pattern, fname.upper()):
                self.last_matches_result = 'filepath matches pattern ' + pattern
                return True

        if filename.endswith('.cshtml.html'):       # we skip .cshtml.html files because they are generated from .cshtml files
            cshtmlFilepath = filename[:-5]
            if os.path.isfile(cshtmlFilepath):
                self.last_matches_result = 'generated from .cshtml file'
                return True

        return False

    # matches a pattern token containing one or several stars with a string
    # A pattern token does not contain /.
    # Example: **/*toto*/** contains 3 pattern tokens: **, *toto* and **
    def matches_token_with_star(self, patternToken, fnameToken):
        
        vals = patternToken.split('*')
        valsFound = []
        oneValueNotFound = False
        l = len(vals)
        cmpt = 0
        for val in vals:
            if val:
                if cmpt == 0:
                    if not fnameToken.startswith(val):
                        valsFound.append(False)
                        oneValueNotFound = True
                    else:
                        valsFound.append(True)
                elif cmpt == l-1:
                    if not fnameToken.endswith(val):
                        valsFound.append(False)
                        oneValueNotFound = True
                    else:
                        valsFound.append(True)
                else:
                    if not val in fnameToken:
                        valsFound.append(False)
                        oneValueNotFound = True
                    else:
                        valsFound.append(True)
            else:
                valsFound.append(True)
            cmpt += 1
                            
        if not oneValueNotFound:
            # check that there are no / between matches
            i = 0
            ok = True
            while i < l-1:
                middle = fnameToken[len(vals[i]):len(fnameToken)-len(vals[i+1])]
                if '/' in middle:
                    ok = False
                i += 1
            if ok:
                return True
        return False


    # matches a pattern corresponding to a file path with a string
    # Example: **/*toto*/**
    def match_string(self, pattern, fname):

        patternTokens = pattern.split('/')
        fnameTokens = fname.split('/')
        cmptFname = len(fnameTokens) - 1

        doubleStarJustPassed = False
        for patternToken in reversed(patternTokens):
            if patternToken == '**':
                doubleStarJustPassed = True
                continue
            
            starPresent = False
            if '*' in patternToken:
                starPresent = True

            if doubleStarJustPassed:
                ok = False
                while cmptFname >= 0:
                    fnameToken = fnameTokens[cmptFname]
                    cmptFname -= 1
                    if not starPresent:
                        if fnameToken == patternToken:
                            ok = True
                            break
                    else:
                        if self.matches_token_with_star(patternToken, fnameToken):
                            ok = True
                            break
                                
                if not ok and cmptFname < 0:
                    return False
            else:
                fnameToken = fnameTokens[cmptFname]
                if not starPresent:
                    if not fnameToken == patternToken:
                        return False
                else:
                    if not self.matches_token_with_star(patternToken, fnameToken):
                        return False
                        
                cmptFname -= 1
                    
            doubleStarJustPassed = False
            
        if cmptFname >= 0 and patternTokens[0] != '**':
            return False
        
        return True

class JSFileFilter(FileFilter):
    
    def __init__(self):
        
        FileFilter.__init__(self)

    def match_file(self, filename, bUTF8):
        
        nbLongLines = 0
        maxLine = 0
        nLine = 0
            
        try:
            with open_source_file(filename) as f:            
                for line in f:
        
                    if nLine <= 15:
                        for _filter in [ _filter for _filter in self.filters if _filter['type'] == 'FileContent' ]:
                            try:
                                if re.search(_filter['value'], line):
                                    self.last_matches_result = 'pattern found in file : ' + _filter['value'] 
                                    return True
                            except:
                                cast.analysers.log.debug('Internal issue when filtering file: ' + str(filename) + ' line ' + str(nLine))
                                cast.analysers.log.debug(str(traceback.format_exc()))
                    nLine += 1
                        
                    l = len(line)
                    if l > 400:
                        nbLongLines += 1
                        if l > maxLine:
                            maxLine = l
        except:
            cast.analysers.log.debug('Internal issue when filtering file: ' + str(filename))
            cast.analysers.log.debug(str(traceback.format_exc()))

        # we check is the file can be a minified file
        if nLine == 0 or nbLongLines / nLine > 0.5 or (nbLongLines / nLine > 0.2 and maxLine > 10000):
            self.last_matches_result = 'minified file'
            return True
        return False

    def matches(self, filename):
        
        if FileFilter.matches(self, filename):
            return True

        try:
            return self.match_file(filename, True)
                
        except UnicodeDecodeError:

            return self.match_file(filename, False)
                
        return False

class CssFileFilter(FileFilter):
    
    def __init__(self):
        
        FileFilter.__init__(self)

    def match_file(self, filename, bUTF8):
        
        nLine = 0
        try:
            with open_source_file(filename) as f:            
                for line in f:
        
                    if nLine <= 15:
                        for _filter in [ _filter for _filter in self.filters if _filter['type'] == 'CssFileContent' ]:
                            try:
                                if re.search(_filter['value'], line):
                                    self.last_matches_result = 'pattern found in file : ' + _filter['value'] 
                                    return True
                            except:
                                pass
                    else:
                        break
        except:
            cast.analysers.log.debug('Internal issue when reading file: ' + str(filename))
            cast.analysers.log.debug(str(traceback.format_exc()))
                    
        return False

    def matches(self, filename):
        
        if FileFilter.matches(self, filename, True):
            return True

        try:
            return self.match_file(filename, True)
                
        except UnicodeDecodeError:

            return self.match_file(filename, False)
                
        return False

class HtmlFileFilter(FileFilter):
    
    def __init__(self):
        
        FileFilter.__init__(self)

    def match_file(self, filename, bUTF8):
        
        nLine = 0
        try:
            with open_source_file(filename) as f:
                for line in f:
        
                    if nLine <= 15:
                        for _filter in [ _filter for _filter in self.filters if _filter['type'] == 'HtmlFileContent' ]:
                            try:
                                if re.search(_filter['value'], line):
                                    self.last_matches_result = 'pattern found in file : ' + _filter['value'] 
                                    return True
                            except:
                                pass
                    else:
                        break
        except:
            cast.analysers.log.debug('Internal issue when reading file: ' + str(filename))
            cast.analysers.log.debug(str(traceback.format_exc()))

        return False

    def matches(self, filename):
        
        if FileFilter.matches(self, filename):
            return True

        try:
            return self.match_file(filename, True)
                
        except UnicodeDecodeError:

            return self.match_file(filename, False)
                
        return False
