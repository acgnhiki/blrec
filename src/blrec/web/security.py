import secrets
from typing import Dict, Optional, Set

from fastapi import Header, Request, status
from fastapi.exceptions import HTTPException

api_key = ''

MAX_WHITELIST = 100
MAX_BLACKLIST = 100
MAX_ATTEMPTING_CLIENTS = 100
MAX_ATTEMPTS = 3
whitelist: Set[str] = set()
blacklist: Set[str] = set()
attempting_clients: Dict[str, int] = {}


async def authenticate(
    request: Request, x_api_key: Optional[str] = Header(None)
) -> None:
    assert api_key, 'api_key is required'

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='No api key'
        )

    assert request.client is not None, 'client should not be None'
    client_ip = request.client.host
    assert client_ip, 'client_ip is required'

    if client_ip in blacklist:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Blacklisted')
    if client_ip not in whitelist:
        if len(whitelist) >= MAX_WHITELIST or len(blacklist) >= MAX_BLACKLIST:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Max clients allowed in whitelist or blacklist ' 'will exceeded',
            )
        if len(attempting_clients) >= MAX_ATTEMPTING_CLIENTS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Max attempting clients allowed exceeded',
            )
        if client_ip not in attempting_clients:
            attempting_clients[client_ip] = 1
        else:
            attempting_clients[client_ip] += 1
        if attempting_clients[client_ip] > MAX_ATTEMPTS:
            del attempting_clients[client_ip]
            blacklist.add(client_ip)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Max api key attempts exceeded',
            )

    if not secrets.compare_digest(x_api_key, api_key):
        if client_ip in whitelist:
            whitelist.remove(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail='API key is invalid'
        )

    if client_ip in attempting_clients:
        del attempting_clients[client_ip]
    if client_ip not in whitelist:
        whitelist.add(client_ip)
