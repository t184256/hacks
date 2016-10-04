import hacks


######################################################
# Usage of @hacks.around: wrapping a function/method #
######################################################

@hacks.friendly  # No name passed
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


##############################################
# Usage of @hacks.around: wrapping an object #
##############################################

class Person:
    pass

@hacks.around('Person')
def change_name(person):
    import copy
    person = copy.copy(person)
    person.name = 'patched'
    return person

def test_hacks_around_object():
    michael = Person()
    michael.name = 'Michael'
    michael = hacks.friendly(michael)  # No name passed
    assert michael.name == 'Michael'
    with hacks.use(change_name):
        assert michael.name == 'patched'
    assert michael.name == 'Michael'


################################################
# Usage of @hacks.around: modifying a function #
################################################

@hacks.friendly  # No name passed
def func():
    return 4


@hacks.around('func')
def stutter(func):
    return lambda: [func(), func()]


def test_hacks_around_function():
    assert func() == 4
    with hacks.use(stutter):
        assert func() == [4, 4]


###############################################
# Usage of @hacks.around: extending via class #
###############################################

class BrokenWatch:
    def tick(self):
        return 'tock'


@hacks.around('BrokenWatch')
def fix_watch(broken_watch_instance):
    class FixedWatch(broken_watch_instance.__class__):
        def tick(self):
            return 'tick'
    def apply_fix(broken_watch_instance):
        import copy
        fixed_watch_instance = copy.copy(broken_watch_instance)
        fixed_watch_instance.__class__ = FixedWatch
        return fixed_watch_instance
    return apply_fix(broken_watch_instance)
    # TODO: write a convenience function 'reclassify_as'
    #return hacks.reclassify(broken_watch_instance, FixedWatch)


def test_hack_around_extend_class():
    broken = BrokenWatch()
    broken = hacks.friendly(broken)  # Name not specified
    assert broken.tick() == 'tock'
    with hacks.use(fix_watch):
        assert broken.tick() == 'tick'
    assert broken.tick() == 'tock'
