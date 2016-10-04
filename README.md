hacks, a Python plugin library that doesn't play by the rules
=============================================================

In one sentence
---------------
`hacks` aims to be a plugin library bringing aspect-oriented approach 
to Python programs.


About
-----
What is `hacks` about? Oh, let me see...

`hacks` is about shooting a complete stranger's leg from around the corner.
Stealthily. Modularly. Painfully.

`hacks` is about patching objects that you're allowed to patch,
and then patching everything else.

`hacks` is about hooking into other code from afar.

`hacks` is about modifying and extending functions
without even having a reference to them.

`hacks` is about extending classes you'll never see
and existing instances of them that you'll never meet.
As you see fit. With null sweat. And that feeling of impending doom.

And `hacks` is about cleaning up all that mess with a single dedent.


Usage
-----
```python
import hacks

# Hacks is usable as a simple call dispatcher:


def main_code():
    N = 2
    for i in range(N):
        # call everyone hooked into 'explicit_call'
        hacks.call.explicit_call(i)
# ...


@hacks.into('explicit_call')  # knows nothing about main_code
def plugin1(i):
    print(i)


class Plugin2:

    @hacks.into('explicit_call')
    @hacks.stealing  # that's a pity that they forgot to expose N
    def method(self, i, N=hacks.steal):
        print(i, 'of', N)

# ...
with hacks.use(plugin1, Plugin2):
    main_code()  # prints '0', '0 of 2', '1', '1 of 2'
main_code()  # print nothing


# Hacks can be used to modify @hacks.friendly objects, e.g. wrap functions:

@hacks.friendly  # name not specified, pass 'greeter' to @hacks.around
def greeter():
    return 'Hello!'
# ...


@hacks.around('greeter')
def reverse(func):
    def func_reversed():
        return func()[::-1]
    return func_reversed


# ...
with hacks.use(reverse):  # reverses all 'printer's
    print(greeter())  # Prints '!olleH'
print(greeter())  # Prints 'Hello!'


# There is special support for extending classes and mutating existing
# instances to use the updated versions transparently:

@hacks.friendly_class  # name not specified, pass 'Clock' to @hacks.up
class Clock:
    def __init__(self, text):
        self._text = text
    def tick(self):
        return self._text


# ...
@hacks.up('Clock')
def tockify(clock_class):
    class TockingClock:
        def tick(self):
            return self._text + '-tock'
    return TockingClock

# ...
ticker = Clock('tick')
print(ticker.tick())  # prints 'tick'

with hacks.use(tockify):  # makes all 'clock's tock
    print(ticker.tick())  # prints 'tick-tock'
    # Yes, ticker has transparently changed its class to TockingClock.

print(ticker.tick())  # prints 'tick'
# And now it changed back to a plain old Clock!
```

There's more: initializers, deinitializers, modifying custom objects and
making non-cooperating objects cooperate.

But the most great feature is hacks.use, enabling and disabling hacks
gracefully without altering their behaviour outside that block or thread.
It can be nested, it can be overridden, it poisons the call stack
and it cleans up after itself at the end of the block. Ain't that nice?

Please see `tests` directory for more powerful usage examples.


Meh, extending code with `hacks` is too explicit!
-------------------------------------------------
Ah, the object of your interest is not decorated?
No problems, monkeypatch it with @hacks_friendly:
```python
sys.stdin = hacks_friendly(sys.stdin)
```
That alone should have near-zero visible effect.
Now change, wrap and extend it however you want with `hacks.use(...)`
without worrying about other threads or cleaning up after yourself.


Meh, extending code with `hacks` is too implicit!
-------------------------------------------------
When you decorate something with `@hacks.friendly`/`friendly_class`,
you kind of set it free from all contracts.
You never know what it will be on next access.
But hey, any decorator is a custom modification, what did you expect?

By the way, that burden of responsibility didn't simply vanish,
it just spread onto the person who `@hacks.up` and `around` your code.

If you're opposed to `stealing`, simply don't `steal`.


And how exactly is that a plugin system?
----------------------------------------
It's usable as one.

Write some code.
Decorate it with `@hacks.friendly` and `@hacks.friendly_class`
paired with nice names.
Add explicit calls to plugins with `hacks.call` where appropriate.

Think of a new aspect, like logging.
Write the logging code that `@hacks.into` explicit plugin calls.
Wrap around entire functions to add more logging.
Modify classes if you want to.

Then execute your code `with hacks.use(logging):`.
Enjoy your pluggable, replaceable, separated logging
without polluting the original code too much.

Write more powerful and game-changing modifications
without touching the main code.
Stack, nest and apply multiple hacks... um, plugins.
Define their 'scopes' flexibly.
Don't break original object's contracts without a good reason.

What else do you need from a plugin system?

Setuptools integration for plugins autodiscovery, right.
It is planned for future releases though. Pull requests are welcome!


So what is the plugin interface? Plugins need a rigid interface!
----------------------------------------------------------------
Not in Pythonland.

If you disagree with me, you must be an interesting and strange person
that should probably have a look at https://github.com/pytest-dev/pluggy


Choosing names requires forces you to design an interface!
----------------------------------------------------------
Really? How unbearable.
Just hook all hacks to `'x'`, my true anarchist.
Good luck differentiating the objects though!


Installation (approximate)
--------------------------
From pypi:

    pip3 install hacks

From Github:

    pip3 install git+https://github.com/t184256/hacks.git

From local source:

    pip3 install -r requirements.txt
    python3 setup.py install


More
----
`hacks` gave life and purpose to a
generic object proxying library called `mutants`.
Check it out: https://github.com/t184256/mutants


License
-------
`hacks` is distributed under the terms of the MIT License;
see [LICENSE.txt](LICENSE.txt).
