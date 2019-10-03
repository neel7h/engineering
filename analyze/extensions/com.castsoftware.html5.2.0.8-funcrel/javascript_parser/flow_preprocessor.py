def preprocess(text):
    ret = text
    while '):' in ret:
        index = ret.find('):')
        indexPointVirg = ret.find(';', index)
        indexArrow = ret.find('=>', index)
        if indexArrow > 0 and indexArrow < indexPointVirg:
            ret = ret[:index + 1] + ' ' * ( indexArrow - index - 1 ) + ret[indexArrow:]
        else:
            break
    return ret