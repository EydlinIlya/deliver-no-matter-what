import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from am_israel_hai_badge.models import SignalType
from am_israel_hai_badge.normalize import (
    normalize_day_history_alert,
    normalize_history_alert,
)

TZ = ZoneInfo("Asia/Jerusalem")


class TestNormalizeHistoryAlert(unittest.TestCase):
    def test_active_alert(self):
        raw = {
            "alertDate": "2026-03-20 14:30:00",
            "category": "1",
            "title": "ירי רקטות וטילים",
            "data": "חיפה - מפרץ, תל אביב",
        }
        alerts = normalize_history_alert(raw)
        self.assertEqual(len(alerts), 2)
        self.assertEqual(alerts[0].area, "חיפה - מפרץ")
        self.assertEqual(alerts[0].signal_type, SignalType.ACTIVE_ALERT)
        self.assertEqual(alerts[0].timestamp, datetime(2026, 3, 20, 14, 30, 0, tzinfo=TZ))
        self.assertEqual(alerts[1].area, "תל אביב")

    def test_preparatory(self):
        raw = {
            "alertDate": "2026-03-20 14:28:00",
            "category": "14",
            "title": "",
            "data": "חיפה - מפרץ",
        }
        alerts = normalize_history_alert(raw)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].signal_type, SignalType.PREPARATORY)

    def test_safety(self):
        raw = {
            "alertDate": "2026-03-20 14:45:00",
            "category": "13",
            "title": "האירוע הסתיים",
            "data": "חיפה - מפרץ",
        }
        alerts = normalize_history_alert(raw)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].signal_type, SignalType.SAFETY)

    def test_iso_timestamp(self):
        raw = {
            "alertDate": "2026-03-20T14:30:00",
            "category": "1",
            "title": "",
            "data": "חיפה - מפרץ",
        }
        alerts = normalize_history_alert(raw)
        self.assertEqual(alerts[0].timestamp, datetime(2026, 3, 20, 14, 30, 0, tzinfo=TZ))


class TestNormalizeDayHistoryAlert(unittest.TestCase):
    def test_active_alert(self):
        raw = {
            "alertDate": "2026-03-20 14:30:00",
            "category_desc": "ירי רקטות וטילים",
            "title": "ירי רקטות וטילים",
            "data": "חיפה - מפרץ",
        }
        alerts = normalize_day_history_alert(raw)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].signal_type, SignalType.ACTIVE_ALERT)

    def test_preparatory(self):
        raw = {
            "alertDate": "2026-03-20 14:28:00",
            "category_desc": "בדקות הקרובות צפויות להתקבל התרעות באזורך",
            "title": "",
            "data": "חיפה - מפרץ",
        }
        alerts = normalize_day_history_alert(raw)
        self.assertEqual(alerts[0].signal_type, SignalType.PREPARATORY)

    def test_safety(self):
        raw = {
            "alertDate": "2026-03-20 14:45:00",
            "category_desc": "האירוע הסתיים",
            "title": "",
            "data": "חיפה - מפרץ",
        }
        alerts = normalize_day_history_alert(raw)
        self.assertEqual(alerts[0].signal_type, SignalType.SAFETY)

    def test_multiple_areas(self):
        raw = {
            "alertDate": "2026-03-20 14:30:00",
            "category_desc": "ירי רקטות וטילים",
            "title": "",
            "data": "חיפה - מפרץ, מפרץ חיפה, תל אביב",
        }
        alerts = normalize_day_history_alert(raw)
        self.assertEqual(len(alerts), 3)
        self.assertEqual(alerts[0].area, "חיפה - מפרץ")
        self.assertEqual(alerts[1].area, "מפרץ חיפה")
        self.assertEqual(alerts[2].area, "תל אביב")


if __name__ == "__main__":
    unittest.main()
