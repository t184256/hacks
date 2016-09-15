import hacks


######################################################
# Usage of @hacks.around: wrapping a function/method #
######################################################

@hacks.friendly('beep')
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

@hacks.around('name')
def change_name(person):
    import copy
    person = copy.copy(person)
    person.name = 'patched'
    return person

def test_hacks_around_object():
    michael = Person()
    michael.name = 'Michael'
    michael = hacks.friendly('name')(michael)
    assert michael.name == 'Michael'
    with hacks.use(change_name):
        assert michael.name == 'patched'
    assert michael.name == 'Michael'


################################################
# Usage of @hacks.around: modifying a function #
################################################

@hacks.friendly('func')
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
