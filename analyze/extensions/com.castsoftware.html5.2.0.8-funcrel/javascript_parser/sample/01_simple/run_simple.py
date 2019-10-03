'''
Created on 29 july 2015

@author: iboillon
'''
from cast.analysers import File
from javascript_parser import analyse, AnalyzerConfiguration

class LocalFile(File):
    
    def __init__(self, path):
        self.path = path
        
    def get_path(self):
        return self.path
    
text = """
fa = function( param) {
}
c = fa('hi');

ov = {
    'param1' : 0,
    fb : function() {}
};

var slCtl = null;
function f() {
   slCtl = sender.getHost();
}
""" 

file = LocalFile('c:\\mydir\\myFile.js')
jsContent = analyse(text, file, AnalyzerConfiguration())
  
jsContent.print()

# jsContent.create_cast_objects(file)
# jsContent.create_cast_links(file)
