import hacks

def test_hacks_enter_exit():
    log = []

    class Hack1:
        @staticmethod
        def __on_enter__(_):
            log.append('Enter1')
        @staticmethod
        def __on_exit__(_):
            log.append('Exit1')

    class Hack2:
        def __on_enter__(self, frameinfo):
            frameinfo[0].f_locals['log'] += ['Enter2']
        def __on_exit__(self, frameinfo):
            frameinfo[0].f_locals['log'] += ['Exit2']

    @hacks.into('action')
    @hacks.stealing
    def act(log=hacks.steal):
        log.append('Action')

    hack1, hack2 = Hack1(), Hack2()
    with hacks.use(hack1, hack2, act):
        hacks.call.action()

    assert log == ['Enter1', 'Enter2', 'Action', 'Exit2', 'Exit1']

    with hacks.use(act, hack1):
        with hacks.use(hack2):
            hacks.call.action()

    assert log == ['Enter1', 'Enter2', 'Action', 'Exit2', 'Exit1'] * 2
