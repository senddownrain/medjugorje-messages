import unittest
from unittest.mock import patch
import requests
from scripts.diagnose_source_network import classify_error, inspect, safe_proxy

class NetworkDiagnosticsTests(unittest.TestCase):
    def test_connect_403_is_not_origin_http_403(self):
        r=classify_error(requests.exceptions.ProxyError('Tunnel connection failed: 403 Forbidden'))
        self.assertEqual(r['layer'],'proxy_connect')
        self.assertEqual(r['connect_status'],403)
        self.assertIsNone(r['http_status'])
        self.assertFalse(r['origin_reached'])

    def test_proxy_credentials_never_appear(self):
        r=safe_proxy('http://name:secret@proxy.example:8080')
        self.assertEqual(r,{'scheme':'http','host':'proxy.example','port':8080,'credentials_redacted':True})

    def test_robots_error_keeps_error_and_never_fetches_content(self):
        with patch('scripts.diagnose_source_network.probe',return_value=({'http_status':403},b'')) as probe:
            r=inspect('supplementary','https://www.medjugorje.ws/en/messages/',None)
        self.assertEqual(r['state'],'ERROR')
        self.assertEqual([call.args[2] for call in probe.call_args_list],['GET','HEAD'])

    def test_origin_403_preserved(self):
        replies=[({'http_status':404},b''),({'http_status':403},b''),({'http_status':403},b'')]
        with patch('scripts.diagnose_source_network.probe',side_effect=replies):
            r=inspect('primary','https://www.medjugorje.hr/en/our-lady-messages-archive',None)
        self.assertEqual(r['state'],'ERROR')
        self.assertEqual(r['attempts'][-1]['http_status'],403)
        self.assertNotIn('observed_dates',r)

if __name__=='__main__':unittest.main()
