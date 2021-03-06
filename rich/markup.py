from collections import defaultdict
from operator import itemgetter
import re
from typing import Dict, Iterable, List, Match, Optional, Tuple, Union

from .errors import MarkupError
from .style import Style
from .text import Span, Text
from ._emoji_replace import _emoji_replace


re_tags = re.compile(r"(\[\[)|(\]\])|(\[.*?\])")


def _parse(markup: str) -> Iterable[Tuple[Optional[str], Optional[str]]]:
    """Parse markup in to an iterable of pairs of text, tag.
    
    Args:
        markup (str): A string containing console markup
    
    """
    position = 0
    for match in re_tags.finditer(markup):
        escape_open, escape_close, tag_text = match.groups()
        start, end = match.span()
        if start > position:
            yield markup[position:start], None
        if tag_text is not None:
            yield None, tag_text
        else:
            yield (escape_open and "[") or (escape_close and "]"), None  # type: ignore
        position = end
    if position < len(markup):
        yield markup[position:], None


def render(markup: str, style: Union[str, Style] = "", emoji: bool = True) -> Text:
    """Render console markup in to a Text instance.

    Args:
        markup (str): A string containing console markup.
        emoji (bool, optional): Also render emoji code. Defaults to True.
    
    Raises:
        MarkupError: If there is a syntax error in the markup.
    
    Returns:
        Text: A test instance.
    """
    text = Text(style=style)
    append = text.append
    stylize = text.stylize

    styles: Dict[str, List[int]] = defaultdict(list)
    style_stack: List[str] = []
    normalize = Style.normalize
    emoji_replace = _emoji_replace

    for plain_text, tag in _parse(markup):
        if plain_text is not None:
            append(emoji_replace(plain_text) if emoji else plain_text)
        if tag is not None:
            if tag.startswith("[/"):
                style_name = tag[2:-1].strip()
                if style_name:
                    style_name = normalize(style_name)
                else:
                    try:
                        style_name = style_stack[-1]
                    except IndexError:
                        raise MarkupError(
                            f"closing tag '[/]' at position {len(text)} has nothing to close"
                        )
                try:
                    style_position = styles[style_name].pop()
                except (KeyError, IndexError):
                    raise MarkupError(
                        f"closing tag {tag!r} at position {len(text)} doesn't match open tag"
                    )
                style_stack.remove(style_name)
                stylize(style_position, len(text), style_name)
            else:
                style_name = normalize(tag[1:-1].strip())
                styles[style_name].append(len(text))
                style_stack.append(style_name)

    text_length = len(text)
    while style_stack:
        style_name = style_stack.pop()
        style_position = styles[style_name].pop()
        text.stylize(style_position, text_length, style_name)

    return text
