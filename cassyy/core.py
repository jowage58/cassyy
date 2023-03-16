"""
Central Authentication Service (CAS) client
"""
import asyncio
import dataclasses
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree
from collections.abc import Awaitable, Callable
from typing import Optional, Union, cast

logger = logging.getLogger(__name__)

CAS_NS = {"cas": "http://www.yale.edu/tp/cas"}
CAS_VALIDATE_ENCODING = "utf-8"
CAS_VALIDATE_TIMEOUT = 10.0

HTTPGetFunc = Callable[[str, float], str]
AsyncHTTPGetFunc = Callable[[str, float], Awaitable[str]]


class CASError(Exception):
    def __init__(self, error_code: str, *args: Optional[str]) -> None:
        super().__init__(error_code, *args)
        self.error_code = error_code


class CASInvalidServiceError(CASError):
    def __init__(self, error_code: str, *args: Optional[str]) -> None:
        super().__init__(error_code, *args)


class CASInvalidTicketError(CASError):
    def __init__(self, error_code: str, *args: Optional[str]) -> None:
        super().__init__(error_code, *args)


@dataclasses.dataclass
class CASUser:
    userid: str
    attributes: dict[str, Optional[str]] = dataclasses.field(default_factory=dict)

    def asdict(self) -> dict[str, Union[str, dict[str, str]]]:
        return dataclasses.asdict(self)


class BaseCASClient:
    def __init__(self, login_url: str, logout_url: str, validate_url: str) -> None:
        self.login_url = login_url
        self.logout_url = logout_url
        self.validate_url = validate_url

    def build_login_url(
        self,
        service: str,
        *,
        callback_post: bool = False,
        **kwargs: str,
    ) -> str:
        params = {"service": service, **kwargs}
        if callback_post:
            params["method"] = "POST"
        qs = urllib.parse.urlencode(params)
        return f"{self.login_url}?{qs}"

    def build_logout_url(self, service: Optional[str] = None, **kwargs: str) -> str:
        if service is None:
            if not kwargs:
                return self.logout_url
            params = kwargs
        else:
            params = {"service": service, **kwargs}
        qs = urllib.parse.urlencode(params)
        return f"{self.logout_url}?{qs}"

    def build_validate_url(self, service: str, ticket: str, **kwargs: str) -> str:
        params = {"service": service, "ticket": ticket, **kwargs}
        qs = urllib.parse.urlencode(params)
        return f"{self.validate_url}?{qs}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"login_url={self.login_url!r}, "
            f"logout_url={self.logout_url!r}, "
            f"validate_url={self.validate_url!r}"
            ")"
        )


class CASClient(BaseCASClient):
    def __init__(
        self,
        login_url: str,
        logout_url: str,
        validate_url: str,
        http_get_func: Optional[HTTPGetFunc] = None,
    ) -> None:
        super().__init__(login_url, logout_url, validate_url)
        if http_get_func is None:
            self._http_get = cast(HTTPGetFunc, _http_get)
        else:
            self._http_get = http_get_func

    @classmethod
    def from_base_url(
        cls,
        base_url: str,
        *,
        login_path: str = "/login",
        logout_path: str = "/logout",
        validate_path: str = "/p3/serviceValidate",
        http_get_func: Optional[HTTPGetFunc] = None,
    ) -> "CASClient":
        return cls(
            login_url=urllib.parse.urljoin(base_url, login_path),
            logout_url=urllib.parse.urljoin(base_url, logout_path),
            validate_url=urllib.parse.urljoin(base_url, validate_path),
            http_get_func=http_get_func,
        )

    def validate(
        self,
        service_url: str,
        ticket: str,
        *,
        timeout: Optional[float] = None,
        **kwargs: str,
    ) -> CASUser:
        if timeout is None:
            timeout = CAS_VALIDATE_TIMEOUT
        target_validate = self.build_validate_url(service_url, ticket, **kwargs)
        logger.debug("Validating %s", target_validate)
        try:
            resp_text = self._http_get(target_validate, timeout)
        except Exception as exc:
            raise CASError(repr(exc)) from exc
        else:
            logger.debug("Response:\n%s", resp_text)
            return parse_cas_response(resp_text)


