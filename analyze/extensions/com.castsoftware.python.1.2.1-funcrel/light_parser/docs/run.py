'''
Created on 23 mai 2016

@author: MRO
'''
from sphinx.application import Sphinx

app = Sphinx(srcdir='source', confdir='source', outdir='output', doctreedir='.doc_doctrees', buildername=None,  freshenv=True)
app.build()
