"""Digest-bound locators for elements in one JATS source document."""

from __future__ import annotations

import hashlib
import re
from xml.etree import ElementTree as ET

_DIGEST = re.compile(r"[0-9a-f]{64}")
_COMPONENT = re.compile(r"([^\W\d][\w.-]*)\[([1-9][0-9]*)\]")
_TARGET_KINDS = frozenset({"sec", "p", "abstract"})


class LocatorError(ValueError):
    """Base error for source locators."""


class MalformedLocatorError(LocatorError):
    """A locator does not match the v1 grammar."""


class DigestMismatchError(LocatorError):
    """A locator names a different source byte stream."""


class PathNotFoundError(LocatorError):
    """A well-formed locator path has no matching element."""


class InvalidTargetError(LocatorError):
    """A locator resolves to an unsupported element kind."""


class ForeignElementError(LocatorError):
    """An element does not belong to this source document."""


def local_name(element: ET.Element) -> str:
    """Return the element name without its namespace."""
    return element.tag.rsplit("}", 1)[-1]


class SourceDocument:
    """One parsed XML tree and its exact-byte SHA256 digest.

    Callers must apply the T006 XML safety gate before ``from_bytes``.
    """

    root: ET.Element
    sha256: str

    def __init__(
        self,
        root: ET.Element,
        sha256: str,
        parents: dict[ET.Element, ET.Element],
    ) -> None:
        """Store the parsed tree, its digest, and its parent index."""
        self.root = root
        self.sha256 = sha256
        self._parents = parents

    @classmethod
    def from_bytes(cls, xml_bytes: bytes) -> SourceDocument:
        """Create a source document from already-validated XML bytes."""
        root = ET.fromstring(xml_bytes)
        parents = {child: parent for parent in root.iter() for child in parent}
        return cls(root, hashlib.sha256(xml_bytes).hexdigest(), parents)

    def locator_for(self, element: ET.Element) -> str:
        """Return the absolute v1 locator for an element in this tree."""
        if element is not self.root and element not in self._parents:
            raise ForeignElementError("Element is not in this source document")

        components: list[str] = []
        current = element
        while current is not self.root:
            parent = self._parents[current]
            name = local_name(current)
            siblings = (child for child in parent if local_name(child) == name)
            index = next(
                position
                for position, sibling in enumerate(siblings, start=1)
                if sibling is current
            )
            components.append(f"{name}[{index}]")
            current = parent
        components.append(f"{local_name(self.root)}[1]")
        return f"jats:v1:{self.sha256}:/{'/'.join(reversed(components))}"

    def resolve(self, locator: str) -> ET.Element:
        """Resolve a v1 locator to a supported target in this tree."""
        parts = locator.split(":", 3)
        if len(parts) != 4 or parts[:2] != ["jats", "v1"]:
            raise MalformedLocatorError("Invalid locator prefix or version")
        digest, path = parts[2:]
        if _DIGEST.fullmatch(digest) is None or not path.startswith("/"):
            raise MalformedLocatorError("Invalid locator digest or path")

        components = path[1:].split("/")
        parsed = [_COMPONENT.fullmatch(component) for component in components]
        if not parsed or any(match is None for match in parsed):
            raise MalformedLocatorError("Invalid locator path component")

        if digest != self.sha256:
            raise DigestMismatchError("Locator digest differs from source")

        root_match = parsed[0]
        assert root_match is not None
        if (
            root_match.group(1) != local_name(self.root)
            or root_match.group(2) != "1"
        ):
            raise PathNotFoundError("Locator root does not match source")

        current = self.root
        for match in parsed[1:]:
            assert match is not None
            name, index_text = match.groups()
            siblings = [child for child in current if local_name(child) == name]
            sibling_count = str(len(siblings))
            if (len(index_text), index_text) > (
                len(sibling_count),
                sibling_count,
            ):
                raise PathNotFoundError("Locator path does not exist")
            current = siblings[int(index_text) - 1]

        if local_name(current) not in _TARGET_KINDS:
            raise InvalidTargetError("Locator target kind is unsupported")
        return current
