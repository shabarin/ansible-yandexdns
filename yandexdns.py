#!/usr/bin/python
# -*- coding: utf-8 -*-

import pycurl
try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO
from six import ensure_str
from six.moves.urllib_parse import urlencode

class Yandexdns(object):
    platform = 'Generic'
    distribution = None

    def __init__(self, module):

        self.module = module
        self.domain = module.params['domain']
        self.type = module.params['type']
        self.admin_mail = module.params['admin_mail']
        self.content = module.params['content']
        self.priority = module.params['priority']
        self.weight = module.params['weight']
        self.port = module.params['port']
        self.target = module.params['target']
        #useful correction
        if self.target is not None and self.target[-1] != '.':
            self.target += '.'
        self.subdomain = module.params['subdomain']
        self.ttl = module.params['ttl']

        self.token = module.params['token']
        self.state = module.params['state']

        self.record_id = 0
        self.cached_record = None
        
        
    def _queryapi(self, method_url, get, post):
        c = pycurl.Curl()
        if bool(get):
            query_url = method_url + '?' + urlencode(get)
        else:
            query_url = method_url
        c.setopt(c.URL, query_url)
        if bool(post):
            # first clear all fields that are None
            post_cleared = {}
            for i in post:
                if post[i] is not None:
                    post_cleared[i] = post[i]
            postfields = urlencode(post_cleared)
            c.setopt(c.POSTFIELDS, postfields)
        buffer = StringIO()
        c.setopt(c.WRITEFUNCTION, buffer.write)
        c.setopt(c.HTTPHEADER, ['PddToken: ' + self.token])
        c.perform()
        http_response_code = c.getinfo(c.RESPONSE_CODE)
        http_response_data = json.loads(ensure_str(buffer.getvalue()))
        c.close()
        if 200 != http_response_code:
            self.module.fail_json(msg='Error querying yandex pdd api, HTTP status=' + c.getinfo(c.RESPONSE_CODE) + ' error=' + http_response_data.error)
        return (http_response_code, http_response_data)
 

    def dnsrecord_find(self):
        (_, data) = self._queryapi('https://pddimp.yandex.ru/api2/admin/dns/list', { 'domain' : self.domain }, {})
        self.record_id = 0
        for record in data['records']:
            if self.subdomain == record['subdomain'] and self.type == record['type']:
                # some additional checks for SRV MX 
                if self.type == 'MX':
                    if self.priority != record['priority']:
                        continue
                if self.type == 'SRV':
                    if self.target != record['content']:
                        continue
                self.record_id = record['record_id']
                self.cached_record = record
                return True
        return False

    def dnsrecord_exists(self):
        return self.dnsrecord_find()

    def dnsrecord_add(self):
        rc = None
        out = ''
        err = ''
        post_data = { 
                "domain" : self.domain, 
                "type" : self.type, 
                'content' : self.content, 
                'subdomain' : self.subdomain, 
        }
        if self.type == 'A' or self.type == 'AAAA':
            post_data['ttl'] = self.ttl
        if self.type == 'SOA':
            post_data['admin_mail'] = self.admin_mail
            post_data['ttl'] = self.ttl
        if self.type == 'SRV' or self.type == 'MX':
            post_data['priority'] = self.priority
        if self.type == 'SRV':
            post_data['weight'] = self.weight
            post_data['port'] = self.port
            post_data['target'] = self.target
        (_, data) = self._queryapi('https://pddimp.yandex.ru/api2/admin/dns/add', {}, post_data)
        rc = 0
        out = data['success'] 
        if 'error' in data:
            err = data['error']
        return (rc, out, err)

    def _changes_needed(self):
        res = False
        for f in ['domain', 'subdomain', 'type']:
            res |= self.cached_record[f] != getattr(self, f)
        if self.type != 'SRV':
            res |= self.cached_record['content'] != self.content # yandex pdd api for SRV records take 'target' argument but returns 'content' field
        if self.type == 'SOA':
            res |= self.cached_record['admin_mail'] != self.admin_mail
        if self.type == 'SRV' or self.type == 'MX':
            res |= self.cached_record['priority'] != self.priority
        if self.type == 'SRV':
            for f in ['weight', 'port']:
                if getattr(self,f) is not None:
                    res |= self.cached_record[f] != getattr(self, f)
            res |= self.cached_record['content'] != self.target # seems like 'dns list' method return target in 'content' field
        return res
           

    def dnsrecord_mod(self):
        rc = None
        out = ''
        err = ''
        if self.record_id == 0:
            self.dnsrecord_find()
        if self._changes_needed():
            post_data = { 
                    "domain" : self.domain, 
                    'record_id': self.record_id, 
                    'subdomain' : self.subdomain, 
                    'content' : self.content, 
                    'priority' : self.priority 
            }
            if self.type == 'A' or self.type == 'AAAA':
                post_data['ttl'] = self.ttl
            if self.type == 'SOA':
                post_data['ttl'] = self.ttl
                post_data['admin_mail'] = self.admin_mail
            if self.type == 'SRV' or self.type == 'MX':
                post_data['priority'] = self.priority
            if self.type == 'SRV':
                post_data['port'] = self.port
                post_data['weight'] = self.weight
                post_data['target'] = self.target
            (_, data) = self._queryapi('https://pddimp.yandex.ru/api2/admin/dns/edit', {}, post_data) 
            out = data['success']
            if 'error' in data:
                err = data['error']
            rc = 0
        return (rc, out, err)

    def dnsrecord_del(self):
        rc = None
        out = ''
        err = ''
        if self.record_id == 0:
            self.dnsrecord_find()
        if self.record_id == 0:
            return (rc, out, err)
        else:
            post_data = { 'domain' : self.domain, 'record_id' : self.record_id }
            (_, data) = self._queryapi('https://pddimp.yandex.ru/api2/admin/dns/del', {}, post_data)
            out = data['success']
            if 'error' in data:
                err = data['error']
            rc = 0
            return (rc, out, err)

