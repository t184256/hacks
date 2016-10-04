import hacks

import copy


@hacks.friendly_class('a', 'b')
class Speaker:
    def __init__(self, phrase):
        self._phrase = phrase
    def phrase(self):
        return self._phrase


@hacks.up('a')
def add_1(SpeakerClass):
    class ModdedClass(SpeakerClass):
        def phrase(self):
            return super().phrase() + '1'
    return ModdedClass


@hacks.up('b')
def add_2(SpeakerClass):
    original_phrase = SpeakerClass.phrase
    def phrase(self):
        return original_phrase(self) + '2'
    SpeakerClass.phrase = phrase
    return SpeakerClass


@hacks.around('c')
def add_3(speaker):
    speaker = copy.copy(speaker)
    speaker._phrase += '3'
    return speaker


@hacks.around('d')
def add_4(speaker):
    original_phrase = speaker.phrase
    print('W', original_phrase())
    speaker = copy.copy(speaker)
    def modded_phrase():
        return original_phrase() + '4'
    speaker.phrase = modded_phrase
    return speaker


def test_hacks_multinames():
    s = Speaker('GREAT')
    s = hacks.friendly('c', 'd')(s)
    assert s.phrase() == 'GREAT'
    with hacks.use(add_2, add_1):  # respects 'a', 'b' order
        assert s.phrase() == 'GREAT12'
    assert s.phrase() == 'GREAT'
    with hacks.use(add_4, add_3):  # respects 'c', 'd' order
        print( s.phrase() )
        assert s.phrase() == 'GREAT34'
    assert s.phrase() == 'GREAT'
