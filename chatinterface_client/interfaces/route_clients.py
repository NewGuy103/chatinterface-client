import json
import httpx
from ..config import simple_log_setup

logger = simple_log_setup()


async def make_request(
    client: httpx.AsyncClient, 
    method: str, url: str,
    **kwargs
) -> tuple | list | dict:
    try:
        res: httpx.Response = await client.request(method, url, **kwargs)
        res.raise_for_status()

        json_res: dict = res.json()
    except httpx.InvalidURL as e:
        logger.debug("Invalid URL passed to httpx:", exc_info=e)
        return ("INVALID_URL", e)
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.warning("Request failed to network issues:", exc_info=e)
        return ("NETWORK_ERROR", e)
    except httpx.HTTPStatusError as e:
        logger.warning("Request failed with HTTP error:", exc_info=e)
        return ("HTTP_STATUS_ERROR", e)
    except json.JSONDecodeError as e:
        logger.warning("Response is not JSON:", exc_info=e)
        return ("INVALID_JSON", e)
    except httpx.HTTPError as e:
        logger.warning("Other request error occured:", exc_info=e)
        return ("HTTP_ERROR", e)
    except Exception as e:
        logger.exception("Unexpected error during request:")
        return ("ERROR", e)

    logger.debug("Request to URL '%s' completed", url)
    return json_res


class HTTPClient:
    def __init__(self, host: str, httpx_client_kwargs: dict) -> None:
        self.client: httpx.AsyncClient = httpx.AsyncClient(**httpx_client_kwargs)
        self.http_host: str = host

    async def wrapped_http_request(self, path: str, method: str, **kwargs: dict) -> tuple:
        url: str = f"{self.http_host}{path}"
        try:
            res: httpx.Response = await self.client.request(method, url, **kwargs)
            res.raise_for_status()

            res_json: dict = res.json()
        except httpx.InvalidURL as e:
            logger.debug("Invalid server URL '%s':", exc_info=e)
            return ("INVALID_URL", e)
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            logger.info("Request failed with network error:", exc_info=e)
            return ("NETWORK_ERROR", e)
        except httpx.HTTPStatusError as e:
            logger.info("Request failed with HTTP error:", exc_info=e)
            return ("HTTP_STATUS_ERROR", e)
        except json.JSONDecodeError as e:
            logger.info("Response is not JSON:", exc_info=e)
            return ("INVALID_JSON", e)
        except httpx.HTTPError as e:
            logger.warning("Other request error occured:", exc_info=e)
            return ("HTTP_ERROR", e)
        except Exception as e:
            logger.exception("Unexpected error during request:")
            return ("ERROR", e)

        return (res_json, None)


class TokenRouteClient:
    def __init__(self, server_host: str, client: httpx.AsyncClient) -> None:
        self.host: str = server_host
        self.client: httpx.AsyncClient = client
    
    async def create_token(self, username: str, password: str, endpoint: str = "/token/") -> tuple | str:
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        if not isinstance(password, str):
            raise TypeError("password is not a string")

        url: str = f"{self.host}{endpoint}"
        data: dict = {
            'username': username,
            'password': password
        }
        token_data: tuple | dict = await make_request(self.client, "POST", url, data=data)

        if isinstance(token_data, tuple):
            return token_data  # let caller handle make_request exception

        token: str = token_data.get('token')
        return token

    async def show_token_info(self, session_token: str, endpoint: str = "/token/info") -> tuple | dict:
        if not isinstance(session_token, str):
            raise TypeError("session token is not a string")

        url: str = f"{self.host}{endpoint}"
        headers: dict = {"Authorization": session_token}

        token_info: tuple | dict = await make_request(self.client, "GET", url, headers=headers)
        return token_info

    async def revoke_token(self, session_token: str, endpoint: str = "/token/revoke") -> tuple | str:
        if not isinstance(session_token, str):
            raise TypeError("session token is not a string")

        url: str = f"{self.host}{endpoint}"
        headers: dict = {"Authorization": session_token}

        revoke_success: tuple | dict = await make_request(self.client, "POST", url, headers=headers)
        if isinstance(revoke_success, tuple):
            return revoke_success
        
        return 0


class ChatsRouteClient:
    def __init__(self, server_host: str, client: httpx.AsyncClient, session_token: str = '') -> None:
        self.host: str = server_host
        self.client: httpx.AsyncClient = client

        if 'Authorization' not in self.client.headers:
            self.client.headers['Authorization'] = session_token

    async def get_contacts(self, endpoint: str = '/chats/recipients') -> tuple | set[str]:
        url: str = f"{self.host}{endpoint}"
        contacts: tuple | list[str] = await make_request(self.client, "GET", url)

        if isinstance(contacts, tuple):
            return contacts
        
        contacts_set: set[str] = set(contacts)
        return contacts_set
    
    async def get_messages(
        self, contact: str, 
        amount: int, 
        endpoint: str = '/chats/messages'
    ) -> tuple | list[tuple[str, bytes, str]]:
        if not isinstance(contact, str):
            raise TypeError("contact is not a string")
        
        if not isinstance(amount, int):
            raise TypeError("amount is not an integer")

        url: str = f"{self.host}{endpoint}"
        params: dict = {'recipient': contact, 'amount': amount}
        messages: tuple | list[tuple[str, bytes, str]] = await make_request(
            self.client, "GET", 
            url, params=params
        )

        return messages

    async def check_user_exists(self, username: str, endpoint: str = '/chats/user-exists') -> tuple | bool:
        if not isinstance(username, str):
            raise TypeError("username is not a string")
        
        url: str = f"{self.host}{endpoint}"
        params: dict = {'username': username}

        user_exists: tuple | bool = await make_request(self.client, "GET", url, params=params)
        return user_exists
