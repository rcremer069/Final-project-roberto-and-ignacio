import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

# Import the functions under test:
# Adjust the import path so it matches your actual project module structure
from project import (
    delete_word_by_id,
    add_new_word,
    generate_quiz
)

# ----------
# TEST delete_word_by_id
# ----------
@patch("project.write_words_csv")
@patch("project.read_words_csv")
def test_delete_word_by_id(mock_read, mock_write):
    """
    Tests the delete_word_by_id function with valid and invalid row IDs.
    """
    # Mock DataFrame
    df_mock = pd.DataFrame([
        {"en": "hello", "de": "hallo"},
        {"en": "cat", "de": "katze"},
    ])
    mock_read.return_value = df_mock

    # 1) Valid row_id
    success, message = delete_word_by_id(row_id=0)
    assert success is True
    assert message == "Word deleted successfully."
    # Ensure we dropped row 0 and called write_words_csv
    assert mock_write.called, "write_words_csv should be called on successful delete."

    # 2) Invalid row_id
    success, message = delete_word_by_id(row_id=999)
    assert success is False
    assert message == "Invalid row index."
    # write_words_csv should not be called for an invalid row
    # We can check call_count or call_args, but in this scenario,
    # we might expect it to be called once from the previous test,
    # so we confirm it was not called again:
    assert mock_write.call_count == 1, "write_words_csv should not be called again on invalid row."

# ----------
# TEST add_new_word
# ----------
@patch("project.write_words_csv")
@patch("project.read_words_csv")
@patch("project.translate_word")
@patch("project.detect_lang")
def test_add_new_word(mock_detect, mock_translate, mock_read, mock_write):
    """
    Tests add_new_word function for various scenarios:
    - Empty input
    - Unsupported language
    - Identical translation
    - Duplicate entry
    - Success
    """
    # Mock an existing CSV with some words
    df_mock = pd.DataFrame([
        {"en": "hello", "de": "hallo"},
    ])
    mock_read.return_value = df_mock

    # 1) Empty input
    success, message = add_new_word("")
    assert success is False
    assert message == "Please enter a word."

    # 2) Unsupported language
    mock_detect.return_value = "fr"  # Suppose we get French
    success, message = add_new_word("bonjour")
    assert success is False
    assert message == "Use English or German only."

    # 3) Identical translation
    mock_detect.return_value = "en"
    mock_translate.return_value = "hello"  # same as input
    success, message = add_new_word("hello")
    assert success is False
    assert message == "The word cannot be translated (it came back identical)."

    # 4) Duplicate entry
    mock_detect.return_value = "en"
    mock_translate.return_value = "hallo"  # so 'en' -> 'hallo' for 'de'
    success, message = add_new_word("hello")
    assert success is False
    assert message == "That pair already exists in the dictionary."

    # 5) Success scenario
    # Let's return something new from translation
    mock_detect.return_value = "en"
    mock_translate.return_value = "blumen"  # "flower" in German, e.g.
    # Also, let’s adapt df so it’s not a duplicate
    df_mock2 = pd.DataFrame([
        {"en": "hello", "de": "hallo"}
    ])
    mock_read.return_value = df_mock2

    success, message = add_new_word("flower")
    assert success is True
    assert "was added successfully!" in message
    # Ensure we wrote to CSV
    mock_write.assert_called_once()

# ----------
# TEST generate_quiz
# ----------
@patch("project.read_words_csv")
def test_generate_quiz(mock_read):
    """
    Tests generate_quiz function, focusing on:
    - Empty DataFrame
    - Non-empty DataFrame (EN or DE quiz)
    """
    # 1) Empty DataFrame
    df_empty = pd.DataFrame(columns=["en", "de"])
    mock_read.return_value = df_empty
    success, err_msg, question_word, answers = generate_quiz("EN")
    assert success is False
    assert err_msg == "No words in the dictionary to quiz on!"
    assert question_word is None
    assert answers is None

    # 2) Non-empty DataFrame
    df_mock = pd.DataFrame([
        {"en": "hello", "de": "hallo"},
        {"en": "cat", "de": "katze"}
    ])
    mock_read.return_value = df_mock

    # generate quiz for English
    success, err_msg, question_word, answers = generate_quiz("EN")
    assert success is True
    assert err_msg is None
    # question_word should be one of 'hello' or 'cat'
    assert question_word in ["hello", "cat"]
    # answers should match the corresponding 'de' value
    # (we can't know which row we sampled, so we just check if it's from the set)
    assert any(ans in ["hallo", "katze"] for ans in answers)

    # generate quiz for German
    success, err_msg, question_word, answers = generate_quiz("DE")
    assert success is True
    assert err_msg is None
    # question_word should be either 'hallo' or 'katze'
    assert question_word in ["hallo", "katze"]
    # answers should be the English side
    assert any(ans in ["hello", "cat"] for ans in answers)
