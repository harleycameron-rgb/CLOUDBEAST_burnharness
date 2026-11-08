import io
import json
import unittest
from unittest.mock import patch

from backend.preview import app
from invariant_harvest import LOCAL_REVISION, verify_evidence
from zero_data import FileIOViolation, forbid_file_io


class PreviewHTTPTests(unittest.TestCase):
    def request(self, *, path='/api/harvest', method='POST', raw=None, **changes):
        raw = json.dumps({'fixture': LOCAL_REVISION}).encode() if raw is None else raw
        env = {'PATH_INFO': path, 'REQUEST_METHOD': method, 'HTTP_HOST': 'localhost:8085',
               'wsgi.url_scheme': 'http', 'CONTENT_TYPE': 'application/json',
               'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw), **changes}
        result = {}
        def start(status, headers):
            result.update(status=status, headers=dict(headers))
        result['body'] = json.loads(b''.join(app(env, start)))
        return result

    def test_real_guarded_fixture_is_reproduced_and_not_persisted(self):
        with forbid_file_io():
            r = self.request()
        self.assertEqual(r['status'], '200 OK')
        self.assertTrue(verify_evidence(r['body']['evidence']))
        self.assertFalse(r['body']['upstream_verified'])
        self.assertFalse(r['body']['persistent_artifacts'])
        self.assertEqual(r['body']['nativeGate'], 'CLOSED')
        self.assertEqual(r['headers']['Cache-Control'], 'no-store')

    def test_requests_are_stateless_and_repeatable(self):
        first, second = self.request(), self.request()
        self.assertEqual(first['body'], second['body'])

    def test_health_does_not_run_fixture(self):
        with patch('backend.preview.local_fixture', side_effect=AssertionError):
            r = self.request(path='/runtime', method='GET')
        self.assertEqual(r['status'], '200 OK')
        self.assertEqual(r['body']['scope'], 'synthetic_local_fixture_only')

    def test_unknown_path_and_unsupported_method(self):
        self.assertTrue(self.request(path='/other')['status'].startswith('404'))
        self.assertTrue(self.request(method='GET')['status'].startswith('405'))

    def test_reject_cross_origin_and_raw_media(self):
        self.assertTrue(self.request(HTTP_ORIGIN='https://other.example')['status'].startswith('403'))
        self.assertTrue(self.request(HTTP_SEC_FETCH_SITE='cross-site')['status'].startswith('403'))
        self.assertTrue(self.request(CONTENT_TYPE='audio/wav')['status'].startswith('415'))
        self.assertTrue(self.request(HTTP_ORIGIN='http://localhost:8085')['status'].startswith('200'))

    def test_reject_malformed_oversized_and_extra_input(self):
        for raw in (b'{', b'[]', b'{"fixture":"unknown"}',
                    b'{"fixture":"wrong","fixture":"local-invariant-tap/1"}',
                    json.dumps({'fixture': LOCAL_REVISION, 'raw_media': [1]}).encode()):
            self.assertTrue(self.request(raw=raw)['status'].startswith('400'))
        for length in ('0', '-1', '257', 'not-number'):
            self.assertTrue(self.request(CONTENT_LENGTH=length)['status'].startswith('413'))

    def test_host_guard_failure_is_visible_and_never_bypassed(self):
        with patch('backend.preview.local_fixture', side_effect=FileIOViolation('private path')):
            r = self.request()
        self.assertTrue(r['status'].startswith('503'))
        self.assertEqual(r['body']['reason'], 'zero_data_guard_refused_host_environment')
        self.assertNotIn('private path', json.dumps(r))

    def test_runtime_or_integrity_failure_never_reports_success(self):
        with patch('backend.preview.verify_evidence', return_value=False):
            self.assertTrue(self.request()['status'].startswith('503'))
        with patch('backend.preview.local_fixture', side_effect=RuntimeError('private trace')):
            r = self.request()
        self.assertEqual(r['body']['nativeGate'], 'CLOSED')
        self.assertNotIn('private trace', json.dumps(r))


if __name__ == '__main__':
    unittest.main()
