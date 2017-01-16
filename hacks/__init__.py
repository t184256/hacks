# Copyright (c) 2016 Alexander Sosedkin <monk@unboiled.info>
# Distributed under the terms of the MIT License, see below:
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


import collections
import importlib
import inspect

import mutants


LOCALS_MARKER = '__used_hacks_registries__'


#####################################################
# hacks.use, registry and active registry detection #
#####################################################

def get_recent_plugins_registry():
    """Traverse the call stack, find most recent 'with hacks.use(...).'"""
    for frameinfo in inspect.stack() :
        if LOCALS_MARKER in frameinfo[0].f_locals:
            registries = frameinfo[0].f_locals[LOCALS_MARKER]
            if not registries:
                continue
            return registries[-1]


class _PluginRegistry:
    """A registry of plugins."""
    def __init__(self, hacks_iterable, package=None, _prev_hacks=None):
        self._prev_hacks_list = list(_prev_hacks) if _prev_hacks else []
        self._requested_hacks_list = list(hacks_iterable)
        self._new_hacks_list = []
        self._hacks_into = collections.defaultdict(list)
        self._hacks_around = collections.defaultdict(list)
        self._hacks_up = collections.defaultdict(list)
        self._package = package

        for hack in self._prev_hacks_list + self._requested_hacks_list:
            self._register(hack)

        self._hacks_list = self._prev_hacks_list + self._new_hacks_list

        self.call = _CallProxy(self)

    def _resolve(self, hack):
        if isinstance(hack, str):
            # Deal with 'my.great.module:deeply.buried.hack' format
            assert hack.count(':') == 1
            hack, further_name = hack.split(':', 1)
            hack = importlib.import_module(hack, package=self._package)
            for part in further_name.split('.'):
                hack = getattr(hack, part)
        return hack

    def _already_registered(self, hack):
        hack = self._resolve(hack)
        registered_hacks = self._prev_hacks_list + self._new_hacks_list

        if inspect.isclass(hack):
            return any(isinstance(reg, hack) for reg in registered_hacks)
        else:
            return any(reg is hack for reg in registered_hacks)

    def _register(self, hack, recursively=True):
        """Register a hack and remember its modifications."""
        hack = self._resolve(hack)

        if hasattr(hack, '__hacks_on_top_of__'):
            for h in hack.__hacks_on_top_of__:
                if not self._already_registered(h):
                    self._register(h)

        if hasattr(hack, '__hacks_into__'):
            for p in hack.__hacks_into__:
                self._hacks_into[p].append(hack)

        if hasattr(hack, '__hacks_around__'):
            for p in hack.__hacks_around__:
                self._hacks_around[p].append(hack)

        if hasattr(hack, '__hacks_up__'):
            for p in hack.__hacks_up__:
                self._hacks_up[p].append(hack)

        # if it was an instance or a class, register methods + inner classes
        if recursively:
            if inspect.isclass(hack):  # class; instantiate and register
                hack = hack()
            self._register_attributes(hack)

        if hack not in (self._prev_hacks_list + self._new_hacks_list):
            self._new_hacks_list.append(hack)

    def _register_attributes(self, hack):
        """Also register methods and methods of inner classes."""
        for attrname, attr in inspect.getmembers(hack, inspect.isroutine):
            if not attrname.startswith('__'):
                self._register(attr, recursively=False)
        for attrname, attr in inspect.getmembers(hack, inspect.isclass):
            if not attrname.startswith('__'):
                self._register(attr, recursively=True)

    def _call_by_name(self, callable_name, *a, **kwa):
        """Return a list of execution results for all applicable methods."""
        # Possibly a hot function, TODO: optimize

        # Rarely-used context stealing:
        frameinfo = inspect.stack()[2]  # 1 from here, 1 from _CallProxy's lambda

        callables = self._hacks_into[callable_name]
        return [self._call_with_extra_hacks(clb, frameinfo, *a, **kwa)
                for clb in callables]

    def _call_with_extra_hacks(self, clb, frameinfo, *a, **kwa):
        if hasattr(clb, '__hacks_stealer__'):
            sig = inspect.signature(clb)
            bound_args = sig.bind_partial(*a, **kwa)
            for param_name, param in sig.parameters.items():
                if param_name in bound_args.arguments:
                    continue  # provided by someone else
                try:
                    if (param.default is _Steal or
                        param.annotation is _Steal):
                        caller_locals = frameinfo[0].f_locals
                        kwa[param_name] = caller_locals[param_name]
                    elif (isinstance(param.default, _Steal) or
                          isinstance(param.annotation, _Steal)):
                        caller_locals = frameinfo[0].f_locals
                        kwa[param_name] = caller_locals[param.default._name]
                    elif (isinstance(param.default, _StealFrameInfo) or
                          isinstance(param.annotation, _StealFrameInfo)):
                        kwa[param_name] = frameinfo
                except KeyError as ke:
                    avail = ', '.join('\'' + k + '\'' for k in caller_locals.keys())
                    text = ke.args[0] + ' (available: ' + avail + ')'
                    raise NameError(text)
        return clb(*a, **kwa)

    def __enter__(self):
        """
        Store in call stack for lookup with get_recent_plugins_registry.
        Call __on_enter__ on hacks in forward order.
        """
        frameinfo = inspect.stack()[1]
        loc = frameinfo[0].f_locals
        if LOCALS_MARKER in loc:
            loc[LOCALS_MARKER].append(self)
        else:
            loc[LOCALS_MARKER] = [self]

        # Call __on_enter__ for hacks in forward order:
        for hack in self._new_hacks_list:
            if hasattr(hack, '__on_enter__'):
                hack.__on_enter__(frameinfo)

    def __exit__(self, type_, value, traceback):
        """
        Remove marker from the call stack.
        Call __on_exit__ on hacks in reverse order.
        """
        frameinfo = inspect.stack()[1]
        loc = frameinfo[0].f_locals
        assert LOCALS_MARKER in loc
        assert loc[LOCALS_MARKER][-1] == self
        loc[LOCALS_MARKER].pop()
        if not loc[LOCALS_MARKER]:
            del loc[LOCALS_MARKER]

        # Call __on_exit__ for hacks in reverse order:
        for hack in reversed(self._new_hacks_list):
            if hasattr(hack, '__on_exit__'):
                hack.__on_exit__(frameinfo)

    def _apply_hacks_around(self, clb, names_for_hacks_around):
        for name_for_hacks_around in names_for_hacks_around:
            for hack in self._hacks_around[name_for_hacks_around]:
                clb = hack(clb)
        return clb

    def _apply_hacks_up(self, cls, names_for_hacks_up):
        for name_for_hacks_up in names_for_hacks_up:
            for hack in self._hacks_up[name_for_hacks_up]:
                cls = hack(cls)
        return cls