def main():
    module = AnsibleModule(
            argument_spec = dict(
                domain=dict(required=True, type='str'),
                type=dict(required=True, choices=['SRV', 'TXT', 'NS', 'MX', 'SOA', 'A', 'AAAA', 'CNAME'], type='str'),
                admin_mail=dict(required=False, type='str'),
                content=dict(required=False, type='str'),
                priority=dict(required=False, type='int'),
                weight=dict(required=False, type='int'),
                port=dict(required=False, type='int'),
                target=dict(required=False, type='str'),
                subdomain=dict(required=False, type='str', default='@'),
                ttl=dict(required=False, type='int'),

                #fqdn=dict(required=True, type='str'),
                token=dict(required=True, type='str'),
                state=dict(default='present', choices=['present', 'absent'], type='str')
            ),
            supports_check_mode=True
    )

    yandexdns = Yandexdns(module);

    rc = None
    out = ''
    err = ''
    result = {}
    result['state'] = yandexdns.state

    if module.check_mode:
        if yandexdns.state == 'absent':
            changed = True if yandexdns.dnsrecord_exists() else False
        elif yandexdns.state == 'present':
            changed = False if yandexdns.dnsrecord_exists() else True
        module.exit_json(changed=changed)

    if yandexdns.state == 'absent':

        if yandexdns.dnsrecord_exists():
            (rc, out, err) = yandexdns.dnsrecord_del()
            if rc != 0:
                module.fail_json(msg=err)

    elif yandexdns.state == 'present':

        if not yandexdns.dnsrecord_exists():
            (rc, out, err) = yandexdns.dnsrecord_add() #params
        else:
            (rc, out, err) = yandexdns.dnsrecord_mod() #params

        if rc is not None and rc != 0:
            module.fail_json(msg=err)

    if rc is None: 
        result['changed'] = False
    else:
        result['changed'] = True
    if out:
        result['stdout'] = out
    if err:
        result['stderr'] = err

    
    module.exit_json(**result)

from ansible.module_utils.basic import *
main()
