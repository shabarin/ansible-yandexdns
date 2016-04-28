# ansible-yandexdns
Ansible module for managing DNS records on Yandex public DNS hosting

## usage examples

    - name: add SPF record for host host1.exampledomain.com
      yandexdns token=<TOKEN> state=present domain=exampledomain.com subdomain=host1 type=TXT content="v=spf1 a mx ip4:{{ ansible_default_ipv4.address }} -all"

    - name: add DKIM record for host host1.exampledomain.com
      yandexdns token=<TOKEN> state=present domain=exampledomain.com subdomain=host1.exampledomain.com._domainkey type=TXT content='<DKIM>'

## installation

Copy `yandexdns.py` file to `library/` folder. 

## recognized parameters
`token` (required) - the yandex pdd api token, can be obtained at https://pddimp.yandex.ru/api2/admin/get_token

`domain` (required) - the domain name (example.com)

`type` (required) - dns record type (can be SRV, TXT, NS, MX, SOA, A, AAAA, CNAME)

`admin_mail` - the 'admin_mail' value for SOA record

`content` - the dns record value

`priority` - integer priority value (for SRV and MX records)

`weight` - SRV record 'weight'

`port` - service port (for SRV record only)

`target` - the canonical host name (for SRV record only)

`subdomain` - subdomain name (host1), defaults to '@'

`ttl` - ttl value

