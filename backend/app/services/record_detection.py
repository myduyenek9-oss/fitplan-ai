from __future__ import annotations

import re

_EXERCISE_TERMS = re.compile(
    r"\u8dd1\u6b65|\u6162\u8dd1|\u5feb\u8d70|\u6563\u6b65|\u8d70\u8def|\u9a91\u8f66|\u5355\u8f66|\u6e38\u6cf3|\u8df3\u7ef3|\u745c\u4f3d|\u666e\u62c9\u63d0|\u722c\u697c|\u722c\u5761|\u692d\u5706\u673a|\u5212\u8239\u673a|"
    r"\u5065\u8eab|\u8fd0\u52a8|\u8bad\u7ec3|\u953b\u70bc|\u7ec3|\u529b\u91cf|\u6709\u6c27|\u5367\u63a8|\u6df1\u8e72|\u786c\u62c9|\u5f15\u4f53|\u4fef\u5367\u6491|\u7ec3\u80f8|\u7ec3\u80cc|\u7ec3\u817f|\u7ec3\u80a9|\u7ec3\u624b\u81c2|\u54c8\u514b|\u6253\u7403"
)
_ACTION_COMPLETED_EXERCISE_MARKERS = re.compile(
    r"\u5b8c\u6210\u4e86?|\u7ed3\u675f\u4e86?|\u56de\u6765|\u7ec3\u4e86|\u8dd1\u4e86|\u8d70\u4e86|\u9a91\u4e86|\u6e38\u4e86|\u505a\u4e86|\u8df3\u4e86|\u6253\u4e86|\u722c\u4e86|\u8fd0\u52a8\u4e86|\u8bad\u7ec3\u4e86|\u953b\u70bc\u4e86"
)
_CONTEXT_COMPLETED_MARKERS = re.compile(r"\u521a\u521a?|\u521a\u624d|\u5df2\u7ecf")
_FUTURE_OR_QUESTION_MARKERS = re.compile(
    r"\u660e\u5929|\u540e\u5929|\u5f85\u4f1a|\u7b49\u4f1a|\u4e00\u4f1a\u513f?|\u7a0d\u540e|\u51c6\u5907|\u8ba1\u5212|\u6253\u7b97|\u60f3\u8981?|\u8981\u53bb|\u5e94\u8be5|\u5efa\u8bae|\u600e\u4e48|\u5982\u4f55|\u80fd\u4e0d\u80fd|\u53ef\u4e0d\u53ef\u4ee5"
)
_NEGATED_EXERCISE = re.compile(
    r"(?:\u6ca1|\u6ca1\u6709|\u672a|\u6ca1\u80fd|\u6ca1\u53bb|\u53d6\u6d88|\u4e0d\u6253\u7b97|\u4e0d\u60f3).{0,8}(?:\u8dd1\u6b65|\u6162\u8dd1|\u8fd0\u52a8|\u8bad\u7ec3|\u5065\u8eab|\u7ec3|\u8d70|\u9a91|\u6e38|\u8df3|\u722c|\u6253\u7403)"
)
_CHINESE_NUMBER = r"[\u96f6\u3007\u4e00\u4e8c\u4e24\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d\u5341\u767e]+"
_DURATION_MARKER = re.compile(
    rf"(?:\d+(?:\.\d+)?|{_CHINESE_NUMBER}|\u534a|\u4e00\u4e2a)\s*(?:\u5206\u949f|\u5206|\u5c0f\u65f6|\u949f\u5934)"
)
_FOOD_COMPLETED_MARKERS = re.compile(
    r"\u5403\u4e86|\u559d\u4e86|\u5403\u8fc7|\u559d\u8fc7|\u5403\u7684\u662f|"
    r"\u65e9\u9910|\u5348\u9910|\u665a\u9910|\u52a0\u9910|"
    r"\u65e9\u4e0a\u5403|\u4e0a\u5348\u5403|\u4e2d\u5348\u5403|\u4e0b\u5348\u5403|\u665a\u4e0a\u5403"
)
_EXERCISE_SET_OR_WEIGHT_MARKER = re.compile(
    r"\d+(?:\.\d+)?\s*(?:\u7ec4|\u6b21|kg|\u516c\u65a4|\u5343\u514b)", re.IGNORECASE
)
_FUTURE_RECORD_MARKERS = re.compile(
    r"\u660e\u5929|\u540e\u5929|\u5f85\u4f1a|\u7b49\u4f1a|\u4e00\u4f1a\u513f?|\u7a0d\u540e|"
    r"(?:\u51c6\u5907|\u8ba1\u5212|\u6253\u7b97|\u60f3|\u60f3\u8981|\u8981)"
    r".{0,8}(?:\u8dd1\u6b65|\u6162\u8dd1|\u5feb\u8d70|\u6563\u6b65|\u9a91\u8f66|\u6e38\u6cf3|\u8df3\u7ef3|"
    r"\u5065\u8eab|\u8fd0\u52a8|\u8bad\u7ec3|\u953b\u70bc|\u7ec3|\u529b\u91cf|\u6709\u6c27|\u5367\u63a8|\u6df1\u8e72|\u786c\u62c9|\u722c\u5761)"
)
_NON_COMPLETED_EXERCISE_INTENT = re.compile(
    r"(?:\u53ea\u80fd|\u53ef\u4ee5|\u80fd|\u5e0c\u671b|\u9700\u8981|\u6253\u7b97)"
    r".{0,8}(?:\u8dd1\u6b65|\u6162\u8dd1|\u8fd0\u52a8|\u8bad\u7ec3|\u5065\u8eab|\u7ec3|\u8d70|\u9a91|\u6e38|\u8df3|\u722c|\u5367\u63a8|\u6df1\u8e72|\u786c\u62c9)"
)


def looks_like_completed_exercise(message: str) -> bool:
    """Conservatively identify a message that reports completed exercise."""
    normalized = re.sub(r"\s+", "", message)
    if not _EXERCISE_TERMS.search(normalized) or _NEGATED_EXERCISE.search(normalized):
        return False

    action_completed = bool(_ACTION_COMPLETED_EXERCISE_MARKERS.search(normalized))
    context_completed = bool(_CONTEXT_COMPLETED_MARKERS.search(normalized))
    if _FUTURE_OR_QUESTION_MARKERS.search(normalized) and not action_completed:
        return False
    return action_completed or context_completed


def looks_like_mixed_completed_records(message: str) -> bool:
    """Identify a message that reports both consumed food and completed exercise."""
    normalized = re.sub(r"\s+", "", message)
    if not _FOOD_COMPLETED_MARKERS.search(normalized):
        return False
    if not _EXERCISE_TERMS.search(normalized) or _NEGATED_EXERCISE.search(normalized):
        return False

    action_completed = bool(_ACTION_COMPLETED_EXERCISE_MARKERS.search(normalized))
    if (
        _FUTURE_RECORD_MARKERS.search(normalized)
        or _NON_COMPLETED_EXERCISE_INTENT.search(normalized)
    ) and not action_completed:
        return False

    exercise_evidence = (
        action_completed
        or (
            _CONTEXT_COMPLETED_MARKERS.search(normalized)
            and not _FUTURE_OR_QUESTION_MARKERS.search(normalized)
        )
        or _DURATION_MARKER.search(normalized)
        or _EXERCISE_SET_OR_WEIGHT_MARKER.search(normalized)
    )
    return bool(exercise_evidence)
