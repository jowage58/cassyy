"""
Central Authentication Service (CAS) client
"""
import dataclasses
import logging
import urllib.parse
import urllib.request
import xml.etree.ElementTree
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def _fetch_url(url: str, timeout: float = 10.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as f:
        return f.read()


class CASError(Exception):
    def __init__(self, error_code: str, *args) -> None:
        super().__init__(error_code, *args)
        self.error_code = error_code


class CASInvalidServiceError(CASError):
    def __init__(self, error_code: str, *args) -> None:
        super().__init__(error_code, *args)


class CASInvalidTicketError(CASError):
    def __init__(self, error_code: str, *args) -> None:
        super().__init__(error_code, *args)


@dataclasses.dataclass
class CASUser:
    user: str
    attributes: Dict[str, str] = dataclasses.field(default_factory=dict)

    def asdict(self) -> Dict[str, ...]:
        return dataclasses.asdict(self)


class CASClient:
    CAS_NS = {'cas': 'http://www.yale.edu/tp/cas'}

    def __init__(
            self,
            login_url: str,
            logout_url: str,
            validate_url: str,
            *,
            timeout: float = 10.0,
    ) -> None:
        self.login_url = login_url
        self.logout_url = logout_url
        self.validate_url = validate_url
        self.timeout = timeout

    @classmethod
    def from_base_url(
            cls,
            base_url: str,
            *,
            login_path: str = '/login',
            logout_path: str = '/logout',
            validate_path: str = '/p3/serviceValidate',
            timeout: float = 10.0,
    ) -> 'CASClient':
        return cls(
            login_url=urllib.parse.urljoin(base_url, login_path),
            logout_url=urllib.parse.urljoin(base_url, logout_path),
            validate_url=urllib.parse.urljoin(base_url, validate_path),
            timeout=timeout,
        )

    def validate(
            self,
            service_url: str,
            ticket: str,
            *,
            timeout: Optional[float] = None,
    ) -> CASUser:
        target_validate = self.build_validate_url(service_url, ticket)
        if timeout is None:
            timeout = self.timeout
        logger.debug('Validating %s', target_validate)
        try:
            cas_response = _fetch_url(target_validate, timeout=timeout)
        except Exception as exc:
            raise CASError(repr(exc))
        else:
            logger.debug('Response:\n%s', cas_response)
            return self.parse_cas_response(cas_response)

    def build_login_url(
            self,
            service: str,
            *,
            callback_post: bool = False,
    ) -> str:
        encoded_service = urllib.parse.quote_plus(service)
        method = 'method=POST&' if callback_post else ''
        return f'{self.login_url}?{method}service={encoded_service}'

    def build_logout_url(self, service: Optional[str] = None) -> str:
        if service is None:
            return self.logout_url
        encoded_service = urllib.parse.quote_plus(service)
        return f'{self.logout_url}?service={encoded_service}'

    def build_validate_url(self, service: str, ticket: str) -> str:
        encoded_service = urllib.parse.quote_plus(service)
        return f'{self.validate_url}?service={encoded_service}&ticket={ticket}'

    def parse_cas_response(self, cas_response: str) -> CASUser:
        try:
            root = xml.etree.ElementTree.fromstring(cas_response)
        except Exception as exc:
            raise CASError('INVALID_RESPONSE', repr(exc)) from exc
        else:
            return self.parse_cas_xml(root)

    def parse_cas_xml(self, root: xml.etree.ElementTree.Element) -> CASUser:
        user_elem = root.find('cas:authenticationSuccess/cas:user',
                              self.CAS_NS)
        if user_elem is not None:
            attr_elem = root.find('cas:authenticationSuccess/cas:attributes',
                                  self.CAS_NS)
            return self.parse_cas_xml_user(user_elem, attr_elem)
        self.parse_cas_xml_error(root)

    def parse_cas_xml_user(
            self,
            user_elem: xml.etree.ElementTree.Element,
            attr_elem: Optional[xml.etree.ElementTree.Element],
    ) -> CASUser:
        user = user_elem.text
        if attr_elem is not None:
            tag_ns = '{' + self.CAS_NS['cas'] + '}'
            user_attrs = {
                e.tag.replace(tag_ns, '', 1): e.text
                for e in attr_elem
            }
        else:
            user_attrs = {}
        return CASUser(user=user, attributes=user_attrs)

    def parse_cas_xml_error(
            self,
            root: xml.etree.ElementTree.Element,
    ) -> None:
        error_code = 'Unknown'
        error_elem = root.find('cas:authenticationFailure', self.CAS_NS)
        if error_elem is not None:
            error_code = error_elem.attrib.get('code', error_code)
            error_text = error_elem.text
            if error_code == 'INVALID_TICKET':
                raise CASInvalidTicketError(error_code, error_text)
            elif error_code == 'INVALID_SERVICE':
                raise CASInvalidServiceError(error_code, error_text)
        raise CASError(error_code)

    def __repr__(self) -> str:
        return (
            'CASClient('
            f'login_url={self.login_url!r}, '
            f'logout_url={self.logout_url!r}, '
            f'validate_url={self.validate_url!r}, '
            f'timeout={self.timeout!r}'
            ')'
        )
