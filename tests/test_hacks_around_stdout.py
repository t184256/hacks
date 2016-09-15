import sys
import io

import hacks


def test_stdout_monkeypatching():
    
    # Let's first patch stdout manually:
    real_stdout = sys.stdout
    fake_stdout = io.StringIO()
    sys.stdout = fake_stdout  # While it is monkey-patched, other users
    print('Hello')            # may write something else into out fake_stdout.
    sys.stdout = real_stdout

    assert fake_stdout.getvalue() == 'Hello\n'


    # Now let's patch stdout with hacks:
    sys.stdout = hacks.friendly('stdout')(sys.stdout)
    # Nothing bad should happen for now

    fake_stdout = io.StringIO()
    @hacks.around('stdout')
    def capture_stdout(real_stdout_ignored):
        return fake_stdout
    
    with hacks.use(capture_stdout):  # hacks-aided monkeypatching should not
        print('Hello')               # affect other users of stdout

    assert fake_stdout.getvalue() == 'Hello\n'


    # The other benefit is that hacks stack nicely
    @hacks.around('stdout')
    def zomg_ponies(stdout_to_modify):
        class Ponyfier:
            def write(self, text):
                ponified = ''.join('🐎' if not c.isspace() else c for c in text)
                stdout_to_modify.write(ponified)
        return Ponyfier()

    with hacks.use(capture_stdout):
        print('I')
        with hacks.use(zomg_ponies):  # A second hack stacks on top
            print('HATE')             # of the first one reasonably
        print('PONIES')

    assert fake_stdout.getvalue() == 'Hello\nI\n🐎🐎🐎🐎\nPONIES\n'
