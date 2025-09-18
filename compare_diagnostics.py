#!/usr/bin/env python3
"""
Сравнение результатов диагностики между двумя машинами
Помогает выявить различия в конфигурации между рабочей и проблемной системами
"""
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple

class DiagnosticsComparator:
    """Класс для сравнения результатов диагностики"""
    
    def __init__(self):
        self.differences = []
        self.similarities = []
        self.recommendations = []
    
    def load_report(self, file_path: str) -> Dict[str, Any]:
        """Загрузка отчета диагностики из JSON файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Ошибка загрузки {file_path}: {e}")
            sys.exit(1)
    
    def compare_values(self, key: str, value1: Any, value2: Any, path: str = "") -> None:
        """Рекурсивное сравнение значений"""
        current_path = f"{path}.{key}" if path else key
        
        if isinstance(value1, dict) and isinstance(value2, dict):
            # Сравниваем словари
            all_keys = set(value1.keys()) | set(value2.keys())
            for k in all_keys:
                if k in value1 and k in value2:
                    self.compare_values(k, value1[k], value2[k], current_path)
                elif k in value1:
                    self.differences.append({
                        "path": f"{current_path}.{k}",
                        "type": "missing_in_machine2",
                        "machine1": value1[k],
                        "machine2": None
                    })
                else:
                    self.differences.append({
                        "path": f"{current_path}.{k}",
                        "type": "missing_in_machine1", 
                        "machine1": None,
                        "machine2": value2[k]
                    })
        
        elif isinstance(value1, list) and isinstance(value2, list):
            # Сравниваем списки
            if set(value1) != set(value2):
                self.differences.append({
                    "path": current_path,
                    "type": "list_difference",
                    "machine1": value1,
                    "machine2": value2,
                    "only_in_1": list(set(value1) - set(value2)),
                    "only_in_2": list(set(value2) - set(value1))
                })
            else:
                self.similarities.append({
                    "path": current_path,
                    "value": value1
                })
        
        else:
            # Сравниваем простые значения
            if value1 != value2:
                self.differences.append({
                    "path": current_path,
                    "type": "value_difference",
                    "machine1": value1,
                    "machine2": value2
                })
            else:
                self.similarities.append({
                    "path": current_path,
                    "value": value1
                })
    
    def analyze_critical_differences(self, report1: Dict, report2: Dict) -> None:
        """Анализ критически важных различий"""
        
        # Различия в переменных окружения
        env1 = report1.get("environment", {})
        env2 = report2.get("environment", {})
        
        missing1 = set(env1.get("missing_required", []))
        missing2 = set(env2.get("missing_required", []))
        
        if missing1 != missing2:
            only_missing_1 = missing1 - missing2
            only_missing_2 = missing2 - missing1
            
            if only_missing_1:
                self.recommendations.append(f"🔧 На машине 1 отсутствуют переменные: {', '.join(only_missing_1)}")
            if only_missing_2:
                self.recommendations.append(f"🔧 На машине 2 отсутствуют переменные: {', '.join(only_missing_2)}")
        
        # Различия в пакетах
        pkg1 = report1.get("packages", {})
        pkg2 = report2.get("packages", {})
        
        missing_pkg1 = set(pkg1.get("missing", []))
        missing_pkg2 = set(pkg2.get("missing", []))
        
        if missing_pkg1 != missing_pkg2:
            only_missing_pkg1 = missing_pkg1 - missing_pkg2
            only_missing_pkg2 = missing_pkg2 - missing_pkg1
            
            if only_missing_pkg1:
                self.recommendations.append(f"📦 На машине 1 отсутствуют пакеты: {', '.join(only_missing_pkg1)}")
            if only_missing_pkg2:
                self.recommendations.append(f"📦 На машине 2 отсутствуют пакеты: {', '.join(only_missing_pkg2)}")
        
        # Различия в версиях пакетов
        installed1 = pkg1.get("installed", {})
        installed2 = pkg2.get("installed", {})
        
        version_diffs = []
        for pkg_name in set(installed1.keys()) & set(installed2.keys()):
            if installed1[pkg_name] != installed2[pkg_name]:
                version_diffs.append(f"{pkg_name}: {installed1[pkg_name]} vs {installed2[pkg_name]}")
        
        if version_diffs:
            self.recommendations.append(f"📦 Различия в версиях пакетов: {'; '.join(version_diffs[:5])}")
        
        # Различия в Python версиях
        py1 = report1.get("python_info", {}).get("version_info")
        py2 = report2.get("python_info", {}).get("version_info")
        
        if py1 != py2:
            self.recommendations.append(f"🐍 Разные версии Python: {py1} vs {py2}")
        
        # Различия в API подключениях
        api1 = report1.get("api_connectivity", {})
        api2 = report2.get("api_connectivity", {})
        
        for api_name in set(api1.keys()) | set(api2.keys()):
            status1 = api1.get(api_name, {}).get("success", False)
            status2 = api2.get(api_name, {}).get("success", False)
            
            if status1 != status2:
                working = "машине 1" if status1 else "машине 2"
                broken = "машине 2" if status1 else "машине 1"
                self.recommendations.append(f"🌐 {api_name}: работает на {working}, не работает на {broken}")
        
        # Различия в импортах
        imp1 = report1.get("imports", {})
        imp2 = report2.get("imports", {})
        
        failed1 = set(imp1.get("failed_external", []) + imp1.get("failed_project", []))
        failed2 = set(imp2.get("failed_external", []) + imp2.get("failed_project", []))
        
        if failed1 != failed2:
            only_failed1 = failed1 - failed2
            only_failed2 = failed2 - failed1
            
            if only_failed1:
                self.recommendations.append(f"📥 На машине 1 не импортируются: {', '.join(only_failed1)}")
            if only_failed2:
                self.recommendations.append(f"📥 На машине 2 не импортируются: {', '.join(only_failed2)}")
    
    def compare_reports(self, report1: Dict, report2: Dict, machine1_name: str, machine2_name: str) -> None:
        """Основная функция сравнения отчетов"""
        print(f"🔍 СРАВНЕНИЕ ДИАГНОСТИКИ")
        print("=" * 60)
        print(f"Машина 1: {machine1_name}")
        print(f"Машина 2: {machine2_name}")
        print(f"Время сравнения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Анализируем критически важные различия
        self.analyze_critical_differences(report1, report2)
        
        # Сравниваем общие секции
        sections_to_compare = [
            "system_info",
            "python_info", 
            "environment",
            "packages",
            "files",
            "api_connectivity",
            "imports",
            "database",
            "network"
        ]
        
        for section in sections_to_compare:
            if section in report1 and section in report2:
                self.compare_values(section, report1[section], report2[section])
        
        # Выводим результаты
        self.print_comparison_results(machine1_name, machine2_name)
    
    def print_comparison_results(self, machine1_name: str, machine2_name: str) -> None:
        """Вывод результатов сравнения"""
        
        # Критические различия
        if self.recommendations:
            print(f"\n🚨 КРИТИЧЕСКИЕ РАЗЛИЧИЯ ({len(self.recommendations)}):")
            print("-" * 50)
            for i, rec in enumerate(self.recommendations, 1):
                print(f"{i:2d}. {rec}")
        
        # Группируем различия по типам
        env_diffs = [d for d in self.differences if d["path"].startswith("environment")]
        pkg_diffs = [d for d in self.differences if d["path"].startswith("packages")]
        system_diffs = [d for d in self.differences if d["path"].startswith("system_info")]
        other_diffs = [d for d in self.differences if not any(d["path"].startswith(p) for p in ["environment", "packages", "system_info"])]
        
        # Различия в переменных окружения
        if env_diffs:
            print(f"\n🔐 РАЗЛИЧИЯ В ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ({len(env_diffs)}):")
            print("-" * 50)
            for diff in env_diffs[:10]:  # Показываем только первые 10
                path = diff["path"].replace("environment.", "")
                if diff["type"] == "value_difference":
                    print(f"  📝 {path}")
                    print(f"     {machine1_name}: {diff['machine1']}")
                    print(f"     {machine2_name}: {diff['machine2']}")
                elif diff["type"] == "list_difference":
                    print(f"  📝 {path}")
                    if diff.get("only_in_1"):
                        print(f"     Только в {machine1_name}: {diff['only_in_1']}")
                    if diff.get("only_in_2"):
                        print(f"     Только в {machine2_name}: {diff['only_in_2']}")
        
        # Различия в пакетах
        if pkg_diffs:
            print(f"\n📦 РАЗЛИЧИЯ В ПАКЕТАХ ({len(pkg_diffs)}):")
            print("-" * 50)
            for diff in pkg_diffs[:10]:
                path = diff["path"].replace("packages.", "")
                if diff["type"] == "value_difference":
                    print(f"  📝 {path}: {diff['machine1']} vs {diff['machine2']}")
                elif diff["type"] == "list_difference" and diff.get("only_in_1"):
                    print(f"  📝 {path} только в {machine1_name}: {diff['only_in_1']}")
                elif diff["type"] == "list_difference" and diff.get("only_in_2"):
                    print(f"  📝 {path} только в {machine2_name}: {diff['only_in_2']}")
        
        # Системные различия
        if system_diffs:
            print(f"\n🖥️ СИСТЕМНЫЕ РАЗЛИЧИЯ ({len(system_diffs)}):")
            print("-" * 50)
            for diff in system_diffs[:10]:
                path = diff["path"].replace("system_info.", "")
                if diff["type"] == "value_difference":
                    print(f"  📝 {path}: {diff['machine1']} vs {diff['machine2']}")
        
        # Прочие различия
        if other_diffs:
            print(f"\n🔧 ПРОЧИЕ РАЗЛИЧИЯ ({len(other_diffs)}):")
            print("-" * 50)
            for diff in other_diffs[:5]:
                if diff["type"] == "value_difference":
                    print(f"  📝 {diff['path']}: {diff['machine1']} vs {diff['machine2']}")
        
        # Общая статистика
        print(f"\n📊 СТАТИСТИКА СРАВНЕНИЯ:")
        print("-" * 50)
        print(f"  📝 Всего различий: {len(self.differences)}")
        print(f"  ✅ Одинаковых параметров: {len(self.similarities)}")
        print(f"  🚨 Критических проблем: {len(self.recommendations)}")
        
        # Приоритетные действия
        print(f"\n🎯 ПРИОРИТЕТНЫЕ ДЕЙСТВИЯ:")
        print("-" * 50)
        if not self.recommendations:
            print("  ✅ Критических различий не найдено!")
            print("  📝 Проверьте логи приложения и детали различий выше")
        else:
            print("  1. Исправьте критические различия (список выше)")
            print("  2. Синхронизируйте версии пакетов")
            print("  3. Проверьте переменные окружения")
            print("  4. Повторите диагностику")
    
    def save_comparison_report(self, filename: str) -> None:
        """Сохранение отчета сравнения"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "differences": self.differences,
            "similarities": len(self.similarities),
            "recommendations": self.recommendations,
            "summary": {
                "total_differences": len(self.differences),
                "critical_issues": len(self.recommendations)
            }
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n💾 Отчет сравнения сохранен в {filename}")
        except Exception as e:
            print(f"\n❌ Ошибка сохранения отчета: {e}")

def main():
    parser = argparse.ArgumentParser(description="Сравнение результатов диагностики PyrusTelegramBot")
    parser.add_argument("report1", help="Путь к первому отчету (JSON)")
    parser.add_argument("report2", help="Путь к второму отчету (JSON)")
    parser.add_argument("--name1", default="Машина 1", help="Название первой машины")
    parser.add_argument("--name2", default="Машина 2", help="Название второй машины")
    parser.add_argument("--output", help="Файл для сохранения отчета сравнения")
    
    args = parser.parse_args()
    
    # Проверяем существование файлов
    if not Path(args.report1).exists():
        print(f"❌ Файл {args.report1} не найден")
        sys.exit(1)
    
    if not Path(args.report2).exists():
        print(f"❌ Файл {args.report2} не найден")
        sys.exit(1)
    
    # Создаем компаратор и сравниваем
    comparator = DiagnosticsComparator()
    
    print("📖 Загрузка отчетов...")
    report1 = comparator.load_report(args.report1)
    report2 = comparator.load_report(args.report2)
    
    comparator.compare_reports(report1, report2, args.name1, args.name2)
    
    # Сохраняем отчет если указан файл
    if args.output:
        comparator.save_comparison_report(args.output)
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

