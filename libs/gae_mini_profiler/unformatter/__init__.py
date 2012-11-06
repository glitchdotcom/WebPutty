import sys

class UnformatStream(object):
    "Outputs tokens to a text stream"
    def __init__(self, out=sys.stdout, indent=u'  '):
        self.out = out
        self.indent = indent

    def emit_token(self, token, level=0):
        try:
            t = unicode(token)
        except UnicodeDecodeError:
            t = repr(token)

        self.out.write((self.indent * level) + t)
        self.out.write(u'\n')

class UnformatObject(object):
    "Saves the tokens as a json-like object"
    def __init__(self):
        self.value = None
        self.stack = []
        self.lastlevel = 0

    def get_last_parent(self):
        current = self.value
        for k in self.stack[:-1]:
            current = current[k]
            if type(current) == list:
                current = current[-1]
        return current

    def emit_token(self, token, level=0):
        if level == 0 and self.value is None:
            self.value = {token: None}
            self.stack.append(token)
            return

        if token != ']': # lists don't have keys on the stack
            for i in xrange(level, self.lastlevel):
                self.stack.pop()
        self.lastlevel = level

        if token in ['>', ']']:
            return

        key = self.stack[-1]
        parent = self.get_last_parent()
        val = parent[key]

        if token == '<':
            if val == None: # special case at beginning where {'Class':None}
                parent[key] = {}
            elif type(val) == list:
                actualval = val[-1] # use the last list element as the class
                val[-1] = {actualval: {}}
                self.stack.append(actualval)
            else: # it's a class name
                parent[key] = {val: {}}
                self.stack.append(val)
        else:
            if token == '[':
                token = []

            if val == None:
                val = token
            elif type(val) == list:
                val.append(token)
            elif type(val) == dict:
                val[token] = None
                self.stack.append(token)
            else:
                raise Exception('invalid token %s', token)
            parent[key] = val

def unformat(text):
    result = UnformatObject()
    unformat_value(text, out=result)
    return result.value

def unformat_value(text, i=0, level=0, delim=None, out=UnformatStream()):
    start = i
    if text == '':
        return i
    if text[i].isdigit():
        # number
        while text[i] not in [',', delim]:
            i += 1
        number = eval(text[start:i])
        out.emit_token(repr(number), level)
    elif text[i] in ["'", '"']:
        i = unformat_quoted(text, i, level, out=out)
    elif text[i] == '[':
        i = unformat_list(text, i, level, '[]', unformat_value, out=out)
    elif text[i] == '(':
        i = unformat_list(text, i, level, '()', unformat_value, out=out)
    else:
        i = unformat_class(text, i, level, delim, out=out)
    return i

def unformat_quoted(text, i, level, out=UnformatStream()):
    start = i
    delim = text[start]
    i += 1
    while text[i] != delim:
        if text[i] == '\\': # escaped
            i += 1
        i += 1
    i += 1 # go past end of quoted section

    try:
        quoted = eval(text[start:i])
    except ValueError:
        # this occurs when \x00lotsmorechars -> \x0...
        quoted = text[start:i]
    out.emit_token(quoted, level)
    return i

def unformat_class(text, i=0, level=0, delim=None, out=UnformatStream()):
    # name
    start = i
    while text[i] not in ['<', ',', delim]:
        i += 1
    class_name = text[start:i]
    out.emit_token(class_name, level)

    if text[i] == '<':
        i = unformat_list(text, i, level, '<>', unformat_attrval, out=out)
    return i

def unformat_attrval(text, i, level, delim, out=UnformatStream()):
    if text[i] == '.':
        out.emit_token('...', level)
        return i + 3

    # attr
    start = i
    while text[i] != '=':
        i += 1
    attr = text[start:i]
    out.emit_token(attr, level)

    i += 1 # unformat =

    # val
    i = unformat_value(text, i, level + 1, delim, out=out)
    return i

def unformat_list(text, i, level, delim, elfn, out=UnformatStream()):
    if len(delim) != 2:
        raise Exception
    out.emit_token(delim[0], level)
    i += 1 # unformat open bracket
    while text[i] != delim[1]:
        i = elfn(text, i, level + 1, delim[1], out=out)
        if text[i] == ',':
            i += 2
    i += 1 # unformat close bracket
    out.emit_token(delim[1], level)
    return i

def main():
    from io import StringIO
    from pprint import pprint

    f = open('examples.txt', 'r')
    for line in f:
        s = StringIO()
        unformat_value(line.strip(), out=UnformatStream(s))
        print(s.getvalue())
        s.close()

        result = UnformatObject()
        unformat_value(line.strip(), out=result)
        pprint(result.value)

        raw_input('cont?')
    f.close()

if __name__ == '__main__':
    main()