def use(*a, only=False, package=None):
    prev_hacks = None
    if not only:
        prev_registry = get_recent_plugins_registry()
        if prev_registry:
            prev_hacks = prev_registry._hacks_list
    return _PluginRegistry(a, _prev_hacks=prev_hacks, package=package)


##############################
# @hacks.into and hacks.call #
##############################

def into(*plugging_point_names):
    """
    Decorate a function/method to be called at specific extension implementations.
    This callable should be later registered in a HacksRegistry.
    After that, hacks.call.one_of_the_passed_names() will call this callable.
    Works internally by setting __hacks_into__ attribute on a decorated callable.
    """
    def into_decorator(func):
        func.__hacks_into__ = plugging_point_names
        return func
    return into_decorator


class _CallProxy():
    """
    A class that proxies calls to hacks, allowing hacks.call.some_func().
    Proxies most calls to all plugging clients, returns all results.
    Automatically determines active hacks registry.
    """
    def __init__(self, registry=None):
        self._registry = registry

    def __getattr__(self, name):
        """Proxy a call to all implementation callables"""
        # Possibly a hot function, TODO: optimize
        registry = self._registry or get_recent_plugins_registry()
        if not registry:
            return lambda *a, **kwa: []
        return lambda *a, **kwa: registry._call_by_name(name, *a, **kwa)


call = _CallProxy()


def stealing(clb):
    """For use with hacks.into only for now. TODO: generalize"""
    clb.__hacks_stealer__ = None
    # the presence of the argument is important, the value is not
    return clb


class _Steal:
    def __init__(self, name=None):
        self._name = name
steal = _Steal


class _StealFrameInfo:
    pass
steal_frameinfo = _StealFrameInfo()


#####################################
# @hacks.friendly and @hacks.around #
#####################################

def around(*names_to_hack_around):
    """
    Decorate a function/method, so that it will wrap other objects later.
    This callable should be later registered in a HacksRegistry. After that,
    hacks.friendly(...)-decorated objects with matching names
    would be wrapped with hacks.around(...)-decorated functions on first call
    in new hacks registry context.
    Works internally by setting __hacks_around__ on the decorated callable.
    """
    def around_decorator(func):
        func.__hacks_around__ = names_to_hack_around
        return func
    return around_decorator


def _cached_effective_wrapped_object(cache, original_object,
                                     names_for_hacks_around):
    # Possibly a hot function, TODO: optimize
    registry = get_recent_plugins_registry()
    if not registry:
        return original_object
    if registry in cache.keys(): # Reuse an object pre-wrapped with hacks
        return cache[registry]
    else: # Wrap an object for use with current registry and cache it
        wrapped = registry._apply_hacks_around(original_object,
                                               names_for_hacks_around)
        cache[registry] = wrapped
        return wrapped


