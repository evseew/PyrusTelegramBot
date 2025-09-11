"""
Клиент для работы с Pyrus API (v4).

Задачи клиента:
- авторизация и получение access_token
- чтение метаданных формы (имя формы, список полей)
- постраничное чтение реестра формы (только открытые задачи)

Примечание по URL: используем PYRUS_API_URL из .env (например,
"https://api.pyrus.com/v4/"), безопасно склеиваем пути без
зависимости от завершающего слэша.
"""

from __future__ import annotations

import os
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx


def _join_url(base: str, path: str) -> str:
    base = base or "https://api.pyrus.com/v4/"
    if not base.endswith('/'):
        base += '/'
    if path.startswith('/'):
        path = path[1:]
    return base + path


class PyrusClient:
    """
    Асинхронный минимальный клиент Pyrus.
    """

    def __init__(self) -> None:
        self.base_url: str = os.getenv("PYRUS_API_URL", "https://api.pyrus.com/v4/")
        self.login: Optional[str] = os.getenv("PYRUS_LOGIN")
        self.security_key: Optional[str] = os.getenv("PYRUS_SECURITY_KEY")
        self._access_token: Optional[str] = None

    async def _auth(self) -> Optional[str]:
        if not self.login or not self.security_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    _join_url(self.base_url, "auth"),
                    json={"login": self.login, "security_key": self.security_key},
                )
                if resp.status_code != 200:
                    return None
                token = resp.json().get("access_token")
                self._access_token = token
                return token
        except Exception:
            return None

    async def get_token(self) -> Optional[str]:
        if self._access_token:
            return self._access_token
        return await self._auth()

    async def get_form_meta(self, form_id: int) -> Optional[Dict[str, Any]]:
        token = await self.get_token()
        if not token:
            return None
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    _join_url(self.base_url, f"forms/{form_id}"),
                    headers={"Authorization": f"Bearer {token}"},
                )
                if resp.status_code != 200:
                    return None
                return resp.json()
        except Exception:
            return None

    async def iter_register_tasks(
        self, form_id: int, include_archived: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Итерация по задачам реестра формы. Возвращает объекты задач
        (элементы массива "tasks"). Пропускаем архивные по include_archived.
        """
        token = await self.get_token()
        if not token:
            return
        cursor: Optional[str] = None

        while True:
            try:
                params = {"include_archived": str(include_archived).lower()}
                if cursor:
                    params["cursor"] = cursor

                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.get(
                        _join_url(self.base_url, f"forms/{form_id}/register"),
                        headers={"Authorization": f"Bearer {token}"},
                        params=params,
                    )
                if resp.status_code != 200:
                    return
                data = resp.json()

                # Pyrus для реестра возвращает поле "tasks"
                tasks: List[Dict[str, Any]] = data.get("tasks") or data.get("items") or []
                for t in tasks:
                    yield t

                cursor = data.get("next_cursor")
                if not cursor:
                    break
            except Exception:
                break


