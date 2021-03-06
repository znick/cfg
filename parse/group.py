import re
import util

class Group(object):
    def __init__(self, data):
        self.name    = data.pop(0)
        self.childs  = set(data.pop(0) if type(data[0]) == list else [])
        self.pattern = (re.compile(data.pop(0))
            if len(data) and type(data[0]) == str else None)
        self.props   = data.pop(0) if len(data) else {}

    def __str__(self):
        return self.name

    def format(self):
        return '{0}: childs: {1}, pattern: {2}'.format(
            self.name, self.childs, self.pattern)

    def remove_childs(self, bad_childs):
        self.childs = self.childs - set(bad_childs)

    def get_matching(self, hosts):
        return filter(lambda host: any(map(lambda name:
            self.pattern.match(name), host.snames)), hosts) if self.pattern else []

class MergeError(Exception):
    def __init__(self, message=None):
        self.message = message
    def __str__(self):
        return self.message
    def __repr__(self):
        return self.__str__()

def merge_lists(src, dst):
    rv = list(dst)
    for prop in src:
        if not prop in dst:
            rv.append(prop)
    return rv

def merge(src, dst, depth):
    errors = []
    def check(name, prop, dst):
        stype, dtype = util.get_type(prop), util.get_type(dst.get(name))
        valid = name not in dst
        if not valid:
            if stype == None: valid = True
            else: valid = util.matches(stype, dtype)
        if not valid:
            errors.append(MergeError('property "%s" type mismatch: %s and %s' %
                (name, stype, dtype)))
        return valid

    def step(sprops, dprops):
        for name, prop in sprops.iteritems():
            if not check(name, prop, dprops):
                return
            if util.is_primitive(prop) or util.is_from_group(prop):
                value = util.get_value(prop)
                if name not in dprops:
                    dprops[name] = util.ValueFromGroup(value, src, depth)
                elif util.is_from_group(dprops[name]):
                    if util.get_depth(dprops[name]) == depth:
                        errors.append(MergeError(
                            ('value for "%s" is absent in "%s" but ' +
                             'came from two diffrent groups: "%s" and "%s", ' +
                             'can\'t merge') %
                            (name, dst, src, dprops[name].source)))
                    elif util.get_depth(dprops[name]) > depth:
                        dprops[name] = util.ValueFromGroup(value, src, depth)
            elif type(prop) == list:
                dprops[name] = (merge_lists(prop, dprops[name])
                    if name in dprops else prop)
            elif type(prop) == dict:
                dprops[name] = (step(prop, dprops[name])
                    if name in dprops else prop)
            else:
                errors.append(MergeError('unknown type of prop %s (%s), ' +
                                         'can\'t merge' % (name, type(prop))))
        return dprops

    step(src.props, dst.props)
    return errors

def expand_groups(groups, hosts):
    def fold_names(groups):
        rv = {}
        for group in groups:
            name = group.name
            if name in rv:
                errors.append(util.ValidationError('duplicate group name "%s"' % name))
            else:
                rv[name] = group
        return rv

    def check_cycles(group_names):
        def step(group, stack):
            bad_childs = []
            for child_name in group.childs:
                if child_name not in group_names:
                    errors.append(util.ValidationError('no such group "%s" in childs of "%s"' %
                        (child_name, group.name)))
                    bad_childs.append(child_name)
                else:
                    child = group_names[child_name]
                    if child in stack:
                        errors.append(util.ValidationError('group dependency cycle: %s' % (stack)))
                    else:
                        step(child, stack + [child])
            group.remove_childs(bad_childs)
        for group in groups:
            step(group, [])

    errors = []
    group_names = fold_names(groups)
    check_cycles(group_names)

    def no_parents(group): return len(group.parents) == 0

    for group in groups:
        group.hosts = []
        group.parents = set()
        group.ancestors = set()
    for group in groups:
        for child_name in group.childs:
            group_names[child_name].parents.add(group)

    queue = filter(no_parents, groups)
    while len(queue):
        group = queue[0]
        for child_name in group.childs:
            child = group_names[child_name]
            child.ancestors.add((group, 1))
            for ancestor, depth in group.ancestors:
                child.ancestors.add((ancestor, depth+1))
            child.parents.remove(group)
            if no_parents(child): queue.append(child)
        queue = queue[1:]

    for group in groups:
        for ancestor, depth in group.ancestors:
            errors.extend(merge(ancestor, group, depth))
        for host in group.get_matching(hosts):
            errors.extend(merge(group, host, 0))
            host.groups += group.ancestors
            host.groups.append((group, 0))

    for host in hosts:
        for group, depth in host.groups:
            group.hosts.append((host, depth))

    return errors
