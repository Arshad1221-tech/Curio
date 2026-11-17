from app.core.security import hash_password, needs_rehash, verify_password
from app.services.text_utils import canonical_genres, clean_list, display_genre, extract_keywords


def test_password_hash_round_trip():
    stored = hash_password("Secret123")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("Secret123", stored)
    assert not verify_password("secret123", stored)
    assert not needs_rehash(stored)


def test_password_hashes_are_salted():
    assert hash_password("Same123") != hash_password("Same123")


def test_verify_rejects_malformed_hash():
    assert not verify_password("anything", "not-a-hash")


def test_canonical_genres_normalises_synonyms_and_compounds():
    assert canonical_genres(["Sci-Fi & Fantasy"]) == ["science fiction", "fantasy"]
    assert canonical_genres("Fiction / Science Fiction / General") == ["fiction", "science fiction"]
    assert canonical_genres(["Hip-Hop/Rap", "R&B/Soul"]) == ["hip-hop", "rap", "r&b", "soul"]


def test_display_genre():
    assert display_genre("science fiction") == "Science Fiction"
    assert display_genre("r&b") == "R&B"
    assert display_genre("hip-hop") == "Hip-Hop"


def test_clean_list_dedupes_and_limits():
    assert clean_list("Space, space , #Reread,,", max_items=5, lower=True) == ["space", "reread"]
    assert len(clean_list([f"t{i}" for i in range(30)], max_items=3)) == 3


def test_extract_keywords_skips_stopwords():
    keywords = extract_keywords("The Martian", "An astronaut is stranded on Mars and must survive on Mars.")
    assert keywords[0] == "mars"
    assert "the" not in keywords and "and" not in keywords
