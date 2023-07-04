def test_metapool_implmentation_set(factory, amm_implementation_meta):

    assert factory.metapool_implementations(0) == amm_implementation_meta.address
