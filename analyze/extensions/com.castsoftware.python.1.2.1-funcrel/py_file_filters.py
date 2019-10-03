'''
Created on 26 nov. 2014

@author: iboillon
'''
import os
import json
from cast.analysers import log
import cast_upgrade_1_5_23 #@UnusedImport
from cast.application import open_source_file # @UnresolvedImport


class FileFilter:
    
    def __init__(self):
        
        jsonPath = os.path.abspath(os.path.join(os.path.dirname(__file__), 'filters.json'))
        self.filters = json.loads(open(jsonPath).read())
    
    
    def matches(self, filename):
        
        fname = filename.replace(os.sep, '/')
        for filter_ in [filter_ for filter_ in self.filters if filter_['type'] == 'FilePath']:
            pattern = filter_['value'].upper()
            if self.match_string(pattern, fname.upper()):
                return True
        
        filters = [filter_ for filter_ in self.filters if filter_['type'] == 'FileContent']
        
        with open_source_file(filename) as f:
            nLine = 0
            
            for filter_ in filters:
                if 'minCount' in filter_:
                    filter_['nCount'] = 0
            try:
                for line in f:
                    for filter_ in filters:
                        try:
                            maxLines = int(filter_['maxLines'])
                            if nLine > maxLines:
                                continue
                        except KeyError:
                            pass
                        
                        if filter_['value'] in line:
                            try:
                                minCount = int(filter_['minCount'])
                                filter_['nCount'] += 1
                                nCount = filter_['nCount']
                                if nCount < minCount:
                                    continue
                            except KeyError:
                                pass
                            
                            return True
                        
                        nLine += 1
            
            except UnicodeDecodeError:
                pass
        
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
