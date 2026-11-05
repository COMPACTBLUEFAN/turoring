from hypothesis import given, strategies as st
from search import binary_search

@given(st.lists(st.integers()), st.integers())
def test_binary_search(items, target):
    items = sorted(items)
    result = binary_search(items, target)
    
    # а) если target есть в items:
    if target in items:
        assert 0 <= result < len(items)
        assert items[result] == target
    # б) если target нет в items:
    else:
        assert result == -1
