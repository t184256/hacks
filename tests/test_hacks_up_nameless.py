import hacks


#########################################
# Usage of @hacks.up: modifying a class #
#########################################

@hacks.friendly_class  # Name not specified
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
    duck = Duck()
    assert duck.quack() == 'quack'
    with hacks.use(woofing_duck):
        assert duck.quack() == 'woof'
        with hacks.use(stuttering_duck):
            assert duck.quack() == 'wo-woof'
    assert duck.quack() == 'quack'
    with hacks.use(stuttering_duck):
        assert duck.quack() == 'qu-quack'
        with hacks.use(woofing_duck):
            assert duck.quack() == 'woof'
    assert duck.quack() == 'quack'


########################################
# Usage of @hacks.up extending a class #
########################################

@hacks.friendly_class  # Name not specified
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
