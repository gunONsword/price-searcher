import importlib.util
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('scheduled', Path(__file__).resolve().parents[2] / 'scripts' / 'collect_all_scheduled.py')
scheduled = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scheduled)

class ScheduledBatchTests(TestCase):
    @patch.object(scheduled, 'request', return_value={'running': False})
    def test_check_never_starts_collection(self, request):
        scheduled.run(check=True)
        request.assert_called_once_with('/api/collect-progress/')

    @patch.object(scheduled.time, 'sleep')
    @patch.object(scheduled.Path, 'write_text')
    @patch.object(scheduled, 'request')
    def test_waits_for_manual_batch_then_collects_all(self, request, write, sleep):
        request.side_effect = [{'running':True}, {'running':False}, {'ok':True,'total':118}, {'running':False,'skipped':[]}]
        scheduled.run()
        self.assertEqual(request.call_args_list[2].args, ('/api/run-collect-daily-prices/', {}))
        write.assert_called_once()

    @patch.object(scheduled.time, 'sleep')
    @patch.object(scheduled.Path, 'write_text')
    @patch.object(scheduled, 'request')
    def test_skipped_keywords_mark_task_failed(self, request, write, sleep):
        request.side_effect = [{'running':False}, {'ok':True,'total':1}, {'running':False,'skipped':[{'keyword':'test','error':'API error'}]}]
        with self.assertRaisesRegex(RuntimeError, 'skipped'):
            scheduled.run()


    def test_busy_api_preserves_the_running_keyword_selection(self):
        from rest_framework.test import APIRequestFactory
        from price import views
        selected = ["existing keyword"]
        request = APIRequestFactory().post('/api/run-collect-daily-prices/', {}, format='json')
        with patch.object(views, '_collect_progress', {'running': True}), patch.object(views, '_collect_keywords_filter', selected):
            response = views.run_collect_daily_prices_api(request)
            self.assertEqual(response.status_code, 409)
            self.assertEqual(views._collect_keywords_filter, selected)
