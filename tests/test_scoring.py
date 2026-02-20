"""
Tests for Evaluation Studio scoring — reference metrics + LLM judge.
Run: pytest tests/test_scoring.py -v
"""
import pytest
from backend.eval_studio.scoring import (
    score_output, EvalScoreRequest, METRIC_FUNCTIONS,
    exact_match, contains_match, levenshtein_similarity,
    rouge_l_score, bleu_score,
)


class TestReferenceMetrics:

    def test_exact_match_true(self):
        assert exact_match("hello world", "hello world").score == 1.0

    def test_exact_match_false(self):
        assert exact_match("hello", "world").score == 0.0

    def test_exact_match_case_insensitive(self):
        assert exact_match("Hello World", "hello world").score == 1.0

    def test_contains_match_true(self):
        assert contains_match("the answer is 42", "42").score == 1.0

    def test_contains_match_false(self):
        assert contains_match("no match here", "xyz").score == 0.0

    def test_levenshtein_identical(self):
        assert levenshtein_similarity("abc", "abc").score == 1.0

    def test_levenshtein_similar(self):
        result = levenshtein_similarity("kitten", "sitting")
        assert 0.0 < result.score < 1.0

    def test_levenshtein_empty(self):
        assert levenshtein_similarity("", "").score == 1.0

    def test_rouge_l_identical(self):
        result = rouge_l_score("the cat sat on the mat", "the cat sat on the mat")
        assert result.score == 1.0

    def test_rouge_l_partial(self):
        result = rouge_l_score("the cat sat on the mat", "the cat on mat")
        assert 0.0 < result.score < 1.0

    def test_rouge_l_empty(self):
        assert rouge_l_score("", "").score == 0.0

    def test_bleu_identical(self):
        result = bleu_score(
            "the cat sat on the mat and looked around",
            "the cat sat on the mat and looked around",
        )
        assert result.score > 0.8

    def test_bleu_different(self):
        result = bleu_score("hello world", "completely different sentence here now")
        assert result.score < 0.5

    def test_metric_functions_registry(self):
        assert "exact_match" in METRIC_FUNCTIONS
        assert "contains" in METRIC_FUNCTIONS
        assert "levenshtein" in METRIC_FUNCTIONS
        assert "rouge_l" in METRIC_FUNCTIONS
        assert "bleu" in METRIC_FUNCTIONS


class TestScoreOutput:

    def _scores_dict(self, response):
        """Helper: convert reference_scores list to {metric: score} dict."""
        return {s.metric: s.score for s in response.reference_scores}

    def test_score_output_basic(self):
        req = EvalScoreRequest(
            input_text="What is 2+2?",
            output_text="4",
            reference_text="4",
            metrics=["exact_match", "contains"],
            llm_judge_enabled=False,
        )
        result = score_output(req)
        scores = self._scores_dict(result)
        assert scores["exact_match"] == 1.0
        assert scores["contains"] == 1.0
        assert result.aggregate_score == 1.0

    def test_score_output_partial_match(self):
        req = EvalScoreRequest(
            input_text="What is the capital of France?",
            output_text="The capital of France is Paris.",
            reference_text="Paris",
            metrics=["exact_match", "contains", "rouge_l"],
            llm_judge_enabled=False,
        )
        result = score_output(req)
        scores = self._scores_dict(result)
        assert scores["exact_match"] == 0.0  # not exact
        assert scores["contains"] == 1.0     # contains "Paris"
        assert scores["rouge_l"] > 0.0

    def test_score_output_no_reference(self):
        req = EvalScoreRequest(
            input_text="Tell me a joke",
            output_text="Why did the chicken cross the road?",
            reference_text=None,
            metrics=["exact_match"],
            llm_judge_enabled=False,
        )
        result = score_output(req)
        # Without reference, no reference_scores computed
        assert len(result.reference_scores) == 0
        assert result.aggregate_score == 0.0

    def test_score_output_all_metrics(self):
        req = EvalScoreRequest(
            input_text="Q",
            output_text="The answer is definitely forty two",
            reference_text="The answer is 42",
            metrics=["exact_match", "contains", "rouge_l", "bleu", "levenshtein"],
            llm_judge_enabled=False,
        )
        result = score_output(req)
        assert len(result.reference_scores) == 5
        for s in result.reference_scores:
            assert 0.0 <= s.score <= 1.0, f"{s.metric} out of range: {s.score}"
