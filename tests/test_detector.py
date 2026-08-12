from __future__ import annotations

from polyglotguard.detector import compare_section_trees
from polyglotguard.markdown import parse_markdown


def rendered_changes(baseline: str, current: str) -> list[tuple[str, str]]:
    return [
        (change.kind.value, change.path.display())
        for change in compare_section_trees(parse_markdown(baseline), parse_markdown(current))
    ]


def test_added_modified_deleted_are_grouped_in_document_order() -> None:
    baseline = """# Keep
old
# Delete first
gone
# Delete second
gone
"""
    current = """# Added first
new
# Keep
changed
# Added second
new
"""
    assert rendered_changes(baseline, current) == [
        ("added", '"Added first"'),
        ("added", '"Added second"'),
        ("modified", '"Keep"'),
        ("deleted", '"Delete first"'),
        ("deleted", '"Delete second"'),
    ]


def test_child_change_does_not_modify_parent() -> None:
    baseline = "# Parent\nparent\n## Child\nold\n"
    current = "# Parent\nparent\n## Child\nnew\n"
    assert rendered_changes(baseline, current) == [("modified", '"Parent" > "Child"')]


def test_rename_and_move_are_deleted_plus_added() -> None:
    baseline = "# One\n## Child\nbody\n# Rename me\nbody\n"
    current = "# Two\n## Child\nbody\n# Renamed\nbody\n"
    assert rendered_changes(baseline, current) == [
        ("added", '"Two"'),
        ("added", '"Two" > "Child"'),
        ("added", '"Renamed"'),
        ("deleted", '"One"'),
        ("deleted", '"One" > "Child"'),
        ("deleted", '"Rename me"'),
    ]


def test_move_between_existing_parents_is_deleted_plus_added() -> None:
    baseline = "# Left\n## Moving\nbody\n# Right\n"
    current = "# Left\n# Right\n## Moving\nbody\n"
    assert rendered_changes(baseline, current) == [
        ("added", '"Right" > "Moving"'),
        ("deleted", '"Left" > "Moving"'),
    ]


def test_level_change_with_same_path_is_modified() -> None:
    baseline = "# Parent\n## Child\nbody\n"
    current = "# Parent\n### Child\nbody\n"
    assert rendered_changes(baseline, current) == [("modified", '"Parent" > "Child"')]


def test_line_endings_and_boundary_blank_lines_do_not_create_drift() -> None:
    baseline = "# A\r\n\r\nbody\r\n\r\n"
    current = "# A\nbody\n"
    assert rendered_changes(baseline, current) == []


def test_trailing_spaces_that_form_hard_break_are_content() -> None:
    assert rendered_changes("# A\nline  \nnext\n", "# A\nline\nnext\n") == [("modified", '"A"')]


def test_image_alt_markup_does_not_change_heading_identity() -> None:
    baseline = "# ![*Alpha* &amp; `Beta`](/image.png)\nbody\n"
    current = "# ![Alpha & Beta](/image.png)\nbody\n"
    assert rendered_changes(baseline, current) == []


def test_reference_link_in_image_alt_preserves_heading_identity() -> None:
    baseline = "# ![See [docs][d]](image.png)\nbody\n\n[d]: /reference\n"
    current = "# ![See [docs](/reference)](image.png)\nbody\n\n[d]: /reference\n"
    assert rendered_changes(baseline, current) == []
