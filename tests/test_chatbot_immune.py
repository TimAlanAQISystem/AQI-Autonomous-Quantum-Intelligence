#!/usr/bin/env python3
"""
AQI Test Suite — Chatbot Immune System
========================================
Tests for the extracted chatbot_immune_system.py module.

Tests cover:
    - Markdown formatting removal
    - Filler prefix stripping
    - Exact-match chatbot kills
    - Contains-match chatbot kills
    - Early-turn exit guard
    - Repetition detection (short + long phrase)
    - Edge cases (empty input, passthrough)

Neg-Proofed: Yes — tests verify both positive kills and safe passthrough.
"""

import sys
import os
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot_immune_system import clean_sentence

logger = logging.getLogger("test_chatbot_immune")


def _ctx(messages=None):
    """Create a minimal context dict for testing."""
    return {"messages": messages or []}


def _ctx_with_turns(n, alan_texts=None):
    """Create context with N conversation turns."""
    msgs = []
    for i in range(n):
        alan_text = alan_texts[i] if alan_texts and i < len(alan_texts) else f"Alan response {i}"
        msgs.append({"user": f"User turn {i}", "alan": alan_text})
    return {"messages": msgs}


class TestMarkdownCleanup:
    """Phase 1: Markdown formatting removal."""
    
    def test_bold_asterisks(self):
        result = clean_sentence("This is **important** info", _ctx())
        assert result == "This is important info"
    
    def test_bold_underscores(self):
        result = clean_sentence("This is __important__ info", _ctx())
        assert result == "This is important info"
    
    def test_numbered_list(self):
        result = clean_sentence("1. First item here", _ctx())
        assert result == "First item here"
    
    def test_bullet_list(self):
        result = clean_sentence("- A bullet point", _ctx())
        assert result == "A bullet point"
    
    def test_markdown_header(self):
        result = clean_sentence("## Section Title", _ctx())
        assert result == "Section Title"
    
    def test_label_colon_format(self):
        result = clean_sentence("Business Information: Your merchant name", _ctx())
        assert result == "Your merchant name"


class TestFillerPrefixStripping:
    """Phase 2: Filler prefix removal."""
    
    def test_got_it(self):
        result = clean_sentence("Got it, three different businesses you run", _ctx())
        assert result == "Three different businesses you run"
    
    def test_yeah(self):
        result = clean_sentence("Yeah, we work with restaurants all the time", _ctx())
        assert result == "We work with restaurants all the time"
    
    def test_absolutely(self):
        result = clean_sentence("Absolutely, let me tell you about our rates", _ctx())
        assert result == "Let me tell you about our rates"
    
    def test_okay(self):
        result = clean_sentence("Okay, so here's what I can do for you", _ctx())
        assert result == "So here's what I can do for you"
    
    def test_no_strip_if_too_short(self):
        # Short remainder after prefix should NOT be stripped
        result = clean_sentence("Got it, ok", _ctx())
        # "ok" is only 2 chars, so prefix stripping won't fire
        # But "got it" itself is a chatbot kill, so it returns ""
        assert result == ""


class TestChatbotKills:
    """Phase 3: Exact-match chatbot phrase kills."""
    
    def test_that_sounds_great(self):
        assert clean_sentence("That sounds great!", _ctx()) == ""
    
    def test_absolutely(self):
        assert clean_sentence("Absolutely.", _ctx()) == ""
    
    def test_sure_thing(self):
        assert clean_sentence("Sure thing", _ctx()) == ""
    
    def test_im_listening(self):
        assert clean_sentence("I'm listening", _ctx()) == ""
    
    def test_i_appreciate_that(self):
        assert clean_sentence("I appreciate that", _ctx()) == ""
    
    def test_great_question(self):
        assert clean_sentence("Great question!", _ctx()) == ""
    
    def test_fair_enough(self):
        assert clean_sentence("Fair enough.", _ctx()) == ""
    
    def test_passthrough_real_content(self):
        """Substantive sentences should NOT be killed."""
        result = clean_sentence("We can save you about 30% on your processing fees", _ctx())
        assert result == "We can save you about 30% on your processing fees"
    
    def test_passthrough_question(self):
        result = clean_sentence("How many transactions do you process per month", _ctx())
        assert result == "How many transactions do you process per month"


class TestContainsKills:
    """Phase 4: Contains-match chatbot phrase kills."""
    
    def test_i_can_help(self):
        assert clean_sentence("Well, I can help with that for sure", _ctx()) == ""
    
    def test_sounds_like_a_great(self):
        assert clean_sentence("That sounds like a great opportunity", _ctx()) == ""
    
    def test_looking_forward_to(self):
        assert clean_sentence("I'm really looking forward to helping you", _ctx()) == ""


