"""Main Api abstract class and a response class to keep the information"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import aiohttp

logger = logging.getLogger("api")


@dataclass(init=False)
class ApiResponse:
    """Proxy class for library responses. Used to make the _request method
    agnostic to the library it uses.
    """

    def __init__(self, resp: aiohttp.ClientResponse) -> None:
        """
        Args:
            resp (aiohttp.ClientResponse): HTTP response from aiohttp client.
        """
        self._resp = resp
        self.status = self._resp.status
        self.json: Optional[Dict[str, Any]] = None
        self.is_ok = 200 <= self.status < 300
        self.headers = self._resp.headers

    async def get_info(self) -> None:
        """Load async information from the response object"""
        self.json = await self._resp.json()


class Api:
    """Abstract class to make an agnostic implementation of HTTP requests."""

    api_url: Optional[str] = None
    _header = {"Content-type": "application/json", "Accepts": "application/json"}

    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 10,  # Default timeout of 60 seconds
    ) -> ApiResponse:
        """
        Send a request to the API and return the response.

        Args:
            method (str): HTTP method to use.
            path (str): URL path of the endpoint.
            data (Optional[Dict[str, Any]]): Request body in JSON format.
            headers (Optional[Dict[str, str]]): Headers to include in the request.

        Returns:
            ApiResponse: Response from the API.
        """
        if headers is None:
            headers = {}
        headers = dict(self._header, **headers)

        # Create a ClientTimeout object
        timeout = aiohttp.ClientTimeout(total=timeout_seconds)

        async with aiohttp.ClientSession(
            # connector=aiohttp.TCPConnector(ssl=False) # TESTING
        ) as session:
            logger.debug("Request to %s%s with data: %s", self.api_url, path, str(data))
            async with session.request(
                method,
                f"{self.api_url}{path}",
                json=data,
                headers=headers,
                timeout=timeout,
            ) as resp:
                if not resp.ok:
                    raise UnsuccessfulResponse(resp.status)
                pars = ApiResponse(resp)
                await pars.get_info()
                return pars

    async def _get(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ApiResponse:
        """Alias for sending a GET request.

        Args:
            path (str): URL path of the endpoint.
            data (Optional[Dict[str, Any]]): Request body in JSON format.
            headers (Optional[Dict[str, str]]): Headers to include in the request.

        Returns:
            ApiResponse: Response from the API.
        """
        return await self._request("GET", path, data, headers)

    async def _post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ApiResponse:
        """Alias for sending a POST request.

        Args:
            path (str): URL path of the endpoint.
            data (Optional[Dict[str, Any]]): Request body in JSON format.
            headers (Optional[Dict[str, str]]): Headers to include in the request.

        Returns:
            ApiResponse: Response from the API.
        """
        return await self._request("POST", path, data, headers)

    async def _put(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ApiResponse:
        """Alias for sending a PUT request.

        Args:
            path (str): URL path of the endpoint.
            data (Optional[Dict[str, Any]]): Request body in JSON format.
            headers (Optional[Dict[str, str]]): Headers to include in the request.

        Returns:
            ApiResponse: Response from the API.
        """
        return await self._request("PUT", path, data, headers)

    async def _delete(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> ApiResponse:
        """Alias for sending a DELETE request.

        Args:
            path (str): URL path of the endpoint.
            data (Optional[Dict[str, Any]]): Request body in JSON format.
            headers (Optional[Dict[str, str]]): Headers to include in the request.

        Returns:
            ApiResponse: Response from the API.
        """
        return await self._request("DELETE", path, data, headers)


class UnsuccessfulResponse(Exception):
    """Used when the response is not 200"""
