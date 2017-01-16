import hacks

def test_hacks_enter_exit():
    log = []

    class Dependency:
        @staticmethod
        def __on_enter__(_):
            log.append('dep_enter')
        @staticmethod
        def __on_exit__(_):
            log.append('dep_exit')
        @staticmethod
        def use(x):
            log.append('used_' + x)

    @hacks.on_top_of(Dependency)
    class User:
        @staticmethod
        def __on_enter__(_):
            hacks.call.use('-')
            log.append('user_enter')
            hacks.call.use('on_enter')
        @staticmethod
        def __on_exit__(_):
            hacks.call.use('on_exit')
            log.append('user_exit')
            hacks.call.use('-')

    with hacks.use(User):
        log.append('|')
    assert log == ['dep_enter', 'user_enter', '|', 'user_exit', 'dep_exit']
    
    del log[:]
    with hacks.use(Dependency, User):
        log.append('|')
    assert log == ['dep_enter', 'user_enter', '|', 'user_exit', 'dep_exit']

    del log[:]
    with hacks.use(Dependency(), User):
        log.append('|')
    assert log == ['dep_enter', 'user_enter', '|', 'user_exit', 'dep_exit']

    del log[:]
    with hacks.use(Dependency, User, Dependency):
        log.append('|')
    assert log == ['dep_enter', 'user_enter', 'dep_enter',
                  '|',
                  'dep_exit', 'user_exit', 'dep_exit']
