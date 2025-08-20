"""
Юнит-тесты для утилитарных функций
"""
import pytest
from datetime import datetime, time
import pytz
from app.utils import is_in_quiet_hours, schedule_after, normalize_phone_e164


class TestQuietHours:
    """Тесты для функции is_in_quiet_hours"""
    
    def test_in_quiet_hours_night(self):
        """Тест: время в тихих часах (ночь)"""
        # 23:30 Челябинского времени - должно быть в тихих часах
        tz = pytz.timezone("Asia/Yekaterinburg")
        dt = tz.localize(datetime(2025, 1, 15, 23, 30))
        
        assert is_in_quiet_hours(dt, "Asia/Yekaterinburg", "22:00", "09:00") is True
    
    def test_in_quiet_hours_early_morning(self):
        """Тест: время в тихих часах (раннее утро)"""
        tz = pytz.timezone("Asia/Yekaterinburg")
        dt = tz.localize(datetime(2025, 1, 15, 7, 30))
        
        assert is_in_quiet_hours(dt, "Asia/Yekaterinburg", "22:00", "09:00") is True
    
    def test_not_in_quiet_hours_day(self):
        """Тест: время НЕ в тихих часах (день)"""
        tz = pytz.timezone("Asia/Yekaterinburg")
        dt = tz.localize(datetime(2025, 1, 15, 14, 30))
        
        assert is_in_quiet_hours(dt, "Asia/Yekaterinburg", "22:00", "09:00") is False
    
    def test_not_in_quiet_hours_boundary_end(self):
        """Тест: граничное время - конец тихих часов"""
        tz = pytz.timezone("Asia/Yekaterinburg")
        dt = tz.localize(datetime(2025, 1, 15, 9, 0))  # Ровно 09:00
        
        assert is_in_quiet_hours(dt, "Asia/Yekaterinburg", "22:00", "09:00") is False
    
    def test_in_quiet_hours_boundary_start(self):
        """Тест: граничное время - начало тихих часов"""
        tz = pytz.timezone("Asia/Yekaterinburg")
        dt = tz.localize(datetime(2025, 1, 15, 22, 0))  # Ровно 22:00
        
        assert is_in_quiet_hours(dt, "Asia/Yekaterinburg", "22:00", "09:00") is True
    
    def test_quiet_hours_utc_input(self):
        """Тест: входное время в UTC"""
        # 18:00 UTC = 23:00 Екатеринбург (UTC+5)
        dt_utc = pytz.UTC.localize(datetime(2025, 1, 15, 18, 0))
        
        assert is_in_quiet_hours(dt_utc, "Asia/Yekaterinburg", "22:00", "09:00") is True


class TestScheduleAfter:
    """Тесты для функции schedule_after"""
    
    def test_schedule_normal_hours(self):
        """Тест: планирование в обычные часы"""
        tz = pytz.timezone("Asia/Yekaterinburg")
        base_time = tz.localize(datetime(2025, 1, 15, 10, 0))  # 10:00
        
        result = schedule_after(base_time, 3, "Asia/Yekaterinburg", "22:00", "09:00")
        expected = tz.localize(datetime(2025, 1, 15, 13, 0))  # 13:00
        
        # Конвертируем в UTC для сравнения
        assert result == expected.astimezone(pytz.UTC).replace(tzinfo=None)
    
    def test_schedule_into_quiet_hours(self):
        """Тест: планирование попадает в тихие часы"""
        tz = pytz.timezone("Asia/Yekaterinburg")
        base_time = tz.localize(datetime(2025, 1, 15, 20, 0))  # 20:00
        
        # +3 часа = 23:00, что в тихих часах
        result = schedule_after(base_time, 3, "Asia/Yekaterinburg", "22:00", "09:00")
        
        # Должно перенестись на 09:00 следующего дня
        expected = tz.localize(datetime(2025, 1, 16, 9, 0))
        
        assert result == expected.astimezone(pytz.UTC).replace(tzinfo=None)
    
    def test_schedule_from_night_time(self):
        """Тест: планирование из ночного времени"""
        tz = pytz.timezone("Asia/Yekaterinburg")
        base_time = tz.localize(datetime(2025, 1, 15, 2, 0))  # 02:00 (тихие часы)
        
        # +1 час = 03:00, всё ещё в тихих часах
        result = schedule_after(base_time, 1, "Asia/Yekaterinburg", "22:00", "09:00")
        
        # Должно перенестись на 09:00 того же дня
        expected = tz.localize(datetime(2025, 1, 15, 9, 0))
        
        assert result == expected.astimezone(pytz.UTC).replace(tzinfo=None)
    
    def test_schedule_fractional_hours(self):
        """Тест: планирование с дробными часами"""
        tz = pytz.timezone("Asia/Yekaterinburg")
        base_time = tz.localize(datetime(2025, 1, 15, 10, 0))
        
        # +1.5 часа = 11:30
        result = schedule_after(base_time, 1.5, "Asia/Yekaterinburg", "22:00", "09:00")
        expected = tz.localize(datetime(2025, 1, 15, 11, 30))
        
        assert result == expected.astimezone(pytz.UTC).replace(tzinfo=None)


class TestNormalizePhone:
    """Тесты для функции normalize_phone_e164"""
    
    def test_russian_mobile_8(self):
        """Тест: российский номер с 8"""
        assert normalize_phone_e164("8-912-345-67-89") == "+79123456789"
    
    def test_russian_mobile_7(self):
        """Тест: российский номер с 7"""
        assert normalize_phone_e164("7-912-345-67-89") == "+79123456789"
    
    def test_russian_mobile_9(self):
        """Тест: российский номер с 9 (без кода страны)"""
        assert normalize_phone_e164("912-345-67-89") == "+79123456789"
    
    def test_international_format(self):
        """Тест: уже международный формат"""
        assert normalize_phone_e164("+79123456789") == "+79123456789"
    
    def test_with_spaces_and_brackets(self):
        """Тест: номер со скобками и пробелами"""
        assert normalize_phone_e164("+7 (912) 345-67-89") == "+79123456789"
    
    def test_invalid_short_number(self):
        """Тест: слишком короткий номер"""
        assert normalize_phone_e164("123") is None
    
    def test_empty_input(self):
        """Тест: пустой ввод"""
        assert normalize_phone_e164("") is None
        assert normalize_phone_e164(None) is None
    
    def test_letters_in_number(self):
        """Тест: буквы в номере (должны удаляться)"""
        assert normalize_phone_e164("8abc912def345gh67ij89") == "+79123456789"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
