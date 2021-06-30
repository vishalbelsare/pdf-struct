from typing import Optional

import regex as re

from pdf_struct import features
from pdf_struct.clustering import get_margins, cluster_positions
from pdf_struct.feature_extractor import BaseFeatureExtractor
from pdf_struct.listing import NumberedListState, SectionNumber
from pdf_struct.lm import compare_losses


def _gt(tb) -> Optional[str]:
    # get text
    return None if tb is None else tb.text


class PlainTextFeatureExtractor(BaseFeatureExtractor):
    def __init__(self, text_lines):
        self.right_margin = get_margins(
            cluster_positions([l.width for l in text_lines], 8)[0][::-1], 5)

    def line_break(self, t1, t2):
        if t1 is None:
            return True
        return t1.width not in self.right_margin

    def left_aligned(self, tb):
        return tb.indent == 0

    def indent(self, t1, t2):
        if t1 is None or t2 is None:
            return 3
        if t1.indent < t2.indent:
            return 1
        if t1.indent > t2.indent:
            return 2
        return 0

    @staticmethod
    def indent_body(t1, t2):
        if t1 is None or t2 is None:
            return 3
        if t1.body_indent < t2.body_indent:
            return 1
        if t1.body_indent > t2.body_indent:
            return 2
        return 0

    def centered(self, t):
        if t is None:
            return False
        if t.indent == 0:
            return False
        right_space = self.right_margin.mean - t.width
        left_space = t.indent
        return abs(right_space - left_space) < 8

    @staticmethod
    def extra_line_space(t1):
        if t1 is None:
            return -1
        return t1.top_spacing

    def dict_like(self, t):
        if t is None:
            return False
        return ':' in t.text and t.width not in self.right_margin

    @staticmethod
    def page_like1(t):
        if t is None:
            return False
        return re.search('page [1-9]|PAGE', t.text) is not None

    @staticmethod
    def page_like2(t):
        if t is None:
            return False
        return re.search('[0-9]/[1-9]|- ?[0-9]+ ?-', t.text) is not None

    @staticmethod
    def horizontal_line(t):
        if t is None:
            return False
        charset = set(t.text.strip())
        charset.discard(' ')
        return len(charset) == 1 and len(t.text.strip()) >= 3 and charset.pop() in set('*-=#%_+')

    def extract_features(self, t1, t2, t3, t4):
        if t3 is None:
            numbered_list_state = NumberedListState.DOWN
        else:
            numbered_list_state = self.multi_level_numbered_list.try_append(
                SectionNumber.extract_section_number(t3.text))
        if t1 is None or t3 is None:
            loss_diff_next = 0.
            loss_diff_prev = 0.
        else:
            loss_diff_next = compare_losses(t2.text, t3.text, prev=t1.text)
            loss_diff_prev = compare_losses(t2.text, t1.text, next=t3.text)

        feat = (
            features.whereas(_gt(t2), _gt(t3)),
            features.colon_ish(_gt(t1), _gt(t2)),
            features.colon_ish(_gt(t2), _gt(t3)),
            features.punctuated(_gt(t1), _gt(t2)),
            features.punctuated(_gt(t2), _gt(t3)),
            self.line_break(t1, t2),
            self.line_break(t2, t3),
            features.list_ish(_gt(t2), _gt(t3)),
            self.indent(t1, t2),
            self.indent(t2, t3),
            self.indent_body(t1, t2),
            self.indent_body(t2, t3),
            features.therefore(_gt(t2), _gt(t3)),
            features.all_capital(_gt(t2)),
            features.all_capital(_gt(t3)),
            features.mask_continuation(_gt(t1), _gt(t2)),
            features.mask_continuation(_gt(t2), _gt(t3)),
            features.space_separated(_gt(t2)),
            features.space_separated(_gt(t3)),
            self.centered(t2),
            self.centered(t3),
            self.extra_line_space(t2),
            self.extra_line_space(t3),
            self.dict_like(t2),
            self.dict_like(t3),
            self.page_like1(t1),
            self.page_like1(t2),
            self.page_like1(t3),
            self.page_like2(t1),
            self.page_like2(t2),
            self.page_like2(t3),
            self.horizontal_line(t1),
            self.horizontal_line(t2),
            self.horizontal_line(t3),
            loss_diff_next,
            loss_diff_prev,
            numbered_list_state.value
        )
        return list(map(float, feat))