def friendly(*names_for_hacks_around):
    """
    Decorate an object to be altered with hacks
    (decorated with @hacks.around).

    Checks the active set of hacks on every usage.
    When it changes, the wrapped object reevaluates
    back from the original one on next access.
    This may result in discarding the modifications to object.

    If that's not what you want,
    and you'd better modify the underlying class behaviour,
    consider using @hacks.friendly_class and @hacks.up.
    """

    if names_for_hacks_around and len(names_for_hacks_around) == 1:
        arg = names_for_hacks_around[0]
        if not isinstance(arg, str):
            # Decorator applied without arguments
            # Use some deduced name, apply to passed object
            if hasattr(arg, '__qualname__'):
                name = arg.__qualname__
            elif hasattr(arg, '__name__'):
                name = arg.__name__
            elif hasattr(arg, '__class__'):
                if hasattr(arg.__class__, '__qualname__'):
                    name = arg.__class__.__qualname__
            else:
                raise RuntimeError('@hacks.friendly: specify name for ' +
                                   str(arg))
            return friendly(name)(arg)

    def friendly_decorator(original_object):
        cache = {}
        def rewrap_object():
            return _cached_effective_wrapped_object(cache, original_object,
                                                    names_for_hacks_around)
        return mutants.ImmutableMutant(rewrap_object)
    return friendly_decorator


###########################################################
# @hacks.before and @hacks.after wrappers of @hack.around #
###########################################################

def before(*names_to_hack_before):
    def before_decorator(func_to_call_before):

        # So '@hacks.before' is synonymous to:
        @around(*names_to_hack_before)
        def hacking_around(*ignored_self_and_original_func):
            original_func = ignored_self_and_original_func[-1]
            possibly_self = ignored_self_and_original_func[:-1]
            def before_aware_func(*a, **kwa):
                extended_args = possibly_self + (original_func,) + a  # Py<3.5
                fr = func_to_call_before(*extended_args, **kwa)
                if isinstance(fr, FakeResult):
                    return fr.result
                return original_func(*a, **kwa)
            return before_aware_func

        return hacking_around
    return before_decorator


def after(*names_to_hack_after):
    def after_decorator(func_to_call_after):

        # So '@hacks.after' is synonymous to:
        @around(*names_to_hack_after)
        def hacking_after(*ignored_self_and_original_func):
            original_func = ignored_self_and_original_func[-1]
            possibly_self = ignored_self_and_original_func[:-1]
            def after_aware_func(*a, **kwa):
                retval = original_func(*a, **kwa)
                extended_args = possibly_self + (retval,) + a  # Py<3.5
                fr = func_to_call_after(*extended_args, **kwa)
                if isinstance(fr, FakeResult):
                    return fr.result
                return retval
            return after_aware_func

        return hacking_after
    return after_decorator


class FakeResult:
    def __init__(self, result):
        self.result = result


#######################################
# @hacks.friendly_class and @hacks.up #
#######################################

def up(*names_to_hack_up):
    def up_decorator(func):
          func.__hacks_up__ = names_to_hack_up
          return func
    return up_decorator


def _cached_effective_wrapped_up_class(cache, original_cls, names_for_hacks_up):
    # Possibly a hot function, TODO: optimize
    registry = get_recent_plugins_registry()
    if not registry:
        return original_cls
    if registry in cache.keys(): # Reuse an class pre-wrapped with hack-ups
        return cache[registry]
    else: # Wrap an object for use with current registry and cache it
        wrapped = registry._apply_hacks_up(original_cls, names_for_hacks_up)
        cache[registry] = wrapped
        return wrapped


def friendly_class(*names_for_hacks_up):
    """
    Decorate an class, which should be modifiable with
    class modifiers (functions decorated with @hacks.up).

    Checks the active set of hacks on every usage.
    When it changes, the hacked class reevaluates
    back from the original one on next access.
    Then the objects get their __class__ reset.

    This kind of modification preserves their state.
    """
    if names_for_hacks_up and len(names_for_hacks_up) == 1:
        arg = names_for_hacks_up[0]
        if not isinstance(arg, str):
            # Decorator applied without arguments
            # Use class name, apply to class
            try:
                name = arg.__qualname__
            except AttributeError:
                raise RuntimeError('@hacks.friendly_class: ' +
                                   'cannot get class name for ' + str(arg))
            return friendly_class(name)(arg)

    def friendly_class_decorator(original_cls):
        cache = {}

        def reclassify(_):
            return _cached_effective_wrapped_up_class(cache, original_cls,
                                                      names_for_hacks_up)

        class MetaAutoreparenting(type):
            def __call__(cls, *args, **kwds):
                original_object = type.__call__(cls, *args, **kwds)
                return mutants.ClassHopperMutant(original_object, reclassify)

        class AutoReparenting(original_cls, metaclass=MetaAutoreparenting):
            pass

        return AutoReparenting

    return friendly_class_decorator


####################
# @hacks.on_top_of #
####################

def on_top_of(*names_to_hack_on_top_of):
    def on_top_of_decorator(func):
          func.__hacks_on_top_of__ = names_to_hack_on_top_of
          return func
    return on_top_of_decorator


# TODO: rewrite into a single class with exported @classmethods
