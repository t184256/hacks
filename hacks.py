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
import inspect

import wrapt


LOCALS_MARKER = '__used_hacks_registries__'


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
    def __init__(self, hacks_iterable):
        self._hacks_list = list(hacks_iterable)
        self._hacks_into = collections.defaultdict(list)
        self._hacks_around = collections.defaultdict(list)
        self._hacks_up = collections.defaultdict(list)
        for hack in hacks_iterable:
            self._register(hack)

        self.call = _CallProxy(self)

    def _register(self, hack, recursively=True):
        """Register a hack and remember its modifications."""
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

    def _register_attributes(self, hack):
        """Also register methods and methods of inner classes."""
        for attrname, attr in inspect.getmembers(hack, inspect.isroutine):
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
                    if param.default is _Steal:
                        caller_locals = frameinfo[0].f_locals
                        kwa[param_name] = caller_locals[param_name]
                    elif isinstance(param.default, _Steal):
                        kwa[param_name] = caller_locals[param.default._name]
                    elif isinstance(param.default, _StealFrameInfo):
                        kwa[param_name] = frameinfo
                except KeyError as ke:
                    avail = ', '.join('\'' + k + '\'' for k in caller_locals.keys())
                    text = ke.args[0] + ' (available: ' + avail + ')'
                    raise NameError(text)
        return clb(*a, **kwa)

    def __enter__(self):
        """Store in call stack for lookup with get_recent_plugins_registry."""
        frameinfo = inspect.stack()[1]
        loc = frameinfo[0].f_locals
        if LOCALS_MARKER in loc:
            loc[LOCALS_MARKER].append(self)
        else:
            loc[LOCALS_MARKER] = [self]

    def __exit__(self, type_, value, traceback):
        """Remove marker from the call stack."""
        frameinfo = inspect.stack()[1]
        loc = frameinfo[0].f_locals
        assert LOCALS_MARKER in loc
        assert loc[LOCALS_MARKER][-1] == self
        loc[LOCALS_MARKER].pop()
        if not loc[LOCALS_MARKER]:
            del loc[LOCALS_MARKER]

    def _apply_hacks_around(self, clb, name_for_hacks_around):
        for hack in self._hacks_around[name_for_hacks_around]:
            clb = hack(clb)
        return clb

    def _apply_hacks_up(self, cls, name_for_hacks_up):
        for hack in self._hacks_up[name_for_hacks_up]:
            cls = hack(cls)
        return cls


def use(*a, only=False):
    prev_registry = get_recent_plugins_registry()
    prev_hacks = prev_registry._hacks_list if prev_registry is not None else []
    hacks_tuple = a if only else tuple(prev_hacks) + a
    return _PluginRegistry(hacks_tuple)


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
        name_for_hacks_around):
    # Possibly a hot function, TODO: optimize
    registry = get_recent_plugins_registry()
    if not registry:
        return original_object
    if registry in cache.keys(): # Reuse an object pre-wrapped with hacks
        return cache[registry]
    else: # Wrap an object for use with current registry and cache it
        wrapped = registry._apply_hacks_around(original_object,
                                               name_for_hacks_around)
        cache[registry] = wrapped
        return wrapped


def friendly(name_for_hacks_around):
    """
    Decorate an object to be altered with hacks
    (decorated with @hacks.around).
    Works internally by using a proxy object.

    Does it best to update the current set of hacks on every usage,
    but probably isn't very good at it
    (now it only covers calls and field access).
    Every re-covering reevaluates the wrapped object back from
    the original one.
    """
    def friendly_decorator(original_object):
        cache = {}

        class HacksProxy(wrapt.CallableObjectProxy):
            def __call__(self, *a, **kwa):
                self.__wrapped__ = _cached_effective_wrapped_object(
                    cache, original_object, name_for_hacks_around
                )
                return super().__call__(*a, **kwa)

            def __getattribute__(self, name):
                self.__wrapped__ = w = _cached_effective_wrapped_object(
                    cache, original_object, name_for_hacks_around
                )
                if name in ('__wrapped__', '__call__'):
                    return object.__getattribute__(self, name)
                return w.__getattr__(name)

        return HacksProxy(original_object)

    return friendly_decorator


#######################################
# @hacks.friendly_class and @hacks.up #
#######################################

def up(*names_to_hack_up):
    def up_decorator(func):
          func.__hacks_up__ = names_to_hack_up
          return func
    return up_decorator


def _cached_effective_wrapped_up_class(cache, original_cls, name_for_hacks_up):
    # Possibly a hot function, TODO: optimize
    registry = get_recent_plugins_registry()
    if not registry:
        return original_cls
    if registry in cache.keys(): # Reuse an class pre-wrapped with hack-ups
        return cache[registry]
    else: # Wrap an object for use with current registry and cache it
        wrapped = registry._apply_hacks_up(original_cls, name_for_hacks_up)
        cache[registry] = wrapped
        return wrapped

def friendly_class(name_for_hacks_up):
    def friendly_class_decorator(original_cls):
        cache = {}

        class MetaAutoreparenting(type):
            def __call__(cls, *args, **kwds):
                new_obj = type.__call__(cls, *args, **kwds)
                return AutoReparenting(new_obj)

        class AutoReparenting(wrapt.CallableObjectProxy):
            def __call__(self, *a, **kwa):
                self.__wrapped__.__class__ = _cached_effective_wrapped_up_class(
                    cache, original_cls, name_for_hacks_up
                )
                return super().__call__(*a, **kwa)

            def __getattribute__(self, name):
                w = wrapt.CallableObjectProxy.__getattribute__(self,
                                                               '__wrapped__')
                w.__class__  =  _cached_effective_wrapped_up_class(
                    cache, original_cls, name_for_hacks_up
                )
                if name in ('__wrapped__', '__call__'):
                    return object.__getattribute__(self, name)
                return w.__getattribute__(name)

        class Autoreparenting(original_cls, metaclass=MetaAutoreparenting):
            pass

        return Autoreparenting

    return friendly_class_decorator


# TODO: variable stealing
# TODO: rewrite into a single class with exported @classmethods
# TODO: .before and .after callable convenience decorators
# TODO: most versatile .friendly decorator for patching generic objects
