class EATValidator:
    def validate(self, rubric: dict):
        self._check_meta(rubric)
        self._check_bands(rubric)

    def _check_meta(self, r):
        meta = r.get('meta', {})
        assert meta.get('version') == 2.0, "Version must be 2.0"
        assert isinstance(meta.get('locked'), bool), "locked must be bool"

    def _check_bands(self, r):
        bands = r.get('bands', [])
        for b in bands:
            mn, mx = b.get('score_min'), b.get('score_max')
            assert 0 <= mn < mx <= 1, f"Invalid range: {mn}-{mx}"
