import pytest

from src.io.tts import strip_markdown


@pytest.mark.parametrize(
    "md_input, expected_output",
    [
        # Basic Formatting
        ("**Bold**", "Bold"),
        ("*Italic*", "Italic"),
        ("__Bold__", "Bold"),
        ("_Italic_", "Italic"),
        ("`Code`", "Code"),
        # Headings
        ("# Heading 1", "Heading 1"),
        ("## Heading 2", "Heading 2"),
        ("### Heading 3", "Heading 3"),
        # Links
        ("[Example](https://example.com)", "Example"),
        ("Click [here](https://example.com) for info", "Click here for info"),
        # Images
        ("![Alt text](image.png)", ""),
        ("Here is an image: ![Alt](img.jpg)", "Here is an image:"),
        # Lists
        ("- Item 1\n- Item 2", "Item 1\nItem 2"),
        ("* Item A\n* Item B", "Item A\nItem B"),
        ("1. First\n2. Second", "First\nSecond"),
        # Mixed Markdown
        ("# Title\n**Bold** and *Italic*\n[Link](url)", "Title\nBold and Italic\nLink"),
        # Edge Cases
        ("", ""),
        ("Normal text", "Normal text"),
        ("`code` and **bold**", "code and bold"),
        ("- **Bold Item**", "Bold Item"),
    ],
)
def test_strip_markdown(md_input, expected_output):
    assert strip_markdown(md_input) == expected_output
