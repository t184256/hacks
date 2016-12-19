import hacks


##########################################################
# @hacks.stealing: stealing locals from hacks.call users #
##########################################################

def normal_function_123():
    for i in range(1, 4):
        j = 7 - i
        hacks.call.inner_cycle_123()  # i not passed to inner_cycle_123


# let the hacks begin

storage = []

@hacks.into('inner_cycle_123')
@hacks.stealing
def store(i:hacks.steal, j=hacks.steal):
    print(i, j)
    assert i + j == 7
    storage.append(i)

def test_store():
    with hacks.use(store):
        normal_function_123()
    assert storage == [1, 2, 3]

    store(4, 3)
    assert storage == [1, 2, 3, 4]


##################################################################
# @hacks.stealing: becoming intimately aware of hacks.call users #
##################################################################

def normal_function_a():
    hacks.call.context_aware()

def normal_function_b():
    some_var = 'x'
    hacks.call.context_aware(1, b=3)


call_log = []

@hacks.into('context_aware')
@hacks.stealing
def context_aware_hack(*args, frameinfo=hacks.steal_frameinfo, **kwargs):
    frame, filename, lineno, function, code_context, index = frameinfo
    some_var_present = 'some_var' in frame.f_locals
    call_log.append((function, args, kwargs, some_var_present))

def test_context_aware_hack():
    with hacks.use(context_aware_hack):
        normal_function_a()
        normal_function_b()
        hacks.call.context_aware('note that')

    assert call_log == [
        ('normal_function_a', (), {}, False),
        ('normal_function_b', (1,), {'b': 3}, True),
        ('test_context_aware_hack', ('note that',), {}, False),
    ]
