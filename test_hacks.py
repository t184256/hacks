import hacks


################################################################
# Usage of @hacks.into with explicit passing of hacks registry #
################################################################

def one_two_explicit(hacks, l):  # shadows the 'hacks' module
    for i in range(1, 3):
        l.append(i)
        hacks.call.append_more(l)
        # uses 'call' from explicitly passed hacks,
        # calls ones that are decorated with @hacks.into('append_more')


@hacks.into('append_more')
def append_tick(l):
    l.append('tick')


def test_hacks_into_explicit():
    l = []
    explicitly_passed_hacks = hacks.use(append_tick)
    one_two_explicit(explicitly_passed_hacks, l)
    assert l == [1, 'tick', 2, 'tick']


#########################################################################
# Usage of @hacks.into with implicit caller-inference of hacks registry #
#########################################################################

def one_two(l):  # NOTE: no hacks argument passed, inferred from caller
    for i in range(1, 3):
        l.append(i)
        hacks.call.append_more(l)
        # uses call from hacks module, which obtains the hack registry
        # from the call stack (nearest 'with hacks.use(...):')


@hacks.into('append_more')
def append_tock(l):
    l.append('tock')


def test_hacks_into_implicit():
    l = []
    with hacks.use(append_tock):
        one_two(l)
    assert l == [1, 'tock', 2, 'tock']


######################################################################
# Usage of @hacks.into: returning values from hacks, nested with-use #
######################################################################

def hack_names():
    return hacks.call.get_name()  # returns a list of results

@hacks.into('get_name')
def alice():
    return 'Alice'

class Bob:
    name = 'Bob'

    @hacks.into('get_name')
    def get_name(self):
        return self.name


def test_hack_into_collect_values():
    assert hack_names() == []
    with hacks.use(alice):
        assert hack_names() == ['Alice']
        with hacks.use(Bob(), only=True):  # use Bob (only)
            assert hack_names() == ['Bob']
        assert hack_names() == ['Alice']
        with hacks.use(Bob):  # use Bob (too), auto-instantiate
            assert hack_names() == ['Alice', 'Bob']
        assert hack_names() == ['Alice']
        assert use_hack_names_from_other_function() == ['Alice']
    assert hack_names() == []

def use_hack_names_from_other_function():
    return hack_names()


################################################
# Usage of @hacks.around: modifying a function #
################################################

@hacks.friendly_callable('func')
def func():
    return 4


@hacks.around('func')
def stutter(func):
    return lambda: [func(), func()]


def test_hacks_around_function():
    assert func() == 4
    with hacks.use(stutter):
        assert func() == [4, 4]
    assert func() == 4


#########################################
# Usage of @hacks.up: modifying a class #
#########################################

@hacks.friendly_class('Duck')
class Duck:
    def quack(self):
        return 'quack'


@hacks.up('Duck')
def woofing_duck(DuckToPatch):
    class WoofingDuck(DuckToPatch):
        def quack(self):
            return 'woof'
    return WoofingDuck


@hacks.up('Duck')
def stuttering_duck(DuckToPatch):
    class StutteringDuck(DuckToPatch):
        real_quack = DuckToPatch.quack
        def quack(self):
            return self.real_quack()[:2] + '-' + self.real_quack()
    return StutteringDuck


def test_hacks_up_class():
    duck = Duck()  # TODO: use it!
    print('1', Duck, duck, duck.quack, duck.quack())
    print('1', Duck.__class__)
    assert duck.quack() == 'quack'
    with hacks.use(woofing_duck):
        print('2', Duck, duck, duck.quack, duck.quack())
        assert duck.quack() == 'woof'
        with hacks.use(stuttering_duck):
            print('3', Duck, duck, duck.quack, duck.quack())
            assert duck.quack() == 'wo-woof'
    assert Duck().quack() == 'quack'
    with hacks.use(stuttering_duck):
        print('4', Duck, duck, duck.quack())
        assert Duck().quack() == 'qu-quack'
        with hacks.use(woofing_duck):
            print('3', Duck().quack())
            assert Duck().quack() == 'woof'
    print('4', Duck().quack())
    assert Duck().quack() == 'quack'


######################################################
# Usage of @hacks.around: wrapping a function/method #
######################################################

@hacks.friendly_callable('beep')
def beep():
    return 'BEEP'
 
 
@hacks.around('beep')
def hush(beep_func):
    def hushed_beep_func():
        return '<hush>' + beep_func().lower() + '</hush>'
    return hushed_beep_func
 
 
def test_hacks_around():
    assert beep() == 'BEEP'
    with hacks.use(hush):
        assert beep() == '<hush>beep</hush>'
    assert beep() == 'BEEP'


############################################################
# Usage of @hacks.before/after: wrapping a function/method #
############################################################

# TODO


########################################
# Usage of @hacks.up extending a class #
########################################

@hacks.friendly_class('Multiplier')
class Multiplier:
    def __init__(self, value):
        self._value = value
    def m(self, a):
        return self._value * a

@hacks.up('Multiplier')
def hack_multiplier(MultiplierToPatch):
    class HackedMultiplier(MultiplierToPatch):
        def m(self, a):
            return self.fmt(super().m(a))
        def fmt(self, x):
            return '<' * self._value + str(x) + '>' * self._value
    return HackedMultiplier

def test_hacks_up():
    a = Multiplier(2)
    assert a.m(4) == 8

    with hacks.use(hack_multiplier):
        assert a.m(4) == '<<8>>'


##############################################
# Usage of @hacks.around: wrapping an object #
##############################################

class Person:
    pass

@hacks.around('name')
def change_name(person):
    import copy
    person = copy.copy(person)
    person.name = 'patched'
    return person

def test_hacks_around_object():
    michael = Person()
    michael.name = 'Michael'
    michael = hacks.friendly_callable('name')(michael)
    assert michael.name == 'Michael'
    with hacks.use(change_name):
        assert michael.name == 'patched'
    assert michael.name == 'Michael'
