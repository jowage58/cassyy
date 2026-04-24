import pytest

from cassyy.core import (
    CASClient,
    CASError,
    CASInvalidServiceError,
    CASInvalidTicketError,
    parse_cas_response,
)

cas_login_url = "https://cas.local/login"
cas_logout_url = "https://cas.local/logout"
cas_validate_url = "https://cas.local/p3/serviceValidate"
test_service_url = "https://foo.org"


@pytest.fixture
def cas_client() -> CASClient:
    return CASClient(cas_login_url, cas_logout_url, cas_validate_url)


def test_from_base_url() -> None:
    c = CASClient.from_base_url("https://cas.local/")
    assert c.login_url == "https://cas.local/login"
    assert c.logout_url == "https://cas.local/logout"
    assert c.validate_url == "https://cas.local/p3/serviceValidate"


def test_from_base_url_with_alt_paths() -> None:
    c = CASClient.from_base_url(
        "https://cas.local/",
        login_path="foo",
        logout_path="bar/baz",
        validate_path="/qux",
    )
    assert c.login_url == "https://cas.local/foo"
    assert c.logout_url == "https://cas.local/bar/baz"
    assert c.validate_url == "https://cas.local/qux"


def test_parse_userid() -> None:
    s = """
    <cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
        <cas:authenticationSuccess>
            <cas:user>jdoe</cas:user>
        </cas:authenticationSuccess>
    </cas:serviceResponse>
    """
    assert parse_cas_response(s).userid == "jdoe"


def test_parse_non_xml() -> None:
    s = "jdoe"
    with pytest.raises(CASError, match="INVALID_RESPONSE") as cm:
        parse_cas_response(s)
    assert cm.value.error_code == "INVALID_RESPONSE"
    assert str(cm.value.args[1]) == "ParseError('syntax error: line 1, column 0')"


def test_parse_invalid_ticket() -> None:
    s = """
    <cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
        <cas:authenticationFailure code="INVALID_TICKET">
            Ticket &#39;ST-foo&#39; not recognized
        </cas:authenticationFailure>
    </cas:serviceResponse>
    """
    with pytest.raises(CASInvalidTicketError, match="INVALID_TICKET") as cm:
        parse_cas_response(s)
    assert cm.value.error_code == "INVALID_TICKET"


def test_parse_invalid_service() -> None:
    s = """
    <cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
        <cas:authenticationFailure code="INVALID_SERVICE">
            Ticket &#39;ST-338345-KTQdtsv9b5WKtfVfrahU-cas3&#39; does not match supplied service. '
            The original service was &#39;https://foo.org&#39; and the supplied service was &#39;https://foo2.org&#39;.
        </cas:authenticationFailure>
    </cas:serviceResponse>
    """
    with pytest.raises(CASInvalidServiceError) as cm:
        parse_cas_response(s)
    assert cm.value.error_code == "INVALID_SERVICE"


def test_build_login_url(cas_client: CASClient) -> None:
    url = cas_client.build_login_url(test_service_url)
    assert f"{cas_login_url}?service=https%3A%2F%2Ffoo.org" == url


def test_build_login_url_with_postback(cas_client: CASClient) -> None:
    url = cas_client.build_login_url(test_service_url, callback_post=True)
    assert f"{cas_login_url}?service=https%3A%2F%2Ffoo.org&method=POST" == url


def test_build_login_url_with_renew(cas_client: CASClient) -> None:
    url = cas_client.build_login_url(test_service_url, renew=True)
    assert f"{cas_login_url}?service=https%3A%2F%2Ffoo.org&renew=true" == url


def test_build_login_url_with_renew_and_postback(cas_client: CASClient) -> None:
    url = cas_client.build_login_url(test_service_url, callback_post=True, renew=True)
    assert (
        f"{cas_login_url}?service=https%3A%2F%2Ffoo.org&method=POST&renew=true" == url
    )


def test_build_validate_url(cas_client: CASClient) -> None:
    url = cas_client.build_validate_url(test_service_url, "tix")
    assert f"{cas_validate_url}?service=https%3A%2F%2Ffoo.org&ticket=tix" == url


def test_build_logout_url(cas_client: CASClient) -> None:
    url = cas_client.build_logout_url(test_service_url)
    assert f"{cas_logout_url}?service=https%3A%2F%2Ffoo.org" == url


def test_parse_attributes() -> None:
    s = """
        <cas:serviceResponse xmlns:cas='http://www.yale.edu/tp/cas'>
            <cas:authenticationSuccess>
                <cas:user>jdoe</cas:user>
                <cas:attributes>
                    <cas:clientIpAddress>10.0.0.2</cas:clientIpAddress>
                    <cas:isFromNewLogin>true</cas:isFromNewLogin>
                    <cas:mail>jdoe@foo.org</cas:mail>
                    <cas:authenticationDate>2022-01-21T23:03:05.920747Z</cas:authenticationDate>
                    <cas:bypassMultifactorAuthentication>false</cas:bypassMultifactorAuthentication>
                    <cas:authnContextClass>mfa-example</cas:authnContextClass>
                    <cas:successfulAuthenticationHandlers>DuoSecurityAuthenticationHandler</cas:successfulAuthenticationHandlers>
                    <cas:userAgent>Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.71 Safari/537.36</cas:userAgent>
                    <cas:cn>Jane Doe</cas:cn>
                    <cas:credentialType>DuoSecurityCredential</cas:credentialType>
                    <cas:authenticationMethod>DuoSecurityAuthenticationHandler</cas:authenticationMethod>
                    <cas:serverIpAddress>10.0.0.1</cas:serverIpAddress>
                    <cas:longTermAuthenticationRequestTokenUsed>false</cas:longTermAuthenticationRequestTokenUsed>
                    </cas:attributes>
            </cas:authenticationSuccess>
        </cas:serviceResponse>
    """
    cas_user = parse_cas_response(s)
    assert cas_user.userid == "jdoe"
    assert cas_user.attributes["mail"] == "jdoe@foo.org"
    assert cas_user.attributes["cn"] == "Jane Doe"
    assert cas_user.attributes["clientIpAddress"] == "10.0.0.2"
