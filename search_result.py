from whoosh.analysis import StandardAnalyzer

class SearchResult:
    def __init__(self, text, matched, ix, field_name, initial_score=0):
        self._text = text
        self._matched = matched
        self._initial_score = initial_score
        self._analyzer = StandardAnalyzer()
        self._ix = ix
        self._field_name = field_name

        self._score = self._calculate_score()

    def __str__(self):
        return self.text

    def __repr__(self):
        return "<MagiaTerm(score={}, text={}, matched={}>".format(self.score, self.text, self.matched)

    @property
    def tokens(self):
        return [t.text for t in self._analyzer(self.text)]

    @property
    def score(self):
        return self._score

    @property
    def text(self):
        return self._text

    @property
    def matched(self):
        return self._matched

    def _calculate_score(self):
        all_tokens_matched = all([token in self.matched for token in self.tokens])
        if all_tokens_matched:
            return 100
        not_matched_tokens = list(set([token for token in self.tokens if token not in self.matched]))
        with self._ix.searcher() as s:
            product = 1
            for token in not_matched_tokens:
                product *= s.frequency(self._field_name, token)
        return product / len(not_matched_tokens)

    def items(self):
        return self.score, self.text, self.matched