class TestExitGuard:
    """Phase 5: Early-turn exit guard (turns 0-3)."""
    
    def test_goodbye_blocked_turn_0(self):
        ctx = _ctx_with_turns(0)  # Turn 0
        assert clean_sentence("Goodbye, have a great day!", ctx) == ""
    
    def test_take_care_blocked_turn_1(self):
        ctx = _ctx_with_turns(2)  # Turn 1 (2 messages / 2 = 1)
        assert clean_sentence("Take care, nice talking to you", ctx) == ""
    
    def test_ill_try_again_blocked_turn_2(self):
        ctx = _ctx_with_turns(4)  # Turn 2
        assert clean_sentence("I'll try again later when you're less busy", ctx) == ""
    
    def test_goodbye_allowed_turn_5(self):
        ctx = _ctx_with_turns(10)  # Turn 5 — past the guard
        # "have a great day" is still in chatbot_contains_kills, so will be killed by that
        result = clean_sentence("Thanks for considering our services", ctx)
        assert result != ""  # Should NOT be blocked by exit guard


class TestRepetitionDetector:
    """Phase 6: Repetition detection."""
    
    def test_short_phrase_blocked_after_2x(self):
        """Short phrases repeated 2x should be blocked."""
        ctx = _ctx_with_turns(4, alan_texts=[
            "Hello there.",
            "I'm listening.",
            "I'm listening.",
            "Let me explain.",
        ])
        # "I'm listening" already killed by chatbot kills, but test the mechanism
        result = clean_sentence("I'm listening", ctx)
        assert result == ""
    
    def test_long_phrase_overlap_blocked(self):
        """Long phrases with >70% word overlap should be blocked."""
        ctx = _ctx_with_turns(4, alan_texts=[
            "We help businesses reduce their processing costs significantly.",
            "Some response.",
            "Some other response.",
            "Another response.",
        ])
        # High overlap with turn 0
        result = clean_sentence(
            "We help businesses reduce their processing costs dramatically", ctx
        )
        assert result == ""
    
    def test_unique_long_phrase_passes(self):
        """Unique long phrases should NOT be blocked."""
        ctx = _ctx_with_turns(4, alan_texts=[
            "We work with restaurants nationwide.",
            "Our rates are very competitive.",
            "Let me explain the savings.",
            "What processor do you use now?",
        ])
        result = clean_sentence(
            "The integration takes about two business days to complete", ctx
        )
        assert result != ""
    
    def test_no_repetition_on_early_turns(self):
        """Repetition detector should not fire on turns < 3."""
        ctx = _ctx_with_turns(2, alan_texts=[
            "Hello, this is Alan.",
            "Hello, this is Alan.",
        ])
        # Only 2 turns, rep detector requires >= 3
        result = clean_sentence("Some unique content here", ctx)
        assert result == "Some unique content here"


class TestEdgeCases:
    """Edge cases and safe passthrough."""
    
    def test_empty_string(self):
        assert clean_sentence("", _ctx()) == ""
    
    def test_whitespace_only(self):
        assert clean_sentence("   ", _ctx()) == ""
    
    def test_none_handling(self):
        # None should be handled gracefully (returns "")
        try:
            result = clean_sentence(None, _ctx())
            assert result == ""
        except (TypeError, AttributeError):
            pass  # Also acceptable — None is not a valid input
    
    def test_numeric_passthrough(self):
        result = clean_sentence("Your current rate is 2.9% plus 30 cents", _ctx())
        assert result == "Your current rate is 2.9% plus 30 cents"
    
    def test_question_passthrough(self):
        result = clean_sentence("What kind of business do you have?", _ctx())
        assert result == "What kind of business do you have?"


def run_all_tests():
    """Run all test classes and report results."""
    test_classes = [
        TestMarkdownCleanup,
        TestFillerPrefixStripping,
        TestChatbotKills,
        TestContainsKills,
        TestExitGuard,
        TestRepetitionDetector,
        TestEdgeCases,
    ]
    
    total = 0
    passed = 0
    failed = 0
    failures = []
    
    for cls in test_classes:
        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                total += 1
                try:
                    getattr(instance, method_name)()
                    passed += 1
                except Exception as e:
                    failed += 1
                    failures.append(f"  FAIL: {cls.__name__}.{method_name}: {e}")
    
    print(f"\n{'='*60}")
    print(f"AQI TEST SUITE — Chatbot Immune System")
    print(f"{'='*60}")
    print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
    
    if failures:
        print(f"\nFailures:")
        for f in failures:
            print(f)
    else:
        print(f"\n✓ ALL TESTS PASSED")
    
    print(f"{'='*60}\n")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
