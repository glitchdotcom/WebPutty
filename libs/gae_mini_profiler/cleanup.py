import StringIO

def cleanup(request, response):
    '''
    Convert request and response dicts to a human readable format where
    possible.
    '''
    request_short = None
    response_short = None
    miss = 0

    if "MemcacheGetRequest" in request:
        request = request["MemcacheGetRequest"]
        response = response["MemcacheGetResponse"]
        request_short = memcache_get(request)
        response_short, miss = memcache_get_response(response)
    elif "MemcacheSetRequest" in request:
        request_short = memcache_set(request["MemcacheSetRequest"])
    elif "Query" in request:
        request_short = datastore_query(request["Query"])
    elif "GetRequest" in request:
        request_short = datastore_get(request["GetRequest"])
    elif "PutRequest" in request:
        request_short = datastore_put(request["PutRequest"])
    # todo:
    # TaskQueueBulkAddRequest
    # BeginTransaction
    # Transaction

    return request_short, response_short, miss

def memcache_get_response(response):
    response_miss = 0
    items = response['item_']
    for i, item in enumerate(items):
        if type(item) == dict:
            item = item['MemcacheGetResponse_Item']['value_']
            item = truncate(repr(item))
            items[i] = item
    response_short = "\n".join(items)
    if not items:
        response_miss = 1
    return response_short, response_miss

def memcache_get(request):
    keys = request['key_']
    request_short = "\n".join([truncate(k) for k in keys])
    namespace = ''
    if 'name_space_' in request:
        namespace = request['name_space_']
        if len(keys) > 1:
            request_short += '\n'
        else:
            request_short += ' '
        request_short += '(ns:%s)' % truncate(namespace)
    return request_short

def memcache_set(request):
    keys = [truncate(i["MemcacheSetRequest_Item"]["key_"]) for i in request["item_"]]
    return "\n".join(keys)

def datastore_query(query):
    kind = query.get('kind_', 'UnknownKind')
    count = query.get('count_', '')

    filters_clean = datastore_query_filter(query)
    orders_clean = datastore_query_order(query)

    s = StringIO.StringIO()
    s.write("SELECT FROM %s\n" % kind)
    if filters_clean:
        s.write("WHERE\n")
        for name, op, value in filters_clean:
            s.write("%s %s %s\n" % (name, op, value))
    if orders_clean:
        s.write("ORDER BY\n")
        for prop, direction in orders_clean:
            s.write("%s %s\n" % (prop, direction))
    if count:
        s.write("LIMIT %s\n" % count)

    result = s.getvalue()
    s.close()
    return result

def datastore_query_filter(query):
    _Operator_NAMES = {
        0: "?",
        1: "<",
        2: "<=",
        3: ">",
        4: ">=",
        5: "=",
        6: "IN",
        7: "EXISTS",
    }
    filters = query.get('filter_', [])
    filters_clean = []
    for f in filters:
        if 'Query_Filter' not in f:
            continue
        f = f["Query_Filter"]
        op = _Operator_NAMES[int(f.get('op_', 0))]
        props = f["property_"]
        for p in props:
            p = p["Property"]
            name = p["name_"] if "name_" in p else "UnknownName"

            if 'value_' in p:

                propval = p['value_']['PropertyValue']

                if 'stringvalue_' in propval:
                    value = propval["stringvalue_"]
                elif 'referencevalue_' in propval:
                    ref = propval['referencevalue_']['PropertyValue_ReferenceValue']
                    els = ref['pathelement_']
                    paths = []
                    for el in els:
                        path = el['PropertyValue_ReferenceValuePathElement']
                        paths.append("%s(%s)" % (path['type_'], id_or_name(path)))
                    value = "->".join(paths)
                elif 'booleanvalue_' in propval:
                    value = propval["booleanvalue_"]
                elif 'uservalue_' in propval:
                    value = 'User(' + propval['uservalue_']['PropertyValue_UserValue']['email_'] + ')'
                elif '...' in propval:
                    value = '...'
                elif 'int64value_' in propval:
                    value = propval["int64value_"]
                else:
                    raise Exception(propval)
            else:
                value = ''
            filters_clean.append((name, op, value))
    return filters_clean

def datastore_query_order(query):
    orders = query.get('order_', [])
    _Direction_NAMES = {
        0: "?DIR",
        1: "ASC",
        2: "DESC",
    }
    orders_clean = []
    for order in orders:
        order = order['Query_Order']
        direction = _Direction_NAMES[int(order.get('direction_', 0))]
        prop = order.get('property_', 'UnknownProperty')
        orders_clean.append((prop, direction))
    return orders_clean

def id_or_name(path):
    if 'name_' in path:
        return path['name_']
    else:
        return path['id_']

def datastore_get(request):
    keys = request["key_"]
    if len(keys) > 1:
        keylist = cleanup_key(keys.pop(0))
        for key in keys:
            keylist += ", " + cleanup_key(key)
        return keylist
    elif keys:
        return cleanup_key(keys[0])

def cleanup_key(key):
    if 'Reference' not in key: 
        #sometimes key is passed in as '...'
        return key
    els = key['Reference']['path_']['Path']['element_']
    paths = []
    for el in els:
        path = el['Path_Element']
        paths.append("%s(%s)" % (path['type_'] if 'type_' in path 
                     else 'UnknownType', id_or_name(path)))
    return "->".join(paths)

def datastore_put(request):
    entities = request["entity_"]
    keys = []
    for entity in entities:
        keys.append(cleanup_key(entity["EntityProto"]["key_"]))
    return "\n".join(keys)

def truncate(value, limit=100):
    if len(value) > limit:
        return value[:limit - 3] + "..."
    else:
        return value
