import hacks

############################################################
# Usage of @hacks.before/after: wrapping a function/method #
############################################################

@hacks.friendly('mul')
def mul(a, b=2):
    return a * b
 
 
@hacks.before('mul')
def triplicate_instead(mul, a, b=2):
    return hacks.FakeResult(mul(a, 3))


def test_triplicate_instead():
    with hacks.use(triplicate_instead):
        assert mul(2) == 6
        assert mul(2, 7) == 6


@hacks.after('mul')
def also_quadruple(retval, a, b=2):
    return hacks.FakeResult(retval * 4)


def test_also_quadruple():
    with hacks.use(also_quadruple):
        assert mul(2) == 16
        assert mul(1, 1) == 4


class StupidProfiler:
    @hacks.before('mul')
    def pre(self, func, a, b=2):
        import time
        self._start = time.time()

    @hacks.after('mul')
    def post(self, func, a, b=2):
        import time
        self._stop = time.time()

    def diff(self):
        return self._stop - self._start


def test_stupid_profiler():
    profiler = StupidProfiler()
    with hacks.use(profiler):
        mul(2, 3)
    assert 0.000000001 < profiler.diff() < 0.1
