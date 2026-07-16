"""
Tests for intent classifier.
"""
from app.services.intent_classifier import classify_intent


class TestIntentClassifier:
    def test_conversational_greeting(self):
        result = classify_intent("Hello there!")
        assert result["intent"] == "conversation"
        assert result["confidence"] >= 0.8

    def test_conversational_question(self):
        result = classify_intent("What is a kernel?")
        assert result["intent"] == "conversation"
        assert result["confidence"] >= 0.7

    def test_conversational_explain(self):
        result = classify_intent("Explain how A* works")
        assert result["intent"] == "conversation"

    def test_conversational_how_to(self):
        result = classify_intent("How does MongoDB Atlas work?")
        assert result["intent"] == "conversation"

    def test_action_open_app(self):
        result = classify_intent("Open Calculator")
        assert result["intent"] == "action"
        assert result["confidence"] >= 0.8

    def test_action_create_folder(self):
        result = classify_intent("Create a folder named Java")
        assert result["intent"] == "action"

    def test_action_move_files(self):
        result = classify_intent("Move all PDF files into Documents/PDFs")
        assert result["intent"] == "action"

    def test_action_delete_file(self):
        result = classify_intent("Delete report.txt from Documents")
        assert result["intent"] == "action"

    def test_action_navigate_url(self):
        result = classify_intent("Go to google.com and search for machine learning")
        assert result["intent"] == "action"

    def test_action_send_email(self):
        result = classify_intent("Send email to user@domain.com about meeting")
        assert result["intent"] == "action"

    def test_action_search_web(self):
        result = classify_intent("Search for latest AI news")
        assert result["intent"] == "action"

    def test_clarification_delete_that(self):
        result = classify_intent("delete that")
        assert result["intent"] == "clarification_required"

    def test_clarification_move_everything(self):
        result = classify_intent("move everything")
        assert result["intent"] == "clarification_required"

    def test_clarification_send_it(self):
        result = classify_intent("send it")
        assert result["intent"] == "clarification_required"

    def test_empty_input(self):
        result = classify_intent("")
        assert result["intent"] == "clarification_required"

    def test_action_find_files(self):
        result = classify_intent("Find all PDF files on my desktop")
        assert result["intent"] == "action"

    def test_action_list_directory(self):
        result = classify_intent("List all files in Documents folder")
        assert result["intent"] == "action"

    def test_conversational_thanks(self):
        result = classify_intent("Thanks!")
        assert result["intent"] == "conversation"
        assert result["confidence"] >= 0.8

    def test_action_rename_file(self):
        result = classify_intent("Rename notes-old.txt to notes.txt")
        assert result["intent"] == "action"

    def test_action_organize_vague(self):
        result = classify_intent("organize my files")
        assert result["intent"] == "clarification_required"