class AsyncCASClient(BaseCASClient):
    def __init__(
        self,
        login_url: str,
        logout_url: str,
        validate_url: str,
        http_get_func: Optional[AsyncHTTPGetFunc] = None,
    ) -> None:
        super().__init__(login_url, logout_url, validate_url)
        if http_get_func is None:
            self._http_get = cast(AsyncHTTPGetFunc, _async_http_get)
        else:
            self._http_get = http_get_func

    @classmethod
    def from_base_url(
        cls,
        base_url: str,
        *,
        login_path: str = "/login",
        logout_path: str = "/logout",
        validate_path: str = "/p3/serviceValidate",
        http_get_func: Optional[AsyncHTTPGetFunc] = None,
    ) -> "AsyncCASClient":
        return cls(
            login_url=urllib.parse.urljoin(base_url, login_path),
            logout_url=urllib.parse.urljoin(base_url, logout_path),
            validate_url=urllib.parse.urljoin(base_url, validate_path),
            http_get_func=http_get_func,
        )

    async def validate(
        self,
        service_url: str,
        ticket: str,
        *,
        timeout: Optional[float] = None,
        **kwargs: str,
    ) -> CASUser:
        if timeout is None:
            timeout = CAS_VALIDATE_TIMEOUT
        target_validate = self.build_validate_url(service_url, ticket, **kwargs)
        logger.debug("Validating %s", target_validate)
        try:
            resp_text = await self._http_get(target_validate, timeout)
        except Exception as exc:
            raise CASError(repr(exc)) from exc
        else:
            logger.debug("Response:\n%s", resp_text)
            return parse_cas_response(resp_text)


def parse_cas_response(cas_response: str) -> CASUser:
    try:
        root = xml.etree.ElementTree.fromstring(cas_response)
    except Exception as exc:
        raise CASError("INVALID_RESPONSE", repr(exc)) from exc
    else:
        return parse_cas_xml(root)


def parse_cas_xml(root: xml.etree.ElementTree.Element) -> CASUser:
    user_elem = root.find("cas:authenticationSuccess/cas:user", CAS_NS)
    if user_elem is not None:
        attr_elem = root.find("cas:authenticationSuccess/cas:attributes", CAS_NS)
        return parse_cas_xml_user(user_elem, attr_elem)
    raise parse_cas_xml_error(root)


def parse_cas_xml_user(
    user_elem: xml.etree.ElementTree.Element,
    attr_elem: Optional[xml.etree.ElementTree.Element],
) -> CASUser:
    if user_elem.text is None:
        raise CASError("USERNAME_NOT_IN_RESPONSE")
    cas_user = CASUser(userid=user_elem.text)
    if attr_elem is not None:
        tag_ns = "{" + CAS_NS["cas"] + "}"
        for e in attr_elem:
            attr_name = e.tag.replace(tag_ns, "", 1)
            cas_user.attributes[attr_name] = e.text
    return cas_user


def parse_cas_xml_error(root: xml.etree.ElementTree.Element) -> CASError:
    error_code = "Unknown"
    error_elem = root.find("cas:authenticationFailure", CAS_NS)
    if error_elem is not None:
        error_code = error_elem.attrib.get("code", error_code)
        error_text = error_elem.text
        if error_code == "INVALID_TICKET":
            return CASInvalidTicketError(error_code, error_text)
        if error_code == "INVALID_SERVICE":
            return CASInvalidServiceError(error_code, error_text)
    return CASError(error_code)


def _http_get(url: str, timeout: float = 10.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as f:
        data = cast(bytes, f.read())
        return data.decode(CAS_VALIDATE_ENCODING)


async def _async_http_get(url: str, timeout: float = 10.0) -> str:
    fut = asyncio.to_thread(_http_get, url, timeout)
    return await asyncio.wait_for(fut, timeout)
