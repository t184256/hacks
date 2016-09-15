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
