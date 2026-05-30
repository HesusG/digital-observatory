from observatory.outputs.digest import pick_top_opportunities


def test_filters_below_threshold_and_sorts_desc():
    items = [
        {"title": "a", "score": 9},
        {"title": "b", "score": 4},
        {"title": "c", "score": 8},
        {"title": "d", "score": 10},
    ]
    out = pick_top_opportunities(items, n=2, min_score=8)
    assert [i["title"] for i in out] == ["d", "a"]


def test_respects_n():
    items = [{"title": str(i), "score": 9} for i in range(5)]
    assert len(pick_top_opportunities(items, n=3, min_score=8)) == 3
