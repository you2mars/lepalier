import uuid

from commun.ids import uuid7


def test_uuid7__version_7_et_variante_rfc() -> None:
    u = uuid7()
    assert isinstance(u, uuid.UUID)
    assert u.version == 7
    assert u.variant == uuid.RFC_4122


def test_uuid7__strictement_croissant_dans_un_processus() -> None:
    ids = [uuid7() for _ in range(2000)]
    assert ids == sorted(ids)
    assert len(set(ids)) == len(ids)
