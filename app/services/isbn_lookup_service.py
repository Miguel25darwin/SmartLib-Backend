"""
Service d'auto-remplissage par ISBN, conforme aux "Consignes de Gestion du
catalogue" : interroge Open Library en premier, puis Google Books en
fallback si l'ISBN est inconnu ou si le service ne repond pas.

Un ISBN structurellement invalide (mauvais prefixe, somme de controle
incorrecte) est rejete AVANT tout appel reseau externe : on ne peut pas se
fier a la fiabilite des bases tierces (Open Library est collaborative et
peut contenir des entrees erronees), donc la validation de format doit
etre faite cote serveur, en amont.
"""

import re

import httpx

from app.schemas.isbn_lookup import IsbnLookupResult

HTTP_TIMEOUT_SECONDS = 5.0

OPEN_LIBRARY_URL = "https://openlibrary.org/api/books"
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"


class InvalidIsbnFormatError(Exception):
    """Levee quand l'ISBN fourni n'est pas structurellement valide (avant tout appel reseau)."""
    pass


def _isbn13_checksum_valid(digits: str) -> bool:
    """Verifie la somme de controle ISBN-13 (algorithme officiel, poids alternes 1 et 3)."""
    total = sum(int(d) * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits[:12]))
    check_digit = (10 - (total % 10)) % 10
    return check_digit == int(digits[12])


def _isbn10_checksum_valid(digits: str) -> bool:
    """Verifie la somme de controle ISBN-10 (poids decroissants 10 a 1, modulo 11)."""
    total = 0
    for i, d in enumerate(digits[:9]):
        total += int(d) * (10 - i)
    check = digits[9]
    check_value = 10 if check == "X" else int(check)
    total += check_value
    return total % 11 == 0


def validate_isbn_format(isbn: str) -> str:
    """
    Valide qu'une chaine est un ISBN-10 ou ISBN-13 structurellement correct.
    Retourne l'ISBN nettoye (sans tirets/espaces) si valide, leve
    InvalidIsbnFormatError sinon. Aucun appel reseau ici — validation pure.
    """
    clean = isbn.strip().replace("-", "").replace(" ", "").upper()

    if not re.fullmatch(r"\d{9}[\dX]", clean) and not re.fullmatch(r"\d{13}", clean):
        raise InvalidIsbnFormatError(
            f"'{isbn}' n'a pas un format ISBN valide (10 ou 13 chiffres attendus)."
        )

    if len(clean) == 13:
        if not clean.startswith(("978", "979")):
            raise InvalidIsbnFormatError(
                f"'{isbn}' n'est pas un ISBN-13 valide : doit commencer par 978 ou 979."
            )
        if not _isbn13_checksum_valid(clean):
            raise InvalidIsbnFormatError(f"'{isbn}' a une somme de controle ISBN-13 incorrecte.")
    else:
        if not _isbn10_checksum_valid(clean):
            raise InvalidIsbnFormatError(f"'{isbn}' a une somme de controle ISBN-10 incorrecte.")

    return clean


def _extract_year(date_str: str | None) -> int | None:
    """Extrait une annee a 4 chiffres depuis une chaine de date heterogene."""
    if not date_str:
        return None
    match = re.search(r"(19|20)\d{2}", date_str)
    return int(match.group(0)) if match else None


def _lookup_open_library(isbn: str) -> IsbnLookupResult | None:
    """Interroge Open Library. Retourne None si l'ISBN est inconnu ou en cas d'erreur reseau."""
    try:
        response = httpx.get(
            OPEN_LIBRARY_URL,
            params={"bibkeys": f"ISBN:{isbn}", "format": "json", "jscmd": "data"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        book_data = data.get(f"ISBN:{isbn}")
        if not book_data:
            return None

        authors = book_data.get("authors", [])
        author_name = authors[0]["name"] if authors else None
        publishers = book_data.get("publishers", [])
        publisher_name = publishers[0]["name"] if publishers else None
        cover = book_data.get("cover", {})
        cover_url = cover.get("medium") or cover.get("small")

        return IsbnLookupResult(
            isbn=isbn,
            title=book_data.get("title"),
            author=author_name,
            publisher=publisher_name,
            publication_year=_extract_year(book_data.get("publish_date")),
            cover_url=cover_url,
            source="open_library",
        )
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        return None


def _lookup_google_books(isbn: str) -> IsbnLookupResult | None:
    """Interroge Google Books en fallback, avec verification stricte de l'ISBN retourne."""
    try:
        response = httpx.get(
            GOOGLE_BOOKS_URL,
            params={"q": f"isbn:{isbn}"},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not items:
            return None

        volume_info = items[0].get("volumeInfo", {})
        identifiers = volume_info.get("industryIdentifiers", [])
        returned_isbns = {ident.get("identifier", "").replace("-", "") for ident in identifiers}
        if isbn not in returned_isbns:
            return None

        authors = volume_info.get("authors", [])
        image_links = volume_info.get("imageLinks", {})

        return IsbnLookupResult(
            isbn=isbn,
            title=volume_info.get("title"),
            author=authors[0] if authors else None,
            publisher=volume_info.get("publisher"),
            publication_year=_extract_year(volume_info.get("publishedDate")),
            cover_url=image_links.get("thumbnail"),
            source="google_books",
        )
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        return None


def lookup_isbn(isbn: str) -> IsbnLookupResult | None:
    """
    Point d'entree unique : valide le format, puis tente Open Library, puis
    Google Books en fallback. Leve InvalidIsbnFormatError si le format est
    structurellement invalide (aucun appel reseau n'est fait dans ce cas).
    """
    clean_isbn = validate_isbn_format(isbn)

    result = _lookup_open_library(clean_isbn)
    if result is not None:
        return result

    return _lookup_google_books(clean_isbn)
